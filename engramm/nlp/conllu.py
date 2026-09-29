"""Reading Universal Dependencies treebanks (CoNLL-U)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Sentence:
    id: str
    text: str
    words: list[str] = field(default_factory=list)
    upos: list[str] = field(default_factory=list)
    xpos: list[str] = field(default_factory=list)
    heads: list[int] = field(default_factory=list)      # 0 = root, else 1-based index
    deprels: list[str] = field(default_factory=list)


def read(path: Path | str) -> list[Sentence]:
    out, cur = [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("# sent_id = "):
            cur = Sentence(line[12:].strip(), "")
        elif line.startswith("# text = ") and cur is not None:
            cur.text = line[9:]
        elif not line.strip():
            if cur is not None and cur.words:
                out.append(cur)
            cur = None
        elif not line.startswith("#"):
            cols = line.split("\t")
            if "-" in cols[0] or "." in cols[0]:
                continue                              # multi-word tokens and empty nodes
            if cur is None:
                cur = Sentence(str(len(out)), "")
            cur.words.append(cols[1])
            cur.upos.append(cols[3])
            cur.xpos.append(cols[4])
            cur.heads.append(int(cols[6]))
            cur.deprels.append(cols[7].split(":")[0])
    if cur is not None and cur.words:
        out.append(cur)
    return out


def is_projective(heads: list[int]) -> bool:
    arcs = [(h, d) for d, h in enumerate(heads, 1) if h > 0]
    for h1, d1 in arcs:
        a1, b1 = sorted((h1, d1))
        for h2, d2 in arcs:
            a2, b2 = sorted((h2, d2))
            if a1 < a2 < b1 < b2:
                return False
    return True
