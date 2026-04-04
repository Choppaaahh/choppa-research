#!/usr/bin/env python3
"""
Chain-to-Vault Exporter — convert reasoning chains into Obsidian-visible vault notes.

Creates one note per day in knowledge/notes/patterns/chains/
Each note contains all chains from that day with wikilinks to promoted patterns.

Usage:
    python3 scripts/chains_to_vault.py              # export all
    python3 scripts/chains_to_vault.py --date 2025-11-01  # single day
    python3 scripts/chains_to_vault.py --stats       # show counts only
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHAINS_FILE = REPO / "logs" / "reasoning_chains.jsonl"
# [PLACEHOLDER] Replace with your vault's chains output directory
OUTPUT_DIR = REPO / "knowledge" / "notes" / "patterns" / "chains"
# [PLACEHOLDER] Replace with your vault's promoted-patterns directory
PROMOTED_DIR = REPO / "knowledge" / "notes" / "patterns"


def load_promoted_patterns():
    """Get mapping of pattern name → vault note filename."""
    patterns = {}
    for f in PROMOTED_DIR.glob("pattern-*.md"):
        name = f.stem.replace("pattern-", "")
        patterns[name] = f.stem
    return patterns


def load_chains():
    """Load all chains grouped by date."""
    by_day = defaultdict(list)
    if not CHAINS_FILE.exists():
        return by_day

    with open(CHAINS_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                c = json.loads(line)
                day = c.get("ts", "")[:10]
                if day:
                    by_day[day].append(c)
            except (json.JSONDecodeError, ValueError):
                continue
    return by_day


def pattern_to_wikilink(pattern_name, promoted):
    """Convert pattern name to wikilink if it's promoted."""
    normalized = pattern_name.lower().replace(" ", "-").replace("_", "-")
    if normalized in promoted:
        return f"[[{promoted[normalized]}|{pattern_name}]]"
    return f"`{pattern_name}`"


def export_day(day, chains, promoted):
    """Write one vault note for a day's chains."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"reasoning-chains-{day}.md"
    filepath = OUTPUT_DIR / filename

    # Count patterns
    patterns_seen = set()
    for c in chains:
        if c.get("pattern"):
            patterns_seen.add(c["pattern"])

    reusable = sum(1 for c in chains if c.get("reusable"))

    body_lines = []
    for i, c in enumerate(chains, 1):
        trigger = c.get("trigger", "unknown")
        chain = c.get("chain", "")
        outcome = c.get("outcome", "")
        pattern = c.get("pattern", "")
        ts = c.get("ts", "")[11:16] if len(c.get("ts", "")) > 16 else ""

        pattern_display = pattern_to_wikilink(pattern, promoted) if pattern else "none"

        body_lines.append(f"### Chain {i} — {ts}")
        body_lines.append(f"**Trigger:** {trigger}")
        body_lines.append(f"**Chain:** {chain}")
        body_lines.append(f"**Outcome:** {outcome}")
        body_lines.append(f"**Pattern:** {pattern_display}")
        if c.get("reusable"):
            body_lines.append("**Reusable:** yes")
        body_lines.append("")

    # Collect all promoted patterns referenced
    linked_patterns = []
    for p in patterns_seen:
        norm = p.lower().replace(" ", "-").replace("_", "-")
        if norm in promoted:
            linked_patterns.append(f"- [[{promoted[norm]}]]")

    content = f"""---
summary: "{len(chains)} reasoning chains from {day}. {len(patterns_seen)} unique patterns, {reusable} reusable."
type: insight
status: current
domains: ["patterns"]
date: {day}
---

# Reasoning Chains — {day}

{len(chains)} chains logged. {len(patterns_seen)} unique patterns. {reusable} marked reusable.

{"".join(line + chr(10) for line in body_lines)}
---

Promoted Patterns Referenced:
{chr(10).join(linked_patterns) if linked_patterns else "- none"}

Domains:
- [[patterns-moc]]
"""

    filepath.write_text(content, encoding="utf-8")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Chain-to-Vault Exporter")
    parser.add_argument("--date", type=str, help="Export single date (YYYY-MM-DD)")
    parser.add_argument("--stats", action="store_true", help="Show counts only")
    args = parser.parse_args()

    by_day = load_chains()
    promoted = load_promoted_patterns()

    if args.stats:
        print(f"\n{'='*50}")
        print(f"CHAIN-TO-VAULT EXPORTER")
        print(f"{'='*50}\n")
        for day in sorted(by_day):
            print(f"  {day}: {len(by_day[day])} chains")
        print(f"\n  Total: {sum(len(v) for v in by_day.values())} chains across {len(by_day)} days")
        print(f"  Promoted patterns available for linking: {len(promoted)}")
        return

    if args.date:
        if args.date in by_day:
            fp = export_day(args.date, by_day[args.date], promoted)
            print(f"  Exported {len(by_day[args.date])} chains → {fp}")
        else:
            print(f"  No chains for {args.date}")
        return

    # Export all days
    total = 0
    for day in sorted(by_day):
        fp = export_day(day, by_day[day], promoted)
        count = len(by_day[day])
        total += count
        print(f"  {day}: {count} chains → {fp.name}")

    print(f"\n  Total: {total} chains exported to {len(by_day)} vault notes")
    print(f"  Location: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
