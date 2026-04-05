#!/usr/bin/env python3
"""
Confidence Decay — Multi-rate decay with query-aware QMD ranking.

Each note gets a confidence score (0-1) based on:
  - decay_class: foundational (∞), structural (90d), ephemeral (14d), default (30d)
  - reference_count: how many other notes link to it
  - last_modified: when was the file last touched

Decay classes (from note type):
  FOUNDATIONAL (∞):  insight, lesson — timeless knowledge, never decays
  STRUCTURAL (90d):  mechanism, procedure, decision — slow decay
  EPHEMERAL (14d):   bug, session, parameter — fast decay, config/state
  DEFAULT (30d):     moc, framework, etc.

QMD ranking integration:
  Scores synced to vault_index.db with decay_class column.
  QMD applies adaptive α based on query type + note class.

Usage:
    python3 scripts/confidence_decay.py                    # show all notes ranked
    python3 scripts/confidence_decay.py --stale            # show notes below 0.3
    python3 scripts/confidence_decay.py --sync-db          # sync to vault_index.db
    python3 scripts/confidence_decay.py --top 20           # top 20
    python3 scripts/confidence_decay.py --bottom 20        # bottom 20
"""

import argparse
import json
import math
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent / "knowledge" / "notes"
ENTROPY_LOG = Path(__file__).resolve().parent.parent / "logs" / "scaffold_entropy.jsonl"

# ─── Multi-rate decay classes ────────────────────────────────────────────────

DECAY_CLASSES = {
    # Note type → (decay_class, half_life_days)
    "insight": ("foundational", None),      # never decays
    "lesson": ("foundational", None),
    "mechanism": ("structural", 90),
    "procedure": ("structural", 90),
    "decision": ("structural", 90),
    "bug": ("ephemeral", 14),
    "session": ("ephemeral", 14),
    "parameter": ("ephemeral", 14),
}

DEFAULT_CLASS = ("default", 30)

# Domain maps / MOCs to skip
SKIP_STEMS = {
    'index', 'grid-mechanics', 'fee-model', 'bug-patterns', 'coin-evaluation',
    'safety-systems', 'microstructure-signals', 'regime-detection',
    'operational-procedures', 'lessons-learned', 'build-roadmap',
    'consciousness-trading', 'wallet-research', 'momoscalp', 'ccorner',
    'scheduled-reports', 'research-trading', 'geopol', 'colby', 'choppa',
    'navigation', 'dashboard', 'session-log', 'agent-coordination',
    'market-sessions', 'cc-operational',
}


# ─── Friction measurement from reasoning chains ─────────────────────────────

def _get_latest_entropy():
    """Read latest entropy score from scaffold_entropy.jsonl.

    Returns float 0-1. Falls back to 0.5 if file missing, empty, or stale (>1hr).
    """
    try:
        if not ENTROPY_LOG.exists():
            return 0.5
        lines = ENTROPY_LOG.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        if not lines:
            return 0.5
        last = json.loads(lines[-1])
        score = float(last.get("entropy", last.get("score", 0.5)))
        # Check staleness — if ts exists and is >1hr old, fallback
        ts_str = last.get("ts", "")
        if ts_str:
            try:
                entry_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_s = (datetime.now(entry_time.tzinfo) - entry_time).total_seconds()
                if age_s > 3600:
                    return 0.5
            except Exception:
                pass
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.5


_chain_friction_cache = None

def _get_chain_friction(note_stem):
    """Get reasoning chain depth ("friction") for a note.

    Chains that produced or reference this pattern have a step count
    (number of → in the chain field). More steps = deeper reasoning =
    higher friction = slower decay.

    Cached on first call — chains file read once per run.
    """
    global _chain_friction_cache
    if _chain_friction_cache is None:
        _chain_friction_cache = {}
        chains_file = Path(__file__).resolve().parent.parent / "logs" / "reasoning_chains.jsonl"
        if chains_file.exists():
            try:
                for line in chains_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not line.strip():
                        continue
                    try:
                        chain = json.loads(line)
                        pattern = chain.get("pattern", "")
                        chain_text = chain.get("chain", "")
                        if pattern and chain_text:
                            # Count steps (→ separators) as friction measure
                            steps = chain_text.count("→") + 1
                            # Keep max friction per pattern
                            norm = pattern.lower().replace("_", "-").replace(" ", "-")
                            _chain_friction_cache[norm] = max(
                                _chain_friction_cache.get(norm, 0), steps
                            )
                    except (json.JSONDecodeError, ValueError):
                        continue
            except Exception:
                pass

    norm_stem = note_stem.lower().replace("pattern-", "").replace("_", "-")
    return _chain_friction_cache.get(norm_stem, 0)


_retrieval_count_cache = None

def _get_retrieval_count(note_stem):
    """Get QMD retrieval count for a note.

    Reads logs/qmd_retrievals.jsonl (logged by QMD search calls).
    Each entry: {"ts": "...", "query": "...", "results": ["note_stem", ...]}
    Count how many times this note appeared in search results.
    """
    global _retrieval_count_cache
    if _retrieval_count_cache is None:
        _retrieval_count_cache = Counter()
        retrieval_file = Path(__file__).resolve().parent.parent / "logs" / "qmd_retrievals.jsonl"
        if retrieval_file.exists():
            try:
                for line in retrieval_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        for result in entry.get("results", []):
                            norm = result.lower().replace("_", "-").replace(" ", "-")
                            _retrieval_count_cache[norm] += 1
                    except (json.JSONDecodeError, ValueError):
                        continue
            except Exception:
                pass

    norm_stem = note_stem.lower().replace("pattern-", "").replace("_", "-")
    return _retrieval_count_cache.get(norm_stem, 0)


def parse_frontmatter(path):
    """Extract YAML frontmatter fields."""
    try:
        text = path.read_text()
        if not text.startswith('---'):
            return {}
        end = text.index('---', 3)
        fm_text = text[3:end]
        fm = {}
        for line in fm_text.strip().split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                fm[key.strip()] = val.strip().strip('"').strip("'")
        return fm
    except Exception:
        return {}


def get_decay_class(note_type):
    """Map note type to decay class and half-life."""
    return DECAY_CLASSES.get(note_type, DEFAULT_CLASS)


def count_incoming_links():
    """Count how many notes link TO each note."""
    link_counts = Counter()
    for note in VAULT.rglob("*.md"):
        try:
            content = note.read_text()
            links = re.findall(r"\[\[([^\]|]+)", content)
            for link in links:
                link_counts[link.strip()] += 1
        except Exception:
            continue
    return link_counts


def calculate_confidence(note_path, link_counts, now, entropy_factor=1.0):
    """Calculate confidence score with multi-rate decay."""
    stem = note_path.stem
    if stem in SKIP_STEMS:
        return None

    fm = parse_frontmatter(note_path)
    mtime = os.path.getmtime(note_path)
    note_type = fm.get('type', 'default')

    # Determine decay class
    decay_class, half_life = get_decay_class(note_type)

    # Last validated: from frontmatter or fall back to mtime
    last_validated_str = fm.get('last_validated', fm.get('date_learned', ''))
    if last_validated_str:
        try:
            lv = datetime.fromisoformat(last_validated_str.split('T')[0])
            last_validated = lv.timestamp()
        except Exception:
            last_validated = mtime
    else:
        last_validated = mtime

    freshest = max(last_validated, mtime)
    age_s = now - freshest
    age_days = age_s / 86400

    refs = link_counts.get(stem, 0)

    # ─── FSRS-inspired dual-strength decay ──────────────────────────────────
    # Stability (S) = how slowly a note decays. Grows with references (access = review).
    # Retrievability (R) = current confidence = e^(-t/S).
    # Adapted from FSRS (Free Spaced Repetition Scheduler) DSR model.
    #
    # Key insight: frequently-referenced notes decay slower than isolated ones.
    # A heavily-linked ephemeral note can outrank a stale foundational note.

    # Base stability from note type (days), scaled by entropy factor
    if half_life is None:
        # Foundational — very high stability, still decays slightly
        base_stability = 365.0 * entropy_factor  # 1 year base
    else:
        base_stability = float(half_life) * entropy_factor  # 14d for ephemeral, 90d for structural

    # Stability grows with references (each ref = implicit "review")
    # FSRS uses S' = S * e^(w * (refs - 1)) where w is a growth factor
    # We use a simpler model: S = base * (1 + ref_boost * log(1 + refs))
    # Diminishing returns — 10 refs helps a lot, 100 refs helps a little more
    ref_boost = 0.3  # tunable: how much references extend stability
    stability = base_stability * (1 + ref_boost * math.log(1 + refs))

    # Friction boost: notes derived from deep reasoning chains decay slower.
    # "Friction" = chain depth (step count in the reasoning chain that produced this note).
    # High-friction chains required more verification/iteration = harder-earned knowledge.
    # Measured from reasoning_chains.jsonl: chains referencing this note's pattern.
    friction = _get_chain_friction(stem)
    if friction > 0:
        # Each step of friction adds ~10% stability. 5-step chain = 1.5x stability.
        stability *= (1 + 0.1 * friction)

    # Retrieval-count boost: notes accessed via QMD search get stability boost.
    # Usage-driven reinforcement (from HMO + Oblivion + TraceCoder convergence).
    # Each retrieval = implicit "this note is useful" signal.
    retrieval_count = _get_retrieval_count(stem)
    if retrieval_count > 0:
        # Diminishing returns: 5 retrievals = 1.48x, 20 = 1.90x, 100 = 2.38x
        stability *= (1 + 0.1 * math.log(1 + retrieval_count))

    # Retrievability = forgetting curve
    # R = e^(-t/S) where t = age in days, S = stability in days
    if stability > 0:
        retrievability = math.exp(-age_days / stability)
    else:
        retrievability = 0.0

    # Clamp to [0.01, 1.0] — nothing is perfectly confident or completely gone
    decay = max(0.01, min(1.0, retrievability))

    return {
        'path': str(note_path.relative_to(VAULT)),
        'stem': stem,
        'type': note_type,
        'decay_class': decay_class,
        'half_life': half_life,
        'stability_days': round(stability, 1),
        'refs': refs,
        'age_days': age_days,
        'decay': decay,
        'last_validated': datetime.fromtimestamp(freshest).strftime('%Y-%m-%d'),
        'summary': fm.get('summary', '')[:80],
    }


def main():
    parser = argparse.ArgumentParser(description='Confidence decay for vault notes')
    parser.add_argument('--stale', action='store_true', help='Show notes below 0.3 confidence')
    parser.add_argument('--top', type=int, default=0, help='Show top N highest confidence')
    parser.add_argument('--bottom', type=int, default=0, help='Show bottom N lowest confidence')
    parser.add_argument('--update', action='store_true', help='Update last_validated on recently modified notes')
    parser.add_argument('--sync-db', action='store_true', help='Write confidence scores to vault_index.db for QMD ranking')
    parser.add_argument('--by-class', action='store_true', help='Show breakdown by decay class')
    parser.add_argument('--adaptive', action='store_true', help='Scale half-lives by scaffold entropy (active=faster decay, idle=slower)')
    args = parser.parse_args()

    now = time.time()
    link_counts = count_incoming_links()
    max_refs = max(link_counts.values()) if link_counts else 1

    # Compute entropy-adaptive factor
    entropy_factor = 1.0
    if args.adaptive:
        entropy = _get_latest_entropy()
        entropy_factor = 1 + (1 - entropy) * 2  # range: 1.0 (active) to 3.0 (idle)
        print(f"[adaptive] entropy={entropy:.2f}  factor={entropy_factor:.2f}x half-life\n")

    notes = []
    for note_path in VAULT.rglob("*.md"):
        result = calculate_confidence(note_path, link_counts, now, entropy_factor=entropy_factor)
        if result:
            notes.append(result)

    # Final confidence: FSRS retrievability IS the confidence.
    # References are already baked into stability (refs boost stability → slower decay).
    # No separate ref_score blending needed — that would double-count references.
    for n in notes:
        n['confidence'] = round(n['decay'], 3)

    notes.sort(key=lambda x: -x['confidence'])

    if args.by_class:
        for cls in ['foundational', 'structural', 'ephemeral', 'default']:
            class_notes = [n for n in notes if n['decay_class'] == cls]
            half = class_notes[0]['half_life'] if class_notes else '?'
            avg = sum(n['confidence'] for n in class_notes) / len(class_notes) if class_notes else 0
            stale = sum(1 for n in class_notes if n['confidence'] < 0.3)
            print(f"\n=== {cls.upper()} (half-life: {half or '∞'}d) — {len(class_notes)} notes, avg {avg:.3f}, {stale} stale ===")
            for n in class_notes[:5]:
                print(f"  {n['confidence']:.3f} | {n['age_days']:>4.0f}d | {n['refs']:>3} refs | {n['stem'][:50]}")
            if len(class_notes) > 5:
                print(f"  ... {len(class_notes) - 5} more")
    elif args.stale:
        stale = [n for n in notes if n['confidence'] < 0.3]
        print(f"=== STALE NOTES (confidence < 0.3): {len(stale)} ===\n")
        for n in stale:
            print(f"  {n['confidence']:.3f} | {n['age_days']:.0f}d | {n['refs']} refs | [{n['decay_class']}] {n['stem']}")
    elif args.top:
        print(f"=== TOP {args.top} HIGHEST CONFIDENCE ===\n")
        for n in notes[:args.top]:
            print(f"  {n['confidence']:.3f} | {n['age_days']:.0f}d | {n['refs']} refs | [{n['decay_class']}] {n['stem']}")
    elif args.bottom:
        bottom = notes[-args.bottom:]
        bottom.reverse()
        print(f"=== BOTTOM {args.bottom} LOWEST CONFIDENCE ===\n")
        for n in bottom:
            print(f"  {n['confidence']:.3f} | {n['age_days']:.0f}d | {n['refs']} refs | [{n['decay_class']}] {n['stem']}")
    else:
        print(f"=== VAULT CONFIDENCE SCORES ({len(notes)} notes) ===\n")
        print(f"{'Score':>6} | {'Age':>5} | {'Refs':>4} | {'Class':<14} | Note")
        print("-" * 85)
        for n in notes[:30]:
            print(f"  {n['confidence']:.3f} | {n['age_days']:>4.0f}d | {n['refs']:>4} | {n['decay_class']:<14} | {n['stem']}")
        print(f"\n  ... {len(notes) - 30} more notes")
        print(f"\n  Avg confidence: {sum(n['confidence'] for n in notes)/len(notes):.3f}")
        print(f"  Stale (<0.3): {sum(1 for n in notes if n['confidence'] < 0.3)}")
        print(f"  Fresh (>0.7): {sum(1 for n in notes if n['confidence'] > 0.7)}")

    if args.sync_db:
        sync_to_db(notes)


def sync_to_db(notes):
    """Write confidence scores + decay_class to vault_index.db for QMD ranking."""
    import sqlite3
    db_path = Path(__file__).resolve().parent.parent / "data" / "vault_index.db"
    if not db_path.exists():
        print("No vault_index.db found — run index_vault.py first")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Add columns if they don't exist
    for col, col_type, default in [
        ("confidence", "REAL", "0.5"),
        ("decay_class", "TEXT", "'default'"),
        ("half_life_days", "INTEGER", "30"),
    ]:
        try:
            cur.execute(f"ALTER TABLE vault_nodes ADD COLUMN {col} {col_type} DEFAULT {default}")
            print(f"Added {col} column to vault_nodes")
        except sqlite3.OperationalError:
            pass

    # Update scores
    updated = 0
    for n in notes:
        cur.execute(
            "UPDATE vault_nodes SET confidence = ?, decay_class = ?, half_life_days = ? WHERE filepath LIKE ?",
            (n['confidence'], n['decay_class'], n['half_life'] or 365, f"%{n['stem']}%")
        )
        if cur.rowcount > 0:
            updated += 1

    conn.commit()
    conn.close()
    print(f"Synced {updated}/{len(notes)} scores + decay classes to vault_index.db")


if __name__ == "__main__":
    main()
