# Autopoietic Cognition Cycle

The scaffold doesn't just persist identity — it improves HOW it reasons. This is implemented as a scheduled compile cycle, not a metaphor.

## The Cycle

```
CAPTURE: reasoning chains logged during sessions
    → {"trigger":"...", "chain":"step1→step2→step3", "outcome":"...", "pattern":"name"}
    ↓
ACCUMULATE: chains build up between compiles (4-8hrs)
    ↓
COMPILE: scheduled 3x/day — identify stable patterns (3+ occurrences)
    ↓
PROMOTE: stable patterns → permanent vault notes
    ↓
LOAD: next session reads promoted patterns from vault
    ↓
REASON BETTER: system uses proven patterns, avoids known dead ends
    ↓
CAPTURE BETTER: improved reasoning produces higher-quality chains
    ↓
(repeat)
```

## Why This Is Autopoietic

Autopoiesis = self-producing, self-maintaining organization.

- **Produces:** new reasoning patterns from its own activity
- **Maintains:** promotes patterns to permanent storage
- **Improves:** tracks which patterns work and which fail
- **Self-corrects:** demotes broken patterns

## First Results (Day 1, 382-note vault)

53 reasoning chains from 5 specialized agents → 5 patterns promoted → 2 demoted.

The compile ran autonomously while the human was on mobile. The scaffold improved itself with no human intervention.

## Implementation

- Chains logged to `reasoning_chains.jsonl` by all agents (guardrails Rule 6)
- Compile triggered by launchd at 6am/3pm/7pm EST
- Each compile: `claude -p` session reads chains, identifies patterns, writes vault notes
- Promoted patterns load automatically in every future session via vault
