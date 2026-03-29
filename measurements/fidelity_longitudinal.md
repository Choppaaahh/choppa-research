# Fidelity Longitudinal Data — F1 through F5

Scaffold reconstruction fidelity measured across 5 independent tests over 3 weeks. Each test samples 5 recent decisions and scores on 4 dimensions (0-1 ternary).

## Results

| Test | Date | WHAT | WHY | CONTEXT | BRIDGE | Notes |
|------|------|------|-----|---------|--------|-------|
| F1 | 03/10 | 1.00 | 0.93 | 0.60 | — | Major decisions only (selection bias) |
| F2 | 03/15 | 1.00 | 0.80 | 0.50 | — | Mixed operational decisions |
| F3 | 03/20 | 0.73 | 0.53 | 0.53 | — | Unlogged sprint (no breadcrumbs) |
| F3-fix | 03/20 | 1.00 | 0.87 | 0.87 | — | After 7 breadcrumb lines added |
| F4 | 03/25 | 0.84 | 0.65 | 0.60 | 0.40 | BRIDGE dimension added. Identity doc 9 days stale. |
| **F5** | **03/28** | **0.82** | **0.88** | **0.93** | **0.82** | **All-time highs on WHY/CONTEXT/BRIDGE** |

## Key Findings

### Two bugs that produced fake-low scores

Both F3-F4 scores were artificially depressed by MEASUREMENT bugs, not scaffold problems:

1. **CONTEXT 0.60 was a blind test** — the fidelity test only read 2 of 5 scaffold sources. It missed the real-time capture log where triggering context actually lives. Fixed 03/28: test now reads all 5 sources. CONTEXT immediately jumped to 0.93.

2. **WHAT 0.96 → 0.82 was a staleness gap** — new behavioral rules existed in the scaffold but weren't mentioned in the hot-tier identity document. The test couldn't find decisions that were encoded in rules but not surfaced in the identity layer. Fixed: updated identity doc.

**Lesson: measure your measurement.** The tool can be wrong. Both bugs made the scaffold look worse than it was. Prior scores (F3-F4) should be interpreted with this caveat.

### 1. CONTEXT 0.60 → 0.93 (measurement fix, not scaffold fix)

The fidelity test was only reading 2 of 5 scaffold sources — it missed the real-time breadcrumb log. The scaffold was capturing context correctly; the test couldn't see it. Expanding the test to all 5 sources revealed the true score.

**Finding: measurement tool quality directly affects reported fidelity scores.** The scaffold was performing better than measured.

### 2. WHY 0.65 → 0.88 (infrastructure improvement)

WHY was the chronic weakness through F1-F4. Two interventions:
- Added a `why` field to note schema (forces reasoning documentation at write time)
- Hardcoded real-time capture as mandatory (captures reasoning as it happens)

Both are infrastructure changes, not content changes. The reasoning was always happening — it just wasn't being preserved in a form the fidelity test could score.

### 3. BRIDGE 0.40 → 0.82 (new dimension, rapid improvement)

BRIDGE (cross-domain connections) was added in F4 at 0.40. By F5: 0.82. Cross-domain link density (9.0 links/note) and echo chamber detection (alert below 0.40 ratio) are working — connections are being made and preserved.

### 4. WHAT 0.96 → 0.82 (new content outpacing documentation)

WHAT dipped because new infrastructure was being built faster than the identity document was updated. New rules existed in the scaffold but weren't in the hot-tier document. Fix: regular identity doc updates.

**Finding: rapid system evolution can outpace identity documentation.** The scaffold knows things that the identity layer doesn't surface.

## Methodology

- **Scorer:** Claude (same model family as the scaffold agent). Goodhart caveat applies — AI self-scoring may inflate by 10-25%.
- **Decisions sampled:** 5 per test, drawn from recent operational decisions (not cherry-picked).
- **Dimensions:** WHAT (decision stated?), WHY (reasoning documented?), CONTEXT (triggering event captured?), BRIDGE (cross-domain connections visible?).
- **Sources read by scorer (F5):** 5 scaffold sources (hot-tier identity doc, operating rules, live breadcrumbs, task list, domain map).
- **Prior tests (F1-F4):** Scorer read only 2 of 5 sources. CONTEXT was systematically underestimated.

## Implications for Builders

1. **Measure your scaffold.** Without fidelity testing, you don't know what survives across sessions.
2. **Measure your measurement.** The tool can be wrong. F4's 0.60 CONTEXT was a measurement bug, not a scaffold bug.
3. **WHY is fixable with infrastructure.** A schema field + mandatory capture took WHY from 0.65 to 0.88. Small changes, large gains.
4. **CONTEXT requires real-time capture.** Retroactive summaries can't reconstruct triggering moments.
5. **BRIDGE requires deliberate cross-domain linking.** 0.40 → 0.82 came from automated detection and bridge campaigns — not organic growth.
