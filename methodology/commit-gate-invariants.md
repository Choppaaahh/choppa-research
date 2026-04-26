# Commit-Gate Invariants — Typed Checks That Refuse Decay

After ~40 cycles of scaffold work, a class of silent rot kept reappearing: rules that referenced infrastructure which no longer existed; notes that lost frontmatter schema; orphans produced by renames; link density thinning below useful thresholds. Each instance was individually minor. Across months, the cumulative drift was significant.

The fix: encode the scaffold's structural commitments as **typed invariants** enforced at commit time. Not a linter warning — a refusal. A commit that breaks an invariant is rejected until it is repaired or the invariant is explicitly amended.

The set has grown over time. The original 6 invariants captured the most acute failure classes. As new failure classes were named, additional invariants were promoted in. As of cycle-30, the production scaffold runs **15 invariants** — the 6 originals + 9 added at the rate of roughly one per architectural-pattern-class that surfaced through adversarial review. Of those 9 additions, **4 are methodologically portable** (any structured-knowledge scaffold benefits from them); the other 5 are scaffold-internal (specific to our trading + autonomous-agent infrastructure). This document covers the 6 originals + 4 portable additions = **10 disciplines** that generalize. The other 5 are mentioned at the end as honest disclosure of the gap between this doc and the production system.

## The 6 Originals

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

## The 4 Portable Additions

These four invariants emerged from specific failure classes the originals didn't cover. They generalize beyond our scaffold's particulars to any structured-knowledge or research workflow.

### `I_bug_note_caught_by` — Every fix references the discipline that caught it

When a bug is documented in `knowledge/notes/bugs/`, its frontmatter must include a `caught_by:` field naming WHICH QA-checklist item, hook, agent, or invariant surfaced the bug. Pre-existing bug notes are NOT grandfathered — every entry must be tagged.

**Why it exists:** Without this tag, the link between failure-modes and the disciplines that catch them goes silent. Disciplines that never catch anything become decorative; disciplines with high catch-rates earn priority. The invariant forces every bug to close the failure↔prevention loop, making the system's catch-rate per-discipline measurable.

**Generalization:** any system that maintains explicit prevention disciplines (checklists, hooks, code-review patterns) benefits from per-failure attribution to the discipline that caught it. Without attribution, you cannot tell which disciplines earn their place.

### `I_reproducibility_fields` — Research artifacts carry source metadata

Every research deepdive note (papers we've read in depth) must carry: `type` matching the deepdive enum, `memory_type` containing `deepdive`, an arXiv ID (frontmatter or first 60 body lines), and a provenance trio (`origin_signature` / `source_trigger` / `trust_tier`).

**Why it exists:** Research captures rot fast when LLMs drift, papers get revised, or tooling turns over. Without explicit substrate + source, a note from cycle-12 saying "MetaRAG showed X" becomes irreproducible by cycle-30 because nobody remembers which arXiv version, which model summarized it, or whether the framing was the model's or the paper's.

**Generalization:** any system that ingests external research benefits from making the ingestion-substrate first-class metadata, not provenance-by-convention.

### `I_background_provenance` — Background-process outputs carry attribution

Every JSONL row written by a background writer (cron jobs, scheduled tasks, autonomous agents) must include `source` (which writer), `trigger` (why it fired — cron / user / chain-reaction / autonomous), and `trust_tier` (direct-user / agent-reasoning / autonomous-unsupervised / transit-amplifier). High-volume sensor feeds (raw market ticks) are file-level exempt; scaffold-memory writers are not.

**Why it exists:** Without provenance, downstream consumers cannot distinguish a row written by a hostile-prompt-injected agent from a row written by the user. The 2603.23064 HEARTBEAT paper showed empirically that 61% of silent memory-pollution attacks in LLM agent architectures exploit the consensus-cue channel — multiple background writers producing convergent-looking content that becomes load-bearing without any single one being flagged. Provenance-at-emission makes the attribution available; without it, retrieval surfaces accept everything as equally trusted.

**Generalization:** any system where multiple processes write to a shared retrieval surface needs provenance-at-emission, not provenance-by-context-loss.

### `I_vault_pattern_claim_scope_check` — Pattern-claims declare their scope inline

When a vault note makes a pattern-shape claim ("X dominates Y" / "P fires N% of the time" / "metric M flipped from A to B"), the note must declare the scope of evidence inline: a ≥3-day data window, OR explicit single-event scoping, OR explicit "no wider data exists" annotation. Without one of these three receipts, the claim is flagged.

**Why it exists:** A common failure mode in self-measuring systems: an agent reads N rows from a recent sub-day window and writes a pattern-shape claim ("100% UC dominance!") that's actually a session-window artifact, not a population claim. The invariant forces every pattern-claim to declare what evidence-window justifies it. Cycle-28 had n=2 instances of this in a single conversation before the discipline was named.

**Generalization:** any system where humans or agents make population-level claims from recent sub-population data benefits from inline scope-of-evidence declaration. The discipline is "no population claim without window-receipt."

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

## Honest disclosure: the 5 scaffold-internal invariants this doc omits

The production scaffold runs 5 additional invariants beyond the 10 above. They are scaffold-specific (trading-bot logic, internal authentication chains, structural-prose layering) and don't generalize cleanly. Listed here for transparency about the gap between this doc and the production system:

- `I_temporal_fabrication_check` — scans CC's prose for fabricated time-claims ("2+ years of...") without verification receipt. LLM-hallucination-specific.
- `I_entry_only_regime_gating` — trading-bot regime-gating logic (advisory mode). Trading-domain specific.
- `I_brutus_verdict_grounded` — adversarial-review output discipline (`DRIVEN-BY:` / `GROUNDING:` / `DOWNSTREAM-CONSEQUENCE:` fields required on Brutus verdicts). Scaffold-team-structure specific.
- `I_sibling_sync_check` — multi-scale layer trace across rules / hooks / agents / patterns / invariant-specs / MOCs / scripts. Concept portable; implementation tightly coupled to scaffold structure.
- `I_apply_handler_guard_present` — runtime-guard discipline on a specific Python module's state-mutating handlers (proposal_queue_apply.py + writer's rebuild_audit_chain). Internal infrastructure.

The 5 above represent failure-classes that surfaced in our specific architecture. The pattern of "name a failure class → mechanize the discipline" generalizes; the specific 5 invariants don't. Adding them would describe scaffold-internal infra; the 10 above describe disciplines.

---

*Implementation: a single Python script runs all 15 invariants on staged or working-tree changes. Exceptions are stored in a JSON file at the repo root. The gate is wired into the commit workflow via a hook; it can be overridden explicitly but the override is logged.*
