"""Prototype classifier (T1/T2), episodic memory, retrieval and fusion (§8-§11)."""
import hashlib
import numpy as np

import hdc
from hdc import D, NB

HALVE_THRESHOLD = 16384


def pad64(packed):
    """(N,1250) uint8 -> (N,157) uint64 (zero padded), for popcount Hamming."""
    packed = np.atleast_2d(packed)
    out = np.zeros((packed.shape[0], 1256), dtype=np.uint8)
    out[:, :NB] = packed
    return out.view(np.uint64)


def signed_i32(packed):
    return 2 * np.unpackbits(packed).astype(np.int32) - 1


class Prototypes:
    def __init__(self, seed=hdc.SEED):
        self.seed = seed
        self.labels = []
        self.index = {}
        self.A = np.zeros((0, D), dtype=np.int16)
        self.P = np.zeros((0, NB), dtype=np.uint8)
        self.halvings = 0

    # §8.2
    def register(self, labels):
        for l in sorted(set(labels)):
            if l not in self.index:
                self.index[l] = len(self.labels)
                self.labels.append(l)
                self.A = np.concatenate([self.A, np.zeros((1, D), np.int16)])
                self.P = np.concatenate([self.P, np.zeros((1, NB), np.uint8)])

    @staticmethod
    def _halve(v):
        v = np.asarray(v, dtype=np.int32)
        mag = np.maximum(np.abs(v) // 2, 1)
        return np.where(v == 0, 0, np.sign(v) * mag).astype(np.int32)

    # §8.4
    def halved_if_needed(self, updated):
        while True:
            upd_idx = set(updated)
            peak = 0
            for c in range(len(self.labels)):
                row = updated[c] if c in upd_idx else self.A[c].astype(np.int32)
                peak = max(peak, int(np.abs(row).max()))
            if peak <= HALVE_THRESHOLD:
                break
            self.halvings += 1
            self.A = self._halve(self.A).astype(np.int16)
            updated = {c: self._halve(r) for c, r in updated.items()}
        return {c: r.astype(np.int16) for c, r in updated.items()}

    def _commit(self, updated):
        updated = self.halved_if_needed(updated)
        for c, row in updated.items():
            self.P[c] = hdc.binarise_proto(row, self.labels[c], self.seed)
        for c, row in updated.items():
            self.A[c] = row

    # §8.3
    def learn(self, enc, y_labels):
        """enc: (M,1250) packed; y_labels: list of label strings."""
        self.register(y_labels)
        yidx = np.array([self.index[l] for l in y_labels], dtype=np.int64)
        present = sorted(set(y_labels))
        updated = {}
        for l in present:
            c = self.index[l]
            rows = np.flatnonzero(yidx == c)
            cnt = np.zeros(D, dtype=np.int64)
            for s in range(0, rows.shape[0], 4096):
                cnt += np.unpackbits(enc[rows[s : s + 4096]], axis=1).sum(axis=0, dtype=np.int64)
            summ = 2 * cnt - rows.shape[0]
            updated[c] = (self.A[c].astype(np.int64) + summ).astype(np.int32)
        self._commit(updated)

    # T2 miss update (§10.3 step 5)
    def miss_update(self, t, pred, s, t2_local=False):
        updated = {t: self.A[t].astype(np.int32) + s}
        if not t2_local:
            updated[pred] = self.A[pred].astype(np.int32) - s
        self._commit(updated)

    def hamming(self, packed_queries, chunk=2048):
        return hdc.hamming_matrix(packed_queries, self.P, chunk)

    def predict(self, packed_queries):
        d = self.hamming(packed_queries)
        sim = 1.0 - ((2.0 * d.astype(np.float64)) / 10000.0)
        return np.argmax(sim, axis=1).astype(np.int64), d


# ----------------------------------------------------------------------------- episodes (§11)
def episode_ids(keys, labels_of_rows):
    ids = np.empty(keys.shape[0], dtype=np.uint64)
    for j in range(keys.shape[0]):
        L = labels_of_rows[j].encode("utf-8")
        msg = len(L).to_bytes(4, "big") + L + keys[j].tobytes()
        ids[j] = int.from_bytes(hashlib.shake_256(msg).digest(8), "big")
    return ids


def ranks_from_ids(ids):
    # sort ascending by (id as unsigned 64-bit, position j); lexsort uses last key as primary
    order = np.lexsort((np.arange(ids.shape[0]), ids))
    rank = np.empty(ids.shape[0], dtype=np.int64)
    rank[order] = np.arange(ids.shape[0])
    return rank


def topk_retrieval(query_packed, keys_signed_f32, rank, k=32, loo_offset=None, block=1000, log=None):
    """Exact top-k by (hamming, rank). keys_signed_f32: (N,D) float32 +-1.
    loo_offset: if not None, query i (global index loo_offset+i) excludes episode loo_offset+i.
    Returns positions (Q,k) int64 and distances (Q,k) int64, in ascending sort-key order."""
    N = keys_signed_f32.shape[0]
    Qn = query_packed.shape[0]
    kk = min(k, N - 1) if loo_offset is not None else min(k, N)
    pos_out = np.empty((Qn, kk), dtype=np.int64)
    dist_out = np.empty((Qn, kk), dtype=np.int64)
    rank32 = rank.astype(np.int64)
    import time
    t0 = time.time()
    for s in range(0, Qn, block):
        e = min(Qn, s + block)
        Qs = hdc.to_signed_f32(query_packed[s:e])
        dot = Qs @ keys_signed_f32.T  # exact integers in float32
        dist = (D - dot.astype(np.int64)) // 2
        key = (dist << 20) | rank32[None, :]
        if loo_offset is not None:
            rows = np.arange(e - s)
            key[rows, loo_offset + s + rows] = np.iinfo(np.int64).max
        part = np.argpartition(key, kk - 1, axis=1)[:, :kk]
        pk = np.take_along_axis(key, part, axis=1)
        o = np.argsort(pk, axis=1, kind="stable")
        sel = np.take_along_axis(part, o, axis=1)
        pos_out[s:e] = sel
        dist_out[s:e] = np.take_along_axis(dist, sel, axis=1)
        if log is not None and (s // block) % 5 == 0:
            log(f"  retrieval {e}/{Qn} {time.time()-t0:.1f}s")
    return pos_out, dist_out


def fused_scores(sim_c, nb_pos, nb_sims, util, val, K, theta0, lam_e, lam_p, util_clip):
    """§11.4 in pure Python binary64, exact operation order."""
    E = [0.0] * K
    uc = float(util_clip)
    for m in range(len(nb_pos)):
        j = nb_pos[m]
        w = (1.0 + (float(util[j]) / uc)) * max(0.0, nb_sims[m] - theta0)
        c = val[j]
        E[c] = E[c] + w
    return [(lam_p * sim_c[c]) + (lam_e * E[c]) for c in range(K)]


def argmax_first(scores):
    best = 0
    bv = scores[0]
    for c in range(1, len(scores)):
        if scores[c] > bv:
            bv = scores[c]; best = c
    return best


def run_t2(model, train_enc, y_train, epochs, cfg, episodes=None, log=print, checkpoint=None):
    """§10. cfg: dict(k, theta0, lambda_e, lambda_p, util_clip, t2_local).
    episodes: dict(val, util, nb_pos, nb_dist) or None.
    checkpoint(step_count, epoch) callback for conformance checks."""
    R = np.random.default_rng(hdc.SEED)
    N = train_enc.shape[0]
    K = len(model.labels)
    use_episodes = cfg["lambda_e"] > 0 and episodes is not None and len(episodes["val"]) > 0
    keys64 = pad64(train_enc)
    lam_p = cfg["lambda_p"]; lam_e = cfg["lambda_e"]; theta0 = cfg["theta0"]; uclip = cfg["util_clip"]
    if use_episodes:
        util = episodes["util"]
        val_list = episodes["val"].tolist()
        nb_pos_all = episodes["nb_pos"]
        nb_sims_all = 1.0 - ((2.0 * episodes["nb_dist"].astype(np.float64)) / 10000.0)
        val_arr = episodes["val"]
    errors = []
    misses_list = []
    ytr = y_train.tolist()
    for ep in range(epochs):
        order = R.permutation(N)
        misses = 0
        P64 = pad64(model.P)
        for step, i in enumerate(order.tolist()):
            e64 = keys64[i]
            d = np.bitwise_count(P64 ^ e64[None, :]).sum(axis=1, dtype=np.int64)
            sim = (1.0 - ((2.0 * d.astype(np.float64)) / 10000.0)).tolist()
            t = ytr[i]
            if use_episodes:
                nbp = nb_pos_all[i]
                score = fused_scores(sim, nbp.tolist(), nb_sims_all[i].tolist(), util, val_list, K,
                                     theta0, lam_e, lam_p, uclip)
            else:
                score = [lam_p * s for s in sim]
            pred = argmax_first(score)
            if use_episodes:
                delta = np.where(val_arr[nbp] == t, 1, -1)
                util[nbp] = np.clip(util[nbp].astype(np.int32) + delta, -uclip, uclip).astype(util.dtype)
            if pred != t:
                misses += 1
                s = signed_i32(train_enc[i])
                model.miss_update(t, pred, s, cfg["t2_local"])
                P64[t] = pad64(model.P[t])[0]
                P64[pred] = pad64(model.P[pred])[0]
            if checkpoint is not None:
                checkpoint(ep, step + 1, misses, dict(i=i, t=t, pred=pred, sim=sim, score=score))
        errors.append(round(misses / N, 6))
        misses_list.append(misses)
        log(f"  T2 epoch {ep+1}: misses {misses} error {misses/N:.6f}")
    return errors, misses_list
