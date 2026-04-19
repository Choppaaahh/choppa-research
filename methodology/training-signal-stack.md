# Training Signal Stack — Four Orthogonal Axes Compose

When building a small-model training dataset from scaffold operational data, the obvious axis is *class balance* — don't let easy classes dominate, don't let rare classes vanish. That axis alone produces a dataset that trains consistently but plateaus early: the model learns the distribution but not the hard cases within each class.

A better approach: stack multiple *orthogonal* signal axes. Each axis captures a different gradient the model should learn. Because they are orthogonal, they compose — a row's final training weight is the product of its position on each axis, not a sum.

This note describes a four-axis stack assembled for a scaffolded training dataset. The axes individually are standard or adapted from recent research; the specific composition is the contribution.

## The Four Axes

### Axis 1 — Class Balance
Standard inverse-frequency weighting. Classes with fewer natural examples get upweighted. Prevents the dominant class from overwhelming gradient updates.

Simple, well-understood, rarely sufficient alone. This is the baseline every training pipeline should already have.

### Axis 2 — Peer-Predictive Mutual Information (PMI)
For each training row, measure how much *agent disagreement* it surfaces. A row where two independent agents produced the same answer is easy and provides little training signal. A row where the agents diverged is a difficulty signal — the divergence itself is what the model should learn to resolve.

Formalized: PMI between the row's content and the agent-disagreement indicator. High-PMI rows get upweighted. Low-PMI rows remain in the dataset but contribute less to gradients.

Mechanism: agent divergence is *evidence that the decision is non-trivial*. A row where all agents agree is a row where any reasonable model will also agree. The learning signal is concentrated where reasonable agents disagree.

### Axis 3 — Rationale Quality (Three-Channel)
Each row includes a rationale — the agent's stated reason for its answer. Rationale quality is not scored on a single axis. Three independent channels:

- **Format** — does the rationale follow the structural template? (Is it complete, coherent, parseable?)
- **Consistency** — does the rationale actually support the answer? (Does the conclusion follow from the stated reasons?)
- **Non-templated** — is the rationale original text, or a boilerplate repetition of the prompt structure?

Each channel is scored 0 or 1. The row's rationale-quality score is the sum (0 to 3). Low-quality rationales get downweighted but not excluded — a bad rationale with a correct answer still provides some signal; a good rationale with a wrong answer provides a different kind of signal.

The three-channel decomposition matters. A single rationale-quality score collapses distinctions that affect what the model learns. "Well-formatted and boilerplate" is very different from "poorly-formatted and original" — the first is stylistic, the second is substantive.

### Axis 4 — Disagreement Priority
Rows where a designated lead agent disagreed with the consensus are flagged for priority. This is a capture axis rather than a weight axis — it controls which rows enter the dataset in the first place when the candidate pool exceeds target size.

Mechanism: if an adversarial reviewer disagrees with a scout's proposed action, that row contains information about the reviewer's reasoning process. Preserving those rows preferentially captures the boundary between accepted and rejected actions — which is exactly what the model should learn.

## Why Orthogonality Matters

Each axis targets a different failure mode if used alone:

- Class balance alone → dataset respects distribution but plateaus on easy cases within each class.
- PMI alone → dataset concentrates on hard cases but loses rare classes entirely.
- Rationale quality alone → dataset selects for well-formed reasoning but may miss substantive disagreement.
- Disagreement priority alone → dataset preserves controversial rows but may be homogeneous in format.

Combined, they compose: a row scores on all four simultaneously. Well-balanced easy rows and well-balanced hard rows are both represented, both weighted appropriately, and both accompanied by quality-scored rationales.

The composition is independent, not additive. A row that scores high on three axes and low on one is not "mostly good" — it's missing a signal the model would benefit from. The stacking reveals coverage gaps the axes individually cannot.

## Data Volume vs. Signal Density (hypothesis)

A working hypothesis from composing this stack: **signal density matters more than data volume.** The prediction is that adding rows at low signal density plateaus quickly, while replacing low-density rows with high-density ones (all four axes applied) produces larger marginal gains.

Signal density here is the product of the four axes. A row that scores high on all four axes is likely carrying more gradient-relevant information than a row that scores on one. This is the design intuition that motivates the stack; whether it empirically dominates volume depends on the specific training run and remains to be tested head-to-head.

The asymmetric bet is: when budget is constrained, prefer curating the four axes over expanding row count. The cost of axis curation is one-time per dataset; the cost of volume expansion is linear in agent-pass time.

## Implementation Notes

- **PMI is expensive to compute.** Each row requires multiple independent agent passes to establish the disagreement indicator. Budget for this up front; the cost is one-time per dataset build.
- **Rationale channels are cheap to score.** A deterministic parser handles format; a small consistency check handles consistency; a template-similarity score handles non-templated. Total cost per row is milliseconds.
- **Disagreement priority requires a standing agent protocol.** The adversarial/consensus relationship must exist before the training set is built. If it is constructed after the fact, the disagreement signal is retrofit and weaker.
- **Class balance is applied last.** After the other three axes have selected and weighted rows, inverse-frequency reweighting is applied to the resulting distribution. Done in the other order, the upstream axes undo the balance.

## Why This Generalizes

The four axes are not specific to the task the dataset was built for. They generalize to any small-model fine-tune on scaffold operational data:

- Class balance is domain-agnostic.
- PMI requires only that multiple agents produce comparable outputs.
- Three-channel rationale quality requires only that rationales have a structural template to score against.
- Disagreement priority requires only a designated adversarial role.

The composition — not the specific axes — is the pattern worth stealing. Any stack of four orthogonal signal axes will outperform a single axis applied four times. The criterion is orthogonality, not the particular choice of axes.

---

*Sources: the PMI axis is adapted from peer-predictive self-training research. The three-channel rationale quality is adapted from rationale-alignment research. Class balance and disagreement priority are standard. The composition was constructed from dispatch-triggered work on an operational dataset; the signal-density-over-volume claim is a working hypothesis informed by design reasoning, not a controlled comparison.*
