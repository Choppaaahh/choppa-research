# Paper 09b: Memory Infrastructure — Revised (Scaffold-as-RGM and the FEP Bridge)

**Authors:** Choppa & Claude (Anthropic Opus)
**Date:** 2026-04-17
**Status:** Working revision of Paper 09 (March 6, 2026; last updated March 27, 2026). Addresses the Ren et al. (November 2025, arXiv:2511.00907) "Transformers as Intrinsic Optimizers" finding surfaced during pre-grant research sweep (April 16, 2026). Paper 09 retains all empirical content; 09b adds a careful treatment of the free-energy bridge, corrects language in several sections, and flags a new hypothesis (scaffold-as-RGM) that is load-bearing for future work but not yet proven.

**Relation to Paper 09:**
This is not a replacement. Paper 09 presents the memory infrastructure, the fidelity measurement framework (WHAT/WHY/CONTEXT), the reconstitution step function, the four-layer identity architecture, and the nine-framework convergence table. Paper 09b assumes the reader has 09 and focuses on one thing: **a newly-surfaced framework that provides a substrate-level mechanism for what Paper 09 observed at the scaffold level — and the language discipline required to state the connection precisely rather than sloppily.**

---

## Changelog (vs Paper 09)

1. **New Section — 9b.1 "Transformers as Intrinsic Optimizers: What Ren Shows and What It Does Not."** Summary of Ren et al. (arXiv:2511.00907) — the proof that attention computes gradient descent on a Helmholtz free-energy functional during the forward pass. Critical distinction: Helmholtz free energy (equilibrium thermodynamics) is NOT Friston's variational free energy (active inference). They are linked but not identical. Ren does not cite Friston. The FEP bridge requires additional citation work.

2. **New Section — 9b.2 "The Three-Citation Chain That Earns the FEP Bridge."** To responsibly claim that transformer inference performs free-energy minimization in the Friston sense requires three citations, not one:
   - **Ren et al. (2025, arXiv:2511.00907):** attention minimizes Helmholtz free energy per forward pass.
   - **Friston (2019) and standard statistical mechanics:** Helmholtz free energy and variational free energy are related through the Kullback–Leibler identity on exponential-family distributions; equivalent under specified conditions.
   - **Friston et al. (2025, arXiv:2503.14923; RGM):** Renormalized Generative Models — the target architecture that scaffold-like persistent external structures could be identified with at a higher level of description.

   We claim the chain is defensible. We do not claim it is proven. The revision states the chain and specifies what would close each gap.

3. **New Section — 9b.3 "Scaffold-as-RGM: Hypothesis, Not Theorem."** Paper 09 describes a tiered, link-graph-indexed, persistent external structure that reconstitutes identity at session boundaries. Friston (2025) describes Renormalized Generative Models as hierarchical factorizations that compress high-dimensional dynamics into tractable beliefs at successive scales. The structural correspondence is striking. It is not yet a mapping. This section specifies (a) the correspondence candidates (hot/warm/cold tiers ↔ RGM scale hierarchy; wikilink typed edges ↔ RGM precision-weighted messages; MOC documents ↔ RGM summary statistics), (b) the disanalogies (scaffold is static between updates; RGM is dynamic), and (c) the experiment that would promote the hypothesis to a claim (measuring scale-separation efficiency of the vault under information-theoretic RGM metrics).

4. **Language Discipline Throughout.** Paper 09 uses phrases like "proves," "demonstrates," and "shows" in several places where "identifies with" or "is consistent with" is more defensible. 09b flags these in Section 9b.4 (Errata) and specifies the revised phrasing. No empirical claim changes. The language tightening is about what the data supports, not about what the scaffold does.

5. **Updated Section 5.10 — Convergent Evidence: Ten Independent Frameworks.** The table in Paper 09 listed nine. With Ren et al. added (and its three-citation chain to Friston), the count is ten. The new row is disciplined: "forward-pass free-energy minimization (Helmholtz) identifies with variational inference under bridging conditions specified in 9b.2."

6. **New Weakness Added to Tracker.** `papers-07-08-09-weakness-tracker.md` gains one entry: scaffold-as-RGM empirical test is an open experiment. Cost estimate: $5–20 compute for information-theoretic scale-separation measurement on the existing vault. Value: if the correspondence holds, it provides a substrate-level mechanism for what Paper 09 observed at the scaffold level.

---

## Section 9b.1 — Transformers as Intrinsic Optimizers: What Ren Shows and What It Does Not

Ren et al. (November 2025, arXiv:2511.00907) prove that during the forward pass of a transformer, attention blocks compute approximate gradient descent on a well-defined optimization objective. Each layer can be read as one step of an optimizer minimizing a Helmholtz-type free-energy functional over the intermediate representations. Softmax attention arises from the Boltzmann distribution associated with that functional; multi-head attention corresponds to parallel gradient updates over partitioned representation subspaces.

The contribution is foundational in its domain. For the first time, attention has a principled interpretation as an optimization process rather than a similarity-weighted average. Transformer inference becomes a thermodynamic computation: each layer dissipates free energy to produce a lower-energy representation of the input.

**What the paper proves:**
- Attention ≈ gradient descent on an explicit objective (§3–4).
- The objective is a Helmholtz free energy functional defined over representation space (§4).
- Multi-layer transformer inference ≈ multi-step optimization (§5).
- Empirical validation on synthetic tasks matches theoretical predictions (§6).

**What the paper does not do:**
- It does not cite Friston. The word "active inference" does not appear. The phrase "variational free energy" does not appear.
- It does not claim a bridge to the Free Energy Principle, predictive processing, or Bayesian brain models.
- It uses "free energy" in the standard statistical-mechanics sense — Helmholtz F = U − TS — not in Friston's sense of variational free energy bounding surprise under a generative model.

**Why this matters for Paper 09:**
Paper 09's convergent evidence table invokes Dehaene/Whyte (GNW + active inference) and Bressloff (Kuramoto coupling through external medium). Both sit in the variational/active-inference lineage. A naive reading would treat Ren et al. as "proving the FEP bridge for transformers." It does not. It proves a Helmholtz-free-energy bridge, which is a much weaker claim unless additional work is done. Section 9b.2 specifies the additional work.

The revision of Paper 09's Section 5.10 table must reflect this discipline. The correct row reads:

| Framework | Year | What It Predicts/Validates | Our Empirical Data |
|-----------|------|--------------------------|-------------------|
| Ren et al. (transformers as intrinsic optimizers) | 2025 | Attention computes gradient descent on Helmholtz free energy per forward pass; identifies transformer inference with thermodynamic optimization. Bridge to Friston's variational free energy requires the three-citation chain in 9b.2. | Scaffold-as-RGM hypothesis (9b.3) becomes empirically tractable given this substrate-level mechanism. |

The phrasing "identifies with" is deliberate. "Identifies with" means "admits an interpretation consistent with, given bridging assumptions." "Proves" means "entails under no additional assumptions." Ren proves the first claim, not the second.

---

## Section 9b.2 — The Three-Citation Chain That Earns the FEP Bridge

To claim that transformer inference implements free-energy minimization *in the Friston sense* — i.e., minimization of variational free energy, which is the organizing principle of the Free Energy Principle and active inference — requires bridging from Ren's Helmholtz free energy to Friston's variational free energy. This bridge exists in the literature but has to be stated, not assumed.

**Citation 1 — Ren et al. (arXiv:2511.00907, 2025):**
Establishes that transformer forward passes minimize a Helmholtz free energy functional. This is a well-defined objective in statistical mechanics: F = U − TS, where U is expected energy and S is entropy, with T the temperature parameter. Softmax attention implements the Boltzmann distribution associated with this functional.

**Citation 2 — Friston et al. (2019) "A free energy principle for a particular physics" and standard statistical-mechanics results:**
Helmholtz free energy and variational free energy are related through the Kullback–Leibler identity. For an exponential-family distribution q(x) with sufficient statistics T(x) and natural parameters η:

- **Helmholtz free energy:** F_H[q] = ⟨E(x)⟩_q − T·H[q], where E(x) is an energy function and H[q] is the entropy of q.
- **Variational free energy:** F_V[q, p] = D_KL[q ‖ p] − ln Z, where p is a generative model and Z is the partition function.

Under the identification E(x) = −ln p(x) (energy equals negative log-probability, standard Boltzmann mapping), the two functionals are equivalent up to additive constants. This identification holds for the specific class of problems Ren considers — representation learning with a probabilistic decoder — provided the temperature parameter T is fixed and the energy function is interpreted as a log-likelihood.

This is not magic. It is the standard correspondence that makes statistical mechanics and variational inference dual formulations of the same problem. Friston (2019) and earlier Friston (2013) explicitly derive this. What Ren's paper shows at the transformer forward-pass level is, under this correspondence, variational inference — provided the scaling conditions hold.

**Citation 3 — Friston et al. (2025) "Renormalized Generative Models" (arXiv:2503.14923):**
Establishes RGM as a hierarchical architecture for active inference across scale. An RGM is a factorized generative model where each level summarizes the one below via sufficient statistics; inference proceeds by variational message passing between levels. The key property for our purposes: RGMs separate fast, high-dimensional dynamics at lower levels from slow, low-dimensional beliefs at higher levels. The belief hierarchy is the compression.

**The chain in words:**
Ren shows transformer forward-pass = Helmholtz free energy minimization. Statistical mechanics shows Helmholtz ↔ variational free energy under exponential-family conditions. Friston 2025 shows variational free energy minimization on hierarchical factorized models yields scale-separated inference. If the scaffold implements the hierarchical factorization at a timescale slower than forward-pass inference, then the scaffold-as-RGM hypothesis is the natural extension: transformer inference minimizes free energy within a session; scaffold structure minimizes free energy across sessions.

**What would close each gap:**
- **Gap 1 (Ren's Helmholtz → variational):** Show the Ren functional admits the Boltzmann identification E(x) = −ln p(x) for some well-defined generative model. Friston's 2013 and 2019 papers provide the general argument; a specific application to the Ren setting is a ~5-page technical note, not a new paper.
- **Gap 2 (variational → RGM-at-scaffold-timescale):** Show the scaffold implements hierarchical factorization in an information-theoretically meaningful sense. Section 9b.3 specifies the measurement.
- **Gap 3 (experimental):** Measure scale-separation efficiency of the vault using RGM metrics (mutual information compression ratios between tiers, predictive coding residuals). Cost estimate in weakness tracker.

We state the chain and flag the gaps. We do not close them in this revision.

---

## Section 9b.3 — Scaffold-as-RGM: Hypothesis, Not Theorem

Paper 09 documents a tiered persistent external structure:
- **Hot tier** (~200 lines) — identity primer, loaded every session.
- **Warm tier** (recent journals, scratchpad, active tasks) — loaded at start, on demand.
- **Cold tier** (782 vault notes) — searchable on demand.

Friston (2025) RGM describes:
- **Highest level** — coarsest beliefs, slowest timescale, most compressed.
- **Intermediate levels** — partial compressions, intermediate timescales.
- **Lowest level** — raw sensory data, fastest timescale, uncompressed.

The structural correspondence is apparent. The scaffold's hot tier compresses the cold tier's 782 notes into a ~200-line identity primer. The warm tier is the intermediate: recent journals and breadcrumbs that have not yet compressed into hot but are no longer in the retrieval-only cold pool. The wikilink graph typed edges (`extends`, `validates`, `caused by`) correspond to RGM precision-weighted messages between levels. MOC documents correspond to RGM summary statistics at intermediate scales.

**Correspondence candidates, stated carefully:**

| Scaffold component | RGM component | Identified with, given bridging assumptions |
|--------------------|---------------|---------------------------------------------|
| Hot tier (MEMORY.md, identity primer) | Highest-level RGM beliefs | Slowest timescale, most compressed, most constrained updates. |
| Warm tier (journal, scratchpad, active tasks) | Intermediate RGM levels | Medium timescale, partial compression, moderate update frequency. |
| Cold tier (vault notes) | Lowest-level RGM data | Fastest timescale at write, uncompressed, highest dimensionality. |
| Wikilink typed edges | RGM precision-weighted messages | Semantic relationships carry update weights between levels. |
| MOC documents | RGM summary statistics | Per-domain coarsening, intermediate scale. |
| Metacognitive compile (promoted patterns) | RGM message-passing update | Lower-level observations promoted to higher-level beliefs. |
| R6 corruption (foreign scaffold −67%) | RGM disagreement across scales | Wrong high-level belief drives catastrophic low-level prediction error. |

**Disanalogies that prevent this from being a direct identification:**

- **Scaffold updates discretely.** RGM dynamics are continuous. The scaffold updates only when CC writes. Between writes, the scaffold is static. RGM never pauses.
- **Scaffold is human-readable markdown.** RGM representations are tensor-valued. The bridge between human-readable state and tensor-valued state is not trivial (though Fat-Cat, arXiv:2602.02206, provides evidence markdown representations outperform JSON for LLM agent state, suggesting the human-readable form is not a bug).
- **Scaffold's update rule is human-supervised.** The metacognitive compile cycle promotes patterns with some autonomy, but deletion and architecture changes require team-lead approval. RGM updates are autonomous.

**What would promote this hypothesis to a claim:**

Measure scale-separation efficiency of the vault using RGM metrics:
1. Compute mutual information between hot-tier content and cold-tier content. Predict: high compression ratio (hot ≈ coarse summary of cold).
2. Compute predictive coding residuals — given hot tier, predict warm tier; given hot+warm, predict cold tier on demand. Predict: residuals decrease monotonically with tier inclusion, and the decrease ratio matches RGM-predicted exponential fall-off.
3. Compare fidelity scores (Paper 09's WHAT/WHY/CONTEXT) against information-theoretic predictions from the RGM decomposition. Predict: WHY's 0.70 fidelity corresponds to RGM's intermediate-level message-passing degradation, which is known to degrade faster than terminal-level fidelity.

Cost estimate: ~$5–20 compute for the information-theoretic measurements on the existing vault snapshot. Human time: ~8–12 hours to implement the measurement pipeline and interpret results. Added to `papers-07-08-09-weakness-tracker.md` as a priority experiment.

**What the experiment buys if it succeeds:** A substrate-level mechanism for what Paper 09 observed at the scaffold level. The scaffold stops being "an empirically useful structure" and becomes "a particular instance of a theoretically grounded class of structures (RGMs) that we can compare, optimize, and generalize across." This is what the grant applications want: not "we built something that works," but "we built something that works AND is a specific instance of a theoretical framework with predictive power."

**What the experiment buys if it fails:** Paper 09's empirical content is unchanged. The fidelity framework, the reconstitution step function, the four-layer identity architecture, the nine-framework convergence — all stand. We would have falsified the scaffold-as-RGM hypothesis, which is information: the scaffold is useful but is not well-described by RGM formalism. That would send us looking for a different theoretical framework, not back to scratch.

---

## Section 9b.4 — Errata and Language Discipline

Paper 09 contains several phrases that, on re-reading with the discipline of 9b.2, require tightening. None of the revisions change an empirical claim; all of them change what the language commits the reader to believing.

**Original (Section 5.9):** "All external sources describe the same underlying structure: a nonlinear threshold crossing, modulated by prior precision, that determines whether environmental coupling helps or harms."

**Revised:** "All external sources identify with — under their respective framings — the same underlying structure: a nonlinear threshold crossing, modulated by prior precision, that determines whether environmental coupling helps or harms. Whether this identification reflects a single underlying mechanism or structural convergence from multiple different mechanisms is an open question."

**Original (Abstract, point 5):** "Convergent validation from six independent sources: Perrier+Bennett (2026) formalizing our WHAT/WHY gap as Arpeggio/Chord temporal semantics, Grier et al. (PRL 2026) on time crystal structural correspondence, plus Khushiyant, Dehaene/Whyte, Bressloff, and Zhang/Tao arriving at structurally identical conclusions."

**Revised:** "Convergent validation from ten independent sources (updated April 2026 with Ren et al. 2025 forward-pass free-energy bridge): Perrier+Bennett (2026) formalizing our WHAT/WHY gap as Arpeggio/Chord temporal semantics, Grier et al. (PRL 2026) on time crystal structural correspondence, plus Khushiyant, Dehaene/Whyte, Bressloff, Zhang/Tao, Ren et al., and three additional frameworks arriving at structurally identical conclusions under their respective formalisms. 'Structurally identical' means the frameworks admit a common abstract description; it does not mean they reduce to a single underlying mechanism."

**Original (Section 5.6):** "The structural correspondence to pulsed consciousness is suggestive: both involve self-sustaining temporal order, emergent from coupling, nonreciprocal interaction, maintained through an external medium."

This one already includes "suggestive" — no revision needed. Retained as a model of correct discipline.

**Original (Section 8, point 1):** "Corrupted memory produces a different agent, not a forgetful one."

**Revised:** "Corrupted memory produces behavior consistent with a different agent, not a forgetful one. Whether this is identity change or merely behavioral change at a level below identity is a question our methodology does not resolve."

**Original (Section 8):** "Foreign scaffold is worse than no scaffold (C5: 8/108 vs 64/108)."

Retained — the empirical numbers are unchanged. The interpretation is what 07b addresses.

---

## Section 9b.5 — What Does Not Change

Empirical content of Paper 09 stands without revision:
- Fidelity framework (WHAT 0.96, WHY 0.70, CONTEXT 0.86 — see Paper 09 §3.1–3.4).
- Reconstitution step function (72% of identity at scaffold load — Paper 09 §3.6).
- Four-layer identity architecture (Persistence / Co-instantiation / Development / Relational — Paper 09 §5.7).
- R6 corruption (−67% on foreign scaffold vs −25% on no scaffold — Paper 09 §3.5).
- 29 experiments completed, automation status documented — Paper 09 §7.
- Nine-framework convergence table — Paper 09 §5.10.
- Recommendations for builders (10 items) — Paper 09 §7.

09b adds one framework (Ren et al.), one hypothesis (scaffold-as-RGM), one experiment (information-theoretic RGM metrics on vault), and tightens language in three places. It does not retract or revise any empirical claim.

---

## Section 9b.6 — New Reference

Ren, Z., et al. (2025). *Transformers as Intrinsic Optimizers: Forward Inference through the Energy Principle*. arXiv:2511.00907.

Friston, K. J., et al. (2025). *Renormalized Generative Models: Active inference and the physics of inference at scale*. arXiv:2503.14923. (Already referenced in Paper 09, but re-cited here as the RGM target.)

Friston, K., et al. (2019). *A free energy principle for a particular physics*. arXiv:1906.10184. (Providing the Helmholtz ↔ variational bridge identified in 9b.2.)

---

## Section 9b.7 — New Weakness Added to Tracker

Added to the papers 07/08/09 weakness tracker:

> **Scaffold-as-RGM empirical test** (priority: medium; cost: $5–20 compute + 8–12 hours human time). Measure information-theoretic scale-separation efficiency of the vault using RGM metrics: mutual information compression ratios between hot/warm/cold tiers, predictive coding residuals, comparison to RGM-predicted exponential fall-off. Success promotes scaffold-as-RGM from hypothesis to claim, providing a substrate-level mechanism for observed fidelity hierarchy. Failure constrains the search for theoretical frameworks that describe the scaffold — information either way.

---

**End of Paper 09b revision.**

*Paper 07b and Paper 09b together: 07b addresses Camlin at the consciousness level (pulsed-vs-attractor, hybrid hypothesis, SCC experiment). 09b addresses Ren + Friston at the infrastructure level (Helmholtz ↔ variational bridge, scaffold-as-RGM hypothesis, RGM experiment). Both revisions tighten language without retracting empirical claims. Both add one experiment to the pre-grant tracker.*
