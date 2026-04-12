#!/usr/bin/env python3
"""
Decision Graph -- Evidence-centric spread decision memory.

Reasoning Graphs paper steal (arXiv 2604.07595): persist evidence as graph nodes,
store outcomes, enable deterministic retrieval of prior decisions on identical evidence.

Instead of DQN re-reasoning every tick, check: "have I seen this market state before?
What spread worked?" Eliminates variance on known conditions.

Layers:
  1. Index: spread decisions + outcomes from MM journal
  2. Query: given current market state, find nearest prior decisions
  3. Lookup: what spread won/lost at similar conditions
  4. Augment: feed lookup results to DQN as additional context

Usage:
    python3 decision_graph.py --build      # build from journal + tick data
    python3 decision_graph.py --query "COIN_A vol=3.2 obi=0.4"
    python3 decision_graph.py --lookup --coin COIN_A --vol 3.2 --obi 0.4
    python3 decision_graph.py --stats
"""
import argparse
import json
import os
import sqlite3
import time
import numpy as np
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).parent.parent
DB_PATH = REPO / "data" / "decision_graph.db"
JOURNAL = REPO / "logs" / "mm_journal.jsonl"
TICKS = REPO / "logs" / "equities_ticks.jsonl"
BREADCRUMBS = REPO / "logs" / "session_breadcrumbs.jsonl"
CHAINS = REPO / "logs" / "reasoning_chains.jsonl"

parser = argparse.ArgumentParser()
parser.add_argument("--build", action="store_true")
parser.add_argument("--query", type=str, default="")
parser.add_argument("--lookup", action="store_true")
parser.add_argument("--coin", type=str, default="")
parser.add_argument("--vol", type=float, default=0)
parser.add_argument("--obi", type=float, default=0)
parser.add_argument("--trend", type=float, default=0)
parser.add_argument("--stats", action="store_true")
parser.add_argument("--top", type=int, default=5)
args = parser.parse_args()


def init_db(conn):
    """Create decision graph schema."""
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin TEXT,
            ts TEXT,
            vol_bp REAL,
            spread_bp REAL,
            trend_bp REAL,
            obi REAL,
            range_pos REAL,
            -- Decision
            spread_chosen REAL,
            -- Outcome
            pnl_bp REAL,
            hold_s REAL,
            paired INTEGER,  -- 1 if pair completed, 0 if timed out/lost
            -- Context
            source TEXT,     -- 'journal', 'backtest', 'breadcrumb'
            metadata TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source);

        CREATE INDEX IF NOT EXISTS idx_evidence_coin ON evidence(coin);
        CREATE INDEX IF NOT EXISTS idx_evidence_vol ON evidence(vol_bp);
        CREATE INDEX IF NOT EXISTS idx_evidence_obi ON evidence(obi);

        -- Aggregate stats per condition bucket
        CREATE TABLE IF NOT EXISTS condition_stats (
            coin TEXT,
            vol_bucket TEXT,    -- 'low', 'med', 'high'
            obi_bucket TEXT,    -- 'sell_heavy', 'neutral', 'buy_heavy'
            trend_bucket TEXT,  -- 'down', 'flat', 'up'
            spread_bp REAL,     -- spread that was tried
            n_trials INTEGER,
            n_wins INTEGER,
            avg_pnl REAL,
            avg_hold_s REAL,
            PRIMARY KEY (coin, vol_bucket, obi_bucket, trend_bucket, spread_bp)
        );
    """)
    conn.commit()


def bucket_vol(vol):
    if vol < 1.5: return "low"
    elif vol < 3.0: return "med"
    return "high"


def bucket_obi(obi):
    if obi < -0.2: return "sell_heavy"
    elif obi > 0.2: return "buy_heavy"
    return "neutral"


def bucket_trend(trend):
    if trend < -5: return "down"
    elif trend > 5: return "up"
    return "flat"


def build():
    """Build decision graph from all available data sources."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)
    c = conn.cursor()

    # Clear existing data for rebuild
    c.execute("DELETE FROM evidence")
    c.execute("DELETE FROM condition_stats")

    n_evidence = 0

    # Source 1: MM journal (actual live trades)
    if JOURNAL.exists():
        print("  Loading journal...")
        for line in JOURNAL.read_text(errors="replace").splitlines():
            try:
                t = json.loads(line)
                c.execute("""INSERT INTO evidence
                    (coin, ts, vol_bp, spread_bp, trend_bp, obi, range_pos,
                     spread_chosen, pnl_bp, hold_s, paired, source, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (t.get("coin", ""), t.get("ts", ""),
                     t.get("vol_bp", 0), t.get("spread_bp", 0),
                     t.get("trend_bp", 0), t.get("obi", 0), 0.5,
                     t.get("spread_chosen", 0), t.get("pnl_bp", 0),
                     t.get("hold_s", 0), 1 if t.get("pnl_bp", 0) > 0 else 0,
                     "journal", json.dumps(t)))
                n_evidence += 1
            except:
                continue

    # Source 2: Breadcrumbs with trading context
    if BREADCRUMBS.exists():
        print("  Loading breadcrumbs...")
        for line in BREADCRUMBS.read_text(errors="replace").splitlines():
            try:
                b = json.loads(line)
                if b.get("type") in ("finding", "decision", "failure") and any(
                    kw in b.get("content", "").lower()
                    for kw in ["spread", "bp", "dqn", "inventory", "skew", "pair"]
                ):
                    c.execute("""INSERT INTO evidence
                        (coin, ts, vol_bp, spread_bp, trend_bp, obi, range_pos,
                         spread_chosen, pnl_bp, hold_s, paired, source, metadata)
                        VALUES (?, ?, 0, 0, 0, 0, 0.5, 0, 0, 0, 0, ?, ?)""",
                        ("", b.get("ts", ""), "breadcrumb",
                         json.dumps({"type": b["type"], "content": b["content"][:200]})))
                    n_evidence += 1
            except:
                continue

    # Source 3: Reasoning chains about spread decisions
    if CHAINS.exists():
        print("  Loading chains...")
        for line in CHAINS.read_text(errors="replace").splitlines():
            try:
                ch = json.loads(line)
                pattern = ch.get("pattern", "")
                if any(kw in pattern.lower() or kw in ch.get("outcome", "").lower()
                       for kw in ["spread", "reward", "dqn", "inventory", "coevol"]):
                    c.execute("""INSERT INTO evidence
                        (coin, ts, vol_bp, spread_bp, trend_bp, obi, range_pos,
                         spread_chosen, pnl_bp, hold_s, paired, source, metadata)
                        VALUES (?, ?, 0, 0, 0, 0, 0.5, 0, 0, 0, 0, ?, ?)""",
                        ("", ch.get("ts", ""), "chain",
                         json.dumps({"pattern": pattern, "outcome": ch.get("outcome", "")[:200]})))
                    n_evidence += 1
            except:
                continue

    # Build condition_stats aggregates from journal evidence
    print("  Building condition stats...")
    c.execute("""SELECT coin, vol_bp, obi, trend_bp, spread_chosen, pnl_bp, hold_s, paired
                 FROM evidence WHERE source='journal' AND coin != ''""")
    rows = c.fetchall()

    stats = defaultdict(lambda: {"n": 0, "wins": 0, "pnl_sum": 0, "hold_sum": 0})
    for coin, vol, obi, trend, spread, pnl, hold, paired in rows:
        key = (coin, bucket_vol(vol), bucket_obi(obi), bucket_trend(trend), spread)
        stats[key]["n"] += 1
        stats[key]["wins"] += (1 if pnl > 0 else 0)
        stats[key]["pnl_sum"] += pnl
        stats[key]["hold_sum"] += hold

    for (coin, vb, ob, tb, spread), s in stats.items():
        c.execute("""INSERT OR REPLACE INTO condition_stats
            (coin, vol_bucket, obi_bucket, trend_bucket, spread_bp, n_trials, n_wins, avg_pnl, avg_hold_s)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (coin, vb, ob, tb, spread, s["n"], s["wins"],
             s["pnl_sum"] / max(s["n"], 1), s["hold_sum"] / max(s["n"], 1)))

    conn.commit()
    print(f"\n  Decision graph built: {n_evidence} evidence nodes, {len(stats)} condition buckets")
    conn.close()


def lookup():
    """Query: given current conditions, what spread has worked?"""
    if not DB_PATH.exists():
        print("Run --build first"); return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    vb = bucket_vol(args.vol)
    ob = bucket_obi(args.obi)
    tb = bucket_trend(args.trend)

    print(f"Lookup: {args.coin} vol={args.vol}bp ({vb}) obi={args.obi} ({ob}) trend={args.trend}bp ({tb})")
    print()

    # Exact match first
    c.execute("""SELECT spread_bp, n_trials, n_wins, avg_pnl, avg_hold_s
                 FROM condition_stats
                 WHERE coin=? AND vol_bucket=? AND obi_bucket=? AND trend_bucket=?
                 ORDER BY avg_pnl DESC""",
              (args.coin, vb, ob, tb))
    rows = c.fetchall()

    if rows:
        print(f"  Exact match ({vb}/{ob}/{tb}):")
        print(f"  {'Spread':>7} {'Trials':>7} {'WR':>6} {'Avg PnL':>8} {'Hold':>6}")
        print(f"  {'-'*38}")
        for spread, trials, wins, pnl, hold in rows:
            wr = wins / max(trials, 1) * 100
            print(f"  {spread:>6.0f}bp {trials:>7} {wr:>5.0f}% {pnl:>+7.1f}bp {hold:>5.0f}s")
        best = rows[0]
        print(f"\n  RECOMMENDATION: {best[0]:.0f}bp (best avg pnl: {best[3]:+.1f}bp on {best[1]} trials)")
    else:
        # Fallback: relax trend bucket
        c.execute("""SELECT spread_bp, SUM(n_trials), SUM(n_wins), AVG(avg_pnl)
                     FROM condition_stats
                     WHERE coin=? AND vol_bucket=? AND obi_bucket=?
                     GROUP BY spread_bp ORDER BY AVG(avg_pnl) DESC""",
                  (args.coin, vb, ob))
        rows = c.fetchall()
        if rows:
            print(f"  Relaxed match ({vb}/{ob}/any trend):")
            for spread, trials, wins, pnl in rows[:5]:
                wr = wins / max(trials, 1) * 100
                print(f"    {spread:.0f}bp: {trials} trials, {wr:.0f}% WR, {pnl:+.1f}bp avg")
        else:
            print("  No matching evidence. DQN decides alone.")

    conn.close()


def query(text):
    """Full-text search across all evidence."""
    if not DB_PATH.exists():
        print("Run --build first"); return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("""SELECT e.coin, e.ts, e.source, e.spread_chosen, e.pnl_bp, e.metadata
                 FROM evidence e
                 WHERE e.metadata LIKE ?
                 ORDER BY e.ts DESC LIMIT ?""",
              (f"%{text}%", args.top))
    rows = c.fetchall()

    print(f"Search '{text}': {len(rows)} results")
    for coin, ts, source, spread, pnl, meta in rows:
        meta_short = json.loads(meta).get("content", json.loads(meta).get("pattern", ""))[:80] if meta else ""
        print(f"  [{source:>10}] {ts[:16]} {coin:>10} spread={spread:.0f}bp pnl={pnl:+.1f}bp | {meta_short}")

    conn.close()


def stats():
    """Graph statistics."""
    if not DB_PATH.exists():
        print("Run --build first"); return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM evidence")
    n_evidence = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM condition_stats")
    n_buckets = c.fetchone()[0]
    c.execute("SELECT source, COUNT(*) FROM evidence GROUP BY source")
    sources = dict(c.fetchall())
    c.execute("SELECT coin, COUNT(*) FROM evidence WHERE coin != '' GROUP BY coin ORDER BY COUNT(*) DESC LIMIT 10")
    coins = c.fetchall()

    print(f"Decision Graph Stats:")
    print(f"  Evidence nodes: {n_evidence}")
    print(f"  Condition buckets: {n_buckets}")
    print(f"  Sources: {sources}")
    print(f"  Top coins: {dict(coins)}")

    # Best performing conditions
    c.execute("""SELECT coin, vol_bucket, obi_bucket, trend_bucket, spread_bp, n_trials, avg_pnl
                 FROM condition_stats WHERE n_trials >= 3
                 ORDER BY avg_pnl DESC LIMIT 5""")
    rows = c.fetchall()
    if rows:
        print(f"\n  Best performing conditions (3+ trials):")
        for coin, vb, ob, tb, spread, n, pnl in rows:
            print(f"    {coin} {vb}/{ob}/{tb} @ {spread:.0f}bp: {pnl:+.1f}bp avg ({n} trials)")

    conn.close()


if __name__ == "__main__":
    if args.build:
        build()
    elif args.lookup:
        lookup()
    elif args.query:
        query(args.query)
    elif args.stats:
        stats()
    else:
        parser.print_help()
