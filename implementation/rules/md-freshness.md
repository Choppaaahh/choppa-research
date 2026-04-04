# Living Document Maintenance — PROACTIVE

These documents are the scaffold's immune system. When they're stale, the scaffold drifts.

## The Documents (update when their content changes, don't wait for "update MDs")

| Document | Location | Update when... |
|----------|----------|----------------|
| MEMORY.md | `~/.claude/projects/YOUR-PROJECT/memory/` | Config, system state, key lessons change |
| SCAFFOLD.md | Project root | Quick status, restart commands, current state changes |
| todo.md | `tasks/` | Task completed, new task discovered, dates pass |
| system-flows.md | `.claude/rules/` | New flow added, existing flow changed, new scheduled task |
| Agent configs | `.claude/agents/*.md` | Context section goes stale, scope changes, new standing orders |
| Session handoff | `logs/session_handoff_*.md` | Written at session end |

## Auto-detect triggers

When ANY of these happen, check if an MD needs updating:
- System state changes (component started/stopped/paused)
- Agent scope changed
- New scheduled task added
- Build queue item completed
- Config changed
- Regime or mode changed

## Scaffold Change Logging

When ANY living doc is edited, append to `logs/scaffold_changes.jsonl`:
```json
{"ts":"ISO8601","doc":"MEMORY.md","change":"description of what changed","by":"agent-name"}
```
These changes can be reviewed adversarially on next team spawn. This creates a 5th autopoietic pathway — the scaffold gets adversarial review just like code does.

## Don't wait for session end

Update the relevant document IMMEDIATELY when the change happens. A stale document misleads the next session, the next agent spawn, or the next scheduled task that reads it.

## Session end sweep

Before closing, check ALL living documents: is anything >24hrs old that should reflect today's changes? Update it.

## "Update docs and MDs" means ALL of this:
1. Update all living documents (MEMORY, SCAFFOLD, todo, system-flows, agent configs, handoff)
2. Commit + push the knowledge vault (it's a SEPARATE git repo — `cd knowledge && git add -A && git commit && git push`)
3. Commit + push the parent repo (`git add knowledge && git commit && git push`)
4. Both repos. Every time. No exceptions.

## Self-update periodically
Don't wait for the user to say "update MDs." If you've made 3+ changes to system state during a session, proactively update the relevant docs. Check every ~30 minutes of active work: is anything I changed not reflected in the living docs yet?
