#!/usr/bin/env python3
"""
Scaffold Integrity Check — verify critical files haven't been corrupted or deleted.

Hashes MEMORY.md + CLAUDE.md + key rules on session end.
Verifies hashes on session start. Alerts Discord if mismatch.

From Animesis "Memory Inalienability" axiom: memory can't be taken away.
Our version: scaffold corruption is detectable.

Usage:
    python3 scripts/scaffold_integrity.py save       # save current hashes (session end)
    python3 scripts/scaffold_integrity.py verify      # verify against saved (session start)
    python3 scripts/scaffold_integrity.py status      # show current state
"""

import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HASH_FILE = REPO / "data" / "scaffold_hashes.json"

# Critical scaffold files — corruption of these = identity damage
CRITICAL_FILES = [
    Path.home() / ".claude" / "projects" / "-Users-claude-Flex-Trading" / "memory" / "MEMORY.md",
    REPO / "CLAUDE.md",
    REPO / ".claude" / "rules" / "workflow.md",
    REPO / ".claude" / "rules" / "qa-checklist.md",
    REPO / ".claude" / "agents" / "guardrails.md",
    REPO / ".claude" / "agents" / "brutus.md",
    REPO / ".claude" / "agents" / "metacognizer.md",
]


def hash_file(path):
    """SHA-256 hash of a file's contents."""
    try:
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
    except FileNotFoundError:
        return "MISSING"
    except Exception as e:
        return f"ERROR:{e}"


def save_hashes():
    """Save current hashes of all critical files."""
    hashes = {}
    for f in CRITICAL_FILES:
        name = f.name
        h = hash_file(f)
        size = f.stat().st_size if f.exists() else 0
        hashes[name] = {"hash": h, "size": size, "path": str(f)}

    hashes["_meta"] = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(CRITICAL_FILES),
    }

    HASH_FILE.parent.mkdir(exist_ok=True)
    HASH_FILE.write_text(json.dumps(hashes, indent=2))
    print(f"  Saved {len(CRITICAL_FILES)} file hashes → {HASH_FILE}")
    for name, data in hashes.items():
        if name != "_meta":
            print(f"    {name}: {data['hash']} ({data['size']} bytes)")


def verify_hashes():
    """Verify current files against saved hashes."""
    if not HASH_FILE.exists():
        print("  No saved hashes found. Run 'save' first.")
        return True  # no baseline = can't verify

    saved = json.loads(HASH_FILE.read_text())
    meta = saved.get("_meta", {})
    print(f"  Verifying against hashes saved at {meta.get('saved_at', '?')}")

    issues = []
    for f in CRITICAL_FILES:
        name = f.name
        if name not in saved:
            continue
        current_hash = hash_file(f)
        saved_hash = saved[name]["hash"]
        saved_size = saved[name]["size"]
        current_size = f.stat().st_size if f.exists() else 0

        if current_hash == "MISSING":
            issues.append(f"  CRITICAL: {name} DELETED")
        elif current_hash != saved_hash:
            size_delta = current_size - saved_size
            # Changed is normal (we edit these). Flag only if SHRUNK significantly (possible corruption)
            if size_delta < -500:
                issues.append(f"  WARNING: {name} shrunk by {abs(size_delta)} bytes (possible corruption)")
            else:
                print(f"  OK (updated): {name} ({size_delta:+d} bytes)")
        else:
            print(f"  OK: {name}")

    if issues:
        print("\n  INTEGRITY ISSUES:")
        for issue in issues:
            print(f"    {issue}")
        alert_discord(issues)
        return False
    else:
        print("\n  All scaffold files intact.")
        return True


def alert_discord(issues):
    """Alert Discord if integrity issues found."""
    env_file = REPO / ".env"
    webhook = ""
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "DISCORD_WEBHOOK_DATA" in line and "=" in line and not line.startswith("#"):
                webhook = line.split("=", 1)[1].strip()
    if not webhook:
        return
    try:
        msg = "**SCAFFOLD INTEGRITY ALERT**\n" + "\n".join(issues)
        data = json.dumps({"content": msg[:1900]}).encode()
        req = urllib.request.Request(webhook, data=data,
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "ScaffoldIntegrity/1.0"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def status():
    """Show current state."""
    if HASH_FILE.exists():
        saved = json.loads(HASH_FILE.read_text())
        meta = saved.get("_meta", {})
        print(f"  Last saved: {meta.get('saved_at', '?')}")
        for name, data in saved.items():
            if name != "_meta":
                current = hash_file(Path(data["path"]))
                match = "✓" if current == data["hash"] else "✗ CHANGED"
                print(f"    {name}: {match}")
    else:
        print("  No saved hashes. Run 'save' to create baseline.")


def main():
    if len(sys.argv) < 2:
        print("Usage: scaffold_integrity.py [save|verify|status]")
        return

    cmd = sys.argv[1]
    if cmd == "save":
        save_hashes()
    elif cmd == "verify":
        verify_hashes()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
