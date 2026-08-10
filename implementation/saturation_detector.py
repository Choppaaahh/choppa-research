# KNOWLEDGE-GAP DECLARATION: The dispatch-escalation consumer schema is not available here; the office routing integration point is deferred. Threshold units and caller-side validation conventions are also unknown.
# ROUTED_FROM: scripts/mech_code_offload.py slug=saturation-detector model=<dispatch-model> cycle-89
"""Detect rolling success-rate saturation and attribute repeated failures.

Output contract:
- detect_drop returns recent_rate, prior_rate, drop, and flag, or an
  insufficient-history response.
- spof returns the dominant component and its share, or None if no component
  reaches the requested fraction.

Top-pitfalls:
1. drop is signed: an improvement produces a negative drop and never flags.
2. The detector compares adjacent windows, not cumulative history; a slow leak
   below threshold/window granularity is intentionally invisible.

# Intended use: an escalation signal for any dispatch/routing pipeline tracking success rates.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Sequence


def detect_drop(outcomes: list[int], window: int, threshold: float) -> dict:
    """Compare the most recent adjacent window with the preceding window."""
    if window <= 0:
        raise ValueError("window must be positive")
    if len(outcomes) < 2 * window:
        return {"flag": False, "reason": "insufficient"}

    prior = outcomes[-2 * window : -window]
    recent = outcomes[-window:]
    prior_rate = sum(prior) / window
    recent_rate = sum(recent) / window
    drop = prior_rate - recent_rate
    return {
        "recent_rate": recent_rate,
        "prior_rate": prior_rate,
        "drop": drop,
        "flag": drop >= threshold,
    }


def spof(failure_attributions: list[str], frac: float = 0.5) -> dict:
    """Return the first component meeting the requested failure share."""
    if not failure_attributions:
        return {"component": None, "share": 0.0}

    counts = Counter(failure_attributions)
    total = len(failure_attributions)
    for component, count in counts.items():
        share = count / total
        if share >= frac:
            return {"component": component, "share": share}
    return {"component": None, "share": 0.0}


def _demo() -> None:
    """Print representative detector and SPOF results as JSONL."""
    examples = [
        detect_drop([1, 1, 1, 1, 1, 0, 0, 0], window=4, threshold=0.3),
        detect_drop([1, 0, 1, 1, 1, 0, 1, 1], window=4, threshold=0.3),
        spof(["worker-A", "worker-A", "worker-A", "worker-B"]),
    ]
    for result in examples:
        print(json.dumps(result, sort_keys=True))


def _self_test() -> None:
    """Run golden, adversarial, edge, and real-entry-point checks."""
    saturation = detect_drop([1, 1, 1, 1, 1, 0, 0, 0], 4, 0.3)
    assert saturation == {
        "recent_rate": 0.25,
        "prior_rate": 1.0,
        "drop": 0.75,
        "flag": True,
    }

    steady = detect_drop([1, 0, 1, 1, 1, 0, 1, 1], 4, 0.3)
    assert steady == {
        "recent_rate": 0.75,
        "prior_rate": 0.75,
        "drop": 0.0,
        "flag": False,
    }

    short = detect_drop([1, 0, 1], 4, 0.3)
    assert short == {"flag": False, "reason": "insufficient"}

    assert spof(["A", "A", "A", "B"]) == {"component": "A", "share": 0.75}
    assert spof(["A", "B", "C", "D"]) == {"component": None, "share": 0.0}
    assert detect_drop([0, 0, 0, 0, 1, 1, 1, 1], 4, 0.3)["flag"] is False
    assert spof([]) == {"component": None, "share": 0.0}

    # T2-ENTRY-POINT: exercise the actual CLI entry point, not only helpers.
    assert main(["--demo"]) == 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and execute the selected operation."""
    parser = argparse.ArgumentParser(
        description="Detect adjacent rolling success-rate drops and SPOFs."
    )
    parser.add_argument("--demo", action="store_true", help="print representative results")
    parser.add_argument("--self-test", action="store_true", help="run built-in tests")
    args = parser.parse_args(argv)

    if args.self_test:
        _self_test()
        print("self-test: PASS")
        return 0
    if args.demo:
        _demo()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


# SMOKE: python3 scripts/saturation_detector.py --demo
# Expected first 2-3 lines:
#   {"drop": 0.75, "flag": true, "prior_rate": 1.0, "recent_rate": 0.25}
#   {"drop": 0.0, "flag": false, "prior_rate": 0.75, "recent_rate": 0.75}
#   {"component": "worker-A", "share": 0.75}

# RESIDUAL UNCERTAINTY:
# 1. The downstream dispatch-escalation signal name and payload contract remain unspecified.
# 2. No repository-specific logging or telemetry convention was provided.
# COMPOSITION: CLI self-test catches helper and entry-point regressions; dispatch routing remains the consumer layer.