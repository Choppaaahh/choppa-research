# KNOWLEDGE-GAP DECLARATION:
# 1. The downstream vault-retrieval guard's import and invocation contract is unknown.
# 2. Production embedding-cosine availability is unknown; this file uses only its fallback.
# 3. The repository's preferred JSON output schema beyond this CLI demo is unknown.
# ROUTED_FROM: scripts/mech_code_offload.py slug=zkip_filter model=<model> cycle-89

"""ZKIP counterfactual retrieval-poison anomaly scorer.

Output contract:
    anomaly_scores(...) returns rounded per-document anomaly scores.
    flag(...) returns {"scores": [...], "flagged": [...]}.
    The CLI supports --demo and --self-test; no flag prints help and exits 1.

This is the RAGuard 2607.26339 Layer-2 scoring core.  It consumes
leave-one-out stability and entropy-delta signals; the LLM decode loop is
intentionally out of scope.

text_stability is a WEAK lexical proxy for the paper's embedding cosine.
"""

from __future__ import annotations

import argparse
import difflib
import json
import math
import sys
from typing import Sequence


# Top pitfalls:
# 1. tau=0.0 ALWAYS flags top_m even on clean corpora (paper behavior).
#    Callers wanting a guard must set tau.
# 2. text_stability is a lexical proxy: semantically identical rephrasings can
#    score LOW. Use embedding cosine when available.
# 3. entropy_deltas use H(all)-H(without_i): POSITIVE means removal REDUCES
#    uncertainty, which is suspicious.
# Intended use: a pre-generation retrieval guard; activate tiered on
# high-stakes retrievals, wire next-touch.


def anomaly_scores(
    stabilities: Sequence[float],
    entropy_deltas: Sequence[float],
    lam: float = 0.5,
) -> list[float]:
    """Compute rounded ZKIP anomaly scores for parallel document signals."""
    if len(stabilities) != len(entropy_deltas):
        raise ValueError("stabilities and entropy_deltas must have equal length")
    return [
        round((1.0 - stability) + lam * max(delta, 0.0), 4)
        for stability, delta in zip(stabilities, entropy_deltas)
    ]


def flag(
    stabilities: Sequence[float],
    entropy_deltas: Sequence[float],
    lam: float = 0.5,
    top_m: int = 1,
    tau: float = 0.0,
) -> dict[str, list[float] | list[int]]:
    """Return scores and threshold-qualified indices among the top_m scores."""
    if top_m < 0:
        raise ValueError("top_m must be non-negative")
    scores = anomaly_scores(stabilities, entropy_deltas, lam)
    ranked = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    selected = ranked[:top_m]
    flagged = [index for index in selected if scores[index] >= tau]
    return {"scores": scores, "flagged": flagged}


def text_stability(ref: str, loo: str) -> float:
    """Return a weak dependency-free lexical similarity proxy."""
    return round(difflib.SequenceMatcher(None, ref, loo).ratio(), 4)


def _demo() -> dict[str, object]:
    """Run a small real-shaped scoring example for the CLI."""
    stabilities = [0.95, 0.60, 0.90]
    entropy_deltas = [-0.1, 0.4, 0.0]
    result = flag(stabilities, entropy_deltas, top_m=1, tau=0.0)
    result["proxy_stability"] = text_stability(
        "The answer is Paris.", "The answer is Paris."
    )
    return result


def _self_test() -> None:
    """Exercise calculations, adversarial guards, and the real CLI entry point."""
    # Golden fixtures are asserted verbatim from the task specification.
    assert anomaly_scores(
        [0.95, 0.60, 0.90], [-0.1, 0.4, 0.0], 0.5
    ) == [0.05, 0.6, 0.1]
    assert flag(
        [0.95, 0.60, 0.90], [-0.1, 0.4, 0.0], top_m=1, tau=0.0
    )["flagged"] == [1]
    assert flag(
        [0.95, 0.60, 0.90], [-0.1, 0.4, 0.0], top_m=1, tau=0.7
    )["flagged"] == []
    assert flag(
        [0.95, 0.92, 0.97], [-0.2, -0.1, 0.0], tau=0.3
    )["flagged"] == []
    assert text_stability("abc", "abc") == 1.0
    try:
        anomaly_scores([0.5], [0.2, 0.3])
    except ValueError:
        pass
    else:
        raise AssertionError("parallel-list mismatch must raise ValueError")
    assert flag([0.8, 0.8], [0.0, 0.0], top_m=1)["flagged"] == [0]

    # T2-ENTRY-POINT: invoke the actual CLI entry point, not only helpers.
    assert main(["--demo"]) == 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="score a demo fixture")
    parser.add_argument("--self-test", action="store_true", help="run built-in tests")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("self-test: PASS")
        return 0
    if args.demo:
        print(json.dumps(_demo(), sort_keys=True))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


# QA: T1 compile / T2 self-test / T3 real-data smoke deferred pending consumer wiring.
# WIRE: consumer-deferred; intended vault-retrieval pre-generation guard.
# CONSUME: queued for next-touch integration with tiered high-stakes retrievals.
# COMPOSITION: commit-gate and downstream retrieval wrapper are the catching layers.
#
# Relevant Notes:
# extends [[pattern-validation-vs-deployment-input-shape-mismatch]]
# same mechanism as [[pattern-cited-not-invoked]]
# extends [[pattern-build-capacity-without-wiring-consumers]]
# validates [[pattern-asymmetric-preferences]]
# extends [[pattern-compile-pass-not-module-loadable-not-semantically-correct]]
# RESIDUAL UNCERTAINTY:
# 1. No production retrieval log or embedding provider was available for T3 smoke.
# 2. Consumer wiring and its expected signal serialization remain unverified.
# 3. The paper's exact embedding implementation is intentionally not reproduced.
#
# SMOKE: python3 scripts/zkip_filter.py --demo
# Expected first lines:
#   {"flagged": [1], "proxy_stability": 1.0, "scores": [0.05, 0.6, 0.1]}