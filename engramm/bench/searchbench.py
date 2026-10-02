"""SearchBench-EN v0 (docs/PREREG_SEARCH_V0.md): items, the sealed split, the privacy and
channels-off checks, blind rating sheets and the scoring against the registered thresholds.

Item (one JSON object per line), written by a person without access to ENGRAMM:
    {"id": "sb-0001", "category": "current", "question": "Who won the 2024 Tour de France?",
     "answer": "Tadej Pogačar", "source": "https://en.wikipedia.org/wiki/2024_Tour_de_France",
     "writer": "w03"}
Categories and sizes (registered): 160 ``current`` (after 1 January 2023), 120 ``longtail`` (subject
not among the 400,000 articles of the Lite pack), 120 ``general``.

Split: per category, items are ordered by SHA-256 of ``seed|id``; the first 40 / 30 / 30 are dev,
the rest (300) test. The test file is sealed: its SHA-256 goes into ``docs/SEARCHBENCH_SEAL.txt``
before any test run, and ``verify_seal`` refuses a changed file.

Rating: two people per answer, blind to the system; labels ``right_sourced`` (right, and the quoted
source sentence answers the question), ``right``, ``wrong``, ``none`` (no answer / "I don't know").
Disagreement: a third person decides; without a third rating the answer stays ``undecided`` and is
reported. The rating page is one static HTML file; raters download their labels as JSON.
"""

from __future__ import annotations

import hashlib
import html
import json
import random
import re
from collections import Counter
from pathlib import Path

CATEGORIES = ("current", "longtail", "general")
TARGET = {"current": 160, "longtail": 120, "general": 120}
DEV_PER_CATEGORY = {"current": 40, "longtail": 30, "general": 30}
LABELS = ("right_sourced", "right", "wrong", "none")
REQUIRED = ("id", "category", "question", "answer", "source")
SEED = "searchbench-v0"
_STOP = frozenset("""a an the of in on at to for from by with and or is are was were be been who what when where
which why how did does do has have had it its this that these those as into than then there their his her he
she they them you your i me my we our""".split())


def load_items(path: Path) -> list[dict]:
    items = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"line {n}: not JSON ({e.msg})") from None
    return items


def validate(items: list[dict], full: bool = True) -> list[str]:
    """Problems with an item file; ``full`` also checks the registered sizes (160/120/120)."""
    problems = []
    ids, questions = Counter(), Counter()
    for i, it in enumerate(items):
        where = f"item {i + 1} ({it.get('id', '?')})"
        for k in REQUIRED:
            if not isinstance(it.get(k), str) or not it.get(k).strip():
                problems.append(f"{where}: missing or empty '{k}'")
        if it.get("category") not in CATEGORIES:
            problems.append(f"{where}: category must be one of {', '.join(CATEGORIES)}")
        src = str(it.get("source", ""))
        if src and not re.match(r"https?://", src):
            problems.append(f"{where}: source should be a URL")
        ids[it.get("id")] += 1
        questions[" ".join(str(it.get("question", "")).lower().split())] += 1
    problems += [f"duplicate id: {k}" for k, v in ids.items() if v > 1 and k]
    problems += [f"duplicate question: {k}" for k, v in questions.items() if v > 1 and k]
    if full:
        have = Counter(it.get("category") for it in items)
        for cat, want in TARGET.items():
            if have.get(cat, 0) != want:
                problems.append(f"category {cat}: {have.get(cat, 0)} items, registered {want}")
    return problems


def _order_key(seed: str, item_id: str) -> str:
    return hashlib.sha256(f"{seed}|{item_id}".encode()).hexdigest()


def split(items: list[dict], seed: str = SEED) -> tuple[list[dict], list[dict]]:
    """(dev, test): per category the first DEV_PER_CATEGORY items in SHA-256 order are dev."""
    dev, test = [], []
    for cat in CATEGORIES:
        group = sorted((it for it in items if it.get("category") == cat), key=lambda it: _order_key(seed, it["id"]))
        k = DEV_PER_CATEGORY[cat]
        dev += group[:k]
        test += group[k:]
    return dev, test


def write_items(items: list[dict], path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(it, ensure_ascii=False, sort_keys=True) + "\n" for it in items),
                          encoding="utf-8")


def seal(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_seal(path: Path, seal_file: Path) -> bool:
    want = None
    for line in Path(seal_file).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*([0-9a-f]{64})\b", line)
        if m:
            want = m.group(1)
    return want is not None and want == seal(path)


def _content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in _STOP and len(w) > 1]


def leaked(question: str, entries: list[dict]) -> bool:
    """True when a network-log entry (any field) carries the question: the whole question, or three
    consecutive content words of it. This is criterion S4 — it must be False for every question."""
    q = " ".join(question.lower().split()).strip(" ?.!")
    words = _content_words(question)
    grams = {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}
    for e in entries:
        blob = " ".join(_content_words(json.dumps(e, ensure_ascii=False)))
        raw = json.dumps(e, ensure_ascii=False).lower()
        if q and q in raw:
            return True
        if any(g in blob for g in grams):
            return True
    return False


def same_answers(a: dict[str, str], b: dict[str, str]) -> tuple[int, list[str]]:
    """(identical count, ids that differ) — criterion S5 (channels off = v3 offline)."""
    ids = sorted(set(a) & set(b))
    diff = [i for i in ids if (a[i] or "").strip() != (b[i] or "").strip()]
    return len(ids) - len(diff), diff


def rating_rows(items: list[dict], runs: dict[str, dict[str, dict]], seed: str = SEED) -> tuple[list[dict], dict]:
    """Blind rows for the sheet and the key that maps each row back to (system, item). Rows are
    shuffled; the system never appears on the sheet."""
    by_id = {it["id"]: it for it in items}
    rows, key = [], {}
    for system, answers in sorted(runs.items()):
        for item_id, rec in sorted(answers.items()):
            if item_id not in by_id:
                continue
            rid = hashlib.sha256(f"{seed}|{system}|{item_id}".encode()).hexdigest()[:12]
            key[rid] = {"system": system, "id": item_id}
            rows.append({"row": rid, "question": by_id[item_id]["question"], "reference": by_id[item_id]["answer"],
                         "reference_source": by_id[item_id]["source"], "reply": rec.get("text", ""),
                         "reply_source": rec.get("source", "")})
    random.Random(seed).shuffle(rows)
    return rows, key


def rating_page(rows: list[dict], title: str = "SearchBench-EN rating") -> str:
    """One self-contained HTML page: per row the question, the reference answer, the reply and its
    source; four labels; the rater downloads a JSON file. No system names, no server."""
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    labels = json.dumps(list(LABELS))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title>
<style>body{{font:15px/1.45 system-ui,sans-serif;max-width:860px;margin:0 auto;padding:16px;background:#fafafa;color:#222}}
.row{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px 14px;margin:12px 0}}
.q{{font-weight:600}}.ref{{color:#555;font-size:13px}}.reply{{white-space:pre-wrap;margin:8px 0;padding:8px;background:#f3f6fa;border-radius:6px}}
label{{margin-right:14px;white-space:nowrap}}button{{font-size:15px;padding:8px 14px}}
@media (prefers-color-scheme:dark){{body{{background:#111;color:#ddd}}.row{{background:#1b1b1b;border-color:#333}}.reply{{background:#202833}}.ref{{color:#aaa}}}}</style>
</head><body><h1>{html.escape(title)}</h1>
<p>For each reply choose one label. <b>right_sourced</b>: the reply answers correctly and the source it shows
supports it. <b>right</b>: correct, but no supporting source. <b>wrong</b>: a wrong answer. <b>none</b>: no answer
or "I don't know". Compare with the reference answer; you do not see which system wrote the reply.</p>
<p><label>Your rater id <input id="rater" size="10"></label> <span id="count"></span></p>
<div id="rows"></div><button id="save">Download my ratings (JSON)</button>
<script>const ROWS={data};const LABELS={labels};const box=document.getElementById('rows');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
ROWS.forEach((r,i)=>{{const d=document.createElement('div');d.className='row';
d.innerHTML=`<div class="q">${{i+1}}. ${{esc(r.question)}}</div><div class="ref">Reference: ${{esc(r.reference)}} — ${{esc(r.reference_source)}}</div>`+
`<div class="reply">${{esc(r.reply)}}</div><div class="ref">Reply source: ${{esc(r.reply_source||'(none)')}}</div>`+
LABELS.map(l=>`<label><input type="radio" name="${{r.row}}" value="${{l}}"> ${{l}}</label>`).join('');box.appendChild(d);}});
const upd=()=>{{document.getElementById('count').textContent=document.querySelectorAll('input[type=radio]:checked').length+' / '+ROWS.length+' rated';}};
box.addEventListener('change',upd);upd();
document.getElementById('save').onclick=()=>{{const out={{rater:document.getElementById('rater').value||'anonymous',labels:{{}}}};
document.querySelectorAll('input[type=radio]:checked').forEach(x=>out.labels[x.name]=x.value);
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,1)],{{type:'application/json'}}));
a.download='searchbench_ratings_'+out.rater+'.json';a.click();}};</script></body></html>"""


def decide(labels: list[str | None]) -> str:
    """The final label of one answer from two raters (and a third when they disagree)."""
    first = [x for x in labels[:2] if x in LABELS]
    if len(first) == 2 and first[0] == first[1]:
        return first[0]
    if len(labels) >= 3 and labels[2] in LABELS:
        return labels[2]
    return "undecided"


def score(items: list[dict], key: dict, ratings: list[dict]) -> dict:
    """Per system and category: the decided labels, then the registered criteria S1–S3 (S4–S6 come
    from the run files)."""
    cat_of = {it["id"]: it["category"] for it in items}
    table: dict = {}
    for rid, ref in key.items():
        labels = [r.get("labels", {}).get(rid) for r in ratings]
        final = decide(labels)
        sysd = table.setdefault(ref["system"], {})
        cell = sysd.setdefault(cat_of.get(ref["id"], "?"), Counter())
        cell[final] += 1
    out = {"systems": {s: {c: dict(v) for c, v in cats.items()} for s, cats in table.items()}}
    out["criteria"] = criteria(out["systems"])
    return out


def _share(c: dict, labels: tuple[str, ...], among: tuple[str, ...] | None = None) -> float | None:
    total = sum(v for k, v in c.items() if among is None or k in among)
    return None if total == 0 else sum(c.get(k, 0) for k in labels) / total


def criteria(systems: dict, offline: str = "offline", atlas: str = "atlas") -> dict:
    def merged(sysname):
        tot = Counter()
        for cnt in systems.get(sysname, {}).values():
            tot.update(cnt)
        return tot
    a_all = merged(atlas)
    s1 = _share(a_all, ("wrong",), ("right_sourced", "right", "wrong"))
    lt_a = _share(systems.get(atlas, {}).get("longtail", {}), ("right_sourced",))
    lt_o = _share(systems.get(offline, {}).get("longtail", {}), ("right_sourced",))
    s3 = _share(systems.get(atlas, {}).get("current", {}), ("right_sourced",))
    return {
        "S1_wrong_share_atlas": s1, "S1_pass": None if s1 is None else s1 <= 0.05,
        "S2_longtail_gain_pp": None if lt_a is None or lt_o is None else round(100 * (lt_a - lt_o), 1),
        "S2_pass": None if lt_a is None or lt_o is None else (lt_a - lt_o) >= 0.20,
        "S3_current_right_sourced": s3, "S3_pass": None if s3 is None else s3 >= 0.30,
    }
