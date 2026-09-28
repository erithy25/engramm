"""Test data of ENGRAMM-Chat v14 (docs/PREREG_CHAT_V14.md), fixed with the registration.

* **SQuAD-Test14:** pool v3 (questions of the paragraphs read in v12), test articles (title bit 1),
  positions 10,000–14,999 in v2 hash order (0–9,999 were Test12 and Test13).
* **NQ-Test14:** NQ-open ``train`` positions 41,710–45,319 in SHAKE-256 order (earlier rounds: 0–41,709).
* **Invented facts and dialogs:** new phrasings (``data/chat_v14_templates.json``), new names, values
  and typo positions (seed ``test14``).
"""

from __future__ import annotations

import hashlib
import json

from experiments.chat_v12_data import pool_v3
from experiments.chat_v2_data import (FACTS_PER_DIALOG, N_FACT_DIALOGS, REPO, TEMPLATES, _shuffle, h64, invented,
                                      load_facts, load_nq, statement, typo, value)

V14 = REPO / "data" / "chat_v14_templates.json"
SPLIT = "test14"
N_SQ = 5000
SQ_FROM = 10000
N_NQ = 3610
NQ_FROM = 41710


def squad_v14_test(pool=None, exclude=None) -> list[dict]:
    """Test14 (the arguments of the older rounds' signature are ignored)."""
    test = [q for q in pool_v3() if h64("article", q["title"]) & 1 == 1]
    return sorted(test, key=lambda q: (h64(q["id"]), q["id"]))[SQ_FROM:SQ_FROM + N_SQ]


def nq_v14_test() -> list[dict]:
    train = load_nq("train")
    return sorted(train, key=lambda q: (h64("nq", q["question"]), q["id"]))[NQ_FROM:NQ_FROM + N_NQ]


def fact_questions_v14(with_typo: bool = False) -> list[dict]:
    t = json.loads(V14.read_text())["fact_questions"]
    rel, facts = load_facts()
    out = []
    for f in facts:
        e = typo(f["entity"], "v14:" + f["id"]) if with_typo else f["entity"]
        out.append({"id": f["id"], "question": t[f["relation"]].format(e=e), "gold": f["answer"],
                    "statement": statement(rel, f), "entity": e})
    return out


def fact_dialogs_v14() -> list[dict]:
    t3 = json.loads(V14.read_text())["dialog"]
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


def chain_dialogs_v14() -> list[dict]:
    t3 = json.loads(V14.read_text())
    t2 = json.loads(TEMPLATES.read_text())["dialog"]["chains"]
    rel, facts = load_facts()
    out = []
    for kind, c in t2.items():
        for f in facts:
            if f["relation"] not in c["relations"] or int(f["id"].rsplit("-", 1)[1]) < 5:
                continue
            p = invented("invented_place", SPLIT, h64("chain", f["id"]) % 100000)
            follows = t3["dialog"]["chains"][kind]
            follow = follows[h64("follow14", f["id"]) % len(follows)]
            turns = [{"user": statement(rel, f)}, {"user": c["second"].format(a=f["answer"], p=p)},
                     {"user": t3["fact_questions"][f["relation"]].format(e=f["entity"]), "check": "ask",
                      "gold": f["answer"], "kind": kind},
                     {"user": follow, "check": "follow", "gold": p, "kind": kind}]
            out.append({"id": f"{SPLIT}-chain-{f['id']}", "turns": turns})
    return out


def manifest() -> dict:
    h = hashlib.sha256()
    for item in (squad_v14_test(), nq_v14_test(), fact_questions_v14(), fact_questions_v14(True), fact_dialogs_v14(),
                 chain_dialogs_v14()):
        h.update(json.dumps(item, sort_keys=True).encode())
    return {"generated_sha256": h.hexdigest(), "templates_sha256": hashlib.sha256(V14.read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=2))
