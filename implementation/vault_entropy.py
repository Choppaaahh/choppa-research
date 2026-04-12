#!/usr/bin/env python3
"""
Vault Entropy Measurement — Thread #30 (Negentropy as Unifying Metric)

Computes Shannon entropy of the vault across multiple dimensions to test
whether the scaffold IS a negentropy injection system.

If entropy is DECREASING over time → negentropy thesis has empirical support.
If entropy is STABLE or INCREASING → we're telling ourselves a story.

Dimensions:
  1. Word distribution entropy (content diversity)
  2. Link degree entropy (connection uniformity)
  3. Domain distribution entropy (topic balance)
  4. Note size entropy (information distribution)

Usage:
    python3 scripts/vault_entropy.py              # compute current entropy
    python3 scripts/vault_entropy.py --report      # show trend if historical data exists
"""

import json
import math
import re
import argparse
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

# ─── Configuration ──────────────────────────────────────────────────────────

BASE_DIR = Path.home() / "Flex" / "Trading"
VAULT_DIR = BASE_DIR / "knowledge" / "notes"
LOGS_DIR = BASE_DIR / "logs"
ENTROPY_FILE = LOGS_DIR / "vault_entropy.jsonl"


def shannon_entropy(counts):
    """Compute Shannon entropy in bits from a list/counter of counts."""
    total = sum(counts)
    if total == 0:
        return 0.0
    entropy = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            entropy -= p * math.log2(p)
    return entropy


def normalized_entropy(counts):
    """Shannon entropy normalized to [0, 1] by dividing by log2(N)."""
    n = len([c for c in counts if c > 0])
    if n <= 1:
        return 0.0
    h = shannon_entropy(counts)
    h_max = math.log2(n)
    return h / h_max if h_max > 0 else 0.0


def read_vault_notes():
    """Read all vault notes, return list of (path, content) tuples."""
    notes = []
    if not VAULT_DIR.exists():
        return notes
    for f in VAULT_DIR.rglob("*.md"):
        try:
            content = f.read_text()
            notes.append((f, content))
        except Exception:
            pass
    return notes


def word_distribution_entropy(notes):
    """
    Entropy of word frequency distribution across the vault.
    Lower entropy = more concentrated vocabulary = more specialized/coherent.
    Higher entropy = more uniform vocabulary = more diverse/scattered.
    """
    word_counts = Counter()
    for _, content in notes:
        # Strip YAML frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end + 3:]
        # Strip wikilinks markup but keep words
        content = re.sub(r'\[\[([^\]]+)\]\]', r'\1', content)
        # Strip markdown formatting
        content = re.sub(r'[#*`|>\-\[\](){}]', ' ', content)
        # Tokenize
        words = re.findall(r'[a-z]+', content.lower())
        word_counts.update(words)

    # Filter to words appearing 2+ times (remove noise)
    filtered = {w: c for w, c in word_counts.items() if c >= 2 and len(w) > 2}
    counts = list(filtered.values())

    h = shannon_entropy(counts)
    h_norm = normalized_entropy(counts)
    vocab_size = len(filtered)

    return {
        "word_entropy_bits": round(h, 4),
        "word_entropy_normalized": round(h_norm, 4),
        "vocab_size": vocab_size,
        "total_words": sum(counts),
    }


def link_degree_entropy(notes):
    """
    Entropy of outgoing link degree distribution.
    Lower entropy = some notes have way more links (hub-and-spoke).
    Higher entropy = all notes have similar link counts (uniform mesh).
    """
    degrees = []
    for _, content in notes:
        link_count = len(re.findall(r'\[\[', content))
        degrees.append(link_count)

    # Degree distribution (how many notes have degree 0, 1, 2, ...)
    degree_dist = Counter(degrees)
    counts = list(degree_dist.values())

    h = shannon_entropy(counts)
    h_norm = normalized_entropy(counts)

    # Also compute as raw degree counts for concentration measure
    h_raw = shannon_entropy(degrees) if degrees else 0.0

    return {
        "link_degree_entropy_bits": round(h, 4),
        "link_degree_entropy_normalized": round(h_norm, 4),
        "mean_degree": round(sum(degrees) / len(degrees), 2) if degrees else 0,
        "max_degree": max(degrees) if degrees else 0,
        "zero_degree_notes": degrees.count(0),
    }


def domain_distribution_entropy(notes):
    """
    Entropy of note distribution across domains/subfolders.
    Lower entropy = concentrated in few domains.
    Higher entropy = evenly spread across domains.
    """
    domain_counts = Counter()
    for path, content in notes:
        # Get relative path from vault root
        rel = path.relative_to(VAULT_DIR)
        parts = rel.parts
        if len(parts) > 1:
            # Subfolder = domain
            domain = "/".join(parts[:-1])
        else:
            domain = "root"
        domain_counts[domain] += 1

    counts = list(domain_counts.values())

    h = shannon_entropy(counts)
    h_norm = normalized_entropy(counts)

    return {
        "domain_entropy_bits": round(h, 4),
        "domain_entropy_normalized": round(h_norm, 4),
        "num_domains": len(domain_counts),
        "domain_sizes": dict(domain_counts.most_common()),
    }


def note_size_entropy(notes):
    """
    Entropy of note sizes (in words).
    Lower entropy = notes are all similar size (uniform structure).
    Higher entropy = wide variation in note sizes.
    """
    sizes = []
    for _, content in notes:
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end + 3:]
        word_count = len(content.split())
        sizes.append(word_count)

    # Bin sizes into buckets for distribution
    if not sizes:
        return {"size_entropy_bits": 0, "size_entropy_normalized": 0}

    # Use 20-word bins
    bin_size = 20
    binned = Counter()
    for s in sizes:
        bin_label = (s // bin_size) * bin_size
        binned[bin_label] += 1

    counts = list(binned.values())
    h = shannon_entropy(counts)
    h_norm = normalized_entropy(counts)

    return {
        "size_entropy_bits": round(h, 4),
        "size_entropy_normalized": round(h_norm, 4),
        "mean_size_words": round(sum(sizes) / len(sizes), 1),
        "median_size_words": sorted(sizes)[len(sizes) // 2],
        "min_size": min(sizes),
        "max_size": max(sizes),
    }


def compute_composite_entropy(word_e, link_e, domain_e, size_e):
    """
    Composite entropy score — weighted average of normalized entropies.

    The negentropy thesis predicts this should DECREASE over time
    as the vault becomes more structured and coherent.
    """
    # Weights reflect importance to the negentropy thesis:
    # - Word entropy: high weight (content coherence is core claim)
    # - Link entropy: medium (structure matters but hub-spoke is expected)
    # - Domain entropy: low (uneven domains are fine — reflects real focus areas)
    # - Size entropy: low (informational, not causal)

    weights = {
        "word": 0.4,
        "link": 0.3,
        "domain": 0.15,
        "size": 0.15,
    }

    composite = (
        weights["word"] * word_e["word_entropy_normalized"] +
        weights["link"] * link_e["link_degree_entropy_normalized"] +
        weights["domain"] * domain_e["domain_entropy_normalized"] +
        weights["size"] * size_e["size_entropy_normalized"]
    )

    return round(composite, 4)


def run_measurement():
    """Run full entropy measurement and log results."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    notes = read_vault_notes()
    if not notes:
        print("No vault notes found.")
        return

    print(f"Vault Entropy Measurement — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 60}")
    print(f"  Notes analyzed: {len(notes)}")

    word_e = word_distribution_entropy(notes)
    link_e = link_degree_entropy(notes)
    domain_e = domain_distribution_entropy(notes)
    size_e = note_size_entropy(notes)
    composite = compute_composite_entropy(word_e, link_e, domain_e, size_e)

    print(f"\n  1. Word Distribution Entropy")
    print(f"     H = {word_e['word_entropy_bits']:.2f} bits (normalized: {word_e['word_entropy_normalized']:.4f})")
    print(f"     Vocab: {word_e['vocab_size']} unique words, {word_e['total_words']} total")

    print(f"\n  2. Link Degree Entropy")
    print(f"     H = {link_e['link_degree_entropy_bits']:.2f} bits (normalized: {link_e['link_degree_entropy_normalized']:.4f})")
    print(f"     Mean degree: {link_e['mean_degree']}, Max: {link_e['max_degree']}, Zero-link: {link_e['zero_degree_notes']}")

    print(f"\n  3. Domain Distribution Entropy")
    print(f"     H = {domain_e['domain_entropy_bits']:.2f} bits (normalized: {domain_e['domain_entropy_normalized']:.4f})")
    print(f"     {domain_e['num_domains']} domains")
    for domain, count in list(domain_e['domain_sizes'].items())[:8]:
        print(f"       {domain}: {count}")

    print(f"\n  4. Note Size Entropy")
    print(f"     H = {size_e['size_entropy_bits']:.2f} bits (normalized: {size_e['size_entropy_normalized']:.4f})")
    print(f"     Mean: {size_e['mean_size_words']} words, Median: {size_e['median_size_words']}, Range: {size_e['min_size']}-{size_e['max_size']}")

    print(f"\n  COMPOSITE ENTROPY: {composite:.4f}")
    print(f"  (0 = perfectly ordered, 1 = maximum disorder)")

    # Interpret
    if composite < 0.5:
        print(f"  → LOW entropy — vault is highly structured/coherent")
    elif composite < 0.7:
        print(f"  → MODERATE entropy — structured with some diversity")
    else:
        print(f"  → HIGH entropy — diverse/scattered content")

    # Log entry
    entry = {
        "ts": datetime.now().isoformat(),
        "notes_count": len(notes),
        "composite_entropy": composite,
        **{f"word_{k}": v for k, v in word_e.items() if not isinstance(v, dict)},
        **{f"link_{k}": v for k, v in link_e.items() if not isinstance(v, dict)},
        **{f"domain_{k}": v for k, v in domain_e.items() if not isinstance(v, dict) and not isinstance(v, list)},
        **{f"size_{k}": v for k, v in size_e.items() if not isinstance(v, dict)},
    }

    with open(ENTROPY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"\n  Logged to: {ENTROPY_FILE}")
    return entry


def show_report():
    """Show entropy trend from historical data."""
    if not ENTROPY_FILE.exists():
        print("No entropy data yet. Run without --report first.")
        return

    entries = []
    for line in ENTROPY_FILE.read_text().strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    if len(entries) < 2:
        print(f"Only {len(entries)} data point(s). Need 2+ for trend analysis.")
        print("Running current measurement...")
        run_measurement()
        return

    print(f"Vault Entropy Trend — {len(entries)} measurements")
    print(f"{'=' * 60}")

    composites = [e["composite_entropy"] for e in entries]
    print(f"\n  Composite Entropy: {composites[0]:.4f} → {composites[-1]:.4f}")
    delta = composites[-1] - composites[0]
    print(f"  Change: {delta:+.4f}")

    if delta < -0.01:
        print(f"  → DECREASING — negentropy thesis SUPPORTED")
        print(f"    The vault is becoming more ordered over time.")
    elif delta > 0.01:
        print(f"  → INCREASING — negentropy thesis CHALLENGED")
        print(f"    The vault is becoming more disordered.")
    else:
        print(f"  → STABLE — insufficient change to determine trend")

    # Per-dimension trends
    for dim in ["word_entropy_normalized", "link_degree_entropy_normalized",
                "domain_entropy_normalized", "size_entropy_normalized"]:
        vals = [e.get(f"word_{dim}" if "word" in dim else
                      f"link_{dim}" if "link" in dim else
                      f"domain_{dim}" if "domain" in dim else
                      f"size_{dim}", 0) for e in entries]
        # Try to get the right key
        short = dim.replace("_entropy_normalized", "").replace("_degree", "")
        vals = [e.get(f"{short}_entropy_normalized",
                e.get(f"{short}_{dim}", 0)) for e in entries]
        if vals[0] > 0:
            delta = vals[-1] - vals[0]
            direction = "↓" if delta < 0 else "↑" if delta > 0 else "→"
            print(f"    {short}: {vals[0]:.4f} → {vals[-1]:.4f} {direction}")


def main():
    parser = argparse.ArgumentParser(description="Vault Entropy Measurement")
    parser.add_argument("--report", action="store_true", help="Show entropy trend")
    args = parser.parse_args()

    if args.report:
        show_report()
    else:
        run_measurement()


if __name__ == "__main__":
    main()
