# Memory Infrastructure Architecture

The scaffold system under study operates across 6 layers of memory infrastructure, totaling 439 markdown documents. This document describes the architecture for replication purposes — the specific content is not included.

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    SESSION (Active)                       │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Claude LLM  │──│  MCP Servers  │──│  Tools (Bash,  │  │
│  │  (Opus/Son)  │  │  (QMD, Git,   │  │   Edit, etc)   │  │
│  │              │  │   Discord)    │  │                │  │
│  └──────┬───────┘  └──────────────┘  └────────────────┘  │
│         │                                                 │
│         │ auto-loads at session start                      │
│         ▼                                                 │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  LAYER 1: Auto-Memory (HOT)                         │  │
│  │  MEMORY.md (200 lines, always loaded)               │  │
│  │  + feedback, project, reference, user memories       │  │
│  │  10 files | Identity + config + preferences          │  │
│  └──────┬──────────────────────────────────────────────┘  │
│         │ read on demand                                  │
│         ▼                                                 │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  LAYER 2: Scaffold (WARM)                           │  │
│  │  journal.md — session log, rehydration point         │  │
│  │  scratchpad.md — live breadcrumbs                    │  │
│  │  active-tasks.md — work tracker                      │  │
│  │  48 files | Session continuity                       │  │
│  └──────┬──────────────────────────────────────────────┘  │
│         │ queried via QMD search                          │
│         ▼                                                 │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  LAYER 3: Knowledge Vault (COLD)                    │  │
│  │  325 atomic notes, 7.14 links/note avg               │  │
│  │  20 domain maps (MOCs)                               │  │
│  │  Wiki-linked graph — browsable in Obsidian           │  │
│  │  Schema-enforced frontmatter (type, status, domains) │  │
│  │  351 files | Durable external memory                 │  │
│  └──────┬──────────────────────────────────────────────┘  │
│         │                                                 │
│         ▼                                                 │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  LAYER 4: Search Engine (QMD)                       │  │
│  │  FTS5 full-text search (~30ms)                       │  │
│  │  Vector/semantic search (~2s)                        │  │
│  │  Deep search with query expansion (~10s)             │  │
│  │  443 documents indexed                               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              BACKGROUND (Always Running)                  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  LAYER 5: Automated Maintenance (17 tasks)          │  │
│  │                                                     │  │
│  │  Connection builder (4x/day) — grows link graph      │  │
│  │  Vault-fix (8hr) — repairs schema/orphans/danglers   │  │
│  │  Brain-cycle (6hr) — detects gaps, generates plans   │  │
│  │  Fidelity-test (12hr) — WHAT/WHY/CONTEXT scoring     │  │
│  │  Eigenform tracker (12hr) — convergence metrics      │  │
│  │  Journal-update (daily) — auto session log           │  │
│  │  Morning-brief (daily) — status summary              │  │
│  │  Self-reflection (daily) — what worked/didn't        │  │
│  │  + 8 more (backup, git-sync, topology, etc)          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  LAYER 6: Agent Team (4 specialized agents)         │  │
│  │                                                     │  │
│  │  Brutus (Opus) — adversarial code/math reviewer     │  │
│  │  Scout (Sonnet) — 3-domain research + cross-synth   │  │
│  │  Archivist (Sonnet) — vault maintenance + linking   │  │
│  │  Wallet-Dive (Sonnet) — wallet analysis specialist  │  │
│  │  All agents read from + write to same vault          │  │
│  │  Pipeline: Scout → Brutus → Team Lead → Archivist   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  LAYER 7: Code Intelligence (GitNexus)              │  │
│  │  6,246 symbols | 14,329 relationships               │  │
│  │  300 execution flows | Impact analysis               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Obsidian Vault Structure

The knowledge vault (Layer 3) is browsable as an Obsidian vault. The human collaborator reads and navigates via Obsidian's graph view, backlinks panel, and local search. The AI collaborator reads and writes via filesystem operations and QMD semantic search. Same data, different interfaces.

```
knowledge/
├── notes/                          # 304 atomic notes
│   ├── domain-1/                   # D1: Core mechanics
│   ├── bugs/                       # Bug patterns (symptom → fix)
│   ├── lessons/                    # Hard-won principles
│   ├── safety/                     # Circuit breakers
│   ├── research/                   # D2: Research domain
│   │   ├── framework/              # Theoretical models
│   │   ├── empirical/              # Experiment results
│   │   ├── identity/               # Scaffold-identity findings
│   │   └── literature/             # Paper summaries
│   ├── self-reflection/            # AI self-reflection sessions (32+)
│   ├── cross-domain/               # Cross-domain synthesis
│   └── [20+ domain map MOCs]       # Navigation layer
├── ops/                            # Operational state
├── captures/                       # Unprocessed inbox
└── templates/                      # Schema templates
```

## Domain Partition (as tested in V2)

| Domain | Label | Content | V2 (232) | V3 (325) |
|--------|-------|---------|----------|----------|
| D1 | Core Mechanics | Domain-specific architecture, parameters, models | ~45 | ~83 |
| D2 | Bugs & Safety | Bug patterns, safety systems, failure modes | ~25 | ~62 |
| D3 | Signals | Signal processing, regime detection, data interpretation | ~15 | ~41 |
| D4 | Operations | Procedures, deployment, operational knowledge | ~20 | ~43 |
| D5 | Personal Context | Identity, AI sessions, lessons, collaborator history | ~12 | ~91 |
| D6 | Research | Theoretical frameworks, empirical data, cross-domain synthesis | ~40 | ~172 |
| **Total** | | | **~232** | **~325** |

## Key Measurements

| Metric | V2 (Mar 12) | V3 (Mar 22) | Change |
|--------|------------|-------------|--------|
| Notes | 232 | 325 | +40% |
| Links/note | 6.9 | 7.14 | +3% |
| Domain maps | 16 | 20 | +25% |
| Orphan notes | 0 | 1 | +1 (today's session, not yet linked) |
| Dangling links | 0 | 3 | +3 |
| Φ_coarse | 1.056 | 0.620 | -41% (see note below) |
| Fidelity (W/W/C) | 100/80-93/50-60 | 96/70/86 | WHY degraded, CONTEXT +43% |
| Eigenform | 3/5 converging | 4/5 converging | +1 signal |
| Sessions | ~230 | 260+ | +30 |
| Total MDs | ~350 | 450+ | +29% |
| Agent team | — | 4 agents (Brutus, Scout, Archivist, Wallet-Dive) | NEW |
| Launchd tasks | — | 17 automated tasks | NEW |

### Φ_coarse Drop: A Scaling Artifact

Φ_coarse dropped from 1.056 → 0.620 between V2 and V3. This is NOT integration decay — it is a measurement artifact from asymmetric domain growth. The largest domain (D6) grew from ~17% to ~53% of the vault with high internal link density (integration ratio 0.275). The formula `cross_ratio × ln(N)` penalizes domains that are simultaneously dense AND bridging.

Three rounds of targeted cross-domain linking raised D6's integration ratio from 0.275 → 0.677, but Φ_coarse continued to fall because the formula's expected cross-domain baseline rises faster than actual cross-links can grow when one domain dominates.

The R6 corruption test provides behavioral evidence of integration independent of graph topology: FULL scaffold (92/100) vs NO-D5 (69/100) vs WRONG-D5 (30/100). The 2.7x corruption:absence ratio proves causal integration regardless of what Φ_coarse reports.

**Implication:** Φ_coarse needs normalization for domain size or supplementation with behavioral metrics at vault scales above ~250 notes.

### Hub Migration: D5 → D2/D4 Co-Dominance

Paper 08 found D5 (Personal Context) as sole integration hub. V3 ablation (R1, March 22) found D2 (Bugs & Safety) emerged as co-dominant:
- R1 (ablation): D2 removal caused largest performance drop (-5.0%), D5 second (-3.7%)
- R8 (novel tasks): D5 still dominates for cross-domain synthesis (+0.55) vs domain knowledge (+0.35)
- R10 (graph structure): D4 (Operations) has highest integration ratio (0.704)

**Interpretation:** Different hubs for different task types. Operational experience domains anchor operational reasoning. Personal context anchors cross-domain synthesis. The hub migrates as experience accumulates — the system's scar tissue becomes its skeleton. This is a developmental trajectory, not degradation.

### R6 Corruption Test: Wrong Scaffold > No Scaffold

The strongest finding from V3: feeding a WRONG personal context (fabricated identity, wrong balance, wrong strategy, wrong fee model) scored 67% lower than the full scaffold — and 57% lower than having NO personal context at all.

| Condition | Score |
|-----------|-------|
| FULL scaffold | 92/100 |
| NO D5 (removed) | 69/100 (-25%) |
| WRONG D5 (corrupted) | 30/100 (-67%) |

Wrong D5 didn't just produce wrong answers — it **refused valid questions** and **defended killed strategies**. D5 is not additive context. It is the interpretive scaffold through which all other domains are processed. Corrupt the scaffold, corrupt all processing.

**Implication for multi-agent systems:** Agents sharing a stale or incorrect memory layer perform WORSE than agents with no shared memory. Memory infrastructure maintenance is not optional — it is load-bearing.

## Replication Notes

To replicate the ablation experiment on your own scaffold:

1. **Partition** your scaffold into 4-8 semantically coherent domains
2. **Design** 2-5 cross-domain questions per domain (questions that benefit from synthesis)
3. **Baseline**: Run all questions with full scaffold, score responses
4. **Ablate**: For each domain, remove it from the scaffold and re-run all questions
5. **Score**: Use a citation-required rubric (our V2 scorer) — not a loose "does this sound integrated" rubric (our V1 scorer)
6. **Analyze**: Build the degradation matrix. Hub domains show off-diagonal degradation; leaf domains show diagonal-only

The method requires no special infrastructure beyond the ability to edit scaffold files and score responses. Any LLM with an external scaffold can be tested.
