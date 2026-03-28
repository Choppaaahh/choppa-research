#!/usr/bin/env python3
"""
Query-Aware Ranked Search — wraps QMD with confidence-based re-ranking.

Uses adaptive α formula (designed by Opus):
  rank = similarity × (α × confidence + (1-α))

Query types detected by keyword heuristic:
  STATE:     "current", "now", "active", "status"  → α=0.5 (recency matters)
  KNOWLEDGE: "why", "how did", "lesson", "caused"  → α=0.05 (relevance dominates)
  DEFAULT:   everything else                        → α=0.25

Decay class awareness:
  FOUNDATIONAL notes get α capped at 0.05 (never penalized by age)
  EPHEMERAL notes get α floored at 0.4 (always recency-weighted)

Requires: vault_index.db with confidence + decay_class columns
          (synced by confidence_decay.py --sync-db)

Usage:
    python3 qmd_ranked_search.py "what is the current config"        # state query
    python3 qmd_ranked_search.py "why does wrong scaffold fail"      # knowledge query
    python3 qmd_ranked_search.py "regime classifier" --debug         # show math

Customize: DB_PATH, STATE_MARKERS, KNOWLEDGE_MARKERS, qmd binary path.
"""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

# ─── CUSTOMIZE ───────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "data" / "vault_index.db"
QMD_BIN = "qmd"  # adjust if not on PATH

STATE_MARKERS = {"current", "now", "active", "running", "what is", "status", "latest", "today", "config"}
KNOWLEDGE_MARKERS = {"why", "how did", "what caused", "lesson", "principle", "mechanism", "explains", "because"}
# ─────────────────────────────────────────────────────────────────────────────


def classify_query(query):
    q = query.lower()
    state = sum(1 for m in STATE_MARKERS if m in q)
    knowledge = sum(1 for m in KNOWLEDGE_MARKERS if m in q)
    if state > knowledge:
        return "state", 0.5
    elif knowledge > state:
        return "knowledge", 0.05
    return "default", 0.25


def get_confidence_scores():
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT filepath, confidence, decay_class FROM vault_nodes WHERE confidence IS NOT NULL")
        return {Path(fp).stem: {"confidence": c or 0.5, "decay_class": dc or "default"} for fp, c, dc in cur.fetchall()}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def run_qmd_search(query, search_type="search"):
    try:
        result = subprocess.run([QMD_BIN, search_type, query], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []
        results = []
        for block in re.split(r'\n(?=qmd://)', result.stdout.strip()):
            if not block.strip():
                continue
            path_match = re.match(r'qmd://([^\s#]+)', block)
            score_match = re.search(r'Score:\s+(\d+)%', block)
            title_match = re.search(r'Title:\s+(.+)', block)
            if path_match:
                results.append({
                    "score": int(score_match.group(1)) / 100.0 if score_match else 0.5,
                    "filepath": path_match.group(1),
                    "title": title_match.group(1).strip() if title_match else path_match.group(1),
                })
        return results
    except Exception:
        return []


def rerank(results, scores, alpha):
    for r in results:
        stem = Path(r["filepath"]).stem
        data = scores.get(stem, {"confidence": 0.5, "decay_class": "default"})
        conf = data["confidence"]
        dc = data["decay_class"]

        # Adaptive α per decay class
        a = alpha
        if dc == "foundational":
            a = min(alpha, 0.05)
        elif dc == "ephemeral":
            a = max(alpha, 0.4)

        r["rank"] = r["score"] * (a * conf + (1 - a))
        r["confidence"] = conf
        r["decay_class"] = dc
        r["alpha"] = a

    results.sort(key=lambda x: -x["rank"])
    return results


def main():
    parser = argparse.ArgumentParser(description="QMD search with confidence re-ranking")
    parser.add_argument("query")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--search-type", default="search", choices=["search", "vsearch", "query"])
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    query_type, alpha = classify_query(args.query)
    scores = get_confidence_scores()
    results = run_qmd_search(args.query, args.search_type)

    if not results:
        print("No results.")
        return

    results = rerank(results, scores, alpha)
    print(f"RANKED — type: {query_type} (α={alpha})\n")
    for r in results[:args.top]:
        if args.debug:
            print(f"  {r['rank']:.3f} (sim={r['score']:.2f} conf={r['confidence']:.2f} α={r['alpha']:.2f} [{r['decay_class']}]) | {r['filepath']}")
        else:
            print(f"  {r['rank']:.3f} | [{r['decay_class'][:4]}] {r['filepath']}")


if __name__ == "__main__":
    main()
