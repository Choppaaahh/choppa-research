#!/usr/bin/env python3
"""
Pattern Reliability Profiles — Paper 4 steal (Reasoning Graphs, arXiv 2604.07595).

Instead of binary promoted/demoted, track continuous reliability per context:
  - How many times used vs rejected
  - Outcome quality when used (positive/negative chains)
  - Per-regime reliability (chop vs trending vs scaffold)
  - Verdict distribution for decision-time context

Reads: reasoning_chains.jsonl, meta_feedback.jsonl, pattern_qvalue output
Writes: logs/pattern_reliability.json (consumed by metacog compile + CC context)

Usage:
    python3 scripts/pattern_reliability.py              # compute all profiles
    python3 scripts/pattern_reliability.py --pattern X  # show specific pattern
    python3 scripts/pattern_reliability.py --top 10     # top 10 most reliable
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).parent.parent
CHAINS_FILE = REPO / "logs" / "reasoning_chains.jsonl"
META_FILE = REPO / "logs" / "meta_feedback.jsonl"
BREADCRUMBS_FILE = REPO / "logs" / "session_breadcrumbs.jsonl"
OUTPUT_FILE = REPO / "logs" / "pattern_reliability.json"

parser = argparse.ArgumentParser()
parser.add_argument("--pattern", type=str, default="", help="Show specific pattern")
parser.add_argument("--top", type=int, default=20, help="Show top N")
parser.add_argument("--min-uses", type=int, default=2, help="Min uses to report")
args = parser.parse_args()


def load_chains():
    """Load reasoning chains and extract pattern references + outcomes."""
    chains = []
    if not CHAINS_FILE.exists():
        return chains
    for line in CHAINS_FILE.read_text(errors="replace").splitlines():
        try:
            c = json.loads(line)
            chains.append(c)
        except:
            continue
    return chains


def load_breadcrumbs():
    """Load breadcrumbs for outcome correlation."""
    crumbs = []
    if not BREADCRUMBS_FILE.exists():
        return crumbs
    for line in BREADCRUMBS_FILE.read_text(errors="replace").splitlines():
        try:
            crumbs.append(json.loads(line))
        except:
            continue
    return crumbs


def classify_chain_outcome(chain):
    """Classify a reasoning chain's outcome as positive, negative, or neutral."""
    outcome = chain.get("outcome", "").lower()
    pattern = chain.get("pattern", "")

    # Positive signals
    pos_signals = ["fixed", "solved", "validated", "confirmed", "deployed", "built",
                   "improvement", "beats", "correct", "working", "proved", "success"]
    # Negative signals
    neg_signals = ["failed", "broken", "wrong", "bug", "error", "crash", "lost",
                   "regression", "worse", "dead end", "abandoned"]

    for s in pos_signals:
        if s in outcome:
            return "positive"
    for s in neg_signals:
        if s in outcome:
            return "negative"
    return "neutral"


def classify_context(chain):
    """Classify the context/regime of a reasoning chain."""
    trigger = chain.get("trigger", "").lower()
    chain_text = chain.get("chain", "").lower()
    full = trigger + " " + chain_text

    if any(w in full for w in ["spread", "fill", "mm ", "maker", "dqn", "reward", "equities"]):
        return "trading"
    if any(w in full for w in ["trending", "regime", "vol ", "chop"]):
        return "regime"
    if any(w in full for w in ["vault", "note", "compile", "breadcrumb", "scaffold"]):
        return "scaffold"
    if any(w in full for w in ["bug", "fix", "qa", "error"]):
        return "qa"
    return "general"


def compute_reliability():
    """Compute reliability profiles for all patterns."""
    chains = load_chains()
    if not chains:
        print("No reasoning chains found.")
        return {}

    # Aggregate per pattern
    profiles = defaultdict(lambda: {
        "uses": 0, "positive": 0, "negative": 0, "neutral": 0,
        "contexts": defaultdict(lambda: {"uses": 0, "positive": 0, "negative": 0, "neutral": 0}),
        "first_seen": None, "last_seen": None,
        "reusable_count": 0,
        "example_outcomes": [],
    })

    for chain in chains:
        pattern = chain.get("pattern", "")
        if not pattern or pattern == "?":
            continue

        p = profiles[pattern]
        p["uses"] += 1
        outcome = classify_chain_outcome(chain)
        p[outcome] += 1

        ctx = classify_context(chain)
        p["contexts"][ctx]["uses"] += 1
        p["contexts"][ctx][outcome] += 1

        ts = chain.get("ts", "")
        if ts:
            if not p["first_seen"] or ts < p["first_seen"]:
                p["first_seen"] = ts
            if not p["last_seen"] or ts > p["last_seen"]:
                p["last_seen"] = ts

        if chain.get("reusable", False):
            p["reusable_count"] += 1

        # Keep last 3 outcomes as examples
        if len(p["example_outcomes"]) < 3:
            p["example_outcomes"].append({
                "ts": ts[:16] if ts else "?",
                "outcome": outcome,
                "text": chain.get("outcome", "")[:100],
            })

    # Compute reliability scores
    results = {}
    for pattern, p in profiles.items():
        total = p["uses"]
        reliability = p["positive"] / total if total > 0 else 0
        failure_rate = p["negative"] / total if total > 0 else 0

        # Per-context reliability
        ctx_scores = {}
        for ctx, cd in p["contexts"].items():
            ct = cd["uses"]
            ctx_scores[ctx] = {
                "uses": ct,
                "reliability": cd["positive"] / ct if ct > 0 else 0,
                "failure_rate": cd["negative"] / ct if ct > 0 else 0,
            }

        results[pattern] = {
            "uses": total,
            "positive": p["positive"],
            "negative": p["negative"],
            "neutral": p["neutral"],
            "reliability": round(reliability, 3),
            "failure_rate": round(failure_rate, 3),
            "contexts": ctx_scores,
            "first_seen": p["first_seen"],
            "last_seen": p["last_seen"],
            "reusable_pct": round(p["reusable_count"] / total * 100, 1) if total else 0,
            "examples": p["example_outcomes"],
        }

    return results


def main():
    profiles = compute_reliability()

    if not profiles:
        return

    # Save full profiles
    with open(OUTPUT_FILE, "w") as f:
        json.dump(profiles, f, indent=2, default=str)

    # Display
    if args.pattern:
        p = profiles.get(args.pattern)
        if p:
            print(f"\n  Pattern: {args.pattern}")
            print(f"  Uses: {p['uses']} | Reliability: {p['reliability']:.1%} | Failure: {p['failure_rate']:.1%}")
            print(f"  Outcomes: +{p['positive']} / -{p['negative']} / ~{p['neutral']}")
            print(f"  Active: {p['first_seen'][:10] if p['first_seen'] else '?'} → {p['last_seen'][:10] if p['last_seen'] else '?'}")
            if p["contexts"]:
                print(f"  Per-context:")
                for ctx, cs in sorted(p["contexts"].items(), key=lambda x: -x[1]["uses"]):
                    print(f"    {ctx:>10}: {cs['uses']}x reliability={cs['reliability']:.1%}")
        else:
            print(f"  Pattern '{args.pattern}' not found")
        return

    # Top patterns by uses (filtered by min-uses)
    sorted_patterns = sorted(
        [(k, v) for k, v in profiles.items() if v["uses"] >= args.min_uses],
        key=lambda x: -x[1]["uses"]
    )

    print(f"\n{'='*70}")
    print(f"PATTERN RELIABILITY PROFILES — {len(profiles)} patterns, {sum(p['uses'] for p in profiles.values())} total uses")
    print(f"{'='*70}")

    for pattern, p in sorted_patterns[:args.top]:
        r = p["reliability"]
        bar = "█" * int(r * 10) + "░" * (10 - int(r * 10))
        ctx_str = " ".join(f"{c}:{s['reliability']:.0%}" for c, s in
                          sorted(p["contexts"].items(), key=lambda x: -x[1]["uses"])[:3])
        print(f"  {pattern:>45} | {p['uses']:>3}x [{bar}] {r:.0%} | {ctx_str}")

    # Summary stats
    total_uses = sum(p["uses"] for p in profiles.values())
    avg_reliability = sum(p["reliability"] * p["uses"] for p in profiles.values()) / max(total_uses, 1)
    multi_use = sum(1 for p in profiles.values() if p["uses"] >= 2)
    print(f"\n  Total: {len(profiles)} patterns, {total_uses} uses, {multi_use} multi-use")
    print(f"  Weighted avg reliability: {avg_reliability:.1%}")
    print(f"  Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
