"""Optimiser and schedules of Sela-2: Muon for the hidden matrices, AdamW for everything else.

The maths of nanochat's MuonAdamW (github.com/karpathy/nanochat, nanochat/optim.py), on one device:
- Muon (per group of equal-shape matrices, stacked): Nesterov momentum; MuonEq row equilibration; Polar-Express
  orthogonalisation (5 steps, coefficients of arXiv 2505.16932, in bfloat16 on the GPU); Muon+ renormalisation of
  the Frobenius norm to sqrt(min(m, n)); NorMuon variance reduction (factored second moment, beta2 0.9); cautious
  weight decay (only where update and weight agree in sign); learning rate × sqrt(max(1, rows / cols));
- AdamW (fp32 maths) for the token embedding, the value embeddings, the output matrix and the per-layer scalars,
  with nanochat's per-group rates, betas and weight decays; rates scaled by 1/sqrt(width / 768).
Schedules as nanochat's base_train.py: 40 warm-up steps, constant, then a linear decay over the last 65 % of the
tokens to 5 % of the peak; Muon momentum 0.85 → 0.97 over the first 400 steps and 0.97 → 0.90 during the decay;
Muon weight decay λ = 0.28 · sqrt(B / 2^19) · min(1, D_ref / D) (D_ref = nanochat's d12 horizon, 1.32 B tokens),
decayed to 0 along a cosine over the run.
"""

from __future__ import annotations

import math

import torch

POLAR_EXPRESS = (
    (8.156554524902461, -22.48329292557795, 15.878769915207462),
    (4.042929935166739, -2.808917465908714, 0.5000178451051316),
    (3.8916678022926607, -2.772484153217685, 0.5060648178503393),
    (3.285753657755655, -2.3681294933425376, 0.46449024233003106),
    (2.3465413258596377, -1.7097828382687081, 0.42323551169305323),
)
B_REF = 2 ** 19
D_REF = 12 * (12 * 12 * 768 ** 2 + 768 * 32_768)          # nanochat d12: 12 tokens per (matrix + head) parameter
WD_REF = 0.28


def orthogonalize(X: torch.Tensor, ns_steps: int = 5) -> torch.Tensor:
    """MuonEq row equilibration, then Polar Express: approximately U V^T of (each matrix of) X."""
    target = X.float().norm(dim=(-2, -1), keepdim=True) / (X.size(-2) ** 0.5)
    row = X.float().norm(dim=-1, keepdim=True).clamp_min(1e-6)
    X = X * (target / row).to(X.dtype)
    X = X / (X.norm(dim=(-2, -1), keepdim=True) * 1.01 + 1e-6)
    if X.size(-2) > X.size(-1):
        for a, b, c in POLAR_EXPRESS[:ns_steps]:
            A = X.mT @ X
            X = a * X + X @ (b * A + c * (A @ A))
    else:
        for a, b, c in POLAR_EXPRESS[:ns_steps]:
            A = X @ X.mT
            X = a * X + (b * A + c * (A @ A)) @ X
    return X


def newton_ok() -> bool:
    """Self-check: the orthogonalised random matrices (wide and tall) have singular values near 1."""
    g = torch.Generator().manual_seed(0)
    for shape in ((64, 256), (256, 64)):
        sv = torch.linalg.svdvals(orthogonalize(torch.randn(*shape, generator=g)))
        if not (0.6 < float(sv.min()) and float(sv.max()) < 1.3):
            return False
    return True


def muon_update(g: torch.Tensor, p: torch.Tensor, mom: torch.Tensor, v2: torch.Tensor, momentum: torch.Tensor,
                lr: torch.Tensor, wd: torch.Tensor, beta2: torch.Tensor, ns_steps: int, red_dim: int,
                low_precision: bool) -> None:
    """One Muon step on stacked matrices g, p (n, rows, cols), in place on p, mom and v2 (nanochat
    muon_step_fused). The hyperparameters are 0-D tensors so that a compiled version never recompiles."""
    momentum = momentum.to(g.dtype)
    mom.lerp_(g, 1 - momentum)
    g = g.lerp_(mom, momentum)                                         # Nesterov
    g = orthogonalize(g.bfloat16() if low_precision else g, ns_steps).to(p.dtype)
    g = g * (min(g.size(-2), g.size(-1)) ** 0.5 / g.float().norm(dim=(-2, -1), keepdim=True).clamp_min(1e-6)).to(g.dtype)
    beta2 = beta2.to(g.dtype)                                          # NorMuon variance reduction
    v_mean = g.float().square().mean(dim=red_dim, keepdim=True)
    n_red = g.size(red_dim)
    v_norm = (v_mean.sum(dim=(-2, -1), keepdim=True) * n_red).sqrt()
    v2.lerp_(v_mean.to(v2.dtype), 1 - beta2)
    step = v2.clamp_min(1e-10).rsqrt()
    v_norm_new = ((v_mean * n_red) * step.float().square()).sum(dim=(-2, -1), keepdim=True).sqrt()
    g = g * (step * (v_norm / v_norm_new.clamp_min(1e-10))).to(g.dtype)
    lr, wd = lr.to(g.dtype), wd.to(g.dtype)
    mask = (g * p) >= 0                                                # cautious weight decay
    p.sub_(lr * g + lr * wd * p * mask)


def adamw_update(p: torch.Tensor, grad: torch.Tensor, m: torch.Tensor, v: torch.Tensor, step: torch.Tensor,
                 lr: torch.Tensor, beta1: torch.Tensor, beta2: torch.Tensor, eps: torch.Tensor,
                 wd: torch.Tensor) -> None:
    p32, g32 = p.float(), grad.float()
    p32.mul_(1 - lr * wd)
    m.lerp_(g32, 1 - beta1)
    v.lerp_(g32.square(), 1 - beta2)
    denom = (v / (1 - beta2 ** step)).sqrt() + eps
    p32.add_(m / denom * (-lr / (1 - beta1 ** step)))
    if p.dtype != torch.float32:                                      # fp32 weights were updated in place
        p.copy_(p32)


class MuonAdamW(torch.optim.Optimizer):
    """Param groups with kind='adamw' (lr, betas, eps, weight_decay) or kind='muon' (lr, momentum, ns_steps, beta2,
    weight_decay; all matrices of a group have one shape). ``compile=True`` compiles both update functions."""

    def __init__(self, groups: list[dict], compile: bool = False):
        for g in groups:
            if g["kind"] == "muon":
                shapes = {tuple(p.shape) for p in g["params"]}
                if len(shapes) != 1 or len(next(iter(shapes))) != 2:
                    raise ValueError(f"a Muon group needs matrices of one shape, got {shapes}")
            g.setdefault("initial_lr", g["lr"])
        super().__init__(groups, {})
        self._muon = torch.compile(muon_update, dynamic=False) if compile else muon_update
        self._adamw = torch.compile(adamw_update, dynamic=False) if compile else adamw_update
        self._t = {k: torch.tensor(0.0) for k in ("lr", "wd", "mom", "b1", "b2", "eps", "step")}

    def _f(self, key: str, value: float) -> torch.Tensor:
        t = self._t[key]
        t.fill_(value)
        return t

    @torch.no_grad()
    def step(self, closure=None):
        for g in self.param_groups:
            if g["kind"] == "adamw":
                for p in g["params"]:
                    if p.grad is None:
                        continue
                    st = self.state[p]
                    if not st:
                        st["step"] = 0
                        st["m"] = torch.zeros_like(p, dtype=torch.float32)
                        st["v"] = torch.zeros_like(p, dtype=torch.float32)
                    st["step"] += 1
                    self._adamw(p, p.grad, st["m"], st["v"], self._f("step", st["step"]), self._f("lr", g["lr"]),
                                self._f("b1", g["betas"][0]), self._f("b2", g["betas"][1]), self._f("eps", g["eps"]),
                                self._f("wd", g["weight_decay"]))
            else:
                ps = [p for p in g["params"] if p.grad is not None]
                if not ps:
                    continue
                rows, cols = ps[0].shape
                st = self.state[g["params"][0]]
                n = len(g["params"])
                if not st:
                    st["mom"] = torch.zeros(n, rows, cols, dtype=ps[0].dtype, device=ps[0].device)
                    st["v2"] = torch.zeros((n, rows, 1) if rows >= cols else (n, 1, cols), dtype=ps[0].dtype,
                                           device=ps[0].device)
                if len(ps) != n:
                    raise RuntimeError("Muon group with some gradients missing")
                grads = torch.stack([p.grad for p in ps])
                stack = torch.stack(ps)
                self._muon(grads, stack, st["mom"], st["v2"], self._f("mom", g["momentum"]),
                           self._f("lr", g["lr"] * max(1.0, rows / cols) ** 0.5), self._f("wd", g["weight_decay"]),
                           self._f("b2", g["beta2"]), g["ns_steps"], -1 if rows >= cols else -2,
                           stack.is_cuda)
                torch._foreach_copy_(ps, list(stack.unbind(0)))
        return None


def muon_weight_decay(batch_tokens: int, total_tokens: int) -> float:
    return WD_REF * math.sqrt(batch_tokens / B_REF) * min(1.0, D_REF / max(1, total_tokens))


def make_optimizer(model, matrix_lr: float = 0.02, embedding_lr: float = 0.3, unembedding_lr: float = 0.008,
                   scalar_lr: float = 0.5, weight_decay: float = 0.0, batch_lr_scale: float = 1.0,
                   compile: bool = False) -> MuonAdamW:
    """nanochat's GPT.setup_optimizer for experiments.sela2_model.Sela2."""
    s = (model.cfg.d / 768) ** -0.5
    matrices = [p for p in model.blocks.parameters()]
    groups = [
        dict(kind="adamw", params=[model.head.weight], lr=unembedding_lr * s * batch_lr_scale, betas=(0.8, 0.96),
             eps=1e-10, weight_decay=0.01),
        dict(kind="adamw", params=[model.emb.weight], lr=embedding_lr * s * batch_lr_scale, betas=(0.8, 0.995),
             eps=1e-10, weight_decay=0.001),
        dict(kind="adamw", params=[model.resid], lr=scalar_lr * 0.01, betas=(0.8, 0.95), eps=1e-10, weight_decay=0.05),
        dict(kind="adamw", params=[model.x0], lr=scalar_lr, betas=(0.96, 0.95), eps=1e-10, weight_decay=0.0),
        dict(kind="adamw", params=[model.smear_gate.weight, model.smear_lambda, model.backout], lr=0.2,
             betas=(0.8, 0.95), eps=1e-10, weight_decay=0.0),
    ]
    if len(model.ve):
        groups.insert(2, dict(kind="adamw", params=[t.weight for t in model.ve], lr=embedding_lr * s * batch_lr_scale * 0.5,
                              betas=(0.8, 0.995), eps=1e-10, weight_decay=0.01))
    for shape in sorted({tuple(p.shape) for p in matrices}):
        groups.append(dict(kind="muon", params=[p for p in matrices if tuple(p.shape) == shape],
                           lr=matrix_lr * batch_lr_scale, momentum=0.95, ns_steps=5, beta2=0.9,
                           weight_decay=weight_decay))
    n_opt = sum(len(g["params"]) for g in groups)
    if n_opt != len(list(model.parameters())):
        raise RuntimeError(f"optimiser covers {n_opt} of {len(list(model.parameters()))} parameter tensors")
    return MuonAdamW(groups, compile=compile)


def lr_mult(frac: float, step: int, warmup: int = 40, warmdown: float = 0.65, final: float = 0.05) -> float:
    """Learning-rate factor at token fraction ``frac`` and optimiser step ``step``."""
    if step < warmup:
        return (step + 1) / warmup
    if frac <= 1 - warmdown:
        return 1.0
    prog = max(0.0, (1 - frac) / warmdown)
    return prog + (1 - prog) * final


def muon_momentum(frac: float, step: int, warmdown: float = 0.65) -> float:
    if step < 400:
        f = step / 400
        m = (1 - f) * 0.85 + f * 0.97
        return m if frac < 1 - warmdown else min(m, 0.97)
    if frac >= 1 - warmdown:
        prog = min(1.0, (frac - (1 - warmdown)) / warmdown)
        return 0.97 * (1 - prog) + 0.90 * prog
    return 0.97


def wd_mult(frac: float) -> float:
    return 0.5 * (1 + math.cos(math.pi * min(1.0, max(0.0, frac))))


def set_schedule(opt: MuonAdamW, frac: float, step: int, wd0: float, warmup: int = 40, warmdown: float = 0.65,
                 final: float = 0.05, lr_scale: float = 1.0) -> float:
    """Applies the schedules to every group; returns the learning-rate factor."""
    f = lr_mult(frac, step, warmup, warmdown, final) * lr_scale
    for g in opt.param_groups:
        g["lr"] = g["initial_lr"] * f
        if g["kind"] == "muon":
            g["momentum"] = muon_momentum(frac, step, warmdown)
            g["weight_decay"] = wd0 * wd_mult(frac)
    return f
