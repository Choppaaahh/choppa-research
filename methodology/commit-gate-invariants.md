# Commit-Gate Invariants — Typed Checks That Refuse Decay

After ~40 cycles of scaffold work, a class of silent rot kept reappearing: rules that referenced infrastructure which no longer existed; notes that lost frontmatter schema; orphans produced by renames; link density thinning below useful thresholds. Each instance was individually minor. Across months, the cumulative drift was significant.

The fix: encode the scaffold's structural commitments as **typed invariants** enforced at commit time. Not a linter warning — a refusal. A commit that breaks an invariant is rejected until it is repaired or the invariant is explicitly amended.

## The Six Invariants

Each invariant has a short symbolic name. Naming matters — it turns a vague "is the vault healthy?" into a specific failure mode with a specific owner.

### `I_orphan` — No new orphan notes
A note added in this commit must have at least one incoming wikilink by commit time, OR be exempted as a MOC / index page. Pre-existing orphans are grandfathered; the invariant only fires on deltas.

**Why it exists:** Orphan creation is easy (write a note, forget to wire it). Orphan removal is tedious (remembering which notes were created loose). Enforcing at creation time costs seconds; retroactive cleanup costs hours.

### `I_dangler_delta` — No new broken wikilinks
A wikilink added in this commit must point to an existing note, OR the target note must be added in the same commit. Pre-existing danglers are grandfathered with a documented rationale.

**Why it exists:** A dangler at creation time usually means the author mistyped a slug or referenced a note they meant to create later. The delta check catches both before they propagate into retrieval results where they appear as false positives.

### `I_compile` — All touched code compiles
Every Python file modified in the commit must pass `py_compile.compile(..., doraise=True)`. No syntax errors, no import-time crashes on trivial parsing.

**Why it exists:** A compile break is the cheapest possible bug. Letting it through means every downstream consumer wastes time discovering it. This invariant is the floor — anything below it is not worth reviewing.

### `I_link_density` — Domain link density doesn't collapse
After the commit, no domain's average links-per-note may drop below a floor threshold. A commit that removes wikilinks across many notes without adding equivalent wiring is rejected.

**Why it exists:** Density collapse is how echo chambers form. A single bulk-edit that innocently strips link blocks can drop a domain from healthy (8+ links/note) to fragmented (2-3) in one commit. The invariant prevents single-commit collapses; gradual drift is caught by weekly audits.

### `I_prose_infrastructure_gap` — Rules reference real infrastructure
Every reference in a rules file, agent config, hook, or living document to a script path, log path, or other scaffold artifact must point to an existing file. Pre-existing broken references are grandfathered in an exception list; NEW references must resolve.

**Why it exists:** The class-bug is *prose describes infrastructure that was never built*. A rule says "run scripts/foo.py after every edit" — scripts/foo.py does not exist. Readers assume the scaffold is more complete than it is. The invariant closes the gap between documented behavior and actual behavior.

### `I_frontmatter_schema` — Notes have valid frontmatter
Every note in the vault must have complete YAML frontmatter: non-empty `summary`, `type`, `status` from an enum of valid values, and non-empty `domains` list. Pre-existing violations are grandfathered in an exception list with an `action_needed: true` flag; NEW violations on touched notes fail the gate.

**Why it exists:** Retrieval quality depends on schema consistency. A note with `status: promoted` (not in the enum — the actual enum uses `current`) silently deranges queries that filter by status. The invariant forces either enum compliance or explicit enum extension.

## Design Properties

### Grandfathering with a half-life
Every invariant has an exception list — pre-existing violations don't block progress, but they are visible and tagged for cleanup. The exception list is meant to shrink over time. A list that grows is a signal that the invariant is too strict or the cleanup cadence is too slow.

This is deliberate. A gate that refuses all pre-existing state is adopted by breaking the state to pass the gate. A gate that allows pre-existing state but tracks exceptions is adopted by gradually reducing the exception count.

### Typed naming, not vibes
Each invariant has a symbolic name (`I_orphan`, `I_compile`, …). When a commit is rejected, the error message cites the specific invariant. This turns "the commit gate failed" into "I_frontmatter_schema failed because note X has status:promoted which is not in {current, emerging, superseded, archived, archive-candidate, stub}."

The typed naming makes the system teachable. "Fix the I_prose_infrastructure_gap failures" is a specific ask; "fix the vault" is not.

### Invariants are amendable
The gate is not frozen. When an invariant fires repeatedly for a structural reason (not carelessness — a legitimate case the invariant didn't anticipate), the amendment routes through the same pipeline as any other rule change: draft, adversarial review, commit. The scaffold self-amends its own quality gates.

## What This Replaces

Before the commit gate, quality enforcement was *aspirational*: a checklist in a rules file that humans were supposed to consult. In practice, the checklist was read at onboarding and ignored thereafter. Drift accumulated. The scaffold's stated quality standard diverged from its measured quality.

The gate makes the standard *enforced*. A commit that would have drifted the system now either repairs the drift or documents the exception. The stated quality is closer to measured quality because they share a ground truth.

## Fit with the Rest of the Architecture

- **Autopoietic production** (see `autopoietic-production.md`): the gate is the fifth production pathway — it produces commits that satisfy structural constraints, rejecting ones that would erode those constraints.
- **Metacognitive cycle** (see `metacognitive-cycle.md`): the gate's refusal patterns feed back into the compile. A class of invariant failure (e.g., repeated `I_frontmatter_schema` on the same domain) is itself a reasoning chain worth capturing.
- **Cleanup queue** (see `cleanup-queue.md`): grandfathered exceptions are drained through the cleanup-queue mechanism on a scheduled cadence. The gate and the queue share ownership of long-tail quality.

---

*Implementation: a single Python script runs all six invariants on staged or working-tree changes. Exceptions are stored in a JSON file at the repo root. The gate is wired into the commit workflow via a hook; it can be overridden explicitly but the override is logged.*
