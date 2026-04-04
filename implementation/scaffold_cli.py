#!/usr/bin/env python3
"""
Scaffold CLI — unified query tool across all logs and vault.

Navigate the full feedback filesystem: reasoning chains, breadcrumbs,
episodes, compiles, vault notes, Q-values. One tool for everything.

Inspired by Meta-Harness "build a CLI over the logs" pattern.

Usage:
    python3 scripts/scaffold_cli.py chains                    # list recent chains
    python3 scripts/scaffold_cli.py chains --pattern "verify"  # search chains by pattern
    python3 scripts/scaffold_cli.py chains --top 10            # top 10 by chain depth
    python3 scripts/scaffold_cli.py breadcrumbs                # today's breadcrumbs
    python3 scripts/scaffold_cli.py breadcrumbs --type insight # filter by type
    python3 scripts/scaffold_cli.py compiles                   # metacog compile history
    python3 scripts/scaffold_cli.py vault --search "keyword"   # search vault notes
    python3 scripts/scaffold_cli.py vault --stats              # vault health stats
    python3 scripts/scaffold_cli.py qvalues                    # pattern Q-values
    python3 scripts/scaffold_cli.py qvalues --promote          # promotion candidates
    python3 scripts/scaffold_cli.py status                     # full system status
    python3 scripts/scaffold_cli.py pareto                     # pareto frontier of patterns
    python3 scripts/scaffold_cli.py warmstart                  # export promoted patterns for cross-model
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHAINS_FILE = REPO / "logs" / "reasoning_chains.jsonl"
BREADCRUMBS_FILE = REPO / "logs" / "session_breadcrumbs.jsonl"
# [PLACEHOLDER] Replace with your system's operational log file path
JOURNAL_FILE = REPO / "logs" / "system_journal.jsonl"
VAULT = REPO / "knowledge" / "notes"
# [PLACEHOLDER] Replace with your vault's promoted-patterns subdirectory
PROMOTED_DIR = VAULT / "patterns"


def load_jsonl(path, limit=None):
    """Load JSONL file, return list of dicts."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    if limit:
        lines = lines[-limit:]
    results = []
    for line in lines:
        try:
            results.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return results


def cmd_chains(args):
    """Query reasoning chains."""
    chains = load_jsonl(CHAINS_FILE)
    if args.pattern:
        chains = [c for c in chains if args.pattern.lower() in c.get("pattern", "").lower()
                  or args.pattern.lower() in c.get("chain", "").lower()
                  or args.pattern.lower() in c.get("trigger", "").lower()]
    if args.date:
        chains = [c for c in chains if args.date in c.get("ts", "")]
    if args.reusable:
        chains = [c for c in chains if c.get("reusable", False)]

    if args.top:
        # Sort by chain depth (step count)
        chains.sort(key=lambda c: c.get("chain", "").count("→"), reverse=True)
        chains = chains[:args.top]

    print(f"\n  REASONING CHAINS — {len(chains)} results\n")
    for c in chains[-args.limit:]:
        ts = c.get("ts", "?")[:16]
        pattern = c.get("pattern", "?")[:40]
        steps = c.get("chain", "").count("→") + 1
        reusable = "✓" if c.get("reusable") else " "
        print(f"  [{ts}] {steps:2d}steps [{reusable}] {pattern}")
        if args.verbose:
            print(f"    trigger: {c.get('trigger', '?')[:70]}")
            print(f"    outcome: {c.get('outcome', '?')[:70]}")
            print()

    print(f"\n  Total: {len(load_jsonl(CHAINS_FILE))} chains")


def cmd_breadcrumbs(args):
    """Query session breadcrumbs."""
    crumbs = load_jsonl(BREADCRUMBS_FILE)
    if args.type:
        crumbs = [c for c in crumbs if c.get("type") == args.type]
    if args.search:
        crumbs = [c for c in crumbs if args.search.lower() in c.get("content", "").lower()]

    print(f"\n  BREADCRUMBS — {len(crumbs)} entries\n")
    for c in crumbs[-args.limit:]:
        ts = c.get("ts", "?")[11:16]
        typ = c.get("type", "?")[:8]
        content = c.get("content", "?")[:80]
        print(f"  [{ts}] {typ:8s} | {content}")


def cmd_compiles(args):
    """Show metacog compile history from chains."""
    chains = load_jsonl(CHAINS_FILE)
    compiles = [c for c in chains if "meta-" in c.get("pattern", "").lower()
                or "compile" in c.get("trigger", "").lower()
                or "promotion" in c.get("pattern", "").lower()]

    print(f"\n  METACOG COMPILES — {len(compiles)} entries\n")
    for c in compiles[-args.limit:]:
        ts = c.get("ts", "?")[:16]
        outcome = c.get("outcome", "?")[:80]
        print(f"  [{ts}] {outcome}")


def cmd_vault(args):
    """Query vault notes."""
    if args.stats:
        notes = list(VAULT.rglob("*.md"))
        total = len(notes)
        # Count links
        link_count = 0
        for n in notes:
            try:
                content = n.read_text(encoding="utf-8", errors="replace")
                content_clean = re.sub(r"`[^`]+`", "", content)
                links = re.findall(r"\[\[([^\]|]+)", content_clean)
                link_count += len(links)
            except:
                pass
        promoted = len(list(PROMOTED_DIR.glob("pattern-*.md")))
        print(f"\n  VAULT STATS")
        print(f"  Notes: {total}")
        print(f"  Links: {link_count}")
        print(f"  Avg links/note: {link_count/total:.1f}" if total else "  Avg: 0")
        print(f"  Promoted patterns: {promoted}")
        return

    if args.search:
        results = []
        for note in VAULT.rglob("*.md"):
            try:
                content = note.read_text(encoding="utf-8", errors="replace")
                if args.search.lower() in content.lower() or args.search.lower() in note.stem.lower():
                    # Extract summary
                    summary = ""
                    for line in content.splitlines():
                        if line.startswith("summary:"):
                            summary = line.split(":", 1)[1].strip().strip('"')[:60]
                            break
                    results.append((note.stem, summary))
            except:
                pass

        print(f"\n  VAULT SEARCH '{args.search}' — {len(results)} results\n")
        for stem, summary in results[:args.limit]:
            print(f"  {stem[:45]:45s} | {summary}")


def cmd_qvalues(args):
    """Run Q-value analysis."""
    os.system(f"python3 {REPO / 'scripts' / 'pattern_qvalue.py'} "
              f"{'--promote' if args.promote else ''} "
              f"{'--scaffold' if args.scaffold else ''}")


def cmd_status(args):
    """Full system status."""
    import subprocess

    print(f"\n  {'='*60}")
    print(f"  SCAFFOLD STATUS — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  {'='*60}\n")

    # Chains + breadcrumbs
    chains = load_jsonl(CHAINS_FILE)
    crumbs = load_jsonl(BREADCRUMBS_FILE)
    print(f"  CHAINS: {len(chains)} total")
    print(f"  BREADCRUMBS: {len(crumbs)} this session")

    # Vault
    notes = list(VAULT.rglob("*.md"))
    promoted = len(list(PROMOTED_DIR.glob("pattern-*.md")))
    print(f"\n  VAULT: {len(notes)} notes, {promoted} promoted patterns")


def cmd_pareto(args):
    """Pareto frontier of patterns — best Q-value vs chain count."""
    chains = load_jsonl(CHAINS_FILE)
    pattern_data = defaultdict(lambda: {"count": 0, "outcomes": []})
    for c in chains:
        p = c.get("pattern", "")
        if not p:
            continue
        pattern_data[p]["count"] += 1
        pattern_data[p]["outcomes"].append(c.get("outcome", ""))

    # Score each pattern
    scored = []
    for pattern, data in pattern_data.items():
        count = data["count"]
        # Simple quality proxy: outcome length suggests depth
        avg_outcome_len = sum(len(o) for o in data["outcomes"]) / max(count, 1)
        scored.append((pattern, count, avg_outcome_len))

    # Pareto: not dominated on both count AND quality
    pareto = []
    for p, c, q in scored:
        dominated = False
        for p2, c2, q2 in scored:
            if c2 > c and q2 > q:
                dominated = True
                break
        if not dominated:
            pareto.append((p, c, q))

    pareto.sort(key=lambda x: -x[1])
    print(f"\n  PARETO FRONTIER — {len(pareto)} patterns (not dominated)\n")
    for p, c, q in pareto[:args.limit]:
        print(f"  {c:3d} chains | quality {q:5.0f} | {p[:50]}")


def cmd_warmstart(args):
    """Export promoted patterns for cross-model warm-start."""
    patterns = []
    for f in sorted(PROMOTED_DIR.glob("pattern-*.md")):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            summary = ""
            behavior_name = ""
            behavior_instruction = ""
            for line in content.splitlines():
                if line.startswith("summary:"):
                    summary = line.split(":", 1)[1].strip().strip('"')
                elif line.startswith("behavior_name:"):
                    behavior_name = line.split(":", 1)[1].strip().strip('"')
                elif line.startswith("behavior_instruction:"):
                    behavior_instruction = line.split(":", 1)[1].strip().strip('"')
            agent_roles = []
            for line in content.splitlines():
                if line.startswith("agent_roles:"):
                    try:
                        agent_roles = json.loads(line.split(":", 1)[1].strip())
                    except (json.JSONDecodeError, ValueError):
                        pass
            patterns.append({
                "name": f.stem.replace("pattern-", ""),
                "summary": summary,
                "behavior_name": behavior_name,
                "behavior_instruction": behavior_instruction,
                "agent_roles": agent_roles,
            })
        except:
            continue

    if args.behaviors:
        # Compact behavior format — 97% token reduction vs full prose
        # Filter by agent role if specified
        if args.agent:
            filtered = []
            for p in patterns:
                roles = p.get("agent_roles", [])
                if args.agent in roles:
                    filtered.append(p)
            patterns_to_show = filtered
            header = f"# Behavior Handbook for {args.agent} — {len(filtered)}/{len(patterns)} patterns"
        else:
            patterns_to_show = patterns
            header = f"# Scaffold Behavior Handbook — {len(patterns)} patterns"

        print(f"{header}\n")
        for p in patterns_to_show:
            if p["behavior_name"] and p["behavior_instruction"]:
                print(f"- **{p['behavior_name']}**: {p['behavior_instruction']}")
            else:
                print(f"- **{p['name']}**: {p['summary'][:120]}")
        return

    if args.json:
        print(json.dumps(patterns, indent=2))
    else:
        print(f"\n  WARM-START EXPORT — {len(patterns)} promoted patterns\n")
        print(f"  Copy this to another model's context to warm-start:\n")
        print(f"  ---")
        for p in patterns:
            print(f"  - {p['name']}: {p['summary'][:80]}")
        print(f"  ---")
        print(f"\n  For JSON: scaffold_cli.py warmstart --json")
        print(f"  For compact: scaffold_cli.py warmstart --behaviors")


def main():
    parser = argparse.ArgumentParser(description="Scaffold CLI — unified log query tool")
    sub = parser.add_subparsers(dest="command")

    # Chains
    p = sub.add_parser("chains", help="Query reasoning chains")
    p.add_argument("--pattern", type=str, help="Filter by pattern name")
    p.add_argument("--date", type=str, help="Filter by date (YYYY-MM-DD)")
    p.add_argument("--reusable", action="store_true", help="Only reusable chains")
    p.add_argument("--top", type=int, help="Top N by chain depth")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--limit", type=int, default=20)

    # Breadcrumbs
    p = sub.add_parser("breadcrumbs", help="Query breadcrumbs")
    p.add_argument("--type", type=str, help="Filter: decision|finding|insight|action|gap")
    p.add_argument("--search", type=str, help="Text search")
    p.add_argument("--limit", type=int, default=20)

    # Compiles
    p = sub.add_parser("compiles", help="Metacog compile history")
    p.add_argument("--limit", type=int, default=10)

    # Vault
    p = sub.add_parser("vault", help="Query vault notes")
    p.add_argument("--search", type=str, help="Search vault by keyword")
    p.add_argument("--stats", action="store_true", help="Vault health stats")
    p.add_argument("--limit", type=int, default=20)

    # Q-values
    p = sub.add_parser("qvalues", help="Pattern Q-values")
    p.add_argument("--promote", action="store_true", help="Show promotion candidates")
    p.add_argument("--scaffold", action="store_true", help="Scaffold channel only")

    # Status
    sub.add_parser("status", help="Full system status")

    # Pareto
    p = sub.add_parser("pareto", help="Pareto frontier of patterns")
    p.add_argument("--limit", type=int, default=20)

    # Warmstart
    p = sub.add_parser("warmstart", help="Export patterns for cross-model")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--behaviors", action="store_true", help="Compact behavior format (97% token reduction)")
    p.add_argument("--agent", type=str, help="Filter behaviors by agent role (e.g. qa, archivist, observer, scout, metacognizer, brutus, team-lead)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmds = {
        "chains": cmd_chains,
        "breadcrumbs": cmd_breadcrumbs,
        "compiles": cmd_compiles,
        "vault": cmd_vault,
        "qvalues": cmd_qvalues,
        "status": cmd_status,
        "pareto": cmd_pareto,
        "warmstart": cmd_warmstart,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
