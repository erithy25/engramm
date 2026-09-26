"""P6 texts and P5 writing speed (docs/PREREG_LM.md §8).

200 prompts: the first 16 tokens of the first 200 near-duplicate-filtered test
documents in split-hash order. ENGRAMM-LM and KN-5 each continue every prompt
with 100 tokens under the registered decoding (temperature 0.9, top-p 0.95,
no repeated 4-gram, quotation cap 32, seed 42). Writes the pairs, a blind
judging file (A/B order randomised per prompt and also swapped), the human
panel form (60 pairs), and the writing speed with and without provenance.

    python -m experiments.lm_generate --scale main --seed 42 --tau-index 1 --beta-index 0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time

import numpy as np

from data.lm_corpus import _split_hash
from engramm.lm.generate import Decoding, generate, longest_copied_run
from engramm.repro import git_revision, peak_rss_mb
from experiments.lm_common import RESULTS_DIR, load_split, write_record
from experiments.lm_final_model import assemble, fitted_mixture, kn_only, null_only
from experiments.lm_mix import dedup_keep

N_PROMPTS, PROMPT_TOKENS, GEN_TOKENS, PANEL = 200, 16, 100, 60


def prompts(tok, split: str = "test", limit: int = 1000):
    test = load_split(split)
    keep = dedup_keep(split, test.n_docs)
    order = sorted((i for i in range(test.n_docs) if keep[i]),
                   key=lambda i: _split_hash(*test.doc_keys[i]))
    out = []
    for i in order:
        ids = test.doc_tokens(i)
        if len(ids) < PROMPT_TOKENS + 20:
            continue
        out.append({"doc": test.doc_keys[i], "prompt": tok.decode(ids[:PROMPT_TOKENS])})
        if len(out) == limit:
            break
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="main")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tau-index", type=int, required=True)
    ap.add_argument("--beta-index", type=int, required=True)
    ap.add_argument("--n", type=int, default=N_PROMPTS)
    ap.add_argument("--split", default="test")
    ap.add_argument("--skip", type=int, default=0, help="skip the first N prompts of the ordered list")
    ap.add_argument("--cache", default="document", help="exploratory: document | prompt | off")
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--tag", default="", help="exploratory runs: suffix for all output files")
    ap.add_argument("--baseline", choices=("kn5", "null"), default="kn5",
                    help="exploratory: the system ENGRAMM-LM is compared with (stored under the key kn5)")
    args = ap.parse_args()
    sfx = f"_{args.tag}" if args.tag else ""
    git_state, t0 = git_revision(), time.time()
    full = assemble(args.scale, args.seed, fitted_mixture(args.scale, args.seed, args.tau_index, args.beta_index))
    kn = kn_only(full) if args.baseline == "kn5" else null_only(full, args.scale)
    dec = Decoding(top_p=args.top_p, cache=args.cache)
    ps = prompts(full.tok, args.split)[args.skip:args.skip + args.n]
    rows, speed = [], {"engramm": [], "kn5": []}
    for j, p in enumerate(ps):
        row = dict(p)
        for name, m in (("engramm", full), ("kn5", kn)):
            ts = time.time()
            g = generate(m, p["prompt"], GEN_TOKENS, seed=42, dec=dec)
            speed[name].append((len(g.ids), time.time() - ts))
            row[name] = g.text
            row[name + "_tokens"] = len(g.ids)
            row[name + "_longest_copy"] = longest_copied_run(full, g.ids)
        rows.append(row)
        if j % 10 == 0:
            print(j, json.dumps({k: row[k] for k in ("prompt", "engramm")}, ensure_ascii=False)[:300], flush=True)
    # speed with provenance (why for every token) on 10 prompts
    tw = time.time()
    n_expl = 0
    for p in ps[:10]:
        g = generate(full, p["prompt"], 50, seed=42, dec=dec, explain=True)
        n_expl += len(g.ids)
    explain_tps = n_expl / (time.time() - tw)
    (RESULTS_DIR / f"p6_generations{sfx}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")

    # blind judging items: both orders, order of first presentation from a hash of the prompt
    items = []
    for k, r in enumerate(rows):
        first_is_engramm = hashlib.sha256(r["prompt"].encode()).digest()[0] & 1
        for swap in (0, 1):
            e_first = bool(first_is_engramm ^ swap)
            a, b = (r["engramm"], r["kn5"]) if e_first else (r["kn5"], r["engramm"])
            items.append({"item": f"{k}-{swap}", "prompt": r["prompt"], "A": a, "B": b,
                          "engramm_is": "A" if e_first else "B"})
    (RESULTS_DIR / f"p6_judge_items{sfx}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n")
    lines = ["# ENGRAMM-LM — Lesebogen für das menschliche Panel (P6)", "",
             "Für jedes Paar: Welche Fortsetzung ist das bessere Englisch (flüssig, sinnvoll, beim Thema)? "
             "Kreuzen Sie A, B oder = an. Die Zuordnung der Systeme ist verdeckt "
             "(Schlüssel: `results/lm/p6_judge_items.json`, Feld `engramm_is`, Varianten `-0`).", ""]
    for it in [i for i in items if i["item"].endswith("-0")][:PANEL]:
        lines += [f"## Paar {it['item']}", "", f"**Anfang:** {it['prompt']}", "", f"**A:** …{it['A']}", "",
                  f"**B:** …{it['B']}", "", "☐ A  ☐ B  ☐ =", ""]
    if not args.tag:
        (RESULTS_DIR / "p6_panel_form.md").write_text("\n".join(lines) + "\n")
    tps = {k: sum(n for n, _ in v) / sum(t for _, t in v) for k, v in speed.items()}
    out = {"scale": args.scale, "n_prompts": len(rows), "split": args.split, "tag": args.tag, "skip": args.skip,
           "baseline": args.baseline,
           "decoding": {"temperature": dec.temperature, "top_p": dec.top_p, "cache": dec.cache,
                        "exploratory": bool(args.tag)}, "tokens_per_second": tps,
           "tokens_per_second_with_provenance": explain_tps, "peak_rss_mb": peak_rss_mb(),
           "longest_copy_max": {k: max(r[k + "_longest_copy"] for r in rows) for k in ("engramm", "kn5")},
           "longest_copy_mean": {k: float(np.mean([r[k + "_longest_copy"] for r in rows])) for k in ("engramm", "kn5")},
           "k3_triggered": bool(tps["engramm"] < 2)}
    print(json.dumps(out, indent=1), flush=True)
    print(write_record(f"p5p6_generate_{args.scale}{sfx}", out, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
