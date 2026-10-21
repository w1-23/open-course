"""CH03-ALG-301 复现：算法 3-1 的 Δ 若在赋值之后计算，收敛判据恒为真。

两种写法都完整跑一遍策略迭代，打印"评估阶段实际做了几次扫描"与最终价值误差。
预期：错误写法每次评估只扫 1 遍（因为 Δ 恒为 0），正确写法要扫到阈值。

运行： python review\\reproductions\\CH03-ALG-301_fix.py
"""
from __future__ import annotations

import numpy as np

GAMMA = 0.9
THETA = 1e-6
N = 5
GOAL = (4, 4)
PITS = {(1, 1), (3, 2)}
STEP_REWARD = -0.04
ACTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _next(state, action):
    if state == GOAL or state in PITS:
        return state, 0.0
    r, c = state
    dr, dc = action
    nr, nc = min(max(r + dr, 0), N - 1), min(max(c + dc, 0), N - 1)
    nxt = (nr, nc)
    if nxt == GOAL:
        return nxt, 1.0
    if nxt in PITS:
        return nxt, -1.0
    return nxt, STEP_REWARD


def policy_evaluation(policy, buggy: bool):
    """返回 (V, 扫描次数)。buggy=True 时把 Δ 放在赋值之后。"""
    V = {s: 0.0 for s in policy}
    sweeps = 0
    while True:
        delta = 0.0
        for s in policy:
            a = policy[s]
            nxt, r = _next(s, a)
            v_new = r + GAMMA * V[nxt]
            if buggy:
                V[s] = v_new
                delta = max(delta, abs(v_new - V[s]))     # ← 恒为 0
            else:
                delta = max(delta, abs(v_new - V[s]))     # ← 用旧值算差
                V[s] = v_new
        sweeps += 1
        if delta < THETA or sweeps > 500:
            break
    return V, sweeps


def greedy(V, s):
    best, best_q = None, -1e9
    for a in ACTIONS:
        nxt, r = _next(s, a)
        q = r + GAMMA * V[nxt]
        if q > best_q + 1e-12:
            best, best_q = a, q
    return best


def run(buggy: bool):
    states = [(r, c) for r in range(N) for c in range(N)]
    policy = {s: ACTIONS[0] for s in states}
    total_sweeps = 0
    for it in range(1, 60):
        V, sweeps = policy_evaluation(policy, buggy)
        total_sweeps += sweeps
        new_policy = {s: greedy(V, s) for s in states}
        if new_policy == policy:
            return it, total_sweeps, sweeps, V
        policy = new_policy
    return 60, total_sweeps, sweeps, V


def main():
    for buggy, name in ((True, "错误写法（Δ 在赋值后计算）"), (False, "正确写法（Δ 用旧值）")):
        iters, total, last, V = run(buggy)
        print(f"{name}")
        print(f"  策略迭代轮数 {iters}，评估扫描总数 {total}，最后一轮 {last} 次扫描")
        print(f"  估计 V(0,0) = {V[(0, 0)]:.6f}   V(4,3) = {V[(4, 3)]:.6f}")
        print()

    print("结论：错误写法下 Δ 恒等于 0，每次评估都在第 1 次扫描后退出（last = 1），")
    print("      '评估到收敛' 这句话与代码不符；正确写法最后一轮需要多次扫描才满足 Δ < θ。")


if __name__ == "__main__":
    main()
