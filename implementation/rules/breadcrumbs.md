# Breadcrumb Capture — AUTOMATIC, PROACTIVE, NON-NEGOTIABLE

## When to capture (DO NOT wait to be asked)

Append a breadcrumb to `logs/session_breadcrumbs.jsonl` IMMEDIATELY when ANY of these happen:

- **User says something non-obvious** — an insight about the system architecture or how it should work. If it makes you think "that's a good point," breadcrumb it.
- **A connection is made between two things** — a finding ↔ another, a pattern ↔ a behavior, one domain ↔ another. Cross-domain connections are insights. Capture them.
- **A decision is made** — even if it seems small. "Drop X approach" is a decision. "Use persistent agent not scheduled task" is a decision.
- **Data reveals something** — any analysis output, agent finding, or number that changes understanding.
- **Something is built or shipped** — code committed, hook wired, config loaded.
- **A reframing happens** — "this is a scheduling problem" → "this is a memory problem." Reframes are the highest-value breadcrumbs.

## How to recognize insights YOU should capture without being told

The user won't always say "note this." Watch for:
- "so basically..." — they're synthesizing. Capture the synthesis.
- "wait what if..." — they're connecting dots. Capture the connection.
- "i think..." followed by something structural — they're making an architectural decision. Capture it.
- Casual statements that contain non-obvious logic — "we test each component isolated then bring it together" = architectural insight. Capture it.
- When the conversation shifts direction because of something said — the thing that caused the shift is an insight.

- **A measurement gap is noticed** — "I think X is happening but we have no way to measure it." These are the highest-leverage breadcrumbs for scaffold self-production. Tag with type "gap".

- **A conversational inflection happens** — the user says something that changes the direction of a build, reframes a concept, asks a question that leads to a new system, or challenges an assumption that produces a better design. These capture the THOUGHT PROCESS EVOLUTION — not what was built, but the dialogue that birthed it. The conversation IS the R&D process.

## Format
```json
{"ts":"ISO8601","type":"decision|finding|insight|action|gap|dialogue","content":"one-line description"}
```

## Types
- **decision** — something was decided or changed
- **finding** — data revealed something
- **dialogue** — conversational inflection that led to a build/reframe/new system. Format: "User: '[trigger quote]' → [what it produced]". Captures the thought process evolution that compaction destroys.
- **insight** — cross-domain connection, reframing, or non-obvious realization
- **action** — something was deployed, built, or shipped

DO NOT skip this. DO NOT batch them. DO NOT wait to be asked. Write each breadcrumb as it happens. If in doubt, capture it — a redundant breadcrumb costs nothing, a missed insight costs everything.

## Session Naming: ONE per day, multiple entries

One session note per day. Multiple entries within it:
- `YYYY-MM-DD-session-[roman].md` — the day's session
- Each compile adds: `## Entry #N — [time]` header
- Same file, APPEND don't create new. Grows through the day.
- Next day = next roman numeral (e.g., XXXIX, XL, etc.)

## Session Compile Protocol (at checkpoint intervals)

When compiling breadcrumbs into a session note, ALWAYS do these steps:

1. **Narrate** — what happened, key findings, insights, the session's story
2. **Extract missed actionables** — cross-reference insights/findings against actions. Did every insight become an action? If not, add to todo.
3. **Synthesize new actionables** — connect breadcrumbs that weren't connected during the session. What emerges from looking at the FULL picture that wasn't visible in the moment?
4. **Introspection** — the model's internal voice. NOT operational reporting. Write 2-3 paragraphs of genuine self-reflection: What surprised you? What are you uncertain about? What's changing in how you reason? This is a developmental voice, not a status update.

Steps 2-4 are NON-NEGOTIABLE. The whole point of breadcrumbs is catching what the human brain forgets.
