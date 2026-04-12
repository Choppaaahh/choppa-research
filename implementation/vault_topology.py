#!/usr/bin/env python3
"""
Vault Topology Analyzer — Auto-discovers structure in any knowledge vault.

No configuration needed. Point it at a directory of markdown notes and it:
1. Extracts all wikilinks → builds a directed graph
2. Finds clusters (connected components)
3. Identifies hubs (high-degree nodes), bridges (connect clusters), peripherals
4. Detects disconnected clusters that SHOULD be connected (shared keywords)
5. Suggests specific connections to strengthen the graph
6. Auto-discovers domains from folder structure + keyword analysis
7. Onboards new users with actionable guidance

Works on any vault — doesn't assume domains, MOCs, or schema.

Usage:
    python3 vault_topology.py /path/to/notes                    # analyze any vault
    python3 vault_topology.py /path/to/notes --onboard          # first-time guidance
    python3 vault_topology.py /path/to/notes --auto-domain      # discover domain structure
    python3 vault_topology.py /path/to/notes --suggest          # connection suggestions
    python3 vault_topology.py /path/to/notes --json             # JSON output for piping
    python3 vault_topology.py /path/to/notes --onboard --suggest  # full onboarding
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_VAULT = Path(__file__).resolve().parent.parent / "knowledge" / "notes"


def extract_notes(vault_dir):
    """Walk vault directory, extract note titles, content, and wikilinks."""
    notes = {}
    for root, dirs, files in os.walk(vault_dir):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = Path(root) / fname
            rel = fpath.relative_to(vault_dir)
            content = fpath.read_text(errors="replace")

            # Extract title from filename or first heading
            title = fname.replace(".md", "")
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            # Extract wikilinks (strip inline code first to avoid false danglers)
            clean = re.sub(r"`[^`]+`", "", content)  # remove backtick spans
            links = re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]", clean)

            # Extract YAML frontmatter
            frontmatter = {}
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    yaml_text = content[3:end]
                    for line in yaml_text.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            frontmatter[k.strip()] = v.strip().strip('"').strip("'")

            # Extract keywords (words > 4 chars, not common)
            stopwords = {
                "about", "above", "after", "again", "being", "below", "between",
                "could", "different", "doesn", "during", "every", "first", "found",
                "given", "going", "great", "having", "however", "isn't", "itself",
                "known", "large", "later", "level", "makes", "might", "never",
                "notes", "number", "often", "other", "point", "quite", "really",
                "right", "seems", "should", "since", "small", "start", "still",
                "takes", "their", "there", "these", "thing", "think", "those",
                "three", "through", "under", "until", "using", "value", "wants",
                "where", "which", "while", "within", "without", "would", "years",
                "based", "because", "before", "called", "example", "important",
                "means", "needs", "second", "system", "trading", "knowledge",
            }
            words = re.findall(r"[a-z]{5,}", content.lower())
            keyword_freq = defaultdict(int)
            for w in words:
                if w not in stopwords:
                    keyword_freq[w] += 1
            # Top keywords by frequency
            top_keywords = sorted(keyword_freq.items(), key=lambda x: -x[1])[:15]
            keywords = [w for w, c in top_keywords if c >= 2]

            folder = str(rel.parent) if str(rel.parent) != "." else "root"

            notes[str(rel)] = {
                "title": title,
                "path": str(rel),
                "folder": folder,
                "links_out": links,
                "frontmatter": frontmatter,
                "keywords": keywords,
                "size": len(content),
            }

    return notes


def build_graph(notes):
    """Build directed graph from wikilinks. Resolve link targets to file paths."""
    # Build title → path lookup
    title_to_path = {}
    for path, note in notes.items():
        title_to_path[note["title"].lower()] = path
        # Also index by filename stem
        stem = Path(path).stem.lower()
        title_to_path[stem] = path

    # Build adjacency
    outgoing = defaultdict(set)
    incoming = defaultdict(set)
    dangling = defaultdict(list)

    for path, note in notes.items():
        for link in note["links_out"]:
            target = title_to_path.get(link.lower())
            if target and target != path:
                outgoing[path].add(target)
                incoming[target].add(path)
            elif not target:
                dangling[path].append(link)

    return outgoing, incoming, dangling


def find_clusters(notes, outgoing, incoming):
    """Find connected components (treating graph as undirected)."""
    visited = set()
    clusters = []

    def dfs(node, cluster):
        if node in visited:
            return
        visited.add(node)
        cluster.add(node)
        for neighbor in outgoing.get(node, set()) | incoming.get(node, set()):
            dfs(neighbor, cluster)

    for path in notes:
        if path not in visited:
            cluster = set()
            dfs(path, cluster)
            clusters.append(cluster)

    clusters.sort(key=len, reverse=True)
    return clusters


def compute_metrics(notes, outgoing, incoming):
    """Compute per-note metrics: degree, betweenness proxy, hub score."""
    metrics = {}
    for path in notes:
        out_deg = len(outgoing.get(path, set()))
        in_deg = len(incoming.get(path, set()))
        total_deg = out_deg + in_deg

        # Role classification
        if in_deg >= 5:
            role = "mega-hub"
        elif total_deg >= 8:
            role = "hub"
        elif in_deg >= 3:
            role = "attractor"
        elif out_deg >= 3 and in_deg >= 1:
            role = "bridge"
        elif out_deg > 0 and in_deg == 0:
            role = "source"
        elif in_deg > 0 and out_deg == 0:
            role = "sink"
        elif total_deg == 0:
            role = "isolated"
        else:
            role = "node"

        metrics[path] = {
            "in": in_deg,
            "out": out_deg,
            "total": total_deg,
            "role": role,
        }

    return metrics


def suggest_connections(notes, outgoing, incoming, clusters, max_suggestions=10):
    """Find notes in different clusters that share keywords → suggest links."""
    suggestions = []

    # Build keyword → notes index
    kw_index = defaultdict(set)
    for path, note in notes.items():
        for kw in note["keywords"]:
            kw_index[kw].add(path)

    # For each pair of clusters, find shared keywords
    cluster_map = {}
    for i, cluster in enumerate(clusters):
        for path in cluster:
            cluster_map[path] = i

    seen_pairs = set()
    for kw, paths in kw_index.items():
        paths = list(paths)
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                a, b = paths[i], paths[j]
                ci, cj = cluster_map.get(a, -1), cluster_map.get(b, -1)
                if ci == cj:
                    continue  # same cluster, skip
                # Different clusters share a keyword
                pair = tuple(sorted([a, b]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                # Count shared keywords
                shared = set(notes[a]["keywords"]) & set(notes[b]["keywords"])
                if len(shared) >= 2:
                    suggestions.append({
                        "note_a": notes[a]["title"],
                        "path_a": a,
                        "cluster_a": ci,
                        "note_b": notes[b]["title"],
                        "path_b": b,
                        "cluster_b": cj,
                        "shared_keywords": sorted(shared),
                        "strength": len(shared),
                    })

    suggestions.sort(key=lambda x: -x["strength"])
    return suggestions[:max_suggestions]


def auto_discover_domains(notes, outgoing, metrics):
    """Auto-discover domains from folder structure + content analysis.

    When the vault is one big connected component (healthy), clusters won't
    help. Instead, use folder structure as primary signal and keyword analysis
    to validate/refine.
    """
    domains = []

    # Group notes by folder
    folder_notes = defaultdict(list)
    for path, note in notes.items():
        folder_notes[note["folder"]].append(path)

    for folder, paths in sorted(folder_notes.items(), key=lambda x: -len(x[1])):
        if len(paths) < 2:
            continue

        # Find the hub of this folder (most connected note)
        hub = max(paths, key=lambda p: metrics[p]["total"])

        # Aggregate keywords for this folder
        all_kw = defaultdict(int)
        for path in paths:
            for kw in notes[path]["keywords"]:
                all_kw[kw] += 1
        top_kw = sorted(all_kw.items(), key=lambda x: -x[1])[:5]

        # Cross-folder connectivity: what % of links go outside this folder?
        # Exclude MOC/index files — they're inherently intra-domain by design
        internal_links = 0
        external_links = 0
        for path in paths:
            if "moc" in path.lower() or "index" in path.lower():
                continue  # MOCs are navigation hubs, not content — skip from ratio
            for target in outgoing.get(path, set()):
                if notes.get(target, {}).get("folder") == folder:
                    internal_links += 1
                else:
                    external_links += 1
        total_links_d = internal_links + external_links
        cohesion = internal_links / total_links_d if total_links_d else 0

        # Note types in this folder
        types = defaultdict(int)
        for p in paths:
            t = notes[p]["frontmatter"].get("type", "unknown")
            types[t] += 1
        dominant_type = max(types.items(), key=lambda x: x[1])[0] if types else "mixed"

        domains.append({
            "folder": folder,
            "size": len(paths),
            "hub": notes[hub]["title"],
            "hub_degree": metrics[hub]["total"],
            "top_keywords": [w for w, c in top_kw],
            "cohesion": round(cohesion, 2),
            "dominant_type": dominant_type,
            "suggested_name": folder.replace("/", " > ").replace("_", " ").title(),
        })

    return domains


def print_report(notes, outgoing, incoming, dangling, clusters, metrics,
                 suggestions=None, domains=None):
    """Print human-readable topology report."""
    total = len(notes)
    total_links = sum(len(v) for v in outgoing.values())
    avg_degree = sum(m["total"] for m in metrics.values()) / total if total else 0
    isolated = sum(1 for m in metrics.values() if m["role"] == "isolated")

    print("=" * 70)
    print("VAULT TOPOLOGY REPORT")
    print("=" * 70)
    print()
    print(f"  Notes:          {total}")
    print(f"  Links:          {total_links}")
    print(f"  Avg degree:     {avg_degree:.1f}")
    print(f"  Clusters:       {len(clusters)} ({len([c for c in clusters if len(c) > 1])} multi-note)")
    print(f"  Isolated notes: {isolated}")
    print(f"  Dangling links: {sum(len(v) for v in dangling.values())}")

    # Role distribution
    role_counts = defaultdict(int)
    for m in metrics.values():
        role_counts[m["role"]] += 1
    print(f"\n  Roles: ", end="")
    for role in ["mega-hub", "hub", "attractor", "bridge", "source", "sink", "node", "isolated"]:
        if role_counts[role]:
            print(f"{role}={role_counts[role]} ", end="")
    print()

    # Top nodes by degree
    top = sorted(metrics.items(), key=lambda x: -x[1]["total"])[:15]
    print(f"\n  TOP NODES BY CONNECTIVITY:")
    print(f"  {'Note':<50} {'In':>4} {'Out':>4} {'Deg':>4}  Role")
    print(f"  {'-'*75}")
    for path, m in top:
        if m["total"] == 0:
            break
        title = notes[path]["title"][:48]
        print(f"  {title:<50} {m['in']:>4} {m['out']:>4} {m['total']:>4}  {m['role']}")

    # Clusters
    print(f"\n  CLUSTERS (multi-note only):")
    for i, cluster in enumerate(clusters):
        if len(cluster) < 2:
            continue
        hub = max(cluster, key=lambda p: metrics[p]["total"])
        hub_title = notes[hub]["title"][:40]
        folders = set(notes[p]["folder"] for p in cluster)
        print(f"    C{i}: {len(cluster)} notes, hub={hub_title}, folders={folders}")

    # Suggestions
    if suggestions:
        print(f"\n  SUGGESTED CONNECTIONS (cross-cluster, shared keywords):")
        for s in suggestions[:7]:
            a = s["note_a"][:30]
            b = s["note_b"][:30]
            kw = ", ".join(s["shared_keywords"][:4])
            print(f"    [{s['strength']} shared] {a} ↔ {b}")
            print(f"              keywords: {kw}")

    # Auto-discovered domains
    if domains:
        print(f"\n  AUTO-DISCOVERED DOMAINS:")
        for d in domains[:10]:
            kw = ", ".join(d["top_keywords"][:4])
            cohesion_pct = int(d["cohesion"] * 100)
            print(f"    {d['suggested_name']} ({d['size']} notes, cohesion={cohesion_pct}%, hub={d['hub'][:35]})")
            print(f"      keywords: {kw}")

    # Health warnings
    print(f"\n  HEALTH:")
    warnings = []
    if avg_degree < 2:
        warnings.append(f"Low connectivity (avg {avg_degree:.1f} < 2.0) — notes are weakly linked")
    if isolated > total * 0.2:
        warnings.append(f"High isolation ({isolated}/{total} = {100*isolated/total:.0f}%) — many orphan notes")
    if len(clusters) > total * 0.3:
        warnings.append(f"Fragmented ({len(clusters)} clusters for {total} notes) — knowledge is siloed")
    dang_count = sum(len(v) for v in dangling.values())
    if dang_count > 5:
        warnings.append(f"{dang_count} dangling links — references to non-existent notes")

    if warnings:
        for w in warnings:
            print(f"    ⚠ {w}")
    else:
        print(f"    ✓ Vault topology is healthy")

    print()


def print_onboard(notes, outgoing, incoming, dangling, clusters, metrics, domains):
    """Print onboarding guidance based on vault's actual structure."""
    total = len(notes)
    total_links = sum(len(v) for v in outgoing.values())
    avg_degree = sum(m["total"] for m in metrics.values()) / total if total else 0
    isolated = sum(1 for m in metrics.values() if m["role"] == "isolated")

    print("=" * 70)
    print("VAULT ONBOARDING REPORT")
    print("=" * 70)
    print()

    # Phase detection — what stage is this vault at?
    if total < 10:
        phase = "seed"
        print("  PHASE: Seed (< 10 notes)")
        print("  Your vault is just starting. Focus on capturing ideas, not structure.")
        print("  Connections will emerge naturally as you write more notes.")
    elif avg_degree < 1.5:
        phase = "disconnected"
        print("  PHASE: Disconnected (low link density)")
        print("  You have notes but they're not linked to each other.")
        print("  Add [[wikilinks]] between related notes to build structure.")
    elif len(clusters) > total * 0.3:
        phase = "fragmented"
        print("  PHASE: Fragmented (many isolated clusters)")
        print("  Notes are clustered but clusters aren't connected to each other.")
        print("  Focus on bridge notes that connect different topic areas.")
    elif isolated > total * 0.15:
        phase = "growing"
        print("  PHASE: Growing (some orphan notes)")
        print(f"  {isolated} notes aren't connected to anything yet.")
        print("  Link these orphans to existing notes or group them into folders.")
    else:
        phase = "mature"
        print("  PHASE: Mature (well-connected graph)")
        print("  Your vault has good connectivity. Focus on depth and cross-domain links.")

    # Auto-discovered structure
    if domains:
        print(f"\n  YOUR VAULT HAS {len(domains)} NATURAL DOMAINS:")
        for d in domains:
            cohesion_pct = int(d["cohesion"] * 100)
            print(f"    - {d['suggested_name']}: {d['size']} notes, {cohesion_pct}% cohesion")

        # Domain health advice
        low_cohesion = [d for d in domains if d["cohesion"] < 0.2]
        high_cohesion = [d for d in domains if d["cohesion"] > 0.6]
        if low_cohesion:
            print(f"\n  LOW-COHESION DOMAINS (notes link outside more than inside):")
            for d in low_cohesion:
                print(f"    {d['suggested_name']}: {int(d['cohesion']*100)}% — consider splitting or merging")
        if high_cohesion:
            print(f"\n  HIGH-COHESION DOMAINS (self-contained clusters):")
            for d in high_cohesion:
                print(f"    {d['suggested_name']}: {int(d['cohesion']*100)}% — add cross-domain bridges")

    # Hub identification
    hubs = [(p, m) for p, m in metrics.items() if m["role"] in ("mega-hub", "hub")]
    if hubs:
        top_hubs = sorted(hubs, key=lambda x: -x[1]["total"])[:5]
        print(f"\n  YOUR TOP HUBS (most-connected notes — these are your MOCs/indexes):")
        for p, m in top_hubs:
            print(f"    {notes[p]['title'][:50]} ({m['total']} connections)")

    # Orphan rescue
    orphans = [p for p, m in metrics.items() if m["role"] == "isolated"]
    if orphans:
        print(f"\n  ORPHAN NOTES ({len(orphans)} — no connections at all):")
        for p in orphans[:10]:
            kw = ", ".join(notes[p]["keywords"][:3]) if notes[p]["keywords"] else "no keywords"
            print(f"    {notes[p]['title'][:40]} ({kw})")
        if len(orphans) > 10:
            print(f"    ... and {len(orphans) - 10} more")

    # Dangling links
    if dangling:
        dang_count = sum(len(v) for v in dangling.values())
        print(f"\n  DANGLING LINKS ({dang_count} — references to non-existent notes):")
        all_dangling = []
        for path, links in dangling.items():
            for link in links:
                all_dangling.append((link, notes[path]["title"]))
        for link, source in all_dangling[:8]:
            print(f"    [[{link}]] (from {source[:35]})")
        if len(all_dangling) > 8:
            print(f"    ... and {len(all_dangling) - 8} more")
        print("  Create these notes or fix the link targets.")

    # Actionable next steps
    print(f"\n  RECOMMENDED ACTIONS:")
    actions = []
    if phase == "seed":
        actions.append("Write more notes — aim for 20+ before worrying about structure")
        actions.append("Use [[wikilinks]] as you write to connect ideas naturally")
    elif phase == "disconnected":
        actions.append("Add [[wikilinks]] — each note should link to at least 2 others")
        actions.append("Create index/MOC notes for your main topics")
    elif phase == "fragmented":
        actions.append("Write bridge notes connecting your biggest clusters")
        actions.append("Create a top-level index linking to each domain's hub note")
    else:
        if avg_degree > 10:
            actions.append("Strong connectivity — focus on content quality over more links")
        if low_cohesion:
            actions.append(f"Review low-cohesion domains: {', '.join(d['suggested_name'] for d in low_cohesion[:3])}")
        if orphans:
            actions.append(f"Connect {len(orphans)} orphan notes to related topics")

    if dangling:
        actions.append(f"Fix {sum(len(v) for v in dangling.values())} dangling links")

    actions.append("Run with --suggest to find cross-domain connection opportunities")
    actions.append("Run periodically (weekly) to track vault health over time")

    for i, action in enumerate(actions, 1):
        print(f"    {i}. {action}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Vault Topology Analyzer")
    parser.add_argument("vault_dir", nargs="?", default=str(DEFAULT_VAULT),
                        help="Path to vault directory (default: knowledge/notes)")
    parser.add_argument("--suggest", action="store_true",
                        help="Include cross-cluster connection suggestions")
    parser.add_argument("--auto-domain", action="store_true",
                        help="Auto-discover domains from cluster structure")
    parser.add_argument("--onboard", action="store_true",
                        help="Onboarding mode — actionable guidance for new users")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of human-readable")
    args = parser.parse_args()

    vault_dir = Path(args.vault_dir)
    if not vault_dir.is_dir():
        print(f"Error: {vault_dir} is not a directory")
        sys.exit(1)

    # Extract and analyze
    notes = extract_notes(vault_dir)
    if not notes:
        print(f"No .md files found in {vault_dir}")
        sys.exit(1)

    outgoing, incoming, dangling = build_graph(notes)
    clusters = find_clusters(notes, outgoing, incoming)
    metrics = compute_metrics(notes, outgoing, incoming)

    suggestions = suggest_connections(notes, outgoing, incoming, clusters) if args.suggest else None
    # Onboard mode always needs domains
    if args.auto_domain or args.onboard:
        domains = auto_discover_domains(notes, outgoing, metrics)
    else:
        domains = None

    if args.onboard:
        print_onboard(notes, outgoing, incoming, dangling, clusters, metrics, domains)
    elif args.json:
        output = {
            "total_notes": len(notes),
            "total_links": sum(len(v) for v in outgoing.values()),
            "avg_degree": round(sum(m["total"] for m in metrics.values()) / len(notes), 2),
            "clusters": len(clusters),
            "isolated": sum(1 for m in metrics.values() if m["role"] == "isolated"),
            "top_nodes": [
                {"title": notes[p]["title"], "path": p, **m}
                for p, m in sorted(metrics.items(), key=lambda x: -x[1]["total"])[:15]
                if m["total"] > 0
            ],
            "cluster_sizes": [len(c) for c in clusters],
        }
        if suggestions:
            output["suggestions"] = suggestions
        if domains:
            output["domains"] = domains
        print(json.dumps(output, indent=2))
    else:
        print_report(notes, outgoing, incoming, dangling, clusters, metrics,
                     suggestions, domains)


if __name__ == "__main__":
    main()
