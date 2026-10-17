"""Sela-2 in the chat server (engramm/app/server.py chat2) and its chat module (engramm/lm/sela_chat.py): routing
between ENGRAMM, grounded answers and free chat; the check of grounded answers; the sampler's stops and penalty;
a real (tiny, random) NumPy model end to end."""

from __future__ import annotations

import json
import threading

import numpy as np
import pytest

from engramm.app.server import ChatService, serve
from engramm.lm.sela_chat import (ChatState, Turn, cut_sentence, is_abstention, language_of, looping, sample,
                                  sources_from_reply, verify)
from tests.test_chat_app import _Assistant, _Bot, _call


class _Sela2:
    """Stands in for engramm.lm.sela_chat.SelaChat."""

    def __init__(self, grounded_text="E is the answer [1].", verified=True, abstained=False):
        self.calls = []
        self.g = {"text": grounded_text, "tokens": 7, "finished": True, "verified": verified, "abstained": abstained,
                  "issues": [] if verified else ["number 5 not in the cited sources"], "cited": [1], "seconds": 0.01,
                  "prompt_tokens": 50}

    def grounded(self, user, sources, max_tokens=90, seed=None):
        self.calls.append(("grounded", user, list(sources)))
        return dict(self.g)

    def chat(self, state, user, max_tokens=160, seed=None):
        self.calls.append(("chat", user, [t.user for t in state.turns]))
        text = f"reply to {user}"
        state.turns.append(Turn(user, text))
        return {"text": text, "tokens": 5, "finished": True, "seconds": 0.01, "prompt_tokens": 20}


@pytest.fixture()
def svc2(tmp_path):
    svc = ChatService("unused")
    svc.bot = _Bot()
    svc.assistant = _Assistant(svc.bot)
    svc.sela2_path = tmp_path / "sela2-chat.npz"
    svc.sela2 = _Sela2()
    srv = serve(svc, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", svc
    srv.shutdown()
    srv.server_close()


def _chat(base, msg, conv="c1", model="sela-2"):
    code, _, body = _call(base, "/api/chat", {"conversation": conv, "message": msg, "model": model})
    return code, json.loads(body)


def test_models_list_sela2(svc2):
    base, svc = svc2
    m = {x["id"]: x for x in json.loads(_call(base, "/api/models")[2])["models"]}
    assert m["sela-2"]["available"] is True and m["sela-2"]["name"] == "Sela-2 Chat"
    svc.sela2_path = None
    m = {x["id"]: x for x in json.loads(_call(base, "/api/models")[2])["models"]}
    assert m["sela-2"]["available"] is False


def test_memory_commands_stay_with_engramm(svc2):
    base, svc = svc2
    code, r = _chat(base, "remember my dog is Rex")
    assert code == 200 and r["kind"] == "learned" and r["model"] == "engramm" and r["text"] == "Got it."
    assert svc.sela2.calls == [] and "_raw" not in r


def test_knowledge_answer_is_grounded_and_checked(svc2):
    base, svc = svc2
    code, r = _chat(base, "who was Ada Lovelace?")
    assert code == 200 and r["kind"] == "sela_grounded" and r["text"] == "E is the answer [1]."
    assert r["sela_checked"] is True and r["model"] == "sela-2"
    assert r["source"]["title"] == "Ada Lovelace" and r["evidence"] == "E."
    assert svc.sela2.calls[0] == ("grounded", "who was Ada Lovelace?", [("Ada Lovelace", "E.")])


def test_failed_check_keeps_engramms_answer(svc2):
    base, svc = svc2
    svc.sela2 = _Sela2(verified=False)
    code, r = _chat(base, "who was Ada Lovelace?")
    assert code == 200 and r["kind"] == "answer" and r["text"].startswith("prev=")
    assert r["sela_checked"] is False and "number 5" in r["sela_note"] and r["model"] == "engramm"


def test_free_chat_keeps_its_turns_per_conversation(svc2, monkeypatch):
    base, svc = svc2

    class _NoSource(_Assistant):
        def turn(self, state, message):
            r = super().turn(state, message)
            r.source = None
            r.kind = "smalltalk"
            return r
    svc.assistant = _NoSource(svc.bot)
    monkeypatch.setattr("tests.test_chat_app._Reply.to_dict", lambda self: {
        "kind": self.kind, "text": self.text, "answer": None, "guess": None, "evidence": None, "source": None,
        "confidence": 0.0, "via": "smalltalk", "resolved": None, "alternatives": []})
    _, r1 = _chat(base, "hi there")
    _, r2 = _chat(base, "tell me more")
    _, r3 = _chat(base, "hello", conv="other")
    assert r1["kind"] == "sela_chat" and r1["text"] == "reply to hi there" and r1["sela_checked"] is None
    assert svc.sela2.calls[1] == ("chat", "tell me more", ["hi there"])
    assert svc.sela2.calls[2] == ("chat", "hello", [])


def test_sela2_while_engramm_loads_and_when_missing(svc2):
    base, svc = svc2
    svc.assistant = None
    code, r = _chat(base, "hello")
    assert code == 200 and r["kind"] == "sela_chat"
    svc.sela2_path = None
    code, r = _chat(base, "hello")
    assert code == 503 and "not installed" in r["error"]


def test_max_tokens_bounds(svc2):
    base, _ = svc2
    code, _, body = _call(base, "/api/chat", {"conversation": "c", "message": "hi", "model": "sela-2", "max_tokens": 9999})
    assert code == 400


# -- the chat module --------------------------------------------------------------------------------------------

def test_verify_rules():
    src = [("Mount Everest", "Its elevation of 8,848.86 m was established in 2020."), ("K2", "K2 is 8,611 m high.")]
    assert verify("Mount Everest is 8,848.86 m high [1].", src, "How high is Mount Everest?")[0]
    ok, issues = verify("It is 8,611 m [1].", src, "How high?")
    assert not ok and any("8,611" in i for i in issues)
    ok, issues = verify("It is high [3].", src)
    assert not ok and any("missing" in i for i in issues)
    assert not verify("It is 8,848.86 m high.", src)[0]                       # no citation
    assert verify("My sources don't say.", src)[0] and is_abstention("Meine Quellen sagen dazu nichts.")
    ok, issues = verify("It was measured by Tenzing [1].", src)
    assert not ok and any("Tenzing" in i for i in issues)
    assert verify("Der Berg ist 8,848.86 m hoch [1].", src)[0]               # German nouns: only numbers checked


def test_sampler_penalises_only_the_reply_and_stops_loops():
    rng = np.random.default_rng(0)
    z = np.full(50, -5.0)
    z[20] = 5.0
    assert sample(z, [], rng, 0.0, 0.9, 1.5) == 20
    z2 = z.copy()
    z2[21] = 4.0
    assert sample(z2, [20], rng, 0.0, 0.9, 2.0) == 21                         # 20 already in the reply
    assert sample(z2, [2, 2], rng, 0.0, 0.9, 2.0) == 20                       # special ids are never penalised
    assert looping([7, 8, 9, 10] * 3) and not looping([7, 8, 9, 10] * 2 + [1, 2, 3, 4])
    assert cut_sentence("One two three four five. Six seven") == "One two three four five."
    assert cut_sentence("One. Two three four five six") == "One. Two three four five six …"
    assert cut_sentence("Fine [1].") == "Fine [1]."
    assert language_of("Kannst du mir helfen?") == "de" and language_of("Can you help me?") == "en"
    assert language_of("It was measured by him.") == "en" and language_of("Was ist das?") == "de"
    assert sources_from_reply({"evidence": "A.", "source": {"kind": "user"}, "alternatives": [{"text": "B.", "source": None}]}) \
        == [("You told me", "A."), ("", "B.")]


def test_real_numpy_model_end_to_end(tmp_path):
    torch = pytest.importorskip("torch")
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    from engramm.lm.chat_format import SPECIAL_TOKENS
    from engramm.lm.sela_chat import SelaChat
    from engramm.lm.tokenizer import LMTokenizer
    from experiments.sela2_model import Sela2, Sela2Config, export_npz
    tk = Tokenizer(models.BPE())
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    tk.decoder = decoders.ByteLevel()
    tk.train_from_iterator(["Hello, how are you? Mount Everest is high. Wie geht es dir?"] * 50,
                           trainers.BpeTrainer(vocab_size=400, special_tokens=SPECIAL_TOKENS, show_progress=False,
                                               initial_alphabet=pre_tokenizers.ByteLevel.alphabet()))
    tk.save(str(tmp_path / "tok.json"))
    tok = LMTokenizer(tmp_path / "tok.json", sha256=None)
    torch.manual_seed(0)
    m = Sela2(Sela2Config(d=32, layers=2, heads=2, ctx=256, vocab=tok.vocab_size, ve_tables=1))
    path = export_npz(m, tmp_path / "sela2-chat.npz")
    svc = ChatService("unused")
    svc.bot = _Bot()
    svc.assistant = _Assistant(svc.bot)
    svc.sela2_path = path
    svc.sela2 = SelaChat(path, tokenizer=tok)
    r = svc.chat("c", "who was Ada Lovelace?", model="sela-2", max_tokens=12)
    assert r["kind"] in ("sela_grounded", "answer") and r["sela_checked"] in (True, False)
    st = ChatState()
    out = svc.sela2.chat(st, "Hello, how are you?", max_tokens=12, seed=0)
    assert isinstance(out["text"], str) and out["tokens"] <= 12 and len(st.turns) == 1
    ids = svc.sela2.build(st, "and you?", reply_room=20)
    assert ids[0] == 0 and ids[-1] != 2                                    # ends with the open assistant turn
