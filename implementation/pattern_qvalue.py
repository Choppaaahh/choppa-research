#!/usr/bin/env python3
"""
Pattern Q-Value Tracker — RL-based promotion thresholds for metacognitive compile.

Two reward channels:
  TRADING:  Trade P&L attributed to patterns active during entry reasoning.
  SCAFFOLD: Operational outcomes (bug catches, dead ends) from reasoning chains.

Q(pattern, context) = exponentially weighted mean of rewards.
Context = regime (trading) or operation_type (scaffold).

High-Q patterns promote faster. Low-Q patterns need more evidence or get demoted.
Regime-conditional: a pattern that works in CHOP but not TRENDING gets
promoted for CHOP reasoning only.

Usage:
    python3 scripts/pattern_qvalue.py                    # show all Q-values
    python3 scripts/pattern_qvalue.py --trading           # trading channel only
    python3 scripts/pattern_qvalue.py --scaffold          # scaffold channel only
    python3 scripts/pattern_qvalue.py --promote           # show promotion candidates
    python3 scripts/pattern_qvalue.py --regime CHOP       # Q-values for specific regime
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CHAINS_FILE = REPO_ROOT / "logs" / "reasoning_chains.jsonl"
TRADES_FILE = REPO_ROOT / "logs" / "orchestrator_dryrun_30s_clock.log"
PROMOTED_DIR = REPO_ROOT / "knowledge" / "notes" / "cc-operational"

# ─── Config ─────────────────────────────────────────────────────────────────

EWM_ALPHA = 0.3          # recent rewards weighted more
PROMOTE_Q = 0.5           # Q above this → promotion candidate
DEMOTE_Q = -0.3           # Q below this → demotion candidate
MIN_SAMPLES_PROMOTE = 2   # need at least 2 rewards to promote
MIN_SAMPLES_DEMOTE = 5    # need 5 to demote (conservative)

# Scaffold outcome → reward mapping
# Rebalanced 04/03: scaffold/research outcomes scored higher to prevent
# trading P&L from dominating Q-values. Architectural and cross-domain
# outcomes are the most valuable for augmented thinking in totality.
OUTCOME_REWARDS = {
    # High-impact scaffold outcomes (1.5-2.0x — architectural/structural changes)
    "architecture": 2.0, "redesign": 2.0, "phase transition": 2.0,
    "reframe": 1.8, "cross-domain": 1.8, "structural": 1.8,
    "autopoietic": 1.5, "novel approach": 1.5, "new pathway": 1.5,
    # Standard positive outcomes
    "bug": 1.0, "caught": 1.0, "fixed": 0.8, "found": 0.7,
    "promoted": 0.8, "validated": 0.6, "novel": 1.0, "shipped": 0.6,
    "insight": 0.8, "connection": 0.6, "convergent": 0.7,
    # Negative outcomes
    "dead end": -0.5, "failed": -0.7, "killed": -0.3,
    "false positive": -0.8, "wasted": -0.6, "noise": -0.4,
    # Neutral
    "insufficient": 0.0, "pending": 0.0,
}


def load_promoted_patterns():
    """Get list of currently promoted pattern names from vault."""
    patterns = set()
    for f in PROMOTED_DIR.glob("pattern-*.md"):
        # Extract pattern name from filename
        name = f.stem.replace("pattern-", "")
        patterns.add(name)
    return patterns


def score_outcome(outcome_text):
    """Score a reasoning chain outcome as a reward signal.

    Uses max-plus-bonus: highest matching keyword score + 0.1 per additional
    positive match. Prevents averaging from diluting high-impact outcomes.
    A chain with 'novel architecture' scores 2.0 + 0.1 = 2.1, not (2.0+1.0)/2 = 1.5.
    """
    if not outcome_text:
        return 0.0
    text = outcome_text.lower()
    matched = []
    for keyword, reward in OUTCOME_REWARDS.items():
        if keyword in text:
            matched.append(reward)
    if not matched:
        return 0.0
    # Max score + small bonus per additional positive match
    matched.sort(reverse=True)
    base = matched[0]
    bonus = sum(0.1 for r in matched[1:] if r > 0)
    return base + bonus


# ─── Cognitive Gating (from neuroscience, not a dependency) ──────────────────

def prediction_error(chain_text, existing_patterns):
    """Measure how NOVEL a chain is relative to existing promoted patterns.

    High PE = chain covers territory no existing pattern covers → prioritize.
    Low PE = chain is redundant with existing knowledge → deprioritize.

    Uses word overlap as a proxy for semantic similarity.
    """
    if not chain_text or not existing_patterns:
        return 1.0  # no patterns = everything is novel

    chain_words = set(chain_text.lower().split())
    if not chain_words:
        return 1.0

    # Compare against each existing pattern name (as word set)
    max_overlap = 0.0
    for pattern in existing_patterns:
        pattern_words = set(pattern.replace("-", " ").replace("_", " ").lower().split())
        if not pattern_words:
            continue
        overlap = len(chain_words & pattern_words) / max(len(chain_words | pattern_words), 1)
        max_overlap = max(max_overlap, overlap)

    # PE = 1 - max_overlap. Novel chains have low overlap = high PE.
    return round(1.0 - max_overlap, 3)


def synaptic_tag(prediction_err, reward):
    """Tag chains that are BOTH novel AND high-reward for fast-track consolidation.

    Neuroscience: strong experiences create molecular tags at synapses
    that say "consolidate this into long-term memory."

    For us: high PE + high reward = TAG → boosted Q-value → promotes faster.
    Low PE or low reward = no tag → normal Q-value processing.

    Returns a multiplier: 1.0 (no tag) to 2.0 (strong tag).
    """
    if prediction_err > 0.7 and reward > 0.5:
        # Novel AND high reward → strong tag (2x weight)
        return 2.0
    elif prediction_err > 0.5 and reward > 0.3:
        # Moderately novel AND positive → mild tag (1.5x)
        return 1.5
    elif prediction_err < 0.2:
        # Redundant → dampen (0.5x weight)
        return 0.5
    return 1.0  # no tag, normal weight


def ewm_mean(values, alpha=EWM_ALPHA):
    """Exponentially weighted mean — recent values count more."""
    if not values:
        return 0.0
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1 - alpha) * result
    return result


def load_scaffold_rewards():
    """Parse reasoning chains for scaffold-level pattern rewards.
    Applies prediction error gating + synaptic tagging from cognitive science."""
    pattern_rewards = defaultdict(list)  # pattern → [(context, reward)]
    promoted_patterns = load_promoted_patterns()

    if not CHAINS_FILE.exists():
        return pattern_rewards

    with open(CHAINS_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                chain = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

            pattern = chain.get("pattern", "")
            outcome = chain.get("outcome", "")
            if not pattern or not outcome:
                continue

            raw_reward = score_outcome(outcome)

            # Cognitive gating: prediction error + synaptic tagging
            chain_text = chain.get("chain", "") + " " + outcome
            pe = prediction_error(chain_text, promoted_patterns)
            tag = synaptic_tag(pe, raw_reward)
            reward = raw_reward * tag  # tagged chains get boosted/dampened

            # Context: use trigger type or "scaffold" as default
            trigger = chain.get("trigger", "scaffold")
            context = "scaffold"
            if "trade" in trigger.lower() or "regime" in trigger.lower():
                context = "trading"
            elif "bug" in trigger.lower() or "qa" in trigger.lower():
                context = "qa"
            elif "research" in trigger.lower() or "scout" in trigger.lower():
                context = "research"

            pattern_rewards[pattern].append({
                "context": context,
                "reward": reward,
                "outcome": outcome[:80],
            })

    return pattern_rewards


def load_trading_rewards():
    """Parse trade logs for trading-level pattern rewards.

    Reads the orchestrator log for trades with active_patterns field.
    Falls back to attributing trades to the regime they occurred in.
    """
    pattern_rewards = defaultdict(list)

    # Read ALL orchestrator logs (dry-run + live) and the patience journal
    # When active_patterns logging is added to orchestrator, parse those too
    log_files = sorted(REPO_ROOT.glob("logs/orchestrator_dryrun*.log"))
    journal = REPO_ROOT / "logs" / "patience_journal.jsonl"
    if journal.exists():
        log_files.append(journal)
    if not log_files:
        return pattern_rewards

    # Parse trade lines: "[17:26:14] CHOP MEAN EXIT: SHORT HYPE +41.1bp gross, +38.2bp net"
    trade_pattern = re.compile(
        r'(CHOP|PATIENCE) (MEAN|CUT|TRAIL|FLIP) (?:EXIT|CLOSE).*?([+-]\d+\.?\d*)bp net'
    )

    for log_file in log_files:
      with open(log_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            # Handle JSONL (patience_journal) and plain text (orchestrator logs)
            if line.strip().startswith("{"):
                try:
                    entry = json.loads(line)
                    if "pnl_bp" in entry:
                        pnl_bp = float(entry["pnl_bp"])
                        strategy = entry.get("strategy", "patience")
                        exit_type = entry.get("reason", "UNKNOWN")
                    else:
                        continue
                except (json.JSONDecodeError, ValueError):
                    continue
            else:
                m = trade_pattern.search(line)
                if not m:
                    continue
                strategy = m.group(1).lower()
                exit_type = m.group(2)
                pnl_bp = float(m.group(3))

            # Normalize reward: bp/100 so ±50bp = ±0.5 reward
            reward = pnl_bp / 100.0

            # Determine context from strategy
            context = "CHOP" if strategy == "chop" else "TRENDING"

            # Precise attribution: if JSONL trade has active_patterns, use those
            active = []
            if line.strip().startswith("{"):
                try:
                    active = json.loads(line).get("active_patterns", [])
                except (json.JSONDecodeError, ValueError):
                    pass
            if active:
                for pat in active:
                    pattern_rewards[pat].append({
                        "context": context,
                        "reward": reward,
                        "outcome": f"{exit_type} {pnl_bp:+.1f}bp",
                    })
            else:
                # Fallback: attribute to regime-level pattern
                pattern_rewards["entry-only-regime-gating"].append({
                    "context": context,
                    "reward": reward,
                    "outcome": f"{exit_type} {pnl_bp:+.1f}bp",
                })

    return pattern_rewards


def compute_q_values(rewards_by_pattern):
    """Compute Q(pattern, context) from accumulated rewards."""
    q_table = {}  # (pattern, context) → {q, n, rewards}

    for pattern, reward_list in rewards_by_pattern.items():
        # Group by context
        by_context = defaultdict(list)
        for r in reward_list:
            by_context[r["context"]].append(r["reward"])

        for context, rewards in by_context.items():
            q = ewm_mean(rewards)
            q_table[(pattern, context)] = {
                "q": round(q, 3),
                "n": len(rewards),
                "mean": round(sum(rewards) / len(rewards), 3),
                "latest": round(rewards[-1], 3) if rewards else 0,
            }

    return q_table


# ─── Phase Transition Detection ─────────────────────────────────────────────
# Two knowledge types: PATTERNS (branches, frequency-promoted at n>=3) vs
# PHASE TRANSITIONS (forks, impact-promoted at n=1 via downstream reorganization).
# A phase transition is a single chain that reorganized everything downstream.
# Detection: count new chains + vault notes in the 48hr window after a chain.

PHASE_TRANSITION_WINDOW_HRS = 48
PHASE_TRANSITION_MIN_INFLUENCE = 15  # need 15+ topically influenced downstream chains

def detect_phase_transitions():
    """Find n=1 chains that caused downstream reorganization.

    For each unique pattern that appears exactly once, measure how many new
    chains and vault notes appeared in the 48hrs after it. High downstream
    count = structural fork = phase transition candidate.
    """
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    if not CHAINS_FILE.exists():
        return []

    # Load all chains with timestamps
    chains = []
    with open(CHAINS_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                c = json.loads(line)
                ts_str = c.get("ts", "")
                if not ts_str:
                    continue
                # Parse ISO timestamp (handle both +00:00 and Z)
                ts_str = ts_str.replace("Z", "+00:00")
                if "+" not in ts_str and ts_str[-1] != "Z":
                    ts_str += "+00:00"
                try:
                    ts = datetime.fromisoformat(ts_str)
                except ValueError:
                    ts = datetime.fromisoformat(ts_str[:19] + "+00:00")
                chains.append({"ts": ts, "pattern": c.get("pattern", ""), "outcome": c.get("outcome", ""), "chain": c.get("chain", "")})
            except (json.JSONDecodeError, ValueError):
                continue

    if not chains:
        return []

    # Count occurrences per pattern
    pattern_counts = defaultdict(int)
    for c in chains:
        if c["pattern"]:
            pattern_counts[c["pattern"]] += 1

    # Get vault note creation dates (from file mtime)
    vault_notes = []
    vault_dir = REPO_ROOT / "knowledge" / "notes"
    if vault_dir.exists():
        for f in vault_dir.rglob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                vault_notes.append({"ts": mtime, "path": str(f.relative_to(REPO_ROOT))})
            except (OSError, ValueError):
                continue

    window = timedelta(hours=PHASE_TRANSITION_WINDOW_HRS)
    candidates = []

    for c in chains:
        pattern = c["pattern"]
        if not pattern or pattern_counts[pattern] > 1:
            continue  # only singletons

        chain_ts = c["ts"]
        window_end = chain_ts + window

        # Extract key concepts from this chain (words from pattern name + outcome)
        source_words = set(
            pattern.replace("-", " ").replace("_", " ").lower().split()
            + c["outcome"].lower().split()
        )
        # Filter stopwords
        stopwords = {"the", "a", "an", "is", "was", "to", "from", "for", "and",
                     "or", "but", "in", "on", "at", "by", "of", "with", "not",
                     "this", "that", "it", "we", "our", "be", "as", "has", "had",
                     "are", "were", "been", "its", "than", "into", "when", "new"}
        source_words = {w for w in source_words if len(w) > 3 and w not in stopwords}

        # Count downstream chains that share concepts (topical influence)
        influenced = 0
        for other in chains:
            if other["ts"] > chain_ts and other["ts"] <= window_end and other["pattern"] != pattern:
                other_words = set(
                    other["pattern"].replace("-", " ").replace("_", " ").lower().split()
                    + other.get("outcome", "").lower().split()
                )
                overlap = len(source_words & other_words)
                if overlap >= 2:  # at least 2 shared concept words
                    influenced += 1

        if influenced >= PHASE_TRANSITION_MIN_INFLUENCE:
            candidates.append({
                "pattern": pattern,
                "ts": chain_ts.isoformat(),
                "outcome": c["outcome"][:100],
                "influenced": influenced,
            })

    # Sort by topical influence
    candidates.sort(key=lambda x: -x["influenced"])
    return candidates


# ─── Maturity Tiers (stolen from ByteRover AKL, adapted) ─────────────────────

MATURITY_TIERS = {
    "CHAIN":     {"label": "🔵 CHAIN",     "desc": "n=1, just captured"},
    "PURGATORY": {"label": "🟡 PURGATORY", "desc": "n=2, seen again but not promoted"},
    "PROMOTED":  {"label": "🟢 PROMOTED",  "desc": "n>=3, in vault as pattern"},
    "STABLE":    {"label": "🟢 STABLE",    "desc": "n>=10 + Q>0.5, high confidence"},
    "STALE":     {"label": "🔴 STALE",     "desc": "promoted but Q declining or no recent rewards"},
}


def classify_tier(pattern_name, n_rewards, q_value, is_promoted, recent_reward_count=0):
    """Classify a pattern into a maturity tier.

    Lifecycle: CHAIN → PURGATORY → PROMOTED → STABLE → STALE
    Based on instance count, Q-value, promotion status, and recency.
    """
    if is_promoted:
        if n_rewards >= 10 and q_value > PROMOTE_Q:
            return "STABLE"
        elif recent_reward_count == 0 and q_value < 0.0:
            return "STALE"
        else:
            return "PROMOTED"
    else:
        if n_rewards >= 3:
            return "PURGATORY"  # enough instances but not yet promoted
        elif n_rewards == 2:
            return "PURGATORY"
        else:
            return "CHAIN"


def show_tiers(q_table, all_rewards, promoted):
    """Display patterns grouped by maturity tier."""
    tier_groups = defaultdict(list)

    for (pattern, context), vals in q_table.items():
        norm = pattern.lower().replace("_", "-").replace(" ", "-")
        is_promoted = norm in promoted or any(norm == p for p in promoted)
        tier = classify_tier(pattern, vals["n"], vals["q"], is_promoted)
        tier_groups[tier].append((pattern, context, vals, is_promoted))

    print(f"\n{'='*70}")
    print(f"PATTERN MATURITY TIERS (ByteRover AKL-inspired lifecycle)")
    print(f"{'='*70}\n")

    for tier_name in ["STABLE", "PROMOTED", "PURGATORY", "CHAIN", "STALE"]:
        info = MATURITY_TIERS[tier_name]
        patterns = tier_groups.get(tier_name, [])
        print(f"  {info['label']} — {info['desc']} ({len(patterns)} patterns)")
        for p, c, v, ip in sorted(patterns, key=lambda x: -x[2]["q"])[:10]:
            print(f"    Q={v['q']:+.3f} n={v['n']:2d} | {p}")
        if len(patterns) > 10:
            print(f"    ... and {len(patterns)-10} more")
        print()

    # Summary
    total = sum(len(v) for v in tier_groups.values())
    print(f"  Total: {total} patterns across {len(tier_groups)} tiers")
    for tier_name in ["STABLE", "PROMOTED", "PURGATORY", "CHAIN", "STALE"]:
        count = len(tier_groups.get(tier_name, []))
        print(f"    {tier_name}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Pattern Q-Value Tracker")
    parser.add_argument("--trading", action="store_true", help="Trading channel only")
    parser.add_argument("--scaffold", action="store_true", help="Scaffold channel only")
    parser.add_argument("--promote", action="store_true", help="Show promotion candidates")
    parser.add_argument("--phase", action="store_true", help="Detect phase transitions (n=1 forks)")
    parser.add_argument("--tiers", action="store_true", help="Show maturity tier breakdown")
    parser.add_argument("--regime", type=str, help="Filter by regime context")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.phase:
        candidates = detect_phase_transitions()
        print(f"\n{'='*70}")
        print(f"PHASE TRANSITION CANDIDATES — n=1 chains with downstream reorganization")
        print(f"Window: {PHASE_TRANSITION_WINDOW_HRS}hrs | Threshold: {PHASE_TRANSITION_MIN_INFLUENCE}+ topically influenced chains")
        print(f"{'='*70}\n")
        if not candidates:
            print("  No phase transitions detected.")
        for c in candidates:
            print(f"  [{c['ts'][:10]}] {c['pattern']}")
            print(f"    ↳ {c['influenced']} topically influenced downstream chains")
            print(f"    ↳ {c['outcome']}")
            print()
        print(f"  Total candidates: {len(candidates)}")
        return

    promoted = load_promoted_patterns()

    # Load both reward channels
    scaffold_rewards = load_scaffold_rewards()
    trading_rewards = load_trading_rewards()

    if args.tiers:
        all_r = defaultdict(list)
        for p, r in scaffold_rewards.items():
            all_r[p].extend(r)
        for p, r in trading_rewards.items():
            all_r[p].extend(r)
        qt = compute_q_values(all_r)
        show_tiers(qt, all_r, promoted)
        return

    # Merge
    all_rewards = defaultdict(list)
    if not args.trading:
        for p, r in scaffold_rewards.items():
            all_rewards[p].extend(r)
    if not args.scaffold:
        for p, r in trading_rewards.items():
            all_rewards[p].extend(r)

    q_table = compute_q_values(all_rewards)

    if args.json:
        output = {}
        for (pattern, context), vals in sorted(q_table.items()):
            key = f"{pattern}@{context}"
            output[key] = vals
        print(json.dumps(output, indent=2))
        return

    # Display
    print(f"\n{'='*70}")
    print(f"PATTERN Q-VALUES — {len(q_table)} entries from {len(all_rewards)} patterns")
    print(f"Promoted patterns in vault: {len(promoted)}")
    print(f"{'='*70}\n")

    # Sort by Q descending
    sorted_q = sorted(q_table.items(), key=lambda x: -x[1]["q"])

    if args.regime:
        sorted_q = [(k, v) for k, v in sorted_q if k[1] == args.regime]

    promote_candidates = []
    demote_candidates = []

    for (pattern, context), vals in sorted_q:
        q = vals["q"]
        n = vals["n"]
        # Exact match: normalize both to kebab-case for comparison
        norm = pattern.lower().replace("_", "-").replace(" ", "-")
        is_promoted = norm in promoted or any(norm == p for p in promoted)

        flag = ""
        if q > PROMOTE_Q and n >= MIN_SAMPLES_PROMOTE and not is_promoted:
            flag = " ← PROMOTE?"
            promote_candidates.append((pattern, context, vals))
        elif q < DEMOTE_Q and n >= MIN_SAMPLES_DEMOTE and is_promoted:
            flag = " ← DEMOTE?"
            demote_candidates.append((pattern, context, vals))

        if args.promote and not flag:
            continue

        status = "P" if is_promoted else " "
        print(f"  [{status}] Q={q:+.3f} n={n:2d} | {pattern:45s} @ {context}{flag}")

    if promote_candidates:
        print(f"\n  PROMOTION CANDIDATES: {len(promote_candidates)}")
        for p, c, v in promote_candidates:
            print(f"    {p} @ {c} — Q={v['q']:+.3f}, n={v['n']}")

    if demote_candidates:
        print(f"\n  DEMOTION CANDIDATES: {len(demote_candidates)}")
        for p, c, v in demote_candidates:
            print(f"    {p} @ {c} — Q={v['q']:+.3f}, n={v['n']}")

    # Summary
    total_rewards = sum(len(r) for r in all_rewards.values())
    print(f"\n  Total reward signals: {total_rewards}")
    print(f"  Scaffold: {sum(len(r) for r in scaffold_rewards.values())}")
    print(f"  Trading: {sum(len(r) for r in trading_rewards.values())}")


if __name__ == "__main__":
    main()
