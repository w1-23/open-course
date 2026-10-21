"""Figures for chapter 8 (离线强化学习与策略评估).

Run from the build directory:

    python figures\\ch08_figs.py

Data figures are computed here (fixed seeds, the sample sizes are quoted in the
captions); the two schematics use ``figkit.blank`` + ``box``/``arrow``.
"""

from __future__ import annotations

import os
import sys

import numpy as np

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUILD_DIR)

import figkit  # noqa: E402
from figkit import C0, C1, C2, C3, C4, GREY, INK  # noqa: E402


# ---------------------------------------------------------------------------
# 8-1  offline setting: no closed loop
# ---------------------------------------------------------------------------
def f01_offline_setting():
    fig, axes = figkit.new(5.05, 1.72, ncols=2)
    for ax in axes:
        figkit.blank(ax, (-0.12, 3.42), (-0.32, 2.46))

    ax = axes[0]
    ax.text(1.64, 2.30, "在线：每一步都能试错", ha="center", fontsize=7.6, color=INK)
    figkit.box(ax, (0.05, 1.42), 0.98, 0.50, "策略 $\\pi$", fc="#e8f0e4", ec="#7d9b6a", fs=7.2)
    figkit.box(ax, (2.10, 1.42), 0.98, 0.50, "环境", fc="#eef3fb", ec="#7d93b2", fs=7.2)
    figkit.arrow(ax, (1.05, 1.80), (2.08, 1.80), text="$a$", color=INK, style="-|>")
    figkit.arrow(ax, (2.08, 1.56), (1.05, 1.56), color=INK, style="-|>")
    ax.text(1.56, 1.50, "$r,\\ s'$", ha="center", va="top", fontsize=6.8, color=INK)
    figkit.box(ax, (2.10, 0.42), 0.98, 0.46, "数据缓冲", fc="#f7f8fa", ec=GREY, fs=7.0)
    figkit.box(ax, (0.05, 0.42), 0.98, 0.46, "更新 $\\theta$", fc="#fdf1d8", ec="#c9a227", fs=7.0)
    figkit.arrow(ax, (2.59, 1.40), (2.59, 0.90), color=GREY, style="-|>")
    figkit.arrow(ax, (2.08, 0.65), (1.05, 0.65), color=GREY, style="-|>")
    figkit.arrow(ax, (0.54, 0.90), (0.54, 1.40), color=GREY, style="-|>")
    ax.text(1.64, 0.10, "样本由当前策略采集", ha="center", fontsize=6.6, color=GREY)

    ax = axes[1]
    ax.text(1.64, 2.30, "离线：数据固定，一次也不交互", ha="center", fontsize=7.6, color=INK)
    figkit.box(ax, (0.02, 1.36), 1.12, 0.62, "$\\mathcal{D}=\\{(s,a,r,s')\\}$\n$\\sim\\mu$",
               fc="#f7f8fa", ec=GREY, fs=6.9)
    figkit.box(ax, (1.52, 1.36), 0.80, 0.62, "学习\n$\\pi$", fc="#e8f0e4", ec="#7d9b6a", fs=7.2)
    figkit.box(ax, (2.64, 1.36), 0.70, 0.62, "部署", fc="#fdecea", ec="#c0392b", fs=7.0)
    figkit.arrow(ax, (1.16, 1.67), (1.50, 1.67), color=INK, style="-|>")
    figkit.arrow(ax, (2.34, 1.67), (2.64, 1.67), color=INK, style="-|>")
    ax.plot([3.00, 3.00, 0.58], [1.34, 0.86, 0.86], color=C3, linewidth=0.8,
            linestyle=(0, (3, 2)))
    ax.annotate("", xy=(0.58, 1.32), xytext=(0.58, 0.88),
                arrowprops=dict(arrowstyle="-|>", color=C3, linewidth=0.8,
                                linestyle="dashed"))
    ax.text(1.62, 0.52, "不能回流", ha="center", fontsize=6.8, color=C3)
    ax.text(1.62, 0.14, "训练时没有新样本可用", ha="center", fontsize=6.6, color=GREY)

    return figkit.save(fig, "ch08_f01_offline_setting")


# ---------------------------------------------------------------------------
# 8-2  extrapolation error: one data set, eight nearly-unconstrained fits
# ---------------------------------------------------------------------------
def f02_extrapolation():
    rng = np.random.default_rng(11)
    n = 500
    a = rng.uniform(0.05, 0.40, n)
    s = rng.uniform(0.0, 1.0, n)
    y = -(a - 0.35) ** 2 + 0.55 + 0.02 * rng.standard_normal(n)

    def poly(a, s):
        cols = [np.ones_like(a), a, a ** 2, a ** 3, s, s * a]
        return np.stack(cols, axis=1)

    grid = np.linspace(-0.15, 1.35, 260)
    fig, ax = figkit.new(4.55, 1.95)
    ax.axvspan(0.05, 0.40, color="#eef3fb", alpha=1.0, zorder=0)
    fits = []
    for _ in range(8):
        idx = rng.choice(n, size=80, replace=False)
        w = np.linalg.lstsq(poly(a[idx], s[idx]), y[idx], rcond=None)[0]
        pred = poly(grid, np.full_like(grid, 0.5)) @ w
        fits.append(pred)
        ax.plot(grid, pred, color=C0, linewidth=0.65, alpha=1.0)
    fits = np.array(fits)
    print("  f02 std inside  =", round(float(fits[:, (grid > 0.10) & (grid < 0.35)].std(0).mean()), 4))
    print("  f02 std outside =", round(float(fits[:, (grid > 0.85) & (grid < 0.95)].std()), 3))

    ax.plot(grid, -(grid - 0.35) ** 2 + 0.55, color=C3, linewidth=1.1,
            linestyle=(0, (4, 2)), label="真实 $Q(s,\\cdot)$")
    ax.set_xlabel("动作 $a$（固定 $s=0.5$）")
    ax.set_ylabel("$Q(s,a)$")
    ax.set_xlim(-0.15, 1.35)
    ax.set_ylim(-0.9, 0.85)
    ax.legend(loc="upper right", fontsize=6.8)
    ax.set_title("同一份数据、8 次重采样：支持集内重合，支持集外分叉", fontsize=7.4)
    ax.text(0.225, 0.04, "数据的动作覆盖", ha="center", fontsize=6.4, color="#4a6a8a",
            transform=ax.get_xaxis_transform())

    return figkit.save(fig, "ch08_f02_extrapolation")


# ---------------------------------------------------------------------------
# 8-3  what each family suppresses
# ---------------------------------------------------------------------------
def f03_suppression():
    fig, axes = figkit.new(5.15, 1.70, ncols=3)
    for ax in axes:
        figkit.blank(ax, (-0.10, 1.10), (-0.34, 1.14))
    rng = np.random.default_rng(3)

    ax = axes[0]
    ax.axvspan(0.18, 0.54, color="#eef3fb", alpha=1.0, zorder=0)
    cand = np.array([0.12, 0.24, 0.31, 0.42, 0.50, 0.66, 0.82])
    val = np.array([0.28, 0.52, 0.60, 0.55, 0.44, 0.78, 0.60])
    inside = (cand >= 0.18) & (cand <= 0.54)
    pick = int(np.where(inside, val, -9).argmax())
    ax.plot(cand[~inside], val[~inside], "o", markersize=2.6, color=GREY,
            mfc="white", mew=0.8)
    ax.plot(cand[inside], val[inside], "o", markersize=2.6, color=C0,
            mfc="white", mew=0.8)
    ax.plot(cand[pick], val[pick], "o", markersize=3.4, color=C3)
    ax.annotate("选中的候选", xy=(cand[pick] + 0.06, val[pick] - 0.06), xytext=(0.60, 0.26),
                fontsize=6.4, color=C3,
                arrowprops=dict(arrowstyle="-", color=C3, linewidth=0.6))
    ax.plot([0.0, 1.0], [0.22, 0.22], color=GREY, linewidth=0.6, linestyle=(0, (2, 2)))
    ax.set_title("BCQ：限制动作选择", fontsize=7.2)
    ax.set_xlabel("动作 $a$", fontsize=7.0)
    ax.text(0.52, -0.28, "支持集外的候选不参与比较", ha="center", fontsize=6.2, color=GREY)

    ax = axes[1]
    ax.axvspan(0.18, 0.54, color="#eef3fb", alpha=1.0, zorder=0)
    grid = np.linspace(0.0, 1.0, 240)
    truth = -(grid - 0.36) ** 2 + 0.58
    pen = 1.15 * np.clip(grid - 0.54, 0.0, None) ** 0.6
    ax.plot(grid, truth, color=C3, linewidth=1.0, linestyle=(0, (4, 2)))
    ax.plot(grid, truth - pen, color=C0, linewidth=1.1)
    ax.annotate("", xy=(0.88, 0.16), xytext=(0.88, 0.52),
                arrowprops=dict(arrowstyle="-|>", color=C0, linewidth=0.8))
    ax.text(0.84, 0.56, "压低", fontsize=6.4, color=C0, ha="right")
    ax.set_title("CQL：压低 $Q$ 值本身", fontsize=7.2)
    ax.set_xlabel("动作 $a$", fontsize=7.0)
    ax.text(0.52, -0.28, "惩罚项把数据外动作的估值拉下来", ha="center", fontsize=6.2, color=GREY)

    ax = axes[2]
    ax.axvspan(0.18, 0.54, color="#eef3fb", alpha=1.0, zorder=0)
    xs = np.linspace(0.19, 0.53, 30)
    ax.plot(xs, -(xs - 0.36) ** 2 + 0.58 + 0.03 * rng.standard_normal(xs.size),
            "o", markersize=2.2, color=C0, mfc="white", mew=0.7)
    ax.plot(xs, -(xs - 0.36) ** 2 + 0.58, color=C2, linewidth=1.2)
    ax.text(0.82, 0.30, "不查询", fontsize=6.6, color=GREY, ha="center")
    ax.set_title("IQL：不查数据外动作", fontsize=7.2)
    ax.set_xlabel("动作 $a$", fontsize=7.0)
    ax.text(0.52, -0.28, "期望回归只在数据内拟合", ha="center", fontsize=6.2, color=GREY)

    return figkit.save(fig, "ch08_f03_suppression")


# ---------------------------------------------------------------------------
# 8-4  compounding error, computed
# ---------------------------------------------------------------------------
def _rollout_bc(T, eps, rng, n_trials=2000):
    """Corridor: correct step advances, wrong step wastes one step.

    The learned policy is (1-eps)-correct on states the expert visits (dev=0)
    and uniform-random on states the expert never visits (dev>0).
    """
    total = 0
    for _ in range(n_trials):
        pos, dev, steps = 0, 0, 0
        while pos < T and steps < 40 * T:
            if dev == 0:
                ok = rng.random() > eps
            else:
                ok = rng.random() > 0.5
            if ok:
                pos += 1
            else:
                dev += 1
            steps += 1
        total += steps
    return total / n_trials - T      # regret = extra steps


def f04_compounding():
    Ts = np.array([3, 5, 8, 12, 16, 20, 26, 32, 40, 48, 56])
    eps = 0.10
    rng = np.random.default_rng(5)
    bc = np.array([_rollout_bc(int(T), eps, rng) for T in Ts])
    # DAgger keeps the policy inside its own state distribution: linear regret
    dag = eps / (1.0 - eps) * Ts

    fig, ax = figkit.new(3.95, 1.95)
    ax.plot(Ts, bc, "o-", color=C0, markersize=3.0, linewidth=1.0, label="行为克隆")
    ax.plot(Ts, dag, "s--", color=C2, markersize=2.6, linewidth=1.0, label="交互式聚合（DAgger）")
    ax.plot(Ts, bc[-1] / Ts[-1] ** 2 * Ts ** 2, ":", color=GREY, linewidth=0.9)
    ax.text(Ts[-1] * 0.62, bc[-1] * 0.40, "$\\propto T^2\\varepsilon$", fontsize=7.0, color=GREY)
    ax.set_xlabel("回合长度 $T$")
    ax.set_ylabel("相对专家的累计损失")
    ax.legend(loc="upper left", fontsize=6.8)
    ax.set_title("$\\varepsilon=0.1$，每点 2000 回合", fontsize=7.6)

    return figkit.save(fig, "ch08_f04_compounding")


# ---------------------------------------------------------------------------
# 8-5  OPE bias-variance, computed on a small MDP
# ---------------------------------------------------------------------------
class SmallMDP:
    """Three states, two actions; state 2 is absorbing (episode over)."""

    gamma = 0.90

    def __init__(self):
        # P[s][a] = list of (prob, next_state, reward)
        self.P = [
            [[(0.70, 0, 0.0), (0.30, 1, 0.4)], [(0.60, 0, 0.0), (0.20, 1, 0.5), (0.20, 2, 0.0)]],
            [[(0.45, 0, 0.2), (0.55, 2, 0.0)], [(0.50, 1, 0.1), (0.30, 2, 0.0), (0.20, 0, 0.6)]],
            [[(1.0, 2, 0.0)], [(1.0, 2, 0.0)]],
        ]
        self.mu = np.array([[0.65, 0.35], [0.55, 0.45], [0.50, 0.50]])
        self.pi = np.array([[0.20, 0.80], [0.30, 0.70], [0.50, 0.50]])

    def value(self, pol, s0=0, T=8):
        v = np.zeros(3)
        for _ in range(T):
            nv = np.zeros(3)
            for s in range(3):
                if s == 2:
                    continue
                for a in range(2):
                    for (p, s2, r) in self.P[s][a]:
                        nv[s] += pol[s, a] * p * (r + self.gamma * v[s2])
            v = nv
        return v[s0]

    def sample(self, rng, n, T=8):
        traj = []
        for _ in range(n):
            s, ep = 0, []
            for _ in range(T):
                if s == 2:
                    ep.append((s, 0, 0.0, 2))     # absorbing filler
                    continue
                a = int(rng.random() > self.mu[s, 0])
                r, s2 = 0.0, 2
                u = rng.random()
                acc = 0.0
                for (p, ns, rr) in self.P[s][a]:
                    acc += p
                    if u <= acc:
                        r, s2 = rr, ns
                        break
                ep.append((s, a, r, s2))
                s = s2
            traj.append(ep)
        return traj


def _discount(T):
    return np.array([SmallMDP.gamma ** t for t in range(T)])


def _estimators(traj, mdp, T=8):
    disc = _discount(T)
    is_w, wis_g, wis_w = [], [], []
    dm_terms, dr_terms = [], []
    for ep in traj:
        g = sum(disc[t] * ep[t][2] for t in range(T))
        w = 1.0
        for t in range(T):
            s, a = ep[t][0], ep[t][1]
            if s == 2:
                break
            w *= mdp.pi[s, a] / mdp.mu[s, a]
        is_w.append(w * g)
        wis_w.append(w)
        wis_g.append(w * g)
    return np.array(is_w), np.array(wis_g), np.array(wis_w)


def _model_from_data(traj, mdp, T=8):
    """Empirical model with Laplace smoothing (direct method / DR base)."""
    cnt = np.zeros((3, 2, 3))
    rsum = np.zeros((3, 2))
    nsa = np.zeros((3, 2))
    for ep in traj:
        for t in range(T):
            s, a, r, s2 = ep[t]
            if s == 2:
                break
            cnt[s, a, s2] += 1.0
            rsum[s, a] += r
            nsa[s, a] += 1.0
    prob = (cnt + 0.5) / (nsa[:, :, None] + 1.5)
    rew = rsum / np.maximum(nsa, 1.0)
    return prob, rew


def _policy_value_model(prob, rew, pol, gamma, T=8):
    v = np.zeros(3)
    for _ in range(T):
        nv = np.zeros(3)
        for s in range(2):
            for a in range(2):
                pa = pol[s, a]
                for s2 in range(3):
                    nv[s] += pa * prob[s, a, s2] * (rew[s, a] + gamma * v[s2])
        v = nv
    return v


def _lin_feats(s, a):
    s = np.asarray(s, dtype=float)
    a = np.asarray(a, dtype=float)
    return np.stack([np.ones_like(s), s, a, s * a, s * s], axis=1)


def f05_ope_bias_variance():
    mdp = SmallMDP()
    T, gamma = 8, mdp.gamma
    true_v = mdp.value(mdp.pi)
    rng = np.random.default_rng(17)
    n_ep, reps = 80, 200
    out = {"IS": [], "WIS": [], "DR": [], "FQE": []}

    for _ in range(reps):
        traj = mdp.sample(rng, n_ep, T)

        isv, wis_g, wis_w = _estimators(traj, mdp, T)
        out["IS"].append(isv.mean())
        out["WIS"].append(wis_g.sum() / max(wis_w.sum(), 1e-9))

        prob, rew = _model_from_data(traj, mdp, T)
        v_dm = _policy_value_model(prob, rew, mdp.pi, gamma, T)[0]

        g0 = np.array([sum(gamma ** t * ep[t][2] for t in range(T)) for ep in traj])
        out["DR"].append(v_dm + np.mean(wis_w * (g0 - v_dm)))

        S = np.array([[ep[t][0] for t in range(T)] for ep in traj]).ravel()
        A = np.array([[ep[t][1] for t in range(T)] for ep in traj]).ravel()
        R = np.array([[ep[t][2] for t in range(T)] for ep in traj]).ravel()
        S2 = np.array([[ep[t][3] for t in range(T)] for ep in traj]).ravel()
        keep = S != 2
        Phi = _lin_feats(S[keep], A[keep])
        theta = np.zeros(Phi.shape[1])
        s2k, rk = S2[keep], R[keep]
        for _it in range(150):
            q0 = _lin_feats(s2k, np.zeros_like(s2k)) @ theta
            q1 = _lin_feats(s2k, np.ones_like(s2k)) @ theta
            qn = mdp.pi[s2k, 0] * q0 + mdp.pi[s2k, 1] * q1
            qn[s2k == 2] = 0.0                    # absorbing: stop bootstrapping
            theta, *_ = np.linalg.lstsq(Phi, rk + gamma * qn, rcond=None)
        out["FQE"].append(float(mdp.pi[0, 0] * (_lin_feats([0], [0]) @ theta)[0]
                                + mdp.pi[0, 1] * (_lin_feats([0], [1]) @ theta)[0]))

    fig, ax = figkit.new(4.45, 2.02)
    style = {"IS": ("o", C3), "WIS": ("s", C4), "DR": ("^", C0), "FQE": ("D", C2)}
    ax.axvline(0.0, color=GREY, linewidth=0.7)
    for name, vals in out.items():
        v = np.array(vals)
        print(f"  {name:4s} mean={v.mean():+.4f} bias={v.mean() - true_v:+.4f} "
              f"std={v.std(ddof=1):.4f}")
        ax.scatter(np.abs(v.mean() - true_v), v.std(ddof=1), marker=style[name][0],
                   s=24, color=style[name][1], label=name, zorder=3)
    ax.set_xlim(-0.002, 0.040)
    ax.set_ylim(0.0, 0.55)
    ax.set_xticks([0.0, 0.01, 0.02, 0.03, 0.04])
    ax.set_xticklabels(["0", "0.01", "0.02", "0.03", "0.04"])
    ax.set_xlabel("偏差的绝对值 $|\\hat V- V^\\pi|$")
    ax.set_ylabel("标准差（200 次重复）")
    ax.legend(loc="upper left", fontsize=6.8, ncol=2)
    ax.set_title("同一数据集上的四个估计量（$N=80$ 条回合）", fontsize=7.4)

    return figkit.save(fig, "ch08_f06_ope")


# ---------------------------------------------------------------------------
# 8-6  effective sample size decays geometrically in the horizon
# ---------------------------------------------------------------------------
def f06_ess():
    mdp = SmallMDP()
    rng = np.random.default_rng(23)
    Ts = np.arange(1, 8)
    n, Tmax = 4000, 8
    traj = mdp.sample(rng, n, Tmax)
    W = np.ones((n, Tmax))
    for i, ep in enumerate(traj):
        w = 1.0
        for t in range(Tmax):
            s_, a_ = ep[t][0], ep[t][1]
            if s_ == 2:
                W[i, t:] = w
                break
            w *= mdp.pi[s_, a_] / mdp.mu[s_, a_]
            W[i, t] = w
    ess = np.array([(W[:, T - 1].sum() ** 2) / np.sum(W[:, T - 1] ** 2) / n for T in Ts])
    print("  ESS/N =", " ".join(f"{e:.2e}" for e in ess))

    fig, ax = figkit.new(3.70, 1.85)
    ax.semilogy(Ts, ess, "o-", color=C0, markersize=2.8, linewidth=1.0)
    ax.set_xlabel("回合长度 $T$")
    ax.set_ylabel("$\\mathrm{ESS}/N$")
    ax.set_yticks([1e-3, 1e-2, 1e-1, 1.0])
    ax.set_yticklabels(["1e-3", "1e-2", "1e-1", "1"])
    ax.set_ylim(1e-3, 1.2)
    ax.set_title("有效样本量随 $T$ 衰减（4000 条回合）", fontsize=7.4)

    return figkit.save(fig, "ch08_f05_ess")


def main() -> int:
    figkit.setup()
    # Negative tick labels must use the ASCII hyphen: the Chinese font carries no
    # U+2212, and a missing glyph prints as an empty box in the PDF.
    import matplotlib
    matplotlib.rcParams["axes.unicode_minus"] = False
    for fn in (f01_offline_setting, f02_extrapolation, f03_suppression,
               f04_compounding, f05_ope_bias_variance, f06_ess):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
