"""Atlas in the dialog (engramm/web/atlas.py, engramm/chat/dialog.py): with every channel off the
answers are exactly those without Atlas; with the shelf on, a question the local reading cannot
answer is answered from a full article fetched from a (local) shelf, with source and date; news
come from the feed index; nothing sent ever contains the question."""

from __future__ import annotations

import datetime as dt
import json
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer

import pytest

from engramm.chat.dialog import Assistant, DialogState
from engramm.chat.textmem import LoggedTextMemory
from engramm.web.atlas import Atlas, is_fresh, news_request
from engramm.web.egress import Egress, NetworkLog, PythonBackend
from engramm.web.feeds import FeedRefresher, Item
from experiments.shelf_build import build
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)
from tests.test_web_shelf import _Range, _docs

CLOCK = lambda: dt.datetime(2026, 10, 1, 18, 30)          # noqa: E731

PERSON = {"t": "Vorna Kell (musician)", "s": "test", "d": "2026-09-21",
          "x": "Vorna \"Vee\" Kell (March 3, 1911 – May 9, 1980) was a Quorvian singer and violinist. "
               "Kell grew up in Velmar and played in local bands. In 1959 she was touring the coast when a radio "
               "host recorded her songs. Kell retired to Ostrin and taught music there."}
ARTICLE = {"t": "Zorblax Bridge", "s": "test", "d": "2026-09-20",
           "x": "The Zorblax Bridge is a suspension bridge over the Velm river in Quorvia. It was opened in 1931 "
                "after six years of construction. The bridge was designed by the engineer Mirela Tosk. Its main "
                "span is 412 metres long."}


@pytest.fixture(scope="module")
def shelf_pack(tmp_path_factory):
    root = tmp_path_factory.mktemp("atlas")
    src = root / "docs.jsonl"
    src.write_text("\n".join(json.dumps(d) for d in _docs(200) + [ARTICLE, PERSON]), encoding="utf-8")
    out = root / "pack"
    build([src], [], out, bucket_kb=64, sample=1000, key_terms=8, workers=2)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Range, directory=str(out)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    (out / "shelf_source.json").write_text(json.dumps({"base_url": url, "hosts": ["127.0.0.1"], "date": "2026-09-27",
                                                       "allow_loopback": True}))
    yield out
    srv.shutdown()


@pytest.fixture()
def atlas_chat(corpus, shelf_pack, tmp_path, monkeypatch):   # noqa: F811
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    monkeypatch.setattr(FeedRefresher, "refresh_now", lambda self: {})
    eg = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"),
                backend=PythonBackend())
    atlas = Atlas(eg, shelf_pack, tmp_path / "state")
    bot = _bot(corpus, LoggedTextMemory(tmp_path / "chat_memory.log"))
    a = Assistant(bot, clock=CLOCK)
    a.atlas = atlas
    return a, atlas, eg


def _ask(a, st, msg):
    return a.turn(st, msg)


QUESTIONS = ["hi", "When was the Zorblax Bridge opened?", "what's the latest news?", "Who designed it?",
             "How tall is the Eiffel Tower?", "tell me about the Zorblax Bridge", "thanks"]


def test_helpers():
    assert is_fresh("Who is the current CEO of Siemens?") and is_fresh("Who won the election in 2026?")
    assert not is_fresh("When was Siemens founded?")
    assert news_request("what's the latest news?") == (True, None)
    assert news_request("any news about Germany?") == (True, "Germany")
    assert news_request("what is going on in France today?") == (True, "France")
    assert news_request("When was the bridge opened?") == (False, None)


def test_channels_off_answers_are_identical(corpus, atlas_chat, tmp_path):   # noqa: F811
    a, atlas, eg = atlas_chat
    plain = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "plain.log")), clock=CLOCK)
    s1, s2 = DialogState("x"), DialogState("x")
    for q in QUESTIONS:
        if news_request(q)[0]:
            continue                               # the news phrase has its own (offline) reply
        r1, r2 = _ask(a, s1, q), _ask(plain, s2, q)
        assert (r1.kind, r1.text, r1.answer) == (r2.kind, r2.text, r2.answer), q
    assert eg.log.tail(100) == []                  # nothing left the machine


def test_shelf_answers_a_question_the_local_reading_cannot(atlas_chat):
    a, atlas, eg = atlas_chat
    st = DialogState("s")
    r = _ask(a, st, "When was the Zorblax Bridge opened?")
    assert r.kind != "answer"                      # offline: not in the local reading
    eg.set_channel("shelf", enabled=True)
    st = DialogState("s2")
    r = _ask(a, st, "When was the Zorblax Bridge opened?")
    assert r.kind == "answer" and r.answer == "1931" and r.via == "atlas", r.text
    assert r.source["kind"] == "shelf" and r.source["title"] == "Zorblax Bridge" and r.source["as_of"] == "2026-09-20"
    assert "Wikipedia" in r.text and "2026-09-20" in r.text
    r = _ask(a, st, "Who designed it?")
    assert r.kind == "answer" and "Mirela Tosk" in r.answer, r.text
    log = eg.log.tail(100)
    assert log and all(x["channel"] == "shelf" and x["what"].startswith("bucket ") for x in log)
    assert all("Zorblax" not in json.dumps(x) and "opened" not in json.dumps(x) for x in log)
    r = _ask(a, DialogState("s3"), "tell me about the Zorblax Bridge")
    assert r.kind == "about" and "suspension bridge" in r.text and r.source["kind"] == "shelf"


def test_personal_questions_never_go_out(atlas_chat):
    a, atlas, eg = atlas_chat
    eg.set_channel("shelf", enabled=True)
    st = DialogState("p")
    _ask(a, st, "What is my favourite bridge?")
    assert eg.log.tail(100) == []


def test_news_from_the_feed_index(atlas_chat):
    a, atlas, eg = atlas_chat
    st = DialogState("n")
    r = _ask(a, st, "what's the latest news?")
    assert r.via == "news" and r.kind == "unknown"     # feeds are off: says how to switch them on
    eg.set_channel("feeds", enabled=True, feeds=["bbc-world"])
    r = _ask(a, st, "what's the latest news?")
    assert r.via == "news" and r.kind == "unknown"     # on, but nothing fetched yet
    now = int(time.time())
    atlas.feeds.add([Item("bbc-world", "g1", "Quorvia opens new rail line", "The line links two cities.",
                          "https://www.bbc.co.uk/news/1", now - 3600),
                     Item("bbc-world", "g2", "Storm hits the coast", "Winds reached 150 km/h.",
                          "https://www.bbc.co.uk/news/2", now - 7200),
                     Item("dw-en", "g3", "Not a selected feed", "x", "https://www.dw.com/3", now)])
    r = _ask(a, st, "what's the latest news?")
    assert r.via == "news" and "Quorvia opens new rail line" in r.text and "Storm hits the coast" in r.text
    assert "Not a selected feed" not in r.text
    r = _ask(a, st, "any news about Quorvia?")
    assert "Quorvia opens new rail line" in r.text and "Storm" not in r.text
    assert r.source["kind"] == "feed" and r.source["key"] == "https://www.bbc.co.uk/news/1"
    assert eg.log.tail(100) == []                      # answering news sends nothing


def test_life_span_in_the_first_sentence_answers_born(atlas_chat):
    a, atlas, eg = atlas_chat
    eg.set_channel("shelf", enabled=True)
    r = _ask(a, DialogState("b"), "When was Vorna Kell born?")
    # not "1959" from "… touring the coast when a radio host …": the life span after the name counts
    assert r.kind == "answer" and "1911" in r.answer, r.text


def test_unsure_shelf_answer_quotes_the_named_article(atlas_chat):
    import dataclasses
    a, atlas, eg = atlas_chat
    eg.set_channel("shelf", enabled=True)
    a.bot.cfg = dataclasses.replace(a.bot.cfg, theta=1e9)      # never sure enough for a short answer
    st = DialogState("q")
    r = _ask(a, st, "When was the Zorblax Bridge opened?")
    assert r.kind == "about" and r.via == "atlas" and r.answer is None
    assert "Zorblax Bridge" in r.text and "opened in 1931" in r.text and "2026-09-20" in r.text
    r2 = _ask(a, st, "Who designed the Zorblax Bridge?")
    assert "Mirela Tosk" in r2.text and r2.text.split("“")[0] != r.text.split("“")[0]   # worded differently
    r3 = _ask(a, DialogState("q2"), "When was the Velmar Tower opened?")                 # not the named article
    assert r3.via != "atlas"
