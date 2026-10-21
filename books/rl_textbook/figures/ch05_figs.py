"""Figures for chapter 5 (策略梯度、信赖域与 PPO).

Run from the build directory::

    python figures\\ch05_figs.py

Every data figure is a real computation on the small chain MDP defined in
``_Chain`` below (four transient states, two actions, slip probability 0.9,
gamma = 0.9).  Because the MDP is finite and the policy is tabular softmax, the
value function, the occupancy measure, the exact policy gradient and the exact
KL between two softmax policies are all available in closed form -- so the
Monte-Carlo estimators in the figures can be scored against the truth instead of
against another estimator.

Seeds, sample counts and protocols are printed at the end of the run and are
repeated in the figure captions of the chapter.
"""

from __future__ import annotations

import os
import sys

import numpy as np

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUILD_DIR)

import figkit  # noqa: E402
from figkit import C0, C1, C2, C3, C4, GREY, INK  # noqa: E402

GAMMA = 0.9
P_SLIP = 0.9          # probability that "go" advances
N_STATE = 4
N_ACT = 2             # 0 = wait, 1 = go
WAIT, GO = 0, 1
TERMINAL_REWARD = 1.0


# ---------------------------------------------------------------------------
# the chain MDP: exact quantities
# ---------------------------------------------------------------------------
def _reward(s: int, a: int) -> float:
    return TERMINAL_REWARD if (s == N_STATE - 1 and a == GO) else 0.0


def _transitions(s: int, a: int) -> list[tuple[int, float]]:
    """(next transient state, probability); terminal is encoded as -1."""
    if a == WAIT:
        return [(s, 1.0)]
    if s == N_STATE - 1:
        return [(-1, P_SLIP), (s, 1.0 - P_SLIP)]
    return [(s + 1, P_SLIP), (s, 1.0 - P_SLIP)]


def softmax(theta: np.ndarray) -> np.ndarray:
    z = np.exp(theta - theta.max(axis=1, keepdims=True))
    return z / z.sum(axis=1, keepdims=True)


def policy_matrices(theta: np.ndarray):
    pi = softmax(theta)
    p_pi = np.zeros((N_STATE, N_STATE))
    r_pi = np.zeros(N_STATE)
    for s in range(N_STATE):
        for a in range(N_ACT):
            for s2, prob in _transitions(s, a):
                if s2 >= 0:
                    p_pi[s, s2] += pi[s, a] * prob
            r_pi[s] += pi[s, a] * _reward(s, a)
    return pi, p_pi, r_pi


def values(theta: np.ndarray):
    """Exact V^pi, Q^pi, and the undiscounted-free occupancy measure."""
    pi, p_pi, r_pi = policy_matrices(theta)
    v = np.linalg.solve(np.eye(N_STATE) - GAMMA * p_pi, r_pi)
    q = np.zeros((N_STATE, N_ACT))
    for s in range(N_STATE):
        for a in range(N_ACT):
            q[s, a] = _reward(s, a)
            for s2, prob in _transitions(s, a):
                if s2 >= 0:
                    q[s, a] += GAMMA * prob * v[s2]
    # occupancy d^pi_gamma(s) = sum_t gamma^t Pr(s_t = s), start at state 0
    d = np.linalg.solve(np.eye(N_STATE) - GAMMA * p_pi.T,
                        np.eye(N_STATE)[0])
    return pi, v, q, d


def objective(theta: np.ndarray) -> float:
    """J(theta) = E[sum_t gamma^t r_{t+1}] = sum_s d(s) r^pi(s)."""
    pi, v, q, d = values(theta)
    _, _, r_pi = policy_matrices(theta)
    return float(d @ r_pi), float(v[0])


def exact_gradient(theta: np.ndarray) -> np.ndarray:
    pi, v, q, d = values(theta)
    grad = np.zeros((N_STATE, N_ACT))
    for s in range(N_STATE):
        qbar = float(pi[s] @ q[s])
        for b in range(N_ACT):
            grad[s, b] = d[s] * pi[s, b] * (q[s, b] - qbar)
    return grad


def kl_softmax(theta_new: np.ndarray, theta_old: np.ndarray) -> float:
    """E_{s ~ d^pi_old}[ KL(pi_old(.|s) || pi_new(.|s)) ]."""
    pi_old, _, _ = policy_matrices(theta_old)
    _, v_old, q_old, d_old = values(theta_old)
    pi_new = softmax(theta_new)
    kl = 0.0
    for s in range(N_STATE):
        kl += d_old[s] * float(np.sum(pi_old[s] * (np.log(pi_old[s]) -
                                                   np.log(pi_new[s]))))
    return kl


# ---------------------------------------------------------------------------
# sampling
# ---------------------------------------------------------------------------
def rollout(theta: np.ndarray, rng: np.random.Generator, max_len: int = 200):
    pi = softmax(theta)
    s, traj = 0, []
    for _ in range(max_len):
        a = int(rng.choice(N_ACT, p=pi[s]))
        r = _reward(s, a)
        nxt = -1
        u, acc = rng.random(), 0.0
        for s2, prob in _transitions(s, a):
            acc += prob
            if u <= acc:
                nxt = s2
                break
        traj.append((s, a, r, nxt))
        if nxt < 0:
            break
        s = nxt
    return traj


def log_policy_grad(theta: np.ndarray, s: int, a: int) -> np.ndarray:
    pi = softmax(theta)
    g = np.zeros((N_STATE, N_ACT))
    g[s, :] = -pi[s]
    g[s, a] += 1.0
    return g


def estimator(theta: np.ndarray, traj, kind: str, lam: float = 1.0,
              v_critic: np.ndarray | None = None) -> np.ndarray:
    """One-episode estimate of grad J.

    kind = "mc"     : sum_t gamma^t G_t grad log pi           (REINFORCE)
    kind = "base"   : sum_t gamma^t (G_t - b(s_t)) grad log pi
    kind = "gae"    : sum_t gamma^t A_t grad log pi, A from GAE(lambda)
    """
    pi = softmax(theta)
    horizon = len(traj)
    rets = np.zeros(horizon)
    g = 0.0
    for t in reversed(range(horizon)):
        g = traj[t][2] + GAMMA * g
        rets[t] = g
    est = np.zeros((N_STATE, N_ACT))
    if kind in ("mc", "base"):
        base = v_critic if v_critic is not None else values(theta)[1]
        for t, (s, a, _, _) in enumerate(traj):
            weight = GAMMA ** t
            if kind == "base":
                weight *= rets[t] - base[s]
            else:
                weight *= rets[t]
            est += weight * log_policy_grad(theta, s, a)
        return est
    # GAE
    adv = np.zeros(horizon)
    running = 0.0
    for t in reversed(range(horizon)):
        s, a, r, nxt = traj[t]
        v_next = 0.0 if nxt < 0 else v_critic[nxt]
        delta = r + GAMMA * v_next - v_critic[s]
        running = delta + GAMMA * lam * running
        adv[t] = running
    for t, (s, a, _, _) in enumerate(traj):
        est += (GAMMA ** t) * adv[t] * log_policy_grad(theta, s, a)
    return est


# ---------------------------------------------------------------------------
# experiment 1: bias / variance of the estimators
# ---------------------------------------------------------------------------
def experiment_estimators(theta0, exact, n_rep=30, n_ep=80, seed=11):
    rng0 = np.random.default_rng(seed)
    pi0, v0, q0, d0 = values(theta0)
    v_wrong = 1.6 * v0                    # a critic with a systematic error
    lams = [0.0, 0.5, 0.9, 0.95, 1.0]
    rows = {}
    for tag, critic in (("exact", v0), ("wrong", v_wrong)):
        for lam in lams:
            reps = []
            for _ in range(n_rep):
                rng = np.random.default_rng(rng0.integers(1 << 62))
                acc = np.zeros((N_STATE, N_ACT))
                for _ in range(n_ep):
                    traj = rollout(theta0, rng)
                    acc += estimator(theta0, traj, "gae", lam, critic)
                reps.append(acc / n_ep)
            reps = np.array(reps)
            mean = reps.mean(axis=0)
            rows[(tag, lam)] = (
                float(np.linalg.norm(mean - exact)),
                float(np.sqrt(np.mean(np.sum((reps - mean) ** 2, axis=(1, 2))))),
            )
    # the two plain Monte-Carlo estimators, as a reference point
    for tag, kind, critic in (("mc", "mc", None), ("base", "base", v0)):
        reps = []
        for _ in range(n_rep):
            rng = np.random.default_rng(rng0.integers(1 << 62))
            acc = np.zeros((N_STATE, N_ACT))
            for _ in range(n_ep):
                traj = rollout(theta0, rng)
                acc += estimator(theta0, traj, kind, 1.0, critic)
            reps.append(acc / n_ep)
        reps = np.array(reps)
        mean = reps.mean(axis=0)
        rows[(tag, None)] = (
            float(np.linalg.norm(mean - exact)),
            float(np.sqrt(np.mean(np.sum((reps - mean) ** 2, axis=(1, 2))))),
        )
    return lams, rows


def f01_estimator_road():
    """Three objects that are routinely confused: occupancy, trajectory
    expectation, and the sample estimate."""
    fig, ax = figkit.new(4.95, 2.10)
    figkit.blank(ax, (-0.12, 4.62), (-0.16, 2.42))

    figkit.box(ax, (0.02, 1.42), 1.28, 0.72,
               "占用测度写法\n$\\sum_s d^{\\pi}_\\gamma\\sum_a\\nabla\\pi\\,Q^{\\pi}$",
               fs=7.4, fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (1.66, 1.42), 1.34, 0.72,
               "轨迹期望写法\n$\\frac{1}{1-\\gamma}\\mathbb{E}[\\nabla\\log\\pi\\,Q]$",
               fs=7.4, fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (3.40, 1.42), 1.14, 0.72,
               "样本估计\n$\\sum_t\\gamma^t\\hat{A}_t\\nabla\\log\\pi$",
               fs=7.4, fc="#fdf1d8", ec="#c9a227")

    figkit.arrow(ax, (1.32, 1.78), (1.64, 1.78), color=INK)
    figkit.arrow(ax, (3.02, 1.78), (3.38, 1.78), color=INK)
    ax.text(1.48, 1.90, "$\\times\\frac{1}{1-\\gamma}$", ha="center",
            fontsize=7.0, color=C1)
    ax.text(3.20, 1.90, "采样", ha="center", fontsize=6.8, color=C1)

    ax.text(0.66, 1.20, "总质量 $1/(1-\\gamma)$", ha="center", fontsize=6.8,
            color=GREY)
    ax.text(2.33, 1.20, "总质量为 1", ha="center", fontsize=6.8, color=GREY)
    ax.text(3.97, 1.20, "无偏、方差大", ha="center", fontsize=6.8, color=GREY)

    figkit.box(ax, (0.02, 0.28), 1.28, 0.56, "被策略固定的\n权重", fs=7.0,
               fc="#f7f8fa", ec=GREY)
    figkit.box(ax, (1.66, 0.28), 1.34, 0.56, "同一条式子的\n另一种读法", fs=7.0,
               fc="#f7f8fa", ec=GREY)
    figkit.box(ax, (3.40, 0.28), 1.14, 0.56, "减基线、加\nGAE 的出发点", fs=7.0,
               fc="#f7f8fa", ec=GREY)

    ax.text(2.30, 2.34, "同一个梯度的三种写法：差一个归一化因子，不是差一个目标",
            ha="center", fontsize=7.6, color=INK)
    return figkit.save(fig, "ch05_f01_estimator_road")


# ---------------------------------------------------------------------------
# experiment 2: figure 2, bias and variance against lambda
# ---------------------------------------------------------------------------
def f02_gae_bias_variance():
    theta0 = np.zeros((N_STATE, N_ACT))
    exact = exact_gradient(theta0)
    lams, rows = experiment_estimators(theta0, exact)
    ex_bias = [rows[("exact", l)][0] for l in lams]
    ex_sd = [rows[("exact", l)][1] for l in lams]
    wr_bias = [rows[("wrong", l)][0] for l in lams]
    wr_sd = [rows[("wrong", l)][1] for l in lams]

    fig, axes = figkit.new(4.45, 2.05, ncols=2)
    ax = axes[0]
    ax.plot(lams, ex_bias, "o-", color=C0, label="critic 精确")
    ax.plot(lams, wr_bias, "s-", color=C1, label="critic 有系统偏差")
    ax.set_xlabel("自举参数 $\\lambda$")
    ax.set_ylabel("偏差（梯度范数）")
    ax.legend(loc="upper right", fontsize=6.6)
    ax.set_title("偏差随 $\\lambda$ 增大而减小", fontsize=7.6)
    ax.set_xticks([0.0, 0.5, 1.0])
    ax.tick_params(labelsize=6.6)

    ax = axes[1]
    ax.plot(lams, ex_sd, "o-", color=C0, label="critic 精确")
    ax.plot(lams, wr_sd, "s-", color=C1, label="critic 有系统偏差")
    ax.set_xlabel("自举参数 $\\lambda$")
    ax.set_ylabel("标准差（梯度范数）")
    ax.set_title("方差随 $\\lambda$ 增大而增大", fontsize=7.6)
    ax.set_xticks([0.0, 0.5, 1.0])
    ax.tick_params(labelsize=6.6)
    ax.legend(loc="upper left", fontsize=6.6)

    mc = rows[("mc", None)]
    print("[f02] exact gap at lambda=0/1: "
          f"bias {ex_bias[0]:.4f}/{ex_bias[-1]:.4f}  sd {ex_sd[0]:.4f}/{ex_sd[-1]:.4f}")
    print(f"[f02] wrong-critic bias {wr_bias[0]:.4f} -> {wr_bias[-1]:.4f}; "
          f"plain MC bias {mc[0]:.4f} sd {mc[1]:.4f}")
    return figkit.save(fig, "ch05_f03_gae_bias_variance")


# ---------------------------------------------------------------------------
# figure 3: step size controls the per-update policy displacement
# ---------------------------------------------------------------------------
def experiment_steps(lrs=(0.05, 1.0, 5.0), iters=30, seeds=8, n_ep=6):
    """One epoch of reuse per iteration, so the步长 is the only knob."""
    out = {}
    for lr in lrs:
        Js, Ks = [], []
        for sd in range(seeds):
            js, kl = ppo_run(np.zeros((N_STATE, N_ACT)), lam=0.95, eps=None,
                             iters=iters, n_ep=n_ep, epochs=1, lr=lr, seed=sd)
            Js.append(js)
            Ks.append(kl)
        out[lr] = (np.array(Js), np.array(Ks))
    return out


def f03_step_size():
    res = experiment_steps()
    fig, axes = figkit.new(4.45, 2.00, ncols=2)
    colors = {0.05: C0, 1.0: C2, 5.0: C1}

    ax = axes[0]
    for lr, (Js, _) in res.items():
        mean, sd = Js.mean(axis=0), Js.std(axis=0)
        x = range(1, len(mean) + 1)
        ax.plot(x, mean, color=colors[lr], label=f"$\\alpha={lr}$")
        ax.fill_between(x, mean - sd, mean + sd, color=colors[lr], alpha=0.16,
                        linewidth=0)
    ax.set_xlabel("迭代轮数")
    ax.set_ylabel("真实目标 $J(\\theta)$")
    ax.legend(loc="upper left", fontsize=6.6)
    ax.set_title("步长决定收敛快慢", fontsize=7.6)

    ax = axes[1]
    for lr, (_, Ks) in res.items():
        ax.plot(range(1, Ks.shape[1] + 1), Ks.mean(axis=0), color=colors[lr],
                label=f"$\\alpha={lr}$")
    ax.set_xlabel("迭代轮数")
    ax.set_ylabel("单步 $D_{\\mathrm{KL}}$")
    ax.set_yscale("log")
    ax.set_yticks([1e-4, 1e-3, 1e-2, 1e-1, 1.0])
    ax.set_yticklabels(["1e-4", "1e-3", "1e-2", "1e-1", "1"])
    ax.axhline(0.01, color=GREY, linewidth=0.7, linestyle=(0, (3, 2)),
               label="阈值 $\\delta=0.01$")
    ax.legend(loc="lower right", fontsize=6.6)
    ax.set_title("同一批数据上的策略位移", fontsize=7.6)

    for lr, (Js, Ks) in res.items():
        mean = Js.mean(axis=0)
        print(f"[f03] alpha={lr}: J {mean[0]:.4f} -> {mean[-5:].mean():.4f}, "
              f"min {mean.min():.4f}, maxKL {Ks.mean(axis=0).max():.3g}, "
              f"medKL {np.median(Ks):.3g}")
    return figkit.save(fig, "ch05_f04_step_size")


# ---------------------------------------------------------------------------
# figure 5: how many epochs of reuse on one batch
# ---------------------------------------------------------------------------
def f05_reuse_epochs():
    lr = 0.5
    epoch_list = [1, 4, 8, 16]
    colors = [C0, C3, C2, C1]
    res = {}
    for ep in epoch_list:
        Js, Ks = [], []
        for sd in range(6):
            js, kl = ppo_run(np.zeros((N_STATE, N_ACT)), lam=0.95, eps=0.2,
                             iters=30, n_ep=6, epochs=ep, lr=lr, seed=sd)
            Js.append(js)
            Ks.append(kl)
        res[ep] = (np.array(Js), np.array(Ks))

    fig, axes = figkit.new(4.45, 2.00, ncols=2)
    ax = axes[0]
    for ep, color in zip(epoch_list, colors):
        Js, _ = res[ep]
        mean, sd = Js.mean(axis=0), Js.std(axis=0)
        x = range(1, len(mean) + 1)
        ax.plot(x, mean, color=color, label=f"{ep} 轮")
        ax.fill_between(x, mean - sd, mean + sd, color=color, alpha=0.14,
                        linewidth=0)
    ax.set_xlabel("迭代轮数")
    ax.set_ylabel("真实目标 $J(\\theta)$")
    ax.legend(loc="lower right", fontsize=6.6, title="每批数据复用",
              title_fontsize=6.2)
    ax.set_title("复用轮数越多，越早到位", fontsize=7.6)

    ax = axes[1]
    for ep, color in zip(epoch_list, colors):
        _, Ks = res[ep]
        ax.plot(range(1, Ks.shape[1] + 1), Ks.mean(axis=0), color=color,
                label=f"{ep} 轮")
    ax.set_xlabel("迭代轮数")
    ax.set_ylabel("单步 $D_{\\mathrm{KL}}$")
    ax.set_yscale("log")
    ax.set_yticks([1e-3, 1e-2, 1e-1, 1.0])
    ax.set_yticklabels(["1e-3", "1e-2", "1e-1", "1"])
    ax.legend(loc="lower right", fontsize=6.6)
    ax.set_title("代价是单步位移变大", fontsize=7.6)

    for ep in epoch_list:
        Js, Ks = res[ep]
        print(f"[f05] epochs={ep}: final J {Js[:, -5:].mean():.4f} "
              f"+-{Js[:, -5:].std():.4f}, medKL {np.median(Ks):.3g}")
    return figkit.save(fig, "ch05_f06_reuse_epochs")


# ---------------------------------------------------------------------------
# table 5-2: epsilon_clip x lambda, same protocol as figure 5
# ---------------------------------------------------------------------------
def table_clip_lambda():
    eps_list = [None, 0.1, 0.2, 0.3]
    lam_list = [0.0, 0.95, 1.0]
    rows = []
    for lam in lam_list:
        for eps in eps_list:
            finals, kls = [], []
            for sd in range(6):
                js, kl = ppo_run(np.zeros((N_STATE, N_ACT)), lam=lam, eps=eps,
                                 iters=30, n_ep=6, epochs=8, lr=0.5, seed=sd)
                finals.append(js[-8:].mean())
                kls.append(float(np.median(kl)))
            rows.append((lam, eps, float(np.mean(finals)),
                         float(np.std(finals)), float(np.mean(kls))))
            print(f"[tab] lam={lam:<5} eps={eps!s:<5} "
                  f"J={rows[-1][2]:.4f} +-{rows[-1][3]:.4f} KL={rows[-1][4]:.3f}")
    return rows


# ---------------------------------------------------------------------------
# figure 4: the clipped surrogate as a function of the ratio
# ---------------------------------------------------------------------------
def f04_ppo_clip():
    eps = 0.2
    ratio = np.linspace(0.2, 1.8, 401)

    def clipped(a):
        adv = np.full_like(ratio, a)
        unclipped = ratio * adv
        clipped_r = np.clip(ratio, 1 - eps, 1 + eps) * adv
        return unclipped, np.minimum(unclipped, clipped_r)

    fig, axes = figkit.new(4.35, 1.85, ncols=2)
    for ax, adv, title in ((axes[0], 1.0, "优势为正"),
                           (axes[1], -1.0, "优势为负")):
        unclipped, clip_obj = clipped(adv)
        ax.plot(ratio, unclipped, color=GREY, linewidth=0.8,
                linestyle=(0, (4, 2)), label="未裁剪")
        ax.plot(ratio, clip_obj, color=C0, linewidth=1.2, label="裁剪后")
        ax.axvline(1.0, color="#d8dbe0", linewidth=0.6)
        ax.axhline(0.0, color="#d8dbe0", linewidth=0.6)
        ax.set_xlabel("概率比 $\\rho$")
        ax.set_ylabel("单步目标")
        ax.set_title(title, fontsize=7.6)
        ax.set_xlim(0.2, 1.8)
    axes[0].legend(loc="lower right", fontsize=6.4)
    axes[1].legend(loc="lower left", fontsize=6.4)
    axes[0].set_ylim(-0.15, 1.75)
    axes[1].set_ylim(-1.75, 0.15)
    axes[0].set_yticks([0.0, 0.5, 1.0, 1.5])
    axes[0].set_yticklabels(["0", "0.5", "1", "1.5"])
    axes[1].set_yticks([-1.5, -1.0, -0.5, 0.0])
    axes[1].set_yticklabels(["-1.5", "-1", "-0.5", "0"])
    for ax in axes:
        ax.axvline(1 - eps, color=C1, linewidth=0.6, linestyle=(0, (2, 2)))
        ax.axvline(1 + eps, color=C1, linewidth=0.6, linestyle=(0, (2, 2)))
    axes[0].text(1 + eps + 0.02, 1.45, "$1+\\epsilon$", fontsize=6.2, color=C1)
    axes[1].text(1 - eps - 0.02, -1.35, "$1-\\epsilon$", fontsize=6.2,
                 color=C1, ha="right")
    print("[f04] eps=0.2; clipping bites outside ratio [0.8, 1.2]")
    return figkit.save(fig, "ch05_f05_ppo_clip")


# ---------------------------------------------------------------------------
# figure 5: the PPO replay experiment (clip vs no clip, lambda sweep)
# ---------------------------------------------------------------------------
def ppo_run(theta0, lam=0.95, eps=0.2, iters=60, n_ep=24, epochs=4,
            lr=0.08, seed=3, minibatch=64):
    """A deliberately small PPO: tabular softmax policy, GAE from the exact
    value function of pi_old, clipped surrogate, several epochs of reuse."""
    rng = np.random.default_rng(seed)
    theta = theta0.copy()
    js, kls = [], []
    for _ in range(iters):
        pi_old = softmax(theta)
        _, v_old, _, _ = values(theta)
        data = []
        for _ in range(n_ep):
            traj = rollout(theta, rng)
            h = len(traj)
            adv = np.zeros(h)
            running = 0.0
            for t in reversed(range(h)):
                s, a, r, nxt = traj[t]
                v_next = 0.0 if nxt < 0 else v_old[nxt]
                delta = r + GAMMA * v_next - v_old[s]
                running = delta + GAMMA * lam * running
                adv[t] = running
            for t in range(h):
                s, a, _, _ = traj[t]
                data.append((s, a, float(adv[t]), float(pi_old[s, a])))
        for _ in range(epochs):
            order = rng.permutation(len(data))
            for start in range(0, len(data), minibatch):
                chunk = [data[i] for i in order[start:start + minibatch]]
                grad = np.zeros_like(theta)
                for s, a, adv, p_old in chunk:
                    pi = softmax(theta)
                    ratio = pi[s, a] / max(p_old, 1e-12)
                    surr_un = ratio * adv
                    if eps is None:
                        # no clipping: plain importance-weighted surrogate
                        if ratio * adv < 1e18:
                            grad += adv * log_policy_grad(theta, s, a)
                    else:
                        if ratio < 1 - eps and adv < 0:
                            continue                 # clipped, gradient zero
                        if ratio > 1 + eps and adv > 0:
                            continue
                        grad += ratio * adv * log_policy_grad(theta, s, a)
                theta = theta + lr * grad / max(len(chunk), 1)
        js.append(objective(theta)[0])
        kls.append(kl_softmax(theta, pi_old))
    return np.array(js), np.array(kls)


# ---------------------------------------------------------------------------
# figure 6: actor-critic data flow
# ---------------------------------------------------------------------------
def f06_actor_critic():
    """A single closed loop, drawn as an orthogonal zig-zag so that no arrow
    crosses a box and no label sits on a line."""
    fig, ax = figkit.new(4.40, 2.05)
    figkit.blank(ax, (-0.10, 4.50), (-0.14, 2.36))

    y1, y2 = 1.52, 0.62
    figkit.box(ax, (0.05, y1), 1.10, 0.54, "环境\n采样", fs=6.8,
               fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (1.52, y1), 1.06, 0.54, "评论家\n估计 $V_\\phi$", fs=6.8,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (2.96, y1), 0.96, 0.54, "优势估计\n$\\hat A_t$", fs=6.8,
               fc="#fdf1d8", ec="#c9a227")
    figkit.box(ax, (2.96, y2), 0.96, 0.54, "演员\n更新 $\\pi_\\theta$", fs=6.8,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (1.52, y2), 1.06, 0.54, "新策略\n下一批 rollout", fs=6.6,
               fc="#f7f8fa", ec=GREY)

    figkit.arrow(ax, (1.17, y1 + 0.27), (1.50, y1 + 0.27), color=INK)
    ax.text(1.335, y1 + 0.35, "$G_t$", ha="center", fontsize=6.4, color=C1)
    figkit.arrow(ax, (2.60, y1 + 0.27), (2.94, y1 + 0.27), color=INK)
    ax.text(2.77, y1 + 0.35, "$V_\\phi$", ha="center", fontsize=6.4, color=C1)
    figkit.arrow(ax, (3.44, y1 - 0.02), (3.44, y2 + 0.56), color=INK)
    ax.text(3.52, (y1 + y2) / 2 + 0.27, "$\\hat A_t$", fontsize=6.4, color=C1)
    figkit.arrow(ax, (2.94, y2 + 0.27), (2.60, y2 + 0.27), color=INK)
    ax.text(2.77, y2 + 0.35, "$\\nabla\\log\\pi$", ha="center", fontsize=6.2,
            color=C1)
    figkit.arrow(ax, (1.50, y2 + 0.27), (0.60, y2 + 0.27), color=INK)
    ax.text(1.02, y2 + 0.36, "数据复用", ha="center", fontsize=6.0, color=GREY)
    figkit.arrow(ax, (0.60, y2 + 0.30), (0.60, y1 - 0.02), color=INK)

    ax.text(2.30, 2.18, "同一批数据、两个学习率：critic 只提供基线，actor 只关心优势",
            ha="center", fontsize=6.8, color=INK)
    return figkit.save(fig, "ch05_f02_actor_critic")


def main() -> int:
    figkit.setup()
    for fn in (f01_estimator_road, f02_gae_bias_variance, f03_step_size,
               f04_ppo_clip, f05_reuse_epochs, f06_actor_critic):
        fn()
    rows = table_clip_lambda()
    print("\n表 5-2 数据（ε_clip × λ，6 seeds，30 迭代，每批 6 回合 × 8 轮复用）")
    for lam, eps, mean, sd, kl in rows:
        print(f"  lambda={lam:<5} eps={eps!s:<5} J={mean:.4f} sd={sd:.4f} KL={kl:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

