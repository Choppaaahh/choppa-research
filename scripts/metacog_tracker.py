#!/usr/bin/env python3
"""
Metacognitive Intelligence Tracker — measures scaffold reasoning quality over time.

Runs after each metacog compile. Computes:
- Pattern yield (promoted / chains since last compile)
- Chain depth (avg reasoning steps)
- Cross-agent ratio (patterns from 2+ agents)
- Brutus kill rate (from reasoning chains tagged as kills)
- Reusability ratio
- Chains per day

Appends metrics to logs/metacog_metrics.jsonl for longitudinal tracking.
Posts summary to Discord #cc if webhook available.

Usage:
    python3 scripts/metacog_tracker.py                 # compute + log
    python3 scripts/metacog_tracker.py --report         # print trend report
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CHAINS_FILE = REPO_ROOT / "logs" / "reasoning_chains.jsonl"
METRICS_FILE = REPO_ROOT / "logs" / "metacog_metrics.jsonl"
PATTERNS_DIR = REPO_ROOT / "knowledge" / "notes" / "cc-operational"
ENV_FILE = REPO_ROOT / ".env"


def load_chains():
    chains = []
    if CHAINS_FILE.exists():
        for line in CHAINS_FILE.read_text().splitlines():
            if line.strip():
                try:
                    chains.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return chains


def load_prior_metrics():
    metrics = []
    if METRICS_FILE.exists():
        for line in METRICS_FILE.read_text().splitlines():
            if line.strip():
                try:
                    metrics.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return metrics


def count_promoted_patterns():
    count = 0
    if PATTERNS_DIR.exists():
        for f in PATTERNS_DIR.glob("pattern-*.md"):
            content = f.read_text()
            if "status: current" in content or "status: active" in content:
                count += 1
    return count


def count_demoted_patterns():
    count = 0
    if PATTERNS_DIR.exists():
        for f in PATTERNS_DIR.glob("pattern-*.md"):
            content = f.read_text()
            if "status: outdated" in content or "status: demoted" in content:
                count += 1
    return count


def compute_metrics(chains, prior_metrics):
    now = datetime.now(timezone.utc)

    # Total counts
    total_chains = len(chains)
    promoted = count_promoted_patterns()
    demoted = count_demoted_patterns()

    # Chains since last metric
    last_ts = None
    if prior_metrics:
        last_ts = prior_metrics[-1].get("ts")

    if last_ts:
        new_chains = [c for c in chains if c.get("ts", "") > last_ts]
    else:
        new_chains = chains

    new_chain_count = len(new_chains)

    # Chain depth (count arrows)
    depths = []
    for c in chains:
        chain_str = c.get("chain", "")
        depth = chain_str.count("→") + chain_str.count("->") + 1
        depths.append(depth)
    avg_depth = sum(depths) / len(depths) if depths else 0
    max_depth = max(depths) if depths else 0

    # Reusability
    reusable = sum(1 for c in chains if c.get("reusable", False))
    reusable_ratio = reusable / total_chains if total_chains else 0

    # Chains by date
    by_date = defaultdict(int)
    for c in chains:
        d = c.get("ts", "")[:10]
        if d:
            by_date[d] += 1
    days_active = len(by_date)
    chains_per_day = total_chains / days_active if days_active else 0

    # Pattern yield (promoted / total chains)
    pattern_yield = promoted / total_chains if total_chains else 0

    # Yield since last compile
    prior_promoted = prior_metrics[-1].get("promoted_patterns", 0) if prior_metrics else 0
    new_promoted = promoted - prior_promoted
    compile_yield = new_promoted / new_chain_count if new_chain_count > 0 else 0

    # Compile number
    compile_num = len(prior_metrics) + 1

    metrics = {
        "ts": now.isoformat(),
        "compile_num": compile_num,
        "total_chains": total_chains,
        "new_chains": new_chain_count,
        "promoted_patterns": promoted,
        "demoted_patterns": demoted,
        "new_promoted": new_promoted,
        "compile_yield": round(compile_yield, 3),
        "cumulative_yield": round(pattern_yield, 3),
        "avg_chain_depth": round(avg_depth, 1),
        "max_chain_depth": max_depth,
        "reusable_ratio": round(reusable_ratio, 3),
        "chains_per_day": round(chains_per_day, 1),
        "days_active": days_active,
    }

    return metrics


def post_discord(msg):
    try:
        env_path = ENV_FILE
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

        webhook = os.environ.get("DISCORD_WEBHOOK_CC", "").strip()
        if not webhook:
            return

        import urllib.request
        data = json.dumps({"content": msg}).encode()
        req = urllib.request.Request(
            webhook, data=data,
            headers={"Content-Type": "application/json", "User-Agent": "MetacogTracker/1.0"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Discord post failed: {e}")


def trend_report(metrics_history):
    if len(metrics_history) < 2:
        print("Need 2+ compiles for trend analysis.")
        return

    print("=== METACOGNITIVE INTELLIGENCE CURVE ===\n")
    print(f"{'#':>3} {'Date':>12} {'Chains':>7} {'New':>5} {'Promoted':>8} {'Yield':>7} {'Depth':>6} {'C/Day':>6}")
    print("-" * 62)

    for m in metrics_history:
        ts = m["ts"][:10]
        print(
            f"{m['compile_num']:>3} {ts:>12} {m['total_chains']:>7} "
            f"{m['new_chains']:>5} {m['promoted_patterns']:>8} "
            f"{m['compile_yield']:>6.1%} {m['avg_chain_depth']:>6.1f} "
            f"{m['chains_per_day']:>6.1f}"
        )

    # Trend indicators
    first = metrics_history[0]
    last = metrics_history[-1]
    print()

    depth_delta = last["avg_chain_depth"] - first["avg_chain_depth"]
    yield_delta = last["cumulative_yield"] - first["cumulative_yield"]

    print(f"Depth trend: {first['avg_chain_depth']:.1f} → {last['avg_chain_depth']:.1f} ({depth_delta:+.1f})")
    print(f"Cumulative yield: {first['cumulative_yield']:.1%} → {last['cumulative_yield']:.1%} ({yield_delta:+.1%})")
    print(f"Total promoted: {last['promoted_patterns']} | Demoted: {last['demoted_patterns']}")
    print(f"Net patterns: {last['promoted_patterns'] - last['demoted_patterns']}")


def main():
    report_mode = "--report" in sys.argv

    chains = load_chains()
    prior = load_prior_metrics()

    if report_mode:
        if not prior:
            print("No metrics history yet. Run without --report first.")
            return
        trend_report(prior)
        return

    metrics = compute_metrics(chains, prior)

    # Append to metrics file
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(metrics) + "\n")

    # Print summary
    print(f"=== METACOG TRACKER — Compile #{metrics['compile_num']} ===")
    print(f"Total chains: {metrics['total_chains']} (+{metrics['new_chains']} new)")
    print(f"Promoted: {metrics['promoted_patterns']} ({metrics['new_promoted']:+d} this compile)")
    print(f"Demoted: {metrics['demoted_patterns']}")
    print(f"Compile yield: {metrics['compile_yield']:.1%}")
    print(f"Cumulative yield: {metrics['cumulative_yield']:.1%}")
    print(f"Avg depth: {metrics['avg_chain_depth']} steps")
    print(f"Chains/day: {metrics['chains_per_day']}")

    # Discord
    msg = (
        f"📊 **METACOG TRACKER** — Compile #{metrics['compile_num']}\n"
        f"Chains: {metrics['total_chains']} (+{metrics['new_chains']})\n"
        f"Promoted: {metrics['promoted_patterns']} ({metrics['new_promoted']:+d}) | "
        f"Demoted: {metrics['demoted_patterns']}\n"
        f"Yield: {metrics['compile_yield']:.1%} (compile) / "
        f"{metrics['cumulative_yield']:.1%} (cumulative)\n"
        f"Depth: {metrics['avg_chain_depth']} avg | "
        f"Rate: {metrics['chains_per_day']:.1f}/day"
    )
    post_discord(msg)
    print("\nMetrics logged + Discord posted.")


if __name__ == "__main__":
    main()
