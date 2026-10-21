"""Figures for chapter 4 (函数逼近与离策略学习).

Run from the build directory:

    python figures\\ch04_figs.py

Every figure is vector SVG written into ``figures/out``; the layout stage keeps
it as vector, so the diagrams stay sharp at any zoom.  The two data figures are
*computed*, not sketched: the numbers printed on stdout are the ones quoted in
the chapter text and captions, so the text can be checked against the script.

Experiment 1 (f03): 19-state random walk, semi-gradient TD(0) vs LSTD, error
    measured in the weighted norm of the chapter, ``||v_theta - v_pi||_mu``.
Experiment 2 (f04, f05): the same update rule under two sampling distributions
    -- Baird's counterexample (off-policy diverges, on-policy does not) and a
    19-state two-action chain where the behaviour policy only shifts the fixed
    point and inflates the variance.
"""

from __future__ import annotations

import os
import sys

import numpy as np
from matplotlib.patches import Polygon

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUILD_DIR)

import figkit  # noqa: E402
from figkit import C0, C1, C2, C3, C4, GREY, INK  # noqa: E402

# --------------------------------------------------------------------------
# shared model machinery
# --------------------------------------------------------------------------

N_WALK = 19          # interior states 1..19, absorbing 0 (reward 0) and 20 (+1)
GAMMA = 0.99
R_RIGHT = 1.0


def walk_model(n=N_WALK, gamma=GAMMA, p_right=0.5, r_right=R_RIGHT):
    """Absorbing random walk as (P, r): P is n x n *substochastic*.

    Missing probability mass is the mass that leaves for a terminal, whose
    value is zero, so the Bellman equation is v = r + gamma P v on the n
    interior states and nothing else is needed.
    """
    P = np.zeros((n, n))
    r = np.zeros(n)
    for i in range(1, n + 1):
        if i + 1 <= n:                       # right step stays inside
            P[i - 1, i] += p_right
        else:                                # right step leaves, reward +1
            r[i - 1] += p_right * r_right
        if i - 1 >= 1:                       # left step stays inside
            P[i - 1, i - 2] += 1.0 - p_right
    return P, r


def true_values(P, r, gamma=GAMMA):
    return np.linalg.solve(np.eye(P.shape[0]) - gamma * P, r)


def visit_distribution(P, rho0):
    """Normalised expected visit counts of the absorbing chain -- the
    distribution of the states the sampler actually shows the learner."""
    nu = np.linalg.solve(np.eye(P.shape[0]) - P.T, rho0)
    return nu / nu.sum()


def legendre_features(n, d):
    """Normalised Legendre polynomials on [-1, 1]: orthogonal (hence well
    conditioned) under a near-uniform mu, so a change in the error is a
    statistical effect and not a linear-algebra accident."""
    t = np.linspace(-1.0, 1.0, n + 2)[1:-1]
    return np.polynomial.legendre.legvander(t, d - 1)


def ve(theta, Phi, v_true, mu):
    return float(np.sqrt(np.sum(mu * (Phi @ theta - v_true) ** 2)))


def td_fixed_point(Phi, P, r, mu, gamma=GAMMA):
    """theta* = A^{-1} b, A = Phi' D (I - gamma P) Phi, b = Phi' D r."""
    D = np.diag(mu)
    A = Phi.T @ D @ (np.eye(P.shape[0]) - gamma * P) @ Phi
    b = Phi.T @ D @ r
    return np.linalg.solve(A, b), A, b


def best_projection(Phi, v_true, mu):
    """argmin_theta ||Phi theta - v||_mu, i.e. Pi_D v, the VE optimum."""
    D = np.diag(mu)
    return np.linalg.solve(Phi.T @ D @ Phi, Phi.T @ D @ v_true)


# --------------------------------------------------------------------------
# samplers
# --------------------------------------------------------------------------

def simulate(P, r, n_steps, rng, rho0):
    """Yield (s, reward, s_next); s_next = -1 marks a transition to a terminal.

    A row of P sums to less than one exactly when part of its probability mass
    leaves the chain, and r[s] collects the expected reward of that exit, so the
    realised exit reward is r[s] / (1 - row_sum).
    """
    n = P.shape[0]
    cum = np.cumsum(P, axis=1)
    s = int(rng.choice(n, p=rho0))
    for _ in range(n_steps):
        u = rng.random()
        tot = cum[s, -1]
        if u >= tot:
            yield s, r[s] / (1.0 - tot), -1
            s = int(rng.choice(n, p=rho0))
        else:
            s2 = min(int(np.searchsorted(cum[s], u)), n - 1)
            yield s, 0.0, s2
            s = s2


def run_td(Phi, P, r, n_steps, alpha, rng, rho0, snaps=None, gamma=GAMMA):
    theta = np.zeros(Phi.shape[1])
    pending = sorted(snaps or [])
    done = []
    k = 0
    for s, rew, s2 in simulate(P, r, n_steps, rng, rho0):
        x = Phi[s]
        v2 = 0.0 if s2 < 0 else Phi[s2] @ theta
        theta = theta + alpha * (rew + gamma * v2 - x @ theta) * x
        k += 1
        while pending and k >= pending[0]:
            done.append((pending.pop(0), theta.copy()))
    return theta, done


def run_lstd(Phi, P, r, n_steps, rng, rho0, gamma=GAMMA):
    d = Phi.shape[1]
    A = 1e-10 * np.eye(d)
    b = np.zeros(d)
    for s, rew, s2 in simulate(P, r, n_steps, rng, rho0):
        x = Phi[s]
        x2 = np.zeros(d) if s2 < 0 else Phi[s2]
        A += np.outer(x, x - gamma * x2)
        b += rew * x
    return np.linalg.solve(A, b)


def run_td_is(Phi, P_behav, n_steps, alpha, rng, rho0, pi_pa, b_pa,
              snaps=None, gamma=GAMMA):
    """Off-policy semi-gradient TD(0): sample (s, a) from the behaviour policy,
    weight the update by rho = pi(a|s) / b(a|s).  The chain that is actually
    followed is the behaviour chain, which is what sets D in the fixed point."""
    n, d = P_behav.shape[0], Phi.shape[1]
    theta = np.zeros(d)
    cum = np.cumsum(P_behav, axis=1)
    pending = sorted(snaps or [])
    done = []
    s = int(rng.choice(n, p=rho0))
    for k in range(1, n_steps + 1):
        a = 0 if rng.random() < b_pa[0] else 1          # 0 = left, 1 = right
        rho = pi_pa[a] / b_pa[a]
        s2 = s + 1 if a == 1 else s - 1
        if s2 < 0 or s2 >= n:
            rew = 1.0 if s2 >= n else 0.0
            v2 = 0.0
            terminal = True
        else:
            rew = 0.0
            v2 = Phi[s2] @ theta
            terminal = False
        theta = theta + alpha * rho * (rew + gamma * v2 - Phi[s] @ theta) * Phi[s]
        if terminal:
            s = int(rng.choice(n, p=rho0))
        else:
            s = s2
        while pending and k >= pending[0]:
            done.append((pending.pop(0), theta.copy()))
    return theta, done


# --------------------------------------------------------------------------
# f01: the deadly triad, drawn as a structure diagram
# --------------------------------------------------------------------------

def f01_triad():
    fig, ax = figkit.new(3.60, 2.05)
    figkit.blank(ax, (-0.05, 3.60), (-0.10, 2.28))

    xs = [0.10, 1.31, 2.52]
    labels = ["函数逼近\n$V_\\theta\\approx V^\\pi$", "自举\n$\\gamma V_\\theta(s')$",
              "离策略\n$\\mu\\neq\\pi$"]
    colors = [("#eef3fb", "#7d93b2"), ("#f7f3ea", "#b79b6a"), ("#f6eef6", "#9a7f9e")]
    for x, lab, (fc, ec) in zip(xs, labels, colors):
        figkit.box(ax, (x, 1.60), 0.94, 0.56, lab, fc=fc, ec=ec, fs=6.9)
    for gx in (1.175, 2.385):
        ax.text(gx, 1.88, "$+$", ha="center", va="center", fontsize=9.0, color=INK)

    figkit.arrow(ax, (1.78, 1.58), (1.78, 1.32), color=C1)
    figkit.box(ax, (0.55, 0.94), 2.46, 0.34,
               "三者齐备：不稳定与发散的风险", fc="#fdecea", ec="#c0392b", fs=7.0)
    ax.text(1.78, 0.80, "可能发散，不是必然发散（Baird 反例是构造性的）",
            ha="center", fontsize=6.3, color=GREY)

    ax.text(1.78, 0.56, "任意去掉一项，风险即可避免：", ha="center",
            fontsize=6.8, color=INK)
    triples = [("表格 TD", "无函数逼近"), ("蒙特卡洛", "无自举"),
               ("on-policy TD", "无离策略")]
    for (lab, note), x in zip(triples, xs):
        figkit.box(ax, (x, 0.02), 0.94, 0.40, f"{lab}\n{note}", fc="#e8f0e4",
                   ec="#7d9b6a", fs=6.4)

    return figkit.save(fig, "ch04_f01_triad")


# --------------------------------------------------------------------------
# f02: value-function geometry, VE / BE / PBE optima
# --------------------------------------------------------------------------

def f02_geometry():
    fig, ax = figkit.new(3.45, 2.10)
    figkit.blank(ax, (-0.10, 3.45), (-0.05, 2.20))

    plane = np.array([[0.45, 0.95], [2.30, 0.62], [3.05, 1.14], [1.20, 1.47]])
    ax.add_patch(Polygon(plane, closed=True, facecolor="#eef3fb",
                         edgecolor="#7d93b2", linewidth=0.7))
    ax.text(1.75, 0.40, "可表示空间 $\\{\\Phi\\theta\\}$（线性函数空间）",
            ha="center", fontsize=6.6, color="#4b6b93")

    # v^pi and its projection: the VE-minimising point
    ax.plot([1.45], [2.00], marker="o", markersize=3.0, color=C1)
    ax.text(1.45, 2.08, "$v^\\pi$", ha="center", fontsize=7.4, color=C1)
    ax.plot([1.45, 1.45], [1.95, 0.92], linestyle=(0, (3, 2)), linewidth=0.7,
            color=GREY)
    ax.text(1.52, 1.30, "$\\Pi_D$", fontsize=6.6, color=GREY)
    ax.plot([1.45], [0.92], marker="o", markersize=3.0, color=C1)
    ax.text(1.36, 0.86, "$\\Pi_D v^\\pi$", ha="right", fontsize=6.6, color=C1)
    ax.text(1.45, 0.72, "VE 最小", ha="center", fontsize=6.6, color=C1)

    # BE-minimising point: on the plane, but not the projection of anything above it
    ax.plot([0.90], [1.20], marker="o", markersize=3.0, color=C2)
    ax.text(0.90, 1.06, "BE 最小", ha="center", fontsize=6.6, color=C2)

    # T^pi v_theta, its perpendicular drop, and the fixed point of projected dynamics
    ax.plot([2.10], [0.95], marker="o", markersize=2.4, color=C0)
    ax.text(2.10, 0.80, "$v_\\theta$", ha="center", fontsize=6.6, color=C0)
    ax.annotate("", xy=(2.38, 1.80), xytext=(2.12, 0.97),
                arrowprops=dict(arrowstyle="-|>", color=C3, linewidth=0.9,
                                shrinkA=0, shrinkB=0))
    ax.text(2.46, 1.88, "$T^\\pi v_\\theta$", ha="left", fontsize=6.8,
            color=C3)
    ax.plot([2.38, 2.38], [1.78, 1.04], linestyle=(0, (3, 2)), linewidth=0.7,
            color=C3)
    ax.plot([2.38], [1.04], marker="o", markersize=3.0, color=C0)
    ax.text(2.46, 1.50, "$\\Pi_D T^\\pi$", ha="left", fontsize=6.6, color=C3)
    ax.text(2.46, 0.92, "$v_{\\theta^*}$：PBE$=0$", ha="left", fontsize=6.6,
            color=C0)

    ax.text(1.70, 0.14, "三个最优点一般不同；$\\Pi_D$ 只对线性函数空间有定义",
            ha="center", fontsize=6.6, color=GREY)

    return figkit.save(fig, "ch04_f02_geometry")


# --------------------------------------------------------------------------
# experiment 1: TD(0) vs LSTD on the 19-state random walk
# --------------------------------------------------------------------------

EXP1_DS = (2, 3, 4, 6, 8, 10)
EXP1_N = 3000
EXP1_ALPHA = 0.05
EXP1_SEEDS = 20


def experiment1():
    n = N_WALK
    P, r = walk_model(n)
    v_true = true_values(P, r)
    rho0 = np.full(n, 1.0 / n)
    mu = visit_distribution(P, rho0)

    rows, store = [], {}
    for d in EXP1_DS:
        Phi = legendre_features(n, d)
        C = Phi.T @ np.diag(mu) @ Phi
        th_td, A, b = td_fixed_point(Phi, P, r, mu)
        th_ve = best_projection(Phi, v_true, mu)
        ve_td_exact = ve(th_td, Phi, v_true, mu)
        ve_best = ve(th_ve, Phi, v_true, mu)
        td_runs, ls_runs = [], []
        for seed in range(EXP1_SEEDS):
            rng = np.random.default_rng(1000 + seed)
            td_runs.append(ve(run_td(Phi, P, r, EXP1_N, EXP1_ALPHA, rng, rho0)[0],
                              Phi, v_true, mu))
            rng = np.random.default_rng(2000 + seed)
            ls_runs.append(ve(run_lstd(Phi, P, r, EXP1_N, rng, rho0),
                              Phi, v_true, mu))
        td_runs, ls_runs = np.array(td_runs), np.array(ls_runs)
        store[d] = (td_runs, ls_runs, ve_best, ve_td_exact)
        rows.append((d, np.linalg.cond(C), ve_best, ve_td_exact,
                     td_runs.mean(), td_runs.std(), ls_runs.mean(), ls_runs.std()))

    d0 = 6
    Phi0 = legendre_features(n, d0)
    th_td0, A0, _ = td_fixed_point(Phi0, P, r, mu)
    sweep = []
    for m in (200, 500, 1500, 5000, 20000):
        tds, lss = [], []
        for seed in range(EXP1_SEEDS):
            rng = np.random.default_rng(3000 + seed)
            tds.append(ve(run_td(Phi0, P, r, m, EXP1_ALPHA, rng, rho0)[0], Phi0,
                          v_true, mu))
            rng = np.random.default_rng(4000 + seed)
            lss.append(ve(run_lstd(Phi0, P, r, m, rng, rho0), Phi0, v_true, mu))
        sweep.append((m, float(np.mean(tds)), float(np.std(tds)),
                      float(np.mean(lss)), float(np.std(lss))))

    ev = np.linalg.eigvals(A0)
    print("\n[实验 1] 19 状态随机游走, gamma=0.99, mu=访问分布, "
          f"n={EXP1_N}, alpha={EXP1_ALPHA}, {EXP1_SEEDS} 种子")
    print("   d  cond(C)   VE(最优投影)  VE(TD不动点)   TD均值      TD标准差"
          "    LSTD均值    LSTD标准差")
    for row in rows:
        print(f"  {row[0]:2d} {row[1]:9.1f}  {row[2]:.3e}    {row[3]:.3e}"
              f"   {row[4]:.3e}  {row[5]:.2e}   {row[6]:.3e}  {row[7]:.2e}")
    print("   1/(1-gamma) =", round(1.0 / (1.0 - GAMMA), 1),
          "| d=6 时 A 的最小/最大特征值:",
          f"{np.min(np.real(ev)):.4f} / {np.max(np.abs(ev)):.4f}")
    print("  样本量扫描 (d=6):      n        TD          LSTD")
    for m, a, sa, b_, sb in sweep:
        print(f"                    {m:6d}  {a:.3e}  {b_:.3e}")
    print("  mu 首/末三个分量:", np.round(mu[:3], 4), np.round(mu[-3:], 4))
    print("  v^pi 在 1/5/10/15/19 处:", np.round(v_true[[0, 4, 9, 14, 18]], 4))
    return store, sweep, mu, v_true


# --------------------------------------------------------------------------
# f03: experiment 1 drawn
# --------------------------------------------------------------------------

def f03_td_vs_lstd(store, sweep):
    fig, axes = figkit.new(4.40, 1.95, ncols=2)

    ax = axes[0]
    ds = list(EXP1_DS)
    ax.errorbar(ds, [store[d][0].mean() for d in ds],
                yerr=[store[d][0].std() for d in ds], color=C1, marker="o",
                label="半梯度 TD(0)", capsize=1.8, elinewidth=0.6)
    ax.errorbar(ds, [store[d][1].mean() for d in ds],
                yerr=[store[d][1].std() for d in ds], color=C0, marker="s",
                label="LSTD", capsize=1.8, elinewidth=0.6)
    ax.plot(ds, [store[d][2] for d in ds], color=C3, linestyle=(0, (4, 2)),
            linewidth=0.9, label="最优投影 $\\Pi_D v^\\pi$")
    ax.set_yscale("log")
    ax.set_ylim(5e-6, 3e-1)
    ax.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1])
    ax.set_yticklabels(["1e-5", "1e-4", "1e-3", "1e-2", "1e-1"])
    ax.set_xticks(list(EXP1_DS))
    ax.set_xlabel("特征数 $d$")
    ax.set_ylabel("$\\|V_\\theta-V^\\pi\\|_\\mu$")
    ax.legend(loc="upper right", fontsize=5.8, handlelength=1.5)
    ax.set_title(f"$n={EXP1_N}$，{EXP1_SEEDS} 个种子", fontsize=7.2)

    ax = axes[1]
    ms = [s[0] for s in sweep]
    ax.plot(ms, [s[1] for s in sweep], color=C1, marker="o", label="半梯度 TD(0)")
    ax.plot(ms, [s[3] for s in sweep], color=C0, marker="s", label="LSTD")
    ax.axhline(store[6][2], color=C3, linestyle=(0, (4, 2)), linewidth=0.9,
               label="最优投影（$2.9\\times10^{-5}$）")
    ax.annotate("TD 的地板由 $\\alpha$ 决定", xy=(6000, 0.048), xytext=(700, 0.9),
                fontsize=6.0, color=C1,
                arrowprops=dict(arrowstyle="-|>", color=C1, linewidth=0.6))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(150, 3e4)
    ax.set_ylim(1e-5, 3e0)
    ax.set_xticks([200, 1000, 5000, 20000])
    ax.set_xticklabels(["200", "1e3", "5e3", "2e4"])
    ax.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0])
    ax.set_yticklabels(["1e-5", "1e-4", "1e-3", "1e-2", "1e-1", "1"])
    ax.set_xlabel("样本量")
    ax.set_ylabel("$\\|V_\\theta-V^\\pi\\|_\\mu$")
    ax.legend(loc="lower left", fontsize=5.8, handlelength=1.5)
    ax.set_title("$d=6$：数据效率与步长地板", fontsize=7.2)

    return figkit.save(fig, "ch04_f03_td_vs_lstd")


# --------------------------------------------------------------------------
# experiment 2a: Baird's counterexample
# --------------------------------------------------------------------------

def baird_setup(gamma=0.99):
    """7 states, 2 actions, 8 weights, exactly as in Sutton & Barto Fig 11.1."""
    n, d = 7, 8
    Phi = np.zeros((n, d))
    for i in range(6):
        Phi[i, i] = 2.0
        Phi[i, 7] = 1.0
    Phi[6, 6] = 1.0
    Phi[6, 7] = 2.0
    dashed_next = np.full(n, -1)          # uniform over the six upper states
    solid_next = np.full(n, 6)            # the seventh state
    return Phi, dashed_next, solid_next, 6.0 / 7.0, gamma


def baird_run(steps, alpha, seed, on_policy, gamma=0.99):
    """Return ||w_t||_2 over time and the final weights."""
    Phi, dashed_next, solid_next, b_dashed, gamma = baird_setup(gamma)
    rng = np.random.default_rng(seed)
    w = np.array([1, 1, 1, 1, 1, 1, 10, 1], dtype=float)
    s = int(rng.integers(0, 7))
    norms = np.empty(steps)
    for t in range(steps):
        if on_policy:                      # pi always takes the solid action
            rho, nxt = 1.0, solid_next[s]
        else:
            if rng.random() < 1.0 - b_dashed:      # solid
                rho, nxt = 7.0, solid_next[s]
            else:                                  # dashed, pi would not
                rho, nxt = 0.0, int(rng.integers(0, 6))
        delta = gamma * (Phi[nxt] @ w) - (Phi[s] @ w)
        w = w + alpha * rho * delta * Phi[s]
        s = nxt
        norms[t] = np.linalg.norm(w)
    return norms, w


def experiment2a():
    steps, alpha = 3000, 0.01
    alphas = (0.005, 0.01, 0.02)
    curves = {a: baird_run(steps, a, 900 + int(a * 1e5), False)[0] for a in alphas}
    on = baird_run(steps, alpha, 700, True)
    off_multi = [baird_run(steps, alpha, 500 + k, False)[0] for k in range(3)]

    Phi, *_ = baird_setup()
    print("\n[实验 2a] Baird 反例：7 状态 2 动作, gamma=0.99, 8 个权重, "
          f"w0=(1,1,1,1,1,1,10,1), steps={steps}")
    for a in alphas:
        c = curves[a]
        print(f"   alpha={a:<6} ||w|| @200/1000/3000 = {c[199]:.3e} / "
              f"{c[999]:.3e} / {c[-1]:.3e}")
    print(f"   on-policy ||w|| @200/1000/3000 = {on[0][199]:.3f} / "
          f"{on[0][999]:.3f} / {on[0][-1]:.3f}")
    print(f"   on-policy 最终 v_hat = {np.round(Phi @ on[1], 3)}")
    print(f"   off-policy 三种子 ||w||@3000 = {[f'{c[-1]:.1e}' for c in off_multi]}")
    print(f"   off-policy ||w|| 首次超过 1e3 的步数: "
          f"{[int(np.argmax(c > 1e3)) + 1 for c in off_multi]}")
    return curves, on, alphas


def f04_baird(curves, on, alphas):
    fig, axes = figkit.new(4.40, 1.95, ncols=2)
    t = np.arange(1, len(on[0]) + 1)

    ax = axes[0]
    ax.plot(t, on[0], color=C3, label="on-policy 采样")
    ax.plot(t, curves[0.01], color=C1, label="off-policy 采样")
    ax.set_yscale("log")
    ax.set_ylim(5e-1, 1e8)
    ax.set_yticks([1e0, 1e2, 1e4, 1e6, 1e8])
    ax.set_yticklabels(["1", "1e2", "1e4", "1e6", "1e8"])
    ax.set_xlabel("更新步数 $t$")
    ax.set_ylabel("$\\|w_t\\|_2$")
    ax.legend(loc="lower left", fontsize=6.2)
    ax.set_title("同一更新式，只改采样分布（$\\alpha=0.01$）", fontsize=7.0)

    ax = axes[1]
    for a, col in zip(alphas, (C0, C2, C1)):
        ax.plot(t, curves[a], color=col, label=f"$\\alpha={a}$")
    ax.set_yscale("log")
    ax.set_ylim(5e-1, 1e8)
    ax.set_yticks([1e0, 1e2, 1e4, 1e6, 1e8])
    ax.set_yticklabels(["1", "1e2", "1e4", "1e6", "1e8"])
    ax.set_xlabel("更新步数 $t$")
    ax.set_ylabel("$\\|w_t\\|_2$")
    ax.legend(loc="lower right", fontsize=6.2)
    ax.set_title("发散与步长无关，只改发散速度", fontsize=7.0)

    return figkit.save(fig, "ch04_f04_baird")


# --------------------------------------------------------------------------
# experiment 2b: on-policy vs off-policy fixed point and its variance
# --------------------------------------------------------------------------

P2 = 0.80      # P(right | target)
B2 = 0.50      # P(right | behaviour)
EXP2B_N = 5000
EXP2B_SEEDS = 20
EXP2B_ALPHA = 0.05


def experiment2b():
    n, gamma = N_WALK, GAMMA
    P_pi, r_pi = walk_model(n, gamma, P2)
    P_b, _ = walk_model(n, gamma, B2)
    v_true = true_values(P_pi, r_pi)
    rho0 = np.full(n, 1.0 / n)
    mu_pi = visit_distribution(P_pi, rho0)
    mu_b = visit_distribution(P_b, rho0)

    d = 6
    Phi = legendre_features(n, d)
    th_on, A_on, _ = td_fixed_point(Phi, P_pi, r_pi, mu_pi)
    th_off, A_off, _ = td_fixed_point(Phi, P_pi, r_pi, mu_b)
    ev_on, ev_off = np.linalg.eigvals(A_on), np.linalg.eigvals(A_off)

    marks = [250, 500, 1000, 2000, 3500, 5000]
    on_runs, off_runs, on_cur, off_cur = [], [], {}, {}
    for seed in range(EXP2B_SEEDS):
        rng = np.random.default_rng(6000 + seed)
        th, snaps = run_td(Phi, P_pi, r_pi, EXP2B_N, EXP2B_ALPHA, rng, rho0,
                           snaps=marks)
        on_runs.append(ve(th, Phi, v_true, mu_pi))
        for k, tk in snaps:
            on_cur.setdefault(k, []).append(ve(tk, Phi, v_true, mu_pi))
        rng = np.random.default_rng(7000 + seed)
        th, snaps = run_td_is(Phi, P_b, EXP2B_N, EXP2B_ALPHA, rng, rho0,
                              (1.0 - P2, P2), (1.0 - B2, B2), snaps=marks)
        off_runs.append(ve(th, Phi, v_true, mu_pi))
        for k, tk in snaps:
            off_cur.setdefault(k, []).append(ve(tk, Phi, v_true, mu_pi))
    on_runs, off_runs = np.array(on_runs), np.array(off_runs)

    ve_best = ve(best_projection(Phi, v_true, mu_pi), Phi, v_true, mu_pi)
    print("\n[实验 2b] 19 状态双动作链, gamma=0.99, d=6, "
          f"pi(right)={P2}, b(right)={B2}, n={EXP2B_N}, "
          f"{EXP2B_SEEDS} 种子, alpha={EXP2B_ALPHA}")
    print(f"   on-policy  不动点 VE = {ve(th_on, Phi, v_true, mu_pi):.4e}")
    print(f"   off-policy 不动点 VE = {ve(th_off, Phi, v_true, mu_pi):.4e}")
    print(f"   最优投影          VE = {ve_best:.4e}")
    print(f"   A_on  特征值 [{np.min(np.real(ev_on)):.3f}, "
          f"{np.max(np.real(ev_on)):.3f}], |Im|max={np.max(np.abs(np.imag(ev_on))):.3f}")
    print(f"   A_off 特征值 [{np.min(np.real(ev_off)):.3f}, "
          f"{np.max(np.real(ev_off)):.3f}], |Im|max={np.max(np.abs(np.imag(ev_off))):.3f}")
    print(f"   on-policy  {EXP2B_SEEDS} 种子 VE: 均值 {on_runs.mean():.4e} "
          f"标准差 {on_runs.std():.4e} 最大 {on_runs.max():.4e}")
    print(f"   off-policy {EXP2B_SEEDS} 种子 VE: 均值 {off_runs.mean():.4e} "
          f"标准差 {off_runs.std():.4e} 最大 {off_runs.max():.4e}")
    print(f"   mu_pi 与 mu_b 的 TV 距离: {0.5 * np.abs(mu_pi - mu_b).sum():.4f}")
    print("   学习曲线 (步数: on均值±标准差 / off均值±标准差)")
    for k in marks:
        a = np.array(on_cur[k])
        b_ = np.array(off_cur[k])
        print(f"     {k:5d}: {a.mean():.3e}±{a.std():.2e} / "
              f"{b_.mean():.3e}±{b_.std():.2e}")
    return on_runs, off_runs, (marks, on_cur, off_cur)


def f05_bias_variance(on_runs, off_runs, curves):
    marks, on_cur, off_cur = curves
    fig, axes = figkit.new(4.40, 1.90, ncols=2)

    ax = axes[0]
    rng = np.random.default_rng(0)
    for col, lab, xc, runs in ((C3, "on-policy", 1, on_runs),
                               (C1, "off-policy", 2, off_runs)):
        jit = rng.uniform(-0.10, 0.10, runs.size)
        ax.plot(xc + jit, runs, linestyle="none", marker="o", markersize=2.3,
                markerfacecolor="none", markeredgecolor=col, markeredgewidth=0.7)
        ax.plot([xc - 0.25, xc + 0.25], [runs.mean()] * 2, color=col, linewidth=1.4)
    ax.set_yscale("log")
    ax.set_xlim(0.45, 2.55)
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["on-policy", "off-policy"])
    ax.set_yticks([1e-3, 1e-2, 1e-1, 1.0])
    ax.set_yticklabels(["1e-3", "1e-2", "1e-1", "1"])
    ax.set_ylabel("最终 $\\|V_\\theta-V^\\pi\\|_\\mu$")
    ax.set_title(f"{on_runs.size} 个种子的最终误差", fontsize=7.2)

    ax = axes[1]
    for col, lab, cur in ((C3, "on-policy", on_cur), (C1, "off-policy", off_cur)):
        m = np.array([np.mean(cur[k]) for k in marks])
        s = np.array([np.std(cur[k]) for k in marks])
        ax.plot(marks, m, color=col, marker="o", label=lab)
        ax.plot(marks, np.maximum(m - s, 1e-4), color=col, linewidth=0.6,
                linestyle=(0, (3, 2)))
        ax.plot(marks, m + s, color=col, linewidth=0.6, linestyle=(0, (3, 2)))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(200, 6000)
    ax.set_ylim(1e-3, 3e0)
    ax.set_xticks([250, 1000, 5000])
    ax.set_xticklabels(["250", "1e3", "5e3"])
    ax.set_yticks([3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0])
    ax.set_yticklabels(["3e-3", "1e-2", "3e-2", "1e-1", "3e-1", "1"])
    ax.set_xlabel("样本量")
    ax.set_ylabel("$\\|V_\\theta-V^\\pi\\|_\\mu$")
    ax.legend(loc="lower left", fontsize=6.2)
    ax.set_title("均值 $\\pm$ 一个标准差", fontsize=7.2)

    return figkit.save(fig, "ch04_f05_bias_variance")


# --------------------------------------------------------------------------

def main() -> int:
    figkit.setup()
    f01_triad()
    f02_geometry()
    store, sweep, mu, v_true = experiment1()
    f03_td_vs_lstd(store, sweep)
    curves, on, alphas = experiment2a()
    f04_baird(curves, on, alphas)
    on_runs, off_runs, curves2 = experiment2b()
    f05_bias_variance(on_runs, off_runs, curves2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
