"""CH02-THM-002 的数值复现：定理 2.5 的「全状态非劣」条件究竟在挡什么。

问题
----
定理 2.5（`content/ch02.md` §2.4.3）要求「对所有状态 s 都有
E_{a~π'}[Q^π(s,a)] ≥ V^π(s)」，才得到 V^{π'} ≥ V^π 逐点成立。
`content/ch02.md` 习题 5 原本声称：「若 π' 只在某一个状态 s0 上改进，其余状态与 π 相同，
则 V^{π'}(s0)>V^π(s0)，但可能存在其他状态 s 使 V^{π'}(s)<V^π(s)。」
本脚本用两状态 MDP 检查这句话——结论是**它不成立**：
只要 π' 在其余状态与 π 完全相同，那些状态的一步优势恰为 0（非劣），
定理 2.5 就把结论推到所有状态；要使别处变差，π' 必须在别处**退化**。

构造（2 状态、2 动作、确定性转移、γ=0.9）
------------------------------------------
状态 s0：动作 good（r=+10，转到 s1）／动作 bad（r=0，转到 s1）
状态 s1：动作 stay（r=0，自环）      ／动作 drop（r=-0.5，自环）
基准策略 π = (bad, stay)：V^π(s0)=V^π(s1)=0。

情形 A（π' 只在 s0 改进，其余与 π 相同）：π' = (good, stay)
    一步优势 A(s0)=10、A(s1)=0 —— 全状态非劣
情形 B（π' 在 s0 改进、在 s1 退化）：π' = (good, drop)
    一步优势 A(s0)=10、A(s1)=-0.5 —— 违反全状态非劣

运行
----
    python review/reproductions/CH02-THM-002_two_state.py
"""
from __future__ import annotations

import numpy as np

GAMMA = 0.9
S = 2
# 每个状态的候选动作：名字 -> (奖励, 后继状态)
ACTIONS = {
    0: {"good": (10.0, 1), "bad": (0.0, 1)},
    1: {"stay": (0.0, 1), "drop": (-0.5, 1)},
}


def model(policy: tuple[str, str]):
    """由确定性平稳策略给出 (P, r)。"""
    P = np.zeros((S, S))
    r = np.zeros(S)
    for s in range(S):
        rew, nxt = ACTIONS[s][policy[s]]
        r[s] = rew
        P[s, nxt] = 1.0
    return P, r


def evaluate(policy: tuple[str, str]) -> np.ndarray:
    """解 (I - γP)V = r。"""
    P, r = model(policy)
    return np.linalg.solve(np.eye(S) - GAMMA * P, r)


def one_step_advantage(pi: tuple[str, str], pi_new: tuple[str, str]) -> np.ndarray:
    """A(s) = Q^π(s, π'(s)) - V^π(s)，确定性策略下即单动作优势。"""
    P_pi, r_pi = model(pi)
    V = evaluate(pi)
    A = np.zeros(S)
    for s in range(S):
        rew, nxt = ACTIONS[s][pi_new[s]]
        A[s] = rew + GAMMA * V[nxt] - V[s]
    return A


def check_identity(pi, pi_new, V_new, V_old, A) -> float:
    """式 (2.22)：D(s) = A(s) + γ E_{s'~P^{π'}}[D(s')]，返回最大绝对偏差。"""
    P_new, _ = model(pi_new)
    D = V_new - V_old
    lhs = D
    rhs = A + GAMMA * P_new @ D
    return float(np.max(np.abs(lhs - rhs)))


def run(name: str, pi: tuple[str, str], pi_new: tuple[str, str]) -> dict:
    V_old = evaluate(pi)
    V_new = evaluate(pi_new)
    D = V_new - V_old
    A = one_step_advantage(pi, pi_new)
    err = check_identity(pi, pi_new, V_new, V_old, A)
    print(f"--- {name}")
    print(f"    π   = {pi}   V^π   = [{V_old[0]:+.4f}, {V_old[1]:+.4f}]")
    print(f"    π'  = {pi_new}   V^π'  = [{V_new[0]:+.4f}, {V_new[1]:+.4f}]")
    print(f"    一步优势 A = [{A[0]:+.4f}, {A[1]:+.4f}]   （全状态非劣？{bool(np.all(A >= -1e-12))}）")
    print(f"    D = V^π' - V^π = [{D[0]:+.4f}, {D[1]:+.4f}]   "
          f"（(2.22) 复核最大偏差 {err:.2e}）")
    return {"A": A, "D": D, "err": err}


def main() -> int:
    base = ("bad", "stay")
    a = run("情形 A：π' 只在 s0 改进，其余与 π 完全相同", base, ("good", "stay"))
    b = run("情形 B：π' 在 s0 改进、在 s1 退化", base, ("good", "drop"))

    print("\n判定：")
    ok_a = a["err"] < 1e-9 and b["err"] < 1e-9
    print(f"  [{'OK' if ok_a else 'FAIL'}] 式 (2.22) 在两种情形下都成立（偏差 < 1e-9）")

    claim_a = a["D"][1] >= -1e-12
    print(f"  [{'OK' if claim_a else 'FAIL'}] 情形 A 的 D(s1)={a['D'][1]:+.4f} ≥ 0："
          "π' 在其余状态与 π 相同时，别处不会变差——习题 5 的「可能使其他状态变差」不成立")

    claim_b = b["D"][0] > 0 and b["D"][1] < 0
    print(f"  [{'OK' if claim_b else 'FAIL'}] 情形 B 的 D=({b['D'][0]:+.4f}, {b['D'][1]:+.4f})："
          "D(s0)>0 而 D(s1)<0，这才是「缺全状态非劣」的反例")

    theo = b["A"][1] < 0 and b["D"][1] < 0
    print(f"  [{'OK' if theo else 'FAIL'}] 情形 B 中 A(s1)<0 与 D(s1)<0 同时成立："
          "别处变差是由「别处的一步优势为负」造成的，不是由「别处被少访问」造成的")

    return 0 if (ok_a and claim_a and claim_b and theo) else 1


if __name__ == "__main__":
    raise SystemExit(main())
