#!/usr/bin/env python3
"""
Vault FTS5 Index — SQLite full-text search over vault notes.

Hermes-inspired: queryable knowledge base in milliseconds instead of grepping.

Usage:
    python3 scripts/index_vault.py          # rebuild index
    python3 scripts/index_vault.py --query "adverse selection"
    python3 scripts/index_vault.py --stats
"""

import os
import re
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

VAULT_DIR = Path(__file__).parent.parent / "knowledge"
DB_PATH = Path(__file__).parent.parent / "data" / "vault_index.db"

# Additional directories to index (beyond vault)
EXTRA_DIRS = [
    Path(__file__).parent.parent / "research",                                    # Papers, drafts
    Path(__file__).parent.parent / "tasks",                                       # Todo, status
    Path.home() / ".claude" / "projects" / "-Users-claude-Flex-Trading" / "memory",  # Trading memory
    Path.home() / ".claude" / "projects" / "-Users-claude" / "memory",            # Global memory/scaffold
]


def create_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vault_fts USING fts5(
            filepath,
            title,
            note_type,
            domains,
            summary,
            content,
            links,
            date_learned,
            tokenize='porter unicode61'
        )
    """)
    # Edge table for graph queries (backlinks, connected components, PageRank)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_edges (
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            context TEXT DEFAULT '',
            PRIMARY KEY (source, target)
        )
    """)
    # Node metadata for quick lookups
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_nodes (
            title TEXT PRIMARY KEY,
            filepath TEXT,
            note_type TEXT,
            domains TEXT,
            link_count INTEGER DEFAULT 0,
            incoming_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def parse_note(filepath):
    """Parse a vault note into indexable fields."""
    try:
        with open(filepath) as f:
            content = f.read()
    except Exception:
        return None

    title = Path(filepath).stem

    # Parse YAML frontmatter
    fm = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    fm[key.strip()] = val.strip().strip('"').strip("'")
            body = parts[2]
        else:
            body = content
    else:
        body = content

    # Extract wikilinks
    links = re.findall(r'\[\[([^\]]+)\]\]', content)

    # Try relative path from common dirs, fall back to basename
    try:
        rel = str(Path(filepath).relative_to(VAULT_DIR))
    except ValueError:
        rel = str(Path(filepath).name)

    return {
        'filepath': rel,
        'title': title,
        'note_type': fm.get('type', 'unknown'),
        'domains': fm.get('domains', ''),
        'summary': fm.get('summary', ''),
        'content': body[:5000],  # cap at 5k chars
        'links': ', '.join(links),
        'date_learned': fm.get('date_learned', ''),
    }


def index_vault(conn):
    """Rebuild the full index including edge table."""
    # Clear existing
    conn.execute("DELETE FROM vault_fts")
    conn.execute("DELETE FROM vault_edges")
    conn.execute("DELETE FROM vault_nodes")

    count = 0
    all_notes = {}  # title -> note data

    # Index vault + extra directories
    all_dirs = [VAULT_DIR] + [d for d in EXTRA_DIRS if d.exists()]
    for scan_dir in all_dirs:
        for root, dirs, files in os.walk(scan_dir):
            # Skip backups, node_modules, .git, HyPaper
            skip = any(s in root for s in ['backups', 'node_modules', '.git', 'HyPaper', '__pycache__', 'sessions'])
            if skip:
                continue
            for f in files:
                if not f.endswith('.md'):
                    continue
                path = os.path.join(root, f)
                note = parse_note(path)
                if note:
                    # Use relative path from the scan dir for cleaner display
                    try:
                        note['filepath'] = str(Path(path).relative_to(scan_dir))
                    except ValueError:
                        note['filepath'] = str(path)
                    conn.execute(
                        "INSERT INTO vault_fts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (note['filepath'], note['title'], note['note_type'],
                         note['domains'], note['summary'], note['content'],
                         note['links'], note['date_learned'])
                    )
                    all_notes[note['title']] = note
                    count += 1

    # Build edge table from wikilinks
    edge_count = 0
    incoming = {}  # title -> count
    for title, note in all_notes.items():
        links = [l.strip() for l in note['links'].split(',') if l.strip()]
        for target in links:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO vault_edges (source, target) VALUES (?, ?)",
                    (title, target)
                )
                edge_count += 1
                incoming[target] = incoming.get(target, 0) + 1
            except Exception:
                pass

        # Insert node
        conn.execute(
            "INSERT OR REPLACE INTO vault_nodes (title, filepath, note_type, domains, link_count, incoming_count) VALUES (?, ?, ?, ?, ?, ?)",
            (title, note['filepath'], note['note_type'], note['domains'],
             len(links), incoming.get(title, 0))
        )

    # Update incoming counts
    for title, inc in incoming.items():
        conn.execute(
            "UPDATE vault_nodes SET incoming_count = ? WHERE title = ?",
            (inc, title)
        )

    conn.commit()
    print(f"  Edges: {edge_count} wikilinks indexed")
    return count


def query(conn, q, top=10):
    """FTS5 search with BM25 ranking."""
    cursor = conn.execute("""
        SELECT filepath, title, note_type, summary,
               bm25(vault_fts) as rank
        FROM vault_fts
        WHERE vault_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (q, top))

    results = []
    for row in cursor:
        results.append({
            'filepath': row[0],
            'title': row[1],
            'type': row[2],
            'summary': row[3][:120],
            'rank': round(row[4], 3),
        })
    return results


def stats(conn):
    """Show index stats."""
    cursor = conn.execute("SELECT COUNT(*) FROM vault_fts")
    count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT note_type, COUNT(*) FROM vault_fts GROUP BY note_type ORDER BY COUNT(*) DESC")
    types = cursor.fetchall()

    print(f"  Vault Index: {count} notes indexed")
    print(f"  DB: {DB_PATH} ({DB_PATH.stat().st_size / 1024:.0f} KB)")
    print(f"  Types: {', '.join(f'{t[0]}={t[1]}' for t in types)}")


def backlinks(conn, title):
    """Find all notes linking TO a given note."""
    cursor = conn.execute(
        "SELECT source FROM vault_edges WHERE target = ? ORDER BY source", (title,))
    return [row[0] for row in cursor]

def outlinks(conn, title):
    """Find all notes a given note links TO."""
    cursor = conn.execute(
        "SELECT target FROM vault_edges WHERE source = ? ORDER BY target", (title,))
    return [row[0] for row in cursor]

def orphans(conn):
    """Find notes with zero incoming links (not linked from anywhere)."""
    cursor = conn.execute("""
        SELECT n.title, n.filepath, n.note_type
        FROM vault_nodes n
        WHERE n.incoming_count = 0
        AND n.note_type != 'unknown'
        ORDER BY n.title
    """)
    return cursor.fetchall()

def hubs(conn, top=15):
    """Find most-connected notes (highest incoming + outgoing)."""
    cursor = conn.execute("""
        SELECT title, note_type, link_count, incoming_count,
               (link_count + incoming_count) as total
        FROM vault_nodes
        ORDER BY total DESC
        LIMIT ?
    """, (top,))
    return cursor.fetchall()

def graph_stats(conn):
    """Graph-level statistics."""
    nodes = conn.execute("SELECT COUNT(*) FROM vault_nodes").fetchone()[0]
    edges = conn.execute("SELECT COUNT(*) FROM vault_edges").fetchone()[0]
    orphan_count = len(orphans(conn))
    avg_links = conn.execute("SELECT AVG(link_count) FROM vault_nodes").fetchone()[0] or 0
    avg_incoming = conn.execute("SELECT AVG(incoming_count) FROM vault_nodes").fetchone()[0] or 0
    print(f"  Graph: {nodes} nodes, {edges} edges")
    print(f"  Avg outgoing: {avg_links:.1f} | Avg incoming: {avg_incoming:.1f}")
    print(f"  Orphans: {orphan_count}")
    print(f"  Density: {edges / (nodes * (nodes-1)) * 100:.3f}%" if nodes > 1 else "  Density: N/A")

def main():
    parser = argparse.ArgumentParser(description="Vault FTS5 Index + Graph")
    parser.add_argument("--query", "-q", type=str, help="Search query")
    parser.add_argument("--top", type=int, default=10, help="Number of results")
    parser.add_argument("--stats", action="store_true", help="Show index stats")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild index")
    parser.add_argument("--backlinks", type=str, help="Find notes linking to TITLE")
    parser.add_argument("--orphans", action="store_true", help="Find orphan notes")
    parser.add_argument("--hubs", action="store_true", help="Find most-connected notes")
    parser.add_argument("--graph", action="store_true", help="Show graph stats")
    args = parser.parse_args()

    conn = create_db()

    if args.rebuild or not args.query and not args.stats:
        print(f"  Indexing vault...")
        count = index_vault(conn)
        print(f"  Indexed {count} notes → {DB_PATH}")

    if args.stats:
        stats(conn)

    if args.query:
        results = query(conn, args.query, args.top)
        print(f"\n  Results for '{args.query}':")
        for i, r in enumerate(results):
            print(f"  {i+1:>2}. [{r['rank']:.1f}] ({r['type']}) {r['title']}")
            print(f"      {r['summary']}")

    if args.backlinks:
        bl = backlinks(conn, args.backlinks)
        print(f"\n  Backlinks to '{args.backlinks}': {len(bl)}")
        for b in bl:
            print(f"    ← {b}")

    if args.orphans:
        orph = orphans(conn)
        print(f"\n  Orphan notes (0 incoming links): {len(orph)}")
        for title, filepath, ntype in orph:
            print(f"    {title} ({ntype}) — {filepath}")

    if args.hubs:
        h = hubs(conn)
        print(f"\n  Hub notes (most connected):")
        print(f"  {'Title':>50s}  {'Type':>10s}  {'Out':>4s}  {'In':>4s}  {'Total':>5s}")
        for title, ntype, out, inc, total in h:
            print(f"  {title[:50]:>50s}  {ntype:>10s}  {out:>4d}  {inc:>4d}  {total:>5d}")

    if args.graph:
        graph_stats(conn)

    conn.close()


if __name__ == "__main__":
    main()
