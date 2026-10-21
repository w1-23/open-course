"""第 0 章（全书导航）的图。四幅全部是矢量，坐标用 0–100 的绝对网格，避免裁切。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import figkit  # noqa: E402

figkit.setup()

C0, C1, C2, C3 = figkit.C0, figkit.C1, figkit.C2, figkit.C3
INK, GREY = figkit.INK, figkit.GREY
BOX_FILL, BOX_EDGE = "#f1f4f8", "#395675"


def f01_map():
    """四部分十二章的横向地图：每部分一列，列头写该部分的核心问题。"""
    fig, ax = figkit.new(5.35, 2.75)
    figkit.blank(ax, (0, 100), (0, 100))

    parts = [
        ("第 1 部分", "数学与决策基础\n问题的数学表述", ["1 多臂老虎机与探索", "2 MDP 与 Bellman", "3 DP / MC / TD"]),
        ("第 2 部分", "经典与深度强化学习\n用数据改进策略", ["4 函数逼近\n与离策略", "5 策略梯度与 PPO", "6 DQN 与连续控制"]),
        ("第 3 部分", "模型、规划与约束\n扩展决策结构", ["7 模型、规划与搜索", "8 离线 RL 与评估", "9 多智能体与安全"]),
        ("第 4 部分", "语言模型与自主智能体\n序列决策与工具使用", ["10 RLHF 与偏好优化", "11 RLVR 与 GRPO", "12 Agentic RL\n与持续学习"]),
    ]
    xs = [1.0, 25.6, 50.2, 74.8]
    w = 21.2
    for x, (head, question, items) in zip(xs, parts):
        figkit.box(ax, (x, 80), w, 12, head, fc=C0, ec=C0, fs=8.7)
        ax.texts[-1].set_color("white")
        for run in ax.texts[-1].get_text().split("\n"):
            pass
        ax.text(x + w / 2, 72.0, question, ha="center", va="top",
                fontsize=8.0, color=INK, linespacing=1.35)
        for k, item in enumerate(items):
            y = 42 - k * 14.5
            figkit.box(ax, (x, y), w, 11.4, item, fc=BOX_FILL, ec=BOX_EDGE, fs=8.2)
    for x in (22.6, 47.2, 71.8):
        figkit.arrow(ax, (x, 86), (x + 2.4, 86), color=GREY)
    ax.text(50, 4.0, "各部分依次扩展表示方法、数据条件与任务结构",
            ha="center", va="center", fontsize=8.0, color=INK)
    figkit.save(fig, "ch00_f01_map")


def f02_ladder():
    """理论分层阶梯：四级，每级写"能证明什么"与"不能外推什么"。"""
    fig, ax = figkit.new(4.35, 2.2)
    figkit.blank(ax, (0, 100), (0, 100))

    rows = [
        ("表格法", "有限 S、A，逐项存值", "收敛、最优性、误差界都可证", C3),
        ("线性函数逼近", "Φ 满列秩、线性空间", "投影不动点、TD 不动点、MSPBE 有闭式", C0),
        ("非线性逼近 + 自举 + 离策略", "神经网络", "只有经验规律：可能不稳定（致命三要素）", C1),
        ("语言模型策略优化", "巨大动作空间、序列奖励", "只有[经验规律]与[渐近]；无收敛定理", C2),
    ]
    y0, h, gap = 76.0, 15.0, 5.0
    for i, (name, cond, claim, color) in enumerate(rows):
        y = y0 - i * (h + gap)
        figkit.box(ax, (2.0, y), 20.0, h, name, fc=color, ec=color, fs=7.0)
        ax.texts[-1].set_color("white")
        ax.text(24.0, y + h - 3.2, cond, ha="left", va="center", fontsize=6.2, color=GREY)
        ax.text(24.0, y + h - 9.4, claim, ha="left", va="center", fontsize=6.4, color=INK)
        if i < len(rows) - 1:
            figkit.arrow(ax, (12.0, y - 0.4), (12.0, y - gap + 0.4), color=GREY)
    ax.text(2.0, 97.0, "定理的前提决定其适用范围", ha="left", va="center",
            fontsize=7.2, color=INK)
    ax.text(2.0, 3.0, "越往下，能搬用的定理越少；把上一级的结论直接下移，是本书反复纠正的错误",
            ha="left", va="center", fontsize=6.2, color=GREY)
    figkit.save(fig, "ch00_f02_ladder")


def f03_objects():
    """六个反复出现的对象及其流向。"""
    fig, ax = figkit.new(4.35, 1.95)
    figkit.blank(ax, (0, 100), (0, 100))

    figkit.box(ax, (2, 62), 20, 12, "环境 / 数据", fc="#e8f0e4", ec="#7d9b6a", fs=7.0)
    figkit.box(ax, (2, 34), 20, 12, "策略 π", fc=BOX_FILL, ec=BOX_EDGE, fs=7.0)
    figkit.box(ax, (39, 62), 22, 12, "价值 V / Q", fc=BOX_FILL, ec=BOX_EDGE, fs=7.0)
    figkit.box(ax, (39, 34), 22, 12, "模型 P、R（学出来的）", fc="#fdf1d8", ec="#c9a227", fs=6.6)
    figkit.box(ax, (76, 62), 21, 12, "目标函数 J", fc=BOX_FILL, ec=BOX_EDGE, fs=7.0)
    figkit.box(ax, (76, 34), 21, 12, "评估与诊断", fc="#f3eefb", ec="#7a5195", fs=7.0)

    figkit.arrow(ax, (22, 70), (39, 70), color=GREY, text="采样", fs=6.0)
    figkit.arrow(ax, (22, 40), (39, 40), color=GREY, text="拟合", fs=6.0)
    figkit.arrow(ax, (50, 62), (50, 46), color=GREY, text="自举", fs=6.0)
    figkit.arrow(ax, (39, 70), (39, 46), color=GREY, text="规划", fs=6.0)
    figkit.arrow(ax, (61, 70), (76, 70), color=GREY, text="估计", fs=6.0)
    figkit.arrow(ax, (61, 40), (76, 40), color=GREY, text="回放", fs=6.0)
    figkit.arrow(ax, (86.5, 62), (86.5, 46), color=GREY, text="打分", fs=6.0)
    ax.text(50, 8, "六个对象在每一章都出现，变的只是「哪些是已知的、哪些要学」",
            ha="center", va="center", fontsize=6.4, color=GREY)
    figkit.save(fig, "ch00_f03_objects")


def f04_route():
    """三条阅读路线。"""
    fig, ax = figkit.new(4.35, 1.7)
    figkit.blank(ax, (0, 100), (0, 100))

    routes = [
        ("速查", "2.1–2.4", "5.1–5.3", "第 10、11 章", C3),
        ("系统", "第 1–3 章", "第 4–6 章", "第 7–9 章 → 预备章 → 10–12 章", C0),
        ("研究", "4.3  投影与半梯度", "8.5  离线评估", "10.3–10.5  DPO 与等价性 / 11.2 GRPO", C2),
    ]
    y = 76.0
    for name, a, b, c, color in routes:
        figkit.box(ax, (1.5, y), 13.0, 12.0, name, fc=color, ec=color, fs=7.2)
        ax.texts[-1].set_color("white")
        figkit.box(ax, (17.0, y), 23.0, 12.0, a, fc="white", ec=GREY, fs=6.2)
        figkit.box(ax, (42.0, y), 23.0, 12.0, b, fc="white", ec=GREY, fs=6.2)
        figkit.box(ax, (67.0, y), 31.0, 12.0, c, fc="white", ec=GREY, fs=6.2)
        y -= 17.0
    ax.text(50, 4.0, "三条路线共用同一套符号与编号；跳读不会遇到未定义的记号",
            ha="center", va="center", fontsize=6.2, color=GREY)
    figkit.save(fig, "ch00_f04_route")


if __name__ == "__main__":
    f01_map()
    f02_ladder()
    f03_objects()
    f04_route()
