"""ChatBench-EN: items, sealed splits, running a system, blind rating sheets and the analysis.

Item (one JSON object per line):
    {"id": "cb-0001", "category": "smalltalk", "turns": ["hi", "how are you?"], "writer": "w07",
     "note": "optional: what a good answer needs"}
Only the reply to the last turn is rated; earlier turns are played to the system first, in one
conversation. Categories: smalltalk, memory, multiturn, facts, explain, writing, robustness.

Splits come from SHAKE-256 of the item id (so adding items never moves old ones): 45 % dev,
20 % val, 25 % test (sealed: its responses are generated and rated exactly once per
registration), 10 % reserve.

A rating is, per item and rater: which reply is better (A, B or tie) and, per reply, whether it is
acceptable (yes/no). The rating page is one static HTML file with the pairs embedded; raters
download their ratings as JSON — no server anywhere.

Analysis: P = (wins + ½ ties) / N per category for system X against Y, with a cluster bootstrap
over items (2,000 resamples, seed 42) for the 95 % interval; acceptability per system; agreement
between raters as Krippendorff's alpha (nominal, over A/B/tie). Parity in a category:
lower 95 % bound of P ≥ 0.40 and P ≥ 0.45 (docs/PREREG_CHATBENCH.md).
"""

from __future__ import annotations

import hashlib
import html
import json
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

CATEGORIES = ("smalltalk", "memory", "multiturn", "facts", "explain", "writing", "robustness")
SPLITS = (("dev", 45), ("val", 20), ("test", 25), ("reserve", 10))


@dataclass
class Item:
    id: str
    category: str
    turns: list[str]
    writer: str = ""
    note: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Item:
        return cls(d["id"], d["category"], list(d["turns"]), d.get("writer", ""), d.get("note", ""))


def load_items(path: Path | str) -> list[Item]:
    items = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            it = Item.from_dict(json.loads(line))
            if it.category not in CATEGORIES:
                raise ValueError(f"{it.id}: unknown category {it.category!r}")
            if not it.turns or not all(isinstance(t, str) and t.strip() for t in it.turns):
                raise ValueError(f"{it.id}: empty turn")
            items.append(it)
    ids = [i.id for i in items]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate item ids")
    return items


def split_of(item_id: str, salt: str = "chatbench-v1") -> str:
    x = int.from_bytes(hashlib.shake_256(f"{salt}|{item_id}".encode()).digest(8), "big") % 100
    acc = 0
    for name, pct in SPLITS:
        acc += pct
        if x < acc:
            return name
    return SPLITS[-1][0]


def run_system(items: list[Item], respond) -> list[dict]:
    """respond(conversation_id, message) → reply text. Each item is its own conversation."""
    out = []
    for it in items:
        reply = ""
        for t in it.turns:
            reply = respond(it.id, t)
        out.append({"id": it.id, "reply": reply})
    return out


@dataclass
class Pair:
    id: str
    category: str
    turns: list[str]
    a_system: str
    b_system: str
    a: str
    b: str


def make_pairs(items: list[Item], replies: dict[str, dict[str, str]], systems: tuple[str, str],
               seed: str = "pairs-v1") -> list[Pair]:
    """Blind pairs: for each item the two systems' replies in an order drawn from SHAKE-256."""
    x, y = systems
    pairs = []
    for it in items:
        if it.id not in replies[x] or it.id not in replies[y]:
            continue
        flip = hashlib.shake_256(f"{seed}|{it.id}".encode()).digest(1)[0] & 1
        a, b = (y, x) if flip else (x, y)
        pairs.append(Pair(it.id, it.category, it.turns, a, b, replies[a][it.id], replies[b][it.id]))
    return pairs


def rating_page(pairs: list[Pair], title: str = "ChatBench rating") -> str:
    """One static HTML page: the pairs (without system names), a form per pair, and a button that
    downloads the ratings as JSON. Works offline in any browser."""
    public = [{"id": p.id, "turns": p.turns, "a": p.a, "b": p.b} for p in pairs]
    data = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title>
<style>
:root{{--bg:#fff;--ink:#1f1f24;--muted:#6b6b76;--line:#e5e5ea;--accent:#4b2bd6;--panel:#f7f7f8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#17171c;--ink:#ececf1;--muted:#9a9aa6;--line:#2c2c35;
--accent:#8b74ff;--panel:#111115}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:16px}}
.pair{{border:1px solid var(--line);border-radius:14px;padding:14px;margin:16px 0}}
.turns{{color:var(--muted);white-space:pre-wrap}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}}
@media (max-width:720px){{.cols{{grid-template-columns:1fr}}}}
.reply{{background:var(--panel);border-radius:10px;padding:10px;white-space:pre-wrap}}
.choice{{margin-top:10px;display:flex;flex-wrap:wrap;gap:12px}}
button{{font:inherit;padding:10px 16px;border-radius:10px;border:0;background:var(--accent);color:#fff;cursor:pointer}}
.progress{{position:sticky;top:0;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line)}}
</style></head><body><main>
<h1>{html.escape(title)}</h1>
<p>For each conversation, read the last user message and the two replies. Choose the better reply
(or “about the same”), and mark each reply as acceptable or not. Judge helpfulness, correctness
and naturalness. You cannot see which system wrote which reply.</p>
<p><label>Your rater code: <input id="rater" required></label></p>
<div class="progress"><span id="done">0</span> / <span id="total"></span> rated
<button id="save" type="button">Download my ratings</button></div>
<div id="pairs"></div></main>
<script>
const PAIRS = {data};
const box = document.getElementById("pairs");
document.getElementById("total").textContent = PAIRS.length;
const esc = (s) => s.replace(/[&<>]/g, (c) => ({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c]));
PAIRS.forEach((p, i) => {{
  const el = document.createElement("section");
  el.className = "pair";
  el.innerHTML = `<div class="turns">${{p.turns.map((t, k) => (k === p.turns.length - 1 ? "<b>User:</b> " : "User: ") + esc(t)).join("\\n")}}</div>
  <div class="cols"><div><b>Reply A</b><div class="reply">${{esc(p.a)}}</div>
  <label><input type="checkbox" name="accA"> acceptable</label></div>
  <div><b>Reply B</b><div class="reply">${{esc(p.b)}}</div>
  <label><input type="checkbox" name="accB"> acceptable</label></div></div>
  <div class="choice"><label><input type="radio" name="w${{i}}" value="A"> A is better</label>
  <label><input type="radio" name="w${{i}}" value="tie"> about the same</label>
  <label><input type="radio" name="w${{i}}" value="B"> B is better</label></div>`;
  el.addEventListener("change", update);
  box.append(el);
}});
function collect() {{
  return PAIRS.map((p, i) => {{
    const el = box.children[i];
    const w = el.querySelector(`input[name="w${{i}}"]:checked`);
    return {{ id: p.id, winner: w ? w.value : null, acc_a: el.querySelector('[name="accA"]').checked,
             acc_b: el.querySelector('[name="accB"]').checked }};
  }});
}}
function update() {{ document.getElementById("done").textContent = collect().filter((r) => r.winner).length; }}
document.getElementById("save").onclick = () => {{
  const rater = document.getElementById("rater").value.trim();
  if (!rater) {{ alert("Please enter your rater code first."); return; }}
  const blob = new Blob([JSON.stringify({{ rater, ratings: collect() }}, null, 1)], {{ type: "application/json" }});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = `ratings-${{rater}}.json`; a.click();
}};
</script></body></html>"""


def krippendorff_alpha_nominal(units: dict[str, list[str]]) -> float | None:
    """Krippendorff's alpha for nominal data; units: item → the labels its raters gave."""
    pairs = defaultdict(float)
    n_total = 0
    for labels in units.values():
        m = len(labels)
        if m < 2:
            continue
        for i, a in enumerate(labels):
            for j, b in enumerate(labels):
                if i != j:
                    pairs[(a, b)] += 1.0 / (m - 1)
        n_total += m
    if n_total == 0:
        return None
    n_c = defaultdict(float)
    for (a, _), v in pairs.items():
        n_c[a] += v
    d_o = sum(v for (a, b), v in pairs.items() if a != b) / n_total
    d_e = sum(n_c[a] * n_c[b] for a in n_c for b in n_c if a != b) / (n_total * (n_total - 1))
    return 1.0 - d_o / d_e if d_e > 0 else 1.0


@dataclass
class Result:
    category: str
    n_items: int
    p: float
    ci95: tuple[float, float]
    accept_x: float
    accept_y: float
    parity: bool = field(default=False)


def analyze(pairs: list[Pair], ratings: list[dict], x: str, y: str, reps: int = 2000,
            seed: int = 42) -> dict:
    """ratings: [{"rater": r, "ratings": [{"id", "winner", "acc_a", "acc_b"}]}]. Scores for x vs y."""
    by_id = {p.id: p for p in pairs}
    per_item: dict[str, list[float]] = defaultdict(list)       # x's score per rating: 1 win, .5 tie, 0 loss
    acc: dict[str, dict[str, list[int]]] = defaultdict(lambda: {x: [], y: []})
    labels: dict[str, list[str]] = defaultdict(list)
    for sheet in ratings:
        for r in sheet["ratings"]:
            p = by_id.get(r["id"])
            if p is None or r.get("winner") not in ("A", "B", "tie"):
                continue
            win_sys = {"A": p.a_system, "B": p.b_system}.get(r["winner"])
            score = 0.5 if win_sys is None else (1.0 if win_sys == x else 0.0)
            per_item[p.id].append(score)
            labels[p.id].append("tie" if win_sys is None else win_sys)
            acc[p.id][p.a_system].append(int(bool(r.get("acc_a"))))
            acc[p.id][p.b_system].append(int(bool(r.get("acc_b"))))
    rng = random.Random(seed)
    out = {"x": x, "y": y, "alpha": krippendorff_alpha_nominal(labels), "categories": {}}
    cats = sorted({by_id[i].category for i in per_item}) + ["all"]
    for cat in cats:
        ids = sorted(i for i in per_item if cat == "all" or by_id[i].category == cat)
        if not ids:
            continue
        means = [sum(per_item[i]) / len(per_item[i]) for i in ids]
        p = sum(means) / len(means)
        boots = []
        for _ in range(reps):
            sample = [means[rng.randrange(len(means))] for _ in means]
            boots.append(sum(sample) / len(sample))
        boots.sort()
        lo, hi = boots[int(0.025 * reps)], boots[int(0.975 * reps) - 1]
        ax = [v for i in ids for v in acc[i][x]]
        ay = [v for i in ids for v in acc[i][y]]
        res = Result(cat, len(ids), p, (lo, hi), sum(ax) / max(len(ax), 1), sum(ay) / max(len(ay), 1))
        res.parity = lo >= 0.40 and p >= 0.45
        out["categories"][cat] = res.__dict__
    return out
