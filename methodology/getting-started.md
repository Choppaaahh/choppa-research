# Getting Started — From Zero to Metacognitive Scaffold

Your vault size will grow from 0 to hundreds of notes. Ours is 824 notes with 10.7 links/note as of April 2026. Here's the path.

## Phase 1: SEED (Day 1-3)

Dump what you know. Don't organize. Just capture.

**For a CS engineer with multiple projects:**
1. Open your projects. For each significant decision, bug, lesson, or mechanism — write a note.
2. One claim per file. Prose-sentence title (not topic labels).
   - GOOD: "auth service crashes on token refresh because session store doesn't handle concurrent writes"
   - BAD: "Auth Issues"
3. Dump 20-50 notes. Speed > quality at this stage.
4. Each note gets minimal frontmatter:
   ```yaml
   ---
   summary: "One sentence that adds info beyond the title"
   type: lesson | bug | mechanism | parameter | procedure | decision | insight
   status: current
   domains: []  # leave empty — domains emerge later
   ---
   ```

**What to capture:**
- Bugs you've fixed (symptom → root cause → fix)
- Architecture decisions (why X over Y)
- Things that keep breaking (patterns)
- Lessons from production incidents
- Mechanisms (how something works)
- Parameters (values + rationale)

**Don't capture:**
- Documentation that already exists elsewhere
- Trivial facts (API URLs, config values — unless the rationale matters)
- Anything you'd google instead of remembering

## Phase 2: CONNECT (Day 3-7)

Link related notes with wikilinks: `[[note title]]`

```markdown
This bug was caused by the same pattern as [[auth service token refresh crash]] —
stale data trusted over fresh data.
```

**Use articulated relationships:**
- `extends [[X]]` — builds on X
- `contradicts [[X]]` — conflicts with X  
- `same mechanism as [[X]]` — structurally identical pattern
- NOT just "see also" — every link should explain WHY it connects

**Domains emerge naturally:**
- After 30+ notes, you'll notice clusters (all the auth notes link together, all the deployment notes link together)
- When a cluster hits 5+ notes, create a domain map (MOC — Map of Content)
- A domain map is just a note that lists related notes with context phrases

**Example domain emergence:**
- Note 1-10: random project notes
- Note 15: "wait, 4 of these are about the same deployment pipeline"
- Note 20: create `deployment-pipeline.md` MOC listing those 4 + new ones
- Note 40: 3-4 domains are clear, most notes link to at least one

## Phase 3: INSTRUMENT (Week 2)

Add feedback loops that make the scaffold self-maintaining.

**Breadcrumb capture:**
- During work sessions, log decisions/findings/insights to a JSONL file as they happen
- Format: `{"ts":"ISO","type":"decision|finding|insight","content":"one line"}`
- At end of day, compile breadcrumbs into a session note (narrate → extract missed actionables → synthesize new connections)

**Fidelity measurement:**
- Can a fresh session reconstruct your reasoning from the scaffold alone?
- Score three dimensions: WHAT (facts), WHY (reasoning), CONTEXT (triggering events)
- Run monthly. Track degradation. The gap between WHAT and WHY is the temporal gap.

**Living documents:**
- Identify 3-5 documents that must stay current (your CLAUDE.md equivalent, task list, memory)
- Check freshness at session start and end
- If any is >24hrs stale and should be current, update it

## Phase 4: METACOGNITION (Week 3+)

The scaffold improves its own reasoning.

**Reasoning chain capture:**
- When you (or your AI) do deep reasoning, log the chain:
  `{"trigger":"what started it","chain":"step1→step2→step3","outcome":"what it produced","pattern":"reusable name"}`
- Review chains periodically (we do 3x/day via scheduled compile)
- Patterns appearing 3+ times with positive outcomes get promoted to permanent vault notes

**The autopoietic cycle:**
```
Capture chains → Accumulate → Compile (review patterns) → 
Promote stable patterns to vault → Load next session → 
Reason better → Capture better chains → Repeat
```

This is where the scaffold starts improving itself. The compile cycle runs autonomously. Patterns get promoted without human intervention. The system teaches itself.

## Phase 5: AUTOPOIETIC CLOSURE (Week 4+)

The scaffold audits itself and produces novel components.

**Walk-forward truth:**
- Periodically audit your own prior numeric claims: "is this number still valid, or was it based on a confounded dataset?"
- Build a pipeline that re-runs key claims against fresh data. If a claim was based on a biased sample, flag it CONFOUNDED rather than silently propagating it.
- We audited 18 prior numeric claims and flagged all 18 CONFOUNDED when run against an honest fill model. The self-audit is load-bearing.

**Versioned resource registry:**
- Immutable per-resource snapshots with restore capability
- Every promoted pattern gets a version number. When it's superseded, the old version stays queryable.
- Prevents pattern-name collisions and lets you trace the lineage of a belief.

**Contract-based spawn context:**
- When spawning an agent sub-task, pass only the context that task needs (a "contract"), not the full context window
- 5-10x context-bloat reduction per multi-agent task
- The contract defines what the sub-agent receives, what it must return, and what it cannot touch

**GEPA-lite (Generalized Evolutionary Protocol for Agents):**
- Periodically run your quality checklists and ruleset against your accumulated bug/failure log
- Mutation types: consolidation (merge two overlapping items), gap-patch (add item for uncovered class), specification (sharpen a vague item)
- Route mutations through adversarial review before applying
- The checklist grows from its own operational experience, not from manual curation

See `methodology/autopoietic-production.md` for the four production pathways in detail.

## Vault Growth Trajectory

| Stage | Notes | Links/note | Domains | Key milestone |
|-------|-------|-----------|---------|---------------|
| Seed | 20-50 | 1-2 | 0 | Raw knowledge captured |
| Connect | 50-100 | 3-4 | 3-5 | Clusters visible, first MOCs |
| Instrument | 100-200 | 5-6 | 8-12 | Feedback loops active, fidelity measured |
| Metacognition | 200+ | 7+ | 15+ | Reasoning patterns compounding |
| Autopoietic | 500+ | 9+ | 20+ | Walk-forward truth, self-audit pipeline active |
| Ours (current) | 824 | 10.7 | 25+ | Scaffold-as-RGM validated, 62 patterns promoted |

The numbers aren't targets — they're what happened to us. Your trajectory will differ based on domain, usage frequency, and how aggressively you connect notes.
