#!/usr/bin/env python3
"""
Scaffold Entropy Monitor — measures information change rate across scaffold components.

Entropy score 0-1 reflects how actively the scaffold is changing.
High entropy (>0.7) = build-heavy session → trigger consolidation.
Low entropy (<0.2) = idle → skip scheduled consolidation.

Replaces fixed 4hr confidence decay schedule with adaptive triggering.
SleepGate steal (arXiv 2603.14517): entropy-triggered > fixed-schedule.

Usage:
    python3 scripts/scaffold_entropy.py              # print current entropy
    python3 scripts/scaffold_entropy.py --log        # log to scaffold_entropy.jsonl
    python3 scripts/scaffold_entropy.py --check      # check + recommend consolidation
    python3 scripts/scaffold_entropy.py --check --consolidate  # check + run if triggered
"""

import argparse
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOGS = BASE / "logs"
ENTROPY_LOG = LOGS / "scaffold_entropy.jsonl"
MEMORY_FILE = Path.home() / ".claude" / "projects" / "-Users-claude-Flex-Trading" / "memory" / "MEMORY.md"
BREADCRUMBS = LOGS / "session_breadcrumbs.jsonl"
CHAINS = LOGS / "reasoning_chains.jsonl"
VAULT = BASE / "knowledge" / "notes"
SCAFFOLD_CHANGES = LOGS / "scaffold_changes.jsonl"

# Consolidation thresholds
HIGH_ENTROPY = 0.7    # trigger consolidation
LOW_ENTROPY = 0.2     # skip consolidation
MIN_INTERVAL_S = 3600   # 1hr minimum between consolidations
MAX_INTERVAL_S = 28800  # 8hr maximum without consolidation


def count_recent_entries(filepath, window_minutes=30):
    """Count JSONL entries within the last N minutes."""
    if not filepath.exists():
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    count = 0
    try:
        for line in filepath.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                ts = entry.get("ts", "")
                if ts > cutoff:
                    count += 1
            except (json.JSONDecodeError, ValueError):
                continue
    except Exception:
        pass
    return count


def count_recent_vault_notes(window_minutes=30):
    """Count vault notes modified in the last N minutes."""
    if not VAULT.exists():
        return 0
    cutoff = time.time() - (window_minutes * 60)
    count = 0
    for f in VAULT.rglob("*.md"):
        try:
            if f.stat().st_mtime > cutoff:
                count += 1
        except OSError:
            continue
    return count


def memory_age_minutes():
    """How many minutes since MEMORY.md was last modified."""
    if not MEMORY_FILE.exists():
        return 9999
    return (time.time() - MEMORY_FILE.stat().st_mtime) / 60


def scaffold_changes_recent(window_minutes=30):
    """Count scaffold_changes.jsonl entries in window."""
    return count_recent_entries(SCAFFOLD_CHANGES, window_minutes)


def compute_entropy(window_minutes=30):
    """
    Compute scaffold entropy score 0-1.

    Components (each 0-1, averaged):
    1. Breadcrumb rate: entries in window / expected max (20)
    2. Chain rate: reasoning chains in window / expected max (5)
    3. Vault churn: notes modified in window / expected max (10)
    4. Memory freshness: inverse of MEMORY.md age (fresh = high)
    5. Scaffold changes: changes in window / expected max (5)
    """
    breadcrumbs = min(count_recent_entries(BREADCRUMBS, window_minutes) / 20.0, 1.0)
    chains = min(count_recent_entries(CHAINS, window_minutes) / 5.0, 1.0)
    vault = min(count_recent_vault_notes(window_minutes) / 10.0, 1.0)
    mem_age = memory_age_minutes()
    memory = max(0, 1.0 - (mem_age / (window_minutes * 2)))  # fresh = 1, stale = 0
    changes = min(scaffold_changes_recent(window_minutes) / 5.0, 1.0)

    components = {
        "breadcrumbs": round(breadcrumbs, 3),
        "chains": round(chains, 3),
        "vault_churn": round(vault, 3),
        "memory_freshness": round(memory, 3),
        "scaffold_changes": round(changes, 3),
    }

    # Weighted average — breadcrumbs and chains matter most
    weights = {
        "breadcrumbs": 0.3,
        "chains": 0.25,
        "vault_churn": 0.2,
        "memory_freshness": 0.15,
        "scaffold_changes": 0.1,
    }
    score = sum(components[k] * weights[k] for k in components)

    return round(score, 3), components


def should_consolidate():
    """
    Check if consolidation should trigger based on entropy history.

    Returns: (should_trigger: bool, reason: str)
    """
    score, components = compute_entropy()

    # Check last consolidation time
    last_consolidation = 0
    if ENTROPY_LOG.exists():
        try:
            for line in ENTROPY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("triggered"):
                        last_consolidation = max(last_consolidation,
                            datetime.fromisoformat(entry["ts"]).timestamp())
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        except Exception:
            pass

    elapsed = time.time() - last_consolidation if last_consolidation else MAX_INTERVAL_S + 1

    # Decision logic
    if elapsed < MIN_INTERVAL_S:
        return False, f"too_recent ({elapsed:.0f}s < {MIN_INTERVAL_S}s min)"

    if elapsed > MAX_INTERVAL_S:
        return True, f"max_interval ({elapsed:.0f}s > {MAX_INTERVAL_S}s max)"

    if score >= HIGH_ENTROPY:
        # Check consecutive high readings (need 2+)
        consecutive_high = 0
        if ENTROPY_LOG.exists():
            try:
                recent = ENTROPY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]
                for line in reversed(recent):
                    try:
                        entry = json.loads(line)
                        if entry.get("score", 0) >= HIGH_ENTROPY:
                            consecutive_high += 1
                        else:
                            break
                    except (json.JSONDecodeError, ValueError):
                        continue
            except Exception:
                pass
        if consecutive_high >= 1:  # current + 1 prior = 2 consecutive
            return True, f"high_entropy ({score:.3f} >= {HIGH_ENTROPY}, {consecutive_high + 1} consecutive)"

    if score <= LOW_ENTROPY:
        return False, f"low_entropy ({score:.3f} <= {LOW_ENTROPY}, skip)"

    return False, f"normal ({score:.3f})"


def log_entry(score, components, triggered, reason):
    """Append to scaffold_entropy.jsonl."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "components": components,
        "triggered": triggered,
        "reason": reason,
    }
    try:
        ENTROPY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ENTROPY_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Log error: {e}")


def consolidate_old_breadcrumbs(max_age_hours=4):
    """Consolidate breadcrumbs older than max_age_hours into summary entries.

    Returns count of consolidated breadcrumbs.
    """
    if not BREADCRUMBS.exists():
        return 0

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    old_entries = []
    recent_entries = []

    for line in BREADCRUMBS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            ts = entry.get("ts", "")
            if ts and ts < cutoff:
                old_entries.append(entry)
            else:
                recent_entries.append(entry)
        except (json.JSONDecodeError, ValueError):
            recent_entries.append({"_raw": line})

    if not old_entries:
        return 0

    # Group old entries by type
    by_type = {}
    for entry in old_entries:
        t = entry.get("type", "unknown")
        by_type.setdefault(t, []).append(entry.get("content", str(entry)))

    # Create summary breadcrumbs
    now = datetime.now(timezone.utc).isoformat()
    summaries = []
    for t, contents in by_type.items():
        themes = "; ".join(contents[:5])
        if len(contents) > 5:
            themes += f" (+{len(contents) - 5} more)"
        summaries.append({
            "ts": now,
            "type": "summary",
            "content": f"Consolidated {len(contents)} {t} breadcrumbs: {themes}",
        })

    # Archive old entries
    archive_dir = LOGS / "breadcrumbs_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / f"consolidated_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
    with open(archive_file, "w") as f:
        for entry in old_entries:
            f.write(json.dumps(entry) + "\n")

    # Rewrite breadcrumbs: summaries + recent
    with open(BREADCRUMBS, "w") as f:
        for s in summaries:
            f.write(json.dumps(s) + "\n")
        for entry in recent_entries:
            if "_raw" in entry:
                f.write(entry["_raw"] + "\n")
            else:
                f.write(json.dumps(entry) + "\n")

    return len(old_entries)


def post_consolidation_report(results):
    """Post consolidation results to Discord #cc channel."""
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
    webhook = os.environ.get("DISCORD_WEBHOOK_CC", "").strip()
    if not webhook:
        print("  [Discord] DISCORD_WEBHOOK_CC not set, skipping post")
        return

    lines = ["**Entropy Consolidation Report**"]
    for step_name, output in results:
        status = "FAILED" if "FAILED" in str(output) or "SKIPPED" in str(output) else "OK"
        lines.append(f"- {step_name}: {status} — {output[:150]}")

    payload = json.dumps({"content": "\n".join(lines)}).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("  [Discord] Posted consolidation report to #cc")
    except Exception as e:
        print(f"  [Discord] Post failed: {e}")


def run_consolidation():
    """Execute all consolidation steps. Returns list of (step_name, result_str)."""
    results = []
    scripts_dir = BASE / "scripts"

    # Step 1: Confidence decay
    decay_script = scripts_dir / "confidence_decay.py"
    if decay_script.exists():
        try:
            result = subprocess.run(
                ["python3", str(decay_script), "--adaptive", "--stale", "--sync-db"],
                capture_output=True, text=True, timeout=60,
                cwd=str(BASE),
            )
            out = (result.stdout.strip() or result.stderr.strip())[:200]
            results.append(("confidence_decay", out if result.returncode == 0 else f"FAILED (rc={result.returncode}): {out}"))
        except subprocess.TimeoutExpired:
            results.append(("confidence_decay", "FAILED (timeout 60s)"))
        except Exception as e:
            results.append(("confidence_decay", f"FAILED: {e}"))
    else:
        results.append(("confidence_decay", "SKIPPED — script not found"))

    # Step 2: Conflict detection
    conflict_script = scripts_dir / "conflict_detector.py"
    if conflict_script.exists():
        try:
            result = subprocess.run(
                ["python3", str(conflict_script)],
                capture_output=True, text=True, timeout=60,
                cwd=str(BASE),
            )
            out = (result.stdout.strip() or result.stderr.strip())[:200]
            results.append(("conflict_detector", out if result.returncode == 0 else f"FAILED (rc={result.returncode}): {out}"))
        except subprocess.TimeoutExpired:
            results.append(("conflict_detector", "FAILED (timeout 60s)"))
        except Exception as e:
            results.append(("conflict_detector", f"FAILED: {e}"))
    else:
        results.append(("conflict_detector", "SKIPPED — script not found"))

    # Step 3: Breadcrumb consolidation
    consolidated = consolidate_old_breadcrumbs()
    results.append(("breadcrumb_consolidation", f"{consolidated} breadcrumbs consolidated"))

    # Step 4: Post to Discord
    post_consolidation_report(results)

    return results


def main():
    parser = argparse.ArgumentParser(description="Scaffold entropy monitor")
    parser.add_argument("--log", action="store_true", help="Log entropy to JSONL")
    parser.add_argument("--check", action="store_true", help="Check and recommend consolidation")
    parser.add_argument("--consolidate", action="store_true", help="Run consolidation if triggered (requires --check)")
    parser.add_argument("--window", type=int, default=30, help="Window in minutes (default 30)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    score, components = compute_entropy(args.window)

    if args.check:
        triggered, reason = should_consolidate()
        if args.log:
            log_entry(score, components, triggered, reason)

        if args.json:
            output = {
                "score": score, "components": components,
                "should_consolidate": triggered, "reason": reason,
            }
            if triggered and args.consolidate:
                results = run_consolidation()
                log_entry(score, components, True, f"consolidated: {reason}")
                output["consolidation"] = {name: out for name, out in results}
            elif not triggered and args.consolidate:
                output["consolidation"] = "not_triggered"
            print(json.dumps(output))
        else:
            status = "CONSOLIDATE" if triggered else "HOLD"
            print(f"Entropy: {score:.3f} | {status} | {reason}")
            for k, v in components.items():
                bar = "#" * int(v * 20)
                print(f"  {k:20s}: {v:.3f} {bar}")

            # Show what would run
            if triggered:
                print("\n  Would run:")
                print("    1. confidence_decay.py --adaptive --stale --sync-db")
                print("    2. conflict_detector.py")
                print("    3. Breadcrumb consolidation (>4hr old)")
                print("    4. Discord #cc report")

            if triggered and args.consolidate:
                print("\n  Running consolidation...")
                results = run_consolidation()
                log_entry(score, components, True, f"consolidated: {reason}")
                for name, out in results:
                    print(f"    [{name}] {out}")
                print("  Consolidation complete.")
            elif not triggered and args.consolidate:
                print("\n  --consolidate passed but trigger condition not met. Skipping.")
    else:
        if args.log:
            log_entry(score, components, False, "monitor")
        if args.json:
            print(json.dumps({"score": score, "components": components}))
        else:
            print(f"Scaffold entropy: {score:.3f} (window={args.window}min)")
            for k, v in components.items():
                bar = "#" * int(v * 20)
                print(f"  {k:20s}: {v:.3f} {bar}")


if __name__ == "__main__":
    main()
