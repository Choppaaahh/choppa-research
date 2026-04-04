# Metacognitive Self-Tracking — AUTOMATIC

## When deep reasoning happens, SAVE IT — INLINE, NOT BATCHED

When you find yourself doing multi-step reasoning that produces a real finding, capture the chain to `logs/reasoning_chains.jsonl` IMMEDIATELY. Not at the end of the session. Not in a batch. THE MOMENT the reasoning completes.

**The batching problem is real:** Sessions can produce many reasoning chains but only a fraction get captured in real-time. Batched chains lose temporal accuracy and miss the reasoning sequence. If you just analyzed data and reached a conclusion — STOP and log the chain BEFORE moving to the next task.

**Minimum per session:** If you've done 2+ hours of deep work and have <5 chains logged, you're batching. Stop and log what you missed.

**Structural trigger:** Every breadcrumb with type `finding` or `insight` implies a reasoning chain produced it. When you write a finding/insight breadcrumb, ALSO write the chain that led to it. Same moment, two log entries. The breadcrumb is WHAT, the chain is HOW. They're always paired.

```json
{"ts":"ISO","trigger":"what started this","chain":"step1 → step2 → step3 → conclusion","outcome":"what it produced","pattern":"reusable pattern name","reusable":true}
```

## Triggers to watch for (capture these automatically)

- **Multi-step analysis** that crosses 3+ reasoning steps — you're doing deep work, save the chain
- **Cross-domain connection** — the moment you connect two different areas of knowledge, THAT reasoning chain is gold
- **Reframing** — when the conclusion is different from where you started. Save how the reframe happened.
- **Contradiction resolution** — when two things seemed to conflict and you resolved it. Save the resolution chain.
- **Agent synthesis** — when combining outputs from multiple agents produces something none of them had alone. Save what you combined and how.
- **User insight capture** — when the USER says something that triggers a reasoning chain in you. Save both the trigger and your chain.
- **Dead end recognition** — when reasoning leads nowhere. Save it anyway — knowing which chains fail is as valuable as knowing which succeed.

## Where things go

| What | Where |
|------|-------|
| Reasoning chains | `logs/reasoning_chains.jsonl` |
| Breadcrumbs (decisions/findings/insights) | `logs/session_breadcrumbs.jsonl` |
| Operational self-knowledge | `knowledge/notes/patterns/` |

## Inline Skill Capture

When a complex multi-step task COMPLETES (not just during reasoning — at the finish line):
- Auto-extract the workflow as a reasoning chain
- Include: what triggered it, steps taken, tools used, what worked, what didn't, reusable pattern
- Don't wait for the scheduled compile — capture NOW at task completion
- The compile still reviews and promotes, but CAPTURE is inline

Triggers for inline skill capture:
- Built a new script → capture the design decisions and QA findings
- Debugged a tricky bug → capture the diagnostic chain
- Completed a multi-file edit → capture what connected the changes
- Research sweep produced actionable findings → capture the search strategy that found them

## Preemptive Breadcrumb Summarization

When breadcrumbs get dense (20+ in a session), don't wait for the compile:
- Auto-consolidate the oldest 10-15 breadcrumbs into a single summary breadcrumb
- Keep the summary + the most recent 10 as individual entries
- This keeps working memory lean without losing signal
- The summary breadcrumb is labeled: `{"type":"summary","content":"Consolidated 15 breadcrumbs: [key themes]"}`

## The compound effect

Every reasoning chain saved is a pattern available to future sessions. Over time:
- "Last time I analyzed this data type, the fee-check-first chain caught the bug" → always check fees first
- "Cross-domain synthesis between two agents produced the per-context gating insight" → always cross-reference agent outputs
- "The quick proxy validation was quick and dirty but validated the concept" → proxy-first-then-proper is a reusable pattern

This isn't journaling. It's the scaffold learning HOW to think better.
