"""Figures for chapter 2 (马尔可夫决策过程与贝尔曼理论).

Run from the build directory:

    python figures\\ch02_figs.py

Every figure is vector SVG written into ``figures/out``; the layout stage keeps
it as vector, so the diagrams stay sharp at any zoom.
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


def _blank(ax, xlim, ylim):
    figkit.blank(ax, xlim, ylim)


def f01_bandit_to_mdp():
    fig, axes = figkit.new(4.30, 1.85, ncols=2)
    for ax, xlim in zip(axes, [(-0.2, 2.9), (-0.2, 3.3)]):
        _blank(ax, xlim, (-0.15, 2.75))

    # ---- left: one-step decision -------------------------------------------
    ax = axes[0]
    ax.text(1.35, 2.58, "老虎机 / 上下文老虎机", ha="center", fontsize=7.6, color=INK)
    figkit.box(ax, (0.05, 1.62), 0.92, 0.52, "上下文 $x_t$", fc="#eef3fb", ec="#7d93b2", fs=7.0)
    figkit.box(ax, (1.62, 1.62), 0.92, 0.52, "动作 $a_t$", fc="#e8f0e4", ec="#7d9b6a", fs=7.0)
    figkit.box(ax, (0.86, 0.62), 1.30, 0.52, "奖励 $r_t$", fc="#fdf1d8", ec="#c9a227", fs=7.0)
    figkit.arrow(ax, (0.98, 1.88), (1.60, 1.88), color=GREY)
    ax.annotate("", xy=(1.55, 1.58), xytext=(1.55, 1.16),
                arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
    ax.annotate("", xy=(1.60, 1.16), xytext=(1.34, 1.58),
                arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
    ax.text(1.35, 0.30, "每步独立，状态不变", ha="center", fontsize=6.8, color=GREY)

    # ---- right: sequential decision ----------------------------------------
    ax = axes[1]
    ax.text(1.55, 2.58, "马尔可夫决策过程", ha="center", fontsize=7.6, color=INK)
    xs = [0.02, 1.05, 2.08]
    for i, x in enumerate(xs):
        figkit.box(ax, (x, 1.60), 0.92, 0.52, f"$s_{i}$", fc="#eef3fb", ec="#7d93b2", fs=7.4)
        figkit.box(ax, (x + 0.10, 0.86), 0.72, 0.42, f"$a_{i}$", fc="#e8f0e4", ec="#7d9b6a", fs=7.4)
        ax.annotate("", xy=(x + 0.46, 1.58), xytext=(x + 0.46, 1.30),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
        if i < 2:
            ax.annotate("", xy=(xs[i + 1] - 0.02, 1.86), xytext=(x + 0.94, 1.86),
                        arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
            ax.text((x + 0.94 + xs[i + 1]) / 2, 1.94, "$P$", ha="center",
                    fontsize=7.0, color=GREY)
        ax.text(x + 0.46, 0.62, f"$r_{{{i + 1}}}$", ha="center", fontsize=7.2, color=C4)
    ax.text(1.55, 0.24, "选择改变后继局面", ha="center", fontsize=6.8, color=GREY)

    return figkit.save(fig, "ch02_f01_bandit_to_mdp")


def f02_loop():
    fig, ax = figkit.new(3.55, 1.95)
    _blank(ax, (-0.15, 3.65), (-0.20, 2.85))

    figkit.box(ax, (0.10, 1.55), 1.05, 0.66, "智能体\n$\\pi(a\\mid s)$", fs=7.4,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (2.10, 1.55), 1.05, 0.66, "环境\n$P,\\ r$", fs=7.4,
               fc="#eef3fb", ec="#7d93b2")

    # action travels along the top lane, state/reward come back along the bottom
    # lane: the two directions never overlap, so the labels stay readable.
    ax.annotate("", xy=(2.05, 2.05), xytext=(1.20, 2.05),
                arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=0.9))
    ax.text(1.62, 2.12, "$a_t$", ha="center", fontsize=7.6, color=INK)
    ax.annotate("", xy=(1.20, 1.70), xytext=(2.05, 1.70),
                arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=0.9))
    ax.text(1.62, 1.40, "$s_{t+1},\\ r_{t+1}$", ha="center", fontsize=7.2, color=INK)

    ax.text(0.62, 2.46, "策略", ha="center", fontsize=7.0, color=GREY)
    ax.text(2.62, 2.46, "转移动力学", ha="center", fontsize=7.0, color=GREY)

    # the three bookkeeping flags of one transition
    y = 0.62
    figkit.box(ax, (0.06, y), 1.00, 0.42, "终止 done", fs=6.6, fc="#fdecea", ec="#c0392b")
    figkit.box(ax, (1.28, y), 1.05, 0.42, "截断 truncated", fs=6.6, fc="#fdf1d8", ec="#c9a227")
    figkit.box(ax, (2.52, y), 0.95, 0.42, "自举掩码", fs=6.6, fc="#eef3fb", ec="#7d93b2")
    ax.text(1.82, 0.26, "两个布尔量必须分开记录，否则截断处会引入偏差",
            ha="center", fontsize=6.4, color=GREY)

    return figkit.save(fig, "ch02_f02_loop")


def f03_contraction():
    """Two value-iteration runs converging to the same fixed point."""
    gamma, r = 0.8, 1.0
    v_star = r / (1.0 - gamma)          # exact fixed point of V = r + gamma V
    iters = 30
    traj_a, traj_b, gap = [], [], []
    va, vb = 0.0, 9.0                   # two very different initial guesses
    for _ in range(iters):
        traj_a.append(va)
        traj_b.append(vb)
        gap.append(abs(va - vb))
        va = r + gamma * va
        vb = r + gamma * vb

    fig, axes = figkit.new(4.10, 1.95, ncols=2)

    ax = axes[0]
    ax.plot(range(iters), traj_a, color=C0, label="$V_0=0$")
    ax.plot(range(iters), traj_b, color=C1, label="$V_0=9$")
    ax.axhline(v_star, color=GREY, linewidth=0.8, linestyle=(0, (4, 2)))
    ax.text(iters * 0.42, v_star + 0.45, f"不动点 ${v_star:.1f}$",
            fontsize=7.0, color=GREY)
    ax.set_xlabel("迭代轮数 $k$")
    ax.set_ylabel("$V_k$")
    ax.set_ylim(0, 10.4)
    ax.legend(loc="lower right", fontsize=7.0)
    ax.set_title("两条初值轨迹", fontsize=8.0)

    ax = axes[1]
    ax.semilogy(range(iters), gap, color=C2, label="两条轨迹的距离")
    ax.plot(range(iters), [9.0 * 0.8 ** k for k in range(iters)],
            color=GREY, linewidth=0.8, linestyle=(0, (4, 2)), label="$\\propto\\gamma^k$")
    ax.set_xlabel("迭代轮数 $k$")
    ax.set_ylabel("$\\Delta_k$")
    ax.legend(loc="upper right", fontsize=7.0)
    ax.set_title("距离按 $\\gamma$ 几何衰减", fontsize=8.0)
    ax.set_ylim(1e-4, 20)
    # Log ticks are labelled by hand: matplotlib's default log formatter emits
    # mathtext with a real minus sign (U+2212), which the Chinese font of this
    # book does not carry, so the tick would print as an empty box.
    ax.set_yticks([1e-4, 1e-2, 1.0])
    ax.set_yticklabels(["1e-4", "1e-2", "1"])

    return figkit.save(fig, "ch02_f03_contraction")


def f04_max_operator():
    fig, ax = figkit.new(3.45, 2.05)
    _blank(ax, (-0.15, 3.60), (-0.30, 2.95))

    figkit.box(ax, (0.02, 1.20), 0.72, 0.55, "状态 $s$", fs=7.2,
               fc="#eef3fb", ec="#7d93b2")
    branches = [("$a_1$", "$r(s,a_1)+\\gamma\\sum_{s'}P V$", C0, 2.20),
                ("$a_2$", "$r(s,a_2)+\\gamma\\sum_{s'}P V$", C2, 1.36),
                ("$a_3$", "$r(s,a_3)+\\gamma\\sum_{s'}P V$", C3, 0.52)]
    for label, expr, color, y in branches:
        ax.annotate("", xy=(1.26, y + 0.24), xytext=(0.78, 1.47),
                    arrowprops=dict(arrowstyle="-|>", color=color, linewidth=0.8))
        ax.text(0.92, y + 0.40, label, fontsize=7.2, color=color, ha="center")
        ax.add_patch(FancyBboxPatch((1.28, y), 1.62, 0.48,
                                    boxstyle="round,pad=0.01,rounding_size=0.02",
                                    linewidth=0.7, facecolor="#f7f8fa",
                                    edgecolor=color))
        ax.text(1.28 + 0.81, y + 0.24, expr, ha="center", va="center",
                fontsize=6.6, color=INK)
        ax.annotate("", xy=(2.96, 1.47), xytext=(2.92, y + 0.24),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))

    figkit.box(ax, (2.98, 1.20), 0.60, 0.55, "$\\max$", fs=9.0,
               fc="#fdf1d8", ec="#c9a227")
    ax.text(1.60, 2.78, "$(T^*V)(s)$：逐点取最大", ha="center", fontsize=7.2, color=INK)
    ax.text(1.72, -0.10, "取最大使方程非线性，但仍是 γ-压缩",
            ha="center", fontsize=6.6, color=GREY)

    return figkit.save(fig, "ch02_f04_max_operator")


def f05_residual_bound():
    """The 1/(1-gamma) amplification of a fixed Bellman residual."""
    gammas = np.linspace(0.0, 0.995, 400)
    delta = 0.1
    bound = delta / (1.0 - gammas)

    fig, ax = figkit.new(3.45, 1.95)
    ax.semilogy(gammas, bound, color=C0, label="上界（δ 固定为 0.1）")
    for g in (0.9, 0.99):
        ax.axvline(g, color=GREY, linewidth=0.7, linestyle=(0, (3, 2)))
        ax.text(g - 0.012, 0.10, f"${g}$", ha="right", fontsize=6.6,
                color=GREY, va="bottom")
    ax.axhline(delta, color=C3, linewidth=0.8, linestyle=(0, (4, 2)),
               label="残差 δ = 0.1 本身")
    ax.set_xlabel("折扣因子 $\\gamma$")
    ax.set_ylabel("误差上界")
    ax.set_ylim(0.08, 30)
    ax.set_xlim(0, 1.0)
    ax.set_yticks([0.1, 1.0, 10.0])
    ax.set_yticklabels(["0.1", "1", "10"])
    ax.legend(loc="upper left", fontsize=6.6)
    ax.set_title("同样的残差，随 $\\gamma\\to1$ 放大", fontsize=8.0)

    return figkit.save(fig, "ch02_f05_residual_bound")


def main() -> int:
    figkit.setup()
    for fn in (f01_bandit_to_mdp, f02_loop, f03_contraction,
               f04_max_operator, f05_residual_bound):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
