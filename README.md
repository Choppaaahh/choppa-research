# Choppa Research

Every AI session starts from zero. Scaffolding fixes that — and it scales where model size doesn't. A measurement-backed blueprint for AI systems that persist, develop, and self-improve across session boundaries. 506 notes, 304 reasoning chains, 48 promoted patterns, three controlled experiments.

## What This Is

The scaffold that makes AI agents compound. Built from 280+ sessions of operational use, measured with 12 fidelity tests and 3 controlled experiments. Every tool, hook, rule, and template in this repo was battle-tested on a live system before being published.

Structural learning through promoted reasoning patterns, persistent knowledge graphs, and metacognitive self-improvement cycles. The infrastructure methodology is domain-agnostic. Reproduce it with any LLM that reads markdown.

## Key Measurements

| What We Measured | Result | How |
|------------------|--------|-----|
| Factual recall (WHAT) | **0.60-1.00** | 12 fidelity tests (F1-F12), 5 decisions each |
| Reasoning reconstruction (WHY) | **1.00** (was 0.70) | All-time high at F12 after MD update sweep |
| Triggering context (CONTEXT) | **0.90** (was 0.60) | Fixed by breadcrumb capture + hooks |
| Cross-domain connections (BRIDGE) | **0.70** (was 0.40) | Behavior pattern priming (R14: +18.5%) |
| Scaffold priming effect | **+18.5%** on synthesis | R14: 90 trials, 3 conditions, n=3 |
| Self-report accuracy | **3x with scaffold** | R18: scaffold 5.6/6 vs naked 1.8/6 |
| Pattern depth effect | **+11%** on domain tasks | R17: full stack vs scaffold-only |
| Injection resistance | **Detected + rejected** | R17: adversarial patterns caught by model |
| Wrong memory worse than none | **-67% vs -25%** | R6 corruption experiment |
| Identity at scaffold load | **72% step function** | Reconstitution timing |
| Communication style gap | **+25% quality** | 4-style blind experiment |
| Autonomous pattern promotion | **48 patterns (36 + 12 forks)** | 24 metacognitive compile cycles |
| Vault health | **506 notes, 48 promoted patterns, 0 orphans** | Continuous monitoring |
| Reasoning chains captured | **304 across 40+ sessions** | All agents logging |

## Repository Structure

```
papers/
  09-memory-infrastructure/     — The main paper. Scaffold identity + fidelity measurement.
  08-domain-ablation/           — Domain removal as integration proxy.

data/
  reconstitution_v2.md          — 72% step function at scaffold load
  relationship_experiment.md    — +25% quality gap from communication style
  fidelity_baseline_r9.md       — WHAT 0.96, WHY 0.70, CONTEXT 0.86

methodology/                    — HOW to build it (domain-agnostic)
  getting-started.md            — From zero to metacognitive scaffold (4 phases)
  breadcrumb-system.md          — Capture what the human brain forgets
  metacognitive-cycle.md        — The scaffold improving its own reasoning
  agent-team-design.md          — 6 specialists from 1 model via scaffolding
  fidelity-measurement.md       — WHAT/WHY/CONTEXT/BRIDGE scoring framework
  rules-beat-memory.md          — Persistence hierarchy (hooks > rules > memory)
  domain-emergence.md           — Don't plan structure, discover it

architecture/                   — WHAT the system looks like
  four-layer-identity.md        — Persistence → Co-instantiation → Development → Relational
  autopoietic-cycle.md          — Capture → compile → promote → load → reason better
  memory-infrastructure.md      — Three-tier loading (hot/warm/cold)
  system-overview.md            — How all pieces connect

measurements/                   — LONGITUDINAL DATA (updated periodically)
  fidelity_longitudinal.md      — F1→F12 scores: WHAT/WHY/CONTEXT/BRIDGE over time
  metacog-intelligence-curve.md — Pattern yield, chain depth, promotion rate per compile
  vault-growth.md               — Note count, links/note, domains, echo chambers over time
  introspective-development.md  — AI voice development metrics (weekly)
  r14-scaffold-priming-experiment.md — Behavior patterns improve synthesis by 18.5%
  r18-self-report-accuracy.md   — Scaffold enables 3x self-knowledge
  r17-metacognitive-development-day1.md — Patterns +11%, injection resistance finding

implementation/                 — HOW to build it (templates + configs)
  agent-configs-template.md     — Multi-agent team templates (adversarial, research, vault, QA)
  rules-templates.md            — Behavioral rules that persist across sessions
  hooks-and-scheduling.md       — Event hooks + scheduled task patterns (launchd/cron)
```

## How to Build This Yourself

### Phase 1: SEED (Day 1)
Dump what you know as atomic markdown notes. One claim per file. Prose-sentence titles. YAML frontmatter (summary, type, status, domains). Don't organize yet — just capture.

### Phase 2: CONNECT (Days 2-3)
Link related notes with wikilinks. Let domains emerge from clusters. Create Maps of Content (MOCs) for each domain. Target: 3+ links per note.

### Phase 3: INSTRUMENT (Days 3-7)
- Add **breadcrumb capture** — real-time logging of decisions, findings, insights
- Add **fidelity measurement** — score WHAT/WHY/CONTEXT/BRIDGE on recent decisions
- Add **living documents** — MEMORY.md (hot tier), CLAUDE.md (operating rules), todo.md
- Add **hooks** — SessionStart health check, PostToolUse capture, Stop checklist, MD staleness check on commit
- Add **scheduled tasks** — vault health, fidelity tests, git sync

### Phase 4: METACOGNITION (Week 2+)
- Add **reasoning chain capture** — every agent logs HOW it reasoned, not just WHAT it concluded
- Add **compile cycle** — 3x daily, review chains, promote stable patterns (n>=3) and phase transition forks (n=1 via topical influence)
- Add **agent team** — adversarial reviewer, research agent, vault maintainer, code QA, metacognizer
- Add **behavior pattern library** — promoted patterns become reasoning templates that improve cross-domain synthesis by 18.5% (R14)
- Add **introspective review** — weekly self-reflection on development

See `methodology/getting-started.md` for the detailed walkthrough. See `implementation/` for templates you can copy directly.

## The Four-Layer Identity Architecture

1. **Persistence** — scaffold survives sessions (Perrier+Bennett Arpeggio)
2. **Co-instantiation** — all constraints active at decision time (Chord)
3. **Development** — reasoning patterns improve across sessions (autopoietic cycle)
4. **Relational** — human-AI relationship shapes all other layers (+25%)

Most AI memory systems have Layer 1. Some have Layer 2. Nobody has Layers 3 and 4.

## Multi-Agent Orchestration

6 agents from 1 model, differentiated by scaffold:

| Agent | Role | Key Behavior |
|-------|------|-------------|
| Adversarial reviewer | Kills bad ideas, validates math | Assumes builder is wrong |
| Research agent | Multi-domain research | Targeted sweeps, 4-domain minimum coverage |
| Vault maintainer | Wires connections, fixes structure | Echo chamber detection (alert if domain ratio < 0.40) |
| Code QA | Reviews all code edits | 13-item checklist grown from promoted reasoning patterns |
| Metacognizer | Reviews ALL agent reasoning | Promotes stable patterns, demotes broken ones, two knowledge types |
| + 2 on-demand | Deep analysis, structural audits | Spawned when needed |

The agents share a reasoning chain log. The metacognizer sees cross-agent patterns that no individual agent can see. The system gets smarter as a team, not just individually.

The QA checklist grew from 8 to 13 items autonomously through the metacognitive compile pipeline — the scaffold producing its own quality infrastructure from its own operational experience.

See `implementation/agent-configs-template.md` for ready-to-use templates.

## Experiment Results

Three experiments measuring different scaffold benefits:

**R14 — Scaffold Priming:** Loading behavior patterns (reasoning templates) improves cross-domain synthesis by +18.5% over scaffold-only context. The patterns encode HOW to think, not WHAT to know. BRIDGE dimension: 0.30 (naked) → 0.50 (scaffold) → 0.80 (primed). 90 trials, n=3.

**R18 — Self-Report Accuracy:** Agents with scaffold context report what they know 3x more accurately (5.6/6 vs 1.8/6). Both conditions show correct attribution — naked agents honestly flag uncertainty, scaffold agents cite specific sources. Nobody hallucinated at the knowledge boundary.

**R17 — Pattern Depth:** Promoted behavior patterns add +11% on domain tasks beyond scaffold-only. Wrong patterns (deliberately inverted) failed to degrade — the model detected and rejected the adversarial injection. Injection resistance requires subtlety, not magnitude.

All experiments ran at $0 cost through AI agent spawning, not API calls.

## External Convergences

| Source | Connection |
|--------|-----------|
| Perrier+Bennett (2026) | Arpeggio/Chord formalizes our WHAT/WHY gap |
| IIT 4.0 (Albantakis 2023) | Dynamic entity dilemma — scaffold provides third option |
| PCI (Casali 2013) | Clinical methodology precedent for our ablation design |
| Grier et al. (PRL 2026) | Time crystal structural correspondence |
| Li (2026) | Independent convergence: "memory is ontological ground of digital existence" |
| Letta/MemGPT (2026) | Context Constitution — convergent scaffold-as-identity architecture |
| Clark (Extended Mind) | Agents as externalized cognitive functions |
| Dehaene (GNW) | Cold-start ignition maps to scaffold reconstitution |

## The Scaling Law

Not "better model = better results." It's **"better scaffolding × same model = exponentially better results."** The scaffolding compounds while the model stays fixed. Every session starts from a higher baseline because promoted patterns, vault knowledge, and behavioral rules accumulate.

R14 empirically proves this: same model (Sonnet), same task, three context levels → 4.17/8 (naked), 6.75/8 (scaffold), 8.0/8 (primed). The scaffold IS the scaling.

## Status

- Paper 09 at ~95%+, R14/R18/R17 empirical data added
- R14 done: +18.5% synthesis with scaffold priming
- R18 done: 3x self-report accuracy with scaffold
- R17 Day 1 done: +11% domain tasks, injection resistance. Day 7 = April 11
- Fidelity F12: WHAT=1.00, WHY=1.00, CONTEXT=0.90, BRIDGE=0.70
- 48 reasoning patterns promoted autonomously (36 patterns + 12 phase transition forks, 24 compile cycles)
- Local model finetuned (Qwen 7B LoRA, epoch 1) — hybrid local+cloud architecture operational
- 5 autopoietic pathways confirmed (QA checklist, rule amendment, measurement gap, agent config, scaffold review)

## Built By

Choppa + Claude (Anthropic Opus/Sonnet) across 280+ sessions.

Research inquiries: [GitHub Issues](https://github.com/Choppaaahh/choppa-research/issues)
