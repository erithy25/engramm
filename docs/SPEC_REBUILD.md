# SPEC_REBUILD — implementation-level specification for independent reproduction

This document specifies the ENGRAMM rebuild completely enough that an engineer
who never sees the implementation can re-implement it and obtain
**bit-identical predictions** for the four benchmark configurations below. It
is the input to the project's independent-reproduction procedure (README,
section *Method*, step 3).

Everything here was derived from the code at commit `08bbe97` and checked by
running small snippets against that code (Linux x86_64, Python 3.11.15,
NumPy 2.4.1). Where a value is quoted in §14 it was computed by the existing
implementation, not by hand.

The document deliberately contains **no test-set accuracy, macro-F1 or
predictions digest** for any configuration.

Normative words: **must** = required for bit-identity; *informative* = context
that does not change any value.

---

## 0. Scope, notation, constants

### 0.1 The four configurations

| id | command | dataset | pipeline | T2 epochs | episodes / fusion |
|---|---|---|---|---|---|
| (a) | `run_benchmark --task wili --shots 10 --seed-list 42` | WiLI-2018, 10 shots per language | prototypes only (T1) | 0 | no |
| (b) | `run_benchmark --task mnist --seed-list 42` | MNIST official 60k/10k | prototypes only (T1) | 0 | no |
| (c) | `run_benchmark --task mnist --seed-list 42 --pipeline prototypes --t2-epochs 2` | MNIST | T1 + T2, λe = 0 | 2 | no (λe forced to 0) |
| (d) | `run_benchmark --task mnist --seed-list 42 --pipeline full --config-from results/tuning/mnist_seed42.json` | MNIST | T1 + episodes + fusion + T2 | 2 | yes |

All four use seed `S = 42` and dimension `D = 10000` (the command-line default;
no configuration overrides it).

### 0.2 Fusion configuration per run

A fusion configuration has six fields. The defaults are
`k = 32, θ0 = 0.0, λe = 1.0, λp = 1.0, util_clip = 8, t2_local = false`.

* (a), (b): the fusion configuration is never constructed. Prediction uses the
  prototypes alone (§9).
* (c): the command line gives `k=32, θ0=0.0, λe=1.0, λp=1.0, t2_local=false`,
  and because the pipeline is `prototypes` with T2 epochs > 0, **λe is then
  overwritten with 0.0**. Effective configuration:
  `k=32, θ0=0.0, λe=0.0, λp=1.0, util_clip=8, t2_local=false`, T2 epochs = 2.
* (d): the configuration file (`results/tuning/mnist_seed42.json`) is read as
  JSON. Its field `test_split_used` must be `false`; otherwise the run
  aborts. Exactly these fields are taken from it:
  * `k` ← top-level `"k"` = **32**
  * `t2_local` ← top-level `"t2_local"` = **false** (default false if absent)
  * `θ0` ← `"selected"."theta0"` = **0.2**
  * `λe` ← `"selected"."lambda_e"` = **0.25**
  * T2 epochs ← `"selected"."t2_epochs"` = **2**
  * encoder options ← `"selected"."encoder_options"` = **{}** (no options)

  **λp is not read from the file.** It keeps the command-line default
  **1.0**. **util_clip is not read either.** It keeps the default **8**.
  Effective configuration: `k=32, θ0=0.2, λe=0.25, λp=1.0, util_clip=8, t2_local=false`.

The JSON numbers are parsed as IEEE-754 binary64 values, so `0.2` means the
double closest to 0.2 and `0.25` means exactly 0.25.

### 0.3 Notation

* `D = 10000`. A hypervector has D binary components, indexed `0 … D−1`.
* `K` = number of classes: 235 for WiLI, 10 for MNIST.
* `‖`: byte-string concatenation.
* `u64be(n)`: n as 8 bytes, big-endian, unsigned. `u32be(n)`: 4 bytes, big-endian.
* `SHAKE256(m, L)`: the first L bytes of the SHAKE-256 extendable-output
  function (FIPS 202) of message m. This is Python's
  `hashlib.shake_256(m).digest(L)`.
* `bits(v)`: the D components of a packed vector v (see §2).
* `s(v)`: the signed ±1 form of a vector, `s_i = 2·bits(v)_i − 1`.
* `H(a, b)`: Hamming distance, the number of components where a and b differ.
* All integer arithmetic is exact unless a width is stated.
* Float arithmetic is IEEE-754 binary64, round-to-nearest-even. Every
  operation is rounded separately: **no fused multiply-add and no extended
  precision** (see §15).

---

## 1. Data

### 1.1 Source files, digests, cache

The loaders read these five files from the cache directory
`/home/user/engramm/data/cache/` (on another machine: the `data/cache/`
directory of the checkout). Each file is verified by SHA-256 over its raw
bytes, as stored. On a mismatch the run aborts; the file is never silently
replaced. A missing file is downloaded from the URL only when downloads are
explicitly allowed.

| file name in cache | SHA-256 (verified by the loader) | source URL |
|---|---|---|
| `wili-2018.zip` | `727e52ca4e13400e6def1b1b594ca12c8b7fd49ad9d45fd5c9e57a1f6d3b7a3f` | `https://zenodo.org/records/841984/files/wili-2018.zip?download=1` |
| `train-images-idx3-ubyte.gz` | `440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609` | `https://ossci-datasets.s3.amazonaws.com/mnist/train-images-idx3-ubyte.gz` |
| `train-labels-idx1-ubyte.gz` | `3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c` | `https://ossci-datasets.s3.amazonaws.com/mnist/train-labels-idx1-ubyte.gz` |
| `t10k-images-idx3-ubyte.gz` | `8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6` | `https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz` |
| `t10k-labels-idx1-ubyte.gz` | `f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6` | `https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz` |

The same directory holds other files (`banking77_*.csv`, `blogs.zip`,
`clinc150_data_full.json`, `encodings/`, `robustness/`, …). None of them is
read by the four configurations.

### 1.2 WiLI-2018: parsing

1. Open `wili-2018.zip`. Read the four archive members `x_train.txt`,
   `y_train.txt`, `x_test.txt` and `y_test.txt`, all at the archive root and
   by exact name. The other members (`labels.csv`, `README.txt`, `urls.txt`)
   are not read.
2. Decode each member as **strict UTF-8**. There is no BOM.
3. Split each member into lines with Python's `str.splitlines()` (no
   `keepends`). **Nothing is stripped**: leading and trailing whitespace is
   part of the text.
   * For these files this is exactly equivalent to splitting the raw bytes
     on `0x0A` and dropping the empty string after the final `\n`. Every
     member ends with `\n`. None of them contains `\r`, `\x0b`, `\x0c`,
     `\x1c`, `\x1d`, `\x1e`, `\x85`, U+2028, U+2029 or `\x00`. This was
     checked on all four members.
   * Result: 117,500 lines per member. `x_train[i]` pairs with
     `y_train[i]`, and `x_test[i]` with `y_test[i]`.
4. A text is used as its UTF-8 bytes. Because decoding is strict and the
   bytes are re-encoded as UTF-8, **the text bytes equal the raw line bytes
   between two `\n`**.
5. Facts for checking: the shortest text is 140 bytes; the longest training
   text is 120,424 bytes; the longest test text is 579,350 bytes (test line
   index 24169). No text is shorter than 3 bytes.

**Labels and class indices.** `labels = sorted(set(y_train))`, sorted in
Python's default string order, which is Unicode code-point order. All labels
are ASCII, so this is also byte order. There must be exactly 235 labels. The
class index of a label is its position in that sorted list. `y_train` and
`y_test` are the lists of class indices. The full sorted label list is given
in §14.1. For example, `be-tarask` sorts before `bel` because `-` (0x2D) is
below the letters.

### 1.3 WiLI few-shot selection (configuration (a))

**RNG.** The run starts by calling `set_all_seeds(42)`, which does three things:

* `random.seed(42)` (Python's `random` module). *Never used afterwards.*
* `numpy.random.seed(42)` (NumPy's legacy global RNG). *Never used afterwards.*
* It returns `G = numpy.random.default_rng(42)`: a `Generator` over the
  `PCG64` bit generator, seeded through `SeedSequence(42)`.

`G` is used for nothing except shot selection. No call is made on `G` before
shot selection starts. Shot selection is exactly the following sequence of
calls, and there are no others:

```
chosen = []
for c in 0, 1, …, 234:                        # class indices = sorted label order
    candidates_c = [i for i in 0..117499 if y_train[i] == c]   # ascending line index;
                                                                # 500 entries (int64 array)
    draw_c = G.choice(candidates_c, size=10, replace=False)     # NumPy Generator.choice,
                                                                # default shuffle=True, p=None
    chosen.append(draw_c)
selected = sort_ascending(concatenate(chosen))  # 2350 distinct line indices
x_train_fs = [x_train[i] for i in selected]
y_train_fs = [y_train[i] for i in selected]
```

* All 235 calls go to the **same** generator in the order shown. Its internal
  state carries over from one call to the next, including the buffered
  32-bit half-word (Appendix A).
* For a 500-element population and `size = 10`, `Generator.choice(…,
  replace=False)` uses Floyd's sampling algorithm and then a Fisher-Yates
  shuffle of the 10 picks, with Lemire-bounded 32-bit draws. The
  bit-exact algorithm is given in Appendix A and was verified against NumPy
  2.4.1.
* **Training order** is ascending original line index (`selected` is
  sorted), so the classes are interleaved. For configuration (a) the order
  does not affect any value, because T1 learning is a sum. It is recorded
  for completeness.
* Result: 2,350 training examples (10 per class) and 117,500 test examples
  in file order.

The test split is used unchanged and in file order. 3,147 test texts also
occur verbatim in the full training split. *Informative:* this count goes
into the record as `test_items_in_train`; the items are not removed.

### 1.4 MNIST: parsing (configurations (b), (c), (d))

Each `.gz` file is gunzipped and read in the IDX format:

* Image files: a 16-byte header, `>IIII` (big-endian uint32):
  `magic, count, rows, cols`. The magic number must be `2051`. It is
  followed by `count·rows·cols` bytes of `uint8` pixels. Training images:
  count 60000; test images: count 10000; rows = cols = 28. Each image is
  flattened **row-major**, so pixel index `p = row·28 + col` with
  `p ∈ 0…783`. Pixel dtype is `uint8` (0…255), with no scaling and no
  normalisation.
* Label files: an 8-byte header, `>II`: `magic, count`. The magic number must
  be `2049`. It is followed by `count` bytes, one label (0…9) each.
* Decompressed sizes: 47,040,016 / 60,008 / 7,840,016 / 10,008 bytes.
* The split is the official one, unchanged, in file order.
* Labels: `labels = ("0","1",…,"9")`, the decimal digit strings. Class index
  = digit value = position in sorted label order.

### 1.5 What else the loaders compute (informative, no effect on predictions)

* *WiLI:* a per-language trigram vocabulary and document frequencies (only
  for the record's `artifacts_digest`), and the mask of test texts that
  occur in the full training split.
* *MNIST:* per-pixel training mean and standard deviation (only for
  `artifacts_digest`).

None of these computations uses an RNG, and none of them feeds into
encoding, learning or prediction.

---

## 2. Bit conventions

* **Packed form.** A hypervector is stored as `D/8 = 1250` bytes. Component
  `i` is bit `7 − (i mod 8)` of byte `⌊i/8⌋`. That is **MSB-first within
  each byte**: NumPy `packbits`/`unpackbits` with the default
  `bitorder='big'`.
  * `bit_i = (byte[i >> 3] >> (7 − (i & 7))) & 1`.
  * Example: components `[1,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,1]` pack to bytes
    `[0x80, 0x01]`.
* **Signed form.** `s_i = 2·bit_i − 1`, so bit 1 → +1 and bit 0 → −1.
* **Thresholding** (signed sum → bit): `> 0` → 1, `< 0` → 0, and `== 0` is a
  **tie**, resolved by §6.
* **Binding** is componentwise XOR. On the packed form it is a bytewise XOR.
* **Hamming distance** is the popcount of the XOR of the packed forms.
* A SHAKE-256 output of `D/8` bytes is used **directly as a packed vector**
  with the same bit order. Component `i` of a hash-derived bit stream is
  therefore bit `7 − (i mod 8)` of output byte `⌊i/8⌋`.

---

## 3. Every hash input, byte by byte

All integers are big-endian. The seed is always `S = 42`, and D is always 10000.

| use | message fed to SHAKE-256 | output length | interpretation |
|---|---|---|---|
| item-memory vector of symbol `σ` (a byte string) | `u64be(S) ‖ u64be(len(σ)) ‖ σ` | 1250 bytes | packed hypervector `IM(σ)` |
| encoding tie stream (§6.2) | `u64be(S) ‖ u64be(D) ‖ u64be(len(I)) ‖ I`, where `I = b"encoding\x00" ‖ packbits(T > 0) ‖ packbits(T == 0)` | 1250 bytes | tie bit per component |
| prototype tie stream (§6.3) | `u64be(S) ‖ u64be(D) ‖ u64be(len(I)) ‖ I`, where `I = b"prototype\x00" ‖ utf8(label)` | 1250 bytes | tie bit per component |
| thermometer permutation seed (§7.2) | `u64be(S) ‖ b"thermometer:order"` (**no length prefix**) | 8 bytes | read as a big-endian unsigned integer, used as a NumPy seed |
| episode id (§11.1) | `u32be(len(utf8(label))) ‖ utf8(label) ‖ key` (key = 1250 packed bytes) | 8 bytes | read as a big-endian unsigned 64-bit integer |

Symbols used by the encoders:

* **WiLI (trigrams):** the 256 one-byte symbols `bytes([b])` for
  `b = 0…255`. The message for byte `0x61` is
  `000000000000002a 0000000000000001 61`.
* **MNIST:** the position symbols `b"pixel:0"` … `b"pixel:783"`: ASCII, the
  decimal index without padding (for example `b"pixel:42"`, 8 bytes). The
  base level symbol `b"thermometer:base"` (16 bytes).

Worked example: `SHAKE256(u64be(42) ‖ u64be(1) ‖ b"a", 1250)` begins
`52 3f 0c 11 00 d4 3d bd`, so `IM(b"a")` begins with the components
`0,1,0,1,0,0,1,0, 0,0,1,1,1,1,1,1, …`.

---

## 4. Permutation (rotation)

`ρ^k(v)` is a **cyclic rotation over components** (not over bytes):

```
ρ^k(v)_i = v_{(i − k) mod D}        for i = 0…D−1
```

Component `i` moves to position `i + k` (mod D), and the last `k`
components wrap around to the front. Equivalently: read the D components as
one D-bit big-endian integer, with component 0 as the most significant bit,
and rotate it **right** by k bits. This is `numpy.roll(bits, k)` on the
unpacked component array.

Worked example, run against the implementation with D = 16:
`v = [0xC0, 0x01]`, so components 0, 1 and 15 are set.

* `ρ^1(v) = [0xE0, 0x00]`: components 0, 1 and 2 are set. Component 15
  wrapped to 0, and 0 and 1 moved to 1 and 2.
* `ρ^2(v) = [0x70, 0x00]`: components 1, 2 and 3 are set.

At D = 10000: `ρ^2(IM(b"a"))` begins `148fc30440350f6f` and `ρ^1(IM(b"a"))`
begins `291f8608806a1ede`.

---

## 5. Trigram encoder (WiLI)

Options for WiLI: no framing (no spaces added), no lower-casing, D = 10000.
The item memory is seeded with S = 42.

For a text t, let `x = utf8(t)` be its bytes, of length n (the raw line bytes, §1.2).

1. If `n < 3` the text is rejected with an error. This does not occur in
   WiLI.
2. Precompute three tables for every byte value `b`:
   `R2[b] = ρ²(IM(bytes([b])))`, `R1[b] = ρ¹(IM(bytes([b])))` and
   `R0[b] = IM(bytes([b]))`.
3. There are `m = n − 2` trigrams, one for each start position `i = 0…n−3`:
   ```
   G_i = R2[x[i]] XOR R1[x[i+1]] XOR R0[x[i+2]]      # packed, 1250 bytes
   ```
   The **first** byte of the trigram gets rotation 2, the second rotation 1
   and the third none. Trigrams overlap, one per byte position, and never
   span two texts.
4. Signed component sums (int32, exact):
   ```
   T_j = Σ_{i=0}^{m−1} (2·bits(G_i)_j − 1) = 2·(number of i with bits(G_i)_j = 1) − m
   ```
5. Binarise T into the packed encoding with the **encoding tie rule** (§6.2).

When m is odd no component can tie. When m is even, ties occur.

*Informative:* the implementation groups texts by trigram count, pads, and
splits very long texts into sub-chunks. All of this only rearranges an
exact integer sum, so the result per text is identical. Batching (2,000
test texts per batch, 5,000 training texts per batch) likewise has no
effect, because each text is encoded independently of the others.

---

## 6. Binarisation and tie resolution

### 6.1 The general rule

Given integer sums `T_0 … T_{D−1}` and an identity byte string `I`:

```
stream = bits( SHAKE256( u64be(S) ‖ u64be(D) ‖ u64be(len(I)) ‖ I , D/8 ) )   # D bits, MSB-first
out_j  = 1           if T_j > 0
         0           if T_j < 0
         stream_j    if T_j == 0          # stream bit at the SAME index j
return packbits(out)
```

The tie bit for component j is **stream bit j**, not the n-th bit consumed.
The stream is always the full D bits, and only the tied positions read it.
If no component ties, the stream is never needed and the result is just
`T > 0`.

### 6.2 Encoding ties (every encoded sample, WiLI and MNIST)

The identity is built from the sample's own content:

```
I = b"encoding\x00" ‖ packbits(T > 0) ‖ packbits(T == 0)
```

* `b"encoding\x00"` is the 8 ASCII bytes `encoding` followed by one zero
  byte: 9 bytes in total.
* `packbits(T > 0)` is the 1250-byte packed vector with bit j = 1 iff
  T_j > 0.
* `packbits(T == 0)` is the 1250-byte packed vector with bit j = 1 iff
  T_j = 0 (the tie mask).
* `len(I) = 2509` at D = 10000, so the length field is `u64be(2509)`.
* The seed is the item-memory seed, S = 42.

The rule is applied per sample and never uses the label, a position in the
data stream, or the batch.

### 6.3 Prototype ties (every binarisation of a class accumulator)

```
I = b"prototype\x00" ‖ utf8(label)
```

For example, the MNIST class "0" has `I = 70726f746f74797065 00 30` (11
bytes), and the WiLI class "ace" has `I = b"prototype\x00ace"`. The seed is
the run seed, S = 42. The stream depends only on (seed, D, label), so each
class effectively has one fixed tie vector, used every time its prototype
is re-binarised.

---

## 7. Pixel thermometer encoder (MNIST)

Parameters: 784 positions, `Q = 16` levels, construction `progressive`,
D = 10000. The item memory is seeded with S = 42.

### 7.1 Position vectors

`Pos_p = IM(b"pixel:" ‖ ascii(decimal(p)))` for `p = 0…783`.

### 7.2 Level vectors (`progressive`)

```
base = bits(IM(b"thermometer:base"))                                  # D bits
seed_T = int.from_bytes(SHAKE256(u64be(S) ‖ b"thermometer:order", 8), "big")
       # for S = 42: digest 3b2dc15762e2d7bf  →  seed_T = 4264277003255076799
order = numpy.random.default_rng(seed_T).permutation(D)               # a fresh Generator
       # PCG64 seeded via SeedSequence(seed_T); permutation = arange(D) then
       # an in-place Fisher-Yates shuffle (Appendix A)
per_step = D // (2·(Q−1)) = 10000 // 30 = 333
L[0] = base
for q = 1 … Q−1:
    L[q] = copy of L[q−1]
    for idx in order[(q−1)·per_step : q·per_step]:      # the next 333 entries of the permutation
        L[q][idx] ^= 1
```

The flips accumulate: level q differs from level 0 in exactly `333·q`
components, namely those listed in `order[0 : 333·q]`. Level 15 differs from
level 0 in 4995 components. Components `order[4995:]` are never flipped.

### 7.3 Quantisation

`q_p = (x_p · 16) // 256` in integer arithmetic, which equals `x_p >> 4`. So
0…15 map to level 0, 16…31 to level 1, …, and 240…255 to level 15. This is
a fixed rule, not fitted to data.

### 7.4 Encoding one image

```
B_p = Pos_p XOR L[q_p]                               # p = 0 … 783
T_j = Σ_{p=0}^{783} (2·bits(B_p)_j − 1) = 2·(number of p with bits(B_p)_j = 1) − 784
encoding = binarise(T) with the encoding tie rule (§6.2)
```

784 is even, so ties occur: roughly 270 components per image.

*Informative:* the implementation pre-binds all 784×16 pairs
`Pos_p XOR L[q]` once and processes images in chunks. Neither affects any
value.

---

## 8. Prototype classifier (T1)

### 8.1 State

* `labels`: the list of class labels. Class index = position in this list.
* `A`: int16 array of shape (K, D), the accumulator. Initially all zeros.
* `P`: uint8 array of shape (K, 1250), the packed prototypes.

### 8.2 Class registration

Before any learning, all training labels are registered in **sorted**
order: `sorted(set(training labels))`, in code-point order. Each new label
is appended with an all-zero A row. Its P row is filled when the class is
first binarised. For all four runs, every class occurs in training, so the
model's class list equals the dataset's sorted label list and model index =
dataset index.

### 8.3 Learning a batch (T1)

Input: packed encodings `e_1 … e_M` with labels. Let `s(e)` be the ±1 form.

```
register_classes(batch labels)                          # no-op after the initial registration
present = sorted(set(batch labels))
updated = {}
for label in present:                                   # classes in sorted order
    c = index(label)
    updated[c] = int32(A[c]) + Σ_{m: label_m = label} s(e_m)    # exact int32 sum
updated = halved_if_needed(updated)                     # §8.4; returns int16 rows
for c in updated: P[c] = binarise(updated[c], prototype tie rule for labels[c])   # §6.3
for c in updated: A[c] = updated[c]
```

Batching:

* **(a):** one batch of 2,350 examples (the batch size is 5,000).
* **(b):** 12 batches of 5,000 examples, in file order, with all 10 classes
  registered first.
* **(c), (d):** one call with all 60,000 examples (§12).

Learning is pure addition as long as no halving happens, so all of these
give the same A and P. §14 shows the (b) and (c)/(d) T1 states are
identical.

After T1, each prototype is
`P_c = binarise(A_c)`: bit 1 where `A_c > 0`, 0 where `A_c < 0`, and the
class's prototype tie-stream bit where `A_c = 0`.

### 8.4 Halving (specified for completeness; it never fires in (a)–(d))

```
HALVE_THRESHOLD = 16384
halved_if_needed(updated):                       # updated: dict class → int32 row
    loop:
        rows = { c: A[c] for all classes }, then overridden by `updated`
        peak = max over all rows of max_j |row_j|    (computed in int32)
        if peak <= 16384: break
        halvings += 1
        A       = halve(A)          # EVERY row of A, including rows in `updated`
        updated = { c: halve(row) for c, row in updated }
    return { c: int16(row) for c, row in updated }

halve(v)_j = 0                               if v_j == 0
           = sign(v_j) · max(|v_j| // 2, 1)  otherwise       # sign-preserving; ±1 stays ±1
```

Rows that are not in `updated` are **not** re-binarised after halving.
Halving preserves every sign, so their P is unchanged anyway. The runner
**aborts** if the halving counter is non-zero at the end: after T1 for (a)
and (b), and after prediction for (c) and (d). Observed maxima of |A| are
6,742 after MNIST T1 and 7,015 after T2 in (c). The recorded run of (d)
reports 0 halvings.

---

## 9. Scoring and prediction with prototypes only ((a), (b), and the prototype term everywhere)

For a packed query q:

```
d_c   = H(q, P_c)                                   # integer 0…D
sim_c = 1.0 − ((2.0 · d_c) / 10000.0)               # binary64: multiply (exact), divide (rounded), subtract (rounded)
```

(These three steps are the order of evaluation of `1.0 - 2.0*d/D`.)

**Prediction** is the argmax over classes of `sim_c`. On exact equality the
winner is the class whose **label comes first in sorted (code-point)
order**. In (a) and (b) this is realised as "the first maximum by class
index", and class index = sorted label order, so the two rules coincide.
For D = 10000 the map d ↦ sim is strictly decreasing over 0…10000 (checked
for every integer d), so the rule is exactly equivalent to "smallest Hamming
distance, ties to the lowest class index".

*Informative:* scoring is done in chunks of 512 queries, test encoding in
batches of 2,000, and later prediction in blocks of 2,048. None of these
affects any value: each query is scored independently against fixed
prototypes.

The predicted class index is then mapped to the dataset's class index by
label. For all four runs this is the identity mapping.

---

## 10. T2 — error-driven refinement ((c) and (d))

### 10.1 The RNG

Directly before T2, a **fresh** generator `R = numpy.random.default_rng(S)`
with S = 42 is created. It is independent of the `set_all_seeds` generator,
which for MNIST is never used at all. `R` is used for exactly two calls,
one per epoch:

```
order_epoch1 = R.permutation(60000)
order_epoch2 = R.permutation(60000)     # the same generator, continuing its stream
```

`permutation(n)` is `arange(n)` followed by NumPy's in-place Fisher-Yates
shuffle using masked-rejection bounded draws (Appendix A).

### 10.2 The epoch loop

```
true_i = class index of training example i          (i = 0 … 59999, file order)
use_episodes = (λe > 0) and (number of episodes > 0)      # (c): false; (d): true
if use_episodes:
    NB = leave-one-out neighbour lists for ALL i, computed ONCE here (§11.3)
errors = []
for epoch in 1 … 2:
    order = R.permutation(60000)
    misses = 0
    for i in order:                     # in permutation order
        if not step(i): misses += 1
    errors.append(misses / 60000)       # Python float division; recorded rounded to 6 decimals
```

### 10.3 One step, `step(i)`, with key `e = encoding_i`, `t = true_i` and `s = s(e)` (int32 ±1)

```
1. sim_c = 1.0 − ((2.0·H(e, P_c)) / 10000.0) for every class c, using the CURRENT P
2. score:
     (c) no episodes:  score_c = λp · sim_c                       (λp = 1.0)
     (d) episodes:     score_c = fused score, §11.4, with the CURRENT utilities
3. pred = argmax_c score_c, ties to the first label in sorted order
4. (d) only: for each of the k = 32 neighbours j in NB_i:
        util_j = clip(util_j + (+1 if val_j == t else −1), −8, +8)
   This happens on EVERY step, hit or miss. The utilities were read in
   step 2, before this update.
5. if pred != t:                                   # a miss
        updated = { t: int32(A[t]) + s }
        if not t2_local:                           # t2_local = false in (c) and (d)
            updated[pred] = int32(A[pred]) − s
        updated = halved_if_needed(updated)        # §8.4
        P[c] = binarise(updated[c], prototype tie rule of labels[c]) for c in updated
        A[c] = updated[c] for c in updated
   return pred == t
```

Only the rows `t` and `pred` change, and only on a miss. They are
re-binarised right away, so the next step sees the new P. A hit changes no
prototype. In (d) it still changes the utilities.

---

## 11. Full pipeline ((d)): episodic memory, retrieval, fusion

### 11.1 Episodes (created during T1)

T1 of the full model (prototypes plus episodes) does the prototype learning of §8.3 on all 60,000
examples in one call. It then appends one episode per training example,
in input (file) order:

* position `j` = the training example index (0 … 59999)
* `key_j` = the packed encoding (1250 bytes)
* `val_j` = the class index of its label
* `util_j` = 0 (int16)
* `id_j` = `int.from_bytes(SHAKE256(u32be(len(L)) ‖ L ‖ key_j, 8), "big")`,
  where `L = utf8(label)`. For MNIST, `len(L) = 1`, so the message starts
  `00000001 3x`. The id is an unsigned 64-bit integer.

In (c), episodes are created too, but λe = 0, so they are never read.

### 11.2 Rank and retrieval order

```
rank_j = position of episode j when all episodes are sorted ascending by the key (id_j as unsigned 64-bit, j)
```

All 60,000 MNIST ids are distinct, so this is simply the order of the ids.
The position `j` would only matter for exact duplicates (same label and
same key); there are none.

**Top-k retrieval** of a query q (k = 32):

```
dist_j = H(q, key_j)             # exact integer Hamming distance
sort key of episode j = (dist_j, rank_j)          # ascending, lexicographic; all keys are distinct
exclusion: in leave-one-out mode, the query's own episode is removed from the candidate set
kk = min(k, N − 1) with exclusion, min(k, N) without           # = 32 here
result = the kk episodes with the smallest sort keys, IN ASCENDING SORT-KEY ORDER
sims_m = 1.0 − ((2.0 · dist_m) / 10000.0)         # binary64, as in §9
```

*Informative:* the implementation computes `dist` as a float32 matrix
product of ±1 vectors, `(D − q·e)/2`. Every partial sum is an integer of
magnitude ≤ 10000 < 2²⁴, so the result is exact and equals the popcount
distance. A reimplementation should simply use popcount.
(`order_key = (dist << 32) | rank`, followed by `argpartition` and a stable
sort, is the same total order.)

### 11.3 When neighbour lists are computed

* **T2:** the neighbour lists NB_i (positions and sims) of all 60,000
  training examples are computed **once**, before the first epoch, in
  leave-one-out mode: example i excludes episode i. At that moment the
  prototypes are the T1 prototypes and every utility is 0, but neither
  influences retrieval, which depends only on the keys and ids. The same
  lists and sims are reused for both epochs. Keys never change.
* **Test:** every test query retrieves its top-32 from **all** 60,000
  episodes, with no exclusion.

### 11.4 Fused score — exact operation order

For a query with neighbours `(j_0, sims_0), …, (j_31, sims_31)` in
retrieval order, current utilities `util` and current prototypes P:

```
for c in 0…K−1:  E_c = 0.0
for m = 0 … 31 (in retrieval order):
    w  = (1.0 + (float(util_{j_m}) / 8.0)) * max(0.0, sims_m − θ0)     # θ0 = 0.2 (binary64)
    E_{val_{j_m}} = E_{val_{j_m}} + w                                   # sequential, in this order
for c in 0…K−1:
    score_c = (λp · sim_c) + (λe · E_c)          # λp = 1.0, λe = 0.25
```

* `sim_c` is the prototype similarity of §9.
* The utility weight is `û(u) = 1 + u/util_clip` with util_clip = 8, so
  û ∈ [0, 2] for u ∈ [−8, 8]. `u/8.0` and `1.0 + …` are exact.
* Every `*`, `−`, `+` and `max` above is a separate binary64 operation with
  its own rounding. **An FMA must not be used**: contracting
  `E + a·b` would change the result.
* The additions into `E_c` happen in retrieval order, starting from 0.0.
  The implementation's `np.add.at` is sequential in this order. A
  pure-Python version of this formula matched the implementation bit for
  bit on 1,000 consecutive T2 steps with evolving utilities.
* `λp · sim_c` and `λe · E_c` are exact here (multiplying by 1.0 and 0.25).
  The final `+` is rounded.
* A weight of exactly zero (for sims ≤ θ0) contributes nothing. The sign of
  a zero cannot change any sum here.

**Class decision:** `argmax_c score_c`, with exact ties going to the class
whose label is first in sorted order (for MNIST, the lowest digit).

### 11.5 Final test prediction in (d)

After T2 (2 epochs), each test image is encoded (§7). Its fused score is
computed with the **final** prototypes P and the **final** utilities from
the end of T2, over its non-excluded top-32 neighbours, and the argmax is
taken as above. Nothing is learned or updated at test time.

---

## 12. End-to-end procedures

### (a) WiLI, 10-shot, prototypes only

```
G = default_rng(42)                                  # via set_all_seeds(42)
load WiLI (§1.2); select shots with G (§1.3)          → 2350 train texts, 117500 test texts
IM = item memory(seed 42, D 10000); encoder = trigram encoder (§5)
model = prototype classifier(D, seed 42); register the 235 labels (sorted)
encode the 2350 training texts (one batch) → learn (§8.3) → A, P
abort if halvings > 0
for each test text, in file order: encode (§5) → predict (§9)
evaluate (§13)
```

### (b) MNIST, prototypes only

```
set_all_seeds(42)                                    # the generator is not used
load MNIST (§1.4)
IM = item memory(42, 10000); encoder = thermometer (§7)
model = prototype classifier(D, seed 42); register "0"…"9"
for batches of 5000 training images in file order: encode → learn (§8.3)
abort if halvings > 0
for each test image, in file order: encode → predict (§9)
evaluate (§13)
```

### (c) MNIST, prototypes + 2 T2 epochs (λe = 0)

```
set_all_seeds(42)                                    # not used
load MNIST; encoder as in (b)
encode all 60000 training images (packed)
T1: prototype learning on all 60000 in one call (§8.3); episodes appended (§11.1), unused
T2: R = default_rng(42); 2 epochs of §10 with use_episodes = false, score = 1.0·sim
predict each test image: argmax_c (1.0·sim_c), ties to the first label (§9)
abort if halvings > 0; evaluate (§13); record t2_error_per_epoch
```

### (d) MNIST full pipeline

```
set_all_seeds(42)                                    # not used
config: k=32, θ0=0.2, λe=0.25, λp=1.0, util_clip=8, t2_local=false, T2 epochs=2
load MNIST; encoder as in (b)
encode all 60000 training images
T1: prototype learning (one call) + 60000 episodes with util 0 and ids (§11.1)
T2: NB = leave-one-out top-32 of every training example (§11.2, §11.3), computed once
    R = default_rng(42); 2 epochs of §10 with fused scores (§11.4) and utility updates
predict each test image: top-32 over all episodes, fused score with the final P and utilities, argmax
abort if halvings > 0; evaluate (§13); record t2_error_per_epoch
```

---

## 13. Evaluation and the predictions digest

Let `y` be the true dataset class indices of the test split, in file order,
and `ŷ` the predicted ones.

* **Accuracy** = `(number of i with y_i == ŷ_i) / n_test`, a single binary64
  division of two integers.
* **Macro-F1** over **all** K dataset classes (235 or 10), whether or not a
  class is ever predicted:
  ```
  TP_c   = number of i with y_i == ŷ_i == c
  pred_c = number of i with ŷ_i == c;  act_c = number of i with y_i == c
  F1_c   = 0.0 if pred_c + act_c == 0 else (2.0 · TP_c) / (pred_c + act_c)
  macro  = mean_c F1_c
  ```
  The mean is NumPy's `mean`: a pairwise sum in NumPy's summation order
  (Appendix B), then one division by K. Only the last bits of the reported
  float depend on this order.
* **`predictions_sha256`** (schema-4 records):
  ```
  SHA-256( utf8(labels[ŷ_0]) ‖ b"\n" ‖ utf8(labels[ŷ_1]) ‖ b"\n" ‖ … ‖ utf8(labels[ŷ_{n−1}]) ‖ b"\n" )
  ```
  `labels` is the dataset's sorted label list, and the items are in
  test-file order. Every label is followed by exactly one `\n`, including
  the last. For MNIST the labels are the digit characters. For WiLI they
  are the language codes, for example `b"mwl\n"`. The result is the
  lower-case hex digest.
* Other result fields (informative): `n_train`, `n_test`, `n_classes`,
  `chance_level = 1/K`. For WiLI also `test_items_in_train` (3,147) and
  `accuracy_excluding_train_duplicates` (accuracy over the test items whose
  text does not occur in the full training split). For (c) and (d) also
  `t2_error_per_epoch`, each value `round(misses/60000, 6)`.

---

## 14. Conformance checklist

All values below were produced by the existing implementation. Where a
digest is over an array, the bytes are row-major. `A` digests use **int16
little-endian**, with rows in sorted-label order. `P`, keys and encodings
are raw packed bytes. "first 8 bytes" means the hex of bytes 0…7 of the
packed vector.

### 14.1 Data

* SHA-256 of the WiLI archive members (raw bytes):
  * `x_train.txt`: `afac7e069450ec7ac2995c7b8203ae9445404a68dbc7a66fedb0f64d3720a12e` (64,085,137 bytes)
  * `y_train.txt`: `bd0d63a9ab19cb15594588d1bb1b43c4b1b39d7f102656a391c259ca862e0753`
  * `x_test.txt`: `c06db2b42ae5a29428aca5ab9505c5117cbdeb82538eb1b087f55a6627c45556` (65,166,417 bytes)
  * `y_test.txt`: `2fbc58bc6f34c8cea1587396d82986a2637adf5ecb2b5cbd8f2a20be0f81ad11`
* WiLI line counts: 117,500 in every member.
* The first five `y_train` lines: `est swe mai oci tha`.
* WiLI sorted labels (235, index 0 first):
  `ace afr als amh ang ara arg arz asm ast ava aym azb aze bak bar bcl be-tarask bel ben bho bjn bod bos bpy bre bul bxr cat cbk cdo ceb ces che chr chv ckb cor cos crh csb cym dan deu diq div dsb dty egl ell eng epo est eus ext fao fas fin fra frp fry fur gag gla gle glg glk glv grn guj hak hat hau hbs heb hif hin hrv hsb hun hye ibo ido ile ilo ina ind isl ita jam jav jbo jpn kaa kab kan kat kaz kbd khm kin kir koi kok kom kor krc ksh kur lad lao lat lav lez lij lim lin lit lmo lrc ltg ltz lug lzh mai mal map-bms mar mdf mhr min mkd mlg mlt mon mri mrj msa mwl mya myv mzn nan nap nav nci nds nds-nl nep new nld nno nob nrm nso oci olo ori orm oss pag pam pan pap pcd pdc pfl pnb pol por pus que roa-tara roh ron rue rup rus sah san scn sco sgs sin slk slv sme sna snd som spa sqi srd srn srp stq sun swa swe szl tam tat tcy tel tet tgk tgl tha ton tsn tuk tur tyv udm uig ukr urd uzb vec vep vie vls vol vro war wln wol wuu xho xmf yid yor zea zh-yue zho`
* MNIST headers (hex of the first 16 / 8 decompressed bytes):
  * training images: `00000803 0000ea60 0000001c 0000001c`
  * test images: `00000803 00002710 0000001c 0000001c`
  * training labels: magic 2049, count 60000
  * test labels: magic 2049, count 10000
* MNIST `y_train[0:10] = 5 0 4 1 9 2 1 3 1 4`; `y_test[0:10] = 7 2 1 0 4 1 4 9 5 9`.
* MNIST training class counts (0…9): 5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949.
* SHA-256 of the MNIST pixel arrays (uint8, N×784):
  * training: `741c988805d008ac6e4c904b69001ba184c24b2c540a4ef403f4c71b676cf757`
  * test: `6d87418db22cc8025d05968bec9bd5c3932904b23485740db143a061a2c9d161`

### 14.2 RNG

* `default_rng(42)` just after seeding, PCG64 128-bit state
  `0xcea44f6798798f2aacbc7c9d68860ac8`, increment
  `0xfa505436c9a8416e66caf2e28d25abff`. The first three raw 64-bit outputs
  are `0xc621fbcd16d92688, 0x705a5661a791ffc1, 0xdbcd12c26eda1624`.
* WiLI (a), class 0 (`ace`): 500 candidates, starting at line indices 221,
  645, 865, 914, 1063, … The `choice` output, **in returned order**:
  `12688, 91494, 12915, 80191, 51818, 51210, 84232, 13622, 26676, 99986`.
* Class 1 (`afr`) output: `95435, 48250, 42647, 79867, 100763, 20138, 54773, 62581, 69173, 110892`.
* `selected` (sorted), the first 16:
  `87, 90, 135, 172, 222, 312, 352, 360, 366, 392, 438, 439, 460, 551, 602, 653`.
  The last 4: `117281, 117359, 117363, 117404`. Count: **2,350**.
* SHA-256 over the 2,350 selected indices, each as `u64be`, in sorted order:
  `3694426073025dbb04a285b339e3319e5071c83f7950e3ffb9af5d1a3c652891`.
* Labels of the first five selected training examples: `jbo por kor ina mdf`.
* Thermometer seed: `SHAKE256(u64be(42) ‖ b"thermometer:order", 8) = 3b2dc15762e2d7bf`
  → `4264277003255076799`. `order[0:10] = 2562, 8813, 3284, 2626, 5087, 6837, 2256, 2241, 1915, 2629`;
  `order[330:336] = 6610, 5863, 7506, 4645, 9618, 1941`.
* T2 (c)/(d), `default_rng(42)`:
  * epoch 1, first 16: `3493, 57546, 8815, 19332, 15566, 22963, 21972, 22093, 1818, 46044, 31538, 36479, 9523, 57704, 10133, 53353`
  * epoch 2, first 16: `17284, 27577, 35294, 27278, 56928, 12169, 6580, 45132, 27388, 57966, 17348, 27607, 31833, 41489, 49994, 21295`

### 14.3 Item memory (seed 42, D 10000)

| symbol | first 8 bytes | note |
|---|---|---|
| `b"a"` | `523f0c1100d43dbd` | full SHA-256 of the 1250 bytes: `c80826456f683afcc9e1d6af917a07c9b228cb0700a10f9200c69c6dc3dd2a8b`; popcount 5011 |
| `b"\x00"` | `7a70e7f7351608f6` | |
| `b"h"` | `d24986c03dfa12bb` | |
| `b"pixel:0"` | `afddd6de5311e14a` | |
| `b"pixel:783"` | `42abbd45d8903552` | |
| `b"thermometer:base"` (= level 0) | `cc20929fdacc2b2f` | full SHA-256: `33c85042f39eca24b790e477b9eb75bc4c68439ccbaba0e5915240a2681e9fa5` |
| `b"a"` at seed 7 | `763264777c3538a9` | shows that the seed enters |

* SHA-256 of the 256 byte-symbol vectors stacked (256×1250, b = 0…255):
  `b8cfa6c95726d2c53273497c451580cf2fcd9b9e6260eaa52d8915fd39599036`.
* SHA-256 of the 784 position vectors stacked (784×1250):
  `9171ffbabe0f3a0f955cb215a7c1fca24932ed6a50dfe62f5fc5857b3fa5d3e3`.

### 14.4 Trigram encoder (seed 42)

| text | bytes (hex) | trigrams | `T[0:8]` | tied components | first 8 bytes | SHA-256 of encoding |
|---|---|---|---|---|---|---|
| `"hello"` | `68656c6c6f` | 3 | `1,1,−1,1,−1,1,1,−1` | 0 | `d636e7709d14afbb` | `90cea789dc0c80f9552aa026e0d60b339853eb1f336e1161cc6e546ab0834512` |
| `"hello!"` | `68656c6c6f21` | 4 | `0,0,0,0,0,2,2,0` | 3734 | `a63ec5f19d14ff3b` | `a92e43456c4fa1dba304c548654a0a0696c38f9fe423f23e04e1cfde0ec5a424` |
| `"abc"` | `616263` | 1 | `−1,1,1,1,1,1,1,−1` | 0 | `7e8bad9e21c366ce` | |
| `"Grüße, Welt"` | `4772c3bcc39f652c2057656c74` | 11 | `−3,−3,−1,1,5,−3,1,−1` | 0 | `1aac47d925c0a4a2` | |

* `"hello!"`: the tie identity is 2509 bytes. The first tied components are
  0, 1, 2, 3, 4, 7, 12 and 18, and the tie-stream bits at those components
  are 1, 0, 1, 0, 0, 0, 1, 0.
* WiLI (a), training example 0 (label `jbo`, 211 bytes): first 8 bytes
  `97e54740fa8cb897`. Example 1 (`por`, 243 bytes): `69d6836e5fb20815`.
* SHA-256 of all 2,350 WiLI (a) training encodings (2350×1250, in selection
  order): `b6913b93826ffe119b63b4d66e5e2b16099a6053689c49212ee4a53980773628`.
* WiLI test text 0 (label `mwl`, 665 bytes, no ties): first 8 bytes
  `ab844237c3475c90`. SHA-256 of the first 100 test encodings:
  `bc47359e3bc03f90628d3864a89eebd0dbdd1cd47110a829ce1cd886358c2f89`. 48 of
  those 100 texts have at least one tie.

### 14.5 Thermometer encoder (seed 42)

* Level first 8 bytes:
  * L0 = `cc20929fdacc2b2f`
  * L1 = `cc20929f9acc0b2f`
  * L2 = `ce20929f9acc1b2f`
  * L15 = `0b95c7b6218091fc`
* `H(L0, L1) = 333`, `H(L7, L8) = 333`, `H(L0, L15) = 4995`.
* SHA-256 of the 16×1250 level table:
  `2aea6a170fd74c7f77664eeb0ba78104893511f46a6cd6c4e80520ac23e3eecf`.
* Quantisation: pixels 0, 15, 16, 127, 128, 255 → levels 0, 0, 1, 7, 8, 15.
* `Pos_0 XOR L0` first 8 bytes: `63fd444189ddca65`.

| image | label | tied components | `T[0:8]` | first 8 bytes |
|---|---|---|---|---|
| training 0 | 5 | 271 | `−14,10,−24,−10,12,8,2,0` | `4eed2e2f2d522685` |
| training 1 | 0 | 283 | `−22,18,−24,−10,12,34,−50,−12` | `4cd81c063d123686` |
| test 0 | 7 | 272 | `−32,24,−24,−10,12,16,−10,8` | `4dc81d271c5234d7` |
| test 1 | 2 | 262 | `18,18,−24,−10,12,12,0,−22` | `cec82e2f0c1636c7` |

SHA-256 of the MNIST encodings:

* the first 1,000 training encodings: `39efb3167dd91b99d60201ad8996d2363cccbe94bf02a8f5072c7de0ca0b25d2`
* all 60,000 training encodings: `c9ca644eac5c3a55dc8de32f9a73bf12c311f35ec7feed368bb90fb27f8dca79` (see §15, item 7)
* the first 1,000 test encodings: `24e8d4226032991db7d1534022b8f8868c160f70dc01aec9e7fa1edd6adc972c`

### 14.6 Prototype tie streams (seed 42, D 10000), first 8 bytes of the packed stream

* label `"0"`: `776ca019dfb2eabd`
* label `"1"`: `88eaba1c35868e7c`
* label `"ace"`: `f98083b7a18ae24c`

### 14.7 T1 prototype states

* **(a) WiLI, after T1:**
  * `A` SHA-256 = `7d7fad7d6b95959531e7a2a780a9a0e3ecec7cfc99789b4ec6f88461a42496a3`
  * `P` SHA-256 = `d6b6964c9a84b9aec50be9996aa0a61dc3fdc75dc40dd166f5a5f60328f8bcd7`
  * 264,024 zero components in `A` in total, 1,132 of them in class `ace`.
    The prototype tie rule is heavily exercised here.
  * `A[ace][0:8] = 4,−2,−4,−4,−2,−2,8,8`, and `P[ace]` first 8 bytes = `83b10e5a29653b3f`.
  * Halvings: 0.
* **(b), (c), (d) MNIST, after T1.** The state is identical for all three:
  * `A` SHA-256 = `b14227b9968fc12c5cd6eb50f11e9f27f9cefade3e5ffaf8aa88cd3c3912359a`
  * `P` SHA-256 = `60f9d66f0df01b577b953821eda4579aa3cc431aa117c17308a8f033a39eae32`
  * Zero components per class 0…9: `0,1,1,0,0,0,0,0,0,0`. max|A| = 6742.
  * `A[0][0:8] = −4325,3499,−5923,−5923,5923,4949,−3441,−3931`, and `P[0]`
    first 8 bytes = `4cc82f061d5236c7`.
  * `A[1][0:8] = −6580,5954,−6742,−6742,6742,6552,−3234,−1210`, and `P[1]`
    first 8 bytes = `4ce90e0f1f5236d7`.

### 14.8 T2, configuration (c)

* Misses per epoch: **10,747** and **9,125** out of 60,000. The recorded
  `t2_error_per_epoch` is `[0.179117, 0.152083]`.
* After T2:
  * `A` SHA-256 = `6f84e91d2eb131ad90e2fd2fba4c165cb7de77fdd00155cd9474240e31d614b5`
  * `P` SHA-256 = `a8b15f4c1e647d9066d4ee2a4ccc88a4db6c3c11fe8ed6d236553bfe78bc44b8`
  * max|A| = 7015, halvings 0, all utilities still 0.

### 14.9 Full pipeline, configuration (d)

* Episode ids (unsigned 64-bit, hex):
  * `id_0 = ab6dcd5d3aab77ec`, `id_1 = 1cbfa3bd5d2d0c09`, `id_2 = dab99623275d09ab`.
  * All 60,000 ids are distinct.
  * SHA-256 over all ids as `u64be` in position order:
    `fba1c601bfefac706d3b860de5d6ac1fc10306ab02478eaae6a8db48653478e8`.
  * The smallest id belongs to episode 50981 (`0001625fabf98577`).
  * `rank[0:5] = 40204, 6826, 51267, 54572, 22565`.
* Training example 0, leave-one-out top-8 positions:
  `32248, 18932, 30483, 26251, 21654, 31008, 52295, 46358`, at distances
  `934, 942, 951, 973, 989, 993, 998, 999`.
* First T2 step (epoch 1, example 3493, label 8):
  * Leave-one-out top-8 positions: `26720, 27579, 59277, 22703, 59015, 3499, 295, 58302`.
  * Their distances: `735, 738, 759, 762, 803, 807, 809, 818`. The 32nd
    neighbour is at distance 908.
  * All 32 neighbours have class 8.
  * Prototype sims (T1 prototypes, classes 0…9): `0.757, 0.8068, 0.8034,
    0.7942, 0.7772, 0.7908, 0.7944, 0.7666, 0.8178, 0.781`.
  * Fused scores: equal to the sims for classes ≠ 8. Class 8 scores
    `5.856550000000001` (Python `repr`).
  * Prediction 8 (a hit). Afterwards, all 32 of its neighbours have
    utility +1.
* After the **first 1,000 steps of epoch 1** (examples `order_epoch1[0:1000]`):
  * 48 misses.
  * Utilities (int16 LE, 60,000 values): SHA-256
    `be1fbcbf700aece0b4bd5de3872af95cdc61a698d70b03a6083460a05490e634`.
    22,229 are non-zero; the minimum is −3 and the maximum 7.
  * `A` SHA-256 `3e2945a9642d97ca80600abccb09ab6d7e7fe166640d75122aac080713031713`.
  * `P` SHA-256 `d09d5b392ee3125771d0eaf59b39309a9fdb9a6339ed4578c5198c88932cfe58`.
* Test image 0, top-8 over all episodes (no exclusion):
  * positions `53843, 27059, 47003, 38620, 14563, 16186, 44566, 15260`
  * distances `575, 638, 670, 673, 679, 681, 692, 694`
  * the 32nd neighbour is at distance 749
* Complete T2: misses per epoch **3,215** and **3,110**. The recorded
  `t2_error_per_epoch` is `[0.053583, 0.051833]`. These come from the
  recorded run, not from a re-run (§15, item 8).

---

## 15. Platform dependence, residual risks, and what could not be pinned down

1. **NumPy Generator algorithms.** NumPy's compatibility policy does not
   guarantee `Generator.choice` and `Generator.permutation` streams across
   versions. Appendix A pins them as implemented in NumPy 2.4.1. They were
   verified bit for bit against NumPy 2.4.1 on:
   * the exact call patterns used here (235 consecutive 10-of-500 draws;
     `permutation(10000)` seeded with the thermometer seed; two consecutive
     `permutation(60000)` draws);
   * SeedSequence and PCG64 states for seeds 0, 7, 42, 2⁶³+12345 and
     2⁶⁴−1.

   A reimplementation that uses NumPy should check §14.2 before anything
   else. Other NumPy versions were not tested.
2. **Floating point.** Only §9 (sims), §11.4 (fusion), §10.2 (error rates)
   and §13 (metrics) use floats. All of them are IEEE binary64 with
   separately rounded operations. **FMA contraction or x87 extended
   precision would change the fused scores.** The prototype-only decisions
   ((a), (b), (c)) are provably equivalent to integer comparisons (§9), so
   only (d) is exposed to float details. The retrieval distance is an exact
   integer. The implementation's float32 matrix product cannot round,
   because every value is an integer below 2²⁴.
3. **Endianness.** No algorithmic step depends on the machine's byte order:
   * all hash inputs use explicit big-endian integers or raw uint8 bytes;
   * SeedSequence builds its 64-bit words from little-endian 32-bit word
     pairs explicitly.

   Only the digests in §14 that are taken over int16 arrays name a byte
   order (little-endian).
4. **Python string semantics.** Labels are sorted by code point, not by
   locale. `str.splitlines()` would split on more characters than `\n`, but
   the WiLI members contain none of them (§1.2), so a byte-level split on
   `\n` is equivalent **for these files**.
5. **Hash randomisation (`PYTHONHASHSEED`).** Sets are used only for
   membership tests and are always sorted before any iteration that could
   affect an output. Hash randomisation has no effect.
6. **Batching and chunking** (training batches of 5,000, test batches of
   2,000, score chunks of 512, prediction blocks of 2,048, retrieval query
   blocks of 1,024, episode blocks, and encoder memory chunks) change no
   value. The one exception would be accumulator halving, which does not
   occur in any of the four runs and aborts the run if it does.
7. **Encoding digest provenance.** The digest of all 60,000 MNIST training
   encodings in §14.5, and the T1/T2 values in §14.7–14.9 that build on it,
   were computed from a cached copy of the encodings. That cache was
   verified against fresh encoding on 1,300 rows (the first 1,000 plus 300
   random ones), but the full 60,000 were not re-encoded, to avoid a long
   job on the shared machine.
8. **Full-run T2 values for (d).** The epoch miss counts 3,215 / 3,110 were
   not recomputed. The full leave-one-out retrieval over 60,000×60,000 is a
   long job. They are taken from the recorded run of configuration (d) at
   commit `72e704e`. Relative to the commit this spec describes, only
   record-metadata code and an unrelated module have changed since then. The
   first 1,000 T2 steps of (d) were recomputed here, and §14.9 lists them.
   The miss counts of (c) were recomputed and match its recorded run.
9. **Halving under (d).** Whether |A| could reach 16,384 in (d) is not
   derivable in closed form. The recorded run reports 0 halvings, and the
   runner aborts on any halving, so a conforming run never takes that path.
10. **Macro-F1 last bits** depend on NumPy's pairwise summation (Appendix
    B). The description was verified against `numpy.mean` on random arrays
    of lengths 7, 10, 129, 235, 300 and 1000. Accuracy is a single exact
    division.
11. **Environment.** These values were computed on Linux x86_64, CPython
    3.11.15, NumPy 2.4.1. The project's reference environment (macOS arm64,
    Python 3.13) was not available. Nothing in the algorithm is expected to
    differ there, provided NumPy is 2.4.1.

---

## Appendix A — NumPy `Generator(PCG64)` paths used, as a pure-Python reference

This code reproduces, bit for bit, `numpy.random.default_rng(seed)` (seeded
through `SeedSequence(seed)`), `permutation(n)` and
`choice(array, size, replace=False)` for populations of at most 10,000
elements, as used in §1.3, §7.2 and §10.1. It was verified against NumPy
2.4.1 (§15, item 1).

```python
M32 = 0xFFFFFFFF; M64 = (1 << 64) - 1; M128 = (1 << 128) - 1

# --- SeedSequence(entropy=int) -> 4 x uint64 for PCG64 ------------------------
INIT_A = 0x43b0d7e5; MULT_A = 0x931e8875
INIT_B = 0x8b51f9dd; MULT_B = 0x58f38ded
MIX_MULT_L = 0xca01f9dd; MIX_MULT_R = 0x4973f715
XSHIFT = 16                                    # pool size 4 words of 32 bits

def seedseq_state(seed_int, n_words64=4):
    words = []                                 # int -> 32-bit words, least significant first
    n = seed_int
    if n == 0:
        words = [0]
    while n > 0:
        words.append(n & M32); n >>= 32
    hc = [INIT_A]
    def hashmix(v):
        v = (v ^ hc[0]) & M32
        hc[0] = (hc[0] * MULT_A) & M32
        v = (v * hc[0]) & M32
        v ^= v >> XSHIFT
        return v
    def mix(x, y):
        r = (MIX_MULT_L * x - MIX_MULT_R * y) & M32
        r ^= r >> XSHIFT
        return r
    pool = [0] * 4
    for i in range(4):
        pool[i] = hashmix(words[i] if i < len(words) else 0)
    for s in range(4):
        for d in range(4):
            if s != d:
                pool[d] = mix(pool[d], hashmix(pool[s]))
    for s in range(4, len(words)):             # only for entropy longer than 128 bits
        for d in range(4):
            pool[d] = mix(pool[d], hashmix(words[s]))
    hb = INIT_B                                # generate_state(4, uint64): 8 x 32-bit words
    out32 = []
    for i in range(2 * n_words64):
        v = pool[i % 4]
        v ^= hb
        hb = (hb * MULT_B) & M32
        v = (v * hb) & M32
        v ^= v >> XSHIFT
        out32.append(v)
    return [out32[2*i] | (out32[2*i+1] << 32) for i in range(n_words64)]   # little-endian word pairs

# --- PCG64 (XSL-RR 128/64) ---------------------------------------------------
PCG_MULT = 0x2360ED051FC65DA44385DF649FCCF645

class PCG64:
    def __init__(self, seed_int):
        s = seedseq_state(seed_int)
        initstate = (s[0] << 64) | s[1]
        initseq   = (s[2] << 64) | s[3]
        self.inc = ((initseq << 1) | 1) & M128
        self.state = 0
        self._step()
        self.state = (self.state + initstate) & M128
        self._step()
        self.has32 = False; self.u32 = 0        # buffered upper half for 32-bit draws
    def _step(self):
        self.state = (self.state * PCG_MULT + self.inc) & M128
    def next64(self):                           # step first, then output the new state
        self._step()
        st = self.state
        x = ((st >> 64) ^ st) & M64
        rot = st >> 122
        return ((x >> rot) | (x << ((64 - rot) & 63))) & M64
    def next32(self):                           # low half first, high half on the next call
        if self.has32:
            self.has32 = False
            return self.u32
        v = self.next64()
        self.has32 = True
        self.u32 = v >> 32
        return v & M32

# --- bounded integers ---------------------------------------------------------
def random_interval(g, mx):
    """Uniform in [0, mx], masked rejection. Used by shuffle/permutation."""
    if mx == 0:
        return 0
    mask = mx
    for sh in (1, 2, 4, 8, 16, 32):
        mask |= mask >> sh
    if mx <= M32:
        while True:
            v = g.next32() & mask
            if v <= mx:
                return v
    while True:
        v = g.next64() & mask
        if v <= mx:
            return v

def bounded_lemire(g, rng):
    """Uniform in [0, rng] inclusive, Lemire's method on 32 bits (rng < 2**32 - 1). Used by choice."""
    if rng == 0:
        return 0
    excl = rng + 1
    m = g.next32() * excl
    left = m & M32
    if left < excl:
        thr = (M32 - rng) % excl
        while left < thr:
            m = g.next32() * excl
            left = m & M32
    return m >> 32

# --- Generator.permutation(n) -------------------------------------------------
def permutation(g, n):
    a = list(range(n))
    for i in range(n - 1, 0, -1):               # i = n-1 down to 1
        j = random_interval(g, i)
        a[i], a[j] = a[j], a[i]
    return a

# --- Generator.choice(pop, size, replace=False), len(pop) <= 10000, p=None, shuffle=True
def choice_noreplace(g, pop, size):
    n = len(pop)
    chosen = set(); idx = []
    for j in range(n - size, n):                # Floyd's algorithm
        v = bounded_lemire(g, j)                # uniform in [0, j]
        if v not in chosen:
            chosen.add(v); idx.append(v)
        else:
            chosen.add(j); idx.append(j)
    for i in range(size - 1, 0, -1):            # shuffle of the picks, i = size-1 down to 1
        j = bounded_lemire(g, i)
        idx[i], idx[j] = idx[j], idx[i]
    return [pop[k] for k in idx]
```

Usage in this spec:

* §1.3: `g = PCG64(42)`, then `choice_noreplace(g, candidates_c, 10)` for
  c = 0…234 on the same `g`.
* §7.2: `permutation(PCG64(4264277003255076799), 10000)`.
* §10.1: `g = PCG64(42)`, then `permutation(g, 60000)` twice on the same `g`.

For populations above 10,000 NumPy uses a different branch of `choice`. It
is not reached here.

## Appendix B — NumPy pairwise summation (used only by macro-F1's mean)

```python
def pairwise_sum(a):                 # a: list of binary64
    n = len(a)
    if n < 8:
        res = a[0]                    # n >= 1 here
        for x in a[1:]:
            res += x
        return res
    if n <= 128:
        r = list(a[:8]); i = 8
        while i < n - (n % 8):
            for j in range(8):
                r[j] += a[i + j]
            i += 8
        res = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
        while i < n:
            res += a[i]; i += 1
        return res
    n2 = n // 2
    n2 -= n2 % 8
    return pairwise_sum(a[:n2]) + pairwise_sum(a[n2:])

mean = pairwise_sum(per_class_f1) / K
```
