"""Figures for chapter 7 (模型、规划与搜索).

Run from the build directory:

    python figures\\ch07_figs.py

Three of the six figures are real computations and report their own numbers on
stdout (Dyna-Q planning steps, MCTS simulation budget, model-error compounding);
the other three are structural diagrams drawn with figkit primitives.
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
# figure 7-1: the three loops of Dyna
# ---------------------------------------------------------------------------
def f01_dyna_loops():
    fig, ax = figkit.new(3.90, 2.05)
    figkit.blank(ax, (-0.05, 3.95), (-0.25, 2.55))

    figkit.box(ax, (1.32, 2.02), 1.05, 0.40, "环境", fs=7.4,
               fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (1.32, 1.10), 1.05, 0.40, "真实经验", fs=7.2,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (1.32, 0.18), 1.05, 0.42, "价值 / 策略", fs=7.2,
               fc="#fdf1d8", ec="#c9a227")

    figkit.box(ax, (2.86, 1.10), 0.82, 0.40, "模型", fs=7.2,
               fc="#f0e9f5", ec="#9b7bb5")
    figkit.box(ax, (2.86, 0.18), 0.82, 0.42, "模拟经验", fs=6.9,
               fc="#f0e9f5", ec="#9b7bb5")

    # environment <-> real experience
    figkit.arrow(ax, (1.56, 2.00), (1.56, 1.52), color=INK)
    ax.text(1.49, 1.76, "$a_t$", ha="right", va="center", fontsize=7.0, color=INK)
    figkit.arrow(ax, (2.13, 1.52), (2.13, 2.00), color=INK)
    ax.text(2.20, 1.76, "$s',r$", ha="left", va="center", fontsize=6.8, color=INK)

    # real experience -> value/policy (direct RL)
    figkit.arrow(ax, (1.56, 1.08), (1.56, 0.62), color=C2)
    ax.text(1.62, 0.85, "直接 RL", ha="left", va="center", fontsize=6.5, color=C2)

    # real experience -> model (model learning)
    figkit.arrow(ax, (2.39, 1.30), (2.84, 1.30), color=C2)
    ax.text(2.61, 1.37, "模型学习", ha="center", va="bottom", fontsize=6.3, color=C2)

    # model -> simulated experience (search control)
    figkit.arrow(ax, (3.27, 1.08), (3.27, 0.62), color=C3)
    ax.text(3.33, 0.85, "搜索控制", ha="left", va="center", fontsize=6.3, color=C3)

    # simulated experience -> value/policy (planning update)
    figkit.arrow(ax, (2.84, 0.39), (2.41, 0.39), color=C3)
    ax.text(2.62, 0.29, "规划更新", ha="center", va="top", fontsize=6.3, color=C3)

    # value/policy -> environment (acting), a long arc on the left
    ax.annotate("", xy=(1.28, 2.05), xytext=(1.28, 0.40),
                arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8,
                                connectionstyle="arc3,rad=-0.55"))
    ax.text(0.72, 1.22, "行动", ha="center", va="center", fontsize=6.6,
            color=GREY, rotation=90)

    # bracket the two purple boxes: the indirect path
    ax.plot([3.86, 3.86], [1.02, 0.30], color=GREY, linewidth=0.6,
            linestyle=(0, (2, 2)))
    ax.text(3.80, 0.66, "间接 RL（规划）", ha="right", va="center", fontsize=6.2,
            color=GREY, rotation=90)
    ax.text(1.95, -0.18, "同一条更新规则，区别只是经验从哪来",
            ha="center", fontsize=6.4, color=GREY)

    return figkit.save(fig, "ch07_f01_dyna_loops")


# ---------------------------------------------------------------------------
# figure 7-2: Dyna-Q, planning steps vs episodes to converge (real run)
# ---------------------------------------------------------------------------
ROWS, COLS = 9, 6
WALLS = {(1, 1), (2, 1), (3, 1), (1, 3), (2, 3), (3, 3), (6, 2)}
START, GOAL = (8, 0), (0, 5)
ACTS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _transitions():
    """Deterministic maze: (next_index, reward); index -1 marks the terminal."""
    nS = ROWS * COLS
    out = [[None] * 4 for _ in range(nS)]
    for r in range(ROWS):
        for c in range(COLS):
            if (r, c) in WALLS:
                continue
            i = r * COLS + c
            for a, (dr, dc) in enumerate(ACTS):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < ROWS and 0 <= nc < COLS) or (nr, nc) in WALLS:
                    nr, nc = r, c
                if (nr, nc) == GOAL:
                    out[i][a] = (-1, 1.0)
                else:
                    out[i][a] = (nr * COLS + nc, 0.0)
    return out


def dyna_q(n_plan, seed, episodes=40, max_steps=2000, alpha=0.1, gamma=0.95,
           eps=0.1):
    """Tabular Dyna-Q on the maze above; returns the steps of every episode."""
    tr = _transitions()
    nS = ROWS * COLS
    # two independent streams: the acting noise is identical across n, so every
    # agent walks the same first trajectory and the curves differ only by
    # planning (this is what makes the comparison readable).
    rng_a = np.random.default_rng(seed)
    rng_p = np.random.default_rng(seed + 100003)
    Q = np.zeros((nS, 4))
    m_next = np.full((nS, 4), -2, dtype=int)
    m_rew = np.zeros((nS, 4))
    seen = np.zeros((nS, 4), dtype=bool)
    visited = []
    steps = []

    def qmax(i):
        q = Q[i]
        return max(q[0], q[1], q[2], q[3])

    for _ in range(episodes):
        s = START[0] * COLS + START[1]
        t = 0
        while t < max_steps:
            t += 1
            if rng_a.random() < eps:
                a = int(rng_a.integers(4))
            else:
                q = Q[s]
                best = max(q[0], q[1], q[2], q[3])
                ties = [j for j in range(4) if q[j] == best]
                a = ties[int(rng_a.integers(len(ties)))]
            s2, r = tr[s][a]
            if not seen[s, a]:
                seen[s, a] = True
                visited.append(s * 4 + a)
            target = r if s2 < 0 else r + gamma * qmax(s2)
            Q[s, a] += alpha * (target - Q[s, a])
            m_next[s, a] = s2
            m_rew[s, a] = r
            # ---- planning: n imaginary updates from the model -------------
            nv = len(visited)
            for _ in range(n_plan):
                code = visited[int(rng_p.integers(nv))]
                ss, aa = code >> 2, code & 3
                ns = m_next[ss, aa]
                rr = m_rew[ss, aa]
                tgt = rr if ns < 0 else rr + gamma * qmax(ns)
                Q[ss, aa] += alpha * (tgt - Q[ss, aa])
            if s2 < 0:
                break
            s = s2
        steps.append(t)
    return np.array(steps)


def _smooth(y, k=3):
    """Centred moving average that keeps the ends (denominator tracks weights)."""
    if k <= 1:
        return y
    num = np.convolve(y, np.ones(k), mode="same")
    den = np.convolve(np.ones_like(y), np.ones(k), mode="same")
    return num / den


def f02_dyna_planning():
    plans = [0, 5, 50]
    seeds = range(30)
    curves = {n: np.mean([dyna_q(n, 1000 + s) for s in seeds], axis=0)
              for n in plans}

    fig, ax = figkit.new(3.45, 2.05)
    colors = {0: C1, 5: C0, 50: C3}
    labels = {0: "$n=0$（仅直接 RL）", 5: "$n=5$", 50: "$n=50$"}
    ep = np.arange(1, curves[0].size + 1)
    for n in plans:
        ax.plot(ep, _smooth(curves[n], 3), color=colors[n], linewidth=1.0,
                label=labels[n])
    ax.set_xlabel("回合")
    ax.set_ylabel("到达目标的步数")
    ax.set_xlim(1, curves[0].size)
    ax.set_ylim(0, min(900, curves[0].max() * 1.06))
    ax.legend(loc="upper right", fontsize=6.6)
    ax.set_title("47 状态迷宫，30 个随机种子", fontsize=7.6)

    def reach(curve, thr=30, run=3):
        for i in range(curve.size - run):
            if np.all(curve[i:i + run] <= thr):
                return i + 1
        return -1

    print("[f02] 首回合步数 %.0f" % curves[0][0])
    for n in plans:
        c = _smooth(curves[n], 3)
        print("[f02] n=%2d  末 5 回合均值 %.1f  首次连续 3 回合 <=30 步: 第 %s 回合"
              % (n, np.mean(c[-5:]), reach(c)))

    return figkit.save(fig, "ch07_f02_dyna_planning")


# ---------------------------------------------------------------------------
# figure 7-3: model error compounds with the rollout horizon (real run)
# ---------------------------------------------------------------------------
def f03_model_error():
    rng = np.random.default_rng(7)
    # true 2-D linear dynamics: marginally unstable, so an imperfect model drifts
    A = np.array([[1.02, 0.06], [-0.04, 0.99]])
    B = np.array([[0.30], [0.10]])
    H, M = 20, 24

    def rollout(A_, B_, s0, acts):
        out = [s0]
        s = s0
        for a in acts:
            s = A_ @ s + B_.ravel() * a
            out.append(s)
        return np.array(out)

    acts = 0.8 * np.sin(np.arange(H) * 0.7)
    starts = rng.uniform(-1.0, 1.0, size=(M, 2))
    truth = np.array([rollout(A, B, s0, acts) for s0 in starts])

    def sample(n):
        s = rng.uniform(-1.0, 1.0, (n, 2))
        a = rng.uniform(-1.0, 1.0, n)
        nxt = s @ A.T + a[:, None] * B.ravel() + rng.normal(0, 0.02, (n, 2))
        return s, a, nxt

    def fit(s, a, nxt):
        X = np.column_stack([s, a])
        coef, *_ = np.linalg.lstsq(X, nxt, rcond=None)
        return coef.T          # (2, 3): next = coef @ [s; a]

    def err_curve(coef):
        A_ = coef[:, :2]
        B_ = coef[:, 2]
        e = []
        for s0 in starts:
            pred = rollout(A_, B_, s0, acts)
            e.append(np.linalg.norm(pred - rollout(A, B, s0, acts), axis=1))
        return np.mean(e, axis=0)

    curves, spreads = {}, {}
    for n in (25, 400):
        s, a, nxt = sample(n)
        curves[n] = err_curve(fit(s, a, nxt))
        if n == 25:
            boots = []
            for _ in range(8):
                idx = rng.integers(0, n, n)
                boots.append(err_curve(fit(s[idx], a[idx], nxt[idx])))
            spreads[n] = np.std(np.array(boots), axis=0)
        print("[f03] 数据量 %3d：h=1 误差 %.4f，h=%d 误差 %.4f"
              % (n, curves[n][1], H, curves[n][H]))

    fig, axes = figkit.new(4.25, 1.90, ncols=2)

    ax = axes[0]
    h = np.arange(1, H + 1)
    ax.semilogy(h, np.maximum(curves[25][1:], 1e-6), color=C1, linewidth=1.0,
                label="$N=25$ 条转移")
    ax.semilogy(h, np.maximum(curves[400][1:], 1e-6), color=C0, linewidth=1.0,
                label="$N=400$")
    ax.set_xlabel("开环推演步数 $h$")
    ax.set_ylabel("状态预测误差")
    ax.set_title("误差随视野累积", fontsize=7.6)
    ax.set_xlim(1, H)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_yticks([1e-4, 1e-3, 1e-2, 1e-1, 1])
    ax.set_yticklabels(["1e-4", "1e-3", "1e-2", "1e-1", "1"])
    ax.legend(loc="lower right", fontsize=6.4)

    ax = axes[1]
    ax.semilogy(h, np.maximum(spreads[25][1:], 1e-6), color=C2, linewidth=1.0)
    ax.set_xlabel("开环推演步数 $h$")
    ax.set_ylabel("集成模型间的标准差")
    ax.set_title("自助集成的不确定性（$N=25$）", fontsize=7.6)
    ax.set_xlim(1, H)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_yticks([1e-4, 1e-3, 1e-2, 1e-1])
    ax.set_yticklabels(["1e-4", "1e-3", "1e-2", "1e-1"])

    return figkit.save(fig, "ch07_f03_model_error")


# ---------------------------------------------------------------------------
# figure 7-4: the four steps of MCTS
# ---------------------------------------------------------------------------
def f04_mcts_four_steps():
    fig, ax = figkit.new(3.55, 2.05)
    figkit.blank(ax, (-0.12, 3.50), (-0.30, 2.62))

    # root node, centred over the three actions
    figkit.box(ax, (0.71, 2.00), 0.68, 0.34, "$s_0$", fs=7.2,
               fc="#eef3fb", ec="#7d93b2")

    # three children: two already visited, the third still unexpanded
    kids = [(0.42, "$Q=.62$\n$N=14$", "#e8f0e4", "#7d9b6a", "$a_1$", -0.10, "right"),
            (1.05, "$Q=.41$\n$N=6$", "#e8f0e4", "#7d9b6a", "$a_2$", 0.12, "left"),
            (1.68, "$Q=?$\n$N=0$", "#f4f4f6", "#b8bcc4", "$a_3$", 0.12, "left")]
    for cx, stat, fc, ec, lab, off, ha in kids:
        figkit.arrow(ax, (1.05, 1.99), (cx, 1.54), color=GREY)
        figkit.box(ax, (cx - 0.31, 1.16), 0.62, 0.36, stat, fs=6.0, fc=fc, ec=ec)
        ax.text((1.05 + cx) / 2 + off, 1.76, lab, fontsize=6.6, color=INK,
                ha=ha, va="center")

    # grandchildren of a_1
    for x, lab in [(0.10, "$a_{11}$"), (0.52, "$a_{12}$")]:
        figkit.arrow(ax, (0.42, 1.15), (x + 0.18, 0.96), color=GREY)
        figkit.box(ax, (x, 0.60), 0.36, 0.34, lab, fs=6.4,
                   fc="#fdf1d8", ec="#c9a227")

    # the four steps, each in a genuinely empty pocket of the canvas
    ax.text(1.48, 2.17, "① 选择", fontsize=6.3, color=C0, ha="left", va="center")
    ax.text(2.06, 1.34, "② 扩展", fontsize=6.3, color=C2, ha="left", va="center")
    ax.text(0.42, 0.42, "③ 模拟", fontsize=6.3, color=C3, ha="center", va="center")
    ax.annotate("", xy=(1.38, 2.13), xytext=(1.70, 1.55),
                arrowprops=dict(arrowstyle="-|>", color=C1, linewidth=0.8,
                                linestyle=(0, (3, 2)),
                                connectionstyle="arc3,rad=-0.38"))
    ax.text(2.12, 1.92, "④ 回传", fontsize=6.3, color=C1, ha="left", va="center")

    ax.text(1.70, 2.52, "UCT 把访问预算分给“看起来好”和“还没试过”", ha="center",
            fontsize=6.6, color=INK)
    ax.text(1.70, -0.22, "只有叶子需要一次随机模拟；网络可以把这一步省掉",
            ha="center", fontsize=6.2, color=GREY)

    return figkit.save(fig, "ch07_f04_mcts_four_steps")


# ---------------------------------------------------------------------------
# figure 7-5: MCTS simulation budget vs decision quality (real run, 井字棋)
# ---------------------------------------------------------------------------
LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6),
         (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))


def winner(b):
    for i, j, k in LINES:
        if b[i] and b[i] == b[j] == b[k]:
            return b[i]
    return 0 if all(b) else None


def negamax(b, p, memo):
    key = (tuple(b), p)
    if key in memo:
        return memo[key]
    w = winner(b)
    if w is not None:
        v = 0 if w == 0 else (1 if w == p else -1)
        memo[key] = v
        return v
    best = -2
    for i in range(9):
        if b[i] == 0:
            b[i] = p
            best = max(best, -negamax(b, -p, memo))
            b[i] = 0
    memo[key] = best
    return best


def playout(b, p, rng):
    """A uniform-random playout; returns the game value for p (+1/0/-1)."""
    b = list(b)
    cur = p
    w = winner(b)
    while w is None:
        free = [i for i in range(9) if b[i] == 0]
        b[free[int(rng.integers(len(free)))]] = cur
        cur = -cur
        w = winner(b)
    if w == 0:
        return 0
    return 1 if w == p else -1


def mcts_move(b, p, n_sim, rng, c=1.0):
    """UCT at the root; returns (most visited move, root value estimate, visits)."""
    kids = [i for i in range(9) if b[i] == 0]
    N = {i: 0 for i in kids}
    W = {i: 0.0 for i in kids}
    for _ in range(n_sim):
        # 1 selection: the unvisited children are tried once before UCT kicks in
        tot = sum(N.values())
        best, arg = -1e9, kids[0]
        for i in kids:
            if N[i] == 0:
                u = 1e6
            else:
                u = W[i] / N[i] + c * np.sqrt(np.log(tot) / N[i])
            if u > best:
                best, arg = u, i
        # 2 expansion + 3 simulation (random playout from the new child)
        b[arg] = p
        if winner(b) is None:
            v = -playout(b, -p, rng)
        else:
            v = 0 if winner(b) == 0 else 1
        b[arg] = 0
        # 4 backpropagation
        N[arg] += 1
        W[arg] += v
    mv = max(kids, key=lambda i: N[i])
    return mv, W[mv] / N[mv] if N[mv] else 0.0, sum(N.values())


def f05_mcts_budget():
    rng = np.random.default_rng(11)
    # collect a fixed set of test positions from random play
    positions = []
    while len(positions) < 120:
        b = [0] * 9
        p = 1
        while winner(b) is None:
            mv = [i for i in range(9) if b[i] == 0]
            positions.append((list(b), p))
            b[mv[int(rng.integers(len(mv)))]] = p
            p = -p
    positions = positions[:120]

    memo = {}
    budgets = [10, 20, 40, 80, 160, 320, 640, 1280]
    hit, verr = [], []
    for n in budgets:
        h, e = 0, 0.0
        for b, p in positions:
            legal = [i for i in range(9) if b[i] == 0]
            vals = {}
            for i in legal:
                b[i] = p
                vals[i] = -negamax(b, -p, memo)
                b[i] = 0
            best = max(vals.values())
            optimal = [i for i in legal if vals[i] == best]
            mv, q, _ = mcts_move(list(b), p, n, rng)
            h += mv in optimal
            e += abs(q - best)
        hit.append(h / len(positions))
        verr.append(e / len(positions))
        print("[f05] 模拟 %4d 次：最优着法命中率 %.3f，根价值平均误差 %.3f"
              % (n, hit[-1], verr[-1]))

    fig, axes = figkit.new(4.25, 1.90, ncols=2)
    x = np.arange(len(budgets))

    ax = axes[0]
    ax.plot(x, hit, "o-", color=C0, markersize=2.6, linewidth=1.0)
    ax.set_xlabel("每次决策的模拟次数")
    ax.set_ylabel("命中最优着法的比例")
    ax.set_xticks(x[::2])
    ax.set_xticklabels([str(budgets[i]) for i in range(0, len(budgets), 2)],
                       fontsize=6.2)
    ax.set_ylim(0.68, 1.02)
    ax.set_title("决策质量", fontsize=7.6)
    ax.axhline(1.0, color=GREY, linewidth=0.6, linestyle=(0, (3, 2)))

    ax = axes[1]
    ax.semilogy(x, verr, "o-", color=C2, markersize=2.6, linewidth=1.0)
    ax.set_xlabel("每次决策的模拟次数")
    ax.set_ylabel("根价值估计的绝对误差")
    ax.set_xticks(x[::2])
    ax.set_xticklabels([str(budgets[i]) for i in range(0, len(budgets), 2)],
                       fontsize=6.2)
    ax.set_yticks([1e-2, 1e-1, 1])
    ax.set_yticklabels(["1e-2", "1e-1", "1"])
    ax.set_title("价值估计", fontsize=7.6)

    return figkit.save(fig, "ch07_f05_mcts_budget")


# ---------------------------------------------------------------------------
# figure 7-6: what the "model" predicts, from observations to latent state
# ---------------------------------------------------------------------------
def f06_world_model_spectrum():
    fig, ax = figkit.new(4.40, 2.10)
    figkit.blank(ax, (-0.08, 4.45), (-0.36, 2.80))

    rows = [
        (2.10, "观测重建", "$\\hat P(o'\\mid o,a)$", "先还原画面，再谈决策",
         "#eef3fb", "#7d93b2"),
        (1.24, "隐空间预测", "$s^{k}=g(s^{k-1},a^{k})$", "只预测 $r,v,p$，不回译观测",
         "#f0e9f5", "#9b7bb5"),
        (0.38, "无模型", "$Q_\\phi(s,a)$ 或 $\\pi_\\theta$", "不做前瞻，直接拟合价值",
         "#e8f0e4", "#7d9b6a"),
    ]
    for y, name, expr, note, fc, ec in rows:
        figkit.box(ax, (0.05, y), 1.20, 0.50, name, fs=8.2, fc=fc, ec=ec)
        ax.text(1.40, y + 0.32, expr, fontsize=7.6, color=INK, va="center")
        ax.text(1.40, y + 0.12, note, fontsize=6.9, color=GREY, va="center")

    for y0, y1 in ((2.10, 1.76), (1.24, 0.90)):
        figkit.arrow(ax, (0.65, y0 - 0.02), (0.65, y1 + 0.02), color=GREY)

    ax.annotate("", xy=(4.24, 0.44), xytext=(4.24, 2.54),
                arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
    ax.text(4.18, 2.68, "越往下", fontsize=6.9, color=GREY, ha="right")
    ax.text(2.12, -0.26, "自上而下模型越来越少、越来越靠近决策；三者都能做出好决策，区别只在要不要还原观测",
            ha="center", fontsize=6.9, color=GREY)

    return figkit.save(fig, "ch07_f06_world_model_spectrum")


def main() -> int:
    figkit.setup()
    for fn in (f01_dyna_loops, f02_dyna_planning, f03_model_error,
               f04_mcts_four_steps, f05_mcts_budget, f06_world_model_spectrum):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
