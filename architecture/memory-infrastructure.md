# Memory Infrastructure Architecture

The scaffold system under study operates across 7 layers of memory infrastructure. Current state: 824 vault notes + 62 promoted patterns + 35+ scheduled maintenance tasks + a specialized multi-agent team. This document describes the architecture for replication purposes — the specific content is not included, and the architecture is domain-agnostic.

## System Diagram

```
┌───────────────────────────────────────────────────────────┐
│                    SESSION (Active)                       │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │  LLM         │──│  MCP Servers │──│  Tools (Bash,  │    │
│  │  (Opus/Son)  │  │  (indexed    │  │   Edit, etc)   │    │
│  │              │  │   search etc)│  │                │    │
│  └──────┬───────┘  └──────────────┘  └────────────────┘    │
│         │                                                  │
│         │ auto-loads at session start                      │
│         ▼                                                  │
│  ┌───────────────────────────────────────────────────┐     │
│  │  LAYER 1: Auto-Memory (HOT)                       │     │
│  │  MEMORY.md (≤200 lines, always loaded)            │     │
│  │  + feedback, project, reference, user memories    │     │
│  │  Identity + config + preferences                  │     │
│  └──────┬────────────────────────────────────────────┘     │
│         │ read on demand                                   │
│         ▼                                                  │
│  ┌───────────────────────────────────────────────────┐     │
│  │  LAYER 2: Scaffold (WARM)                         │     │
│  │  journal.md — session log, rehydration point      │     │
│  │  scratchpad.md — live breadcrumbs                 │     │
│  │  active-tasks.md — work tracker                   │     │
│  │  Session continuity                               │     │
│  └──────┬────────────────────────────────────────────┘     │
│         │ queried via indexed search                       │
│         ▼                                                  │
│  ┌───────────────────────────────────────────────────┐     │
│  │  LAYER 3: Knowledge Vault (COLD)                  │     │
│  │  824 atomic notes, 10.7 links/note avg            │     │
│  │  20+ domain maps (MOCs)                           │     │
│  │  Wiki-linked graph — browsable in Obsidian        │     │
│  │  Schema-enforced frontmatter (type, status,       │     │
│  │  domains, learnable)                              │     │
│  │  Cross-domain link ratio: 98.7% of notes link     │     │
│  │  outside their home domain                        │     │
│  └──────┬────────────────────────────────────────────┘     │
│         │                                                  │
│         ▼                                                  │
│  ┌───────────────────────────────────────────────────┐     │
│  │  LAYER 4: Search Engine                           │     │
│  │  FTS5 full-text search (~30ms)                    │     │
│  │  Vector/semantic search (~2s)                     │     │
│  │  Graph-augmented spreading activation             │     │
│  │  EFE-mode re-rank (epistemic + pragmatic)         │     │
│  └───────────────────────────────────────────────────┘     │
│                                                            │
└────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│              BACKGROUND (Always Running)                  │
│                                                           │
│  ┌───────────────────────────────────────────────────┐    │
│  │  LAYER 5: Automated Maintenance (35+ tasks)       │    │
│  │                                                   │    │
│  │  Connection builder — grows link graph            │    │
│  │  Vault-fix — repairs schema/orphans/danglers      │    │
│  │  Fidelity tests — WHAT/WHY/CONTEXT/BRIDGE         │    │
│  │  RGM health check — scaffold structural property  │    │
│  │  Metacognitive compile — 3x/day pattern promotion │    │
│  │  Supersedes proposer — semantic conflict detection│    │
│  │  Walk-forward truth — self-audit of prior claims  │    │
│  │  + many domain-specific monitors                  │    │
│  └───────────────────────────────────────────────────┘    │
│                                                           │
│  ┌───────────────────────────────────────────────────┐    │
│  │  LAYER 6: Agent Team (specialized roles)          │    │
│  │                                                   │    │
│  │  Adversarial reviewer — kills bad ideas           │    │
│  │  Research agent — multi-domain search + synthesis │    │
│  │  Vault maintainer — wires connections, schema     │    │
│  │  Code QA — reviews edits against 16-item list     │    │
│  │  Metacognizer — reviews all agent reasoning       │    │
│  │  All agents read from + write to same vault       │    │
│  │  Pipeline: research → adversarial → team lead →   │    │
│  │            vault maintainer                       │    │
│  └───────────────────────────────────────────────────┘    │
│                                                           │
│  ┌───────────────────────────────────────────────────┐    │
│  │  LAYER 7: Governance Layer                        │    │
│  │  Learnable-flag frontmatter on all resources      │    │
│  │  Typed commit-gate invariants (orphan/dangler/    │    │
│  │   compile/link-density) on auto-deploys           │    │
│  │  Versioned resource registry (chaos-tested        │    │
│  │   byte-identical restore, per-resource snapshots) │    │
│  │  Contract-based spawn context (~7.7× context      │    │
│  │   reduction via physical contract-swap wrapper)   │    │
│  │  Per-tool-call trace log (30d retention → monthly │    │
│  │   summary, prune-with-safety-cutoff)              │    │
│  └───────────────────────────────────────────────────┘    │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

## Obsidian Vault Structure

The knowledge vault (Layer 3) is browsable as an Obsidian vault. The human collaborator reads and navigates via Obsidian's graph view, backlinks panel, and local search. The AI collaborator reads and writes via filesystem operations and indexed search. Same data, different interfaces.

```
knowledge/
├── notes/                          # 824 atomic notes
│   ├── <domain-1>/                 # Core operational mechanics
│   ├── bugs/                       # Bug patterns (symptom → fix)
│   ├── lessons/                    # Hard-won principles
│   ├── safety/                     # Circuit breakers
│   ├── research/                   # Research frameworks, empirical data
│   │   ├── framework/              # Theoretical models
│   │   ├── empirical/              # Experiment results
│   │   └── literature/             # Paper summaries
│   ├── self-reflection/            # AI self-reflection sessions
│   ├── cross-domain/               # Cross-domain synthesis
│   └── [20+ domain map MOCs]       # Navigation layer
├── ops/                            # Operational state
├── captures/                       # Unprocessed inbox
└── templates/                      # Schema templates
```

## Key Metrics Over Time

| Metric | Early snapshot (~350 notes) | Current (~824 notes) |
|--------|------------------------------|-----------------------|
| Notes | ~232 / ~325 | 824 |
| Links/note | 6.9 — 7.1 | 10.7 |
| Cross-domain ratio | not measured | 98.7% |
| Domain maps (MOCs) | 16 — 20 | 20+ |
| Orphans | 0 — 3 | 0 — 3 (transient, new-note wiring pending) |
| Dangling links | 0 — 3 | 3 (persistent, documented) |
| Promoted patterns | < 10 | 62 |
| Compile cycles | < 5 | 40+ (0 retracted promotions) |
| Fidelity WHAT/WHY/CONTEXT/BRIDGE | 96/70/86/— | 90/87/82/73 (F17 fresh) |
| Automated tasks | ~17 | 35+ |
| Agent team | 4 roles | 5+ roles with shared reasoning-chain log |

## Notable Empirical Findings

### The Corruption-Worse-Than-Absence Finding (R6)

Replicated across multiple conditions: feeding a scaffolded agent a *wrong* identity-layer context scored ~67% worse than the full scaffold — and ~57% worse than having *no* identity-layer context at all.

| Condition | Score |
|-----------|-------|
| FULL scaffold | 92/100 |
| NO identity layer (removed) | 69/100 (-25%) |
| WRONG identity layer (corrupted) | 30/100 (-67%) |

Wrong identity context didn't just produce wrong answers — it *refused valid questions* and *defended killed decisions*. The identity layer is not additive context. It is the interpretive scaffold through which all other domains are processed. Corrupt the scaffold, corrupt all processing.

**Implication for multi-agent systems:** Agents sharing a stale or incorrect memory layer perform WORSE than agents with no shared memory. Memory infrastructure maintenance is not optional — it is load-bearing.

### Hub Migration as Developmental Trajectory

Earlier snapshot analysis found the personal-context domain (D5) as sole integration hub. Later analysis found a second domain (operational-experience / bugs-and-safety) emerged as co-dominant:

- Ablation (D2 removal): largest performance drop
- Novel-task synthesis: D5 still dominates
- Graph structure: operational domain has highest internal integration ratio

**Interpretation:** Different hubs for different task types. Operational experience domains anchor operational reasoning. Personal-context domains anchor cross-domain synthesis. The hub migrates as experience accumulates — the system's scar tissue becomes its skeleton. This is a developmental trajectory, not degradation.

### Fidelity Recovery Through Infrastructure

Baseline fidelity dropped across several months of infrastructure drift. Adding a daily fidelity-measurement cron + a vault-first retrieval hook + breadcrumb-backed WHY reconstruction raised WHAT from ~0.60 to 0.90, WHY from ~0.78 to 0.87, CONTEXT from ~0.40 to 0.82, BRIDGE from ~0.43 to 0.73 across ~10 days. Measurement infrastructure is itself self-reinforcing.

## Replication Notes

To replicate the ablation experiment on your own scaffold:

1. **Partition** your scaffold into 4-8 semantically coherent domains
2. **Design** 2-5 cross-domain questions per domain (questions that benefit from synthesis)
3. **Baseline**: Run all questions with full scaffold, score responses
4. **Ablate**: For each domain, remove it from the scaffold and re-run all questions
5. **Corrupt**: For each domain, replace it with plausible-but-wrong content and re-run
6. **Score**: Use a citation-required rubric — not a loose "does this sound integrated" rubric
7. **Analyze**: Build the degradation matrix. Hub domains show off-diagonal degradation (corrupting them breaks other domains too); leaf domains show diagonal-only effects.

The method requires no special infrastructure beyond the ability to edit scaffold files and score responses. Any LLM with an external scaffold can be tested.

See also `governance-layer.md` for the self-modification infrastructure that sits on top of Layers 1-6 and enables safe evolution of the scaffold itself.
