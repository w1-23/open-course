"""Show why repeated selection needs an independent held-out evaluation.

Run from the workspace root with: python source/labs/selection_overfit_demo.py
Uses only the Python standard library.
"""

import random


SEED = 20261021
TRAIN_SIZE = 80
TEST_SIZE = 4000
ROUNDS = (1, 10, 50, 200)


def make_data(n, seed, training):
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        signal = rng.uniform(-1.0, 1.0)
        noise = rng.gauss(0.0, 0.15)
        target = signal + noise
        # In the small training sample, a nuisance feature correlates with the
        # target. In held-out data it is independent and therefore unreliable.
        nuisance = (target + rng.gauss(0.0, 0.08) if training
                    else rng.uniform(-1.0, 1.0))
        rows.append((signal, nuisance, target))
    return rows


def mse(rows, weights):
    w0, w1 = weights
    return sum((w0 * x0 + w1 * x1 - y) ** 2
               for x0, x1, y in rows) / len(rows)


def main():
    train = make_data(TRAIN_SIZE, SEED, True)
    test = make_data(TEST_SIZE, SEED + 1, False)
    rng = random.Random(SEED + 2)
    candidates = [(1.0, 0.0)]
    print("候选数  训练集最佳误差  留出集误差  被选权重(w信号, w干扰)")
    for count in range(1, max(ROUNDS) + 1):
        # Each candidate is a possible update. Selection uses only training data.
        candidates.append((rng.uniform(-1.5, 1.5), rng.uniform(-1.5, 1.5)))
        if count in ROUNDS:
            selected = min(candidates, key=lambda w: mse(train, w))
            print(f"{count:>4}    {mse(train, selected):>12.4f}"
                  f"  {mse(test, selected):>10.4f}  ({selected[0]: .2f}, {selected[1]: .2f})")
    print("说明：候选生成与选择规则固定。本实验演示反复筛选会利用训练样本偶然性；")
    print("留出集只用于最终检查，不参与候选选择，因此本实验不是完整 RSI。")


if __name__ == "__main__":
    main()
