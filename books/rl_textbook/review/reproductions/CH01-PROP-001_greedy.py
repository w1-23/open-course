"""CH01-PROP-001 反例：纯贪心 + 全 0 初值并不必然锁定在首个臂。

书中命题 1.1 称：若臂 1 非最优，贪心"此后几乎总选臂 1"，故 Regret(T) = TΔ₁ + O(1)。
本脚本给出一个确定性的两臂反例，其遗憾是常数而不是线性。

运行： python review\\reproductions\\CH01-PROP-001_greedy.py
"""
from __future__ import annotations

T = 200


def run(rewards, tie_low_index=True, verbose=True):
    """rewards[a][t] 为确定性奖励序列；返回累积遗憾与各臂被选次数。"""
    K = len(rewards)
    q = [0.0] * K
    n = [0] * K
    best = max(sum(r[:T]) / T for r in rewards)     # 用长期平均定义最优臂
    regret, picks = 0.0, [0] * K
    for t in range(T):
        # 贪心 + 固定平局规则（下标小者优先）
        a = 0
        for i in range(1, K):
            if q[i] > q[a] + 1e-12:
                a = i
        r = rewards[a][t]
        picks[a] += 1
        regret += best - r
        n[a] += 1
        q[a] += (r - q[a]) / n[a]
    if verbose:
        print(f"  各臂被选次数 {picks}  累积遗憾 {regret:.3f}")
    return regret, picks


def main():
    print("反例：K=2，臂 1 恒定 −1，臂 2 恒定 +1（最优均值 1，Δ₁ = 2）")
    rew = [[-1.0] * T, [1.0] * T]
    r1, p1 = run(rew)
    print(f"  命题 1.1 的预测：Regret(T) = T·Δ₁ + O(1) = {T * 2} + O(1)")
    print(f"  实测：Regret({T}) = {r1:.3f}，在选择序列里臂 1 只出现 {p1[0]} 次\n")

    print("对照：若臂 1 恒定 +1、臂 2 恒定 0（臂 1 才是最优臂）")
    rew2 = [[1.0] * T, [0.0] * T]
    r2, p2 = run(rew2)
    print(f"  实测遗憾 {r2:.3f}（此时锁定在最优臂，遗憾为 0，命题在此情形下「成立但平凡」）\n")

    print("再对照：臂 1 恒定 +0.5（次优）、臂 2 恒定 +1（最优）")
    rew3 = [[0.5] * T, [1.0] * T]
    r3, p3 = run(rew3)
    print(f"  实测遗憾 {r3:.3f} = T·Δ₁，此时命题才真的成立（首次采样为正，锁死）\n")

    print("结论：贪心是否锁死取决于首个样本的符号，不是必然事件；")
    print("      正确表述是「存在锁定（最坏情形线性遗憾），但不保证锁定」。")


if __name__ == "__main__":
    main()
