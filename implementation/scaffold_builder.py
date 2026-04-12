#!/usr/bin/env python3
"""
Scaffold Builder -- Autonomous self-improvement via cron.

Unlike autonomous_exploration (which wonders), this BUILDS.
Reads vault gaps, stale todos, unactioned insights, and proposes/executes
small improvements to the scaffold infrastructure.

Three modes:
1. GAP FILLER: reads probe QA failures + thin domains -> proposes vault notes
2. INSIGHT ROUTER: reads recent ccorner/breadcrumbs for actionable insights -> adds to todo.md
3. METRIC IMPROVER: reads fidelity/chord/coverage scores -> proposes experiments

Fires daily at 4am UTC (midnight EDT) via cron. Uses claude -p for execution.

Usage:
    python3 scaffold_builder.py              # run all 3 modes
    python3 scaffold_builder.py --mode gap    # gap filler only
    python3 scaffold_builder.py --mode insight # insight router only
    python3 scaffold_builder.py --mode metric  # metric improver only
    python3 scaffold_builder.py --dry-run      # propose but don't execute
"""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).parent.parent
PROPOSALS_LOG = REPO / "logs" / "scaffold_builder.jsonl"
TODO_FILE = REPO / "tasks" / "todo.md"

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["gap", "insight", "metric", "all"], default="all")
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()


def log_proposal(mode, proposal, executed=False):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat()[:19],
        "mode": mode,
        "proposal": proposal,
        "executed": executed,
    }
    with open(PROPOSALS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def mode_gap_filler():
    """Read probe QA failures + thin domains -> propose vault notes."""
    print("  [GAP] Scanning for vault gaps...")
    proposals = []

    # 1. Check probe QA for recent failures
    probe_log = REPO / "logs" / "vault_probe_qa_cron.log"
    if probe_log.exists():
        content = probe_log.read_text(errors="replace")
        fails = [l for l in content.splitlines() if "FAIL" in l or "WEAK" in l]
        if fails:
            recent_fails = fails[-5:]
            for f in recent_fails:
                proposals.append(f"GAP: Probe QA failure - {f.strip()[:100]}")

    # 2. Check domain balance
    domain_counts = defaultdict(int)
    vault_dir = REPO / "knowledge" / "notes"
    if vault_dir.exists():
        for f in vault_dir.rglob("*.md"):
            parts = f.relative_to(vault_dir).parts
            if len(parts) > 1:
                domain_counts[parts[0]] += 1

    thin = [(d, c) for d, c in domain_counts.items() if c < 15 and d not in ("auto-repair", "ops")]
    for domain, count in thin:
        proposals.append(f"GAP: Domain '{domain}' has only {count} notes - needs growth")

    # 3. Check for unlinked recent notes
    try:
        result = subprocess.run(
            ["python3", str(REPO / "scripts" / "index_vault.py"), "--stats"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO))
        for line in result.stdout.splitlines():
            if "orphan" in line.lower():
                proposals.append(f"GAP: {line.strip()}")
    except Exception:
        pass

    return proposals


def mode_insight_router():
    """Read recent breadcrumbs/ccorner for actionable insights -> route to todo."""
    print("  [INSIGHT] Scanning for unactioned insights...")
    proposals = []

    # Read recent breadcrumbs with type insight/finding/dialogue
    bc_file = REPO / "logs" / "session_breadcrumbs.jsonl"
    if bc_file.exists():
        actionable_types = {"insight", "finding", "dialogue"}
        action_keywords = ["should", "could", "need", "wire", "build", "add", "fix", "upgrade", "implement"]

        recent = []
        for line in bc_file.read_text(errors="replace").splitlines()[-100:]:
            try:
                bc = json.loads(line)
                if bc.get("type") in actionable_types:
                    content = bc.get("content", "")
                    if any(kw in content.lower() for kw in action_keywords):
                        recent.append(bc)
            except:
                continue

        # Check which are already in todo.md
        todo_content = TODO_FILE.read_text(errors="replace") if TODO_FILE.exists() else ""

        for bc in recent[-10:]:
            content = bc["content"][:80]
            # Simple dedup: check if key phrases are already in todo
            key_phrase = content.split("--")[0].strip() if "--" in content else content[:40]
            if key_phrase.lower() not in todo_content.lower():
                proposals.append(f"INSIGHT: {content}")

    return proposals


def mode_metric_improver():
    """Read scaffold metrics -> propose experiments to improve weakest."""
    print("  [METRIC] Analyzing scaffold health...")
    proposals = []

    metrics = {}

    # Fidelity
    fid_file = REPO / "logs" / "fidelity_scores.jsonl"
    if fid_file.exists():
        try:
            last = json.loads([l for l in fid_file.read_text().splitlines() if l.strip()][-1])
            avg = last.get("avg", {})
            metrics["fidelity"] = avg
            weakest = min(avg.items(), key=lambda x: x[1] if x[1] is not None else 1)
            if weakest[1] is not None and weakest[1] < 0.60:
                proposals.append(f"METRIC: Fidelity {weakest[0].upper()} at {weakest[1]:.0%} - propose experiment to improve")
        except Exception:
            pass

    # Chord
    try:
        result = subprocess.run(
            ["python3", str(REPO / "scripts" / "chord_measure.py")],
            capture_output=True, text=True, timeout=30, cwd=str(REPO))
        for line in result.stdout.splitlines():
            if "Avg Chord" in line:
                import re
                m = re.search(r'(\d+)%', line)
                if m:
                    chord = int(m.group(1))
                    metrics["chord"] = chord
                    if chord < 50:
                        proposals.append(f"METRIC: Chord at {chord}% - propose Chord auto-fire improvements")
    except Exception:
        pass

    # Metacog patterns usage
    try:
        result = subprocess.run(
            ["python3", str(REPO / "scripts" / "metacog_tracker.py")],
            capture_output=True, text=True, timeout=30, cwd=str(REPO))
        for line in result.stdout.splitlines():
            if "used" in line.lower() and "unused" in line.lower():
                proposals.append(f"METRIC: {line.strip()} - review unused patterns for demotion")
    except Exception:
        pass

    # Bug-patterns growth
    bug_dir = REPO / "knowledge" / "bug-patterns"
    if bug_dir.exists():
        n_bugs = len(list(bug_dir.glob("*.md")))
        metrics["bug_patterns"] = n_bugs

    return proposals


def execute_proposals(proposals):
    """Add top proposals to todo.md."""
    if not proposals:
        print("  No proposals generated.")
        return

    print(f"\n  {len(proposals)} proposals:")
    for p in proposals[:10]:
        print(f"    {p}")

    if args.dry_run:
        print("\n  [DRY RUN] Would add to todo.md")
        for p in proposals:
            log_proposal(args.mode, p, executed=False)
        return

    # Append top 5 to todo.md
    top = proposals[:5]
    with open(TODO_FILE, "a") as f:
        f.write(f"\n## Scaffold Builder Proposals ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n")
        for p in top:
            f.write(f"- [ ] {p}\n")
            log_proposal(args.mode, p, executed=True)

    print(f"\n  Added {len(top)} proposals to todo.md")

    # Post summary to Discord
    try:
        import sys
        sys.path.insert(0, str(REPO / "scripts"))
        summary = f"Scaffold Builder: {len(proposals)} proposals\n" + "\n".join(f"  {p[:80]}" for p in top)
        post(summary, "cc")
        print("  Posted to Discord")
    except Exception:
        pass


def main():
    print(f"Scaffold Builder -- {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"Mode: {args.mode}")

    proposals = []

    if args.mode in ("gap", "all"):
        proposals.extend(mode_gap_filler())
    if args.mode in ("insight", "all"):
        proposals.extend(mode_insight_router())
    if args.mode in ("metric", "all"):
        proposals.extend(mode_metric_improver())

    execute_proposals(proposals)


if __name__ == "__main__":
    main()
