"""Data of ENGRAMM-Chat v12 (docs/PREREG_CHAT_V12.md): pool v3, the new dev set and the test set.

Pool v3 consists of the SQuAD questions whose paragraph ENGRAMM read in v12 (the segment of
``chat4``, ``experiments/chat_squad_read.py``). These paragraphs were not read before, so no
question of pool v3 was ever in a pool, a dev set or a test set.

* **Dev12:** pool-v3 questions of the 42 SQuAD-Dev2 articles (the development articles). The span
  perceptron was never trained on these articles.
* **Test12:** pool-v3 questions of the test articles (title bit 1), positions 0–4,999 in v2 hash
  order. Nothing of a test article was ever used for training or development.
* **Invented facts and dialogs:** new phrasings (``data/chat_v12_templates.json``), new names, values
  and typo positions (seed ``test12``).
* **NQ-Test12:** NQ-open ``train`` positions 34,490–38,099 in SHAKE-256 order (earlier rounds:
  0–34,489).
"""

from __future__ import annotations

import hashlib
import json

from experiments.chat_eval import load_squad
from experiments.chat_v2_data import (CACHE, FACTS_PER_DIALOG, N_FACT_DIALOGS, REPO, TEMPLATES, _shuffle, h64,
                                      invented, load_facts, load_nq, statement, typo, value)

V12 = REPO / "data" / "chat_v12_templates.json"

SPLIT = "test12"
N_SQ = 5000
N_NQ = 3610
NQ_FROM = 34490


def pool_v3() -> list[dict]:
    """Every SQuAD question whose paragraph is part of the v12 reading (``squad_read.json``)."""
    from experiments.chat_squad_read import paragraphs
    sel = json.loads((CACHE / "squad_read.json").read_text())
    paras = paragraphs()
    read = {paras[i][1] for i in sel["read_index"]}
    return [q for q in load_squad() if q["context"] in read]


def dev_titles() -> set[str]:
    """The 42 articles of SQuAD-Dev2 (fixed since PREREG_CHAT_V2)."""
    from engramm.chat.corpus import Corpus
    from experiments.chat_v2_common import MODEL_DIR, squad_v2_splits
    dev2, _ = squad_v2_splits(Corpus.load(MODEL_DIR, index_name="chat3"))
    return {q["title"] for q in dev2}


def squad_v12_dev() -> list[dict]:
    titles = dev_titles()
    return sorted((q for q in pool_v3() if q["title"] in titles), key=lambda q: (h64(q["id"]), q["id"]))


def squad_v12_test(pool=None, exclude=None) -> list[dict]:
    """Test12 (the arguments of the older rounds' signature are ignored: pool v3 has no used question)."""
    test = [q for q in pool_v3() if h64("article", q["title"]) & 1 == 1]
    return sorted(test, key=lambda q: (h64(q["id"]), q["id"]))[:N_SQ]


def nq_v12_test() -> list[dict]:
    train = load_nq("train")
    return sorted(train, key=lambda q: (h64("nq", q["question"]), q["id"]))[NQ_FROM:NQ_FROM + N_NQ]


def fact_questions_v12(with_typo: bool = False) -> list[dict]:
    t = json.loads(V12.read_text())["fact_questions"]
    rel, facts = load_facts()
    out = []
    for f in facts:
        e = typo(f["entity"], "v12:" + f["id"]) if with_typo else f["entity"]
        out.append({"id": f["id"], "question": t[f["relation"]].format(e=e), "gold": f["answer"],
                    "statement": statement(rel, f), "entity": e})
    return out


def fact_dialogs_v12() -> list[dict]:
    t3 = json.loads(V12.read_text())["dialog"]
    t2 = json.loads(TEMPLATES.read_text())["dialog"]
    kinds = sorted(t3["facts"])
    out = []
    for d in range(N_FACT_DIALOGS["test"]):
        chosen = _shuffle(kinds, SPLIT, "kinds", d)[:FACTS_PER_DIALOG]
        vals = {k: value(t2["facts"][k]["values"], k, SPLIT, d) for k in chosen}
        tells = [t3["facts"][k]["tell"].format(v=vals[k]) for k in chosen]
        asks = _shuffle(chosen, SPLIT, "asks", d)
        gone = asks[h64("forget", SPLIT, d) % len(asks)]
        turns = [{"user": s} for s in tells]
        turns += [{"user": t3["facts"][k]["ask"], "check": "ask", "gold": vals[k], "kind": k} for k in asks]
        turns.append({"user": t3["forget"].format(topic=t2["facts"][gone]["topic"]), "check": "forget", "kind": gone})
        turns.append({"user": t3["facts"][gone]["ask"], "check": "forgotten", "gold": vals[gone], "kind": gone})
        control = [s for k, s in zip(chosen, tells) if k != gone]
        out.append({"id": f"{SPLIT}-facts-{d}", "turns": turns, "control": control})
    return out


def chain_dialogs_v12() -> list[dict]:
    t3 = json.loads(V12.read_text())
    t2 = json.loads(TEMPLATES.read_text())["dialog"]["chains"]
    rel, facts = load_facts()
    out = []
    for kind, c in t2.items():
        for f in facts:
            if f["relation"] not in c["relations"] or int(f["id"].rsplit("-", 1)[1]) < 5:
                continue
            p = invented("invented_place", SPLIT, h64("chain", f["id"]) % 100000)
            follows = t3["dialog"]["chains"][kind]
            follow = follows[h64("follow12", f["id"]) % len(follows)]
            turns = [{"user": statement(rel, f)}, {"user": c["second"].format(a=f["answer"], p=p)},
                     {"user": t3["fact_questions"][f["relation"]].format(e=f["entity"]), "check": "ask",
                      "gold": f["answer"], "kind": kind},
                     {"user": follow, "check": "follow", "gold": p, "kind": kind}]
            out.append({"id": f"{SPLIT}-chain-{f['id']}", "turns": turns})
    return out


def manifest() -> dict:
    h = hashlib.sha256()
    for item in (squad_v12_test(), nq_v12_test(), fact_questions_v12(), fact_questions_v12(True), fact_dialogs_v12(),
                 chain_dialogs_v12()):
        h.update(json.dumps(item, sort_keys=True).encode())
    return {"generated_sha256": h.hexdigest(), "templates_sha256": hashlib.sha256(V12.read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=2))
