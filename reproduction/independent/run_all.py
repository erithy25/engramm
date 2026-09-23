"""End-to-end runner for configurations (a)-(d), with the §14 conformance checks that need full data.

usage: run_all.py [--small] [stages...]   stages: a mnist_enc b c d  (default: all)
"""
import os, sys, time, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import hdc, model
from hdc import sha256_hex, D

SMALL = "--small" in sys.argv
stages = [a for a in sys.argv[1:] if not a.startswith("--")] or ["a", "mnist_enc", "b", "c", "d"]
OUT = os.path.join(HERE, "out_small" if SMALL else "out")
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "run.log"), "a")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(time.strftime("%H:%M:%S ") + s + "\n"); LOG.flush()


RESULTS = []
CHECKFILE = os.path.join(OUT, "checks_full.json")
if os.path.exists(CHECKFILE):
    RESULTS = [r for r in json.load(open(CHECKFILE))]


def rec(section, name, got, expected):
    ok = got == expected
    global RESULTS
    RESULTS = [r for r in RESULTS if not (r["section"] == section and r["check"] == name)]
    RESULTS.append(dict(section=section, check=name, got=str(got), expected=str(expected), ok=bool(ok)))
    log(("PASS" if ok else "FAIL"), section, name, "| got:", got, "| exp:", expected)
    with open(CHECKFILE, "w") as f:
        json.dump(RESULTS, f, indent=1)


def save_result(cfg, res):
    p = os.path.join(OUT, "results.json")
    allr = json.load(open(p)) if os.path.exists(p) else {}
    allr[cfg] = res
    with open(p, "w") as f:
        json.dump(allr, f, indent=1)
    log("RESULT", cfg, json.dumps(res))


# ============================================================================ (a) WiLI
def stage_a():
    t0 = time.time()
    W = hdc.load_wili()
    selected, _ = hdc.select_shots(W["y_train"], 235, 10, 42)
    enc = hdc.TrigramEncoder(42)
    ylab = [W["labels"][W["y_train"][i]] for i in selected]
    tr_enc = np.stack([enc.encode_one(W["x_train"][i])[0] for i in selected])
    m = model.Prototypes(42)
    m.register(W["labels"])
    for s in range(0, len(selected), 5000):
        m.learn(tr_enc[s:s + 5000], ylab[s:s + 5000])
    if m.halvings:
        raise RuntimeError("halving occurred in (a)")
    rec("14.7", "(a) A sha256 [runner]", sha256_hex(m.A.astype("<i2").tobytes()), "7d7fad7d6b95959531e7a2a780a9a0e3ecec7cfc99789b4ec6f88461a42496a3")
    rec("14.7", "(a) P sha256 [runner]", sha256_hex(m.P.tobytes()), "d6b6964c9a84b9aec50be9996aa0a61dc3fdc75dc40dd166f5a5f60328f8bcd7")
    x_test = W["x_test"]; y_test = W["y_test"]
    if SMALL:
        x_test = x_test[:3000]; y_test = y_test[:3000]
    n = len(x_test)
    te = np.empty((n, hdc.NB), dtype=np.uint8)
    t1 = time.time()
    ntied_texts = 0
    for i, x in enumerate(x_test):
        e, T = enc.encode_one(x)
        te[i] = e
        if i % 10000 == 0:
            log(f"  (a) encoded {i}/{n} {time.time()-t1:.1f}s")
    t_enc = time.time() - t1
    np.save(os.path.join(OUT, "wili_test_enc.npy"), te)
    rec("14.4", "first 100 test encodings sha256 [runner]", sha256_hex(te[:100].tobytes()), "bc47359e3bc03f90628d3864a89eebd0dbdd1cd47110a829ce1cd886358c2f89")
    pred, d = m.predict(te)
    res = hdc.evaluate(y_test, pred, W["labels"])
    trainset = set(W["x_train"])
    dup = np.array([x in trainset for x in x_test])
    keep = ~dup
    res["test_items_in_train"] = int(dup.sum())
    res["accuracy_excluding_train_duplicates"] = int((pred[keep] == y_test[keep]).sum()) / int(keep.sum())
    res["n_train"] = len(selected); res["n_classes"] = 235; res["chance_level"] = 1 / 235
    res["halvings"] = m.halvings
    res["runtime_s"] = round(time.time() - t0, 1); res["test_encoding_s"] = round(t_enc, 1)
    np.save(os.path.join(OUT, "a_predictions.npy"), pred.astype(np.int64))
    save_result("a", res)


# ============================================================================ MNIST encodings
def stage_mnist_enc():
    t0 = time.time()
    M = hdc.load_mnist()
    th = hdc.ThermometerEncoder(42)
    xtr = M["x_train"]; xte = M["x_test"]
    if SMALL:
        xtr = xtr[:4000]; xte = xte[:500]
    etr, ntr = th.encode_batch(xtr)
    ete, nte = th.encode_batch(xte)
    np.save(os.path.join(OUT, "mnist_train_enc.npy"), etr)
    np.save(os.path.join(OUT, "mnist_test_enc.npy"), ete)
    log(f"  MNIST encoding {time.time()-t0:.1f}s; mean ties train {ntr.mean():.1f} test {nte.mean():.1f}")
    rec("14.5", "first 1000 train encodings sha256 [runner]", sha256_hex(etr[:1000].tobytes()), "39efb3167dd91b99d60201ad8996d2363cccbe94bf02a8f5072c7de0ca0b25d2")
    rec("14.5", "all 60000 train encodings sha256", sha256_hex(etr.tobytes()), "c9ca644eac5c3a55dc8de32f9a73bf12c311f35ec7feed368bb90fb27f8dca79")
    rec("14.5", "first 1000 test encodings sha256 [runner]", sha256_hex(ete[:1000].tobytes()), "24e8d4226032991db7d1534022b8f8868c160f70dc01aec9e7fa1edd6adc972c")
    json.dump(dict(mnist_encoding_s=round(time.time() - t0, 1)), open(os.path.join(OUT, "mnist_enc_time.json"), "w"))


def load_mnist_enc():
    M = hdc.load_mnist()
    etr = np.load(os.path.join(OUT, "mnist_train_enc.npy"))
    ete = np.load(os.path.join(OUT, "mnist_test_enc.npy"))
    ytr = M["y_train"][: etr.shape[0]]; yte = M["y_test"][: ete.shape[0]]
    return M, etr, ytr, ete, yte


def check_mnist_t1(m, tag):
    rec("14.7", f"MNIST T1 A sha256 ({tag})", sha256_hex(m.A.astype("<i2").tobytes()), "b14227b9968fc12c5cd6eb50f11e9f27f9cefade3e5ffaf8aa88cd3c3912359a")
    rec("14.7", f"MNIST T1 P sha256 ({tag})", sha256_hex(m.P.tobytes()), "60f9d66f0df01b577b953821eda4579aa3cc431aa117c17308a8f033a39eae32")
    rec("14.7", f"MNIST T1 zeros per class ({tag})", (m.A == 0).sum(axis=1).tolist(), [0, 1, 1, 0, 0, 0, 0, 0, 0, 0])
    rec("14.7", f"MNIST T1 max|A| ({tag})", int(np.abs(m.A.astype(np.int32)).max()), 6742)
    rec("14.7", f"MNIST T1 A[0][0:8], P[0] first8 ({tag})", (m.A[0, :8].tolist(), m.P[0, :8].tobytes().hex()), ([-4325, 3499, -5923, -5923, 5923, 4949, -3441, -3931], "4cc82f061d5236c7"))
    rec("14.7", f"MNIST T1 A[1][0:8], P[1] first8 ({tag})", (m.A[1, :8].tolist(), m.P[1, :8].tobytes().hex()), ([-6580, 5954, -6742, -6742, 6742, 6552, -3234, -1210], "4ce90e0f1f5236d7"))


# ============================================================================ (b)
def stage_b():
    t0 = time.time()
    M, etr, ytr, ete, yte = load_mnist_enc()
    labels = M["labels"]
    m = model.Prototypes(42)
    m.register(labels)
    for s in range(0, etr.shape[0], 5000):
        m.learn(etr[s:s + 5000], [labels[c] for c in ytr[s:s + 5000]])
    if m.halvings:
        raise RuntimeError("halving in (b)")
    check_mnist_t1(m, "b, 12 batches")
    pred, _ = m.predict(ete)
    res = hdc.evaluate(yte, pred, labels)
    res.update(n_train=int(etr.shape[0]), n_classes=10, chance_level=0.1, halvings=m.halvings,
               runtime_s_excluding_encoding=round(time.time() - t0, 1))
    np.save(os.path.join(OUT, "b_predictions.npy"), pred.astype(np.int64))
    save_result("b", res)


# ============================================================================ (c)
def stage_c():
    t0 = time.time()
    M, etr, ytr, ete, yte = load_mnist_enc()
    labels = M["labels"]
    m = model.Prototypes(42)
    m.register(labels)
    m.learn(etr, [labels[c] for c in ytr])
    check_mnist_t1(m, "c, one call")
    cfg = dict(k=32, theta0=0.0, lambda_e=1.0, lambda_p=1.0, util_clip=8, t2_local=False)
    cfg["lambda_e"] = 0.0  # pipeline=prototypes with T2 epochs > 0
    ids = model.episode_ids(etr, [labels[c] for c in ytr])  # episodes created, never read
    episodes = dict(val=ytr.copy(), util=np.zeros(etr.shape[0], np.int16), ids=ids)
    t1 = time.time()
    errors, misses = model.run_t2(m, etr, ytr, 2, cfg, episodes=None, log=log)
    t_t2 = time.time() - t1
    rec("14.8", "(c) T2 misses per epoch", misses, [10747, 9125])
    rec("14.8", "(c) t2_error_per_epoch", errors, [0.179117, 0.152083])
    rec("14.8", "(c) A sha256 after T2", sha256_hex(m.A.astype("<i2").tobytes()), "6f84e91d2eb131ad90e2fd2fba4c165cb7de77fdd00155cd9474240e31d614b5")
    rec("14.8", "(c) P sha256 after T2", sha256_hex(m.P.tobytes()), "a8b15f4c1e647d9066d4ee2a4ccc88a4db6c3c11fe8ed6d236553bfe78bc44b8")
    rec("14.8", "(c) max|A| / halvings / utilities all 0", (int(np.abs(m.A.astype(np.int32)).max()), m.halvings, int(np.count_nonzero(episodes["util"]))), (7015, 0, 0))
    pred, _ = m.predict(ete)
    if m.halvings:
        raise RuntimeError("halving in (c)")
    res = hdc.evaluate(yte, pred, labels)
    res.update(n_train=int(etr.shape[0]), n_classes=10, chance_level=0.1, halvings=m.halvings,
               t2_error_per_epoch=errors, t2_misses_per_epoch=misses, t2_s=round(t_t2, 1),
               runtime_s_excluding_encoding=round(time.time() - t0, 1), config=cfg)
    np.save(os.path.join(OUT, "c_predictions.npy"), pred.astype(np.int64))
    save_result("c", res)


# ============================================================================ (d)
def stage_d():
    t0 = time.time()
    M, etr, ytr, ete, yte = load_mnist_enc()
    labels = M["labels"]
    N = etr.shape[0]
    cfg = dict(k=32, theta0=0.2, lambda_e=0.25, lambda_p=1.0, util_clip=8, t2_local=False)
    m = model.Prototypes(42)
    m.register(labels)
    m.learn(etr, [labels[c] for c in ytr])
    check_mnist_t1(m, "d")
    ids = model.episode_ids(etr, [labels[c] for c in ytr])
    rec("14.9", "ids sha256 (u64be)", hashlib.sha256(ids.astype(">u8").tobytes()).hexdigest(), "fba1c601bfefac706d3b860de5d6ac1fc10306ab02478eaae6a8db48653478e8")
    rec("14.9", "ids distinct", len(np.unique(ids)) == N, True)
    jmin = int(np.argmin(ids))
    rec("14.9", "smallest id episode / value", (jmin, format(int(ids[jmin]), "016x")), (50981, "0001625fabf98577"))
    rank = model.ranks_from_ids(ids)
    rec("14.9", "rank[0:5]", rank[:5].tolist(), [40204, 6826, 51267, 54572, 22565])
    episodes = dict(val=ytr.astype(np.int64).copy(), util=np.zeros(N, np.int16), ids=ids, rank=rank)

    # leave-one-out neighbour lists, computed once (cached)
    nbf = os.path.join(OUT, "d_loo_nb.npz")
    t1 = time.time()
    keys_f32 = hdc.to_signed_f32(etr)
    if os.path.exists(nbf):
        z = np.load(nbf); nb_pos, nb_dist = z["pos"], z["dist"]
        log("  loaded cached LOO neighbour lists")
    else:
        nb_pos, nb_dist = model.topk_retrieval(etr, keys_f32, rank, k=cfg["k"], loo_offset=0, block=500, log=log)
        np.savez(nbf, pos=nb_pos, dist=nb_dist)
    t_loo = time.time() - t1
    log(f"  LOO retrieval {t_loo:.1f}s")
    rec("14.9", "train ex0 LOO top-8 positions", nb_pos[0, :8].tolist(), [32248, 18932, 30483, 26251, 21654, 31008, 52295, 46358])
    rec("14.9", "train ex0 LOO top-8 distances", nb_dist[0, :8].tolist(), [934, 942, 951, 973, 989, 993, 998, 999])
    i0 = 3493
    rec("14.9", "ex3493 label", int(ytr[i0]), 8)
    rec("14.9", "ex3493 LOO top-8 positions", nb_pos[i0, :8].tolist(), [26720, 27579, 59277, 22703, 59015, 3499, 295, 58302])
    rec("14.9", "ex3493 LOO top-8 distances", nb_dist[i0, :8].tolist(), [735, 738, 759, 762, 803, 807, 809, 818])
    rec("14.9", "ex3493 32nd neighbour distance", int(nb_dist[i0, 31]), 908)
    rec("14.9", "ex3493 all 32 neighbours class 8", bool((ytr[nb_pos[i0]] == 8).all()), True)
    episodes["nb_pos"] = nb_pos; episodes["nb_dist"] = nb_dist
    # brute-force cross-check of retrieval on a few queries (popcount + Python sort)
    k64 = model.pad64(etr)
    okb = True
    for q in [0, 1, 2, 3493 % N, N - 1]:
        dq = np.bitwise_count(k64 ^ k64[q][None, :]).sum(axis=1).astype(np.int64)
        cand = sorted((int(dq[j]), int(rank[j]), j) for j in range(N) if j != q)[:32]
        okb &= [c[2] for c in cand] == nb_pos[q].tolist() and [c[0] for c in cand] == nb_dist[q].tolist()
    rec("impl", "LOO retrieval == brute force popcount/sort (5 queries)", bool(okb), True)

    state = {}

    def checkpoint(ep, step, misses, info):
        if ep == 0 and step == 1:
            rec("14.9", "first T2 step example", info["i"], 3493)
            rec("14.9", "first step prototype sims", [round(x, 4) for x in info["sim"]], [0.757, 0.8068, 0.8034, 0.7942, 0.7772, 0.7908, 0.7944, 0.7666, 0.8178, 0.781])
            rec("14.9", "first step sims exact repr", [repr(x) for x in info["sim"]], [repr(x) for x in [0.757, 0.8068, 0.8034, 0.7942, 0.7772, 0.7908, 0.7944, 0.7666, 0.8178, 0.781]])
            rec("14.9", "first step fused == sims for c != 8", all(info["score"][c] == info["sim"][c] for c in range(10) if c != 8), True)
            rec("14.9", "first step class-8 fused score repr", repr(info["score"][8]), "5.856550000000001")
            rec("14.9", "first step prediction", info["pred"], 8)
            u = episodes["util"][nb_pos[3493]]
            rec("14.9", "first step: all 32 neighbours util +1", u.tolist(), [1] * 32)
        if ep == 0 and step == 1000:
            u = episodes["util"]
            rec("14.9", "after 1000 steps: misses", misses, 48)
            rec("14.9", "after 1000 steps: util sha256", sha256_hex(u.astype("<i2").tobytes()), "be1fbcbf700aece0b4bd5de3872af95cdc61a698d70b03a6083460a05490e634")
            rec("14.9", "after 1000 steps: util nonzero/min/max", (int(np.count_nonzero(u)), int(u.min()), int(u.max())), (22229, -3, 7))
            rec("14.9", "after 1000 steps: A sha256", sha256_hex(m.A.astype("<i2").tobytes()), "3e2945a9642d97ca80600abccb09ab6d7e7fe166640d75122aac080713031713")
            rec("14.9", "after 1000 steps: P sha256", sha256_hex(m.P.tobytes()), "d09d5b392ee3125771d0eaf59b39309a9fdb9a6339ed4578c5198c88932cfe58")

    t2s = time.time()
    errors, misses = model.run_t2(m, etr, ytr, 2, cfg, episodes=episodes, log=log, checkpoint=checkpoint)
    t_t2 = time.time() - t2s
    rec("14.9", "(d) T2 misses per epoch (recorded run)", misses, [3215, 3110])
    rec("14.9", "(d) t2_error_per_epoch (recorded run)", errors, [0.053583, 0.051833])
    u = episodes["util"]
    log(f"  final utilities: nonzero {np.count_nonzero(u)} min {u.min()} max {u.max()}; max|A| {np.abs(m.A.astype(np.int32)).max()} halvings {m.halvings}")
    np.save(os.path.join(OUT, "d_final_util.npy"), u); np.save(os.path.join(OUT, "d_final_A.npy"), m.A); np.save(os.path.join(OUT, "d_final_P.npy"), m.P)

    # test: top-32 over all episodes, no exclusion
    t3 = time.time()
    te_pos, te_dist = model.topk_retrieval(ete, keys_f32, rank, k=cfg["k"], loo_offset=None, block=500, log=log)
    t_te = time.time() - t3
    np.savez(os.path.join(OUT, "d_test_nb.npz"), pos=te_pos, dist=te_dist)
    rec("14.9", "test0 top-8 positions", te_pos[0, :8].tolist(), [53843, 27059, 47003, 38620, 14563, 16186, 44566, 15260])
    rec("14.9", "test0 top-8 distances", te_dist[0, :8].tolist(), [575, 638, 670, 673, 679, 681, 692, 694])
    rec("14.9", "test0 32nd neighbour distance", int(te_dist[0, 31]), 749)
    del keys_f32
    dP = m.hamming(ete)
    simP = 1.0 - ((2.0 * dP.astype(np.float64)) / 10000.0)
    te_sims = 1.0 - ((2.0 * te_dist.astype(np.float64)) / 10000.0)
    val_list = episodes["val"].tolist()
    pred = np.empty(ete.shape[0], dtype=np.int64)
    for q in range(ete.shape[0]):
        sc = model.fused_scores(simP[q].tolist(), te_pos[q].tolist(), te_sims[q].tolist(), u, val_list, 10,
                                cfg["theta0"], cfg["lambda_e"], cfg["lambda_p"], cfg["util_clip"])
        pred[q] = model.argmax_first(sc)
    if m.halvings:
        raise RuntimeError("halving in (d)")
    res = hdc.evaluate(yte, pred, labels)
    res.update(n_train=int(N), n_classes=10, chance_level=0.1, halvings=m.halvings,
               t2_error_per_epoch=errors, t2_misses_per_epoch=misses, t2_s=round(t_t2, 1),
               loo_retrieval_s=round(t_loo, 1), test_retrieval_s=round(t_te, 1),
               runtime_s_excluding_encoding=round(time.time() - t0, 1), config=cfg)
    np.save(os.path.join(OUT, "d_predictions.npy"), pred.astype(np.int64))
    save_result("d", res)


for st in stages:
    log(f"==== stage {st} (small={SMALL})")
    ts = time.time()
    {"a": stage_a, "mnist_enc": stage_mnist_enc, "b": stage_b, "c": stage_c, "d": stage_d}[st]()
    log(f"==== stage {st} done in {time.time()-ts:.1f}s")
