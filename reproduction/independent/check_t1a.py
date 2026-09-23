import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import hdc, model
from hdc import sha256_hex

RESULTS = []


def rec(section, name, got, expected):
    ok = got == expected
    RESULTS.append(dict(section=section, check=name, got=str(got), expected=str(expected), ok=bool(ok)))
    print(("PASS" if ok else "FAIL"), section, name, "| got:", got, "| exp:", expected, flush=True)


W = hdc.load_wili()
selected = np.load(os.path.join(HERE, "out", "wili_selected.npy"))
tr_enc = np.load(os.path.join(HERE, "out", "wili_train_enc.npy"))
ylab = [W["labels"][W["y_train"][i]] for i in selected]
m = model.Prototypes(42)
m.register(W["labels"])
for s in range(0, len(ylab), 5000):
    m.learn(tr_enc[s:s + 5000], ylab[s:s + 5000])
rec("14.7", "(a) model labels == dataset labels", m.labels == W["labels"], True)
rec("14.7", "(a) A sha256 (int16 LE)", sha256_hex(m.A.astype("<i2").tobytes()), "7d7fad7d6b95959531e7a2a780a9a0e3ecec7cfc99789b4ec6f88461a42496a3")
rec("14.7", "(a) P sha256", sha256_hex(m.P.tobytes()), "d6b6964c9a84b9aec50be9996aa0a61dc3fdc75dc40dd166f5a5f60328f8bcd7")
rec("14.7", "(a) zeros in A total / in ace", (int((m.A == 0).sum()), int((m.A[0] == 0).sum())), (264024, 1132))
rec("14.7", "(a) A[ace][0:8]", m.A[0, :8].tolist(), [4, -2, -4, -4, -2, -2, 8, 8])
rec("14.7", "(a) P[ace] first 8", m.P[0, :8].tobytes().hex(), "83b10e5a29653b3f")
rec("14.7", "(a) halvings", m.halvings, 0)
np.save(os.path.join(HERE, "out", "a_A.npy"), m.A); np.save(os.path.join(HERE, "out", "a_P.npy"), m.P)

# halving unit test (synthetic): sign preserving, +-1 stays +-1
v = np.array([0, 1, -1, 2, -3, 16385, -16386, 7], dtype=np.int32)
rec("impl", "halve()", model.Prototypes._halve(v).tolist(), [0, 1, -1, 1, -1, 8192, -8193, 3])

# episode ids for the first 3 MNIST training encodings
M = hdc.load_mnist()
th = hdc.ThermometerEncoder(42)
e3, _ = th.encode_batch(M["x_train"][:3])
ids = model.episode_ids(e3, [str(int(y)) for y in M["y_train"][:3]])
rec("14.9", "id_0..id_2", [format(int(x), "016x") for x in ids], ["ab6dcd5d3aab77ec", "1cbfa3bd5d2d0c09", "dab99623275d09ab"])

with open(os.path.join(HERE, "out", "checks_t1a.json"), "w") as f:
    json.dump(RESULTS, f, indent=1)
print("n_fail", sum(not r["ok"] for r in RESULTS))
