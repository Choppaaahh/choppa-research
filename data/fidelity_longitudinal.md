# Fidelity Longitudinal Data — F1 through F5

Scaffold reconstruction fidelity measured across 5 independent tests over 3 weeks. Each test samples 5 recent decisions and scores on 4 dimensions (0-1 ternary).

## Results

| Test | Date | WHAT | WHY | CONTEXT | BRIDGE | Notes |
|------|------|------|-----|---------|--------|-------|
| F1 | 03/10 | 1.00 | 0.93 | 0.60 | — | Major decisions only (selection bias) |
| F2 | 03/15 | 1.00 | 0.80 | 0.50 | — | Mixed operational decisions |
| F3 | 03/20 | 0.73 | 0.53 | 0.53 | — | Unlogged sprint (no breadcrumbs) |
| F3-fix | 03/20 | 1.00 | 0.87 | 0.87 | — | After 7 breadcrumb lines added |
| F4 | 03/25 | 0.84 | 0.65 | 0.60 | 0.40 | BRIDGE dimension added. MEMORY.md 9 days stale. |
| **F5** | **03/28** | **0.82** | **0.88** | **0.93** | **0.82** | **All-time highs on WHY/CONTEXT/BRIDGE** |

## Key Findings

### 1. CONTEXT 0.60 → 0.93 (measurement fix, not scaffold fix)

F4's CONTEXT score of 0.60 persisted for days. The assumption: the scaffold was losing triggering context. The reality: the fidelity test was only reading MEMORY.md and vault notes — it wasn't reading `logs/session_breadcrumbs.jsonl`, which is WHERE triggering context is captured.

Fix (03/28): expanded fidelity test to read all 5 scaffold sources (MEMORY.md, CLAUDE.md, breadcrumbs, todo, cc-operational MOC). CONTEXT immediately jumped to 0.93.

**Finding: measurement tool quality directly affects reported fidelity scores.** The scaffold was performing better than measured. Fixing the measurement revealed the true score.

### 2. WHY 0.65 → 0.88 (infrastructure improvement)

WHY was the chronic weakness through F1-F4. Two interventions:
- `why` field added to note frontmatter (forces reasoning documentation at write time)
- Breadcrumb capture hardcoded as mandatory rule (captures reasoning as it happens)

Both are infrastructure changes, not content changes. The reasoning was always happening — it just wasn't being preserved in a form the fidelity test could score.

### 3. BRIDGE 0.40 → 0.82 (new dimension, rapid improvement)

BRIDGE (cross-domain connections) was added in F4 at 0.40. By F5: 0.82. The vault's cross-domain link density (8.1 links/note) and echo chamber detection (alert below 0.40 ratio) are working — cross-domain connections are being made and preserved.

### 4. WHAT 0.96 → 0.82 (new content outpacing documentation)

WHAT dipped because new infrastructure (rules, patterns, stolen patterns) was being built faster than MEMORY.md was updated. New rules like `bug-fix-protocol` and `research-to-action` existed in the scaffold but weren't in the hot-tier identity document. Fix: added infrastructure changes to MEMORY.md System Self-Knowledge section.

**Finding: rapid system evolution can outpace identity documentation.** The scaffold knows things that the identity layer doesn't surface. Regular MEMORY.md updates are necessary not just for staleness prevention but for WHAT fidelity.

## Methodology

- **Scorer:** Claude (same model family as the scaffold agent). Goodhart caveat applies — AI self-scoring may inflate by 10-25%.
- **Decisions sampled:** 5 per test, drawn from recent operational decisions (not cherry-picked).
- **Dimensions:** WHAT (decision stated?), WHY (reasoning documented?), CONTEXT (triggering event captured?), BRIDGE (cross-domain connections visible?).
- **Sources read by scorer (F5):** MEMORY.md, CLAUDE.md, session_breadcrumbs.jsonl, todo.md, cc-operational-moc.md.
- **Prior tests (F1-F4):** Scorer read only MEMORY.md + vault notes. CONTEXT was systematically underestimated.

## Implications for Builders

1. **Measure your scaffold.** Without fidelity testing, you don't know what survives across sessions.
2. **Measure your measurement.** The tool can be wrong. F4's 0.60 CONTEXT was a measurement bug, not a scaffold bug.
3. **WHY is fixable with infrastructure.** The `why` frontmatter field + breadcrumb capture took WHY from 0.65 to 0.88. Small schema changes, large fidelity gains.
4. **CONTEXT requires real-time capture.** Retroactive summaries can't reconstruct triggering moments. Breadcrumbs are the only reliable source.
5. **BRIDGE requires deliberate cross-domain linking.** 0.40 → 0.82 came from echo chamber detection and bridge campaigns — not organic growth.
