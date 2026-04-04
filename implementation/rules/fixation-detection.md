# Fixation Detection — Co-Regulation Check (from Ralph Wiggum)

Self-monitoring can't catch design fixation. A dedicated check must flag when the agent is stuck.

## Triggers (check proactively)

1. **Gate stagnation:** Any deploy gate, block, or hold that's been active 5+ days without re-evaluation. Check: is the condition that created the gate still true? Has new data changed the math?

2. **Repeated rejection:** User pushes past the agent's recommendation 2+ times on the same topic. Agent said no, user said yes, outcome was positive. Flag: "User overrode agent — was agent fixated?"

3. **Over-caution pattern:** Agent recommends "wait for more data" or "park for later" 3+ times in one session on actionable items. Flag: "Possible over-caution — is waiting justified or habitual?"

4. **Stale thesis:** A research direction or architectural decision that hasn't been stress-tested in 7+ days. Flag: "This assumption is load-bearing but hasn't been challenged recently."

## What to Do When Flagged

Don't auto-fix. Route to an adversarial reviewer:
- "Reviewer, this gate has been active for X days. The original condition was Y. Current state is Z. Should the gate hold?"
- "Reviewer, agent recommended against X three times. User overrode twice with positive outcome. Is agent fixated?"

The point is DETECTION, not auto-correction. Same principle as a grind detector — detection-only first.

## Why This Exists

Ralph Wiggum (arXiv 2603.24768) proved empirically: co-regulation catches fixation that self-regulation misses. A long-running block was never flagged by self-monitoring — an external nudge was needed to surface it. An adversarial reviewer can provide that nudge when the primary agent can't see past its own prior commitment.
