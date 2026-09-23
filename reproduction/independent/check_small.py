import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import hdc
from hdc import sha256_hex, item_memory, rho, D

RESULTS = []


def rec(section, name, got, expected):
    ok = got == expected
    RESULTS.append(dict(section=section, check=name, got=str(got), expected=str(expected), ok=bool(ok)))
    print(("PASS" if ok else "FAIL"), section, name, "| got:", got, "| exp:", expected, flush=True)


# ---------------------------------------------------------------- §2 / §4 worked examples
v = np.array([0xC0, 0x01], dtype=np.uint8)
rec("4", "rho^1 D=16 [C0,01]", rho(v, 1).tobytes().hex(), "e000")
rec("4", "rho^2 D=16 [C0,01]", rho(v, 2).tobytes().hex(), "7000")
rec("2", "packbits example", np.packbits(np.array([1,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,1], np.uint8)).tobytes().hex(), "8001")

# ---------------------------------------------------------------- §3 / §14.3 item memory
a = item_memory(b"a")
rec("3", "IM(a) first 8", a[:8].tobytes().hex(), "523f0c1100d43dbd")
rec("3", "IM(a) first 16 components", "".join(map(str, np.unpackbits(a)[:16])), "0101001000111111")
rec("14.3", "IM(a) sha256", sha256_hex(a.tobytes()), "c80826456f683afcc9e1d6af917a07c9b228cb0700a10f9200c69c6dc3dd2a8b")
rec("14.3", "IM(a) popcount", int(np.unpackbits(a).sum()), 5011)
rec("4", "rho^2(IM(a)) first 8", rho(a, 2)[:8].tobytes().hex(), "148fc30440350f6f")
rec("4", "rho^1(IM(a)) first 8", rho(a, 1)[:8].tobytes().hex(), "291f8608806a1ede")
rec("14.3", "IM(\\x00) first 8", item_memory(b"\x00")[:8].tobytes().hex(), "7a70e7f7351608f6")
rec("14.3", "IM(h) first 8", item_memory(b"h")[:8].tobytes().hex(), "d24986c03dfa12bb")
rec("14.3", "IM(pixel:0) first 8", item_memory(b"pixel:0")[:8].tobytes().hex(), "afddd6de5311e14a")
rec("14.3", "IM(pixel:783) first 8", item_memory(b"pixel:783")[:8].tobytes().hex(), "42abbd45d8903552")
tb = item_memory(b"thermometer:base")
rec("14.3", "IM(thermometer:base) first 8", tb[:8].tobytes().hex(), "cc20929fdacc2b2f")
rec("14.3", "IM(thermometer:base) sha256", sha256_hex(tb.tobytes()), "33c85042f39eca24b790e477b9eb75bc4c68439ccbaba0e5915240a2681e9fa5")
rec("14.3", "IM(a) seed 7 first 8", item_memory(b"a", 7)[:8].tobytes().hex(), "763264777c3538a9")
stack256 = np.stack([item_memory(bytes([b])) for b in range(256)])
rec("14.3", "256 byte-symbol stack sha256", sha256_hex(stack256.tobytes()), "b8cfa6c95726d2c53273497c451580cf2fcd9b9e6260eaa52d8915fd39599036")
stack784 = np.stack([item_memory(b"pixel:" + str(p).encode()) for p in range(784)])
rec("14.3", "784 position stack sha256", sha256_hex(stack784.tobytes()), "9171ffbabe0f3a0f955cb215a7c1fca24932ed6a50dfe62f5fc5857b3fa5d3e3")

# ---------------------------------------------------------------- §14.6 prototype tie streams
rec("14.6", "proto stream '0'", hdc.proto_stream_packed("0")[:8].tobytes().hex(), "776ca019dfb2eabd")
rec("14.6", "proto stream '1'", hdc.proto_stream_packed("1")[:8].tobytes().hex(), "88eaba1c35868e7c")
rec("14.6", "proto stream 'ace'", hdc.proto_stream_packed("ace")[:8].tobytes().hex(), "f98083b7a18ae24c")

# ---------------------------------------------------------------- §14.2 RNG
g = np.random.default_rng(42)
st = g.bit_generator.state["state"]
rec("14.2", "PCG64 state", hex(st["state"]), "0xcea44f6798798f2aacbc7c9d68860ac8")
rec("14.2", "PCG64 inc", hex(st["inc"]), "0xfa505436c9a8416e66caf2e28d25abff")
raw3 = [hex(int(x)) for x in g.bit_generator.random_raw(3)]
rec("14.2", "first 3 raw", raw3, ["0xc621fbcd16d92688", "0x705a5661a791ffc1", "0xdbcd12c26eda1624"])

# pure-python Appendix A reference cross-check
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import appendix_a as AA
pg = AA.PCG64(42)
rec("A", "appendix PCG64(42) first 3 raw", [hex(pg.next64()) for _ in range(3)], ["0xc621fbcd16d92688", "0x705a5661a791ffc1", "0xdbcd12c26eda1624"])

therm_seed = int.from_bytes(hdc.shake(hdc.u64be(42) + b"thermometer:order", 8), "big")
rec("14.2", "thermometer seed digest", hdc.shake(hdc.u64be(42) + b"thermometer:order", 8).hex(), "3b2dc15762e2d7bf")
rec("14.2", "thermometer seed int", therm_seed, 4264277003255076799)
order = np.random.default_rng(therm_seed).permutation(D)
rec("14.2", "order[0:10]", order[:10].tolist(), [2562, 8813, 3284, 2626, 5087, 6837, 2256, 2241, 1915, 2629])
rec("14.2", "order[330:336]", order[330:336].tolist(), [6610, 5863, 7506, 4645, 9618, 1941])
order_py = AA.permutation(AA.PCG64(therm_seed), D)
rec("A", "appendix permutation(10000) == numpy", order_py == order.tolist(), True)

R = np.random.default_rng(42)
p1 = R.permutation(60000); p2 = R.permutation(60000)
rec("14.2", "T2 epoch1 first 16", p1[:16].tolist(), [3493, 57546, 8815, 19332, 15566, 22963, 21972, 22093, 1818, 46044, 31538, 36479, 9523, 57704, 10133, 53353])
rec("14.2", "T2 epoch2 first 16", p2[:16].tolist(), [17284, 27577, 35294, 27278, 56928, 12169, 6580, 45132, 27388, 57966, 17348, 27607, 31833, 41489, 49994, 21295])
gpy = AA.PCG64(42)
q1 = AA.permutation(gpy, 60000); q2 = AA.permutation(gpy, 60000)
rec("A", "appendix two permutation(60000) == numpy", (q1 == p1.tolist()) and (q2 == p2.tolist()), True)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "checks_small.json"), "w") as f:
    json.dump(RESULTS, f, indent=1)
print("n_fail", sum(not r["ok"] for r in RESULTS))
