# QA Config-Consumer Verification Checklist

After adding ANY config dict, flag, field, or new module file — run all 13 checks:

1. **Grep for every place the old alias or key is used** — backward-compat aliases create illusion of coverage
2. **Verify each consumer reaches the NEW dict/field** — not just the alias that points to a subset
3. **For liveness checks: does this verify the consumer is RUNNING?** — not just registered in a config file
4. **For except branches: is the data appended after failure safe to include?** — bare except that appends = silent contamination
5. **For deque windows: is len()>=M intentional?** — M*tick_interval is the real window, not maxlen*tick_interval
6. **For any "if --flag" comment: grep argparse for that flag** — aspirational comments are silent bugs
7. **For new module files: grep for the primary side-effecting calls** — if missing, it's simulation-only regardless of --dry-run flag
8. **For time-windowed checks: verify window_duration / capture_interval >= required_sample_count** — if buffer can't fill, threshold never fires

9. **For any code that must execute as a side effect — state writes, initialization, config loading — verify it is reachable on ALL paths through the method** — three failure modes: (a) state written at wrong lifecycle stage (ghost state); (b) init code placed after early `return` (AttributeError on first use); (c) side-effect inside bare `except` (silent non-execution).

10. **For any new cooldown/gate/check added to one entry method: grep ALL other entry methods in the same file for the same gate** — partial gate coverage leaves asymmetric protection; missing the same gate in sibling methods is a canonical bug class.

11. **For any `continue` in a loop: list all statements after it in the loop body — verify each skip is intentional** — a `continue` added to suppress one action silently skips all subsequent statements in the iteration.

12. **For any config parameter scaled for a tick rate: verify ALL other tick-count-based params in the same file are scaled consistently** — changing one window (deque maxlen, threshold count, lookback) without scaling peer params creates silent disablement.

13. **For any method with an early `return`, `break`, or `raise`: list all statements below it — verify none are unconditional initialization that must always run** — early control flow trapping init code = AttributeError on first access.

## Self-Growth Protocol
This checklist is a LIVING document. New items are added through the metacognitive compile pipeline:
- Metacognizer identifies 3+ chains with the same bug class → drafts candidate item
- Routes through adversarial review for validation
- Team lead appends to this file

## Why 13 items?
Each item was added because a real bug slipped through a previous version of this checklist. The checklist grew from 8 items (catching repeating bug classes from 2 sessions) to 13. Items 9-11 added from orchestrator review sessions. Item #12 from a tick-rate migration. Item #13 from the first autopoietic production pipeline (metacog compile → QA draft → team lead approval).
