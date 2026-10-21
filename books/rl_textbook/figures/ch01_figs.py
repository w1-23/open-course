"""Figures for chapter 1 (多臂老虎机与探索).

Run from the build directory:

    python figures\\ch01_figs.py

Three of the four figures carry numbers that are computed here, not drawn by
hand: the 10-armed Gaussian testbed is simulated with a fixed seed, so the
caption in ``content/ch01.md`` can state the seed and the number of runs and the
curve is reproducible byte for byte.

Every figure is vector SVG written into ``figures/out``.
"""

from __future__ import annotations

import os
import sys

import numpy as np

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUILD_DIR)

import figkit  # noqa: E402
from figkit import C0, C1, C2, C3, C4, GREY, INK  # noqa: E402

# ---------------------------------------------------------------- experiment
SEED = 20261020          # stated in the figure caption and in the text
RUNS = 2000              # independent bandit problems
HORIZON = 5000           # steps per run (long enough to see the linear regime)
K = 10                   # arms
UCB_C = 2.0              # UCB1 exploration constant (S&B use c = 2)
EPS_FIX = 0.1            # fixed epsilon
EPS_SMALL = 0.01
EPS_DECAY_C = 10.0       # GLIE: eps_t = min(1, c/t), c = K


def _testbed(seed: int = SEED, runs: int = RUNS, k: int = K):
    rng = np.random.default_rng(seed)
    mu = rng.normal(0.0, 1.0, size=(runs, k))
    gap = mu.max(axis=1, keepdims=True) - mu      # (runs, k), >= 0
    return mu, gap


def _simulate(kind: str, mu: np.ndarray, gap: np.ndarray, seed: int) -> np.ndarray:
    """One bandit algorithm; returns cumulative regret, shape (runs, T)."""
    runs, k = mu.shape
    rng = np.random.default_rng(seed)
    rows = np.arange(runs)
    N = np.zeros((runs, k))
    Q = np.zeros((runs, k))
    # Gaussian Thompson sampling: prior N(0,1) on each mean, reward noise N(0,1),
    # so the posterior after n pulls is N(sum r / (n+1), 1/(n+1)).
    prec = np.ones((runs, k))
    pm = np.zeros((runs, k))
    reg = np.zeros(runs)
    out = np.empty((runs, HORIZON))

    for t in range(HORIZON):
        if kind == "ts":
            theta = pm + rng.standard_normal((runs, k)) / np.sqrt(prec)
            a = theta.argmax(axis=1)
        else:
            if kind == "ucb1":
                # an arm never pulled is treated as a maximiser
                bonus = UCB_C * np.sqrt(np.log(t + 1.0) / np.maximum(N, 1.0))
                idx = np.where(N > 0.0, Q + bonus, np.inf)
            else:
                idx = Q
            # a whisper of noise breaks exact ties uniformly
            a = (idx + 1e-9 * rng.standard_normal((runs, k))).argmax(axis=1)
            if kind == "eps_fix":
                eps = EPS_FIX
            elif kind == "eps_small":
                eps = EPS_SMALL
            elif kind == "eps_glie":
                eps = min(1.0, EPS_DECAY_C / (t + 1.0))
            else:
                eps = 0.0
            if eps > 0.0:
                pick = rng.random(runs) < eps
                a = np.where(pick, rng.integers(0, k, size=runs), a)

        r = mu[rows, a] + rng.standard_normal(runs)
        reg = reg + gap[rows, a]
        out[:, t] = reg

        N[rows, a] += 1.0
        Q[rows, a] += (r - Q[rows, a]) / N[rows, a]
        pm[rows, a] = (prec[rows, a] * pm[rows, a] + r) / (prec[rows, a] + 1.0)
        prec[rows, a] += 1.0

    return out


ALGOS = (
    ("greedy", "贪心 $\\varepsilon=0$", "#000000", "-"),
    ("eps_fix", "$\\varepsilon=0.1$", C0, "-"),
    ("eps_small", "$\\varepsilon=0.01$", C2, "-"),
    ("eps_glie", "GLIE $\\varepsilon_t=\\min(1,10/t)$", C3, "-"),
    ("ucb1", "UCB1 $c=2$", C1, "-"),
    ("ts", "Thompson", C4, "-"),
)


def run_experiment():
    mu, gap = _testbed()
    curves = {}
    for i, (kind, _label, _c, _ls) in enumerate(ALGOS):
        # a distinct child seed per algorithm keeps the reward streams independent
        curves[kind] = _simulate(kind, mu, gap, seed=SEED + 7919 * (i + 1))
    return curves


def _ascii_log_ticks(ax, axis: str, values, labels) -> None:
    """Log ticks by hand: matplotlib's formatter emits U+2212, absent in 宋体."""
    if axis == "y":
        ax.set_yticks(values)
        ax.set_yticklabels(labels)
    else:
        ax.set_xticks(values)
        ax.set_xticklabels(labels)


# ------------------------------------------------------------------- figures
def f01_problem():
    """Why a bandit is a decision problem and where regret comes from."""
    fig, axes = figkit.new(4.30, 1.90, ncols=2)
    for ax, xlim in zip(axes, [(-0.15, 3.05), (-0.15, 3.25)]):
        figkit.blank(ax, xlim, (-0.25, 2.75))

    ax = axes[0]
    ax.text(1.45, 2.58, "无状态：每次选择都是一次独立抽奖",
            ha="center", fontsize=7.2, color=INK)
    figkit.box(ax, (0.05, 1.70), 1.28, 0.50, "K 个臂\n分布 $\\nu_1,\\dots,\\nu_K$", fs=6.8,
               fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (1.70, 1.70), 0.92, 0.50, "选 $a_t$", fs=7.0,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (1.70, 0.70), 0.92, 0.50, "观测 $r_t$", fs=7.0,
               fc="#fdf1d8", ec="#c9a227")
    figkit.arrow(ax, (1.35, 1.95), (1.68, 1.95))
    ax.text(1.52, 2.06, "$\\nu_{a_t}$", ha="center", fontsize=6.6, color=GREY)
    # action down, reward back up: the same two-terminal loop as an agent and
    # its environment, which is why the bandit is the smallest such problem
    figkit.arrow(ax, (2.32, 1.68), (2.32, 1.24))
    figkit.arrow(ax, (1.98, 1.24), (1.98, 1.68))
    ax.text(1.86, 1.46, "更新\n$Q_t$", ha="right", fontsize=6.4, color=GREY)
    ax.text(1.55, 0.44, "只有 $a_t$ 影响 $r_t$，不影响下一刻的分布",
            ha="center", fontsize=6.4, color=GREY)

    ax = axes[1]
    ax.text(1.55, 2.58, "遗憾的两个来源", ha="center", fontsize=7.2, color=INK)
    figkit.box(ax, (0.02, 1.52), 3.05, 0.72,
               "① 必要的试验：每个候选臂都得试到\n"
               "约 $\\ln T/\\mathrm{KL}_a$ 次，代价 $\\sum_a \\Delta_a/\\mathrm{KL}_a$",
               fs=6.5, fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (0.02, 0.66), 3.05, 0.72,
               "② 未修正的错误：把噪声当信号，或从此\n"
               "不再回访次优臂，代价随 $T$ 线性增长",
               fs=6.5, fc="#fdecea", ec="#c0392b")
    ax.text(1.55, 0.34, "第二项是否为零，决定遗憾是 $\\ln T$ 还是 $T$",
            ha="center", fontsize=6.4, color=GREY)

    return figkit.save(fig, "ch01_f01_problem")


def f02_regret(curves):
    """Cumulative regret: linear axes, then the log-log slope."""
    fig, axes = figkit.new(4.30, 2.05, ncols=2)
    t = np.arange(1, HORIZON + 1)

    ax = axes[0]
    for kind, label, color, ls in ALGOS:
        m = curves[kind].mean(axis=0)
        ax.plot(t, m, color=color, linestyle=ls, linewidth=0.9, label=label)
    ax.set_xlabel("步数 $t$", fontsize=7.4)
    ax.set_ylabel("累积遗憾", fontsize=7.4)
    ax.set_xlim(1, HORIZON)
    ax.set_title("累积遗憾（2000 次试验均值）", fontsize=7.4)
    ax.set_ylim(0, curves["greedy"].mean(axis=0)[-1] * 1.14)
    ax.legend(loc="upper left", fontsize=5.9, handlelength=1.4,
              borderpad=0.2, labelspacing=0.25)

    ax = axes[1]
    fit_lo, fit_hi = 1000, HORIZON
    for kind, label, color, ls in ALGOS:
        m = curves[kind].mean(axis=0)
        seg = slice(fit_lo - 1, fit_hi)
        slope = np.polyfit(np.log(t[seg]), np.log(m[seg]), 1)[0]
        ax.loglog(t, m, color=color, linestyle=ls, linewidth=0.9,
                  label=f"{label}（{slope:.2f}）")
    ax.set_xlabel("步数 $t$（对数）", fontsize=7.4)
    ax.set_ylabel("累积遗憾（对数）", fontsize=7.4)
    ax.set_title("双对数斜率：1 为线性，$<1$ 为次线性", fontsize=7.4)
    _ascii_log_ticks(ax, "x", [10, 30, 100, 300, 1000],
                     ["10", "30", "100", "300", "1000"])
    _ascii_log_ticks(ax, "y", [10, 100, 1000], ["10", "100", "1000"])
    ax.set_xlim(1, HORIZON)
    ax.legend(loc="upper left", fontsize=5.7, handlelength=1.3,
              borderpad=0.2, labelspacing=0.22)

    return figkit.save(fig, "ch01_f02_regret")


def f03_ucb_snapshot():
    """One UCB1 run, frozen: estimates, confidence half-widths, true values."""
    mu, gap = _testbed(runs=1)
    runs, k = 1, K
    rng = np.random.default_rng(SEED + 31)
    N = np.zeros((runs, k))
    Q = np.zeros((runs, k))
    rows = np.arange(runs)
    snap_at = 200
    for t in range(snap_at + 1):
        bonus = UCB_C * np.sqrt(np.log(t + 1.0) / np.maximum(N, 1.0))
        idx = np.where(N > 0.0, Q + bonus, np.inf)
        a = (idx + 1e-9 * rng.standard_normal((runs, k))).argmax(axis=1)
        r = mu[rows, a] + rng.standard_normal(runs)
        N[rows, a] += 1.0
        Q[rows, a] += (r - Q[rows, a]) / N[rows, a]
    half = UCB_C * np.sqrt(np.log(snap_at + 1.0) / np.maximum(N, 1.0))
    a = (np.where(N > 0.0, Q + half, np.inf) + 1e-9).argmax(axis=1)

    fig, ax = figkit.new(3.30, 2.02)
    xs = np.arange(k)
    for i in range(k):
        ax.errorbar(xs[i], Q[0, i], yerr=half[0, i], color=C0, linewidth=0.7,
                    capsize=1.6, elinewidth=0.7, marker="o", markersize=2.4)
    ax.scatter(xs, mu[0], marker="_", s=26, color=C1, linewidth=1.0, zorder=3)
    ax.axhline(mu.max(), color=GREY, linewidth=0.7, linestyle=(0, (4, 2)))
    ax.plot([xs[a[0]]], [Q[0, a[0]]], marker="o", markersize=5.4,
            markerfacecolor="none", markeredgecolor=C3, markeredgewidth=1.0,
            linestyle="none")
    ax.set_xticks(xs)
    ax.set_xticklabels([str(i + 1) for i in range(k)])
    ax.set_xlabel("臂 $a$", fontsize=7.4)
    ax.set_ylabel("$Q_t(a)$ 与置信半宽", fontsize=7.4)
    ax.set_title(f"UCB1 第 {snap_at} 步的快照（单次运行）", fontsize=7.4)
    lo = min((Q[0] - half[0]).min(), mu[0].min())
    hi = max((Q[0] + half[0]).max(), mu[0].max())
    ax.set_ylim(lo - 0.35, hi + 0.35)
    ax.set_xlim(-0.55, k - 0.45)

    # The legend lives outside the axes: inside there is no free corner, since
    # whichever arm wins the index sits wherever its interval reaches.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], color=C0, linewidth=0.7, marker="o", markersize=2.4,
               label="$Q_t(a)\\pm\\beta_t$"),
        Line2D([], [], color=C1, linewidth=1.0, marker="_", markersize=5,
               linestyle="none", label="真实值 $q_*(a)$"),
        Line2D([], [], color=C3, linewidth=1.0, marker="o", markersize=5,
               markerfacecolor="none", linestyle="none", label="被选中臂"),
        Line2D([], [], color=GREY, linewidth=0.7, linestyle=(0, (4, 2)),
               label="$\\mu^*$"),
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=4,
               fontsize=5.4, frameon=False, handlelength=1.0,
               columnspacing=0.9, handletextpad=0.4)

    return figkit.save(fig, "ch01_f03_ucb")

    return figkit.save(fig, "ch01_f03_ucb")


def f04_context_bridge():
    """Contextual bandit on the left, MDP on the right: where the second half is."""
    fig, axes = figkit.new(4.30, 1.90, ncols=2)
    for ax, xlim in zip(axes, [(-0.15, 3.10), (-0.15, 3.25)]):
        figkit.blank(ax, xlim, (-0.25, 2.80))

    ax = axes[0]
    ax.text(1.50, 2.62, "上下文老虎机：一步决策", ha="center", fontsize=7.2,
            color=INK)
    figkit.box(ax, (0.02, 1.78), 0.95, 0.48, "上下文 $x_t$", fs=6.9,
               fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (1.28, 1.78), 1.05, 0.48, "策略 $\\pi(\\cdot\\mid x_t)$",
               fs=6.9, fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (1.28, 0.82), 1.05, 0.48, "奖励 $r_t$", fs=6.9,
               fc="#fdf1d8", ec="#c9a227")
    figkit.arrow(ax, (0.99, 2.02), (1.26, 2.02))
    ax.annotate("", xy=(1.80, 1.76), xytext=(1.80, 1.32),
                arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
    ax.text(1.52, 0.56, "下一刻的上下文独立抽样：\n$x_{t+1}\\sim\\rho$，与 $a_t$ 无关",
            ha="center", fontsize=6.2, color=GREY)

    ax = axes[1]
    ax.text(1.55, 2.62, "马尔可夫决策过程：序贯决策", ha="center", fontsize=7.2,
            color=INK)
    xs = [0.02, 1.12, 2.22]
    for i, x in enumerate(xs):
        figkit.box(ax, (x, 1.72), 0.86, 0.48, f"$s_{i}$", fs=7.2,
                   fc="#eef3fb", ec="#7d93b2")
        figkit.box(ax, (x + 0.06, 0.86), 0.74, 0.44, f"$a_{i}$", fs=7.0,
                   fc="#e8f0e4", ec="#7d9b6a")
        ax.annotate("", xy=(x + 0.43, 1.70), xytext=(x + 0.43, 1.32),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
        if i < 2:
            ax.annotate("", xy=(xs[i + 1] - 0.02, 1.96), xytext=(x + 0.88, 1.96),
                        arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=0.9))
            ax.text((x + 0.88 + xs[i + 1]) / 2, 2.04, "$P$", ha="center",
                    fontsize=6.8, color=INK)
        ax.text(x + 0.43, 0.62, f"$r_{{{i + 1}}}$", ha="center", fontsize=6.8,
                color=C4)
    ax.text(1.55, 0.30, "动作改变后继状态：信用分配与跨期探索",
            ha="center", fontsize=6.3, color=GREY)

    return figkit.save(fig, "ch01_f04_context_bridge")


def main() -> int:
    figkit.setup()
    # Linear axes with negative values print a real minus sign (U+2212) by
    # default; 宋体 has no such glyph, so the tick would become an empty box.
    import matplotlib
    matplotlib.rcParams["axes.unicode_minus"] = False

    curves = run_experiment()

    marks = (10, 100, 500, 1000, 5000)
    print("cumulative regret (mean over %d runs, seed %d)" % (RUNS, SEED))
    for kind, _label, _c, _ls in ALGOS:
        m = curves[kind].mean(axis=0)
        se = curves[kind].std(axis=0, ddof=1) / np.sqrt(RUNS)
        vals = "  ".join(f"{m[t - 1]:8.1f}" for t in marks)
        print(f"  {kind:9s} {vals}   se(T=5000)={se[-1]:6.2f}")
    t = np.arange(1, HORIZON + 1)
    print("log-log slope  [100,1000] / [1000,5000]:")
    for kind, _label, _c, _ls in ALGOS:
        m = curves[kind].mean(axis=0)
        s1 = np.polyfit(np.log(t[99:1000]), np.log(m[99:1000]), 1)[0]
        s2 = np.polyfit(np.log(t[999:]), np.log(m[999:]), 1)[0]
        rate = (m[-1] - m[-101]) / 100.0
        print(f"  {kind:9s} {s1:6.3f} / {s2:6.3f}   last-100-step rate={rate:6.3f}")

    for fn in (f01_problem, lambda: f02_regret(curves), f03_ucb_snapshot,
               f04_context_bridge):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
