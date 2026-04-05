#!/usr/bin/env python3
"""
Reasoning Chain Writer — logs chains with proper format.

Usage:
    python3 scripts/chain_writer.py --trigger "what started this" --chain "step1 → step2 → conclusion" --outcome "what it produced" --pattern "pattern-name"
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CHAINS_FILE = BASE / "logs" / "reasoning_chains.jsonl"


def write_chain(trigger, chain, outcome, pattern="", reusable=True):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "trigger": trigger,
        "chain": chain,
        "outcome": outcome,
        "pattern": pattern,
        "reusable": reusable,
    }

    with open(CHAINS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[chain] {trigger[:50]} → {pattern or 'no pattern'}")
    return entry


def main():
    parser = argparse.ArgumentParser(description="Reasoning Chain Writer")
    parser.add_argument("--trigger", required=True, help="What started this reasoning")
    parser.add_argument("--chain", required=True, help="Step-by-step reasoning")
    parser.add_argument("--outcome", required=True, help="What it produced")
    parser.add_argument("--pattern", default="", help="Reusable pattern name")
    parser.add_argument("--not-reusable", action="store_true", help="Mark as not reusable")
    args = parser.parse_args()

    write_chain(args.trigger, args.chain, args.outcome, args.pattern, not args.not_reusable)


if __name__ == "__main__":
    main()
