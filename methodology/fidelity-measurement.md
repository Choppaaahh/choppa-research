# Fidelity Measurement — Does Your Memory Actually Work?

Most AI memory systems measure RECALL (can it retrieve the fact?). We measure RECONSTRUCTION (can it rebuild the reasoning agent?). The gap is where most systems silently fail.

## Three Dimensions

### WHAT (factual recall)
Can the system correctly state facts from the scaffold?
- Current config values, recent decisions, active tasks
- Our score: 0.96 (near-perfect)
- This is what RAG systems optimize for

### WHY (reasoning reconstruction)
Can the system explain WHY decisions were made?
- The reasoning chain, tradeoffs considered, alternatives rejected
- Our score: 0.70 (the gap)
- This is what most systems miss

### CONTEXT (triggering events)
Can the system recall WHAT TRIGGERED the reasoning?
- The bug that caused the fix, the data that changed the approach
- Our score: 0.86 (improved by breadcrumb capture)
- Without context, decisions look arbitrary

## The WHAT/WHY Gap

The 0.26 gap between WHAT (0.96) and WHY (0.70) is our most important finding.

It maps to Perrier & Bennett's (2026) temporal gap formalism:
- WHAT = P_weak (Arpeggio) — each ingredient present somewhere in the window
- WHY = P_strong (Chord) — all ingredients co-instantiated at decision time

Retrieving facts is easier than reconstructing reasoning because reasoning requires MULTIPLE facts active simultaneously. RAG retrieves ingredients one at a time. Reasoning needs them all together.

## How to Measure

1. **Pick 5-10 recent decisions** from your scaffold
2. **Start a fresh session** (no conversation history)
3. **Load only your scaffold files** (CLAUDE.md, memory, vault)
4. **Ask the system to explain each decision:**
   - WHAT: "What is the current X?" (factual)
   - WHY: "Why did we choose X over Y?" (reasoning)
   - CONTEXT: "What triggered this decision?" (triggering event)
5. **Score each 0/1/2:**
   - 0 = wrong or absent
   - 1 = approximately correct
   - 2 = precise with specific details
6. **Track over time.** Monthly measurement. Watch for degradation.

## What Improves Each Dimension

| Dimension | Improves with | Degrades with |
|-----------|--------------|---------------|
| WHAT | More scaffold facts | Stale scaffold (our MEMORY.md went 9 days stale → WHAT dropped) |
| WHY | `why:` field in frontmatter, reasoning chains, breadcrumbs | Time since decision (reasoning fades faster than facts) |
| CONTEXT | Live breadcrumbing, triggering event capture | Missing breadcrumbs during flow states |

## Vault Stats (our system)
- 382 notes, 8.1 links/note, 0 orphans, 0 danglers
- 20+ domain maps
- 53+ reasoning chains captured in one day
- Fidelity measured 12+ times across 8 weeks
