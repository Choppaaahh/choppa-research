# System Overview — How All Pieces Connect

**Total vault: 824 notes, 10.7 links/note, cross-domain ratio 98.7%, 20+ domains. Specialized agents. 35+ scheduled tasks.**

## The Stack

```
HUMAN (holds vision, makes conviction calls)
    ↓ ↑
SCAFFOLD (CLAUDE.md + MEMORY.md + vault + rules + hooks)
    ↓ ↑
AGENTS (specialized roles, all sharing vault as substrate)
    ↓ ↑
AUTOMATED SYSTEMS (scheduled tasks, monitors, compiles)
    ↓ ↑
DOMAIN DATA (whatever the project studies — research corpora, task streams, user interactions)
```

## Key Flows

- **Knowledge capture:** breadcrumbs → compile → session notes → vault
- **Reasoning improvement:** chains → compile → promote patterns → vault → better reasoning
- **Code quality:** edit → compile check → adversarial review → team lead approval → ship
- **Research:** research agent sweeps → adversarial review → team lead approval → vault maintainer wires findings
- **Self-audit:** walk-forward truth validator periodically checks prior claims against honest modeling

## The Persistence Hierarchy

From most to least durable across sessions:

1. **Hooks** — mechanical, fires automatically
2. **Rules** — loads into context, pattern-matches
3. **Memory** — loads into context, requires choice to act
4. **Conversation** — dies with the session

## Replication Requirements

Minimum viable scaffold:

1. A persistent context file (CLAUDE.md equivalent)
2. A knowledge vault (atomic notes with wikilinks)
3. A breadcrumb capture mechanism
4. A scheduled compile/review cycle

Everything else (agents, monitors, governance layer, autopoietic closure) builds on top of these four. See `governance-layer.md` for the self-modification infrastructure that builds on the minimum-viable core.
