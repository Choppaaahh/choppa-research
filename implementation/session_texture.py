#!/usr/bin/env -S python3 -u
"""
Session Texture Analyzer — captures what's lost between sessions.

Analyzes conversation transcripts for:
1. Conversational texture — message velocity, rhythm, back-and-forth patterns
2. Energy/attention — message length, interruptions, natural language cues
3. Human implicit signals — question framing, topic steering, probe vs directive ratio

Runs at CC session compile time. Reads breadcrumbs + estimates from session patterns.
Output: texture tags appended to session notes or logged to texture_log.jsonl.

Usage:
    python3 scripts/session_texture.py                    # analyze current breadcrumbs
    python3 scripts/session_texture.py --file FILE        # analyze specific breadcrumb file
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BREADCRUMBS = REPO / "logs" / "session_breadcrumbs.jsonl"
TEXTURE_LOG = REPO / "logs" / "session_texture.jsonl"

# ─── Energy Word Maps ───────────────────────────────────────────────────────

HIGH_ENERGY = {
    # Customize with your own high-energy phrases
    # Examples: "lets go", "ship it", "perfect", "exactly"
}

LOW_ENERGY = {
    # Customize with your own low-energy / disengaged phrases
    # Examples: "maybe", "not sure", "later", "skip"
}

PROBE_WORDS = {
    # Customize with question/exploration phrases
    # Examples: "what if", "how come", "explain", "what about"
}

DIRECTIVE_WORDS = {
    # Customize with command/decision phrases
    # Examples: "do it", "build", "fix", "deploy", "push"
}


def load_breadcrumbs(filepath=None):
    """Load breadcrumbs from file."""
    path = Path(filepath) if filepath else BREADCRUMBS
    if not path.exists():
        return []
    crumbs = []
    with open(path) as f:
        for line in f:
            if line.strip():
                try:
                    crumbs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return crumbs


def analyze_texture(breadcrumbs):
    """Analyze session texture from breadcrumbs."""
    if not breadcrumbs:
        return None

    # Parse timestamps
    timestamps = []
    for b in breadcrumbs:
        try:
            ts = datetime.fromisoformat(b["ts"].replace("Z", "+00:00"))
            timestamps.append(ts)
        except (KeyError, ValueError):
            pass

    if len(timestamps) < 2:
        return None

    # ─── 1. Velocity & Rhythm ───────────────────────────────────────────
    intervals = []
    for i in range(1, len(timestamps)):
        delta = (timestamps[i] - timestamps[i-1]).total_seconds()
        if delta > 0:
            intervals.append(delta)

    avg_interval = sum(intervals) / len(intervals) if intervals else 0
    session_duration = (timestamps[-1] - timestamps[0]).total_seconds()
    crumbs_per_hour = len(breadcrumbs) / (session_duration / 3600) if session_duration > 0 else 0

    # Burst detection: intervals < 120s = rapid exchange
    bursts = sum(1 for i in intervals if i < 120)
    burst_ratio = bursts / len(intervals) if intervals else 0

    # ─── 2. Energy from Content ─────────────────────────────────────────
    high_count = 0
    low_count = 0
    probe_count = 0
    directive_count = 0
    interrupt_count = 0
    total_content_len = 0

    for b in breadcrumbs:
        content = b.get("content", "").lower()
        total_content_len += len(content)

        # Energy word matching
        for word in HIGH_ENERGY:
            if word in content:
                high_count += 1
                break  # one match per crumb

        for word in LOW_ENERGY:
            if word in content:
                low_count += 1
                break

        for word in PROBE_WORDS:
            if word in content:
                probe_count += 1
                break

        for word in DIRECTIVE_WORDS:
            if word in content:
                directive_count += 1
                break

        if "interrupted" in content.lower():
            interrupt_count += 1

    avg_content_len = total_content_len / len(breadcrumbs) if breadcrumbs else 0

    # Energy score: -1.0 (low) to +1.0 (high)
    energy_signals = high_count + interrupt_count - low_count
    max_signals = max(high_count + low_count + interrupt_count, 1)
    energy_score = energy_signals / max_signals

    # Mode: probing vs directing
    total_mode = max(probe_count + directive_count, 1)
    directive_ratio = directive_count / total_mode

    # ─── 3. Session Arc ─────────────────────────────────────────────────
    # Split session into thirds and compare energy
    third = len(breadcrumbs) // 3
    if third > 0:
        types_early = [b.get("type", "") for b in breadcrumbs[:third]]
        types_mid = [b.get("type", "") for b in breadcrumbs[third:2*third]]
        types_late = [b.get("type", "") for b in breadcrumbs[2*third:]]

        # Insight/finding density per phase
        insight_early = sum(1 for t in types_early if t in ("insight", "finding"))
        insight_mid = sum(1 for t in types_mid if t in ("insight", "finding"))
        insight_late = sum(1 for t in types_late if t in ("insight", "finding"))

        arc = "unknown"
        if insight_early > insight_late:
            arc = "front-loaded"  # discoveries early, execution late
        elif insight_late > insight_early:
            arc = "back-loaded"  # building early, discoveries late
        elif insight_mid > insight_early and insight_mid > insight_late:
            arc = "peak-middle"  # explore → discover → wrap
        else:
            arc = "even"
    else:
        arc = "too-short"

    # ─── Compile Results ────────────────────────────────────────────────
    result = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "session_duration_min": round(session_duration / 60, 1),
        "breadcrumb_count": len(breadcrumbs),
        "texture": {
            "crumbs_per_hour": round(crumbs_per_hour, 1),
            "avg_interval_s": round(avg_interval, 0),
            "burst_ratio": round(burst_ratio, 2),  # % of intervals < 2min
        },
        "energy": {
            "score": round(energy_score, 2),  # -1.0 to +1.0
            "high_signals": high_count,
            "low_signals": low_count,
            "interrupts": interrupt_count,
            "avg_content_len": round(avg_content_len, 0),
        },
        "mode": {
            "directive_ratio": round(directive_ratio, 2),  # 0=all probing, 1=all directing
            "probes": probe_count,
            "directives": directive_count,
        },
        "arc": arc,
        "label": _energy_label(energy_score, burst_ratio, directive_ratio),
    }

    return result


def _energy_label(energy_score, burst_ratio, directive_ratio):
    """Human-readable session energy label."""
    if energy_score > 0.5 and burst_ratio > 0.5:
        return "HIGH FLOW — rapid exchanges, decisive, building"
    elif energy_score > 0.3:
        return "ENGAGED — active work, moderate pace"
    elif energy_score > 0:
        return "STEADY — consistent work, even tempo"
    elif energy_score > -0.3:
        return "REFLECTIVE — slower pace, exploring, uncertain"
    else:
        return "LOW — winding down, fatigued, or disengaged"


def main():
    filepath = None
    if len(sys.argv) > 2 and sys.argv[1] == "--file":
        filepath = sys.argv[2]

    breadcrumbs = load_breadcrumbs(filepath)
    if not breadcrumbs:
        print("No breadcrumbs to analyze.")
        return

    result = analyze_texture(breadcrumbs)
    if not result:
        print("Insufficient data for texture analysis.")
        return

    # Print summary
    print(f"\n  SESSION TEXTURE ANALYSIS")
    print(f"  {'─'*40}")
    print(f"  Duration: {result['session_duration_min']}min | {result['breadcrumb_count']} breadcrumbs")
    print(f"  Velocity: {result['texture']['crumbs_per_hour']}/hr | avg interval {result['texture']['avg_interval_s']}s")
    print(f"  Burst ratio: {result['texture']['burst_ratio']:.0%} (exchanges < 2min)")
    print(f"  Energy: {result['energy']['score']:+.2f} ({result['energy']['high_signals']}H / {result['energy']['low_signals']}L / {result['energy']['interrupts']}int)")
    print(f"  Mode: {result['mode']['directive_ratio']:.0%} directive ({result['mode']['directives']}D / {result['mode']['probes']}P)")
    print(f"  Arc: {result['arc']}")
    print(f"  Label: {result['label']}")
    print()

    # Log to file
    try:
        with open(TEXTURE_LOG, "a") as f:
            f.write(json.dumps(result) + "\n")
        print(f"  Logged to {TEXTURE_LOG}")
    except Exception as e:
        print(f"  Log error: {e}")


if __name__ == "__main__":
    main()
