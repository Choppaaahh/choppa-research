#!/usr/bin/env python3
"""
Reasoning Graph — Graph-indexed reasoning history.
Replaces flat JSONL scanning with queryable graph structure.
Library Theorem steal: O(log N) retrieval vs O(N) flat scan.

Nodes: patterns, chains, breadcrumbs, decisions
Edges: pattern→chain (produced_by), chain→chain (preceded_by),
       breadcrumb→pattern (triggered), decision→chain (grounded_by)

Usage:
    python3 scripts/reasoning_graph.py --build          # build graph from logs
    python3 scripts/reasoning_graph.py --query "DQN"    # search graph
    python3 scripts/reasoning_graph.py --pattern X      # show pattern neighborhood
    python3 scripts/reasoning_graph.py --stats           # graph statistics
    python3 scripts/reasoning_graph.py --related "topic" # find related chains+patterns
"""

import argparse
import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).parent.parent
CHAINS_FILE = REPO / "logs" / "reasoning_chains.jsonl"
BREADCRUMBS_FILE = REPO / "logs" / "session_breadcrumbs.jsonl"
DB_PATH = REPO / "data" / "reasoning_graph.db"

parser = argparse.ArgumentParser()
parser.add_argument("--build", action="store_true", help="Build/rebuild graph from logs")
parser.add_argument("--query", type=str, default="", help="Full-text search")
parser.add_argument("--pattern", type=str, default="", help="Show pattern neighborhood")
parser.add_argument("--related", type=str, default="", help="Find related chains+patterns")
parser.add_argument("--stats", action="store_true", help="Graph statistics")
args = parser.parse_args()


def safe_load(path):
    items = []
    if not path.exists():
        return items
    for line in path.read_text(errors="replace").splitlines():
        try:
            items.append(json.loads(line))
        except:
            pass
    return items


def build_graph():
    """Build SQLite graph from reasoning chains + breadcrumbs."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Create tables
    c.executescript("""
        DROP TABLE IF EXISTS nodes;
        DROP TABLE IF EXISTS edges;
        DROP TABLE IF EXISTS fts_nodes;

        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY,
            type TEXT,        -- 'chain', 'pattern', 'breadcrumb', 'decision'
            name TEXT,
            content TEXT,
            ts TEXT,
            metadata TEXT
        );

        CREATE TABLE edges (
            source_id INTEGER,
            target_id INTEGER,
            edge_type TEXT,   -- 'produced_by', 'preceded_by', 'triggered', 'grounded_by'
            FOREIGN KEY (source_id) REFERENCES nodes(id),
            FOREIGN KEY (target_id) REFERENCES nodes(id)
        );

        CREATE VIRTUAL TABLE fts_nodes USING fts5(name, content, type);
    """)

    node_id = 0
    pattern_ids = {}  # pattern_name → node_id
    chain_ids = []    # (node_id, ts, pattern)

    # Load chains
    chains = safe_load(CHAINS_FILE)
    for chain in chains:
        node_id += 1
        pattern = chain.get("pattern", "")
        trigger = chain.get("trigger", "")
        chain_text = chain.get("chain", "")
        outcome = chain.get("outcome", "")
        ts = chain.get("ts", "")
        content = f"{trigger} → {chain_text} → {outcome}"

        c.execute("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?)",
                  (node_id, "chain", pattern or "unnamed", content, ts,
                   json.dumps({"reusable": chain.get("reusable", False)})))
        c.execute("INSERT INTO fts_nodes VALUES (?, ?, ?)",
                  (pattern or "unnamed", content, "chain"))

        chain_ids.append((node_id, ts, pattern))

        # Create pattern node if new
        if pattern and pattern not in pattern_ids:
            node_id += 1
            pattern_ids[pattern] = node_id
            c.execute("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?)",
                      (node_id, "pattern", pattern, "", ts, "{}"))
            c.execute("INSERT INTO fts_nodes VALUES (?, ?, ?)",
                      (pattern, pattern.replace("-", " "), "pattern"))

        # Edge: chain → pattern (produced_by)
        if pattern and pattern in pattern_ids:
            c.execute("INSERT INTO edges VALUES (?, ?, ?)",
                      (chain_ids[-1][0], pattern_ids[pattern], "produced_by"))

    # Temporal edges between chains (preceded_by)
    sorted_chains = sorted(chain_ids, key=lambda x: x[1])
    for i in range(1, len(sorted_chains)):
        c.execute("INSERT INTO edges VALUES (?, ?, ?)",
                  (sorted_chains[i][0], sorted_chains[i-1][0], "preceded_by"))

    # Load breadcrumbs
    breadcrumbs = safe_load(BREADCRUMBS_FILE)
    for bc in breadcrumbs:
        node_id += 1
        bc_type = bc.get("type", "action")
        content = bc.get("content", "")
        ts = bc.get("ts", "")

        c.execute("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?)",
                  (node_id, "breadcrumb", bc_type, content, ts,
                   json.dumps({"type": bc_type})))
        c.execute("INSERT INTO fts_nodes VALUES (?, ?, ?)",
                  (bc_type, content, "breadcrumb"))

        # Edge: breadcrumb → matching pattern (triggered)
        for pname, pid in pattern_ids.items():
            if pname.replace("-", " ") in content.lower() or pname in content.lower():
                c.execute("INSERT INTO edges VALUES (?, ?, ?)",
                          (node_id, pid, "triggered"))

    conn.commit()

    # Stats
    c.execute("SELECT COUNT(*) FROM nodes")
    n_nodes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM edges")
    n_edges = c.fetchone()[0]
    c.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type")
    type_counts = dict(c.fetchall())

    conn.close()
    print(f"Graph built: {n_nodes} nodes, {n_edges} edges")
    print(f"  Types: {type_counts}")
    print(f"  Patterns: {len(pattern_ids)}")
    print(f"  Saved: {DB_PATH}")


def query_graph(query, limit=10):
    """Full-text search across reasoning graph."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("""
        SELECT n.type, n.name, n.content, n.ts, rank
        FROM fts_nodes f
        JOIN nodes n ON n.name = f.name AND n.type = f.type
        WHERE fts_nodes MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))

    results = c.fetchall()
    conn.close()

    if not results:
        print(f"  No results for '{query}'")
        return

    print(f"\n  REASONING GRAPH: '{query}' ({len(results)} results)")
    print(f"  {'='*50}")
    for typ, name, content, ts, rank in results:
        print(f"  [{typ:>10}] {name}")
        print(f"             {content[:100]}")
        print(f"             ts={ts[:16] if ts else '?'}")
        print()


def show_pattern(pattern_name):
    """Show a pattern's full neighborhood: chains that produced it, breadcrumbs that triggered it."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Find pattern node
    c.execute("SELECT id, name, ts FROM nodes WHERE type='pattern' AND name LIKE ?",
              (f"%{pattern_name}%",))
    patterns = c.fetchall()

    if not patterns:
        print(f"  Pattern '{pattern_name}' not found")
        conn.close()
        return

    for pid, pname, pts in patterns:
        print(f"\n  PATTERN: {pname}")
        print(f"  {'='*50}")

        # Chains that produced this pattern
        c.execute("""
            SELECT n.name, n.content, n.ts FROM edges e
            JOIN nodes n ON n.id = e.source_id
            WHERE e.target_id = ? AND e.edge_type = 'produced_by'
            ORDER BY n.ts
        """, (pid,))
        chains = c.fetchall()
        print(f"  Produced by {len(chains)} chains:")
        for name, content, ts in chains:
            print(f"    [{ts[:16] if ts else '?'}] {content[:80]}")

        # Breadcrumbs that triggered this pattern
        c.execute("""
            SELECT n.name, n.content, n.ts FROM edges e
            JOIN nodes n ON n.id = e.source_id
            WHERE e.target_id = ? AND e.edge_type = 'triggered'
            ORDER BY n.ts
        """, (pid,))
        triggers = c.fetchall()
        if triggers:
            print(f"  Triggered by {len(triggers)} breadcrumbs:")
            for name, content, ts in triggers[:5]:
                print(f"    [{ts[:16] if ts else '?'}] {content[:80]}")

    conn.close()


def find_related(topic, limit=10):
    """Find chains and patterns related to a topic."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # FTS search
    c.execute("""
        SELECT DISTINCT n.type, n.name, n.content, n.ts
        FROM fts_nodes f
        JOIN nodes n ON n.name = f.name AND n.type = f.type
        WHERE fts_nodes MATCH ?
        ORDER BY n.ts DESC
        LIMIT ?
    """, (topic, limit))

    results = c.fetchall()
    conn.close()

    print(f"\n  RELATED to '{topic}': {len(results)} results")
    for typ, name, content, ts in results:
        print(f"  [{typ:>10}] {name} ({ts[:10] if ts else '?'})")
        print(f"             {content[:80]}")


def show_stats():
    """Show graph statistics."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM nodes")
    n_nodes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM edges")
    n_edges = c.fetchone()[0]
    c.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type")
    types = dict(c.fetchall())
    c.execute("SELECT edge_type, COUNT(*) FROM edges GROUP BY edge_type")
    edge_types = dict(c.fetchall())

    # Most connected patterns
    c.execute("""
        SELECT n.name, COUNT(e.source_id) as connections
        FROM nodes n
        JOIN edges e ON e.target_id = n.id
        WHERE n.type = 'pattern'
        GROUP BY n.name
        ORDER BY connections DESC
        LIMIT 10
    """)
    top_patterns = c.fetchall()

    conn.close()

    print(f"\n  REASONING GRAPH STATS")
    print(f"  {'='*50}")
    print(f"  Nodes: {n_nodes} | Edges: {n_edges}")
    print(f"  Types: {types}")
    print(f"  Edge types: {edge_types}")
    print(f"\n  Most connected patterns:")
    for name, count in top_patterns:
        print(f"    {name:>45}: {count} connections")


def main():
    if args.build:
        build_graph()
    elif args.query:
        if not DB_PATH.exists():
            print("  Graph not built. Run --build first.")
            return
        query_graph(args.query)
    elif args.pattern:
        if not DB_PATH.exists():
            print("  Graph not built. Run --build first.")
            return
        show_pattern(args.pattern)
    elif args.related:
        if not DB_PATH.exists():
            print("  Graph not built. Run --build first.")
            return
        find_related(args.related)
    elif args.stats:
        if not DB_PATH.exists():
            print("  Graph not built. Run --build first.")
            return
        show_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
