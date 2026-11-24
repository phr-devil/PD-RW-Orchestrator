"""Synthetic sensor example for a read-only review pilot only."""
import random


def split_sequences(samples: list[tuple[int, float, int]], seed: int = 42):
    """Rows: (time_index, synthetic_pressure, synthetic_label)."""
    shuffled = list(samples)
    random.Random(seed).shuffle(shuffled)
    cut = int(0.8 * len(shuffled))
    return shuffled[:cut], shuffled[cut:]


def naive_accuracy(predicted: list[int], truth: list[int]) -> float:
    if len(predicted) != len(truth) or not truth:
        raise ValueError("Invalid comparison")
    return sum(p == t for p, t in zip(predicted, truth)) / len(truth)


SYNTHETIC_ROWS = [
    (i, float((i // 4) % 3), (i // 4) % 2) for i in range(40)
]
