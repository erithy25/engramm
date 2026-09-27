"""Test data of ENGRAMM-Chat v4 (docs/PREREG_CHAT_V4.md §3), fixed with the registration.

The v4 test consists of data nobody has looked at:

* SQuAD: pool questions 2,000–2,999 of the test articles in v2 hash order (v2: 0–999, v3: 1,000–1,999).
* NQ-open: train positions 5,610–9,219 in SHAKE-256 order (v2-dev 0–1,999, v3 2,000–5,609).
* Invented facts and dialogs: new phrasings (``data/chat_v4_templates.json``), new names,
  new values and new typo positions.
"""

from __future__ import annotations

import hashlib
import json

from experiments.chat_v2_data import (FACTS_PER_DIALOG, N_FACT_DIALOGS, REPO, TEMPLATES, _shuffle, h64, invented,
                                      load_facts, load_nq, statement, typo, value)

V4 = REPO / "data" / "chat_v4_templates.json"
SPLIT = "test4"
N_SQ, N_NQ = 1000, 3610


def squad_v4_test(pool: list[dict], exclude: set[str]) -> list[dict]:
    rest = sorted((q for q in pool if q["id"] not in exclude), key=lambda q: (h64(q["id"]), q["id"]))
    test_articles = [q for q in rest if h64("article", q["title"]) & 1 == 1]
    return test_articles[2000:2000 + N_SQ]


def nq_v4_test() -> list[dict]:
    train = load_nq("train")
    return sorted(train, key=lambda q: (h64("nq", q["question"]), q["id"]))[5610:5610 + N_NQ]


def fact_questions_v4(with_typo: bool = False) -> list[dict]:
    t = json.loads(V4.read_text())["fact_questions"]
    rel, facts = load_facts()
    out = []
    for f in facts:
        e = typo(f["entity"], "v4:" + f["id"]) if with_typo else f["entity"]
        out.append({"id": f["id"], "question": t[f["relation"]].format(e=e), "gold": f["answer"],
                    "statement": statement(rel, f), "entity": e})
    return out


def fact_dialogs_v4() -> list[dict]:
    t3 = json.loads(V4.read_text())["dialog"]
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


def chain_dialogs_v4() -> list[dict]:
    t3 = json.loads(V4.read_text())
    t2 = json.loads(TEMPLATES.read_text())["dialog"]["chains"]
    rel, facts = load_facts()
    out = []
    for kind, c in t2.items():
        for f in facts:
            if f["relation"] not in c["relations"] or int(f["id"].rsplit("-", 1)[1]) < 5:
                continue
            p = invented("invented_place", SPLIT, h64("chain", f["id"]) % 100000)
            follows = t3["dialog"]["chains"][kind]
            follow = follows[h64("follow4", f["id"]) % len(follows)]
            turns = [{"user": statement(rel, f)}, {"user": c["second"].format(a=f["answer"], p=p)},
                     {"user": t3["fact_questions"][f["relation"]].format(e=f["entity"]), "check": "ask",
                      "gold": f["answer"], "kind": kind},
                     {"user": follow, "check": "follow", "gold": p, "kind": kind}]
            out.append({"id": f"{SPLIT}-chain-{f['id']}", "turns": turns})
    return out


def manifest() -> dict:
    h = hashlib.sha256()
    for item in (fact_questions_v4(), fact_questions_v4(True), fact_dialogs_v4(), chain_dialogs_v4()):
        h.update(json.dumps(item, sort_keys=True).encode())
    return {"generated_sha256": h.hexdigest(), "templates_sha256": hashlib.sha256(V4.read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=2))
