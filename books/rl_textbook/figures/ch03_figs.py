"""Figures for chapter 3 (动态规划、蒙特卡洛与时序差分).

Run from the build directory:

    python figures\\ch03_figs.py

Every figure is vector SVG written into ``figures/out``.  f02--f05 are *computed*
experiments, not sketches: the parameters, seeds and episode counts printed at the
end of the run are the numbers quoted in the chapter text and its captions.

    f01  two routes: model-based DP, and sampling-based MC / TD      (schematic)
    f02  one GPI family: value iteration / truncated / full policy
         evaluation on a random MDP                                 (real)
    f03  19-state random walk: MC vs TD(0) RMSE learning curves      (real)
    f04  19-state random walk: RMSE vs lambda, three step sizes      (real)
    f05  5x5 cliff task: SARSA vs Q-learning                        (real)
"""

from __future__ import annotations

import os
import sys

import numpy as np

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUILD_DIR)

import figkit  # noqa: E402
from figkit import C0, C1, C2, C3, C4, GREY, INK  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

# --------------------------------------------------------------------------
# shared experiment settings (quoted verbatim in the chapter captions)
N_SEEDS = 100
N_EPISODES = 100
RW_STATES = 19
RW_TRUE = np.arange(1, RW_STATES + 1) / (RW_STATES + 1)   # 1/6 .. 5/6
RW_INIT = 0.0                       # V_0 = 0: no prior knowledge
ALPHA_MC = 0.02
ALPHA_TD = 0.30
LAMBDAS = np.round(np.linspace(0.0, 1.0, 11), 2)
ALPHA_SET = (0.10, 0.20, 0.30)

CLIFF_SEEDS = 20
CLIFF_EPISODES = 500
CLIFF_EPS = 0.10
CLIFF_ALPHA = 0.50
CLIFF_GAMMA = 1.0


# --------------------------------------------------------------------------
# f01: the two routes into the same Bellman equation
def f01_two_routes():
    fig, axes = figkit.new(4.55, 1.95, ncols=2)

    ax = axes[0]
    figkit.blank(ax, (-0.10, 3.05), (-0.35, 3.05))
    ax.text(1.05, 2.86, "有模型：动态规划", ha="center", fontsize=7.4, color=INK)
    figkit.box(ax, (0.28, 1.62), 1.55, 0.56, "策略评估\n$V\\leftarrow T^{\\pi}V$",
               fs=7.0, fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (0.28, 0.62), 1.55, 0.56, "策略改进\n$\\pi\\leftarrow\\mathrm{greedy}(Q)$",
               fs=7.0, fc="#e8f0e4", ec="#7d9b6a")
    figkit.arrow(ax, (1.52, 1.55), (1.52, 1.24), color=INK)
    figkit.arrow(ax, (0.60, 1.24), (0.60, 1.55), color=INK)
    ax.text(1.60, 1.39, "$V^{\\pi}$", fontsize=6.8, color=INK, ha="left")
    ax.text(0.50, 1.39, "$\\pi$", fontsize=6.8, color=INK, ha="right")
    ax.text(1.05, 0.16, "期望对已知的 $P$ 求和", ha="center", fontsize=6.6, color=GREY)

    ax = axes[1]
    figkit.blank(ax, (-0.10, 3.15), (-0.35, 3.05))
    ax.text(1.45, 2.86, "无模型：采样估计", ha="center", fontsize=7.4, color=INK)
    figkit.box(ax, (0.10, 1.74), 1.62, 0.52, "MC\n整条回报 $G_t$",
               fs=6.6, fc="#fdf1d8", ec="#c9a227")
    figkit.box(ax, (0.10, 1.00), 1.62, 0.52, "TD\n一步目标 $R+\\gamma V(S')$",
               fs=6.4, fc="#f7eef3", ec="#a06b8a")
    figkit.box(ax, (0.10, 0.14), 2.92, 0.50, "同一个贝尔曼方程，换掉右端的期望",
               fs=6.8, fc="#eef3fb", ec="#7d93b2")
    figkit.arrow(ax, (0.60, 1.72), (0.60, 1.54), color=GREY)
    ax.text(0.68, 1.63, "自举", fontsize=6.2, color=GREY, ha="left", va="center")
    figkit.arrow(ax, (0.90, 0.98), (0.90, 0.64), color=GREY)
    ax.text(1.86, 1.24, "偏差偏高\n方差偏低", fontsize=6.1, color=GREY, ha="left",
            va="center")

    return figkit.save(fig, "ch03_f01_two_routes")


# --------------------------------------------------------------------------
# f02: one family -- value iteration, truncated evaluation, full evaluation
def _random_mdp(n_states: int, n_actions: int, seed: int = 7):
    rng = np.random.default_rng(seed)
    P = rng.random((n_states, n_actions, n_states)) ** 3
    P /= P.sum(axis=2, keepdims=True)
    R = rng.uniform(-1.0, 1.0, (n_states, n_actions))
    return P, R


def _vi_synchronous(P, R, gamma, tol=1e-13, max_iter=20000):
    n = R.shape[0]
    V = np.zeros(n)
    hist = []
    for _ in range(max_iter):
        V_new = (R + gamma * P @ V).max(axis=1)
        hist.append(V_new.copy())
        hit = np.max(np.abs(V_new - V)) < tol
        V = V_new
        if hit:
            break
    return hist


def _vi_star(P, R, gamma):
    return _vi_synchronous(P, R, gamma)[-1]


def _gpi(P, R, gamma, V_star, n_sweeps=None, eval_tol=1e-8,
         max_rounds=400, target=1e-9):
    """GPI with `n_sweeps` in-place evaluation sweeps per improvement step.

    n_sweeps=1 is value iteration (one Gauss-Seidel sweep = one backup round);
    n_sweeps=None evaluates each policy to `eval_tol` (full policy iteration).
    """
    n, n_actions = R.shape
    rng = np.random.default_rng(3)
    pi = rng.integers(0, n_actions, n)
    V = np.zeros(n)
    backups = 0
    rounds, errs, works = [], [], []
    for r in range(max_rounds):
        Ppi = P[np.arange(n), pi]
        Rpi = R[np.arange(n), pi]
        sweeps = 0
        while True:
            delta = 0.0
            for s in range(n):
                v = Rpi[s] + gamma * (Ppi[s] @ V)
                delta = max(delta, abs(v - V[s]))
                V[s] = v
            sweeps += 1
            if n_sweeps is not None:
                if sweeps >= n_sweeps:
                    break
            elif delta < eval_tol:
                break
        backups += sweeps * n
        err = max(np.max(np.abs(V - V_star)), 1e-15)
        rounds.append(r + 1)
        errs.append(err)
        works.append(backups)
        new_pi = (R + gamma * P @ V).argmax(axis=1)
        improved = not np.array_equal(new_pi, pi)
        pi = new_pi
        if err <= target or (n_sweeps is None and not improved):
            break
    return rounds, errs, works


def f02_dp_comparison():
    gamma = 0.9
    n_states, n_actions = 40, 4
    P, R = _random_mdp(n_states, n_actions)
    hist = _vi_synchronous(P, R, gamma)
    V_star = hist[-1]
    sync_err = [np.max(np.abs(V - V_star)) for V in hist]
    sync_rounds = next(k + 1 for k, e in enumerate(sync_err) if e <= 1e-6)

    curves = {}
    for label, m in (("m=1（值迭代）", 1), ("m=5", 5), ("$m=\\infty$（完整评估）", None)):
        curves[label] = _gpi(P, R, gamma, V_star, n_sweeps=m)

    fig, axes = figkit.new(4.55, 1.95, ncols=2)
    colors = {list(curves)[0]: C0, list(curves)[1]: C2, list(curves)[2]: C1}

    ax = axes[0]
    for label, (rounds, errs, _) in curves.items():
        ax.semilogy(rounds, errs, color=colors[label], marker="o", markersize=1.7,
                    label=label)
    ax.axhline(1e-6, color=GREY, linewidth=0.8, linestyle=(0, (4, 2)))
    ax.text(104, 2.0e-6, "误差 $10^{-6}$", fontsize=6.0, color=GREY, va="bottom",
            ha="right")
    ax.set_xlabel("轮数（每引入一个策略 = 一轮）")
    ax.set_ylabel("$\\|V_k-V^*\\|_\\infty$")
    ax.set_ylim(1e-12, 3)
    ax.set_yticks([1e-12, 1e-9, 1e-6, 1e-3, 1.0])
    ax.set_yticklabels(["1e-12", "1e-9", "1e-6", "1e-3", "1"])
    ax.legend(loc="lower left", fontsize=5.9)
    ax.set_title("按轮数：$m$ 越大轮数越少", fontsize=7.6)

    ax = axes[1]
    for label, (_, errs, works) in curves.items():
        ax.loglog(works, errs, color=colors[label], marker="o", markersize=1.7,
                  label=label)
    ax.axhline(1e-6, color=GREY, linewidth=0.8, linestyle=(0, (4, 2)))
    ax.set_xlabel("累计状态备份次数")
    ax.set_ylabel("$\\|V_k-V^*\\|_\\infty$")
    ax.set_ylim(1e-12, 3)
    ax.set_yticks([1e-12, 1e-9, 1e-6, 1e-3, 1.0])
    ax.set_yticklabels(["1e-12", "1e-9", "1e-6", "1e-3", "1"])
    ax.set_xticks([1e3, 1e4])
    ax.set_xticklabels(["1e3", "1e4"])
    ax.legend(loc="lower left", fontsize=5.9)
    ax.set_title("按计算量：完整评估贵约三倍", fontsize=7.6)

    print(f"  [f02] |S|={n_states}, |A|={n_actions}, gamma={gamma}, seed=7, "
          f"initial policy seed=3")
    print(f"  [f02] synchronous VI: {len(hist)} iterations, "
          f"{sync_rounds} to reach 1e-6")
    for label, (rounds, errs, works) in curves.items():
        hit_r = next((r for r, e in zip(rounds, errs) if e <= 1e-6), None)
        hit_w = next((w for w, e in zip(works, errs) if e <= 1e-6), None)
        print(f"  [f02] {label:22s} rounds={len(rounds):4d} "
              f"first<=1e-6 at round {hit_r} with {hit_w} backups; "
              f"final err {errs[-1]:.2e}")
    return figkit.save(fig, "ch03_f02_dp_comparison")


# --------------------------------------------------------------------------
# 19-state random walk (shape of Sutton & Barto, example 6.2)
def _rw_episode(rng):
    """States 0..4, start at 2; reward +1 only when passing the right end."""
    s = RW_STATES // 2
    states, rewards = [], []
    while True:
        states.append(s)
        s += 1 if rng.random() < 0.5 else -1
        if s < 0:
            rewards.append(0.0)
            return states, rewards
        if s >= RW_STATES:
            rewards.append(1.0)
            return states, rewards
        rewards.append(0.0)


def _make_episodes(seeds, episodes):
    out = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        out.append([_rw_episode(rng) for _ in range(episodes)])
    return out


def _rmse(V):
    return float(np.sqrt(np.mean((V - RW_TRUE) ** 2)))


def _run_mc(runs, alpha):
    out = np.zeros((len(runs), len(runs[0])))
    for i, run in enumerate(runs):
        V = np.full(RW_STATES, RW_INIT)
        for j, (states, rewards) in enumerate(run):
            G = 0.0
            for t in range(len(states) - 1, -1, -1):
                G += rewards[t]
                V[states[t]] += alpha * (G - V[states[t]])
            out[i, j] = _rmse(V)
    return out


def _run_td0(runs, alpha):
    out = np.zeros((len(runs), len(runs[0])))
    for i, run in enumerate(runs):
        V = np.full(RW_STATES, RW_INIT)
        for j, (states, rewards) in enumerate(run):
            for t in range(len(states)):
                s = states[t]
                v_next = 0.0 if t + 1 >= len(states) else V[states[t + 1]]
                V[s] += alpha * (rewards[t] + v_next - V[s])
            out[i, j] = _rmse(V)
    return out


def _lam_targets(V, states, rewards, lam):
    """Offline lambda-return targets, O(T) backward recursion (gamma = 1).

    G^lam_t = R_{t+1} + gamma[(1-lam) V(S_{t+1}) + lam G^lam_{t+1}],
    with V(terminal) = 0; lam = 1 gives the Monte-Carlo return exactly.
    """
    T = len(states)
    out = np.zeros(T)
    g = 0.0
    for t in range(T - 1, -1, -1):
        v_next = V[states[t + 1]] if t + 1 < T else 0.0
        g = rewards[t] + (1.0 - lam) * v_next + lam * g
        out[t] = g
    return out


def _run_lambda(runs, alpha, lam):
    out = np.zeros((len(runs), len(runs[0])))
    for i, run in enumerate(runs):
        V = np.full(RW_STATES, RW_INIT)
        for j, (states, rewards) in enumerate(run):
            targets = _lam_targets(V, states, rewards, lam)
            for t, s in enumerate(states):
                V[s] += alpha * (targets[t] - V[s])
            out[i, j] = _rmse(V)
    return out


def _curve_stats(curves):
    mean = curves.mean(axis=0)
    sd = curves.std(axis=0, ddof=1)
    return mean, sd, sd / np.sqrt(curves.shape[0])


def f03_mc_vs_td():
    runs = _make_episodes(range(N_SEEDS), N_EPISODES)
    mc = _run_mc(runs, ALPHA_MC)
    td = _run_td0(runs, ALPHA_TD)
    mc_m, mc_sd, mc_se = _curve_stats(mc)
    td_m, td_sd, td_se = _curve_stats(td)

    fig, ax = figkit.new(3.55, 2.05)
    ep = np.arange(1, N_EPISODES + 1)
    ax.plot(ep, mc_m, color=C1, label=f"MC，$\\alpha$={ALPHA_MC}")
    ax.plot(ep, td_m, color=C0, label=f"TD(0)，$\\alpha$={ALPHA_TD}")
    ax.set_xlabel("回合数")
    ax.set_ylabel("19 个状态的 RMSE")
    ax.set_xlim(0, N_EPISODES)
    ax.set_yscale("log")
    ax.set_ylim(0.055, 0.80)
    ax.set_yticks([0.06, 0.1, 0.2, 0.4, 0.7])
    ax.set_yticklabels(["0.06", "0.1", "0.2", "0.4", "0.7"])
    ax.legend(loc="lower left", fontsize=6.6)
    ax.set_title(f"{N_SEEDS} 个种子的平均，$V_0=0$", fontsize=7.4)

    print(f"  [f03] 19-state walk, V_0=0, {N_SEEDS} seeds x {N_EPISODES} episodes, "
          f"gamma=1")
    print(f"  [f03] RMSE after {N_EPISODES} episodes: MC {mc_m[-1]:.3f} "
          f"(sd {mc_sd[-1]:.4f}, se {mc_se[-1]:.4f}), TD(0) {td_m[-1]:.3f} "
          f"(sd {td_sd[-1]:.4f}, se {td_se[-1]:.4f})")
    print(f"  [f03] RMSE at episode 10: MC {mc_m[9]:.3f}, TD(0) {td_m[9]:.3f}")
    return figkit.save(fig, "ch03_f03_mc_vs_td")


def f04_lambda_sweep():
    runs = _make_episodes(range(N_SEEDS), N_EPISODES)
    data = {a: {l: _run_lambda(runs, a, l) for l in LAMBDAS} for a in ALPHA_SET}
    marks = ("o", "s", "^")
    colors = (C0, C2, C1)

    fig, ax = figkit.new(3.55, 2.05)
    for a, color, mk in zip(ALPHA_SET, colors, marks):
        mean = [data[a][l][:, -1].mean() for l in LAMBDAS]
        ax.plot(LAMBDAS, mean, color=color, marker=mk, markersize=2.6,
                label=f"$\\alpha$={a}")
        i = int(np.argmin(mean))
        ax.plot([LAMBDAS[i]], [mean[i]], marker=mk, markersize=4.6,
                markerfacecolor="none", markeredgecolor=color, markeredgewidth=0.9)
    ax.set_xlabel("$\\lambda$")
    ax.set_ylabel(f"{N_EPISODES} 回合后的 RMSE")
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_xticklabels(["0", "0.2", "0.4", "0.6", "0.8", "1"])
    ax.set_ylim(0.055, 0.375)
    ax.legend(loc="upper center", fontsize=6.4, ncol=3, columnspacing=0.9)
    ax.set_title("空心圈为每条曲线的极小点", fontsize=7.4)

    print(f"  [f04] 19-state walk, V_0=0, {N_SEEDS} seeds x {N_EPISODES} episodes, "
          f"offline lambda-return, gamma=1")
    for a in ALPHA_SET:
        row = [data[a][l][:, -1].mean() for l in LAMBDAS]
        i = int(np.argmin(row))
        print(f"  [f04] alpha={a:4.2f}: argmin lam={LAMBDAS[i]:.2f} "
              f"({row[i]:.4f}); lam=0 {row[0]:.4f}; lam=1 {row[-1]:.4f} | "
              + " ".join(f"{v:.3f}" for v in row))
    return figkit.save(fig, "ch03_f04_lambda_sweep")


# --------------------------------------------------------------------------
# f05: 5x5 cliff task, SARSA vs Q-learning
CLIFF_CELLS = {(4, 1), (4, 2), (4, 3)}
CLIFF_START = (4, 0)
CLIFF_GOAL = (4, 4)
ACTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _cliff_step(state, a):
    dr, dc = ACTIONS[a]
    nr, nc = state[0] + dr, state[1] + dc
    if not (0 <= nr < 5 and 0 <= nc < 5):
        return state, -1.0, False
    if (nr, nc) in CLIFF_CELLS:
        return CLIFF_START, -100.0, False
    if (nr, nc) == CLIFF_GOAL:
        return CLIFF_GOAL, -1.0, True
    return (nr, nc), -1.0, False


def _eps_greedy(rng, q, state, eps):
    if rng.random() < eps:
        return int(rng.integers(0, 4))
    row = q[state[0], state[1]]
    best = np.flatnonzero(row == row.max())
    return int(best[rng.integers(0, len(best))])


def _run_cliff(on_policy: bool):
    returns = np.zeros((CLIFF_SEEDS, CLIFF_EPISODES))
    falls = np.zeros((CLIFF_SEEDS, CLIFF_EPISODES))
    final_q = []
    for i in range(CLIFF_SEEDS):
        rng = np.random.default_rng(1000 + i)
        q = np.zeros((5, 5, 4))
        for ep in range(CLIFF_EPISODES):
            s = CLIFF_START
            a = _eps_greedy(rng, q, s, CLIFF_EPS)
            total, fell = 0.0, 0
            for _ in range(200):
                s2, r, done = _cliff_step(s, a)
                total += r
                if r <= -100.0:
                    fell += 1
                if on_policy:
                    a2 = _eps_greedy(rng, q, s2, CLIFF_EPS)
                    target = r + CLIFF_GAMMA * q[s2[0], s2[1], a2]
                else:
                    target = r + CLIFF_GAMMA * q[s2[0], s2[1]].max()
                    a2 = None
                q[s[0], s[1], a] += CLIFF_ALPHA * (target - q[s[0], s[1], a])
                if done:
                    break
                s = s2
                a = a2 if on_policy else _eps_greedy(rng, q, s, CLIFF_EPS)
            returns[i, ep] = total
            falls[i, ep] = fell
        final_q.append(q)
    return returns, falls, final_q


def _greedy_path(q):
    s = CLIFF_START
    path = [s]
    for _ in range(30):
        a = int(np.argmax(q[s[0], s[1]]))
        s2, _, done = _cliff_step(s, a)
        path.append(s2)
        if done or s2 == s:
            break
        s = s2
    return path


def f05_cliff():
    sar_ret, sar_fall, sar_q = _run_cliff(True)
    ql_ret, ql_fall, ql_q = _run_cliff(False)
    fig, axes = figkit.new(4.55, 2.05, ncols=2)

    ax = axes[0]
    ep = np.arange(1, CLIFF_EPISODES + 1)
    ax.plot(ep, np.cumsum(ql_fall.mean(axis=0)), color=C0, label="Q-learning")
    ax.plot(ep, np.cumsum(sar_fall.mean(axis=0)), color=C1, label="SARSA")
    ax.set_xlabel("回合数")
    ax.set_ylabel("累计掉崖次数")
    ax.set_ylim(0, 80)
    ax.set_yticks([0, 20, 40, 60, 80])
    ax.set_yticklabels(["0", "20", "40", "60", "80"])
    ax.legend(loc="upper left", fontsize=6.6)
    ax.set_title("训练期累计掉崖：相差约一倍", fontsize=7.6)

    ax = axes[1]
    figkit.blank(ax, (-0.2, 5.05), (-0.35, 5.35))
    for r in range(5):
        for c in range(5):
            if (r, c) in CLIFF_CELLS:
                fc, ec = "#fbe3e0", "#c0392b"
            elif (r, c) == CLIFF_GOAL:
                fc, ec = "#e8f0e4", "#4a7a3a"
            elif (r, c) == CLIFF_START:
                fc, ec = "#eef3fb", "#7d93b2"
            else:
                fc, ec = "#fbfbfc", "#c9ccd2"
            ax.add_patch(FancyBboxPatch((c + 0.06, 4 - r + 0.06), 0.88, 0.88,
                                        boxstyle="round,pad=0.004,rounding_size=0.03",
                                        linewidth=0.6, facecolor=fc, edgecolor=ec))
    ax.text(2.5, 0.5, "悬崖", ha="center", va="center", fontsize=6.6, color="#c0392b")
    ax.text(4.5, 0.80, "目标", ha="center", va="center", fontsize=6.2, color="#4a7a3a")
    ax.text(0.5, -0.18, "起点", ha="center", va="center", fontsize=6.0, color=GREY)

    def _draw(path, color, label, dy, lx, ly):
        xs = [c + 0.5 for r, c in path]
        ys = [4 - r + 0.5 + dy for r, c in path]
        ax.plot(xs, ys, color=color, linewidth=1.0, marker="o", markersize=1.9)
        ax.text(lx, ly, label, fontsize=5.9, color=color, ha="center", va="bottom",
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))

    sar_path, ql_path = _greedy_path(sar_q[-1]), _greedy_path(ql_q[-1])
    _draw(ql_path, C0, "Q-learning：最优", +0.14, 1.9, 1.66)
    _draw(sar_path, C1, "SARSA：保守", -0.14, 2.6, 4.98)
    ax.set_title("学到的贪婪路径", fontsize=7.6)

    print(f"  [f05] cliff: {CLIFF_SEEDS} seeds x {CLIFF_EPISODES} episodes, "
          f"eps={CLIFF_EPS}, alpha={CLIFF_ALPHA}, gamma={CLIFF_GAMMA}")
    print(f"  [f05] mean return last 100 episodes: Q-learning "
          f"{ql_ret[:, -100:].mean():.2f}, SARSA {sar_ret[:, -100:].mean():.2f}")
    print(f"  [f05] mean cliff falls per episode: Q-learning "
          f"{ql_fall.mean():.3f}, SARSA {sar_fall.mean():.3f}")
    print(f"  [f05] total cliff falls: Q-learning {ql_fall.sum():.0f}, "
          f"SARSA {sar_fall.sum():.0f}")
    print(f"  [f05] greedy path SARSA    : {sar_path}")
    print(f"  [f05] greedy path Q-learning: {ql_path}")
    return figkit.save(fig, "ch03_f05_cliff")


def main() -> int:
    figkit.setup()
    # matplotlib's default formatter writes U+2212 for minus signs; the SimSun
    # subset used for the PDF has no glyph for it, so ticks must use ASCII '-'.
    import matplotlib.pyplot as plt
    plt.rcParams["axes.unicode_minus"] = False
    for fn in (f01_two_routes, f02_dp_comparison, f03_mc_vs_td,
               f04_lambda_sweep, f05_cliff):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
