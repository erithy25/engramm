"""Stage 4 — a short answer instead of a whole sentence (docs/PREREG_CHAT_V2.md).

From the best K sentences, candidate spans are collected:

* typed questions (who/when/where/how many/…): spans of the expected type
  (names, dates, numbers — ``question.spans``);
* other questions: chunks of consecutive content words (a noun-phrase proxy).

Spans made only of question words are dropped. Each occurrence votes with

    weight = sentence weight × exp(−distance / λ)

where the sentence weight falls with the retrieval score (softmax with temperature
τ over Σidf-normalised scores) and ``distance`` is the word distance to the nearest
question word in that sentence. Votes of the same normalised span are added up
(redundancy across sentences), and a short span that is part of a longer winning
name gives its votes to it. The answer is the span with the most votes; its
confidence is its share of all votes times the best sentence's normalised score.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from engramm.chat.question import (CONNECT, DATE, OTHER, STOP, Question, Span, spans, type_matches, words)
from engramm.lm.chat import normalize

PUNCT_BREAK = frozenset(",.;:!?()[]{}\"“”‘’'—–-/")


@dataclass(frozen=True)
class ExtractParams:
    k: int = 10                 # sentences considered
    tau: float = 0.15           # softmax temperature on score/Σidf
    lam: float = 4.0            # distance decay (words)
    other_max: int = 4          # longest chunk for untyped questions
    type_only: bool = True      # typed questions: only spans of the expected type
    soft_min: float = 0.0       # HDC anchors: meaning similarity above which a sentence word counts as a
                                # (weaker) match of a question word; 0 = off
    definition: float = 2.0     # weight of the "X is <answer>" candidate for "What is X?" questions
    head_beta: float = 0.0      # HDC type match: votes × exp(β·(sim(candidate, head noun) − 0.5)); 0 = off
    copula: float = 0.0         # weight of the subject for "Which is the Y?" when the sentence says "X … is the Y"
    direction: float = 0.0      # bonus for candidates on the answer side of the anchors (before them for
                                # subject questions "Who wrote …", after them for "What did X …")
    nb: float = 0.0             # > 0: choose spans with the counted statistics (spanstats), temperature 1/nb
    nb_prox: float = 0.0        # extra weight of the proximity heuristic in the counted mode
    rule_types: tuple = ()      # expected answer types that keep the rule mode even when counting is on
    merge: float = 0.5          # share of a short span's votes that also count for longer spans containing it
    conf_power: float = 1.0     # confidence = (vote share)^power × best sentence score (counted mode)
    sent_beta: float = 0.0      # > 0: one softmax over the candidates of all K sentences, score + β·log(sentence
                                # weight) (else each sentence spreads its own weight)
    mbr: float = 0.0            # > 0: choose among the top `mbr_n` spans by (1 − mbr)·vote share + mbr·expected
    mbr_n: int = 10             # token F1 against all voted spans (minimum Bayes risk for the F1 measure)
    mbr_temp: float = 1.0       # the expectation uses vote^mbr_temp (renormalised); < 1 flattens it
    choice: bool = False        # "X or Y?" questions: answer with the option the best sentences contain
    len_bonus: float = 0.0      # counted mode: + len_bonus × (words − 1) on a candidate's score (max 5 words)
    conf_r0: float = 1.0        # confidence = share^conf_power × r0^conf_r0 × (1 + conf_ns × sentences whose
    conf_ns: float = 0.0        # candidates include the answer)


@dataclass
class Extracted:
    text: str | None
    confidence: float
    sentence: int               # candidate position of the sentence the answer was taken from
    votes: list[tuple[str, float]]


def chunks(ws: list[str], lw: list[str], max_len: int) -> list[Span]:
    """Runs of content words (no stop words, no punctuation), at most ``max_len`` long;
    'of' may join two runs ("University of Notre Dame")."""
    out, i, n = [], 0, len(ws)
    while i < n:
        if lw[i] in STOP or ws[i] in PUNCT_BREAK or not ws[i][0].isalnum():
            i += 1
            continue
        j = i + 1
        while j < n and (lw[j] not in STOP and ws[j] not in PUNCT_BREAK and ws[j][0].isalnum()
                         or (lw[j] in CONNECT and j + 1 < n and lw[j + 1] not in STOP and ws[j + 1][0].isalnum()
                             and j > i)):
            j += 1
        for a in range(i, j):
            for b in range(a + 1, min(j, a + max_len) + 1):
                if lw[a] in CONNECT or lw[b - 1] in CONNECT:
                    continue
                out.append(Span(" ".join(ws[a:b]), "CHUNK", a, b))
        i = j
    return out


def _qword_positions(lw: list[str], qwords: set) -> list[int]:
    return [i for i, w in enumerate(lw) if w in qwords and w not in STOP]


_SPAN_MEMO: dict = {}


def _spans(text: str, initial_is_name):
    key = (text, id(initial_is_name))
    v = _SPAN_MEMO.get(key)
    if v is None:
        if len(_SPAN_MEMO) > 200_000:
            _SPAN_MEMO.clear()
        v = spans(text, initial_is_name)
        _SPAN_MEMO[key] = v
    return v


_YEARLIKE = re.compile(r"(\d{3,4}(?:\s(?:BC|BCE|AD|CE))?|AD\s\d{1,4})$")


def date_granularity(q: Question, sp: Span) -> str | None:
    """Reduce a date span to what the question asks for (year / decade / century / month)."""
    qw = set(q.words)
    t = sp.text
    if "year" in qw or "years" in qw:
        m = re.search(r"(\d{3,4}\s(?:BC|BCE|AD|CE)|AD\s\d{1,4}|\d{3,4})(?!\d)", t)
        return m.group(1) if m else None
    if "decade" in qw:
        return t if re.fullmatch(r"\d{3}0s", t) else None
    if "century" in qw or "centuries" in qw:
        return t if "century" in t.lower() else None
    if "month" in qw:
        m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)", t)
        return m.group(1) if m else None
    return t


_AUX = frozenset(("did", "does", "do", "was", "were", "is", "are", "has", "have", "had", "can", "could", "will",
                  "would", "should", "may", "might"))


def question_direction(q: Question) -> int:
    """−1: the answer is the subject ("Who wrote X?"), +1: it follows the verb ("What did X write?"), 0: unknown."""
    ws = [w for w in q.words if w[0].isalnum()]
    for i, w in enumerate(ws):
        if w in ("what", "which", "who", "whom", "whose"):
            j = i + 1
            if w in ("what", "which", "whose") and j < len(ws) and ws[j] not in _AUX and ws[j] not in STOP:
                j += 1
            if j < len(ws):
                return 1 if ws[j] in _AUX else -1
            return 0
    return 0


_COP_Q = re.compile(r"^(?:what|which|who)\s+(?:is|are|was|were)\s+(?:the\s+)?(?P<y>.+?)\??$", re.I)


def copula_subject(q: Question, text: str) -> str | None:
    """For "Which is the tallest building in X?": the sentence subject of "S …, is the tallest building"."""
    m = _COP_Q.match(q.text.strip())
    if not m:
        return None
    y = [w.lower() for w in words(m.group("y")) if w[0].isalnum() and w.lower() not in STOP]
    if len(y) < 2:
        return None
    ws = words(text)
    lw = [w.lower() for w in ws]
    for i in range(len(lw) - 1):
        if lw[i] in ("is", "was", "are", "were") and i + 1 < len(lw):
            after = [w for w in lw[i + 1:i + 1 + 2 * len(y) + 2] if w not in STOP]
            if sum(1 for w in y if w in after) >= max(2, len(y) - 1):
                j = 0
                while j < i and ws[j] not in (",", "(") and j < 8:
                    j += 1
                subj = " ".join(ws[:j])
                return subj if subj and j < i + 1 else None
    return None


_DEF_Q = re.compile(r"^(?:what|who)\s+(?:is|are|was|were)\s+(?:an?\s+|the\s+)?(?P<x>.+?)\??$", re.I)


def definition_span(q: Question, text: str) -> str | None:
    """For "What is X?": the phrase after "X … is/are/was/were" in the sentence."""
    m = _DEF_Q.match(q.text.strip())
    if not m or q.atype != OTHER:
        return None
    xw = [w.lower() for w in words(m.group("x")) if w[0].isalnum()]
    # "What was X called / used for / based on?" are not definitions
    if not xw or xw[-1].endswith("ed") or xw[-1] in ("for", "on", "in", "of", "to", "by", "from", "with", "as") \
            or len(xw) > 6:
        return None
    x = [w for w in xw if w not in STOP]
    if not x:
        return None
    ws = words(text)
    lw = [w.lower() for w in ws]
    last = -1
    for i, w in enumerate(lw):
        if w == x[-1]:
            last = i
            break
    if last < 0:
        return None
    j = last + 1
    while j < len(ws) and (ws[j] in ("(", ")") or (j > 0 and ws[j - 1] == "(") or lw[j].isupper()):
        j += 1
    while j < len(ws) and lw[j] not in ("is", "are", "was", "were", "refers", "means"):
        if ws[j] in (".", ";") or j - last > 6:
            return None
        j += 1
    if j >= len(ws):
        return None
    j += 1
    if j < len(ws) and lw[j] == "to":        # "refers to"
        j += 1
    k = j
    while k < len(ws) and ws[k] not in (".", ";", ",", ":", "(", ")") and k - j < 12:
        k += 1
    phrase = " ".join(ws[j:k]).replace(" -", "-").replace("- ", "-")
    return phrase or None


def extract_counted(q: Question, texts: list[str], rel: np.ndarray, p: ExtractParams, stats, info,
                    initial_is_name=None) -> Extracted:
    """The counted mode: each sentence spreads its weight over its candidates by
    softmax(nb · naive-Bayes score); votes of equal spans add up across sentences."""
    from engramm.chat.spanstats import features_for_sentence
    k = min(p.k, len(texts))
    r = np.asarray(rel[:k], dtype=np.float64)
    sw = np.exp((r - r.max()) / p.tau)
    sw /= sw.sum()
    votes: dict[str, float] = {}
    surface: dict[str, tuple[float, str, int]] = {}
    sent_keys: list[set] = []   # normalised candidates of each sentence (redundancy for the confidence)
    pooled = []                 # (sentence, span, score) for the global softmax
    for si in range(k):
        cands = features_for_sentence(q, texts[si], info, initial_is_name,
                                      extended=getattr(stats, "extended", False),
                                      domain=getattr(stats, "domain", False),
                                      max_chunk=getattr(stats, "max_chunk", 5))
        if not cands:
            continue
        sent_keys.append({normalize(sp.text) for sp, _ in cands})
        sc = np.array([stats.score(f) for _, f in cands]) * p.nb
        if p.len_bonus:
            sc += p.len_bonus * np.array([min(sp.end - sp.start, 6) - 1 for sp, _ in cands], dtype=np.float64)
        if p.nb_prox > 0:
            lw = [w.lower() for w in words(texts[si])]
            qc = set(q.content)
            anchors = [i for i, w in enumerate(lw) if w in qc]
            if anchors:
                for j, (sp, _) in enumerate(cands):
                    d = min(min(abs(sp.start - x), abs(x - (sp.end - 1))) for x in anchors)
                    sc[j] -= p.nb_prox * d / p.lam
        if q.atype == DATE:
            for j, (sp, _) in enumerate(cands):
                if sp.kind in ("DATE", "YEAR") and date_granularity(q, sp) not in (sp.text,):
                    sc[j] -= 2.0 * p.nb
        if p.sent_beta > 0:
            lsw = float(np.log(max(sw[si], 1e-300)))
            pooled += [(si, sp, float(x) + p.sent_beta * lsw) for (sp, _), x in zip(cands, sc)]
            continue
        e = np.exp(sc - sc.max())
        e /= e.sum()
        for (sp, _), pr in zip(cands, e):
            v = float(sw[si]) * float(pr)
            key = normalize(sp.text)
            if not key:
                continue
            votes[key] = votes.get(key, 0.0) + v
            best = surface.get(key)
            if best is None or v > best[0]:
                surface[key] = (v, sp.text, si)
    if pooled:
        allsc = np.array([x for _, _, x in pooled])
        e = np.exp(allsc - allsc.max())
        e /= e.sum()
        for (si, sp, _), pr in zip(pooled, e):
            v = float(pr)
            key = normalize(sp.text)
            if not key:
                continue
            votes[key] = votes.get(key, 0.0) + v
            best = surface.get(key)
            if best is None or v > best[0]:
                surface[key] = (v, sp.text, si)
    if not votes:
        return Extracted(None, 0.0, -1, [])
    keys = sorted(votes, key=lambda x: (-votes[x], x))
    merged = dict(votes)
    for a in keys[:30]:
        for b in keys[:30]:
            if a != b and len(b.split()) > len(a.split()) and f" {a} " in f" {b} ":
                merged[b] += votes[a] * p.merge
    order = sorted(merged, key=lambda x: (-merged[x], -len(x.split()), x))
    total = sum(votes.values())
    top = order[0]
    if p.mbr > 0:
        top = mbr_choice(order[:p.mbr_n], votes, merged, total, p.mbr, p.mbr_temp)
    conf = min(1.0, merged[top] / total) ** p.conf_power * max(float(r[0]), 0.0) ** p.conf_r0
    if p.conf_ns:
        conf *= 1.0 + p.conf_ns * sum(1 for ks in sent_keys if top in ks)
    return Extracted(surface[top][1], conf, surface[top][2], [(x, merged[x]) for x in order[:5]])


def token_f1(a: list[str], b: list[str]) -> float:
    """SQuAD token F1 of two normalised token lists."""
    if not a or not b:
        return 0.0
    rest: dict[str, int] = {}
    for w in b:
        rest[w] = rest.get(w, 0) + 1
    same = 0
    for w in a:
        if rest.get(w, 0) > 0:
            same += 1
            rest[w] -= 1
    if same == 0:
        return 0.0
    prec, rec = same / len(a), same / len(b)
    return 2 * prec * rec / (prec + rec)


def mbr_choice(cands: list[str], votes: dict[str, float], merged: dict[str, float], total: float,
               weight: float, temp: float = 1.0) -> str:
    """The candidate with the highest (1 − weight)·vote share + weight·expected F1, where the expectation
    runs over every voted span with its vote share. Ties keep the vote order of ``cands``."""
    toks = {k: k.split() for k in votes}
    dist = {k: v ** temp for k, v in votes.items()} if temp != 1.0 else votes
    dsum = sum(dist.values())
    best, best_s = cands[0], -1.0
    for a in cands:
        ta = toks.get(a) or a.split()
        ef1 = sum(v * token_f1(ta, toks[b]) for b, v in dist.items()) / dsum
        s = (1.0 - weight) * min(1.0, merged[a] / total) + weight * ef1
        if s > best_s + 1e-12:
            best, best_s = a, s
    return best


_AUX = frozenset(("is", "are", "was", "were", "do", "does", "did", "has", "have", "had", "can", "could", "would",
                  "will", "should", "may", "might", "must"))
_CUT = frozenset(("since", "than", "relative", "compared", "according", "when", "while", "because", "if"))


def choice_options(q: Question) -> list[str]:
    """The options of a question "… X or Y …?" (normalised), longest first: the words right after
    "or" up to a stop word or punctuation (at least one word, at most four), the same number of words
    before "or" (not across punctuation), and the single words next to "or"."""
    ws = words(q.text)
    lw = [w.lower() for w in ws]
    ors = [i for i, w in enumerate(lw) if w == "or"]
    if len(ors) != 1:
        return []
    k = ors[0]
    alpha = [w for w in lw if w[0].isalnum()]
    # a choice: a yes/no-form question ("Is it X or Y?"), or options after a colon ("…: X or Y?"),
    # or "which … X or Y?" ending with the options
    aux = bool(alpha) and alpha[0] in _AUX
    colon = ":" in ws[:k]
    ends = all(not w[0].isalnum() for w in ws[k + 1:][4:]) and "which" in alpha
    if not (aux or colon or ends):
        return []
    right = []
    for j in range(k + 1, min(len(ws), k + 5)):
        if not ws[j][0].isalnum() or (right and (lw[j] in STOP or lw[j] in _CUT)):
            break
        right.append(lw[j])
    left = []
    for j in range(k - 1, -1, -1):
        if len(left) == len(right) or not ws[j][0].isalnum() or (left and lw[j] in STOP):
            break
        left.insert(0, lw[j])
    if not left or not right:
        return []
    opts = [normalize(" ".join(left)), normalize(" ".join(right)), normalize(left[-1]), normalize(right[0])]
    out = []
    for o in opts:
        if o and o not in out:
            out.append(o)
    return sorted(out, key=lambda o: -len(o.split()))


def extract_choice(q: Question, texts: list[str], rel: np.ndarray, p: ExtractParams) -> Extracted | None:
    """For "X or Y?": the option contained in the most sentence weight (softmax over the K best
    sentences); ties go to the longer option. None when no option occurs or both occur equally."""
    opts = choice_options(q)
    if not opts:
        return None
    k = min(p.k, len(texts))
    r = np.asarray(rel[:k], dtype=np.float64)
    sw = np.exp((r - r.max()) / p.tau)
    sw /= sw.sum()
    ev = {o: 0.0 for o in opts}
    first = {o: -1 for o in opts}
    for si in range(k):
        t = f" {normalize(texts[si])} "
        for o in opts:
            if f" {o} " in t:
                ev[o] += float(sw[si])
                if first[o] < 0:
                    first[o] = si
    best = max(opts, key=lambda o: (ev[o], len(o.split())))
    if ev[best] <= 0:
        return None
    rivals = [o for o in opts if o != best and o not in best and best not in o]
    if any(ev[o] >= ev[best] for o in rivals):
        return None
    conf = ev[best] * max(float(r[0]), 0.0) ** p.conf_r0 * (1.0 + p.conf_ns)
    return Extracted(best, conf, first[best], [(o, ev[o]) for o in opts])


def extract(q: Question, texts: list[str], rel: np.ndarray, p: ExtractParams = ExtractParams(),
            initial_is_name=None, word_vec=None, stats=None, info=None) -> Extracted:
    if p.choice and texts:
        x = extract_choice(q, texts, rel, p)
        if x is not None:
            return x
    if p.nb > 0 and stats is not None and info is not None and q.atype not in p.rule_types:
        return extract_counted(q, texts, rel, p, stats, info, initial_is_name)
    """``texts`` best first, ``rel`` = their scores divided by Σidf (same order)."""
    if not texts:
        return Extracted(None, 0.0, -1, [])
    k = min(p.k, len(texts))
    r = np.asarray(rel[:k], dtype=np.float64)
    sw = np.exp((r - r.max()) / p.tau)
    sw /= sw.sum()
    qwords = set(w for w in q.words if w[0].isalnum())
    qcontent = set(q.content)
    qdir = question_direction(q) if p.direction > 0 else 0
    head_vecs = []
    if p.head_beta > 0 and word_vec is not None:
        heads = [q.head] if q.head and q.head not in STOP and q.head not in ("is", "was", "are", "were") else []
        if not heads:
            heads = {"PERSON": ["person"], "LOCATION": ["place"], "DATE": ["year"], "NUMBER": ["number"]}.get(
                q.atype, [])
        head_vecs = [v for v in (word_vec(h) for h in heads) if v is not None]
    votes: dict[str, float] = {}
    surface: dict[str, tuple[float, str, int]] = {}
    for si in range(k):
        text = texts[si]
        ws = words(text)
        lw = [w.lower() for w in ws]
        anchors = [(x, 1.0) for x in _qword_positions(lw, qcontent)]
        if p.soft_min > 0 and word_vec is not None:
            qvs = [v for v in (word_vec(w) for w in qcontent) if v is not None]
            if qvs:
                for i, w in enumerate(lw):
                    if w in qcontent or w in STOP or not w[0].isalpha():
                        continue
                    wv = word_vec(w)
                    if wv is None:
                        continue
                    best = max(1.0 - int(np.bitwise_count(wv ^ qv).sum()) / (64 * len(wv)) for qv in qvs)
                    if best > p.soft_min:
                        anchors.append((i, (best - p.soft_min) / (1.0 - p.soft_min)))
        if q.atype != OTHER:
            cands = [s for s in _spans(text, initial_is_name) if type_matches(q.atype, s)]
            if q.atype == DATE:
                red = []
                for s_ in cands:
                    t = date_granularity(q, s_)
                    if t:
                        red.append(Span(t, s_.kind, s_.start, s_.end))
                cands = red
            if not p.type_only and not cands:
                cands = chunks(ws, lw, p.other_max)
        else:
            cands = chunks(ws, lw, p.other_max)
        extra = []
        dphrase = definition_span(q, text) if p.definition > 0 else None
        if dphrase:
            extra.append((Span(dphrase, "DEF", 0, 0), p.definition))
        cphrase = copula_subject(q, text) if p.copula > 0 else None
        if cphrase:
            extra.append((Span(cphrase, "DEF", 0, 0), p.copula))
        for sp, prior in [(c, 1.0) for c in cands] + extra:
            sw_words = [w.lower() for w in words(sp.text) if w[0].isalnum()]
            if not sw_words or all(w in qwords or w in STOP for w in sw_words):
                continue
            # drop the question words at the edges of a span ("Paris" from "capital Paris")
            if q.atype == OTHER and sp.kind != "DEF" and (sw_words[0] in qwords or sw_words[-1] in qwords):
                continue
            # a number with the question's own noun ("eight provinces" for "how many provinces") → bare number
            if sp.kind == "NUMBER" and len(sw_words) > 1 and sw_words[-1] in qwords:
                continue
            # the rest of a name the question already gives ("West" of "Kanye West")
            if sp.kind == "NAME" and ((sp.start > 0 and lw[sp.start - 1] in qwords and ws[sp.start - 1][0].isupper())
                                      or (sp.end < len(ws) and lw[sp.end] in qwords and ws[sp.end][0].isupper())):
                continue
            if sp.kind == "DEF":
                prox = 1.0
            elif anchors:
                prox = max(w * math.exp(-min(abs(sp.start - x), abs(x - (sp.end - 1))) / p.lam) for x, w in anchors)
                if qdir:
                    first = min(x for x, _ in anchors)
                    last = max(x for x, _ in anchors)
                    if (qdir < 0 and sp.end <= first) or (qdir > 0 and sp.start > last):
                        prox *= 1.0 + p.direction
            else:
                prox = math.exp(-10 / p.lam)
            if head_vecs and sp.kind != "DEF":
                best_t = None
                for w in sw_words:
                    wv = word_vec(w) if w not in qwords else None
                    if wv is None:
                        continue
                    t = max(1.0 - int(np.bitwise_count(wv ^ hv).sum()) / (64 * len(wv)) for hv in head_vecs)
                    best_t = t if best_t is None else max(best_t, t)
                prior *= math.exp(p.head_beta * ((best_t if best_t is not None else 0.5) - 0.5))
            v = float(sw[si]) * prox * prior
            key = normalize(sp.text)
            if not key:
                continue
            votes[key] = votes.get(key, 0.0) + v
            best = surface.get(key)
            if best is None or v > best[0]:
                surface[key] = (v, sp.text, si)
    if not votes:
        return Extracted(None, 0.0, -1, [])
    # a name's votes also count for the longer names that contain it
    keys = sorted(votes, key=lambda x: (-votes[x], x))
    merged = dict(votes)
    for a in keys:
        ta = a.split()
        for b in keys:
            if a != b and len(b.split()) > len(ta) and f" {a} " in f" {b} ":
                merged[b] += votes[a] * 0.5
    order = sorted(merged, key=lambda x: (-merged[x], -len(x.split()), x))
    total = sum(votes.values())
    top = order[0]
    conf = min(1.0, merged[top] / total) * float(r[0])
    return Extracted(surface[top][1], conf, surface[top][2], [(x, merged[x]) for x in order[:5]])


# ---------------------------------------------------------------------------
# SQuAD metrics (official v1.1 definitions)
# ---------------------------------------------------------------------------

def exact_match(pred: str | None, golds: list[str]) -> float:
    if not pred:
        return 0.0
    p = normalize(pred)
    return float(any(p == normalize(g) for g in golds))


def f1(pred: str | None, golds: list[str]) -> float:
    if not pred:
        return 0.0
    pt = normalize(pred).split()
    best = 0.0
    for g in golds:
        gt = normalize(g).split()
        common = {}
        for w in pt:
            common[w] = common.get(w, 0)
        same = 0
        gcount = {}
        for w in gt:
            gcount[w] = gcount.get(w, 0) + 1
        for w in pt:
            if gcount.get(w, 0) > 0:
                same += 1
                gcount[w] -= 1
        if same == 0:
            continue
        prec, rec = same / len(pt), same / len(gt)
        best = max(best, 2 * prec * rec / (prec + rec))
    return best


def correct(pred: str | None, gold: str, slack: int = 3) -> bool:
    """Facts/dialog rule: gold is a whole-word part of the answer, answer ≤ gold + 3 words."""
    if not pred:
        return False
    p, g = normalize(pred), normalize(gold)
    return bool(g) and f" {g} " in f" {p} " and len(p.split()) <= len(g.split()) + slack
