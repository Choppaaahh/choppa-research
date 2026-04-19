#!/usr/bin/env python3
"""
Retrieval Hit Distribution — measure vault_search discrimination quality.

A good retrieval system has a SHARP drop between rank-1 and rank-2 (peaked at
the right answer). A weak retrieval has a FLAT distribution (many near-equal
candidates = poor discrimination).

Metrics per query:
  top_score   = rank-1 score
  drop_abs    = top_score - rank-2 score
  drop_ratio  = (top_score - rank-2 score) / top_score
  gini        = Gini coefficient over top-K scores (concentration)
  shape       = KEYWORD | SHORT-PROSE | NARRATIVE-PROSE | UNKNOWN (P8)

Aggregate verdict:
  SHARP  : median drop_ratio >= 0.20
  MIXED  : 0.05 < median drop_ratio < 0.20
  FLAT   : median drop_ratio <= 0.05

Query-shape stratification (P8 — Brutus's addition):
  KEYWORD         : <=3 significant tokens, no verb markers ("adverse selection", "BM25 IDF")
  SHORT-PROSE     : 4-8 tokens with at least one verb marker ("why does grid bleed capital")
  NARRATIVE-PROSE : >8 tokens, multi-clause ("the scaffold is a nested RGM because...")
  UNKNOWN         : can't classify (empty after stopword strip, all punctuation)

The aggregate is stratified per-shape under `by_shape` so a keyword-sharp /
narrative-flat mix doesn't get averaged into MIXED and hide the regression.

Usage:
    python3 scripts/retrieval_hit_distribution.py                 # N=50 from breadcrumbs
    python3 scripts/retrieval_hit_distribution.py -n 20           # smoke test
    python3 scripts/retrieval_hit_distribution.py --from-probe    # reuse probe gaps
    python3 scripts/retrieval_hit_distribution.py --jsonl         # append aggregate
    python3 scripts/retrieval_hit_distribution.py --per-query     # dump per-query details
    python3 scripts/retrieval_hit_distribution.py --by-shape      # per-query with shape tags + per-shape breakdown
"""

import argparse
import json
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from _query_prep import prep_query  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BREADCRUMBS = REPO / "logs" / "session_breadcrumbs.jsonl"
PROBE_LOG = REPO / "logs" / "vault_probe_qa.jsonl"
VAULT_SEARCH = REPO / "scripts" / "vault_search.py"
OUT_LOG = REPO / "logs" / "retrieval_hit_distribution.jsonl"

# Same pattern as probe_diagnostics.py / compile_update_detector.py — vault_search
# scores are NOT normalized to [0,1]; can exceed 1.0 on direct-title/seed hits.
RESULT_LINE_RE = re.compile(r"^\s*\d+\.\s*\[(?P<score>[0-9.]+)\]\s*(?:\([^)]*\)\s*)?(?P<slug>\S.*?)\s*$")

SHARP_THRESHOLD = 0.20
FLAT_THRESHOLD = 0.05
SHARP_Q_RATIO = 0.30  # drop_ratio >= 0.30 => a "sharp" query

# ─────────────────────────────────────────────────────────────────────────────
# Query-shape classification (P8 — Brutus's addition to retrieval-fix plan)
# ─────────────────────────────────────────────────────────────────────────────
# Rationale: median-across-all-shapes hides class-specific regressions.
# A narrative-prose collapse with keyword-query staying sharp would look
# "MIXED" at the aggregate when actually one class catastrophically regressed.
#
# Classifier is deterministic, stdlib-only, heuristic: token count after
# stopword strip + presence of verb markers + multi-clause punctuation.

SHAPE_KEYWORD = "KEYWORD"
SHAPE_SHORT_PROSE = "SHORT-PROSE"
SHAPE_NARRATIVE = "NARRATIVE-PROSE"
SHAPE_UNKNOWN = "UNKNOWN"
ALL_SHAPES = (SHAPE_KEYWORD, SHAPE_SHORT_PROSE, SHAPE_NARRATIVE, SHAPE_UNKNOWN)

# Keep the stopword list conservative — we want to count "real" tokens for
# the keyword heuristic. These are the tokens that don't add content meaning.
_STOPWORDS = frozenset({
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "from", "by", "with",
    "and", "or", "but", "if", "as", "that", "this", "these", "those", "it",
    "its", "be", "am", "s", "t",
})

# Verb markers — presence of any of these bumps a short query from KEYWORD to
# SHORT-PROSE. We're explicit rather than using a POS tagger because we're
# stdlib-only and heuristics-all-the-way is simpler + deterministic.
_VERB_MARKERS = frozenset({
    "is", "are", "was", "were", "does", "did", "do", "have", "has", "had",
    "could", "would", "should", "will", "can", "may", "might", "must",
    "being", "been", "get", "got", "gets", "goes", "went", "makes", "made",
    "why", "how", "what", "when", "where", "which", "who",  # wh-words tend to open prose queries
})

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-']*")


def _significant_tokens(query: str) -> list[str]:
    """Tokenize, lowercase, drop stopwords. Deterministic."""
    return [t.lower() for t in _TOKEN_RE.findall(query) if t.lower() not in _STOPWORDS]


def _raw_tokens(query: str) -> list[str]:
    """Tokenize + lowercase but KEEP stopwords — used to detect verb markers."""
    return [t.lower() for t in _TOKEN_RE.findall(query)]


def classify_query_shape(query: str) -> str:
    """Classify a query into KEYWORD / SHORT-PROSE / NARRATIVE-PROSE / UNKNOWN.

    Deterministic heuristics only — same query → same classification every time.

    Rules (in order):
      1. Strip stopwords. If 0 significant tokens remain → UNKNOWN (all stopwords/punct).
      2. Count raw tokens (pre-stopword-strip) + significant tokens.
      3. If >8 raw tokens OR contains comma/colon/semicolon/em-dash → NARRATIVE-PROSE
         (multi-clause punctuation is the narrative-prose tell).
      4. Has verb marker (is/does/why/how/etc.) AND raw-token count 4-8 → SHORT-PROSE.
      5. Raw-token count between 4 and 8 without verbs → KEYWORD (terse phrase like
         "adverse selection probe diagnostics"; still keyword-shaped, no prose scaffolding).
      6. <=3 significant tokens → KEYWORD.
      7. Fallback → SHORT-PROSE (shouldn't hit — defensive default).
    """
    if not query or not query.strip():
        return SHAPE_UNKNOWN
    sig = _significant_tokens(query)
    if not sig:
        return SHAPE_UNKNOWN
    raw = _raw_tokens(query)
    n_raw = len(raw)
    n_sig = len(sig)
    # Multi-clause punctuation → narrative. Applies regardless of length.
    if any(ch in query for ch in (",", ";", ":", "—", " - ")):
        if n_raw > 6:  # avoid false-positive on "adverse selection: test" (colon but keyword-shaped)
            return SHAPE_NARRATIVE
    if n_raw > 8:
        return SHAPE_NARRATIVE
    has_verb = any(tok in _VERB_MARKERS for tok in raw)
    if has_verb and n_raw >= 4:
        return SHAPE_SHORT_PROSE
    if n_sig <= 3:
        return SHAPE_KEYWORD
    # 4-8 raw tokens, no verb markers — still keyword-shaped (terse noun phrase).
    if n_raw <= 8:
        return SHAPE_KEYWORD
    return SHAPE_SHORT_PROSE  # defensive fallback


def load_breadcrumb_queries(limit: int) -> list[str]:
    """Pull the most recent N breadcrumb contents as retrieval queries.

    Skips empty/too-short entries and dedups. Uses the content field directly
    as the query — these are the most realistic proxies for what a fresh CC
    session would search for.
    """
    if not BREADCRUMBS.exists():
        return []
    queries: list[str] = []
    seen: set[str] = set()
    for line in reversed(BREADCRUMBS.read_text(errors="replace").splitlines()):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (row.get("content") or "").strip()
        if len(content) < 10:
            continue
        # Truncate very long contents to the first clause — vault_search handles
        # ~100-char queries well but chokes on 500-char paragraphs.
        query = content[:120]
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(query)
        if len(queries) >= limit:
            break
    return queries


def load_probe_queries(limit: int) -> list[str]:
    """Pull gap queries from the probe log (actual failed retrievals)."""
    if not PROBE_LOG.exists():
        return []
    queries: list[str] = []
    seen: set[str] = set()
    for line in reversed(PROBE_LOG.read_text(errors="replace").splitlines()):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        for gap in row.get("gaps") or []:
            g = (gap or "").strip()
            if len(g) < 10:
                continue
            key = g.lower()
            if key in seen:
                continue
            seen.add(key)
            queries.append(g)
            if len(queries) >= limit:
                return queries
    return queries


def run_vault_search(query: str, timeout: int = 15) -> list[float]:
    """Run vault_search and return parsed top-K scores (empty list on failure)."""
    try:
        proc = subprocess.run(
            ["python3", str(VAULT_SEARCH), query, "--top", "5"],
            capture_output=True, text=True, timeout=timeout, cwd=str(REPO),
        )
    except subprocess.TimeoutExpired:
        print(f"  [timeout] {query[:60]}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print(f"  [missing vault_search.py]", file=sys.stderr)
        return []
    if proc.returncode != 0:
        return []
    scores: list[float] = []
    in_results = False
    for line in proc.stdout.splitlines():
        if "RESULTS:" in line:
            in_results = True
            continue
        if not in_results:
            continue
        m = RESULT_LINE_RE.match(line)
        if m:
            try:
                scores.append(float(m.group("score")))
            except ValueError:
                continue
    return scores


def gini(values: list[float]) -> float:
    """Gini coefficient — 0 = perfectly flat, ~1 = perfectly peaked."""
    if not values:
        return 0.0
    if all(v == 0 for v in values):
        return 0.0
    sorted_v = sorted(v for v in values if v >= 0)
    n = len(sorted_v)
    cumulative = 0.0
    for i, v in enumerate(sorted_v, 1):
        cumulative += i * v
    total = sum(sorted_v)
    if total == 0:
        return 0.0
    return (2 * cumulative) / (n * total) - (n + 1) / n


def analyze_query(query: str, distill_upstream: bool = False) -> dict | None:
    """Run search and compute hit-distribution metrics for one query.

    When distill_upstream=True, pass the query through _query_prep.prep_query
    before vault_search — this is the measurement lever for testing whether
    prose-aware preprocessing bumps the sharp_count on compound-prose queries.
    Shape classification runs on the ORIGINAL (pre-prep) query so shape
    stratification remains comparable across runs.
    """
    shape = classify_query_shape(query)
    search_query = prep_query(query) if distill_upstream else query
    scores = run_vault_search(search_query)
    if len(scores) < 2:
        return None  # can't compute a drop with <2 results
    top = scores[0]
    rank2 = scores[1]
    drop_abs = top - rank2
    drop_ratio = (drop_abs / top) if top > 0 else 0.0
    return {
        "query": query,
        "search_query": search_query,
        "distilled": search_query != query,
        "shape": shape,
        "scores": scores,
        "top_score": top,
        "rank2_score": rank2,
        "drop_abs": drop_abs,
        "drop_ratio": drop_ratio,
        "gini": gini(scores),
        "k": len(scores),
    }


def _aggregate_block(findings: list[dict]) -> dict:
    """Compute aggregate statistics over a (possibly filtered) finding set.

    Returns the same metric shape regardless of N — so per-shape blocks are
    shape-stable for downstream consumers. If findings is empty, returns a
    zero-block (n=0, no verdict, nulls elsewhere) so the by_shape dict always
    has all keys present.
    """
    if not findings:
        return {
            "n": 0,
            "median_drop_ratio": None,
            "mean_drop_ratio": None,
            "median_top_score": None,
            "median_gini": None,
            "sharp_frac": None,
            "flat_frac": None,
            "sharp_n": 0,
            "flat_n": 0,
            "buckets": {"0-0.05": 0, "0.05-0.15": 0, "0.15-0.30": 0, "0.30-0.50": 0, "0.50+": 0},
            "verdict": None,
        }
    drop_ratios = [f["drop_ratio"] for f in findings]
    top_scores = [f["top_score"] for f in findings]
    ginis = [f["gini"] for f in findings]
    sharp = sum(1 for r in drop_ratios if r >= SHARP_Q_RATIO)
    flat = sum(1 for r in drop_ratios if r <= FLAT_THRESHOLD)
    median_drop = statistics.median(drop_ratios)
    # Histogram buckets for drop_ratio
    buckets = {"0-0.05": 0, "0.05-0.15": 0, "0.15-0.30": 0, "0.30-0.50": 0, "0.50+": 0}
    for r in drop_ratios:
        if r <= 0.05:
            buckets["0-0.05"] += 1
        elif r <= 0.15:
            buckets["0.05-0.15"] += 1
        elif r <= 0.30:
            buckets["0.15-0.30"] += 1
        elif r <= 0.50:
            buckets["0.30-0.50"] += 1
        else:
            buckets["0.50+"] += 1
    if median_drop >= SHARP_THRESHOLD:
        verdict = "SHARP"
    elif median_drop <= FLAT_THRESHOLD:
        verdict = "FLAT"
    else:
        verdict = "MIXED"
    return {
        "n": len(findings),
        "median_drop_ratio": round(median_drop, 4),
        "mean_drop_ratio": round(statistics.mean(drop_ratios), 4),
        "median_top_score": round(statistics.median(top_scores), 4),
        "median_gini": round(statistics.median(ginis), 4),
        "sharp_frac": round(sharp / len(findings), 4),
        "flat_frac": round(flat / len(findings), 4),
        "sharp_n": sharp,
        "flat_n": flat,
        "buckets": buckets,
        "verdict": verdict,
    }


def aggregate(findings: list[dict]) -> dict:
    """Compute aggregate statistics over all per-query findings.

    Returns overall aggregate at the top level (backward-compat: existing
    consumers like retrieval_health_alert read `median_drop_ratio` here) AND
    nested `by_shape` dict with per-shape breakdowns (P8 addition).
    """
    overall = _aggregate_block(findings)
    if not findings:
        overall["by_shape"] = {s: _aggregate_block([]) for s in ALL_SHAPES}
        return overall
    by_shape: dict[str, dict] = {}
    for shape in ALL_SHAPES:
        subset = [f for f in findings if f.get("shape") == shape]
        by_shape[shape] = _aggregate_block(subset)
    overall["by_shape"] = by_shape
    return overall


def print_summary(
    agg: dict,
    source: str,
    per_query: list[dict] | None = None,
    show_shape_breakdown: bool = False,
) -> None:
    print()
    print(f"  Retrieval Hit Distribution — source: {source}")
    print(f"  {'=' * 56}")
    print(f"  N queries analyzed : {agg['n']}")
    if agg["n"] == 0:
        print("  (no valid results — nothing to report)")
        return
    print(f"  Median top score   : {agg['median_top_score']:.3f}")
    print(f"  Median drop ratio  : {agg['median_drop_ratio']:.3f}  (sharp>=0.20, flat<=0.05)")
    print(f"  Mean drop ratio    : {agg['mean_drop_ratio']:.3f}")
    print(f"  Median gini        : {agg['median_gini']:.3f}  (higher = more peaked)")
    print(f"  Sharp queries      : {agg['sharp_n']}/{agg['n']} ({agg['sharp_frac']*100:.1f}%) — drop_ratio >= 0.30")
    print(f"  Flat queries       : {agg['flat_n']}/{agg['n']} ({agg['flat_frac']*100:.1f}%) — drop_ratio <= 0.05")
    print()
    print("  Drop-ratio histogram:")
    for bucket, count in agg["buckets"].items():
        bar = "#" * min(count, 40)
        print(f"    {bucket:10s} : {count:4d}  {bar}")
    print()
    print(f"  VERDICT: {agg['verdict']}")
    if agg["verdict"] == "SHARP":
        print("    Retrieval discriminates well — top result stands clear of runners-up.")
    elif agg["verdict"] == "FLAT":
        print("    Retrieval is degenerate — top-K scores cluster, poor discrimination.")
        print("    Investigate: query phrasing, seed-expansion over-smoothing, or index staleness.")
    else:
        print("    Mixed — some queries peak sharply, others flatten. Look at per-query details.")

    # Per-shape breakdown (P8) — always shown when we have the data; --by-shape
    # adds the per-query shape-tagged dump below.
    by_shape = agg.get("by_shape") or {}
    if by_shape:
        print()
        print("  Per-shape breakdown:")
        print(f"    {'SHAPE':<17} {'N':>4}  {'med_drop':>8}  {'med_top':>7}  {'sharp':>5}  {'flat':>4}  verdict")
        for shape in ALL_SHAPES:
            b = by_shape.get(shape) or {}
            n = b.get("n", 0)
            if n == 0:
                print(f"    {shape:<17} {n:>4}  {'—':>8}  {'—':>7}  {'—':>5}  {'—':>4}  —")
                continue
            md = b.get("median_drop_ratio")
            mt = b.get("median_top_score")
            sn = b.get("sharp_n", 0)
            fn = b.get("flat_n", 0)
            v = b.get("verdict") or "—"
            md_s = f"{md:.3f}" if md is not None else "—"
            mt_s = f"{mt:.3f}" if mt is not None else "—"
            print(f"    {shape:<17} {n:>4}  {md_s:>8}  {mt_s:>7}  {sn:>5}  {fn:>4}  {v}")
        # Flag divergence — if any shape's verdict differs from overall, call it out.
        shape_verdicts = {s: (by_shape.get(s) or {}).get("verdict") for s in ALL_SHAPES}
        distinct = {v for v in shape_verdicts.values() if v}
        if len(distinct) > 1:
            print()
            print("    NOTE: shape verdicts disagree — overall may be hiding a class-specific regression.")

    if per_query is not None:
        print()
        if show_shape_breakdown:
            print("  Per-query detail (shape-tagged):")
            for f in per_query:
                shape = f.get("shape", SHAPE_UNKNOWN)
                print(
                    f"    [{shape:<15}] drop={f['drop_ratio']:.3f} "
                    f"top={f['top_score']:.2f} r2={f['rank2_score']:.2f}  {f['query'][:60]}"
                )
        else:
            print("  Per-query detail:")
            for f in per_query:
                print(f"    drop={f['drop_ratio']:.3f} top={f['top_score']:.2f} r2={f['rank2_score']:.2f}  {f['query'][:70]}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--num", type=int, default=50, help="Number of queries to sample (default 50)")
    ap.add_argument("--from-probe", action="store_true", help="Source queries from vault_probe_qa.jsonl gaps instead of breadcrumbs")
    ap.add_argument("--jsonl", action="store_true", help="Append aggregate to logs/retrieval_hit_distribution.jsonl")
    ap.add_argument("--per-query", action="store_true", help="Print per-query details")
    ap.add_argument("--by-shape", action="store_true", help="Per-query details with query-shape tags (implies --per-query)")
    ap.add_argument(
        "--distill-upstream",
        action="store_true",
        help="Wrap each query with _query_prep.prep_query() before vault_search "
             "(prose-aware pre-filter). Default OFF for measurement continuity.",
    )
    args = ap.parse_args()
    # --by-shape is a stricter form of --per-query — force the per-query dump too.
    if args.by_shape:
        args.per_query = True

    source = "probe-gaps" if args.from_probe else "breadcrumbs"
    if args.from_probe:
        queries = load_probe_queries(args.num)
    else:
        queries = load_breadcrumb_queries(args.num)

    if not queries:
        print(f"No queries available from {source}", file=sys.stderr)
        return 2

    distill_msg = " [distill-upstream ON]" if args.distill_upstream else ""
    print(f"  Running vault_search on {len(queries)} queries from {source}...{distill_msg}", file=sys.stderr)
    findings: list[dict] = []
    for i, q in enumerate(queries, 1):
        if i % 5 == 0:
            print(f"    {i}/{len(queries)}", file=sys.stderr)
        result = analyze_query(q, distill_upstream=args.distill_upstream)
        if result is not None:
            findings.append(result)

    agg = aggregate(findings)
    print_summary(
        agg,
        source,
        per_query=findings if args.per_query else None,
        show_shape_breakdown=args.by_shape,
    )

    if args.jsonl:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "n_requested": args.num,
            "distill_upstream": bool(args.distill_upstream),
            **agg,
        }
        OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with OUT_LOG.open("a") as f:
            f.write(json.dumps(record) + "\n")
        print(f"  appended aggregate to {OUT_LOG.relative_to(REPO)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
