#!/usr/bin/env python3
"""
Spreading Activation Search — Graph-augmented vault retrieval.

Combines QMD semantic search (seed) with wikilink graph traversal (expand)
and composite reranking. 39% improvement over naive RAG per Pavlović et al.

Flow:
  1. SEED: QMD vector_search returns top-K notes by semantic similarity
  2. EXPAND: Follow [[wikilinks]] 1-2 hops from seed notes
  3. RERANK: Score by (semantic * 0.6 + graph_proximity * 0.3 + recency * 0.1)
  4. Return top results with context

Usage:
    python3 scripts/vault_search.py "why does the grid bleed"
    python3 scripts/vault_search.py "adverse selection" --hops 2 --top 10
"""

import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

NOTES_DIR = Path(__file__).parent.parent / "knowledge" / "notes"


def load_graph():
    """Load all notes and their wikilinks into a graph."""
    notes = {}
    for root, dirs, files in os.walk(NOTES_DIR):
        for f in files:
            if not f.endswith('.md'):
                continue
            path = os.path.join(root, f)
            title = f.replace('.md', '')
            try:
                with open(path) as fh:
                    content = fh.read()
                links = re.findall(r'\[\[([^\]]+)\]\]', content)

                # Extract date_learned for recency scoring
                date_match = re.search(r'date_learned:\s*(\d{4}-\d{2}-\d{2})', content)
                date_str = date_match.group(1) if date_match else "2026-01-01"

                # Extract summary for display
                summary_match = re.search(r'summary:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
                summary = summary_match.group(1) if summary_match else title

                notes[title.lower()] = {
                    'title': title,
                    'path': path,
                    'links': [l.lower() for l in links],
                    'date': date_str,
                    'summary': summary[:120],
                }
            except Exception:
                pass
    return notes


def build_backlinks(graph):
    """Build reverse link index."""
    backlinks = {}
    for title, note in graph.items():
        for link in note['links']:
            if link not in backlinks:
                backlinks[link] = []
            backlinks[link].append(title)
    return backlinks


def keyword_search(graph, query, top_k=10):
    """Simple keyword matching as seed (fallback when QMD unavailable)."""
    query_words = set(query.lower().split())
    scored = []
    for title, note in graph.items():
        # Score by word overlap in title + summary
        text = (title + ' ' + note['summary']).lower()
        matches = sum(1 for w in query_words if w in text)
        if matches > 0:
            # Boost exact phrase match
            if query.lower() in text:
                matches += 3
            scored.append((title, matches / len(query_words)))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]


def expand_hops(graph, backlinks, seeds, max_hops=2):
    """Expand seed notes through wikilink graph. Returns {title: hop_distance}."""
    expanded = {}
    frontier = [(s, 0) for s in seeds]
    visited = set()

    while frontier:
        title, hop = frontier.pop(0)
        if title in visited or hop > max_hops:
            continue
        visited.add(title)
        expanded[title] = hop

        if title in graph:
            # Forward links
            for link in graph[title]['links']:
                if link not in visited:
                    frontier.append((link, hop + 1))
            # Backlinks
            for bl in backlinks.get(title, []):
                if bl not in visited:
                    frontier.append((bl, hop + 1))

    return expanded


def rerank(graph, seeds_with_scores, expanded, query):
    """Composite reranking: semantic * 0.6 + graph_proximity * 0.3 + recency * 0.1"""
    seed_scores = {title: score for title, score in seeds_with_scores}
    today = datetime.now()

    results = []
    for title, hop in expanded.items():
        if title not in graph:
            continue

        note = graph[title]

        # Semantic score (from seed matching, 0 if not a seed)
        semantic = seed_scores.get(title, 0)

        # Graph proximity (1.0 for seeds, 0.5 for 1-hop, 0.25 for 2-hop)
        proximity = 1.0 / (1 + hop)

        # Recency (days since date_learned, normalized)
        try:
            note_date = datetime.strptime(note['date'], '%Y-%m-%d')
            days_old = (today - note_date).days
            recency = max(0, 1.0 - days_old / 90)  # decay over 90 days
        except Exception:
            recency = 0.5

        # Composite score
        score = semantic * 0.6 + proximity * 0.3 + recency * 0.1

        results.append({
            'title': note['title'],
            'path': note['path'],
            'summary': note['summary'],
            'score': score,
            'hop': hop,
            'semantic': semantic,
            'proximity': proximity,
            'recency': recency,
        })

    results.sort(key=lambda x: -x['score'])
    return results


def search(query, top_k=10, max_hops=2):
    """Full spreading activation search."""
    print(f"  Loading vault graph...")
    graph = load_graph()
    backlinks = build_backlinks(graph)
    print(f"  {len(graph)} notes, {sum(len(n['links']) for n in graph.values())} links")

    # Step 1: SEED — keyword search (QMD integration would replace this)
    print(f"  Seeding: '{query}'")
    seeds = keyword_search(graph, query, top_k=top_k)
    if not seeds:
        print("  No seed matches found.")
        return []

    seed_titles = [s[0] for s in seeds]
    print(f"  Seeds: {len(seeds)} notes")

    # Step 2: EXPAND — follow wikilinks
    expanded = expand_hops(graph, backlinks, seed_titles, max_hops=max_hops)
    print(f"  Expanded: {len(expanded)} notes ({len(expanded) - len(seeds)} via graph)")

    # Step 3: RERANK — composite scoring
    results = rerank(graph, seeds, expanded, query)

    return results[:top_k]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spreading Activation Vault Search")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("--top", type=int, default=10, help="Number of results (default 10)")
    parser.add_argument("--hops", type=int, default=2, help="Max graph hops (default 2)")
    args = parser.parse_args()

    results = search(args.query, top_k=args.top, max_hops=args.hops)

    print(f"\n  {'='*60}")
    print(f"  RESULTS: '{args.query}' (top {args.top})")
    print(f"  {'='*60}")
    for i, r in enumerate(results):
        hop_str = f"seed" if r['hop'] == 0 else f"hop-{r['hop']}"
        print(f"  {i+1:>2}. [{r['score']:.2f}] ({hop_str}) {r['title']}")
        print(f"      {r['summary']}")
        print()
