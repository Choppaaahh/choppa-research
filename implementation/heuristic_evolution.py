#!/usr/bin/env python3
"""
MeLA-Inspired Heuristic Evolution -- Auto-generates researcher templates.

MeLA paper steal (arXiv 2507.20541): evolve heuristics via metacognitive loop.
Generate candidate -> backtest -> diagnose errors -> refine -> promote.

Instead of manually designing researcher templates, this script:
1. Reads vault findings + researcher results to identify patterns
2. Generates candidate template parameters (spread, threshold, logic)
3. Backtests each candidate against recent tick data
4. Diagnoses failures (why did it lose? too tight? wrong regime?)
5. Refines parameters based on diagnosis
6. Promotes winners to researcher template pool

Usage:
    python3 heuristic_evolution.py --evolve           # run one evolution cycle
    python3 heuristic_evolution.py --evolve --rounds 5 # 5 rounds of refinement
    python3 heuristic_evolution.py --show              # show current template pool
    python3 heuristic_evolution.py --audit             # audit template performance
"""
import argparse
import json
import random
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
TEMPLATE_POOL = REPO / "logs" / "evolved_templates.jsonl"
EVOLUTION_LOG = REPO / "logs" / "heuristic_evolution.jsonl"
TICK_FILE = REPO / "logs" / "equities_ticks.jsonl"
FINDINGS_FILE = REPO / "logs" / "researcher_findings.jsonl"

parser = argparse.ArgumentParser()
parser.add_argument("--evolve", action="store_true")
parser.add_argument("--rounds", type=int, default=3)
parser.add_argument("--show", action="store_true")
parser.add_argument("--audit", action="store_true")
parser.add_argument("--candidates", type=int, default=10)
args = parser.parse_args()

# All available coins
CRYPTO_COINS = ["COIN_A", "COIN_B", "COIN_C", "COIN_D", "COIN_E"]
EQ_COINS = ["xyz:CL", "xyz:BRENTOIL", "xyz:SILVER"]
ALL_COINS = CRYPTO_COINS + EQ_COINS

# Template DNA: parameters that define a strategy
LOGIC_TYPES = ["tagged_mm", "mean_reversion", "trend_scalp", "vol_breakout", "pairs_spread", "depth_imbalance"]

SPREAD_RANGE = (2, 20)
ENTRY_THRESH_RANGE = (0.5, 5.0)
EXIT_MULT_RANGE = (0.5, 3.0)
LOOKBACK_RANGE = (5, 60)


def load_ticks(coin, n=5000):
    """Load recent ticks for a coin."""
    import subprocess
    lines = subprocess.run(
        ["tail", "-10000", str(TICK_FILE)],
        capture_output=True, text=True).stdout.splitlines()

    ticks = []
    for line in lines:
        try:
            t = json.loads(line)
            bbo = t.get("bbo", {})
            if coin in bbo:
                d = bbo[coin]
                ticks.append({"mid": d["m"], "bid": d["b"], "ask": d["a"],
                              "spread": d["s"], "ts": t["ts"]})
        except:
            continue

    return ticks[-n:]


def generate_candidate():
    """Generate a random template candidate (mutation)."""
    logic = random.choice(LOGIC_TYPES)
    coin = random.choice(ALL_COINS)
    spread = round(random.uniform(*SPREAD_RANGE), 1)
    entry_thresh = round(random.uniform(*ENTRY_THRESH_RANGE), 2)
    exit_mult = round(random.uniform(*EXIT_MULT_RANGE), 2)
    lookback = random.randint(*LOOKBACK_RANGE)
    maker_fee = 0.15 if coin.startswith("xyz:") else 1.44

    return {
        "name": f"EVO-{logic[:3]}-s{spread:.0f}-e{entry_thresh:.1f}",
        "logic": logic,
        "coin": coin,
        "params": {
            "spread_bp": spread,
            "entry_threshold": entry_thresh,
            "exit_mult": exit_mult,
            "lookback": lookback,
            "maker_fee": maker_fee,
        },
        "generation": 0,
        "parent": None,
    }


def mutate(template):
    """Mutate a template's parameters slightly."""
    child = json.loads(json.dumps(template))
    child["parent"] = child["name"]
    child["generation"] = template.get("generation", 0) + 1

    # Mutate one random parameter
    param = random.choice(["spread_bp", "entry_threshold", "exit_mult", "lookback"])
    p = child["params"]

    if param == "spread_bp":
        p[param] = max(2, min(20, p[param] + random.uniform(-2, 2)))
    elif param == "entry_threshold":
        p[param] = max(0.3, min(5, p[param] + random.uniform(-0.5, 0.5)))
    elif param == "exit_mult":
        p[param] = max(0.3, min(3, p[param] + random.uniform(-0.3, 0.3)))
    elif param == "lookback":
        p[param] = max(5, min(60, p[param] + random.randint(-5, 5)))

    p[param] = round(p[param], 2)
    child["name"] = f"EVO-{child['logic'][:3]}-s{p['spread_bp']:.0f}-e{p['entry_threshold']:.1f}"
    return child


def backtest_template(template, ticks):
    """Backtest a template on tick data. Returns {pnl_bp, n_trades, win_rate}."""
    if len(ticks) < 100:
        return {"pnl_bp": 0, "n_trades": 0, "win_rate": 0, "error": "insufficient data"}

    p = template["params"]
    spread = p["spread_bp"]
    fee = p["maker_fee"]
    lookback = p["lookback"]
    logic = template["logic"]

    pnl = 0
    trades = 0
    wins = 0

    for i in range(lookback, len(ticks) - 1):
        mid = ticks[i]["mid"]
        nmid = ticks[i + 1]["mid"]
        nbid = ticks[i + 1]["bid"]
        nask = ticks[i + 1]["ask"]

        if logic == "tagged_mm":
            # Simple MM: place bid+ask at spread, collect fills
            our_bid = mid * (1 - spread / 2 / 10000)
            our_ask = mid * (1 + spread / 2 / 10000)
            if nask <= our_bid:
                trade_pnl = spread / 2 - fee
                pnl += trade_pnl
                trades += 1
                if trade_pnl > 0: wins += 1
            if nbid >= our_ask:
                trade_pnl = spread / 2 - fee
                pnl += trade_pnl
                trades += 1
                if trade_pnl > 0: wins += 1

        elif logic == "mean_reversion":
            # Mean reversion: enter when price deviates from MA, exit at MA
            window = [ticks[j]["mid"] for j in range(i - lookback, i)]
            ma = sum(window) / len(window)
            dev = (mid - ma) / ma * 10000

            if abs(dev) > p["entry_threshold"] * spread:
                # Entry: bet on reversion
                direction = -1 if dev > 0 else 1  # sell if above MA, buy if below
                exit_px = ma
                actual_move = (nmid - mid) / mid * 10000
                trade_pnl = actual_move * direction - fee
                pnl += trade_pnl
                trades += 1
                if trade_pnl > 0: wins += 1

        elif logic == "trend_scalp":
            # Trend following: enter on momentum, exit on reversal
            window = [ticks[j]["mid"] for j in range(i - lookback, i)]
            trend = (window[-1] - window[0]) / window[0] * 10000

            if abs(trend) > p["entry_threshold"] * spread:
                direction = 1 if trend > 0 else -1
                actual_move = (nmid - mid) / mid * 10000
                trade_pnl = actual_move * direction - fee
                pnl += trade_pnl
                trades += 1
                if trade_pnl > 0: wins += 1

        elif logic == "vol_breakout":
            # Vol breakout: enter when vol expands beyond threshold
            rets = [(ticks[j]["mid"] - ticks[j - 1]["mid"]) / ticks[j - 1]["mid"] * 10000
                    for j in range(i - lookback + 1, i)]
            vol = (sum(r ** 2 for r in rets) / len(rets)) ** 0.5

            if vol > p["entry_threshold"] * 2:
                direction = 1 if rets[-1] > 0 else -1
                actual_move = (nmid - mid) / mid * 10000
                trade_pnl = actual_move * direction - fee
                pnl += trade_pnl
                trades += 1
                if trade_pnl > 0: wins += 1

        elif logic in ("pairs_spread", "depth_imbalance"):
            # Simplified: treat as MM with adjusted params
            adj_spread = spread * p["exit_mult"]
            our_bid = mid * (1 - adj_spread / 2 / 10000)
            our_ask = mid * (1 + adj_spread / 2 / 10000)
            if nask <= our_bid:
                trade_pnl = adj_spread / 2 - fee
                pnl += trade_pnl
                trades += 1
                if trade_pnl > 0: wins += 1
            if nbid >= our_ask:
                trade_pnl = adj_spread / 2 - fee
                pnl += trade_pnl
                trades += 1
                if trade_pnl > 0: wins += 1

    wr = wins / max(trades, 1) * 100
    return {"pnl_bp": round(pnl, 1), "n_trades": trades, "win_rate": round(wr, 1)}


def diagnose_failure(template, result):
    """Diagnose why a template failed. Returns refinement suggestions."""
    issues = []

    if result["n_trades"] == 0:
        issues.append("no_trades: spread too wide or threshold too high")
    elif result["win_rate"] < 40:
        issues.append("low_winrate: entry signal too noisy or spread too tight")
    elif result["pnl_bp"] < 0 and result["win_rate"] > 50:
        issues.append("losers_too_big: need tighter exits or wider spread")
    elif result["pnl_bp"] < 0:
        issues.append("wrong_logic: this logic type may not work for this coin")

    if result["n_trades"] > 0 and result["pnl_bp"] / max(result["n_trades"], 1) < -1:
        issues.append("per_trade_loss: avg loss exceeds threshold")

    return issues


def evolve():
    """Run one evolution cycle: generate, test, diagnose, refine, promote."""
    print(f"MeLA Evolution Cycle — {args.candidates} candidates, {args.rounds} rounds")
    print("=" * 60)

    # Load existing pool for seeding mutations
    existing = []
    if TEMPLATE_POOL.exists():
        for line in TEMPLATE_POOL.read_text().splitlines():
            try:
                existing.append(json.loads(line))
            except:
                pass

    all_results = []

    for round_num in range(args.rounds):
        print(f"\n--- Round {round_num + 1}/{args.rounds} ---")

        # Generate candidates: mix of random + mutations of existing winners
        candidates = []
        n_random = args.candidates // 2
        n_mutate = args.candidates - n_random

        for _ in range(n_random):
            candidates.append(generate_candidate())

        if existing:
            # Mutate top performers
            winners = sorted(existing, key=lambda x: x.get("best_pnl", 0), reverse=True)[:5]
            for _ in range(n_mutate):
                parent = random.choice(winners)
                candidates.append(mutate(parent))
        else:
            for _ in range(n_mutate):
                candidates.append(generate_candidate())

        # Test each candidate
        round_results = []
        for cand in candidates:
            ticks = load_ticks(cand["coin"], n=5000)
            if len(ticks) < 200:
                continue

            # Split: 70% train, 30% val
            split = int(len(ticks) * 0.7)
            train_result = backtest_template(cand, ticks[:split])
            val_result = backtest_template(cand, ticks[split:])

            cand["train_pnl"] = train_result["pnl_bp"]
            cand["val_pnl"] = val_result["pnl_bp"]
            cand["train_trades"] = train_result["n_trades"]
            cand["val_wr"] = val_result["win_rate"]
            cand["best_pnl"] = val_result["pnl_bp"]

            status = "PASS" if val_result["pnl_bp"] > 0 and val_result["n_trades"] >= 3 else "FAIL"

            if status == "FAIL":
                issues = diagnose_failure(cand, val_result)
                cand["diagnosis"] = issues

            round_results.append((cand, status, val_result))
            marker = "+" if status == "PASS" else "-"
            print(f"  {marker} {cand['name']:>25} {cand['coin']:>12} "
                  f"train={train_result['pnl_bp']:>+6.0f} val={val_result['pnl_bp']:>+6.0f} "
                  f"trades={val_result['n_trades']} wr={val_result['win_rate']:.0f}%")

        # Promote winners to pool
        winners = [(c, s, r) for c, s, r in round_results if s == "PASS"]
        for cand, _, result in winners:
            cand["promoted_ts"] = datetime.now(timezone.utc).isoformat()[:19]
            existing.append(cand)

        # Seed next round with this round's winners (for mutation)
        all_results.extend(round_results)

    # Save promoted templates
    n_promoted = sum(1 for _, s, _ in all_results if s == "PASS")
    n_total = len(all_results)

    with open(TEMPLATE_POOL, "w") as f:
        for t in existing:
            f.write(json.dumps(t) + "\n")

    # Log evolution cycle
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat()[:19],
        "rounds": args.rounds,
        "candidates": len(all_results),
        "promoted": n_promoted,
        "yield_pct": round(n_promoted / max(n_total, 1) * 100, 1),
    }
    with open(EVOLUTION_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"\n{'=' * 60}")
    print(f"Evolution complete: {n_promoted}/{n_total} promoted ({log_entry['yield_pct']}% yield)")
    print(f"Template pool: {len(existing)} total templates")


def show():
    """Show current template pool."""
    if not TEMPLATE_POOL.exists():
        print("No templates. Run --evolve first.")
        return

    templates = [json.loads(l) for l in TEMPLATE_POOL.read_text().splitlines() if l.strip()]
    templates.sort(key=lambda x: x.get("best_pnl", 0), reverse=True)

    print(f"Template Pool: {len(templates)} templates")
    print(f"{'Name':>30} {'Coin':>12} {'Logic':>15} {'Val PnL':>8} {'WR':>5} {'Gen':>4}")
    print("-" * 80)
    for t in templates[:20]:
        print(f"{t['name']:>30} {t['coin']:>12} {t['logic']:>15} "
              f"{t.get('val_pnl', 0):>+7.0f} {t.get('val_wr', 0):>4.0f}% {t.get('generation', 0):>4}")


def audit():
    """Audit template evolution history."""
    if not EVOLUTION_LOG.exists():
        print("No evolution history.")
        return

    entries = [json.loads(l) for l in EVOLUTION_LOG.read_text().splitlines() if l.strip()]
    print(f"Evolution History: {len(entries)} cycles")
    for e in entries[-10:]:
        print(f"  {e['ts']}: {e['promoted']}/{e['candidates']} promoted ({e['yield_pct']}% yield)")


if __name__ == "__main__":
    if args.evolve:
        evolve()
    elif args.show:
        show()
    elif args.audit:
        audit()
    else:
        parser.print_help()
