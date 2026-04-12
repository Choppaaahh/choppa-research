#!/usr/bin/env python3
"""
Vault Probe QA — MemMA steal (arXiv 2603.18718).

After each compile or session, generate probe questions the vault SHOULD answer.
Query the vault. Failed probes = memory gaps to repair.

Flow:
1. Read recent breadcrumbs (last 20)
2. Generate probe questions from breadcrumbs (what should the vault know?)
3. Query vault_search.py for each probe
4. Score: does the top result actually answer the question?
5. Failed probes → log as gaps for Archivist repair

Usage:
    python3 scripts/vault_probe_qa.py                    # run probes from recent breadcrumbs
    python3 scripts/vault_probe_qa.py --session XLIV     # probes from specific session
    python3 scripts/vault_probe_qa.py --custom "query"   # single custom probe
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
BREADCRUMBS = REPO / "logs" / "session_breadcrumbs.jsonl"
CHAINS = REPO / "logs" / "reasoning_chains.jsonl"
PROBE_LOG = REPO / "logs" / "vault_probe_qa.jsonl"
VAULT_SEARCH = REPO / "scripts" / "vault_search.py"

parser = argparse.ArgumentParser()
parser.add_argument("--session", type=str, default="", help="Filter breadcrumbs by session")
parser.add_argument("--custom", type=str, default="", help="Single custom probe query")
parser.add_argument("--n", type=int, default=10, help="Number of probes to generate")
args = parser.parse_args()


def load_recent_breadcrumbs(n=20, session_filter=""):
    """Load last N breadcrumbs, optionally filtered by session."""
    crumbs = []
    if not BREADCRUMBS.exists():
        return crumbs
    for line in BREADCRUMBS.read_text(errors="replace").splitlines():
        try:
            c = json.loads(line)
            if session_filter and session_filter.lower() not in c.get("content", "").lower():
                continue
            crumbs.append(c)
        except:
            continue
    return crumbs[-n:]


def load_recent_chains(n=10):
    """Load last N reasoning chains."""
    chains = []
    if not CHAINS.exists():
        return chains
    for line in CHAINS.read_text(errors="replace").splitlines():
        try:
            chains.append(json.loads(line))
        except:
            continue
    return chains[-n:]


def generate_probes(breadcrumbs, chains, max_probes=10):
    """Generate probe questions from recent breadcrumbs and chains.
    Each probe is a question the vault SHOULD be able to answer."""
    probes = []

    for c in breadcrumbs:
        content = c.get("content", "")
        crumb_type = c.get("type", "")

        # Decision breadcrumbs → "Why did we decide X?"
        if crumb_type == "decision" and len(content) > 30:
            # Extract the decision topic
            topic = content.split("→")[0].strip() if "→" in content else content[:80]
            probes.append({
                "query": topic,
                "expected": "vault note explaining this decision",
                "source": f"breadcrumb:{crumb_type}",
                "content": content[:100],
            })

        # Finding breadcrumbs → "Do we have data on X?"
        elif crumb_type == "finding" and len(content) > 30:
            topic = content.split(":")[0].strip() if ":" in content else content[:60]
            probes.append({
                "query": topic,
                "expected": "vault note documenting this finding",
                "source": f"breadcrumb:{crumb_type}",
                "content": content[:100],
            })

        # Insight breadcrumbs → "Is this insight captured?"
        elif crumb_type == "insight" and len(content) > 30:
            probes.append({
                "query": content[:80],
                "expected": "vault note capturing this insight",
                "source": f"breadcrumb:{crumb_type}",
                "content": content[:100],
            })

    # Chains → "Is the pattern from this chain in the vault?"
    for chain in chains:
        pattern = chain.get("pattern", "")
        if pattern and pattern != "?" and len(pattern) > 5:
            probes.append({
                "query": pattern.replace("-", " "),
                "expected": f"vault note for pattern: {pattern}",
                "source": "chain",
                "content": chain.get("trigger", "")[:100],
            })

    # Deduplicate by query similarity (crude: first 30 chars)
    seen = set()
    unique = []
    for p in probes:
        key = p["query"][:30].lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique[:max_probes]


def run_vault_search(query, top=3):
    """Run vault_search.py and parse results."""
    try:
        result = subprocess.run(
            ["python3", str(VAULT_SEARCH), query, "--top", str(top)],
            capture_output=True, text=True, timeout=30, cwd=str(REPO)
        )
        output = result.stdout

        # Parse results
        results = []
        for line in output.splitlines():
            # Match: "   1. [0.70] (seed) note-name"
            m = re.match(r'\s+\d+\.\s+\[([0-9.]+)\]\s+\((\w+)\)\s+(.+)', line)
            if m:
                results.append({
                    "score": float(m.group(1)),
                    "type": m.group(2),
                    "note": m.group(3).strip(),
                })
            # Match summary line after note name
            elif results and line.strip() and not line.startswith("=") and not line.startswith("RESULTS"):
                results[-1]["summary"] = line.strip()

        return results
    except Exception as e:
        return [{"error": str(e)}]


def score_probe(probe, results):
    """Score whether vault results answer the probe question.
    Returns: PASS (strong match), WEAK (partial), FAIL (no match)."""
    if not results:
        return "FAIL", "no results"

    top = results[0]
    if "error" in top:
        return "FAIL", f"search error: {top['error']}"

    score = top.get("score", 0)
    note = top.get("note", "")
    summary = top.get("summary", "")

    # Strong match: score >= 0.7 and note name or summary overlaps with query
    query_words = set(probe["query"].lower().split())
    note_words = set(note.lower().replace("-", " ").split())
    summary_words = set(summary.lower().split()) if summary else set()

    overlap = len(query_words & (note_words | summary_words)) / max(len(query_words), 1)

    if score >= 0.7 and overlap >= 0.3:
        return "PASS", f"{note} (score={score:.2f}, overlap={overlap:.0%})"
    elif score >= 0.5 or overlap >= 0.2:
        return "WEAK", f"{note} (score={score:.2f}, overlap={overlap:.0%})"
    else:
        return "FAIL", f"best: {note} (score={score:.2f}, overlap={overlap:.0%})"


def main():
    ts = datetime.now(timezone.utc).isoformat()[:19]

    if args.custom:
        # Single custom probe
        print(f"\n  Probing: '{args.custom}'")
        results = run_vault_search(args.custom)
        if results:
            for r in results[:3]:
                print(f"    [{r.get('score', 0):.2f}] {r.get('note', '?')}")
                if r.get("summary"):
                    print(f"           {r['summary'][:80]}")
        return

    # Generate probes from recent activity
    breadcrumbs = load_recent_breadcrumbs(n=20, session_filter=args.session)
    chains = load_recent_chains(n=10)
    probes = generate_probes(breadcrumbs, chains, max_probes=args.n)

    if not probes:
        print("  No probes generated — no recent breadcrumbs/chains")
        return

    print(f"\n{'='*60}")
    print(f"  VAULT PROBE QA — {len(probes)} probes from recent activity")
    print(f"{'='*60}")

    results_log = []
    pass_count = 0
    weak_count = 0
    fail_count = 0

    for i, probe in enumerate(probes):
        results = run_vault_search(probe["query"])
        verdict, detail = score_probe(probe, results)

        icon = {"PASS": "✓", "WEAK": "~", "FAIL": "✗"}[verdict]
        print(f"\n  {icon} Probe {i+1}: '{probe['query'][:60]}'")
        print(f"    Source: {probe['source']}")
        print(f"    Verdict: {verdict} — {detail}")

        if verdict == "PASS":
            pass_count += 1
        elif verdict == "WEAK":
            weak_count += 1
        else:
            fail_count += 1
            print(f"    ⚠ GAP: {probe['expected']}")

        results_log.append({
            "ts": ts,
            "probe": probe["query"][:80],
            "source": probe["source"],
            "verdict": verdict,
            "detail": detail[:100],
        })

    # Summary
    total = len(probes)
    score = (pass_count + weak_count * 0.5) / max(total, 1)
    print(f"\n{'='*60}")
    print(f"  RESULTS: {pass_count} PASS / {weak_count} WEAK / {fail_count} FAIL")
    print(f"  Vault coverage score: {score:.0%}")
    if fail_count > 0:
        print(f"  ⚠ {fail_count} gaps found — Archivist should create missing notes")
    print(f"{'='*60}")

    # Log results
    with open(PROBE_LOG, "a") as f:
        summary = {
            "ts": ts, "probes": total, "pass": pass_count,
            "weak": weak_count, "fail": fail_count, "score": round(score, 2),
            "gaps": [r["probe"] for r in results_log if r["verdict"] == "FAIL"],
        }
        f.write(json.dumps(summary) + "\n")

    # AUTO-REPAIR: generate stub notes for FAIL gaps
    if fail_count > 0:
        repair_dir = REPO / "knowledge" / "notes" / "auto-repair"
        repair_dir.mkdir(parents=True, exist_ok=True)
        for r in results_log:
            if r["verdict"] != "FAIL":
                continue
            slug = r["probe"][:50].lower().replace(" ", "-").replace(":", "").replace("/", "-")
            slug = "".join(c for c in slug if c.isalnum() or c == "-")
            repair_file = repair_dir / f"{slug}.md"
            if repair_file.exists():
                continue
            # Find the source breadcrumb content
            source_bc = next((p for p in probes if p["query"][:80] == r["probe"]), None)
            content_str = source_bc.get("content", r["probe"]) if source_bc else r["probe"]
            with open(repair_file, "w") as f:
                f.write(f"---\n")
                f.write(f'summary: "AUTO-REPAIR stub: {r["probe"][:60]}"\n')
                f.write(f"type: finding\n")
                f.write(f"status: stub\n")
                f.write(f'domains: ["cc-operational"]\n')
                f.write(f"date: {ts[:10]}\n")
                f.write(f"---\n\n")
                f.write(f"# {r['probe'][:60]}\n\n")
                f.write(f"**Auto-generated stub** — probe QA found this gap.\n\n")
                f.write(f"Source: {r['source']}\n\n")
                f.write(f"Content: {content_str}\n\n")
                f.write(f"**TODO:** Expand this stub into a full vault note with context, wikilinks, and analysis.\n")
            print(f"  AUTO-REPAIR: created stub {repair_file.name}")


if __name__ == "__main__":
    main()
