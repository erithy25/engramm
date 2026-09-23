"""Independent re-implementation of the ENGRAMM HDC classifier from SPEC_REBUILD.md.

Written from the specification only. All section references (§) are to that document.
"""
import gzip
import hashlib
import os
import struct
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

D = 10000
NB = D // 8  # 1250 packed bytes
SEED = 42

FILE_SHA = {
    "wili-2018.zip": "727e52ca4e13400e6def1b1b594ca12c8b7fd49ad9d45fd5c9e57a1f6d3b7a3f",
    "train-images-idx3-ubyte.gz": "440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609",
    "train-labels-idx1-ubyte.gz": "3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c",
    "t10k-images-idx3-ubyte.gz": "8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6",
    "t10k-labels-idx1-ubyte.gz": "f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6",
}


# ----------------------------------------------------------------------------- helpers
def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def u64be(n):
    return int(n).to_bytes(8, "big")


def u32be(n):
    return int(n).to_bytes(4, "big")


def shake(msg, length):
    return hashlib.shake_256(msg).digest(length)


def read_verified(name):
    path = os.path.join(DATA, name)
    with open(path, "rb") as f:
        raw = f.read()
    got = sha256_hex(raw)
    if got != FILE_SHA[name]:
        raise RuntimeError(f"SHA-256 mismatch for {name}: {got}")
    return raw


# ----------------------------------------------------------------------------- data (§1)
def load_wili():
    raw = read_verified("wili-2018.zip")
    import io

    zf = zipfile.ZipFile(io.BytesIO(raw))
    members = {}
    member_raw = {}
    for m in ("x_train.txt", "y_train.txt", "x_test.txt", "y_test.txt"):
        b = zf.read(m)
        member_raw[m] = b
        s = b.decode("utf-8", errors="strict")
        members[m] = s.splitlines()
    x_train = [t.encode("utf-8") for t in members["x_train.txt"]]
    x_test = [t.encode("utf-8") for t in members["x_test.txt"]]
    ytr = members["y_train.txt"]
    yte = members["y_test.txt"]
    labels = sorted(set(ytr))
    assert len(labels) == 235, len(labels)
    idx = {l: i for i, l in enumerate(labels)}
    y_train = np.array([idx[l] for l in ytr], dtype=np.int64)
    y_test = np.array([idx[l] for l in yte], dtype=np.int64)
    return dict(
        x_train=x_train,
        y_train=y_train,
        x_test=x_test,
        y_test=y_test,
        labels=labels,
        member_raw=member_raw,
        y_train_str=ytr,
    )


def _idx(raw_gz, magic_expected):
    b = gzip.decompress(raw_gz)
    if magic_expected == 2051:
        magic, count, rows, cols = struct.unpack(">IIII", b[:16])
        assert magic == 2051
        arr = np.frombuffer(b, dtype=np.uint8, offset=16).reshape(count, rows * cols)
        return b, arr
    magic, count = struct.unpack(">II", b[:8])
    assert magic == 2049
    arr = np.frombuffer(b, dtype=np.uint8, offset=8)
    assert arr.shape[0] == count
    return b, arr


def load_mnist():
    out = {}
    for key, name, magic in (
        ("xtr", "train-images-idx3-ubyte.gz", 2051),
        ("ytr", "train-labels-idx1-ubyte.gz", 2049),
        ("xte", "t10k-images-idx3-ubyte.gz", 2051),
        ("yte", "t10k-labels-idx1-ubyte.gz", 2049),
    ):
        raw, arr = _idx(read_verified(name), magic)
        out[key] = arr
        out[key + "_raw"] = raw
    labels = [str(i) for i in range(10)]
    return dict(
        x_train=out["xtr"],
        y_train=out["ytr"].astype(np.int64),
        x_test=out["xte"],
        y_test=out["yte"].astype(np.int64),
        labels=labels,
        raw=out,
    )


# ----------------------------------------------------------------------------- RNG (§1.3)
def select_shots(y_train, n_classes, shots, seed=SEED):
    G = np.random.default_rng(seed)
    chosen = []
    draws = []
    for c in range(n_classes):
        cand = np.flatnonzero(y_train == c).astype(np.int64)
        d = G.choice(cand, size=shots, replace=False)
        draws.append(d)
        chosen.append(d)
    selected = np.sort(np.concatenate(chosen))
    return selected, draws


# ----------------------------------------------------------------------------- bits (§2-§4, §6)
def item_memory(sym, seed=SEED):
    msg = u64be(seed) + u64be(len(sym)) + sym
    return np.frombuffer(shake(msg, NB), dtype=np.uint8).copy()


def rho(v, k):
    """Cyclic rotation over components: out_i = v_{(i-k) mod D} (np.roll on bits)."""
    n = v.shape[-1] * 8
    return np.packbits(np.roll(np.unpackbits(v), k))[: n // 8]


def tie_stream_bits(identity, seed=SEED, d=D):
    msg = u64be(seed) + u64be(d) + u64be(len(identity)) + identity
    return np.unpackbits(np.frombuffer(shake(msg, d // 8), dtype=np.uint8))


def binarise_encoding(T, seed=SEED):
    """§6.2: T int array (D,). Returns packed uint8 (1250,)."""
    pos = T > 0
    tie = T == 0
    if not tie.any():
        return np.packbits(pos)
    ident = b"encoding\x00" + np.packbits(pos).tobytes() + np.packbits(tie).tobytes()
    stream = tie_stream_bits(ident, seed)
    out = np.where(tie, stream.astype(bool), pos)
    return np.packbits(out)


def binarise_encoding_batch(T, seed=SEED):
    """T: (N, D) int array. Returns (N, 1250) uint8 and number of tied components per row."""
    pos = T > 0
    tie = T == 0
    P = np.packbits(pos, axis=1)
    Z = np.packbits(tie, axis=1)
    ntie = tie.sum(axis=1)
    out = P.copy()
    for i in np.flatnonzero(ntie):
        ident = b"encoding\x00" + P[i].tobytes() + Z[i].tobytes()
        msg = u64be(seed) + u64be(D) + u64be(len(ident)) + ident
        stream = np.frombuffer(shake(msg, NB), dtype=np.uint8)
        # tied positions take the stream bit at the same index
        out[i] = P[i] | (stream & Z[i])
    return out, ntie


_proto_stream_cache = {}


def proto_stream_packed(label, seed=SEED):
    key = (label, seed)
    if key not in _proto_stream_cache:
        ident = b"prototype\x00" + label.encode("utf-8")
        msg = u64be(seed) + u64be(D) + u64be(len(ident)) + ident
        _proto_stream_cache[key] = np.frombuffer(shake(msg, NB), dtype=np.uint8).copy()
    return _proto_stream_cache[key]


def binarise_proto(row, label, seed=SEED):
    """§6.3 prototype tie rule. row: int (D,)."""
    P = np.packbits(row > 0)
    Z = np.packbits(row == 0)
    return P | (proto_stream_packed(label, seed) & Z)


# ----------------------------------------------------------------------------- trigram encoder (§5)
class TrigramEncoder:
    def __init__(self, seed=SEED):
        self.seed = seed
        base = np.stack([item_memory(bytes([b]), seed) for b in range(256)])  # (256,1250)
        self.R0 = base
        self.R1 = np.stack([rho(v, 1) for v in base])
        self.R2 = np.stack([rho(v, 2) for v in base])
        # padded uint64 views for the fast path (1256 bytes = 157 words)
        pad = lambda a: np.concatenate([a, np.zeros((256, 6), np.uint8)], axis=1)
        self.W0 = np.ascontiguousarray(pad(self.R0)).view(np.uint64)
        self.W1 = np.ascontiguousarray(pad(self.R1)).view(np.uint64)
        self.W2 = np.ascontiguousarray(pad(self.R2)).view(np.uint64)

    def sums_reference(self, x):
        """Naive exact T for one text (bytes)."""
        a = np.frombuffer(x, dtype=np.uint8)
        n = a.shape[0]
        if n < 3:
            raise ValueError("text shorter than 3 bytes")
        G = self.R2[a[:-2]] ^ self.R1[a[1:-1]] ^ self.R0[a[2:]]
        m = n - 2
        cnt = np.unpackbits(G, axis=1).sum(axis=0, dtype=np.int64)
        return (2 * cnt - m).astype(np.int32)

    # fast bit counting: byte-lane SWAR counting on uint64 words
    _LANE = np.uint64(0x0101010101010101)

    def counts_fast(self, x):
        a = np.frombuffer(x, dtype=np.uint8)
        n = a.shape[0]
        if n < 3:
            raise ValueError("text shorter than 3 bytes")
        m = n - 2
        acc = np.zeros((8, 157, 8), dtype=np.int64)  # (bit-in-byte shift, word, lane)
        lane = self._LANE
        for s0 in range(0, m, 255):
            s1 = min(m, s0 + 255)
            Gw = self.W2[a[s0:s1]] ^ self.W1[a[s0 + 1 : s1 + 1]] ^ self.W0[a[s0 + 2 : s1 + 2]]
            for b in range(8):
                lanesum = ((Gw >> np.uint64(b)) & lane).sum(axis=0, dtype=np.uint64)
                acc[b] += lanesum.view(np.uint8).reshape(157, 8)
        # acc[b, w, l] = count of bit b (LSB-index) of byte (8w+l)
        # component index i = 8*byte + (7 - b)
        cnt = acc.transpose(1, 2, 0)[:, :, ::-1].reshape(-1)[:D]
        return cnt, m

    def encode_one(self, x):
        cnt, m = self.counts_fast(x)
        T = (2 * cnt - m).astype(np.int32)
        return binarise_encoding(T, self.seed), T


# ----------------------------------------------------------------------------- thermometer encoder (§7)
class ThermometerEncoder:
    Q = 16

    def __init__(self, seed=SEED, positions=784):
        self.seed = seed
        self.positions = positions
        self.Pos = np.stack([item_memory(b"pixel:" + str(p).encode("ascii"), seed) for p in range(positions)])
        base_bits = np.unpackbits(item_memory(b"thermometer:base", seed))
        self.seed_T = int.from_bytes(shake(u64be(seed) + b"thermometer:order", 8), "big")
        self.order = np.random.default_rng(self.seed_T).permutation(D)
        per_step = D // (2 * (self.Q - 1))
        self.per_step = per_step
        levels = [base_bits.copy()]
        for q in range(1, self.Q):
            L = levels[-1].copy()
            for idx in self.order[(q - 1) * per_step : q * per_step]:
                L[idx] ^= 1
            levels.append(L)
        self.L_bits = np.stack(levels)  # (16, D) uint8
        self.L = np.packbits(self.L_bits, axis=1)
        # gemm formulation
        rank = np.empty(D, dtype=np.int64)
        rank[self.order] = np.arange(D)
        self.t = rank // per_step + 1  # component j flipped at level q iff q >= t_j
        self.sPos = (2.0 * np.unpackbits(self.Pos, axis=1).astype(np.float32) - 1.0)  # (784, D)
        self.sL0 = 2 * base_bits.astype(np.int32) - 1
        self.colsum = self.sPos.sum(axis=0).astype(np.int64)  # exact
        self.groups = [(tt, np.flatnonzero(self.t == tt)) for tt in range(1, self.Q)]

    @staticmethod
    def quantise(x):
        return (x.astype(np.int64) * 16) // 256

    def sums_reference(self, img):
        q = self.quantise(img)
        B = self.Pos ^ self.L[q]
        cnt = np.unpackbits(B, axis=1).sum(axis=0, dtype=np.int64)
        return (2 * cnt - self.positions).astype(np.int32)

    def sums_batch(self, imgs):
        """Exact T for a batch (N,784) via float32 GEMM on +-1 (all partial sums are small integers)."""
        q = self.quantise(imgs)
        N = imgs.shape[0]
        inner = np.empty((N, D), dtype=np.int64)
        inner[:] = self.colsum[None, :]
        for tt, cols in self.groups:
            Ind = (q >= tt).astype(np.float32)
            M = Ind @ self.sPos[:, cols]
            inner[:, cols] = self.colsum[cols][None, :] - 2 * np.rint(M).astype(np.int64)
        T = -self.sL0[None, :] * inner
        return T.astype(np.int32)

    def encode_batch(self, imgs, chunk=2000):
        outs = []
        ties = []
        for s in range(0, imgs.shape[0], chunk):
            T = self.sums_batch(imgs[s : s + chunk])
            e, nt = binarise_encoding_batch(T, self.seed)
            outs.append(e)
            ties.append(nt)
        return np.concatenate(outs), np.concatenate(ties)


# ----------------------------------------------------------------------------- similarity / metrics (§9, §13)
def to_signed_f32(packed, chunk=4096):
    packed = np.asarray(packed)
    if packed.ndim == 1:
        return 2.0 * np.unpackbits(packed).astype(np.float32) - 1.0
    out = np.empty((packed.shape[0], packed.shape[1] * 8), dtype=np.float32)
    for s in range(0, packed.shape[0], chunk):
        b = np.unpackbits(packed[s : s + chunk], axis=1).astype(np.float32)
        b *= 2.0
        b -= 1.0
        out[s : s + chunk] = b
    return out


def hamming_matrix(Q_packed, P_packed, chunk=2048):
    """Exact Hamming distances (int64) via float32 GEMM on +-1."""
    Ps = to_signed_f32(P_packed)
    out = np.empty((Q_packed.shape[0], P_packed.shape[0]), dtype=np.int64)
    for s in range(0, Q_packed.shape[0], chunk):
        Qs = to_signed_f32(Q_packed[s : s + chunk])
        dot = Qs @ Ps.T
        out[s : s + chunk] = (D - np.rint(dot).astype(np.int64)) // 2
    return out


def sim_of_dist(d):
    return 1.0 - ((2.0 * d) / 10000.0)


def pairwise_sum(a):
    n = len(a)
    if n < 8:
        res = a[0]
        for x in a[1:]:
            res += x
        return res
    if n <= 128:
        r = list(a[:8])
        i = 8
        while i < n - (n % 8):
            for j in range(8):
                r[j] += a[i + j]
            i += 8
        res = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
        while i < n:
            res += a[i]
            i += 1
        return res
    n2 = n // 2
    n2 -= n2 % 8
    return pairwise_sum(a[:n2]) + pairwise_sum(a[n2:])


def evaluate(y, yhat, labels):
    y = np.asarray(y, dtype=np.int64)
    yhat = np.asarray(yhat, dtype=np.int64)
    K = len(labels)
    n = y.shape[0]
    acc = int((y == yhat).sum()) / n
    f1 = []
    for c in range(K):
        tp = int(((y == c) & (yhat == c)).sum())
        pc = int((yhat == c).sum())
        ac = int((y == c).sum())
        f1.append(0.0 if pc + ac == 0 else (2.0 * tp) / (pc + ac))
    macro_pw = pairwise_sum(f1) / K
    macro_np = float(np.mean(np.array(f1, dtype=np.float64)))
    h = hashlib.sha256()
    lab_b = [l.encode("utf-8") + b"\n" for l in labels]
    h.update(b"".join(lab_b[i] for i in yhat))
    return dict(accuracy=acc, macro_f1=macro_pw, macro_f1_numpy_mean=macro_np, predictions_sha256=h.hexdigest(), n_test=n)
