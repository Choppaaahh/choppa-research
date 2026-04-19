#!/usr/bin/env python3
"""
retrieval_reuse_tracker.py — within-session vault_search reuse-rate measurement.

Third member of the retrieval-quality telemetry triple:
  - retrieval_frequency_tracker.py  — corpus-scoped: which notes get retrieved over time?
                                      (Adamatzky current-reinforcement, λ=0.05 boost)
  - query_shape_telemetry.py        — corpus-scoped: what SHAPE are the queries?
  - retrieval_reuse_tracker.py (here) — session-scoped: are notes REVISITED within
                                       a session/task, or is every query fresh?

Source: cycle-16 Brutus Deepdive #4 (arXiv 2508.13171 Cognitive Workspace) — the paper
reports 54-57% reuse-rate vs 0% for stateless RAG. Our scaffold should show non-trivial
reuse within a session because related-topic queries should hit overlapping notes. If
reuse rate is effectively zero, either (a) query topics are too diverse for within-session
overlap, or (b) our retrieval is over-diversifying results, or (c) sessions are too short
for reuse to register. All three are diagnostic.

Algorithm (MVP — stdlib only):
  1. Load logs/retrieval_log.jsonl (rows with ts + query + results).
  2. Segment into sessions via temporal gap (default 60 min breaks a session).
  3. For each session:
       - Collect all note slugs retrieved.
       - Count multi-retrievals (same slug appeared in N>1 results).
       - Compute reuse_rate = sum(retrievals beyond first) / total retrievals.
  4. Emit per-session + aggregate row to logs/retrieval_reuse.jsonl.

Output row format:
  {ts, session_count, total_retrievals, total_unique_slugs, global_reuse_rate,
   session_stats: [{start_ts, end_ts, query_count, retrieval_count, unique_slugs,
                    reuse_rate, most_reused_slug, most_reused_count}]}

CLI:
  python3 scripts/retrieval_reuse_tracker.py                   # run + print + write jsonl
  python3 scripts/retrieval_reuse_tracker.py --gap-min 30      # custom session-break gap
  python3 scripts/retrieval_reuse_tracker.py --report          # last row
  python3 scripts/retrieval_reuse_tracker.py --history 10      # last N rows

Caveat: upstream retrieval_log.jsonl is populated as vault_search.py runs. If the log
is empty or sparse, reuse-rate computation is not meaningful. Will accumulate data over
time (producer-orphan-free by design — this is the consumer of an existing writer).

Reference: cycle-16 Brutus Deepdive #4 vault note:
  research-consciousness/cognitive-workspace-active-memory-deepdive.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
IN = LOGS / "retrieval_log.jsonl"
OUT = LOGS / "retrieval_reuse.jsonl"


def load_retrievals() -> list[dict]:
    """Load retrieval_log.jsonl rows with parsed timestamps. Rows with bad ts dropped."""
    if not IN.exists():
        return []
    rows = []
    for ln in IN.read_text(errors="replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            row = json.loads(ln)
        except json.JSONDecodeError:
            continue
        ts_raw = row.get("ts")
        if not ts_raw:
            continue
        try:
            row["_ts"] = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        rows.append(row)
    rows.sort(key=lambda r: r["_ts"])
    return rows


def segment_sessions(rows: list[dict], gap_min: float) -> list[list[dict]]:
    """Break rows into sessions on temporal gaps > gap_min."""
    if not rows:
        return []
    sessions = [[rows[0]]]
    gap = timedelta(minutes=gap_min)
    for row in rows[1:]:
        prev_ts = sessions[-1][-1]["_ts"]
        if row["_ts"] - prev_ts > gap:
            sessions.append([row])
        else:
            sessions[-1].append(row)
    return sessions


def analyze_session(session: list[dict]) -> dict:
    """Compute reuse-rate + stats for one session."""
    query_count = len(session)
    all_slugs: list[str] = []
    for row in session:
        for slug in row.get("results", []):
            if slug:
                all_slugs.append(slug)

    retrieval_count = len(all_slugs)
    slug_counter = Counter(all_slugs)
    unique_slugs = len(slug_counter)

    # reuse = retrievals beyond first-hit for each slug
    reuses = sum(max(0, c - 1) for c in slug_counter.values())
    reuse_rate = (reuses / retrieval_count) if retrieval_count > 0 else 0.0

    top = slug_counter.most_common(1)
    most_reused_slug, most_reused_count = (top[0] if top else ("", 0))

    return {
        "start_ts": session[0]["_ts"].isoformat(),
        "end_ts": session[-1]["_ts"].isoformat(),
        "query_count": query_count,
        "retrieval_count": retrieval_count,
        "unique_slugs": unique_slugs,
        "reuse_rate": round(reuse_rate, 4),
        "most_reused_slug": most_reused_slug,
        "most_reused_count": most_reused_count,
    }


def aggregate(sessions: list[list[dict]]) -> dict:
    """Global + per-session aggregate."""
    if not sessions:
        return {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session_count": 0,
            "total_retrievals": 0,
            "total_unique_slugs": 0,
            "global_reuse_rate": 0.0,
            "session_stats": [],
            "note": "retrieval_log.jsonl empty or unparseable — no reuse signal",
        }

    session_stats = [analyze_session(s) for s in sessions]

    # Global reuse across all sessions (not average of per-session rates)
    all_slugs: list[str] = []
    for s in sessions:
        for row in s:
            all_slugs.extend(row.get("results", []))
    total_retrievals = len(all_slugs)
    slug_counter = Counter(all_slugs)
    total_unique = len(slug_counter)
    reuses = sum(max(0, c - 1) for c in slug_counter.values())
    global_rate = (reuses / total_retrievals) if total_retrievals > 0 else 0.0

    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_count": len(sessions),
        "total_retrievals": total_retrievals,
        "total_unique_slugs": total_unique,
        "global_reuse_rate": round(global_rate, 4),
        "session_stats": session_stats,
    }


def write_row(row: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(row) + "\n")


def render(row: dict) -> str:
    if row.get("session_count", 0) == 0:
        return f"=== Retrieval Reuse — {row['ts']} ===\n  {row.get('note', '(no data)')}"
    lines = [
        f"=== Retrieval Reuse — {row['ts']} ===",
        f"  Sessions:          {row['session_count']}",
        f"  Total retrievals:  {row['total_retrievals']}",
        f"  Unique slugs:      {row['total_unique_slugs']}",
        f"  Global reuse rate: {row['global_reuse_rate']:.1%}",
        "",
        "  Recent sessions (last 5):",
    ]
    for s in row.get("session_stats", [])[-5:]:
        lines.append(
            f"    [{s['query_count']:>3}q -> {s['retrieval_count']:>3}r, "
            f"{s['unique_slugs']:>3} uniq, reuse {s['reuse_rate']:.1%}]  "
            f"{s['start_ts'][:16]}  top: {s['most_reused_slug'][:30]}"
        )
    return "\n".join(lines)


def read_history(n: int = 0) -> list[dict]:
    if not OUT.exists():
        return []
    lines = OUT.read_text(errors="replace").splitlines()
    rows = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    if n > 0:
        rows = rows[-n:]
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap-min", type=float, default=60.0,
                    help="Session break gap in minutes. Default: 60.")
    ap.add_argument("--report", action="store_true", help="Print last row without writing")
    ap.add_argument("--history", type=int, default=0, help="Print last N rows")
    args = ap.parse_args()

    if args.report:
        rows = read_history(1)
        if rows:
            print(render(rows[-1]))
        else:
            print("No retrieval-reuse measurements on record.")
        return 0

    if args.history:
        for r in read_history(args.history):
            print(render(r))
            print()
        return 0

    retrievals = load_retrievals()
    sessions = segment_sessions(retrievals, gap_min=args.gap_min)
    row = aggregate(sessions)
    write_row(row)
    print(render(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
