"""Evaluation data for ENGRAMM-Chat v2, stages 1.1–5 (docs/PREREG_CHAT_V2.md §3).

Fixed together with the registration, before any stage 1.1–5 code: every split,
every invented name and every dialog is a pure function of the files below and
SHAKE-256, so the test data cannot drift while the system is developed.

* SQuAD v1.1 (same files and pool rule as stage 1): split by *article*
  (SHAKE-256 of the title, bit 0 → dev articles, bit 1 → test articles). Dev2 =
  the first 2,000 pool questions of dev articles in question-hash order; Test2 =
  the first 1,000 pool questions of test articles in question-hash order. The
  1,500 questions used by stage 1 (dev + test) are excluded from both.
* NQ-open (Kwiatkowski et al. 2019; Lee et al. 2019): dev = the first 2,000
  questions of the train file in SHAKE-256(question) order; test = all 3,610
  questions of the validation file.
* Invented facts: the 200 facts of ``data/lm_facts_templates.json`` (statement
  form A) with the question templates of ``data/chat_v2_templates.json``; the
  typo variant replaces one inner letter of the entity.
* Dialogs: generated from ``data/chat_v2_templates.json``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "cache" / "chat"
TEMPLATES = REPO / "data" / "chat_v2_templates.json"
FACTS = REPO / "data" / "lm_facts_templates.json"
NQ_REVISION = "5dd9790a83002ad084ddeb7c420dc716852c6f28"
NQ_SHA256 = {
    "train": "25d3a544324f900b31ebc05a3a5686bdd5b9b42738133500675c3f20eee7d83a",
    "validation": "b074bed0bccb56fa1551a8ac1c9c51ce89bc11c7fbb6a9c713b2c33a98531e12",
}
NQ_URL = ("https://huggingface.co/datasets/google-research-datasets/nq_open/resolve/"
          f"{NQ_REVISION}/nq_open/{{split}}-00000-of-00001.parquet")
N_SQ_DEV, N_SQ_TEST, N_NQ_DEV = 2000, 1000, 2000
N_FACT_DIALOGS = {"dev": 100, "test": 200}
FACTS_PER_DIALOG = 4
SYLLABLES = ("ka", "lo", "mi", "ran", "tor", "vel", "sha", "qui", "dor", "bel", "nix", "zar", "fen", "gul",
             "hor", "pem", "ris", "tam", "wo", "yel", "bru", "cas", "dun", "ep", "fro", "gai", "jul", "kro")
COMPANY_SUFFIX = ("Works", "Labs", "Systems", "Foods", "Motors", "Textiles")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")


def h64(*parts) -> int:
    """First 8 bytes (big-endian) of SHAKE-256 over the parts joined by U+001F."""
    data = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.shake_256(data).digest(8), "big")


# ---------------------------------------------------------------------------
# SQuAD and NQ
# ---------------------------------------------------------------------------

def squad_splits(pool: list[dict], exclude: set[str]) -> tuple[list[dict], list[dict]]:
    """(dev2, test2) from the stage-1 pool; ``exclude`` = ids used by stage 1."""
    rest = sorted((q for q in pool if q["id"] not in exclude), key=lambda q: (h64(q["id"]), q["id"]))
    dev = [q for q in rest if h64("article", q["title"]) & 1 == 0][:N_SQ_DEV]
    test = [q for q in rest if h64("article", q["title"]) & 1 == 1][:N_SQ_TEST]
    return dev, test


def load_nq(split: str) -> list[dict]:
    import pyarrow.parquet as pq
    path = CACHE / f"nq_open_{split}.parquet"
    if not path.exists():
        import urllib.request
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(NQ_URL.format(split=split), path)
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != NQ_SHA256[split]:
        raise RuntimeError(f"{path.name}: SHA-256 {got} != {NQ_SHA256[split]}")
    rows = pq.read_table(path).to_pylist()
    return [{"id": f"nq-{split}-{i}", "question": r["question"], "answers": list(r["answer"])}
            for i, r in enumerate(rows)]


def nq_splits() -> tuple[list[dict], list[dict]]:
    train = load_nq("train")
    dev = sorted(train, key=lambda q: (h64("nq", q["question"]), q["id"]))[:N_NQ_DEV]
    return dev, load_nq("validation")


# ---------------------------------------------------------------------------
# invented facts
# ---------------------------------------------------------------------------

def load_facts() -> tuple[dict, list[dict]]:
    d = json.loads(FACTS.read_text())
    return {r["name"]: r for r in d["relations"]}, d["facts"]


def statement(rel: dict, fact: dict) -> str:
    return rel[fact["relation"]]["A"].format(e=fact["entity"], a=fact["answer"])


def typo(word: str, key: str) -> str:
    """Replace one inner letter (never the first or last) by another lower-case letter."""
    h = h64("typo", key)
    p = 1 + h % (len(word) - 2)
    c = word[p].lower()
    new = chr(ord("a") + (ord(c) - ord("a") + 1 + (h >> 16) % 25) % 26) if c.isalpha() else "x"
    return word[:p] + new + word[p + 1:]


def fact_questions(split: str, with_typo: bool = False) -> list[dict]:
    """One question per invented fact, in the split's phrasing."""
    templates = json.loads(TEMPLATES.read_text())["fact_questions"]
    rel, facts = load_facts()
    out = []
    for f in facts:
        e = typo(f["entity"], f["id"]) if with_typo else f["entity"]
        out.append({"id": f["id"], "question": templates[f["relation"]][split].format(e=e),
                    "gold": f["answer"], "statement": statement(rel, f), "entity": e})
    return out


# ---------------------------------------------------------------------------
# dialogs
# ---------------------------------------------------------------------------

def invented(kind: str, split: str, i: int) -> str:
    h = h64("name", kind, split, i)
    n = 2 + h % 2
    word = "".join(SYLLABLES[(h >> (8 + 5 * k)) % len(SYLLABLES)] for k in range(n)).capitalize()
    if kind == "invented_company":
        return f"{word} {COMPANY_SUFFIX[(h >> 40) % len(COMPANY_SUFFIX)]}"
    return word


def value(spec, kind_key: str, split: str, i: int) -> str:
    if isinstance(spec, list):
        return spec[h64("value", kind_key, split, i) % len(spec)]
    if spec == "date":
        h = h64("date", split, i)
        return f"{1 + h % 28} {MONTHS[(h >> 8) % 12]}"
    return invented(spec, split, i * 31 + len(kind_key))


def _shuffle(items: list, *key) -> list:
    return sorted(items, key=lambda x: (h64("shuffle", *key, x), str(x)))


def fact_dialogs(split: str) -> list[dict]:
    """Tell 4 facts about yourself, ask them back, forget one, ask it again.

    Each dialog also carries a ``control`` script: the same tells without the forgotten
    one; the memory after the forget must be bit-identical to the control's memory."""
    t = json.loads(TEMPLATES.read_text())["dialog"]
    kinds = sorted(t["facts"])
    out = []
    for d in range(N_FACT_DIALOGS[split]):
        chosen = _shuffle(kinds, split, "kinds", d)[:FACTS_PER_DIALOG]
        vals = {k: value(t["facts"][k]["values"], k, split, d) for k in chosen}
        tells = [t["facts"][k]["tell"][split].format(v=vals[k]) for k in chosen]
        asks = _shuffle(chosen, split, "asks", d)
        gone = asks[h64("forget", split, d) % len(asks)]
        turns = [{"user": s} for s in tells]
        turns += [{"user": t["facts"][k]["ask"][split], "check": "ask", "gold": vals[k], "kind": k} for k in asks]
        turns.append({"user": t["forget"][split].format(topic=t["facts"][gone]["topic"]), "check": "forget",
                      "kind": gone})
        turns.append({"user": t["facts"][gone]["ask"][split], "check": "forgotten", "gold": vals[gone],
                      "kind": gone})
        control = [s for k, s in zip(chosen, tells) if k != gone]
        out.append({"id": f"{split}-facts-{d}", "turns": turns, "control": control})
    return out


def chain_dialogs(split: str) -> list[dict]:
    """Learn a fact and a second fact about its answer; ask, then follow up with a pronoun."""
    t = json.loads(TEMPLATES.read_text())
    qs = t["fact_questions"]
    rel, facts = load_facts()
    out = []
    for kind, c in t["dialog"]["chains"].items():
        chosen = [f for f in facts if f["relation"] in c["relations"]]
        for f in chosen:
            idx = int(f["id"].rsplit("-", 1)[1])
            if (idx < 5) != (split == "dev"):
                continue
            p = invented("invented_place", split, h64("chain", f["id"]) % 100000)
            follow = c["follow"][split][h64("follow", f["id"]) % len(c["follow"][split])]
            turns = [{"user": statement(rel, f)}, {"user": c["second"].format(a=f["answer"], p=p)},
                     {"user": qs[f["relation"]][split].format(e=f["entity"]), "check": "ask", "gold": f["answer"],
                      "kind": kind},
                     {"user": follow, "check": "follow", "gold": p, "kind": kind}]
            out.append({"id": f"{split}-chain-{f['id']}", "turns": turns})
    return out


def manifest() -> dict:
    """Digest of all generated evaluation data (stored in the registration)."""
    h = hashlib.sha256()
    for split in ("dev", "test"):
        for item in (fact_questions(split), fact_questions(split, True), fact_dialogs(split), chain_dialogs(split)):
            h.update(json.dumps(item, sort_keys=True).encode())
    return {"generated_sha256": h.hexdigest(), "templates_sha256": hashlib.sha256(TEMPLATES.read_bytes()).hexdigest(),
            "facts_sha256": hashlib.sha256(FACTS.read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=2))
    for d in (fact_dialogs("test")[0], chain_dialogs("test")[0]):
        print(json.dumps(d, indent=1))
    print(fact_questions("test", True)[:3])
