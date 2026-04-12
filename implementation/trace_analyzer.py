#!/usr/bin/env python3
"""
Trace Analyzer -- GEPA-inspired failure analysis for pattern mutations.

NousResearch Hermes steal: reads the full reasoning chain of FAILED patterns,
understands WHY they failed, and proposes directional mutations.

Q-values say "this pattern scored 0.3" (scalar).
Trace analysis says "this pattern failed because X, mutate condition Y" (directional).

Usage:
    python3 trace_analyzer.py --analyze              # analyze recent failed chains
    python3 trace_analyzer.py --propose              # propose mutations
    python3 trace_analyzer.py --report               # failure pattern report
"""
import argparse
import json
import os
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).parent.parent
CHAINS_FILE = REPO / "logs" / "reasoning_chains.jsonl"
BREADCRUMBS_FILE = REPO / "logs" / "session_breadcrumbs.jsonl"
MUTATIONS_FILE = REPO / "logs" / "trace_mutations.jsonl"

parser = argparse.ArgumentParser()
parser.add_argument("--analyze", action="store_true")
parser.add_argument("--propose", action="store_true")
parser.add_argument("--report", action="store_true")
parser.add_argument("--days", type=int, default=7)
args = parser.parse_args()


# Failure indicators in chain outcomes
FAILURE_SIGNALS = [
    "failed", "broken", "wrong", "killed", "lost", "negative",
    "underperform", "worse", "bug", "error", "crash", "stale",
    "overcorrect", "exploit", "dead code", "not fire", "never ran",
]

SUCCESS_SIGNALS = [
    "validated", "confirmed", "improved", "beat", "works",
    "deployed", "shipped", "fixed", "correct", "proven",
]


def load_chains(days=7):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()[:10]
    chains = []
    if CHAINS_FILE.exists():
        for line in CHAINS_FILE.read_text(errors="replace").splitlines():
            try:
                c = json.loads(line)
                if c.get("ts", "") >= cutoff:
                    chains.append(c)
            except:
                pass
    return chains


def classify_chain(chain):
    """Classify a chain as success, failure, or neutral."""
    outcome = chain.get("outcome", "").lower()
    trigger = chain.get("trigger", "").lower()
    full = f"{trigger} {outcome}"

    fail_count = sum(1 for s in FAILURE_SIGNALS if s in full)
    success_count = sum(1 for s in SUCCESS_SIGNALS if s in full)

    if fail_count > success_count:
        return "failure"
    elif success_count > fail_count:
        return "success"
    return "neutral"


def extract_failure_reason(chain):
    """Extract WHY the chain failed from the chain text."""
    chain_text = chain.get("chain", "")
    outcome = chain.get("outcome", "")

    # Look for causal patterns
    reasons = []
    for text in [chain_text, outcome]:
        text_lower = text.lower()
        # "because" clauses
        if "because" in text_lower:
            idx = text_lower.index("because")
            reasons.append(text[idx:idx+100].strip())
        # "due to" clauses
        if "due to" in text_lower:
            idx = text_lower.index("due to")
            reasons.append(text[idx:idx+100].strip())
        # arrow patterns "X -> failed because Y"
        if "->" in text and ("failed" in text_lower or "wrong" in text_lower):
            parts = text.split("->")
            for p in parts:
                if any(s in p.lower() for s in FAILURE_SIGNALS):
                    reasons.append(p.strip()[:100])

    return reasons if reasons else [outcome[:100]]


def propose_mutation(chain, failure_reasons):
    """Propose a directional mutation based on failure analysis."""
    pattern = chain.get("pattern", "")
    trigger = chain.get("trigger", "")
    outcome = chain.get("outcome", "")

    # Classify failure type
    mutation = {
        "pattern": pattern,
        "trigger": trigger[:100],
        "failure_reasons": failure_reasons,
        "proposed_mutation": "",
        "confidence": "low",
    }

    outcome_lower = outcome.lower()

    if "overcorrect" in outcome_lower or "too aggressive" in outcome_lower:
        mutation["proposed_mutation"] = f"SOFTEN: {pattern} parameters are too aggressive. Reduce thresholds/multipliers by 30-50%."
        mutation["confidence"] = "medium"
    elif "dead code" in outcome_lower or "never fire" in outcome_lower or "not fire" in outcome_lower:
        mutation["proposed_mutation"] = f"ACTIVATE: {pattern} exists but conditions prevent firing. Check thresholds, data requirements, feature availability."
        mutation["confidence"] = "high"
    elif "exploit" in outcome_lower or "hack" in outcome_lower:
        mutation["proposed_mutation"] = f"GUARD: {pattern} has an exploitable path. Add bounds/caps to prevent degenerate behavior."
        mutation["confidence"] = "high"
    elif "wrong" in outcome_lower and "fee" in outcome_lower:
        mutation["proposed_mutation"] = f"FIX INPUT: {pattern} uses wrong data source (fees, prices, etc). Verify all inputs are per-coin aware."
        mutation["confidence"] = "high"
    elif "stale" in outcome_lower or "stuck" in outcome_lower:
        mutation["proposed_mutation"] = f"ADD TIMEOUT: {pattern} gets stuck. Add time-based decay or forced re-evaluation."
        mutation["confidence"] = "medium"
    else:
        mutation["proposed_mutation"] = f"INVESTIGATE: {pattern} failed for unclear reasons. Manual review needed. Reasons: {'; '.join(failure_reasons[:2])}"
        mutation["confidence"] = "low"

    return mutation


def analyze():
    """Analyze recent failed chains and extract failure patterns."""
    chains = load_chains(args.days)
    if not chains:
        print("No chains in the last {args.days} days.")
        return

    classified = {"success": [], "failure": [], "neutral": []}
    for c in chains:
        cat = classify_chain(c)
        classified[cat].append(c)

    print(f"TRACE ANALYSIS — Last {args.days} Days")
    print(f"{'='*60}")
    print(f"  Total chains: {len(chains)}")
    print(f"  Success: {len(classified['success'])}")
    print(f"  Failure: {len(classified['failure'])}")
    print(f"  Neutral: {len(classified['neutral'])}")

    # Failure pattern frequency
    failure_patterns = Counter()
    for c in classified["failure"]:
        failure_patterns[c.get("pattern", "unnamed")] += 1

    if failure_patterns:
        print(f"\n  Top failure patterns:")
        for pattern, count in failure_patterns.most_common(10):
            print(f"    {pattern}: {count}x")

    # Detailed failure analysis
    print(f"\n  Failure Details:")
    for c in classified["failure"][:10]:
        reasons = extract_failure_reason(c)
        print(f"\n    Pattern: {c.get('pattern', '?')}")
        print(f"    Trigger: {c.get('trigger', '?')[:80]}")
        print(f"    Why: {reasons[0][:80]}")

    return classified


def propose():
    """Propose mutations for failed patterns."""
    chains = load_chains(args.days)
    failures = [c for c in chains if classify_chain(c) == "failure"]

    if not failures:
        print("No failures to propose mutations for.")
        return

    print(f"MUTATION PROPOSALS — {len(failures)} failures analyzed")
    print(f"{'='*60}")

    mutations = []
    for c in failures:
        reasons = extract_failure_reason(c)
        m = propose_mutation(c, reasons)
        mutations.append(m)

        print(f"\n  [{m['confidence'].upper():>6}] {m['pattern']}")
        print(f"    Mutation: {m['proposed_mutation'][:100]}")

    # Save mutations
    with open(MUTATIONS_FILE, "w") as f:
        for m in mutations:
            m["ts"] = datetime.now(timezone.utc).isoformat()[:19]
            f.write(json.dumps(m) + "\n")

    high = sum(1 for m in mutations if m["confidence"] == "high")
    med = sum(1 for m in mutations if m["confidence"] == "medium")
    print(f"\n  {high} high-confidence, {med} medium-confidence mutations proposed")
    print(f"  Saved to {MUTATIONS_FILE}")


def report():
    """Failure pattern report with trends."""
    chains = load_chains(args.days)

    # Trend: are failures increasing or decreasing?
    by_day = defaultdict(lambda: {"success": 0, "failure": 0, "neutral": 0})
    for c in chains:
        day = c.get("ts", "")[:10]
        cat = classify_chain(c)
        by_day[day][cat] += 1

    print(f"FAILURE TREND — Last {args.days} Days")
    print(f"{'='*60}")
    print(f"{'Date':>12} {'Success':>8} {'Failure':>8} {'Neutral':>8} {'Fail%':>6}")
    print("-" * 45)
    for day in sorted(by_day.keys()):
        d = by_day[day]
        total = d["success"] + d["failure"] + d["neutral"]
        fail_pct = d["failure"] / max(total, 1) * 100
        print(f"{day:>12} {d['success']:>8} {d['failure']:>8} {d['neutral']:>8} {fail_pct:>5.0f}%")


if __name__ == "__main__":
    if args.analyze:
        analyze()
    elif args.propose:
        propose()
    elif args.report:
        report()
    else:
        parser.print_help()
