#!/usr/bin/env python3
"""
Metacognitive Intelligence Tracker — measures scaffold reasoning quality over time.

Runs after each metacog compile. Computes:
- Pattern yield (promoted / chains since last compile)
- Chain depth (avg reasoning steps)
- Reusability ratio
- Chains per day

Appends metrics to logs/metacog_metrics.jsonl for longitudinal tracking.
Optionally posts to Discord webhook (set DISCORD_WEBHOOK env var).

Usage:
    python3 metacog_tracker.py                 # compute + log
    python3 metacog_tracker.py --report        # print trend report

Customize paths below for your project structure.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ─── CUSTOMIZE THESE PATHS ──────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent  # adjust to your project root
CHAINS_FILE = REPO_ROOT / "logs" / "reasoning_chains.jsonl"
METRICS_FILE = REPO_ROOT / "logs" / "metacog_metrics.jsonl"
PATTERNS_DIR = REPO_ROOT / "knowledge" / "notes" / "cc-operational"  # where promoted patterns live
ENV_FILE = REPO_ROOT / ".env"
DISCORD_WEBHOOK_VAR = "DISCORD_WEBHOOK"  # env var name for your webhook
# ────────────────────────────────────────────────────────────────────────────


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
    total_chains = len(chains)
    promoted = count_promoted_patterns()
    demoted = count_demoted_patterns()

    # Chains since last metric
    last_ts = prior_metrics[-1].get("ts") if prior_metrics else None
    new_chains = [c for c in chains if c.get("ts", "") > last_ts] if last_ts else chains
    new_chain_count = len(new_chains)

    # Chain depth (count arrows)
    depths = []
    for c in chains:
        chain_str = c.get("chain", "")
        depth = chain_str.count("\u2192") + chain_str.count("->") + 1
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

    # Yields
    pattern_yield = promoted / total_chains if total_chains else 0
    prior_promoted = prior_metrics[-1].get("promoted_patterns", 0) if prior_metrics else 0
    new_promoted = promoted - prior_promoted
    compile_yield = new_promoted / new_chain_count if new_chain_count > 0 else 0
    compile_num = len(prior_metrics) + 1

    return {
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


def post_discord(msg):
    try:
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        webhook = os.environ.get(DISCORD_WEBHOOK_VAR, "").strip()
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
        print(f"{m['compile_num']:>3} {ts:>12} {m['total_chains']:>7} "
              f"{m['new_chains']:>5} {m['promoted_patterns']:>8} "
              f"{m['compile_yield']:>6.1%} {m['avg_chain_depth']:>6.1f} "
              f"{m['chains_per_day']:>6.1f}")
    first, last = metrics_history[0], metrics_history[-1]
    print(f"\nDepth: {first['avg_chain_depth']:.1f} -> {last['avg_chain_depth']:.1f}")
    print(f"Yield: {first['cumulative_yield']:.1%} -> {last['cumulative_yield']:.1%}")
    print(f"Promoted: {last['promoted_patterns']} | Demoted: {last['demoted_patterns']}")


def main():
    if "--report" in sys.argv:
        prior = load_prior_metrics()
        if prior:
            trend_report(prior)
        else:
            print("No metrics history yet.")
        return

    chains = load_chains()
    prior = load_prior_metrics()
    metrics = compute_metrics(chains, prior)

    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(metrics) + "\n")

    print(f"=== METACOG TRACKER -- Compile #{metrics['compile_num']} ===")
    print(f"Chains: {metrics['total_chains']} (+{metrics['new_chains']})")
    print(f"Promoted: {metrics['promoted_patterns']} ({metrics['new_promoted']:+d}) | Demoted: {metrics['demoted_patterns']}")
    print(f"Yield: {metrics['compile_yield']:.1%} (compile) / {metrics['cumulative_yield']:.1%} (cumulative)")
    print(f"Depth: {metrics['avg_chain_depth']} avg | Rate: {metrics['chains_per_day']:.1f}/day")

    msg = (f"METACOG TRACKER -- Compile #{metrics['compile_num']}\n"
           f"Chains: {metrics['total_chains']} (+{metrics['new_chains']})\n"
           f"Promoted: {metrics['promoted_patterns']} ({metrics['new_promoted']:+d}) | "
           f"Demoted: {metrics['demoted_patterns']}\n"
           f"Yield: {metrics['compile_yield']:.1%} | Depth: {metrics['avg_chain_depth']}")
    post_discord(msg)
    print("\nMetrics logged.")


if __name__ == "__main__":
    main()
