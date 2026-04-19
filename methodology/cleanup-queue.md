# The Cleanup Queue — Long-Tail Quality as a First-Class Object

Every scaffold accumulates long-tail quality debt. Notes that need re-linking. Rules that still reference renamed files. Bug notes without schema tags. Tasks completed but never archived. Each item is individually cheap to fix. Collectively, they compound into a substrate that *looks* healthy at summary statistics but is noticeably worse at retrieval.

The naive solution — "periodically audit the vault" — fails in practice because audits are interrupt-driven work that loses to anything with a visible deadline. The cleanup queue turns long-tail quality into a scheduled, measurable object.

## The Aggregator

A single script scans the scaffold for drift, bucketed by category and priority:

| Priority | Category examples |
|---|---|
| HIGH | Frontmatter schema violations |
| MEDIUM | Notes with unresolved status markers; bugs with no associated quality check |
| LOW | Zero-fire quality checks (present in the checklist but never actually catching anything); grandfathered exceptions in the commit gate |
| INFO | Archived scripts; resolved archive-candidate notes |
| DEFER | Rows flagged for future use but not actionable now |

The aggregator runs in under a second. Output is a ranked list: *this many items, these priorities, these categories*. First output on a real scaffold: ~500 items. Most low-priority. A handful high-priority.

Visibility matters. Before the aggregator, the answer to "how much cleanup is pending?" was a shrug. After: a number that goes up when neglected and down when drained.

## The Drainage Cadence

Two scheduled operations per week, both anchored to specific weekdays so the agent knows which role it's playing:

- **Wednesday — Health sweep.** Run the health checks (graph health, schema compliance, link density, orphan count). Report deltas since last sweep. No writes unless trivially safe.
- **Saturday — Drainage.** Pick one priority tier (HIGH, then MEDIUM, then LOW). Drain items from the queue up to a bounded edit count. Archive-not-delete for anything that might have downstream references. Report what was drained and what was deferred.

The day-of-week encoding is a small trick that matters. "Run maintenance sometimes" produces variable-quality maintenance. "Saturday is drainage day" produces drainage every Saturday because the cadence is a schedule primitive, not a discretionary ask.

## Archive-Not-Delete

A recurring temptation: delete stale items. A recurring regret: stale items turned out to have downstream references that nobody remembered.

The discipline: **anything removed from the active surface is moved to an archive subtree, not deleted.** The archive preserves git history, preserves any wikilinks that target it, and makes the removal reversible. An archive subtree with a clear INDEX file is as navigable as the active surface — just explicitly marked as superseded or resolved.

First instance: a scaffold cleanup revealed a writer script that hadn't been called in months. The temptation was `rm`. The discipline was `git mv scripts/foo.py scripts/archive/foo.py` + append a line to `scripts/archive/INDEX.md` explaining the retirement. Three sessions later, a search for a behavior that script had once implemented surfaced the archive entry, saved ~30 minutes of reconstruction.

## Categories Worth Tracking

Different scaffolds will have different categories. The ones that generalize:

- **Schema violations on the primary knowledge substrate.** If the vault has frontmatter, track frontmatter drift. If it's a task list with required fields, track field-completeness drift.
- **Zero-fire quality checks.** A checklist item that never catches anything in 30+ bug notes is either the wrong item, the wrong wording, or a duplicate of a broader item. Flag it, don't delete it — the zero-fire signal itself is the interesting data.
- **Grandfathered exceptions.** Every commit-gate exception is a deferred repair. The list is meant to shrink. If it grows, the schedule isn't draining fast enough.
- **Resolved-but-not-archived items.** Done tasks, fixed bugs, superseded notes. Living in the active surface means every retrieval hits them and the reader has to re-establish that they're stale.

## Failure Modes

### The drainage that never drains
If the queue never shrinks, the cadence is inadequate, the scope is too small per sweep, or the aggregator is counting items that are no longer drift (exceptions grandfathered for a real reason). First check: is the count actually declining over the long run? If not, audit the categories.

### The drainage that drains too aggressively
A Saturday that drains 200 items is suspicious. Fast drainage usually means either the items weren't real drift (false positive in the aggregator) or the drainage wasn't careful enough (mass metadata bumps, bulk archives without review). Cap per-sweep edit counts. Prefer many small Saturdays to one heroic one.

### The report that nobody reads
A weekly ritual that writes a report file but nobody consumes it is theater. Pipe drainage summaries into the same channel that other operational updates flow through. Make the report live adjacent to the thing it describes.

## Why a Dedicated Object

Long-tail quality could be handled ad-hoc — "I'll clean things up when I notice." In practice, "when I notice" means "never, because the interesting work always wins." Giving long-tail quality a name (the queue), a home (the aggregator output), and a schedule (Wednesday health, Saturday drainage) makes it a first-class thing the system attends to.

The same move that turns attention-dependent memory into position-guaranteed memory (hooks > rules > conversation) turns attention-dependent cleanup into schedule-guaranteed cleanup.

---

*Implementation: a single script scans the scaffold and emits a ranked queue. A cron job runs the health sweep Wednesdays and the drainage Saturdays. The archive is a git-tracked subtree; an INDEX file lists what was moved and why. Drainage is bounded per sweep to prevent over-correction.*
