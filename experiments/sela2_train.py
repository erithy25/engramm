"""Sela-2 training on one GPU (docs/SELA2_ANLEITUNG.md): pretraining, chat fine-tuning, evaluation, export.

    python -m experiments.sela2_train pretrain --data D --deadline T      # WSD pretraining, chat data in the decay
    python -m experiments.sela2_train sft --data D --deadline T           # assistant-only fine-tuning of the base
    python -m experiments.sela2_train evaluate --data D --model M --tag T # bits per byte, yardstick, GPU samples
    python -m experiments.sela2_train export --model M --out X.npz       # the desktop app's weights (int8)
    python -m experiments.sela2_train smoke                               # every path on the CPU, tiny model

Pretraining (docs/PLAN_V5_FROM_SCRATCH.md §12): the Sela-2 model (experiments/sela2_model.py) with Muon + AdamW
(experiments/sela2_optim.py, nanochat's rates and schedules: 40 warm-up steps, constant, linear decay over the last
65 % of the tokens to 5 %), 524,288 tokens per step, context 2,048, attention within each document (FlexAttention
block mask when it matches the dense attention and is faster). The data are the token streams of
experiments/sela2_data.py, mixed by source; at 70 % of the tokens the mix switches to the decay mix, which adds the
chat, grounded-QA and identity conversations (full loss). The mix respects what each source holds (a source that
would run out is down-weighted, never silently repeated; a repeat would be logged).

Safeguards as the Sela-1 trainer (experiments/h100_train.py): the token target is fitted to ``--deadline`` from the
throughput of steps 40-100 and re-fitted at checkpoints while the rate is constant; a full state (model, optimiser,
data positions) is written every ``--ckpt-minutes`` in a background thread and a restart resumes from it; the last
state before the decay is kept (continuable later); CUDA out-of-memory switches to the chunked loss, then halves the
micro-batch; three non-finite losses in a row end with exit code 3 (the driver continues from the last state at
half the learning rate); a loss above ``--loss-bound`` at step ``--loss-check`` ends with exit code 4 (the driver
restarts with the AdamW recipe).

Fine-tuning: one pass (or what the deadline allows) over the fine-tuning conversations, best-fit packed into 2,048-
token rows without splitting a conversation, loss only on the assistant's tokens and its <|im_end|>; optimiser state
from the end of pretraining, learning rate 0.8 × the pretraining peak, linear decay over the second half to 0, no
weight decay (nanochat chat_sft.py).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import threading
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from experiments import sela2_optim as O
from experiments.sela2_model import (EOS, Sela2, Sela2Config, chunked_loss, dense_attend, doc_mask, export_npz,
                                     fused_loss)

REPO = Path(__file__).resolve().parents[1]
DIVERGED, RECIPE_FAILED = 3, 4
OOM = getattr(torch, "OutOfMemoryError", None) or torch.cuda.OutOfMemoryError
TOKENIZER_FILE = REPO / "data" / "lm2_tokenizer.json"

SIZES = {
    "sela2": dict(d=1024, layers=24, heads=8, ctx=2048, vocab=49_152, ve_tables=2),
    "small": dict(d=384, layers=6, heads=6, ctx=512, vocab=49_152, ve_tables=1),
    "tiny": dict(d=64, layers=4, heads=2, ctx=128, vocab=512, ve_tables=1),
    "probe": dict(d=128, layers=2, heads=2, ctx=256, vocab=49_152, ve_tables=1),   # the pod's 3-minute dry run
}
STABLE_MIX = {"fwe": 0.30, "fwehq": 0.12, "dclm": 0.24, "c4": 0.08, "cosmo": 0.07, "wiki_en": 0.06, "pg19": 0.04,
              "fw2_de": 0.07, "wiki_de": 0.02}
DECAY_MIX = {"fwe": 0.10, "fwehq": 0.20, "dclm": 0.14, "c4": 0.05, "cosmo": 0.05, "wiki_en": 0.07, "pg19": 0.03,
             "fw2_de": 0.05, "wiki_de": 0.02, "chat_en_decay": 0.15, "chat_de_decay": 0.03, "grounded_decay": 0.10,
             "identity_decay": 0.01}
SFT_MIX = {"chat_en_sft": 1, "chat_de_sft": 1, "grounded_sft": 1, "identity_sft": 3}     # passes over each stream
CHAT_VAL = ("chat_en_val", "chat_de_val", "grounded_val")
PROMPTS_CHAT = [("en", "Hi! Who are you?"), ("en", "Explain in two sentences why the sky is blue."),
                ("en", "Write a short, friendly email inviting my team to a lunch on Friday."),
                ("en", "Give me three tips for sleeping better."),
                ("de", "Hallo! Wer bist du?"), ("de", "Erkläre kurz, was ein Sprachmodell ist."),
                ("de", "Schreib mir eine kurze Einkaufsliste für ein Frühstück.")]
PROMPTS_GROUNDED = [
    ("en", [("Mount Everest", "Mount Everest is Earth's highest mountain above sea level, located in the Himalayas. "
             "Its elevation of 8,848.86 m was most recently established in 2020 by Chinese and Nepali authorities."),
            ("K2", "K2, at 8,611 m above sea level, is the second-highest mountain on Earth.")],
     "How high is Mount Everest?"),
    ("en", [("Marie Curie", "Marie Curie was a Polish and naturalised-French physicist and chemist who conducted "
             "pioneering research on radioactivity. She was the first woman to win a Nobel Prize.")],
     "What is the capital of Australia?"),
    ("de", [("Berlin", "Berlin ist die Hauptstadt und mit rund 3,7 Millionen Einwohnern die bevölkerungsreichste "
             "Stadt Deutschlands.")], "Wie viele Einwohner hat Berlin?")]
PROMPTS_TEXT = ["The history of the city", "Albert Einstein was", "How to make a cup of tea: First,",
                "Die Geschichte der Stadt"]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def scan(data: Path) -> dict[str, dict]:
    """Every stream in ``data``: name → manifest record (+ 'path')."""
    out = {}
    for j in sorted(Path(data).glob("*.json")):
        try:
            rec = json.loads(j.read_text())
        except ValueError:
            continue
        name = rec.get("name") if isinstance(rec, dict) else None
        if name and (Path(data) / f"{name}.u16").exists():
            rec["path"] = Path(data) / f"{name}.u16"
            out[name] = rec
    return out


def check_tokenizer(streams: dict[str, dict], expect: str | None) -> str:
    shas = {r.get("tokenizer_sha256") for r in streams.values()}
    if len(shas) != 1:
        raise SystemExit(f"the data were tokenised with different tokenizers: {shas}")
    sha = shas.pop()
    if expect and sha != expect:
        raise SystemExit(f"data tokenizer {sha} differs from {expect} ({TOKENIZER_FILE.name})")
    return sha


def group_of(name: str) -> str:
    """Source group of a stream file name: fwe_2 → fwe, dclm_0_1 → dclm, chat_en_decay → chat_en_decay."""
    return re.sub(r"(_\d+)+$", "", name)


def plan_weights(avail: dict[str, int], total: int, split: float, stable: dict, decay: dict) -> tuple[dict, dict]:
    """Per-phase source weights near ``stable`` / ``decay`` that need at most what each source holds."""
    S = {g: float(w) for g, w in stable.items() if avail.get(g, 0) > 0}
    D = {g: float(w) for g, w in decay.items() if avail.get(g, 0) > 0}
    if not S or not D:
        raise SystemExit(f"no data for the mix (have {sorted(avail)})")

    def norm(m):
        s = sum(m.values())
        return {k: v / s for k, v in m.items()}
    for _ in range(50):
        ns, nd = norm(S), norm(D)
        need = {g: ns.get(g, 0.0) * total * split + nd.get(g, 0.0) * total * (1 - split) for g in set(S) | set(D)}
        over = {g: need[g] / avail[g] for g in need if need[g] > 0.98 * avail[g]}
        if not over:
            break
        for g, r in over.items():
            f = 0.97 / r
            if g in S:
                S[g] *= f
            if g in D:
                D[g] *= f
    return norm(S), norm(D)


class Source:
    """Token files of one source group read in order; rows are taken contiguously (no document repeated unless the
    source runs out, which is counted in ``epoch``)."""

    def __init__(self, paths: list[Path]):
        self.paths = list(paths)
        self.mm = [np.memmap(p, dtype=np.uint16, mode="r") for p in self.paths]
        self.total = int(sum(len(m) for m in self.mm))
        self.fi = self.pos = self.epoch = 0

    def take(self, n: int) -> np.ndarray:
        out = np.empty(n, dtype=np.uint16)
        k = 0
        while k < n:
            m = self.mm[self.fi]
            c = min(n - k, len(m) - self.pos)
            out[k:k + c] = m[self.pos:self.pos + c]
            k += c
            self.pos += c
            if self.pos >= len(m):
                self.fi, self.pos = self.fi + 1, 0
                if self.fi >= len(self.mm):
                    self.fi, self.epoch = 0, self.epoch + 1
        return out

    def used(self) -> int:
        return self.epoch * self.total + sum(len(m) for m in self.mm[:self.fi]) + self.pos

    def state(self) -> dict:
        return {"fi": self.fi, "pos": self.pos, "epoch": self.epoch}

    def load(self, st: dict) -> None:
        self.fi, self.pos, self.epoch = int(st["fi"]), int(st["pos"]), int(st["epoch"])


class PretrainMix:
    def __init__(self, data: Path, seed: int, stable: dict = STABLE_MIX, decay: dict = DECAY_MIX):
        streams = scan(data)
        groups: dict[str, list[Path]] = {}
        for name, rec in streams.items():
            if name.startswith(("val_", "lm_")) or name.endswith(("_sft", "_val")):
                continue
            groups.setdefault(group_of(name), []).append(rec["path"])
        self.sources = {g: Source(sorted(p)) for g, p in groups.items() if g in stable or g in decay}
        self.stable, self.decay = stable, decay
        self.rng = np.random.default_rng(seed)
        self.weights: tuple[dict, dict] | None = None
        self._planned_for = None

    def avail(self) -> dict[str, int]:
        return {g: s.total for g, s in self.sources.items()}

    def plan(self, total: int, split: float) -> None:
        if self._planned_for != (total, split):
            self.weights = plan_weights(self.avail(), total, split, self.stable, self.decay)
            self._planned_for = (total, split)

    def batch(self, B: int, T: int, decay_phase: bool) -> torch.Tensor:
        w = self.weights[1] if decay_phase else self.weights[0]
        names = sorted(w)
        p = np.asarray([w[n] for n in names])
        pick = self.rng.choice(len(names), size=B, p=p / p.sum())
        rows = np.stack([self.sources[names[i]].take(T + 1) for i in pick])
        return torch.from_numpy(rows.astype(np.int64))

    def state(self) -> dict:
        return {"rng": self.rng.bit_generator.state, "sources": {g: s.state() for g, s in self.sources.items()}}

    def load(self, st: dict) -> None:
        self.rng.bit_generator.state = st["rng"]
        for g, s in st["sources"].items():
            if g in self.sources:
                self.sources[g].load(s)

    def report(self) -> dict:
        return {g: {"tokens_available": s.total, "tokens_used": s.used(), "repeats": s.epoch}
                for g, s in self.sources.items()}


def conversations(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(tokens, mask, starts) of a chat stream; conversation i spans tokens[starts[i]:starts[i+1]] (with its
    opening <|eos|>; the stream ends with one more <|eos|>)."""
    toks = np.fromfile(path, dtype=np.uint16)
    mpath = path.with_suffix(".mask")
    mask = np.unpackbits(np.fromfile(mpath, dtype=np.uint8))[:len(toks)] if mpath.exists() else np.zeros(len(toks), np.uint8)
    starts = np.flatnonzero(toks == EOS)
    return toks, mask, starts


class SFTData:
    """Fine-tuning rows: conversations best-fit packed into rows of T + 1 tokens (padding: <|eos|>, no loss)."""

    def __init__(self, data: Path, T: int, seed: int, mix: dict = SFT_MIX, buffer: int = 512):
        streams = scan(data)
        self.parts = []
        order = []
        for name, reps in mix.items():
            if name not in streams:
                continue
            toks, mask, starts = conversations(streams[name]["path"])
            k = len(self.parts)
            self.parts.append((toks, mask))
            convs = [(k, int(a), int(b)) for a, b in zip(starts[:-1], starts[1:]) if 2 < b - a <= T + 1]
            order += convs * int(reps)
        if not order:
            raise SystemExit("no fine-tuning conversations found")
        rng = np.random.default_rng(seed)
        self.order = [order[i] for i in rng.permutation(len(order))]
        self.tokens_total = int(sum(b - a for _, a, b in self.order))
        self.pos = 0
        self.buf: list[tuple[int, int, int]] = []
        self.T, self.buffer = T, buffer

    def exhausted(self) -> bool:
        return self.pos >= len(self.order) and not self.buf

    def _fill(self) -> None:
        while len(self.buf) < self.buffer and self.pos < len(self.order):
            self.buf.append(self.order[self.pos])
            self.pos += 1

    def row(self) -> tuple[np.ndarray, np.ndarray]:
        cap = self.T + 1
        ids = np.zeros(cap, dtype=np.int64)
        msk = np.zeros(cap, dtype=np.uint8)
        k = 0
        while True:
            self._fill()
            if not self.buf:
                break
            best, best_len = -1, -1
            for i, (_, a, b) in enumerate(self.buf):
                n = b - a
                if n <= cap - k and n > best_len:
                    best, best_len = i, n
            if best < 0:
                break
            p, a, b = self.buf.pop(best)
            toks, mask = self.parts[p]
            ids[k:k + b - a] = toks[a:b]
            msk[k:k + b - a] = mask[a:b]
            k += b - a
        return ids, msk

    def batch(self, B: int) -> tuple[torch.Tensor, torch.Tensor, int]:
        rows = [self.row() for _ in range(B)]
        ids = torch.from_numpy(np.stack([r[0] for r in rows]))
        msk = torch.from_numpy(np.stack([r[1] for r in rows]).astype(np.int64))
        tgt = ids[:, 1:].clone()
        tgt[msk[:, 1:] == 0] = -1
        return ids[:, :-1], tgt, int((msk[:, 1:] > 0).sum())


# ---------------------------------------------------------------------------
# model, attention, steps
# ---------------------------------------------------------------------------

def pick_device(cpu: bool) -> torch.device:
    if not cpu:
        if not torch.cuda.is_available():
            raise SystemExit("no CUDA GPU visible (torch.cuda.is_available() is False)")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        return torch.device("cuda")
    return torch.device("cpu")


def build_model(args) -> tuple[Sela2, dict]:
    cfg = dict(SIZES[args.size])
    if getattr(args, "vocab", 0):
        cfg["vocab"] = args.vocab
    model = Sela2(Sela2Config(**cfg))
    return model, cfg


class Stepper:
    """Forward + loss for one micro-batch, with the attention path (flex → dense) and loss (fused → chunked)
    fallbacks of the Sela-1 trainer."""

    def __init__(self, model: Sela2, args, device, out: Path, meta: dict):
        self.model, self.device, self.out, self.meta = model, device, out, meta
        self.cuda = device.type == "cuda"
        self.compiled = bool(args.compile and (self.cuda or os.environ.get("SELA2_COMPILE_CPU") == "1"))
        self.cap, self.bf16 = model.cfg.softcap, bool(args.bf16 and self.cuda)
        self.fused = args.loss == "fused"

        def dense(idx):
            return model.hidden(idx, dense_attend(doc_mask(idx)))
        self.f_dense = torch.compile(dense) if self.compiled else dense
        self.f_loss = torch.compile(fused_loss) if (self.compiled and self.fused) else fused_loss
        self.attn, self.f_flex = "dense", None
        if self.cuda and self.compiled and getattr(args, "flex", 1) and not (meta.get("attention") or {}).get("flex_disabled"):
            from torch.nn.attention.flex_attention import flex_attention

            def flex(idx, bm):
                return model.hidden(idx, lambda q, k, v: flex_attention(q, k, v, block_mask=bm))
            self.f_flex = torch.compile(flex, dynamic=False)

    def choose(self, probe: torch.Tensor, args) -> None:
        if self.f_flex is None:
            return
        from experiments.h100_train import choose_attention
        inp, tgt = probe[:, :-1].to(self.device), probe[:, 1:].to(self.device)
        ns = argparse.Namespace(d=self.model.cfg.d, heads=self.model.cfg.heads, flex=1, compile=True)

        def run_step(kind):
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=self.bf16):
                h = self._hidden(inp, kind)
            self._loss(h, tgt).backward()
        if choose_attention(self.model, ns, self.device, inp, run_step, self.out)["decision"] == "flex":
            self.attn = "flex"
        else:
            self.f_flex = None

    def _hidden(self, inp, kind=None):
        kind = kind or self.attn
        if kind == "flex":
            from experiments.h100_train import flex_block_mask
            return self.f_flex(inp, flex_block_mask(inp, True))
        return self.f_dense(inp)

    def _loss(self, h, tgt):
        W = self.model.head.weight
        if self.fused:
            return self.f_loss(h, W, tgt, self.cap, self.bf16)
        return chunked_loss(h, W, tgt, self.cap, self.bf16)

    def loss(self, inp, tgt):
        with torch.autocast(self.device.type, dtype=torch.bfloat16, enabled=self.bf16):
            h = self._hidden(inp)
        return self._loss(h, tgt)

    def fallback(self, e: Exception) -> str:
        """After a failed micro-step: what to change ('' = give up)."""
        if isinstance(e, OOM):
            if self.fused:
                self.fused = False
                return "out of memory: chunked loss"
            return "out of memory"
        if self.attn == "flex":
            from experiments.h100_train import disable_flex
            self.attn, self.f_flex = "dense", None
            disable_flex(self.meta, self.out, f"{type(e).__name__}: {e}")
            return "flex failed: dense attention"
        if self.compiled or self.fused:
            self.compiled, self.fused = False, False
            m = self.model
            self.f_dense = lambda idx: m.hidden(idx, dense_attend(doc_mask(idx)))
            return f"compiled/fused step failed ({type(e).__name__}: {str(e)[:200]}): eager, chunked loss"
        return ""


def to_cpu(obj):
    if torch.is_tensor(obj):
        return obj.detach().to("cpu", copy=True)
    if isinstance(obj, dict):
        return {k: to_cpu(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(to_cpu(v) for v in obj)
    return obj


def atomic_save(obj, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


class AsyncSaver:
    """torch.save in a background thread (the GPU copy to CPU memory happens first, on the caller's thread)."""

    def __init__(self):
        self.t: threading.Thread | None = None
        self.error: BaseException | None = None

    def save(self, obj, path: Path) -> None:
        self.wait()
        cpu = to_cpu(obj)

        def run():
            try:
                atomic_save(cpu, path)
            except BaseException as e:          # reported by wait(); a full disk must not kill training silently
                self.error = e
        self.t = threading.Thread(target=run, daemon=True)
        self.t.start()

    def wait(self) -> None:
        if self.t is not None:
            self.t.join()
            self.t = None
        if self.error is not None:
            e, self.error = self.error, None
            log(f"WARNING: saving a state failed: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------

@torch.no_grad()
def logprobs_packed(model: Sela2, seqs: list[np.ndarray], device, rows: int = 8) -> list[np.ndarray]:
    """log p of tokens 1.. of every sequence (each starts with <|eos|>, length ≤ ctx + 1), many sequences packed per
    row with the attention kept inside each one."""
    T = model.cfg.ctx
    out: list[np.ndarray | None] = [None] * len(seqs)
    order = sorted(range(len(seqs)), key=lambda i: -len(seqs[i]))
    packs, cur, used = [], [], 0
    for i in order:
        n = len(seqs[i])
        if used + n > T + 1 and cur:
            packs.append(cur)
            cur, used = [], 0
        cur.append(i)
        used += n
    if cur:
        packs.append(cur)
    for b in range(0, len(packs), rows):
        batch = packs[b:b + rows]
        L = max(sum(len(seqs[i]) for i in p) for p in batch)
        ids = np.zeros((len(batch), L), dtype=np.int64)
        spans = []
        for r, p in enumerate(batch):
            k = 0
            for i in p:
                ids[r, k:k + len(seqs[i])] = seqs[i]
                spans.append((r, k, len(seqs[i]), i))
                k += len(seqs[i])
        x = torch.from_numpy(ids).to(device)
        logits = model(x[:, :-1]) if L > 1 else None
        lp = F.log_softmax(logits.float(), dim=-1)
        tgt = x[:, 1:]
        sel = lp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1).double().cpu().numpy()
        for r, k, n, i in spans:
            out[i] = sel[r, k:k + n - 1]
    return out


@torch.no_grad()
def eval_stream(model: Sela2, rec: dict, device, max_docs: int = 0) -> dict:
    """Bits per byte of a validation stream (NAME.starts.npy / NAME.bytes.npy beside it): each document's tokens and
    its end marker (the next <|eos|>), bytes + 1. Documents longer than the context: windows of ctx, stride ctx/2."""
    path = Path(rec["path"])
    toks = np.fromfile(path, dtype=np.uint16)
    starts = np.load(str(path).replace(".u16", ".starts.npy")).astype(np.int64)
    nbytes = np.load(str(path).replace(".u16", ".bytes.npy")).astype(np.float64) + 1.0
    ends = np.append(starts[1:] - 1, len(toks) - 1)                    # index of the end marker
    if max_docs:
        starts, ends, nbytes = starts[:max_docs], ends[:max_docs], nbytes[:max_docs]
    T = model.cfg.ctx
    was = model.training
    model.eval()
    bits = np.zeros(len(starts))
    short = [d for d in range(len(starts)) if ends[d] - starts[d] + 2 <= T + 1]
    seqs = [toks[starts[d] - 1:ends[d] + 1].astype(np.int64) for d in short]
    for d, lp in zip(short, logprobs_packed(model, seqs, device)):
        bits[d] = -lp.sum() / math.log(2)
    for d in range(len(starts)):
        if ends[d] - starts[d] + 2 <= T + 1:
            continue
        seq = torch.from_numpy(toks[starts[d] - 1:ends[d] + 1].astype(np.int64)).to(device)
        n, done, a = len(seq), 0, 0
        while done < n - 1:
            win = seq[a:a + T + 1][None]
            W = win.shape[1] - 1
            lp = F.log_softmax(model(win[:, :-1])[0].float(), dim=-1)
            sel = lp[torch.arange(W, device=device), win[0, 1:]]
            bits[d] -= float(sel[done - a:].double().sum()) / math.log(2)
            done = a + W
            a += T // 2
    model.train(was)
    return {"docs": int(len(starts)), "bpb": float(bits.sum() / nbytes.sum()), "per_doc_bits": bits}


@torch.no_grad()
def chat_val_loss(model: Sela2, rec: dict, device, max_convs: int = 500) -> dict:
    """Mean loss (nats) on the assistant's tokens of held-out conversations."""
    toks, mask, starts = conversations(Path(rec["path"]))
    seqs, masks = [], []
    for a, b in zip(starts[:-1], starts[1:]):
        if b - a <= model.cfg.ctx + 1:
            seqs.append(toks[a:b].astype(np.int64))
            masks.append(mask[a:b])
        if len(seqs) >= max_convs:
            break
    was = model.training
    model.eval()
    tot, n = 0.0, 0
    for s, m, lp in zip(seqs, masks, logprobs_packed(model, seqs, device)):
        sel = m[1:] > 0
        tot -= float(lp[sel].sum())
        n += int(sel.sum())
    model.train(was)
    return {"convs": len(seqs), "assistant_tokens": n, "loss": tot / max(1, n)}


def val_streams(data: Path) -> dict[str, dict]:
    return {n: r for n, r in scan(data).items() if n.startswith(("val_", "lm_"))
            and Path(str(r["path"]).replace(".u16", ".starts.npy")).exists()}


@torch.no_grad()
def generate(model: Sela2, ids: list[int], n: int, device, temperature: float = 0.7, top_p: float = 0.9,
             stop: tuple[int, ...] = (EOS,), seed: int = 0) -> list[int]:
    """Sampling on the GPU (full forward per token; short texts only)."""
    g = torch.Generator(device="cpu").manual_seed(seed)
    out = list(ids)
    was = model.training
    model.eval()
    for _ in range(n):
        x = torch.tensor([out[-model.cfg.ctx:]], device=device)
        z = model(x)[0, -1].float().cpu() / max(temperature, 1e-6)
        p = torch.softmax(z, -1)
        sp, si = torch.sort(p, descending=True)
        keep = (torch.cumsum(sp, 0) - sp) < top_p
        sp = sp * keep
        nxt = int(si[torch.multinomial(sp / sp.sum(), 1, generator=g)])
        if nxt in stop:
            break
        out.append(nxt)
    model.train(was)
    return out[len(ids):]


def samples(model: Sela2, tok, device, chat: bool) -> dict:
    from engramm.lm.chat_format import IM_END, SYSTEM, SYSTEM_GROUNDED, Message, render, sources_block
    rows = []
    if chat:
        for lang, q in PROMPTS_CHAT:
            ids, _ = render(tok, [Message("system", SYSTEM[lang]), Message("user", q)], add_generation_prompt=True)
            rows.append({"kind": "chat", "lang": lang, "prompt": q,
                         "reply": tok.decode(generate(model, ids, 160, device, stop=(EOS, IM_END)))})
        for lang, srcs, q in PROMPTS_GROUNDED:
            ids, _ = render(tok, [Message("system", SYSTEM_GROUNDED[lang]), Message("sources", sources_block(srcs)),
                                  Message("user", q)], add_generation_prompt=True)
            rows.append({"kind": "grounded", "lang": lang, "prompt": q, "sources": srcs,
                         "reply": tok.decode(generate(model, ids, 80, device, temperature=0.3, stop=(EOS, IM_END)))})
    for p in PROMPTS_TEXT:
        ids = [EOS] + [int(t) for t in tok.encode(p)]
        rows.append({"kind": "text", "prompt": p, "reply": tok.decode(generate(model, ids, 60, device, temperature=0.9))})
    return {"settings": {"top_p": 0.9, "temperature": "0.7 chat / 0.3 grounded / 0.9 text", "seed": 0}, "samples": rows}


# ---------------------------------------------------------------------------
# pretraining
# ---------------------------------------------------------------------------

def pretrain(args, device) -> dict:
    out, ckdir = Path(args.out), Path(args.ckpt_dir)
    out.mkdir(parents=True, exist_ok=True)
    ckdir.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(args.seed)
    model, cfg = build_model(args)
    model.to(device)
    streams = scan(Path(args.data))
    tok_sha = check_tokenizer(streams, args.tokenizer_sha or None)
    data = PretrainMix(Path(args.data), seed=args.seed)
    state_path, predecay = ckdir / "state_pre.pt", ckdir / "state_pre_predecay.pt"
    meta = {"tokens": 0, "step": 0, "train_seconds": 0.0, "total_tokens": int(args.total_tokens), "cfg": cfg,
            "recipe": args.recipe, "lr_scale": 1.0, "bad": 0, "next_eval": args.eval_every, "tokenizer_sha256": tok_sha,
            "args": {k: v for k, v in vars(args).items() if k != "func"}}
    opt = None
    if state_path.exists():
        st = torch.load(state_path, map_location="cpu", weights_only=False)
        if st["meta"]["cfg"] != cfg or st["meta"]["recipe"] != args.recipe:
            raise SystemExit(f"{state_path} belongs to another configuration or recipe; move it away to start fresh")
        model.load_state_dict(st["model"])
        meta = st["meta"]
        if args.lr_scale != meta["lr_scale"]:
            log(f"learning rate scale {meta['lr_scale']} -> {args.lr_scale} (continuing from the last state)")
            meta.setdefault("lr_changes", []).append({"tokens": meta["tokens"], "to": args.lr_scale})
            meta["lr_scale"] = args.lr_scale
        data.load(meta["data"])
        opt_state = st["opt"]
        log(f"resumed at {meta['tokens'] / 1e6:.0f} M tokens (step {meta['step']})")
    else:
        opt_state = None
    wd0 = O.muon_weight_decay(args.batch_tokens, meta["total_tokens"]) if args.recipe == "sela2" else 0.0
    meta.setdefault("wd0", wd0)
    opt = make_opt(model, args, meta["wd0"], device)
    if opt_state is not None:
        opt.load_state_dict(opt_state)
    st = opt_state = None
    T, micro = cfg["ctx"], args.micro_batch
    data.plan(meta["total_tokens"], args.decay_data_at)
    stepper = Stepper(model, args, device, out, meta)
    if meta["step"] == 0 or "attention_used" not in meta:
        stepper.choose(_peek(data, micro, T), args)
    saver = AsyncSaver()
    logf = open(out / "train_log.jsonl", "a")
    curve = out / "curve.jsonl"
    end_by = float(args.deadline or 0)
    cap = int(args.total_tokens)
    start_step = meta["step"]
    rate_from, rate_at = start_step + 40, start_step + 100
    t_rate, tok_rate, checked = time.time(), meta["tokens"], not end_by
    if end_by and time.time() >= end_by:
        if meta["tokens"] == 0:
            raise SystemExit("time budget used up before any training")
        log("time budget already used up: no further training")
        meta["total_tokens"] = meta["tokens"]
    t_ck = time.time()
    loss_ema = None
    def progress() -> float:
        """Token fraction; inside the decay with a deadline: the larger of the token progress and the elapsed share
        of the time to the deadline, so the learning rate always reaches its final value in time."""
        total = meta["total_tokens"]
        frac = meta["tokens"] / total
        d0 = 1 - args.warmdown
        if frac >= d0 and "decay_t0" not in meta:
            meta["decay_t0"], meta["decay_tok0"] = time.time(), meta["tokens"]
        if not end_by or "decay_t0" not in meta:
            return frac
        tok_p = (meta["tokens"] - meta["decay_tok0"]) / max(1, total - meta["decay_tok0"])
        time_p = (time.time() - meta["decay_t0"]) / max(1.0, end_by - meta["decay_t0"])
        return d0 + (1 - d0) * min(1.0, max(tok_p, time_p, 0.0))

    while meta["tokens"] < meta["total_tokens"]:
        total = meta["total_tokens"]
        data.plan(total, args.decay_data_at)
        frac = progress()
        if frac >= 1.0:
            log(f"learning-rate decay complete by the deadline at {meta['tokens'] / 1e9:.3f} B tokens")
            meta["total_tokens"] = meta["tokens"]
            meta["ended_by_deadline"] = True
            break
        if meta["tokens"] > 0 and frac >= 1 - args.warmdown and not predecay.exists():
            saver.wait()
            atomic_save(to_cpu({"model": model.state_dict(), "opt": opt.state_dict(),
                                "meta": {**meta, "data": data.state(), "predecay": True}}), predecay)
            log(f"pre-decay state saved at {meta['tokens'] / 1e9:.3f} B tokens")
        lr_f = O.set_schedule(opt, frac, meta["step"], meta["wd0"], warmdown=args.warmdown, lr_scale=meta["lr_scale"])
        decay_phase = frac >= args.decay_data_at
        t0 = time.time()
        n_micro = max(1, args.batch_tokens // (micro * T))
        while True:
            try:
                opt.zero_grad(set_to_none=True)
                acc = torch.zeros((), dtype=torch.float32, device=device)
                saved = data.state()
                for _ in range(n_micro):
                    b = data.batch(micro, T, decay_phase)
                    if device.type == "cuda":
                        b = b.pin_memory().to(device, non_blocking=True)
                    loss = stepper.loss(b[:, :-1], b[:, 1:]) / n_micro
                    loss.backward()
                    acc += loss.detach().float()
                loss_sum = float(acc)
                break
            except Exception as e:
                loss = b = None
                opt.zero_grad(set_to_none=True)
                data.load(saved)                        # the failed attempt's rows are trained again
                if device.type == "cuda":
                    torch.cuda.empty_cache()
                what = stepper.fallback(e)
                if what == "out of memory":
                    if micro <= 2:
                        raise
                    micro //= 2
                    n_micro = max(1, args.batch_tokens // (micro * T))
                    what = f"out of memory: micro-batch {micro}"
                if not what or (meta["step"] > start_step + 3 and not isinstance(e, OOM) and "flex" not in what):
                    raise
                log(f"step failed – {what}")
                t_rate, tok_rate = time.time(), meta["tokens"]
        gn = float(torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip if args.clip > 0 else float("inf")))
        if not (math.isfinite(loss_sum) and math.isfinite(gn)):
            meta["bad"] += 1
            opt.zero_grad(set_to_none=True)
            log(f"non-finite loss/gradient at step {meta['step']} ({meta['bad']} in a row)")
            if meta["bad"] >= 3:
                saver.wait()
                logf.close()
                raise SystemExit(DIVERGED)
            continue
        meta["bad"] = 0
        opt.step()
        meta["step"] += 1
        meta["tokens"] += n_micro * micro * T
        meta["train_seconds"] += time.time() - t0
        if getattr(args, "stop_after_steps", 0) and meta["step"] == args.stop_after_steps:   # tests: a simulated kill
            meta["data"] = data.state()
            saver.save({"model": model.state_dict(), "opt": opt.state_dict(), "meta": meta}, state_path)
            saver.wait()
            logf.close()
            raise SystemExit(9)
        loss_ema = loss_sum if loss_ema is None else 0.95 * loss_ema + 0.05 * loss_sum
        if start_step == 0 and meta["step"] == 20:
            meta["loss_at_20"] = loss_ema
        if (start_step == 0 and meta["step"] == args.loss_check and "loss_at_20" in meta
                and not (loss_ema < meta["loss_at_20"] - args.loss_drop and loss_ema < args.loss_bound)):
            saver.wait()
            log(f"loss {loss_ema:.3f} at step {meta['step']} (step 20: {meta['loss_at_20']:.3f}; needed a drop of "
                f"{args.loss_drop} and < {args.loss_bound}): the recipe is not learning")
            logf.close()
            raise SystemExit(RECIPE_FAILED)
        if not checked:
            if meta["step"] == rate_from:
                t_rate, tok_rate = time.time(), meta["tokens"]
            elif meta["step"] >= rate_at:
                checked = True
                rate = (meta["tokens"] - tok_rate) / max(1e-9, time.time() - t_rate)
                left = max(0.0, end_by - time.time())
                fit = int(meta["tokens"] + rate * left * 0.95)
                meta["rate_check"] = {"at_step": meta["step"], "tok_per_s": rate}
                if fit < meta["total_tokens"]:
                    log(f"throughput {rate / 1e3:.0f} k tok/s, {left / 3600:.2f} h left: token target "
                        f"{meta['total_tokens'] / 1e9:.3f} B -> {fit / 1e9:.3f} B")
                    meta["total_tokens"] = max(fit, meta["tokens"])
                else:
                    log(f"throughput {rate / 1e3:.0f} k tok/s: {(meta['total_tokens'] - meta['tokens']) / 1e9:.3f} B "
                        f"tokens fit into the {left / 3600:.2f} h left")
        if end_by and time.time() > end_by + 600 and meta["total_tokens"] > meta["tokens"]:
            log("deadline exceeded by 10 min: training stops here")
            meta["total_tokens"] = meta["tokens"]
        if meta["step"] % args.log_every == 0:
            rec = {"step": meta["step"], "tokens": meta["tokens"], "frac": round(meta["tokens"] / meta["total_tokens"], 5),
                   "loss": loss_sum, "lr_factor": lr_f, "grad_norm": gn, "micro": micro, "decay_mix": decay_phase,
                   "tok_per_s": n_micro * micro * T / max(1e-9, time.time() - t0),
                   "train_hours": meta["train_seconds"] / 3600,
                   "gpu_mem_gb": torch.cuda.max_memory_allocated() / 2 ** 30 if device.type == "cuda" else 0.0}
            logf.write(json.dumps(rec) + "\n")
            logf.flush()
            print(rec, flush=True)
        if meta["tokens"] >= meta["next_eval"]:
            ev = {n: eval_stream(model, r, device, args.eval_docs)["bpb"] for n, r in val_streams(Path(args.data)).items()
                  if n.startswith("val_")}
            row = {"tokens": meta["tokens"], "train_hours": meta["train_seconds"] / 3600, "bpb": ev}
            with open(curve, "a") as f:
                f.write(json.dumps(row) + "\n")
            log(f"curve {json.dumps(row)}")
            meta["next_eval"] += args.eval_every
        if time.time() - t_ck > args.ckpt_minutes * 60:
            rate = (meta["tokens"] - tok_rate) / max(1e-9, time.time() - t_rate)
            fr = meta["tokens"] / meta["total_tokens"]
            if end_by and checked and fr < (1 - args.warmdown) - 0.05 and time.time() - t_rate >= 300 and rate > 0:
                fit = min(cap, int(meta["tokens"] + rate * max(0.0, end_by - time.time()) * 0.95))
                fit = max(fit, int(meta["tokens"] / ((1 - args.warmdown) - 0.03)) + 1)
                if abs(fit - meta["total_tokens"]) > 0.01 * meta["total_tokens"]:
                    log(f"token target re-fitted at {meta['tokens'] / 1e9:.3f} B ({rate / 1e3:.0f} k tok/s): "
                        f"{meta['total_tokens'] / 1e9:.3f} B -> {fit / 1e9:.3f} B")
                    meta.setdefault("refits", []).append({"tokens": meta["tokens"], "to": fit, "tok_per_s": rate})
                    meta["total_tokens"] = fit
            meta["data"] = data.state()
            meta["attention_used"] = stepper.attn
            saver.save({"model": model.state_dict(), "opt": opt.state_dict(), "meta": meta}, state_path)
            t_ck = time.time()
    saver.wait()
    logf.close()
    meta["data"] = data.state()
    meta["data_report"] = data.report()
    meta["attention_used"], meta["loss_used"] = stepper.attn, "fused" if stepper.fused else "chunked"
    if meta["tokens"] > 0 and not predecay.exists():
        atomic_save(to_cpu({"model": model.state_dict(), "opt": opt.state_dict(), "meta": {**meta, "predecay": True}}),
                    predecay)
        log("training ended before the decay: continuable state saved")
    atomic_save(to_cpu({"model": model.state_dict(), "opt": opt.state_dict(), "meta": meta}), state_path)
    atomic_save({"model": {k: v.detach().float().cpu() for k, v in model.state_dict().items()}, "cfg": cfg,
                 "meta": meta}, ckdir / "model_base.pt")
    (out / "pretrain_meta.json").write_text(json.dumps({k: v for k, v in meta.items() if k != "data"}, indent=1,
                                                       default=str) + "\n")
    log(f"pretraining finished: {meta['tokens'] / 1e9:.3f} B tokens in {meta['train_seconds'] / 3600:.2f} h")
    return meta


def _peek(data: PretrainMix, B: int, T: int) -> torch.Tensor:
    """A batch for the start-up checks without moving the data positions."""
    st = data.state()
    b = data.batch(B, T, False)
    data.load(st)
    return b


def make_opt(model, args, wd0: float, device):
    compile_opt = bool(args.compile and device.type == "cuda")
    if args.recipe == "adamw":                     # fallback: the Sela-1 optimiser on every parameter
        groups = [dict(kind="adamw", params=list(model.parameters()), lr=args.adamw_lr, betas=(0.9, 0.95), eps=1e-8,
                       weight_decay=0.1)]
        return O.MuonAdamW(groups, compile=compile_opt)
    return O.make_optimizer(model, weight_decay=wd0, compile=compile_opt)


# ---------------------------------------------------------------------------
# fine-tuning
# ---------------------------------------------------------------------------

def sft(args, device) -> dict:
    out, ckdir = Path(args.out), Path(args.ckpt_dir)
    out.mkdir(parents=True, exist_ok=True)
    st = torch.load(ckdir / "state_pre.pt", map_location="cpu", weights_only=False)
    pre_meta = st["meta"]
    cfg = pre_meta["cfg"]
    model = Sela2(Sela2Config(**cfg)).to(device)
    model.load_state_dict(st["model"])
    args.recipe = pre_meta["recipe"]
    opt = make_opt(model, args, 0.0, device)
    opt.load_state_dict(st["opt"])
    st = None
    for g in opt.param_groups:                     # nanochat chat_sft.py: init 0.8 × base rate, no weight decay
        g["initial_lr"] = g["initial_lr"] * args.sft_lr_frac * pre_meta.get("lr_scale", 1.0)
        g["weight_decay"] = 0.0 if g["kind"] == "muon" else g["weight_decay"]
        if g["kind"] == "muon":
            g["momentum"] = 0.95
    T, micro = cfg["ctx"], args.micro_batch
    data = SFTData(Path(args.data), T, seed=args.seed)
    rows_per_step = max(1, args.sft_batch_tokens // (T + 1))
    n_micro = max(1, rows_per_step // micro)
    est_steps = max(1, math.ceil(data.tokens_total / (n_micro * micro * (T + 1) * 0.92)))
    total_steps = est_steps
    stepper = Stepper(model, args, device, out, {"step": 0})
    logf = open(out / "sft_log.jsonl", "a")
    end_by = float(args.deadline or 0)
    t_start, step, trained = time.time(), 0, 0
    log(f"fine-tuning: {data.tokens_total / 1e6:.0f} M tokens in {len(data.order)} conversations, ~{est_steps} steps")
    if getattr(args, "sft_max_steps", 0):
        total_steps = min(total_steps, args.sft_max_steps)
    while step < total_steps and not data.exhausted():
        frac = step / total_steps
        f = 1.0 if frac < 0.5 else max(0.0, (1 - frac) / 0.5)
        for g in opt.param_groups:
            g["lr"] = g["initial_lr"] * f
        t0 = time.time()
        while True:
            try:
                opt.zero_grad(set_to_none=True)
                pos, buf = data.pos, list(data.buf)
                acc = torch.zeros((), dtype=torch.float32, device=device)
                n_tgt = 0
                for _ in range(n_micro):
                    inp, tgt, nt = data.batch(micro)
                    n_tgt += nt
                    inp, tgt = inp.to(device), tgt.to(device)
                    loss = stepper.loss(inp, tgt) / n_micro
                    loss.backward()
                    acc += loss.detach().float()
                break
            except Exception as e:
                loss = None
                opt.zero_grad(set_to_none=True)
                data.pos, data.buf = pos, buf
                if device.type == "cuda":
                    torch.cuda.empty_cache()
                what = stepper.fallback(e)
                if what == "out of memory":
                    if micro <= 1:
                        raise
                    micro //= 2
                    n_micro = max(1, rows_per_step // micro)
                    what = f"out of memory: micro-batch {micro}"
                if not what:
                    raise
                log(f"fine-tuning step failed – {what}")
        loss_v = float(acc)
        if not math.isfinite(loss_v):
            log(f"non-finite fine-tuning loss at step {step}: stopping with the last good weights")
            break
        opt.step()
        step += 1
        trained += n_tgt
        if step == 20 and end_by:                  # fit the number of steps to the deadline
            rate = 20 / max(1e-9, time.time() - t_start)
            fit = int(step + rate * max(0.0, end_by - time.time()) * 0.95)
            if fit < total_steps:
                log(f"fine-tuning steps fitted to the deadline: {total_steps} -> {fit}")
                total_steps = max(step + 1, fit)
        if end_by and time.time() > end_by:
            log("fine-tuning deadline reached")
            break
        if step % args.log_every == 0 or step == 1:
            rec = {"step": step, "of": total_steps, "loss": loss_v, "lr_factor": f, "assistant_tokens": trained,
                   "s_per_step": time.time() - t0}
            logf.write(json.dumps(rec) + "\n")
            logf.flush()
            print(rec, flush=True)
    logf.close()
    meta = {"pretrain": {k: v for k, v in pre_meta.items() if k not in ("data",)}, "sft_steps": step,
            "sft_planned_steps": total_steps, "sft_assistant_tokens": trained, "sft_seconds": time.time() - t_start,
            "sft_conversations_total": len(data.order), "sft_rows_used": data.pos}
    atomic_save({"model": {k: v.detach().float().cpu() for k, v in model.state_dict().items()}, "cfg": cfg,
                 "meta": meta}, ckdir / "model_chat.pt")
    (out / "sft_meta.json").write_text(json.dumps(meta, indent=1, default=str) + "\n")
    log(f"fine-tuning finished: {step} steps, {trained / 1e6:.1f} M assistant tokens")
    return meta


# ---------------------------------------------------------------------------
# evaluation and export commands
# ---------------------------------------------------------------------------

def load_model_file(path: Path, device) -> tuple[Sela2, dict]:
    st = torch.load(path, map_location="cpu", weights_only=False)
    model = Sela2(Sela2Config(**st["cfg"]))
    model.load_state_dict({k: v.float() for k, v in st["model"].items()})
    return model.to(device), st.get("meta", {})


def cmd_evaluate(args) -> None:
    device = pick_device(args.cpu)
    if device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = False
    model, meta = load_model_file(Path(args.model), device)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"tag": args.tag, "model": str(args.model), "params": model.param_counts(), "torch": torch.__version__,
           "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu", "bpb": {}, "chat_val": {}}
    streams = scan(Path(args.data))
    for name, rec in val_streams(Path(args.data)).items():
        t0 = time.time()
        r = eval_stream(model, rec, device, args.final_docs if name.startswith("val_") else 0)
        np.save(out / f"perdoc_{args.tag}_{name}.npy", r.pop("per_doc_bits").astype(np.float32))
        r["seconds"] = round(time.time() - t0, 1)
        res["bpb"][name] = r
        log(f"{name}: {r['bpb']:.4f} bpb ({r['docs']} documents)")
    for name in CHAT_VAL:
        if name in streams:
            res["chat_val"][name] = chat_val_loss(model, streams[name], device)
            log(f"{name}: assistant loss {res['chat_val'][name]['loss']:.4f}")
    if args.samples:
        try:
            from engramm.lm.tokenizer import LMTokenizer
            tok = LMTokenizer(Path(args.tokenizer), sha256=None)
            res["samples"] = samples(model, tok, device, chat=args.tag != "base")
        except Exception as e:                       # samples are a bonus; never lose the numbers over them
            res["samples_error"] = f"{type(e).__name__}: {e}"
    (out / f"eval_{args.tag}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str) + "\n")


def cmd_export(args) -> None:
    model, meta = load_model_file(Path(args.model), torch.device("cpu"))
    from engramm.lm.tokenizer import file_sha256
    tok = Path(args.tokenizer)
    m = {"source": Path(args.model).name, "tokens": (meta.get("pretrain") or meta).get("tokens"),
         "sft_steps": meta.get("sft_steps")}
    path = export_npz(model, args.out, meta=m, quant=args.quant)
    import numpy as _np
    with _np.load(path) as z:                      # the tokenizer the app must use, by file name and SHA-256
        arrays = {k: z[k] for k in z.files}
    header = json.loads(bytes(arrays["header"]).decode("utf-8"))
    header["tokenizer"] = {"file": tok.name, "sha256": file_sha256(tok)}
    arrays["header"] = _np.frombuffer(json.dumps(header).encode("utf-8"), dtype=_np.uint8)
    tmp = Path(str(path) + ".tmp.npz")
    _np.savez(tmp, **arrays)
    tmp.replace(path)
    if args.bf16_out:
        torch.save({"model": {k: v.to(torch.bfloat16) for k, v in model.state_dict().items()},
                    "cfg": model.cfg.to_dict(), "meta": meta}, args.bf16_out)
    log(f"exported {path} ({Path(path).stat().st_size / 1e6:.0f} MB)")


def cmd_pretrain(args) -> None:
    pretrain(args, pick_device(args.cpu))


def cmd_sft(args) -> None:
    sft(args, pick_device(args.cpu))


# ---------------------------------------------------------------------------
# smoke test: every path on the CPU with a tiny model and synthetic data
# ---------------------------------------------------------------------------

def fake_data(d: Path, vocab: int = 512, seed: int = 0) -> None:
    """Synthetic streams in the layout of experiments/sela2_data.py (a learnable pattern, so losses fall)."""
    from experiments.sela2_data import write_stream
    rng = np.random.default_rng(seed)

    def doc(n):
        a = int(rng.integers(20, vocab - 40))
        x = (a + np.arange(n) * int(rng.integers(1, 4))) % (vocab - 20) + 16
        return np.concatenate([[0], x]).astype(np.uint16)
    for g, n_docs in (("fwe_0", 300), ("fwehq_0", 80), ("dclm_0", 200), ("cosmo_0", 50), ("wiki_en_0", 50),
                      ("pg19_0", 10), ("fw2_de_0", 60), ("wiki_de_0", 20)):
        write_stream(d, g, [doc(int(rng.integers(20, 300))) for _ in range(n_docs)], "fake", {})
    for name in ("chat_en_decay", "chat_en_sft", "chat_en_val", "chat_de_decay", "chat_de_sft", "chat_de_val",
                 "grounded_decay", "grounded_sft", "grounded_val", "identity_decay", "identity_sft"):
        docs, masks = [], []
        for _ in range(60):
            n = int(rng.integers(10, 100))
            x = doc(n)
            x[1] = 1
            m = np.zeros(len(x), np.uint8)
            m[len(x) // 2:] = 1
            docs.append(x)
            masks.append(m)
        write_stream(d, name, docs, "fake", {"kind": "chat"}, masks=masks)
    for name in ("val_fwe", "val_dclm", "lm_test"):
        docs = [doc(int(rng.integers(20, 400))) for _ in range(20)]
        write_stream(d, name, docs, "fake", {}, nbytes=[3 * len(x) for x in docs])


def cmd_smoke(args) -> None:
    root = Path(args.dir)
    if root.exists():
        shutil.rmtree(root)
    data, ck, out = root / "data", root / "ckpt", root / "out"
    fake_data(data)
    torch.set_num_threads(max(1, args.threads))
    common = dict(data=str(data), ckpt_dir=str(ck), out=str(out), size="tiny", vocab=512, cpu=True, compile=0, flex=0,
                  bf16=0, loss="fused", micro_batch=4, batch_tokens=4 * 128, seed=0, tokenizer_sha="", recipe="sela2",
                  lr_scale=1.0, warmdown=0.65, decay_data_at=0.7, clip=0.0, loss_check=10 ** 9, loss_bound=99.0,
                  loss_drop=1.5, log_every=10, eval_every=40_000, eval_docs=10, ckpt_minutes=0.0, adamw_lr=1e-3)
    a = argparse.Namespace(**common, total_tokens=120_000, deadline=0, stop_after_steps=0)
    # 1) an uninterrupted run
    meta = pretrain(a, torch.device("cpu"))
    ref = torch.load(ck / "model_base.pt", weights_only=False)["model"]
    log_rows = [json.loads(x) for x in (out / "train_log.jsonl").read_text().splitlines()]
    curve = [json.loads(x) for x in (out / "curve.jsonl").read_text().splitlines()]
    assert any(r["decay_mix"] for r in log_rows) and not log_rows[0]["decay_mix"]
    first = float(np.mean([r["loss"] for r in log_rows[:3]]))
    last = float(np.mean([r["loss"] for r in log_rows[-3:]]))
    assert last < first - 0.5, (first, last)
    assert (ck / "state_pre_predecay.pt").exists() and meta["data_report"]["chat_en_decay"]["tokens_used"] > 0
    # 2) the same run killed after 37 steps and restarted: bit-identical weights (model, optimiser, data positions)
    ck2 = root / "ckpt2"
    b = argparse.Namespace(**{**vars(a), "ckpt_dir": str(ck2), "out": str(root / "out2"), "stop_after_steps": 37})
    try:
        pretrain(b, torch.device("cpu"))
        raise AssertionError("the simulated kill did not happen")
    except SystemExit as e:
        assert e.code == 9
    pretrain(argparse.Namespace(**{**vars(b), "stop_after_steps": 0}), torch.device("cpu"))
    again = torch.load(ck2 / "model_base.pt", weights_only=False)["model"]
    assert all(torch.equal(ref[k], again[k]) for k in ref), "resume is not exact"
    # 3) a deadline: the token target is fitted to the measured rate, the decay finishes by the deadline even when
    #    the run slows down (an injected slowdown in the decay), and the learning rate never rises in the decay
    ck3 = root / "ckpt3"
    slow = {"on": False}
    orig_batch = PretrainMix.batch

    def slowed(self, B, T, decay_phase):
        if decay_phase and not slow["on"]:
            slow["on"] = True
        if slow["on"]:
            time.sleep(0.15)
        return orig_batch(self, B, T, decay_phase)
    PretrainMix.batch = slowed
    try:
        t_end = time.time() + 40
        m3 = pretrain(argparse.Namespace(**{**vars(a), "ckpt_dir": str(ck3), "out": str(root / "out3"),
                                            "total_tokens": 50_000_000, "deadline": t_end, "log_every": 1}),
                      torch.device("cpu"))
    finally:
        PretrainMix.batch = orig_batch
    rows3 = [json.loads(x) for x in (root / "out3" / "train_log.jsonl").read_text().splitlines()]
    assert time.time() < t_end + 30, "the run did not end by its deadline"
    lrs = [r["lr_factor"] for r in rows3 if r["step"] > 40]
    in_decay = [r["lr_factor"] for r in rows3 if r["frac"] >= 0.36]
    assert in_decay and all(b <= a + 1e-9 for a, b in zip(in_decay, in_decay[1:])), "learning rate rose in the decay"
    assert lrs[-1] < 0.2, f"decay not finished by the deadline (last factor {lrs[-1]:.3f})"
    assert m3["total_tokens"] < 50_000_000 and slow["on"] and m3.get("ended_by_deadline"), m3.get("ended_by_deadline")
    sft_args = argparse.Namespace(**{**common, "deadline": 0, "sft_lr_frac": 0.8, "sft_batch_tokens": 4 * 129})
    sm = sft(sft_args, torch.device("cpu"))
    assert sm["sft_steps"] > 0 and (ck / "model_chat.pt").exists()
    ev = argparse.Namespace(data=str(data), model=str(ck / "model_chat.pt"), out=str(out), tag="chat", cpu=True,
                            final_docs=10, samples=0, tokenizer="")
    cmd_evaluate(ev)
    res = json.loads((out / "eval_chat.json").read_text())
    assert set(res["bpb"]) == {"val_fwe", "val_dclm", "lm_test"} and all(math.isfinite(v["bpb"]) for v in res["bpb"].values())
    assert res["chat_val"]["chat_en_val"]["loss"] > 0
    # 3) export to the app format; NumPy logits equal torch
    from engramm.lm.sela import KVCache2, Sela2Model
    model, _ = load_model_file(ck / "model_chat.pt", torch.device("cpu"))
    path = export_npz(model, root / "chat.npz", quant="fp32")
    nm = Sela2Model.load(path)
    ids = [0, 1] + list(range(16, 60))
    with torch.no_grad():
        ref = model(torch.tensor([ids]))[0].numpy()
    got = nm.forward(ids, KVCache2(nm.cfg))
    assert np.abs(got - ref).max() < 1e-3
    # 4) packed evaluation equals one-by-one evaluation
    seqs = [np.asarray([0] + list(range(16, 16 + n)), dtype=np.int64) for n in (5, 30, 60)]
    packed = logprobs_packed(model, seqs, torch.device("cpu"))
    for sq, lp in zip(seqs, packed):
        with torch.no_grad():
            one = F.log_softmax(model(torch.from_numpy(sq[None, :-1]))[0].float(), -1)
        want = one.gather(-1, torch.from_numpy(sq[1:])[:, None])[:, 0].double().numpy()
        assert np.abs(lp - want).max() < 1e-4
    print(json.dumps({"smoke": "ok", "pretrain_tokens": meta["tokens"], "loss_first": first, "loss_last": last,
                      "sft_steps": sm["sft_steps"], "curve_points": len(curve)}))


def add_common(p) -> None:
    p.add_argument("--data", default="/workspace/sela2/data")
    p.add_argument("--ckpt-dir", default=os.environ.get("SELA2_CKPT_DIR", "/workspace/sela2/ckpt"))
    p.add_argument("--out", default=str(REPO / "results" / "sela2"))
    p.add_argument("--size", default="sela2", choices=sorted(SIZES))
    p.add_argument("--vocab", type=int, default=0)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--compile", type=int, default=1)
    p.add_argument("--flex", type=int, default=1)
    p.add_argument("--bf16", type=int, default=1)
    p.add_argument("--loss", default="fused", choices=["fused", "chunked"])
    p.add_argument("--micro-batch", type=int, default=16)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--tokenizer-sha", default="")
    p.add_argument("--deadline", type=float, default=0.0, help="Unix time by which this stage must end")
    p.add_argument("--log-every", type=int, default=10)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pretrain")
    add_common(p)
    p.add_argument("--total-tokens", type=float, default=6e9, help="upper bound; the deadline decides")
    p.add_argument("--batch-tokens", type=int, default=524_288)
    p.add_argument("--recipe", default="sela2", choices=["sela2", "adamw"])
    p.add_argument("--adamw-lr", type=float, default=8e-4)
    p.add_argument("--lr-scale", type=float, default=1.0)
    p.add_argument("--warmdown", type=float, default=0.65)
    p.add_argument("--decay-data-at", type=float, default=0.70)
    p.add_argument("--clip", type=float, default=0.0, help="0 = no clipping (nanochat)")
    p.add_argument("--loss-check", type=int, default=300)
    p.add_argument("--loss-drop", type=float, default=1.5, help="nats the loss must fall from step 20 to the check")
    p.add_argument("--loss-bound", type=float, default=7.0)
    p.add_argument("--eval-every", type=float, default=5e8)
    p.add_argument("--eval-docs", type=int, default=100)
    p.add_argument("--ckpt-minutes", type=float, default=20.0)
    p.set_defaults(func=cmd_pretrain)
    p = sub.add_parser("sft")
    add_common(p)
    p.add_argument("--sft-lr-frac", type=float, default=0.8)
    p.add_argument("--sft-batch-tokens", type=int, default=262_144)
    p.add_argument("--sft-max-steps", type=int, default=0, help="tests: stop after this many steps")
    p.add_argument("--adamw-lr", type=float, default=8e-4)
    p.set_defaults(func=cmd_sft)
    p = sub.add_parser("evaluate")
    p.add_argument("--data", default="/workspace/sela2/data")
    p.add_argument("--model", required=True)
    p.add_argument("--out", default=str(REPO / "results" / "sela2"))
    p.add_argument("--tag", required=True)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--final-docs", type=int, default=1000)
    p.add_argument("--samples", type=int, default=1)
    p.add_argument("--tokenizer", default=str(TOKENIZER_FILE))
    p.set_defaults(func=cmd_evaluate)
    p = sub.add_parser("export")
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--quant", default="int8", choices=["int8", "fp16", "fp32"])
    p.add_argument("--tokenizer", default=str(TOKENIZER_FILE))
    p.add_argument("--bf16-out", default="")
    p.set_defaults(func=cmd_export)
    p = sub.add_parser("smoke")
    p.add_argument("--dir", default="/dev/shm/engramm/sela2_smoke")
    p.add_argument("--threads", type=int, default=2)
    p.set_defaults(func=cmd_smoke)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
