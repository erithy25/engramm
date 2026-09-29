"""“Tell me about X”: the opening sentences of the article about X.

Wikipedia articles start with a definition ("Photosynthesis is the process …"), which is the
best short explanation ENGRAMM has read. This module finds the article for a topic — by its
exact title, then by simple variants (no article, singular, title case), then among the
retrieved sentences — and returns its first sentences, cleaned of pronunciation guides and
reference debris. "Tell me more" continues with the next sentences of the same article.

The title table is built once per corpus from the document keys (Wikipedia documents only)
as sorted 64-bit hashes (8 bytes per title, no Python strings kept).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import numpy as np

_ARTICLES = re.compile(r"^(?:the|a|an)\s+", re.I)


def title_key(text: str) -> str:
    t = text.replace("_", " ").replace("’", "'").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def _h(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(title_key(text).encode("utf-8"), digest_size=8).digest(), "little")


def variants(topic: str) -> list[str]:
    """Titles to try for a topic, most specific first."""
    t = topic.strip().strip("?.!\"'“”‘’").strip()
    t = re.sub(r"\s+", " ", t)
    out = [t]
    no_art = _ARTICLES.sub("", t)
    out.append(no_art)
    low = no_art.lower()
    # plural → singular ("black holes" → "black hole", "volcanoes" → "volcano", "cities" → "city")
    if low.endswith("ies") and len(low) > 4:
        out.append(no_art[:-3] + "y")
    if re.search(r"(?:ches|shes|sses|xes|zes|oes)$", low):
        out.append(no_art[:-2])
    if low.endswith("s") and not low.endswith("ss") and len(low) > 3:
        out.append(no_art[:-1])
    # "the beatles" → "The Beatles" (title with article), "bmw" → "BMW"
    out.append("The " + no_art)
    out.append(no_art.upper())
    seen, res = set(), []
    for v in out:
        k = title_key(v)
        if k and k not in seen:
            seen.add(k)
            res.append(v)
    return res


_PAREN_JUNK = re.compile(r"\s*\((?:[^()]*?(?:/[^/()]+/|pronounced|listen|IPA|;\s*(?:born|lit\.|from)|"
                         r"[ˈˌəɪʊʃʒθðŋɛɔæɑ])[^()]*?)\)", re.I)
_BRACKETS = re.compile(r"\s*\[[^\]]*\]")
_EMPTY_PAREN = re.compile(r"\s*\(\s*[,;]?\s*\)")


def clean_sentence(s: str) -> str:
    s = _BRACKETS.sub("", s)
    for _ in range(2):
        s = _PAREN_JUNK.sub("", s)
    s = _EMPTY_PAREN.sub("", s)
    s = re.sub(r"\(\s*;\s*", "(", s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


@dataclass
class About:
    title: str
    doc: int
    sentences: list[str]          # cleaned
    next_sentence: int            # corpus sentence id to continue with ("tell me more")
    end_sentence: int
    source: dict


class TitleIndex:
    def __init__(self, corpus):
        self.c = corpus
        hashes, docs = [], []
        for d, (src, key) in enumerate(corpus.doc_keys):
            if src in ("wiki", "wikipedia") and key:
                hashes.append(_h(key))
                docs.append(d)
        h = np.asarray(hashes, dtype=np.uint64)
        order = np.argsort(h, kind="stable")
        self.hashes = h[order]
        self.docs = np.asarray(docs, dtype=np.int64)[order]

    def lookup(self, title: str) -> list[int]:
        k = np.uint64(_h(title))
        lo = int(np.searchsorted(self.hashes, k, side="left"))
        hi = int(np.searchsorted(self.hashes, k, side="right"))
        return [int(d) for d in self.docs[lo:hi] if title_key(self.c.doc_keys[int(d)][1]) == title_key(title)]


def _is_definition(sentence: str, title: str) -> bool:
    """Does the sentence read like an article's first line about ``title``?"""
    low = sentence.lower()
    tw = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in ("the", "a", "an", "of")]
    if not tw:
        return False
    head = low[:max(80, len(title) + 40)]
    return any(w in head for w in tw) and bool(re.search(r"\b(?:is|was|are|were|refers to|may refer to)\b", low))


class AboutFinder:
    def __init__(self, corpus, retriever=None):
        self.c = corpus
        self.r = retriever
        self._titles: TitleIndex | None = None

    @property
    def titles(self) -> TitleIndex:
        if self._titles is None:
            self._titles = TitleIndex(self.c)
        return self._titles

    def _doc_text(self, d: int, start: int | None = None, n: int = 3, max_chars: int = 700
                  ) -> tuple[list[str], int, int]:
        lo, hi = self.c.doc_sentences(d)
        s = lo if start is None else start
        out, chars = [], 0
        title = self.c.doc_keys[d][1]
        while s < hi and len(out) < n:
            t = clean_sentence(self.c.sentence_text(s))
            s += 1
            # a lead document starts with its title as a line of its own ("Black hole\nA black hole is …")
            if t.startswith(title + " ") and not out:
                rest = t[len(title):].strip()
                if rest[:1].isupper():
                    t = rest
            if t == title or len(t) < 3 or not re.search(r"[A-Za-z]", t):
                continue
            if out and chars + len(t) > max_chars:
                s -= 1
                break
            out.append(t)
            chars += len(t)
        return out, s, hi

    def _best_doc(self, docs: list[int], title: str) -> int | None:
        """Several documents may carry the same title (an article chunk and its lead): the one
        whose first sentence defines the title, else the first."""
        best = None
        for d in docs:
            lo, hi = self.c.doc_sentences(d)
            if hi <= lo:
                continue
            first = self.c.sentence_text(lo)
            if _is_definition(first, title):
                return d
            if best is None:
                best = d
        return best

    def find(self, topic: str, n: int = 3, max_chars: int = 700) -> About | None:
        for v in variants(topic):
            docs = self.titles.lookup(v)
            if docs:
                d = self._best_doc(docs, v)
                if d is None:
                    continue
                sents, nxt, end = self._doc_text(d, n=n, max_chars=max(max_chars, 150 * n))
                if not sents or "may refer to" in sents[0].lower():
                    continue          # a disambiguation page
                src_key = self.c.doc_keys[d][1]
                return About(src_key, d, sents, nxt, end, {"kind": "base", "source": self.c.doc_keys[d][0],
                                                            "key": src_key, "token_offset": 0})
        return None

    def more(self, about: About, n: int = 3) -> About | None:
        if about.next_sentence >= about.end_sentence:
            return None
        sents, nxt, end = self._doc_text(about.doc, start=about.next_sentence, n=n)
        if not sents:
            return None
        return About(about.title, about.doc, sents, nxt, end, about.source)
