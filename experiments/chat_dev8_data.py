"""Development dialogs for stage 3 after E20 (``data/chat_dev8_paraphrases.json``).

Many phrasings per fact kind, combined at random (SHAKE-256, seed ``dev8``): every dialog
tells four facts, each in one of the listed phrasings, asks them back in other listed
phrasings, forgets one and asks it again. Spent by design — development only.
"""

from __future__ import annotations

import json

from experiments.chat_v2_data import (FACTS_PER_DIALOG, REPO, TEMPLATES, _shuffle, h64, invented, load_facts,
                                      statement, value)

DEV8 = REPO / "data" / "chat_dev8_paraphrases.json"
FILES = {"dev8": DEV8, "dev9": REPO / "data" / "chat_dev9_paraphrases.json"}
SPLIT = "dev8"
N_DIALOGS = 400


def _pick(options: list[str], *key, split: str = SPLIT) -> str:
    return options[h64("pick", split, *key) % len(options)]


def fact_dialogs_dev8(split: str = SPLIT) -> list[dict]:
    p = json.loads(FILES[split].read_text())["dialog"]
    t2 = json.loads(TEMPLATES.read_text())["dialog"]
    kinds = sorted(p["facts"])
    out = []
    for d in range(N_DIALOGS):
        chosen = _shuffle(kinds, split, "kinds", d)[:FACTS_PER_DIALOG]
        vals = {k: value(t2["facts"][k]["values"], k, split, d) for k in chosen}
        tells = [_pick(p["facts"][k]["tell"], "tell", k, d, split=split).format(v=vals[k]) for k in chosen]
        asks = _shuffle(chosen, split, "asks", d)
        gone = asks[h64("forget", split, d) % len(asks)]
        ask_text = {k: _pick(p["facts"][k]["ask"], "ask", k, d, split=split) for k in chosen}
        turns = [{"user": s} for s in tells]
        turns += [{"user": ask_text[k], "check": "ask", "gold": vals[k], "kind": k} for k in asks]
        turns.append({"user": _pick(p["forget"], "forget", d, split=split).format(topic=t2["facts"][gone]["topic"]),
                      "check": "forget", "kind": gone})
        turns.append({"user": _pick(p["facts"][gone]["ask"], "ask2", gone, d, split=split), "check": "forgotten",
                      "gold": vals[gone], "kind": gone})
        control = [s for k, s in zip(chosen, tells) if k != gone]
        out.append({"id": f"{split}-facts-{d}", "turns": turns, "control": control})
    return out


def chain_dialogs_dev8(split: str = SPLIT) -> list[dict]:
    p = json.loads(FILES[split].read_text())["dialog"]["chains"]
    t2 = json.loads(TEMPLATES.read_text())
    rel, facts = load_facts()
    out = []
    for kind, c in t2["dialog"]["chains"].items():
        for f in facts:
            if f["relation"] not in c["relations"]:
                continue
            pl = invented("invented_place", split, h64("chain", f["id"]) % 100000)
            follow = _pick(p[kind], "follow", f["id"], split=split)
            ask = t2["fact_questions"][f["relation"]]["dev" if h64("q", f["id"]) & 1 else "test"]
            turns = [{"user": statement(rel, f)}, {"user": c["second"].format(a=f["answer"], p=pl)},
                     {"user": ask.format(e=f["entity"]), "check": "ask", "gold": f["answer"], "kind": kind},
                     {"user": follow, "check": "follow", "gold": pl, "kind": kind}]
            out.append({"id": f"{split}-chain-{f['id']}", "turns": turns})
    return out


if __name__ == "__main__":
    d = fact_dialogs_dev8()
    print(len(d), "dialogs;", len(chain_dialogs_dev8()), "chains")
    print(json.dumps(d[0], indent=1))
