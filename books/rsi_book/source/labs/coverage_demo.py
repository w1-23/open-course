"""Reproducible lesson: candidate coverage is not the same as selection accuracy.

Run with Python 3.10+:
    python source/labs/coverage_demo.py

Only the Python standard library is used. The fixed seed makes the displayed
Monte Carlo estimates repeatable. Change p, sensitivity, or false_positive_rate
to explore how proposal quality and verifier errors interact.
"""

from math import ceil, log
import random


P_CORRECT = 0.05
VERIFIER_SENSITIVITY = 0.90
VERIFIER_FALSE_POSITIVE_RATE = 0.10
TRIALS = 40_000
SEED = 20261021
COUNTS = (1, 5, 20, 59, 100)


def coverage_probability(p_correct: float, count: int) -> float:
    """Probability that count iid proposals contain at least one correct one."""
    return 1.0 - (1.0 - p_correct) ** count


def simulate(count: int, rng: random.Random) -> tuple[float, float]:
    """Return (coverage, selected accuracy) over independent proposal sets.

    The selector takes the first candidate marked positive by a noisy verifier.
    If none is marked positive, it chooses a uniformly random candidate.
    Ground truth is used only to score the selected candidate after selection.
    """
    covered = 0
    selected_correct = 0

    for _ in range(TRIALS):
        candidates = [rng.random() < P_CORRECT for _ in range(count)]
        covered += any(candidates)

        positive = None
        for index, is_correct in enumerate(candidates):
            rate = (VERIFIER_SENSITIVITY if is_correct
                    else VERIFIER_FALSE_POSITIVE_RATE)
            if rng.random() < rate:
                positive = index
                break

        winner = positive if positive is not None else rng.randrange(count)
        selected_correct += candidates[winner]

    return covered / TRIALS, selected_correct / TRIALS


def main() -> None:
    required = ceil(log(1.0 - 0.95) / log(1.0 - P_CORRECT))
    print(f"p(候选正确)={P_CORRECT:.2f}；达到 95% 理论覆盖率至少需要候选数：{required}")
    print("  N      理论覆盖率       模拟覆盖率       选中准确率")
    rng = random.Random(SEED)
    for count in COUNTS:
        coverage, accuracy = simulate(count, rng)
        theory = coverage_probability(P_CORRECT, count)
        print(f"{count:3d}      {theory:7.3%}        "
              f"{coverage:7.3%}        {accuracy:7.3%}")


if __name__ == "__main__":
    main()
