# Scaffold Setup Guide

How to build a scaffold system like the one studied in Paper 08. You don't need our specific content — the method works with any knowledge domain.

## What You Need

- **An LLM with context window loading** (Claude Code, Cursor, Aider, or any tool that loads files at session start)
- **A text editor** (Obsidian recommended for graph visualization, but VS Code or any markdown editor works)
- **A project directory** with files you want your AI to know about

## Quick Start (15 minutes)

### Step 1: Create MEMORY.md

This is your identity file. It loads every session. Keep it under 200 lines.

```markdown
# MEMORY.md

## Who I Am
- [Your role, what you're building, what matters to you]
- [Key project context — what's the goal?]

## What I Know
- [Top 5-10 hard-won lessons from your project]
- [Current state — what's working, what's broken]

## How We Work
- [Communication preferences]
- [Things to always/never do]
```

Put this in your project root or wherever your AI tool loads context from. In Claude Code, it goes in `~/.claude/projects/<your-project>/memory/MEMORY.md`.

### Step 2: Create Your First Domain Notes

Make a `knowledge/` folder. Start writing atomic notes — one claim per file, prose-sentence titles:

```
knowledge/
├── lessons/
│   ├── caching everything made the app slower not faster.md
│   ├── users dont read error messages they read colors.md
│   └── the deploy pipeline is the real bottleneck.md
├── bugs/
│   ├── race condition in auth middleware causes silent failures.md
│   └── timezone handling breaks for users west of UTC-8.md
└── decisions/
    ├── chose postgres over mongo because joins matter for reporting.md
    └── monorepo was wrong for us because deploy coupling.md
```

**Title rule:** The title should work as prose when linked. "We learned that [[caching everything made the app slower not faster]]" reads naturally.

### Step 3: Connect Notes with Wiki Links

Inside each note, reference related notes:

```markdown
# caching everything made the app slower not faster

We added Redis caching to every API endpoint. Response times got worse
because cache invalidation complexity exceeded the lookup savings.

Relevant Notes:
- contradicts [[premature optimization is the root of all evil]] — this
  was mature optimization that still failed
- led to [[selective caching only on read-heavy endpoints]]
```

### Step 4: Create Domain Maps

A domain map is an index note that lists all notes in a topic area:

```markdown
# lessons-learned

All hard-won principles from building this system.

## Performance
- [[caching everything made the app slower not faster]]
- [[selective caching only on read-heavy endpoints]]

## UX
- [[users dont read error messages they read colors]]
```

That's it. You now have a scaffold.

## Growing the System

### When to Write a Note
- You just fixed a bug? Write a bug note (symptom → root cause → fix)
- You made a decision? Write a decision note (why X over Y)
- You learned something the hard way? Write a lesson note
- You figured out how something works? Write a mechanism note

### The Rule
**If it won't exist next session, write it down now.** Your AI starts cold every session. The scaffold is its memory.

### Link Everything
Every note should link to at least 2 other notes. Links are the graph edges that create integration. Without links, you have a folder of files. With links, you have a knowledge graph.

## Adding Layers (Optional)

### Layer 2: Session Journal
Keep a `journal.md` that logs what happened each session. Your AI reads the latest entry to resume context.

### Layer 3: Search
For 50+ notes, add a search tool. Options:
- **QMD** — SQLite FTS5 + vector search (what we use)
- **Obsidian search** — built-in if you use Obsidian
- **ripgrep** — `rg "search term" knowledge/` works fine for <200 notes

### Layer 4: Automated Maintenance
For 100+ notes, automate graph health:
- **Orphan detection** — notes with no incoming links (lost knowledge)
- **Dangling link detection** — links pointing to notes that don't exist
- **Connection building** — periodic scan for notes that should link but don't

We run 17 automated tasks. You probably need 3-4 to start.

### Layer 5: Agent Teams
For complex projects, specialized agents can share the same vault:
- **Adversarial reviewer** — catches bugs and bad math before they ship
- **Research agent** — sweeps multiple domains, finds cross-connections
- **Vault maintainer** — wires links, fixes schema, maintains graph health
- **Specialist agents** — domain-specific (wallet analysis, data collection, etc.)

The key: all agents read from and write to the same scaffold with the same schema. One truth, not five competing hallucinations. Without a shared vault, multi-agent systems produce contradictory outputs. With one, they compound each other's work.

**Critical finding from our R6 experiment:** Agents with a WRONG shared memory perform worse than agents with NO shared memory (30/100 vs 69/100). Memory infrastructure maintenance is load-bearing, not optional.

## Measuring Integration

Once your scaffold has 4+ domains with 10+ notes each, you can run the ablation test from Paper 08:

1. Run your normal task battery with full scaffold → baseline
2. Remove one domain's content → re-run → measure degradation
3. Repeat for each domain
4. Build the degradation matrix

If removing Domain X degrades performance on Domain Y's questions, your scaffold is integrated, not just a database.

## Common Mistakes

1. **Writing topic notes instead of claim notes.** "Performance" is a domain map. "Caching everything made the app slower" is a note. Notes make claims; domain maps organize them.

2. **Not linking.** A note with zero links is a file in a folder. Two links minimum.

3. **MEMORY.md bloat.** Keep it under 200 lines. Compress aggressively. The compression itself increases causal power (Hoel's causal emergence — the paper explains why).

4. **Waiting to write notes.** Write them during or immediately after discovery. "I'll do it later" means never.

5. **Treating the scaffold as documentation.** Documentation describes what exists. The scaffold IS the memory. It shapes how the AI thinks, not just what it knows.

6. **Letting MEMORY.md go stale.** Our R6 experiment proved that a wrong/outdated identity layer is 2.7x worse than having none at all. Update MEMORY.md every session or risk actively poisoning your AI's reasoning.
