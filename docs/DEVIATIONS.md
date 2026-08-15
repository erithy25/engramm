# DEVIATIONS — where the rebuild differs from D2 / D4

The rebuild follows the recovered specification where it exists. This file
records every point where it could not, and why. Three kinds of entry:

* **GAP** — the specification is silent or was lost with the fragments, and
  a choice had to be made. The choice is stated so it can be challenged.
* **INFERRED** — not stated outright, but determined by surviving evidence
  (a code fragment's signature, a surviving line of pseudocode).
* **CHANGED** — the rebuild deliberately does something different.

Nothing here is a silent design change. If a future measurement disagrees
with the historical numbers, this file is the first place to look.

---

## D1 — the specification is fragmentary

`docs/D2_SPEC.md` survives as 22 lines of a two-column layout that was
mangled during recovery, and `docs/D4_PROTOTYP.md` as 5 lines. Most of what
is known comes from the edit logs in `docs/archive/edit-logs/`. The encoder
pseudocode survives only as this fragment:

```
             rot1(V[seq[i+1]]) XOR
             V[seq[i+2]]
        acc += (2t − 1)        # int-SIMD
      return [acc > 0] tiebreak V_tie
```

Everything below follows from that plus the surviving API signatures.

---

## INFERRED-1 — the text alphabet is bytes, not Unicode characters

**Evidence.** The recovered core takes bytes: `learn_online(self, data: bytes,
label)` and `self.im.encode_signed(data)`, and `legacy/spielwiese.py` calls
`eng.learn(t.encode(), label)`.

**Consequence.** The item memory holds 256 symbol vectors, one per byte
value, rather than one per Unicode codepoint. For WiLI's 235 languages this
matters: a Devanagari or Han character becomes three UTF-8 bytes, so a
"trigram" spans one character there and three in ASCII text.

**Why not changed.** Byte-level is what the historical numbers were measured
with, and this rebuild's first job is to be comparable to them. Whether
codepoint-level trigrams work better is a separate question, and changing it
here would confound the comparison.

## INFERRED-2 — rotation assignment within a trigram

**Evidence.** The fragment shows `rot1` applied to `seq[i+1]` and nothing
applied to `seq[i+2]`. The pattern `rot(k)` for the character `k` positions
from the end gives `rot2(V[seq[i]]) XOR rot1(V[seq[i+1]]) XOR V[seq[i+2]]`,
which is also the standard construction in the trigram language-ID work D1
cites (Joshi et al. 2016).

**Consequence.** Position within the trigram is encoded by rotation depth,
so `"abc"` and `"cba"` bind to unrelated vectors.

## INFERRED-3 — pre-rotated item-memory copies

**Evidence.** `docs/D2_SPEC.md` §6 budgets "Item-Memory inkl. ρ-Kopien" at
0.96 MB — roughly three copies of 256 vectors at D = 10,000.

**Consequence.** The two rotated tables are materialised once instead of
rotating during encoding. This is an optimisation with no semantic effect:
`permute(V[b], k)` and `V_k[b]` are the same vector.

---

## GAP-1 — construction of the thermometer levels

**What the record says.** `docs/D4_PROTOTYP.md` names
"Q=16-Stufen-Thermometer-Encoding" and a `PixelLevelMemory` computing
"Position ⊗ Thermometer-Level, Mehrheitsbündelung". How the level vectors
themselves are built is not recorded anywhere that survived.

**Choice made.** The standard order-preserving level construction: level 0
is a random hypervector, and each subsequent level flips a further
`D / (2·(Q−1))` components, drawn from one fixed deterministic permutation.
Adjacent levels are therefore similar, distant levels progressively less so,
and levels 0 and 15 are approximately orthogonal.

**Why.** "Thermometer" names exactly this property — that intensity is
ordered, so nearby brightnesses must encode to nearby vectors. Independent
random vectors per level would make level 3 and level 4 as unrelated as
level 3 and level 15, discarding the ordering that makes the encoding worth
choosing.

**Risk.** The original may have used a different construction with the same
name, e.g. a literal thermometer code. If the MNIST result deviates from
94.62 %, this is the most likely place for the difference to originate.

## GAP-2 — mapping pixel intensity to level

**What the record says.** Nothing.

**Choice made.** `level = pixel · Q // 256`, giving 16 equal-width bins over
the full `uint8` range. No quantile binning, no statistics of any kind.

**Why.** A quantile mapping would be a fitted statistic, and fitting it over
the whole dataset is exactly the leak the audit flagged as the most
plausible one for MNIST (`docs/AUDIT_2026-08.md` §8.1). A fixed arithmetic
mapping cannot leak, so the question does not arise. It is also
scale-invariant across splits by construction.

## GAP-3 — texts shorter than three bytes

**What the record says.** Nothing.

**Choice made.** Such a text has no trigrams, so its accumulator is all
zeros and every component is a tie. Rather than resolve that silently, the
encoder rejects the input with an explicit error.

**Why.** A zero accumulator is not a vector with an unlucky tie; it carries
no information at all. Producing some vector for it would fabricate content.
WiLI paragraphs are far longer than three bytes, so this is an edge case,
not a data-loss path.

## GAP-4 — tie resolution

**What the record says.** The fragment ends `return [acc > 0] tiebreak
V_tie`, i.e. a single shared tie vector, and `docs/D6_EHRLICHKEIT.md`
records observation W14: at two shots per class the system collapsed onto
one class.

**Choice made: a keyed hash of the object's identity**, not a shared vector.
Decided from the analysis in `docs/UNDERSTANDING.md` §B2.2 (Erik Thye,
2026-08-15) before any benchmark was run. A tie at component *i* resolves to
one bit of SHAKE-256 over `(seed, dimension, object identity, i)`.

**Why not the recorded `V_tie`.** A shared tie vector carries no bias, so it
looks harmless — but it forces two objects to agree wherever both tie, which
inflates their similarity exactly as much as resolving every tie to a
constant does. Measured on two-vector bundles at D = 10,000:

| rule | agreement between unrelated bundles | similarity |
|---|---|---|
| always +1 | 62.49 % | +0.250 |
| shared tie vector (the recorded `V_tie`) | 62.53 % | +0.251 |
| **keyed hash of identity** | **50.04 %** | **+0.001** |

That is a plausible mechanism for the W14 collapse, and it is why this
deviates from the fragment rather than following it.

**The identity differs by site, because the sites differ.** Ties arise in
two places, and only one of them has a class:

| site | bundled | P(tie) | identity | inflation avoided |
|---|---|---|---|---|
| encoding, MNIST | 784 pixels | 2.85 % | the sample's own sign pattern + tie mask | +0.0016 |
| encoding, WiLI | ~600 trigrams | ~3.3 % | same | +0.0022 |
| **prototype, WiLI 10-shot** | 10 examples | **24.6 %** | the class label | **+0.121** |
| prototype, MNIST full | 60,000 examples | 1.03 % | the class label | +0.0002 |

Encoding has no label available and must not have one — the test split
carries none at encoding time, and using one would be the leak
`tests/test_no_leakage.py` exists to prevent. The sample's own content
serves as its identity instead: specifically the sign pattern and tie mask,
which is exactly what thresholding depends on and nothing more.

The effect is concentrated almost entirely at one site — the prototype with
few shots, which is the M1 replication setting. The rule is nevertheless
applied uniformly, because it costs 0.2 % of encoding time (measured:
14.8 µs per sample, ~1 s for MNIST) and a per-site exception would need its
own justification.

**Determinism.** The key contains no counter, no position in the data
stream and no batch boundary, so the resolution is invariant to sample
order and to how a run is chunked. SHAKE-256 rather than a NumPy bit
generator, because its output is fixed by standard rather than by a library
version, and these bits reach committed results. The seed participates, so
tie resolution varies across seeds like every other random choice and its
contribution shows up in the seed-to-seed spread.

---

## CHANGED-1 — `sim_from_dh` takes the dimension explicitly

The legacy signature was `sim_from_dh(dh)` with the dimension held in module
state. It is now `sim_from_dh(dh, dimension)`, so the dimension stays
configurable and no global has to be consistent with the data.

## CHANGED-2 — sign-preserving accumulator halving

The recovered pseudocode says `clip_or_halve`. Plain integer halving maps
`+1` to `0`, which destroys that component's sign and manufactures a tie the
data never produced. The rebuild halves magnitudes but never below 1, so
binarised prototypes are provably unchanged by halving.

Whether the original had this defect cannot be determined — the relevant
code did not survive. If it did, its prototypes drifted slightly on every
halving, which would matter only after long runs.

## CHANGED-3 — class indices assigned in sorted label order

Batch learning registers classes in sorted order rather than first-seen
order, so a shuffled batch produces a bit-identical state instead of one
differing by a row permutation. The recovered `_ensure_class` appended in
first-seen order.

## CHANGED-4 — item memory derived by hash, not by a random stream

A symbol's hypervector is derived from `(seed, symbol)` via SHAKE-256. How
the original did it is unknown. A stream-drawn memory would make a symbol's
vector depend on when it was first seen, and therefore make the learned
state depend on presentation order — which would contradict the project's
own order-invariance claims. The hash construction removes the dependency
entirely and is stable across platforms and NumPy versions.

## CHANGED-5 — scope: no episodes, no HNSW, no consolidation

The rebuild implements prototypes only. The episodic layer, the HNSW index
and the consolidation phases are out of scope until the core is measured
(README roadmap). Historical numbers that depend on the episodic layer —
notably MNIST 94.62 %, which the record attributes +8.13 pp to it — are
therefore **not directly comparable** to what this core will produce. The
WiLI figure is less affected: the record has prototypes-only *ahead* by
4.2 pp there (82.64 % vs 79.30 %).
