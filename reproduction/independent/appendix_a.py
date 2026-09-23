"""Pure-Python reference of the NumPy Generator(PCG64) paths, transcribed from SPEC Appendix A."""
M32 = 0xFFFFFFFF; M64 = (1 << 64) - 1; M128 = (1 << 128) - 1

INIT_A = 0x43b0d7e5; MULT_A = 0x931e8875
INIT_B = 0x8b51f9dd; MULT_B = 0x58f38ded
MIX_MULT_L = 0xca01f9dd; MIX_MULT_R = 0x4973f715
XSHIFT = 16


def seedseq_state(seed_int, n_words64=4):
    words = []
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
    for s in range(4, len(words)):
        for d in range(4):
            pool[d] = mix(pool[d], hashmix(words[s]))
    hb = INIT_B
    out32 = []
    for i in range(2 * n_words64):
        v = pool[i % 4]
        v ^= hb
        hb = (hb * MULT_B) & M32
        v = (v * hb) & M32
        v ^= v >> XSHIFT
        out32.append(v)
    return [out32[2*i] | (out32[2*i+1] << 32) for i in range(n_words64)]


PCG_MULT = 0x2360ED051FC65DA44385DF649FCCF645


class PCG64:
    def __init__(self, seed_int):
        s = seedseq_state(seed_int)
        initstate = (s[0] << 64) | s[1]
        initseq = (s[2] << 64) | s[3]
        self.inc = ((initseq << 1) | 1) & M128
        self.state = 0
        self._step()
        self.state = (self.state + initstate) & M128
        self._step()
        self.has32 = False; self.u32 = 0

    def _step(self):
        self.state = (self.state * PCG_MULT + self.inc) & M128

    def next64(self):
        self._step()
        st = self.state
        x = ((st >> 64) ^ st) & M64
        rot = st >> 122
        return ((x >> rot) | (x << ((64 - rot) & 63))) & M64

    def next32(self):
        if self.has32:
            self.has32 = False
            return self.u32
        v = self.next64()
        self.has32 = True
        self.u32 = v >> 32
        return v & M32


def random_interval(g, mx):
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


def permutation(g, n):
    a = list(range(n))
    for i in range(n - 1, 0, -1):
        j = random_interval(g, i)
        a[i], a[j] = a[j], a[i]
    return a


def choice_noreplace(g, pop, size):
    n = len(pop)
    chosen = set(); idx = []
    for j in range(n - size, n):
        v = bounded_lemire(g, j)
        if v not in chosen:
            chosen.add(v); idx.append(v)
        else:
            chosen.add(j); idx.append(j)
    for i in range(size - 1, 0, -1):
        j = bounded_lemire(g, i)
        idx[i], idx[j] = idx[j], idx[i]
    return [pop[k] for k in idx]
