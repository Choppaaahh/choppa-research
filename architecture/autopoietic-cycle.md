# Autopoietic Cognition Cycle

The scaffold doesn't just persist identity — it improves HOW it reasons. This is implemented as a scheduled compile cycle backed by a governance layer, not a metaphor.

## The Core Cycle

```
CAPTURE: reasoning chains logged during sessions
    → {"trigger":"...", "chain":"step1→step2→step3", "outcome":"...", "pattern":"name", "tip_type":"strategic|tactical|operational|metacognitive"}
    ↓
ACCUMULATE: chains build up between compiles (several hours)
    ↓
COMPILE: scheduled 3x/day — identify stable patterns (≥3 occurrences) + phase-transition forks (single occurrence with high topical influence)
    ↓
PROMOTE: stable patterns → permanent vault notes; patterns below quality threshold flagged for adversarial review
    ↓
LOAD: next session reads promoted patterns from vault via retrieval, weighted by reliability + recency
    ↓
REASON BETTER: system uses proven patterns, avoids known dead ends; negative-example field on chains captures what-not-to-do signal from demotions
    ↓
CAPTURE BETTER: improved reasoning produces higher-quality chains
    ↓
(repeat, with periodic walk-forward-truth audit of cumulative claims)
```

## Why This Is Autopoietic

Autopoiesis = self-producing, self-maintaining organization.

- **Produces:** new reasoning patterns from its own activity
- **Maintains:** promotes patterns to permanent storage, supersedes older patterns when new ones dominate
- **Improves:** tracks which patterns work and which fail (reliability scoring; 7-dim quality scorer on promotion candidates)
- **Self-corrects:** demotes broken patterns; walk-forward truth invalidates confounded claims systematically
- **Governs its own evolution:** learnable-flag frontmatter on resources + typed commit-gate invariants + versioned resource registry with chaos-tested restore

## Cumulative Results

Across 40+ compile cycles: 62 patterns promoted autonomously, 0 retracted promotions. The scaffold self-audit pipeline (walk-forward truth) flagged 18/18 prior reinforcement-learning-derived backtest claims as CONFOUNDED — evidence that the governance layer catches errors the promotion pipeline itself would miss.

QA checklist grown autonomously from 8 items to 16 through metacognitive compile — each new checklist item traces to a bug a prior audit missed. The scaffold produces its own quality infrastructure from its own operational experience.

## Implementation

- Chains logged to `reasoning_chains.jsonl` by all agents with `tip_type` classification
- Compile triggered by scheduler (cron on Pi; launchd on Mac; equivalent on other platforms) — typically 3x daily
- Each compile: `claude -p` session reads chains, identifies patterns, writes vault notes, logs decisions to `scaffold_changes.jsonl` with `auto_approved: true` + gate reason
- Promoted patterns load automatically in every future session via dynamic vault retrieval (see R18b experiment: dynamic per-task retrieval beats static preload by 67%)
- Governance layer: commit-gate runs invariants (I_orphan / I_dangler_delta / I_compile / I_link_density) before any auto-deploy; learnable-flag frontmatter blocks unauthorized self-modification of gatekeeping resources; versioned resource registry provides byte-identical restore on chaos-test

## Paper 10 connection

The autopoietic cycle is the operational instantiation of Layer 3 in the four-layer identity architecture. Paper 10 reframes this as the scaffold's contribution to the triad's identity continuity — the cycle is what allows the coupled system to exhibit diachronic identity across session boundaries rather than merely persisting static content.
