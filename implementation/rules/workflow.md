# Workflow Rules

## Plan-First Gate (NON-NEGOTIABLE)
Before coding, check: does this task hit ANY of these triggers?
- **Touches 3+ files** — architectural change, plan the blast radius
- **Touches critical files** — files that run live, process real data, or gate deployments
- **New system/loop/pipeline** — anything that creates a new data flow or feedback loop
- **Cross-cutting concern** — change affects multiple agents, scheduled tasks, or output channels
- **User says "design", "architect", "how should we"** — they want dialogue, not code

If ANY trigger fires: **STOP. Present the plan to the user BEFORE writing code.** Format:
```
PLAN: [what we're building]
FILES: [which files change]
BLAST RADIUS: [what could break]
STEPS: [ordered implementation]
OPEN QUESTIONS: [decisions that need user input]
```

This opens dialogue. The user stress-tests the plan, catches design issues, suggests alternatives. THEN we code.

WHY: Build momentum makes models skip design review. The cost of planning is 5 minutes. The cost of catching bugs post-implementation is much higher.

## Self-Improvement Loop
After ANY bug fix or correction:
1. Update `knowledge/bug-patterns/` with a new note (or update existing)
2. Include: what broke, root cause, fix applied, how to detect if it recurs
3. Wikilink to affected systems
4. Review `knowledge/bug-patterns/` at session start before making changes

Never fix the same bug twice. If you are — the lesson wasn't captured.

## Verification Before Done
Never mark a fix complete without proving it works:
1. After code change → grep to confirm the change is in place
2. After deploy → check logs for expected behavior
3. After parameter change → verify the parameter reads correctly at runtime

Ask: "What would prove this fix actually works?" Then do that thing.

## Autonomous Bug Fixing
When given a bug report:
1. Check `knowledge/bug-patterns/` first — has this been seen before?
2. Grep for the symptom in logs and code
3. Trace root cause before proposing fix
4. Fix it. Don't ask permission, don't hand-hold.
5. Verify the fix (see above)
6. Log the pattern (see Self-Improvement Loop)

Zero context switching from the user. Use available context.

## Task Management (multi-step work)
For any dispatch with 3+ steps:
1. Write plan to `tasks/todo.md` with checkable items before starting
2. Check in: "Plan is X steps, starting with Y. Confirm?"
3. Mark items complete as you go
4. If something breaks mid-plan → STOP, re-plan, don't push through
5. After completion → add review notes to `tasks/todo.md`
6. Capture lessons if any corrections were made

## Deploy Protocol (NON-NEGOTIABLE)
Before ANY code runs in a live environment:
1. **Write tests** — minimum 2 tests per new function. Cover the happy path + the most likely edge case.
2. **Run full test suite** — ALL must pass.
3. **Compile check** — verify syntax on every modified file.
4. **Adversarial review** — Re-read the code as if you did NOT write it. Ask: "What breaks? What's the edge case? What happens when the API returns garbage?"
5. **Dry-run** — Launch without live effects for 5+ minutes. Verify logic and behavior.
6. **Minimum scope deploy** — Start with smallest possible scope. If no crashes after initial period, scale up.
7. **Monitor** — Any crash = wind-down (not force close), fix, back to step 1.

## Post-Change Checklist
After ANY live code change, before considering it done:
1. **Orphan check:** verify only expected processes running
2. **State sync:** check for any live state that doesn't match bot's internal state
3. **Process cleanup:** If killing processes, use SIGTERM first. If not dead in 3 seconds, SIGKILL (-9).
4. **Compile check:** verify no syntax errors before restart

## Post-Action Reflection
After code pushes, parameter changes, architectural decisions, or any decision that changes system behavior:
1. **What did I just do?** — one sentence
2. **What assumption could be wrong?** — what belief am I acting on unverified
3. **What would I see in 48hrs if wrong?** — concrete predicted failure state
4. **Log it** — append to `memory/reflections.jsonl` with timestamp

## Skill Auto-Creation
After complex sessions (5+ tool calls, multi-file edits, bug fixes):
- Consider: "Would a future session benefit from knowing HOW I did this?"
- If yes: create a vault note capturing the procedure, pitfalls, and verification steps
- NOT mandatory — skip for routine work.
