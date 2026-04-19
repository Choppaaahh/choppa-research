#!/usr/bin/env python3
"""
cleanup_queue_status.py — Phase A of cleanup-queue management.

Read-only aggregator. Surfaces the deferred-cleanup backlog across 7 categories
so we can see what's accumulating and drain on cadence. No edits, ever.

Categories (stable keys for trend comparison):
  frontmatter_schema_violations  (HIGH)   — bad enum values in note frontmatter
  archive_candidate_notes        (MEDIUM) — status: archive-candidate
  superseded_notes               (MEDIUM) — status: superseded
  action_needed_notes            (MEDIUM) — action_needed: true
  bugs_no_existing_qa_item       (MEDIUM) — caught_by: [0]
  qa_items_zero_catch            (LOW)    — checklist items never fired (#4, #11, #13)
  prose_infra_gap_exceptions     (LOW)    — grandfathered broken refs pending revival
  archived_scripts               (INFO)   — scripts/archive/ + .claude/hooks/archive/
  sft_v2_templated_rows          (DEFER)  — superseded by v5 retrain
  backfilled_chains              (DEFER)  — low-signal, exclude from training

Output:
  default     : human-readable report + append one-line summary to logs/cleanup_queue.jsonl
  --json      : machine-readable full snapshot to stdout
  --trend     : read last N weekly entries, compute delta per category
  --category  : drill into one category, list items
  --weeks N   : window for --trend (default 4)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTES = REPO / "knowledge" / "notes"
BUGS = NOTES / "bugs"
EXC = REPO / ".claude" / "commit-gate-exceptions.json"
SFT_V2 = REPO / "data" / "sft_compile_ops_v2.jsonl"
BACKFILL = REPO / "logs" / "reasoning_chains_backfilled.jsonl"
ARCH_SCRIPTS = REPO / "scripts" / "archive"
ARCH_HOOKS = REPO / ".claude" / "hooks" / "archive"
HIST = REPO / "logs" / "cleanup_queue.jsonl"

PRIORITY = {
    "frontmatter_schema_violations": "HIGH",
    "archive_candidate_notes": "MEDIUM",
    "superseded_notes": "MEDIUM",
    "action_needed_notes": "MEDIUM",
    "bugs_no_existing_qa_item": "MEDIUM",
    "qa_items_zero_catch": "LOW",
    "prose_infra_gap_exceptions": "LOW",
    "archived_scripts": "INFO",
    "sft_v2_templated_rows": "DEFER",
    "backfilled_chains": "DEFER",
}

RESOLUTION = {
    "frontmatter_schema_violations": "archivist Saturday drainage — rename to controlled enum (10-15/week)",
    "archive_candidate_notes": "confirm + move to knowledge/notes/archive/",
    "superseded_notes": "verify supersedes link + move or prune",
    "action_needed_notes": "triage: execute action, or re-classify as done",
    "bugs_no_existing_qa_item": "propose new QA checklist item via metacog compile",
    "qa_items_zero_catch": "quarterly review: sharpen item, or deprecate if truly dead",
    "prose_infra_gap_exceptions": "quarterly review when trading revives (Observer etc)",
    "archived_scripts": "informational — reference copies in scripts/archive/",
    "sft_v2_templated_rows": "superseded by v5 retrain (not drained individually)",
    "backfilled_chains": "flagged exclude-from-training (not drained individually)",
}

# QA items considered "zero-catch" today. Item #8 is RESERVED (skip).
# Keep explicit so this stays deterministic across runs even as bug notes land.
ZERO_CATCH_QA_ITEMS = [4, 11, 13]


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

def _iter_md(root: Path):
    if not root.exists():
        return
    for p in root.rglob("*.md"):
        yield p


def _read_frontmatter(path: Path) -> dict:
    """Tiny YAML-ish frontmatter reader. Only captures top-level scalars we care about."""
    try:
        with path.open() as f:
            first = f.readline()
            if not first.startswith("---"):
                return {}
            out = {}
            for line in f:
                if line.startswith("---"):
                    break
                m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", line.rstrip())
                if m:
                    out[m.group(1)] = m.group(2).strip()
            return out
    except Exception:
        return {}


def collect_exceptions() -> tuple[list[str], list[str]]:
    """Return (prose_infra_gap_items, frontmatter_schema_items) as display strings."""
    prose, fm = [], []
    if not EXC.exists():
        return prose, fm
    try:
        data = json.load(EXC.open())
    except Exception:
        return prose, fm
    for e in data.get("exceptions", []) or []:
        src = e.get("source", "?")
        tgt = e.get("target", "?")
        prose.append(f"{src}:{e.get('line','?')} -> {tgt}")
    for e in data.get("frontmatter_schema", []) or []:
        src = e.get("source", "?")
        viols = ",".join(e.get("violations", []))
        fm.append(f"{src} [{viols}]")
    return prose, fm


def collect_notes_by_status() -> dict:
    # Archive/ subtree is cold-storage — notes there already resolved the queue;
    # exempt them so drained items stop counting (fix 2026-04-19 per MEDIUM drain finding).
    ARCHIVE_PREFIX = NOTES / "archive"
    archive_candidate, superseded, action_needed = [], [], []
    for p in _iter_md(NOTES):
        if ARCHIVE_PREFIX in p.parents:
            continue  # cold-storage: already drained
        fm = _read_frontmatter(p)
        st = (fm.get("status") or "").strip().strip('"').strip("'")
        if st == "archive-candidate":
            archive_candidate.append(str(p.relative_to(REPO)))
        elif st == "superseded":
            superseded.append(str(p.relative_to(REPO)))
        an = (fm.get("action_needed") or "").strip().lower()
        if an in {"true", "yes", "1"}:
            action_needed.append(str(p.relative_to(REPO)))
    return {
        "archive_candidate_notes": archive_candidate,
        "superseded_notes": superseded,
        "action_needed_notes": action_needed,
    }


def collect_bugs_no_existing_item() -> list[str]:
    """Bug notes with caught_by: [0] — flagged no-existing-QA-item."""
    out = []
    pat = re.compile(r"^caught_by:\s*\[0\]\s*$")
    for p in _iter_md(BUGS):
        try:
            with p.open() as f:
                head = []
                for i, line in enumerate(f):
                    if i > 30:
                        break
                    head.append(line)
        except Exception:
            continue
        if any(pat.match(line.strip()) for line in head):
            out.append(str(p.relative_to(REPO)))
    return out


def collect_qa_hit_counts() -> dict[int, int]:
    """Derive empirical QA checklist item hit counts from bug note frontmatter."""
    counts: Counter = Counter()
    pat = re.compile(r"^caught_by:\s*\[([^\]]*)\]")
    for p in _iter_md(BUGS):
        try:
            with p.open() as f:
                for line in f:
                    m = pat.match(line.strip())
                    if not m:
                        continue
                    for n in m.group(1).split(","):
                        n = n.strip()
                        if n.isdigit():
                            counts[int(n)] += 1
                    break
        except Exception:
            continue
    return counts


def collect_archived_scripts() -> list[str]:
    out = []
    for d in (ARCH_SCRIPTS, ARCH_HOOKS):
        if not d.exists():
            continue
        for p in d.iterdir():
            if p.is_file() and not p.name.startswith("."):
                out.append(str(p.relative_to(REPO)))
    return out


def _count_jsonl_field(path: Path, field: str, value: str) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get(field) == value:
                n += 1
    return n


def _count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open() as f:
        return sum(1 for line in f if line.strip())


# ---------------------------------------------------------------------------
# Main snapshot
# ---------------------------------------------------------------------------

def snapshot() -> dict:
    prose, fm = collect_exceptions()
    by_status = collect_notes_by_status()
    no_item_bugs = collect_bugs_no_existing_item()
    archived = collect_archived_scripts()
    qa_counts = collect_qa_hit_counts()
    zero_catch = [i for i in ZERO_CATCH_QA_ITEMS if qa_counts.get(i, 0) == 0]

    items = {
        "frontmatter_schema_violations": fm,
        "archive_candidate_notes": by_status["archive_candidate_notes"],
        "superseded_notes": by_status["superseded_notes"],
        "action_needed_notes": by_status["action_needed_notes"],
        "bugs_no_existing_qa_item": no_item_bugs,
        "qa_items_zero_catch": [f"QA item #{i}" for i in zero_catch],
        "prose_infra_gap_exceptions": prose,
        "archived_scripts": archived,
        "sft_v2_templated_rows": [f"sft_compile_ops_v2.jsonl:rationale_source=templated"] *
                                 _count_jsonl_field(SFT_V2, "rationale_source", "templated"),
        "backfilled_chains": [f"reasoning_chains_backfilled.jsonl"] *
                             _count_jsonl_lines(BACKFILL),
    }
    counts = {k: len(v) for k, v in items.items()}
    total = sum(counts.values())

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "counts": counts,
        "items": items,
        "qa_hit_counts": {str(k): v for k, v in sorted(qa_counts.items())},
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _bucket_order(cat: str) -> int:
    return {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3, "DEFER": 4}[PRIORITY[cat]]


def render_report(snap: dict) -> str:
    lines = []
    ts = snap["ts"]
    total = snap["total"]
    n_cats = sum(1 for k, v in snap["counts"].items() if v > 0)
    lines.append(f"CLEANUP QUEUE STATUS — {ts}")
    lines.append("=" * 42)
    lines.append(f"Total items: {total} across {n_cats} non-empty categories")
    lines.append("")
    for cat, cnt in sorted(snap["counts"].items(), key=lambda kv: (_bucket_order(kv[0]), -kv[1])):
        if cnt == 0:
            continue
        tag = PRIORITY[cat]
        lines.append(f"[{tag:<6}] {cnt:>4}x  {cat}")
        lines.append(f"          Resolution: {RESOLUTION[cat]}")
        lines.append("")
    lines.append("=" * 42)
    lines.append("GROWTH/DRAINAGE PROJECTION:")
    lines.append(render_trend_block(snap))
    return "\n".join(lines)


def render_category(snap: dict, cat: str) -> str:
    if cat not in snap["items"]:
        return f"unknown category: {cat}\nknown: {', '.join(sorted(snap['items'].keys()))}"
    items = snap["items"][cat]
    lines = [
        f"CATEGORY: {cat}  [{PRIORITY[cat]}]  count={len(items)}",
        f"Resolution: {RESOLUTION[cat]}",
        "-" * 42,
    ]
    # De-dup synthetic placeholders (e.g. backfilled chains repeats one line)
    if items and len(set(items)) == 1 and len(items) > 1:
        lines.append(f"{items[0]}  (x{len(items)})")
    else:
        for it in items:
            lines.append(it)
    return "\n".join(lines)


def render_trend_block(snap: dict, weeks: int = 4) -> str:
    if not HIST.exists():
        return "  (no history yet — this is the first run; trend available after 2+ weekly snapshots)"
    rows = []
    with HIST.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    if len(rows) < 2:
        return f"  (only {len(rows)} prior snapshot(s); trend available after 2+)"
    rows = rows[-weeks:]
    oldest = rows[0]
    current = snap
    lines = []
    # Overall total
    delta_total = current["total"] - oldest["total"]
    arrow = "+" if delta_total >= 0 else ""
    lines.append(f"  total: {oldest['total']} -> {current['total']} ({arrow}{delta_total}) over {len(rows)} snapshots")
    # Per-category delta, flag grew-2-weeks
    consecutive_growth = {}
    for cat in current["counts"]:
        series = [r.get("counts", {}).get(cat, 0) for r in rows] + [current["counts"][cat]]
        diffs = [series[i + 1] - series[i] for i in range(len(series) - 1)]
        grew = sum(1 for d in diffs[-2:] if d > 0)
        old = series[0]
        new = series[-1]
        delta = new - old
        if delta == 0 and grew == 0:
            continue
        arrow = "+" if delta >= 0 else ""
        flag = "  [GROWING 2+ weeks]" if grew >= 2 else ""
        lines.append(f"  {cat}: {old} -> {new} ({arrow}{delta}){flag}")
        consecutive_growth[cat] = grew
    if not lines[1:]:
        lines.append("  (no category-level change)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def append_history(snap: dict) -> None:
    try:
        HIST.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": snap["ts"], "total": snap["total"], "counts": snap["counts"]}
        with HIST.open("a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception as e:
        print(f"  (warning: failed to append history: {e})", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--json", action="store_true", help="machine-readable full snapshot")
    ap.add_argument("--trend", action="store_true", help="show trend from history")
    ap.add_argument("--weeks", type=int, default=4, help="weeks window for --trend (default 4)")
    ap.add_argument("--category", type=str, default=None, help="drill into one category")
    ap.add_argument("--no-append", action="store_true", help="skip appending to history jsonl")
    args = ap.parse_args()

    snap = snapshot()

    if args.category:
        print(render_category(snap, args.category))
        return 0

    if args.json:
        print(json.dumps(snap, indent=2))
        return 0

    if args.trend:
        print(render_trend_block(snap, weeks=args.weeks))
        return 0

    print(render_report(snap))
    if not args.no_append:
        append_history(snap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
