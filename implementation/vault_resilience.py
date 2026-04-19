#!/usr/bin/env python3
"""
Vault Resilience (E + F) — Adamatzky fault-tolerance metric.

Link-density (C) says "the graph is linked." It doesn't say "the graph would
survive losing the 10 most-central notes." Physarum networks (Adamatzky) show
fault tolerance depends on redundant paths, not raw edge count. E + F are the
missing dimensions:

  E (efficiency)    — average pair-reachability within 3 hops. Measures how
                      easily the graph can flow information end-to-end. Range
                      0.0 (fully disconnected) — 1.0 (all pairs within 3 hops).

  F (fault tolerance) — fraction of E that survives after removing the top-K
                      highest-degree nodes. Range 0.0 (graph collapses without
                      hubs) — 1.0 (graph unchanged; load is fully distributed).

Together: high E + low F = brittle-hub-dependent graph (Tero tree). High E +
high F = mesh-redundant graph (Tero physarum after reinforcement).

Reads from vault_search.py's shared graph loader.

Usage:
    python3 scripts/vault_resilience.py                       # default K=10, N=200 pair samples
    python3 scripts/vault_resilience.py --k 20                # remove top 20 hubs
    python3 scripts/vault_resilience.py --samples 500         # more pair samples (slower, tighter CI)
    python3 scripts/vault_resilience.py --jsonl               # append to logs/vault_resilience.jsonl
"""

import argparse
import json
import random
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.vault_search import load_graph, build_backlinks  # type: ignore

OUT_LOG = REPO / "logs" / "vault_resilience.jsonl"


def build_adjacency(graph: dict, backlinks: dict) -> dict[str, set[str]]:
    """Bidirectional adjacency — treat wikilinks as undirected for reachability."""
    adj: dict[str, set[str]] = defaultdict(set)
    for node, rec in graph.items():
        for target in rec.get("links", []):
            if target in graph:  # skip danglers
                adj[node].add(target)
                adj[target].add(node)
    for node, backs in backlinks.items():
        for src in backs:
            if src in graph:
                adj[node].add(src)
                adj[src].add(node)
    return adj


def reachable_within(adj: dict[str, set[str]], seed: str, hops: int) -> set[str]:
    """BFS up to `hops` from seed; return visited set including seed."""
    visited = {seed}
    frontier = deque([(seed, 0)])
    while frontier:
        node, d = frontier.popleft()
        if d >= hops:
            continue
        for nb in adj.get(node, ()):
            if nb not in visited:
                visited.add(nb)
                frontier.append((nb, d + 1))
    return visited


def measure_efficiency(adj: dict[str, set[str]], samples: int, hops: int, rng: random.Random) -> float:
    """E = fraction of random (a, b) pairs where b is reachable from a within `hops`."""
    nodes = list(adj.keys())
    if len(nodes) < 2:
        return 0.0
    hits = 0
    for _ in range(samples):
        a = rng.choice(nodes)
        b = rng.choice(nodes)
        if a == b:
            continue
        if b in reachable_within(adj, a, hops):
            hits += 1
    return hits / samples


def top_degree_nodes(adj: dict[str, set[str]], k: int) -> list[str]:
    return sorted(adj.keys(), key=lambda n: -len(adj[n]))[:k]


def remove_nodes(adj: dict[str, set[str]], to_remove: set[str]) -> dict[str, set[str]]:
    """Return new adjacency with given nodes deleted."""
    new_adj: dict[str, set[str]] = defaultdict(set)
    for node, neighbors in adj.items():
        if node in to_remove:
            continue
        for nb in neighbors:
            if nb in to_remove:
                continue
            new_adj[node].add(nb)
    return new_adj


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k", type=int, default=10, help="Top-K highest-degree nodes to remove (default 10)")
    ap.add_argument("--samples", type=int, default=200, help="Random pair samples for E (default 200)")
    ap.add_argument("--hops", type=int, default=3, help="Hop radius for reachability (default 3)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    ap.add_argument("--jsonl", action="store_true", help="Append to logs/vault_resilience.jsonl")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    print(f"\nVault Resilience — Adamatzky E + F metric")
    print(f"  loading graph...")
    graph = load_graph(include_superseded=False)
    backlinks = build_backlinks(graph)
    adj = build_adjacency(graph, backlinks)
    total_nodes = len(adj)
    total_edges = sum(len(v) for v in adj.values()) // 2
    print(f"  nodes: {total_nodes}  undirected-edges: {total_edges}")

    hubs = top_degree_nodes(adj, args.k)
    print(f"  top-{args.k} hubs (by degree): {', '.join(hubs[:5])}{'...' if args.k > 5 else ''}")

    print(f"\n  measuring E (baseline efficiency, {args.samples} pairs, {args.hops}-hop)...")
    e_baseline = measure_efficiency(adj, args.samples, args.hops, rng)

    print(f"  measuring E after removing top-{args.k} hubs...")
    adj_reduced = remove_nodes(adj, set(hubs))
    rng2 = random.Random(args.seed)  # same sample points for paired comparison
    e_stressed = measure_efficiency(adj_reduced, args.samples, args.hops, rng2)

    f_score = e_stressed / e_baseline if e_baseline > 0 else 0.0

    print(f"\n  E (baseline):   {e_baseline:.3f}")
    print(f"  E (no hubs):    {e_stressed:.3f}")
    print(f"  F (survived):   {f_score:.3f}  (fraction of efficiency retained)")
    print()

    if f_score >= 0.85:
        verdict = "MESH — load distributed, hub-robust"
    elif f_score >= 0.65:
        verdict = "HYBRID — hub-leaning but mostly redundant"
    elif f_score >= 0.40:
        verdict = "HUB-DEPENDENT — graph relies on central nodes"
    else:
        verdict = "BRITTLE — removing hubs collapses connectivity"
    print(f"  verdict: {verdict}")

    if args.jsonl:
        OUT_LOG.parent.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with open(OUT_LOG, "a") as f:
            f.write(json.dumps({
                "ts": ts, "nodes": total_nodes, "edges": total_edges,
                "k_removed": args.k, "samples": args.samples, "hops": args.hops,
                "e_baseline": round(e_baseline, 4), "e_stressed": round(e_stressed, 4),
                "f_score": round(f_score, 4), "top_hubs": hubs,
            }) + "\n")
        print(f"\n  appended to {OUT_LOG.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
