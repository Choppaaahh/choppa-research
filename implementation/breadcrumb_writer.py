#!/usr/bin/env python3
"""
Breadcrumb Writer — logs breadcrumbs with auto-classification via local Qwen.

Replaces manual breadcrumb logging. Auto-classifies type via local model,
falls back to manual type if local model is unreachable.

Usage:
    python3 scripts/breadcrumb_writer.py "User deployed Config B7"
    python3 scripts/breadcrumb_writer.py "R14 proved +18.5% synthesis" --type finding
    python3 scripts/breadcrumb_writer.py --batch  # classify untyped breadcrumbs
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
BREADCRUMB_FILE = BASE / "logs" / "session_breadcrumbs.jsonl"
LOCAL_SCRIPT = BASE / "scripts" / "local_inference.py"

VALID_TYPES = {"decision", "finding", "insight", "action", "dialogue", "gap"}


def auto_classify(text):
    """Classify breadcrumb type via local Qwen model."""
    try:
        result = subprocess.run(
            ["python3", str(LOCAL_SCRIPT), "--classify", text],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            raw = result.stdout.strip().lower().split()[0] if result.stdout.strip() else ""
            # Map close matches
            mapping = {
                "deployment": "action",
                "deploy": "action",
                "built": "action",
                "shipped": "action",
                "discovered": "finding",
                "found": "finding",
                "connected": "insight",
                "reframed": "insight",
                "decided": "decision",
                "chose": "decision",
            }
            classified = mapping.get(raw, raw)
            if classified in VALID_TYPES:
                return classified
    except Exception:
        pass
    return "action"  # safe default


def write_breadcrumb(content, bc_type=None):
    """Write a breadcrumb to the log file."""
    if not bc_type:
        bc_type = auto_classify(content)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": bc_type,
        "content": content,
    }

    with open(BREADCRUMB_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[{bc_type}] {content[:80]}")
    return entry


def batch_classify():
    """Find untyped or mistyped breadcrumbs and reclassify."""
    if not BREADCRUMB_FILE.exists():
        print("No breadcrumbs file found.")
        return

    lines = BREADCRUMB_FILE.read_text().splitlines()
    updated = 0
    new_lines = []

    for line in lines:
        if not line.strip():
            new_lines.append(line)
            continue
        try:
            bc = json.loads(line)
            if bc.get("type") not in VALID_TYPES:
                new_type = auto_classify(bc.get("content", ""))
                bc["type"] = new_type
                updated += 1
                print(f"  Reclassified: {bc['content'][:50]} → {new_type}")
            new_lines.append(json.dumps(bc))
        except:
            new_lines.append(line)

    if updated > 0:
        BREADCRUMB_FILE.write_text("\n".join(new_lines) + "\n")
        print(f"\nUpdated {updated} breadcrumbs.")
    else:
        print("All breadcrumbs properly typed.")


def main():
    parser = argparse.ArgumentParser(description="Breadcrumb Writer")
    parser.add_argument("content", nargs="?", help="Breadcrumb content")
    parser.add_argument("--type", type=str, choices=list(VALID_TYPES), help="Override auto-classification")
    parser.add_argument("--batch", action="store_true", help="Batch reclassify untyped breadcrumbs")
    args = parser.parse_args()

    if args.batch:
        batch_classify()
    elif args.content:
        write_breadcrumb(args.content, args.type)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
