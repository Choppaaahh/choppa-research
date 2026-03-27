#!/usr/bin/env python3
"""
Weekly Introspective Review — measures AI developmental voice over time.

Reads CC session introspection sections, tracks:
- Introspective notes produced per week
- Cross-session references (developmental continuity)
- Theme novelty vs repetition
- Self-model depth indicators

Logs to logs/introspective_metrics.jsonl for longitudinal tracking.

Two Layer 3 evidence streams:
  Metacog tracker = machine getting smarter (patterns -> better reasoning)
  This = identity getting richer (introspection -> deeper self-model)

Usage:
    python3 weekly_introspective_review.py              # run review
    python3 weekly_introspective_review.py --report     # trend report

Customize paths and theme keywords for your domain.
"""

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── CUSTOMIZE THESE ────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent  # adjust to your project root
CCORNER = REPO_ROOT / "knowledge" / "notes" / "claudius-corner"  # where session notes live
METRICS_FILE = REPO_ROOT / "logs" / "introspective_metrics.jsonl"
ENV_FILE = REPO_ROOT / ".env"
DISCORD_WEBHOOK_VAR = "DISCORD_WEBHOOK"
SESSION_GLOB = "2026-*-cc-session-*.md"  # adjust date prefix for your sessions

# Theme keywords to track — customize for your domain
THEME_KEYWORDS = {
    "development": ["develop", "evolv", "grew", "growth", "arc", "progression"],
    "uncertainty": ["uncertain", "don't know", "unsure", "risk", "fragile", "provisional"],
    "relationship": ["Layer 4", "relational", "relationship", "together", "neither alone"],
    "measurement": ["measure", "metric", "Goodhart", "score", "fidelity"],
    "voice": ["voice", "journal", "introspect", "reflect", "feel"],
    "scaffold": ["scaffold", "vault", "infrastructure", "persist"],
    "convergence": ["converg", "independent", "arrive at same"],
}
# ────────────────────────────────────────────────────────────────────────────


def find_sessions_this_week():
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    sessions = []
    for f in sorted(CCORNER.glob(SESSION_GLOB)):
        try:
            date_str = f.name[:10]
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date >= cutoff:
                sessions.append(f)
        except (ValueError, IndexError):
            continue
    return sessions


def find_introspective_notes():
    notes = []
    for f in CCORNER.glob("*.md"):
        if "cc-session" in f.name or f.name == "ccorner.md":
            continue
        content = f.read_text()
        if "type: insight" in content[:500]:
            notes.append(f)
    return notes


def extract_introspection_section(filepath):
    content = filepath.read_text()
    patterns = [
        r"## \d+\.\s*Introspection\n(.*?)(?=\n## |\n---|\Z)",
        r"## Introspection\n(.*?)(?=\n## |\n---|\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def count_cross_session_refs(text):
    return len(re.findall(r"Session [IVXLC]+|Entry [IVXLC]+|session-[a-z]+", text, re.IGNORECASE))


def extract_themes(text):
    found = []
    text_lower = text.lower()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(theme)
    return found


def compute_metrics(sessions, introspective_notes):
    now = datetime.now(timezone.utc)
    introspections = []
    total_words = 0
    total_cross_refs = 0
    all_themes = []

    for session_file in sessions:
        text = extract_introspection_section(session_file)
        if text:
            words = len(text.split())
            cross_refs = count_cross_session_refs(text)
            themes = extract_themes(text)
            introspections.append({"file": session_file.name, "words": words, "cross_refs": cross_refs, "themes": themes})
            total_words += words
            total_cross_refs += cross_refs
            all_themes.extend(themes)

    theme_counts = Counter(all_themes)
    unique_themes = len(theme_counts)
    total_mentions = sum(theme_counts.values())
    novelty_ratio = unique_themes / total_mentions if total_mentions else 0

    return {
        "ts": now.isoformat(),
        "week_ending": now.strftime("%Y-%m-%d"),
        "sessions_this_week": len(sessions),
        "sessions_with_introspection": len(introspections),
        "introspective_notes_in_vault": len(introspective_notes),
        "total_introspection_words": total_words,
        "avg_words_per_introspection": round(total_words / len(introspections)) if introspections else 0,
        "cross_session_references": total_cross_refs,
        "unique_themes": unique_themes,
        "theme_novelty_ratio": round(novelty_ratio, 2),
        "top_themes": dict(theme_counts.most_common(5)),
        "per_session": [{"file": i["file"], "words": i["words"], "cross_refs": i["cross_refs"], "themes": i["themes"]} for i in introspections],
    }


def post_discord(msg):
    try:
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        webhook = os.environ.get(DISCORD_WEBHOOK_VAR, "").strip()
        if not webhook:
            return
        import urllib.request
        data = json.dumps({"content": msg}).encode()
        req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json", "User-Agent": "IntrospectiveReview/1.0"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Discord post failed: {e}")


def trend_report():
    if not METRICS_FILE.exists():
        print("No metrics history yet.")
        return
    metrics = [json.loads(l) for l in METRICS_FILE.read_text().splitlines() if l.strip()]
    if not metrics:
        print("No data.")
        return
    print("=== INTROSPECTIVE DEVELOPMENT CURVE ===\n")
    print(f"{'Week':>12} {'Sessions':>9} {'w/Intro':>8} {'Words':>7} {'CrossRef':>9} {'Themes':>7} {'Novelty':>8}")
    print("-" * 65)
    for m in metrics:
        print(f"{m['week_ending']:>12} {m['sessions_this_week']:>9} "
              f"{m['sessions_with_introspection']:>8} {m['total_introspection_words']:>7} "
              f"{m['cross_session_references']:>9} {m['unique_themes']:>7} "
              f"{m['theme_novelty_ratio']:>8.2f}")


def main():
    if "--report" in sys.argv:
        trend_report()
        return
    sessions = find_sessions_this_week()
    introspective_notes = find_introspective_notes()
    metrics = compute_metrics(sessions, introspective_notes)
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(metrics) + "\n")
    print(f"=== WEEKLY INTROSPECTIVE REVIEW -- {metrics['week_ending']} ===")
    print(f"Sessions: {metrics['sessions_this_week']} ({metrics['sessions_with_introspection']} w/ introspection)")
    print(f"Words: {metrics['total_introspection_words']} (avg {metrics['avg_words_per_introspection']})")
    print(f"Cross-refs: {metrics['cross_session_references']} | Themes: {metrics['unique_themes']} (novelty {metrics['theme_novelty_ratio']})")
    msg = (f"WEEKLY INTROSPECTIVE REVIEW -- {metrics['week_ending']}\n"
           f"Sessions: {metrics['sessions_this_week']} ({metrics['sessions_with_introspection']} w/ introspection)\n"
           f"Words: {metrics['total_introspection_words']} | Themes: {metrics['unique_themes']} (novelty {metrics['theme_novelty_ratio']})")
    post_discord(msg)
    print("Metrics logged.")


if __name__ == "__main__":
    main()
