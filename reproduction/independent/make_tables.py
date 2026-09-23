"""Collect conformance checks and results into markdown tables (printed to stdout)."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

rows = []
for f in ("checks_small.json", "checks_data.json", "checks_enc.json", "checks_t1a.json", "checks_full.json"):
    p = os.path.join(OUT, f)
    if os.path.exists(p):
        for r in json.load(open(p)):
            r["file"] = f
            rows.append(r)


def short(s, n=90):
    s = str(s)
    return s if len(s) <= n else s[: n - 3] + "..."


print("| # | § | check | result | value obtained | expected (spec) |")
print("|---|---|---|---|---|---|")
for i, r in enumerate(rows, 1):
    exp = "(same)" if r["ok"] else short(r["expected"], 70)
    print(f"| {i} | {r['section']} | {r['check'].replace('|', '/')} | {'PASS' if r['ok'] else '**FAIL**'} | `{short(r['got']).replace('|', '/')}` | {exp.replace('|', '/')} |")
print()
print(f"Total checks: {len(rows)}; pass {sum(r['ok'] for r in rows)}; fail {sum(not r['ok'] for r in rows)}")
print()
res = json.load(open(os.path.join(OUT, "results.json"))) if os.path.exists(os.path.join(OUT, "results.json")) else {}
print("| config | n_test | accuracy | macro-F1 | predictions_sha256 | T2 error per epoch (misses) | runtime |")
print("|---|---|---|---|---|---|---|")
for c in "abcd":
    if c not in res:
        continue
    r = res[c]
    t2 = f"{r['t2_error_per_epoch']} ({r['t2_misses_per_epoch']})" if "t2_error_per_epoch" in r else "-"
    rt = r.get("runtime_s", r.get("runtime_s_excluding_encoding"))
    print(f"| ({c}) | {r['n_test']} | {r['accuracy']!r} | {r['macro_f1']!r} | `{r['predictions_sha256']}` | {t2} | {rt} s |")
