"""What kind of thing is a word? Counted from what ENGRAMM has read (stage 3).

A category (food, colour, car, job) is described by a handful of general English anchor
words ("food", "dish", "eat", … for food). The *lift* of a word for a category is

    lift = P(sentence has an anchor | sentence has the word) / P(sentence has an anchor)

counted over the 14.8 M sentences of the corpus: "paella" co-occurs with food words 24
times more often than an average sentence does, "crazy" only 1.8 times. The word's
sentences are those holding its exact token sequence (" paella"), found through the
sentence index. Nothing is learnt; the anchors are the only hand-written part.

The same counts give the capitalisation of a word in running text ("Professionally" at the
start of a sentence is not a name, because the corpus writes "professionally" in lower case
mid-sentence).
"""

from __future__ import annotations

import numba
import numpy as np

ANCHORS = {
    "#food": ("food foods dish dishes eat eating ate eaten cook cooking cooked recipe recipes restaurant meal meals "
              "cuisine delicious taste tasty menu dinner lunch breakfast"),
    "#colour": "colour color colours colors coloured colored shade shades paint painted bright dark hue",
    "#car": "car cars drive driving drove driver vehicle vehicles engine motor sedan models dealership",
    "#job": ("job jobs profession occupation career employed hired worked works working employer salary trained "
             "apprentice qualified"),
}
# lift needed before a word counts as a member (food/colour/car words reach 6–30, filler words stay below 6;
# occupations reach only 2–7, so the job group needs the sentence's own cue as well — see facts.py)
LIFT_MIN = {"#food": 5.0, "#colour": 6.0, "#car": 8.0, "#job": 3.0}
MIN_SENTENCES = 20             # fewer occurrences: unknown word, no category


@numba.njit(cache=True)
def _phrase_mask(tokens, starts, lens, sids, pat):
    out = np.zeros(len(sids), dtype=np.bool_)
    m = len(pat)
    for k in range(len(sids)):
        s = sids[k]
        a = starts[s]
        b = a + lens[s]
        for i in range(a, b - m + 1):
            ok = True
            for j in range(m):
                if tokens[i + j] != pat[j]:
                    ok = False
                    break
            if ok:
                out[k] = True
                break
    return out


class Typer:
    """Category lift and capitalisation of words, from the corpus' sentence index."""

    def __init__(self, corpus, max_sentences: int = 200_000):
        self.c = corpus
        ix = corpus.index
        self.ptr = np.asarray(ix.ptr)
        self.post = ix.post
        self.term_of = np.asarray(ix.term_of)
        self.starts = np.asarray(ix.starts)
        self.lens = np.asarray(ix.lens)
        self.n = int(ix.n)
        self.max_sentences = max_sentences
        index = {t: i for i, t in enumerate(ix.terms)}
        self.anchor_sets: dict[str, np.ndarray] = {}
        for label, ws in ANCHORS.items():
            arrs = [self._plist(index[w]) for w in ws.split() if w in index]
            self.anchor_sets[label] = np.unique(np.concatenate(arrs)) if arrs else np.zeros(0, dtype=np.int64)
        self._lift: dict[str, dict | None] = {}
        self._lower: dict[str, float | None] = {}

    def _plist(self, t: int) -> np.ndarray:
        return np.asarray(self.post[self.ptr[t]:self.ptr[t + 1]], dtype=np.int64)

    def sentences(self, text: str) -> np.ndarray:
        """Sorted ids of the sentences that contain the exact token sequence of " text"."""
        ids = np.asarray(self.c.tok.encode(" " + text.strip()), dtype=np.int64)
        if len(ids) == 0:
            return np.zeros(0, dtype=np.int64)
        ts = sorted({int(self.term_of[i]) for i in ids if self.term_of[i] >= 0},
                    key=lambda t: (int(self.ptr[t + 1] - self.ptr[t]), t))
        if not ts:
            return np.zeros(0, dtype=np.int64)
        s = self._plist(ts[0])
        for t in ts[1:]:
            if len(s) == 0:
                break
            p = self._plist(t)
            pos = np.minimum(np.searchsorted(p, s), len(p) - 1)
            s = s[p[pos] == s]
        if len(s) > self.max_sentences:
            s = s[:self.max_sentences]
        if len(s):
            s = s[_phrase_mask(np.asarray(self.c.tokens), self.starts, self.lens, s,
                               ids.astype(np.asarray(self.c.tokens).dtype))]
        return s

    def counts(self, text: str) -> tuple[int, dict] | None:
        """(sentences with the word, {category: those that also hold an anchor}), or None when
        the word is too rare."""
        key = text.strip()
        if key in self._lift:
            return self._lift[key]
        s = self.sentences(key)
        out = None
        if len(s) >= MIN_SENTENCES:
            hits = {}
            for label, u in self.anchor_sets.items():
                if len(u) == 0:
                    continue
                pos = np.minimum(np.searchsorted(u, s), len(u) - 1)
                hits[label] = int((u[pos] == s).sum())
            out = (len(s), hits)
        self._lift[key] = out
        return out

    def lift(self, text: str) -> dict | None:
        """{category: lift} for a word or short phrase, or None when it is too rare."""
        c = self.counts(text)
        if c is None:
            return None
        n, hits = c
        return {lab: (h / n) / (len(self.anchor_sets[lab]) / self.n) for lab, h in hits.items()}

    def category(self, text: str) -> str | None:
        """The category a word clearly belongs to: its co-occurrences with the category's
        anchors exceed chance by at least 1.5 times as many as for any other category, and its
        lift reaches the category's minimum."""
        c = self.counts(text)
        if c is None:
            return None
        n, hits = c
        excess = {lab: h - n * len(self.anchor_sets[lab]) / self.n for lab, h in hits.items()}
        ranked = sorted(excess.items(), key=lambda kv: (-kv[1], kv[0]))
        best, val = ranked[0]
        second = max(ranked[1][1], 0.0) if len(ranked) > 1 else 0.0
        lf = (hits[best] / n) / (len(self.anchor_sets[best]) / self.n)
        if val > 0 and val >= 1.5 * second and lf >= LIFT_MIN.get(best, 5.0):
            return best
        return None

    def lower_share(self, word: str) -> float | None:
        """Share of lower-case spellings among the mid-sentence occurrences of a word (None
        when the corpus has fewer than 5)."""
        w = word.strip()
        key = w.lower()
        if key in self._lower:
            return self._lower[key]
        lo, cap = 0, 0
        for form, is_lower in ((key, True), (key[:1].upper() + key[1:], False)):
            n = len(self.sentences(form))
            if is_lower:
                lo = n
            else:
                cap = n
        out = lo / (lo + cap) if lo + cap >= 5 else None
        self._lower[key] = out
        return out
