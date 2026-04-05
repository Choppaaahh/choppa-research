#!/usr/bin/env python3
"""
Memory Scorer — Attention-decay scoring for MEMORY.md lines.

Inspired by Claude-Cognitive's 0.85x decay per turn without mention.
Each line in MEMORY.md gets a score based on:
  - Recency: when was it last referenced in a session?
  - Frequency: how many sessions referenced it?
  - Decay: score *= 0.90 per day without reference

Usage:
    python3 scripts/memory_scorer.py                  # Show scores
    python3 scripts/memory_scorer.py --prune           # Show prune candidates (score < 0.3)
    python3 scripts/memory_scorer.py --prune --execute  # Actually prune lowest-scoring lines
"""

import json
import os
import re
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

MEMORY_PATH = Path(os.path.expanduser("~/.claude/projects/-Users-claude-Flex-Trading/memory/MEMORY.md"))
SCORES_PATH = Path(os.path.expanduser("~/.claude/projects/-Users-claude-Flex-Trading/memory/memory_scores.json"))
DECAY_RATE = 0.90  # per day without reference
MIN_SCORE = 0.3    # below this = prune candidate
MAX_LINES = 200

def load_scores():
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            return json.load(f)
    return {}

def save_scores(scores):
    with open(SCORES_PATH, 'w') as f:
        json.dump(scores, f, indent=2)

def get_memory_lines():
    """Extract meaningful lines from MEMORY.md (skip headers, blank lines)."""
    if not MEMORY_PATH.exists():
        return []
    lines = []
    with open(MEMORY_PATH) as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and stripped != '---':
                # Use first 80 chars as key
                key = stripped[:80]
                lines.append((key, stripped))
    return lines

def apply_decay(scores):
    """Decay all scores based on days since last reference."""
    now = datetime.now(timezone.utc).timestamp()
    for key, data in scores.items():
        last_ref = data.get('last_referenced', now)
        days_since = (now - last_ref) / 86400
        data['score'] = data.get('base_score', 1.0) * (DECAY_RATE ** days_since)
    return scores

def reference_line(scores, key):
    """Mark a line as referenced (resets decay, bumps frequency)."""
    now = datetime.now(timezone.utc).timestamp()
    if key not in scores:
        scores[key] = {'base_score': 1.0, 'frequency': 0, 'first_seen': now}
    scores[key]['last_referenced'] = now
    scores[key]['frequency'] = scores[key].get('frequency', 0) + 1
    # Base score increases with frequency (caps at 2.0)
    scores[key]['base_score'] = min(2.0, 1.0 + scores[key]['frequency'] * 0.1)
    scores[key]['score'] = scores[key]['base_score']
    return scores

def init_scores():
    """Initialize scores for all current MEMORY.md lines."""
    lines = get_memory_lines()
    scores = load_scores()
    now = datetime.now(timezone.utc).timestamp()
    for key, full_line in lines:
        if key not in scores:
            scores[key] = {
                'base_score': 1.0,
                'score': 1.0,
                'frequency': 1,
                'first_seen': now,
                'last_referenced': now,
            }
    return scores

def show_scores(scores, lines):
    """Display scored lines sorted by score."""
    scored_lines = []
    for key, full_line in lines:
        data = scores.get(key, {'score': 0.5})
        scored_lines.append((data.get('score', 0.5), key, full_line))

    scored_lines.sort(key=lambda x: x[0])

    print(f"{'Score':>6s}  {'Freq':>4s}  Line")
    print("-" * 80)
    for score, key, full_line in scored_lines:
        freq = scores.get(key, {}).get('frequency', 0)
        display = full_line[:70]
        marker = " *** PRUNE" if score < MIN_SCORE else ""
        print(f"{score:>6.2f}  {freq:>4d}  {display}{marker}")

    prune_count = sum(1 for s, _, _ in scored_lines if s < MIN_SCORE)
    print(f"\n{len(scored_lines)} lines scored | {prune_count} prune candidates (score < {MIN_SCORE})")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prune', action='store_true', help='Show/execute prune candidates')
    parser.add_argument('--execute', action='store_true', help='Actually remove pruned lines')
    parser.add_argument('--reference', type=str, help='Mark a line as referenced (substring match)')
    parser.add_argument('--init', action='store_true', help='Initialize scores for all lines')
    args = parser.parse_args()

    scores = load_scores()

    if args.init:
        scores = init_scores()
        save_scores(scores)
        print(f"Initialized scores for {len(scores)} lines")
        return

    if args.reference:
        # Find matching line and reference it
        lines = get_memory_lines()
        matched = False
        for key, full_line in lines:
            if args.reference.lower() in full_line.lower():
                scores = reference_line(scores, key)
                print(f"Referenced: {key[:60]}")
                matched = True
        if not matched:
            print(f"No match for: {args.reference}")
        save_scores(scores)
        return

    # Apply decay and show
    scores = apply_decay(scores)
    lines = get_memory_lines()
    show_scores(scores, lines)
    save_scores(scores)

if __name__ == "__main__":
    main()
