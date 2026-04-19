#!/usr/bin/env python3
"""
query_shape_telemetry.py — rolling-window instrument for vault_search query-shape drift.

Query-shape drift is invisible to latency telemetry. The vault_search may remain fast
while query shape shifts from KEYWORD → NARRATIVE-PROSE, and the underlying retrieval
quality silently degrades (per retrieval-hit-distribution data: narrative-prose queries
have 2-3x flatter top-score distributions than keyword queries). Latency telemetry shows
"retrieval was fast." Shape telemetry shows "retrieval was fast but pointed at a
distribution the ranker discriminates poorly on."

This script reads the last N queries issued against the vault (from breadcrumbs and
probe logs), classifies each by shape using the same classifier as
retrieval_hit_distribution.py (to ensure contract parity per QA #16), and emits a row
to logs/query_shape.jsonl with the shape distribution, avg query length, and stop-word
rate over the window.

Outputs:
    logs/query_shape.jsonl — one row per invocation with:
        ts, window_size, shape_counts {KEYWORD/SHORT-PROSE/NARRATIVE-PROSE/UNKNOWN},
        shape_percentages, avg_tokens, median_tokens, avg_significant_tokens,
        stopword_rate, trend (vs last row): flag if narrative-prose % shifted >10pp

Rolling window default = 100 queries. Adjust via --window.

Usage:
    python3 query_shape_telemetry.py                  # default N=100
    python3 query_shape_telemetry.py --window 200     # larger window
    python3 query_shape_telemetry.py --report         # print latest row
    python3 query_shape_telemetry.py --history 10     # last 10 rows

Source: addresses query-shape drift meta-pattern surfaced in cycle-14 retrieval-fix
sprint (P6 BM25+IDF landed, P8 query-shape classification added, but rolling
telemetry on shape distribution was missing — this closes that gap).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
OUT = LOGS / "query_shape.jsonl"

# Source the shape classifier from retrieval_hit_distribution.py to avoid divergence
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from retrieval_hit_distribution import (
        classify_query_shape,
        _significant_tokens,
        _raw_tokens,
        load_breadcrumb_queries,
        load_probe_queries,
    )
except ImportError as e:
    print(f"ERROR: cannot import from retrieval_hit_distribution.py — {e}", file=sys.stderr)
    print("This script shares the classifier to maintain QA checklist #16 writer/reader contract.", file=sys.stderr)
    sys.exit(1)


def load_queries(window: int) -> list[str]:
    """Load up to `window` recent queries from breadcrumbs + probe."""
    queries: list[str] = []
    try:
        queries.extend(load_breadcrumb_queries(window))
    except Exception as e:
        print(f"  warn: load_breadcrumb_queries failed: {e}", file=sys.stderr)
    if len(queries) < window:
        try:
            queries.extend(load_probe_queries(window - len(queries)))
        except Exception as e:
            print(f"  warn: load_probe_queries failed: {e}", file=sys.stderr)
    return queries[:window]


def stopword_rate(query: str) -> float:
    """Ratio of stopwords in the query. Proxy for signal-to-noise."""
    raw = _raw_tokens(query)
    if not raw:
        return 0.0
    sig = _significant_tokens(query)
    return 1.0 - (len(sig) / len(raw))


def analyze_window(queries: list[str]) -> dict:
    """Compute shape distribution + query-length stats over the window."""
    if not queries:
        return {
            "window_size": 0,
            "shape_counts": {},
            "shape_percentages": {},
            "avg_tokens": 0,
            "median_tokens": 0,
            "avg_significant_tokens": 0,
            "stopword_rate": 0.0,
        }

    shapes: dict[str, int] = {"KEYWORD": 0, "SHORT-PROSE": 0, "NARRATIVE-PROSE": 0, "UNKNOWN": 0}
    token_counts: list[int] = []
    sig_token_counts: list[int] = []
    sw_rates: list[float] = []

    for q in queries:
        shape = classify_query_shape(q)
        if shape in shapes:
            shapes[shape] += 1
        else:
            shapes["UNKNOWN"] += 1
        raw = _raw_tokens(q)
        sig = _significant_tokens(q)
        token_counts.append(len(raw))
        sig_token_counts.append(len(sig))
        sw_rates.append(stopword_rate(q))

    total = len(queries)
    percentages = {k: round(100.0 * v / total, 1) for k, v in shapes.items()}

    return {
        "window_size": total,
        "shape_counts": shapes,
        "shape_percentages": percentages,
        "avg_tokens": round(sum(token_counts) / total, 1),
        "median_tokens": median(token_counts),
        "avg_significant_tokens": round(sum(sig_token_counts) / total, 1),
        "stopword_rate": round(sum(sw_rates) / total, 3),
    }


def detect_drift(current: dict, previous: dict | None) -> dict:
    """Flag if narrative-prose % shifted >10pp since last row."""
    if not previous:
        return {"trend": "FIRST_ROW", "narrative_shift_pp": 0.0}
    cur_pct = current.get("shape_percentages", {}).get("NARRATIVE-PROSE", 0.0)
    prev_pct = previous.get("shape_percentages", {}).get("NARRATIVE-PROSE", 0.0)
    shift = cur_pct - prev_pct
    if shift > 10.0:
        trend = "NARRATIVE_DRIFT_UP"
    elif shift < -10.0:
        trend = "NARRATIVE_DRIFT_DOWN"
    else:
        trend = "STABLE"
    return {"trend": trend, "narrative_shift_pp": round(shift, 1)}


def read_last_row() -> dict | None:
    if not OUT.exists():
        return None
    lines = OUT.read_text().splitlines()
    for ln in reversed(lines):
        ln = ln.strip()
        if not ln:
            continue
        try:
            return json.loads(ln)
        except json.JSONDecodeError:
            continue
    return None


def read_history(n: int) -> list[dict]:
    if not OUT.exists():
        return []
    lines = OUT.read_text().splitlines()
    rows = []
    for ln in lines[-n:]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return rows


def write_row(row: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(row) + "\n")


def render(row: dict) -> str:
    sp = row.get("shape_percentages", {})
    drift = row.get("trend", "FIRST_ROW")
    shift = row.get("narrative_shift_pp", 0.0)
    return (
        f"=== Query-Shape Telemetry — {row['ts']} ===\n"
        f"  Window:       {row['window_size']} queries\n"
        f"  KEYWORD:      {sp.get('KEYWORD', 0):>5}%\n"
        f"  SHORT-PROSE:  {sp.get('SHORT-PROSE', 0):>5}%\n"
        f"  NARRATIVE-PROSE: {sp.get('NARRATIVE-PROSE', 0):>5}%\n"
        f"  UNKNOWN:      {sp.get('UNKNOWN', 0):>5}%\n"
        f"  Avg tokens:   {row.get('avg_tokens', 0)} (median {row.get('median_tokens', 0)}, significant {row.get('avg_significant_tokens', 0)})\n"
        f"  Stopword rate: {row.get('stopword_rate', 0):.1%}\n"
        f"  Trend:        {drift} ({shift:+.1f}pp narrative)\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=100, help="Rolling window size (default 100)")
    ap.add_argument("--report", action="store_true", help="Print latest row without writing")
    ap.add_argument("--history", type=int, default=0, help="Print last N rows")
    args = ap.parse_args()

    if args.report:
        row = read_last_row()
        if row:
            print(render(row))
        else:
            print("No query-shape telemetry on record.")
        return 0

    if args.history:
        for r in read_history(args.history):
            print(render(r))
        return 0

    queries = load_queries(args.window)
    if not queries:
        print("  warn: no queries loaded from breadcrumbs or probe log — cannot build row", file=sys.stderr)
        return 1

    analysis = analyze_window(queries)
    previous = read_last_row()
    drift = detect_drift(analysis, previous)

    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **analysis,
        **drift,
    }
    write_row(row)
    print(render(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
