"""Figures for chapter 9 (层次、多智能体与安全约束).

    python figures\\ch09_figs.py

Every figure is vector SVG written into ``figures/out``.  The three data
figures are computed here (no hand-drawn curves); each one prints an evidence
line so the numbers quoted in the prose can be re-derived.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import matplotlib

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUILD_DIR)

import figkit  # noqa: E402
from figkit import C0, C1, C2, C3, C4, GREY, GRID, INK  # noqa: E402

NF = 7.0   # default text size used in the diagrams


def _blank(ax, xlim, ylim):
    figkit.blank(ax, xlim, ylim)


# --------------------------------------------------------------------------
# 9-1  temporal abstraction: options as macro actions
# --------------------------------------------------------------------------
def f00_frameworks():
    """Three extensions of the standard MDP, one box each."""
    fig, ax = figkit.new(3.45, 1.95)
    _blank(ax, (-0.05, 3.55), (0.55, 3.15))

    figkit.box(ax, (0.42, 2.52), 2.72, 0.46,
               "标准 MDP：单个决策者、单步动作、只最大化回报",
               fs=7.0, fc="#eef3fb", ec="#7d93b2")

    items = [("SMDP", "动作跨多个时间步", C0),
             ("Markov 博弈", "多个决策者", C1),
             ("CMDP", "回报外的约束", C3)]
    for i, (name, note, color) in enumerate(items):
        x = 0.04 + i * 1.17
        ax.annotate("", xy=(x + 0.54, 2.06), xytext=(1.78, 2.50),
                    arrowprops=dict(arrowstyle="-|>", color=color, linewidth=0.8,
                                    shrinkA=1.0, shrinkB=1.0,
                                    connectionstyle="arc3,rad=%.2f"
                                    % (0.10 * (1 - i))))
        figkit.box(ax, (x, 1.62), 1.08, 0.42, name, fs=7.2,
                   fc="#f7f8fa", ec=color)
        ax.text(x + 0.54, 1.50, note, fontsize=6.3, color=color, ha="center",
                va="top")
        ax.text(x + 0.54, 1.18, ("第 9.1 节", "第 9.2 节", "第 9.3 节")[i],
                fontsize=6.0, color=GREY, ha="center", va="top")
    ax.text(1.78, 0.62, "本章只对这三个框架做完整推导；元学习仅作案例（9.4）",
            fontsize=6.2, color=GREY, ha="center", va="top")

    return figkit.save(fig, "ch09_f00_frameworks")


def f01_options():
    fig, ax = figkit.new(4.30, 1.88)
    _blank(ax, (-0.15, 4.45), (-0.10, 3.10))

    # timeline
    ax.annotate("", xy=(4.05, 1.55), xytext=(0.08, 1.55),
                arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=0.9))
    ax.text(4.14, 1.55, "t", fontsize=7.0, color=INK, va="center")

    prim = [(0.20, 0.32), (0.52, 0.64), (0.84, 0.96), (1.16, 1.28),
            (1.48, 1.60), (1.80, 1.92), (2.12, 2.24), (2.44, 2.56),
            (2.76, 2.88), (3.08, 3.20)]
    for x0, x1 in prim:
        ax.add_patch(matplotlib.patches.Rectangle((x0, 1.43), x1 - x0, 0.25,
                                                  facecolor="#eef3fb",
                                                  edgecolor="#7d93b2",
                                                  linewidth=0.6))

    # three options as brackets over groups of primitives
    groups = [((0.20, 0.96), "选项 $o_1$", C0, 2.60),
              ((1.16, 2.24), "选项 $o_2$", C1, 2.60),
              ((2.44, 3.20), "选项 $o_3$", C3, 2.60)]
    for (x0, x1), name, color, y in groups:
        ax.annotate("", xy=(x0, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="|-|", color=color, linewidth=0.9))
        ax.text((x0 + x1) / 2, y + 0.12, name, ha="center", fontsize=6.8,
                color=color)
        for xa, xb in prim:
            if xa >= x0 - 0.01 and xb <= x1 + 0.01:
                ax.plot([(xa + xb) / 2, (xa + xb) / 2], [1.70, y - 0.04],
                        color=color, linewidth=0.4, alpha=0.55)

    ax.text(0.02, 1.18, "原始动作 $a_t$：每一步都要做一次决策", fontsize=6.7,
            color=GREY, ha="left")
    ax.text(0.02, 0.86, "选项内部的策略 $\\pi_o$ 连续执行，直到 $\\beta_o$ 叫停",
            fontsize=6.7, color=GREY, ha="left")

    # the option triple
    for lab, xx, w in (("$I_o\\subseteq\\mathcal{S}$", 0.06, 0.86),
                       ("$\\pi_o$", 1.00, 0.44),
                       ("$\\beta_o$", 1.50, 0.44)):
        figkit.box(ax, (xx, 0.14), w, 0.40, lab, fs=7.0,
                   fc="#f7f8fa", ec="#9aa4b2")
    ax.text(2.10, 0.34, "三元组：起始集合、内部策略、终止概率", fontsize=6.8,
            color=INK, va="center")

    return figkit.save(fig, "ch09_f01_options")


# --------------------------------------------------------------------------
# 9-2  experiment: primitive actions vs hand-made options on a maze
# --------------------------------------------------------------------------
def _make_maze():
    nr, nc = 11, 15
    wall = np.zeros((nr, nc), dtype=int)
    for r in range(nr):
        if r != 2:
            wall[r, 5] = 1
        if r != 8:
            wall[r, 10] = 1
    start, goal = (1, 1), (9, 13)
    return wall, start, goal


def _bfs_dist(wall, target):
    nr, nc = wall.shape
    dist = np.full((nr, nc), -1, dtype=int)
    from collections import deque
    q = deque([target])
    dist[target] = 0
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < nr and 0 <= cc < nc and wall[rr, cc] == 0 and dist[rr, cc] < 0:
                dist[rr, cc] = dist[r, c] + 1
                q.append((rr, cc))
    return dist


MOVES = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _step(wall, s, a):
    nr, nc = wall.shape
    r, c = s
    dr, dc = MOVES[a]
    rr, cc = min(max(r + dr, 0), nr - 1), min(max(c + dc, 0), nc - 1)
    if wall[rr, cc] == 0:
        return (rr, cc)
    return s


def _eps_greedy(q, s, n, rng, eps):
    if rng.random() < eps:
        return int(rng.integers(n))
    row = q[s]
    best = np.flatnonzero(row == row.max())
    return int(best[rng.integers(len(best))])


def _run_primitive(wall, start, goal, seed, episodes=150, alpha=0.1,
                   gamma=0.95, eps=0.1):
    rng = np.random.default_rng(seed)
    nr, nc = wall.shape
    q = np.zeros((nr, nc, 4))
    first = -1
    for ep in range(episodes):
        s, steps = start, 0
        while s != goal and steps < 200:
            a = _eps_greedy(q, s, 4, rng, eps)
            s2 = _step(wall, s, a)
            r = 10.0 if s2 == goal else -0.05
            done = s2 == goal
            tgt = r + (0.0 if done else gamma * q[s2].max())
            q[s][a] += alpha * (tgt - q[s][a])
            s, steps = s2, steps + 1
        if s == goal and first < 0:
            first = ep + 1
    return first


def _run_options(wall, start, goal, seed, episodes=150, alpha=0.1,
                 gamma=0.95, eps=0.1, cap=60):
    rng = np.random.default_rng(seed)
    wps = [(2, 4), (8, 9), goal]
    dists = [_bfs_dist(wall, w) for w in wps]
    nr, nc = wall.shape
    q = np.zeros((nr, nc, len(wps)))
    first = -1
    for ep in range(episodes):
        s = start
        guard = 0
        while s != goal and guard < 20:
            k = _eps_greedy(q, s, len(wps), rng, eps)
            s0, disc, tau, done = s, 0.0, 0, False
            while tau < cap:
                d = dists[k]
                best, besta = 10 ** 9, 0
                for a in range(4):
                    s2 = _step(wall, s, a)
                    if d[s2] >= 0 and d[s2] < best:
                        best, besta = d[s2], a
                s2 = _step(wall, s, besta)
                r = 10.0 if s2 == goal else -0.05
                disc += (gamma ** tau) * r
                tau += 1
                s = s2
                if s == goal:
                    done = True
                    break
                if s == wps[k]:
                    break
            if done:
                tgt = disc
            else:
                tgt = disc + (gamma ** tau) * q[s].max()
            q[s0][k] += alpha * (tgt - q[s0][k])
            guard += 1
        if s == goal and first < 0:
            first = ep + 1
    return first


def f02_maze():
    wall, start, goal = _make_maze()
    seeds = range(40)
    prim = [_run_primitive(wall, start, goal, s) for s in seeds]
    opt = [_run_options(wall, start, goal, s) for s in seeds]
    prim_ok = [x for x in prim if x > 0]
    opt_ok = [x for x in opt if x > 0]
    print("f02: primitive solved %d/40 median=%s | options solved %d/40 median=%s"
          % (len(prim_ok), int(np.median(prim_ok)) if prim_ok else None,
             len(opt_ok), int(np.median(opt_ok)) if opt_ok else None))

    fig, axes = figkit.new(4.50, 2.00, ncols=2)

    ax = axes[0]
    for r in range(wall.shape[0]):
        for c in range(wall.shape[1]):
            if wall[r, c]:
                ax.add_patch(matplotlib.patches.Rectangle(
                    (c - 0.5, r - 0.5), 1.0, 1.0, facecolor="#b9c0c9",
                    edgecolor="none", zorder=1))
    ax.plot(start[1], start[0], marker="o", color=C0, markersize=4.0)
    bb = dict(facecolor="white", edgecolor="none", pad=1.0)
    ax.text(start[1] + 1.1, start[0] - 0.15, "$s_0$", fontsize=7.0, color=C0,
            ha="left", va="center", bbox=bb)
    ax.plot(goal[1], goal[0], marker="*", color=C4, markersize=9.0)
    ax.text(goal[1], goal[0] + 1.15, "目标", fontsize=6.8, color=C4,
            ha="center", va="top", bbox=bb)
    for i, w in enumerate([(2, 4), (8, 9)]):
        ax.plot(w[1], w[0], marker="s", color=C1, markersize=3.6)
        ax.text(w[1] - 1.0, w[0] + 0.15, "$w_%d$" % (i + 1), fontsize=6.6,
                color=C1, ha="right", va="center", bbox=bb)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    ax.set_xlim(-1.2, 15.0)
    ax.set_ylim(11.2, -1.2)
    ax.set_title("三室迷宫：两道门各一个", fontsize=7.6)

    ax = axes[1]
    bins = np.arange(0, 61, 10)
    hp, _ = np.histogram([x for x in prim if x > 0], bins=bins)
    ho, _ = np.histogram([x for x in opt if x > 0], bins=bins)
    centers = (bins[:-1] + bins[1:]) / 2
    ax.bar(centers - 2.0, hp, width=3.6, color=C0, label="原始动作")
    ax.bar(centers + 2.0, ho, width=3.6, color=C3, label="选项")
    ax.set_xlabel("首次到达目标所需回合数")
    ax.set_ylabel("种子数")
    ax.legend(loc="upper right", fontsize=6.6)
    ax.set_title("探索成本：40 个种子", fontsize=7.6)
    ax.set_ylim(0, 44)

    return figkit.save(fig, "ch09_f02_maze")


# --------------------------------------------------------------------------
# 9-3  experiment: independent vs joint-action Q-learning on a 2x2 game
# --------------------------------------------------------------------------
CLIMB = np.array([[11.0, 0.0], [0.0, 7.0]])   # both agents share this payoff
PENNY = np.array([[1.0, -1.0], [-1.0, 1.0]])


def _indep_q(seed, payoff, payoff2=None, episodes=2000, alpha=0.1, gamma=0.0,
             eps=0.1):
    """Two learners, each with its own Q over its own actions, updated
    simultaneously from the realised joint action (no shared information)."""
    if payoff2 is None:
        payoff2 = payoff
    rng = np.random.default_rng(seed)
    q1, q2 = np.zeros(2), np.zeros(2)
    d1, acts = [], []
    for _ in range(episodes):
        a1 = _eps_greedy({"x": q1}, "x", 2, rng, eps)
        a2 = _eps_greedy({"x": q2}, "x", 2, rng, eps)
        r1, r2 = payoff[a1, a2], payoff2[a1, a2]
        q1[a1] += alpha * (r1 + gamma * q1.max() - q1[a1])
        q2[a2] += alpha * (r2 + gamma * q2.max() - q2[a2])
        d1.append(q1[0] - q1[1])
        acts.append((a1, a2))
    return int(np.argmax(q1)), int(np.argmax(q2)), np.array(d1), np.array(acts)


def _joint_q(seed, payoff, episodes=2000, alpha=0.1, gamma=0.0, eps=0.1):
    """One learner over the four joint actions (centralised execution)."""
    rng = np.random.default_rng(seed)
    q = np.zeros((2, 2))
    for _ in range(episodes):
        if rng.random() < eps:
            j = int(rng.integers(4))
            a1, a2 = j // 2, j % 2
        else:
            best = np.argwhere(q == q.max())
            a1, a2 = best[rng.integers(len(best))]
        r = payoff[a1, a2]
        q[a1, a2] += alpha * (r + gamma * q.max() - q[a1, a2])
    a1, a2 = np.unravel_index(int(np.argmax(q)), q.shape)
    return int(a1), int(a2)


def f03_game():
    seeds = range(60)
    ind = np.zeros(4, dtype=int)
    joi = np.zeros(4, dtype=int)
    for s in seeds:
        a1, a2, _, _ = _indep_q(s, CLIMB)
        ind[a1 * 2 + a2] += 1
        a1, a2 = _joint_q(s, CLIMB)
        joi[a1 * 2 + a2] += 1
    _, _, dp, ap = _indep_q(0, PENNY, -PENNY, episodes=1500)
    cross = int(np.sum(np.diff(np.sign(dp)) != 0))
    f1 = float((ap[-300:, 0] == 0).mean())
    f2 = float((ap[-300:, 1] == 0).mean())
    joint = [(ap[-300:, 0] == x).astype(float) * (ap[-300:, 1] == y).astype(float)
             for x in range(2) for y in range(2)]
    print("f03: pennies switches=%d last300 freq a1=%.2f a2=%.2f joint=%s"
          % (cross, f1, f2, [round(float(j.mean()), 2) for j in joint]))
    print("f03: climbing indep final cells %s (optimum block 0 = (a1,b1)=11)"
          % ind.tolist())
    print("f03: climbing joint final cells %s" % joi.tolist())
    print("f03: matching-pennies zero crossings of Q1 diff = %d / 1500 episodes"
          % cross)

    cell_r = [CLIMB[0, 0], CLIMB[0, 1], CLIMB[1, 0], CLIMB[1, 1]]
    labels = ["$a_1b_1$\n$r=11$" if r == 11 else ("$a_2b_2$\n$r=7$" if r == 7
              else ("$a_1b_2$\n$r=0$" if r == 0 and False else "$r=%d$" % r))
              for r in cell_r]
    labels = ["$a_1b_1$", "$a_1b_2$", "$a_2b_1$", "$a_2b_2$"]
    colors = [C3 if r == 11 else (C0 if r == 7 else GREY) for r in cell_r]

    fig, axes = figkit.new(4.50, 1.95, ncols=2)
    xs = np.arange(4)
    for ax, cnt, title in ((axes[0], ind, "独立学习：60 个种子的落点"),
                           (axes[1], joi, "联合动作学习：60 个种子的落点")):
        ax.bar(xs, cnt, width=0.6, color=colors)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontsize=6.6)
        ax.set_ylabel("种子数")
        ax.set_ylim(0, 72)
        ax.set_title(title, fontsize=7.4)
        for x, v in zip(xs, cnt):
            if v:
                ax.text(x, v + 1.2, str(v), ha="center", fontsize=6.6, color=INK)

    return figkit.save(fig, "ch09_f03_game")


# --------------------------------------------------------------------------
# 9-4  risk: expectation vs tail, two policies on the same budget
# --------------------------------------------------------------------------
def _sample_losses(kind, n, rng):
    """Empirical losses.  The risky policy has EXACTLY a 1% atom at 20.2, so the
    numbers printed below need no sampling noise."""
    if kind == "safe":
        return np.full(n, 1.0)
    k = n // 100
    return np.concatenate([np.full(n - k, 0.20), np.full(k, 20.20)])


def _var(z, alpha):
    return float(np.quantile(z, alpha, method="higher"))


def _cvar_inf(z, alpha, n_eta=20001):
    """inf_eta { eta + E[(Z-eta)_+]/(1-alpha) } evaluated on the empirical
    distribution: with few distinct atoms the integral is a finite sum, so the
    grid search is exact up to the grid step (this is the definition, NOT the
    tail-average shortcut)."""
    vals, cnt = np.unique(z, return_counts=True)
    p = cnt / len(z)
    etas = np.linspace(vals.min() - 1.0, vals.max() + 1.0, n_eta)
    tail = (np.maximum(vals[None, :] - etas[:, None], 0.0) * p[None, :]).sum(1)
    f = etas + tail / (1.0 - alpha)
    k = int(np.argmin(f))
    return float(f[k]), float(etas[k])


def _cvar_tail(z, alpha):
    """Average of the largest (1-alpha) fraction of the samples."""
    zs = np.sort(z)
    k = int(round((1.0 - alpha) * len(zs)))
    return float(zs[-k:].mean())


def f04_risk():
    rng = np.random.default_rng(20261019)
    n = 1000000
    za = _sample_losses("safe", n, rng)
    zb = _sample_losses("fast", n, rng)
    alpha = 0.95
    rows = []
    for name, z in (("safe", za), ("fast", zb)):
        c_inf, eta = _cvar_inf(z, alpha)
        c_tail = _cvar_tail(z, alpha)
        rows.append((name, z.mean(), _var(z, alpha), c_inf, c_tail, eta))
        print("f04: %-4s E=%.3f VaR95=%.2f CVaR95(inf)=%.2f topmass=%.2f eta*=%.2f"
              % (name, z.mean(), _var(z, alpha), c_inf, c_tail, eta))
    e_f, v_f, c_f = rows[1][1], rows[1][2], rows[1][4]

    fig, ax = figkit.new(3.55, 2.00)
    ybot = 2.2e-3
    for name, z, color, lab in (("safe", za, C3, "稳妥策略"),
                                ("fast", zb, C1, "冒进策略")):
        vals, cnt = np.unique(z, return_counts=True)
        ax.vlines(vals, ybot, cnt / float(len(z)), color=color, linewidth=2.0,
                  label=lab)
        ax.plot(vals, cnt / float(len(z)), "o", color=color, markersize=2.8)
    ax.set_xscale("linear")
    ax.set_yscale("log")
    ax.set_xlim(-1.4, 23.2)
    ax.set_ylim(ybot, 2.6)
    ax.set_xlabel("损失 $Z$")
    ax.set_ylabel("概率（对数轴）")
    ax.axhline(0.05, color=GREY, linewidth=0.7, linestyle=(0, (2, 2)))
    ax.text(21.9, 0.056, "$1-\\alpha=0.05$", fontsize=5.7, color=GREY,
            ha="right", va="bottom")
    ax.text(-0.12, 1.30, "0.99", fontsize=5.8, color=C1, ha="center", va="bottom")
    ax.text(1.30, 0.50, "1.00", fontsize=5.8, color=C3, ha="left", va="center")
    ax.text(20.9, 0.011, "0.01", fontsize=5.8, color=C1, ha="left", va="center")
    ax.text(3.2, 2.25,
            "稳妥：$\\mathbb{E}=1.00$，$\\mathrm{VaR}=1.00$，$\\mathrm{CVaR}=1.00$\n"
            "冒进：$\\mathbb{E}=%.2f$，$\\mathrm{VaR}=0.20$，$\\mathrm{CVaR}=%.2f$"
            % (e_f, c_f),
            fontsize=5.9, color=INK, va="top", linespacing=1.7)
    ax.legend(fontsize=5.9, loc="lower center", frameon=False, handlelength=1.6,
              borderaxespad=0.1)
    ax.set_title("两条损失分布（纵轴对数）：期望更低，尾部重得多", fontsize=7.0)

    return figkit.save(fig, "ch09_f04_risk")


# --------------------------------------------------------------------------
# 9-5  CTDE and the monotone mixing network of QMIX
# --------------------------------------------------------------------------
def f05_ctde():
    fig, ax = figkit.new(4.30, 2.10)
    _blank(ax, (-0.10, 4.40), (-0.15, 3.10))

    # --- left: CTDE ------------------------------------------------------
    ax.text(1.02, 3.00, "集中训练、分散执行", fontsize=7.4, color=INK, ha="center")
    figkit.box(ax, (0.06, 1.86), 0.62, 0.46, "智能体 1\n$\\pi_1(o_1)$", fs=6.4,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (0.06, 1.20), 0.62, 0.46, "智能体 2\n$\\pi_2(o_2)$", fs=6.4,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (1.32, 1.53), 0.92, 0.52, "集中 critic\n$Q_i(s,a_1,a_2)$", fs=6.4,
               fc="#eef3fb", ec="#7d93b2")
    figkit.arrow(ax, (0.70, 2.09), (1.30, 1.84), color=GREY, style="-|>")
    figkit.arrow(ax, (0.70, 1.43), (1.30, 1.68), color=GREY, style="-|>")
    ax.text(1.18, 0.92, "执行时只用局部观测 $o_i$\n训练时 critic 可看全局状态与联合动作",
            fontsize=6.2, color=GREY, ha="center", va="top", linespacing=1.6)
    ax.plot([0.06, 2.30], [0.46, 0.46], color=GRID, linewidth=0.8, linestyle=(0, (2, 2)))

    # --- right: QMIX mixer ----------------------------------------------
    ax.text(3.42, 3.00, "QMIX 的单调混合", fontsize=7.4, color=INK, ha="center")
    for i, (yy, lab) in enumerate([(2.16, "$Q_1$"), (1.62, "$Q_2$"), (1.08, "$\\cdots$")]):
        figkit.box(ax, (2.62, yy), 0.42, 0.34, lab, fs=6.8, fc="#e8f0e4", ec="#7d9b6a")
        ax.annotate("", xy=(3.30, 1.72), xytext=(3.06, yy + 0.17),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.7))
    figkit.box(ax, (3.30, 1.44), 0.66, 0.62, "单调\n混合", fs=6.6, fc="#fdf1d8", ec="#c9a227")
    figkit.box(ax, (4.06, 1.58), 0.30, 0.34, "$Q_{tot}$", fs=6.6, fc="#eef3fb", ec="#7d93b2")
    ax.annotate("", xy=(4.04, 1.75), xytext=(3.98, 1.75),
                arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.7))
    ax.text(3.63, 2.34, "$\\partial Q_{tot}/\\partial Q_i\\geq 0$", fontsize=6.4,
            color=C1, ha="center")

    # the 2x2 counterexample, drawn as a matrix
    ax.text(3.62, 0.92, "反例：$[[1,0],[0,1]]$", fontsize=6.2, color=INK,
            ha="center")
    ax.text(2.92, 0.55, "$a_1$", fontsize=5.6, color=GREY, ha="right", va="center")
    ax.text(2.92, 0.25, "$a_2$", fontsize=5.6, color=GREY, ha="right", va="center")
    ax.text(3.14, 0.755, "$b_1$", fontsize=5.6, color=GREY, ha="center")
    ax.text(3.48, 0.755, "$b_2$", fontsize=5.6, color=GREY, ha="center")
    for r in range(2):
        for c in range(2):
            v = 1 if r == c else 0
            ax.add_patch(matplotlib.patches.Rectangle(
                (2.97 + c * 0.34, 0.10 + (1 - r) * 0.30), 0.34, 0.30,
                facecolor="#eef3fb" if v else "#ffffff", edgecolor="#9aa4b2",
                linewidth=0.6))
            ax.text(3.14 + c * 0.34, 0.10 + (1 - r) * 0.30 + 0.15, str(v),
                    fontsize=6.2, color=INK, ha="center", va="center")
    ax.text(3.62, 0.00, "单调混合表示不出这个 $Q_{tot}$", fontsize=5.8,
            color=GREY, ha="center")

    return figkit.save(fig, "ch09_f05_ctde")


def main() -> int:
    figkit.setup()
    matplotlib.rcParams["axes.unicode_minus"] = False
    for fn in (f00_frameworks, f01_options, f02_maze, f03_game, f04_risk, f05_ctde):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
