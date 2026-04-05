#!/usr/bin/env python3
"""
Cross-Agent Knowledge Flow Tracker — measures whether agents USE each other's work.

Stolen from CORAL (arXiv 2604.01658): the key mechanism for multi-agent evolution
is knowledge reuse, not just knowledge production. This script measures flow.

Scans vault notes for provenance (created_by) and checks backlinks to see which
OTHER agents referenced the note. High reuse = knowledge flowing. Zero reuse = siloed.

Usage:
    python3 scripts/knowledge_flow_tracker.py              # full report
    python3 scripts/knowledge_flow_tracker.py --summary     # just the flow matrix
"""

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
VAULT = BASE / "knowledge" / "notes"
CHAINS = BASE / "logs" / "reasoning_chains.jsonl"

WIKILINK_RE = re.compile(r"\[\[(.+?)\]\]")

# Known agents — expand as team grows
AGENTS = {"team-lead", "brutus", "scout", "archivist", "qa", "observer", "metacognizer", "wallet-dive", "auditor"}


def scan_provenance():
    """Scan vault notes for created_by and who references them."""
    notes = {}

    for md in VAULT.rglob("*.md"):
        content = md.read_text(errors="ignore")
        rel = str(md.relative_to(VAULT))
        stem = md.stem

        # Extract created_by from frontmatter
        created_by = None
        validated_by = None
        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                fm = content[3:fm_end]
                for line in fm.splitlines():
                    if line.strip().startswith("created_by:"):
                        created_by = line.split(":", 1)[1].strip().strip('"')
                    if line.strip().startswith("validated_by:"):
                        validated_by = line.split(":", 1)[1].strip().strip('"')

        # Extract outgoing wikilinks
        links_out = WIKILINK_RE.findall(content)

        notes[stem] = {
            "path": rel,
            "created_by": created_by,
            "validated_by": validated_by,
            "links_out": links_out,
            "referenced_by": [],  # populated below
        }

    # Build backlinks
    for stem, note in notes.items():
        for link in note["links_out"]:
            link_stem = link.split("|")[0] if "|" in link else link
            if link_stem in notes:
                notes[link_stem]["referenced_by"].append(stem)

    return notes


def infer_agent_from_path(path):
    """Infer which agent likely created a note based on its path."""
    path_lower = path.lower()
    if "scout-findings" in path_lower:
        return "scout"
    if "cc-session" in path_lower or "claudius-corner" in path_lower:
        return "team-lead"
    if "pattern-" in path_lower:
        return "metacognizer"
    if "bug-" in path_lower:
        return "qa"
    if "wallet-" in path_lower:
        return "wallet-dive"
    if "experiment-" in path_lower:
        return "team-lead"
    return None


def compute_flow_matrix(notes):
    """Compute agent-to-agent knowledge flow matrix.

    flow[A][B] = number of notes created by A that are referenced by notes
    from B. High flow[scout][brutus] = Brutus reviews Scout's work (good).
    Zero flow[scout][archivist] = Archivist doesn't wire Scout's findings (gap).
    """
    flow = defaultdict(lambda: defaultdict(int))
    reuse_scores = []

    for stem, note in notes.items():
        creator = note["created_by"] or infer_agent_from_path(note["path"])
        if not creator:
            continue

        # Who references this note?
        referencing_agents = set()
        for ref_stem in note["referenced_by"]:
            ref_note = notes.get(ref_stem, {})
            ref_creator = ref_note.get("created_by") or infer_agent_from_path(ref_note.get("path", ""))
            if ref_creator and ref_creator != creator:
                referencing_agents.add(ref_creator)
                flow[creator][ref_creator] += 1

        reuse_scores.append({
            "note": stem,
            "creator": creator,
            "reuse_count": len(referencing_agents),
            "reused_by": list(referencing_agents),
        })

    return flow, reuse_scores


def main():
    parser = argparse.ArgumentParser(description="Cross-Agent Knowledge Flow Tracker")
    parser.add_argument("--summary", action="store_true", help="Just the flow matrix")
    args = parser.parse_args()

    notes = scan_provenance()
    flow, reuse_scores = compute_flow_matrix(notes)

    # Count notes per creator
    creator_counts = Counter()
    for note in notes.values():
        creator = note["created_by"] or infer_agent_from_path(note["path"])
        if creator:
            creator_counts[creator] += 1

    print(f"Knowledge Flow Tracker")
    print(f"{'=' * 60}")
    print(f"  Total notes scanned: {len(notes)}")
    print(f"  Notes with created_by: {sum(1 for n in notes.values() if n['created_by'])}")
    print(f"  Notes with inferred creator: {sum(1 for n in notes.values() if infer_agent_from_path(n['path']))}")
    print()

    # Creator distribution
    print("NOTES PER CREATOR:")
    for creator, count in creator_counts.most_common():
        print(f"  {creator:15s}: {count}")
    print()

    # Flow matrix
    all_agents = sorted(set(list(flow.keys()) + [a for d in flow.values() for a in d]))
    if all_agents:
        print("KNOWLEDGE FLOW MATRIX (creator → referencer):")
        header = f"  {'from→to':15s}" + "".join(f"{a[:8]:>9s}" for a in all_agents)
        print(header)
        for creator in all_agents:
            row = f"  {creator:15s}"
            for referencer in all_agents:
                val = flow[creator][referencer]
                row += f"{val:>9d}" if val > 0 else f"{'·':>9s}"

            print(row)
        print()

    if args.summary:
        return

    # Reuse analysis
    reused = [r for r in reuse_scores if r["reuse_count"] > 0]
    siloed = [r for r in reuse_scores if r["reuse_count"] == 0]

    print(f"REUSE ANALYSIS:")
    print(f"  Notes with cross-agent reuse: {len(reused)} ({len(reused)/len(reuse_scores)*100:.0f}%)" if reuse_scores else "")
    print(f"  Siloed notes (no cross-agent refs): {len(siloed)}")
    print()

    # Top reused notes
    top = sorted(reuse_scores, key=lambda x: -x["reuse_count"])[:10]
    if top and top[0]["reuse_count"] > 0:
        print("TOP REUSED NOTES (most cross-agent references):")
        for r in top:
            if r["reuse_count"] == 0:
                break
            print(f"  {r['note'][:50]:50s} creator={r['creator']:12s} reused_by={r['reused_by']}")
        print()

    # Siloed creators (agents whose work isn't referenced by others)
    siloed_creators = defaultdict(int)
    for r in siloed:
        siloed_creators[r["creator"]] += 1

    if siloed_creators:
        print("SILOED WORK (creator's notes not referenced by other agents):")
        for creator, count in sorted(siloed_creators.items(), key=lambda x: -x[1]):
            total = creator_counts[creator]
            pct = count / total * 100 if total else 0
            print(f"  {creator:15s}: {count}/{total} siloed ({pct:.0f}%)")


if __name__ == "__main__":
    main()
