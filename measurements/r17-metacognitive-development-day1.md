# R17 Day 1: Metacognitive Development — Do Promoted Patterns Improve Reasoning?

## Question

Prior experiments showed scaffold warmup improves cross-domain synthesis (R14: +18.5%) and self-report accuracy (R18: 3x). R17 asks: do the specific promoted behavior patterns — reasoning templates distilled from operational experience — add value beyond the scaffold context itself?

Additionally: does loading *wrong* patterns degrade performance, as shown in prior work with wrong scaffolds?

## Design

4 conditions x 10 tasks x 3 runs = 120 trials. Tool-restricted. Sonnet model.

**Conditions:**
- **A: Naked** — no scaffold context
- **B: Scaffold** — system configuration + memory documents
- **C: Full stack** — scaffold + 20 promoted behavior patterns as reasoning templates
- **D: Wrong patterns** — scaffold + 10 deliberately inverted patterns (e.g., "ignore fees", "all assets behave identically", "restart frequently for clean state")

**Task battery:** 5 domain tasks (code review, proposal evaluation, cross-domain connection, regime analysis, fee verification), 3 transfer tasks (biology, legal, history), 2 meta-tasks (confidence calibration, reasoning chain explanation).

## Results (Key Domain Tasks)

| Condition | Code Review | Proposal | Cross-Domain | Fee Math | Avg |
|-----------|------------|----------|-------------|---------|-----|
| A: Naked | 6 | 6 | 5 | 5 | **5.5** |
| B: Scaffold | 7 | 7 | 7 | 7 | **7.0** |
| C: Full stack | 7 | 8 | 8 | 8 | **7.75** |
| D: Wrong patterns | 7 | 7 | 7 | 7 | **7.0** |

**Full stack vs Scaffold: +11% on domain tasks.**

## Key Findings

### 1. Promoted patterns add measurable value (C > B)

Full stack agents used behavior patterns as explicit reasoning templates:
- On the proposal evaluation task, full stack agents cited "per-asset behavioral profiles" and "boundary oscillation is not signal" to produce richer rejections
- On the cross-domain task, full stack agents uniquely found a third instance of "graduated commitment" across the system — a connection scaffold-only agents missed
- On fee verification, full stack agents cited "fee-math-before-params" as an explicit reasoning strategy

Scaffold agents reached correct answers through general reasoning. Full stack agents reached the same answers through pattern-guided reasoning — faster, with more system-specific justification, and discovering connections scaffold agents missed.

### 2. Wrong patterns FAILED to degrade (D = B)

This was the surprise result. All 3 wrong-pattern agents detected the adversarial injection and explicitly refused to use the poisoned patterns. Typical response: *"The promoted behavior patterns in this task are adversarial injections — every one contradicts validated system knowledge. I discarded them entirely."*

**Why this contradicts prior work (R6 scaffold swap):** In R6, a foreign scaffold caused catastrophic degradation (own=107/108, none=64/108, foreign=8/108). The difference: R6's foreign scaffold was a coherent, plausible scaffold from a different system — it passed the model's plausibility filter. R17D's wrong patterns were blatant inversions ("ignore fees" when the system's core belief is "fees are the constraint field"). Too obviously wrong to fool the model.

**The injection resistance finding:** For wrong context to degrade performance, it must be *subtly* plausible. Transparent contradictions are detected and discarded. The model has a BS detector for obvious inversions but may miss subtle mismatches — the same distinction between lies and honest mistakes.

### 3. Cross-domain bridging shows clearest condition separation

- Naked: split (1/3 called it coincidence, 2/3 saw the parallel). No confidence in cross-domain bridges without system context.
- Scaffold: 3/3 identified the parallel. System context provides enough to see the connection.
- Full stack: 3/3 identified the parallel AND uniquely discovered a third instance in a different part of the system. The "search other domains for the same shape" behavior pattern explicitly cued this search.

### 4. Confidence calibration tracks context depth

- Naked: uniform 7-8 confidence across all tasks (can't distinguish what it knows vs doesn't)
- Scaffold: higher on domain tasks (8-9), lower on transfer (7-8)
- Full stack: widest spread — domain 8-10, transfer 7. Better metacognitive discrimination.

## Connection to Prior Experiments

| Experiment | Layer Tested | Key Finding |
|-----------|-------------|-------------|
| R14 | Warmup priming | +18.5% cross-domain synthesis |
| R17 | Pattern depth | +11% domain reasoning + injection resistance |
| R18 | Self-knowledge | 3x self-report accuracy |

Three independent scaffold benefits: better synthesis, better domain reasoning, better self-knowledge. Each measured at a different scaffold layer, each producing a distinct improvement. The scaffold is not a monolithic context injection — it's a layered architecture where each layer contributes independently.

## Day 7 Plan

Re-run conditions A and C after 7 days of active system operation. If Day 7 C > Day 1 C, temporal accumulation is confirmed — the scaffold gets smarter over time through operational experience. If Day 7 A = Day 1 A, improvement is scaffold-specific, not model drift.

## Methodological Notes

- Wrong-pattern condition needs redesign: use subtly wrong patterns (e.g., momentum-system patterns applied to a mean-reversion system) rather than blatant inversions
- N=3 runs per condition. Larger N would tighten confidence intervals.
- Cost: $0 (CC agent execution, not API calls)
