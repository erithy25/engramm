"""Live check of what the chat answers when it searches the web, end to end (informational in CI:
search engines and Wikimedia treat data-centre addresses with suspicion).

    python scripts/chat_smoke.py [ENGRAMM_CORE]

Asks everyday questions in English and German the way a user does ("google …" makes the web search
certain: the small test corpus behind the chat knows none of it) through the app's own network core
(engramm-core egress, or urllib without it) and prints per question the reply the chat shows, its
source and the time it took. A reply counts when it holds what it should; exit code 0 when at least
three in four do, so whatever breaks an answer (a search engine's markup, an API, the composition in
engramm/chat/dialog.py) shows up here.
"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from engramm.chat import index as v2index  # noqa: E402
from engramm.chat.bot import BotConfig, ChatBot, TextMemory  # noqa: E402
from engramm.chat.corpus import Corpus  # noqa: E402
from engramm.chat.dialog import Assistant, DialogState  # noqa: E402
from engramm.chat.retrieve import Retriever, Weights  # noqa: E402
from engramm.lm.model import COMPONENTS, HDCLanguageModel, MixtureSpec  # noqa: E402
from engramm.lm.stream import build_split  # noqa: E402
from engramm.lm.tokenizer import LMTokenizer  # noqa: E402
from engramm.web.atlas import Atlas  # noqa: E402
from engramm.web.egress import Egress, NetworkLog, PythonBackend, RustBackend  # noqa: E402
from tests.test_chat_v2 import DOCS, KEYS  # noqa: E402

# (question, language, any of these in the reply counts; compared without case, dots and commas)
QUESTIONS = [("When was real madrid founded?", "en", ["1902"]),
             ("Who is the president of France?", "en", ["macron"]),
             ("What is the capital of Canada?", "en", ["ottawa"]),
             ("How tall is the Eiffel Tower?", "en", ["330", "324", "312"]),
             ("Who painted the Mona Lisa?", "en", ["leonardo"]),
             ("How many legs does a spider have?", "en", ["eight", "8 legs"]),
             ("What is the boiling point of water?", "en", ["100"]),
             ("Who won the 2022 FIFA World Cup?", "en", ["argentina"]),
             ("What is the speed of light?", "en", ["299"]),
             ("Who wrote Harry Potter?", "en", ["rowling"]),
             ("When did World War II end?", "en", ["1945"]),
             ("How old is Taylor Swift?", "en", ["36"]),
             ("Who founded Apple?", "en", ["jobs", "wozniak"]),
             ("What is the largest ocean?", "en", ["pacific"]),
             ("Who is the CEO of Tesla?", "en", ["musk"]),
             ("What does DNA stand for?", "en", ["deoxyribonucleic"]),
             ("Who discovered penicillin?", "en", ["fleming"]),
             ("What is the population of Japan?", "en", ["122", "123", "124", "125"]),
             ("Wer ist der Bundespräsident von Deutschland?", "de", ["steinmeier"]),
             ("Wann wurde der FC Bayern München gegründet?", "de", ["1900"]),
             ("Was ist die Hauptstadt von Spanien?", "de", ["madrid"]),
             ("Wie lang ist die Donau?", "de", ["2850", "2857", "2845", "2888"]),
             ("Wer hat die Relativitätstheorie entwickelt?", "de", ["einstein"]),
             ("Wie viele Einwohner hat München?", "de", ["14", "15", "16"]),
             ("Was ist Photosynthese?", "de", ["licht", "energie"]),
             ("Wann ist Goethe gestorben?", "de", ["1832"]),
             ("Wie hoch ist der Mount Everest?", "de", ["8848", "8849"]),
             ("Wer hat das Telefon erfunden?", "de", ["bell", "reis", "meucci"])]


def _corpus() -> Corpus:
    """The small corpus of the tests (tests/test_chat_flows.py): the chat around the web search."""
    tok = LMTokenizer()
    train = build_split(DOCS * 2, KEYS * 2, tok.encode_batch)
    model = HDCLanguageModel.build(train, seed=42, tok=tok,
                                   mixture=MixtureSpec(COMPONENTS, np.full((64, 5), 0.2),
                                                       np.array([2000, 4000, 8000]), 1024.0, 4.0))
    ix, dptr, dpost, sent_doc = v2index.build(model.tokens, model.train.doc_starts, tok)
    c = Corpus(model.tokens, model.train.doc_starts, model.train.doc_keys, tok, model.cb.eng, ix, sent_doc, dptr,
               dpost)
    c.wide, c.classes = model.cb.wide, model.cb.classes
    return c


def _plain(text: str) -> str:
    return text.lower().replace(".", "").replace(",", "").replace(" ", "").replace(" ", "")


def main() -> int:
    core = sys.argv[1] if len(sys.argv) > 1 else None
    corpus = _corpus()
    good, sources, slow = 0, {}, []
    with tempfile.TemporaryDirectory() as tmp:
        e = Egress(log=NetworkLog(Path(tmp) / "network.log"), backend=RustBackend(core) if core else PythonBackend(),
                   core=core)
        assistant = Assistant(ChatBot(TextMemory(), corpus, BotConfig(weights=Weights(cov=3, type=2, pcov=1), theta=0.0),
                                      retriever=Retriever(corpus, df_cap=1.0)),
                              clock=dt.datetime.now)
        assistant.atlas = Atlas(e, None, Path(tmp) / "state")
        for n, (q, lang, want) in enumerate(QUESTIONS):
            st = DialogState(f"smoke-{n}")
            st.lang = lang
            t0 = time.time()
            r = assistant.turn(st, ("such im Internet nach " if lang == "de" else "google ") + q)
            took = time.time() - t0
            ok = r.via == "web" and any(_plain(w) in _plain(r.text) for w in want)
            good += ok
            host = (r.source or {}).get("source", "-")
            sources[host] = sources.get(host, 0) + 1
            if took > 8:
                slow.append(q)
            text = r.text.replace("\n", " ")
            print(f"{'ok ' if ok else 'BAD'} {q!r} ({took:.1f} s, {r.kind}, {host})\n      {text[:300]}")
            time.sleep(1.5)                          # well inside Wikimedia's 200 requests a minute (a shared CI address)
        e.close()
    print(f"{good}/{len(QUESTIONS)} answered; sources: {dict(sorted(sources.items(), key=lambda x: -x[1]))}; "
          f"slower than 8 s: {len(slow)}")
    return 0 if good * 4 >= len(QUESTIONS) * 3 else 1


if __name__ == "__main__":
    sys.exit(main())
