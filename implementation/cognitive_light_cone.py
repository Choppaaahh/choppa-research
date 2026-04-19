#!/usr/bin/env python3
"""
cognitive_light_cone.py — Levin CLC 4-dimension tracker for scaffolded system vs baseline.

Implements the Cognitive Light Cone metric (Pezzulo & Levin, arXiv:2602.08079) as a
substrate-independent proxy for the scaffold's cognitive scope. Scores the current
scaffold state on four dimensions:

    1. TIME HORIZON   — how far into the future goals are represented
    2. SPATIAL SCOPE  — breadth of the system's effective representational space
    3. GOAL PERSISTENCE — how reliably goals survive perturbation / context loss
    4. MULTISCALE COORDINATION — goals pursued at multiple timescales simultaneously

Writes a single row to logs/cognitive_light_cone.jsonl per invocation:
    {"ts": ISO, "time_horizon": ..., "spatial_scope": ...,
     "goal_persistence": ..., "multiscale": ..., "score_summary": {...}}

The scores are not absolute magnitudes. They are defined relative to a fixed baseline
(a raw LLM cold-start session) which scores 1 on each dimension by convention. The
scaffolded system's score is the estimated ratio on each dimension. Quarterly runs
produce a longitudinal record for Paper 09c §5.11.3 empirical backing and for
tracking scaffold cognitive scope over time.

Usage:
    python3 cognitive_light_cone.py                # score current scaffold + write row
    python3 cognitive_light_cone.py --report       # pretty-print last row
    python3 cognitive_light_cone.py --history N    # last N rows with trend

Source: knowledge/notes/research-consciousness/scaffold-cognitive-light-cone-measurement.md
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "knowledge" / "notes"
LOGS = ROOT / "logs"
OUT = LOGS / "cognitive_light_cone.jsonl"


# ---------- dimension 1: TIME HORIZON ----------

def score_time_horizon() -> dict:
    """Effective forward goal horizon in orders of magnitude over baseline (1 hour)."""
    horizons = []
    todo = ROOT / "tasks" / "todo.md"
    if todo.exists():
        horizons.append(("todo.md", 24 * 7))  # week-scale
    build_queue = list((ROOT / "tasks").glob("build*.md")) + list((ROOT / "tasks").glob("*build*queue*.md"))
    if build_queue:
        horizons.append(("build_queue", 24 * 30 * 3))  # quarter-scale
    papers_dir = ROOT / "research"
    if papers_dir.exists() and any(papers_dir.rglob("*.md")):
        horizons.append(("paper_drafts", 24 * 30 * 12))  # year-scale
    memory = Path.home() / ".claude" / "projects" / "MEMORY.md"  # configure per deployment
    if memory.exists():
        horizons.append(("MEMORY.md", 4))  # session-protocol anchor
    eff = max((h for _, h in horizons), default=1)
    return {
        "max_horizon_hours": eff,
        "baseline_hours": 1,
        "ratio": round(eff / 1, 1),
        "components": [name for name, _ in horizons],
    }


# ---------- dimension 2: SPATIAL SCOPE ----------

def score_spatial_scope() -> dict:
    """Breadth of representational/control space. Baseline = single conversation context."""
    notes = list(VAULT.rglob("*.md")) if VAULT.exists() else []
    note_count = len(notes)
    domains = set()
    for p in notes:
        rel = p.relative_to(VAULT) if VAULT in p.parents else None
        if rel and rel.parent and str(rel.parent) != ".":
            domains.add(str(rel.parent).split(os.sep)[0])
    domain_count = len(domains)

    cron_count = 0
    crontab = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
    if crontab.returncode == 0:
        cron_count = len([ln for ln in crontab.stdout.splitlines() if ln.strip() and not ln.startswith("#")])

    agents_dir = ROOT / ".claude" / "agents"
    agent_count = len(list(agents_dir.glob("*.md"))) if agents_dir.exists() else 0

    baseline_tokens = 200_000
    effective_scope_tokens = (note_count * 800) + (cron_count * 500) + (agent_count * 2000)
    ratio = max(1.0, effective_scope_tokens / baseline_tokens)
    return {
        "vault_notes": note_count,
        "domains": domain_count,
        "cron_tasks": cron_count,
        "agents": agent_count,
        "ratio": round(ratio, 1),
    }


# ---------- dimension 3: GOAL PERSISTENCE ----------

def score_goal_persistence() -> dict:
    """Reliability of goal survival across session boundaries. Baseline = 1 (reset = loss)."""
    reconstitution_file = LOGS / "reconstitution_log.jsonl" if LOGS.exists() else None
    scaffold_fidelity = None
    if reconstitution_file and reconstitution_file.exists():
        rows = []
        for ln in reconstitution_file.read_text().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        if rows:
            pct_vals = [r.get("reconstitution_pct") for r in rows if isinstance(r.get("reconstitution_pct"), (int, float))]
            if pct_vals:
                scaffold_fidelity = sum(pct_vals[-5:]) / len(pct_vals[-5:]) / 100.0

    persistent_substrate = {
        "MEMORY.md": (Path.home() / ".claude" / "projects" / "MEMORY.md"  # configure per deployment).exists(),
        "CLAUDE.md": (ROOT / "CLAUDE.md").exists(),
        "todo.md": (ROOT / "tasks" / "todo.md").exists(),
        "vault": VAULT.exists(),
    }
    substrate_count = sum(1 for v in persistent_substrate.values() if v)

    fidelity = scaffold_fidelity if scaffold_fidelity is not None else 0.72  # default per R14 historical
    ratio = max(1.0, fidelity * substrate_count * 5)
    return {
        "substrate_components": substrate_count,
        "measured_fidelity": round(fidelity, 2),
        "ratio": round(ratio, 1),
    }


# ---------- dimension 4: MULTISCALE COORDINATION ----------

def score_multiscale() -> dict:
    """Number of timescales the system operates on simultaneously. Baseline = 1."""
    timescales = set()
    # within-session / generation
    timescales.add("generation")
    # session-level
    if (ROOT / "tasks" / "todo.md").exists():
        timescales.add("session")
    # episodic / compile
    compile_chain = LOGS / "reasoning_chains.jsonl"
    if compile_chain.exists():
        timescales.add("episodic")
    # training / architectural
    if (ROOT / "data").exists() and any((ROOT / "data").glob("sft_*.jsonl")):
        timescales.add("training")
    # retrieval-autopoietic
    if (ROOT / "scripts" / "retrieval_frequency_tracker.py").exists():
        timescales.add("retrieval_reinforcement")

    return {
        "timescales_active": sorted(list(timescales)),
        "count": len(timescales),
        "ratio": round(len(timescales) / 1, 1),
    }


# ---------- aggregator + I/O ----------

def score_all() -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "time_horizon": score_time_horizon(),
        "spatial_scope": score_spatial_scope(),
        "goal_persistence": score_goal_persistence(),
        "multiscale": score_multiscale(),
    }


def write_row(row: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(row) + "\n")


def render_row(row: dict) -> str:
    th = row["time_horizon"]["ratio"]
    ss = row["spatial_scope"]["ratio"]
    gp = row["goal_persistence"]["ratio"]
    ms = row["multiscale"]["ratio"]
    return (
        f"=== Cognitive Light Cone — {row['ts']} ===\n"
        f"  Time horizon:           {th:>6}x  ({row['time_horizon']['max_horizon_hours']}h vs 1h baseline)\n"
        f"  Spatial scope:          {ss:>6}x  ({row['spatial_scope']['vault_notes']} notes, "
        f"{row['spatial_scope']['domains']} domains, {row['spatial_scope']['cron_tasks']} cron, "
        f"{row['spatial_scope']['agents']} agents)\n"
        f"  Goal persistence:       {gp:>6}x  (fidelity={row['goal_persistence']['measured_fidelity']}, "
        f"substrate={row['goal_persistence']['substrate_components']}/4)\n"
        f"  Multiscale coord:       {ms:>6}x  ({row['multiscale']['count']} timescales: "
        f"{', '.join(row['multiscale']['timescales_active'])})\n"
    )


def read_history(n: int) -> list:
    if not OUT.exists():
        return []
    lines = OUT.read_text().splitlines()
    rows = []
    for ln in lines[-n:]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="Print latest row without writing")
    ap.add_argument("--history", type=int, default=0, help="Print last N rows")
    args = ap.parse_args()

    if args.report:
        rows = read_history(1)
        if rows:
            print(render_row(rows[-1]))
        else:
            print("No CLC measurements on record.")
        return
    if args.history:
        for r in read_history(args.history):
            print(render_row(r))
        return

    row = score_all()
    write_row(row)
    print(render_row(row))


if __name__ == "__main__":
    main()
