#!/usr/bin/env python3
"""
Vault Research Suggestions — lint the vault for knowledge gaps and research opportunities.

Goes beyond structural health (orphans, danglers) to ask:
- What questions does the vault suggest but not answer?
- What claims are weak (low confidence, few supporting notes)?
- What connections are implied but not explicit?
- What domains are thin relative to their importance?

Stolen from Karpathy's LLM Wiki "lint" concept: health checks that suggest
new investigations, not just fixes.

Usage:
    python3 scripts/vault_research_suggestions.py              # full analysis
    python3 scripts/vault_research_suggestions.py --quick      # just gap detection
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
VAULT = BASE / "knowledge" / "notes"
CHAINS = BASE / "logs" / "reasoning_chains.jsonl"
BREADCRUMBS = BASE / "logs" / "session_breadcrumbs.jsonl"

WIKILINK_RE = re.compile(r"\[\[(.+?)\]\]")


def scan_vault():
    """Scan all vault notes for metadata and links."""
    notes = {}
    for md in VAULT.rglob("*.md"):
        rel = md.relative_to(VAULT)
        content = md.read_text(errors="ignore")

        # Extract frontmatter
        status = "unknown"
        domains = []
        note_type = "unknown"
        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                fm = content[3:fm_end]
                for line in fm.splitlines():
                    if line.startswith("status:"):
                        status = line.split(":", 1)[1].strip().strip('"')
                    if line.startswith("type:"):
                        note_type = line.split(":", 1)[1].strip().strip('"')
                    if line.startswith("domains:"):
                        domains = re.findall(r'"([^"]+)"', line)

        # Extract wikilinks
        links = WIKILINK_RE.findall(content)

        notes[str(rel)] = {
            "path": str(rel),
            "status": status,
            "type": note_type,
            "domains": domains,
            "links_out": links,
            "word_count": len(content.split()),
        }

    return notes


def find_dangling_links(notes):
    """Find wikilinks that point to non-existent notes."""
    all_stems = set()
    for path in notes:
        stem = Path(path).stem
        all_stems.add(stem)

    danglers = Counter()
    for note in notes.values():
        for link in note["links_out"]:
            if link not in all_stems and link + ".md" not in all_stems:
                danglers[link] += 1

    return danglers


def find_thin_domains(notes):
    """Find domains with few notes relative to how often they're referenced."""
    domain_counts = Counter()
    domain_refs = Counter()

    for note in notes.values():
        for d in note["domains"]:
            domain_counts[d] += 1
        for link in note["links_out"]:
            # If a link contains a domain-like name, count as domain reference
            for d in domain_counts:
                if d.lower() in link.lower():
                    domain_refs[d] += 1

    thin = []
    for d, count in domain_counts.items():
        if count < 5:
            thin.append((d, count, domain_refs.get(d, 0)))

    return sorted(thin, key=lambda x: x[2], reverse=True)


def find_stale_claims(notes, days=14):
    """Find notes older than N days that haven't been updated."""
    stale = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for path, note in notes.items():
        md_path = VAULT / path
        mtime = datetime.fromtimestamp(md_path.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff and note["status"] == "current":
            stale.append((path, mtime, note["word_count"]))

    return sorted(stale, key=lambda x: x[1])[:20]


def find_question_gaps(notes):
    """Analyze reasoning chains for unanswered questions and dead ends."""
    gaps = []

    if CHAINS.exists():
        for line in CHAINS.read_text().splitlines():
            try:
                chain = json.loads(line)
                outcome = chain.get("outcome", "")
                pattern = chain.get("pattern", "")

                # Dead ends are research opportunities
                if "dead end" in outcome.lower() or "unknown" in outcome.lower():
                    gaps.append({
                        "type": "dead_end",
                        "trigger": chain.get("trigger", "?"),
                        "outcome": outcome[:100],
                    })

                # Chains with no reusable pattern suggest unexplored territory
                if chain.get("reusable") is False:
                    gaps.append({
                        "type": "non_reusable",
                        "trigger": chain.get("trigger", "?"),
                        "outcome": outcome[:100],
                    })
            except json.JSONDecodeError:
                continue

    return gaps[:20]


def find_implied_connections(notes):
    """Find notes that share topics but aren't linked."""
    # Simple: find pairs of notes in the same domain that don't link to each other
    by_domain = defaultdict(list)
    for path, note in notes.items():
        for d in note["domains"]:
            by_domain[d].append(path)

    unlinked = []
    for domain, paths in by_domain.items():
        if len(paths) < 2:
            continue
        for i, p1 in enumerate(paths):
            stems1 = set(notes[p1]["links_out"])
            for p2 in paths[i + 1:]:
                stem2 = Path(p2).stem
                stem1 = Path(p1).stem
                if stem2 not in stems1 and stem1 not in set(notes[p2]["links_out"]):
                    # Check word overlap for relevance
                    unlinked.append((p1, p2, domain))

    return unlinked[:20]


def main():
    parser = argparse.ArgumentParser(description="Vault Research Suggestions")
    parser.add_argument("--quick", action="store_true", help="Quick gap detection only")
    args = parser.parse_args()

    print("Vault Research Suggestions")
    print("=" * 55)
    print()

    notes = scan_vault()
    print(f"Scanned {len(notes)} notes")
    print()

    # 1. Dangling links = demand signals
    danglers = find_dangling_links(notes)
    if danglers:
        top = danglers.most_common(10)
        print("DEMAND SIGNALS (dangling links — notes the vault wants but doesn't have):")
        for link, count in top:
            print(f"  [[{link}]] — referenced {count}x")
        print()

    # 2. Question gaps from reasoning chains
    gaps = find_question_gaps(notes)
    if gaps:
        dead_ends = [g for g in gaps if g["type"] == "dead_end"]
        if dead_ends:
            print(f"DEAD ENDS ({len(dead_ends)} chains led nowhere — research opportunities):")
            for g in dead_ends[:5]:
                print(f"  Trigger: {g['trigger'][:60]}")
                print(f"  Outcome: {g['outcome'][:60]}")
                print()

    if args.quick:
        return

    # 3. Thin domains
    thin = find_thin_domains(notes)
    if thin:
        print("THIN DOMAINS (few notes but frequently referenced):")
        for domain, count, refs in thin[:5]:
            print(f"  {domain}: {count} notes, {refs} references")
        print()

    # 4. Stale claims
    stale = find_stale_claims(notes)
    if stale:
        print(f"STALE CLAIMS ({len(stale)} current notes >14 days old):")
        for path, mtime, wc in stale[:10]:
            days_old = (datetime.now(timezone.utc) - mtime).days
            print(f"  {Path(path).stem} — {days_old}d old, {wc} words")
        print()

    # 5. Implied connections
    unlinked = find_implied_connections(notes)
    if unlinked:
        print(f"IMPLIED CONNECTIONS ({len(unlinked)} same-domain note pairs without links):")
        for p1, p2, domain in unlinked[:10]:
            print(f"  [{domain}] {Path(p1).stem} ↔ {Path(p2).stem}")
        print()

    print("SUGGESTED RESEARCH QUESTIONS:")
    print("  1. What do the dangling links tell us about what the vault needs?")
    print("  2. Can dead-end chains be revisited with new data?")
    print("  3. Which thin domains should be expanded vs archived?")
    print("  4. Do stale claims still hold given recent system changes?")
    print("  5. Would the implied connections produce new insights if wired?")


if __name__ == "__main__":
    main()
