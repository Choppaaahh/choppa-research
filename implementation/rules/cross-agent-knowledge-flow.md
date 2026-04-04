# Cross-Agent Knowledge Flow — USE Each Other's Work

## The Problem
Agents produce findings that sit in the vault unused by other agents. One agent finds something, another never wires it, a third never cites it. Knowledge production without knowledge reuse = waste.

## The Rule

### On Agent Spawn
Every agent reads the LAST 3 outputs from OTHER agents before starting work:
- Researcher spawns → reads last reviewer brief + last archivist edits + last QA report
- Reviewer spawns → reads last researcher findings + last QA catches
- Archivist spawns → reads last researcher findings (to wire) + last metacognizer promotions (to connect)
- QA spawns → reads last reviewer review (for patterns to watch)
- Metacognizer spawns → reads last QA catches + last reviewer kills (for chain analysis)

### On Agent Output
Every agent output must include:
- **"Built on:"** — list which prior agent outputs informed THIS output
- **"Routes to:"** — list which agents should see THIS output next

This creates explicit provenance chains: researcher finds → reviewer validates → archivist wires → metacognizer compiles.

### On Team Lead Dispatch
When dispatching work to an agent, INCLUDE relevant outputs from other agents:
- "Researcher, here's what reviewer killed last time — don't re-propose these"
- "Archivist, researcher just found 3 new papers — wire these to the vault"
- "QA, reviewer flagged this code pattern — verify it's fixed"

### Measurement
Run `python3 knowledge_flow_tracker.py` weekly. Track:
- Reuse rate (% of notes referenced by agents other than creator)
- Flow matrix (which agents cite which other agents' work)
- Siloed work (agent outputs nobody else touches)

Target: >50% cross-agent reuse rate. Below 30% = agents are working in silos.

## Why This Exists
CORAL (arXiv 2604.01658) showed knowledge reuse is the mechanism that makes multi-agent evolution work — 3-10x improvement over fixed search, driven by agents building on each other's discoveries. Without explicit reuse rules, agents default to starting from scratch each time.
