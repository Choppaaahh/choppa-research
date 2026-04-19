#!/usr/bin/env python3
"""
Retrieval Frequency Tracker — Current-reinforcement signal for vault_search.

Adamatzky physarum steal: tubes that carry nutrient flow get reinforced,
unused tubes wither. Applied here: notes that are RETRIEVED often should
weight UP in future searches (current reinforcement — dynamic signal),
COMPLEMENTARY to link-density (structural signal — static).

Data flow:
  vault_search emits top-N results -> tracker logs each as a retrieval event
  -> frequency_boost() reads history -> vault_search optionally adds boost
  to composite score (--freq-boost flag, opt-in).

Schema (logs/retrieval_frequency.jsonl, one event per line):
  {
    "ts":         ISO-8601 UTC timestamp,
    "query":      str  — the search query that produced the hit,
    "top_slug":   str  — lowercased note slug/title key (matches graph key),
    "top_score":  float — the composite score at retrieval time,
    "rank":       int  — 1-indexed rank within the result list (1..N)
  }

Schema contract (checklist item #16): writer (this file, --record path and
vault_search auto-emission) and reader (--frequencies, frequency_boost) agree
on all five field names, types, and units. Any field drift breaks the boost.

CLI:
  # Record a retrieval event manually
  python3 scripts/retrieval_frequency_tracker.py --record pattern-honest-backtest \\
      --rank 1 --query "backtest survivors" --score 3.42

  # Dump per-slug frequencies over last 30 days
  python3 scripts/retrieval_frequency_tracker.py --frequencies --days 30

  # Library use (from vault_search.py):
  from retrieval_frequency_tracker import frequency_boost
  boost = frequency_boost("pattern-honest-backtest", lookback_days=30)
  # -> float in [0.0, 1.0], log-scale normalized over corpus max
"""

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "logs" / "retrieval_frequency.jsonl"

# Schema fields — writer and reader MUST agree
SCHEMA_FIELDS = ("ts", "query", "top_slug", "top_score", "rank")


def _utcnow_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_event(slug, rank=1, query="", score=0.0):
    """Append one retrieval event to the log. Cheap — single JSONL write."""
    if not slug:
        return
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": _utcnow_iso(),
        "query": str(query)[:200],  # cap absurd lengths
        "top_slug": str(slug).lower(),
        "top_score": float(score),
        "rank": int(rank),
    }
    # Ensure schema contract
    assert set(event.keys()) == set(SCHEMA_FIELDS), "schema drift"
    try:
        with open(LOG_PATH, "a") as fh:
            fh.write(json.dumps(event, separators=(",", ":")) + "\n")
    except Exception:
        # Tracking must never crash the caller
        pass


def _load_events(lookback_days=30):
    """Read events within lookback window. Returns list of dicts."""
    if not LOG_PATH.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    events = []
    try:
        with open(LOG_PATH) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                # Verify schema shape — skip malformed rows rather than crash
                if not all(k in ev for k in SCHEMA_FIELDS):
                    continue
                try:
                    ev_ts = datetime.strptime(ev["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if ev_ts < cutoff:
                    continue
                events.append(ev)
    except Exception:
        return []
    return events


def frequencies(lookback_days=30):
    """Return {slug: count} for events in lookback window."""
    counts = {}
    for ev in _load_events(lookback_days=lookback_days):
        slug = ev["top_slug"]
        counts[slug] = counts.get(slug, 0) + 1
    return counts


def frequency_boost(slug, lookback_days=30):
    """Return 0.0-1.0 boost for a slug based on retrieval frequency.

    Log-scale normalized against the corpus maximum in the window. A slug
    never-retrieved returns 0.0. The most-retrieved slug returns ~1.0.
    Log-scale means: the 10th retrieval matters less than the 1st,
    preventing runaway positive-feedback loops (physarum tubes saturate,
    don't explode).
    """
    if not slug:
        return 0.0
    slug = str(slug).lower()
    counts = frequencies(lookback_days=lookback_days)
    if not counts:
        return 0.0
    count = counts.get(slug, 0)
    if count <= 0:
        return 0.0
    max_count = max(counts.values())
    if max_count <= 0:
        return 0.0
    # log(1+x) maps 0->0, 1->log(2)~0.693, ... ; divide by log(1+max) to
    # normalize to [0, 1]. Log-scale: diminishing returns on high counts.
    return math.log(1.0 + count) / math.log(1.0 + max_count)


def _cli():
    parser = argparse.ArgumentParser(description="Retrieval frequency tracker (Adamatzky steal)")
    sub = parser.add_mutually_exclusive_group(required=True)
    sub.add_argument("--record", type=str, metavar="SLUG",
                     help="Log one retrieval event for the given slug.")
    sub.add_argument("--frequencies", action="store_true",
                     help="Dump per-slug counts over --days window.")
    sub.add_argument("--boost", type=str, metavar="SLUG",
                     help="Print frequency_boost(SLUG) over --days window.")
    parser.add_argument("--rank", type=int, default=1,
                        help="Rank of the hit (1-indexed). Default 1.")
    parser.add_argument("--query", type=str, default="",
                        help="Query text that produced the hit.")
    parser.add_argument("--score", type=float, default=0.0,
                        help="Composite score at retrieval time.")
    parser.add_argument("--days", type=int, default=30,
                        help="Lookback window in days. Default 30.")
    args = parser.parse_args()

    if args.record:
        record_event(args.record, rank=args.rank, query=args.query, score=args.score)
        print(f"recorded: {args.record} rank={args.rank}")
        return

    if args.frequencies:
        freqs = frequencies(lookback_days=args.days)
        if not freqs:
            print(f"(no retrieval events in last {args.days} days)")
            return
        ordered = sorted(freqs.items(), key=lambda kv: -kv[1])
        print(f"{'count':>6}  slug")
        print(f"{'-'*6}  {'-'*40}")
        for slug, count in ordered:
            print(f"{count:>6}  {slug}")
        print(f"\n  total events: {sum(freqs.values())}  |  unique slugs: {len(freqs)}  "
              f"|  window: {args.days}d")
        return

    if args.boost:
        boost = frequency_boost(args.boost, lookback_days=args.days)
        print(f"boost({args.boost}, {args.days}d) = {boost:.4f}")
        return


if __name__ == "__main__":
    _cli()
