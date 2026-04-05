#!/usr/bin/env python3
"""
Session Historian — mine old breadcrumbs for unvaulted decisions.

Surfaces breadcrumb entries >7 days old that:
- Are type: dialogue, decision, or insight (not action)
- Have >5 words in content
- Don't contain wikilinks (not already connected to vault)

Output: candidate_vault_notes.jsonl for Archivist weekly review.

Usage:
    python3 scripts/session_historian.py              # default 7-day lookback
    python3 scripts/session_historian.py --days 14    # custom lookback
    python3 scripts/session_historian.py --dry-run    # preview without writing
"""

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
BREADCRUMBS = BASE / "logs" / "session_breadcrumbs.jsonl"
ARCHIVE_DIR = BASE / "logs" / "breadcrumbs_archive"
OUTPUT = BASE / "logs" / "candidate_vault_notes.jsonl"

PROMOTABLE_TYPES = {"dialogue", "decision", "insight"}
MIN_WORDS = 5
WIKILINK_RE = re.compile(r"\[\[.+?\]\]")


def load_breadcrumbs(max_age_days):
    """Load breadcrumbs older than max_age_days from all sources."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    entries = []

    # Current breadcrumbs file
    for src in [BREADCRUMBS] + sorted(ARCHIVE_DIR.glob("*.jsonl")):
        if not src.exists():
            continue
        for line in src.read_text().splitlines():
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Handle both single objects and arrays
            items = parsed if isinstance(parsed, list) else [parsed]
            for entry in items:
                if not isinstance(entry, dict):
                    continue

                ts_str = entry.get("ts", "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue

                if ts < cutoff:
                    entries.append(entry)

    return entries


def filter_candidates(entries):
    """Filter to promotable candidates."""
    candidates = []
    for e in entries:
        etype = e.get("type", "")
        content = e.get("content", "")

        # Type filter
        if etype not in PROMOTABLE_TYPES:
            continue

        # Word count filter
        if len(content.split()) < MIN_WORDS:
            continue

        # Already-vaulted filter (has wikilinks = already connected)
        if WIKILINK_RE.search(content):
            continue

        candidates.append(e)

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Session Historian — mine old breadcrumbs")
    parser.add_argument("--days", type=int, default=7, help="Age threshold in days (default: 7)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing output")
    args = parser.parse_args()

    entries = load_breadcrumbs(args.days)
    candidates = filter_candidates(entries)

    print(f"Session Historian — {args.days}-day lookback")
    print(f"  Total breadcrumbs older than {args.days} days: {len(entries)}")
    print(f"  Promotable candidates: {len(candidates)}")
    print()

    if not candidates:
        print("  No candidates found.")
        return

    # Group by type
    by_type = {}
    for c in candidates:
        t = c.get("type", "unknown")
        by_type.setdefault(t, []).append(c)

    for t, items in sorted(by_type.items()):
        print(f"  {t}: {len(items)}")
        for item in items[:5]:  # show first 5
            content = item["content"][:80]
            print(f"    {item['ts'][:10]} — {content}")
        if len(items) > 5:
            print(f"    ... and {len(items) - 5} more")
        print()

    if not args.dry_run:
        with open(OUTPUT, "w") as f:
            for c in candidates:
                f.write(json.dumps(c) + "\n")
        print(f"  Written to {OUTPUT}")
    else:
        print("  (dry-run — no output written)")


if __name__ == "__main__":
    main()
