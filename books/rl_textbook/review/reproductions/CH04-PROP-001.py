"""CH04-PROP-001 / 004 reproduction (v2).

A. 式 (4.17) 的第二个等号：一般地 u^T A u = ||v||_mu^2 - gamma <v,Pv>_mu，
   只有 <v,Pv>_mu = ||v||_mu^2 时才等于 (1-gamma)||v||_mu^2。用一个不可约
   3 状态链给出反例数值，并验证 >= (1-gamma)||v||^2 仍成立。

B. Baird 反例的谱：核对式 (4.19) 的 {−0.2393, −0.0218, 0, 0.5714(五重)}
   与正文"最小特征值 −1.02 为负"的说法。

运行：python review/reproductions/CH04-PROP-001.py
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)


def check_identity():
    gamma = 0.9
    # 不可约链：平稳分布满支撑
    P = np.array([[0.20, 0.70, 0.10],
                  [0.30, 0.50, 0.20],
                  [0.10, 0.30, 0.60]])
    evals, evecs = np.linalg.eig(P.T)
    idx = int(np.argmin(np.abs(evals - 1.0)))
    mu = np.real(evecs[:, idx])
    mu = mu / mu.sum()
    D = np.diag(mu)
    Phi = np.array([[1.0, 0.0],
                    [1.0, 1.0],
                    [0.0, 1.0]])

    print("[A] mu =", np.round(mu, 4))
    worst = 0.0
    for u in (np.array([1.0, -1.0]), np.array([1.0, 2.0]), np.array([-2.0, 1.0])):
        v = Phi @ u
        A = Phi.T @ D @ (np.eye(3) - gamma * P) @ Phi
        lhs = u @ A @ u
        quad_v = v @ D @ v
        cross = v @ D @ (P @ v)
        gap = lhs - (1 - gamma) * quad_v
        worst = max(worst, abs(gap))
        print(f"    u={u}: u^T A u={lhs:.6f}  ||v||^2={quad_v:.6f}  <v,Pv>={cross:.6f}"
              f"  ||v||^2-g<v,Pv>={quad_v - gamma * cross:.6f}"
              f"  (1-g)||v||^2={(1 - gamma) * quad_v:.6f}  diff={gap:+.6f}")
    print("    equality (1-g)||v||^2 holds for none of the three u:", worst > 1e-9)
    print("    inequality u^T A u >= (1-g)||v||^2 holds:", worst > -1e-12)
    # 反例：<v,Pv> 为负时，u^T A u 明显大于 (1-g)||v||^2
    u = np.array([1.0, -1.0])
    v = Phi @ u
    A = Phi.T @ D @ (np.eye(3) - gamma * P) @ Phi
    print("    ratio u^T A u / ((1-g)||v||^2) =",
          round((u @ A @ u) / ((1 - gamma) * (v @ D @ v)), 4))


def baird():
    gamma = 0.99
    n_states, d = 7, 8
    Phi = np.zeros((n_states, d))
    for i in range(6):
        Phi[i, i] = 2.0
        Phi[i, 7] = 1.0
    Phi[6, 6] = 1.0
    Phi[6, 7] = 2.0
    print("\n[B] Phi shape", Phi.shape, "rank", np.linalg.matrix_rank(Phi))

    P_pi = np.zeros((n_states, n_states))
    P_pi[:, 6] = 1.0
    D = np.eye(n_states) / n_states
    A = Phi.T @ D @ (np.eye(n_states) - gamma * P_pi) @ Phi
    ev = np.sort(np.linalg.eigvals(A).real)
    print("    eig(A) =", ev)
    print("    min eig =", round(ev[0], 6), " max eig =", round(ev[-1], 6))
    target = np.array([-0.2393, -0.0218, 0.0, 0.5714, 0.5714, 0.5714, 0.5714, 0.5714])
    print("    matches (4.19) at 1e-3?", np.allclose(ev, target, atol=1e-3))
    print("    matches (4.19) at 1e-4?", np.allclose(np.round(ev, 4), np.round(target, 4),
                                                    atol=5e-5))
    for alpha in (0.005, 0.01, 0.02):
        rho = max(abs(1 - alpha * ev))
        print(f"    alpha={alpha}: rho(I-aA)={rho:.6f}, 3000-step growth={rho ** 3000:.3e}")
    # 其它可能的 −1.02 来源：A 的对称部分、以及 on-policy 分布下的 A
    sym = (A + A.T) / 2
    print("    min eig(sym(A)) =", round(np.linalg.eigvalsh(sym)[0], 6))
    d_pi = np.zeros(n_states)
    d_pi[6] = 1.0
    A_pi = Phi.T @ np.diag(d_pi) @ (np.eye(n_states) - gamma * P_pi) @ Phi
    print("    eig(A) under D=d^pi:", np.round(np.sort(np.linalg.eigvals(A_pi).real), 4))


if __name__ == "__main__":
    check_identity()
    baird()
