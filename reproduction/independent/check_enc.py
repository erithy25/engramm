import os, sys, time, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import hdc
from hdc import sha256_hex, D

RESULTS = []


def rec(section, name, got, expected):
    ok = got == expected
    RESULTS.append(dict(section=section, check=name, got=str(got), expected=str(expected), ok=bool(ok)))
    print(("PASS" if ok else "FAIL"), section, name, "| got:", got, "| exp:", expected, flush=True)


enc = hdc.TrigramEncoder(42)
cases = [
    ("hello", "68656c6c6f", 3, [1, 1, -1, 1, -1, 1, 1, -1], 0, "d636e7709d14afbb", "90cea789dc0c80f9552aa026e0d60b339853eb1f336e1161cc6e546ab0834512"),
    ("hello!", "68656c6c6f21", 4, [0, 0, 0, 0, 0, 2, 2, 0], 3734, "a63ec5f19d14ff3b", "a92e43456c4fa1dba304c548654a0a0696c38f9fe423f23e04e1cfde0ec5a424"),
    ("abc", "616263", 1, [-1, 1, 1, 1, 1, 1, 1, -1], 0, "7e8bad9e21c366ce", None),
    ("Grüße, Welt", "4772c3bcc39f652c2057656c74", 11, [-3, -3, -1, 1, 5, -3, 1, -1], 0, "1aac47d925c0a4a2", None),
]
for text, hx, ntri, T8, ties, first8, full in cases:
    x = text.encode("utf-8")
    Tref = enc.sums_reference(x)
    e, T = enc.encode_one(x)
    rec("14.4", f"{text!r} bytes", x.hex(), hx)
    rec("14.4", f"{text!r} fast==reference sums", bool(np.array_equal(Tref, T)), True)
    rec("14.4", f"{text!r} trigrams", len(x) - 2, ntri)
    rec("14.4", f"{text!r} T[0:8]", T[:8].tolist(), T8)
    rec("14.4", f"{text!r} ties", int((T == 0).sum()), ties)
    rec("14.4", f"{text!r} first 8", e[:8].tobytes().hex(), first8)
    if full:
        rec("14.4", f"{text!r} sha256", sha256_hex(e.tobytes()), full)
# hello! tie details
x = b"hello!"; T = enc.sums_reference(x)
tied = np.flatnonzero(T == 0)
ident = b"encoding\x00" + np.packbits(T > 0).tobytes() + np.packbits(T == 0).tobytes()
stream = hdc.tie_stream_bits(ident)
rec("14.4", "hello! identity length", len(ident), 2509)
rec("14.4", "hello! first tied components", tied[:8].tolist(), [0, 1, 2, 3, 4, 7, 12, 18])
rec("14.4", "hello! stream bits at those", stream[tied[:8]].tolist(), [1, 0, 1, 0, 0, 0, 1, 0])

# random texts: fast vs reference, incl. long ones crossing 255-row blocks
rng = np.random.default_rng(0)
ok = True
for n in [3, 4, 5, 100, 255, 256, 257, 258, 511, 512, 1000, 3001]:
    x = rng.integers(0, 256, n, dtype=np.uint8).tobytes()
    c, m = enc.counts_fast(x)
    if not np.array_equal((2 * c - m), enc.sums_reference(x)):
        ok = False; print("mismatch at n", n)
rec("impl", "fast trigram counter == reference on random texts", ok, True)

# WiLI (a) training encodings
W = hdc.load_wili()
selected = np.load(os.path.join(HERE, "out", "wili_selected.npy"))
t0 = time.time()
tr_enc = np.stack([enc.encode_one(W["x_train"][i])[0] for i in selected])
dt = time.time() - t0
ntri = sum(len(W["x_train"][i]) - 2 for i in selected)
print(f"encoded 2350 train texts ({ntri} trigrams) in {dt:.2f}s -> {ntri/dt/1e6:.3f} M trigrams/s", flush=True)
rec("14.4", "train ex0 label/len/first8", (W["labels"][W["y_train"][selected[0]]], len(W["x_train"][selected[0]]), tr_enc[0, :8].tobytes().hex()), ("jbo", 211, "97e54740fa8cb897"))
rec("14.4", "train ex1 label/len/first8", (W["labels"][W["y_train"][selected[1]]], len(W["x_train"][selected[1]]), tr_enc[1, :8].tobytes().hex()), ("por", 243, "69d6836e5fb20815"))
rec("14.4", "all 2350 train encodings sha256", sha256_hex(tr_enc.tobytes()), "b6913b93826ffe119b63b4d66e5e2b16099a6053689c49212ee4a53980773628")
np.save(os.path.join(HERE, "out", "wili_train_enc.npy"), tr_enc)
te = []; nt = 0
for i in range(100):
    e, T = enc.encode_one(W["x_test"][i]); te.append(e); nt += int((T == 0).any())
te = np.stack(te)
rec("14.4", "test0 label/len/first8", (W["labels"][W["y_test"][0]], len(W["x_test"][0]), te[0, :8].tobytes().hex()), ("mwl", 665, "ab844237c3475c90"))
rec("14.4", "first 100 test encodings sha256", sha256_hex(te.tobytes()), "bc47359e3bc03f90628d3864a89eebd0dbdd1cd47110a829ce1cd886358c2f89")
rec("14.4", "first 100 test texts with a tie", nt, 48)

# ---------------------------------------------------------------- thermometer
th = hdc.ThermometerEncoder(42)
L = th.L
rec("14.5", "L0 first8", L[0, :8].tobytes().hex(), "cc20929fdacc2b2f")
rec("14.5", "L1 first8", L[1, :8].tobytes().hex(), "cc20929f9acc0b2f")
rec("14.5", "L2 first8", L[2, :8].tobytes().hex(), "ce20929f9acc1b2f")
rec("14.5", "L15 first8", L[15, :8].tobytes().hex(), "0b95c7b6218091fc")
ham = lambda a, b: int(np.unpackbits(a ^ b).sum())
rec("14.5", "H(L0,L1),H(L7,L8),H(L0,L15)", (ham(L[0], L[1]), ham(L[7], L[8]), ham(L[0], L[15])), (333, 333, 4995))
rec("14.5", "level table sha256", sha256_hex(L.tobytes()), "2aea6a170fd74c7f77664eeb0ba78104893511f46a6cd6c4e80520ac23e3eecf")
rec("14.5", "quantisation", th.quantise(np.array([0, 15, 16, 127, 128, 255], np.uint8)).tolist(), [0, 0, 1, 7, 8, 15])
rec("14.5", "Pos0 xor L0 first8", (th.Pos[0] ^ L[0])[:8].tobytes().hex(), "63fd444189ddca65")
M = hdc.load_mnist()
Ttr = th.sums_batch(M["x_train"][:1000]); Tte = th.sums_batch(M["x_test"][:1000])
ok = all(np.array_equal(th.sums_reference(M["x_train"][i]), Ttr[i]) for i in range(0, 1000, 37)) and \
     all(np.array_equal(th.sums_reference(M["x_test"][i]), Tte[i]) for i in range(0, 1000, 41))
rec("impl", "thermometer GEMM sums == reference (sampled)", ok, True)
etr, ntr = hdc.binarise_encoding_batch(Ttr); ete, nte = hdc.binarise_encoding_batch(Tte)
for name, T, e, nt, i, lab, ties, T8, f8 in (
        ("training 0", Ttr, etr, ntr, 0, 5, 271, [-14, 10, -24, -10, 12, 8, 2, 0], "4eed2e2f2d522685"),
        ("training 1", Ttr, etr, ntr, 1, 0, 283, [-22, 18, -24, -10, 12, 34, -50, -12], "4cd81c063d123686"),
        ("test 0", Tte, ete, nte, 0, 7, 272, [-32, 24, -24, -10, 12, 16, -10, 8], "4dc81d271c5234d7"),
        ("test 1", Tte, ete, nte, 1, 2, 262, [18, 18, -24, -10, 12, 12, 0, -22], "cec82e2f0c1636c7")):
    y = (M["y_train"] if name.startswith("training") else M["y_test"])[i]
    rec("14.5", f"{name} label/ties/T[0:8]/first8", (int(y), int(nt[i]), T[i, :8].tolist(), e[i, :8].tobytes().hex()), (lab, ties, T8, f8))
    # also single-sample binariser
    assert np.array_equal(hdc.binarise_encoding(T[i]), e[i])
rec("14.5", "first 1000 train encodings sha256", sha256_hex(etr.tobytes()), "39efb3167dd91b99d60201ad8996d2363cccbe94bf02a8f5072c7de0ca0b25d2")
rec("14.5", "first 1000 test encodings sha256", sha256_hex(ete.tobytes()), "24e8d4226032991db7d1534022b8f8868c160f70dc01aec9e7fa1edd6adc972c")

with open(os.path.join(HERE, "out", "checks_enc.json"), "w") as f:
    json.dump(RESULTS, f, indent=1)
print("n_fail", sum(not r["ok"] for r in RESULTS))
