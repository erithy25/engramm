"""Writing: deterministic sampling with a quotation cap (docs/PREREG_LM.md §8).

* Randomness is u_t = SHAKE-256(seed ‖ SHA-256(prompt ids) ‖ t) — the same seed
  and prompt give the same text on every machine.
* Temperature, then nucleus (top-p) truncation over tokens ordered by
  (−p, id); the draw is an exact integer inverse-CDF over probabilities in
  2^-40 fixed point.
* No 4-gram of the running text may repeat.
* Quotation cap: once the last 32 tokens occur verbatim in a source, every
  continuation that would extend that verbatim run is forbidden, so no more
  than 32 consecutive tokens are ever copied from one place.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

from engramm.lm.suffix import _dist_counts
from engramm.lm.tokenizer import EOS

QUOTE_CAP = 32
NO_REPEAT = 4
FIXED_BITS = 40


@dataclass
class Decoding:
    temperature: float = 0.9
    top_p: float = 0.95
    no_repeat: int = NO_REPEAT
    quote_cap: int = QUOTE_CAP
    stop_at_eos: bool = True


@dataclass
class Generation:
    prompt_ids: np.ndarray
    ids: list[int] = field(default_factory=list)
    text: str = ""
    steps: list[dict] = field(default_factory=list)


def uniform(seed: int, prompt_ids: np.ndarray, t: int) -> int:
    """A 64-bit uniform integer for step t."""
    digest = hashlib.sha256(np.ascontiguousarray(prompt_ids, dtype=np.uint16).tobytes()).digest()
    raw = hashlib.shake_256(seed.to_bytes(8, "big") + digest + t.to_bytes(8, "big")).digest(8)
    return int.from_bytes(raw, "big")


def _banned_repeats(seq: list[int], n: int) -> set[int]:
    if n <= 1 or len(seq) < n - 1:
        return set()
    tail = tuple(seq[len(seq) - (n - 1):])
    out = set()
    for i in range(len(seq) - n + 1):
        if tuple(seq[i:i + n - 1]) == tail:
            out.add(seq[i + n - 1])
    return out


def _banned_quotes(model, seq: list[int], cap: int) -> set[int]:
    if len(seq) < cap:
        return set()
    pat = np.asarray(seq[len(seq) - cap:], dtype=np.uint16)
    if EOS in pat:
        return set()
    out: set[int] = set()
    from engramm.lm.suffix import sa_range
    for idx, toks in ((model.index, model.tokens), (model.user.sa, model.user.tokens)):
        if idx is None:
            continue
        a, b = sa_range(toks, idx.sa, pat, cap, 0, len(idx.sa))
        if b > a:
            counts = _dist_counts(toks, idx.sa, a, b, cap, model.vocab)
            out.update(int(w) for w in np.flatnonzero(counts))
    return out


def sample_from(p: np.ndarray, u: int, dec: Decoding, banned: set[int]) -> int:
    q = np.array(p, dtype=np.float64)
    if banned:
        q[list(banned)] = 0.0
    if q.sum() <= 0:
        q = np.array(p, dtype=np.float64)            # nothing left: ignore the bans
    if dec.temperature != 1.0:
        nz = q > 0
        q[nz] = np.exp(np.log(q[nz]) / dec.temperature)
    q /= q.sum()
    order = np.lexsort((np.arange(len(q)), -q))
    cum = np.cumsum(q[order])
    cut = int(np.searchsorted(cum, dec.top_p, side="left")) + 1
    keep = order[:cut]
    weights = np.floor(q[keep] * (1 << FIXED_BITS)).astype(np.int64)
    weights[weights == 0] = 1
    total = int(weights.sum())
    r = u % total
    idx = int(np.searchsorted(np.cumsum(weights), r, side="right"))
    return int(keep[idx])


def generate(model, prompt: str, n_tokens: int = 100, seed: int = 0, dec: Decoding | None = None,
             explain: bool = False) -> Generation:
    dec = dec or Decoding()
    prompt_ids = model.tok.encode(prompt)
    seq = [EOS] + [int(x) for x in prompt_ids]
    gen = Generation(prompt_ids)
    for t in range(n_tokens):
        p = model.next_distribution(np.asarray(seq, dtype=np.uint16))
        banned = _banned_repeats(seq[1:], dec.no_repeat) | _banned_quotes(model, seq[1:], dec.quote_cap)
        if not dec.stop_at_eos:
            banned.add(EOS)
        w = sample_from(p, uniform(seed, prompt_ids, t), dec, banned)
        if explain:
            gen.steps.append(model.why(np.asarray(seq, dtype=np.uint16), w))
        if w == EOS and dec.stop_at_eos:
            break
        seq.append(w)
        gen.ids.append(w)
    gen.text = model.tok.decode(gen.ids)
    return gen


def longest_copied_run(model, ids: list[int]) -> int:
    """Length of the longest stretch of ``ids`` that occurs verbatim in the base corpus."""
    best, n = 0, len(ids)
    arr = np.asarray(ids, dtype=np.uint16)
    start = 0
    for end in range(1, n + 1):
        while start < end and model.index.count(arr[start:end]) == 0:
            start += 1
        best = max(best, end - start)
    return best
