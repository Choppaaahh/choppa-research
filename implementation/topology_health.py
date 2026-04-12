#!/usr/bin/env python3
"""Topology health — per-domain integration ratios and alerts."""

import json
import re
from collections import defaultdict
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent / "knowledge" / "notes"
LOG = Path(__file__).resolve().parent.parent / "logs"

SKIP_STEMS = {
    'index', 'grid-mechanics', 'fee-model', 'bug-patterns', 'coin-evaluation',
    'safety-systems', 'microstructure-signals', 'regime-detection',
    'operational-procedures', 'lessons-learned', 'build-roadmap',
    'domain-1', 'domain-2', 'domain-3', 'domain-4',
    'scheduled-reports', 'research-trading', 'geopol', 'colby', 'choppa',
    'navigation', 'dashboard', 'session-log', 'agent-coordination',
    'market-sessions', 'cc-operational', 'consciousness-framework',
    'consciousness-empirical', 'consciousness-identity', 'consciousness-literature',
}


def scan():
    notes = {}  # stem → {domains, links_out, links_in}
    for f in VAULT.rglob("*.md"):
        stem = f.stem
        if stem in SKIP_STEMS:
            continue
        content = f.read_text(errors="replace")
        domains = []
        links = set()
        for line in content.split("\n"):
            if line.startswith("domains:"):
                raw = line.replace("domains:", "").strip().strip("[]")
                for d in raw.split(","):
                    d = d.strip().strip('"').strip("'")
                    if d:
                        domains.append(d)
            # Find wikilinks
            for m in re.findall(r'\[\[([^\]]+)\]\]', line):
                links.add(m)
        notes[stem] = {"domains": domains, "links_out": links, "path": str(f)}

    # Compute incoming links
    for stem, data in notes.items():
        data["links_in"] = set()
    for stem, data in notes.items():
        for link in data["links_out"]:
            if link in notes:
                notes[link]["links_in"].add(stem)

    # Per-domain stats
    domain_notes = defaultdict(list)
    for stem, data in notes.items():
        for d in data["domains"]:
            domain_notes[d].append(stem)

    # Cross-domain ratio per domain
    results = {}
    for domain, stems in sorted(domain_notes.items(), key=lambda x: len(x[1]), reverse=True):
        total_links = 0
        cross_links = 0
        for stem in stems:
            for link in notes[stem]["links_out"]:
                if link in notes:
                    total_links += 1
                    link_domains = notes[link]["domains"]
                    if domain not in link_domains:
                        cross_links += 1
        ratio = cross_links / total_links if total_links > 0 else 0
        results[domain] = {
            "notes": len(stems),
            "total_links": total_links,
            "cross_links": cross_links,
            "ratio": round(ratio, 3),
        }

    return notes, results


def main():
    notes, results = scan()

    print(f"Vault: {len(notes)} notes (excluding MOCs)")
    print()

    alerts = []
    for domain in sorted(results, key=lambda d: results[d]["ratio"]):
        r = results[domain]
        if r["notes"] < 3:
            continue
        pct = int(r["ratio"] * 100)
        bar = "#" * min(pct, 40)
        flag = " *** LOW" if r["ratio"] < 0.15 and r["notes"] >= 5 else ""
        print(f"  {domain:>30}: {pct:3d}%  ({r['notes']} notes, {r['cross_links']}/{r['total_links']} cross){flag}")
        if r["ratio"] < 0.15 and r["notes"] >= 5:
            alerts.append(f"{domain} at {pct}% ({r['notes']} notes)")

    print()
    if alerts:
        print(f"ALERTS: {len(alerts)} low-integration domains")
        for a in alerts:
            print(f"  [WARN] {a}")
    else:
        print("No alerts — all domains above threshold")

    # Log
    try:
        log_entry = {
            "ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "note_count": len(notes),
            "domains": len(results),
            "alerts": alerts,
            "results": {d: r for d, r in results.items() if r["notes"] >= 3},
        }
        with open(LOG / "topology_health.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
