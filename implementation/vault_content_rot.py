#!/usr/bin/env python3
"""
Vault Content Rot Scanner — verify concrete claims still match reality.

The scaffold checks structural integrity (links, summaries, probe scores) but
NOT content integrity. A note with healthy wikilinks can reference scripts/X.py
that no longer exists or commands that no longer run. This scanner walks every
vault note, extracts concrete references (file paths, script names, log files),
and verifies each one resolves on the current filesystem.

References checked:
- `scripts/<name>.py` — script existence
- `.claude/(rules|agents|hooks|skills)/<name>.<ext>` — config existence
- `logs/<name>.(jsonl|log)` — log file existence (informational only — logs may
  be intentionally absent if a feature was retired)
- `tasks/<name>.md` — task file existence

Note: vault cross-references (`[[wikilinks]]`) are out of scope — `vault_search.py
--graph-health` already reports danglers. This tool catches rot in the other
direction (notes referencing non-vault filesystem paths).

Output: per-note rot count + global summary, optionally written to JSONL.
A "rotted" note is not necessarily wrong — sometimes the reference is historical
and intentional. The scanner surfaces; humans triage.

Usage:
    python3 scripts/vault_content_rot.py                  # human-readable summary
    python3 scripts/vault_content_rot.py --jsonl          # machine output to logs/
    python3 scripts/vault_content_rot.py --top 20         # top 20 most-rotted notes
    python3 scripts/vault_content_rot.py --note <slug>    # diagnose one note
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VAULT = REPO / "knowledge" / "notes"
LOG_FILE = REPO / "logs" / "vault_content_rot.jsonl"

# Reference patterns — match in note bodies, frontmatter, and code blocks.
# Each tuple: (regex, category, repo-relative-resolver)
REFERENCE_PATTERNS = [
    (re.compile(r"\bscripts/([a-z0-9_]+)\.py\b"), "script", lambda m: REPO / "scripts" / f"{m.group(1)}.py"),
    (re.compile(r"\b\.claude/(rules|agents|hooks|skills)/([a-zA-Z0-9_-]+)\.(md|sh|json)\b"),
     "config", lambda m: REPO / ".claude" / m.group(1) / f"{m.group(2)}.{m.group(3)}"),
    (re.compile(r"\blogs/([a-z0-9_]+)\.(jsonl|log)\b"), "log", lambda m: REPO / "logs" / f"{m.group(1)}.{m.group(2)}"),
    (re.compile(r"\btasks/([a-z0-9_-]+)\.md\b"), "task", lambda m: REPO / "tasks" / f"{m.group(1)}.md"),
]


def scan_note(path: Path) -> list[dict]:
    """Return list of broken reference records for one note."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    seen: set[tuple[str, str]] = set()
    broken: list[dict] = []
    for pattern, category, resolver in REFERENCE_PATTERNS:
        for m in pattern.finditer(text):
            ref = m.group(0)
            target = resolver(m)
            key = (category, ref)
            if key in seen:
                continue
            seen.add(key)
            if not target.exists():
                broken.append({"category": category, "ref": ref, "target": str(target.relative_to(REPO))})
    return broken


def scan_all() -> list[dict]:
    """Walk vault, return per-note rot records (only notes with rot)."""
    out = []
    for md in sorted(VAULT.rglob("*.md")):
        broken = scan_note(md)
        if broken:
            out.append({
                "note": str(md.relative_to(REPO)),
                "rot_count": len(broken),
                "broken_refs": broken,
            })
    return out


def write_jsonl(records: list[dict]) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a") as f:
        for r in records:
            f.write(json.dumps({"ts": ts, **r}) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jsonl", action="store_true", help="Append findings to logs/vault_content_rot.jsonl")
    ap.add_argument("--top", type=int, default=15, help="Show top N most-rotted notes (default 15)")
    ap.add_argument("--note", help="Diagnose a single note by slug or path")
    args = ap.parse_args()

    if args.note:
        candidates = list(VAULT.rglob(f"*{args.note}*.md"))
        if not candidates:
            print(f"no note matching '{args.note}'", file=sys.stderr)
            return 2
        for path in candidates[:5]:
            broken = scan_note(path)
            print(f"\n{path.relative_to(REPO)}")
            if not broken:
                print("  no rot detected")
                continue
            for b in broken:
                print(f"  [{b['category']:6s}] {b['ref']}  →  missing: {b['target']}")
        return 0

    findings = scan_all()
    total_notes = len(list(VAULT.rglob("*.md")))
    rotted_notes = len(findings)
    total_refs = sum(f["rot_count"] for f in findings)

    by_cat: dict[str, int] = {}
    for f in findings:
        for b in f["broken_refs"]:
            by_cat[b["category"]] = by_cat.get(b["category"], 0) + 1

    print(f"\nVault Content Rot — scanned {total_notes} notes")
    print(f"  notes with rot: {rotted_notes} ({100*rotted_notes/max(total_notes,1):.1f}%)")
    print(f"  total broken refs: {total_refs}")
    if by_cat:
        print(f"  by category: {dict(sorted(by_cat.items(), key=lambda kv: -kv[1]))}")
    print()

    findings.sort(key=lambda f: -f["rot_count"])
    print(f"Top {min(args.top, len(findings))} most-rotted notes:")
    for f in findings[:args.top]:
        print(f"  [{f['rot_count']:2d}] {f['note']}")
        for b in f["broken_refs"][:3]:
            print(f"         {b['category']}: {b['ref']}")
        if f["rot_count"] > 3:
            print(f"         (+{f['rot_count']-3} more)")

    if args.jsonl:
        write_jsonl(findings)
        print(f"\nAppended {len(findings)} records to {LOG_FILE.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
