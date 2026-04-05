#!/usr/bin/env python3
"""
Generate VAULT_INDEX.md — lightweight progressive disclosure for session start.

Hermes-inspired: CC knows what exists without loading the full vault.
Level 0: VAULT_INDEX.md (names, domains, stats) — always available
Level 1: FTS5 query (relevant snippets) — on demand
Level 2: Full note (read file) — when needed

Usage:
    python3 scripts/generate_vault_index.py
"""

import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

VAULT_DIR = Path(__file__).parent.parent / "knowledge" / "notes"
OUTPUT = Path(__file__).parent.parent / "knowledge" / "VAULT_INDEX.md"
DB_PATH = Path(__file__).parent.parent / "data" / "vault_index.db"


def main():
    notes = []
    domains = defaultdict(int)
    types = defaultdict(int)
    total_links = 0
    recent = []
    now = datetime.now()
    week_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d')

    for root, dirs, files in os.walk(VAULT_DIR):
        for f in files:
            if not f.endswith('.md'):
                continue
            path = os.path.join(root, f)
            title = f.replace('.md', '')
            subfolder = os.path.relpath(root, VAULT_DIR)

            try:
                with open(path) as fh:
                    content = fh.read()
            except:
                continue

            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            total_links += len(links)

            # Parse frontmatter
            fm = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            fm[k.strip()] = v.strip().strip('"').strip("'")

            note_type = fm.get('type', 'unknown')
            domain_str = fm.get('domains', subfolder)
            date = fm.get('date_learned', '')
            summary = fm.get('summary', '')[:80]

            types[note_type] += 1
            domains[subfolder] += 1
            notes.append({'title': title, 'type': note_type, 'folder': subfolder, 'date': date, 'summary': summary})

            if date >= week_ago:
                recent.append({'title': title, 'type': note_type, 'date': date, 'summary': summary})

    # Sort recent by date
    recent.sort(key=lambda x: x['date'], reverse=True)

    # Generate markdown
    lines = []
    lines.append(f"# Vault Index (auto-generated)")
    lines.append(f"## Updated: {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"## Stats: {len(notes)} notes | {total_links} links | {total_links/len(notes):.1f} links/note")
    lines.append("")

    lines.append("### Domain Folders")
    for folder, count in sorted(domains.items(), key=lambda x: -x[1]):
        lines.append(f"- **{folder}/** ({count} notes)")
    lines.append("")

    lines.append("### Note Types")
    type_str = " | ".join(f"{t}={c}" for t, c in sorted(types.items(), key=lambda x: -x[1]))
    lines.append(type_str)
    lines.append("")

    lines.append("### Hot Notes (updated last 7 days)")
    for n in recent[:20]:
        lines.append(f"- [{n['date']}] ({n['type']}) **{n['title']}** — {n['summary']}")
    if len(recent) > 20:
        lines.append(f"- ...+{len(recent)-20} more")
    lines.append("")

    lines.append("### Search")
    lines.append("```bash")
    lines.append("# FTS5 full-text search (milliseconds)")
    lines.append('python3 scripts/index_vault.py --query "your search terms"')
    lines.append("")
    lines.append("# Spreading activation (graph + semantic)")
    lines.append('python3 scripts/vault_search.py "your search terms"')
    lines.append("")
    lines.append("# Community detection")
    lines.append("python3 scripts/vault_communities.py")
    lines.append("```")

    content = "\n".join(lines)
    with open(OUTPUT, 'w') as f:
        f.write(content)

    print(f"  Generated: {OUTPUT}")
    print(f"  {len(notes)} notes, {len(recent)} recent, {len(content)} chars")


if __name__ == "__main__":
    main()
