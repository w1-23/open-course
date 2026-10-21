"""Figures for chapter 10 (RLHF 与偏好优化).

Run from the build directory:

    python figures\\ch10_figs.py

Every figure is written as vector SVG into ``figures/out``.
"""

from __future__ import annotations

import os
import sys

import numpy as np

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUILD_DIR)

import figkit  # noqa: E402
from figkit import C0, C1, C2, C3, C4, GREY, INK  # noqa: E402

SEED = 20261020
BETA_STAR = 1.15  # beta_KL that maximises true quality in the toy RM study


# --------------------------------------------------------------------------
# 图 10-1  RLHF 三阶段流水线
# --------------------------------------------------------------------------
def f01_pipeline():
    fig, ax = figkit.new(4.30, 1.78)
    figkit.blank(ax, (-0.10, 8.75), (0.00, 3.45))

    stages = [
        (0.10, "① SFT", "演示数据\n监督微调", "#eef3fb", "#7d93b2"),
        (2.40, "② 奖励模型", "成对偏好\n$r_\\phi(x,y)$", "#e8f0e4", "#7d9b6a"),
        (4.70, "③ PPO", "对 $r_\\phi$ 优化\nKL 拉回 $\\pi_{\\mathrm{ref}}$", "#fdf1d8", "#c9a227"),
        (6.95, "对齐模型", "$\\pi_\\theta$\n部署", "#f4eef7", "#9b7bb0"),
    ]
    for x, title, body, fc, ec in stages:
        figkit.box(ax, (x, 2.10), 1.62, 0.95, body, fc=fc, ec=ec, fs=6.8)
        ax.text(x + 0.81, 3.20, title, ha="center", fontsize=7.0, color=INK)
    for x in (1.78, 4.08, 6.38):
        figkit.arrow(ax, (x, 2.58), (x + 0.56, 2.58), color=GREY)

    # the KL leash: pi_theta is pulled back to the SFT policy of stage 1
    ax.annotate("", xy=(5.45, 2.02), xytext=(0.90, 2.02),
                arrowprops=dict(arrowstyle="-|>", color=C1, linewidth=0.9,
                                linestyle=(0, (4, 2)), connectionstyle="arc3,rad=0.30"))
    ax.text(3.20, 0.95, "KL 正则项：$\\beta_{KL}D_{KL}(\\pi_\\theta\\|\\pi_{\\mathrm{ref}})$，"
                        "绳的另一端是 ① 的 SFT 策略", ha="center", fontsize=6.6, color=C1)

    ax.text(4.30, 0.32, "数据流：提示 → 成对比较（人类标注）→ 三类模型依次接力",
            ha="center", fontsize=6.6, color=GREY)
    return figkit.save(fig, "ch10_f01_pipeline")


# --------------------------------------------------------------------------
# 图 10-2  Bradley–Terry：概率曲线与对数损失
# --------------------------------------------------------------------------
def f02_bt():
    z = np.linspace(-6.0, 6.0, 600)
    sig = 1.0 / (1.0 + np.exp(-z))
    loss = -np.log(sig)

    fig, axes = figkit.new(3.45, 1.80, ncols=2)

    ax = axes[0]
    ax.plot(z, sig, color=C0, linewidth=1.1)
    ax.axhline(0.5, color=GREY, linewidth=0.7, linestyle=(0, (3, 2)))
    ax.axvline(0.0, color=GREY, linewidth=0.7, linestyle=(0, (3, 2)))
    pts = [-3.0, -0.8, 1.2, 3.4]
    ax.plot(pts, 1.0 / (1.0 + np.exp(-np.array(pts))), "o", color=C1, markersize=3.2)
    ax.set_xlabel("奖励差 $z$")
    ax.set_ylabel("$P(y_w\\succ y_l\\mid x)$")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("偏好概率 $\\sigma(z)$", fontsize=7.8)

    ax = axes[1]
    ax.plot(z, loss, color=C2, linewidth=1.1)
    ax.set_xlabel("奖励差 $z$")
    ax.set_ylabel("$-\\log\\sigma(z)$")
    ax.set_ylim(0.0, 6.4)
    ax.set_yticks([0.0, 2.0, 4.0, 6.0])
    ax.set_yticklabels(["0", "2", "4", "6"])
    ax.set_title("成对损失：分对后梯度变小", fontsize=7.8)
    ax.text(2.9, 4.05, "$z>0$ 且很大时\n损失趋零", fontsize=6.4, color=GREY,
            ha="center", linespacing=1.4)

    return figkit.save(fig, "ch10_f02_bt")


# --------------------------------------------------------------------------
# 图 10-3  KL 正则的效果（真算：Gibbs 形式的闭式解）
# --------------------------------------------------------------------------
def f03_kl():
    rng = np.random.default_rng(SEED)
    K = 200
    r = rng.normal(0.0, 1.0, size=K)          # 每个候选回答的奖励
    beta = np.logspace(np.log10(0.05), np.log10(20.0), 120)

    er, kl = [], []
    for b in beta:
        logw = r / b
        logw -= logw.max()
        w = np.exp(logw)
        w /= w.sum()                            # pi_ref 取均匀，故 w 即 pi_beta
        er.append(float(w @ r))
        kl.append(float(w @ np.log(w * K)))     # D_KL(pi_beta || uniform)
    er = np.array(er)
    kl = np.array(kl)

    fig, axes = figkit.new(3.55, 1.85, ncols=2)
    ticks = [0.1, 1.0, 10.0]

    ax = axes[0]
    ax.semilogx(beta, er, color=C0, linewidth=1.1)
    ax.axhline(r.max(), color=GREY, linewidth=0.7, linestyle=(0, (3, 2)))
    ax.text(3.30, r.max() - 0.16, "上限 $\\max_a r_a$", fontsize=6.2, color=GREY)
    ax.set_xticks(ticks)
    ax.set_xticklabels(["0.1", "1", "10"])
    ax.set_xlabel("$\\beta_{KL}$（越大越贴参考策略）")
    ax.set_ylabel("期望奖励 $E_\\pi[r]$")
    ax.set_title("奖励随 $\\beta_{KL}$ 下降", fontsize=7.6)

    ax = axes[1]
    ax.loglog(beta, kl, color=C2, linewidth=1.1)
    ax.set_xticks(ticks)
    ax.set_xticklabels(["0.1", "1", "10"])
    ax.set_yticks([1e-2, 1e-1, 1.0])
    ax.set_yticklabels(["0.01", "0.1", "1"])
    ax.set_xlabel("$\\beta_{KL}$")
    ax.set_ylabel("$D_{KL}(\\pi\\|\\pi_{\\mathrm{ref}})$")
    ax.set_title("偏离参考策略的代价", fontsize=7.6)

    return figkit.save(fig, "ch10_f03_kl")


# --------------------------------------------------------------------------
# 图 10-4  RLHF 与 DPO 的信息流
# --------------------------------------------------------------------------
def f04_dpo_flow():
    fig, ax = figkit.new(4.30, 1.80)
    figkit.blank(ax, (-0.10, 8.75), (-0.15, 3.35))

    # ---- row 1: RLHF -------------------------------------------------------
    ax.text(0.05, 3.10, "RLHF：两阶段，奖励模型在环", fontsize=7.4, color=INK)
    figkit.box(ax, (0.05, 2.05), 1.55, 0.68, "成对偏好\n$(x,y_w,y_l)$", fs=6.6,
               fc="#f7f8fa", ec="#9aa3ad")
    figkit.box(ax, (2.00, 2.05), 1.55, 0.68, "奖励模型\n$r_\\phi$", fs=6.6,
               fc="#e8f0e4", ec="#7d9b6a")
    figkit.box(ax, (3.95, 2.05), 1.75, 0.68, "PPO：在线采样\n再向 $r_\\phi$ 打分", fs=6.4,
               fc="#fdf1d8", ec="#c9a227")
    for x in (1.63, 3.58):
        figkit.arrow(ax, (x, 2.39), (x + 0.34, 2.39), color=GREY)
    ax.annotate("", xy=(4.83, 2.02), xytext=(4.83, 1.75),
                arrowprops=dict(arrowstyle="-|>", color=C1, linewidth=0.9))
    ax.text(4.83, 1.58, "逐 token KL 惩罚 + 价值头", ha="center", fontsize=6.3, color=C1)
    ax.text(7.20, 2.39, "需要\nRM + 采样\n+ 价值头", ha="center", va="center",
            fontsize=6.3, color=C1, linespacing=1.5)

    ax.plot([0.05, 8.05], [1.30, 1.30], color="#d0d4d9", linewidth=0.7,
            linestyle=(0, (2, 2)))

    # ---- row 2: DPO --------------------------------------------------------
    ax.text(0.05, 1.05, "DPO：单阶段，奖励被重新参数化进策略", fontsize=7.4, color=INK)
    figkit.box(ax, (0.05, 0.02), 1.55, 0.68, "成对偏好\n$(x,y_w,y_l)$", fs=6.6,
               fc="#f7f8fa", ec="#9aa3ad")
    figkit.box(ax, (2.00, 0.02), 1.95, 0.68, "同一网络：$\\pi_\\theta$\n与冻结的 $\\pi_{\\mathrm{ref}}$",
               fs=6.4, fc="#eef3fb", ec="#7d93b2")
    figkit.box(ax, (4.35, 0.02), 1.95, 0.68, "成对 logistic 损失\n一次反向传播", fs=6.4,
               fc="#fdf1d8", ec="#c9a227")
    figkit.arrow(ax, (1.63, 0.36), (1.97, 0.36), color=GREY)
    figkit.arrow(ax, (3.98, 0.36), (4.32, 0.36), color=GREY)
    ax.text(7.20, 0.36, "不需要\nRM / 采样\n/ 价值头", ha="center", va="center",
            fontsize=6.3, color=C1, linespacing=1.5)

    return figkit.save(fig, "ch10_f04_dpo_flow")


# --------------------------------------------------------------------------
# 图 10-5  奖励黑客：代理分数上升、真实质量先升后降（真算）
# --------------------------------------------------------------------------
def f05_overopt(beta_star=BETA_STAR):
    rng = np.random.default_rng(SEED)
    K, REPS = 300, 60
    beta = np.logspace(np.log10(0.05), np.log10(20.0), 90)
    q_curve = np.zeros((REPS, beta.size))
    rm_curve = np.zeros((REPS, beta.size))
    len_curve = np.zeros((REPS, beta.size))

    for k in range(REPS):
        base = rng.normal(0.0, 1.0, size=K)             # 与长度无关的质量
        ell = rng.normal(0.0, 1.0, size=K)              # 长度（标准化）
        # 人类真实判断：适度长度有帮助，冗长开始扣分（倒 U 形）。常数 1.4 只是
        # 纵向平移（BT 只依赖奖励差），让曲线落在正区间便于阅读。
        q = 1.4 + base + 0.8 * ell - 1.5 * ell ** 2
        # 学到的 RM：从成对比较里只拟合出线性的长度项，没有倒 U 形惩罚
        rm = base + 0.8 * ell
        for j, b in enumerate(beta):
            logw = rm / b
            logw -= logw.max()
            w = np.exp(logw)
            w /= w.sum()
            q_curve[k, j] = float(w @ q)
            rm_curve[k, j] = float(w @ rm)
            len_curve[k, j] = float(w @ ell)

    qm, rmm, lm = q_curve.mean(0), rm_curve.mean(0), len_curve.mean(0)
    qse = q_curve.std(0, ddof=1) / np.sqrt(REPS)
    jstar = int(np.argmax(qm))
    ticks = [0.1, 1.0, 10.0]
    print(f"[f05] beta*={beta[jstar]:.3f}  q(beta*)={qm[jstar]:.3f}  "
          f"q(0.05)={qm[0]:.3f}  q(20)={qm[-1]:.3f}  "
          f"rm(0.05)={rmm[0]:.3f}  rm(20)={rmm[-1]:.3f}  "
          f"len(0.05)={lm[0]:.3f}  len(20)={lm[-1]:.3f}  "
          f"se(beta*)={qse[jstar]:.3f}  reps={REPS} K={K} seed={SEED}")

    fig, axes = figkit.new(3.60, 1.95, ncols=2)

    ax = axes[0]
    ax.fill_between(beta, qm - qse, qm + qse, color=C0, alpha=0.15, linewidth=0)
    line_q, = ax.semilogx(beta, qm, color=C0, linewidth=1.1, label="真实质量")
    line_r, = ax.semilogx(beta, rmm, color=C1, linewidth=1.1, label="奖励模型分数（代理）")
    ax.axvline(beta[jstar], color=GREY, linewidth=0.7, linestyle=(0, (3, 2)))
    ax.text(beta[jstar] * 1.12, 1.55, "$\\beta_{KL}^\\ast$",
            fontsize=6.6, color=GREY)
    ax.set_xticks(ticks)
    ax.set_xticklabels(["0.1", "1", "10"])
    ax.set_xlabel("$\\beta_{KL}$")
    ax.set_ylabel("分数")
    ax.set_title("代理升、真实质量先升后降", fontsize=7.4)

    ax = axes[1]
    ax.semilogx(beta, lm, color=C3, linewidth=1.1)
    ax.axhline(0.0, color=GREY, linewidth=0.7, linestyle=(0, (3, 2)))
    ax.set_xticks(ticks)
    ax.set_xticklabels(["0.1", "1", "10"])
    ax.set_xlabel("$\\beta_{KL}$")
    ax.set_ylabel("平均长度（标准化）")
    ax.set_title("优化越激进，输出越长", fontsize=7.4)

    fig.legend(handles=[line_r, line_q], loc="outside lower center", ncol=2,
               fontsize=5.8, frameon=False, handlelength=1.4, columnspacing=1.6)

    return figkit.save(fig, "ch10_f05_overopt")


# --------------------------------------------------------------------------
# 图 10-6  偏好优化方法家族（定性示意）
# --------------------------------------------------------------------------
def f06_family():
    fig, ax = figkit.new(3.70, 1.95)
    figkit.blank(ax, (-0.30, 4.25), (-0.28, 3.35))

    ax.annotate("", xy=(4.05, 0.22), xytext=(0.16, 0.22),
                arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
    ax.annotate("", xy=(0.16, 3.30), xytext=(0.16, 0.22),
                arrowprops=dict(arrowstyle="-|>", color=GREY, linewidth=0.8))
    ax.text(2.15, -0.12, "工程复杂度（RM、在线采样、内存）", ha="center",
            fontsize=6.4, color=GREY)
    ax.text(-0.18, 1.80, "对偏好模型的假设强度", rotation=90, va="center",
            fontsize=6.4, color=GREY, ha="center")

    pts = [
        (3.50, 2.80, "PPO-RLHF", "#fdf1d8", "#c9a227"),
        (2.55, 2.45, "DPO", "#eef3fb", "#7d93b2"),
        (1.90, 1.95, "IPO", "#f4eef7", "#9b7bb0"),
        (1.38, 1.45, "KTO", "#e8f0e4", "#7d9b6a"),
        (1.12, 0.95, "ORPO", "#fdf6e3", "#c9a227"),
        (0.80, 0.52, "SimPO", "#f4eef7", "#9b7bb0"),
    ]
    for x, y, name, fc, ec in pts:
        figkit.box(ax, (x - 0.50, y - 0.17), 1.00, 0.34, name, fs=6.0, fc=fc, ec=ec)

    ax.text(0.30, 3.22, "右上：显式奖励模型 + 在线采样；左下：无参考策略", fontsize=5.8,
            color=GREY, ha="left", va="center")
    return figkit.save(fig, "ch10_f06_family")


def main() -> int:
    figkit.setup()
    import matplotlib
    matplotlib.rcParams["axes.unicode_minus"] = False
    for fn in (f01_pipeline, f02_bt, f03_kl, f04_dpo_flow, f05_overopt, f06_family):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
