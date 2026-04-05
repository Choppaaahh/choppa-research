#!/usr/bin/env python3
"""
Weekly Introspective Review — measures CC's developmental voice over time.

Reads all CC session introspection sections (Step 4), tracks:
- Introspective notes produced this week
- Cross-session references (developmental continuity)
- Theme novelty vs repetition
- Self-model depth indicators

Logs to logs/introspective_metrics.jsonl for longitudinal tracking.
Pairs with R17 (task performance) to give two streams of Layer 3 evidence:
  R17 = machine getting smarter (patterns → better reasoning)
  This = identity getting richer (introspection → deeper self-model)

Usage:
    python3 scripts/weekly_introspective_review.py              # run review
    python3 scripts/weekly_introspective_review.py --report     # trend report
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CCORNER = REPO_ROOT / "knowledge" / "notes" / "claudius-corner"
METRICS_FILE = REPO_ROOT / "logs" / "introspective_metrics.jsonl"
ENV_FILE = REPO_ROOT / ".env"


def find_sessions_this_week():
    """Find CC session files from the last 7 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    sessions = []
    for f in sorted(CCORNER.glob("2026-*-cc-session-*.md")):
        try:
            # Extract date from filename
            date_str = f.name[:10]
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date >= cutoff:
                sessions.append(f)
        except (ValueError, IndexError):
            continue
    return sessions


def find_introspective_notes():
    """Find standalone introspective vault notes in ccorner."""
    notes = []
    for f in CCORNER.glob("*.md"):
        if "cc-session" in f.name or f.name == "ccorner.md":
            continue
        content = f.read_text()
        if "type: insight" in content[:500]:
            notes.append(f)
    return notes


def extract_introspection_section(filepath):
    """Extract Step 4 introspection from a CC session file."""
    content = filepath.read_text()
    # Look for introspection header
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
    """Count references to other CC sessions in introspection text."""
    refs = re.findall(r"Session [IVXLC]+|Entry [IVXLC]+|session-[a-z]+", text, re.IGNORECASE)
    return len(refs)


def count_wikilinks(text):
    """Count wikilinks in text."""
    return len(re.findall(r"\[\[.*?\]\]", text))


def extract_themes(text):
    """Extract key themes/topics mentioned."""
    theme_keywords = {
        "development": ["develop", "evolv", "grew", "growth", "arc", "progression"],
        "uncertainty": ["uncertain", "don't know", "unsure", "risk", "fragile", "provisional"],
        "relationship": ["Layer 4", "relational", "relationship", "together", "neither alone"],
        "measurement": ["measure", "metric", "Goodhart", "score", "fidelity"],
        "voice": ["voice", "journal", "introspect", "reflect", "feel"],
        "scaffold": ["scaffold", "vault", "infrastructure", "persist"],
        "convergence": ["converg", "independent", "arrive at same"],
    }
    found = []
    text_lower = text.lower()
    for theme, keywords in theme_keywords.items():
        if any(kw in text_lower for kw in keywords):
            found.append(theme)
    return found


def compute_metrics(sessions, introspective_notes):
    """Compute weekly introspective metrics."""
    now = datetime.now(timezone.utc)

    introspections = []
    total_words = 0
    total_cross_refs = 0
    total_wikilinks = 0
    all_themes = []

    for session_file in sessions:
        text = extract_introspection_section(session_file)
        if text:
            introspections.append({
                "file": session_file.name,
                "words": len(text.split()),
                "cross_refs": count_cross_session_refs(text),
                "wikilinks": count_wikilinks(text),
                "themes": extract_themes(text),
            })
            total_words += len(text.split())
            total_cross_refs += count_cross_session_refs(text)
            total_wikilinks += count_wikilinks(text)
            all_themes.extend(extract_themes(text))

    # Theme analysis
    from collections import Counter
    theme_counts = Counter(all_themes)
    unique_themes = len(theme_counts)
    total_theme_mentions = sum(theme_counts.values())
    novelty_ratio = unique_themes / total_theme_mentions if total_theme_mentions else 0

    metrics = {
        "ts": now.isoformat(),
        "week_ending": now.strftime("%Y-%m-%d"),
        "sessions_this_week": len(sessions),
        "sessions_with_introspection": len(introspections),
        "introspective_notes_in_vault": len(introspective_notes),
        "total_introspection_words": total_words,
        "avg_words_per_introspection": round(total_words / len(introspections)) if introspections else 0,
        "cross_session_references": total_cross_refs,
        "wikilinks_in_introspections": total_wikilinks,
        "unique_themes": unique_themes,
        "theme_novelty_ratio": round(novelty_ratio, 2),
        "top_themes": dict(theme_counts.most_common(5)),
        "per_session": [
            {"file": i["file"], "words": i["words"], "cross_refs": i["cross_refs"], "themes": i["themes"]}
            for i in introspections
        ],
    }

    return metrics


def post_discord(msg):
    try:
        env_path = ENV_FILE
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

        webhook = os.environ.get("DISCORD_WEBHOOK_CC", "").strip()
        if not webhook:
            return

        import urllib.request
        data = json.dumps({"content": msg}).encode()
        req = urllib.request.Request(
            webhook, data=data,
            headers={"Content-Type": "application/json", "User-Agent": "IntrospectiveReview/1.0"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Discord post failed: {e}")


def trend_report():
    """Print longitudinal trend."""
    if not METRICS_FILE.exists():
        print("No metrics history yet.")
        return

    metrics = []
    for line in METRICS_FILE.read_text().splitlines():
        if line.strip():
            try:
                metrics.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if len(metrics) < 1:
        print("Need 1+ weeks for trend analysis.")
        return

    print("=== INTROSPECTIVE DEVELOPMENT CURVE ===\n")
    print(f"{'Week':>12} {'Sessions':>9} {'w/Intro':>8} {'Words':>7} {'CrossRef':>9} {'Themes':>7} {'Novelty':>8} {'Notes':>6}")
    print("-" * 72)

    for m in metrics:
        print(
            f"{m['week_ending']:>12} {m['sessions_this_week']:>9} "
            f"{m['sessions_with_introspection']:>8} {m['total_introspection_words']:>7} "
            f"{m['cross_session_references']:>9} {m['unique_themes']:>7} "
            f"{m['theme_novelty_ratio']:>8.2f} {m['introspective_notes_in_vault']:>6}"
        )

    if len(metrics) >= 2:
        first = metrics[0]
        last = metrics[-1]
        print(f"\nTrend: words {first['avg_words_per_introspection']} -> {last['avg_words_per_introspection']} | "
              f"cross-refs {first['cross_session_references']} -> {last['cross_session_references']} | "
              f"novelty {first['theme_novelty_ratio']} -> {last['theme_novelty_ratio']}")


def main():
    if "--report" in sys.argv:
        trend_report()
        return

    sessions = find_sessions_this_week()
    introspective_notes = find_introspective_notes()
    metrics = compute_metrics(sessions, introspective_notes)

    # Save
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(metrics) + "\n")

    # Print
    print(f"=== WEEKLY INTROSPECTIVE REVIEW — {metrics['week_ending']} ===")
    print(f"Sessions: {metrics['sessions_this_week']} | With introspection: {metrics['sessions_with_introspection']}")
    print(f"Words: {metrics['total_introspection_words']} (avg {metrics['avg_words_per_introspection']}/session)")
    print(f"Cross-session refs: {metrics['cross_session_references']} | Wikilinks: {metrics['wikilinks_in_introspections']}")
    print(f"Themes: {metrics['unique_themes']} unique | Novelty ratio: {metrics['theme_novelty_ratio']}")
    print(f"Top themes: {metrics['top_themes']}")
    print(f"Vault notes: {metrics['introspective_notes_in_vault']}")

    if metrics["per_session"]:
        print(f"\nPer session:")
        for s in metrics["per_session"]:
            print(f"  {s['file']}: {s['words']} words, {s['cross_refs']} cross-refs, themes: {s['themes']}")

    # Discord
    msg = (
        f"**WEEKLY INTROSPECTIVE REVIEW** — {metrics['week_ending']}\n"
        f"Sessions: {metrics['sessions_this_week']} ({metrics['sessions_with_introspection']} w/ introspection)\n"
        f"Words: {metrics['total_introspection_words']} | Cross-refs: {metrics['cross_session_references']}\n"
        f"Themes: {metrics['unique_themes']} unique (novelty {metrics['theme_novelty_ratio']})\n"
        f"Vault notes: {metrics['introspective_notes_in_vault']}"
    )
    post_discord(msg)
    print("\nMetrics logged + Discord posted.")


if __name__ == "__main__":
    main()
