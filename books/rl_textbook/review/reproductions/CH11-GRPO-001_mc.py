"""CH11-GRPO-001 的可复现数值验证。

问题：组内相对优势 Â_i = (r_i − r̄)/s_r 是不是"与动作无关的基线"，即
      E[Â_i ∇log π(a_i)] 是否等于未加基线的 g_i？

做法：3 臂 bandit，策略 π 固定（softmax），奖励 r_k 固定，G 个样本独立同分布。
      G=3、K=3 时**穷举全部 27 个样本组**，得到精确期望（无蒙特卡洛噪声）；
      G=5、K=3 时穷举 243 个样本组。
      对每个样本组 i=1（对称，取任意一个样本等价）计算
        A. g_i                                  （未加基线）
        B. E[(r_i − r̄) ∇log π(a_i)]            （组均值中心化）
        C. E[(r_i − r̄)/s_r ∇log π(a_i)]        （GRPO 式，s_r>0 时）
      并检验 B == (1 − 1/G) · A 是否成立。

运行：python review/reproductions/CH11-GRPO-001_mc.py
"""

from __future__ import annotations

import itertools
import math
import sys

import numpy as np

PI = np.array([0.5, 0.3, 0.2])      # 3 臂策略
R = np.array([1.0, 0.0, -1.0])      # 各臂奖励
THETA_LOGITS = np.array([0.2, -0.1, 0.0])


def grad_log_pi(a: int) -> np.ndarray:
    """∇_logits log π(a) = e_a − π。"""
    e = np.zeros_like(PI)
    e[a] = 1.0
    return e - PI


def g_plain() -> np.ndarray:
    """未加基线的一步策略梯度：Σ_a π(a) r_a ∇log π(a)。"""
    return sum(PI[a] * R[a] * grad_log_pi(a) for a in range(3))


def exact(G: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """穷举 K^G 个样本组，返回 (B, C, 用于 C 的有效组数)。"""
    K = len(PI)
    B = np.zeros(3)
    C = np.zeros(3)
    n_valid = 0
    for tup in itertools.product(range(K), repeat=G):
        p = 1.0
        for a in tup:
            p *= PI[a]
        if p == 0.0:
            continue
        r = R[list(tup)]
        rbar = r.mean()
        i = 0
        B += p * (r[i] - rbar) * grad_log_pi(tup[i])
        s = r.std(ddof=0)
        if s > 1e-12:                      # 全同奖励时 Â 无定义（0/0），按实现惯例跳过
            C += p * (r[i] - rbar) / s * grad_log_pi(tup[i])
            n_valid += p
    return B / 1.0, C, np.array([n_valid])


def main() -> int:
    A = g_plain()
    print("策略 π =", PI, " 奖励 r =", R)
    print("未加基线 g_i =", np.round(A, 6))
    print()
    print(f"{'G':>2} {'‖B‖/‖A‖':>10} {'1−1/G':>8} {'相对误差':>10} "
          f"{'‖C‖/‖A‖':>10} {'有效组质量':>10}")
    ok = True
    for G in (2, 3, 5):
        B, C, n_valid = exact(G)
        ratio = np.linalg.norm(B) / np.linalg.norm(A)
        target = 1.0 - 1.0 / G
        err = abs(ratio - target) / target
        c_ratio = np.linalg.norm(C) / np.linalg.norm(A)
        print(f"{G:>2} {ratio:>10.6f} {target:>8.4f} {err:>10.2e} "
              f"{c_ratio:>10.6f} {n_valid[0]:>10.4f}")
        if err > 1e-9:
            ok = False
    print()
    if ok:
        print("结论 1：E[(r_i − r̄)∇log π] = (1 − 1/G)·g_i —— 组均值把梯度按 1−1/G 缩小，")
        print("        不是「零效应基线」；G=1 时恒为 0（本脚本从 G=2 起测）。")
    else:
        print("!! 与 (1−1/G) 不符，推导需要重查")
        return 1

    # 除以 s_r 之后：与 (1−1/G)g_i 的差别，说明"期望不变"不成立
    G = 3
    B, C, n_valid = exact(G)
    target = (1 - 1.0 / G) * A
    print(f"\nG={G} 时：")
    print("  (1−1/G)·g_i        =", np.round(target, 6))
    print("  E[(r_i−r̄)/s_r∇logπ] =", np.round(C, 6))
    print("  归一化后与缩放的差 =", np.round(C - target, 6))
    print("\n结论 2：再除以 s_r 后结果不再等于 (1−1/G)g_i（有限 G 下差项非零），")
    print("        所以不能主张「期望不变」，只能说是一个带缩放的上升方向。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
