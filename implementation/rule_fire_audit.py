#!/usr/bin/env python3
"""
Rule Fire-Rate Auditor — measure which rules/hooks/checks actually fire.

The autoimmune-loop diagnosis: every failure adds a rule, no success removes
one. Without measurement we can't tell which rules are load-bearing and which
are dead weight. This script audits inferred fire-rate over a configurable
window (default 90 days) across three substrates:

1. **Hooks** (.claude/hooks/*.sh) — count appearances in hook log files +
   .output/.log files in logs/. Each appearance = one fire.

2. **QA checklist items** — scan knowledge/notes/bugs/*.md frontmatter for
   `caught_by: [N, M]` references. Each tagged item is one fire of that
   checklist item. Items 1-16 are the current QA checklist.

3. **Archivist campaigns** — scan logs/scaffold_changes.jsonl for `gate:
   archivist-campaign-X` strings. Each tagged change is one fire of that
   campaign type.

Output: per-substrate fire counts, ZERO-FIRE flags (load-bearing-suspect),
and recency (most-recent fire timestamp).

Usage:
    python3 scripts/rule_fire_audit.py                    # 90-day window default
    python3 scripts/rule_fire_audit.py --days 30          # narrower window
    python3 scripts/rule_fire_audit.py --jsonl            # machine output
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO / ".claude" / "hooks"
BUGS_DIR = REPO / "knowledge" / "notes" / "bugs"
SCAFFOLD_LOG = REPO / "logs" / "scaffold_changes.jsonl"
LOG_DIR = REPO / "logs"
OUT_LOG = LOG_DIR / "rule_fire_audit.jsonl"


def cutoff_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def audit_hooks(cutoff: str) -> dict:
    """Tally hook appearances in logs/ files newer than cutoff."""
    hooks = sorted(p.stem for p in HOOKS_DIR.glob("*.sh")) if HOOKS_DIR.exists() else []
    fires: dict[str, dict] = {h: {"count": 0, "last": None} for h in hooks}
    cutoff_dt = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    for log in LOG_DIR.glob("*"):
        if not log.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(log.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if mtime < cutoff_dt:
            continue
        try:
            text = log.read_text(errors="replace")[:200_000]
        except OSError:
            continue
        for h in hooks:
            n = text.count(h)
            if n:
                fires[h]["count"] += n
                fires[h]["last"] = max(fires[h]["last"] or "", mtime.isoformat())
    return fires


def audit_qa_checklist(cutoff: str) -> dict:
    """Scan bug notes for `caught_by:` frontmatter."""
    items: dict[int, dict] = {i: {"count": 0, "last": None, "examples": []} for i in range(1, 17)}
    if not BUGS_DIR.exists():
        return items
    re_caught = re.compile(r"^caught_by:\s*\[([0-9,\s]+)\]", re.MULTILINE)
    for bug in BUGS_DIR.rglob("*.md"):
        try:
            text = bug.read_text(errors="replace")[:5000]
        except OSError:
            continue
        try:
            mtime = datetime.fromtimestamp(bug.stat().st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            continue
        if mtime < cutoff:
            continue
        m = re_caught.search(text)
        if not m:
            continue
        for token in m.group(1).split(","):
            try:
                idx = int(token.strip())
            except ValueError:
                continue
            if 1 <= idx <= 16:
                items[idx]["count"] += 1
                items[idx]["last"] = max(items[idx]["last"] or "", mtime)
                if len(items[idx]["examples"]) < 2:
                    items[idx]["examples"].append(bug.stem)
    return items


def audit_archivist_campaigns(cutoff: str) -> dict:
    """Tally `gate: archivist-campaign-X` from scaffold_changes.jsonl."""
    campaigns: dict[str, dict] = defaultdict(lambda: {"count": 0, "last": None})
    if not SCAFFOLD_LOG.exists():
        return dict(campaigns)
    for line in SCAFFOLD_LOG.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (rec.get("ts") or "") < cutoff:
            continue
        gate = rec.get("gate", "")
        m = re.match(r"archivist-campaign-(\w+)", gate)
        if not m:
            continue
        key = m.group(1)
        campaigns[key]["count"] += 1
        campaigns[key]["last"] = max(campaigns[key]["last"] or "", rec.get("ts") or "")
    return dict(campaigns)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=90, help="Lookback window in days (default 90)")
    ap.add_argument("--jsonl", action="store_true", help="Append summary to logs/rule_fire_audit.jsonl")
    args = ap.parse_args()

    cutoff = cutoff_iso(args.days)
    hooks = audit_hooks(cutoff)
    qa = audit_qa_checklist(cutoff)
    camps = audit_archivist_campaigns(cutoff)

    print(f"\nRule Fire Audit — last {args.days} days (since {cutoff[:10]})\n")

    print("HOOKS:")
    if hooks:
        for h, d in sorted(hooks.items(), key=lambda kv: -kv[1]["count"]):
            flag = "  ← ZERO-FIRE" if d["count"] == 0 else ""
            last = (d["last"] or "—")[:10]
            print(f"  [{d['count']:4d}] {h:40s} last:{last}{flag}")
    else:
        print("  (no hooks found)")

    print("\nQA CHECKLIST (items 1-16):")
    zero_fire = [i for i, d in qa.items() if d["count"] == 0]
    fired = [(i, d) for i, d in qa.items() if d["count"] > 0]
    for i, d in sorted(fired, key=lambda kv: -kv[1]["count"]):
        last = (d["last"] or "—")[:10]
        ex = f"  ex: {', '.join(d['examples'])}" if d["examples"] else ""
        print(f"  [#{i:2d}] fires={d['count']:3d}  last:{last}{ex}")
    if zero_fire:
        print(f"  ZERO-FIRE items: {zero_fire}  ← review for deprecation or untagged bugs")

    print("\nARCHIVIST CAMPAIGNS (1-6):")
    if camps:
        for k, d in sorted(camps.items(), key=lambda kv: -kv[1]["count"]):
            last = (d["last"] or "—")[:10]
            print(f"  [{d['count']:4d}] {k:30s} last:{last}")
    else:
        print("  (no scaffold_changes.jsonl entries with archivist-campaign gate in window)")

    if args.jsonl:
        OUT_LOG.parent.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with open(OUT_LOG, "a") as f:
            f.write(json.dumps({
                "ts": ts, "window_days": args.days,
                "hooks": hooks, "qa": qa, "campaigns": camps,
            }) + "\n")
        print(f"\nAppended summary to {OUT_LOG.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
