# Breadcrumb System — Capturing What the Human Brain Forgets

Our vault has 824 notes. The breadcrumb system captures the reasoning BETWEEN notes — the decisions, insights, and connections that happen during work sessions but would otherwise be lost when the session ends.

## The Problem

During a work session, you make dozens of micro-decisions. Most are never recorded:
- "We should test X" → discussed but never done
- "This connects to Y" → seen but not captured
- "That approach won't work because Z" → known but not documented

By session end, half of these are forgotten. The breadcrumb system catches them in real-time.

## How It Works

### Capture (during session)
Every significant moment gets a one-line entry in `session_breadcrumbs.jsonl`:
```json
{"ts":"2026-03-26T21:15:00Z","type":"insight","content":"ALL agents should log reasoning chains — the entire team gets smarter through shared metacognitive log"}
```

Types: `decision`, `finding`, `insight`, `action`

### When to capture (proactive — don't wait to be asked)
- User says "so basically..." → they're synthesizing → CAPTURE
- A connection is made between two things → CAPTURE
- A decision is made (even if it seems small) → CAPTURE
- Data reveals something → CAPTURE
- A reframing happens → CAPTURE (highest value breadcrumbs)

### Compile (scheduled — 3pm and 7pm daily)
A scheduled task reads all breadcrumbs and compiles a session note with 5 mandatory steps:

1. **NARRATE** — what happened today
2. **EXTRACT MISSED** — cross-reference insights against actions. Did every insight become an action? If not, add to task list.
3. **SYNTHESIZE NEW** — connect breadcrumbs that weren't connected in the moment. What patterns emerge from the full picture?
4. **REASONING CHAIN REVIEW** — which reasoning patterns worked? Which led to dead ends? Promote stable patterns.
5. **LIVING DOCUMENT SWEEP** — check all key documents for staleness. Update anything >24hrs old.

### The result
- 69 breadcrumbs in one session → 8 missed actionables extracted → 6 synthesized connections found
- The system catches what the human brain forgets
- Insights that would die with the session get promoted to permanent knowledge

## Session Notes

One session note per day, multiple entries:
- `2026-03-26-session.md` — the day's session
- Entry #1 (morning compile), Entry #2 (evening wrap)
- Each entry timestamped and numbered
- Same file grows through the day

## Implementation

**For Claude Code users:**
- `.claude/rules/breadcrumbs.md` — rule that auto-loads, defines capture triggers
- `launchd` plist at 3pm and 7pm EST for compilation
- Can be replicated with any scheduler (cron, GitHub Actions, etc.)

**For any AI system:**
- The pattern is: structured logging during sessions + scheduled review
- The compile step is the key innovation — it's not just archiving, it's REASONING about what was captured
- Steps 2+3 (extract missed, synthesize new) are where the value lives
