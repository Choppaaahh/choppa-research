#!/usr/bin/env python3
"""
Conflict Detector — finds stale, contradictory, or superseded entries in MEMORY.md.
Phase 2 of entropy-triggered consolidation (SleepGate steal).

Uses local Qwen for semantic comparison (0 cost).
Falls back to string similarity if Qwen unavailable.
Logs conflicts to logs/conflict_detections.jsonl.

Usage:
    python3 scripts/conflict_detector.py              # scan MEMORY.md
    python3 scripts/conflict_detector.py --fix         # scan + auto-merge SUPERSEDES
    python3 scripts/conflict_detector.py --section "Active Config"  # scan one section
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional

MEMORY_PATH = Path.home() / ".claude/projects/-Users-claude-Flex-Trading/memory/MEMORY.md"
LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "conflict_detections.jsonl"
TENSIONS_DIR = Path(__file__).resolve().parent.parent / "knowledge" / "notes" / "cc-operational" / "tensions"

QWEN_TIMEOUT = 30
SIMILARITY_THRESHOLD = 0.55  # fallback: flag pairs above this similarity


def parse_memory_sections(path: Path) -> Dict[str, List[str]]:
    """Parse MEMORY.md into {section_name: [entries]}."""
    sections: Dict[str, List[str]] = {}
    current_section = None

    if not path.exists():
        return sections

    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
            # Strip trailing date/parens from section headers like "Active Config (04/05 2am UTC)"
            if "(" in current_section:
                current_section = current_section[:current_section.index("(")].strip()
            sections[current_section] = []
        elif current_section and stripped.startswith("- "):
            sections[current_section].append(stripped[2:])

    return sections


def query_qwen(entry_a: str, entry_b: str) -> Optional[str]:
    """Ask Qwen to classify relationship between two entries. Returns classification or None on failure."""
    prompt = (
        "Compare these two MEMORY.md entries. Are they: "
        "SUPERSEDES (second replaces first), CONTRADICTS (they conflict), "
        "EXTENDS (second adds to first), or UNRELATED? Reply with one word.\n\n"
        f"Entry 1: {entry_a}\n\nEntry 2: {entry_b}"
    )
    try:
        result = subprocess.run(
            ["python3", os.path.join(os.path.dirname(__file__), "local_inference.py"), prompt, "--max-tokens", "10"],
            capture_output=True, text=True, timeout=QWEN_TIMEOUT,
            cwd=Path(__file__).resolve().parent.parent,
        )
        if result.returncode != 0:
            return None
        response = result.stdout.strip().upper()
        # Extract the classification word from response
        for cls in ("SUPERSEDES", "CONTRADICTS", "EXTENDS", "UNRELATED"):
            if cls in response:
                return cls
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def fallback_similarity(entry_a: str, entry_b: str) -> str:
    """String similarity fallback when Qwen is unavailable."""
    # Strip markdown bold markers for cleaner comparison
    clean_a = entry_a.replace("**", "").lower()
    clean_b = entry_b.replace("**", "").lower()
    ratio = SequenceMatcher(None, clean_a, clean_b).ratio()
    if ratio > SIMILARITY_THRESHOLD:
        return "POSSIBLE_OVERLAP"
    return "UNRELATED"


def compare_entries(entries: list[str], use_qwen: bool = True) -> List[dict]:
    """Compare all entry pairs within a section. Returns list of conflict records."""
    conflicts = []
    n = len(entries)
    for i in range(n):
        for j in range(i + 1, n):
            classification = None
            if use_qwen:
                classification = query_qwen(entries[i], entries[j])
            if classification is None:
                classification = fallback_similarity(entries[i], entries[j])

            if classification in ("SUPERSEDES", "CONTRADICTS", "EXTENDS", "POSSIBLE_OVERLAP"):
                conflicts.append({
                    "entry_a": entries[i][:120],
                    "entry_b": entries[j][:120],
                    "classification": classification,
                    "idx_a": i,
                    "idx_b": j,
                })
    return conflicts


def log_conflicts(section: str, conflicts: List[dict]) -> None:
    """Append conflict detections to JSONL log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        for c in conflicts:
            record = {"ts": ts, "section": section, **c}
            f.write(json.dumps(record) + "\n")


def log_tension(section: str, conflict: dict) -> None:
    """Write CONTRADICTS conflicts to tensions directory for human review."""
    TENSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = TENSIONS_DIR / f"tension-{ts}-{section.lower().replace(' ', '-')[:20]}.md"
    content = (
        f"---\n"
        f"type: tension\n"
        f"section: {section}\n"
        f"detected: {datetime.now(timezone.utc).isoformat()}\n"
        f"status: unresolved\n"
        f"---\n\n"
        f"# Tension in {section}\n\n"
        f"**Entry A:** {conflict['entry_a']}\n\n"
        f"**Entry B:** {conflict['entry_b']}\n\n"
        f"**Classification:** {conflict['classification']}\n\n"
        f"## Resolution\n\n"
        f"_Pending human review._\n"
    )
    filename.write_text(content)
    print(f"  Tension logged: {filename.name}")


def scan(target_section: Optional[str] = None, fix: bool = False) -> dict:
    """Main scan. Returns summary dict."""
    sections = parse_memory_sections(MEMORY_PATH)
    if not sections:
        print(f"No sections found in {MEMORY_PATH}")
        return {"sections": 0, "conflicts": 0}

    total_conflicts = 0
    summary: Dict[str, List[dict]] = {}

    # Check if Qwen is reachable with a quick test
    use_qwen = query_qwen("test entry one", "test entry two") is not None
    if not use_qwen:
        print("Qwen unavailable — falling back to string similarity")

    for name, entries in sections.items():
        if target_section and name != target_section:
            continue
        if len(entries) < 2:
            continue

        print(f"\n--- {name} ({len(entries)} entries, {len(entries)*(len(entries)-1)//2} pairs) ---")
        conflicts = compare_entries(entries, use_qwen=use_qwen)

        if conflicts:
            summary[name] = conflicts
            total_conflicts += len(conflicts)
            for c in conflicts:
                tag = c["classification"]
                print(f"  [{tag}] #{c['idx_a']} vs #{c['idx_b']}")
                print(f"    A: {c['entry_a'][:80]}...")
                print(f"    B: {c['entry_b'][:80]}...")

                if tag == "CONTRADICTS":
                    log_tension(name, c)

            log_conflicts(name, conflicts)
        else:
            print("  No conflicts detected.")

    print(f"\n=== Summary: {total_conflicts} conflicts across {len(summary)} sections ===")

    if fix and summary:
        print("\n--fix: SUPERSEDES entries would be merged (not yet implemented — logs only).")

    return {"sections": len(sections), "conflicts": total_conflicts, "details": summary}


def main():
    parser = argparse.ArgumentParser(description="Detect conflicts in MEMORY.md entries")
    parser.add_argument("--fix", action="store_true", help="Auto-merge SUPERSEDES entries (future)")
    parser.add_argument("--section", type=str, default=None, help="Scan only this section")
    args = parser.parse_args()

    if not MEMORY_PATH.exists():
        print(f"MEMORY.md not found at {MEMORY_PATH}")
        sys.exit(1)

    scan(target_section=args.section, fix=args.fix)


if __name__ == "__main__":
    main()
