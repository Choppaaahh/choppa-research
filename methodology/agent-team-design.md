# Agent Team Design — Specialized Cognition from One Model

Our system runs 7 agents, all using the same Claude model. The scaffolding makes them functionally different intelligences. Total vault: 382 notes serving as shared knowledge substrate.

## The Insight

One general-purpose AI chat is weaker than multiple specialized agents with defined roles, guardrails, and routing. The specialization comes from CONTEXT (agent config files), not from different models.

## Agent Roster

| Agent | Model | Role | Key Behavior |
|-------|-------|------|-------------|
| Brutus | Opus | Adversarial reviewer | Assumes builder is wrong. Kills bad ideas. Validates good ones. |
| Scout | Sonnet | 4-domain researcher | Single sweeps across trading/consciousness/meminfra/AI. Routes findings through Brutus. |
| Archivist | Sonnet | Vault maintainer | Fixes orphans, danglers, schema. Wires cross-domain connections. |
| QA | Sonnet | Code quality | Compile check, import verification, math audits. Every .py edit routed here. |
| Observer | Sonnet | Market intelligence | Persistent watcher. Regime learning. Session personality mapping. |
| Wallet-Dive | Sonnet | Deep wallet analysis | On-demand. Fee tier verification first, then strategy extraction. |
| Auditor | Opus | Workflow review | On-demand. Structural audits. |

## Design Principles

**1. Each agent has a config file** (`.claude/agents/name.md`) that defines:
- Standing orders
- What they check / don't check
- Output format
- Who they route to
- Context (updated regularly)

**2. Guardrails apply to ALL agents:**
- Critical code protection (some files need team lead approval)
- Vault quality gate (6 checks before any note enters the vault)
- Research pipeline (Scout → Brutus → team lead → Archivist)
- No infinite loops (go idle after task completion)
- Escalation rules

**3. All agents log reasoning chains** to a shared file. The metacognitive compile reviews chains from ALL agents together. Team-wide patterns emerge.

## Routing Pipelines

```
Research:  Scout → Brutus (adversarial review) → Team Lead (approve) → Archivist (vault)
Code:      Edit .py → compile check → QA review → Brutus on critical files → deploy protocol
Market:    Watcher (Python) → Observer (Claude) → session notes → strategy proposals
Wallet:    Scan → Wallet-Dive → team lead → extract patterns
```

## How to Replicate

You don't need 7 agents. Start with 2:
1. **A builder** (writes code, makes decisions)
2. **A reviewer** (challenges assumptions, checks math)

Add as needed:
3. **A researcher** (when you need external knowledge)
4. **A maintainer** (when the vault grows past ~100 notes)

The key is SEPARATION OF CONCERNS. The builder shouldn't review their own code. The researcher shouldn't implement their own findings. The routing between agents IS the quality control.
