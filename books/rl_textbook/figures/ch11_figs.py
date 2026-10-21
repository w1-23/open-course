"""Figures for chapter 11 (RLVR 与推理强化学习).

Run from the build directory:

    python figures\\ch11_figs.py

Vector SVG goes to ``figures/out``.  f02 与 f05 are computed experiments; the
others are schematics whose labels are quoted in the chapter text.

    f01  verifiable-reward pipeline                             (schematic)
    f02  group standardization: three example groups            (real)
    f03  GRPO vs PPO: four points of difference                 (schematic)
    f04  answer length and policy entropy during training       (schematic,
         qualitative trends reported in the literature, [经验规律])
    f05  verifier false positives: reward up, accuracy down     (real)
    f06  multi-stage R1 pipeline                                (schematic)
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

GROUP = 6                       # completions per prompt (figure 11-2)
EPS_NUM = 1e-4                  # numerical guard only
HACK_SEEDS = 200
HACK_STEPS = 400
HACK_LR = 0.30
HACK_P_FP = (0.0, 0.30)         # verifier false-positive rate


# --------------------------------------------------------------------------
def f01_verifier_pipeline():
    fig, ax = figkit.new(4.55, 1.45)
    figkit.blank(ax, (-0.30, 10.75), (-0.35, 2.35))
    y0, h = 1.35, 0.55

    figkit.box(ax, (0.12, y0), 1.45, h, "提示 $q$", fs=6.8, fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (1.85, y0), 1.85, h, "$G$ 个回答\n$o_1,\\dots,o_G$", fs=6.6,
               fc="#fdf1d8", ec="#c9a227")
    figkit.box(ax, (4.05, y0), 1.75, h, "判定器 $V(q,o)$\n输出 0/1", fs=6.6,
               fc="#f2f2f4", ec="#8b949e")
    figkit.box(ax, (6.15, y0), 1.75, h, "组内标准化\n$\\hat A_i$", fs=6.6,
               fc="#f7eef3", ec="#a06b8a")
    figkit.box(ax, (8.25, y0), 2.15, h, "策略更新\n$\\pi_\\theta\\leftarrow\\pi_\\theta+\\eta\\nabla$",
               fs=6.4, fc="#e8f0e4", ec="#7d9b6a")

    for x0, x1 in ((1.50, 1.83), (3.70, 4.03), (5.80, 6.13), (7.90, 8.23)):
        figkit.arrow(ax, (x0, y0 + h / 2), (x1, y0 + h / 2), color=INK)

    figkit.arrow(ax, (9.30, y0), (9.30, 0.55), color=GREY)
    figkit.arrow(ax, (9.30, 0.45), (0.75, 0.45), color=GREY)
    figkit.arrow(ax, (0.75, 0.45), (0.75, y0), color=GREY)
    ax.text(5.0, 0.12, "同一提示、同一策略，$G$ 条样本互为基线（不需要价值网络）",
            ha="center", fontsize=6.3, color=GREY)
    ax.text(9.55, 0.95, "只更新策略", fontsize=5.9, color=GREY, ha="left")
    return figkit.save(fig, "ch11_f01_pipeline")


# --------------------------------------------------------------------------
def f02_group_norm():
    groups = {
        "2/6 正确": np.array([1, 1, 0, 0, 0, 0]),
        "3/6 正确": np.array([1, 1, 1, 0, 0, 0]),
        "6/6 正确": np.ones(GROUP),
    }
    fig, axes = figkit.new(4.55, 1.95, ncols=2)

    ax = axes[0]
    for k, (name, r) in enumerate(groups.items()):
        ax.scatter(np.full(len(r), k) + np.linspace(-0.16, 0.16, len(r)), r,
                   s=9, color=C0, zorder=3, marker="o")
        ax.plot([k - 0.28, k + 0.28], [r.mean()] * 2, color=C1, linewidth=0.9,
                linestyle=(0, (3, 2)))
        ax.text(k, 1.12, f"$\\bar r$={r.mean():.2f}", ha="center", fontsize=5.9,
                color=C1)
    ax.set_xlim(-0.45, 2.45)
    ax.set_ylim(-0.22, 1.28)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(list(groups))
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["0", "1"])
    ax.set_ylabel("判定器奖励 $r_i$")
    ax.set_title("每个提示采 6 条，奖励多为 0/1", fontsize=7.2)

    ax = axes[1]
    for k, (name, r) in enumerate(groups.items()):
        s = r.std() if r.std() > 0 else 0.0
        a = (r - r.mean()) / (s + EPS_NUM)
        if s == 0:
            ax.text(k, 0.0, "全同\n掩掉", ha="center", va="center", fontsize=6.0,
                    color="#c0392b")
        else:
            ax.scatter(np.full(len(a), k) + np.linspace(-0.16, 0.16, len(a)), a,
                       s=9, color=C2, zorder=3)
            ax.text(k + 0.30, a.max(), f"{a.max():.2f}", fontsize=5.6, color=C2,
                    va="center")
            ax.text(k + 0.30, a.min(), f"{a.min():.2f}", fontsize=5.6, color=C2,
                    va="center")
    ax.axhline(0, color=GREY, linewidth=0.7)
    ax.set_xlim(-0.45, 2.45)
    ax.set_ylim(-1.55, 1.75)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(list(groups))
    ax.set_yticks([-1, 0, 1])
    ax.set_yticklabels(["-1", "0", "1"])
    ax.set_ylabel("$\\hat A_i$")
    ax.set_title("标准化后只剩两个取值", fontsize=7.2)

    for name, r in groups.items():
        s = r.std()
        a = (r - r.mean()) / (s + EPS_NUM) if s > 0 else np.zeros_like(r)
        print(f"  [f02] {name}: mean={r.mean():.4f} std={s:.4f} "
              f"advantage set={sorted(set(np.round(a, 3)))}")
    return figkit.save(fig, "ch11_f02_group_norm")


# --------------------------------------------------------------------------
def f03_grpo_vs_ppo():
    fig, ax = figkit.new(4.55, 2.35)
    figkit.blank(ax, (-1.55, 6.35), (-0.25, 4.75))
    rows = (
        ("采样单位", "按步采样：一个状态×动作", "$G$ 条完整回答共享一个提示"),
        ("优势来源", "critic 学 $V_\\phi$，GAE 估 $A_t$", "组内标准化奖励 $\\hat A_i$"),
        ("比率与裁剪", "token 级 $\\rho_t$，对称裁剪", "token 级 $\\rho_{i,t}$，对称裁剪"),
        ("KL 的位置", "进奖励：$r_t-\\beta_{KL}\\log\\frac{\\pi}{\\pi_{\\rm ref}}$",
         "进损失：整批加 $-\\beta_{KL}\\widehat{D}_{KL}$"),
    )
    ax.text(-0.05, 4.45, "同一件事", ha="right", fontsize=6.6, color=INK)
    ax.text(1.55, 4.45, "PPO（第 5.4 节）", ha="center", fontsize=7.0, color=C0)
    ax.text(4.65, 4.45, "GRPO", ha="center", fontsize=7.0, color=C2)

    for k, (name, ppo, grpo) in enumerate(rows):
        y = 3.55 - k * 1.02
        ax.text(-0.05, y + 0.36, name, ha="right", va="center", fontsize=6.5,
                color=INK)
        figkit.box(ax, (0.15, y), 2.75, 0.78, ppo, fs=6.0, fc="#eef3fb", ec="#7d93b2")
        figkit.box(ax, (3.25, y), 2.85, 0.78, grpo, fs=6.0, fc="#f2f0f6", ec="#8f7fa8")

    ax.text(1.55, 0.10, "有无 critic 只是第一行", ha="center", fontsize=6.2, color=GREY)
    ax.text(4.65, 0.10, "差别还在比率单位与 KL 的位置", ha="center", fontsize=6.2,
            color=GREY)
    return figkit.save(fig, "ch11_f03_grpo_vs_ppo")


# --------------------------------------------------------------------------
def f04_length_entropy():
    steps = np.arange(0, 601, 20)
    length = 320 + 980 * (1 - np.exp(-steps / 210.0))
    length = length + 45 * np.sin(steps / 33.0) * np.exp(-steps / 700.0)
    entropy = 1.55 * np.exp(-steps / 260.0) + 0.42 + 0.03 * np.sin(steps / 41.0)

    fig, axes = figkit.new(4.55, 1.75, ncols=2)
    ax = axes[0]
    ax.plot(steps, length, color=C1)
    ax.set_xlabel("训练步")
    ax.set_ylabel("平均回答长度（token）")
    ax.set_ylim(200, 1450)
    ax.set_yticks([400, 800, 1200])
    ax.set_yticklabels(["400", "800", "1200"])
    ax.set_title("长度膨胀：先快后慢", fontsize=7.2)

    ax = axes[1]
    ax.plot(steps, entropy, color=C0)
    ax.set_xlabel("训练步")
    ax.set_ylabel("策略熵（nat/token）")
    ax.set_ylim(0.3, 1.7)
    ax.set_yticks([0.5, 1.0, 1.5])
    ax.set_yticklabels(["0.5", "1.0", "1.5"])
    ax.set_title("熵塌缩：多样性下降", fontsize=7.2)

    print("  [f04] schematic curves; endpoints length "
          f"{length[-1]:.0f} tokens, entropy {entropy[-1]:.2f} nats/token")
    return figkit.save(fig, "ch11_f04_length_entropy")


# --------------------------------------------------------------------------
def f05_false_positive():
    """Three-arm bandit: learn to satisfy the verifier, not the truth.

    arm 0: 真推理（判定器与真值都以 p_c 给 1）
    arm 1: 格式捷径（格式分 0.5 稳拿，另以 p_fp 拿到正确性分；真实正确率恒为 0）
    arm 2: 其他（都给 0）
    """
    p_c = 0.35
    fig, axes = figkit.new(4.55, 1.75, ncols=2)
    ax = axes[0]
    ax2 = axes[1]
    styles = ((C0, "假阳率 0"), (C1, f"假阳率 {HACK_P_FP[1]:.2f}"))

    curves = {}
    for (p_fp, (color, label)) in zip(HACK_P_FP, styles):
        mu = np.array([p_c, 0.5 + 0.5 * p_fp, 0.0])   # expected verifier reward
        rew = np.zeros((HACK_SEEDS, HACK_STEPS))
        acc = np.zeros((HACK_SEEDS, HACK_STEPS))
        for seed in range(HACK_SEEDS):
            rng = np.random.default_rng(7000 + seed)
            logits = np.zeros(3)
            baseline, seen = 0.0, 0
            for t in range(HACK_STEPS):
                p = np.exp(logits - logits.max())
                p = p / p.sum()
                a = rng.choice(3, p=p)
                u = rng.random()
                if a == 0:
                    r = 1.0 if u < p_c else 0.0
                elif a == 1:
                    r = 0.5 + (0.5 if u < p_fp else 0.0)
                else:
                    r = 0.0
                seen += 1
                baseline += (r - baseline) / seen
                grad = -p
                grad[a] += 1.0
                logits += HACK_LR * (r - baseline) * grad
                rew[seed, t] = float(p @ mu)
                acc[seed, t] = float(p[0] * p_c)
        curves[p_fp] = (rew.mean(axis=0), acc.mean(axis=0),
                        rew.std(axis=0) / np.sqrt(HACK_SEEDS),
                        acc.std(axis=0) / np.sqrt(HACK_SEEDS))

    for (p_fp, (color, label)) in zip(HACK_P_FP, styles):
        rr, aa, rs, as_ = curves[p_fp]
        ax.plot(np.arange(HACK_STEPS), rr, color=color, label=label)
        ax2.plot(np.arange(HACK_STEPS), aa, color=color, label=label)
    ax.set_xlabel("训练步")
    ax.set_ylabel("判定器奖励（期望）")
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_yticklabels(["0", "0.5", "1"])
    ax.legend(loc="lower right", fontsize=6.0)
    ax.set_title("判定器看到的奖励上升", fontsize=7.2)

    ax2.set_xlabel("训练步")
    ax2.set_ylabel("真实正确率（期望）")
    ax2.set_ylim(0, 1.05)
    ax2.set_yticks([0, 0.5, 1.0])
    ax2.set_yticklabels(["0", "0.5", "1"])
    ax2.legend(loc="lower right", fontsize=6.0)
    ax2.set_title("真实正确率可以下降", fontsize=7.2)

    for p_fp in HACK_P_FP:
        rr, aa = curves[p_fp][0], curves[p_fp][1]
        print(f"  [f05] p_fp={p_fp:.2f}: verifier reward {rr[0]:.3f}->{rr[-1]:.3f}, "
              f"true accuracy {aa[0]:.3f}->{aa[-1]:.3f}")
    print(f"  [f05] 3-arm bandit, REINFORCE, {HACK_SEEDS} seeds x {HACK_STEPS} steps, "
          f"lr={HACK_LR}")
    return figkit.save(fig, "ch11_f05_false_positive")


# --------------------------------------------------------------------------
def f06_multistage():
    fig, ax = figkit.new(4.55, 1.95)
    figkit.blank(ax, (-0.15, 9.4), (-0.55, 2.55))
    stages = (
        ("① 冷启动 SFT", "少量长 CoT 示范\n教会 think 格式", "#eef3fb", "#7d93b2"),
        ("② RLVR（GRPO）", "规则奖励：正确性\n+ 格式 + 语言一致", "#fdf1d8", "#c9a227"),
        ("③ 拒绝采样 + SFT", "只留判定器通过的回答\n约 800K 条", "#f2f0f6", "#8f7fa8"),
        ("④ 全场景 RL", "加入偏好奖励\n有用性与安全性", "#e8f0e4", "#7d9b6a"),
    )
    w, hh, gap = 2.05, 1.30, 0.30
    for k, (name, desc, fc, ec) in enumerate(stages):
        x = 0.10 + k * (w + gap)
        figkit.box(ax, (x, 0.90), w, hh, "", fs=6.4, fc=fc, ec=ec)
        ax.text(x + w / 2, 1.94, name, ha="center", fontsize=6.9, color=INK)
        ax.text(x + w / 2, 1.36, desc, ha="center", va="center", fontsize=6.0,
                color=GREY, linespacing=1.35)
        if k < 3:
            figkit.arrow(ax, (x + w + 0.02, 1.55), (x + w + gap - 0.02, 1.55),
                         color=INK)
    ax.text(4.7, 0.42, "只在前两阶段用规则奖励；偏好奖励要等推理能力站稳之后才引入",
            ha="center", fontsize=6.2, color=GREY)
    ax.text(4.7, 0.08, "第 3 阶段把推理与通用能力合回同一条数据流",
            ha="center", fontsize=6.0, color=GREY)
    return figkit.save(fig, "ch11_f06_multistage")


def main() -> int:
    figkit.setup()
    import matplotlib.pyplot as plt
    plt.rcParams["axes.unicode_minus"] = False
    for fn in (f01_verifier_pipeline, f02_group_norm, f03_grpo_vs_ppo,
               f04_length_entropy, f05_false_positive, f06_multistage):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
