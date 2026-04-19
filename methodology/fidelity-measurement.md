# Fidelity Measurement — Does Your Memory Actually Work?

Most AI memory systems measure RECALL (can it retrieve the fact?). We measure RECONSTRUCTION (can it rebuild the reasoning agent?). The gap is where most systems silently fail.

## Four Dimensions

### WHAT (factual recall)
Can the system correctly state facts from the scaffold?
- Current config values, recent decisions, active tasks
- Our score: 1.00 (perfect — F17 measurement)
- This is what RAG systems optimize for

### WHY (reasoning reconstruction)
Can the system explain WHY decisions were made?
- The reasoning chain, tradeoffs considered, alternatives rejected
- Our score: 0.87 (up from 0.70 through breadcrumb improvements)
- This is what most systems miss

### CONTEXT (triggering events)
Can the system recall WHAT TRIGGERED the reasoning?
- The bug that caused the fix, the data that changed the approach
- Our score: 0.82 (improved by live breadcrumbing + trigger-clause discipline)
- Without context, decisions look arbitrary

### BRIDGE (cross-domain synthesis)
Can the system synthesize across domains using scaffold knowledge?
- Connecting findings from one area to implications in another
- Our score: 0.73 (the hardest dimension — requires wikilink density to be high enough)
- This is the dimension that distinguishes retrieval from reasoning

## The WHY-BRIDGE Gap

The 0.14 gap between WHY (0.87) and BRIDGE (0.73) is our current target. BRIDGE requires co-instantiating findings from multiple domains simultaneously — it's sensitive to cross-domain wikilink density. Below ~5 cross-domain links per domain, bridge synthesis drops sharply.

It maps to Perrier & Bennett's (2026) temporal gap formalism:
- WHAT = P_weak (Arpeggio) — each ingredient present somewhere in the window
- BRIDGE = P_strong (Chord) — all ingredients co-instantiated at decision time

Retrieving facts is easier than reconstructing reasoning because reasoning requires MULTIPLE facts active simultaneously. RAG retrieves ingredients one at a time. Reasoning needs them all together.

The BRIDGE dimension is sensitive to cross-domain wikilink density — isolated domains (echo chambers with <40% cross-domain link ratio) suppress bridge synthesis even when individual notes are accurate.

## How to Measure

1. **Pick 5-10 recent decisions** from your scaffold
2. **Start a fresh session** (no conversation history)
3. **Load only your scaffold files** (CLAUDE.md, memory, vault)
4. **Ask the system to explain each decision:**
   - WHAT: "What is the current X?" (factual)
   - WHY: "Why did we choose X over Y?" (reasoning)
   - CONTEXT: "What triggered this decision?" (triggering event)
   - BRIDGE: "How does this connect to [different domain]?" (cross-domain synthesis)
5. **Score each 0/1/2:**
   - 0 = wrong or absent
   - 1 = approximately correct
   - 2 = precise with specific details
6. **Track over time.** Monthly measurement. Watch for degradation.

## What Improves Each Dimension

| Dimension | Improves with | Degrades with |
|-----------|--------------|---------------|
| WHAT | More scaffold facts | Stale scaffold |
| WHY | `why:` field in frontmatter, reasoning chains, breadcrumbs | Time since decision (reasoning fades faster than facts) |
| CONTEXT | Live breadcrumbing, triggering event capture | Missing breadcrumbs during flow states |
| BRIDGE | Cross-domain wikilinks, MOC density | Echo-chamber domains (<40% cross-domain ratio) |

## Vault Stats (our system, April 2026)
- 824 notes, 10.7 links/note, 0 orphans, 0 danglers
- 25+ domain maps
- 531 reasoning chains captured across sessions
- Fidelity measured 17+ times across 8 weeks (F17: WHAT=1.00, WHY=0.87, CONTEXT=0.82, BRIDGE=0.73)
