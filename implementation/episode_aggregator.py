#!/usr/bin/env python3
"""
episode_aggregator.py — xMemory bounded-coherent-stream applied to breadcrumb log.

xMemory (Hu et al., arXiv:2602.02007) argues agent memory is NOT RAG — it is a
bounded, coherent dialogue stream with duplicate-dense spans that cannot be
retrieved via similarity-based top-k. They propose a four-level hierarchy
(Messages → Episodes → Semantics → Themes) where Episodes are contiguous
temporal-causal blocks of messages.

This script implements the Messages → Episodes layer over
logs/session_breadcrumbs.jsonl. Each breadcrumb is a "message." Episodes are
grouped by temporal proximity + topic coherence.

Algorithm (MVP — deliberately simple, stdlib only):
    1. Load breadcrumbs ordered by ts.
    2. Sliding-window group:
         - Break episode on temporal gap > --gap-min minutes.
         - Break episode on topic-shift: Jaccard similarity of significant tokens
           between current breadcrumb and last-N episode tokens < --shift-threshold.
    3. Emit episode records to logs/episodes.jsonl:
         { episode_id, start_ts, end_ts, breadcrumb_count, types, theme_tokens,
           one_line_theme }

Deferred upgrades (documented inline):
    - Dense embeddings via scaffold:v4 (currently: stdlib tokenize + stopword strip)
    - Causal-link graph (which breadcrumb references which via wikilinks or
      content substring)
    - Cross-session episode continuity (episodes that span compaction boundaries)
    - Semantics layer (cluster Episodes → recurring concept clusters)

CLI:
    python3 scripts/episode_aggregator.py                 # build episodes, print summary
    python3 scripts/episode_aggregator.py --gap-min 30    # custom temporal gap
    python3 scripts/episode_aggregator.py --shift 0.15    # custom topic-shift threshold
    python3 scripts/episode_aggregator.py --jsonl         # also append to logs/episodes.jsonl
    python3 scripts/episode_aggregator.py --last 20       # only process last 20 breadcrumbs (smoke)

Source: research-consciousness/xmemory-deep-dive.md;
        knowledge/notes/cc-operational/xmemory-bounded-coherent-stream-applied-to-breadcrumbs-produces-episode-hierarchy.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BREADCRUMBS_LOG = ROOT / "logs" / "session_breadcrumbs.jsonl"
OUT = ROOT / "logs" / "episodes.jsonl"

TOKEN_RE = re.compile(r"[a-z][a-z0-9_\-]{2,}")
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "of", "at",
    "by", "for", "with", "about", "to", "from", "in", "on", "off", "out",
    "up", "down", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "this", "that", "these",
    "those", "it", "its", "i", "me", "my", "we", "our", "you", "your",
    "what", "which", "who", "when", "where", "why", "how", "all", "any",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "can", "will",
    "just", "also", "still", "now", "got", "get", "new",
}


def load_breadcrumbs(limit: int | None = None) -> list[dict]:
    if not BREADCRUMBS_LOG.exists():
        return []
    rows = []
    for ln in BREADCRUMBS_LOG.read_text(errors="replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            row = json.loads(ln)
        except json.JSONDecodeError:
            continue
        ts_raw = row.get("ts")
        if not ts_raw:
            continue
        try:
            row["_ts"] = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        rows.append(row)
    rows.sort(key=lambda r: r["_ts"])
    if limit is not None and limit > 0:
        rows = rows[-limit:]
    return rows


def significant_tokens(text: str) -> set[str]:
    toks = TOKEN_RE.findall(text.lower())
    return {t for t in toks if t not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def aggregate_episodes(
    breadcrumbs: list[dict],
    gap_min: float,
    shift_threshold: float,
) -> list[dict]:
    """Group breadcrumbs into episodes via temporal-gap + topic-shift breaks."""
    if not breadcrumbs:
        return []

    episodes = []
    current = {
        "breadcrumbs": [breadcrumbs[0]],
        "token_pool": significant_tokens(str(breadcrumbs[0].get("content", ""))),
    }

    gap = timedelta(minutes=gap_min)

    for crumb in breadcrumbs[1:]:
        prev_ts = current["breadcrumbs"][-1]["_ts"]
        cur_ts = crumb["_ts"]
        time_gap = cur_ts - prev_ts

        new_tokens = significant_tokens(str(crumb.get("content", "")))
        similarity = jaccard(current["token_pool"], new_tokens)

        # Break conditions: temporal gap OR topic shift
        broke = False
        if time_gap > gap:
            broke = True
        elif similarity < shift_threshold:
            broke = True

        if broke:
            episodes.append(_finalize(current))
            current = {"breadcrumbs": [crumb], "token_pool": new_tokens}
        else:
            current["breadcrumbs"].append(crumb)
            # Token pool = union (so episodes accumulate coherent theme)
            current["token_pool"] = current["token_pool"] | new_tokens

    episodes.append(_finalize(current))
    return episodes


def _finalize(ep: dict) -> dict:
    crumbs = ep["breadcrumbs"]
    start = crumbs[0]["_ts"]
    end = crumbs[-1]["_ts"]
    types = Counter(str(c.get("type", "unknown")) for c in crumbs)

    # Theme tokens: top-10 most-frequent significant tokens across the episode
    all_tokens: list[str] = []
    for c in crumbs:
        all_tokens.extend(TOKEN_RE.findall(str(c.get("content", "")).lower()))
    theme_counter = Counter(t for t in all_tokens if t not in STOPWORDS)
    theme = [tok for tok, _ in theme_counter.most_common(10)]

    # One-line theme = first-breadcrumb content truncated (as an anchor)
    first_content = str(crumbs[0].get("content", "")).strip()
    one_line = (first_content[:120] + "...") if len(first_content) > 120 else first_content

    return {
        "start_ts": start.isoformat(),
        "end_ts": end.isoformat(),
        "duration_min": round((end - start).total_seconds() / 60.0, 1),
        "breadcrumb_count": len(crumbs),
        "types": dict(types),
        "theme_tokens": theme,
        "one_line_theme": one_line,
    }


def write_episodes(episodes: list[dict]) -> None:
    """Append a SINGLE aggregate row to episodes.jsonl per invocation."""
    OUT.parent.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    aggregate = {
        "ts": ts,
        "episode_count": len(episodes),
        "breadcrumb_span": (
            f"{episodes[0]['start_ts']} -> {episodes[-1]['end_ts']}"
            if episodes else "empty"
        ),
        "episodes": episodes,
    }
    with OUT.open("a") as f:
        f.write(json.dumps(aggregate) + "\n")


def render_summary(episodes: list[dict]) -> str:
    if not episodes:
        return "(no episodes — empty breadcrumb log)"

    lines = []
    lines.append(f"=== Episode Aggregation — {len(episodes)} episodes ===")
    durations = [e["duration_min"] for e in episodes]
    counts = [e["breadcrumb_count"] for e in episodes]
    lines.append(
        f"  Span: {episodes[0]['start_ts'][:16]} -> {episodes[-1]['end_ts'][:16]}"
    )
    lines.append(
        f"  Breadcrumbs per episode: min {min(counts)}, median {sorted(counts)[len(counts)//2]}, max {max(counts)}"
    )
    lines.append(
        f"  Duration per episode (min): min {min(durations)}, max {max(durations):.1f}"
    )
    lines.append("")
    lines.append("--- Episode list (most recent 10) ---")
    for ep in episodes[-10:]:
        lines.append(
            f"  [{ep['breadcrumb_count']:>3} crumbs, {ep['duration_min']:>5.1f}m] "
            f"{ep['start_ts'][:16]} | theme: {', '.join(ep['theme_tokens'][:5])}"
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap-min", type=float, default=45.0,
                    help="Temporal gap (min) that breaks an episode. Default: 45.")
    ap.add_argument("--shift", type=float, default=0.12, dest="shift_threshold",
                    help="Topic-shift threshold. Jaccard below this breaks episode. Default: 0.12.")
    ap.add_argument("--jsonl", action="store_true",
                    help="Also append aggregate row to logs/episodes.jsonl.")
    ap.add_argument("--last", type=int, default=0,
                    help="Only process last N breadcrumbs (smoke test).")
    args = ap.parse_args()

    breadcrumbs = load_breadcrumbs(limit=args.last or None)
    if not breadcrumbs:
        print("no breadcrumbs loaded — nothing to aggregate", file=sys.stderr)
        return 1

    episodes = aggregate_episodes(
        breadcrumbs, gap_min=args.gap_min, shift_threshold=args.shift_threshold
    )
    print(render_summary(episodes))

    if args.jsonl:
        write_episodes(episodes)
        print(f"\nappended aggregate row to {OUT}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
