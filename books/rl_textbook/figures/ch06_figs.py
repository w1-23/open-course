"""Figures for chapter 6 (deep RL: DQN family and continuous control).

All data figures are computed here; the continuous-control experiment is
cached in cache/ch06_exp.npz so that repeated builds do not retrain.
"""
import math
import os

import numpy as np

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, BUILD_DIR)

import figkit
from figkit import C0, C1, C2, C3, C4, GREY, INK

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

CACHE = os.path.join(BUILD_DIR, "cache", "ch06_exp.npz")

SEEDS = [0, 1, 2, 3, 4]
STEPS = 15000


# --------------------------------------------------------------------- fig 6-1
def f01_patchmap():
    """Failure mode -> patch -> price, one row per patch."""
    rows = [
        ("样本高度相关\n数据只用一次", "经验回放", "分布偏移"),
        ("目标含自身参数\n更新追自己", "目标网络", "价值传播变慢"),
        ("最大算子\n系统性高估", "Double DQN", "可能转为低估"),
        ("状态价值与\n优势耦合", "Dueling", "语义偏移常数"),
        ("均匀采样\n浪费预算", "优先回放", "引入偏差"),
        ("探索效率\n随动作数下降", "Noisy Net", "探索与价值耦合"),
    ]
    fig, ax = figkit.new(5.05, 2.10)
    figkit.blank(ax, (0, 1), (0, 1))
    n = len(rows)
    top, bot = 0.945, 0.045
    h = (top - bot) / n * 0.66
    for i, (fail, patch, price) in enumerate(rows):
        y = top - (i + 0.5) * (top - bot) / n
        figkit.box(ax, (0.005, y - h / 2), 0.335, h, fail, fc="#f7f7f9", ec=GREY, fs=6.5)
        figkit.box(ax, (0.515, y - h / 2), 0.215, h, patch, fc="#eef3fb", ec="#7d93b2", fs=6.6)
        figkit.arrow(ax, (0.345, y), (0.512, y), color=GREY, style="-|>")
        ax.text(0.755, y, price, fontsize=6.3, color=C1, va="center", ha="left")
    ax.text(0.005, 0.995, "失效模式", fontsize=6.9, color=INK, va="bottom", ha="left",
            fontweight="bold")
    ax.text(0.515, 0.995, "补丁", fontsize=6.9, color=INK, va="bottom", ha="left",
            fontweight="bold")
    ax.text(0.755, 0.995, "代价", fontsize=6.9, color=INK, va="bottom", ha="left",
            fontweight="bold")
    return figkit.save(fig, "ch06_f01_patchmap")


# --------------------------------------------------------------------- fig 6-2
def f02_maxbias():
    """Monte-Carlo bias of the max operator: E[max Q] - max E[Q]."""
    rng = np.random.default_rng(7)
    ms = np.array([2, 3, 4, 6, 8, 12, 16, 24, 32])
    sigmas = [0.1, 0.3, 0.5]
    fig, ax = figkit.new(3.05, 1.85)
    colors = [C0, C1, C2]
    for sig, c in zip(sigmas, colors):
        bias = []
        for m in ms:
            x = rng.normal(0.0, sig, (400_000, m))
            bias.append(x.max(1).mean() - 0.0)
        ax.plot(ms, bias, "o-", color=c, markersize=2.6, linewidth=0.9,
                label=f"σ = {sig:g}")
    ax.set_xlabel("动作数 $m$")
    ax.set_ylabel("过估计")
    ax.set_xticks([2, 4, 8, 12, 16, 24, 32])
    ax.set_xticklabels(["2", "4", "8", "12", "16", "24", "32"])
    ax.set_ylim(0, 1.22)
    ax.legend(loc="lower right", fontsize=6.4, handlelength=1.5, borderaxespad=0.25,
              frameon=False)
    return figkit.save(fig, "ch06_f02_maxbias")


# ------------------------------------------------------- continuous-control task
class LQR:
    """Discrete double integrator with quadratic cost."""

    dt, gamma, horizon, a_max = 0.1, 0.99, 100, 2.0
    state_dim, act_dim = 2, 1

    def reset(self, rng):
        return np.array([rng.uniform(-2.0, 2.0), rng.uniform(-1.0, 1.0)], np.float32)

    def step(self, s, a):
        a = float(np.clip(float(np.asarray(a).reshape(-1)[0]), -self.a_max, self.a_max))
        p = s[0] + self.dt * s[1]
        v = s[1] + self.dt * a
        p, v = float(np.clip(p, -4, 4)), float(np.clip(v, -4, 4))
        return np.array([p, v], np.float32), -0.1 * (p * p + 0.1 * v * v + 0.01 * a * a)


def _lqr_optimum():
    import scipy.linalg as sla
    env = LQR()
    A = np.array([[1, env.dt], [0, 1]])
    B = np.array([[0], [env.dt]])
    Q = np.diag([1.0, 0.1])
    R = np.array([[0.01]])
    P = sla.solve_discrete_are(A, B, Q, R)
    return np.linalg.inv(R + B.T @ P @ B) @ B.T @ P @ A


def _eval(env, act, episodes=20):
    rets = []
    for k in range(episodes):
        rng = np.random.default_rng(10_000 + k)
        s, tot, n = env.reset(rng), 0.0, 0
        while n < env.horizon:
            s, r = env.step(s, act(s))
            tot += r
            n += 1
        rets.append(tot)
    return float(np.mean(rets))


def _lqr_return():
    env = LQR()
    K = _lqr_optimum()
    return _eval(env, lambda s: float(np.clip(-(K @ s)[0], -env.a_max, env.a_max)))


def _train(algo, seed, steps=STEPS, batch=64, warm=800, lr=3e-4, tau=0.005,
           noise=0.15, delay=2):
    import torch
    import torch.nn as nn

    torch.set_num_threads(1)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    env = LQR()
    gamma, amax = env.gamma, env.a_max

    def mlp(i, o):
        return nn.Sequential(nn.Linear(i, 32), nn.ReLU(), nn.Linear(32, 32), nn.ReLU(),
                             nn.Linear(32, o))

    class DetActor(nn.Module):
        def __init__(self):
            super().__init__()
            self.body = mlp(2, 1)

        def forward(self, s):
            return amax * torch.tanh(self.body(s))

    class GaussActor(nn.Module):
        def __init__(self):
            super().__init__()
            self.body = mlp(2, 2)

        def forward(self, s):
            mu, ls = self.body(s).chunk(2, -1)
            return mu, torch.clamp(ls, -10.0, 1.0)

        def sample(self, s):
            mu, ls = self(s)
            std = ls.exp()
            eps = torch.randn_like(mu)
            x = torch.tanh(mu + std * eps)
            logp = (-0.5 * (((mu + std * eps - mu) / std) ** 2 + 2 * ls
                            + math.log(2 * math.pi))).sum(-1)
            logp -= torch.log(1 - x ** 2 + 1e-6).sum(-1)
            return amax * x, logp

    sac = algo == "sac"
    actor = GaussActor() if sac else DetActor()
    actor_t = GaussActor() if sac else DetActor()
    actor_t.load_state_dict(actor.state_dict())
    nq = 2 if algo in ("td3", "sac") else 1
    qs = [mlp(3, 1) for _ in range(nq)]
    qts = [mlp(3, 1) for _ in range(nq)]
    for q, qt in zip(qs, qts):
        qt.load_state_dict(q.state_dict())
    opt_a = torch.optim.Adam(actor.parameters(), lr=lr)
    opt_q = [torch.optim.Adam(q.parameters(), lr=lr) for q in qs]
    alpha = 0.05

    cap = 50_000
    S = np.zeros((cap, 2), np.float32); A = np.zeros((cap, 1), np.float32)
    R = np.zeros((cap, 1), np.float32); S2 = np.zeros((cap, 2), np.float32)
    T = np.zeros((cap, 1), np.float32)
    n_fill, ptr = 0, 0

    def soft(tgt, src):
        with torch.no_grad():
            for p, q in zip(tgt.parameters(), src.parameters()):
                p.mul_(1 - tau).add_(tau * q)

    s, ep_ret, ep_len, ep_idx = env.reset(rng), 0.0, 0, 0
    curve = []          # (env_step, mean return of last 5 episodes)
    ep_returns = []

    for t in range(1, steps + 1):
        if t < warm:
            a = rng.uniform(-amax, amax, 1).astype(np.float32)
        else:
            with torch.no_grad():
                st = torch.as_tensor(s)[None]
                if sac:
                    at = actor.sample(st)[0][0].numpy()
                else:
                    at = actor(st)[0].numpy()
            a = at + (noise * rng.standard_normal(1).astype(np.float32) if not sac else 0)
            a = np.clip(a, -amax, amax).astype(np.float32)
        s2, r = env.step(s, a)
        ep_len += 1
        term = 1.0 if ep_len >= env.horizon else 0.0
        S[ptr], A[ptr], R[ptr], S2[ptr], T[ptr] = s, a, r, s2, term
        ptr = (ptr + 1) % cap
        n_fill = min(n_fill + 1, cap)
        s, ep_ret = s2, ep_ret + r
        if term:
            ep_returns.append(ep_ret)
            curve.append((t, float(np.mean(ep_returns[-5:]))))
            s, ep_ret, ep_len = env.reset(rng), 0.0, 0

        if t >= warm and n_fill >= batch:
            idx = rng.integers(0, n_fill, batch)
            tS = torch.as_tensor(S[idx]); tA = torch.as_tensor(A[idx])
            tR = torch.as_tensor(R[idx]); tS2 = torch.as_tensor(S2[idx])
            tT = torch.as_tensor(T[idx])
            with torch.no_grad():
                if algo == "ddpg":
                    y = tR + gamma * (1 - tT) * qts[0](torch.cat([tS2, actor_t(tS2)], -1))
                elif algo == "td3":
                    eps = torch.clamp(torch.randn(batch, 1) * 0.2, -0.5, 0.5)
                    a2 = torch.clamp(actor_t(tS2) + eps, -amax, amax)
                    y = tR + gamma * (1 - tT) * torch.min(
                        qts[0](torch.cat([tS2, a2], -1)), qts[1](torch.cat([tS2, a2], -1)))
                else:
                    a2, logp2 = actor.sample(tS2)
                    qm = torch.min(qs[0](torch.cat([tS2, a2], -1)),
                                   qs[1](torch.cat([tS2, a2], -1)))
                    y = tR + gamma * (1 - tT) * (qm - alpha * logp2.unsqueeze(-1))
            for q, o in zip(qs, opt_q):
                loss = ((q(torch.cat([tS, tA], -1)) - y) ** 2).mean()
                o.zero_grad(); loss.backward(); o.step()

            if sac:
                a_pi, logp = actor.sample(tS)
                qm = torch.min(qs[0](torch.cat([tS, a_pi], -1)),
                               qs[1](torch.cat([tS, a_pi], -1)))
                loss_a = (alpha * logp.unsqueeze(-1) - qm).mean()
                opt_a.zero_grad(); loss_a.backward(); opt_a.step()
                for q, qt in zip(qs, qts):
                    soft(qt, q)
            elif algo == "ddpg" or (algo == "td3" and t % delay == 0):
                a_pi = actor(tS)
                loss_a = -qs[0](torch.cat([tS, a_pi], -1)).mean()
                opt_a.zero_grad(); loss_a.backward(); opt_a.step()
                soft(actor_t, actor)
                for q, qt in zip(qs, qts):
                    soft(qt, q)

    def policy(st):
        with torch.no_grad():
            o = actor(torch.as_tensor(st)[None])
            if sac:
                return float(np.clip(np.tanh(o[0][0].numpy()) * amax, -amax, amax)[0])
            return float(np.clip(o[0].numpy(), -amax, amax)[0])

    ret = _eval(env, policy)
    return ret, np.asarray(curve, dtype=np.float32)


def _run_experiment():
    """Train DDPG/TD3/SAC on the LQR task; returns cache arrays."""
    out = {}
    for algo in ("ddpg", "td3", "sac"):
        for seed in SEEDS:
            ret, curve = _train(algo, seed)
            out[f"{algo}_ret_{seed}"] = np.array([ret], np.float32)
            out[f"{algo}_curve_{seed}"] = curve
            print(f"  {algo} seed {seed}: {ret:7.2f}", flush=True)
    return out


def _load_experiment():
    if os.path.exists(CACHE):
        d = np.load(CACHE)
        return {k: d[k] for k in d.files}
    import torch  # noqa: F401  (fail early with a clear message)
    print("training DDPG/TD3/SAC (cached afterwards) ...", flush=True)
    data = _run_experiment()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.savez_compressed(CACHE, **data, ref=np.array([_lqr_return()], np.float32))
    return data


# --------------------------------------------------------------------- fig 6-3
def f03_returns(data=None):
    data = data or _load_experiment()
    ref = float(data["ref"][0]) if "ref" in data else _lqr_return()
    algos = ["ddpg", "td3", "sac"]
    names = ["DDPG", "TD3", "SAC"]
    rets = [np.array([float(data[f"{a}_ret_{s}"][0]) for s in SEEDS]) for a in algos]
    norm = [np.clip(ref / r, 0.0, 1.02) for r in rets]

    fig, ax = figkit.new(3.2, 1.90)
    rng = np.random.default_rng(3)
    for i, (v, c) in enumerate(zip(norm, [C0, C1, C2])):
        ax.boxplot([v], positions=[i + 1], widths=0.42, showfliers=False,
                   medianprops=dict(color=INK, linewidth=1.1),
                   boxprops=dict(color=c, linewidth=0.9),
                   whiskerprops=dict(color=c, linewidth=0.8),
                   capprops=dict(color=c, linewidth=0.8))
        x = i + 1 + rng.uniform(-0.11, 0.11, len(v))
        ax.scatter(x, v, s=9, color=c, zorder=3, linewidths=0)
    ax.axhline(1.0, color=GREY, linestyle="--", linewidth=0.9)
    ax.text(3.42, 1.03, "LQR 最优", fontsize=6.4, color=GREY, ha="right", va="bottom")
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(names)
    ax.set_ylabel("归一化回报")
    ax.set_ylim(0, 1.06)
    ax.set_xlim(0.45, 3.55)
    return figkit.save(fig, "ch06_f03_returns")


# --------------------------------------------------------------------- fig 6-4
def f04_curves(data=None):
    data = data or _load_experiment()
    ref = float(data["ref"][0]) if "ref" in data else _lqr_return()
    fig, ax = figkit.new(3.35, 1.90)
    grid = np.linspace(0, STEPS, 240)
    for algo, name, c in (("ddpg", "DDPG", C0), ("td3", "TD3", C1), ("sac", "SAC", C2)):
        mat = []
        for s in SEEDS:
            cur = data[f"{algo}_curve_{s}"]
            mat.append(np.interp(grid, cur[:, 0], cur[:, 1]))
        mat = np.clip(ref / np.asarray(mat), 0.0, 1.02)
        k = 25
        mat = np.apply_along_axis(
            lambda v: np.convolve(v, np.ones(k) / k, mode="same"), 1, mat)
        med = np.median(mat, 0)
        lo, hi = np.percentile(mat, 25, 0), np.percentile(mat, 75, 0)
        ax.plot(grid, med, color=c, linewidth=1.1, label=name)
        ax.fill_between(grid, lo, hi, color=c, alpha=0.14, linewidth=0)
    ax.axhline(1.0, color=GREY, linestyle="--", linewidth=0.9)
    ax.set_xlabel("环境步数")
    ax.set_ylabel("归一化回报")
    ax.set_xlim(0, STEPS)
    ax.set_ylim(0, 1.02)
    ax.legend(loc="upper left", fontsize=6.6, handlelength=1.4, borderaxespad=0.25,
              frameon=False)
    return figkit.save(fig, "ch06_f04_curves")


# --------------------------------------------------------------------- fig 6-5
def f05_sim2real():
    fig, ax = figkit.new(5.05, 1.95)
    figkit.blank(ax, (0, 1), (0, 1))
    figkit.box(ax, (0.02, 0.56), 0.22, 0.26, "仿真\nμ(s), P(s'|s,a)", fc="#eef3fb", ec="#7d93b2",
               fs=7.8)
    figkit.box(ax, (0.76, 0.56), 0.22, 0.26, "真机\n观测与执行", fc="#fdf1e7", ec="#c85200",
               fs=7.8)
    gaps = [("观测延迟", "相机与推理\n滞后数十毫秒"), ("动作频率", "滤波与限幅\n改变实际动作"),
            ("安全约束", "一次碰撞的\n代价不可逆")]
    for i, (t1, t2) in enumerate(gaps):
        y = 0.84 - i * 0.28
        figkit.box(ax, (0.31, y - 0.10), 0.38, 0.20, f"{t1}：{t2}", fc="#f7f7f9", ec=GREY, fs=7.2)
        figkit.arrow(ax, (0.245, 0.69), (0.305, y), color=GREY, style="-|>")
        figkit.arrow(ax, (0.695, y), (0.755, 0.69), color=GREY, style="-|>")
    ax.text(0.5, 0.06, "域随机化扩大训练分布，但不提供泛化保证",
            fontsize=7.2, color=C1, ha="center", va="center")
    return figkit.save(fig, "ch06_f05_sim2real")


def main():
    figkit.setup()
    f01_patchmap()
    f02_maxbias()
    data = _load_experiment()
    f03_returns(data)
    f04_curves(data)
    f05_sim2real()


if __name__ == "__main__":
    raise SystemExit(main())
