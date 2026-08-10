# Agent Team Design — Specialized Cognition, Routed Not Spawned

Our system runs many specialized AI workers off a small set of models. The scaffolding — not the model — makes them functionally different intelligences. Shared substrate: a ~2,400-note living knowledge vault.

## The Insight (unchanged)

One general-purpose AI chat is weaker than many specialized workers with defined roles, guardrails, and routing. Specialization comes from CONTEXT — role definitions, injected conventions, spec contracts — not from different weights.

## The Architecture: a routed office, not a standing team

Work is classified by reasoning threshold and routed to the cheapest layer that can carry it:

| Tier | What runs there | Mechanism |
|---|---|---|
| **Mechanical code-drafting** | New scripts, boilerplate, structured transforms | Offload to routed non-frontier models with a spec CONTRACT: golden fixtures (ground-truth I/O pairs the model asserts verbatim, never recomputes), adversarial self-test requirements, entry-point tests |
| **Scheduled specialists** | Vault gardening, backlog harvesting, system audits, gap-drains | Cron-fired wrapper scripts, each assembling fresh context per run — stateless workers, no drift |
| **Adversarial review** | Every substantive artifact | An escalation ladder: a cheap *decorrelated pair* (two different-lab models voting) first; bigger models only when stakes or disagreement demand it |
| **In-session subagents** | Deep adversarial passes, cross-model verification, triage sweeps | Spawned rarely, deliberately, with standing orders — the escalation class, not the default |
| **The orchestrator** | Judgment, synthesis, operator dialogue, final verification | The main session. Never offloaded. |

## The Verification Spine (where the quality actually comes from)

Every worker's output is **untrusted until verified** — the trust membrane:

1. **T1** — does it compile / parse?
2. **T2** — does it pass its own self-test against *pre-computed* golden fixtures? (The truth-source is decorrelated from the code-author: the spec-writer computes expected values, the builder asserts them.)
3. **T3** — does it behave on *real* data? Fixtures test pure functions; production code dies in the glue. One test must always invoke the real entry point.

The recurring lesson that shaped this: defect *rate* is roughly model-independent. The variable you control is **which tier catches the defect** — and every lever pushes catches from expensive tiers (deep review, production) into cheap ones (compile, self-test).

## Decorrelation as a design principle

Two different-lineage models reviewing beat one bigger same-lineage model. Shared training lineage means shared blind spots; the review ladder deliberately crosses labs. (This is the same principle behind our public co-failure benchmark — it's load-bearing in production here, not just measured.)

## Routing pipelines (current)

```
Code:      spec w/ golden fixtures → routed builder → T1/T2 self-verify → orchestrator T3 → review ladder
Research:  scoped dispatch → external-source worker → orchestrator verification (claims re-checked at source) → vault
Maintenance: cron fires specialist → bounded pass w/ write-receipts → change-log with provenance
```

Routing between workers IS the quality control. The builder never grades its own work; the truth-source for tests never comes from the code-author; review crosses model lineages.

## Governance Layer (unchanged)

Every worker operates within a three-layer contract:
- **VIEW** (locked) — what it sees, what tools it gets. Cannot self-modify.
- **STRUCTURE** (orchestrator-only) — who routes to whom. Workers cannot rewire.
- **EVOLUTION** (free) — workers contribute knowledge, log reasoning, propose notes.

Knowledge growth is encouraged. Role drift is not. Full contract: `architecture/governance-layer.md`.

## How to Replicate

Start with two roles: a **builder** and a **reviewer** — and make the reviewer's fixtures come from you, not the builder. Add, in order, as volume demands:
3. **Scheduled maintenance workers** (when your knowledge base needs regular tending)
4. **A review ladder** (when one reviewer becomes the bottleneck — add a cheap decorrelated pair below it)
5. **Spec contracts with golden fixtures** (the single highest-leverage upgrade: it converts expensive review catches into free self-test catches)

The key remains SEPARATION OF CONCERNS — enforced by routing, not by trust.
