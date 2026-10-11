"""The web search (engramm/web/search.py) and its place in the dialog (engramm/chat/dialog.py):
result pages of Bing, DuckDuckGo (HTML and lite), the Brave Search API and Wikipedia's search are
read correctly (click links decoded, ads left out); DuckDuckGo gets its form posted (a GET is a bot
check), Bing the keywords first; a bot check or results that do not match the question (a typo is
no mismatch) send the search on to the next engine; DuckDuckGo's fact box answers by itself when
the engines fail; "google …" / "such im Internet nach …" are
recognised in both languages and search even with the channel off; with the channel off an
unanswered question gets an offer ("yes" searches); with it on, the search runs on its own; a
personal question never goes out; the reply names its sources and lists the results as links.
No real network: a test double plays the search engines and the pages."""

from __future__ import annotations

import base64
import datetime as dt
import json
import urllib.parse

import pytest

from engramm.chat.dialog import Assistant, DialogState
from engramm.chat.textmem import LoggedTextMemory
from engramm.web.atlas import Atlas
from engramm.web.egress import Egress, EgressError, Fetched, NetworkLog, check
from engramm.web.feeds import FeedRefresher
from engramm.web.search import (Result, WebSearch, content_words, parse_bing, parse_brave, parse_ddg, parse_ddg_lite,
                                parse_instant, parse_wikipedia, query_forms, relevant, search_request, subject_phrase,
                                subject_words)
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)

CLOCK = lambda: dt.datetime(2026, 10, 1, 18, 30)          # noqa: E731
TOWER = "https://quorvia.example/zorblax-tower"


def _bing_link(url: str) -> str:
    enc = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    return f"https://www.bing.com/ck/a?!&amp;&amp;p=4f2a&amp;ptn=3&amp;u=a1{enc}&amp;ntb=1"


def bing_page(results: list[tuple[str, str, str]]) -> str:
    items = "".join(
        f'<li class="b_algo" data-id iid=SERP.{i}><div class="b_tpcn"><a class="tilk" href="{_bing_link(u)}">'
        f'<div class="tptt">{urllib.parse.urlsplit(u).hostname}</div></a></div><h2><a target="_blank" '
        f'href="{_bing_link(u)}" h="ID=SERP,{i}">{t}</a></h2><div class="b_caption"><p class="b_lineclamp2">'
        f'<span class="news_dt">3 days ago</span>&nbsp;&#0183;&#32;{s}</p></div></li>'
        for i, (t, u, s) in enumerate(results))
    ad = '<li class="b_ad"><h2><a href="https://ads.example/buy">Buy a tower</a></h2></li>'
    return f'<html><body><ol id="b_results">{ad}{items}</ol></body></html>'


def ddg_page(results: list[tuple[str, str, str]]) -> str:
    ad = ('<div class="result results_links results_links_deep result--ad "><div class="links_main links_deep '
          'result__body"><h2 class="result__title"><a rel="nofollow" class="result__a" '
          'href="https://duckduckgo.com/y.js?ad_domain=ads.example">Buy a tower</a></h2></div></div>')
    items = "".join(
        f'<div class="result results_links results_links_deep web-result "><div class="links_main links_deep '
        f'result__body"><h2 class="result__title"><a rel="nofollow" class="result__a" '
        f'href="//duckduckgo.com/l/?uddg={urllib.parse.quote(u, safe="")}&amp;rut=abc">{t}</a></h2>'
        f'<a class="result__snippet" href="//duckduckgo.com/l/?uddg={urllib.parse.quote(u, safe="")}">{s}</a>'
        f'</div></div>' for t, u, s in results)
    return f"<html><body>{ad}{items}</body></html>"


def ddg_lite_page(results: list[tuple[str, str, str]]) -> str:
    rows = ('<tr class="result-sponsored"><td>1.</td><td><a rel="nofollow" href="https://duckduckgo.com/y.js?ad=1" '
            "class='result-link'>Buy a tower</a></td></tr>")
    for i, (t, u, s) in enumerate(results):
        rows += (f'<tr><td valign="top">{i + 1}.&nbsp;</td><td><a rel="nofollow" '
                 f'href="//duckduckgo.com/l/?uddg={urllib.parse.quote(u, safe="")}&amp;rut=x" class=\'result-link\'>{t}</a>'
                 f"</td></tr><tr><td>&nbsp;</td><td class='result-snippet'>{s}</td></tr>")
    return f"<html><body><table>{rows}</table></body></html>"


GOOD = [("The <strong>Zorblax</strong> Tower | Quorvia Travel", TOWER,
         "The <b>Zorblax</b> Tower in Velmar is 318 metres high and was opened in 1931."),
        ("Zorblax Tower - Quorvia Wiki", "https://wiki.quorvia.example/Zorblax_Tower",
         "The Zorblax Tower is a lattice tower in Velmar, the capital of Quorvia."),
        ("Visiting the Zorblax Tower", "https://www.velmar-tours.example/tower",
         "Tickets for the Zorblax Tower cost 12 euros."),
        ("Zorblax Tower (video)", "https://www.youtube.com/watch?v=zorblax", "A drone flight around the Zorblax Tower.")]
JUNK = [("TALL Definition & Meaning", "https://dictionary.example/tall", "Tall applies to what grows high."),
        ("Download the desktop app", "https://apps.example/download", "Download the app for free."),
        ("Zoo shops near you", "https://zoo.example/", "Find the best zoo shops.")]

PAGE = """<html><head><title>The Zorblax Tower</title></head><body><nav>Home | Tours | Contact</nav><main>
<p>The Zorblax Tower is the tallest structure in Quorvia and the symbol of its capital, Velmar. It stands on the
south bank of the Velm river and can be seen from almost everywhere in the city.</p>
<p>The tower is 318 metres high. It was designed by the engineer Mirela Tosk and was opened to the public in 1931,
after four years of construction.</p>
<p>More than two million people visit the tower every year, and the view from the top is one of the best in the
country when the weather is clear.</p></main><footer>© 2026 Quorvia Travel. All rights reserved.</footer></body></html>"""


def instant_answer(heading: str, abstract: str, facts: dict[str, str]) -> dict:
    return {"Heading": heading, "AbstractText": abstract, "AbstractURL": f"https://en.wikipedia.org/wiki/{heading.replace(' ', '_')}",
            "Infobox": {"content": [{"label": k, "value": v, "data_type": "string"} for k, v in facts.items()]
                        + [{"label": "Twitter profile", "value": "zorblax", "data_type": "twitter_profile"},
                           {"label": "Founded", "value": {"time": "+1931"}, "data_type": "time"}]}}


ZORBLAX_FACTS = instant_answer("Zorblax Tower", "The Zorblax Tower is a lattice tower in Velmar, Quorvia.",
                               {"Height": "318 metres", "Architect": "Mirela Tosk"})


class FakeWeb:
    """The search engines and pages of this test: the egress rules first (as the real backends),
    then an answer by host. ``bing`` / ``ddg`` / ``lite`` choose what those engines do; DuckDuckGo
    answers only its posted form (a GET gets the bot check, as the real one since 2026); ``facts``
    is what DuckDuckGo's Instant Answer API knows, by name."""
    name = "fake"

    def __init__(self, bing="good", ddg="good", lite="good", facts=None):
        self.bing, self.ddg, self.lite = bing, ddg, lite
        self.facts = facts or {}
        self.seen: list = []

    def fetch(self, req, settings) -> Fetched:
        check(req, settings)
        self.seen.append(req)
        u = urllib.parse.urlsplit(req.url)
        host = u.hostname or ""
        html_ = "text/html; charset=utf-8"
        if host == "www.bing.com":
            if self.bing == "captcha":
                return Fetched(True, 200, b"<html>Please solve this captcha</html>", final_host=host, content_type=html_)
            page = bing_page(GOOD if self.bing == "good" else JUNK)
            return Fetched(True, 200, page.encode(), final_host=host, content_type=html_)
        if host == "html.duckduckgo.com":
            if self.ddg == "anomaly" or not req.form or "Origin" not in dict(req.headers):
                return Fetched(False, 202, b'<div class="anomaly-modal">', error="HTTP 202", final_host=host)
            return Fetched(True, 200, ddg_page(GOOD).encode(), final_host=host, content_type=html_)
        if host == "lite.duckduckgo.com":
            if self.lite == "anomaly" or not req.form:
                return Fetched(False, 202, b"", error="HTTP 202", final_host=host)
            page = ddg_lite_page(GOOD if self.lite == "good" else JUNK)
            return Fetched(True, 200, page.encode(), final_host=host, content_type=html_)
        if host == "api.duckduckgo.com":
            q = urllib.parse.parse_qs(u.query)["q"][0]
            body = self.facts.get(q, {"Heading": "", "AbstractText": "", "Infobox": ""})
            return Fetched(True, 200, json.dumps(body).encode(), final_host=host, content_type="application/x-javascript")
        if host.endswith("wikipedia.org"):
            return Fetched(False, 429, b"", error="HTTP 429", final_host=host)
        if host == "api.search.brave.com":
            dict_headers = dict(req.headers)
            if dict_headers.get("X-Subscription-Token") != "good-key":
                return Fetched(False, 401, b"", error="HTTP 401", final_host=host)
            body = {"web": {"results": [{"title": t, "url": u_, "description": s} for t, u_, s in GOOD]}}
            return Fetched(True, 200, json.dumps(body).encode(), final_host=host, content_type="application/json")
        if host == "quorvia.example":
            return Fetched(True, 200, PAGE.encode(), final_host=host, content_type=html_)
        return Fetched(False, 404, b"", error="HTTP 404", final_host=host)


def _egress(tmp_path, web: FakeWeb, **search) -> Egress:
    e = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"), backend=web)
    if search:
        e.set_channel("search", **search)
    return e


# -- result pages --------------------------------------------------------------------------------

def test_result_pages_are_read():
    for parse, page in ((parse_bing, bing_page(GOOD)), (parse_ddg, ddg_page(GOOD)), (parse_ddg_lite, ddg_lite_page(GOOD))):
        got = parse(page)
        assert [r.url for r in got] == [u for _, u, _ in GOOD], parse.__name__       # click links decoded, no ads
        assert got[0].title == "The Zorblax Tower | Quorvia Travel" and got[0].site == "quorvia.example"
        assert got[0].snippet.startswith("The Zorblax Tower in Velmar is 318 metres high"), got[0].snippet
        assert got[2].site == "velmar-tours.example"                                  # "www." is no part of the site
    brave = parse_brave(json.dumps({"web": {"results": [
        {"title": "A <strong>b</strong>", "url": "https://a.example/x", "description": "c <strong>d</strong>"},
        {"title": "local", "url": "https://192.168.1.10/admin", "description": "never"},
        {"title": "plain", "url": "http://b.example/", "description": ""}]}}))
    assert [(r.title, r.url, r.snippet) for r in brave] == [("A b", "https://a.example/x", "c d"),
                                                             ("plain", "https://b.example/", "")]
    wiki = parse_wikipedia(json.dumps({"query": {"search": [{"title": "Zorblax Tower", "snippet":
                                                             '<span class="searchmatch">Zorblax</span> Tower is'}]}}), "de")
    assert wiki[0].url == "https://de.wikipedia.org/wiki/Zorblax_Tower" and wiki[0].snippet == "Zorblax Tower is"
    assert parse_bing("<html>captcha</html>") == [] and parse_brave("not json") == []
    variant = bing_page(GOOD).replace('<li class="b_algo"', '<li class="b_algo b_vtl_deeplinks"')
    assert [r.url for r in parse_bing(variant)] == [u for _, u, _ in GOOD]   # extra classes on a result


def test_instant_answer_is_read():
    doc = parse_instant(json.dumps(ZORBLAX_FACTS))
    assert doc["t"] == "Zorblax Tower" and doc["facts"] and doc["host"] == "en.wikipedia.org"
    assert doc["x"].split("\n") == ["The Zorblax Tower is a lattice tower in Velmar, Quorvia.",
                                    "Zorblax Tower – Height: 318 metres.", "Zorblax Tower – Architect: Mirela Tosk."]
    assert parse_instant(json.dumps({"Heading": "", "AbstractText": "", "Infobox": ""})) is None
    assert parse_instant("<html>") is None


def test_relevance_and_query_forms():
    good, junk = parse_bing(bing_page(GOOD)), parse_bing(bing_page(JUNK))
    assert relevant("How tall is the Zorblax Tower?", good)
    assert not relevant("How tall is the Zorblax Tower?", junk)              # "tall" alone: a dictionary
    assert not relevant("Wie hoch ist der Zorblax Tower?", junk, "de")
    assert query_forms("How tall is the Zugspitze?") == ["How tall is the Zugspitze", "zugspitze tall"]
    # Bing answers a client it distrusts for the first word alone: the thing asked about goes first
    assert query_forms("How tall is the Zugspitze?", "bing") == ["zugspitze tall", "How tall is the Zugspitze"]
    assert query_forms("Wie sind die Öffnungszeiten vom Louvre?", "bing", "de")[0] == "louvre öffnungszeiten"
    assert content_words("Wie hoch ist die Zugspitze?") == "hoch zugspitze"
    assert content_words("Who is the current CEO of Siemens?") == "ceo siemens"
    assert subject_words("Wie sind die Öffnungszeiten vom Louvre?", "de") == ["Louvre", "Öffnungszeiten"]
    assert subject_phrase("Wann spielt Bayern München das nächste Mal?", "de") == "Bayern München"
    assert subject_phrase("How tall is the Zorblax Tower?") == "Zorblax Tower"
    assert subject_phrase("what is the bitcoin price") is None


def test_a_typo_is_no_mismatch():
    """"Chatbt" for ChatGPT: DuckDuckGo understands it and answers with the right pages; they count
    as matching (a near spelling of the name), Bing's word-for-word junk still does not."""
    q = "Who is current CEO of Chatbt?"
    results = [Result("Sam Altman - Wikipedia", "https://en.wikipedia.org/wiki/Sam_Altman",
                      "Sam Altman is the chief executive officer of OpenAI, the company behind ChatGPT.", "en.wikipedia.org",
                      "duckduckgo", 0),
               Result("Who Owns ChatGPT? Owner & Makers", "https://example.org/chatgpt-owner",
                      "ChatGPT is made by OpenAI; its CEO is Sam Altman.", "example.org", "duckduckgo", 1),
               Result("OpenAI - Wikipedia", "https://en.wikipedia.org/wiki/OpenAI",
                      "OpenAI is an American artificial intelligence organization.", "en.wikipedia.org", "duckduckgo", 2)]
    assert relevant(q, results, strict=False)
    assert not relevant(q, parse_bing(bing_page(JUNK)), strict=False)
    assert not relevant("Who is the CEO of Zorblax?", results, strict=False)  # another name entirely


@pytest.mark.parametrize("text,want", [
    ("google the capital of Peru", ("", "capital of Peru")),
    ("Google it", ("", "")),
    ("can you google who won the 2022 world cup?", ("en", "who won the 2022 world cup")),
    ("search the web for louvre opening hours", ("en", "louvre opening hours")),
    ("look up the bitcoin price online", ("en", "bitcoin price")),
    ("look it up online", ("en", "")),
    ("web search: zugspitze height", ("en", "zugspitze height")),
    ("Googel mal die Öffnungszeiten vom Louvre", ("de", "Öffnungszeiten vom Louvre")),
    ("such im Internet nach dem Bitcoin Kurs", ("de", "Bitcoin Kurs")),
    ("Kannst du das googeln?", ("de", "")),
    ("kannst du mal im internet nach dem wetter in berlin suchen", ("de", "wetter in berlin")),
    ("Schau mal im Netz nach, wer CEO von Siemens ist", ("de", "wer CEO von Siemens ist")),
    ("kannst du googeln wer CEO von Siemens ist", ("de", "wer CEO von Siemens ist")),
    ("das musst du googeln", ("de", "")),
    ("Websuche: Zugspitze Höhe", ("de", "Zugspitze Höhe")),
    ("I use google every day", None),
    ("who founded google", None),
    ("google is a company", None),
    ("google's ceo", None),
    ("wie funktioniert google", None),
    ("find me a restaurant", None),
])
def test_search_requests(text, want):
    assert search_request(text) == want


# -- the engines in turn -------------------------------------------------------------------------

def test_engines_in_turn(tmp_path):
    web = FakeWeb(ddg="anomaly", lite="junk")
    e = _egress(tmp_path, web, enabled=False)
    ws = WebSearch(e)
    with pytest.raises(EgressError, match="switched off"):                  # not asked for, channel off: nothing sent
        ws.search("How tall is the Zorblax Tower?", "en")
    assert web.seen == []
    found = ws.search("How tall is the Zorblax Tower?", "en", explicit=True)
    # DuckDuckGo answered with a bot check, its lite page twice with unrelated pages (the question,
    # then keywords); Bing, asked with the keywords first, with the tower
    assert found.engine == "bing" and found.results[0].url == TOWER, found
    assert [t[0] for t in found.tried] == ["duckduckgo", "duckduckgo-lite", "duckduckgo-lite"]
    assert "refused" in found.tried[0][1] and "did not match" in found.tried[1][1]
    assert [r.what for r in web.seen] == ["search:duckduckgo", "search:duckduckgo-lite", "search:duckduckgo-lite",
                                          "search:bing"]
    ddg = web.seen[0]
    assert ddg.url == "https://html.duckduckgo.com/html/" and dict(ddg.form) == {"q": "How tall is the Zorblax Tower",
                                                                               "b": "", "kl": "us-en"}
    assert dict(ddg.headers)["Origin"] == "https://html.duckduckgo.com"   # posted as from its own search box
    assert dict(web.seen[2].form)["q"] == "zorblax tower tall"
    assert "q=zorblax+tower+tall" in web.seen[3].url
    assert all(dict(r.headers).get("Accept-Language", "").startswith("en") for r in web.seen)
    pages = ws.read(found.results, n=3, explicit=True)
    assert [p["url"] for p in pages] == [TOWER]                            # the others 404; videos are never read
    assert all("youtube" not in r.url for r in web.seen)
    best = ws.best("How tall is the Zorblax Tower?", found.results, pages)
    assert best[0][1] == "The tower is 318 metres high." or "318 metres high" in best[0][1], best[:3]
    log = e.log.tail(50)
    assert {x["channel"] for x in log} == {"search"} and all("tall" not in x["what"] for x in log)


def test_one_engine_and_the_brave_key(tmp_path):
    web = FakeWeb(bing="captcha")
    e = _egress(tmp_path, web, enabled=True, engine="bing")
    found = WebSearch(e).search("Zorblax Tower height", "en")
    assert not found.ok and found.tried == [("bing", "refused (bot check)")]   # one engine chosen: no other one
    e.set_channel("search", engine="auto", brave_key="bad-key")
    found = WebSearch(e).search("Zorblax Tower height", "en")
    assert found.tried[0] == ("brave", "the Brave API key was not accepted") and found.engine == "duckduckgo"
    e.set_channel("search", brave_key="good-key")
    found = WebSearch(e).search("Zorblax Tower height", "de")
    assert found.engine == "brave" and found.results[0].url == TOWER
    brave_req = next(r for r in web.seen if r.what == "search:brave" and dict(r.headers)["X-Subscription-Token"] == "good-key")
    assert "search_lang=de" in brave_req.url
    assert all("good-key" not in json.dumps(x) for x in e.log.tail(50))       # the key is never logged


# -- in the dialog -------------------------------------------------------------------------------

@pytest.fixture()
def web_chat(corpus, tmp_path, monkeypatch):   # noqa: F811
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    monkeypatch.setattr(FeedRefresher, "refresh_now", lambda self: {})
    web = FakeWeb(bing="good")
    eg = _egress(tmp_path, web, enabled=False)       # most of these tests are about the switch being off
    atlas = Atlas(eg, None, tmp_path / "state")
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "chat_memory.log")), clock=CLOCK)
    a.atlas = atlas
    return a, eg, web


def test_google_command_searches_even_with_the_channel_off(web_chat):
    a, eg, web = web_chat
    st = DialogState("g")
    r = a.turn(st, "google how tall is the Zorblax Tower")
    assert r.via == "web" and r.kind == "answer" and r.answer == "318 metres", r.text
    assert r.text.startswith("The Zorblax Tower is 318 metres tall."), r.text           # the answer first
    # one source (the page that says it), no list of results, no footer about the search
    assert r.source["kind"] == "web" and r.source["key"] == TOWER and r.source["source"] == "quorvia.example"
    assert r.links == [] and "Searched with" not in r.text and "results are below" not in r.text
    assert "Web search" in r.text                                            # the tip to switch it on, once
    assert eg.log.tail(50) and all(x["channel"] == "search" for x in eg.log.tail(50))
    r2 = a.turn(st, "search the web for the Zorblax Tower tickets")
    assert r2.via == "web" and "Web search" not in r2.text, r2.text


def test_offer_then_yes_searches(web_chat):
    a, eg, web = web_chat
    st = DialogState("o")
    r = a.turn(st, "How tall is the Zorblax Tower?")
    assert r.text.endswith("Should I search the web for it?"), r.text
    assert web.seen == []                                                    # an offer sends nothing
    r = a.turn(st, "yes please")
    assert r.via == "web" and "318 metres" in r.text, r.text
    assert any("Zorblax" in dict(q.form).get("q", "") for q in web.seen if q.what.startswith("search:"))


def test_google_it_takes_the_question_before(web_chat):
    a, eg, web = web_chat
    st = DialogState("i")
    a.turn(st, "How tall is the Zorblax Tower?")
    r = a.turn(st, "google it")
    assert r.via == "web" and "318 metres" in r.text, r.text
    r = a.turn(DialogState("i2"), "can you search the internet?")
    assert r.via == "web" and "what should i search for" in r.text.lower() and r.links == []


def test_channel_on_searches_by_itself_but_never_personal_questions(web_chat):
    a, eg, web = web_chat
    eg.set_channel("search", enabled=True)
    st = DialogState("a")
    r = a.turn(st, "How tall is the Zorblax Tower?")
    assert r.via == "web" and "318 metres" in r.text and "Should I search" not in r.text, r.text
    n = len(web.seen)
    for q in ("What is my favourite tower?", "How old are you?", "my sister is called Lena", "thanks"):
        a.turn(st, q)
    assert len(web.seen) == n                                                # nothing about the user went out


def test_german(web_chat):
    a, eg, web = web_chat
    st = DialogState("de")
    r = a.turn(st, "such im Internet nach der Höhe vom Zorblax Tower")
    # no German sentence form for "der Höhe vom …": the source's own sentence, which holds the answer
    assert r.via == "web" and r.answer == "318 metres" and r.text.startswith("Laut quorvia.example: "), r.text
    assert "318 metres high" in r.text and "Gesucht mit" not in r.text, r.text
    req = next(q for q in web.seen if q.what == "search:duckduckgo")
    assert dict(req.form)["kl"] == "de-de" and dict(req.headers)["Accept-Language"].startswith("de")
    r = a.turn(DialogState("de2"), "googel mal")
    assert "wonach soll ich suchen" in r.text, r.text


def test_a_blocked_engine_is_no_dead_end(corpus, tmp_path, monkeypatch):   # noqa: F811
    """DuckDuckGo blocks: Bing answers, and the reply is just the answer (which engine is the
    network log's business, not the reply's)."""
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    web = FakeWeb(ddg="anomaly", lite="anomaly")
    eg = _egress(tmp_path, web, enabled=False)
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "m.log")), clock=CLOCK)
    a.atlas = Atlas(eg, None, tmp_path / "state")
    r = a.turn(DialogState("b"), "google how tall is the Zorblax Tower")
    assert r.answer == "318 metres" and r.text.startswith("The Zorblax Tower is 318 metres tall."), r.text
    assert "blocked" not in r.text and any(x["what"] == "search:bing" for x in eg.log.tail(50))


def test_nothing_found_is_said_plainly(corpus, tmp_path, monkeypatch):   # noqa: F811
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    web = FakeWeb(bing="captcha", ddg="anomaly", lite="anomaly")
    eg = _egress(tmp_path, web, enabled=False)
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "m.log")), clock=CLOCK)
    a.atlas = Atlas(eg, None, tmp_path / "state")
    r = a.turn(DialogState("n"), "google Zorblax Tower")
    assert r.via == "web" and r.kind == "unknown" and "Brave" in r.text, r.text
    # each engine once, in plain words
    assert "(DuckDuckGo: blocked; Bing: blocked; Wikipedia: blocked)" in r.text, r.text


def test_the_fact_box_answers_when_the_engines_fail(corpus, tmp_path, monkeypatch):   # noqa: F811
    """Every engine refuses, DuckDuckGo's Instant Answer API knows the tower: its fact box answers,
    with its source; only the name went to the API, not the question."""
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    web = FakeWeb(bing="captcha", ddg="anomaly", lite="anomaly", facts={"Zorblax Tower": ZORBLAX_FACTS})
    eg = _egress(tmp_path, web, enabled=False)
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "m.log")), clock=CLOCK)
    a.atlas = Atlas(eg, None, tmp_path / "state")
    r = a.turn(DialogState("f"), "google who was the architect of the Zorblax Tower")
    assert r.via == "web" and r.text.startswith("Mirela Tosk was the architect of the Zorblax Tower."), r.text
    assert r.links == [] and r.source["key"] == "https://en.wikipedia.org/wiki/Zorblax_Tower"
    api = [q for q in web.seen if q.what == "facts:duckduckgo"]
    assert len(api) == 1 and urllib.parse.parse_qs(urllib.parse.urlsplit(api[0].url).query)["q"] == ["Zorblax Tower"]


def test_errors_never_carry_the_question(tmp_path):
    """A transport error names the URL, and a search URL holds the question: the log and the reply
    keep only the host."""
    class Failing(FakeWeb):
        def fetch(self, req, settings):
            check(req, settings)
            return Fetched(False, 0, error=f"{req.url}: Network Error: timed out reading response")

    e = _egress(tmp_path, Failing())
    found = WebSearch(e).search("Who is the secret Zorblax heir?", "en", explicit=True)
    assert not found.ok and ("bing", "timed out") in found.tried
    log = json.dumps(e.log.tail(50))
    assert "Zorblax" not in log and "heir" not in log and "www.bing.com" in log


def test_the_sentence_that_answers_wins():
    """Rules of the sentence choice on made-up pages: the sentence that names the thing asked about
    and a number other sites agree on beats one about something else on the same page; a list
    entry is no sentence; an opening-hours question needs times of day."""
    from engramm.web.search import Result, answers
    results = [Result("Zorblax Tower - Wiki", "https://wiki.quorvia.example/zt", "", "wiki.quorvia.example", "bing", 0),
               Result("Zorblax Tower facts", "https://facts.example/zt",
                      "At 318 metres, the Zorblax Tower is the tallest structure of Quorvia.", "facts.example", "bing", 1)]
    pages = [{"t": "Zorblax Tower - Wiki", "url": "https://wiki.quorvia.example/zt", "host": "wiki.quorvia.example", "rank": 0,
              "x": "The new antenna on the roof has a height of 4.88 metres and was added in 2001.\n"
                   "1 2 “Zorblax Tower – height and facts”.\n"
                   "The Zorblax Tower is 318 metres high and stands on the bank of the Velm."}]
    best = WebSearch.best("How tall is the Zorblax Tower?", results, pages)
    assert "318 metres" in best[0][1] and "Zorblax Tower" in best[0][1], best
    assert all("1 2" not in b[1] for b in best)
    assert answers("What are the opening hours of the museum?", "The museum is open daily from 9 a.m. to 6 p.m.")
    assert not answers("What are the opening hours of the museum?", "The museum is free after 6 p.m. on Fridays.")
    assert not answers("How tall is the tower?", "The tower is very tall and famous.")
    assert answers("Who designed the tower?", "It was designed by Mirela Tosk.")


def test_web_search_is_on_from_the_start(corpus, tmp_path, monkeypatch):   # noqa: F811
    """A new installation (no network.json): a question ENGRAMM cannot answer offline goes to the web
    by itself, with sources; a personal one does not; the shelf and the feeds stay off."""
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    web = FakeWeb(bing="good")
    eg = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"), backend=web)
    assert eg.enabled("search") and not eg.enabled("shelf") and not eg.enabled("feeds")
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "m.log")), clock=CLOCK)
    a.atlas = Atlas(eg, None, tmp_path / "state")
    st = DialogState("new")
    r = a.turn(st, "How tall is the Zorblax Tower?")
    assert r.via == "web" and "318 metres" in r.text and r.source["key"] == TOWER, r.text
    assert "Should I search" not in r.text and "Tip:" not in r.text
    n = len(web.seen)
    a.turn(st, "What is my favourite tower?")
    assert len(web.seen) == n


# -- the short answer ------------------------------------------------------------------------------

def _rows(*items: tuple[float, str, str]) -> list[tuple[float, str, dict]]:
    """(score, sentence, host) → WebSearch.best's rows."""
    return [(sc, sent, {"t": host, "x": sent, "url": f"https://{host}/{i}", "host": host, "rank": i})
            for i, (sc, sent, host) in enumerate(items)]


def test_answer_types():
    from engramm.web.search import answer_type
    assert answer_type("Who is currently the president of the usa?") == "person"
    assert answer_type("Wer ist der aktuelle Bundeskanzler?") == "person"
    assert answer_type("What is the capital of Australia?") == "place"
    assert answer_type("How tall is the Zugspitze?") == "quantity"
    assert answer_type("How many people live in Berlin?") == "count"
    assert answer_type("When was Siemens founded?") == "date"
    assert answer_type("What is the bitcoin price?") == "money"
    assert answer_type("Wie sind die Öffnungszeiten vom Louvre?") == "hours"
    assert answer_type("Why is the sky blue?") is None


def test_the_answer_the_sources_agree_on():
    """The president question of the user's report: the pages hold the answer in several sentences
    of several sites, between sentences about past presidents; the one about today wins, and the
    sentence shown for it is the one that says "current"."""
    from engramm.web.search import short_answer
    q = "Who is currently the president of the usa?"
    rows = _rows((5.0, "The President is to be commander-in-chief of the army and navy of the United States.", "en.wikipedia.org"),
                 (4.6, "James Monroe was the fifth president of the United States, serving from 1817 to 1825.", "en.wikipedia.org"),
                 (4.4, "Donald Trump is the 47th and current president since January 20, 2025.", "en.wikipedia.org"),
                 (4.2, "The incumbent president is Donald Trump, who assumed office on January 20, 2025.", "britannica.com"),
                 (4.0, "Under President Donald Trump’s second administration, the economy grew.", "whitehouse.gov"),
                 (3.9, "Herbert Hoover was the 31st president of the United States, serving from 1929 to 1933.", "history.example"))
    a = short_answer(q, rows)
    assert a is not None and a.text == "Donald Trump" and a.kind == "person" and a.sites == 3, a
    assert "current" in a.sentence or "incumbent" in a.sentence
    # one sentence alone, or two names as strong as each other: no short answer
    assert short_answer(q, rows[:3]) is None
    assert short_answer("Who founded the Zorblax company?",
                        _rows((5.0, "Mirela Tosk founded the Zorblax company with Ivo Brandt.", "a.example"),
                              (4.9, "Ivo Brandt and Mirela Tosk founded Zorblax in 1931.", "b.example"))) is None


def test_no_answer_from_the_wrong_kind_of_name():
    """Traps met in the live test: a competition for its winner, part of the asked name, a common
    word written with a capital ("Territory" of "Australian Capital Territory")."""
    from engramm.web.search import short_answer
    cup = _rows((5.0, "22 clubs have won the UEFA Champions League / European Cup.", "uefa.example"),
                (4.8, "See also the UEFA Europa League, another annual competition.", "sports.example"),
                (4.5, "The European Cup was renamed in 1992.", "sports.example"))
    a = short_answer("Who won the last Champions League?", cup)
    assert a is None, a
    cap = _rows((5.0, "Canberra is the capital of Australia.", "a.example"),
                (4.9, "The capital lies in the Australian Capital Territory, a federal territory.", "b.example"),
                (4.8, "Canberra became the capital of Australia in 1913.", "c.example"))
    a = short_answer("What is the capital of Australia?", cap)
    assert a is not None and a.text == "Canberra", a


def test_numbers_dates_and_hours():
    from engramm.web.search import short_answer
    rhine = _rows((5.0, "The Rhine is 1,232 kilometres (766 mi) long.", "a.example"),
                  (4.0, "The Rhine River stretches for 1,232 km and drains six countries.", "b.example"),
                  (3.0, "The Upper Rhine Plain is about 300 km long.", "c.example"))
    a = short_answer("How long is the Rhine?", rhine)
    assert a is not None and a.text in ("1,232 kilometres", "1,232 km"), a
    founded = _rows((5.0, "Siemens – Founded: October 01, 1847, Berlin.", "en.wikipedia.org"),
                    (4.0, "Siemens & Halske was founded on 1 October 1847.", "b.example"),
                    (3.5, "Siemens was founded in 1847 by Werner von Siemens.", "c.example"))
    a = short_answer("When was Siemens founded?", founded)
    assert a is not None and "1847" in a.text and " 01," not in a.text, a
    hours = _rows((5.0, "Das Louvre hat jeden Tag außer Dienstag von 9 Uhr bis 18 Uhr geöffnet.", "a.example"))
    a = short_answer("Wie sind die Öffnungszeiten vom Louvre?", hours, "de")
    assert a is not None and a.text == "9 Uhr bis 18 Uhr", a


def test_the_answer_as_a_sentence():
    from engramm.chat.dialog import _spelled_as_seen, _web_head
    from engramm.web.search import Answer
    def ans(text, kind, sentence="x"):
        return Answer(text, kind, sentence, {"host": "a.example"}, 3, 2)
    assert _web_head("Who is currently the president of the usa?", ans("Donald Trump", "person"), "en", []) \
        == "Donald Trump is currently the president of the USA."
    assert _web_head("Wer ist der aktuelle Bundeskanzler?", ans("Friedrich Merz", "person"), "de", []) \
        == "Der aktuelle Bundeskanzler ist Friedrich Merz."
    assert _web_head("Wie hoch ist die Zugspitze?", ans("2962 m", "quantity"), "de", []) == "Die Zugspitze ist 2962 m hoch."
    # a count from the web is rounded and dated
    head = _web_head("How many people live in Berlin?",
                     ans("3,520,031", "count", "On 31 December 2015, Berlin had a population of 3,520,031."), "en", [])
    assert head == "About 3.5 million people live in Berlin (as of 2015).", head
    assert _web_head("When does the Louvre open?", ans("9 a.m. to 6 p.m.", "hours"), "en", []) is None
    # the question's misspelling is written as the pages write the name
    assert _spelled_as_seen("Sam Altman is current CEO of Chatbt.", "Who is current CEO of Chatbt?",
                            ["Who Owns ChatGPT? Largest Shareholders"]) == "Sam Altman is current CEO of ChatGPT."


def test_who_won_without_a_year_is_no_vote():
    """The winner most pages name is history's most frequent one, not the last one."""
    from engramm.web.search import short_answer
    rows = _rows((5.0, "Real Madrid have won the Champions League a record 15 times.", "a.example"),
                 (4.8, "Real Madrid beat Borussia Dortmund in the 2024 final.", "b.example"),
                 (4.6, "The last winners are Paris Saint-Germain (2026) and Real Madrid (2024).", "c.example"),
                 (4.4, "Real Madrid also won in 2022.", "d.example"))
    assert short_answer("Who won the last Champions League?", rows) is None
    a = short_answer("Who won the Champions League in 2024?", rows)
    assert a is not None and a.text == "Real Madrid", a
