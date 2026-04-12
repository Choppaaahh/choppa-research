#!/usr/bin/env python3
"""
Chord Instrumentation — Measure metacognitive co-instantiation.
Perrier & Bennett (arXiv 2603.09043) steal.

Arpeggio: ingredients appear individually across a session (scattered)
Chord: ingredients co-instantiate at a single decision point (simultaneous)

Measures from scaffold traces:
1. For each decision breadcrumb, check if MEMORY, SELF, TEMPORAL, UNCERTAIN
   ingredients are present in the surrounding context (±2 breadcrumbs)
2. Chord score = how many decisions have all 4 ingredients co-present
3. Arpeggio score = how many ingredients appear ANYWHERE in the session

Usage:
    python3 scripts/chord_measure.py                # measure current session
    python3 scripts/chord_measure.py --history      # trend over time
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).parent.parent
BREADCRUMBS = REPO / "logs" / "session_breadcrumbs.jsonl"
CHAINS = REPO / "logs" / "reasoning_chains.jsonl"
CHORD_LOG = REPO / "logs" / "chord_scores.jsonl"

parser = argparse.ArgumentParser()
parser.add_argument("--history", action="store_true")
parser.add_argument("--window", type=int, default=2, help="Context window around decisions")
args = parser.parse_args()

# Metacognitive ingredient detectors
INGREDIENT_DETECTORS = {
    "MEMORY": [
        "vault", "vault_search", "prior", "we've seen", "previously",
        "breadcrumb", "pattern", "knowledge", "note", "documented",
    ],
    "SELF": [
        "confidence", "track record", "my bias", "i tend to",
        "over-caution", "i notice", "my assumption", "calibration",
    ],
    "TEMPORAL": [
        "recently", "today", "yesterday", "this session", "last session",
        "since", "changed", "now", "currently", "was", "became",
    ],
    "UNCERTAIN": [
        "uncertain", "might be wrong", "could be", "risk",
        "assumption", "what if", "challenge", "caveat", "unknown",
    ],
}


def detect_ingredients(text):
    """Detect which metacognitive ingredients are present in text."""
    text_lower = text.lower()
    present = set()
    for ingredient, keywords in INGREDIENT_DETECTORS.items():
        if any(kw in text_lower for kw in keywords):
            present.add(ingredient)
    return present


def load_breadcrumbs():
    items = []
    if not BREADCRUMBS.exists():
        return items
    for line in BREADCRUMBS.read_text(errors="replace").splitlines():
        try:
            items.append(json.loads(line))
        except:
            pass
    return items


def measure_chord():
    """Measure Chord vs Arpeggio scores from breadcrumb traces."""
    breadcrumbs = load_breadcrumbs()
    if not breadcrumbs:
        print("No breadcrumbs found.")
        return

    # Find decision points
    decisions = [(i, bc) for i, bc in enumerate(breadcrumbs)
                 if bc.get("type") in ("decision", "action")]

    if not decisions:
        print("No decision breadcrumbs found.")
        return

    # Arpeggio: which ingredients appear ANYWHERE in the session?
    all_text = " ".join(bc.get("content", "") for bc in breadcrumbs)
    arpeggio_ingredients = detect_ingredients(all_text)
    arpeggio_score = len(arpeggio_ingredients) / 4.0

    # Chord: for each decision, which ingredients co-present in ±window?
    chord_scores = []
    decision_details = []

    for idx, (pos, decision) in enumerate(decisions):
        # Get context window: decision + surrounding breadcrumbs
        window_start = max(0, pos - args.window)
        window_end = min(len(breadcrumbs), pos + args.window + 1)
        context = " ".join(bc.get("content", "") for bc in breadcrumbs[window_start:window_end])

        ingredients = detect_ingredients(context)
        chord = len(ingredients) / 4.0
        chord_scores.append(chord)

        decision_details.append({
            "decision": decision.get("content", "")[:60],
            "ts": decision.get("ts", "")[:16],
            "ingredients": sorted(ingredients),
            "chord_score": chord,
            "missing": sorted(set(INGREDIENT_DETECTORS.keys()) - ingredients),
        })

    avg_chord = sum(chord_scores) / len(chord_scores) if chord_scores else 0
    full_chord = sum(1 for s in chord_scores if s >= 1.0)  # all 4 ingredients
    partial_chord = sum(1 for s in chord_scores if 0.5 <= s < 1.0)

    # Report
    print(f"\n{'='*60}")
    print(f"CHORD / ARPEGGIO MEASUREMENT")
    print(f"{'='*60}")
    print(f"  Breadcrumbs: {len(breadcrumbs)} | Decisions: {len(decisions)}")
    print(f"  Arpeggio score: {arpeggio_score:.0%} ({len(arpeggio_ingredients)}/4 ingredients somewhere in session)")
    print(f"  Avg Chord score: {avg_chord:.0%} (ingredients co-present at decision time)")
    print(f"  Full Chord (4/4): {full_chord}/{len(decisions)} decisions ({full_chord/max(len(decisions),1)*100:.0f}%)")
    print(f"  Partial (2-3/4): {partial_chord}/{len(decisions)}")
    print(f"  Missing Chord (0-1/4): {len(decisions) - full_chord - partial_chord}/{len(decisions)}")

    if arpeggio_score > avg_chord + 0.2:
        print(f"\n  ⚠ ARPEGGIO > CHORD by {(arpeggio_score-avg_chord)*100:.0f}pp — ingredients scattered, not co-instantiated")
    elif avg_chord >= 0.75:
        print(f"\n  ✓ CHORD STRONG — metacognitive ingredients co-present at most decisions")

    # Show worst decisions (lowest chord)
    worst = sorted(decision_details, key=lambda x: x["chord_score"])[:3]
    if worst:
        print(f"\n  Lowest-Chord decisions (repair targets):")
        for d in worst:
            print(f"    [{d['ts']}] {d['decision']}")
            print(f"      Present: {d['ingredients']} | Missing: {d['missing']}")

    # Log
    with open(CHORD_LOG, "a") as f:
        log_entry = {
            "ts": breadcrumbs[-1].get("ts", "")[:19] if breadcrumbs else "",
            "n_decisions": len(decisions),
            "arpeggio": round(arpeggio_score, 2),
            "avg_chord": round(avg_chord, 2),
            "full_chord_pct": round(full_chord / max(len(decisions), 1), 2),
            "ingredients_session": sorted(arpeggio_ingredients),
        }
        f.write(json.dumps(log_entry) + "\n")

    return avg_chord, arpeggio_score


def show_history():
    """Show Chord score trend over time."""
    if not CHORD_LOG.exists():
        print("No history — run without --history first.")
        return

    entries = []
    for line in CHORD_LOG.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except:
            pass

    print(f"\n  CHORD SCORE HISTORY ({len(entries)} measurements)")
    print(f"  {'='*50}")
    for e in entries:
        arp = e.get("arpeggio", 0)
        chd = e.get("avg_chord", 0)
        full = e.get("full_chord_pct", 0)
        bar = "█" * int(chd * 10) + "░" * (10 - int(chd * 10))
        print(f"  {e.get('ts', '?')[:10]} | Chord [{bar}] {chd:.0%} | Arpeggio {arp:.0%} | Full {full:.0%}")


def main():
    if args.history:
        show_history()
    else:
        measure_chord()


if __name__ == "__main__":
    main()
