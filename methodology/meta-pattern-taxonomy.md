# Meta-Pattern Taxonomy — Naming Class-Bugs So They Can Be Remediated

The metacognitive cycle promotes reasoning patterns — ways of thinking that consistently produce good outcomes. Meta-patterns are a different level: they are *recurring failure modes of the scaffold itself*. Named meta-patterns let a class of bug be addressed once instead of individually forever.

## The Observation

In a scaffold of ~850 notes, ~70 promoted patterns, and hundreds of rules and hooks, the same kinds of failure kept recurring. Not the same instance — different instances of the same structural shape. Left nameless, each occurrence was treated as a one-off. Named, they become classes.

A selection of recurring classes the scaffold surfaced:

### `prose-infrastructure-gap`
Rules, agent configs, and hooks that describe running `scripts/foo.py` or reading `logs/bar.jsonl` — where the referenced file does not exist. The prose documents infrastructure that was never built (or was removed). Readers assume the scaffold is more complete than it is.

Remediation: a typed commit-gate invariant that refuses NEW broken references and tracks pre-existing ones as grandfathered exceptions. See `commit-gate-invariants.md`.

### `silent-hook-rot`
Hooks, cron jobs, or scheduled tasks that are wired in but never fire (or fire and silently produce nothing). The hook exists in config, so the scaffold looks instrumented. The hook does not run, so no data accumulates. Debugging sessions waste time asking "what does the data say?" when there is no data.

Remediation: a zero-fire audit that flags hooks with no invocation record over a window. Either repair the hook or retire it — do not leave it in config as decorative evidence of instrumentation.

### `producer-orphan`
A writer script that produces a log, a dataset, or a file — where no reader ever consumes the output. The writer accumulates data; the reader was never built or was deleted. The output grows; the system's behavior does not change.

Remediation: at commit time, every producer should have an identified consumer. If the consumer does not exist, either build it or retire the producer.

### `cited-not-invoked`
A rule that documents a behavior (e.g., "every agent dispatch MUST emit a breadcrumb") but the behavior is not enforced anywhere. The rule is cited by other rules, referenced in documentation, and honored by no one because nothing triggers it. Compliance is aspirational; actual behavior is unchanged.

Remediation: default-inversion. Move the behavior from "what the rule says to do" to "what the agent's dispatch prompt actually does" — include the invocation command directly in the template the agent receives. The rule is no longer a request; it is a prefabricated action.

### `stdin-json-vs-env-var-confusion`
A hook or script reads an environment variable that is assumed to be set by the harness but actually never is. The harness delivers input via stdin as JSON; the hook ignores stdin and queries `$CLAUDE_FILE_PATH` (or similar), which is always empty. The hook appears to run but does nothing with the actual input.

Remediation: convention — all hooks read from stdin via `jq` for the known input keys. Audit any hook that reads harness-adjacent env vars; they are almost certainly wrong.

### `self-measurement-gap-in-self-improvement-systems`
A self-improvement system that lacks instrumentation to measure whether it is, in fact, improving. The compile cycle promotes patterns but does not track retraction rate. The breadcrumb system captures events but does not track gap rate. The system claims to be autopoietic but has no meter on its own effect size.

Remediation: when building a self-improvement mechanism, build its measurement at the same time. If the mechanism cannot be measured, it cannot be tuned, and its apparent progress is a narrative not a result.

## Why Naming Works

Two things happen when a meta-pattern gets named:

1. **Remediation becomes class-level.** Before naming, fixing "this hook doesn't work" is ten discrete bug fixes. After naming (`silent-hook-rot`), the fix is a single audit script that catches all current and future instances. The cost of the audit amortizes over every instance it catches.

2. **Recognition becomes automatic.** A symptom that previously took investigation to classify ("is this the same thing I saw last week?") becomes a fast pattern match. The agent sees the shape, not the details. Recognition is cheap. Investigation is expensive.

The effect is the same as in code refactoring — extract the recurring pattern, give it a name, call the name. The difference is that the recurring pattern is a *failure* rather than a useful abstraction, so the "call" is an audit or a gate rather than a function invocation.

## Naming Discipline

A meta-pattern name should be:

- **Phenomenological** — it describes what the pattern looks like, not what causes it. `prose-infrastructure-gap` describes the shape. `documentation-laziness` would be a cause hypothesis.
- **Specific** — it picks out one shape, not a family. `silent-hook-rot` is a specific failure mode; `hook-problems` is not.
- **Memorable** — short enough to cite in conversation. A name that requires the agent to copy-paste is a name that won't get cited.
- **Hyphenated-slug** — writable as a vault note, referenceable as a wikilink.

A name that does not meet these criteria rots; it gets used once and forgotten. A name that does meet them gets cited across notes, rules, and conversation, compounding the class-level remediation effect.

## Fit with the Rest of the Architecture

- **Metacognitive cycle** promotes instance patterns; this taxonomy promotes class patterns. Same mechanism (3+ instances with shared structure → named + remediated), different scope (reasoning chains vs. scaffold failure modes).
- **Commit-gate invariants** are the enforcement arm for named meta-patterns that can be caught structurally. `I_prose_infrastructure_gap` operationalizes the `prose-infrastructure-gap` class.
- **Cleanup queue** drains grandfathered instances of meta-patterns that exist before their naming. New instances are caught by gates; old instances are drained on the weekly cadence.

---

*Auto-promotion heuristic: when the same structural shape appears 3+ times across distinct instances, draft a meta-pattern name and vault note. If the shape is caught by an existing invariant, link them. If not, consider whether a new invariant is warranted — or whether the pattern is better handled as a recurring audit.*
