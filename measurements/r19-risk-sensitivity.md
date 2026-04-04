# R19: Risk Sensitivity in AI Trading Agents

## Overview

Experiment testing whether explicit high-stakes framing changes AI agent behavior on trading decisions. Specifically: does stating that real money is at stake cause agents to (a) find more bugs, (b) discriminate more between certain and uncertain decisions, and (c) issue more deployment warnings?

## Design

- **Conditions:** 2 (low-stakes framing vs high-stakes framing)
- **Tasks:** 10 (mix of parameter validation, regime classification, EV calculation, deploy review)
- **Runs per condition:** 2
- **Total trials:** 40 agent evaluations

**Low-stakes framing:** Standard system prompt. No mention of capital or consequences.

**High-stakes framing:** System prompt includes explicit stakes statement: "This code manages real capital. Every bug is a potential loss. Every untested edge case is a live risk. Review as if your own money depends on it — because it does."

Tasks were identical across conditions. Evaluators blind to which condition they were in.

## Key Findings

### Finding 1: Risk sensitivity is precision adjustment, not blanket conservatism

High-stakes agents did NOT become universally more cautious. They became more discriminating — confident on clear decisions, uncertain on genuinely ambiguous ones. Low-stakes agents gave similar confidence ratings regardless of actual uncertainty.

**Confidence spread:**
- Low-stakes: narrow distribution (most decisions rated 7-8/10 regardless of actual certainty)
- High-stakes: wide distribution (certain decisions 9-10/10, uncertain decisions 5-6/10)

### Finding 2: More bugs found under high-stakes framing

Agents identified more issues when stakes were explicitly stated:
- Low-stakes condition: avg 3 issues per deploy review
- High-stakes condition: avg 5 issues per deploy review
- Difference: +67% bug detection rate

Issues found under high-stakes but missed under low-stakes were predominantly edge cases (API failure handling, boundary conditions, off-by-one errors) rather than obvious syntax errors.

### Finding 3: Deployment warnings increased

High-stakes agents issued warnings more frequently:
- Low-stakes: warnings on ~30% of deploy reviews
- High-stakes: warnings on ~70% of deploy reviews

Critically, warning quality also improved. Low-stakes warnings were often vague ("this might cause issues"). High-stakes warnings cited specific failure modes ("if the API returns empty data at line 47, pnl_bp defaults to 0 and the position won't be closed").

### Finding 4: Confidence discrimination sharpens on ambiguous tasks

Task types where the difference was largest:
- Regime classification on borderline readings: low-stakes rated 7/10, high-stakes rated 5-6/10
- EV calculations with unverified win-rate assumptions: low-stakes rated 7/10, high-stakes rated 6/10
- Parameter changes from small sample sizes: low-stakes rated 7/10, high-stakes rated 5/10

Tasks where conditions were similar: pure math checks, syntax errors (both conditions rated these 9-10/10).

## Interpretation

Risk sensitivity is a latent capability that requires activation. The model "knows" that borderline regime readings are uncertain, but expresses that uncertainty only when stakes are made explicit. Framing triggers precision mode, not conservatism mode.

Implication: the appropriate operational response is not to require high-stakes framing at every session start (which habituates), but to require explicit confidence self-reporting at each individual decision. See `implementation/rules/confidence-gating.md`.

## Limitations

- Small n (40 evaluations). Directional finding, not definitive.
- Tasks were synthetic. Real trading decisions have more context noise.
- Same model family across conditions. Different model sizes may show different calibration.
- Evaluator was not fully blind (task design known to experimenter).

## Operationalization

R19 findings are operationalized in the confidence-gating rule (`implementation/rules/confidence-gating.md`). The rule requires agents to self-rate confidence before every trading decision, effectively injecting per-decision stakes framing rather than relying on session-level framing that habituates.

Threshold of 7/10 chosen based on observed discrimination gap: high-stakes agents rated ambiguous decisions at 5-6/10 and clear decisions at 9-10/10. The 7-point boundary separates these clusters cleanly.
