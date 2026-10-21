"""CH04-PROP-004 reproduction: Baird counterexample spectrum.

构造与 content/ch04.md 第 275–282 行一致：
  7 状态、8 特征（前六个 2e_i+e_8，第七个 e_7+2e_8）、目标策略恒选实线（一步到状态 7）、
  D 为均匀分布、gamma=0.99。
输出 A 的特征值、最小特征值、对称部分的最小特征值，以及各步长下的发散速率。

运行：python review/reproductions/CH04-PROP-004.py
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)

GAMMA = 0.99
N_STATES, D = 7, 8

Phi = np.zeros((N_STATES, D))
for i in range(6):
    Phi[i, i] = 2.0
    Phi[i, 7] = 1.0
Phi[6, 6] = 1.0
Phi[6, 7] = 2.0

P_pi = np.zeros((N_STATES, N_STATES))
P_pi[:, 6] = 1.0                       # 实线动作：任意状态一步到状态 7
Dm = np.eye(N_STATES) / N_STATES       # 行为策略下的更新分布是均匀分布

A = Phi.T @ Dm @ (np.eye(N_STATES) - GAMMA * P_pi) @ Phi
ev = np.sort(np.linalg.eigvals(A).real)

print("Phi shape", Phi.shape, "rank", np.linalg.matrix_rank(Phi))
print("eig(A)      =", ev)
print("min eig(A)  =", round(ev[0], 6))
print("max eig(A)  =", round(ev[-1], 6))
print("min eig(sym(A)) =", round(np.linalg.eigvalsh((A + A.T) / 2)[0], 6))
print("paper value (4.19) = {-0.2393, -0.0218, 0, 0.5714x5}")
print("second negative eigenvalue:", round(ev[1], 6))

for alpha in (0.005, 0.01, 0.02):
    rho = max(abs(1 - alpha * ev))
    print(f"alpha={alpha}: per-step factor={rho:.6f}, 3000-step growth={rho ** 3000:.3e}")
