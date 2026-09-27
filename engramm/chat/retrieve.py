"""Stage 1.1 — finding the sentence (docs/PREREG_CHAT_V2.md).

Candidates: the BM25 top-N of stage 1, plus the sentence *after* each of the best
candidates (answers often follow the sentence that names the topic).

Each candidate gets features, all counts or bit arithmetic:

=========  ==================================================================
bm25       stage-1 BM25
cov        idf-weighted share of the question terms in the sentence
soft       S_HDC of stage 1 (meaning-vector soft match)
pcov       share of the question terms missing from the sentence but found in
           the two sentences before it (same document)
kcov       share of the question terms in the document's title / URL
tmatch     the sentence holds a span of the expected answer type that is not
           part of the question
wiki       the sentence comes from Wikipedia
isq        the sentence is itself a question (ends with "?")
short      fewer than 6 words
=========  ==================================================================

score = bm25 + Σidf · (w_cov·cov + w_soft·soft + w_pcov·pcov + w_kcov·kcov
        + w_type·tmatch + w_wiki·wiki − w_q·isq − w_short·short); weights on dev.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from engramm.chat.question import Question, analyse, spans, type_matches, words
import numba

from engramm.lm.chat import DF_CAP, B, K1, _bm25_acc, _soft_match, top_k

FEATURES = ("bm25", "cov", "soft", "pcov", "kcov", "tmatch", "wiki", "isq", "short", "phr", "dcov", "prox", "dfull")


@dataclass(frozen=True)
class Weights:
    cov: float = 2.0
    soft: float = 0.0
    pcov: float = 0.0
    kcov: float = 0.0
    type: float = 0.0
    wiki: float = 0.0
    q: float = 0.0
    short: float = 0.0
    phr: float = 0.0
    dcov: float = 0.0
    prox: float = 0.0
    dfull: float = 0.0

    def vector(self) -> np.ndarray:
        """Weights aligned with FEATURES (bm25 has weight 1 and is not scaled by Σidf)."""
        return np.array([0.0, self.cov, self.soft, self.pcov, self.kcov, self.type, self.wiki, -self.q,
                         -self.short, self.phr, self.dcov, self.prox, self.dfull])


@dataclass
class Query:
    text: str
    q: Question
    terms: np.ndarray            # int64 term ids (deduplicated, df-capped)
    idf: np.ndarray
    toks: np.ndarray             # one token per term (for the soft match)
    strings: list[str]           # term strings
    bigrams: dict = field(default_factory=dict)   # (term, next term) in question order → weight

    @property
    def idf_sum(self) -> float:
        return float(self.idf.sum())


@dataclass
class Candidates:
    query: Query
    ids: np.ndarray              # sentence ids
    feats: np.ndarray            # (n, len(FEATURES))
    texts: list[str] = field(default_factory=list)

    def scores(self, w: Weights) -> np.ndarray:
        f = self.feats
        return f[:, 0] + self.query.idf_sum * (f @ w.vector())

    def order(self, w: Weights) -> np.ndarray:
        """Candidate positions best first (score desc, sentence id asc)."""
        return np.lexsort((self.ids, -self.scores(w)))


@numba.njit(cache=True)
def _bm25_list(tokens, starts, lens, term_of, qmask, sids, avglen):
    out = np.zeros(len(sids), dtype=np.float64)
    seen = np.zeros(len(qmask), dtype=np.int64) - 1
    for k in range(len(sids)):
        s = sids[k]
        n_terms = 0
        for i in range(starts[s], starts[s] + lens[s]):
            if term_of[tokens[i]] >= 0:
                n_terms += 1
        norm = K1 * (1.0 - B + B * n_terms / avglen)
        acc = 0.0
        for i in range(starts[s], starts[s] + lens[s]):
            t = term_of[tokens[i]]
            if t >= 0 and qmask[t] > 0 and seen[t] != k:
                seen[t] = k
                acc += qmask[t] * (K1 + 1.0) / (1.0 + norm)
        out[k] = acc
    return out


@numba.njit(cache=True)
def _stats(tokens, starts, lens, sent_doc, term_of, qidx, qidf, pidx, bw, ids):
    """Per candidate: bitmask of question terms present, Σidf present, Σ bigram weights of
    distinct adjacent question-term pairs, compactness, Σidf of missing terms found in the
    two previous sentences of the same document."""
    n = len(ids)
    nq = len(qidf)
    mask = np.zeros(n, dtype=np.uint64)
    cov = np.zeros(n)
    phr = np.zeros(n)
    prox = np.zeros(n)
    pcov = np.zeros(n)
    npz = bw.shape[0]
    pairs = np.zeros((max(npz, 1), max(npz, 1)), dtype=np.bool_)
    for k in range(n):
        s = ids[k]
        m = np.uint64(0)
        prev_q = -1
        first = -1
        last = -1
        tpos = 0
        for a in range(npz):
            for b in range(npz):
                pairs[a, b] = False
        for i in range(starts[s], starts[s] + lens[s]):
            t = term_of[tokens[i]]
            if t < 0:
                continue
            q = qidx[t]
            if q >= 0:
                m |= np.uint64(1) << np.uint64(q)
                if first < 0:
                    first = tpos
                last = tpos
            pq = pidx[t]
            if pq >= 0 and prev_q >= 0 and prev_q != pq and not pairs[prev_q, pq]:
                pairs[prev_q, pq] = True
                phr[k] += bw[prev_q, pq]
            prev_q = pq
            tpos += 1
        mask[k] = m
        matched = 0
        for j in range(nq):
            if (m >> np.uint64(j)) & np.uint64(1):
                cov[k] += qidf[j]
                matched += 1
        if matched >= 2:
            prox[k] = matched / (last - first + 1)
        pm = np.uint64(0)
        p = s
        for _ in range(2):
            if p <= 0 or sent_doc[p - 1] != sent_doc[s]:
                break
            p -= 1
            for i in range(starts[p], starts[p] + lens[p]):
                t = term_of[tokens[i]]
                if t >= 0 and qidx[t] >= 0:
                    pm |= np.uint64(1) << np.uint64(qidx[t])
        missing = pm & ~m
        for j in range(nq):
            if (missing >> np.uint64(j)) & np.uint64(1):
                pcov[k] += qidf[j]
    return mask, cov, phr, prox, pcov


class Retriever:
    def __init__(self, corpus, df_cap: float = DF_CAP, n_bm25: int = 300, n_expand: int = 30, n_docs: int = 5,
                 per_doc: int = 60):
        self.c = corpus
        ix = corpus.index
        self.ix = ix
        self.idf = ix.idf()
        self.df = np.diff(np.asarray(ix.ptr))
        self.df_cap = df_cap * ix.n
        self.avglen = float(np.asarray(ix.sent_terms).mean())
        self.n_bm25, self.n_expand, self.n_top_docs, self.per_doc = n_bm25, n_expand, n_docs, per_doc
        self._dscore = np.zeros(corpus.n_docs, dtype=np.float64) if corpus.doc_ptr is not None else None
        self._acc = np.zeros(ix.n, dtype=np.float64)
        self._mark = np.zeros(ix.n, dtype=np.bool_)
        self.term_of = np.asarray(ix.term_of)

    # -- question ------------------------------------------------------------------------

    def query(self, question: str) -> Query:
        ids = self.c.tok.encode(question)
        seen, terms, toks = set(), [], []
        for t in ids:
            tm = int(self.term_of[t])
            if tm < 0 or tm in seen or self.df[tm] > self.df_cap:
                continue
            seen.add(tm)
            terms.append(tm)
            toks.append(int(t))
        seq = [int(self.term_of[t]) for t in ids if self.term_of[t] >= 0]
        bigrams = {}
        for a, b in zip(seq, seq[1:]):
            if a != b and (self.df[a] <= self.df_cap or self.df[b] <= self.df_cap):
                bigrams[(a, b)] = float(self.idf[a] + self.idf[b]) / 2.0
        terms = np.asarray(terms, dtype=np.int64)
        return Query(question, analyse(question), terms, self.idf[terms], np.asarray(toks, dtype=np.int64),
                     [self.ix.terms[t] for t in terms], bigrams)

    # -- candidates ------------------------------------------------------------------------

    def _bm25_many(self, sids: np.ndarray, query: Query) -> np.ndarray:
        qmask = np.zeros(len(self.ix.terms), dtype=np.float64)
        qmask[query.terms] = query.idf
        return _bm25_list(self.c.tokens, self.ix.starts, self.ix.lens, self.term_of, qmask,
                          np.asarray(sids, dtype=np.int64), self.avglen)

    def candidates(self, query: Query | str, weights: Weights | None = None, text_k: int | None = None
                   ) -> Candidates:
        """All candidates with features. With ``weights`` and ``text_k``, the text features
        (answer type, question sentence, length) are computed only for the ``text_k`` best by
        the other features, and the rest are dropped (the fast path used when answering)."""
        if isinstance(query, str):
            query = self.query(query)
        if len(query.terms) == 0:
            return Candidates(query, np.zeros(0, dtype=np.int64), np.zeros((0, len(FEATURES))), [])
        ix = self.ix
        ids, sc = _bm25_acc(query.terms, query.idf, ix.ptr, ix.post, ix.sent_terms, self.avglen, self._acc,
                            self._mark)
        ids, sc = top_k(ids, sc, self.n_bm25)
        ids = [int(x) for x in ids]
        have = set(ids)
        extra = []
        for s in ids[:self.n_expand]:
            nxt = s + 1
            if nxt < ix.n and nxt not in have and self.c.sent_doc[nxt] == self.c.sent_doc[s]:
                have.add(nxt)
                extra.append(nxt)
        dfull = self.doc_scores(query)
        if dfull is not None and self.n_top_docs:
            docs, _ = dfull
            starts = ix.starts
            for d in docs[:self.n_top_docs]:
                lo, hi = self.c.doc_sentences(int(d))
                if hi <= lo:
                    continue
                a = int(starts[lo])
                b = int(starts[hi - 1]) + int(ix.lens[hi - 1])
                tm = self.term_of[np.asarray(self.c.tokens[a:b])]
                pos = np.flatnonzero(np.isin(tm, query.terms)) + a
                sids = np.unique(np.searchsorted(np.asarray(starts[lo:hi]), pos, side="right") - 1 + lo)
                added = 0
                for s in sids:
                    s = int(s)
                    if s not in have:
                        have.add(s)
                        extra.append(s)
                        added += 1
                        if added >= self.per_doc:
                            break
        all_ids = np.asarray(ids + extra, dtype=np.int64)
        bm = np.concatenate([np.asarray(sc, dtype=np.float64), self._bm25_many(np.asarray(extra, dtype=np.int64),
                                                                                query)])
        return self.featurise(query, all_ids, bm, dfull, weights, text_k)

    def doc_scores(self, query: Query):
        """(documents best first, their idf-weighted term coverage), or None without a doc index."""
        if self._dscore is None or len(query.terms) == 0:
            return None
        c = self.c
        nd = c.n_docs
        touched = []
        dsum = 0.0
        for t in query.terms:
            docs = np.asarray(c.doc_post[c.doc_ptr[t]:c.doc_ptr[t + 1]])
            w = float(np.log(1.0 + (nd - len(docs) + 0.5) / (len(docs) + 0.5)))
            dsum += w
            self._dscore[docs] += w
            touched.append(docs)
        allt = np.unique(np.concatenate(touched)) if touched else np.zeros(0, dtype=np.int64)
        vals = self._dscore[allt] / (dsum or 1.0)
        self._dscore[allt] = 0.0
        order = np.lexsort((allt, -vals))
        return allt[order], vals[order]

    def featurise(self, query: Query, ids: np.ndarray, bm25: np.ndarray, dfull=None,
                  weights: Weights | None = None, text_k: int | None = None) -> Candidates:
        c, ix = self.c, self.ix
        isum = query.idf_sum or 1.0
        nq = min(len(query.terms), 64)
        qidx = np.full(len(ix.terms), -1, dtype=np.int32)
        qidx[query.terms[:nq]] = np.arange(nq, dtype=np.int32)
        pterms = sorted({t for pair in query.bigrams for t in pair})[:64]
        pidx = np.full(len(ix.terms), -1, dtype=np.int32)
        pidx[np.asarray(pterms, dtype=np.int64)] = np.arange(len(pterms), dtype=np.int32)
        bw = np.zeros((len(pterms), len(pterms)), dtype=np.float64)
        for (a, b), w in query.bigrams.items():
            ia, ib = pidx[a], pidx[b]
            if ia >= 0 and ib >= 0:
                bw[ia, ib] = w
        mask, cov, phr, prox, pcov = _stats(c.tokens, ix.starts, ix.lens, c.sent_doc, self.term_of, qidx,
                                            query.idf[:nq].astype(np.float64), pidx, bw, ids)
        feats = np.zeros((len(ids), len(FEATURES)))
        F = {n: i for i, n in enumerate(FEATURES)}
        feats[:, F["bm25"]] = bm25
        feats[:, F["cov"]] = cov / isum
        feats[:, F["phr"]] = phr / isum
        feats[:, F["prox"]] = prox
        feats[:, F["pcov"]] = pcov / isum
        docs = c.sent_doc[ids].astype(np.int64)
        # document-level features
        dmask: dict[int, int] = {}
        for d, m in zip(docs.tolist(), mask.tolist()):
            dmask[d] = dmask.get(d, 0) | m
        qi = query.idf[:nq]
        bitw = {}
        for d, m in dmask.items():
            bitw[d] = sum(float(qi[j]) for j in range(nq) if (m >> j) & 1) / isum
        feats[:, F["dcov"]] = [bitw[d] for d in docs.tolist()]
        if dfull is not None:
            dd, dv = dfull
            srt = np.argsort(dd, kind="stable")
            dd_s, dv_s = dd[srt], dv[srt]
            pos = np.searchsorted(dd_s, docs)
            pos = np.minimum(pos, len(dd_s) - 1)
            feats[:, F["dfull"]] = np.where(dd_s[pos] == docs, dv_s[pos], 0.0) if len(dd_s) else 0.0
        kcache: dict[int, float] = {}
        for k, d in enumerate(docs.tolist()):
            if d not in kcache:
                kw = c.key_words(d)
                kcache[d] = sum(float(w) for w, st in zip(query.idf, query.strings) if st in kw) / isum
            feats[k, F["kcov"]] = kcache[d]
            feats[k, F["wiki"]] = float(c.doc_keys[d][0].startswith("wiki"))
        for k, s in enumerate(ids.tolist()):
            toks = c.sentence_tokens(s)
            content = toks[self.term_of[toks] >= 0].astype(np.int64)
            feats[k, F["soft"]] = _soft_match(query.toks, query.idf, content, c.eng) if len(content) else 0.0
        # text features
        if weights is not None and text_k is not None and len(ids) > text_k:
            pre = feats[:, 0] + isum * (feats @ weights.vector())
            keep = np.lexsort((ids, -pre))[:text_k]
            keep.sort()
            ids, feats = ids[keep], feats[keep]
        texts = []
        qwords = set(query.q.words)
        for k, s in enumerate(ids.tolist()):
            text = c.sentence_text(s)
            texts.append(text)
            tmatch = 0.0
            if query.q.atype != "OTHER":
                for sp in spans(text):
                    if type_matches(query.q.atype, sp) and not (set(w.lower() for w in words(sp.text)) <= qwords):
                        tmatch = 1.0
                        break
            feats[k, F["tmatch"]] = tmatch
            feats[k, F["isq"]] = float(text.rstrip('"”’\') ').endswith("?"))
            feats[k, F["short"]] = float(len(words(text)) < 6)
        return Candidates(query, ids, feats, texts)

    def rank(self, question: str, w: Weights) -> tuple[Candidates, np.ndarray]:
        cands = self.candidates(question)
        return cands, cands.order(w)
