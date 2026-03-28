#!/usr/bin/env python3
"""
Multi-Rate Confidence Decay — score vault notes with class-aware decay.

Not all knowledge decays at the same rate:
  FOUNDATIONAL (∞):  insights, lessons — timeless, never decays
  STRUCTURAL (90d):  mechanisms, procedures, decisions — slow decay
  EPHEMERAL (14d):   bugs, sessions, parameters — fast decay, config/state
  DEFAULT (30d):     everything else

Score = ref_weight × ref_score + decay_weight × decay_factor
  Weights vary by class: foundational = 50/50, ephemeral = 20/80 (freshness dominates)

Syncs scores + decay_class to SQLite for QMD ranked search integration.

Usage:
    python3 confidence_decay.py                    # show all notes ranked
    python3 confidence_decay.py --by-class         # breakdown by decay class
    python3 confidence_decay.py --stale            # notes below 0.3
    python3 confidence_decay.py --sync-db          # sync to vault_index.db

Customize VAULT path, DECAY_CLASSES mapping, and SKIP_STEMS for your project.
"""

import argparse
import math
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

# ─── CUSTOMIZE THESE ─────────────────────────────────────────────────────────
VAULT = Path(__file__).parent.parent / "knowledge" / "notes"  # adjust to your vault
DB_PATH = Path(__file__).parent.parent / "data" / "vault_index.db"

# Map note types to decay classes + half-lives (days)
# None = infinite (no decay)
DECAY_CLASSES = {
    "insight": ("foundational", None),
    "lesson": ("foundational", None),
    "mechanism": ("structural", 90),
    "procedure": ("structural", 90),
    "decision": ("structural", 90),
    "bug": ("ephemeral", 14),
    "session": ("ephemeral", 14),
    "parameter": ("ephemeral", 14),
}
DEFAULT_CLASS = ("default", 30)

# MOCs/indexes to skip (they're navigation, not knowledge)
SKIP_STEMS = {"index", "dashboard", "navigation"}
# ─────────────────────────────────────────────────────────────────────────────


def parse_frontmatter(path):
    try:
        text = path.read_text()
        if not text.startswith('---'):
            return {}
        end = text.index('---', 3)
        fm = {}
        for line in text[3:end].strip().split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                fm[key.strip()] = val.strip().strip('"').strip("'")
        return fm
    except Exception:
        return {}


def get_decay_class(note_type):
    return DECAY_CLASSES.get(note_type, DEFAULT_CLASS)


def count_incoming_links():
    link_counts = Counter()
    for note in VAULT.rglob("*.md"):
        try:
            content = note.read_text()
            for link in re.findall(r"\[\[([^\]|]+)", content):
                link_counts[link.strip()] += 1
        except Exception:
            continue
    return link_counts


def calculate_confidence(note_path, link_counts, now):
    stem = note_path.stem
    if stem in SKIP_STEMS:
        return None

    fm = parse_frontmatter(note_path)
    mtime = os.path.getmtime(note_path)
    note_type = fm.get('type', 'default')
    decay_class, half_life = get_decay_class(note_type)

    # Last validated from frontmatter or file mtime
    lv_str = fm.get('last_validated', fm.get('date_learned', ''))
    try:
        last_validated = datetime.fromisoformat(lv_str.split('T')[0]).timestamp() if lv_str else mtime
    except Exception:
        last_validated = mtime

    freshest = max(last_validated, mtime)
    age_s = now - freshest

    # Multi-rate decay
    if half_life is None:
        decay = 0.95 + 0.05 * math.exp(-age_s / (365 * 86400))
    else:
        decay = math.exp(-(math.log(2) / (half_life * 86400)) * age_s)

    return {
        'path': str(note_path.relative_to(VAULT)),
        'stem': stem,
        'type': note_type,
        'decay_class': decay_class,
        'half_life': half_life,
        'refs': link_counts.get(stem, 0),
        'age_days': age_s / 86400,
        'decay': decay,
    }


def compute_scores(notes, max_refs):
    for n in notes:
        ref_score = min(n['refs'] / max(max_refs * 0.3, 1), 1.0)
        weights = {
            'foundational': (0.5, 0.5),
            'structural': (0.4, 0.6),
            'ephemeral': (0.2, 0.8),
            'default': (0.4, 0.6),
        }
        rw, dw = weights.get(n['decay_class'], (0.4, 0.6))
        n['confidence'] = round(ref_score * rw + n['decay'] * dw, 3)
    return notes


def sync_to_db(notes):
    import sqlite3
    if not DB_PATH.exists():
        print(f"No database found at {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for col, ctype, default in [("confidence", "REAL", "0.5"), ("decay_class", "TEXT", "'default'"), ("half_life_days", "INTEGER", "30")]:
        try:
            cur.execute(f"ALTER TABLE vault_nodes ADD COLUMN {col} {ctype} DEFAULT {default}")
        except sqlite3.OperationalError:
            pass
    updated = 0
    for n in notes:
        cur.execute("UPDATE vault_nodes SET confidence=?, decay_class=?, half_life_days=? WHERE filepath LIKE ?",
                    (n['confidence'], n['decay_class'], n['half_life'], f"%{n['stem']}%"))
        if cur.rowcount > 0:
            updated += 1
    conn.commit()
    conn.close()
    print(f"Synced {updated}/{len(notes)} scores to database")


def main():
    parser = argparse.ArgumentParser(description='Multi-rate confidence decay')
    parser.add_argument('--stale', action='store_true')
    parser.add_argument('--top', type=int, default=0)
    parser.add_argument('--bottom', type=int, default=0)
    parser.add_argument('--by-class', action='store_true')
    parser.add_argument('--sync-db', action='store_true')
    args = parser.parse_args()

    now = time.time()
    link_counts = count_incoming_links()
    max_refs = max(link_counts.values()) if link_counts else 1

    notes = [r for r in (calculate_confidence(p, link_counts, now) for p in VAULT.rglob("*.md")) if r]
    notes = compute_scores(notes, max_refs)
    notes.sort(key=lambda x: -x['confidence'])

    if args.by_class:
        for cls in ['foundational', 'structural', 'ephemeral', 'default']:
            cn = [n for n in notes if n['decay_class'] == cls]
            hl = cn[0]['half_life'] if cn else '?'
            avg = sum(n['confidence'] for n in cn) / len(cn) if cn else 0
            stale = sum(1 for n in cn if n['confidence'] < 0.3)
            print(f"\n{cls.upper()} (half-life: {hl or '∞'}d) — {len(cn)} notes, avg {avg:.3f}, {stale} stale")
            for n in cn[:5]:
                print(f"  {n['confidence']:.3f} | {n['age_days']:>4.0f}d | {n['refs']:>3} refs | {n['stem'][:50]}")
    elif args.stale:
        stale = [n for n in notes if n['confidence'] < 0.3]
        print(f"STALE (<0.3): {len(stale)}")
        for n in stale[:20]:
            print(f"  {n['confidence']:.3f} | [{n['decay_class']}] {n['stem']}")
    else:
        print(f"VAULT CONFIDENCE ({len(notes)} notes)")
        for n in notes[:args.top or 15]:
            print(f"  {n['confidence']:.3f} | {n['age_days']:>4.0f}d | [{n['decay_class']:<12}] {n['stem']}")
        print(f"\n  Avg: {sum(n['confidence'] for n in notes)/len(notes):.3f} | Stale: {sum(1 for n in notes if n['confidence']<0.3)} | Fresh: {sum(1 for n in notes if n['confidence']>0.7)}")

    if args.sync_db:
        sync_to_db(notes)


if __name__ == "__main__":
    main()
