#!/usr/bin/env python3
"""
Probe Diagnostics — classify FAIL probes as TOOLING vs CONTENT.

Reads logs/vault_probe_qa.jsonl, replays each FAIL/WEAK probe through
vault_search.py, and classifies *why* the probe failed:

  TOOLING — search subprocess errored, timed out, parse-failed, or returned
            zero results. Query was severely truncated mid-word. The probe
            pipeline is broken; fix the script, not the note.

  CONTENT — search returned results but top score < 0.5 (or score 0.5-0.7
            with low overlap). The vault genuinely lacks a good match.
            Fix the note (write or enrich), not the script.

Usage:
    python3 scripts/probe_diagnostics.py                       # diagnose latest probe row
    python3 scripts/probe_diagnostics.py --row -1              # latest (default)
    python3 scripts/probe_diagnostics.py --row -2              # prior run
    python3 scripts/probe_diagnostics.py --since 2026-04-19    # all probes since date
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROBE_LOG = REPO / "logs" / "vault_probe_qa.jsonl"
VAULT_SEARCH = REPO / "scripts" / "vault_search.py"

RESULT_LINE_RE = re.compile(r"^\s*\d+\.\s*\[(?P<score>[0-9.]+)\]\s*(?:\([^)]*\)\s*)?(?P<slug>\S.*?)\s*$")


def load_probe_rows() -> list[dict]:
    if not PROBE_LOG.exists():
        return []
    rows = []
    for line in PROBE_LOG.read_text(errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def replay_query(query: str, timeout: int = 15) -> dict:
    """Re-run vault_search and return diagnostic facts (no scoring opinion)."""
    diag = {"query": query, "stdout_lines": 0, "results": [], "error": None, "rc": None}
    try:
        proc = subprocess.run(
            ["python3", str(VAULT_SEARCH), query, "--top", "5"],
            capture_output=True, text=True, timeout=timeout, cwd=str(REPO),
        )
    except subprocess.TimeoutExpired:
        diag["error"] = "timeout"
        return diag
    except FileNotFoundError:
        diag["error"] = "vault_search-missing"
        return diag
    diag["rc"] = proc.returncode
    diag["stdout_lines"] = len(proc.stdout.splitlines())
    if proc.returncode != 0:
        diag["error"] = f"rc={proc.returncode}"
        diag["stderr_tail"] = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ""
        return diag
    in_results = False
    for line in proc.stdout.splitlines():
        if "RESULTS:" in line:
            in_results = True
            continue
        if not in_results:
            continue
        m = RESULT_LINE_RE.match(line)
        if m:
            diag["results"].append({"score": float(m.group("score")), "slug": m.group("slug").strip()})
    return diag


def classify(query: str, diag: dict) -> tuple[str, str]:
    """Return (class, reason) — TOOLING / CONTENT / UNCLASSIFIED."""
    if diag["error"]:
        return "TOOLING", f"vault_search {diag['error']}"
    if not diag["results"]:
        if diag["stdout_lines"] == 0:
            return "TOOLING", "vault_search returned empty stdout"
        return "TOOLING", "stdout had lines but no parseable result rows"
    top = diag["results"][0]
    # Severely truncated query (gap-text in jsonl is capped ~80 chars and often ends mid-word)
    if len(query) > 0 and not query[-1].isspace() and not query[-1].isalnum() and query[-1] not in ".!?\"'":
        return "TOOLING", f"query ends mid-token (truncated): '{query[-15:]!r}'"
    # Post-P6 BM25 distribution: typical top scores 5-14. P1 formal calibration pending.
    if top["score"] < 5.0:
        return "CONTENT", f"top score {top['score']:.2f} < 5.0 (vault lacks coverage)"
    if top["score"] < 7.0:
        return "CONTENT", f"top score {top['score']:.2f} (weak match: {top['slug']})"
    return "UNCLASSIFIED", f"top score {top['score']:.2f} ({top['slug']}) — probe scored FAIL despite decent vault hit, check probe overlap logic"


def diagnose_row(row: dict) -> list[dict]:
    """Replay every gap in the row and classify."""
    out = []
    for gap in row.get("gaps", []):
        diag = replay_query(gap)
        cls, reason = classify(gap, diag)
        out.append({
            "ts": row.get("ts"),
            "query": gap,
            "class": cls,
            "reason": reason,
            "top_score": diag["results"][0]["score"] if diag["results"] else None,
            "top_slug": diag["results"][0]["slug"] if diag["results"] else None,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--row", type=int, default=-1, help="Probe row index (default -1 = latest)")
    g.add_argument("--since", help="Diagnose all rows with ts >= YYYY-MM-DD")
    ap.add_argument("--json", action="store_true", help="Emit JSON (one record per line) instead of table")
    args = ap.parse_args()

    rows = load_probe_rows()
    if not rows:
        print("no probe log entries found", file=sys.stderr)
        return 2

    if args.since:
        targets = [r for r in rows if (r.get("ts") or "") >= args.since]
        if not targets:
            print(f"no probe rows with ts >= {args.since}", file=sys.stderr)
            return 2
    else:
        try:
            targets = [rows[args.row]]
        except IndexError:
            print(f"row {args.row} out of range (have {len(rows)})", file=sys.stderr)
            return 2

    findings = []
    for row in targets:
        findings.extend(diagnose_row(row))

    if not findings:
        print("no FAIL gaps in selected rows — nothing to diagnose")
        return 0

    if args.json:
        for f in findings:
            print(json.dumps(f))
        return 0

    tooling = sum(1 for f in findings if f["class"] == "TOOLING")
    content = sum(1 for f in findings if f["class"] == "CONTENT")
    other = len(findings) - tooling - content
    print(f"\nProbe diagnostics — {len(findings)} FAIL gap(s) across {len(targets)} run(s)")
    print(f"  TOOLING: {tooling}   CONTENT: {content}   UNCLASSIFIED: {other}\n")
    for f in findings:
        ts = (f["ts"] or "")[:16]
        print(f"  [{f['class']:12s}] {ts}  {f['query'][:60]}")
        print(f"               reason: {f['reason']}")
        if f["top_slug"]:
            print(f"               top:    [{f['top_score']:.2f}] {f['top_slug']}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
