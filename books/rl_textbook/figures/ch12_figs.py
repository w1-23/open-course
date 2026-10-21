"""Figures for chapter 12 (Agentic RL and continual learning).

Five figures, two of them from a real experiment:

    f01  one answer versus a multi-step episode (timeline)
    f02  the agentic loop: growing context, tool calls, terminated / truncated exits
    f03  decision tree that separates the four kinds of adaptation
    f04  catastrophic forgetting on a three-task regression sequence   [computed]
    f05  stability-plasticity trade-off while sweeping the EWC weight    [computed]

Run:  python figures\\ch12_figs.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUILD_DIR)

import figkit  # noqa: E402
from figkit import C0, C1, C2, C3, C4, INK, GREY  # noqa: E402

# --------------------------------------------------------------------------
# f01: one answer versus one episode
# --------------------------------------------------------------------------


def f01_single_vs_multi():
    fig, axes = figkit.new(4.40, 2.05, ncols=1)
    ax = axes

    figkit.blank(ax, (0.0, 10.0), (0.1, 4.35))

    ax.text(0.05, 4.10, "单次回答（第 10 章）", fontsize=7.2, color=INK)
    ax.text(0.05, 2.48, "多步回合（本章）", fontsize=7.2, color=INK)

    # row 1: prompt -> policy -> answer -> reward
    figkit.box(ax, (0.60, 3.05), 1.45, 0.62, "提示 $x$", fc="#eef3fb",
               ec="#7d93b2", fs=6.8)
    figkit.box(ax, (2.75, 3.05), 1.75, 0.62, "策略一次生成 $y$", fc="#eef3fb",
               ec="#7d93b2", fs=6.8)
    figkit.box(ax, (5.20, 3.05), 1.35, 0.62, "奖励 $r(x,y)$", fc="#e8f0e4",
               ec="#7d9b6a", fs=6.8)
    figkit.arrow(ax, (2.05, 3.36), (2.75, 3.36))
    figkit.arrow(ax, (4.50, 3.36), (5.20, 3.36))
    ax.text(6.75, 3.34, "一个动作、一次奖励", fontsize=6.6, color=GREY)

    # row 2: prompt -> action -> tool -> observation -> action -> answer -> reward
    y = 1.60
    figkit.box(ax, (0.30, y), 1.20, 0.58, "提示 $x$", fc="#eef3fb",
               ec="#7d93b2", fs=6.6)
    figkit.box(ax, (1.90, y), 1.30, 0.58, "生成 $a_1$", fc="#fdf2e9",
               ec="#c58a4a", fs=6.6)
    figkit.box(ax, (3.60, y), 1.35, 0.58, "工具 / 环境", fc="#f2eef7",
               ec="#8d78a8", fs=6.6)
    figkit.box(ax, (5.30, y), 1.35, 0.58, "观测 $o_1$", fc="#f2eef7",
               ec="#8d78a8", fs=6.6)
    figkit.box(ax, (7.00, y), 1.15, 0.58, "生成 $a_2$", fc="#fdf2e9",
               ec="#c58a4a", fs=6.6)
    figkit.box(ax, (8.45, y), 1.15, 0.58, "奖励 $R(\\tau)$", fc="#e8f0e4",
               ec="#7d9b6a", fs=6.6)
    figkit.arrow(ax, (1.50, y + 0.29), (1.90, y + 0.29))
    figkit.arrow(ax, (3.20, y + 0.29), (3.60, y + 0.29))
    figkit.arrow(ax, (4.95, y + 0.29), (5.30, y + 0.29))
    figkit.arrow(ax, (6.65, y + 0.29), (7.00, y + 0.29))
    figkit.arrow(ax, (8.15, y + 0.29), (8.45, y + 0.29))

    # context growth underneath row 2
    ax.plot([0.30, 9.60], [1.28, 1.28], color=GREY, linewidth=0.6)
    for x0 in (0.30, 1.90, 3.60, 5.30, 7.00, 8.45):
        ax.plot([x0, x0], [1.28, 1.40], color=GREY, linewidth=0.5)
    ax.text(0.30, 0.98, "上下文 $h_t$：每一步只追加 $(a_t,o_t)$，不覆盖旧内容",
            fontsize=6.5, color=GREY)

    ax.text(0.30, 0.42, "$t=0$ 生成；$t=1$ 调用工具；$t=2$ 再生成——"
                        "任务完成即终止，步数或预算用尽即截断",
            fontsize=6.4, color=GREY)

    return figkit.save(fig, "ch12_f01_single_vs_multi")


# --------------------------------------------------------------------------
# f02: the agentic loop with the two exits
# --------------------------------------------------------------------------


def f02_agentic_loop():
    fig, ax = figkit.new(4.20, 2.45)
    figkit.blank(ax, (0.0, 10.0), (0.0, 5.6))

    figkit.box(ax, (0.55, 3.55), 2.10, 0.85,
               "策略 $\\pi_\\theta(a\\mid h_t)$\n选择动作类型", fc="#eef3fb",
               ec="#7d93b2", fs=6.8)
    figkit.box(ax, (3.65, 3.55), 2.20, 0.85,
               "执行\ntoken 或工具调用", fc="#fdf2e9", ec="#c58a4a", fs=6.8)
    figkit.box(ax, (6.75, 3.55), 2.30, 0.85,
               "追加观测 $o_t$\n$h_{t+1}=h_t\\oplus(a_t,o_t)$", fc="#f2eef7",
               ec="#8d78a8", fs=6.8)

    figkit.arrow(ax, (2.65, 3.97), (3.65, 3.97))
    figkit.arrow(ax, (5.85, 3.97), (6.75, 3.97))
    # feedback loop back to the policy
    figkit.arrow(ax, (7.90, 3.55), (1.60, 3.55), rad=-0.35)
    ax.text(4.75, 2.62, "回合继续", ha="center", fontsize=6.6, color=GREY)
    ax.text(4.75, 2.30, "$t\\leftarrow t+1$", ha="center", fontsize=6.6,
            color=GREY)

    # two exits
    figkit.box(ax, (1.60, 0.55), 3.10, 0.78,
               "任务完成 $\\rightarrow$ terminated\n自举停止，$V(h_T)=0$",
               fc="#e8f0e4", ec="#7d9b6a", fs=6.6)
    figkit.box(ax, (5.55, 0.55), 3.60, 0.78,
               "步数或预算用尽 $\\rightarrow$ truncated\n保留自举项 $\\gamma V_\\phi(h_T)$",
               fc="#fdf2e9", ec="#c58a4a", fs=6.6)
    figkit.arrow(ax, (2.20, 3.55), (2.90, 1.35), color="#7d9b6a")
    figkit.arrow(ax, (6.40, 3.55), (6.60, 1.35), color="#c58a4a")
    ax.text(0.30, 0.12, "两个出口必须分开记账：把截断当终止会系统性低估长回合的价值。",
            fontsize=6.4, color=GREY)

    return figkit.save(fig, "ch12_f02_agentic_loop")


# --------------------------------------------------------------------------
# f03: decision tree for the four kinds of adaptation
# --------------------------------------------------------------------------


def f03_four_adaptations():
    fig, ax = figkit.new(4.30, 2.55)
    figkit.blank(ax, (0.0, 10.0), (0.0, 6.2))

    figkit.box(ax, (3.75, 5.05), 2.50, 0.62, "参数 $\\theta$ 变了吗？",
               fc="#eef3fb", ec="#7d93b2", fs=7.0)
    figkit.box(ax, (1.15, 3.60), 2.30, 0.62, "写入了外部存储？",
               fc="#f2eef7", ec="#8d78a8", fs=7.0)
    figkit.box(ax, (6.55, 3.60), 2.60, 0.62, "要求任务序列上不遗忘？",
               fc="#fdf2e9", ec="#c58a4a", fs=7.0)

    leaves = (
        (0.10, 1.10, 2.25, "否 $\\rightarrow$ 上下文内适应\n提示、示例，不改参数",
         "#eef3fb", "#7d93b2"),
        (2.55, 1.10, 2.25, "是 $\\rightarrow$ 记忆更新\n写外部存储，跨回合",
         "#f2eef7", "#8d78a8"),
        (5.25, 1.10, 2.25, "否 $\\rightarrow$ 参数更新\n微调或 RL 训练",
         "#fdf2e9", "#c58a4a"),
        (7.70, 1.10, 2.25, "是 $\\rightarrow$ 持续 RL\n序列训练 + 抗遗忘",
         "#e8f0e4", "#7d9b6a"),
    )
    for x, y, w, text, fc, ec in leaves:
        figkit.box(ax, (x, y), w, 0.85, text, fc=fc, ec=ec, fs=6.2)

    figkit.arrow(ax, (4.20, 5.03), (2.30, 4.24))
    figkit.arrow(ax, (5.80, 5.03), (7.85, 4.24))
    figkit.arrow(ax, (1.55, 3.58), (1.20, 1.97))
    figkit.arrow(ax, (3.05, 3.58), (3.65, 1.97))
    figkit.arrow(ax, (7.05, 3.58), (6.35, 1.97))
    figkit.arrow(ax, (8.65, 3.58), (8.80, 1.97))

    ax.text(0.45, 4.62, "不改变策略参数", fontsize=6.4, color=GREY)
    ax.text(6.35, 4.62, "改变策略参数", fontsize=6.4, color=GREY)
    ax.text(0.15, 0.30, "四个分支只有右下角一类是「持续学习」意义上的 RL；"
                        "其余三类可能用到 RL，但不是持续 RL。",
            fontsize=6.4, color=GREY)

    return figkit.save(fig, "ch12_f03_four_adaptations")


# --------------------------------------------------------------------------
# a small numpy MLP: three regression tasks learned in sequence
# --------------------------------------------------------------------------

TASKS = (
    ("任务 1", 0.00, 0.30, lambda x: np.sin(2.0 * np.pi * x)),
    ("任务 2", 0.35, 0.65, lambda x: 1.0 - 2.0 * x),
    ("任务 3", 0.70, 1.00, lambda x: 0.30 + 0.40 * np.cos(2.0 * np.pi * x)),
)
N_TRAIN = 40
N_EVAL = 120
N_HID = 32
STEPS = 400
LR = 0.01
SEEDS = range(5)
EWC_LAMBDA = 10.0


def task_data(k, n, rng=None):
    lo, hi, f = TASKS[k][1], TASKS[k][2], TASKS[k][3]
    if rng is None:
        x = np.linspace(lo, hi, n)
    else:
        x = rng.uniform(lo, hi, n)
    return x.reshape(-1, 1), f(x).reshape(-1, 1)


def init_net(rng):
    def w(fan_in, fan_out):
        return rng.normal(0.0, np.sqrt(2.0 / fan_in), size=(fan_in, fan_out))

    return [w(1, N_HID), np.zeros(N_HID), w(N_HID, N_HID), np.zeros(N_HID),
            w(N_HID, 1), np.zeros(1)]


def forward(params, x):
    W1, b1, W2, b2, W3, b3 = params
    h1 = np.tanh(x @ W1 + b1)
    h2 = np.tanh(h1 @ W2 + b2)
    return h2 @ W3 + b3, (h1, h2)


def grads(params, x, y, mask=None):
    W1, b1, W2, b2, W3, b3 = params
    out, (h1, h2) = forward(params, x)
    g_out = 2.0 * (out - y) / x.shape[0]
    if mask is not None:
        g_out = g_out * mask[:, None]
    gW3 = h2.T @ g_out
    gb3 = g_out.sum(0)
    g2 = (g_out @ W3.T) * (1.0 - h2 ** 2)
    gW2 = h1.T @ g2
    gb2 = g2.sum(0)
    g1 = (g2 @ W2.T) * (1.0 - h1 ** 2)
    gW1 = x.T @ g1
    gb1 = g1.sum(0)
    return [gW1, gb1, gW2, gb2, gW3, gb3]


def mse(params, x, y):
    out, _ = forward(params, x)
    return float(np.mean((out - y) ** 2))


def train(params, x, y, steps, lr, anchors=(), lam=0.0, replay=None):
    """Adam on MSE plus an EWC penalty and an optional replay mixture."""
    m = [np.zeros_like(p) for p in params]
    v = [np.zeros_like(p) for p in params]
    b1, b2, eps = 0.9, 0.999, 1e-8
    for t in range(1, steps + 1):
        g = grads(params, x, y)
        if replay is not None and replay[0].size:
            xr, yr = replay
            gr = grads(params, xr, yr)
            g = [a + b for a, b in zip(g, gr)]
        for k, a in enumerate(anchors):
            thr, fisher = a
            g = [gk + lam * fk * (pk - tk)
                 for gk, fk, pk, tk in zip(g, fisher, params, thr)]
        for i in range(len(params)):
            m[i] = b1 * m[i] + (1 - b1) * g[i]
            v[i] = b2 * v[i] + (1 - b2) * g[i] ** 2
            mh = m[i] / (1 - b1 ** t)
            vh = v[i] / (1 - b2 ** t)
            params[i] = params[i] - lr * mh / (np.sqrt(vh) + eps)
    return params


def fisher_diag(params, x, y):
    """Diagonal Fisher of the regression loss, one sample at a time."""
    acc = [np.zeros_like(p) for p in params]
    n = x.shape[0]
    for i in range(n):
        g = grads(params, x[i:i + 1], y[i:i + 1])
        for a, gi in zip(acc, g):
            a += gi ** 2 * n
    return [a / max(n, 1) for a in acc]


def run_sequence(seed, method, lam=0.0, replay_frac=0.5):
    rng = np.random.default_rng(seed)
    params = init_net(rng)
    xt = [task_data(k, N_TRAIN)[0] for k in range(3)]
    yt = [task_data(k, N_TRAIN)[1] for k in range(3)]
    xe = [task_data(k, N_EVAL)[0] for k in range(3)]
    ye = [task_data(k, N_EVAL)[1] for k in range(3)]

    anchors = []
    buf_x, buf_y = np.zeros((0, 1)), np.zeros((0, 1))
    curve = []          # MSE on every task after every stage
    for k in range(3):
        replay = None
        if method == "replay" and buf_x.shape[0]:
            n_rep = max(1, int(replay_frac / (1.0 - replay_frac) * N_TRAIN))
            idx = rng.integers(0, buf_x.shape[0], n_rep)
            replay = (buf_x[idx], buf_y[idx])
        if method == "ewc" and anchors:
            params = train(params, xt[k], yt[k], STEPS, LR, anchors, lam)
        else:
            params = train(params, xt[k], yt[k], STEPS, LR, replay=replay)
        if method == "replay":
            buf_x = np.vstack([buf_x, xt[k]])
            buf_y = np.vstack([buf_y, yt[k]])
        if method == "ewc":
            anchors.append(([p.copy() for p in params], fisher_diag(params, xt[k], yt[k])))
        curve.append([mse(params, xe[j], ye[j]) for j in range(3)])
    return np.array(curve), params, (xe, ye)


def experiment():
    """Returns curves (method -> seeds x stages x tasks) and a lambda sweep."""
    curves = {}
    finals = {}
    for method in ("naive", "ewc", "replay"):
        runs, preds = [], []
        for s in SEEDS:
            curve, params, (xe, ye) = run_sequence(1000 + s, method, EWC_LAMBDA)
            runs.append(curve)
            grid = np.linspace(0.0, 1.0, 200).reshape(-1, 1)
            preds.append(forward(params, grid)[0][:, 0])
        curves[method] = np.array(runs)
        finals[method] = np.array(preds)

    sweep = {}
    for lam in (0.3, 1.0, 3.0, 10.0, 30.0, 100.0):
        vals = []
        for s in SEEDS:
            curve, _, _ = run_sequence(2000 + s, "ewc", lam)
            vals.append(curve)
        sweep[lam] = np.array(vals)

    return curves, finals, sweep


def metrics(curve):
    """ACC / BWT / FWT from a stages x tasks MSE table (lower MSE is better)."""
    a = -curve                      # performance, higher is better
    K = a.shape[0]
    acc = float(np.mean(a[-1]))
    bwt = float(np.mean([a[-1, k] - (a[k, k] if k < K else a[-1, k])
                         for k in range(K - 1)])) if K > 1 else 0.0
    fwt = float(np.mean([a[k - 1, k] for k in range(1, K)])) if K > 1 else 0.0
    return acc, bwt, fwt


# --------------------------------------------------------------------------
# f04: forgetting curves
# --------------------------------------------------------------------------


def f04_forgetting(curves, finals):
    fig, axes = figkit.new(4.40, 1.58, ncols=2)
    ax, ax2 = axes

    stages = np.arange(1, 4)
    style = (("naive", "无防护", C1, "-"), ("ewc", "EWC $\\lambda=10$", C0, "-"),
             ("replay", "回放", C3, "--"))
    for name, lab, color, ls in style:
        m = curves[name][:, :, 0].mean(0)
        sd = curves[name][:, :, 0].std(0)
        ax.errorbar(stages, m, yerr=sd, color=color, linestyle=ls, linewidth=1.0,
                    marker="o", markersize=2.6, capsize=1.6, label=lab)
    ax.set_yscale("log")
    ax.set_yticks([1e-4, 1e-3, 1e-2, 1e-1, 1])
    ax.set_yticklabels(["1e-4", "1e-3", "1e-2", "1e-1", "1"])
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["学完 T1", "学完 T2", "学完 T3"])
    ax.set_xlabel("训练阶段", fontsize=7.0)
    ax.set_ylabel("任务 1 的 MSE", fontsize=7.0)
    ax.minorticks_off()
    ax.legend(fontsize=6.0, frameon=False, loc="upper left")
    ax.set_title("遗忘随任务序列累积（5 个种子）", fontsize=6.8)

    grid = np.linspace(0.0, 1.0, 200)
    truth = np.where(grid <= 0.30, TASKS[0][3](grid),
                     np.where(grid <= 0.65, TASKS[1][3](grid), TASKS[2][3](grid)))
    ax2.plot(grid, truth, color=GREY, linewidth=1.4)
    for name, lab, color, ls in style:
        pred = finals[name].mean(0)
        ax2.plot(grid, pred, color=color, linestyle=ls, linewidth=0.9, label=lab)
    for lo, hi in ((0.0, 0.30), (0.35, 0.65), (0.70, 1.0)):
        ax2.axvspan(lo, hi, color="#eef3fb", zorder=0)
    ax2.set_xlabel("输入 $x$", fontsize=7.0)
    ax2.set_ylabel("输出", fontsize=7.0)
    ax2.set_yticks([-0.25, 0.0, 0.5, 1.0])
    ax2.set_yticklabels(["-0.25", "0", "0.5", "1"])
    ax2.set_title("学完 T3 之后的预测（灰线为真值）", fontsize=6.8)
    ax2.legend(fontsize=5.8, frameon=True, framealpha=0.85, loc="lower left")

    return figkit.save(fig, "ch12_f04_forgetting")


# --------------------------------------------------------------------------
# f05: stability-plasticity trade-off
# --------------------------------------------------------------------------


def f05_tradeoff(curves, sweep):
    fig, ax = figkit.new(3.30, 2.10)
    figkit.blank(ax, (8.0e-5, 1.3e-3), (7.0e-4, 5.0))
    ax.set_xscale("log")
    ax.set_yscale("log")

    def point(c):
        """(plasticity cost on the last task, forgetting of earlier tasks)."""
        acc, bwt, _ = metrics(c)
        last = float(np.mean(c[-1, -1]))
        return last, -bwt

    xs, ys, labs = [], [], []
    for lam in sorted(sweep):
        x, y = point(sweep[lam].mean(0))
        xs.append(x)
        ys.append(y)
        labs.append("$\\lambda=%g$" % lam)

    ax.plot(xs, ys, color=C0, linewidth=0.9, marker="o", markersize=2.6)
    # label four representative weights; the sweep also contains 1 and 3
    show = {0.3: (5, 4), 10.0: (5, -9), 30.0: (5, 4), 100.0: (5, 4)}
    for lam, x, y in zip(sorted(sweep), xs, ys):
        if lam in show:
            ax.annotate("$\\lambda=%g$" % lam, (x, y), textcoords="offset points",
                        xytext=show[lam], fontsize=5.8, color=C0)

    x_n, y_n = point(curves["naive"].mean(0))
    x_r, y_r = point(curves["replay"].mean(0))
    ax.plot([x_n], [y_n], marker="s", markersize=3.4, color=C1, linewidth=0)
    ax.annotate("无防护", (x_n, y_n), textcoords="offset points",
                xytext=(-6, -10), fontsize=6.0, color=C1, ha="right")
    ax.plot([x_r], [y_r], marker="^", markersize=4.0, color=C3, linewidth=0)
    ax.annotate("回放", (x_r, y_r), textcoords="offset points",
                xytext=(4, 3), fontsize=6.0, color=C3)

    ax.set_xticks([1e-4, 3e-4, 6e-4])
    ax.set_xticklabels(["1e-4", "3e-4", "6e-4"])
    ax.set_yticks([1e-3, 1e-2, 1e-1, 1.0, 3.0])
    ax.set_yticklabels(["1e-3", "1e-2", "1e-1", "1", "3"])
    ax.minorticks_off()
    ax.set_xlabel("末任务 MSE（越小越可塑）", fontsize=7.0)
    ax.set_ylabel("遗忘量（越小越稳定）", fontsize=7.0)
    ax.set_title("正则强度把工作点推向稳定端", fontsize=7.0)

    return figkit.save(fig, "ch12_f05_tradeoff")


def main() -> int:
    figkit.setup()
    f01_single_vs_multi()
    f02_agentic_loop()
    f03_four_adaptations()
    curves, finals, sweep = experiment()
    f04_forgetting(curves, finals)
    f05_tradeoff(curves, sweep)

    for name in ("naive", "ewc", "replay"):
        acc, bwt, fwt = metrics(curves[name].mean(0))
        last = curves[name][:, -1, :].mean(0)
        print("%-7s ACC(-MSE)=%.4f  BWT=%.4f  FWT=%.4f  final per task=%s"
              % (name, acc, bwt, fwt, np.array2string(last, precision=4)))
    for lam in sorted(sweep):
        acc, bwt, _ = metrics(sweep[lam].mean(0))
        print("  lambda=%6g  meanMSE=%.4f  遗忘量=%.4f  末任务MSE=%.5f"
              % (lam, -acc, -bwt, float(np.mean(sweep[lam][:, -1, -1]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
