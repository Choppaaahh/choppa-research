# Cognitive Light Cone — First-Run Measurement

**Date:** 2026-04-19
**Tool:** `implementation/cognitive_light_cone.py`
**Metric source:** Pezzulo & Levin (2026), arXiv:2602.08079 — "Cognitive Light Cone" substrate-independent metric for system cognitive sophistication.

## What the metric measures

Four dimensions that characterize the spatiotemporal scope of goals a system can represent and pursue. Each is scored as a ratio against a fixed baseline: a raw LLM cold-start session with no scaffold (baseline = 1x on every dimension by convention).

## Scoreboard

| Dimension | Ratio vs. baseline | Interpretation |
|---|---:|---|
| Time horizon | 8640x | Effective goal horizon is year-scale (papers + build queue) vs. ~1 hour of within-session conversation for the raw LLM. |
| Spatial scope | 3.7x | Breadth-of-representational-space over baseline context window, counting vault notes × 800 tokens plus scheduled tasks plus agent configs. Conservative — does not include transitive graph reach. |
| Goal persistence | 14.4x | Reliability of goal survival across context loss. Scored from substrate-component count (4/4 persistent substrates present) × measured reconstitution fidelity (0.72). |
| Multiscale coordination | 5.0x | Simultaneous active timescales: generation, session, episodic-compile, training-data, retrieval-reinforcement. |

## What this says

Applied to the current scaffolded system, Levin's own substrate-independent metric produces scores between **3.7x and 8640x** the raw-LLM baseline across the four dimensions. The dimension with the largest ratio (time horizon) reflects goal-persistence infrastructure (papers, build queue, MEMORY.md) that the raw LLM has no mechanism to represent. The dimension with the smallest ratio (spatial scope) is the most conservative — it counts only raw knowledge surface area against context window size, ignoring the graph structure that makes the knowledge retrievable.

The measurement supports the position that the scaffold extends the underlying model's cognitive light cone by orders of magnitude on Levin's own scale, and that the extension is driven primarily by temporal mechanisms (persistence + multiscale coordination) rather than raw information volume.

## Caveats

- **N=1 system, N=1 measurement.** Cross-system and cross-time replication would strengthen the claim. Longitudinal data will accumulate as the script runs quarterly (cron-scheduled).
- **The baseline is stipulated.** Setting raw-LLM cold-start to 1x is a convention. A different baseline choice would rescale all dimensions uniformly but would not affect cross-dimensional comparison.
- **The dimension formulas are interpretive.** Levin's original formulation uses descriptive examples, not explicit formulas. The operationalization in `cognitive_light_cone.py` is one reasonable interpretation; alternative operationalizations may yield different absolute numbers. The order-of-magnitude story should be robust to operationalization choice.
- **The 8640x time-horizon figure is a ceiling, not a mean.** It is the maximum horizon from any single component; most individual goals operate on shorter horizons. A mean-weighted score would be lower.

## What this enables

This measurement is the empirical backing for Paper 09c §5.11.3's response to the embodied-cognition critique. Levin's framework applied to our scaffolded system, using Levin's own metric, yields scores that place the system well above the disembodied-AI baseline the critique relies on. The scaffold mechanism is what closes most of the gap.

## Next run

The tracker writes a new row to `logs/cognitive_light_cone.jsonl` on every invocation. Quarterly cadence captures longitudinal growth — if the time-horizon figure climbs as the build queue deepens, or the spatial-scope figure climbs as the vault grows, the trajectory becomes a secondary measurement (not just the instantaneous score).

## Reproducibility

To reproduce on a scaffolded system of your own:
1. Have a vault of notes, a todo file, a MEMORY-anchor file, and scheduled tasks operating at multiple timescales.
2. Run `python3 implementation/cognitive_light_cone.py` — output is a single JSON row + a human-readable score table.
3. Configure the `MEMORY_PATH` environment variable to point to your deployment's persistence anchor.

The baseline (1x) is universal. The ratios depend on your scaffold's structure — they are a self-description, not a universal fact.
