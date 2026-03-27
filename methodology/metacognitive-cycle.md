# Metacognitive Cycle — The Scaffold Improving Its Own Reasoning

Across 382 vault notes and 50+ reasoning chains captured in one day, we observed patterns in HOW the AI reasons, not just WHAT it produces. This led to a structured self-improvement cycle.

## The Insight

Different reasoning chains produce different quality outcomes:
- **Data-first chains** (start with numbers, follow surprises) → consistently produce good results
- **Hypothesis-first chains** (start with theory, look for confirmation) → consistently produce dead ends
- **Cross-domain chains** (connect trading to consciousness to market structure) → produce the most novel insights

If we can identify WHICH chains work and promote them, the system reasons better over time.

## Reasoning Chain Format

Every agent logs chains to a shared file:
```json
{
  "ts": "2026-03-26T13:29:00Z",
  "trigger": "what started the reasoning",
  "chain": "step1 → step2 → step3 → conclusion",
  "outcome": "what it produced",
  "pattern": "reusable-pattern-name",
  "reusable": true
}
```

## The Compile Cycle (3x daily)

1. **Read all chains** from all agents
2. **Group by pattern name** — which patterns appear 3+ times?
3. **Check outcomes** — do they produce good results? Bad results?
4. **Promote stable patterns** (3+ occurrences, positive outcomes) → permanent vault notes
5. **Demote broken patterns** (pattern used but outcome was bad) → update status to outdated
6. **Meta-observation** — what TYPE of reasoning is working best right now?

## First Results (Day 1)

5 patterns promoted:
- `MCR-coiling-dynamics` (HIGH confidence) — 8 chains
- `classifier-lag-stale-windows` (HIGH) — 6 chains  
- `power-window-relay-structure` (MED-HIGH) — 7 chains
- `post-trend-exhaustion-lifecycle` (HIGH) — 3 chains
- `meta-reasoning-operations` (HIGH) — 5 chains

2 patterns broken:
- `btc-safe-haven-coil` — failed on second test
- `multi-coin-simultaneous-coil` — divergent release

## The Closed Loop

```
Capture chains during sessions
    ↓
Accumulate in shared log
    ↓
Compile 3x/day (identify stable patterns)
    ↓
Promote to permanent vault knowledge
    ↓
Next session loads promoted patterns
    ↓
System reasons better using proven patterns
    ↓
Captures better chains
    ↓
(repeat — autopoietic cycle)
```

## Multi-Agent Reasoning

When multiple specialized agents share the same reasoning chain log:
- Adversarial reviewer logs KILL patterns (what fails and why)
- Code QA logs BUG patterns (which checks catch real issues)
- Market observer logs MARKET patterns (regime dynamics)
- Researcher logs SEARCH patterns (which strategies find relevant work)

The compile cycle sees ALL patterns together. Cross-agent patterns emerge:
"The adversarial reviewer kills proposals that lack fee math" → system-wide lesson.

53 chains from 5 agents in day 1. By week 2, team-wide patterns stabilize. By month 1, a genuine collective reasoning profile.

## Why This Matters

Standard AI memory stores WHAT was decided. This stores HOW decisions were reached.

The difference: "We chose strategy X" is a fact. "We chose X by starting with data, noticing anomaly Y, connecting to Z, and testing with fee math" is a reasoning pattern. The pattern is reusable. The fact is not.

A system that improves HOW it thinks — not just WHAT it knows — is autopoietic in the strongest sense.
