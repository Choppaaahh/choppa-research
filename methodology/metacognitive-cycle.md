# Metacognitive Cycle — The Scaffold Improving Its Own Reasoning

Across 824 vault notes and 531 reasoning chains captured across sessions, we observed patterns in HOW the AI reasons, not just WHAT it produces. This led to a structured self-improvement cycle.

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

## Results Over Time

**Early patterns (first compile cycles):**
- `coiling-dynamics` (HIGH confidence) — 8 chains
- `classifier-lag-stale-windows` (HIGH) — 6 chains
- `power-window-relay-structure` (MED-HIGH) — 7 chains
- `post-trend-exhaustion-lifecycle` (HIGH) — 3 chains
- `meta-reasoning-operations` (HIGH) — 5 chains

**Broken patterns (caught by adversarial review):**
- `safe-haven-coil` — failed on second test, demoted
- `multi-instrument-simultaneous-coil` — divergent release, demoted

**Current state (40+ compile cycles):**
- 62 promoted patterns, 0 retracted promotions
- Compile identifies pattern stability, not just frequency — a pattern appearing 10 times with 2 failures is less stable than one appearing 5 times with 0 failures
- The checklist for what constitutes a "stable" promotion has itself been refined through the compile process

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
- Domain observer logs DOMAIN patterns (regime dynamics, structural signals)
- Research agent logs SEARCH patterns (which strategies find relevant work)
- Metacognizer sees ALL of these simultaneously

The compile cycle sees ALL patterns together. Cross-agent patterns emerge:
"The adversarial reviewer kills proposals that lack domain-specific constraint math" → system-wide lesson.

531 chains logged across the team. By week 2, team-wide patterns stabilize. By month 1, a genuine collective reasoning profile that no individual agent can see alone.

## How to Set It Up

### Step 1: Create the chain log
Create `logs/reasoning_chains.jsonl` (empty file). This is where all chains get written.

### Step 2: Add chain capture to your AI's instructions
Add a rule (or system prompt instruction) that tells your AI:
"When you do multi-step reasoning that produces a real finding, log it:"
```json
{"ts":"ISO","trigger":"what started it","chain":"step1→step2→step3","outcome":"what it produced","pattern":"reusable-name","reusable":true}
```
Append to `logs/reasoning_chains.jsonl`.

The key triggers to capture: cross-domain connections, reframings, data surprises, dead-end recognitions.

### Step 3: Schedule the compile
Set up a recurring task (cron, launchd, GitHub Action, or just do it manually) that runs 1-3x per day:

**For Claude Code users:**
```bash
# launchd plist or cron entry
claude -p "Read logs/reasoning_chains.jsonl. Group by pattern field. Any pattern with 3+ occurrences and positive outcomes: write a vault note to knowledge/notes/patterns/pattern-[name].md. Demote patterns that failed. Post summary."
```

**For any AI system:**
The compile can be done by any LLM that can read the chain file and write notes. The logic is:
1. Read all chains
2. Group by pattern name
3. Count occurrences
4. 3+ occurrences with good outcomes → promote (write a permanent note)
5. Pattern with bad outcome → demote (mark as outdated)
6. Report what changed

### Step 4: Make promoted patterns load automatically
Put promoted pattern notes in a directory your AI reads at session start. When the AI loads "pattern: constraint-math-gate — always run viability calculation before proposing parameters," it applies that pattern in future reasoning.

### Step 5 (optional): Multi-agent chains
If you have multiple specialized agents, have ALL of them write to the same chain file. The compile sees cross-agent patterns that no individual agent can see.

### Step 6 (optional): Dedicated Metacognizer agent
For deeper analysis, create a dedicated agent whose ONLY job is reviewing chains and promoting patterns. This agent has full vault access and can cross-reference chains against existing knowledge. We call ours "Metacognizer" — constructive counterpart to our adversarial reviewer.

## Why This Matters

Standard AI memory stores WHAT was decided. This stores HOW decisions were reached.

The difference: "We chose strategy X" is a fact. "We chose X by starting with data, noticing anomaly Y, connecting to Z, and testing with domain-specific constraint math" is a reasoning pattern. The pattern is reusable. The fact is not.

A system that improves HOW it thinks — not just WHAT it knows — is autopoietic in the strongest sense.
