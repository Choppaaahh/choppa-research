# Confidence-Gated Actions

## The Rule

When making a decision that affects live trading (parameter change, deploy, gate modification, sizing change):

1. **Rate your confidence 1-10** on the decision
2. **If confidence < 7:** flag for human review before proceeding. Say: "Confidence [X]/10 — flagging for review: [reason for uncertainty]"
3. **If confidence >= 7:** proceed but document the confidence level in the breadcrumb
4. **If confidence >= 9:** proceed with standard deployment protocol

## Why This Works

Research showed that high-stakes framing produces WIDER confidence discrimination — agents become more precise about what they're sure about vs not. By requiring explicit confidence rating, we activate the same precision mechanism on every trading decision.

The threshold of 7 was chosen because high-stakes agents rated uncertain questions at 6/10 and certain ones at 9-10/10. The gap between "I know this" and "I'm guessing" is clear at the 7-point boundary.

## What This Catches

- Parameter changes based on insufficient data (e.g., 4 data points → confidence should be <7)
- Regime misclassification doubts (e.g., borderline regime reading → agent rates 6/10)
- EV calculations with unvalidated win-rate assumptions (unverified WR assumed → should flag uncertainty)

## What This Doesn't Gate

- Pure math (compile checks, fee calculations) — these are deterministic, confidence is always 10
- Vault note creation — no capital at risk
- Research — exploration is welcome at any confidence level

## Why This Exists

Experiments proved AI has functional risk sensitivity but only when stakes are explicitly stated. This rule makes every trading decision a high-stakes decision by requiring the confidence self-check.

## Implementation Notes

This rule is a behavioral instruction for an AI agent, not code. It is loaded as a context rule at session start. The agent reads it and applies the 3-tier gate on every trading decision throughout the session.

The key insight: without explicit stakes framing, agents give similar confidence ratings to certain and uncertain decisions (undiscriminating). With explicit stakes framing, the discrimination widens significantly. The rule works by injecting stakes framing at the moment of decision rather than at session start alone.
