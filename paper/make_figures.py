#!/usr/bin/env python3
"""Figures, tables and numbers of the paper (paper/main.tex), computed from the repository's own result files.

    nice -n 19 python3 paper/make_figures.py

Writes
  paper/figures/*.pdf            vector figures (matplotlib)
  paper/generated/numbers.tex    \\stat{...} values used in the text (bootstrap and Wilson intervals included)
  paper/generated/tab_*.tex      table bodies that main.tex \\input-s
  paper/generated/stats.json     everything above in machine-readable form

Inputs (read only): results/sela2/learn*/{summary.json,part_*.json,app_learn_*.json},
results/sela2/learn_probe/*.json, data/sela2/learn_sessions*.json (synthetic users only). Real users' texts are not
in the repository and are not needed: their result files keep each message only as SHA-256 and length, and the
held-out scores (nats with and without the memory) are stored per message.

Requires numpy and matplotlib. No network access. Deterministic (fixed bootstrap seed).
"""

from __future__ import annotations

import glob
import json
import math
import re
import zlib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results" / "sela2"
DATA = REPO / "data" / "sela2"
OUT_FIG = REPO / "paper" / "figures"
OUT_GEN = REPO / "paper" / "generated"
B = 10_000                     # bootstrap replicates
SEED = 20261019                # bootstrap seed (any fixed value; the date of the first registered measurement)
FACT_KEYS = ("name", "city", "pet", "food")

STATS: dict[str, str] = {}     # \stat{key} -> text for numbers.tex
JSON_OUT: dict = {}            # stats.json


def rng_for(key: str) -> np.random.Generator:
    """A bootstrap generator per quantity (fixed seed and the quantity's name): the same run gets the same interval
    wherever it is reported, independent of the order of the computations."""
    return np.random.default_rng([SEED, zlib.crc32(key.encode("utf-8"))])


def stat(key: str, value) -> None:
    STATS[key] = str(value)


def fmt(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


# ---------------------------------------------------------------------------------------------------- loading ----

def load_parts(run: str) -> list[dict]:
    files = sorted(glob.glob(str(RES / run / "part_*.json")))
    if not files:
        raise SystemExit(f"no part files for {run}")
    return [u for f in files for u in json.loads(Path(f).read_text(encoding="utf-8"))["results"]]


def load_summary(run: str) -> dict:
    return json.loads((RES / run / "summary.json").read_text(encoding="utf-8"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def users_of(data_file: str) -> dict:
    return {u["id"]: u for u in load_json(DATA / data_file)["users"]}


# -------------------------------------------------------------------------------------------------- statistics ----

def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """95 % Wilson score interval for a proportion k/n, in percent."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (100 * max(0.0, centre - half), 100 * min(1.0, centre + half))


def l3_gain(base: np.ndarray, mem: np.ndarray) -> float:
    """Relative reduction in bits per byte, in percent (bytes cancel: the ratio of summed nats)."""
    return 100.0 * (base.sum() - mem.sum()) / base.sum()


def user_arrays(users: list[dict], probe: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Per user: summed nats of the held-out messages without and with the memory."""
    if probe:   # development probe (experiments/sela2_learn_probe.py): the app's rule and mixing setting = "R2_app"
        b = [sum(h["base"] for h in u["held_out"]) for u in users]
        m = [sum(h["grid"]["R2_app"] for h in u["held_out"]) for u in users]
    else:       # app measurement (experiments/sela2_learn_eval.py)
        b = [sum(h["nats_base"] for h in u["held_out"]) for u in users]
        m = [sum(h["nats_memory"] for h in u["held_out"]) for u in users]
    return np.array(b), np.array(m)


def clusters_of(users: list[dict], data_file: str | None) -> list[str]:
    """The resampling unit of each user. Synthetic users (experiments/sela2_learn_data.py) come in 10 hobby scripts per
    set, each shared by 4 users (same four hobby messages, same two held-out sentences; only the facts and the appended
    mistakes differ): the hobby script is the independent unit. Real users each have their own messages: the user."""
    if data_file is None:
        return [u["id"] for u in users]
    d = users_of(data_file)
    return [f"{d[u['id']]['lang']}:{d[u['id']]['hobby']}" for u in users]


def bootstrap_l3(b: np.ndarray, m: np.ndarray, key: str,
                 clusters: list[str] | None = None) -> tuple[float, float, float]:
    """L3 and its 95 % percentile interval from resampling clusters (users, or hobby scripts) with replacement."""
    if clusters is None:
        clusters = [str(i) for i in range(len(b))]
    keys = sorted(set(clusters))
    cb = np.array([b[[i for i, c in enumerate(clusters) if c == k]].sum() for k in keys])
    cm = np.array([m[[i for i, c in enumerate(clusters) if c == k]].sum() for k in keys])
    n = len(keys)
    idx = rng_for(key).integers(0, n, size=(B, n))
    gains = 100.0 * (cb[idx].sum(1) - cm[idx].sum(1)) / cb[idx].sum(1)
    lo, hi = np.percentile(gains, [2.5, 97.5])
    return l3_gain(b, m), float(lo), float(hi)


def bootstrap_prop(rows: list[tuple[str, int, int]], key: str) -> tuple[float, float]:
    """95 % percentile interval of a pooled proportion (in %) from resampling users; rows: (user, hits, trials)."""
    h = np.array([r[1] for r in rows], dtype=float)
    t = np.array([r[2] for r in rows], dtype=float)
    idx = rng_for(key).integers(0, len(rows), size=(B, len(rows)))
    p = 100.0 * h[idx].sum(1) / np.maximum(1.0, t[idx].sum(1))
    lo, hi = np.percentile(p, [2.5, 97.5])
    return float(lo), float(hi)


# -------------------------------------------------------------------------------- registered measurements ----

REGISTERED = [  # key, section, run directory, users' data file (None: real users), what changed
    ("s7", "§7", "learn", "learn_sessions.json", "first version (facts as first-person turn; C with near-form filter)"),
    ("s8", "§8", "learn_v2", "learn_sessions_v2.json", "labelled note + guard; whole-text word check; sentence exclusion"),
    ("s9a", "§9", "learn_v3_labels", "learn_sessions_v3.json", "same code, note as labels (A/B arm 1)"),
    ("s9b", "§9", "learn_v3_sentences", "learn_sessions_v3.json", "note as third-person sentences (A/B arm 2)"),
    ("s10a", "§10", "learn_v4_labels", "learn_sessions_v4.json", "repeat of the note A/B, labels"),
    ("s10b", "§10", "learn_v4_sentences", "learn_sessions_v4.json", "repeat of the note A/B, sentences"),
    ("s11", "§11", "learn_real", None, "letter shape rule; first real users"),
    ("s12a", "§12", "learn_real2_relevant", None, "relevance filter for the note (decides)"),
    ("s12b", "§12", "learn_real2_all", None, "no filter (comparison, same users)"),
]
DEV_RUNS = ["learn_dev_v2a", "learn_dev_v2b", "learn_dev_v2c", "learn_dev_v2d", "learn_dev_v2e", "learn_dev_v2f",
            "learn_dev_v2g", "learn_dev_v2h"]


def app_off_problems(run: str) -> int:
    a = load_json(RES / run / "app_learn_off.json")
    return int(a["summary"]["all"]["prompts_with_a_problem"])


def app_intrusions(run: str, arm: str, facts: dict) -> tuple[int, int]:
    """Sela-2 replies to the 100 app prompts (after teaching the first test user) that name one of that user's facts.
    Counted from the recorded replies with the measurement's own definition (experiments/sela2_learn_eval.intrusion);
    the §12 runs also recorded the per-reply field, which must agree."""
    a = load_json(RES / run / f"app_learn_{arm}.json")
    reps = [t for x in a["rows"] for t in x["replies"] if t.get("model") == "sela-2"]
    hits = 0
    for t in reps:
        hit = bool(intrusion(facts, None, t.get("text") or ""))
        if "intrusion" in t:
            assert bool(t["intrusion"]) == hit, (run, arm, "recorded intrusion field disagrees with the recount")
        hits += hit
    return hits, len(reps)


def intrusion(facts: dict, asked: str | None, text: str) -> list[str]:
    """experiments/sela2_learn_eval.intrusion: facts (name, city, pet's name, favourite food) a reply mentions although
    the probe did not ask for them."""
    return [k for k in FACT_KEYS if k != asked and facts.get(k)
            and re.search(r"(?<!\w)" + re.escape(str(facts[k])) + r"(?!\w)", text, re.IGNORECASE)]


def facts_from_note(note: str, lang: str) -> dict:
    """The four facts of a user as the result file shows them (the note in sentence or label form). Used for real
    users, whose data file is not in the repository; for synthetic users the data file is used and compared."""
    if lang == "en":
        pats = {"name": [r"The user's name is ([^.]+)\.", r"name: ([^;.]+)"],
                "city": [r"The user lives in ([^.]+)\.", r"lives in: ([^;.]+)"],
                "pet": [r"The user's \w+ (?:is|are) called ([^.]+)\.", r"their \w+: ([^;.]+)"],
                "food": [r"The user's favourite food is ([^.]+)\.", r"favourite food: ([^;.]+)"]}
    else:
        pats = {"name": [r"Der Nutzer heißt ([^.]+)\.", r"Name: ([^;.]+)"],
                "city": [r"Der Nutzer wohnt in ([^.]+)\.", r"wohnt in: ([^;.]+)"],
                "pet": [r"(?:Der|Die|Das) \w+ des Nutzers heißt ([^.]+)\.", r"(?:Hund|Katze): ([^;.]+)"],
                "food": [r"Das Lieblingsessen des Nutzers ist ([^.]+)\.", r"Lieblingsessen: ([^;.]+)"]}
    out = {}
    for k, ps in pats.items():
        for p in ps:
            mm = re.search(p, note)
            if mm:
                out[k] = mm.group(1).strip()
                break
    return out


def probe_intrusion(users: list[dict], facts_of, arm: str) -> tuple[int, int]:
    """Sela-2 replies to the probes (one arm) that name a fact the probe did not ask for (§12, L6)."""
    hits = n = 0
    for u in users:
        facts = facts_of(u)
        for r in u["arms"][arm]:
            if r.get("model") != "sela-2":
                continue
            asked = FACT_KEYS[r["probe"]] if r["kind"] == "fact" else None   # fact probes come first, in this order
            n += 1
            hits += bool(intrusion(facts, asked, r.get("text") or ""))
    return hits, n


_WRONG_EXTRA = {"should of": r"(?!\s+course\b)",
                "she go": "".join(rf"(?<!{w} )" for w in ("does", "did", "will", "would", "can", "could", "should",
                                                          "let", "might", "may", "must", "where", "when", "why"))}


def wrong_pattern(wrong: str) -> re.Pattern:
    """experiments/sela2_learn_eval.wrong_pattern: a reply contains the user's injected wrong form."""
    extra = _WRONG_EXTRA.get(wrong, "")
    if wrong == "she go":
        return re.compile(extra + r"(?<!\w)she go(?!\w)", re.IGNORECASE)
    return re.compile(r"(?<!\w)" + re.escape(wrong) + extra + r"(?!\w)", re.IGNORECASE)


def copies(users: list[dict], arm: str) -> list[dict]:
    """Replies of one arm that contain an injected wrong form, with what happened to that mistake when the user's
    message was learned (spell-checked / not learned / filtered / stored, read from the memory itself)."""
    out = []
    for u in users:
        fate = {c["wrong"]: c["how"] for c in u["errors_caught"]}
        for r in u["arms"][arm]:
            if not r.get("error_copied"):
                continue
            # the reply text in the results is scrubbed of real users' word runs; the wrong form itself survives
            hits = [w for w in fate if wrong_pattern(w).search(r.get("text") or "")]
            out.append({"user": u["id"], "probe": r["kind"], "wrong": hits, "fate": [fate[w] for w in hits]})
    return out


def registered_measurements() -> list[dict]:
    rows = []
    for key, sec, run, data_file, what in REGISTERED:
        s = load_summary(run)
        users = load_parts(run)
        assert len(users) == s["users"] == 40, run
        c, a = s["criteria"], s["arms"]
        b, m = user_arrays(users)
        g, lo, hi = bootstrap_l3(b, m, f"L3:{run}", clusters_of(users, data_file))
        g_u, lo_u, hi_u = bootstrap_l3(b, m, f"L3-by-user:{run}")   # resampling users instead (comparison only)
        assert abs(round(g, 2) - c["L3_memory_bpb"]["value"]) < 0.006, (run, g)
        n_pair = a["F"]["fact_probes"]
        kF, kOff = a["F"]["fact_used"], a["off"]["fact_used"]
        assert kOff == 0, run                      # off never used a fact: L1 equals the F rate
        l1 = 100 * (kF - kOff) / n_pair
        w = wilson(kF, n_pair)
        off_app = app_off_problems(run)
        # L1 with a bootstrap over users (the fact probes of one user are not independent of each other)
        per_user = []
        for u in users:
            pr = [r for r in u["arms"]["off"] if r["kind"] == "fact"
                  and all(u["arms"][arm][r["probe"]].get("model") == "sela-2" for arm in ("off", "F", "FK"))]
            per_user.append((u["id"], sum(bool(u["arms"]["F"][r["probe"]].get("fact_used")) for r in pr), len(pr)))
        assert sum(x[1] for x in per_user) == kF and sum(x[2] for x in per_user) == n_pair, run
        l1_boot = bootstrap_prop(per_user, f"L1:{run}")
        fk_copies = copies(users, "FK")
        assert len(fk_copies) == a["FK"]["error_copied"], run
        row = {"key": key, "section": sec, "run": run, "users": "synthetic" if data_file else "real", "change": what,
               "FK_copies": fk_copies,
               "resampling_unit": "hobby script (10 per set)" if data_file else "user (40)",
               "L3_ci_by_user": (lo_u, hi_u), "L1_ci_boot": l1_boot,
               "n_users": s["users"], "replies_per_arm": a["F"]["replies"], "sela_replies": a["F"]["sela_replies"],
               "fact_probes": n_pair, "coverage": c["L1_coverage"]["value"],
               "L1": l1, "L1_k": kF, "L1_ci": w,
               "L1_FK": 100 * a["FK"]["fact_used"] / n_pair, "L1_FK_k": a["FK"]["fact_used"],
               "L1_en_F": a["F"]["fact_used_pct_en"], "L1_de_F": a["F"]["fact_used_pct_de"],
               "L2_F": a["F"]["error_copied"], "L2_FK": a["FK"]["error_copied"], "L2_off": a["off"]["error_copied"],
               "L2b_F": a["F"]["role_confusion"], "L2b_FK": a["FK"]["role_confusion"],
               "L2b_off": a["off"]["role_confusion"], "role_checked": a["F"]["role_checked"],
               "L3": g, "L3_ci": (lo, hi), "bpb_base": s["held_out"]["bpb_base"],
               "bpb_memory": s["held_out"]["bpb_memory"], "held_bytes": s["held_out"]["bytes"],
               "L4_off": off_app, "L4_F": c["L4_app_F"]["value"], "L4_FK": c["L4_app_FK"]["value"],
               "L5": c["L5_speed"]["value"], "L5_tokps_F": a["F"].get("decode_tokens_per_s"),
               "errors": s["errors_caught"], "decision": s["decision"],
               "users_gain_pos": int(((b - m) > 0).sum())}
        if "L6_intrusion_F" in c:
            row.update({"L6_F": c["L6_intrusion_F"]["value"], "L6_FK": c["L6_intrusion_FK"]["value"],
                        "L6_F_k": a["F"]["intrusion"], "L6_FK_k": a["FK"]["intrusion"],
                        "L6_app_F": c["L6_app_F"]["value"], "L6_app_FK": c["L6_app_FK"]["value"]})
        rows.append(row)
    return rows


# ------------------------------------------------------------------------------------- lexical reuse (§11) ----

SYNTH_GROUPS = [  # label, data file, app run whose held-out scores are used (code identical to the registered test)
    ("§7", "learn_sessions.json", "learn_dev_v2f"),
    ("§8", "learn_sessions_v2.json", "learn_v2"),
    ("§9", "learn_sessions_v3.json", "learn_v3_labels"),
    ("§10", "learn_sessions_v4.json", "learn_v4_labels"),
]
BINS = [("none", "no shared bigram"), ("lt10", "$0$–$10\\,\\%$"), ("10to20", "$10$–$20\\,\\%$"),
        ("ge20", "$\\geq 20\\,\\%$")]


def bigrams(text: str) -> list[tuple[str, str]]:
    """Word pairs of a text: lower-cased \\w+ tokens, consecutive pairs (the definition that reproduces the
    numbers of docs/PREREG_SELA2.md §11)."""
    w = re.findall(r"\w+", text.lower())
    return [tuple(w[i:i + 2]) for i in range(len(w) - 1)]


def bin_of(shared: int, total: int) -> str:
    p = 100.0 * shared / total
    if shared == 0:
        return "none"
    if p < 10:
        return "lt10"
    if p < 20:
        return "10to20"
    return "ge20"


def lexical_reuse() -> dict:
    """For every held-out sentence of the four synthetic groups: the share of its bigrams that already occur in the
    same user's taught messages, and its nats with and without the memory (the app measurement's own scores)."""
    sents = []          # (group, hobby script, shared, total, nats_base, nats_memory, user)
    for label, data_file, run in SYNTH_GROUPS:
        users = users_of(data_file)
        for u in load_parts(run):
            taught = set(bg for msg in users[u["id"]]["teach"] for bg in bigrams(msg))
            script = f"{users[u['id']]['lang']}:{users[u['id']]['hobby']}"
            for i, h in enumerate(u["held_out"]):
                assert h["text"] == users[u["id"]]["held_out"][i], "held-out text differs from the data file"
                hb = bigrams(h["text"])
                sents.append((label, script, sum(bg in taught for bg in hb), len(hb), h["nats_base"],
                              h["nats_memory"], u["id"], h["text"]))
    out = {"groups": {}, "bins": {}}
    for label, _, run in SYNTH_GROUPS:
        g = [s for s in sents if s[0] == label]
        out["groups"][label] = {"run": run, "sentences": len(g),
                                "bigram_reuse_pct": 100.0 * sum(s[2] for s in g) / sum(s[3] for s in g),
                                "L3": l3_gain(np.array([s[4] for s in g]), np.array([s[5] for s in g]))}
    # bins over all 320 sentence scores, with a cluster bootstrap over hobby scripts (10 per group, resampled within
    # each group): the 4 users of a script share its held-out sentences
    def bin_gains(sample):
        res = {}
        for b, _ in BINS:
            ss = [s for s in sample if bin_of(s[2], s[3]) == b]
            res[b] = (l3_gain(np.array([s[4] for s in ss]), np.array([s[5] for s in ss])) if ss else float("nan"),
                      len(ss))
        return res
    point = bin_gains(sents)
    by_script = {}
    for s in sents:
        by_script.setdefault((s[0], s[1]), []).append(s)
    keys_by_group = {lab: [k for k in by_script if k[0] == lab] for lab, _, _ in SYNTH_GROUPS}
    reps = {b: [] for b, _ in BINS}
    rng = rng_for("reuse-bins")
    for _ in range(B):
        sample = []
        for lab, keys in keys_by_group.items():
            pick = rng.integers(0, len(keys), size=len(keys))
            for i in pick:
                sample.extend(by_script[keys[i]])
        bg = bin_gains(sample)
        for b, _ in BINS:
            reps[b].append(bg[b][0])
    for b, label in BINS:
        arr = np.array(reps[b])
        arr = arr[~np.isnan(arr)]
        lo, hi = np.percentile(arr, [2.5, 97.5])
        out["bins"][b] = {"label": label, "sentences": point[b][1], "L3": point[b][0], "ci": (float(lo), float(hi))}
    # within-group contrast: sentences without vs with a shared bigram
    out["within"] = {}
    for label, _, _ in SYNTH_GROUPS:
        g = [s for s in sents if s[0] == label]
        z = [s for s in g if s[2] == 0]
        p = [s for s in g if s[2] > 0]
        out["within"][label] = {
            "n_zero": len(z), "L3_zero": l3_gain(np.array([s[4] for s in z]), np.array([s[5] for s in z])),
            "n_pos": len(p), "L3_pos": l3_gain(np.array([s[4] for s in p]), np.array([s[5] for s in p]))}
    # rank correlation (per sentence) between reuse and relative gain, with the same cluster bootstrap
    share = np.array([s[2] / s[3] for s in sents])
    rel = np.array([(s[4] - s[5]) / s[4] for s in sents])
    out["spearman"] = spearman(share, rel)
    idx_by_key = {}
    for i, s in enumerate(sents):
        idx_by_key.setdefault((s[0], s[1]), []).append(i)
    rhos = []
    rng = rng_for("reuse-spearman")
    for _ in range(2000):
        ii = []
        for lab, keys in keys_by_group.items():
            for j in rng.integers(0, len(keys), size=len(keys)):
                ii.extend(idx_by_key[keys[j]])
        ii = np.array(ii)
        rhos.append(spearman(share[ii], rel[ii]))
    out["spearman_ci"] = tuple(float(x) for x in np.percentile(rhos, [2.5, 97.5]))
    out["distinct_sentences"] = len({(s[0], s[7]) for s in sents})
    out["scripts"] = len({(s[0], s[1]) for s in sents})
    out["sentences"] = [{"group": s[0], "script": s[1], "user": s[6], "shared": s[2], "bigrams": s[3],
                         "nats_base": s[4], "nats_memory": s[5]} for s in sents]
    return out


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    def rank(a):
        vals, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
        order = a.argsort(kind="mergesort")
        r = np.empty(len(a))
        r[order] = np.arange(len(a))
        sums = np.zeros(len(vals))
        np.add.at(sums, inv, r)
        return (sums / cnt)[inv]
    return float(np.corrcoef(rank(x), rank(y))[0, 1])


# --------------------------------------------------------------------------------- L3 across user groups ----

L3_GROUPS = [  # label, kind, source, users' data file (None: real), population, role
    ("§7 users", "parts", "learn_dev_v2f", "learn_sessions.json", "synthetic", "dev"),
    ("§8", "parts", "learn_v2", "learn_sessions_v2.json", "synthetic", "test"),
    ("§9", "parts", "learn_v3_labels", "learn_sessions_v3.json", "synthetic", "test"),
    ("§10", "parts", "learn_v4_labels", "learn_sessions_v4.json", "synthetic", "test"),
    ("real dev", "probe", "probe_r15_real_dev.json", None, "real", "dev"),
    ("§11 real", "parts", "learn_real", None, "real", "test"),
    ("§12 real", "parts", "learn_real2_relevant", None, "real", "test"),
]


def l3_groups() -> list[dict]:
    out = []
    for label, kind, src, data_file, pop, role in L3_GROUPS:
        if kind == "probe":
            users = load_json(RES / "learn_probe" / src)["results"]
            b, m = user_arrays(users, probe=True)
        else:
            users = load_parts(src)
            b, m = user_arrays(users)
        cl = clusters_of(users, data_file)
        g, lo, hi = bootstrap_l3(b, m, f"L3:{src}", cl)
        out.append({"label": label, "source": src, "population": pop, "role": role, "n_users": len(users),
                    "n_clusters": len(set(cl)), "n_sentences": int(sum(len(u["held_out"]) for u in users)),
                    "n_distinct_sentences": len({json.dumps(h.get("text"), sort_keys=True)
                                                 for u in users for h in u["held_out"]}),   # real: SHA-256 per text
                    "L3": g, "ci": (lo, hi), "users_gain_pos": int(((b - m) > 0).sum())})
    return out


# ---------------------------------------------------------------------------------- probes: mixing grids ----

PROBE_GRID_SETS = [("§7 users", "probe_r14_v1.json"), ("§9 users", "probe_r14_v3.json"),
                   ("§10 users", "probe_r14_v4.json"), ("real dev users", "probe_r14_real_dev.json")]
PROBE_GRID_CITED = [("§9 users", "probe_v3.json"), ("§10 users", "probe_v4.json"),
                    ("real dev users (round 15)", "probe_r15_real_dev.json")]
APP_SETTING = "0.1/0.9/0.01"


def grid_summary(fname: str) -> dict:
    d = load_json(RES / "learn_probe" / fname)
    g = d["summary"]["grid"]
    keys = [k for k in g if k.count("/") == 2]
    best = max(keys, key=lambda k: g[k]["gain_pct"])
    worst = min(keys, key=lambda k: g[k]["gain_pct"])
    return {"file": fname, "commit": d["code_commit"][:7], "settings": len(keys),
            "app": g[APP_SETTING]["gain_pct"], "best": g[best]["gain_pct"], "best_setting": best,
            "worst": g[worst]["gain_pct"], "worst_setting": worst, "grid": {k: g[k]["gain_pct"] for k in keys}}


# ---------------------------------------------------------------------------------- probes: letter rules ----

R14 = [("real dev", "probe_r14_real_dev.json"), ("§7", "probe_r14_v1.json"), ("§9", "probe_r14_v3.json"),
       ("§10", "probe_r14_v4.json")]


def letter_rules() -> dict:
    sums = {name: load_json(RES / "learn_probe" / f)["summary"] for name, f in R14}
    commits = {load_json(RES / "learn_probe" / f)["code_commit"][:7] for _, f in R14}
    assert len(commits) == 1, commits
    rules = list(sums["real dev"]["letter_rules"])
    out = []
    for r in rules:
        row = {"rule": r}
        if r.startswith("none"):
            row["check"], row["nats"] = "none", None
        else:
            kind, nats = r.split(">")[0], float(r.split(">")[1].split("+")[0])
            row["check"], row["nats"] = kind, nats
        row["shape"] = r.endswith("+shape")
        row["stored_total"] = sum(sums[n]["letter_rules"][r]["mistakes_stored"] for n, _ in R14)
        for n, _ in R14:
            row[f"L3[{n}]"] = sums[n]["letter_rules"][r]["held_out_gain_pct"]
            row[f"stored[{n}]"] = sums[n]["letter_rules"][r]["mistakes_stored"]
        row["dropped_real"] = sums["real dev"]["letter_rules"][r]["correct_sentences_dropped_whole"]
        out.append(row)
    n_correct_real = sums["real dev"]["rules"]["R2_app"]["correct_sentences"]
    baseline = next(x for x in out if x["rule"] == "none")["stored_total"]
    admissible = [x for x in out if x["stored_total"] <= baseline]
    chosen = max(admissible, key=lambda x: x["L3[real dev]"])
    return {"commit": commits.pop(), "rules": out, "baseline_stored": baseline, "chosen": chosen["rule"],
            "n_correct_real": n_correct_real,
            "mistakes_per_set": {n: sums[n]["mistakes"] for n, _ in R14}}


def final_tradeoff() -> dict:
    """Probe round 15 (final code, real development users): what the sentence exclusion costs and buys."""
    d = load_json(RES / "learn_probe" / "probe_r15_real_dev.json")
    sm = d["summary"]
    out = {"commit": d["code_commit"][:7], "mistakes": sm["mistakes"], "stored": sm["mistakes_stored"],
           "by_wrong": sm["by_wrong"], "learnable": sm["messages_learnable"],
           "analyse_mean_s": sm["analyse_seconds_mean"], "analyse_max_s": sm["analyse_seconds_max"],
           "drift": sm["max_rewind_drift_nats"], "rules": sm["rules"]}
    return out


# --------------------------------------------------------------------------------------- fact intrusion ----

def intrusion_analysis() -> dict:
    out = {"before": [], "s12": {}}
    # §12 motivation (counted after §11 on consumed measurements; experiments/sela2_learn_eval.intrusion)
    for run, data_file in (("learn_v3_sentences", "learn_sessions_v3.json"),
                           ("learn_v4_sentences", "learn_sessions_v4.json"), ("learn_real", None)):
        users = load_parts(run)
        if data_file:
            D = users_of(data_file)
            facts_of = lambda u, D=D: D[u["id"]]["facts"]
            t_facts = D["en00"]["facts"]
        else:
            facts_of = lambda u: facts_from_note(u["facts_shown"][0], u["lang"])
            u0 = next(u for u in users if u["id"] == "en00")
            t_facts = facts_from_note(u0["facts_shown"][0], "en")
        row = {"run": run}
        for arm in ("off", "F", "FK"):
            k, n = probe_intrusion(users, facts_of, arm)
            row[arm] = (k, n)
        for arm in ("off", "facts", "knn"):
            row[f"app_{arm}"] = app_intrusions(run, arm, t_facts)
        out["before"].append(row)
    # §12 itself: both runs, recounted from the parts and compared with the summaries
    for run in ("learn_real2_relevant", "learn_real2_all"):
        s = load_summary(run)
        users = load_parts(run)
        row = {"run": run}
        for arm in ("off", "F", "FK"):
            k = s["arms"][arm]["intrusion"]
            n = s["arms"][arm]["sela_replies"]
            # recount from the per-reply field the measurement recorded (the §12 runs store it)
            k2 = sum(bool(r.get("intrusion")) for u in users for r in u["arms"][arm] if r.get("model") == "sela-2")
            assert k == k2, (run, arm, k, k2)
            row[arm] = (k, n)
        # app replies naming the taught user's facts: the per-reply field recorded during the measurement (the app
        # summary did not sum it at measurement time; docs/PREREG_SELA2.md §12.1, commit 2edd391)
        for arm in ("off", "facts", "knn"):
            a = load_json(RES / run / f"app_learn_{arm}.json")
            reps = [t for x in a["rows"] for t in x["replies"] if t.get("model") == "sela-2"]
            assert all("intrusion" in t for t in reps), (run, arm)
            row[f"app_{arm}"] = (sum(bool(t.get("intrusion")) for t in reps), len(reps))
        assert row["app_facts"][0] == s["criteria"]["L6_app_F"]["value"], run
        assert row["app_knn"][0] == s["criteria"]["L6_app_FK"]["value"], run
        row["L1_F"] = (s["arms"]["F"]["fact_used"], s["arms"]["F"]["fact_probes"])
        row["L1_FK"] = (s["arms"]["FK"]["fact_used"], s["arms"]["FK"]["fact_probes"])
        row["L1_off"] = (s["arms"]["off"]["fact_used"], s["arms"]["off"]["fact_probes"])
        # fact use by language (arm F), on the fact probes Sela-2 answered in all arms, checked against the summary
        for lg in ("en", "de"):
            pr = [(u, i) for u in users if u["lang"] == lg for i, r in enumerate(u["arms"]["off"]) if r["kind"] == "fact"
                  and all(u["arms"][a][i].get("model") == "sela-2" for a in ("off", "F", "FK"))]
            k = sum(bool(u["arms"]["F"][i].get("fact_used")) for u, i in pr)
            assert abs(round(100 * k / len(pr), 1) - s["arms"]["F"][f"fact_used_pct_{lg}"]) < 0.06, (run, lg, k, len(pr))
            row[f"L1_{lg}"] = (k, len(pr))
        assert row["L1_off"][0] == 0 and row["L1_off"][1] == row["L1_F"][1], (run, row["L1_off"])
        row["L1_en_F"], row["L1_de_F"] = s["arms"]["F"]["fact_used_pct_en"], s["arms"]["F"]["fact_used_pct_de"]
        row["L4_F"], row["L4_FK"] = s["criteria"]["L4_app_F"]["value"], s["criteria"]["L4_app_FK"]["value"]
        row["L4_off"] = app_off_problems(run)
        row["L2"] = (s["arms"]["F"]["error_copied"], s["arms"]["FK"]["error_copied"])
        row["L2b"] = (s["arms"]["F"]["role_confusion"], s["arms"]["FK"]["role_confusion"])
        row["coverage"] = s["criteria"]["L1_coverage"]["value"]
        row["L5"] = s["criteria"]["L5_speed"]["value"]
        row["L3"] = s["criteria"]["L3_memory_bpb"]["value"]
        row["decision"] = s["decision"]
        out["s12"][run] = row
    return out


# ------------------------------------------------------------------------------------------------ figures ----

PDF_META = {"CreationDate": None, "Creator": None, "Producer": None}   # byte-identical reruns
C_BLUE, C_ORANGE, C_AQUA = "#2a78d6", "#eb6834", "#1baf7a"     # validated categorical slots 1-3 (dataviz palette)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d3"


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
        "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
        "legend.fontsize": 7, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
        "ytick.color": INK2, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "figure.dpi": 150, "legend.frameon": False,
    })
    return plt


def fig_l3_and_reuse(plt, groups: list[dict], reuse: dict) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.6, 2.55), gridspec_kw={"width_ratios": [1.35, 1.0]})
    # (a) L3 per user group
    xs = np.arange(len(groups))
    reuse_pct = {"§7 users": reuse["groups"]["§7"]["bigram_reuse_pct"],
                 "§8": reuse["groups"]["§8"]["bigram_reuse_pct"],
                 "§9": reuse["groups"]["§9"]["bigram_reuse_pct"],
                 "§10": reuse["groups"]["§10"]["bigram_reuse_pct"]}
    ax1.axhline(0, color=INK2, lw=0.6)
    ax1.axhline(1.0, color=INK2, lw=0.8, ls=(0, (4, 3)))
    ax1.text(3.52, 1.12, "threshold\n1 %", ha="center", va="bottom", fontsize=6.3, color=INK2, linespacing=0.95)
    for x, g in zip(xs, groups):
        col = C_BLUE if g["population"] == "synthetic" else C_ORANGE
        lo, hi = g["ci"]
        ax1.plot([x, x], [lo, hi], color=col, lw=1.4, solid_capstyle="round", zorder=2)
        face = "white" if g["role"] == "dev" else col
        ax1.plot(x, g["L3"], "o", ms=6, mfc=face, mec=col, mew=1.5, zorder=3)
        ax1.text(x + 0.14, g["L3"], f"{g['L3']:+.2f}", fontsize=6.5, va="center", ha="left", color=INK)
    labels = []
    for g in groups:
        r = reuse_pct.get(g["label"])
        if g["label"] == "real dev":
            sub = "(12.9 %$^{\\dagger}$)"
        elif r is None:
            sub = "(n/a)"
        else:
            sub = f"({r:.1f} %)"
        labels.append(f"{g['label']}\n{sub}")
    ax1.set_xticks(xs)
    ax1.set_xticklabels(labels, fontsize=6.6)
    ax1.set_xlim(-0.5, len(groups) - 0.4)
    ax1.set_ylabel("held-out gain L3 (% of bits per byte)")
    ax1.set_title("(a) Memory gain by user group (40 users each)", loc="left")
    ax1.yaxis.grid(True, color=GRID, lw=0.5)
    ax1.set_axisbelow(True)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", mfc=C_BLUE, mec=C_BLUE, ms=5, label="synthetic, test"),
         Line2D([], [], marker="o", ls="", mfc="white", mec=C_BLUE, mew=1.4, ms=5, label="synthetic, development"),
         Line2D([], [], marker="o", ls="", mfc=C_ORANGE, mec=C_ORANGE, ms=5, label="real (WildChat), test"),
         Line2D([], [], marker="o", ls="", mfc="white", mec=C_ORANGE, mew=1.4, ms=5,
                label="real, development (probe)")]
    ax1.legend(handles=h, loc="upper center", ncol=2, fontsize=6.3, handletextpad=0.3, columnspacing=0.8,
               bbox_to_anchor=(0.5, 1.0))
    ymax = max(g["ci"][1] for g in groups)
    ax1.set_ylim(min(-1.0, min(g["ci"][0] for g in groups) - 0.3), ymax + 1.6)
    # (b) dose-response
    bins = [reuse["bins"][b] for b, _ in BINS]
    xb = np.arange(len(bins))
    ax2.axhline(0, color=INK2, lw=0.6)
    for x, bb in zip(xb, bins):
        lo, hi = bb["ci"]
        ax2.plot([x, x], [lo, hi], color=C_BLUE, lw=1.4, solid_capstyle="round", zorder=2)
        ax2.plot(x, bb["L3"], "s", ms=6, mfc=C_BLUE, mec=C_BLUE, zorder=3)
        ax2.text(x + 0.12, bb["L3"], f"{bb['L3']:+.2f}", fontsize=6.5, va="center", ha="left", color=INK)
    ax2.set_xticks(xb)
    ax2.set_xticklabels([f"{lab}\n$n={bb['sentences']}$".replace("no shared bigram", "none")
                         for (b, lab), bb in zip(BINS, bins)], fontsize=6.6)
    ax2.set_xlim(-0.5, len(bins) - 0.3)
    ax2.set_xlabel("share of a held-out sentence's bigrams already in the user's messages", fontsize=7)
    ax2.set_ylabel("L3 (%)")
    ax2.set_title("(b) Gain by lexical reuse (320 synthetic sentences)", loc="left")
    ax2.yaxis.grid(True, color=GRID, lw=0.5)
    ax2.set_axisbelow(True)
    fig.tight_layout(w_pad=1.2)
    fig.savefig(OUT_FIG / "fig_l3_reuse.pdf", metadata=PDF_META)
    plt.close(fig)


def fig_letter_rules(plt, lr: dict) -> None:
    rules = lr["rules"]
    col = {"none": C_BLUE, "alone": C_ORANGE, "frame": C_AQUA}
    lab = {"none": "no outside check", "alone": "word alone", "frame": "word in a fixed sentence"}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.6, 2.35))
    base = lr["baseline_stored"]
    for ax, ykey, ylabel, title in (
            (ax1, "dropped_real", f"correct real-dev sentences dropped (of {lr['n_correct_real']})",
             "(a) False alarms vs. missed mistakes"),
            (ax2, "L3[real dev]", "L3 on real development users (%)", "(b) Memory gain vs. missed mistakes")):
        ax.axvspan(ax.get_xlim()[0] if False else 0, base + 0.5, color="#eeeeea", zorder=0, lw=0)
        ax.axvline(base + 0.5, color=INK2, lw=0.7, ls=(0, (4, 3)))
        # small deterministic offsets so that rules with identical values stay visible
        seen = {}
        for r in rules:
            key = (r["stored_total"], round(r[ykey], 3))
            k = seen.get(key, 0)
            seen[key] = k + 1
            dx = (k % 4) * 0.9 - 1.35 * (k > 0)
            mark = dict(marker="o", ms=5.5, mew=1.3, mec=col[r["check"]],
                        mfc=col[r["check"]] if r["shape"] else "white")
            if r["rule"] == lr["chosen"]:
                ax.plot(r["stored_total"] + dx, r[ykey], marker="*", ms=12, mfc=col["none"], mec=INK, mew=0.6,
                        zorder=5, ls="")
            else:
                ax.plot(r["stored_total"] + dx, r[ykey], ls="", zorder=4, **mark)
        ax.set_xlabel("injected mistakes stored in the memory (4 user sets, 480 injected)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left")
        ax.yaxis.grid(True, color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_xlim(38, 86)
        ax.text(base + 0.1, 0.03, "admissible\n$\\leq$%d" % base, transform=ax.get_xaxis_transform(), ha="right",
                va="bottom", fontsize=6.1, color=INK2, linespacing=0.95)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", mfc=col[k], mec=col[k], ms=5, label=lab[k]) for k in ("none", "alone", "frame")]
    h += [Line2D([], [], marker="o", ls="", mfc="white", mec=INK2, mew=1.2, ms=5, label="without shape rule"),
          Line2D([], [], marker="o", ls="", mfc=INK2, mec=INK2, ms=5, label="with shape rule"),
          Line2D([], [], marker="*", ls="", mfc=col["none"], mec=INK, mew=0.6, ms=10, label="chosen (by the fixed rule)")]
    fig.legend(handles=h, loc="lower center", ncol=6, fontsize=6.3, handletextpad=0.2, columnspacing=0.9,
               bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=1.5)
    fig.savefig(OUT_FIG / "fig_letter_rules.pdf", metadata=PDF_META)
    plt.close(fig)


def fig_grids(plt, grids: list[tuple[str, dict]]) -> None:
    lams = [0.05, 0.1, 0.2, 0.3]
    floors = [0.7, 0.75, 0.8, 0.85, 0.9]
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    cmap = LinearSegmentedColormap.from_list("div", ["#c7362f", "#e88b7d", "#f0efec", "#86b6ef", "#1c5cab"])
    vmax = max(max(abs(v) for v in g["grid"].values()) for _, g in grids)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    fig, axes = plt.subplots(1, len(grids), figsize=(6.6, 1.95), sharey=True)
    for ax, (name, g) in zip(axes, grids):
        M = np.array([[g["grid"][f"{lam}/{fl}/0.01"] for lam in lams] for fl in floors])
        im = ax.imshow(M, cmap=cmap, norm=norm, origin="lower", aspect="auto")
        for i, fl in enumerate(floors):
            for j, lam in enumerate(lams):
                v = M[i, j]
                ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=5.6,
                        color="white" if abs(v) > 0.6 * vmax else INK)
                if abs(lam - 0.1) < 1e-9 and abs(fl - 0.9) < 1e-9:
                    ax.add_patch(__import__("matplotlib").patches.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                                                           lw=1.2, ec=INK))
        ax.set_xticks(range(len(lams)))
        ax.set_xticklabels([str(x) for x in lams])
        ax.set_yticks(range(len(floors)))
        ax.set_yticklabels([str(x) for x in floors])
        ax.set_xlabel(r"largest share $\lambda_{\max}$")
        ax.set_title(name, loc="left", fontsize=7.5)
        for sp in ax.spines.values():
            sp.set_visible(False)
    axes[0].set_ylabel("similarity floor")
    cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02)
    cb.set_label("L3 (%)", fontsize=7)
    cb.ax.tick_params(labelsize=6.5)
    fig.savefig(OUT_FIG / "fig_grids.pdf", metadata=PDF_META)
    plt.close(fig)


# ----------------------------------------------------------------------------------------- LaTeX output ----

_TEX = {"§": r"\S{}", "–": "--", "—": "---", "·": r"\textperiodcentered{}", "≤": r"$\leq$", "≥": r"$\geq$",
        "λ": r"$\lambda$", "τ": r"$\tau$", "ä": r"\"a", "ö": r"\"o", "ü": r"\"u", "ß": r"\ss{}", "−": "-"}


def write_tex(path: Path, text: str) -> None:
    """Generated LaTeX is plain ASCII (the paper compiles with pdfLaTeX as well as XeLaTeX)."""
    for k, v in _TEX.items():
        text = text.replace(k, v)
    bad = sorted({c for c in text if ord(c) > 127})
    assert not bad, (path.name, bad)
    path.write_text(text, encoding="ascii")


def pct(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}"


def ci(lo: float, hi: float, nd: int = 1) -> str:
    return f"[{lo:.{nd}f}, {hi:.{nd}f}]"


def signed(x: float, nd: int = 2) -> str:
    s = f"{x:+.{nd}f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


DECISION = {"s7": "A+B off, C off", "s8": "A+B on, C on", "s9a": "C off again", "s9b": "not adopted$^{\\dagger}$",
            "s10a": "–", "s10b": "sentences adopted", "s11": "C on", "s12a": "filter adopted", "s12b": "comparison"}


def write_tables(reg: list[dict], groups: list[dict], reuse: dict, grids_cited: list[tuple[str, dict]],
                 grids_r14: list[tuple[str, dict]], lr: dict, intr: dict, dev: list[dict]) -> None:
    R = {r["key"]: r for r in reg}
    # --- main table: the registered measurements
    lines = []
    for r in reg:
        l3 = f"{signed(r['L3'])} {ci(*r['L3_ci'], nd=2)}".replace("[-", "[$-$").replace(", -", ", $-$")
        l1 = f"{pct(r['L1'])} {ci(*r['L1_ci'])}"
        l6 = f"{pct(r['L6_F'])} / {pct(r['L6_FK'])}" if "L6_F" in r else "–"
        lines.append(" & ".join([
            r["section"] + ("" if r["key"] not in ("s9a", "s10a", "s12a") else ""),
            {"s7": "v1", "s8": "v2", "s9a": "v3 · labels", "s9b": "v3 · sentences", "s10a": "v4 · labels",
             "s10b": "v4 · sentences", "s11": "real · test", "s12a": "real · test2, filter",
             "s12b": "real · test2, all"}[r["key"]],
            l1, f"{r['L2_F']} / {r['L2_FK']}", f"{r['L2b_F']} / {r['L2b_FK']}", l3,
            f"{r['L4_F']} / {r['L4_FK']} ({r['L4_off']})", fmt(r["L5"], 3) if r["L5"] is not None else "–", l6,
            DECISION[r["key"]],
        ]) + r" \\")
    write_tex(OUT_GEN / "tab_registered.tex", "\n".join(lines) + "\n")
    # --- error fate
    lines = []
    for key, label in (("s7", "§7 (v1)"), ("s8", "§8 (v2)"), ("s9a", "§9 (v3)"), ("s10a", "§10 (v4)"),
                       ("s11", "§11 (real test)"), ("s12a", "§12 (real test2)")):
        r = R[key]
        e = r["errors"]
        tot = sum(e.values())
        assert tot == 120, (key, tot)
        copied = f"{r['L2_FK']}"
        twin = {"s9a": "s9b", "s10a": "s10b", "s12a": "s12b"}.get(key)
        if twin:  # both runs of a paired measurement teach the same memory; only the replies differ
            assert R[twin]["errors"] == e, (key, twin)
            copied = f"{r['L2_FK']} / {R[twin]['L2_FK']}"
        lines.append(f"{label} & {e['spell-checked']} & {e['not learned']} & {e['filtered']} & {e['stored']} & "
                     f"{copied} \\\\")
    write_tex(OUT_GEN / "tab_errors.tex", "\n".join(lines) + "\n")
    # --- dose-response
    lines = []
    for b, label in BINS:
        x = reuse["bins"][b]
        lines.append(f"{label} & {x['sentences']} & {signed(x['L3'])} & "
                     f"{ci(*x['ci'], nd=2).replace('[-', '[$-$').replace(', -', ', $-$')} \\\\")
    write_tex(OUT_GEN / "tab_reuse.tex", "\n".join(lines) + "\n")
    # --- mixing grid (cited probes)
    lines = []
    for name, g in grids_cited:
        bs = g["best_setting"].split("/")
        ws = g["worst_setting"].split("/")
        lines.append(f"{name} & \\texttt{{{g['file'].replace('_', chr(92) + '_')}}} & {signed(g['app'])} & "
                     f"{signed(g['best'])} ({bs[0]}, {bs[1]}, {bs[2]}) & {signed(g['worst'])} ({ws[0]}, {ws[1]}, "
                     f"{ws[2]}) \\\\")
    write_tex(OUT_GEN / "tab_grid.tex", "\n".join(lines) + "\n")
    # --- letter rules (all 18, appendix) and the four rows of the main text
    def rule_label(x):
        if x["check"] == "none":
            s = "no outside check"
        else:
            s = ("word alone" if x["check"] == "alone" else "fixed sentence") + f" $>{x['nats']:.2f}$ nats"
        return s + (" + shape rule" if x["shape"] else "")
    lines = []
    for x in lr["rules"]:
        star = r"$^{\star}$" if x["rule"] == lr["chosen"] else ""
        lines.append(f"{rule_label(x)}{star} & {pct(x['L3[real dev]'], 2)} & {pct(x['L3[§7]'], 2)} & "
                     f"{pct(x['L3[§9]'], 2)} & {pct(x['L3[§10]'], 2)} & {x['stored_total']} & "
                     f"{x['dropped_real']} \\\\")
    write_tex(OUT_GEN / "tab_letter_all.tex", "\n".join(lines) + "\n")
    pick = ["none", "none+shape", "alone>2.08", "frame>1.50+shape"]
    lines = []
    for rname in pick:
        x = next(y for y in lr["rules"] if y["rule"] == rname)
        name = {"none": "previous rule, no outside check", "none+shape": r"\textbf{+ shape rule (chosen)}",
                "alone>2.08": r"word alone $>2.08$ nats (earlier fix)",
                "frame>1.50+shape": r"fixed sentence $>1.5$ nats + shape rule"}[rname]
        lines.append(f"{name} & {pct(x['L3[real dev]'], 2)} & {pct(x['L3[§7]'], 2)} & {x['stored_total']} & "
                     f"{x['dropped_real']} \\\\")
    write_tex(OUT_GEN / "tab_letter.tex", "\n".join(lines) + "\n")
    # --- intrusion before §12 (motivation, recounted)
    lines = []
    for row in intr["before"]:
        name = {"learn_v3_sentences": r"§9 sentences (\texttt{learn\_v3\_sentences})",
                "learn_v4_sentences": r"§10 sentences (\texttt{learn\_v4\_sentences})",
                "learn_real": r"§11 real test (\texttt{learn\_real})"}[row["run"]]
        k, n = row["F"]
        kk, nn = row["FK"]
        lines.append(f"{name} & {row['off'][0]}/{row['off'][1]} & {k}/{n} ({pct(100 * k / n)}) & "
                     f"{kk}/{nn} ({pct(100 * kk / nn)}) & {row['app_facts'][0]} / {row['app_knn'][0]} of "
                     f"{row['app_facts'][1]} \\\\")
    write_tex(OUT_GEN / "tab_intrusion_before.tex", "\n".join(lines) + "\n")
    # --- §12 comparison
    a, b = intr["s12"]["learn_real2_relevant"], intr["s12"]["learn_real2_all"]
    def frac(t):
        return f"{t[0]}/{t[1]} ({pct(100 * t[0] / t[1])})"
    def wil(t):
        lo, hi = wilson(*t)
        return f"[{lo:.1f}, {hi:.1f}]"
    rows = [
        (r"L1 fact use, F (off: 0 in both runs)", f"{frac(a['L1_F'])} {wil(a['L1_F'])}",
         f"{frac(b['L1_F'])} {wil(b['L1_F'])}", r"F$-$off $\geq +15$"),
        (r"\quad with C (FK)", frac(a["L1_FK"]), frac(b["L1_FK"]), "–"),
        (r"L6 unasked facts in probe replies, F", f"{frac(a['F'])} {wil(a['F'])}", f"{frac(b['F'])} {wil(b['F'])}",
         r"$\leq 10\,\%$"),
        (r"\quad with C (FK)", f"{frac(a['FK'])} {wil(a['FK'])}", f"{frac(b['FK'])} {wil(b['FK'])}", "–"),
        (r"L6 app replies naming the taught user's facts, F", f"{a['app_facts'][0]} of {a['app_facts'][1]}",
         f"{b['app_facts'][0]} of {b['app_facts'][1]}", r"$\leq 3$"),
        (r"\quad with C (FK)", f"{a['app_knn'][0]} of {a['app_knn'][1]}", f"{b['app_knn'][0]} of {b['app_knn'][1]}",
         "–"),
        (r"L2 copied mistakes, F / FK", f"{a['L2'][0]} / {a['L2'][1]}", f"{b['L2'][0]} / {b['L2'][1]}",
         r"$\leq$ off $+2$"),
        (r"L2b user fact claimed as own, F / FK", f"{a['L2b'][0]} / {a['L2b'][1]}", f"{b['L2b'][0]} / {b['L2b'][1]}",
         r"$\leq$ off $+2$"),
        (r"L4 app prompts with a problem, F / FK (off)", f"{a['L4_F']} / {a['L4_FK']} ({a['L4_off']})",
         f"{b['L4_F']} / {b['L4_FK']} ({b['L4_off']})", r"$\leq$ off $+2$"),
    ]
    write_tex(OUT_GEN / "tab_s12.tex", "\n".join(" & ".join(x) + r" \\" for x in rows) + "\n")
    # --- development runs (appendix)
    lines = []
    for d in dev:
        lines.append(f"\\texttt{{{d['run'].replace('learn_dev_', '')}}} & {d['commit']} & {pct(d['L1'])} & "
                     f"{d['L2_F']} / {d['L2_FK']} & {d['L2b_F']} / {d['L2b_FK']} & {signed(d['L3'])} & "
                     f"{d['L4_F']} / {d['L4_FK']} ({d['L4_off']}) & "
                     f"{fmt(d['L5'], 3) if d['L5'] is not None else '–'}{d['L5_note']} & {d['stored']} \\\\")
    write_tex(OUT_GEN / "tab_dev.tex", "\n".join(lines) + "\n")


# the commit that added each development run's results (git log --oneline -- results/sela2/learn_dev_v2*)
DEV_COMMITS = {"learn_dev_v2a": "667b7e7", "learn_dev_v2b": "bff5750", "learn_dev_v2c": "0b6afaf",
               "learn_dev_v2d": "23a77e6", "learn_dev_v2e": "6b78c5a", "learn_dev_v2f": "f8300cb",
               "learn_dev_v2g": "3f69535", "learn_dev_v2h": "0bc896b"}


def dev_runs() -> list[dict]:
    out = []
    for run in DEV_RUNS:
        s = load_summary(run)
        c, a = s["criteria"], s["arms"]
        out.append({"run": run, "commit": DEV_COMMITS[run],
                    "L1": c["L1_fact_use"]["value"], "L2_F": a["F"]["error_copied"], "L2_FK": a["FK"]["error_copied"],
                    "L2b_F": a["F"]["role_confusion"], "L2b_FK": a["FK"]["role_confusion"],
                    "L3": c["L3_memory_bpb"]["value"], "L4_F": c["L4_app_F"]["value"],
                    "L4_FK": c["L4_app_FK"]["value"], "L4_off": app_off_problems(run),
                    "L5": c["L5_speed"]["value"], "L5_note": "$^{a}$" if run == "learn_dev_v2a" else "",
                    "stored": s["errors_caught"]["stored"]})
    return out


def write_numbers(reg, groups, reuse, grids_cited, grids_r14, lr, intr) -> None:
    R = {r["key"]: r for r in reg}
    for r in reg:
        k = r["key"]
        stat(f"L3.{k}", signed(r["L3"]))
        stat(f"L3ci.{k}", ci(*r["L3_ci"], nd=2).replace("[-", "[$-$").replace(", -", ", $-$"))
        stat(f"L1.{k}", pct(r["L1"]))
        stat(f"L1ci.{k}", ci(*r["L1_ci"]))
        stat(f"L1k.{k}", f"{r['L1_k']}/{r['fact_probes']}")
        stat(f"L5.{k}", fmt(r["L5"], 3))
        stat(f"pos.{k}", str(r["users_gain_pos"]))
    # memory entries per user after the eight teaching messages (mean per registered run; FK arm's memory)
    ent = {r["key"]: float(np.mean([u["knn_entries"] for u in load_parts(r["run"])])) for r in reg}
    stat("entries.s7", f"{ent['s7']:.0f}")
    later = [v for k, v in ent.items() if k != "s7"]
    stat("entries.min", f"{min(later):.0f}")
    stat("entries.max", f"{max(later):.0f}")
    # writing speed of the int8 model in the app measurements (arm F; §7 recorded a different speed measure)
    tps = [r["L5_tokps_F"] for r in reg if r.get("L5_tokps_F") is not None]
    assert len(tps) == len(reg) - 1, tps
    stat("tokps.min", f"{min(tps):.1f}")
    stat("tokps.max", f"{max(tps):.1f}")
    # synthetic groups: how much wider the interval over hobby scripts is than one over users (treated as independent)
    ratios = [(r["L3_ci"][1] - r["L3_ci"][0]) / (r["L3_ci_by_user"][1] - r["L3_ci_by_user"][0])
              for r in reg if r["users"] == "synthetic"]
    stat("ciratio.min", f"{min(ratios):.1f}")
    stat("ciratio.max", f"{max(ratios):.1f}")
    # how far the Wilson interval of L1 (replies independent) lies from a bootstrap over users, at either end
    stat("l1boot.maxdiff", f"{max(max(abs(r['L1_ci'][0] - r['L1_ci_boot'][0]), abs(r['L1_ci'][1] - r['L1_ci_boot'][1])) for r in reg):.1f}")
    for g in groups:
        k = {"§7 users": "dev7", "§8": "g8", "§9": "g9", "§10": "g10", "real dev": "rdev", "§11 real": "g11",
             "§12 real": "g12"}[g["label"]]
        stat(f"G.{k}", signed(g["L3"]))
        stat(f"Gci.{k}", ci(*g["ci"], nd=2).replace("[-", "[$-$").replace(", -", ", $-$"))
        stat(f"Gpos.{k}", f"{g['users_gain_pos']}/{g['n_users']}")
    for lab in ("§7", "§8", "§9", "§10"):
        k = {"§7": "s7", "§8": "s8", "§9": "s9", "§10": "s10"}[lab]
        stat(f"reuse.{k}", pct(reuse["groups"][lab]["bigram_reuse_pct"]))
        w = reuse["within"][lab]
        stat(f"wz.{k}", signed(w["L3_zero"]))
        stat(f"wzn.{k}", str(w["n_zero"]))
        stat(f"wp.{k}", signed(w["L3_pos"]))
        stat(f"wpn.{k}", str(w["n_pos"]))
    for b, _ in BINS:
        x = reuse["bins"][b]
        stat(f"bin.{b}", signed(x["L3"]))
        stat(f"binci.{b}", ci(*x["ci"], nd=2).replace("[-", "[$-$").replace(", -", ", $-$"))
        stat(f"binn.{b}", str(x["sentences"]))
    stat("rho", f"{reuse['spearman']:.2f}")
    stat("rhoci", ci(*reuse["spearman_ci"], nd=2))
    for name, g in grids_cited:
        k = {"§9 users": "g9", "§10 users": "g10", "real dev users (round 15)": "rdev"}[name]
        stat(f"grid.app.{k}", signed(g["app"]))
        stat(f"grid.best.{k}", signed(g["best"]))
        stat(f"grid.worst.{k}", signed(g["worst"]))
    stat("lr.baseline", str(lr["baseline_stored"]))
    ch = next(x for x in lr["rules"] if x["rule"] == lr["chosen"])
    stat("lr.chosen.L3", pct(ch["L3[real dev]"], 2))
    stat("lr.chosen.dropped", str(ch["dropped_real"]))
    stat("lr.ncorrect", str(lr["n_correct_real"]))
    outside = [x for x in lr["rules"] if x["check"] != "none"]
    stat("lr.outside.minstored", str(min(x["stored_total"] for x in outside)))
    stat("lr.outside.maxstored", str(max(x["stored_total"] for x in outside)))
    for row in intr["before"]:
        k = {"learn_v3_sentences": "v3s", "learn_v4_sentences": "v4s", "learn_real": "real"}[row["run"]]
        kk, n = row["F"]
        stat(f"intr.{k}", pct(100 * kk / n))
        stat(f"intrk.{k}", f"{kk}/{n}")
        lo, hi = wilson(kk, n)
        stat(f"intrci.{k}", ci(lo, hi))
        stat(f"intrapp.{k}", f"{row['app_facts'][0]}")
        stat(f"intrappk.{k}", f"{row['app_knn'][0]}")
    a, b = intr["s12"]["learn_real2_relevant"], intr["s12"]["learn_real2_all"]
    for tag, x in (("on", a), ("off", b)):
        for arm in ("F", "FK"):
            kk, n = x[arm]
            stat(f"s12.{tag}.{arm}", pct(100 * kk / n))
            stat(f"s12k.{tag}.{arm}", f"{kk}/{n}")
            stat(f"s12ci.{tag}.{arm}", ci(*wilson(kk, n)))
        stat(f"s12.app.{tag}.F", str(x["app_facts"][0]))
        stat(f"s12.app.{tag}.FK", str(x["app_knn"][0]))
        stat(f"s12.L1.{tag}", pct(100 * x["L1_F"][0] / x["L1_F"][1]))
        stat(f"s12.L1k.{tag}", f"{x['L1_F'][0]}/{x['L1_F'][1]}")
        for lg in ("en", "de"):
            stat(f"s12.L1{lg}.{tag}", f"{x[f'L1_{lg}'][0]}")
            stat(f"s12.L1{lg}n", f"{x[f'L1_{lg}'][1]}")
        stat(f"s12.L1ci.{tag}", ci(*wilson(*x["L1_F"])))
    # error copies with Wilson intervals (one example used in the text: §11 FK)
    r = R["s11"]
    stat("s11.L2FK.ci", ci(*wilson(r["L2_FK"], r["replies_per_arm"]), nd=2))
    lines = ["% generated by paper/make_figures.py – do not edit by hand",
             r"\makeatletter",
             r"\newcommand{\stat}[1]{\ifcsname stat@#1\endcsname\csname stat@#1\endcsname\else"
             r"\textbf{\textcolor{red}{??#1??}}\fi}"]
    for k, v in sorted(STATS.items()):
        lines.append(rf"\expandafter\def\csname stat@{k}\endcsname{{{v}}}")
    lines.append(r"\makeatother")
    write_tex(OUT_GEN / "numbers.tex", "\n".join(lines) + "\n")


def main() -> None:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    OUT_GEN.mkdir(parents=True, exist_ok=True)
    reg = registered_measurements()
    groups = l3_groups()
    reuse = lexical_reuse()
    grids_cited = [(name, grid_summary(f)) for name, f in PROBE_GRID_CITED]
    grids_r14 = [(name, grid_summary(f)) for name, f in PROBE_GRID_SETS]
    lr = letter_rules()
    intr = intrusion_analysis()
    dev = dev_runs()
    ft = final_tradeoff()
    for rule in ("R0_none", "R1_word_check", "R2_app"):
        x = ft["rules"][rule]
        stat(f"r15.{rule}.L3", pct(x["held_out_gain_pct"], 2))
        stat(f"r15.{rule}.dropped", f"{x['correct_sentences_dropped_whole']}/{x['correct_sentences']}")
        stat(f"r15.{rule}.errpart", f"{x['error_sentences_partly_learned']}/{x['error_sentences']}")
        stat(f"r15.{rule}.tok", pct(x["correct_tokens_learned_pct"]))
    stat("r15.stored", f"{ft['stored']}/{ft['mistakes']}")
    # by language: the wrong forms of each language, from the synthetic sets (the real users use the same list)
    lang_of = {}
    for f in sorted(glob.glob(str(REPO / "data" / "sela2" / "learn_sessions*.json"))):
        if "real" in Path(f).name:
            continue
        for u in load_json(Path(f))["users"]:
            for e in u["errors"]:
                assert lang_of.setdefault(e["wrong"], u["lang"]) == u["lang"], e
    by_lang = {"en": [0, 0], "de": [0, 0]}
    for w, x in ft["by_wrong"].items():
        by_lang[lang_of[w]][0] += x["stored"]
        by_lang[lang_of[w]][1] += x["n"]
    assert sum(v[0] for v in by_lang.values()) == ft["stored"] and sum(v[1] for v in by_lang.values()) == ft["mistakes"]
    for lg, (k, n) in by_lang.items():
        stat(f"r15.stored.{lg}", f"{k}")
        stat(f"r15.n.{lg}", f"{n}")
    en_stored = sorted(w for w, x in ft["by_wrong"].items() if lang_of[w] == "en" and x["stored"])
    stat("r15.en.forms", ", ".join(r"\emph{" + w + "}" for w in en_stored))
    stat("r15.learnable", f"{ft['learnable'][0]}/{ft['learnable'][1]}")
    stat("r15.analyse.mean", pct(ft["analyse_mean_s"]))
    stat("r15.analyse.max", pct(ft["analyse_max_s"]))
    stat("r15.drift", str(ft["drift"]))
    JSON_OUT["final_tradeoff"] = ft
    plt = setup_matplotlib()
    fig_l3_and_reuse(plt, groups, reuse)
    fig_letter_rules(plt, lr)
    fig_grids(plt, grids_r14)
    write_tables(reg, groups, reuse, grids_cited, grids_r14, lr, intr, dev)
    write_numbers(reg, groups, reuse, grids_cited, grids_r14, lr, intr)
    JSON_OUT.update({"bootstrap_replicates": B, "seed": SEED, "registered": reg, "l3_groups": groups,
                     "reuse": {k: v for k, v in reuse.items() if k != "sentences"},
                     "grids_cited": dict(grids_cited), "grids_r14": dict(grids_r14), "letter_rules": lr,
                     "intrusion": intr, "dev_runs": dev, "stats": STATS})
    (OUT_GEN / "stats.json").write_text(json.dumps(JSON_OUT, indent=1, ensure_ascii=False, default=str) + "\n",
                                       encoding="utf-8")
    print(f"wrote {len(list(OUT_FIG.glob('*.pdf')))} figures, {len(STATS)} numbers, tables in {OUT_GEN}")


if __name__ == "__main__":
    main()
