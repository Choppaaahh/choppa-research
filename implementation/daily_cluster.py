#!/usr/bin/env python3
"""
3pm Daily Cluster — fidelity + vault health + chord + probe QA + digest.
Posts results to Discord #cc channel.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "scripts"))

def run_script(name, args=[]):
    try:
        result = subprocess.run(
            ["python3", str(REPO / "scripts" / name)] + args,
            capture_output=True, text=True, timeout=120, cwd=str(REPO))
        return result.stdout[:500]
    except Exception as e:
        return f"ERROR: {e}"

def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sections = [f"**SCHEDULED TASKS DIGEST -- {ts}**"]
    sections.append("")

    # Fidelity
    print("1. Fidelity...")
    fid_path = REPO / "logs" / "fidelity_scores.jsonl"
    if fid_path.exists():
        try:
            last = json.loads([l for l in fid_path.read_text().splitlines() if l.strip()][-1])
            avg = last.get("avg", {})
            scores = " | ".join(f"{k.upper()}={v:.2f}" for k, v in avg.items() if v is not None)
            flags = []
            if avg.get("why", 1) < 0.65: flags.append("WHY below threshold")
            if avg.get("context", 1) < 0.70: flags.append("CONTEXT degraded")
            line = f"Fidelity: {scores}"
            if flags:
                line += f"\n  Flags: {', '.join(flags)}"
            sections.append(line)
        except Exception:
            pass

    # Vault health
    print("2. Vault...")
    vault = run_script("index_vault.py", ["--stats"])
    for line in vault.splitlines():
        if "notes indexed" in line.lower():
            sections.append(f"Vault: {line.strip()}")
            break

    # Chord (one line)
    print("3. Chord...")
    chord = run_script("chord_measure.py")
    chord_parts = []
    for line in chord.splitlines():
        if "Avg Chord" in line:
            import re
            m = re.search(r'(\d+)%', line)
            if m: chord_parts.append(f"Chord {m.group(1)}%")
        if "Full Chord" in line:
            m = re.search(r'(\d+/\d+)', line)
            if m: chord_parts.append(f"Full {m.group(1)}")
    if chord_parts:
        sections.append(" | ".join(chord_parts))

    # Metacog (one line)
    print("4. Metacog...")
    mc = run_script("metacog_tracker.py")
    mc_parts = {}
    for line in mc.splitlines():
        if "Compile #" in line:
            import re
            m = re.search(r'Compile #(\d+)', line)
            if m: mc_parts["compile"] = m.group(1)
        if "Promoted:" in line:
            m = re.search(r'Promoted: (\d+)', line)
            if m: mc_parts["promoted"] = m.group(1)
        if "Chains/day" in line or "Rate:" in line:
            m = re.search(r'([\d.]+)/day', line)
            if m: mc_parts["rate"] = m.group(1)
        if "Total chains:" in line or "total_chains" in line:
            m = re.search(r'(\d+)', line)
            if m: mc_parts["chains"] = m.group(1)
    if mc_parts:
        sections.append(f"Metacog: compile #{mc_parts.get('compile','?')} | "
                       f"{mc_parts.get('promoted','?')} promoted | "
                       f"{mc_parts.get('chains','?')} chains")

    # Confidence
    print("5. Confidence...")
    conf = run_script("confidence_decay.py")
    for line in conf.splitlines():
        if "avg" in line.lower() and "confidence" in line.lower():
            sections.append(f"Confidence: {line.strip()}")
            break

    # Bot status (one line)
    print("6. Bot...")
    bot = run_script("process_supervisor.py", ["--check-only"])
    bot_parts = []
    for line in bot.splitlines():
        l = line.strip()
        if "HEALTHY" in l or "RUNNING" in l or "OFF" in l:
            bot_parts.append(l)
    if bot_parts:
        sections.append(f"Bot: {' | '.join(bot_parts[:3])}")

    # Domain health
    print("7. Domains...")
    try:
        from pathlib import Path as _P
        domain_counts = {}
        for f in _P("knowledge/notes").rglob("*.md"):
            parts = f.relative_to("knowledge/notes").parts
            if len(parts) > 1:
                domain = parts[0]
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        top = sorted(domain_counts.items(), key=lambda x: -x[1])
        thin = [(d, c) for d, c in top if c < 20]
        top_str = " | ".join(f"{d} {c}" for d, c in top[:4])
        thin_str = ", ".join(f"{d} {c}" for d, c in thin[:3]) if thin else "none"
        sections.append(f"Domains: {top_str} | thin: {thin_str}")
    except Exception:
        pass

    # Research (compact)
    print("8. Research...")
    digest = run_script("research_digest.py")
    for line in digest.splitlines():
        if "findings in last" in line:
            sections.append(f"Research: {line.strip()}")
            break

    # Predictions
    print("9. Predictions...")
    pred_report = run_script("prediction_tracker.py", ["--report"])
    for line in pred_report.splitlines():
        if "Total:" in line or "Accuracy:" in line or "Pending:" in line:
            sections.append(f"Predictions: {line.strip()}")

    # Scaffold health
    print("10. Health...")
    health = run_script("scaffold_health.py", ["--short"])
    if health.strip():
        sections.append(health.strip())

    # Living doc staleness check
    print("11. Staleness...")
    import os
    from pathlib import Path as _P2
    stale = []
    for name, path in [
        ("MEMORY.md", _P2(os.path.expanduser("~/.claude/projects/YOUR-PROJECT-PATH/memory/MEMORY.md"))),
        ("todo.md", REPO / "tasks" / "todo.md"),
    ]:
        if path.exists():
            age_hrs = (time.time() - path.stat().st_mtime) / 3600
            if age_hrs > 12:
                stale.append(f"{name} ({age_hrs:.0f}hrs)")
    if stale:
        sections.append(f"STALE: {', '.join(stale)}")

    report = "\n".join(sections)
    print(f"\n{report}")

    # Post to Discord
    try:
        post(report, "cc")
        print("\nPosted to Discord #cc")
    except Exception as e:
        print(f"\nDiscord post failed: {e}")


if __name__ == "__main__":
    main()
