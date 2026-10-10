"""Stage 1.1 sentence index: better sentence boundaries plus a document index.

Sentence boundaries (v2): after a token that ends in ``.``, ``!`` or ``?`` (closing
quotes/brackets ignored) only if the next token starts with white space or is the
document end — so "12.5", "U.S." and "e.g." no longer end a sentence — and, for a bare
``.``, not after a single letter (initials) or a common abbreviation (Mr, Dr, St, …),
and not when the next word starts in lower case. Line breaks and document ends still
end a sentence; at most 64 tokens per sentence.

Document index: for every term the documents that contain it (CSR), derived from
the sentence postings, so a question can be scored against whole articles.
"""

from __future__ import annotations

import json
from pathlib import Path

import numba
import numpy as np

from engramm.lm.chat import MAX_SENT, SentenceIndex, _index, term_table
from engramm.lm.tokenizer import EOS

ABBREVIATIONS = frozenset((
    "mr", "mrs", "ms", "dr", "st", "jr", "sr", "prof", "gen", "col", "lt", "sgt", "capt", "cpt", "mt", "ft", "vs",
    "no", "nos", "co", "inc", "ltd", "corp", "dept", "univ", "est", "approx", "fig", "figs", "vol", "vols", "ed",
    "eds", "rev", "hon", "gov", "sen", "rep", "pres", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep",
    "sept", "oct", "nov", "dec", "e", "i", "g", "c", "ca", "cf", "al", "op", "pp", "p", "ch", "sec", "vii", "ii",
    "iii", "iv", "vi", "viii", "ix", "x", "xi", "xii", "bros", "adm", "cmdr", "rt", "gens", "maj", "brig",
))
CLOSERS = "\"'”’)]}»"


def token_flags(tok):
    """Per token: ender, is-bare-dot, abbreviation/initial, starts with space, starts with
    space + lower-case letter, contains a line break."""
    texts = [p.decode("utf-8", errors="replace") for p in tok.token_bytes()]
    ender = np.array([t.rstrip(" ").rstrip(CLOSERS).endswith((".", "!", "?")) for t in texts], dtype=np.bool_)
    dot = np.array([t == "." for t in texts], dtype=np.bool_)
    abbrev = np.array([(t.strip().lower() in ABBREVIATIONS) or (len(t.strip()) == 1 and t.strip().isalpha())
                       for t in texts], dtype=np.bool_)
    space = np.array([t[:1].isspace() for t in texts], dtype=np.bool_)
    lower = np.array([len(t) > 1 and t[0] == " " and t[1].isalpha() and t[1].islower() for t in texts],
                     dtype=np.bool_)
    newline = np.array(["\n" in t for t in texts], dtype=np.bool_)
    space[EOS] = True
    return ender, dot, abbrev, space, lower, newline


@numba.njit(cache=True)
def _segment_v2(tokens, ender, dot, abbrev, space, lower, newline, max_len):
    n = len(tokens)
    starts = np.empty(n // 2 + 2, dtype=np.int64)
    lens = np.empty(n // 2 + 2, dtype=np.int32)
    k = 0
    s = -1
    for i in range(n):
        t = tokens[i]
        if t == 0:
            if s >= 0:
                starts[k] = s
                lens[k] = i - s
                k += 1
                s = -1
            continue
        if s < 0:
            s = i
        end = newline[t]
        if not end and ender[t]:
            nxt = tokens[i + 1] if i + 1 < n else 0
            if space[nxt]:
                end = True
                if dot[t]:
                    if i > s and abbrev[tokens[i - 1]]:
                        end = False
                    if lower[nxt]:
                        end = False
        if end or i - s + 1 >= max_len:
            starts[k] = s
            lens[k] = i - s + 1
            k += 1
            s = -1
    if s >= 0:
        starts[k] = s
        lens[k] = n - s
        k += 1
    return starts[:k], lens[:k]


def doc_postings(ptr: np.ndarray, post: np.ndarray, sent_doc: np.ndarray):
    """CSR term → documents (each once), from the sentence postings (sorted per term)."""
    dp = sent_doc[post]
    n_terms = len(ptr) - 1
    term_of_entry = np.repeat(np.arange(n_terms, dtype=np.int64), np.diff(ptr))
    keep = np.ones(len(dp), dtype=bool)
    keep[1:] = (dp[1:] != dp[:-1]) | (term_of_entry[1:] != term_of_entry[:-1])
    counts = np.bincount(term_of_entry[keep], minlength=n_terms)
    dptr = np.zeros(n_terms + 1, dtype=np.int64)
    np.cumsum(counts, out=dptr[1:])
    return dptr, dp[keep].astype(np.int32)


def build(tokens: np.ndarray, doc_starts: np.ndarray, tok):
    """(sentence index, document pointers, document postings, sentence → document)."""
    term_of, terms, _ = term_table(tok)
    t = np.ascontiguousarray(tokens, dtype=np.uint16)
    starts, lens = _segment_v2(t, *token_flags(tok), MAX_SENT)
    ptr, post, sent_terms = _index(t, starts, lens, term_of, len(terms))
    ix = SentenceIndex(starts, lens, ptr, post, sent_terms, term_of, terms)
    sent_doc = (np.searchsorted(doc_starts, starts, side="right") - 1).astype(np.int32)
    dptr, dpost = doc_postings(ptr, post, sent_doc)
    return ix, dptr, dpost, sent_doc


def save(d: Path, ix: SentenceIndex, dptr, dpost, sent_doc, info: dict) -> None:
    ix.save(d)
    np.save(d / "doc_ptr.npy", dptr)
    np.save(d / "doc_post.npy", dpost)
    np.save(d / "sent_doc.npy", sent_doc)
    (d / "info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


def load_docs(d: Path, mmap: bool = True):
    m = "r" if mmap else None
    return (np.load(d / "doc_ptr.npy", mmap_mode=m), np.load(d / "doc_post.npy", mmap_mode=m),
            np.load(d / "sent_doc.npy", mmap_mode=m))
