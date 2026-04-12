#!/usr/bin/env python3
"""
cron_health.py — Meta-cron that verifies all other crons ran on schedule.

Checks log file freshness, signal file freshness, and trader process liveness.
Outputs a summary table to stdout and writes alerts to signals/cron_health_alert.json.

Usage:
    python3 scripts/cron_health.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent          # ~/Flex/Trading
SIGNALS = BASE / "signals"
ALERT_FILE = SIGNALS / "cron_health_alert.json"

# ---------------------------------------------------------------------------
# Expected crons: log path (relative to BASE) and max acceptable age in minutes
# ---------------------------------------------------------------------------
EXPECTED_CRONS = {
    "overnight_report": {"log": "logs/overnight_report.log", "max_age_min": 150},
    "market_scanner":   {"log": "logs/scanner.log",          "max_age_min": 150},
    "compound_allocator": {"log": "logs/compound.log",       "max_age_min": 150},
    "bot5_scanner":     {"log": "../bot5-scanner/output/cron.log", "max_age_min": 1500},
    "param_sweep":      {"log": "logs/sweep.log",            "max_age_min": 1500},
}

# Signal files that should stay fresh when their producers are active
SIGNAL_CHECKS = {
    "allocation.json":      {"path": "signals/allocation.json",      "max_age_min": 150},
    "scanner_output.json":  {"path": "signals/scanner_output.json",  "max_age_min": 150},
}

PID_FILE = SIGNALS / "multi_trader_pids.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def file_age_minutes(filepath: Path) -> float:
    """Return file age in minutes, or -1 if the file does not exist."""
    if not filepath.exists():
        return -1.0
    mtime = filepath.stat().st_mtime
    return (time.time() - mtime) / 60.0


def fmt_age(minutes: float) -> str:
    """Human-readable age string."""
    if minutes < 0:
        return "N/A"
    if minutes < 1:
        return "<1m"
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f}h"
    days = hours / 24
    return f"{days:.1f}d"


def pid_alive(pid: int) -> bool:
    """Return True if the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_crons():
    """Check each expected cron log. Returns list of result dicts."""
    results = []
    for name, spec in EXPECTED_CRONS.items():
        log_path = (BASE / spec["log"]).resolve()
        age = file_age_minutes(log_path)
        max_age = spec["max_age_min"]

        if age < 0:
            status = "MISSING"
            ok = False
        elif age > max_age:
            status = "STALE"
            ok = False
        else:
            status = "OK"
            ok = True

        results.append({
            "name": name,
            "log": str(log_path),
            "status": status,
            "age_min": round(age, 1),
            "max_age_min": max_age,
            "ok": ok,
        })
    return results


def check_signals():
    """Check freshness of key signal files. Returns list of result dicts."""
    results = []
    for label, spec in SIGNAL_CHECKS.items():
        sig_path = (BASE / spec["path"]).resolve()
        age = file_age_minutes(sig_path)
        max_age = spec["max_age_min"]

        if age < 0:
            status = "MISSING"
            ok = False
        elif age > max_age:
            status = "STALE"
            ok = False
        else:
            status = "OK"
            ok = True

        results.append({
            "name": label,
            "path": str(sig_path),
            "status": status,
            "age_min": round(age, 1),
            "max_age_min": max_age,
            "ok": ok,
        })
    return results


def check_traders():
    """Verify trader PIDs from multi_trader_pids.json are alive. Returns list of result dicts."""
    results = []

    if not PID_FILE.exists():
        results.append({
            "name": "multi_trader_pids.json",
            "status": "MISSING",
            "detail": "PID file not found",
            "ok": False,
        })
        return results

    try:
        with open(PID_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        results.append({
            "name": "multi_trader_pids.json",
            "status": "ERROR",
            "detail": f"Failed to read: {e}",
            "ok": False,
        })
        return results

    # Check launcher PID
    launcher_pid = data.get("launcher_pid")
    if launcher_pid:
        alive = pid_alive(launcher_pid)
        results.append({
            "name": "launcher",
            "pid": launcher_pid,
            "status": "OK" if alive else "DEAD",
            "ok": alive,
        })

    # Check each trader
    traders = data.get("traders", {})
    for coin, info in traders.items():
        pid = info.get("pid")
        if pid:
            alive = pid_alive(pid)
            results.append({
                "name": f"trader_{coin}",
                "pid": pid,
                "status": "OK" if alive else "DEAD",
                "ok": alive,
            })

        rec_pid = info.get("recorder_pid")
        if rec_pid:
            alive = pid_alive(rec_pid)
            results.append({
                "name": f"recorder_{coin}",
                "pid": rec_pid,
                "status": "OK" if alive else "DEAD",
                "ok": alive,
            })

    # Check watchdog
    watchdog = data.get("watchdog", {})
    wd_pid = watchdog.get("pid")
    if wd_pid:
        alive = pid_alive(wd_pid)
        results.append({
            "name": "watchdog",
            "pid": wd_pid,
            "status": "OK" if alive else "DEAD",
            "ok": alive,
        })

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_table(cron_results, signal_results, trader_results):
    """Print a formatted summary table to stdout."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{'='*60}")
    print(f"  CRON HEALTH CHECK  —  {now_str}")
    print(f"{'='*60}\n")

    # Cron jobs
    print("  CRON JOBS")
    print(f"  {'Name':<22} {'Status':<10} {'Age':<10} {'Max':<10}")
    print(f"  {'-'*22} {'-'*10} {'-'*10} {'-'*10}")
    for r in cron_results:
        age_str = fmt_age(r["age_min"]) if r["age_min"] >= 0 else "---"
        max_str = fmt_age(r["max_age_min"])
        print(f"  {r['name']:<22} {r['status']:<10} {age_str:<10} {max_str:<10}")

    print()

    # Signal files
    print("  SIGNAL FILES")
    print(f"  {'Name':<22} {'Status':<10} {'Age':<10} {'Max':<10}")
    print(f"  {'-'*22} {'-'*10} {'-'*10} {'-'*10}")
    for r in signal_results:
        age_str = fmt_age(r["age_min"]) if r["age_min"] >= 0 else "---"
        max_str = fmt_age(r["max_age_min"])
        print(f"  {r['name']:<22} {r['status']:<10} {age_str:<10} {max_str:<10}")

    print()

    # Trader processes
    print("  TRADER PROCESSES")
    print(f"  {'Name':<22} {'Status':<10} {'PID':<10}")
    print(f"  {'-'*22} {'-'*10} {'-'*10}")
    for r in trader_results:
        pid_str = str(r.get("pid", r.get("detail", "---")))
        print(f"  {r['name']:<22} {r['status']:<10} {pid_str:<10}")

    print()

    # Summary
    all_results = cron_results + signal_results + trader_results
    total = len(all_results)
    ok_count = sum(1 for r in all_results if r["ok"])
    fail_count = total - ok_count

    if fail_count == 0:
        print(f"  ALL {total} CHECKS PASSED")
    else:
        print(f"  {fail_count}/{total} CHECKS FAILED")

    print(f"{'='*60}\n")


def write_alerts(cron_results, signal_results, trader_results):
    """Write alert JSON if any check failed."""
    alerts = []

    for r in cron_results:
        if not r["ok"]:
            alerts.append({
                "type": "cron_stale",
                "name": r["name"],
                "status": r["status"],
                "age_min": r["age_min"],
                "max_age_min": r["max_age_min"],
                "log": r["log"],
            })

    for r in signal_results:
        if not r["ok"]:
            alerts.append({
                "type": "signal_stale",
                "name": r["name"],
                "status": r["status"],
                "age_min": r["age_min"],
                "max_age_min": r["max_age_min"],
                "path": r["path"],
            })

    for r in trader_results:
        if not r["ok"]:
            alerts.append({
                "type": "process_dead",
                "name": r["name"],
                "status": r["status"],
                "pid": r.get("pid"),
                "detail": r.get("detail"),
            })

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "alerts": alerts,
    }

    SIGNALS.mkdir(parents=True, exist_ok=True)

    # Write atomically: temp file + rename
    tmp_path = ALERT_FILE.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(payload, f, indent=2)
    tmp_path.rename(ALERT_FILE)

    if alerts:
        print(f"  Wrote {len(alerts)} alert(s) to {ALERT_FILE}")
    else:
        print(f"  No alerts. Wrote clean status to {ALERT_FILE}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cron_results = check_crons()
    signal_results = check_signals()
    trader_results = check_traders()

    print_table(cron_results, signal_results, trader_results)
    write_alerts(cron_results, signal_results, trader_results)

    # Exit code: 1 if any failures, 0 if all OK
    all_results = cron_results + signal_results + trader_results
    has_failures = any(not r["ok"] for r in all_results)
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
