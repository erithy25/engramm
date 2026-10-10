"""The web search (engramm/web/search.py) and its place in the dialog (engramm/chat/dialog.py):
result pages of Bing, DuckDuckGo (HTML and lite), the Brave Search API and Wikipedia's search are
read correctly (click links decoded, ads left out); a bot check or results that do not match the
question send the search on to the next engine; "google …" / "such im Internet nach …" are
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
from engramm.web.search import (WebSearch, content_words, parse_bing, parse_brave, parse_ddg, parse_ddg_lite,
                                parse_wikipedia, query_forms, relevant, search_request)
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


class FakeWeb:
    """The search engines and pages of this test: the egress rules first (as the real backends),
    then an answer by host. ``bing`` / ``ddg`` choose what those engines do."""
    name = "fake"

    def __init__(self, bing="good", ddg="good", lite="good"):
        self.bing, self.ddg, self.lite = bing, ddg, lite
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
            if self.ddg == "anomaly":
                return Fetched(False, 202, b'<div class="anomaly-modal">', error="HTTP 202", final_host=host)
            return Fetched(True, 200, ddg_page(GOOD).encode(), final_host=host, content_type=html_)
        if host == "lite.duckduckgo.com":
            if self.lite == "anomaly":
                return Fetched(False, 202, b"", error="HTTP 202", final_host=host)
            return Fetched(True, 200, ddg_lite_page(GOOD).encode(), final_host=host, content_type=html_)
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


def test_relevance_and_query_forms():
    good, junk = parse_bing(bing_page(GOOD)), parse_bing(bing_page(JUNK))
    assert relevant("How tall is the Zorblax Tower?", good)
    assert not relevant("How tall is the Zorblax Tower?", junk)              # "tall" alone: a dictionary
    assert not relevant("Wie hoch ist der Zorblax Tower?", junk, "de")
    assert query_forms("How tall is the Zugspitze?") == ["How tall is the Zugspitze", "zugspitze tall"]
    assert content_words("Wie hoch ist die Zugspitze?") == "hoch zugspitze"


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
    web = FakeWeb(bing="junk", ddg="anomaly")
    e = _egress(tmp_path, web)
    ws = WebSearch(e)
    with pytest.raises(EgressError, match="switched off"):                  # not asked for, channel off: nothing sent
        ws.search("How tall is the Zorblax Tower?", "en")
    assert web.seen == []
    found = ws.search("How tall is the Zorblax Tower?", "en", explicit=True)
    # Bing answered twice with unrelated pages (the question, then keywords), DuckDuckGo with a bot check
    assert found.engine == "duckduckgo-lite" and found.results[0].url == TOWER, found
    assert [t[0] for t in found.tried] == ["bing", "bing", "duckduckgo"]
    assert "did not match" in found.tried[0][1] and "refused" in found.tried[2][1]
    assert [r.what for r in web.seen] == ["search:bing", "search:bing", "search:duckduckgo", "search:duckduckgo-lite"]
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
    eg = _egress(tmp_path, web)
    atlas = Atlas(eg, None, tmp_path / "state")
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "chat_memory.log")), clock=CLOCK)
    a.atlas = atlas
    return a, eg, web


def test_google_command_searches_even_with_the_channel_off(web_chat):
    a, eg, web = web_chat
    st = DialogState("g")
    r = a.turn(st, "google how tall is the Zorblax Tower")
    assert r.via == "web" and r.kind in ("answer", "about"), r.text
    assert "318 metres" in r.text and "quorvia.example" in r.text and "Bing" in r.text, r.text
    assert r.source["kind"] == "web" and r.source["key"] == TOWER
    assert [x["url"] for x in r.links][:3] == [u for _, u, _ in GOOD][:3]
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
    assert any("Zorblax" in urllib.parse.unquote(q.url) for q in web.seen if q.what.startswith("search:"))


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
    assert r.via == "web" and r.text.startswith("Laut ") and "Gesucht mit Bing" in r.text, r.text
    req = next(q for q in web.seen if q.what == "search:bing")
    assert "setlang=de" in req.url and dict(req.headers)["Accept-Language"].startswith("de")
    r = a.turn(DialogState("de2"), "googel mal")
    assert "wonach soll ich suchen" in r.text, r.text


def test_nothing_found_is_said_plainly(corpus, tmp_path, monkeypatch):   # noqa: F811
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    web = FakeWeb(bing="captcha", ddg="anomaly", lite="anomaly")
    eg = _egress(tmp_path, web)
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "m.log")), clock=CLOCK)
    a.atlas = Atlas(eg, None, tmp_path / "state")
    r = a.turn(DialogState("n"), "google Zorblax Tower")
    assert r.via == "web" and r.kind == "unknown" and "Bing: refused" in r.text and "Brave" in r.text, r.text


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
