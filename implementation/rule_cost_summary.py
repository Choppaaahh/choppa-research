#!/usr/bin/env python3
"""
Rule Cost Summary — measure context-cost of rule/agent/CLAUDE.md files.

The autoimmune diagnosis: defenses became the primary source of operational
complexity. Cost framing missing. This is a starting-point estimate — true
cost would need agent-side instrumentation we don't have, but file size + load
frequency is a useful proxy.

Each scaffold-context file is loaded into the LLM's context every session.
Total bytes / ~4 chars-per-token gives a rough token estimate. Files >300
lines or >15KB are flagged as heavy contributors.

Output: per-file size + line count + est tokens, total session-cost estimate,
heavy-contributor flags.

Usage:
    python3 scripts/rule_cost_summary.py                   # human summary
    python3 scripts/rule_cost_summary.py --jsonl           # machine output
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGETS = [
    ("CLAUDE.md", REPO / "CLAUDE.md"),
    (".claude/rules", REPO / ".claude" / "rules"),
    (".claude/agents", REPO / ".claude" / "agents"),
]
OUT_LOG = REPO / "logs" / "rule_cost_summary.jsonl"
HEAVY_BYTES = 15_000
HEAVY_LINES = 300


def measure(path: Path) -> dict:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return {"path": str(path.relative_to(REPO)), "error": "unreadable"}
    bytes_n = len(text.encode("utf-8", errors="replace"))
    lines = text.count("\n") + 1
    return {
        "path": str(path.relative_to(REPO)),
        "bytes": bytes_n,
        "lines": lines,
        "est_tokens": bytes_n // 4,
        "heavy": bytes_n >= HEAVY_BYTES or lines >= HEAVY_LINES,
    }


def collect() -> list[dict]:
    out = []
    for label, p in TARGETS:
        if p.is_file():
            out.append(measure(p))
        elif p.is_dir():
            for f in sorted(p.glob("*.md")) + sorted(p.glob("*.sh")) + sorted(p.glob("*.json")):
                out.append(measure(f))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jsonl", action="store_true", help="Append to logs/rule_cost_summary.jsonl")
    args = ap.parse_args()

    rows = collect()
    if not rows:
        print("no scaffold-context files found", file=sys.stderr)
        return 2
    total_bytes = sum(r.get("bytes", 0) for r in rows)
    total_lines = sum(r.get("lines", 0) for r in rows)
    total_tokens = sum(r.get("est_tokens", 0) for r in rows)
    heavy = [r for r in rows if r.get("heavy")]

    print(f"\nRule Cost Summary — {len(rows)} files")
    print(f"  total bytes:      {total_bytes:>10,}")
    print(f"  total lines:      {total_lines:>10,}")
    print(f"  est. tokens:      {total_tokens:>10,}  (~{total_tokens/1000:.1f}k per session load)")
    print(f"  heavy files:      {len(heavy):>10}  (>15KB or >300 lines)\n")

    if heavy:
        print("HEAVY CONTRIBUTORS:")
        for r in sorted(heavy, key=lambda r: -r.get("bytes", 0)):
            print(f"  [{r['lines']:4d} lines, {r['bytes']:>6,} B, ~{r['est_tokens']:>5} tok]  {r['path']}")
        print()

    print("ALL FILES (sorted by size):")
    for r in sorted(rows, key=lambda r: -r.get("bytes", 0))[:25]:
        marker = " ←H" if r.get("heavy") else ""
        print(f"  [{r.get('lines', 0):4d}L  {r.get('bytes', 0):>6,}B]  {r['path']}{marker}")

    if args.jsonl:
        OUT_LOG.parent.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with open(OUT_LOG, "a") as f:
            f.write(json.dumps({
                "ts": ts, "total_bytes": total_bytes, "total_lines": total_lines,
                "est_tokens": total_tokens, "heavy_count": len(heavy), "files": rows,
            }) + "\n")
        print(f"\nAppended summary to {OUT_LOG.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
