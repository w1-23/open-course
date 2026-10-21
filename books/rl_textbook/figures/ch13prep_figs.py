"""Figures for the "language model as policy" prelude chapter.

Every figure is a schematic; nothing here is a data plot, so no seeds or
sample sizes are claimed.  Kept deliberately small: four panels, each one idea.
"""
from __future__ import annotations

import os
import sys

import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import figkit  # noqa: E402

C0 = figkit.C0
C1 = figkit.C1
C2 = figkit.C2
C3 = figkit.C3
C4 = figkit.C4
INK = figkit.INK
GREY = figkit.GREY
GRID = figkit.GRID


def f01_autoregressive():
    """One episode = one generation; the reward lands after the last token."""
    fig, ax = figkit.new(5.0, 2.15)
    figkit.blank(ax, (-0.15, 10.3), (-0.35, 3.05))

    figkit.box(ax, (0.05, 1.55), 1.30, 0.62, "提示\nx", fs=7.2,
               fc="#eef3fb", ec="#7d93b2")

    xs = [1.85, 3.05, 4.25, 5.45, 6.65]
    toks = ["y1", "y2", "y3", "y4", "eos"]
    for i, (x, t) in enumerate(zip(xs, toks)):
        fc = "#f7f8fa" if t != "eos" else "#fdf1d8"
        ec = GREY if t != "eos" else "#c9a227"
        figkit.box(ax, (x, 1.55), 0.86, 0.62, t, fs=7.2, fc=fc, ec=ec)

    figkit.arrow(ax, (1.37, 1.86), (1.83, 1.86), color=INK)
    for i in range(len(xs) - 1):
        figkit.arrow(ax, (xs[i] + 0.88, 1.86), (xs[i + 1] - 0.02, 1.86), color=INK)

    figkit.box(ax, (7.95, 1.55), 1.75, 0.62, "标量奖励\nr(x, y)", fs=7.2,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.arrow(ax, (7.53, 1.86), (7.93, 1.86), color=INK)

    # what each token is conditioned on
    ax.annotate("", xy=(1.85, 2.42), xytext=(7.53, 2.42),
                arrowprops=dict(arrowstyle="-", color=GREY, linewidth=0.6,
                                connectionstyle="arc3,rad=0.0"))
    ax.text(4.70, 2.58, "每一步只依赖已经生成的前缀，前缀越长条件越具体",
            ha="center", fontsize=6.6, color=GREY)

    # the episode bracket
    ax.annotate("", xy=(7.55, 0.92), xytext=(1.83, 0.92),
                arrowprops=dict(arrowstyle="<|-", color=C1, linewidth=0.7))
    ax.text(4.70, 0.68, "一次生成 = 一个回合：奖励在序列末尾才出现一次",
            ha="center", fontsize=6.6, color=C1)

    ax.text(4.70, 0.18, "词表就是动作空间；终止 = 生成 eos 或达到长度上限",
            ha="center", fontsize=6.6, color=INK)
    return figkit.save(fig, "ch13prep_f01_autoregressive")


def f02_three_models():
    """pi_old samples, pi_theta is updated, pi_ref only enters the KL term."""
    fig, ax = figkit.new(5.4, 2.45)
    figkit.blank(ax, (-0.15, 10.3), (-0.40, 3.35))

    figkit.box(ax, (0.10, 1.95), 2.05, 0.66, "旧策略\nπ_old：本轮固定", fs=7.3,
               fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (3.20, 1.95), 2.30, 0.66, "训练数据\n(prompt, completion, r)",
               fs=7.3, fc="#f7f8fa", ec=GREY)
    figkit.box(ax, (6.75, 1.95), 2.10, 0.66, "策略\nπ_θ：每轮更新", fs=7.3,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (6.75, 0.62), 2.10, 0.62, "参考\nπ_ref：全程冻结", fs=7.3,
               fc="#fdf1d8", ec="#c9a227")

    figkit.arrow(ax, (2.17, 2.28), (3.18, 2.28), color=INK)
    ax.text(2.67, 2.40, "采样", ha="center", fontsize=6.2, color=GREY)
    figkit.arrow(ax, (5.52, 2.28), (6.73, 2.28), color=INK)
    ax.text(6.12, 2.40, "比率 ρ", ha="center", fontsize=6.2, color=GREY)

    figkit.arrow(ax, (7.30, 1.93), (7.30, 1.28), color=INK)
    ax.text(7.45, 1.62, "KL(π_θ‖π_ref)", fontsize=6.2, color=C1)

    figkit.arrow(ax, (6.73, 1.55), (2.18, 1.32), color=GREY, rad=-0.10)
    ax.text(4.40, 0.98, "每轮结束 π_old ← π_θ", ha="center", fontsize=6.4,
            color=GREY)

    ax.text(5.05, 0.14, "π_old 只出现在比率的分母里；π_ref 只出现在 KL 项里；只有 π_θ 被更新",
            ha="center", fontsize=6.6, color=INK)
    return figkit.save(fig, "ch13prep_f02_three_models")


def f03_credit_broadcast():
    """One scalar reward is broadcast to every token: coarse credit assignment."""
    fig, ax = figkit.new(4.9, 2.18)
    figkit.blank(ax, (-0.15, 9.5), (-0.38, 2.85))

    ax.text(0.05, 2.44, "序列级奖励", fontsize=6.8, color=INK)
    figkit.box(ax, (0.05, 1.62), 1.45, 0.54, "r = 1.7", fs=7.2,
               fc="#e8f0e4", ec="#7d9b6a")

    xs = [2.65, 4.10, 5.55, 7.00]
    for x in xs:
        figkit.box(ax, (x, 0.52), 0.95, 0.48, "token", fs=6.6,
                   fc="#f7f8fa", ec=GREY)
        ax.annotate("", xy=(x + 0.47, 1.04), xytext=(1.55, 1.66),
                    arrowprops=dict(arrowstyle="-|>", color=C1, linewidth=0.7,
                                    connectionstyle="arc3,rad=-0.12"))

    ax.text(4.55, 1.44, "同一标量广播到每个 token", ha="center", fontsize=6.6,
            color=C1)
    ax.text(0.05, 0.20, "粗信用分配：哪个 token 让奖励变高，这一层看不出来",
            fontsize=6.6, color=C4)
    return figkit.save(fig, "ch13prep_f03_credit_broadcast")


def f04_reward_sources():
    """Reliability against cost for the four reward sources."""
    fig, ax = figkit.new(4.3, 2.35)
    figkit.blank(ax, (0.0, 1.0), (0.0, 1.0))

    ax.set_xlim(0.02, 1.02)
    ax.set_ylim(0.06, 1.02)
    ax.set_xlabel("获取代价（标注 / 计算 / 延迟）", fontsize=7.0)
    ax.set_ylabel("信号可靠性", fontsize=7.0)
    ax.set_xticks([0.2, 0.8])
    ax.set_xticklabels(["低", "高"], fontsize=6.8)
    ax.set_yticks([0.3, 0.9])
    ax.set_yticklabels(["低", "高"], fontsize=6.8)
    ax.grid(True, color=GRID, linewidth=0.5, linestyle=(0, (3, 3)))

    pts = [
        (0.20, 0.30, "规则（格式/长度）", C1, 0.05, 0.02),
        (0.34, 0.80, "验证器（单测/判题）", C3, 0.05, 0.03),
        (0.70, 0.52, "奖励模型（偏好拟合）", C0, 0.05, 0.03),
        (0.84, 0.88, "工具返回（检索/执行）", C2, -0.30, -0.10),
    ]
    for x, y, name, color, dx, dy in pts:
        ax.plot([x], [y], "o", color=color, markersize=5)
        ax.text(x + dx, y + dy, name, fontsize=6.3, color=color, ha="left")

    ax.text(0.04, 0.10, "假阴：漏掉好答案；假阳：放过坏答案", fontsize=6.0, color=GREY)
    ax.text(0.52, 0.96, "可验证 ≠ 正确", fontsize=6.2, color=GREY)
    return figkit.save(fig, "ch13prep_f04_reward_sources")


def main() -> int:
    figkit.setup()
    for fn in (f01_autoregressive, f02_three_models, f03_credit_broadcast,
               f04_reward_sources):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
