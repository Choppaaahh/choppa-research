# KNOWLEDGE-GAP DECLARATION: I do not know whether callers require unrounded theta or
# whether vectors are guaranteed to have matching dimensions and nonzero norms.
# ROUTED_FROM: scripts/mech_code_offload.py slug=competitive-write-gate model={{MODEL}} cycle-89
"""Corpus-calibrated vault deduplication threshold.

Output contract:
  pairwise_calibrate returns theta rounded to four decimal places.
  gate returns max_sim, theta, and a SKIP/INSERT verdict.

Top pitfalls:
  1. Theta is CORPUS-relative; comparing gates across corpora of different densities
     is meaningless.
  2. A corpus with len<2 returns theta=0.0, which makes EVERYTHING insert. This is
     deliberate and documents permissive behavior for tiny corpora.
"""

import math
import sys


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have matching dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def pairwise_calibrate(vectors: list[list[float]]) -> float:
    """Return 0.86 times the mean nearest-neighbor cosine, rounded to four places."""
    if len(vectors) < 2:
        return 0.0
    maxima = []
    for index, vector in enumerate(vectors):
        maxima.append(max(
            _cosine(vector, other)
            for other_index, other in enumerate(vectors)
            if other_index != index
        ))
    return round(0.86 * (sum(maxima) / len(maxima)), 4)


def gate(new_vec: list[float], vectors: list[list[float]]) -> dict:
    """Classify a candidate as SKIP only when similarity strictly exceeds theta."""
    theta = pairwise_calibrate(vectors)
    max_sim = max((_cosine(new_vec, vector) for vector in vectors), default=0.0)
    return {
        "max_sim": round(max_sim, 4),
        "theta": theta,
        "verdict": "SKIP" if max_sim > theta else "INSERT",
    }


def _self_test() -> None:
    corpus = [[1, 0], [0, 1], [0.8, 0.6]]
    assert pairwise_calibrate(corpus) == 0.6307
    near_duplicate = gate([0.6, 0.8], corpus)
    assert near_duplicate["max_sim"] == 0.96
    assert near_duplicate["verdict"] == "SKIP"
    orthogonal = gate([-1, 0], corpus)
    assert orthogonal["max_sim"] == 0.0
    assert orthogonal["verdict"] == "INSERT"
    assert pairwise_calibrate([[1, 0]]) == 0.0
    assert main(["--demo"]) == 0


def _demo() -> None:
    corpus = [[1, 0], [0, 1], [0.8, 0.6]]
    print("fixture\tmax_sim\ttheta\tverdict")
    for name, vector in (("near-duplicate", [0.6, 0.8]), ("orthogonal", [-1, 0])):
        result = gate(vector, corpus)
        print(f"{name}\t{result['max_sim']:.4f}\t{result['theta']:.4f}\t{result['verdict']}")
    print(f"tiny-corpus-theta\t-\t{pairwise_calibrate([[1, 0]]):.4f}\t-")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--self-test"]:
        _self_test()
        return 0
    if args == ["--demo"]:
        _demo()
        return 0
    print("usage: competitive_write_gate.py --demo | --self-test", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

# Intended use: a write-time dedup gate for any embedded knowledge store.
# QA: T1 compile / T2 self-test / T3 demo smoke required.
# WIRE: consumer deferred to query-to-vault dedup integration.
# CONSUME: queued for next-touch wiring.

# SMOKE: python3 scripts/competitive_write_gate.py --demo
# Expected first lines:
#   fixture	max_sim	theta	verdict
#   near-duplicate	0.9600	0.6307	SKIP
#   orthogonal	0.0000	0.6307	INSERT

# RESIDUAL UNCERTAINTY:
# 1. Existing consumers may expect full-precision theta rather than four-decimal output.
# 2. Zero-vector handling is permissive and may need an explicit upstream validation rule.