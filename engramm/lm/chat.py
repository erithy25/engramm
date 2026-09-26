"""ENGRAMM-Chat, stage 1: answer questions by looking things up (docs/PREREG_CHAT.md).

No free generation: the question is matched against every sentence ENGRAMM has
read (and every sentence it was taught with ``learn``), and the best sentence is
returned with its source.

* Sentences: the train stream cut after tokens that end in ``.``, ``!``, ``?`` or
  contain a line break, and at document ends; longer than 64 tokens → 64-token pieces.
* Terms: a token's text, stripped and lower-cased; tokens without a letter or digit
  are not terms.
* BM25 over sentences (binary term frequency, k1 = 1.2, b = 0.75; terms in more
  than 5 % of sentences ignored) gives the top 200 candidates.
* HDC re-ranking: score = BM25 + α · S_HDC, where S_HDC is an idf-weighted soft
  word match between question and sentence from the counted meaning vectors
  (sim = 1 − ham/1024, clipped at 0).
* "I don't know" when score / Σ idf(question terms) < θ.

Everything is counting and integer/bit arithmetic plus a fixed float formula;
no model other than ENGRAMM's own is involved.
"""

from __future__ import annotations

import re
import string
import time
from dataclasses import dataclass
from pathlib import Path

import numba
import numpy as np

from engramm.lm.semantic import popcount64
from engramm.lm.tokenizer import EOS

MAX_SENT = 64
K1, B = 1.2, 0.75
DF_CAP = 0.05
TOP_BM25 = 200
# α and θ chosen on the dev split (docs/PREREG_CHAT.md §2;
# results/chat/chat_stage1_container_20260926T211521Z.json)
FROZEN_ALPHA = 2.0
FROZEN_THETA = 2.16878620662428


# ---------------------------------------------------------------------------
# vocabulary → terms
# ---------------------------------------------------------------------------

def term_table(tok) -> tuple[np.ndarray, list[str], np.ndarray]:
    """(term id per token or −1, term strings, sentence-end flag per token)."""
    pieces = tok.token_bytes()
    texts = [p.decode("utf-8", errors="replace") for p in pieces]
    norm = [t.strip().lower() for t in texts]
    ok = [bool(re.search(r"[0-9a-zÀ-￿]", n)) and "�" not in n for n in norm]
    vocab = sorted({n for n, g in zip(norm, ok) if g})
    index = {t: i for i, t in enumerate(vocab)}
    term_of = np.array([index[n] if g else -1 for n, g in zip(norm, ok)], dtype=np.int32)
    ends = np.array([t.rstrip(" ").endswith((".", "!", "?")) or "\n" in t for t in texts], dtype=np.bool_)
    ends[EOS] = True
    return term_of, vocab, ends


# ---------------------------------------------------------------------------
# sentence segmentation and inverted index (numba)
# ---------------------------------------------------------------------------

@numba.njit(cache=True)
def _segment(tokens, ends, max_len):
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
        if ends[t] or i - s + 1 >= max_len:
            starts[k] = s
            lens[k] = i - s + 1
            k += 1
            s = -1
    if s >= 0:
        starts[k] = s
        lens[k] = n - s
        k += 1
    return starts[:k], lens[:k]


@numba.njit(cache=True)
def _index(tokens, starts, lens, term_of, n_terms):
    """CSR postings term → sentence ids (each sentence once per term) and the number of
    term tokens per sentence."""
    n_sent = len(starts)
    counts = np.zeros(n_terms + 1, dtype=np.int64)
    last = np.full(n_terms, -1, dtype=np.int64)
    sent_terms = np.zeros(n_sent, dtype=np.int32)
    for s in range(n_sent):
        for i in range(starts[s], starts[s] + lens[s]):
            tm = term_of[tokens[i]]
            if tm < 0:
                continue
            sent_terms[s] += 1
            if last[tm] != s:
                last[tm] = s
                counts[tm + 1] += 1
    ptr = np.cumsum(counts)
    post = np.empty(ptr[-1], dtype=np.int32)
    fill = ptr[:-1].copy()
    last[:] = -1
    for s in range(n_sent):
        for i in range(starts[s], starts[s] + lens[s]):
            tm = term_of[tokens[i]]
            if tm < 0 or last[tm] == s:
                continue
            last[tm] = s
            post[fill[tm]] = s
            fill[tm] += 1
    return ptr, post, sent_terms


@numba.njit(cache=True)
def _bm25_acc(qterms, qidf, ptr, post, sent_terms, avglen, acc, mark):
    """Accumulate BM25 into ``acc``; returns the touched sentence ids (``mark`` avoids
    duplicates and is reset afterwards)."""
    total = 0
    for j in range(len(qterms)):
        total += ptr[qterms[j] + 1] - ptr[qterms[j]]
    touched = np.empty(total, dtype=np.int64)
    k = 0
    for j in range(len(qterms)):
        t = qterms[j]
        w = qidf[j]
        for p in range(ptr[t], ptr[t + 1]):
            s = post[p]
            if not mark[s]:
                mark[s] = True
                touched[k] = s
                k += 1
            norm = K1 * (1.0 - B + B * sent_terms[s] / avglen)
            acc[s] += w * (K1 + 1.0) / (1.0 + norm)
    touched = touched[:k]
    scores = np.empty(k, dtype=np.float64)
    for i in range(k):
        s = touched[i]
        scores[i] = acc[s]
        acc[s] = 0.0
        mark[s] = False
    return touched, scores


def top_k(ids: np.ndarray, scores: np.ndarray, k: int):
    """The k best (score desc, id asc) — deterministic, ties broken by id."""
    if len(ids) > k:
        kth = np.partition(scores, len(scores) - k)[len(scores) - k]
        above = scores > kth
        tie = np.flatnonzero(scores == kth)
        need = k - int(above.sum())
        keep = np.concatenate([np.flatnonzero(above), tie[np.argsort(ids[tie], kind="stable")][:need]])
        ids, scores = ids[keep], scores[keep]
    order = np.lexsort((ids, -scores))
    return ids[order], scores[order]


@numba.njit(cache=True)
def _soft_match(q_tok, q_idf, s_toks, eng):
    """Σ_q idf(q) · max_s sim(eng[q], eng[s]) / Σ idf, sim = max(0, 1 − ham/1024)."""
    W = eng.shape[1]
    num = 0.0
    den = 0.0
    for a in range(len(q_tok)):
        best = 0.0
        qa = q_tok[a]
        for b in range(len(s_toks)):
            sb = s_toks[b]
            if sb == qa:
                best = 1.0
                break
            h = 0
            for k in range(W):
                h += popcount64(eng[qa, k] ^ eng[sb, k])
            sim = 1.0 - h / 1024.0
            if sim > best:
                best = sim
        num += q_idf[a] * best
        den += q_idf[a]
    return num / den if den > 0 else 0.0


# ---------------------------------------------------------------------------
# index object
# ---------------------------------------------------------------------------

@dataclass
class SentenceIndex:
    starts: np.ndarray        # int64 stream position of each sentence
    lens: np.ndarray          # int32 tokens per sentence
    ptr: np.ndarray           # int64 CSR pointers per term
    post: np.ndarray          # int32 sentence ids
    sent_terms: np.ndarray    # int32 term tokens per sentence
    term_of: np.ndarray       # int32 term id per token
    terms: list[str]

    @classmethod
    def build(cls, tokens: np.ndarray, tok) -> SentenceIndex:
        term_of, terms, ends = term_table(tok)
        t = np.ascontiguousarray(tokens, dtype=np.uint16)
        starts, lens = _segment(t, ends, MAX_SENT)
        ptr, post, sent_terms = _index(t, starts, lens, term_of, len(terms))
        return cls(starts, lens, ptr, post, sent_terms, term_of, terms)

    @property
    def n(self) -> int:
        return len(self.starts)

    def idf(self) -> np.ndarray:
        df = np.diff(self.ptr).astype(np.float64)
        return np.log(1.0 + (self.n - df + 0.5) / (df + 0.5))

    def save(self, d: Path) -> None:
        d.mkdir(parents=True, exist_ok=True)
        for name in ("starts", "lens", "ptr", "post", "sent_terms", "term_of"):
            np.save(d / f"{name}.npy", getattr(self, name))
        (d / "terms.txt").write_text("\n".join(self.terms) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, d: Path, mmap: bool = False) -> SentenceIndex:
        arrs = {n: np.load(d / f"{n}.npy", mmap_mode="r" if mmap else None)
                for n in ("starts", "lens", "ptr", "post", "sent_terms", "term_of")}
        terms = (d / "terms.txt").read_text(encoding="utf-8").split("\n")[:-1]
        return cls(terms=terms, **arrs)


# ---------------------------------------------------------------------------
# the engine
# ---------------------------------------------------------------------------

@dataclass
class Answer:
    question: str
    text: str | None                 # None = "I don't know"
    source: dict | None
    score: float
    confidence: float                # score / Σ idf of the question terms
    candidates: list[dict]
    seconds: float


class ChatEngine:
    def __init__(self, model, index: SentenceIndex, alpha: float = 0.0, theta: float = 0.0,
                 df_cap: float = DF_CAP):
        self.model = model
        self.index = index
        self.alpha = float(alpha)
        self.theta = float(theta)
        self.idf = index.idf()
        self.df_cap = df_cap * index.n
        self.df = np.diff(index.ptr)
        self.avglen = float(index.sent_terms.mean()) if index.n else 1.0
        self._user_key = None
        self._user = None
        self._acc = None
        self._mark = None

    # -- question → terms ------------------------------------------------------------

    def _query(self, question: str):
        ids = self.model.tok.encode(question)
        seen, qterms, qtoks = set(), [], []
        for t in ids:
            tm = int(self.index.term_of[t])
            if tm < 0 or tm in seen or self.df[tm] > self.df_cap:
                continue
            seen.add(tm)
            qterms.append(tm)
            qtoks.append(int(t))
        qterms = np.asarray(qterms, dtype=np.int64)
        return qterms, self.idf[qterms], np.asarray(qtoks, dtype=np.int64)

    # -- user texts (taught with learn) ---------------------------------------------------

    def _user_sentences(self):
        """(sentence token arrays, source ids) of the live user texts; cached per state."""
        key = tuple(sorted(self.model.user_texts.items()))
        if key != self._user_key:
            sents = []
            ends = term_table_ends(self)
            for sid, text in sorted(self.model.user_texts.items()):
                ids = np.asarray(self.model.tok.encode(text), dtype=np.uint16)
                starts, lens = _segment(np.concatenate([ids, [EOS]]).astype(np.uint16), ends, MAX_SENT)
                for s, n in zip(starts, lens):
                    sents.append((ids[s:s + n], sid))
            self._user_key, self._user = key, sents
        return self._user

    def _bm25_one(self, toks: np.ndarray, qterms, qidf) -> float:
        terms = self.index.term_of[toks]
        present = set(int(x) for x in terms if x >= 0)
        n_terms = int((terms >= 0).sum())
        norm = K1 * (1.0 - B + B * n_terms / self.avglen)
        return float(sum(w * (K1 + 1.0) / (1.0 + norm) for t, w in zip(qterms, qidf) if int(t) in present))

    # -- ranking ---------------------------------------------------------------------------

    def rank(self, question: str, alpha: float | None = None, top: int = TOP_BM25):
        """Candidates as (score, bm25, soft, kind, ref) sorted best first; kind 'base' with
        ref = sentence id, 'user' with ref = (tokens, source id)."""
        alpha = self.alpha if alpha is None else alpha
        qterms, qidf, qtoks = self._query(question)
        if len(qterms) == 0:
            return [], 0.0, (qterms, qidf, qtoks)
        if self._acc is None:
            self._acc = np.zeros(self.index.n, dtype=np.float64)
            self._mark = np.zeros(self.index.n, dtype=np.bool_)
        ids, sc = _bm25_acc(qterms, qidf, self.index.ptr, self.index.post, self.index.sent_terms,
                            self.avglen, self._acc, self._mark)
        cand, bm = top_k(ids, sc, top)
        eng = self.model.cb.eng
        tokens = self.model.tokens
        rows = []
        for s, b in zip(cand, bm):
            st = int(self.index.starts[s])
            toks = np.asarray(tokens[st:st + int(self.index.lens[s])], dtype=np.int64)
            toks = toks[self.index.term_of[toks] >= 0]
            soft = _soft_match(qtoks, qidf, toks, eng) if alpha else 0.0
            rows.append((b + alpha * soft * float(qidf.sum()), b, soft, "base", int(s)))
        for toks, sid in self._user_sentences():
            b = self._bm25_one(toks, qterms, qidf)
            if b <= 0:
                continue
            tt = toks.astype(np.int64)
            soft = _soft_match(qtoks, qidf, tt[self.index.term_of[tt] >= 0], eng) if alpha else 0.0
            rows.append((b + alpha * soft * float(qidf.sum()), b, soft, "user", (toks, sid)))
        rows.sort(key=lambda r: (-r[0], 0 if r[3] == "user" else 1, r[4] if r[3] == "base" else r[4][1]))
        return rows, float(qidf.sum()), (qterms, qidf, qtoks)

    def sentence_text(self, row) -> str:
        if row[3] == "user":
            return self.model.tok.decode(row[4][0]).strip()
        s = row[4]
        st = int(self.index.starts[s])
        return self.model.tok.decode(self.model.tokens[st:st + int(self.index.lens[s])]).strip()

    def source(self, row) -> dict:
        if row[3] == "user":
            return {"kind": "user", "source": row[4][1]}
        return self.model._describe(int(self.index.starts[row[4]]))

    def answer(self, question: str, n_alternatives: int = 3) -> Answer:
        t0 = time.time()
        rows, idf_sum, _ = self.rank(question)
        if not rows:
            return Answer(question, None, None, 0.0, 0.0, [], time.time() - t0)
        best = rows[0]
        conf = best[0] / idf_sum if idf_sum > 0 else 0.0
        cands = [{"text": self.sentence_text(r), "source": self.source(r), "score": r[0]}
                 for r in rows[:1 + n_alternatives]]
        text = cands[0]["text"] if conf >= self.theta else None
        return Answer(question, text, cands[0]["source"] if text else None, best[0], conf, cands,
                      time.time() - t0)


def term_table_ends(engine: ChatEngine) -> np.ndarray:
    if not hasattr(engine, "_ends"):
        engine._ends = term_table(engine.model.tok)[2]
    return engine._ends


# ---------------------------------------------------------------------------
# answer checking (SQuAD normalisation)
# ---------------------------------------------------------------------------

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = frozenset(string.punctuation)


def normalize(s: str) -> str:
    """The official SQuAD v1.1 normalisation: lower case, drop ASCII punctuation,
    drop articles, collapse white space."""
    s = "".join(ch for ch in s.lower() if ch not in _PUNCT)
    s = _ARTICLES.sub(" ", s)
    return " ".join(s.split())


def contains_answer(sentence: str, answers: list[str]) -> bool:
    ns = " " + normalize(sentence) + " "
    return any((" " + normalize(a) + " ") in ns for a in answers if normalize(a))
