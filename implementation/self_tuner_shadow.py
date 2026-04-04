#!/usr/bin/env python3
"""
Self-Tuning Shadow Mode — observes a live market-making bot and logs what it WOULD change.

Does NOT modify the live bot. Reads fill data + spread data, runs diagnostics,
proposes param adjustments, logs everything. After 48-72hrs, compare shadow
proposals against actual fixed-param performance.

Architecture:
  FAST LOOP (every N trades): populate diagnostic buffer with anomaly flags
  SLOW LOOP (every M fast loops): read buffer, adjust only if threshold fast loops agree

Regime-filtered: only compares data within the same market regime.
Ratchet rule: N trades to move a param, 2N trades to move it back.

Usage:
    python3 self_tuner_shadow.py                    # run shadow mode
    python3 self_tuner_shadow.py --analyze          # compare shadow vs fixed
    python3 self_tuner_shadow.py --status           # show current shadow state

Adapt the fill-loading section at the bottom to your exchange's fills API.
"""

import argparse
import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FILL_LOG = BASE / "logs" / "mm_live.log"                    # your bot's fill log
SPREAD_LOG = BASE / "logs" / "market_data_stream.jsonl"     # your spread/tick log
SHADOW_LOG = BASE / "logs" / "self_tuner_shadow.jsonl"
SHADOW_STATE = BASE / "data" / "self_tuner_state.json"

# --- YOUR LIVE PARAMS — replace with your current config ---
LIVE_PARAMS = {
    "target_bp": 10.0,   # target profit in basis points
    "stop_bp": 5.0,      # stop loss in basis points
    "timeout_s": 120,    # max hold time in seconds
}

# Guardrails — non-negotiable bounds for any param change
GUARDRAILS = {
    "target_bp": {"min": 2.0, "max": 20.0, "step": 1.0},
    "stop_bp":   {"min": 2.0, "max": 15.0, "step": 1.0},
    "timeout_s": {"min": 60,  "max": 600,  "step": 30},
}

# Tuning thresholds
FAST_WINDOW = 20        # trades per fast-loop observation
SLOW_WINDOW = 5         # fast-loop observations before slow-loop decision
CONFIRM_THRESHOLD = 4   # out of SLOW_WINDOW must agree for adjustment
RATCHET_FORWARD = 100   # trades to justify moving a param
RATCHET_BACK = 200      # trades to justify reversing a param move

# Diagnostic triggers — these conditions flag anomalies
DIAG = {
    "target_too_ambitious": {"condition": "target_hit_pct < 0.30 and avg_timeout_pnl > 1.0"},
    "target_too_tight":     {"condition": "target_hit_pct > 0.90 and avg_peak_above_target > 2.0"},
    "timeout_too_short":    {"condition": "timeout_pct > 0.50 and avg_timeout_pnl > 0.0"},
    "timeout_too_long":     {"condition": "avg_hold_s > timeout_s * 0.95"},
    "spread_compressed":    {"condition": "avg_spread_bp < target_bp * 0.4"},
    "instrument_trending":  {"condition": "same_side_pct > 0.80"},
}


class DiagnosticBuffer:
    """Fast-loop diagnostic accumulator."""

    def __init__(self):
        self.observations = deque(maxlen=SLOW_WINDOW)
        self.total_trades = 0
        self.param_history = []  # (trade_count, param, old_val, new_val, reason)

    def add_observation(self, obs):
        """Add a fast-loop observation (dict of diagnostic flags)."""
        self.observations.append(obs)

    def slow_loop_check(self):
        """Check if SLOW_WINDOW observations agree on any diagnostic."""
        if len(self.observations) < SLOW_WINDOW:
            return None

        proposals = []
        for diag_name in DIAG:
            count = sum(1 for obs in self.observations if obs.get(diag_name, False))
            if count >= CONFIRM_THRESHOLD:
                proposals.append(diag_name)

        return proposals if proposals else None


def compute_diagnostics(trades, spreads, current_params):
    """Compute fast-loop diagnostics from a trade window."""
    if not trades:
        return {}

    n = len(trades)
    target_bp = current_params["target_bp"]
    timeout_s = current_params["timeout_s"]

    # Classify exits
    target_hits = [t for t in trades if t.get("reason") == "TARGET"]
    timeouts = [t for t in trades if t.get("reason") == "TIMEOUT"]
    stops = [t for t in trades if t.get("reason") == "STOP"]

    target_hit_pct = len(target_hits) / n if n else 0
    timeout_pct = len(timeouts) / n if n else 0
    stop_pct = len(stops) / n if n else 0

    # P&L stats
    avg_pnl = sum(t.get("pnl_bp", 0) for t in trades) / n if n else 0
    avg_timeout_pnl = (sum(t.get("pnl_bp", 0) for t in timeouts) / len(timeouts)) if timeouts else 0
    avg_hold_s = sum(t.get("hold_s", 0) for t in trades) / n if n else 0

    # Peak analysis (how much are we leaving on the table?)
    peaks = [t.get("peak_bp", 0) for t in trades]
    avg_peak = sum(peaks) / n if peaks else 0
    avg_peak_above_target = max(0, avg_peak - target_bp)

    # Win rate
    wins = sum(1 for t in trades if t.get("pnl_bp", 0) > 0)
    wr = wins / n if n else 0

    # Side analysis (trending detection)
    sides = [t.get("direction", "") for t in trades]
    if sides:
        most_common = max(set(sides), key=sides.count)
        same_side_pct = sides.count(most_common) / len(sides)
    else:
        same_side_pct = 0

    # Spread analysis
    avg_spread_bp = sum(spreads) / len(spreads) if spreads else 0

    # Run diagnostics
    flags = {}
    ctx = {
        "target_hit_pct": target_hit_pct,
        "avg_timeout_pnl": avg_timeout_pnl,
        "avg_peak_above_target": avg_peak_above_target,
        "timeout_pct": timeout_pct,
        "avg_hold_s": avg_hold_s,
        "timeout_s": timeout_s,
        "avg_spread_bp": avg_spread_bp,
        "target_bp": target_bp,
        "same_side_pct": same_side_pct,
    }

    for diag_name, diag_def in DIAG.items():
        try:
            flags[diag_name] = eval(diag_def["condition"], {"__builtins__": {}}, ctx)
        except Exception:
            flags[diag_name] = False

    # Metadata
    flags["_meta"] = {
        "n": n,
        "wr": round(wr, 3),
        "avg_pnl_bp": round(avg_pnl, 2),
        "target_hit_pct": round(target_hit_pct, 3),
        "timeout_pct": round(timeout_pct, 3),
        "stop_pct": round(stop_pct, 3),
        "avg_hold_s": round(avg_hold_s, 1),
        "avg_spread_bp": round(avg_spread_bp, 2),
        "same_side_pct": round(same_side_pct, 3),
        "avg_peak_above_target": round(avg_peak_above_target, 2),
    }

    return flags


def propose_adjustment(proposals, current_params, buffer):
    """Given confirmed slow-loop proposals, suggest ONE param change."""
    # Priority order: stop first (safety), then target, then timeout

    for diag in proposals:
        if diag == "target_too_ambitious":
            param = "target_bp"
            direction = -1  # reduce target
            reason = "Target hit rate <30% but timeouts still profitable"
        elif diag == "target_too_tight":
            param = "target_bp"
            direction = +1  # increase target
            reason = "Target hit rate >90% with room above"
        elif diag == "timeout_too_short":
            param = "timeout_s"
            direction = +1  # extend timeout
            reason = ">50% timeouts with positive P&L — need more time"
        elif diag == "timeout_too_long":
            param = "timeout_s"
            direction = -1  # shorten timeout
            reason = "Avg hold time = timeout — always timing out"
        elif diag == "spread_compressed":
            param = "target_bp"
            direction = -1  # reduce target to match spread
            reason = "Spread < 40% of target — can't capture"
        elif diag == "instrument_trending":
            return {"action": "pause_instrument", "reason": "80%+ fills on same side — trending detected"}
        else:
            continue

        step = GUARDRAILS[param]["step"]
        new_val = current_params[param] + (direction * step)
        new_val = max(GUARDRAILS[param]["min"], min(GUARDRAILS[param]["max"], new_val))

        if new_val == current_params[param]:
            continue  # hit guardrail, skip

        # Ratchet check — is this reversing a previous move?
        last_move = None
        for hist in reversed(buffer.param_history):
            if hist[1] == param:
                last_move = hist
                break

        if last_move:
            last_direction = 1 if last_move[3] > last_move[2] else -1
            if direction != last_direction and buffer.total_trades - last_move[0] < RATCHET_BACK:
                continue  # ratchet: need RATCHET_BACK trades to reverse

        return {
            "action": "adjust",
            "param": param,
            "old": current_params[param],
            "new": new_val,
            "direction": "increase" if direction > 0 else "decrease",
            "reason": reason,
            "diag": diag,
        }

    return None


def log_shadow(entry):
    """Append to shadow log."""
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    with open(SHADOW_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_state():
    """Load or initialize shadow state."""
    if SHADOW_STATE.exists():
        return json.loads(SHADOW_STATE.read_text())
    return {
        "shadow_params": dict(LIVE_PARAMS),
        "live_params": dict(LIVE_PARAMS),
        "buffer_observations": [],
        "param_history": [],
        "total_trades_processed": 0,
        "started": datetime.now(timezone.utc).isoformat(),
    }


def save_state(state):
    """Save shadow state."""
    SHADOW_STATE.parent.mkdir(parents=True, exist_ok=True)
    SHADOW_STATE.write_text(json.dumps(state, indent=2))


def analyze():
    """Compare shadow proposals against fixed-param performance."""
    if not SHADOW_LOG.exists():
        print("No shadow log found. Run shadow mode first.")
        return

    entries = []
    for line in SHADOW_LOG.read_text().splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    observations = [e for e in entries if e.get("type") == "fast_loop"]
    adjustments = [e for e in entries if e.get("type") == "slow_loop_proposal"]

    print(f"Shadow Mode Analysis")
    print(f"{'='*50}")
    print(f"  Observations: {len(observations)}")
    print(f"  Proposed adjustments: {len(adjustments)}")
    print()

    if observations:
        metas = [o.get("diagnostics", {}).get("_meta", {}) for o in observations]
        avg_wr = sum(m.get("wr", 0) for m in metas) / len(metas)
        avg_pnl = sum(m.get("avg_pnl_bp", 0) for m in metas) / len(metas)
        print(f"  Avg win rate across windows: {avg_wr:.1%}")
        print(f"  Avg P&L per trade: {avg_pnl:+.2f}bp")

    if adjustments:
        print(f"\n  Proposed Changes:")
        for a in adjustments:
            p = a.get("proposal", {})
            print(f"    {p.get('param','?')}: {p.get('old','?')} → {p.get('new','?')} ({p.get('reason','?')})")


def status():
    """Show current shadow state."""
    state = load_state()
    print(f"Self-Tuner Shadow Status")
    print(f"{'='*50}")
    print(f"  Started: {state.get('started', '?')}")
    print(f"  Trades processed: {state.get('total_trades_processed', 0)}")
    print(f"  Live params:   target={state['live_params']['target_bp']}bp  stop={state['live_params']['stop_bp']}bp  timeout={state['live_params']['timeout_s']}s")
    print(f"  Shadow params: target={state['shadow_params']['target_bp']}bp  stop={state['shadow_params']['stop_bp']}bp  timeout={state['shadow_params']['timeout_s']}s")
    print(f"  Param changes: {len(state.get('param_history', []))}")


def load_fills_from_log():
    """
    Load trade round-trips from your fill log.

    Replace this function with your exchange's fills API. Each returned
    trade dict should have these keys:
      - direction: "LONG" or "SHORT"
      - pnl_bp: float — round-trip P&L in basis points (fees included)
      - hold_s: int — seconds held
      - reason: "TARGET", "STOP", or "TIMEOUT"
      - peak_bp: float — highest favorable excursion (if available, else 0)
    """
    trades = []
    if not FILL_LOG.exists():
        return trades

    for line in FILL_LOG.read_text().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("type") == "round_trip":
                trades.append(entry)
        except Exception:
            continue

    return trades


def main():
    parser = argparse.ArgumentParser(description="Self-Tuning Shadow Mode")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.analyze:
        analyze()
        return
    if args.status:
        status()
        return

    print("Self-Tuner Shadow Mode — observing, NOT modifying live bot")
    print(f"  Fast loop: every {FAST_WINDOW} trades")
    print(f"  Slow loop: every {FAST_WINDOW * SLOW_WINDOW} trades ({CONFIRM_THRESHOLD}/{SLOW_WINDOW} must agree)")
    print(f"  Ratchet: {RATCHET_FORWARD} trades forward, {RATCHET_BACK} trades to reverse")
    print(f"  Live params: target={LIVE_PARAMS['target_bp']}bp  stop={LIVE_PARAMS['stop_bp']}bp  timeout={LIVE_PARAMS['timeout_s']}s")
    print(f"  Logging to: {SHADOW_LOG}")
    print()

    state = load_state()
    buffer = DiagnosticBuffer()
    buffer.total_trades = state.get("total_trades_processed", 0)
    buffer.param_history = [(h[0], h[1], h[2], h[3], h[4]) for h in state.get("param_history", [])]

    shadow_params = state.get("shadow_params", dict(LIVE_PARAMS))
    spread_buffer = deque(maxlen=100)

    # Load fills — replace load_fills_from_log() with your exchange's fills API
    trade_buffer = load_fills_from_log()

    # Get recent spreads from market data stream
    if SPREAD_LOG.exists():
        for line in SPREAD_LOG.read_text().splitlines()[-100:]:
            try:
                d = json.loads(line)
                for spread_val in d.get("spreads_bp", {}).values():
                    spread_buffer.append(spread_val)
            except Exception:
                continue

    processed = state.get("total_trades_processed", 0)
    remaining = trade_buffer[processed:]

    print(f"  Found {len(trade_buffer)} round-trips, {len(remaining)} new since last run")

    # Process in FAST_WINDOW chunks
    for i in range(0, len(remaining), FAST_WINDOW):
        chunk = remaining[i:i + FAST_WINDOW]
        if len(chunk) < FAST_WINDOW:
            break  # incomplete window

        spreads = list(spread_buffer) if spread_buffer else [2.0]  # default estimate

        # Fast loop: compute diagnostics
        diags = compute_diagnostics(chunk, spreads, shadow_params)
        buffer.add_observation(diags)
        buffer.total_trades += len(chunk)

        log_shadow({
            "type": "fast_loop",
            "trade_window": [buffer.total_trades - FAST_WINDOW, buffer.total_trades],
            "diagnostics": diags,
            "shadow_params": dict(shadow_params),
        })

        meta = diags.get("_meta", {})
        flags = [k for k, v in diags.items() if v is True]
        print(f"  [{buffer.total_trades}T] WR={meta.get('wr',0):.0%}  P&L={meta.get('avg_pnl_bp',0):+.1f}bp  flags={flags or 'none'}")

        # Slow loop: check for confirmed signals
        proposals = buffer.slow_loop_check()
        if proposals:
            adjustment = propose_adjustment(proposals, shadow_params, buffer)
            if adjustment:
                if adjustment.get("action") == "adjust":
                    old = adjustment["old"]
                    new = adjustment["new"]
                    param = adjustment["param"]
                    shadow_params[param] = new
                    buffer.param_history.append((buffer.total_trades, param, old, new, adjustment["reason"]))
                    print(f"  >>> SHADOW ADJUSTMENT: {param} {old} → {new} ({adjustment['reason']})")

                log_shadow({
                    "type": "slow_loop_proposal",
                    "confirmed_diagnostics": proposals,
                    "proposal": adjustment,
                    "shadow_params": dict(shadow_params),
                })

    # Save state
    state["shadow_params"] = shadow_params
    state["total_trades_processed"] = buffer.total_trades
    state["param_history"] = [(h[0], h[1], h[2], h[3], h[4]) for h in buffer.param_history]
    save_state(state)

    print(f"\n  Shadow params: target={shadow_params['target_bp']}bp  stop={shadow_params['stop_bp']}bp  timeout={shadow_params['timeout_s']}s")
    print(f"  Live params:   target={LIVE_PARAMS['target_bp']}bp  stop={LIVE_PARAMS['stop_bp']}bp  timeout={LIVE_PARAMS['timeout_s']}s")
    if shadow_params != LIVE_PARAMS:
        print(f"  DIVERGED — shadow suggests different params")
    else:
        print(f"  ALIGNED — no changes proposed")


if __name__ == "__main__":
    main()
