#!/usr/bin/env python3
"""
Scaffold Health -- Comprehensive health metrics for the external brain.

Measures everything the scaffold needs to self-diagnose:
- Vault: notes, links, orphans, danglers, domain balance
- Memory: breadcrumbs/day, chains/day, patterns promoted/used
- Fidelity: WHAT/WHY/CONTEXT/BRIDGE scores
- Chord: co-instantiation rate at decision time
- Bot: uptime, pairs/hr, P&L, inventory drag
- Infra: crons running, tick recorder, disk space

Fires in daily cluster. Also callable standalone for debugging.

Usage:
    python3 scaffold_health.py           # full report
    python3 scaffold_health.py --short   # one-liner for daily cluster
"""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).parent.parent

parser = argparse.ArgumentParser()
parser.add_argument("--short", action="store_true")
args = parser.parse_args()


def vault_health():
    """Vault statistics."""
    vault = REPO / "knowledge" / "notes"
    notes = list(vault.rglob("*.md"))
    n_notes = len(notes)

    # Domain counts
    domains = defaultdict(int)
    for f in notes:
        parts = f.relative_to(vault).parts
        if len(parts) > 1:
            domains[parts[0]] += 1

    thin = [(d, c) for d, c in sorted(domains.items(), key=lambda x: x[1]) if c < 15]

    # Link count from index
    links = 0
    try:
        result = subprocess.run(
            ["python3", str(REPO / "scripts" / "index_vault.py"), "--stats"],
            capture_output=True, text=True, timeout=15, cwd=str(REPO))
        for line in result.stdout.splitlines():
            if "wikilinks" in line.lower():
                import re
                m = re.search(r'(\d+)\s*wikilinks', line)
                links = int(m.group(1)) if m else 0
    except Exception:
        links = 0

    return {"notes": n_notes, "links": links, "domains": len(domains),
            "thin_domains": thin, "links_per_note": round(links / max(n_notes, 1), 1)}


def memory_health():
    """Breadcrumb + chain + pattern metrics."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    bc_file = REPO / "logs" / "session_breadcrumbs.jsonl"
    chain_file = REPO / "logs" / "reasoning_chains.jsonl"

    bc_today = 0
    bc_total = 0
    chain_today = 0
    chain_total = 0

    if bc_file.exists():
        for line in bc_file.read_text(errors="replace").splitlines():
            try:
                c = json.loads(line)
                bc_total += 1
                if today in c.get("ts", "") or yesterday in c.get("ts", ""):
                    bc_today += 1
            except:
                pass

    if chain_file.exists():
        for line in chain_file.read_text(errors="replace").splitlines():
            try:
                c = json.loads(line)
                chain_total += 1
                if today in c.get("ts", "") or yesterday in c.get("ts", ""):
                    chain_today += 1
            except:
                pass

    # Metacog
    promoted = 0
    try:
        result = subprocess.run(
            ["python3", str(REPO / "scripts" / "metacog_tracker.py")],
            capture_output=True, text=True, timeout=30, cwd=str(REPO))
        for line in result.stdout.splitlines():
            if "Promoted:" in line:
                import re
                m = re.search(r'Promoted: (\d+)', line)
                if m: promoted = int(m.group(1))
    except Exception:
        pass

    return {"bc_today": bc_today, "bc_total": bc_total,
            "chains_today": chain_today, "chains_total": chain_total,
            "promoted": promoted}


def fidelity_health():
    """Latest fidelity scores."""
    fid_file = REPO / "logs" / "fidelity_scores.jsonl"
    if not fid_file.exists():
        return None
    try:
        last = json.loads([l for l in fid_file.read_text().splitlines() if l.strip()][-1])
        return last.get("avg", {})
    except Exception:
        return None


def bot_health():
    """Bot process + recent P&L."""
    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    bot_running = "equities_mm" in result.stdout
    tick_running = "tick_recorder" in result.stdout

    # Latest log P&L
    log_dir = REPO / "logs"
    latest_log = None
    for f in sorted(log_dir.glob("crypto_mm_live_*.log"), reverse=True):
        latest_log = f
        break

    pnl = 0
    pairs = 0
    if latest_log:
        import re
        content = latest_log.read_text(errors="replace")
        bal_lines = re.findall(r'P&L=\$([\+\-\d.]+)', content)
        if bal_lines:
            pnl = float(bal_lines[-1])
        pairs = len(re.findall(r'PAIR COMPLETE', content))

    return {"bot_running": bot_running, "tick_running": tick_running,
            "session_pnl": pnl, "session_pairs": pairs}


def infra_health():
    """Infrastructure checks."""
    # Cron count
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    crons = len([l for l in result.stdout.splitlines() if l.strip() and not l.startswith("#")])

    # Disk space
    result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    disk_lines = result.stdout.splitlines()
    disk_pct = "?"
    if len(disk_lines) > 1:
        parts = disk_lines[1].split()
        disk_pct = parts[4] if len(parts) > 4 else "?"

    # Bug patterns
    bugs = len(list((REPO / "knowledge" / "bug-patterns").glob("*.md"))) if (REPO / "knowledge" / "bug-patterns").exists() else 0

    return {"crons": crons, "disk_used": disk_pct, "bug_patterns": bugs}


def main():
    v = vault_health()
    m = memory_health()
    f = fidelity_health()
    b = bot_health()
    i = infra_health()

    if args.short:
        fid_str = f"F:{f.get('what',0):.0%}/{f.get('why',0):.0%}/{f.get('context',0):.0%}/{f.get('bridge',0):.0%}" if f else "F:?"
        print(f"Health: {v['notes']}n {v['links']}L {v['links_per_note']}L/n | "
              f"{m['bc_today']}bc {m['chains_today']}ch {m['promoted']}pat | "
              f"{fid_str} | "
              f"{'BOT OK' if b['bot_running'] else 'BOT DOWN'} {b['session_pairs']}pairs ${b['session_pnl']:+.0f} | "
              f"{i['crons']}crons {i['disk_used']}disk {i['bug_patterns']}bugs")
        return

    print("=" * 60)
    print(f"SCAFFOLD HEALTH -- {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print("=" * 60)

    print(f"\nVault: {v['notes']} notes | {v['links']} links | {v['links_per_note']} links/note | {v['domains']} domains")
    if v['thin_domains']:
        print(f"  Thin: {', '.join(f'{d} ({c})' for d, c in v['thin_domains'][:5])}")

    print(f"\nMemory: {m['bc_today']} breadcrumbs today | {m['chains_today']} chains today | {m['promoted']} promoted patterns")
    print(f"  Totals: {m['bc_total']} breadcrumbs | {m['chains_total']} chains")

    if f:
        print(f"\nFidelity: WHAT={f.get('what',0):.0%} WHY={f.get('why',0):.0%} CONTEXT={f.get('context',0):.0%} BRIDGE={f.get('bridge',0):.0%}")
    else:
        print("\nFidelity: no scores")

    print(f"\nBot: {'RUNNING' if b['bot_running'] else 'DOWN'} | {b['session_pairs']} pairs | ${b['session_pnl']:+.1f} P&L")
    print(f"  Tick recorder: {'RUNNING' if b['tick_running'] else 'DOWN'}")

    print(f"\nInfra: {i['crons']} crons | {i['disk_used']} disk | {i['bug_patterns']} bug patterns")


if __name__ == "__main__":
    main()
