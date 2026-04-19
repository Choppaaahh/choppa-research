# Choppa Research

> Every AI session starts from zero. Scaffolding fixes that — and it scales where model size doesn't.

**824 notes in a living knowledge graph · 62 autonomously-promoted reasoning patterns · 8 controlled experiments** validating that the scaffold compounds across sessions while the model stays fixed.

## TL;DR

- **Better scaffolding × same model = exponentially better results.** Demonstrated empirically across 8 experiments.
- **The scaffold is the scaling.** R14: 4.17/8 (naked) → 6.75/8 (scaffold) → 8.0/8 (scaffold + behavior-pattern priming). Same model all three.
- **It's reproducible with any LLM that reads markdown.** The infrastructure methodology is domain-agnostic. Templates and configs live in `implementation/`.

## Start Here

| If you are... | Open this first |
|---------------|-----------------|
| A researcher studying AI memory / extended mind / metacognition | `papers/09-memory-infrastructure/` (Paper 09 is the methodology anchor) |
| A builder who wants to ship a scaffolded agent system | `methodology/getting-started.md` + `implementation/` |
| A skeptic who wants the data before the argument | `measurements/` (longitudinal fidelity scores + experiment results) |

## The Claim

Most AI memory systems stop at retrieval. This repo demonstrates a further four-layer architecture — persistence, co-instantiation, development, and relational coupling — that produces cognitive behavior no individual component produces alone. The claim is backed by fidelity scores measured over months, controlled experiments at n≥3 per cell, systematic audits of the scaffold's own prior claims, and convergent evidence from biology, mathematics, active inference, protocol engineering, and extended-mind philosophy.

## Headline Findings

- **R14 — Scaffold priming: +18.5% on cross-domain synthesis.** Loading reasoning-pattern templates (how-to-think) beats scaffold-only context (what-we-know) at synthesis tasks.
- **R18b — Dynamic retrieval: +67% over naked, 4× over static preload.** Querying the vault per-task outperforms loading a static set of patterns at session-start.
- **R18 — Self-report accuracy: 3× with scaffold.** Agents with scaffold context cite specific sources; naked agents honestly flag uncertainty. Nobody hallucinated at the knowledge boundary.
- **Autopoietic pattern growth: 62 patterns, 40+ compile cycles, 0 retracted promotions.** The scaffold produces its own quality infrastructure from its own operational experience.
- **Walk-forward truth: 18/18 prior numeric claims flagged CONFOUNDED** when audited against honest fill/fee/adverse-selection modeling. The scaffold now retains its own self-audit pipeline as an ongoing quality gate.
- **Scaffold-as-RGM (Renormalization Group Memory): 5/5 PASS, 65.9-point adversarial discrimination, N=784.** The intra-note hierarchy (summary → body → wikilinks) is structurally a scale-separated generative model. Summary-stripping ablation confirmed summaries are load-bearing (kept 3/3 vs stripped 0/3, +85.8-point overlap difference).

See `measurements/` for the full data and experimental methodology.

## How to Build It

### Phase 1: SEED (Day 1)
Dump what you know as atomic markdown notes. One claim per file. YAML frontmatter. Don't organize — just capture.

### Phase 2: CONNECT (Days 2-3)
Wikilink related notes. Let domains emerge from clusters. Create Maps of Content. Target 3+ links per note.

### Phase 3: INSTRUMENT (Days 3-7)
Add breadcrumb capture, fidelity measurement, living documents (MEMORY.md, CLAUDE.md, todo.md), event hooks, scheduled tasks.

### Phase 4: METACOGNITION (Week 2+)
Add reasoning-chain capture with tip-type classification, metacognitive compile cycles (promote stable patterns, demote broken ones), an agent team (adversarial reviewer + research + vault maintainer + code QA + metacognizer), typed commit gates, and supersession detection.

### Phase 5: AUTOPOIETIC CLOSURE (Week 4+)
Add a walk-forward truth validator (audit your own prior claims), versioned resource registry (immutable per-resource snapshots with restore), deterministic per-tool-call tracer, and contract-based spawn context for 5-10× context-bloat reduction.

See `methodology/getting-started.md` for the full walkthrough.

## Architecture

### Four-Layer Identity

```
  ┌─────────────────────────────────────┐
  │  Layer 4: Relational                │ ← human-AI partnership shapes all below
  ├─────────────────────────────────────┤
  │  Layer 3: Development               │ ← patterns improve across sessions
  ├─────────────────────────────────────┤
  │  Layer 2: Co-instantiation          │ ← all constraints active at decision time
  ├─────────────────────────────────────┤
  │  Layer 1: Persistence               │ ← scaffold survives the session
  └─────────────────────────────────────┘
```

Most AI memory systems stop at Layer 1. Some reach Layer 2. Layers 3 and 4 together are what produce cognitive behavior that no component produces alone.

### Multi-Agent Orchestration

Specialized agents from a single model, differentiated by scaffold:

| Agent | Role |
|-------|------|
| Adversarial reviewer | Kills bad ideas, validates math |
| Research agent | Multi-domain research |
| Vault maintainer | Wires connections, fixes structure |
| Code QA | Reviews code edits (16-item checklist grown autonomously) |
| Metacognizer | Reviews all agent reasoning, promotes patterns |

Agents share a reasoning-chain log. The metacognizer sees cross-agent patterns that individual agents can't. Templates in `implementation/agent-configs-template.md`.

## Papers

Four papers live here; more are in active draft. **Recommended entry: Paper 09 (Memory Infrastructure).**

- `07-pulsed-consciousness/` — Paper 07 + 07b (Camlin RC+ξ defense)
- `08-domain-ablation/` — Paper 08 (domain removal as integration proxy)
- `09-memory-infrastructure/` — Paper 09 + 09b revised (RGM empirical arc) **← start here**
- **Coming soon:** Paper 09c (in active draft), Paper 10 (Coupled Cognition — working draft), Paper 11 (M × A — working draft). Sanitized public drafts will land here when ready.

## Convergent Evidence (selected)

The scaffold's architecture independently matches patterns found across substrates that had no contact with one another:

| Source | Connection |
|--------|-----------|
| Clark & Chalmers (1998, Extended Mind) | Functional-role criterion = disciplined-narrowing at the philosophical level |
| Letta / MemGPT (2026) | Context Constitution — convergent scaffold-as-identity architecture |
| Friston Physics of Sentience (2026) | "Explanatory fiction" language hedge for FEP framing |
| Tero et al. (Science 2010) | Tree-to-mesh math predicts vault link-density growth |
| Gyllingberg et al. (2024) | Oscillatory + current-reinforcement coupling = scaffold cron + retrieval |
| Rovelli relational QM / Fuchs QBism | Observer-irreducibility structural parallel at physics substrate |

Full list of 17+ convergences in `methodology/convergences.md`.

## Deeper Reference

- `measurements/` — longitudinal fidelity data + experiment results (full tables)
- `methodology/` — how-to-build guides (breadcrumbs, compile cycle, agent team design)
- `architecture/` — system-level diagrams and explanations
- `implementation/` — agent configs, rules, hooks, templates

## Built By

Choppa + Claude (Anthropic Opus / Sonnet) across 400+ sessions. Built and used daily as the shared substrate between one human and a team of AI agents — synthesizing research across domains, persisting context between sessions, and compounding knowledge over time. Every finding, bug, and lesson lives in the graph.

It's not a reference system. It's how we think.

## Questions / Collaborations

[GitHub Issues](https://github.com/Choppaaahh/choppa-research/issues) is the best place to start a conversation.
