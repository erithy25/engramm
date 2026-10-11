"""Web search (Atlas channel "search", docs/SPEC_ATLAS.md): ask a search engine, read the best
result pages here and keep their main text — rules only, no neural network.

    ws = WebSearch(egress)
    found = ws.search("capital of australia", lang="en")    # the results of the first engine that answers
    pages = ws.read(found.results, n=3)                      # main text of the best result pages
    best = ws.best(question, found.results, pages)           # the sentences that answer best, with source

Engines, tried in turn with engine "auto": the Brave Search API (only with a key), Bing,
DuckDuckGo (HTML page, then the lite page) and, when every engine refused, Wikipedia's own search.
A bot check (captcha, DuckDuckGo's "anomaly" page, HTTP 202/429) counts as no answer, and so do
results that do not match the question: an engine that distrusts a client may answer with
unrelated pages ("bitcoin kurs" → a download page). Then the question is asked once more as
keywords, and then the next engine. With one engine chosen, only that one is asked.

This is the one Atlas channel where the question leaves the computer: it goes to the search
engine. That happens only when the user switched the web search on (questions ENGRAMM cannot
answer offline) or asked for a search in so many words ("google …", "such im Internet nach …").
The network log shows each request (engine host, never the question).
"""

from __future__ import annotations

import base64
import html
import json
import math
import re
import time
import urllib.parse
from dataclasses import dataclass, field

from engramm.web.egress import Egress, Request, is_private_host

ENGINES = ("brave", "duckduckgo", "duckduckgo-lite", "bing")
ENGINE_NAMES = {"brave": "Brave Search", "bing": "Bing", "duckduckgo": "DuckDuckGo", "duckduckgo-lite": "DuckDuckGo",
                "wikipedia": "Wikipedia"}
MAX_QUERY = 300
PAGE_TIMEOUT = 8.0                              # seconds per result page; they are read in parallel
PAGE_BYTES = 2 << 20
# pages without readable text (videos, social media, app stores) stay in the list but are not read
_NO_TEXT_HOSTS = ("youtube.com", "youtu.be", "tiktok.com", "instagram.com", "facebook.com", "x.com", "twitter.com",
                  "pinterest.com", "apps.apple.com", "play.google.com", "linkedin.com", "vimeo.com", "spotify.com")
_NO_TEXT_PATH = re.compile(r"\.(?:pdf|docx?|xlsx?|pptx?|zip|mp[34]|jpe?g|png|gif|webp)(?:$|[?#])", re.I)
_BLOCKED = re.compile(r"captcha|anomaly-modal|unusual traffic|are you a robot|verify you are (?:a )?human|"
                      r"challenge-form|cf-chl|/sorry/index", re.I)
_TAG = re.compile(r"<[^>]+>")
# words a search query does not need ("what is", "wie hoch ist", "please") — both languages
_STOP_QUERY = frozenset("""a an the of in on at to for from by with and or is are was were be been it its this that these
those what which who whom whose when where why how do does did can could would should will shall may might must please
tell me us you your i my about there here der die das den dem des ein eine einer eines einem einen und oder ist sind war
waren wird werden wurde wurden hat haben hatte im in am an auf aus bei mit nach von vom zu zum zur für über unter wer wie
was wann wo warum wieso weshalb welche welcher welches welchen kannst könntest du mir mal bitte sag sage erzähl
erzähle es sich current currently latest now today recent recently still actually aktuell aktuelle aktuellen aktueller
derzeit derzeitige heute jetzt momentan gerade noch eigentlich""".split())


@dataclass
class Result:
    title: str
    url: str
    snippet: str
    site: str                                   # host without "www."
    engine: str
    rank: int = 0

    def to_dict(self) -> dict:
        return {"title": self.title, "url": self.url, "snippet": self.snippet, "site": self.site, "engine": self.engine}


@dataclass
class Found:
    query: str
    engine: str | None = None                   # the engine whose results these are
    results: list[Result] = field(default_factory=list)
    tried: list[tuple[str, str]] = field(default_factory=list)   # (engine, what went wrong)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return bool(self.results)


def site_of(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def clean_text(fragment: str) -> str:
    """Text of an HTML fragment: no tags, entities decoded, single spaces."""
    return " ".join(html.unescape(_TAG.sub(" ", fragment)).split()).replace(" ,", ",").replace(" .", ".")


def search_query(text: str, max_words: int = 12) -> str:
    """The question as a search query: as typed, without a trailing "?" and very long input cut."""
    q = " ".join(text.strip().split()).rstrip("?!. ")
    q = q[:MAX_QUERY]
    words = q.split()
    return " ".join(words[:max_words * 2]) if len(words) > max_words * 2 else q


def content_words(text: str) -> str:
    """The words of a question that carry its content ("wie hoch ist die zugspitze" → "hoch zugspitze")."""
    words = re.findall(r"[^\W_][\w'\-]*", text.lower())
    return " ".join(w for w in words if w not in _STOP_QUERY) or text


def query_forms(text: str, engine: str = "duckduckgo", lang: str = "en") -> list[str]:
    """The ways to ask an engine, best first: the question as typed and its content words with the
    thing asked about first ("How tall is the Zugspitze?" → "zugspitze tall"). Bing gets the
    keywords first: to a client it distrusts it answers for the first word alone ("How tall is the
    Zugspitze" → dictionary pages for "tall"), so that word must be the thing asked about."""
    q = search_query(text)
    names = [w.lower() for w in subject_words(text, lang)]
    rest = [w for w in content_words(q).split() if w not in names]
    kw = " ".join(dict.fromkeys(names + rest))
    forms = [q] + ([kw] if kw and kw.lower() != q.lower() else [])
    return forms[::-1] if engine == "bing" else forms


_COMMON_DE = re.compile(r"(?:ung|ungen|heit|keit|schaft|zeit|zeiten|tion|tät|nis|tum|ismus|ment|höhe|länge|preis|preise|"
                        r"kurs|wetter|rezept|rezepte|hauptstadt|einwohner|bedeutung)$")


def subject_words(text: str, lang: str = "en") -> list[str]:
    """The words that name the thing asked about, most telling first: the names of an English
    question; in German (every noun capitalised) the capitalised words that are no common nouns
    ("Öffnungszeiten", "Höhe"), from the end ("die Öffnungszeiten vom Louvre": "Louvre")."""
    names = _names(text)
    if lang != "de":
        return names
    proper = [w for w in names if not _COMMON_DE.search(w.lower())]
    return list(reversed(proper)) + [w for w in names if w not in proper]


def subject_phrase(text: str, lang: str = "en") -> str | None:
    """The whole name of the thing asked about: the run of adjacent name words around the most
    telling one ("Wann spielt Bayern München?" → "Bayern München", "How tall is the Zorblax
    Tower?" → "Zorblax Tower"); at most four words. None when the question names nothing."""
    first = next(iter(subject_words(text, lang)), None)
    if first is None:
        return None
    names = {w for w in _names(text) if lang != "de" or not _COMMON_DE.search(w.lower())} | {first}
    words = _WORD.findall(text)
    i = j = words.index(first)
    while i > 0 and words[i - 1] in names and j - i < 3:
        i -= 1
    while j + 1 < len(words) and words[j + 1] in names and j - i < 3:
        j += 1
    return " ".join(words[i:j + 1])


_WORD = re.compile(r"[^\W_][\w'\-]*")


def _names(text: str) -> list[str]:
    """Capitalised words that are no question word and no abbreviation ("CEO") — names in an English
    question or keywords ("Zugspitze height"); in German every noun is capitalised, so there they
    only count as content words."""
    return [w for w in _WORD.findall(text) if w[:1].isupper() and not w.isupper() and w.lower() not in _STOP_QUERY]


def relevant(question: str, results: list[Result], lang: str = "en", top: int = 6, strict: bool = True) -> bool:
    """Do the results match the question? A result matches when it has every name of an English
    question and at least half of its content words (title, snippet or address; words compared by
    their first five letters, a word an answer uses for it counts: "tall" → "height", "metres").
    Two matching results among the first six are needed (one when the engine returned fewer than
    three), and one of them must have all the content words (all but one of three or more): an
    engine that distrusts the client answers "who is the CEO of Siemens" with Siemens' own home
    pages, which never say who leads it. ``strict=False`` (engines that answer every client the same,
    DuckDuckGo, Brave, Wikipedia): one matching result is enough, and it need not hold every word —
    they understand typos and synonyms ("Chatbt" → ChatGPT pages) better than a word count does."""
    toks = list(dict.fromkeys(w for w in content_words(question).split() if len(w) >= 3))
    if not toks:
        return bool(results)
    must = [w.lower() for w in _names(question)] if lang != "de" else []
    forms = {t: {t[:5]} | {x[:5] for x in _ANSWER_WORDS.get(t, ())} for t in toks}
    need = max(1, -(-len(toks) // 2))
    hits = full = 0
    for r in results[:top]:
        hay = f"{r.title} {r.snippet} {urllib.parse.unquote(r.url)}".lower()
        words = set(re.findall(r"[^\W_]{4,}", hay))
        have = {t for t in toks if any(f in hay for f in forms[t]) or _near(t, words) or (t in _EXPAND and _EXPAND[t] in hay)}
        if all(m in have or m[:5] in hay or _near(m, words) for m in must) and len(have) >= need:
            hits += 1
            full += len(have) >= len(toks) - (1 if len(toks) >= 3 else 0)
    if not strict:
        return hits >= 1
    return hits >= (1 if len(results) < 3 else 2) and full >= 1


def _near(word: str, words: set[str]) -> bool:
    """A typo or another spelling of the word among the words ("chatbt" and "chatgpt")."""
    if len(word) < 5:
        return False
    import difflib
    return bool(difflib.get_close_matches(word, [w for w in words if abs(len(w) - len(word)) <= 2], n=1, cutoff=0.75))


def _market(lang: str) -> tuple[str, str, str]:
    """(language, country, DuckDuckGo region) for a conversation language."""
    return ("de", "DE", "de-de") if lang == "de" else ("en", "US", "us-en")


def _https(url: str) -> str | None:
    """An https URL to a public host, or None (http is upgraded; everything else is dropped)."""
    url = html.unescape(url.strip())
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url.startswith("https://") or len(url) > 2000:
        return None
    u = urllib.parse.urlsplit(url)
    if not u.hostname or u.username or u.password or is_private_host(u.hostname):
        return None
    return url


# ---------------------------------------------------------------------------
# engines: request and result page
# ---------------------------------------------------------------------------

def bing_url(query: str, lang: str) -> str:
    lg, cc, _ = _market(lang)
    return "https://www.bing.com/search?" + urllib.parse.urlencode(
        {"q": query, "setlang": lg, "cc": cc, "mkt": f"{lg}-{cc}", "count": "10"})


def _bing_target(href: str) -> str:
    """The result's own address behind Bing's click link (…/ck/a?…&u=a1<base64url>)."""
    href = html.unescape(href)
    u = urllib.parse.urlsplit(href)
    if (u.hostname or "").endswith("bing.com") and u.path.startswith("/ck/"):
        enc = (urllib.parse.parse_qs(u.query).get("u") or [""])[0]
        if enc.startswith("a1"):
            enc = enc[2:]
            try:
                return base64.urlsafe_b64decode(enc + "=" * (-len(enc) % 4)).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                return ""
        return ""
    return href


def parse_bing(page: str) -> list[Result]:
    out = []
    for block in re.split(r'<li class="b_algo(?:\s[^"]*)?"', page)[1:]:
        block = block.split('<li class="b_ad', 1)[0]
        h2 = re.search(r"<h2[^>]*>\s*<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", block, re.S)
        if not h2:
            continue
        url = _https(_bing_target(h2.group(1)))
        title = clean_text(h2.group(2))
        if not url or not title:
            continue
        rest = block[h2.end():]
        sn = re.search(r"<p[^>]*>(.*?)</p>", rest, re.S) or re.search(r'class="b_caption"[^>]*>(.*?)</div>', rest, re.S)
        # the date in front ("3 days ago · …") is no part of the text
        frag = re.sub(r"<span class=\"news_dt\">.*?</span>(?:\s|&nbsp;|&#0?183;|·|&#32;)*", "", sn.group(1), flags=re.S) \
            if sn else ""
        snippet = re.sub(r"^(?:Web|Webseite)\s*", "", clean_text(frag)).lstrip("·  ").strip()
        out.append(Result(title, url, snippet, site_of(url), "bing"))
    return out


def ddg_form(query: str, lang: str, lite: bool = False) -> tuple[str, tuple[tuple[str, str], ...]]:
    """(address, form fields) of DuckDuckGo's HTML or lite search form."""
    region = _market(lang)[2]
    if lite:
        return "https://lite.duckduckgo.com/lite/", (("q", query), ("kl", region))
    return "https://html.duckduckgo.com/html/", (("q", query), ("b", ""), ("kl", region))


def _ddg_target(href: str) -> str:
    href = html.unescape(href)
    if href.startswith("//"):
        href = "https:" + href
    u = urllib.parse.urlsplit(href)
    if (u.hostname or "").endswith("duckduckgo.com"):
        if u.path.startswith("/l/"):
            return (urllib.parse.parse_qs(u.query).get("uddg") or [""])[0]
        return ""                                # ads (/y.js) and DuckDuckGo's own pages
    return href


def parse_ddg(page: str) -> list[Result]:
    out = []
    for block in re.split(r'<div class="result ', page)[1:]:
        if block.startswith(("results_links_deep result--ad", "result--ad")) or "result--ad" in block[:200]:
            continue
        a = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S) or \
            re.search(r'href="([^"]+)"[^>]*class="result__a"[^>]*>(.*?)</a>', block, re.S)
        if not a:
            continue
        url = _https(_ddg_target(a.group(1)))
        title = clean_text(a.group(2))
        if not url or not title:
            continue
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div|td)>', block, re.S)
        out.append(Result(title, url, clean_text(sn.group(1)) if sn else "", site_of(url), "duckduckgo"))
    return out


def parse_ddg_lite(page: str) -> list[Result]:
    out = []
    links = [m for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", page, re.S) if re.search(r"class=[\"']result-link", m.group(1))]
    for i, a in enumerate(links):
        end = links[i + 1].start() if i + 1 < len(links) else len(page)
        row_start = page.rfind("<tr", 0, a.start())
        if "result-sponsored" in page[row_start:a.start()]:
            continue
        href = re.search(r"href=[\"']([^\"']+)[\"']", a.group(1))
        url = _https(_ddg_target(href.group(1))) if href else None
        title = clean_text(a.group(2))
        if not url or not title:
            continue
        sn = re.search(r"class=[\"']result-snippet[\"'][^>]*>(.*?)</td>", page[a.end():end], re.S)
        out.append(Result(title, url, clean_text(sn.group(1)) if sn else "", site_of(url), "duckduckgo-lite"))
    return out


def brave_url(query: str, lang: str) -> str:
    return "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": query, "count": "10", "search_lang": _market(lang)[0], "safesearch": "moderate"})


def parse_brave(body: str) -> list[Result]:
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return []
    out = []
    for r in ((d.get("web") or {}).get("results") or []):
        url = _https(str(r.get("url") or ""))
        title = clean_text(str(r.get("title") or ""))
        if url and title:
            snippet = clean_text(str(r.get("description") or ""))
            out.append(Result(title, url, snippet, site_of(url), "brave"))
    return out


def wikipedia_url(query: str, lang: str) -> str:
    return f"https://{_market(lang)[0]}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": "6", "utf8": "1"})


def parse_wikipedia(body: str, lang: str) -> list[Result]:
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return []
    host = f"{_market(lang)[0]}.wikipedia.org"
    out = []
    for r in ((d.get("query") or {}).get("search") or []):
        title = str(r.get("title") or "")
        if title:
            url = f"https://{host}/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            out.append(Result(title, url, clean_text(str(r.get("snippet") or "")), host, "wikipedia"))
    return out


def parse_instant(body: str) -> dict | None:
    """A DuckDuckGo Instant Answer as a document: its summary and one sentence per fact box line."""
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return None
    heading = clean_text(str(d.get("Heading") or ""))
    abstract = clean_text(str(d.get("AbstractText") or ""))
    lines = [abstract] if abstract else []
    for c in ((d.get("Infobox") or {}).get("content") or [])[:20]:
        label, value = clean_text(str(c.get("label") or "")), c.get("value")
        if label and isinstance(value, str) and value.strip() and not label.lower().endswith("profile"):
            value = clean_text(re.sub(r"[\[\]]+", " ", value)).strip(" .")   # "[ ISIN: [ DE0007236101]]"
            value = re.sub(rf"^{re.escape(label)}\s*:\s*", "", value, flags=re.I)
            if value:
                lines.append(f"{heading} – {label}: {value}.")
    if not heading or not lines:
        return None
    url = _https(str(d.get("AbstractURL") or "")) or "https://duckduckgo.com/?q=" + urllib.parse.quote(heading)
    return {"t": heading, "x": "\n".join(lines), "url": url, "host": site_of(url), "rank": 0, "facts": True}


def blocked(status: int, body: str, results: list[Result]) -> str | None:
    """Why an engine's answer is no result list, or None when it is one."""
    if results:
        return None
    if status in (202, 403, 429, 503):
        return f"refused (HTTP {status}: bot check or rate limit)"
    if _BLOCKED.search(body[:200_000]):
        return "refused (bot check)"
    return "no results"


# ---------------------------------------------------------------------------
# the search
# ---------------------------------------------------------------------------

class WebSearch:
    def __init__(self, egress: Egress):
        self.egress = egress

    def settings(self) -> dict:
        return self.egress.settings["channels"]["search"]

    def engines(self) -> list[str]:
        conf = self.settings()
        choice = conf.get("engine", "auto")
        if choice == "auto":
            return (["brave"] if conf.get("brave_key") else []) + ["duckduckgo", "duckduckgo-lite", "bing"]
        if choice == "duckduckgo":
            return ["duckduckgo", "duckduckgo-lite"]
        return [choice]

    def search(self, query: str, lang: str = "en", explicit: bool = False, k: int = 8,
               stop=None) -> Found:
        """Ask the engines in turn until one returns results. Raises EgressError when the channel
        is off and the search was not asked for (the caller decides; nothing was sent). ``stop``:
        asked before each engine; true ends the search (the answer came from elsewhere)."""
        t0 = time.time()
        query = search_query(query)
        found = Found(query)
        if not query:
            return found
        chain = self.engines()
        for engine in chain + (["wikipedia"] if self.settings().get("engine", "auto") == "auto" else []):
            if stop is not None and found.tried and stop():
                break
            for form in query_forms(query, engine, lang)[:1 if engine in ("brave", "wikipedia") else 2]:
                results, why = self._ask(engine, form, lang, explicit)
                if results and not relevant(query, results, lang, strict=engine == "bing"):
                    results, why = [], "results did not match the question"
                if results:
                    results = _dedupe(results)[:k]
                    for i, r in enumerate(results):
                        r.rank = i
                    found.engine, found.results = engine, results
                    break
                found.tried.append((engine, why or "no results"))
                if why and why.startswith(("refused", "the Brave")):
                    break                        # a bot check answers the next form the same way
            if found.results:
                break
        found.seconds = round(time.time() - t0, 2)
        return found

    def _ask(self, engine: str, query: str, lang: str, explicit: bool) -> tuple[list[Result], str | None]:
        lg = _market(lang)[0]
        accept_lang = ("Accept-Language", "de-DE,de;q=0.9,en;q=0.6" if lg == "de" else "en-US,en;q=0.9")
        accept_html = ("Accept", "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8")
        if engine == "brave":
            key = str(self.settings().get("brave_key") or "")
            if not key:
                return [], "no API key"
            req = Request("search", brave_url(query, lang), "search:brave", ("api.search.brave.com",),
                          headers=(("Accept", "application/json"), ("X-Subscription-Token", key)), explicit=explicit)
        elif engine == "bing":
            req = Request("search", bing_url(query, lang), "search:bing", ("bing.com",),
                          headers=(accept_html, accept_lang), explicit=explicit)
        elif engine in ("duckduckgo", "duckduckgo-lite"):
            # the form, posted as DuckDuckGo's own search box does: a GET of the same page is
            # answered with a bot check (HTTP 202) since 2026
            url, form = ddg_form(query, lang, lite=engine.endswith("lite"))
            origin = url.split("/", 3)[:3]
            origin = "/".join(origin)
            req = Request("search", url, f"search:{engine}", ("duckduckgo.com",), explicit=explicit, form=form,
                          headers=(accept_html, accept_lang, ("Referer", origin + "/"), ("Origin", origin)))
        elif engine == "wikipedia":
            req = Request("search", wikipedia_url(query, lang), "search:wikipedia", (f"{lg}.wikipedia.org",),
                          headers=(("Accept", "application/json"),), explicit=explicit, plain_agent=True)
        else:
            return [], "unknown engine"
        res = self.egress.fetch(req)
        body = res.body.decode("utf-8", "replace")
        if not res.ok and res.status not in (202,):
            if engine == "brave" and res.status in (401, 403, 422):
                return [], "the Brave API key was not accepted"
            if res.status in (403, 429, 503):
                return [], f"refused (HTTP {res.status}: bot check or rate limit)"
            if res.status:
                return [], f"HTTP {res.status}"
            return [], "timed out" if re.search(r"time(?:d)? ?out", res.error or "", re.I) else "network error"
        parse = {"brave": parse_brave, "bing": parse_bing, "duckduckgo": parse_ddg, "duckduckgo-lite": parse_ddg_lite,
                 "wikipedia": lambda b: parse_wikipedia(b, lang)}[engine]
        results = parse(body) if res.status == 200 else []
        return results, blocked(res.status, body, results)

    def instant(self, subject: str, lang: str = "en", explicit: bool = False) -> dict | None:
        """DuckDuckGo's Instant Answer API for the thing asked about: the encyclopedia summary and its
        fact box ("Key people: Sam Altman (CEO)") as a document of sentences, or None. An official,
        keyless API (no question text: only the name)."""
        if not subject or len(subject) > 80:
            return None
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": subject, "format": "json", "no_html": "1", "skip_disambig": "1", "t": "engramm"})
        req = Request("search", url, "facts:duckduckgo", ("api.duckduckgo.com",), headers=(("Accept", "application/json"),),
                      explicit=explicit, plain_agent=True, timeout=8.0)
        # through the pool: it runs while the search runs, and the service answers one request at a time
        res = self.egress.fetch_many([req])[0]
        if res is None or not res.ok:
            return None
        return parse_instant(res.body.decode("utf-8", "replace"))

    def read(self, results: list[Result], n: int = 3, explicit: bool = False, question: str = "") -> list[dict]:
        """The main text of ``n`` readable result pages, fetched at once: [{"t": title, "x": text,
        "url", "host", "rank"}]. With the question: the results that name its words first (an
        engine that distrusts the client puts realtor.com first for "real madrid founded"), an
        encyclopedia before the rest at equal match, one page more than needed (one often fails)."""
        from engramm.web.clean import paragraphs
        readable = [r for r in results if _readable(r.url)]
        if question:
            words = [w for w in content_words(question).lower().split() if len(w) >= 3]

            def match(r: Result) -> tuple:
                hay = f"{r.title} {r.snippet} {urllib.parse.unquote(r.url)}".lower()
                said = sum(bool(re.search(rf"\b{re.escape(w[:6])}", hay)) for w in words)
                return (-said, 0 if "wikipedia.org" in r.site else 1, r.rank)
            readable = sorted(readable, key=match)
            n += 1
        picked = readable[:n]
        reqs = [Request("search", r.url, "page", ("*",), max_bytes=PAGE_BYTES, explicit=explicit,
                        headers=(("Accept", "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"),),
                        timeout=PAGE_TIMEOUT) for r in picked]
        docs = []
        for r, res in zip(picked, self.egress.fetch_many(reqs)):
            if res is None or not res.ok:
                continue
            ctype = (res.content_type or "text/html").lower()
            if "html" not in ctype and "text/plain" not in ctype:
                continue
            page = _decode(res.body, ctype)
            text = "\n".join(paragraphs(page)) if "html" in ctype else page
            if len(text) >= 80:
                docs.append({"t": r.title, "x": text[:60_000], "url": r.url, "host": r.site, "rank": r.rank})
        return docs[:n - 1] if question else docs

    @staticmethod
    def best(question: str, results: list[Result], pages: list[dict], n: int = 6,
             lang: str = "en", per_source: int = 2) -> list[tuple[float, str, dict]]:
        """The sentences of the snippets and pages that answer the question best, best first, at
        most two per source: (score, sentence, doc).

        A sentence must hold at least one content word of the question; each such word counts by
        its rarity among the candidates (a word of the page's own title a little less: the page is
        about it anyway), words an answer uses for what is asked ("how tall" → "metres", "high")
        count half. Higher-ranked results weigh a little more (the engine's own judgment), a
        snippet the engine cut off ("…") less, and a sentence whose names other sites name too
        more ("Roland Busch" on four sites, "Ann Fairchild" on one). A question about the present
        ("who is the president", "currently", "aktuell") prefers sentences about the present
        ("current", "incumbent", "since 2025", "seit") over ones about the past ("former", "served
        from … to …")."""
        from engramm.web.clean import SENTENCE, is_reference
        from engramm.web.shelf import tokens
        docs = [{"t": r.title, "x": r.snippet, "url": r.url, "host": r.site, "rank": r.rank, "snippet": True}
                for r in results if len(r.snippet) >= 40] + list(pages)
        asked = [t for t in tokens(content_words(question)) if t not in _STOP_QUERY]
        if not docs or not asked:
            return []
        qset = set(asked)
        syn = {x for w in asked for x in _ANSWER_WORDS.get(w, ())} - qset
        names = [w.lower() for w in _names(question)] if lang != "de" else []
        phrases = _phrases(question)
        number = bool(_WANTS_NUMBER.search(question))
        clock = bool(_WANTS_CLOCK.search(question))
        now = _asks_now(question)
        why = bool(re.match(r"\s*(?:why|warum|wieso|weshalb|how come)\b", question, re.I))
        cands = []
        expanded = [_EXPAND[w] for w in qset if w in _EXPAND]
        for d in docs:
            title = set(tokens(d["t"]))
            for para in d["x"].split("\n"):
                para = re.sub(r"\s*\[(?:\d{1,3}|[a-z]|note \d+|citation needed)\]", "", para)
                for sent in SENTENCE.split(para.strip()):
                    sent = sent.strip()
                    if 25 <= len(sent) <= 450 and (d.get("facts") or _prose(sent)) and not is_reference(sent) \
                            and not _junk(sent):
                        toks = set(tokens(sent))
                        if toks & qset or any(x in sent.lower() for x in expanded):
                            cands.append((sent, d, toks, title))
        if not cands:
            return []
        # a sentence word counts for a question word in its other forms too ("highest" for "high"), and the
        # written-out form for an abbreviation ("chief executive officer" for "CEO")
        cands = [(sent, d, {w for w in qset | syn if any(_same_word(t, w) for t in toks)
                            or (w in _EXPAND and _EXPAND[w] in sent.lower())}, toks, title)
                 for sent, d, toks, title in cands]
        cands = [c for c in cands if c[2] & qset]
        if not cands:
            return []
        df: dict[str, int] = {}
        for _, _, said, _, _ in cands:
            for t in said:
                df[t] = df.get(t, 0) + 1
        N = len(cands)
        idf = {t: math.log(1 + N / c) for t, c in df.items()}
        sites: dict[str, str] = {}
        for d in docs:
            sites[d["host"]] = sites.get(d["host"], "") + " " + _digits((d["t"] + " " + d["x"][:20_000]).lower())
        stems = {w[:5] for w in qset | syn}
        scored = []
        for sent, d, said, toks, title in cands:
            hit, alt = said & qset, said & syn
            score = sum(idf[t] for t in hit) + sum(0.5 * idf[t] for t in alt)
            # the page's title implies its subject in each sentence, at half the weight of saying it
            score *= (0.5 + (len(hit) + 0.5 * len((title & qset) - hit)) / len(qset)) / math.sqrt(1 + 0.02 * len(toks))
            low = sent.lower()
            # the question's own wording ("capital of australia") in the sentence: it talks about just that
            score *= 1.0 + 0.3 * min(2, sum(ph in low for ph in phrases))
            if names:                                  # the thing asked about, named in the sentence itself
                score *= 1.5 if all(n in low for n in names) else 1.0 if any(n in low for n in names) else 0.45
            if clock:                                  # "opening hours": an answer has times of day
                score *= 1.6 if _CLOCK.search(sent) else 0.6
            elif number:                               # "how tall", "when": an answer has a number
                score *= 1.4 if re.search(r"\d", sent) else 0.75
            if number or clock:                        # the same number on other sites: "2962" on three of them
                nums = {x for x in re.findall(r"\d+(?:[.,]\d+)?", _digits(sent)) if len(x.replace(".", "").replace(",", "")) >= 2}
                agree = max((sum(x in text for h, text in sites.items() if h != d["host"]) for x in nums), default=0)
                score *= 1.0 + 0.25 * min(3, agree)
            if _PRONOUN_START.match(sent):            # "He held …": the subject is in an earlier sentence
                score *= 0.8
            if why and _BECAUSE.search(sent):          # "why …": the sentence that gives a reason
                score *= 1.5
            if now:                                    # "who is the president": the sentence about today
                score *= (1.6 if _NOW_S.search(sent) else 1.0) * (0.6 if _PAST_S.search(sent) else 1.0)
            cut = d.get("snippet") and sent.endswith(("…", "..."))
            given = [w for w in _NAME.findall(sent) if w.lower()[:5] not in stems and w not in _NOT_NAME]
            support = max((sum(w.lower() in text for h, text in sites.items() if h != d["host"]) for w in given),
                          default=0)
            score *= (1.0 + 0.06 * max(0, 5 - d.get("rank", 5))) * (1.0 + 0.2 * min(3, support)) * (0.7 if cut else 1.0)
            scored.append((score, _tidy(sent), d))
        scored.sort(key=lambda x: -x[0])
        out, per = [], {}
        for row in scored:
            key = row[2]["url"]
            if per.get(key, 0) < per_source:
                per[key] = per.get(key, 0) + 1
                out.append(row)
            if len(out) >= n:
                break
        return out


def _dedupe(results: list[Result]) -> list[Result]:
    seen, out = set(), []
    for r in results:
        key = r.url.split("#")[0].rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _readable(url: str) -> bool:
    site = site_of(url)
    if any(site == h or site.endswith("." + h) for h in _NO_TEXT_HOSTS):
        return False
    return not _NO_TEXT_PATH.search(url)


def _decode(body: bytes, ctype: str) -> str:
    m = re.search(r"charset=([\w-]+)", ctype)
    enc = m.group(1) if m else None
    if enc is None:
        meta = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
        enc = meta.group(1).decode("ascii", "ignore") if meta else "utf-8"
    try:
        return body.decode(enc, "replace")
    except LookupError:
        return body.decode("utf-8", "replace")


_JUNK = re.compile(r"cookie|javascript|sign in|log ?in|subscribe|newsletter|anmelden|registrier|datenschutz|privacy policy|"
                   r"all rights reserved|alle rechte|©|click here|hier klicken|advertisement|anzeige|"
                   r"^this (?:article|page) is about|^for other uses|^not to be confused|redirects here|"
                   r"^dieser artikel (?:behandelt|beschreibt|befasst)|^zu weiteren bedeutungen|^siehe auch|"
                   r"^(?:learn more|read more|find out more|click|see more|watch|explore our|mehr erfahren|jetzt lesen)\b|"
                   r"\bin this (?:guide|article|post|video|blog)\b|\bin diesem (?:artikel|beitrag|ratgeber|video)\b", re.I)
# the words an answer sentence uses for what a question asks ("how tall" → "… 2,962 m high")
_ANSWER_WORDS = {
    "tall": ("height", "high", "metres", "meters", "feet", "elevation"), "high": ("height", "metres", "meters", "elevation"),
    "height": ("high", "metres", "meters", "tall"), "hoch": ("höhe", "meter", "metern", "höchste"),
    "höhe": ("hoch", "meter", "metern"), "long": ("length", "kilometres", "kilometers", "km", "miles"),
    "lang": ("länge", "kilometer", "km"), "old": ("born", "age", "aged", "years"), "alt": ("geboren", "jahre", "alter"),
    "far": ("distance", "kilometres", "kilometers", "km", "miles"), "weit": ("entfernung", "kilometer", "km"),
    "big": ("area", "size", "square", "population"), "groß": ("fläche", "größe", "quadratkilometer", "einwohner"),
    "many": ("number", "population", "total"), "viele": ("anzahl", "einwohner", "insgesamt"),
    "died": ("death", "dead", "passed"), "gestorben": ("tod", "starb"), "born": ("birth", "née"), "geboren": ("geburt",),
    "ceo": ("chief", "executive", "vorstandsvorsitzender", "chef"), "chef": ("ceo", "vorstandsvorsitzender", "leitet"),
    "öffnungszeiten": ("geöffnet", "uhr", "montag", "dienstag", "mittwoch"), "hours": ("open", "opening", "closed"),
    "price": ("costs", "eur", "usd", "€", "$"), "preis": ("kostet", "euro", "€"), "kurs": ("preis", "euro", "€", "usd"),
    "live": ("population", "inhabitants", "residents"), "people": ("population", "inhabitants", "residents"),
    "leben": ("einwohner", "bevölkerung"), "menschen": ("einwohner", "bevölkerung"),
    "trainer": ("coach", "cheftrainer", "head coach", "manager"), "coach": ("manager", "head coach", "trainer"),
    "wrote": ("author", "written"), "founded": ("established", "founder"), "gegründet": ("gründung", "gründer"),
}


def _junk(sentence: str) -> bool:
    s = sentence.strip()
    return bool(_JUNK.search(s)) or s.count("|") >= 2 or len(s) < 25 or s.endswith("?")


def _tidy(sentence: str) -> str:
    """A snippet's date ("3 days ago · …", "12.05.2024 · …") is not part of the sentence; a "…"
    where the engine cut it off stays (it says that something is missing)."""
    s = re.sub(r"^(?:\d+ (?:days?|hours?|minutes?|weeks?) ago|vor \d+ \w+|\w{3} \d{1,2}, \d{4}|\d{1,2}\.\d{1,2}\.\d{4})"
               r"\s*[·•-]\s*", "", sentence.strip())
    return re.sub(r"\s*(?:…|\.\.\.)$", " …", s).strip()


_NAME = re.compile(r"\b[A-ZÄÖÜ][\w'’\-]{3,}")
_WANTS_CLOCK = re.compile(r"\b(?:opening hours|opening times|open(?:ing)? until|what time|when does .{1,40} (?:open|close)|"
                          r"öffnungszeiten|geöffnet|wann (?:öffnet|schließt|macht)|uhrzeit)\b", re.I)
_CLOCK = re.compile(r"\b(?:[01]?\d|2[0-3])(?:[:.][0-5]\d)\s*(?:a\.?m\.?|p\.?m\.?|uhr|h)?\b|\b(?:1[0-2]|0?[1-9])\s*(?:a\.?m\.?|p\.?m\.?)"
                    r"(?![a-z])|\b(?:[01]?\d|2[0-3])\s*uhr\b", re.I)


# abbreviations in questions and how pages write them out
_EXPAND = {"ceo": "chief executive officer", "cfo": "chief financial officer", "cto": "chief technology officer",
           "coo": "chief operating officer", "usa": "united states", "uk": "united kingdom", "eu": "european union",
           "un": "united nations", "nyc": "new york city", "brd": "bundesrepublik deutschland",
           "ezb": "europäische zentralbank", "ecb": "european central bank"}
_PRONOUN_START = re.compile(r"(?:he|she|it|they|his|her|its|their|this|these|er|sie|es|sein|seine|ihr|ihre|dies|diese)\b", re.I)


def _digits(text: str) -> str:
    """Numbers in one form: "2,962", "2.962" and "2 962" are "2962"."""
    return re.sub(r"(?<=\d)[,.\s\u202f\u00a0](?=\d{3}\b)", "", text)


def _prose(sentence: str) -> bool:
    """A sentence, not a list entry or a reference ("1 2 “Canberra – Australia's capital city”."):
    six words or more, three of them lower-case words of three letters or more."""
    words = sentence.split()
    return len(words) >= 6 and sum(1 for w in words if re.fullmatch(r"[a-zäöüß]{3,}[,;:.!]?", w)) >= 3


def agree(question: str, first: str, second: str) -> bool:
    """Does the second sentence say what the first says — the same number ("2962") or the same name
    ("Eugen Langen") that the question does not already hold?"""
    asked = set(re.findall(r"\w+", question.lower()))
    def facts(x: str) -> set[str]:
        nums = {n for n in re.findall(r"\d+(?:[.,]\d+)?", _digits(x)) if sum(c.isdigit() for c in n) >= 3}
        names = {re.sub(r"['’]s$", "", w.lower()) for w in _NAME.findall(x) if w not in _NOT_NAME}
        return nums | (names - asked)
    return bool(facts(first) & facts(second))


def _phrases(question: str) -> list[str]:
    """Runs of the question from one content word to the next ("capital of australia")."""
    words = re.findall(r"[^\W_][\w'\-]*", question.lower())
    pos = [i for i, w in enumerate(words) if w not in _STOP_QUERY and len(w) >= 3]
    return [" ".join(words[a:b + 1]) for a, b in zip(pos, pos[1:]) if b - a <= 3]


def answers(question: str, sentence: str) -> bool:
    """Can the sentence answer the question at all? An opening-hours question needs times of day
    and a word for opening or closing, a "how tall / when / how many" question a number; otherwise
    any sentence can."""
    if _WANTS_CLOCK.search(question):
        return bool(_CLOCK.search(sentence)) and bool(re.search(r"\b(?:open|opens|opening|close[sd]?|closing|hours|"
                                                               r"geöffnet|öffnet|schließt|öffnungszeiten)\b", sentence, re.I))
    if _WANTS_NUMBER.search(question):
        return bool(re.search(r"\d", sentence))
    return True


# -- the short answer --------------------------------------------------------------------------------
# What kind of answer a question wants, and the spans of that kind in the sentences that answer it
# best; the span most sentences and sites agree on is the answer ("Donald Trump" in nine sentences
# of three sites, "James Monroe" in one). No neural network: the question's wording, the shape of
# the span and the agreement of the sources.

_Q_PERSON = re.compile(r"^\s*(?:and |und )?(?:who(?:'s|m)?|wer|wem|wen)\b|\bwho (?:is|was|are|were|leads|runs|won|wrote|founded|"
                       r"invented|directed|owns|heads|coaches|plays|sang|painted|discovered)\b|\bwie hei(?:ß|ss)t (?:der|die|das)\b|"
                       r"\bname of the\b", re.I)
_Q_PLACE = re.compile(r"^\s*(?:where|wo|wohin|woher)\b|\bcapital (?:city )?of\b|\bhauptstadt\b|\bin which (?:city|country|state)\b|"
                      r"\bin welche[mr]? (?:stadt|land|staat)\b", re.I)
_Q_DATE = re.compile(r"^\s*(?:when|wann)\b|\b(?:what|which|in welchem) (?:year|jahr)\b|\bseit wann\b|\bdate of\b", re.I)
_Q_QUANTITY = re.compile(r"\bhow (?:tall|high|long|far|deep|wide|heavy|big|large|fast)\b|\b(?:height|length|elevation|distance)\b|"
                         r"\bwie (?:hoch|lang|weit|tief|breit|schwer|groß|schnell)\b|\b(?:höhe|länge|entfernung)\b", re.I)
_Q_COUNT = re.compile(r"\bhow many\b|\bwie viele\b|\b(?:population|einwohner|einwohnerzahl|number of|anzahl)\b", re.I)
_Q_MONEY = re.compile(r"\b(?:price|cost|costs|how much (?:is|does|do|are)|preis|kurs|kostet|wie viel kostet)\b", re.I)


def answer_type(question: str) -> str | None:
    """"hours", "money", "quantity", "count", "date", "place", "person" or None (a question that
    a sentence answers, not a span: "why …", "what is …")."""
    if _WANTS_CLOCK.search(question):
        return "hours"
    for kind, rx in (("money", _Q_MONEY), ("quantity", _Q_QUANTITY), ("count", _Q_COUNT), ("date", _Q_DATE),
                     ("place", _Q_PLACE), ("person", _Q_PERSON)):
        if rx.search(question):
            return kind
    return None


_BECAUSE = re.compile(r"\b(?:because|due to|caused by|this is why|that is why|the reason|results? from|weil|aufgrund|"
                      r"deshalb|daher|darum|verursacht|liegt (?:daran|an))\b", re.I)
_EVENT_Q = re.compile(r"\b(?:won|win|wins|winner|winners|champion|champions?hip|beat|defeated|gewann|gewonnen|gewinnt|sieger|"
                      r"siegerin|meister|weltmeister)\b", re.I)
_NOW_Q = re.compile(r"\b(?:current|currently|now|today|incumbent|present|at the moment|right now|aktuell\w*|derzeit\w*|jetzt|"
                    r"heute|momentan|zurzeit|amtierend\w*|gerade)\b", re.I)
_PRESENT_Q = re.compile(r"^\s*(?:who|wer|wie hei(?:ß|ss)t)\b.*\b(?:is|are|ist|sind|heißt|heisst|leads|runs|heads|owns|coaches|"
                        r"leitet|führt|regiert)\b", re.I)
_NOW_S = re.compile(r"\b(?:current|currently|incumbent|now|present|today|serving|has been|since|as of|aktuell\w*|derzeit\w*|"
                    r"amtierend\w*|seit|zurzeit|momentan|heute)\b", re.I)
_PAST_S = re.compile(r"\b(?:former|formerly|previous|previously|was the|served (?:as|from)|from \d{4} (?:to|until) \d{4}|"
                     r"\d{4}\s*[–-]\s*\d{4}|ehemalig\w*|früher\w*|war (?:der|die|von)|von \d{4} bis \d{4})\b", re.I)


def _asks_now(question: str) -> bool:
    """A question about the present: "currently", "aktuell", or "who is …" (who was is history)."""
    return bool(_NOW_Q.search(question) or _PRESENT_Q.search(question))


# capitalised words that are part of no name an answer gives: titles, articles, sentence starts
_TITLE_WORDS = frozenset("""The A An In On At Of For And But Or As By To From Under Since After Before During With Without Its His
Her Their Our Your My This That These Those There Then When While Where What Which Who Also However Although According
President Presidents Vice Chancellor Kanzler Bundeskanzler Bundeskanzlerin Chief Executive Officer Chairman Chairwoman Chair
Minister Prime Premier King Queen Prince Princess Pope Senator Governor Mayor Bürgermeister Bürgermeisterin Dr Mr Mrs Ms Sir
Lord Lady General Former Current Incumbent Acting Head Leader Founder Co-founder Director Manager Coach Trainer Herr Frau
Der Die Das Den Dem Des Ein Eine Einer Eines Im Am Vom Zum Zur Bei Mit Nach Seit Laut Unter Von Und Oder Er Sie Es
Amtierender Amtierende Amtierenden Aktueller Aktuelle Derzeitiger Derzeitige Ehemaliger Ehemalige Neuer Neue Neuen
Präsident Präsidentin Vorsitzender Vorsitzende Chef Chefin Gründer Gründerin Wikipedia Edit Born Died Geboren Gestorben
Hauptstadt Capital City Stadt Population Einwohner See Siehe Image Photo Official Website Homepage Inc Ltd Corp Corporation
Mai Jänner Januar Februar März April August September November Dezember
GmbH AG SE LLC Group Company Unternehmen Jetzt Liste Mehr Hier Alle Alles Neu Neue Infos Info Erfahre Erfahren Erhalten
Lesen Weitere Weiter Startseite News Nachrichten Aktuelles Übersicht Home Menu Menü Read More Learn Discover Find Click Visit
Watch Live Latest Breaking Update Updates Top Best Guide""".split())
_NOT_PERSON = frozenset("""amendment act constitution party league cup award awards prize trophy championship championships
tournament council committee commission court congress senate house parliament government administration department ministry
agency office university college school institute foundation museum church street avenue road river mountain lake island
islands bank group company corporation club team stadium arena airport station bridge tower hotel festival series season
edition final finals games olympics war battle treaty empire kingdom republic state states union city county district""".split())
_ORDINAL = re.compile(r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|twenty|thirty|"
                      r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)[\w\-]*")
_PARTICLES = frozenset("von van der den de da di du la le bin ibn al del dos zu y".split())
_SPAN_TOKEN = re.compile(r"[^\W\d_][\w'’\-]*\.?")


def _name_spans(sentence: str, asked: set[str]) -> list[tuple[str, int]]:
    """The names a sentence gives that the question does not: runs of capitalised words (with
    "von", "van", "de" … inside), split at titles and the question's own words ("President Donald
    Trump" → "Donald Trump", "Siemens CEO Roland Busch" → "Roland Busch"). (name, token position)."""
    toks = list(_SPAN_TOKEN.finditer(sentence))
    out, run = [], []

    def close() -> None:
        while run and run[-1][0].lower() in _PARTICLES:
            run.pop()
        while run and run[0][0].lower() in _PARTICLES:
            run.pop(0)
        if run and len(run) <= 4 and not all(re.fullmatch(r"[A-Z]\.", w) for w, _ in run):
            out.append((" ".join(w for w, _ in run), run[0][1]))
        run.clear()

    prev_end = None
    for i, m in enumerate(toks):
        w = re.sub(r"['’]s$", "", m.group(0))
        w = w if re.fullmatch(r"[A-Z]\.", w) else w.rstrip(".")
        gap = sentence[prev_end:m.start()] if prev_end is not None else " "
        prev_end = m.end()
        if run and gap.strip() not in ("",):
            close()
        low = w.lower()
        stop = w in _TITLE_WORDS or w.capitalize() in _TITLE_WORDS or w in _NOT_NAME or low[:5] in asked or low in asked
        if stop and run and not gap.strip() and w[:1].isupper() and (low[:5] in asked or low in asked):
            run.clear()                            # "UEFA Europa League", "FC Bayern": part of the asked name
        initial = bool(re.fullmatch(r"[A-Z]\.", w))
        if w[:1].isupper() and not stop and (initial or not (w.isupper() and 1 < len(w) <= 3 and run)):
            run.append((w, i))
        elif low in _PARTICLES and run:
            run.append((w, i))
        else:
            close()
        if m.group(0).endswith((".", "'s", "’s")) and not re.fullmatch(r"[A-Z]\.", m.group(0)):
            close()
    close()
    return out


_UNIT = (r"(?:km²|km2|m²|square (?:kilomet(?:re|er)s|miles)|sq ?mi|quadratkilometer|km/h|mph|°C|°F|"
         r"kilomet(?:re|er)s?|kilometern?|metres?|meters?|metern?|feet|foot|ft|miles?|mi|km|cm|mm|m|kg|kilograms?|"
         r"tonnes?|tons?|t|years?|jahre?n?)")
_QTY = re.compile(r"(?<![\w.,])(\d{1,3}(?:[,.\s  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)\s*(" + _UNIT + r")(?![\w²])", re.I)
_COUNT_RX = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(million|billion|mio\.?|millionen|milliarden|mrd\.?)(?!\w)|"
                       r"(?<![\w.,])(\d{1,3}(?:[,.\s  ]\d{3})+)(?![\d])", re.I)
_MONTHS = ("january|february|march|april|may|june|july|august|september|october|november|december|"
           "januar|februar|märz|mai|juni|juli|oktober|dezember")
_DATE_RX = re.compile(rf"\b(?:(?:{_MONTHS})\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}\.?\s+(?:{_MONTHS})\s+\d{{4}})\b", re.I)
_YEAR_RX = re.compile(r"(?<![\d.,])(1[0-9]{3}|20[0-9]{2})(?![\d.,]\d)")
_MONEY_RX = re.compile(r"(?:[$€£]\s?\d[\d,.]*(?:\s?(?:million|billion|bn|k|mio\.?|mrd\.?))?|\d[\d,.]*\s?(?:€|eur|euro|usd|us-dollar|"
                       r"dollars?|\$)(?!\w))", re.I)
_RANGE_RX = re.compile(r"\b(?:[01]?\d|2[0-3])(?:[:.][0-5]\d)?\s*(?:a\.?m\.?|p\.?m\.?|uhr|h)?\s*(?:–|-|to|until|bis)\s*"
                       r"(?:[01]?\d|2[0-3])(?:[:.][0-5]\d)?\s*(?:a\.?m\.?|p\.?m\.?|uhr|h)?(?![\w])", re.I)


def _number(text: str) -> float | None:
    """2,962 / 2.962 / 2 962 → 2962; 3,7 / 3.7 → 3.7."""
    t = re.sub(r"[\s  ]", "", text)
    if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", t):
        return float(re.sub(r"[,.]", "", t))
    try:
        return float(t.replace(",", "."))
    except ValueError:
        return None


def _spans(kind: str, sentence: str, asked: set[str]) -> list[tuple[str, str, int]]:
    """(key, text, position) of each span of the kind in the sentence; the key makes "2,962 m" and
    "2962 m" one answer, "3.7 million" and "3,700,000" too."""
    out = []
    if kind in ("person", "place"):
        for name, pos in _name_spans(sentence, asked):
            out.append((name.lower(), name, pos))
    elif kind == "quantity":
        prev_end = -10
        for m in _QTY.finditer(sentence):
            alt = re.fullmatch(r"\s*[(\[]\s*|\s*(?:or|oder|/)\s*", sentence[prev_end:m.start()]) if prev_end >= 0 else None
            prev_end = m.end()
            if alt:
                continue
            v = _number(m.group(1))
            unit = m.group(2).lower()
            unit = {"metres": "m", "meters": "m", "metre": "m", "meter": "m", "metern": "m", "feet": "ft", "foot": "ft",
                    "kilometres": "km", "kilometers": "km", "kilometre": "km", "kilometer": "km", "kilometern": "km",
                    "miles": "mi", "mile": "mi"}.get(unit, unit)
            if v is not None and unit not in ("years", "year", "jahre", "jahr", "jahren"):
                out.append((f"{v:g} {unit}", m.group(0).strip(), len(sentence[:m.start()].split())))
    elif kind == "count":
        for m in _COUNT_RX.finditer(sentence):
            if m.group(1):
                v = _number(m.group(1))
                mult = 1e9 if m.group(2).lower().startswith(("billion", "milliard", "mrd")) else 1e6
                v = v * mult if v is not None else None
            else:
                v = _number(m.group(3))
            if v:
                key = f"{float(f'{v:.2g}'):g}"          # two significant digits: 3.68 million ≈ 3,685,265
                out.append((key, m.group(0).strip(), len(sentence[:m.start()].split())))
    elif kind == "date":
        for m in _DATE_RX.finditer(sentence):
            year = re.search(r"\d{4}", m.group(0)).group(0)
            out.append((year, re.sub(r"\b0(\d)\b", r"\1", m.group(0)), len(sentence[:m.start()].split())))
        for m in _YEAR_RX.finditer(sentence):
            if not any(m.start() >= d.start() and m.end() <= d.end() for d in _DATE_RX.finditer(sentence)):
                out.append((m.group(1), m.group(1), len(sentence[:m.start()].split())))
    elif kind == "money":
        for m in _MONEY_RX.finditer(sentence):
            out.append((m.group(0).strip().lower(), m.group(0).strip(), len(sentence[:m.start()].split())))
    elif kind == "hours":
        for m in _RANGE_RX.finditer(sentence):
            out.append((m.group(0).strip().lower(), m.group(0).strip(), len(sentence[:m.start()].split())))
    return out


@dataclass
class Answer:
    text: str                                   # the short answer: "Donald Trump", "2,962 m"
    kind: str                                   # its kind (answer_type)
    sentence: str                               # the sentence that says it best
    doc: dict                                   # where that sentence stands
    votes: int                                  # sentences that give it
    sites: int                                  # sites that give it


def rank_answers(question: str, rows: list[tuple[float, str, dict]], lang: str = "en") -> tuple[str | None, list[dict]]:
    """(answer kind, candidates best first): {"text", "score", "votes", "sites", "facts", "best": (weight, sentence, doc)}.

    Each span of the wanted kind gets the weight of each sentence that gives it (relative to the
    best sentence). It weighs more when the sentence ties it to the question's words — "The
    incumbent president is Donald Trump", "Siemens CEO Roland Busch", a fact box line "Siemens – Key
    people: Roland Busch (CEO)" — and, for a question about the present, when the sentence is about
    the present too. A person is a name of two words or more ("Sam Altman", not "OpenAI"); a lone
    surname counts for the full name it ends. A span that is the question's own subject spelled
    differently ("ChatGPT" for "Chatbt") is no answer."""
    kind = answer_type(question)
    if kind is None or not rows:
        return kind, []
    qwords = [w for w in re.findall(r"[^\W_][\w'\-]*", question.lower()) if w not in _STOP_QUERY]
    asked = set(qwords) | {x for w in qwords if w in _EXPAND for x in _EXPAND[w].split()}
    asked |= {x for w in qwords for x in _ANSWER_WORDS.get(w, ())}
    asked |= {w[:5] for w in asked if len(w) >= 5}
    subject = {w for w in qwords if len(w) >= 5}
    now = _asks_now(question) and kind in ("person", "place")
    top = max(r[0] for r in rows) or 1.0
    year = re.search(r"\b(?:1[89]|20)\d{2}\b", question)   # "who won the 2014 World Cup": that year's sentences
    # the words the pages also write in lower case ("cup", "territory", "amendment", "jetzt"): common
    # words, which a name — written with a capital everywhere — is not
    lower = set()
    for d in {id(r[2]): r[2] for r in rows}.values():
        lower |= set(re.findall(r"(?<![.!?]\s)(?<!^)\b([a-zäöüß][a-zäöüß'\-]{2,})\b", d.get("t", "") + " " + d.get("x", "")[:30_000]))
    tally: dict[str, dict] = {}
    for score, sent, doc in rows:
        w = score / top
        if now:
            w *= (1.8 if _NOW_S.search(sent) else 1.0) * (0.5 if _PAST_S.search(sent) else 1.0)
        if year and kind != "date" and year.group(0) not in sent:
            w *= 0.3
        if doc.get("facts") and re.search(r" – [^:]{2,40}: ", sent):
            label = sent.split(" – ", 1)[1].split(":", 1)[0].lower()
            # a fact box line whose label is what is asked ("Key people" for a CEO, "Length" for how long)
            w *= 3.0 if any(x in label or label[:5] in x for x in asked if len(x) >= 3) else 0.3
        low = sent.lower()
        words = re.findall(r"[^\W_][\w'\-]*", low)
        near_pos = [i for i, t in enumerate(words) if t in asked or t[:5] in asked]
        # clauses (between commas, semicolons, brackets): "Roland Busch (CEO)" and "Jim Hagemann Snabe (chairman)"
        bounds, n = [], 0
        for part in re.split(r"[,;]|\s[–-]\s", sent):
            k = len(re.findall(r"[^\W_][\w'\-]*", part))
            bounds.append((n, n + k, any(t in asked or t[:5] in asked for t in re.findall(r"[^\W_][\w'\-]*", part.lower()))))
            n += k
        box = bool(doc.get("facts")) and " – " in sent and ":" in sent
        if kind == "count":                            # a count changes: the newest year a sentence names counts most
            years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", sent)]
            this = time.gmtime().tm_year
            if years:
                w *= 1.5 if max(years) >= this - 2 else 0.7 if max(years) < this - 5 else 1.0
        if kind == "count" and re.search(r"\b(?:urban area|metropolitan|metro area|agglomeration|ballungsraum|metropolregion|"
                                         r"großraum)\b", low) and not re.search(r"urban|metro|ballung|großraum", question.lower()):
            w *= 0.4                                   # the city, not its metropolitan area
        for key, text, pos in _spans(kind, sent, asked):
            toks = key.split()
            if kind in ("person", "place") and any(_near(t, subject) or t in subject for t in toks if len(t) >= 4):
                continue                               # the thing asked about, not its answer
            dist = min((abs(pos - i) for i in near_pos), default=99)
            clause = next((c for c in bounds if c[0] <= pos < c[1]), None)
            same = bool(clause and clause[2])
            weight = w * (2.0 if same or dist <= 2 else 1.3 if dist <= 8 else 1.0)
            if box and not same:
                weight *= 0.2                          # "Jim Hagemann Snabe (chairman)" in a CEO's fact line
            if kind == "person" and any(re.search(r"[a-zäöü][A-Z]|\d", t) for t in text.split()):
                continue                               # "OpenAI", "iPhone 15": no name of a person
            if kind == "person" and any(t in _NOT_PERSON or _ORDINAL.fullmatch(t) or _COMMON_DE.search(t) for t in toks):
                continue                               # "European Cup", "Twenty-second Amendment", "Gründung"
            if kind in ("person", "place"):
                common = [t for t in toks if t in lower and t not in _PARTICLES]
                if common:
                    weight *= 0.25 if len(common) == len(toks) or kind == "person" else 0.6
            e = tally.setdefault(key, {"text": text, "w": 0.0, "votes": 0, "sites": set(), "best": (-1.0, sent, doc),
                                       "facts": False})
            e["w"] += weight
            e["votes"] += 1
            e["sites"].add(doc.get("host", ""))
            e["facts"] |= box and same
            if weight > e["best"][0]:
                e["best"] = (weight, sent, doc)
                e["text"] = text
    if kind == "person":
        _merge_names(tally)
    elif kind in ("count", "quantity"):
        _merge_numbers(tally, 0.06 if kind == "count" else 0.01)
    for e in tally.values():
        e["score"] = e["w"] * (1.0 + 0.4 * (len(e["sites"]) - 1))
    return kind, sorted(tally.values(), key=lambda e: -e["score"])


def _absorb(into: dict, e: dict) -> None:
    into["w"] += e["w"]
    into["votes"] += e["votes"]
    into["sites"] |= e["sites"]
    into["facts"] |= e["facts"]
    if e["best"][0] > into["best"][0]:
        into["best"] = e["best"]


def _merge_names(tally: dict[str, dict]) -> None:
    """One person, one answer: "Trump", "Donald John Trump" and "Chefcoachs Vincent Kompany" count
    for the full name written most ("Donald Trump", "Vincent Kompany"); a lone word that ends no
    full name is no person's name ("OpenAI", "Deutschland") and drops out."""
    full = sorted((k for k in tally if " " in k), key=lambda k: -tally[k]["votes"])
    for k in full:
        if k not in tally:
            continue
        last, first = k.split()[-1], k.split()[0]
        for other in full:
            if other == k or other not in tally:
                continue
            o_last, o_first = other.split()[-1], other.split()[0]
            same = (o_last == last and (o_first.startswith(first[:3]) or first.startswith(o_first[:3]))) \
                or f" {k} " in f" {other} "
            if same and tally[other]["votes"] <= tally[k]["votes"]:
                _absorb(tally[k], tally.pop(other))
    for k in [k for k in tally if " " in k and re.fullmatch(r"[a-z]\.", k.split()[-1])]:
        owner = [f for f in tally if f != k and f.split()[0] == k.split()[0] and not f.endswith(".")]
        if len(owner) == 1:
            _absorb(tally[owner[0]], tally.pop(k))
    for k in [k for k in tally if " " not in k]:
        owner = [f for f in tally if " " in f and k in (f.split()[-1], f.split()[0])]
        e = tally.pop(k)
        if len(owner) == 1:
            _absorb(tally[owner[0]], e)


def _merge_numbers(tally: dict[str, dict], tolerance: float) -> None:
    """Numbers within the tolerance of each other are one answer (3.45, 3.7 and 3.88 million
    people in Berlin, from different years), shown as the most voted one says it."""
    def value(k: str) -> tuple[float, str] | None:
        m = re.match(r"([\d.e+]+)\s*(.*)", k)
        try:
            return (float(m.group(1)), m.group(2)) if m else None
        except ValueError:
            return None
    keys = sorted(tally, key=lambda k: -tally[k]["votes"])
    for k in keys:
        if k not in tally or value(k) is None:
            continue
        v, unit = value(k)
        for other in keys:
            if other == k or other not in tally or value(other) is None:
                continue
            ov, ounit = value(other)
            if ounit == unit and v and abs(ov - v) / v <= tolerance:
                _absorb(tally[k], tally.pop(other))


def short_answer(question: str, rows: list[tuple[float, str, dict]], lang: str = "en") -> Answer | None:
    """The answer the best sentences agree on (rank_answers), or None when they do not clearly
    agree on one: the winner needs two sentences (or a fact box line), twice the weight of the
    runner-up and a sentence that ties it to the question. A price or opening hours (they change,
    sites disagree) come from the best sentence that has them."""
    kind = answer_type(question)
    if kind is None or not rows:
        return None
    if kind in ("money", "hours"):
        asked = {w for w in re.findall(r"[^\W_][\w'\-]*", question.lower()) if w not in _STOP_QUERY}
        top = max(r[0] for r in rows) or 1.0
        for score, sent, doc in rows:
            sp = _spans(kind, sent, asked)
            if sp and score >= 0.5 * top:
                return Answer(sp[0][1], kind, sent, doc, 1, 1)
        return None
    if kind == "person" and _EVENT_Q.search(question) and not re.search(r"\b(?:1[89]|20)\d{2}\b", question):
        # "who won the last Champions League": the winner named most often is history's (Real Madrid),
        # not the last one — the sentence answers that, not a vote
        return None
    kind, ranked = rank_answers(question, rows, lang)
    if not ranked:
        return None
    win = ranked[0]
    second = ranked[1]["score"] if len(ranked) > 1 else 0.0
    if win["votes"] < 2 and not win["facts"]:
        return None
    votes2 = ranked[1]["votes"] if len(ranked) > 1 else 0
    clear = win["score"] >= 2.0 * second or (win["score"] >= 1.5 * second and win["votes"] >= max(3, 3 * votes2)
                                             and len(win["sites"]) >= 2)
    if not clear or win["score"] < 1.0:
        return None
    if kind == "person" and " " not in win["text"]:
        return None                                    # a person's answer is a full name
    sent, doc = _evidence(question, win, rows)
    return Answer(win["text"], kind, sent, doc, win["votes"], len(win["sites"]))


def _evidence(question: str, win: dict, rows: list[tuple[float, str, dict]]) -> tuple[str, dict]:
    """The sentence to show for the answer: one that holds the whole answer ("Johann Wolfgang von
    Goethe", not "Goethe wrote to his son") close to a word of the question, short rather than
    long, from a good row; else the one the answer got most weight from."""
    asked = {w for w in re.findall(r"[^\W_][\w'\-]*", question.lower()) if w not in _STOP_QUERY and len(w) >= 3}
    asked |= {x for w in list(asked) if w in _EXPAND for x in _EXPAND[w].split()}
    want = win["text"].lower()
    best, pick = -1.0, (win["best"][1], win["best"][2])
    now = _asks_now(question)
    for score, sent, doc in rows:
        low = sent.lower()
        if want not in low:
            continue
        words = re.findall(r"[^\W_][\w'\-]*", low)
        at = len(low[:low.index(want)].split())
        near = min((abs(at - i) for i, t in enumerate(words) if t in asked or t[:5] in {a[:5] for a in asked}), default=99)
        value = score * (1.6 if near <= 6 else 1.0) / (1.0 + max(0, len(sent) - 160) / 200)
        if now:
            value *= (1.4 if _NOW_S.search(sent) else 1.0) * (0.6 if _PAST_S.search(sent) else 1.0)
        if value > best:
            best, pick = value, (sent, doc)
    return pick


def _same_word(t: str, w: str) -> bool:
    """A word of a sentence and of the question are one word in another form ("highest", "high";
    "heights", "height"; "geöffnet", "geöffnete")."""
    if t == w:
        return True
    if len(w) >= 4 and t.startswith(w) and len(t) - len(w) <= 3:
        return True
    return len(t) >= 6 and len(w) >= 6 and t[:6] == w[:6]


_WANTS_NUMBER = re.compile(r"\b(?:how (?:tall|high|long|far|old|many|much|big|deep|wide|heavy|large|fast|hot|cold)|height|length|"
                           r"population|price|cost|costs|opening hours|hours|when|what year|which year|what time|"
                           r"wie (?:hoch|lang|weit|alt|viele?|groß|tief|breit|schwer|schnell|teuer|warm|kalt)|wann|"
                           r"welchem jahr|höhe|länge|preis|kurs|kostet|öffnungszeiten|einwohner|uhrzeit)\b", re.I)
# capitalised words that are no names (sentence starts, titles, months)
_NOT_NAME = frozenset("""This That These Those There Their They When While Where What Which With After Before During
According However Although Because Since From Into About Also Both Each Many Most Some Such Other Here Today
January February March April June July August September October November December Monday Tuesday Wednesday
Thursday Friday Saturday Sunday Diese Dieser Dieses Damit Dabei Danach Dort Heute Laut Seit Nach Unter Über Sowie
Januar Februar März Juni Juli Oktober Dezember Montag Dienstag Mittwoch Donnerstag Freitag Samstag Sonntag""".split())


# ---------------------------------------------------------------------------
# "google …": a search the user asks for
# ---------------------------------------------------------------------------

_POLITE_EN = r"(?:(?:hey|hi|ok(?:ay)?|so|engramm|please|pls|now|and)[,!]?\s+)*(?:(?:can|could|would|will) you\s+(?:please\s+)?|please\s+)?"
_POLITE_DE = r"(?:(?:hey|hallo|ok(?:ay)?|also|engramm|bitte|jetzt|und)[,!]?\s+)*(?:(?:kannst|könntest|würdest|magst) du\s+(?:bitte\s+)?(?:mal\s+)?|bitte\s+)?"
_WEB_EN = r"(?:the )?(?:web|internet|net|online|google|bing|duckduckgo)"
_ON_WEB_EN = r"(?:online|on (?:the )?(?:web|internet|net|google|bing)|in (?:the )?(?:web|internet)|with google)"
_WEB_DE = r"(?:im|ins|in|auf dem|übers?|über das) (?:internet|netz|web)|online|bei google|mit google|per google|im browser"
# "google is a company", "google's ceo": about Google, no request
_NOT_REQ = r"(?!\s*(?:is|was|has|had|does|did|are|were|and|or|ist|war|hat|hatte|sind|waren|und|oder|gehört|ceo|founder|gründer)\b|'s\b|’s\b)"
# "google …" alone says nothing about the language: the caller decides
_SEARCH_ANY = [
    re.compile(rf"^(?:google|bing)\b{_NOT_REQ}(?: (?:it|that|this|for))?(?: for)?[:,]?\s*(?P<q>.*)$", re.I),
]
_SEARCH_EN = [
    re.compile(rf"^{_POLITE_EN}(?:google|bing)\b{_NOT_REQ}(?: (?:it|that|this|for))?(?: for)?(?: (?:me|us))?[:,]?\s*(?P<q>.*)$", re.I),
    re.compile(rf"^{_POLITE_EN}(?:do|run|make|start) an? (?:web|internet|online|google) search(?: for| on| about)?[:,]?\s*(?P<q>.*)$", re.I),
    re.compile(rf"^{_POLITE_EN}(?:web|internet|online|google) search(?: for| on| about)?[:,]?\s*(?P<q>.*)$", re.I),
    re.compile(rf"^{_POLITE_EN}search {_WEB_EN}(?: for| about)?(?: (?:it|that|this))?[:,]?\s*(?P<q>.*)$", re.I),
    re.compile(rf"^{_POLITE_EN}(?:search|look) for (?P<q>.+?) {_ON_WEB_EN}$", re.I),
    re.compile(rf"^{_POLITE_EN}search (?P<q>.+?) {_ON_WEB_EN}$", re.I),
    re.compile(rf"^{_POLITE_EN}(?:look|check|find)(?: (?:it|that|this))? (?:up )?{_ON_WEB_EN}(?: for)?[:,]?\s*(?P<q>.*)$", re.I),
    re.compile(rf"^{_POLITE_EN}(?:look|check) up (?P<q>.+?) {_ON_WEB_EN}$", re.I),
    re.compile(rf"^{_POLITE_EN}(?:look|check) (?P<q>.+?) up {_ON_WEB_EN}$", re.I),
    re.compile(rf"^{_POLITE_EN}find (?P<q>.+?) {_ON_WEB_EN}$", re.I),
    re.compile(rf"^{_POLITE_EN}what does (?:google|the (?:web|internet)) say about (?P<q>.+)$", re.I),
]
_SEARCH_DE = [
    re.compile(rf"^{_POLITE_DE}(?:googeln|googlen|googel|google|googl)\b{_NOT_REQ}(?: (?:mal|doch|bitte|das|es|dies|danach))*(?: nach)?[:,]?\s*(?P<q>.*)$", re.I),
    re.compile(rf"^{_POLITE_DE}(?:mal )?(?:{_WEB_DE}) (?:mal )?(?:nach|zu|über) (?P<q>.+?) (?:suchen|schauen|nachschauen|gucken|recherchieren)$", re.I),
    re.compile(rf"^{_POLITE_DE}(?:such|suche|schau|schaue|guck|gucke|sieh|recherchier|recherchiere|finde?)(?: (?:mal|bitte|doch|das|es|dies|danach))*"
               rf" (?:{_WEB_DE})(?: (?:mal|bitte|doch))*(?: nach| zu| über)?[:,]?\s*(?P<q>.*)$", re.I),
    re.compile(rf"^{_POLITE_DE}(?:such|suche|schau|guck|recherchier|recherchiere|finde?)(?: (?:mal|bitte|doch))*(?: nach| zu)? (?P<q>.+?)"
               rf" (?:{_WEB_DE})(?: nach)?$", re.I),
    re.compile(rf"^{_POLITE_DE}(?:mal )?(?P<q>.+?) (?:googeln|googlen|ergoogeln|(?:{_WEB_DE}) (?:suchen|nachschauen|nachsehen|"
               rf"nachgucken|recherchieren|finden))$", re.I),
    re.compile(r"^(?:websuche|internetsuche|web-suche|google-suche|googlesuche)[:,]?\s*(?P<q>.*)$", re.I),
    re.compile(rf"^{_POLITE_DE}was (?:sagt|findet) (?:google|das internet|das netz) (?:zu|über) (?P<q>.+)$", re.I),
]
# "google it" / "such das im Internet": the question before
_THAT = re.compile(r"^(?:it|that|this|that up|it up|this up|that for me|it for me|for it|for that|das|es|dies|dazu|danach|"
                   r"das mal|es mal|mal|bitte|mal bitte|bitte mal|for me|für mich|)$", re.I)


def search_request(text: str) -> tuple[str, str] | None:
    """(language, query) for a request to search the web ("google the capital of Peru",
    "such im Internet nach Öffnungszeiten Louvre", "kannst du das googeln?"), else None. The
    language is "de", "en" or "" (a bare "google …" says nothing about it). The query is "" when
    it refers to the question before ("google it", "such das im Netz") or names nothing ("can you
    search the internet?")."""
    t = " ".join(text.strip().split()).rstrip(" ?!.")
    if not t or len(t) > 400:
        return None
    for lang, pats in (("", _SEARCH_ANY), ("de", _SEARCH_DE), ("en", _SEARCH_EN)):
        for rx in pats:
            m = rx.match(t)
            if not m:
                continue
            q = m.group("q").strip(" ,:;\"'„“”")
            q = re.sub(r"^(?:for|about|nach|zu|über)\s+", "", q, flags=re.I)
            q = re.sub(r"\s*\b(?:musst|kannst|könntest|solltest|sollst) du$", "", q, flags=re.I).strip()
            q = re.sub(r"^(?:the|der|die|das|dem|den|des)\s+(?=\S+\s+\S)", "", q, flags=re.I)
            if _THAT.match(q):
                q = ""
            return lang, q
    return None
