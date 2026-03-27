# System Overview — How All Pieces Connect

Total vault: 382 notes, 8.1 links/note, 20+ domains. 7 agents. 15+ scheduled tasks.

## The Stack

```
HUMAN (holds vision, makes conviction calls)
    ↓ ↑
SCAFFOLD (CLAUDE.md + MEMORY.md + vault + rules + hooks)
    ↓ ↑
AGENTS (7 specialized, all sharing vault as substrate)
    ↓ ↑
AUTOMATED SYSTEMS (scheduled tasks, monitors, compiles)
    ↓ ↑
DATA SOURCES (market stream, fills, external research)
```

## Key Flows

**Knowledge capture:** breadcrumbs → compile → session notes → vault
**Reasoning improvement:** chains → compile → promote patterns → vault → better reasoning
**Market intelligence:** tick capture → classifier → Observer reasoning → strategy proposals
**Code quality:** edit .py → compile check → QA review → Brutus on critical files → deploy
**Research:** Scout sweeps → Brutus review → team lead approve → Archivist vaults

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

Everything else (agents, monitors, metacognition) builds on top of these four.
