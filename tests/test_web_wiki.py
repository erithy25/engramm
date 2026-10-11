"""Answers from Wikidata and Wikipedia (engramm/web/wiki.py) and their place in the web search of the
dialog: a question is read into a relation and the thing it asks about, the thing is found by its
name, the statement that holds today is chosen (an ended one is not: Biden for the president of
2026), dates, quantities and names are written in the conversation's language, "what is X" gets
the first sentences of X's article, and the answer comes even when every search engine blocks.
Only the name of the thing goes to Wikidata, after a "too many requests" Wikimedia is left alone
for a while, and the reply has one source and no list of links.

No real network: a test double plays Wikidata's and Wikipedia's APIs in their JSON format."""

from __future__ import annotations

import datetime as dt
import json
import urllib.parse

import pytest

from engramm.chat.dialog import Assistant, DialogState
from engramm.chat.textmem import LoggedTextMemory
from engramm.web.atlas import Atlas
from engramm.web.egress import Egress, Fetched, NetworkLog, check
from engramm.web.feeds import FeedRefresher
from engramm.web.wiki import (WikiKnowledge, choose, defined, format_date, format_number, format_quantity, parse)
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)
from tests.test_web_search import CLOCK, FakeWeb

ITEM = "wikibase-entityid"


def _time(t: str, precision: int = 11) -> dict:
    return {"value": {"time": t, "timezone": 0, "before": 0, "after": 0, "precision": precision,
                      "calendarmodel": "http://www.wikidata.org/entity/Q1985727"}, "type": "time"}


def _item(qid: str) -> dict:
    return {"value": {"entity-type": "item", "numeric-id": int(qid[1:]), "id": qid}, "type": ITEM}


def _qty(amount: str, unit: str = "1") -> dict:
    u = unit if unit == "1" else f"http://www.wikidata.org/entity/{unit}"
    return {"value": {"amount": amount, "unit": u}, "type": "quantity"}


def _st(prop: str, value: dict, rank: str = "normal", **quals: dict) -> dict:
    """A statement as wbgetclaims gives it, with qualifiers (P580 start, P582 end, P585 point in time)."""
    out = {"mainsnak": {"snaktype": "value", "property": prop, "datavalue": value}, "type": "statement",
           "id": f"Q$x-{prop}", "rank": rank, "references": []}
    if quals:
        out["qualifiers"] = {p: [{"snaktype": "value", "property": p, "datavalue": v}] for p, v in quals.items()}
    return out


def _hit(qid: str, label: str, description: str, match: str | None = None) -> dict:
    return {"id": qid, "title": qid, "concepturi": f"http://www.wikidata.org/entity/{qid}", "label": label,
            "description": description, "match": {"type": "alias" if match else "label", "language": "en",
                                                  "text": match or label}}


SEARCH = {
    "real madrid": [_hit("Q8682", "Real Madrid CF", "association football club in Madrid, Spain", "Real Madrid")],
    "United States": [_hit("Q30", "United States of America", "country in North America", "United States")],
    "Deutschland": [_hit("Q183", "Deutschland", "Staat in Mitteleuropa")],
    "Berlin": [_hit("Q64", "Berlin", "capital and largest city of Germany")],
    "Zugspitze": [_hit("Q3375", "Zugspitze", "höchster Berg Deutschlands")],
    "Faust": [_hit("Q1352553", "Faust", "German legend"), _hit("Q3227", "Faust", "tragic play by Goethe")],
    "Donald Trump": [_hit("Q22686", "Donald Trump", "president of the United States since 2025")],
    "Elon Musk": [_hit("Q317521", "Elon Musk", "businessman (born 1971)")],
    "Stephen King": [_hit("Q39829", "Stephen King", "American author (born 1947)")],
    "Siemens": [_hit("Q81230", "Siemens", "German multinational conglomerate"),
                _hit("Q4523", "Siemens", "Wikimedia disambiguation page")],
}
CLAIMS = {
    ("Q8682", "P571"): [_st("P571", _time("+1902-03-06T00:00:00Z"))],
    ("Q30", "P35"): [_st("P35", _item("Q6279"), P580=_time("+2021-01-20T00:00:00Z"), P582=_time("+2025-01-20T00:00:00Z")),
                     _st("P35", _item("Q22686"), "preferred", P580=_time("+2025-01-20T00:00:00Z")),
                     _st("P35", _item("Q76"), "deprecated")],
    ("Q183", "P6"): [_st("P6", _item("Q567"), P580=_time("+2005-11-22T00:00:00Z"), P582=_time("+2021-12-08T00:00:00Z")),
                     _st("P6", _item("Q61053"), P580=_time("+2021-12-08T00:00:00Z"), P582=_time("+2025-05-06T00:00:00Z")),
                     _st("P6", _item("Q1173"), P580=_time("+2025-05-06T00:00:00Z"))],
    ("Q64", "P1082"): [_st("P1082", _qty("+3644826"), P585=_time("+2018-12-31T00:00:00Z")),
                       _st("P1082", _qty("+3913644"), P585=_time("+2024-12-31T00:00:00Z")),
                       _st("P1082", _qty("+3878100"), P585=_time("+2023-12-31T00:00:00Z"))],
    ("Q3375", "P2044"): [_st("P2044", _qty("+2962", "Q11573"))],
    ("Q3227", "P50"): [_st("P50", _item("Q5879"))],
    ("Q22686", "P569"): [_st("P569", _time("+1946-06-14T00:00:00Z"))],
}
LABELS = {
    "Q8682": ("Real Madrid CF", "Real Madrid", "Real_Madrid_CF", "Real_Madrid"),
    "Q30": ("United States of America", "Vereinigte Staaten", "United_States", "Vereinigte_Staaten"),
    "Q22686": ("Donald Trump", "Donald Trump", "Donald_Trump", "Donald_Trump"),
    "Q6279": ("Joe Biden", "Joe Biden", "Joe_Biden", "Joe_Biden"),
    "Q183": ("Germany", "Deutschland", "Germany", "Deutschland"),
    "Q1173": ("Friedrich Merz", "Friedrich Merz", "Friedrich_Merz", "Friedrich_Merz"),
    "Q61053": ("Olaf Scholz", "Olaf Scholz", "Olaf_Scholz", "Olaf_Scholz"),
    "Q64": ("Berlin", "Berlin", "Berlin", "Berlin"),
    "Q3375": ("Zugspitze", "Zugspitze", "Zugspitze", "Zugspitze"),
    "Q3227": ("Faust", "Faust", "Faust,_Part_One", "Faust._Eine_Tragödie."),
    "Q5879": ("Johann Wolfgang von Goethe", "Johann Wolfgang von Goethe", "Johann_Wolfgang_von_Goethe",
              "Johann_Wolfgang_von_Goethe"),
    "Q317521": ("Elon Musk", "Elon Musk", "Elon_Musk", "Elon_Musk"),
    "Q39829": ("Stephen King", "Stephen King", "Stephen_King", "Stephen_King"),
    "Q81230": ("Siemens", "Siemens", "Siemens", "Siemens"),
}
SUMMARIES = {
    "Elon_Musk": "Elon Reeve Musk (born June 28, 1971) is a businessman known for his leadership of Tesla, SpaceX and X. "
                 "He has been the wealthiest person in the world since 2021. Born in Pretoria, he moved to Canada.",
    "Stephen_King": "Stephen Edwin King (born September 21, 1947) is an American author of horror, supernatural fiction "
                    "and fantasy. Described as the King of Horror, he has written 65 novels.",
}
ARTICLE = ("Real Madrid Club de Fútbol is a Spanish professional football club based in Madrid.\n"
           "Founded in 1902 as Madrid Football Club, it has traditionally worn a white home kit since its inception. "
           "The club has won a record 15 European Cups.\n" * 3)


class FakeWikimedia:
    """Wikidata's Action API and Wikipedia's REST and Action APIs in their JSON format; the egress
    rules first, as the real backends. ``limited``: answer "too many requests" (HTTP 429)."""
    name = "fake"

    def __init__(self, limited: bool = False):
        self.limited = limited
        self.seen: list = []

    def fetch(self, req, settings) -> Fetched:
        check(req, settings)
        self.seen.append(req)
        u = urllib.parse.urlsplit(req.url)
        host, q = u.hostname or "", {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        js = "application/json; charset=utf-8"
        if self.limited:
            return Fetched(False, 429, b"You are making too many requests", error="HTTP 429", final_host=host)

        def ok(obj) -> Fetched:
            return Fetched(True, 200, json.dumps(obj).encode(), final_host=host, content_type=js)
        if host == "www.wikidata.org":
            action = q.get("action")
            if action == "wbsearchentities":
                hits = next((v for k, v in SEARCH.items() if k.lower() == q["search"].lower()), [])   # any case
                return ok({"searchinfo": {"search": q["search"]}, "search": hits, "success": 1})
            if action == "wbgetclaims":
                return ok({"claims": {q["property"]: CLAIMS.get((q["entity"], q["property"]), [])}})
            if action == "wbgetentities":
                ents = {}
                for qid in q["ids"].split("|"):
                    if qid not in LABELS:
                        continue
                    en, de, en_t, de_t = LABELS[qid]
                    ents[qid] = {"type": "item", "id": qid,
                                 "labels": {"en": {"language": "en", "value": en}, "de": {"language": "de", "value": de}},
                                 "descriptions": {},
                                 "sitelinks": {"enwiki": {"site": "enwiki", "title": en_t.replace("_", " ")},
                                               "dewiki": {"site": "dewiki", "title": de_t.replace("_", " ")}}}
                return ok({"entities": ents, "success": 1})
        if host.endswith("wikipedia.org"):
            if u.path.startswith("/api/rest_v1/page/summary/"):
                title = urllib.parse.unquote(u.path.rsplit("/", 1)[1])
                if title not in SUMMARIES:
                    return Fetched(False, 404, b"", error="HTTP 404", final_host=host)
                return ok({"type": "standard", "title": title.replace("_", " "), "extract": SUMMARIES[title],
                           "content_urls": {"desktop": {"page": f"https://{host}/wiki/{title}"}}})
            if q.get("list") == "search":
                hits = [{"ns": 0, "title": "Real Madrid CF"}] if "madrid" in q.get("srsearch", "") else []
                return ok({"query": {"search": hits}})
            if q.get("prop") == "extracts":
                if q.get("titles") != "Real Madrid CF":
                    return ok({"query": {"pages": {"-1": {"title": q.get("titles"), "missing": ""}}}})
                return ok({"query": {"pages": {"8682": {"pageid": 8682, "title": "Real Madrid CF", "extract": ARTICLE}}}})
        return Fetched(False, 404, b"", error="HTTP 404", final_host=host)


class _Both:
    """The search engines of tests/test_web_search.py and Wikimedia, by host."""
    name = "fake"

    def __init__(self, web: FakeWeb, wiki: FakeWikimedia):
        self.web, self.wiki = web, wiki

    def fetch(self, req, settings):
        host = urllib.parse.urlsplit(req.url).hostname or ""
        if host == "www.wikidata.org" or host.endswith("wikipedia.org"):
            return self.wiki.fetch(req, settings)
        return self.web.fetch(req, settings)


def _wk(tmp_path, wiki: FakeWikimedia, **search) -> tuple[WikiKnowledge, Egress]:
    e = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"), backend=wiki)
    if search:
        e.set_channel("search", **search)
    return WikiKnowledge(e), e


# -- reading the question ----------------------------------------------------------------------------

@pytest.mark.parametrize("question,lang,rel,subject", [
    ("When was real madrid founded?", "en", "inception", "real madrid"),
    ("Who is currently the president of the usa?", "en", "head_state", "United States"),
    ("Who is the CEO of Siemens?", "en", "ceo", "Siemens"),
    ("Wer ist der aktuelle Bundeskanzler?", "de", "head_gov", "Deutschland"),
    ("Who is the German chancellor?", "en", "head_gov", "Germany"),
    ("What's the capital of Australia?", "en", "capital", "Australia"),
    ("Wie hoch ist die Zugspitze?", "de", "elevation", "Zugspitze"),
    ("How many people live in Berlin?", "en", "population", "Berlin"),
    ("Wie viele Einwohner hat Berlin?", "de", "population", "Berlin"),
    ("Who wrote Faust?", "en", "author", "Faust"),
    ("Wer ist der Trainer von Bayern München?", "de", "coach", "Bayern München"),
    ("Where was Albert Einstein born?", "en", "birthplace", "Albert Einstein"),
    ("Who founded Microsoft?", "en", "founder", "Microsoft"),
    ("How old is Donald Trump?", "en", "age", "Donald Trump"),
    ("When did the Berlin Wall fall?", "en", "dissolved", "Berlin Wall"),
    ("When did Michael Jackson die?", "en", "death", "Michael Jackson"),
    ("Which team does Messi play for?", "en", "team", "Messi"),
    ("Wo liegt die Zugspitze?", "de", "located", "Zugspitze"),
    ("Wann wurde Real Madrid gegründet?", "de", "inception", "Real Madrid"),
    ("Who is Stephen King?", "en", None, "Stephen King"),                 # a name, not the king of Stephen
    ("What is photosynthesis?", "en", None, "photosynthesis"),
    ("Was ist ein Schwarzes Loch?", "de", None, "Schwarzes Loch"),
])
def test_questions_are_read(question, lang, rel, subject):
    asked = parse(question, lang)
    assert asked is not None and (asked.rel.key if asked.rel else None) == rel and asked.subject == subject, asked


@pytest.mark.parametrize("question", ["Why is the sky blue?", "What is the bitcoin price?", "What is the weather in Berlin?",
                                      "Who won the last Champions League?", "How do I cook rice?", "What is my name?"])
def test_questions_no_entry_answers(question):
    assert parse(question, "en") is None


def test_values_are_written_in_the_conversations_language():
    assert format_date(_time("+1902-03-06T00:00:00Z")["value"], "en") == ("6 March 1902", "on 6 March 1902")
    assert format_date(_time("+1902-03-06T00:00:00Z")["value"], "de") == ("6. März 1902", "am 6. März 1902")
    assert format_date(_time("+1847-00-00T00:00:00Z", 9)["value"], "en") == ("1847", "in 1847")
    assert format_date(_time("+1990-10-00T00:00:00Z", 10)["value"], "de") == ("Oktober 1990", "im Oktober 1990")
    assert format_date(_time("-0044-03-15T00:00:00Z")["value"], "en")[0] == "15 March 44 BC"
    assert format_number(3913644, "en") == "3,913,644" and format_number(3913644, "de") == "3.913.644"
    assert format_number(1232.5, "de") == "1.232,5"
    assert format_quantity(_qty("+2962", "Q11573")["value"], "en") == "2,962 m"
    assert format_quantity(_qty("+2962", "Q11573")["value"], "de") == "2.962 m"
    assert format_quantity(_qty("+27360000000000", "Q4917")["value"], "en") == "US$27.36 trillion"
    assert format_quantity(_qty("+27360000000000", "Q4917")["value"], "de") == "27,36 Billionen US-Dollar"
    assert format_quantity(_qty("+12", "Q99999")["value"], "en", {"Q99999": "parsec"}) == "12 parsec"
    assert format_quantity(_qty("+2962.06", "Q11573")["value"], "en") == "2,962 m"     # as Wikidata has it
    assert format_quantity(_qty("+1.81", "Q11573")["value"], "de") == "1,81 m"


def test_the_statement_that_holds_today():
    us = CLAIMS[("Q30", "P35")]
    assert [s["mainsnak"]["datavalue"]["value"]["id"] for s in choose(us, now=True, many=False)] == ["Q22686"]
    germany = CLAIMS[("Q183", "P6")]                      # no preferred rank: the one that has not ended
    assert choose(germany, now=True, many=False)[0]["mainsnak"]["datavalue"]["value"]["id"] == "Q1173"
    # before Merz took office the same statements answer Scholz
    assert choose(germany, now=True, many=False, today=dt.date(2024, 1, 1))[0]["mainsnak"]["datavalue"]["value"]["id"] \
        == "Q61053"
    berlin = CLAIMS[("Q64", "P1082")]                     # the newest count
    assert choose(berlin, now=True, many=False)[0]["mainsnak"]["datavalue"]["value"]["amount"] == "+3913644"
    assert choose([_st("P35", _item("Q1"), "deprecated")], now=False, many=False) == []


# -- answers -------------------------------------------------------------------------------------------

def test_answers_from_wikidata(tmp_path):
    wiki = FakeWikimedia()
    wk, e = _wk(tmp_path, wiki)
    f = wk.answer("When was real madrid founded?", "en", explicit=True)
    assert f.text == "Real Madrid was founded on 6 March 1902.", f
    assert f.answer == "6 March 1902" and f.url == "https://en.wikipedia.org/wiki/Real_Madrid_CF"
    assert f.evidence == "Real Madrid CF – inception: 6 March 1902"
    # only the thing's name went to Wikidata, not the question
    searched = [urllib.parse.parse_qs(urllib.parse.urlsplit(r.url).query) for r in wiki.seen if "wbsearchentities" in r.url]
    assert searched and all(s["search"] == ["real madrid"] for s in searched)
    assert all(r.plain_agent for r in wiki.seen)              # Wikimedia gets ENGRAMM's own name and contact

    f = wk.answer("Who is currently the president of the usa?", "en", explicit=True)
    assert f.text == "Donald Trump is currently the president of the USA." and f.person, f
    f = wk.answer("Wer ist der aktuelle Bundeskanzler?", "de", explicit=True)
    assert f.text == "Der aktuelle Bundeskanzler ist Friedrich Merz." and f.url.startswith("https://de.wikipedia.org/"), f
    f = wk.answer("How many people live in Berlin?", "en", explicit=True)
    assert f.text == "Berlin has a population of 3,913,644 (as of 2024).", f
    f = wk.answer("Wie hoch ist die Zugspitze?", "de", explicit=True)
    assert f.text == "Die Zugspitze ist 2.962 m hoch.", f
    f = wk.answer("Who wrote Faust?", "en", explicit=True)        # the legend has no author, the play has
    assert f.text == "Johann Wolfgang von Goethe wrote Faust.", f
    born = dt.date(1946, 6, 14)
    today = dt.date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    f = wk.answer("How old is Donald Trump?", "en", explicit=True)
    assert f.text == f"Donald Trump is {age} years old (born on 14 June 1946).", f


def test_what_a_thing_is_from_wikipedia(tmp_path):
    wk, e = _wk(tmp_path, FakeWikimedia())
    f = wk.answer("Who is Elon Musk?", "en", explicit=True)
    assert f.kind == "summary" and f.url == "https://en.wikipedia.org/wiki/Elon_Musk"
    assert f.text.startswith("Elon Reeve Musk (born June 28, 1971) is a businessman") and "Pretoria" not in f.text, f
    f = wk.answer("Who is Stephen King?", "en", explicit=True)
    assert f.kind == "summary" and "American author" in f.text, f
    assert wk.answer("Who is Zorblax Quux?", "en", explicit=True) is None      # no entry of that name
    assert defined("What does photosynthesis mean?") == "photosynthesis" and defined("Why is the sky blue?") is None


def test_the_article_that_matches_the_question(tmp_path):
    wk, e = _wk(tmp_path, FakeWikimedia())
    pages = wk.article("When was real madrid founded?", "en", explicit=True)
    assert len(pages) == 1 and pages[0]["url"] == "https://en.wikipedia.org/wiki/Real_Madrid_CF"
    assert "Founded in 1902" in pages[0]["x"] and pages[0]["host"] == "en.wikipedia.org"
    assert wk.article("Why is the sky blue?", "en", explicit=True) == []


def test_wikimedia_is_left_alone_after_too_many_requests(tmp_path):
    wiki = FakeWikimedia(limited=True)
    wk, e = _wk(tmp_path, wiki)
    assert wk.answer("When was real madrid founded?", "en", explicit=True) is None
    n = len(wiki.seen)
    assert n == 1                                            # the first 429 ends the lookup
    wiki.limited = False
    assert wk.answer("When was real madrid founded?", "en", explicit=True) is None and len(wiki.seen) == n


def test_nothing_goes_out_with_the_channel_off(tmp_path):
    wiki = FakeWikimedia()
    wk, e = _wk(tmp_path, wiki, enabled=False)
    assert wk.answer("When was real madrid founded?", "en", explicit=False) is None
    assert wk.article("When was real madrid founded?", "en", explicit=False) == []
    assert wiki.seen == []


# -- in the dialog -------------------------------------------------------------------------------------

@pytest.fixture()
def chat(corpus, tmp_path, monkeypatch):   # noqa: F811
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    monkeypatch.setattr(FeedRefresher, "refresh_now", lambda self: {})
    web, wiki = FakeWeb(), FakeWikimedia()
    eg = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"), backend=_Both(web, wiki))
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "chat_memory.log")), clock=CLOCK)
    a.atlas = Atlas(eg, None, tmp_path / "state")
    return a, eg, web, wiki


def test_the_answer_comes_even_when_every_search_engine_blocks(chat):
    """The user's report: "When was real madrid founded?" found nothing (DuckDuckGo blocked, Bing
    answered for "real"). Wikidata answers; the reply is the answer with one source, no list."""
    a, eg, web, wiki = chat
    web.bing, web.ddg, web.lite = "captcha", "anomaly", "anomaly"
    stages = []
    a.progress = lambda conversation, info: stages.append((conversation, info["stage"]))
    r = a.turn(DialogState("rm"), "google when was real madrid founded")
    assert r.via == "web" and r.kind == "answer" and r.text.startswith("Real Madrid was founded on 6 March 1902."), r.text
    assert r.answer == "6 March 1902" and r.links == []
    assert r.source["key"] == "https://en.wikipedia.org/wiki/Real_Madrid_CF" and r.source["source"] == "en.wikipedia.org"
    assert "No page I read" not in r.text and "results are below" not in r.text and "Searched with" not in r.text
    assert stages and stages[0] == ("rm", "search") and stages[-1] == ("rm", "write")


def test_the_page_says_what_the_search_does_and_a_person_answer_is_the_next_he(chat):
    a, eg, web, wiki = chat
    eg.set_channel("search", enabled=True)
    stages = []
    a.progress = lambda conversation, info: stages.append(dict(info))
    r = a.turn(DialogState("t"), "How tall is the Zorblax Tower?")             # the engines find it, pages are read
    assert r.kind == "answer" and "318 metres" in r.text, r.text
    assert [s["stage"] for s in stages] == ["search", "read", "write"], stages
    assert "Zorblax" in stages[0]["query"] and stages[1]["sites"][0] == "quorvia.example"
    st = DialogState("p")
    r = a.turn(st, "Who is currently the president of the usa?")
    assert r.kind == "answer" and r.text.startswith("Donald Trump is currently the president of the USA."), r.text
    assert a.bot.context.get("answer") == "Donald Trump" and a.bot.context.get("atype") == "PERSON"


def test_what_is_x_gets_wikipedias_first_sentences(chat):
    a, eg, web, wiki = chat
    r = a.turn(DialogState("w"), "google who is elon musk")
    assert r.via == "web" and r.text.startswith("Elon Reeve Musk (born June 28, 1971) is a businessman"), r.text
    assert r.source["key"] == "https://en.wikipedia.org/wiki/Elon_Musk" and r.links == []
