# Rules Beat Memory — The Persistence Hierarchy

The single most important operational lesson from 8 weeks of scaffold development.

## The Problem

A behavioral habit (like "capture breadcrumbs") exists in memory. Every new session KNOWS it should do it. But it doesn't FEEL the urgency — the behavioral activation requires more than just knowing the rule.

This is the Arpeggio/Chord distinction (Perrier & Bennett, 2026):
- **Arpeggio:** the ingredient (rule) is present somewhere in the scaffold
- **Chord:** all ingredients are co-instantiated at decision time (urgency + rule + context)

Facts transfer. Urgency doesn't.

## The Persistence Hierarchy

From most to least durable across session boundaries:

1. **Hooks** (PostToolUse, SessionStart) — fires automatically, no AI involvement. Maximum persistence.
2. **Rules** (`.claude/rules/` files) — loads into context every session, fires on pattern match. High persistence.
3. **Memory** (MEMORY.md) — loads into context, requires AI to choose to act. Medium persistence.
4. **Conversation** — dies with the session. Zero persistence.

**Always push behavioral habits as HIGH up this hierarchy as possible.**

## Examples

| Habit | Bad (conversation) | Better (memory) | Best (rule/hook) |
|-------|-------------------|-----------------|-------------------|
| "Send code to QA" | "Remember to route to QA" | Memory note: "always send to QA" | PostToolUse hook on .py edits |
| "Capture breadcrumbs" | "Don't forget breadcrumbs" | Feedback memory about breadcrumbs | Rule with explicit trigger patterns |
| "Update living docs" | "Check MDs before closing" | Stop hook reminder | Stop hook that checks freshness |

## The Operational Lesson

If a new workflow is agreed on in conversation, **implement it immediately** as a hook, rule, or script. Never say "we should do X next session." The terminal closes and it's gone.

The cost of implementing now: 5-10 minutes.
The cost of forgetting: hours of realignment in the next session.
