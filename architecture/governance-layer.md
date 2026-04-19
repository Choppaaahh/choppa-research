# Governance Layer — Safe Self-Modification

Layers 1-6 of the memory infrastructure (see `memory-infrastructure.md`) handle capture, storage, retrieval, and reasoning. The governance layer sits on top and answers a different question: **how does the scaffold modify itself safely?**

When a scaffold has an autopoietic compile cycle (see `autopoietic-cycle.md`) that can promote patterns, amend rules, and restructure resources, it can also corrupt itself. The governance layer is the set of guardrails + invariants + audit infrastructure that makes self-modification survivable.

## Five governance primitives

### 1. Learnable-flag frontmatter

Every resource in the scaffold has a `learnable: true | false` flag in its frontmatter. This flag determines whether autonomous agents may modify the resource.

```yaml
---
name: guardrails.md
learnable: false   # core safety definitions — only the human modifies
---
```

```yaml
---
name: pattern-check-what-scaled.md
learnable: true    # promoted reasoning pattern — compile cycle may update
---
```

A pre-commit hook blocks any commit that modifies a `learnable: false` file unless an explicit `LEARNABLE_OVERRIDE=1` env var is set. This moves the governance decision from "rules the agent should read" to "structural property of the file the filesystem enforces."

**Principle:** make evolvability a property of the resource, not a judgment the modifying agent has to make every time.

### 2. Typed commit-gate invariants

On every auto-deploy path, a commit gate runs a set of typed invariants before the commit proceeds. Four core invariants in the reference implementation:

- `I_orphan` — no new notes with zero incoming wikilinks (prevents dead additions)
- `I_dangler_delta` — set-difference of broken wikilink targets does not increase (allows fixing broken links, blocks adding new ones)
- `I_compile` — any modified `.py` file passes `py_compile` (no syntax errors shipped)
- `I_link_density` — average links-per-note does not drop by more than a threshold (prevents silent graph-structure regressions)

Any failing invariant blocks the commit + logs the blocked change to `scaffold_changes.jsonl` with the failing invariant list.

**Principle:** preventive invariant checks are stronger than reactive human review. Human review catches errors after they ship; invariant checks catch them pre-commit.

### 3. Versioned resource registry

Every learnable resource gets immutable per-resource snapshots on change:

```
.claude/snapshots/
├── metacognition.md/
│   ├── v1.0.0.md
│   ├── v1.0.1.md
│   └── .index.json  (hash, mtime, version, ancestor)
├── pattern-check-what-scaled.md/
│   ├── v1.0.0.md
│   └── .index.json
...
```

CLI operations: `register`, `list`, `diff`, `restore`, `scan`, `status`.

Chaos-test validated: corrupting a resource, restoring from a prior version, and verifying byte-identical SHA256 match against the saved snapshot. Restore time for a ~50-line rules file: under 100ms.

**Principle:** git history is per-commit and repository-wide. Per-resource versioning gives you a ``restore(name, version)`` primitive that is one operation, regardless of how many commits touched the file.

### 4. Contract-based spawn context

Agent configurations in a production scaffold can be 5-10 KB each. When spawning multiple agents per session, context-bloat becomes real.

The contract system auto-generates compressed "capability + constraint" specs for each agent and tool. A wrapper script physically swaps the full agent configs with their contract equivalents before launching a subordinate session, then restores the full configs on exit via a `trap`-based handler with lockfile protection.

Measured savings in the reference implementation: ~7.7× spawn-context reduction (~78 KB full config → ~10 KB contracts across 11 agent configs).

**Principle:** the swap is a run-time decision ( `--use-contracts` flag), not a permanent config change. When deeper context is needed for a task, full configs still apply.

### 5. Tracer with safety-cutoff pruning

Every agent dispatch records a deterministic trace: inputs, tool calls in order, decisions made, outputs, durations. Retained raw for 30 days, then summarized to monthly aggregates.

Critical detail in the prune path: `summarize` records a `summary_cutoff_ts` per monthly summary. `prune` only deletes traces with `ts_start < summary_cutoff_ts`. This prevents the bug where a new trace in month M gets silently pruned because the month has *any* summary file — even one written before the new trace existed. The safety cutoff is load-bearing.

**Principle:** audit infrastructure has its own correctness conditions. A tracer that silently loses traces is worse than no tracer.

## Beyond the five primitives

Two more governance mechanisms worth noting:

### Walk-forward truth validator

Audits the scaffold's own prior numeric claims against honest modeling. When a scaffold accumulates empirical claims over months, some of those claims will have been derived under methodology that later gets invalidated. The walk-forward-truth validator systematically re-tests prior claims against current methodology and flags CONFOUNDED claims for re-review. In the reference implementation, a single run flagged 18/18 reinforcement-learning-derived backtest claims as confounded — claims that would otherwise have continued to be cited as validated evidence.

### Supersedes proposer

A semantic-similarity pipeline that identifies pairs of promoted patterns where the newer one likely supersedes the older. Does not auto-merge — surfaces proposals for human review. Prevents the scaffold from accumulating redundant patterns that retrieval would treat as independent signals.

## Composition

The five primitives compose. A typical self-modification event:

1. Metacognitive compile produces a candidate pattern change
2. Learnable-flag check confirms the target file is modifiable
3. Pattern-quality scorer runs (7-dim composite score, flags low-quality candidates for adversarial review)
4. Commit-gate runs typed invariants
5. Resource registry snapshots the pre-change state
6. Change applies; scaffold_changes.jsonl logs it with `auto_approved: true` + gate reason
7. Tracer records the dispatch trace of any agent involved

Any step can block the change. Each step has a distinct failure mode. Together they convert "the scaffold can modify itself" from a liability into a survivable property.

## Why this matters for replication

The autopoietic cycle on its own is a nice idea that will damage any scaffold it runs on within a few dozen iterations, because nothing stops the compile from promoting broken patterns or corrupting protected resources. The governance layer is what makes the autopoietic claim serviceable in practice.

If you're building a scaffolded LLM system, implement the governance primitives early. They're much easier to retrofit at 200 notes than at 2000.
