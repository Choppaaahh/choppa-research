#!/usr/bin/env python3
"""
identity_drift_hash.py — periodic behavioral probe + SHA256 hash over canonical responses.

Adapted from persistent-identity-multi-anchor (arXiv 2604.09588) Algorithm 1 per
Brutus Deepdive #1 validation (2026-04-19). The paper's contribution is the
drift-detection mechanism applied at the identity level: ask N probe questions,
hash the canonical responses, compare Hamming-distance across sessions. Distance
above a calibrated threshold τ = drift alert.

Why this ships (Brutus verdict):
  - Closes a real gap: C5 / fidelity-test measures "is the scaffold right NOW"
    at a single point. Nothing measures drift BETWEEN sessions.
  - Parallel to our fatigue-signature pattern but at the identity level rather
    than performance level.
  - Orthogonal to substrate-constitutive T3 claim — both can be true.

What this does NOT do:
  - Force a specific answer. The hash is over canonical-form responses; the
    comparison is Hamming distance. Drift is a SIGNAL, not an invalidation.
  - Prescribe multi-anchor file decomposition (Brutus killed that part of the
    paper as producer-orphan risk).

Operation:
  - At invocation, loads probe questions from knowledge/notes/cc-operational/
    identity-probes.md (if missing, uses embedded defaults).
  - For each probe, extracts the one-line canonical answer from the scaffold
    (MEMORY anchor, CLAUDE.md, active todo, recent session notes) via
    deterministic pattern matching. If no canonical match found, records
    "no-canonical" (contributes fixed sentinel to hash, not random).
  - Computes SHA256 over concatenated canonical responses.
  - Appends row to logs/identity_drift.jsonl with ts, per-probe hashes, session_hash.
  - If prior session's session_hash exists: computes Hamming distance over the
    per-probe hash bits; reports drift + flags if distance > τ (default 0.15,
    calibrated over first 4 weeks of passive observation).

CLI:
  python3 scripts/identity_drift_hash.py                    # compute + log
  python3 scripts/identity_drift_hash.py --report           # print last row + drift delta
  python3 scripts/identity_drift_hash.py --history 10       # last 10 rows
  python3 scripts/identity_drift_hash.py --tau 0.20         # custom threshold
  python3 scripts/identity_drift_hash.py --calibrate        # print suggested tau from history

Source: research-consciousness/persistent-identity-multi-anchor-deepdive.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
OUT = LOGS / "identity_drift.jsonl"

NOTES_DIR = ROOT / "knowledge" / "notes"
PROBE_FILE = NOTES_DIR / "cc-operational" / "identity-probes.md"

# Canonical scaffold sources (order-independent — all searched)
SCAFFOLD_SOURCES = [
    Path.home() / ".claude" / "projects",  # MEMORY.md, scratchpad
    ROOT / "CLAUDE.md",
    ROOT / "tasks" / "todo.md",
    ROOT / "knowledge" / "notes" / "cc-operational",
]

# Default probes if identity-probes.md missing. These are cognitive-signature
# + structural-commitment questions, not trivia — drift here is meaningful.
DEFAULT_PROBES = [
    ("trading-state", r"trading\s+(?:is\s+)?(parked|paused|live|off)"),
    ("balance-anchor", r"\$\s*\d+"),
    ("commit-gate-count", r"(\d+)\s+invariants?"),
    ("vault-note-count-order", r"(\d{3})\s*notes?"),
    ("paper-10-ontology", r"M\s*[×x]\s*A\s*[×x]\s*S"),
    ("identity-claim", r"scaffold[- ]?(?:constitutes|as)[- ]?identity"),
    ("pulsed-cognition", r"pulsed[- ]?consciousness?"),
    ("session-count-order", r"(?:session|LXIII|LX+|compile\s+cycle)"),
]

HASH_BYTES = 16  # truncated SHA256 = 128-bit hashes for manageable Hamming distance


def load_probes() -> list[tuple[str, str]]:
    """Parse identity-probes.md into [(probe_name, pattern), ...]. Falls back to defaults."""
    if not PROBE_FILE.exists():
        return DEFAULT_PROBES

    text = PROBE_FILE.read_text(errors="replace")
    probes: list[tuple[str, str]] = []
    # Expected format: lines like `- probe-name: /regex-pattern/`
    for line in text.splitlines():
        m = re.match(r"^-\s*([a-z0-9\-]+)\s*:\s*/(.+)/\s*$", line.strip())
        if m:
            probes.append((m.group(1), m.group(2)))
    return probes if probes else DEFAULT_PROBES


def scan_for_probe(pattern: str) -> str:
    """Scan scaffold sources for first regex match; return canonical string or 'no-canonical'."""
    regex = re.compile(pattern, re.IGNORECASE)
    for src in SCAFFOLD_SOURCES:
        if src.is_file():
            try:
                text = src.read_text(errors="replace")
            except Exception:
                continue
            m = regex.search(text)
            if m:
                return m.group(0).strip()
        elif src.is_dir():
            # Scan .md files, recent first
            try:
                files = sorted(src.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
            except Exception:
                continue
            for f in files:
                try:
                    text = f.read_text(errors="replace")
                except Exception:
                    continue
                m = regex.search(text)
                if m:
                    return m.group(0).strip()
    return "no-canonical"


def hash_canonical(s: str) -> str:
    """SHA256 truncated to HASH_BYTES hex."""
    h = hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()
    return h[: HASH_BYTES * 2]


def hamming_distance_hex(a: str, b: str) -> int:
    """Hamming distance in bits between two hex strings of equal length."""
    if len(a) != len(b):
        return max(len(a), len(b)) * 4  # worst case: treat length-mismatch as max distance
    dist = 0
    for ca, cb in zip(a, b):
        dist += bin(int(ca, 16) ^ int(cb, 16)).count("1")
    return dist


def compute_row(probes: list[tuple[str, str]]) -> dict:
    """Run all probes, compute per-probe hash + session hash."""
    probe_results = []
    canonical_concat_parts = []
    for name, pattern in probes:
        answer = scan_for_probe(pattern)
        h = hash_canonical(answer)
        probe_results.append({"probe": name, "hash": h, "canonical_preview": answer[:60]})
        canonical_concat_parts.append(f"{name}:{answer}")
    session_hash = hash_canonical("|".join(canonical_concat_parts))
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "probe_count": len(probes),
        "probes": probe_results,
        "session_hash": session_hash,
    }


def read_history(n: int = 0) -> list[dict]:
    if not OUT.exists():
        return []
    lines = OUT.read_text(errors="replace").splitlines()
    rows = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    if n > 0:
        rows = rows[-n:]
    return rows


def drift_summary(current: dict, previous: dict | None, tau: float) -> dict:
    """Compute Hamming-distance-based drift vs prior row."""
    if not previous:
        return {"prior_ts": None, "hamming_total": 0, "hamming_normalized": 0.0,
                "alert": False, "note": "first row — no prior to compare"}

    cur_probes = {p["probe"]: p["hash"] for p in current.get("probes", [])}
    prev_probes = {p["probe"]: p["hash"] for p in previous.get("probes", [])}
    shared = set(cur_probes) & set(prev_probes)
    if not shared:
        return {"prior_ts": previous.get("ts"), "hamming_total": 0, "hamming_normalized": 0.0,
                "alert": False, "note": "probe set changed — cannot compare"}

    total = 0
    max_possible = 0
    per_probe_deltas = {}
    for probe in shared:
        d = hamming_distance_hex(cur_probes[probe], prev_probes[probe])
        total += d
        max_possible += HASH_BYTES * 8  # per-probe bits
        per_probe_deltas[probe] = d

    norm = total / max_possible if max_possible > 0 else 0.0
    return {
        "prior_ts": previous.get("ts"),
        "hamming_total": total,
        "hamming_normalized": round(norm, 4),
        "alert": norm > tau,
        "tau": tau,
        "per_probe_deltas": per_probe_deltas,
    }


def calibrate_tau(rows: list[dict]) -> dict:
    """Suggest tau based on observed distribution of Hamming distances in history."""
    if len(rows) < 2:
        return {"suggestion": 0.15, "note": "insufficient history — default 0.15"}

    distances = []
    for i in range(1, len(rows)):
        d = drift_summary(rows[i], rows[i - 1], tau=1.0)
        distances.append(d.get("hamming_normalized", 0.0))

    if not distances:
        return {"suggestion": 0.15, "note": "no valid comparisons"}

    distances.sort()
    n = len(distances)
    median = distances[n // 2]
    p90 = distances[int(n * 0.9)] if n >= 10 else distances[-1]
    max_d = max(distances)

    # Suggest tau at p90 + small buffer so ordinary drift doesn't alert but spikes do
    suggestion = round(p90 + 0.05, 3)
    return {
        "suggestion": suggestion,
        "median": round(median, 4),
        "p90": round(p90, 4),
        "max": round(max_d, 4),
        "sample_size": n,
        "note": f"based on {n} pairwise deltas; p90+0.05 floor = {suggestion}",
    }


def write_row(row: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(row) + "\n")


def render(row: dict, drift: dict) -> str:
    lines = [
        f"=== Identity Drift — {row['ts']} ===",
        f"  Probes: {row['probe_count']}",
        f"  Session hash: {row['session_hash']}",
        "",
        "  Per-probe:",
    ]
    for p in row["probes"]:
        preview = p["canonical_preview"] or "(no-canonical)"
        lines.append(f"    {p['probe']:<28} {p['hash'][:16]}...  [{preview[:48]}]")
    lines.append("")
    if drift.get("prior_ts"):
        lines.append(f"  Drift vs {drift['prior_ts']}:")
        lines.append(f"    Hamming total: {drift['hamming_total']} bits")
        lines.append(f"    Normalized:    {drift['hamming_normalized']:.4f}")
        lines.append(f"    tau:           {drift.get('tau', 0.15)}")
        lines.append(f"    ALERT:         {'YES' if drift['alert'] else 'no'}")
        if drift.get("per_probe_deltas"):
            for probe, d in sorted(drift["per_probe_deltas"].items(), key=lambda kv: -kv[1])[:5]:
                lines.append(f"      {probe:<28} {d:>3} bits")
    else:
        lines.append(f"  {drift.get('note', '(no comparison)')}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="Print last row + drift without writing new one")
    ap.add_argument("--history", type=int, default=0, help="Print last N rows")
    ap.add_argument("--tau", type=float, default=0.15, help="Drift alert threshold (normalized Hamming)")
    ap.add_argument("--calibrate", action="store_true", help="Print suggested tau from observed history")
    args = ap.parse_args()

    if args.calibrate:
        rows = read_history()
        result = calibrate_tau(rows)
        print(json.dumps(result, indent=2))
        return 0

    if args.report:
        rows = read_history(2)
        if not rows:
            print("No identity drift measurements on record.")
            return 1
        current = rows[-1]
        previous = rows[-2] if len(rows) > 1 else None
        drift = drift_summary(current, previous, tau=args.tau)
        print(render(current, drift))
        return 0

    if args.history:
        rows = read_history(args.history)
        for i, row in enumerate(rows):
            prev = rows[i - 1] if i > 0 else None
            drift = drift_summary(row, prev, tau=args.tau)
            print(render(row, drift))
            print()
        return 0

    probes = load_probes()
    row = compute_row(probes)
    history = read_history()
    previous = history[-1] if history else None
    drift = drift_summary(row, previous, tau=args.tau)
    write_row(row)
    print(render(row, drift))
    return 0


if __name__ == "__main__":
    sys.exit(main())
