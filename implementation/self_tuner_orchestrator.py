#!/usr/bin/env python3
"""
Self-Tuner Shadow Mode — Strategy Orchestrator

Fast/slow loop architecture for auto-tuning mean-reversion entry parameters.
Reads from a strategy journal (JSONL). Shadow mode only — logs proposals, does
not apply changes. Operator reviews proposals and applies manually.

Parameters tuned:
  - entry_threshold_default_bp: standard entry threshold (basis points from mean)
  - entry_threshold_volatile_bp: threshold for high-volatility instruments
  - confirmation_candles: number of confirming candles required before entry
  - alpha_trending_to_range: EMA smoothing coefficient for regime transitions
  - grind_threshold_bp: directional movement threshold for grind detection

Usage:
    python3 self_tuner_orchestrator.py
    python3 self_tuner_orchestrator.py --analyze
    python3 self_tuner_orchestrator.py --status

Configuration:
    Set STRATEGY_JOURNAL env var to point at your journal file.
    Set DISCORD_WEBHOOK env var for optional Discord notifications.
"""

import argparse
import json
import os
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
JOURNAL = Path(os.getenv("STRATEGY_JOURNAL", str(BASE / "logs" / "strategy_journal.jsonl")))
SHADOW_LOG = BASE / "logs" / "self_tuner_shadow.jsonl"
SHADOW_STATE = BASE / "data" / "self_tuner_state.json"

# Current live params — customize to your system's defaults
LIVE_PARAMS = {
    "entry_threshold_default_bp": 25,       # basis points from mean for standard instruments
    "entry_threshold_volatile_bp": 45,      # basis points from mean for high-volatility instruments
    "confirmation_candles": 2,              # candles required to confirm entry signal
    "confirmation_timeout_s": 150,          # max wait for confirmation (seconds)
    "alpha_trending_to_range": 0.03,        # EMA alpha: how fast to flip trending→range regime
    "grind_threshold_bp": 80,               # directional drift that triggers grind detection
    "grind_window_bars": 60,                # lookback window for grind detection (bars)
}

# Guardrails — hard limits the tuner will not exceed
GUARDRAILS = {
    "entry_threshold_default_bp": {"min": 15, "max": 50, "step": 5},
    "entry_threshold_volatile_bp": {"min": 25, "max": 100, "step": 5},
    "confirmation_candles": {"min": 1, "max": 4, "step": 1},
    "alpha_trending_to_range": {"min": 0.01, "max": 0.10, "step": 0.01},
}

FAST_WINDOW = 10   # trades per fast-loop evaluation
SLOW_WINDOW = 5    # fast-loop agreements needed to confirm a proposal
CONFIRM_THRESHOLD = 4


def post_notification(message):
    """Post to a Discord webhook (optional). Set DISCORD_WEBHOOK env var."""
    webhook = os.getenv("DISCORD_WEBHOOK")
    if not webhook:
        return
    try:
        subprocess.run([
            "curl", "-s", "-X", "POST", webhook,
            "-H", "Content-Type: application/json",
            "-H", "User-Agent: SelfTuner/1.0",
            "-d", json.dumps({"content": message})
        ], capture_output=True, timeout=10)
    except Exception:
        pass


def load_trades():
    """Load range-strategy entries/exits from the strategy journal."""
    trades = []
    if not JOURNAL.exists():
        return trades

    entries = {}  # instrument → entry event
    with open(JOURNAL) as f:
        for line in f:
            try:
                event = json.loads(line)
            except Exception:
                continue

            etype = event.get("type")
            instrument = event.get("instrument", event.get("coin", ""))

            if etype == "entry" and event.get("strategy") == "range":
                entries[instrument] = event
            elif etype == "trade" and instrument in entries:
                # "trade" events have pnl_bp; "exit" events often don't
                entry_event = entries.pop(instrument)
                pnl_bp = event.get("pnl_bp", 0)
                method = event.get("reason", "unknown")
                hold_s = 0
                try:
                    t1 = datetime.fromisoformat(entry_event["ts"].replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
                    hold_s = (t2 - t1).total_seconds()
                except Exception:
                    pass

                trades.append({
                    "instrument": instrument,
                    "pnl_bp": pnl_bp,
                    "hold_s": hold_s,
                    "method": method,
                    "peak_bp": event.get("peak_bp", 0),
                    "regime_at_exit": event.get("regime", "RANGE"),
                })

    return trades


def compute_diagnostics(trades, params):
    """
    Compute diagnostics for range-strategy round-trips.

    Flags raised:
      threshold_too_tight      — high cut rate (>40%) suggests entries on noise
      regime_flip_exits_high   — regime flips driving >50% of exits (alpha too high)
      volatile_threshold_too_tight — volatile-instrument cut rate >> others by >1.5x
    """
    if not trades:
        return {}

    n = len(trades)
    wins = sum(1 for t in trades if t["pnl_bp"] > 0)
    wr = wins / n if n else 0
    avg_pnl = sum(t["pnl_bp"] for t in trades) / n
    avg_hold = sum(t["hold_s"] for t in trades) / n

    by_method = defaultdict(int)
    for t in trades:
        by_method[t["method"]] += 1

    regime_flip_pct = by_method.get("regime_flip", 0) / n if n else 0
    mean_exit_pct = by_method.get("mean_exit", 0) / n if n else 0
    cut_pct = by_method.get("cut", 0) / n if n else 0

    flags = {}
    flags["threshold_too_tight"] = cut_pct > 0.40
    flags["regime_flip_exits_high"] = regime_flip_pct > 0.50

    # Volatile-instrument-specific check: tag instruments via journal field
    volatile_trades = [t for t in trades if t.get("is_volatile", False)]
    normal_trades = [t for t in trades if not t.get("is_volatile", False)]
    if volatile_trades and normal_trades:
        v_cut_rate = sum(1 for t in volatile_trades if t["pnl_bp"] < -100) / len(volatile_trades)
        n_cut_rate = sum(1 for t in normal_trades if t["pnl_bp"] < -100) / len(normal_trades)
        flags["volatile_threshold_too_tight"] = v_cut_rate > n_cut_rate * 1.5

    flags["_meta"] = {
        "n": n,
        "wr": round(wr, 3),
        "avg_pnl_bp": round(avg_pnl, 2),
        "avg_hold_s": round(avg_hold, 1),
        "regime_flip_pct": round(regime_flip_pct, 3),
        "mean_exit_pct": round(mean_exit_pct, 3),
        "cut_pct": round(cut_pct, 3),
    }

    return flags


def main():
    parser = argparse.ArgumentParser(description="Self-Tuner Shadow — Strategy Orchestrator")
    parser.add_argument("--analyze", action="store_true", help="Show proposals from shadow log")
    parser.add_argument("--status", action="store_true", help="Show current shadow state")
    args = parser.parse_args()

    if args.status:
        if SHADOW_STATE.exists():
            state = json.loads(SHADOW_STATE.read_text())
            print("Self-Tuner Status")
            print(f"  Trades processed: {state.get('total_trades_processed', 0)}")
            print(f"  Shadow params: {json.dumps(state.get('shadow_params', LIVE_PARAMS), indent=2)}")
        else:
            print("No state file yet. Run the tuner first.")
        return

    if args.analyze:
        if SHADOW_LOG.exists():
            entries = [json.loads(l) for l in SHADOW_LOG.read_text().splitlines() if l.strip()]
            proposals = [e for e in entries if e.get("type") == "proposal"]
            print("Self-Tuner Analysis")
            print(f"  Total entries: {len(entries)}")
            print(f"  Proposals: {len(proposals)}")
            for p in proposals:
                print(f"    {p.get('param','?')}: {p.get('old','?')} -> {p.get('new','?')}")
        else:
            print("No shadow log yet.")
        return

    print("Self-Tuner Shadow Mode")
    print(f"  Reading from: {JOURNAL}")
    print()

    trades = load_trades()
    if not trades:
        print("  No range-strategy trades found in journal.")
        print("  The strategy needs to log entry/exit events to JOURNAL.")
        post_notification("Self-Tuner: no range trades in journal. Collecting data.")
        return

    print(f"  Found {len(trades)} range round-trips")

    shadow_params = dict(LIVE_PARAMS)
    diags = compute_diagnostics(trades, shadow_params)
    meta = diags.get("_meta", {})
    flags = [k for k, v in diags.items() if v is True]

    print(f"  WR={meta.get('wr', 0):.0%} avg_pnl={meta.get('avg_pnl_bp', 0):+.1f}bp")
    print(f"  Regime flip exits: {meta.get('regime_flip_pct', 0):.0%}")
    print(f"  Mean exits:        {meta.get('mean_exit_pct', 0):.0%}")
    print(f"  Cut exits:         {meta.get('cut_pct', 0):.0%}")
    print(f"  Flags: {flags or 'none'}")

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": "analysis",
        "trades": len(trades),
        "diagnostics": diags,
        "shadow_params": shadow_params,
        "flags": flags,
    }
    with open(SHADOW_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    state = {
        "shadow_params": shadow_params,
        "live_params": LIVE_PARAMS,
        "total_trades_processed": len(trades),
    }
    SHADOW_STATE.parent.mkdir(parents=True, exist_ok=True)
    SHADOW_STATE.write_text(json.dumps(state, indent=2))

    msg = (
        f"Self-Tuner: {len(trades)} range trades analyzed | "
        f"WR: {meta.get('wr', 0):.0%} | "
        f"Avg P&L: {meta.get('avg_pnl_bp', 0):+.1f}bp | "
        f"Flags: {', '.join(flags) if flags else 'none'}"
    )
    post_notification(msg)
    print(f"\n  Notification sent.")


if __name__ == "__main__":
    main()
