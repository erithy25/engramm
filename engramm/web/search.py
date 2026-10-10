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

ENGINES = ("brave", "bing", "duckduckgo", "duckduckgo-lite")
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
erzähle es sich""".split())


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


def query_forms(text: str) -> list[str]:
    """The question as typed and, as a second try, its content words with the names first
    ("How tall is the Zugspitze?" → "zugspitze tall")."""
    q = search_query(text)
    names = [w.lower() for w in _names(text)]
    rest = [w for w in content_words(q).split() if w not in names]
    kw = " ".join(dict.fromkeys(names + rest))
    return [q] + ([kw] if kw and kw.lower() != q.lower() else [])


_WORD = re.compile(r"[^\W_][\w'\-]*")


def _names(text: str) -> list[str]:
    """Capitalised words that are no question word and no abbreviation ("CEO") — names in an English
    question or keywords ("Zugspitze height"); in German every noun is capitalised, so there they
    only count as content words."""
    return [w for w in _WORD.findall(text) if w[:1].isupper() and not w.isupper() and w.lower() not in _STOP_QUERY]


def relevant(question: str, results: list[Result], lang: str = "en", top: int = 6) -> bool:
    """Do the results match the question? A result matches when it has every name of an English
    question and at least half of its content words (title, snippet or address; words compared by
    their first five letters, a word an answer uses for it counts: "tall" → "height", "metres").
    Two matching results among the first six are needed (one when the engine returned fewer than
    three), and one of them must have all the content words (all but one of three or more): an
    engine that distrusts the client answers "who is the CEO of Siemens" with Siemens' own home
    pages, which never say who leads it."""
    toks = list(dict.fromkeys(w for w in content_words(question).split() if len(w) >= 3))
    if not toks:
        return bool(results)
    must = {w.lower()[:5] for w in _names(question)} if lang != "de" else set()
    forms = {t: {t[:5]} | {x[:5] for x in _ANSWER_WORDS.get(t, ())} for t in toks}
    need = max(1, -(-len(toks) // 2))
    hits = full = 0
    for r in results[:top]:
        hay = f"{r.title} {r.snippet} {urllib.parse.unquote(r.url)}".lower()
        have = {t for t in toks if any(f in hay for f in forms[t])}
        if must <= {t[:5] for t in have} | {m for m in must if m in hay} and len(have) >= need:
            hits += 1
            full += len(have) >= len(toks) - (1 if len(toks) >= 3 else 0)
    return hits >= (1 if len(results) < 3 else 2) and full >= 1


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
    for block in re.split(r'<li class="b_algo"', page)[1:]:
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


def ddg_url(query: str, lang: str, lite: bool = False) -> str:
    base = "https://lite.duckduckgo.com/lite/?" if lite else "https://html.duckduckgo.com/html/?"
    return base + urllib.parse.urlencode({"q": query, "kl": _market(lang)[2]})


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
            return (["brave"] if conf.get("brave_key") else []) + ["bing", "duckduckgo", "duckduckgo-lite"]
        if choice == "duckduckgo":
            return ["duckduckgo", "duckduckgo-lite"]
        return [choice]

    def search(self, query: str, lang: str = "en", explicit: bool = False, k: int = 8) -> Found:
        """Ask the engines in turn until one returns results. Raises EgressError when the channel
        is off and the search was not asked for (the caller decides; nothing was sent)."""
        t0 = time.time()
        query = search_query(query)
        found = Found(query)
        if not query:
            return found
        chain = self.engines()
        for engine in chain + (["wikipedia"] if self.settings().get("engine", "auto") == "auto" else []):
            for form in query_forms(query)[:1 if engine in ("brave", "wikipedia") else 2]:
                results, why = self._ask(engine, form, lang, explicit)
                if results and not relevant(query, results, lang):
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
            req = Request("search", ddg_url(query, lang, lite=engine.endswith("lite")), f"search:{engine}",
                          ("duckduckgo.com",), headers=(accept_html, accept_lang), explicit=explicit)
        elif engine == "wikipedia":
            req = Request("search", wikipedia_url(query, lang), "search:wikipedia", (f"{lg}.wikipedia.org",),
                          headers=(("Accept", "application/json"),), explicit=explicit)
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

    def read(self, results: list[Result], n: int = 3, explicit: bool = False) -> list[dict]:
        """The main text of the first ``n`` readable result pages, fetched at once:
        [{"t": title, "x": text, "url", "host", "rank"}], in result order."""
        from engramm.web.clean import paragraphs
        picked = [r for r in results if _readable(r.url)][:n]
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
        return docs

    @staticmethod
    def best(question: str, results: list[Result], pages: list[dict], n: int = 6,
             lang: str = "en") -> list[tuple[float, str, dict]]:
        """The sentences of the snippets and pages that answer the question best, best first, at
        most two per source: (score, sentence, doc).

        A sentence must hold at least one content word of the question; each such word counts by
        its rarity among the candidates (a word of the page's own title a little less: the page is
        about it anyway), words an answer uses for what is asked ("how tall" → "metres", "high")
        count half. Higher-ranked results weigh a little more (the engine's own judgment), a
        snippet the engine cut off ("…") less, and a sentence whose names other sites name too
        more ("Roland Busch" on four sites, "Ann Fairchild" on one)."""
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
        cands = []
        expanded = [_EXPAND[w] for w in qset if w in _EXPAND]
        for d in docs:
            title = set(tokens(d["t"]))
            for para in d["x"].split("\n"):
                for sent in SENTENCE.split(para.strip()):
                    sent = sent.strip()
                    if 25 <= len(sent) <= 450 and _prose(sent) and not is_reference(sent) and not _junk(sent):
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
            if per.get(key, 0) < 2:
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
                   r"^dieser artikel (?:behandelt|beschreibt|befasst)|^zu weiteren bedeutungen|^siehe auch", re.I)
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
    return len(words) >= 6 and sum(1 for w in words if re.fullmatch(r"[a-zäöüß]{3,}[,;:]?", w)) >= 3


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
