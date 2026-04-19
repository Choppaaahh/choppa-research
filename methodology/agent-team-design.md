# Agent Team Design — Specialized Cognition from One Model

Our system runs multiple agents, all using the same Claude model. The scaffolding makes them functionally different intelligences. Total vault: 824 notes serving as shared knowledge substrate.

## The Insight

One general-purpose AI chat is weaker than multiple specialized agents with defined roles, guardrails, and routing. The specialization comes from CONTEXT (agent config files), not from different models.

## Agent Roster

| Agent | Model tier | Role | Key Behavior |
|-------|-----------|------|-------------|
| Adversarial reviewer | Opus | Adversarial review | Assumes builder is wrong. Kills bad ideas. Validates good ones. |
| Research agent | Sonnet | Multi-domain research | Single sweeps across target domains. Routes findings through adversarial reviewer. |
| Vault maintainer | Sonnet | Vault health | Fixes orphans, danglers, schema. Wires cross-domain connections. |
| Code QA | Sonnet | Code quality | Compile check, import verification, math audits. Every code edit routed here. |
| Observer | Sonnet | Domain intelligence | Persistent watcher. Regime learning. Session personality mapping. |
| Metacognizer | Sonnet | Pattern promotion | Reviews all agent reasoning chains. Promotes stable patterns. |
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
- Research pipeline (research agent → adversarial review → team lead → vault maintainer)
- No infinite loops (go idle after task completion)
- Escalation rules

**3. All agents log reasoning chains** to a shared file. The metacognitive compile reviews chains from ALL agents together. Team-wide patterns emerge.

## Routing Pipelines

```
Research:  Research agent → Adversarial review → Team Lead (approve) → Vault maintainer
Code:      Edit code → compile check → Code QA review → adversarial review on critical files
Domain:    Watcher (script) → Observer (AI) → session notes → proposals
```

## How to Replicate

You don't need 7 agents. Start with 2:
1. **A builder** (writes code, makes decisions)
2. **A reviewer** (challenges assumptions, checks math)

Add as needed:
3. **A researcher** (when you need external knowledge)
4. **A vault maintainer** (when the vault grows past ~100 notes)
5. **A metacognizer** (when reasoning chain volume exceeds manual review)

The key is SEPARATION OF CONCERNS. The builder shouldn't review their own code. The researcher shouldn't implement their own findings. The routing between agents IS the quality control.

## Governance Layer

Each agent operates within a three-layer structural contract:
- **VIEW** (locked) — what the agent sees and what tools it uses. Cannot self-modify.
- **STRUCTURE** (team-lead only) — who reports to whom, routing paths. Agents cannot rewire this.
- **EVOLUTION** (free) — agents contribute to shared knowledge, log chains, propose vault notes.

Knowledge growth is encouraged. Role drift is not. See `architecture/governance-layer.md` for the full contract specification.
