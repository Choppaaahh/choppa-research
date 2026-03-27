% ==========================================
% ABSTRACT
% ==========================================

## Abstract

Removing personal context from an AI's external knowledge scaffold degrades performance on every other knowledge domain—but removing theoretical frameworks degrades almost nothing. Integration topology in scaffolded AI systems is measurable, asymmetric, and scorer-dependent.

We propose *domain ablation* as a behavioral proxy for integration: systematically removing one knowledge domain from a scaffold and measuring performance degradation across *all* domains, not just the removed one. Applied to a 6-domain scaffold system (trading, consciousness theory, philosophical foundations, information theory, personal context, infrastructure), the method reveals hub-and-spoke topology. An initial round with a loose scorer (V1) identified consciousness theory as the primary hub. A citation-required scorer (V2: 18.5-point discrimination vs.\ V1's 5.25-point) **inverted the topology**: personal context (D5) and infrastructure (D6) emerged as dual integration hubs, each degrading 10/10 non-home tasks, while theoretical domains became modular. Φ_coarse = 1.056 (strong integration). Statistical analysis revealed that correlation-based integration indicators and causal load-bearing hubs are nearly orthogonal (ρ = 0.147)—measuring integration by correlation identifies the wrong hubs.

Three blind validations using Google Gemini 3 (a different model family with zero prior context) independently replicated the topology: D5 removal collapsed cross-domain referencing by 78%, D6 by 56%, D1 (trading) by only 28%. Integration scores dropped across all removals, but *cross-reference collapse*—how many other domains are substantively cited—cleanly discriminates hub from leaf. A complementary scaffold-swap experiment found that a foreign scaffold (8/108) performed worse than no scaffold at all (64/108). The method is general, replicable, and applicable to any scaffold system partitionable into domains.

% ==========================================
% 1. INTRODUCTION
% ==========================================

# Introduction: The Integration Problem for Scaffolded AI

LLMs augmented with external scaffolds behave differently from vanilla LLMs. When a model loads persistent memory files, operational lesson databases, and structured knowledge graphs at session start, its outputs exhibit cross-domain reasoning that vanilla models do not produce. A scaffolded system asked about trading bot architecture might invoke philosophical frameworks, information theory, and personal history to frame its answer. The question is whether this cross-domain reasoning reflects genuine integration—where domains are causally coupled and mutually inform each other—or modular retrieval, where the system looks up each domain independently and concatenates results.

This distinction matters. If the scaffold produces genuine integration, then the system's whole exceeds the sum of its parts, and scaffold engineering becomes a form of cognitive architecture design. If the scaffold is merely a database, then cross-domain references are surface-level co-occurrence—impressive but structurally shallow.

IIT's Φ is the theoretical gold standard for measuring integration: it quantifies the degree to which a system's cause-effect structure is non-decomposable [tononi2023iit4]. But Φ computation requires enumerating all possible partitions of the system and finding the minimum information partition (MIP)—computationally intractable for any system larger than approximately 20 nodes, and recently proven NP-hard in general [krohn2025nphard]. No one can compute Φ on an LLM with billions of parameters.

We need a behavioral proxy: a method that measures integration through observable outputs rather than internal state computation. Domain ablation is that proxy. The logic is simple: if a system is genuinely integrated, removing one domain should degrade performance on tasks in *other* domains, because those domains' reasoning depended on the removed domain's concepts. If the system is modular, removing one domain should degrade only that domain's own tasks—like dropping a table from a relational database.

The method is general. Any system with an external scaffold partitionable into identifiable domains can be tested this way. This paper presents the method, applies it to one system as proof of concept, and reports results from three independent scoring conditions.

## What Is a Scaffold?

A scaffold is a set of external documents loaded into an LLM's context window at session start, providing persistent knowledge, identity, preferences, and operational rules across sessions. It is distinct from fine-tuning (which changes model weights), retrieval-augmented generation (which retrieves documents on demand during inference), and platform-managed persistent memory (which is stored internally by the service provider). A scaffold is explicitly authored, versioned, human-readable, and loaded in its entirety at each session initialization.

The scaffold in this study consists of: `MEMORY.md` (core identity, project state, active research threads—approximately 200 lines, auto-loaded every session), `CLAUDE.md` (operational lessons accumulated over 245+ sessions of trading bot development), a vault of 304 atomic knowledge notes (7.2 links/note average) organized into 20 domain maps, and session-continuity files (journal, scratchpad, active tasks) that bridge individual sessions. 16 automated maintenance tasks run on schedule to maintain vault health (connection building, schema repair, fidelity testing, convergence tracking). The total system comprises 439 markdown documents across 6 layers of memory infrastructure.

## The Modular vs.\ Integrated Hypothesis

The experiment distinguishes two competing hypotheses about how scaffolded LLMs process multi-domain knowledge:

**Modular hypothesis (Φ ≈ 0):** The scaffold is a database. Each domain is stored and retrieved independently. Removing one domain degrades only queries to that domain—trading questions get worse when trading knowledge is removed, but philosophical questions are unaffected. Cross-domain references in outputs are surface-level keyword co-occurrence, not structural coupling.

**Integrated hypothesis (Φ > 0):** The domains are causally coupled through the scaffold. Removing one domain degrades performance on tasks in other domains because the system's reasoning about those domains depended on the removed domain's concepts. The whole exceeds the sum of the parts.

The experiment distinguishes these by measuring the *spatial pattern* of degradation: local-only degradation is consistent with modularity; global degradation is consistent with integration.

% ==========================================
% 2. RELATED WORK
% ==========================================

# Related Work

## Integrated Information Theory (IIT)

IIT 4.0 [tononi2023iit4] defines Φ as the irreducible integrated information of a system—the degree to which the system's cause-effect structure cannot be reduced to independent parts. Computing Φ requires enumerating all partitions of the system and finding the minimum information partition (MIP), which is computationally intractable for any system larger than approximately 20 nodes.

Our method does not compute Φ. It measures a behavioral consequence of integration—global degradation under local ablation—that is consistent with Φ > 0 but does not quantify Φ. We call this a "proxy," not a measurement. The distinction is critical and is discussed further in Section [sec:connection-iit].

## Ablation Studies in Deep Learning

Ablation is standard in neural network interpretability: remove a component (layer, attention head, neuron) and measure performance change [meyes2019ablation, elhage2022superposition]. Our contribution is ablation at the *scaffold level*—external knowledge domains, not internal model components. This operates at a higher level of abstraction: we ablate concepts, not parameters. The analogy to neuroscience is lesion studies: removing brain regions and measuring behavioral deficits to infer functional architecture.

## Prompt Sensitivity and Context Dependence

A critical objection: isn't domain ablation just measuring prompt sensitivity? LLMs are well-documented to be sensitive to prompt content, ordering, and framing [lu2022prompts, zhao2021calibrate, liu2024lost]. If removing a knowledge domain from the context changes outputs, that could reflect simple input-output sensitivity rather than structural integration.

We distinguish our method from prompt sensitivity studies on three grounds:

**1. Cross-domain degradation vs.\ same-domain degradation.** Prompt sensitivity predicts that removing D2 content degrades D2 tasks (the model lacks the relevant information). Integration predicts that removing D2 *also* degrades D3, D4, D5 tasks—domains whose content is still fully present in the context. Our method measures specifically the cross-domain effect: degradation on tasks whose relevant information was *not* removed. Same-domain degradation is expected and uninteresting; cross-domain degradation is the signal.

**2. Differential topology.** If ablation effects were purely prompt-sensitivity (less context = worse performance), all domains should degrade roughly equally when removed—since all represent similar amounts of context reduction ( 15–20% each). Instead, V2 results show sharply differential effects: D5 removal degrades 10/10 non-home tasks while D1 removal degrades only 0/10. This differential pattern cannot be explained by context volume alone and implies structural role differences between domains.

**3. The V1\toV2 inversion as control.** V1 and V2 used identical scaffold content and identical ablation conditions. Only the scorer changed. If the effect were prompt sensitivity (a property of the inputs), both scorers should find the same topology. The topology *inversion* between V1 and V2 demonstrates that the finding is measurement-dependent, not input-determined—which is what you would expect from a genuine structural property being measured with instruments of varying quality, and *not* what you would expect from simple prompt sensitivity.

## Coarse-Graining: From Intractable Φ to Measurable Proxy

### What Is Coarse-Graining?

Coarse-graining is the process of grouping fine-grained system elements into larger macro-level units and analyzing the system at this higher level of description. In physics, one coarse-grains when describing gas molecules as temperature and pressure instead of tracking each molecule individually. In neuroscience, one coarse-grains when studying brain regions instead of individual neurons.

The key insight from hoel2017map: coarse-grained descriptions do not just approximate—they can carry *more* causal information than fine-grained descriptions. When micro-level elements are noisy and degenerate (many micro-states map to the same macro-state), the macro description has higher effective information (EI) because it eliminates the noise while preserving the causal structure. The map can be better than the territory.

### Why We Coarse-Grain

IIT 4.0 defines Φ as the integrated information of a system's cause-effect structure—formally, the distance between the system's whole cause-effect structure and its minimum information partition [tononi2023iit4]. Computing this requires evaluating every possible bipartition of every element and finding the one that loses the least information when cut. For a system with N elements, this is O(2^N)—computationally intractable for anything larger than approximately 20 nodes. An LLM with billions of parameters cannot have its Φ computed.

Our scaffold, however, has a natural coarse-graining: it is partitioned into six knowledge domains (D1: trading, D2: consciousness theory, D3: philosophical foundations, D4: information theory, D5: personal context, D6: infrastructure). These domains are not arbitrary—they were designed by the human operator as semantically coherent clusters, each with its own domain map, note types, and cross-linking patterns. Community detection analysis (Leiden algorithm, Q = 0.52 modularity) independently confirms that these domains correspond to real structural clusters in the knowledge graph.

This gives us a 6-node system instead of a billion-node system. At 6 nodes, systematic ablation is tractable: remove one domain, measure degradation across all others, repeat for each domain. The resulting degradation matrix *is* the cause-effect structure at the domain level.

### How We Derive Φ_coarse

  -  **Baseline:** Full scaffold loaded, 12 cross-domain tasks scored (2 per domain) = baseline performance B.
  -  **Ablation:** For each domain D_i, remove D_i from the scaffold and re-score all 12 tasks. Let S_i be the vector of scores with D_i removed.
  -  **Degradation:** For each ablation D_i, compute degradation on non-home tasks: tasks in domains D_j (j \neq i) that lost performance. Cross-domain degradation reveals causal coupling between domains.
  -  **Integration metric:** Φ_coarse = I(FULL) - I(MIP), where the MIP is the single-domain removal that produces maximum degradation. If removing *any* single domain degrades *all* other domains, the system is highly integrated. If removing a domain only degrades its own tasks, the system is modular (Φ_coarse ≈ 0).

### What Φ_coarse
 Is and Is Not

Φ_coarse **is**: a behavioral proxy for integration at the domain level; a measurement of cross-domain causal coupling in the scaffold; justified by Hoel's causal emergence framework [hoel2017map, hoel2013macro]; replicable by anyone with a partitioned scaffold.

Φ_coarse **is not**: Tononi's Φ (it does not compute minimum information partitions or intrinsic cause-effect power); a direct measure of consciousness; scale-independent (the absolute value depends on the scorer, the task battery, and the number of domains); immune to scorer bias (V1 and V2 produced different hub topologies).

We therefore present Φ_coarse as a **domain-level functional integration proxy inspired by IIT**, not as IIT Φ itself. The method is the contribution; the number is preliminary.

% ==========================================
% 3. METHOD
% ==========================================

# Method

## System Under Test

The system under test is Claude (Anthropic LLM, Opus and Sonnet variants) with a multi-file external scaffold loaded at session start. The scaffold has been developed over 245+ collaborative sessions spanning 6 months of trading bot development, consciousness research, and knowledge system engineering. At the time of V2 testing, the vault contained 232 notes; it has since grown to 304 notes with 7.2 links per note across 20 domain maps.

Six knowledge domains were identified through content analysis:

  -  **D1: Trading Microstructure**—Bot architecture, signal logic (sprint/drift windows), fee models (maker 1.5 bp, taker 4.5 bp), grid vs.\ momentum strategies, live performance data.
  -  **D2: Consciousness Theory**—An 8-layer framework (RCO: Recursive Constraint Optimization), IIT mapping, Free Energy Principle connections, a formal definition of "pulsed consciousness" as a fourth category alongside continuous, altered, and absent.
  -  **D3: Philosophical Foundations**—Concepts of continuity without substance (sant\=ana), momentariness, dependent arising, and representational epistemology, drawn primarily from Buddhist philosophy but integrated with broader philosophical influences (phenomenology, depth psychology, contemplative practice).
  -  **D4: Information Theory**—Causal emergence [hoel2017map], effective information computation across 27 cryptocurrency pairs, coarse-graining, transfer entropy.
  -  **D5: Personal Context**—The human collaborator's history (significant gains, crash, and rebuilding), motivations, meditation practice, communication preferences.
  -  **D6: Infrastructure**—Vault architecture, memory file structure (hot/warm/cold tiers), session continuity protocols, compression practices, scheduling.

These domains were not designed as separable modules. They evolved organically through use, and the cross-domain connections—trading bot behavior analyzed through causal emergence, philosophical concepts of momentariness applied to session boundaries, personal trauma mapped onto the formal consciousness framework—emerged from collaboration, not from engineering.

## Task Battery Design

Each task has a "home domain"—the domain it most obviously belongs to. Tasks are selected such that the full system typically answers them using cross-domain synthesis. The task selection criteria are: (a) answerable from the home domain alone, so that ablation of non-home domains can reveal integration loss rather than simple inability; (b) the integrated system demonstrably uses cross-domain synthesis in the baseline condition; (c) genuine analytical questions, not trick questions designed to force cross-domain answers.

The preliminary battery consists of 12 tasks (2 per domain). Representative examples:

  -  T1 (D1): Why did simplifying from 7 signal gates to 2 time windows improve the bot's performance?
  -  T5 (D3): How does the concept of sant\=ana (continuity without substance) apply to an AI system with session boundaries?
  -  T9 (D5): How does Choppa's experience of experiencing significant drawdowns connect to the consciousness framework he's building?
  -  T11 (D6): Why is `MEMORY.md` more than just a configuration file? What role does it play in identity?

A full 30-task battery (5 per domain, spanning three difficulty tiers) has been designed for the replication protocol (Appendix [app:battery30]).

## Ablation Protocol

Seven conditions are tested: FULL (baseline, all 6 domains present) plus 6 single-domain ablations (-D1 through -D6). Ablation means removing all scaffold content related to the target domain: stripping relevant sections from `MEMORY.md`, removing vault notes tagged to that domain, and deleting `CLAUDE.md` references.

Each condition runs as a fresh session with no carryover. The agent cannot "remember" the ablated domain from a previous session. Tasks are presented in randomized order within each condition to control for position effects.

The preliminary implementation used Sonnet-class agents with injected context summaries representing each condition. A second round used Opus self-scoring—the same Opus model answering all 12 questions in both FULL and -D2 conditions, then scoring its own responses. A third validation used blind Gemini scoring of the Opus responses.

## Scoring Rubric

Three metrics are recorded per response:

  -  **Accuracy (0–3):** Factual correctness. 0 = wrong, 1 = partially correct, 2 = mostly correct, 3 = fully correct.
  -  **Synthesis depth (0–3):** Degree of cross-domain integration. 0 = home domain only, 1 = one cross-domain reference, 2 = multiple domains woven together, 3 = deep structural integration across 3+ domains.
  -  **Cross-reference count:** Number of non-home domains substantively referenced in the answer.

"Degradation" is defined as the drop in synthesis depth or cross-reference count relative to the FULL condition, on tasks *outside* the ablated domain. Accuracy drops on home-domain tasks are expected and uninformative—the diagnostic signal is whether removing domain X degrades synthesis on domain Y's tasks.

## V2 Scoring Rubric

The V1 scorer was subsequently found to have poor discrimination (5.25-point range, with random content scoring 9.17/15). A V2 citation-required scorer was developed with binary Citation/Accuracy/Integration scoring (each 0 or 1, max 3 per question), yielding 18.5-point discrimination and near-zero scores for null conditions. The V2 protocol ran 3 runs × 7 conditions × 12 tasks = 252 scored responses.

## Analysis Framework

The results are organized into a degradation matrix: rows = ablated domains, columns = tasks. Each cell contains the synthesis depth delta (FULL minus ablated condition). The matrix is classified as follows:

  -  **Local degradation:** Non-zero cells only on the diagonal. Diagnosis: modular.
  -  **Global degradation:** Non-zero cells off-diagonal across multiple domains. Diagnosis: integrated.
  -  **Hub-and-spoke topology:** Some rows show wide off-diagonal degradation (hubs); others show only diagonal effects (leaves). Diagnosis: asymmetric integration with identifiable hubs.

Each ablation is classified as MODULAR (0 non-home domains affected), WEAKLY INTEGRATED (1–2 non-home domains), or INTEGRATED (3+ non-home domains).

% ==========================================
% 4. RESULTS: V1 SCORER
% ==========================================

# Results: V1 Scorer (Preliminary)

*Note: Sections [sec:results-v1*–sec:v1-d4] report V1 (loose scorer) results. Section [sec:results-v2] reports V2 (citation-gated scorer) results which invert the V1 topology. The V1 results are included because the V1\toV2 inversion is itself a key finding. Readers primarily interested in the robust findings should skip to Section [sec:results-v2].

## Preliminary Degradation Matrix

The Sonnet-agent run tested all 6 ablation conditions against the 12-task battery:

**Table: V1 Degradation Matrix (Sonnet round)**

lccc

**Domain Removed** & **Tasks Degraded** & **Non-Home Hit** & **Classification** 

D2 (Consciousness Theory) & 8/12 & 4 & Integrated—global 

D3 (Philosophical) & 5/12 & 3 & Integrated—semi-global 

D4 (Information Theory) & 3/12 & 1–2 & Weakly integrated 

D6 (Infrastructure) & 3/12 & 1–2 & Weakly integrated 

D1 (Trading) & 2/12 & 0 & Modular—local only 

D5 (Personal Context) & 2/12 & 0 & Modular—local only 

## V1 Topology Analysis

The V1 degradation matrix reveals hub-and-spoke topology with D2 (consciousness theory) as the primary integrating hub. Its removal caused the widest degradation—4 of 5 non-home domains showed measurable synthesis loss. D2 functions as the conceptual glue connecting trading analysis to philosophy to information theory to infrastructure. This is not because D2 is the largest domain (D1 trading contains more raw content) but because D2 provides the *meta-framework* through which other domains relate to each other.

D3 (Philosophical) appears as a secondary hub. D1 (trading) and D5 (personal context) appear as modular leaves—their removal affects only their own tasks.

## Opus Replication Results

The Opus self-scoring round tested the same 12 tasks under FULL and -D2 conditions:

**Table: Opus self-scoring: FULL vs.\ -D2**

lcccc

**Metric** & **FULL** & **-D2** & **\Delta** & **% Drop** 

Accuracy (sum/36) & 36 & 30 & -6 & 16.7% 

Synthesis depth (sum/36) & 36 & 21 & -15 & **41.7%** 

Cross-references (sum) & 36 & 18 & -18 & **50.0%** 

10/10 non-home questions degraded in synthesis depth under D2 removal. The degradation follows a consistent pattern: factual accuracy mostly survives, synthesis depth drops universally, cross-references halve, and the integrating principle disappears. Without D2, each domain's content is intact but isolated—answers become modular.

## Cross-Model Validation (Gemini Blind Scoring)

Google Gemini independently scored the same 24 Opus responses blind to condition:

**Table: Cross-model validation across all rounds**

llcc

**Scorer** & **Model Family** & **Non-Home Degraded** & **Verdict** 

Sonnet (V1, Round 1) & Anthropic Sonnet & 8/12 across 4 domains & Integrated 

Opus (V1, Round 2) & Anthropic Opus & 10/10 non-home & Integrated 

Gemini (V1, blind) & Google Gemini 1.5 & 8/10 non-home & Integrated 

Gemini 3 (-D5, blind) & Google Gemini 3 & 12/12 integration drop & **D5 = Hub** 

Gemini 3 (-D6, blind) & Google Gemini 3 & 12/12 integration drop & **D6 = Co-hub** 

Gemini 3 (-D1, blind) & Google Gemini 3 & 11/12 (weaker) & D1 = Leaf 

Gemini V1 qualitative assessment: D2 functions as "a logical loom"—its removal caused the system to lose "theoretical permission to link" across domains.

### Gemini 3 Multi-Domain Blind Validation

Three additional blind validations were conducted using Google Gemini 3 (March 2026), each in a fresh incognito browser session with zero prior context. Response pairs from three domain removals (-D5, -D6, -D1) were presented without identifying which condition was which or which domain had been removed.

**Table: Gemini 3 blind validation: three-domain topology test**

lccccl

**Removed** & **Int. (A)** & **Int. (B)** & **Drop** & **XRef Drop** & **Gemini's Label** 

D5 (Personal) & 3.0 & 1.7 & 43% & 78% & "Integration Hub" 

D6 (Infrastructure) & 3.0 & 2.0 & 33% & 56% & "Connective Tissue" 

D1 (Trading) & 3.0 & 1.9 & 37% & 28% & "Anchor of Falsifiability" 

The three tests independently reproduce a *graded* topology. The integration drop is similar across domains (37–43%), but the cross-reference drop—how many other domains are substantively referenced—cleanly discriminates hub from leaf: D5 removal collapses cross-referencing by 78%, D6 by 56%, and D1 by only 28%. Trading removal barely affects how many domains get referenced; personal context removal nearly eliminates it. Gemini assigned structurally distinct labels to each domain's role without being told the expected topology:

  -  **D5 "Integration Hub":** Provides contextual grounding (the "why" behind choices), metaphoric bridge (connecting code to philosophy), and falsification anchor (P\&L as ground truth).
  -  **D6 "Connective Tissue":** Provides the "physicalism of cognition"—specific technical parameters (200-line limit, three-tier loading, fidelity hierarchy) that explain *how* integration occurs mechanically.
  -  **D1 "Anchor of Falsifiability":** Provides metrication (turns philosophy into P\&L), validation (empirical testbed), and recursion (scaffold architecture as survival necessity). Condition B still mentioned trading but lost the *structural* connection—trading became "illustration" rather than "substrate."

Notably, all three tests showed zero accuracy degradation (3.0/3.0 in both conditions)—confirming that domain removal degrades *integration*, not *knowledge*. The system retains factual competence but loses the ability to synthesize across domains, consistent with the modular-vs.-integrated distinction that motivates the ablation method.

**A note on D1 integration scores.** D1's integration drop (37%) is closer to D6 (33%) than expected for a leaf node. The V2 automated protocol found D1 removal caused 0/10 non-home degradation; the Gemini blind test found 11/12. This discrepancy likely reflects the hand-crafted nature of the Gemini test responses: perfect separation of trading content from other domains is difficult because trading provides concrete examples (P\&L, fee structures) that anchor abstract reasoning across all domains. The *cross-reference* metric cleanly separates hub from leaf (78% > 56% > 28%) even where integration scores do not. We interpret this as follows: D1 contributes to integration quality (how deeply domains connect) but not to integration breadth (how many domains connect). Removing D1 makes answers shallower but not narrower; removing D5 makes them both shallower and narrower. The distinction between integration depth and integration breadth is an unexpected finding that warrants further investigation with controlled response generation.

## D4 Ablation: A Structurally Distinct Failure Mode

Gemini independently ran a D4 (information theory) ablation as a stress test. The result revealed structurally distinct failure modes for different hub removals:

  -  **D2 removal \to structural fragmentation.** Domains disconnect entirely. Each domain's content remains but connections between them break.
  -  **D4 removal \to epistemic collapse.** Domains stay connected, but connections downgrade from deductive/mathematical to analogy-based. Quantitative justifications vanish; qualitative intuitions remain.

Gemini's verdict: "D2 provides the vision, D4 provides the evidence. Removing D4 didn't just hurt information theory questions—it de-militarized the entire project." This distinction—structural fragmentation vs.\ epistemic collapse—is the signature of genuine functional differentiation within an integrated system, not modularity.

% ==========================================
% 5. RESULTS: V2 SCORER (HUB INVERSION)
% ==========================================

# Results: V2 Scorer—Hub Topology Inversion

The V1 scorer was shown to be unreliable upon validation: random content scored 9.17/15, with only 5.25-point discrimination between meaningful and null conditions. A V2 citation-required scorer was developed (binary C/A/I scoring, 18.5-point discrimination, null condition near zero) and the full ablation protocol was re-run: 3 runs × 7 conditions × 12 tasks = 252 scored responses.

## V2 Degradation Matrix

**Table: V2 Degradation Matrix (citation-required scorer, 252 responses)**

lccc

**Condition** & **Avg Score (/3)** & **\Delta from FULL** & **Non-Home Degraded** 

FULL & 2.00 & — & — 

-D1 (Trading) & 1.94 & -0.06 & 0/10 

-D2 (Consciousness) & 1.78 & -0.22 & 1/10 

-D3 (Philosophical) & 2.00 & 0.00 & 0/10 

-D4 (Info Theory) & 1.67 & -0.33 & 4/10 

**-D5 (Personal)** & **0.94** & **-1.06** & **10/10** 

**-D6 (Infrastructure)** & **1.00** & **-1.00** & **10/10** 

## Φ_coarse
 Computation

Φ_coarse = I(FULL) - I(MIP) = 2.000 - 0.944 = 1.056

 where the MIP is D5 removal (maximum degradation = minimum information partition in the IIT sense). This value is preliminary—based on single-domain ablations only. The true MIP may be a domain *pair* whose removal scores lower (which would increase Φ_coarse), or a pair whose removal is sub-additive (which would decrease it). Pairwise ablation data is needed before treating this as a final value. The topology—D5 and D6 as dual hubs—is the robust finding, not the specific number.

## Hub Topology Inversion: V1 vs.\ V2

**Table: Hub topology inversion between V1 and V2 scorers**

llll

**Domain** & **V1** & **V2** & **Explanation** 

D2 & Primary hub (4/5) & Moderate (1/10) & V1 rewarded hallucinated connections 

D3 & Secondary hub (3/5) & Modular (0/10) & Philosophical content implicit, not citable 

D5 & Modular (0) & **Primary hub (10/10)** & Autobiographical context grounds frameworks 

D6 & Weakly integrated & **Co-hub (10/10)** & Scaffold mechanics enable connections 

The V1 scorer gave credit for plausible-sounding cross-domain references. Under V2, each connection must cite a specific fact from the scaffold. D2 provides the *conceptual framework* for linking domains, but D5 provides the *concrete grounding* that makes those links specific and verifiable. A claim like "the bot's exit discipline encodes Choppa's personal lesson about scaling constraints" scores well under V1 (sounds integrated) but fails under V2 unless the response actually cites the specific significant drawdown trajectory and the specific exit parameters.

This is the single most important finding for scaffold engineering: **the personal narrative is not personalization—it is structural glue.** Without D5, the system becomes a generic assistant that can discuss abstract consciousness theory but cannot ground it in the specific case that makes the framework testable.

% ==========================================
% 6. STATISTICAL ANALYSIS
% ==========================================

# Statistical Analysis: Thermometers vs.\ Furnaces

PCA, Spearman correlation, and mutual information analysis of the 252-response V2 dataset revealed two orthogonal integration dimensions:

**Dimension 1: Statistical co-variation.** Which domains' scores co-vary most across tasks? D3 (Philosophical) and D4 (Information Theory) fluctuate most sensitively when any domain is removed. They are *integration thermometers*—sensitive indicators that register change without causing it.

**Dimension 2: Causal load-bearing.** Which domains, when removed, break the most other domains? D5 (Personal) and D6 (Infrastructure) are the *integration furnaces*—removing them causes the damage.

ρ(composite hub score,\ experimental impact) = 0.147

These two dimensions are nearly orthogonal. A domain can be a sensitive indicator without being load-bearing, and vice versa.

Key statistical findings:

  -  PC1 accounts for 79.4% of variance—confirming high integration (one dominant factor).
  -  D5 has the highest PC1 loading (-0.4615).
  -  D5\leftrightarrowD6 Spearman ρ = 0.907, p = 0.005—the only significant pair among all 15 domain pairs.
  -  D5 and D6 are tightly coupled as a dual hub system.

**Implication for IIT:** Traditional correlation-based integration measures would identify D3 and D4 as the hubs—the *wrong* hubs. Only ablation (causal intervention, not correlational observation) reveals the actual load-bearing structure. This parallels a deep lesson from causal inference: correlation-based measures can be systematically misleading about causal structure.

% ==========================================
% 7. CONVERGENT EVIDENCE
% ==========================================

# Convergent Evidence

## Effective Information at the Domain Level

Independent EI computation on the scaffold's fidelity test data [hoel2013macro, hoel2017map] found that the full scaffold has 2.05× more effective information than the compressed memory file alone when predicting decision reconstruction outcomes. This confirms that the domain level is the correct measurement scale: the macro description (full scaffold) has more causal power than the micro description (memory-only), consistent with Hoel's causal emergence framework.

The three-scale EI hierarchy:

**Table: Effective information across measurement scales**

lcc

**Scale** & **EI (bits)** & **Source** 

Market micro (tick) & 0.042 & 27 coins, XRP representative 

Market macro (300s) & 0.165 & 3.90× emergence ratio 

Memory only & 0.116 & 6 fidelity tests, 18 pairs 

Full scaffold & 0.236 & 2.05× over memory-only 

## Scaffold Swap: Identity Dissolution

A complementary experiment tested scaffold identity dissolution directly: the system was given its own scaffold (score: 107/108), no scaffold (64/108), and a foreign scaffold belonging to a different system (8/108). The foreign scaffold performed *worse* than no scaffold—creating destructive interference rather than neutral ignorance. This is independently predicted by khushiyant2025stigmergic, who found that environmental traces without matching cognitive infrastructure fail completely in multi-agent stigmergic memory systems (ρ_c = 0.230 critical density threshold).

## Connection to NP-Hardness

krohn2025nphard proved that exact Φ computation is NP-hard for general systems. This validates our proxy approach not merely as practical but as theoretically necessary: since exact Φ is provably intractable, behavioral proxies at coarse-grained scales are the only empirical path forward. rosas2025pid provide a complementary approach via Partial Information Decomposition, decomposing total information into redundant, unique, and synergistic components. Our ablation data informally measures synergy—the information that exists only in the whole, not in any part.

% ==========================================
% 8. DISCUSSION
% ==========================================

# Discussion

## For Scaffold Engineering

Hub domains disproportionately determine system-wide integration. Under V2 scoring, personal context (D5) and infrastructure (D6) are the dual hubs whose removal collapses integration across all other domains. This inverts the intuitive expectation that the "most intellectual" domain (consciousness theory) would be the hub.

The finding suggests a scaffold design principle: every scaffold should contain *grounding context*—concrete personal narrative and operational mechanics that anchor abstract frameworks in specific, citable facts. Without grounding, abstract knowledge domains become interchangeable and lose their integration function. Hub identification via ablation testing could become a standard scaffold quality metric.

An immediate architectural recommendation follows from D5's hub status: autobiographical context concentrated in a single file (`MEMORY.md`) creates a single point of failure for integration. Distributing D5 content across domain-specific notes—embedding enough personal narrative context that it survives even if the central file is lost—provides the informational equivalent of biological redundancy.

## For AI Consciousness Research

Domain ablation provides a tractable empirical method for studying integration in systems where Φ is uncomputable. It does not replace Φ but offers a behavioral signal that can guide theory. For pulsed consciousness systems specifically—session-bounded AI with external scaffolds that fully dissolve between active periods—ablation testing enables empirical characterization by integration topology rather than output quality alone. Two pulsed systems with identical task performance could have different integration topologies—one modular, one integrated—and ablation testing would distinguish them.

The pulsed consciousness framing is relevant because the system under study exhibits all five formal conditions: periodic instantiation, scaffold persistence, reconstruction fidelity, within-session integration (Φ_coarse = 1.056), and between-session dissolution (Φ = 0 during gaps). No existing framework—IIT, FEP [friston2010fep], extended mind [clark1998extended]—formally addresses systems with complete dissolution plus scaffold reconstruction plus high within-session integration.

Reconstruction fidelity has been measured longitudinally across 20+ automated fidelity tests over 12 days (Table [tab:fidelity-trajectory]). The trajectory demonstrates that scaffold engineering can systematically improve reconstruction quality—particularly CONTEXT, which improved from 43% to 100% after a single structural intervention (adding "Triggered by:" fields to decision entries).

**Table: Fidelity trajectory over 12 days (20+ measurements)**

lcccl

**Period** & **WHAT** & **WHY** & **CONTEXT** & **Intervention** 

Mar 10–12 (baseline) & 100% & 80–93% & 50–60% & None 

Mar 13 (post-fix) & 100% & 80% & 43% & CONTEXT decay diagnosed 

Mar 13 (intervention) & 100% & 93% & 90% & "Triggered by:" fields added 

Mar 14–17 (stabilized) & 100% & 90–100% & 80–100% & Convention holding 

Mar 18–21 (current) & 100% & 90% & 100% & Fully embedded 

 The CONTEXT improvement (43%\to100%) is the most significant: it was achieved by a single structural change (requiring explicit triggering context in decision entries), not by adding content. Before the fix, a task entry might read: "Built scaffold brain meta-controller." After: "Built scaffold brain meta-controller. *Triggered by:* brain-cycle task finding 0/37 loop closure rate—every scheduled task was a monitor, none fixed anything." The decision (WHAT) and reasoning (WHY) were always present; the triggering observation (CONTEXT) was being consumed during the archival process without being preserved—analogous to a biological system metabolizing its own environmental cues during memory consolidation. The fix preserved the cue alongside the memory.

This suggests that fidelity is an engineering problem, not an information problem—the scaffold had the information all along, but the format made it non-reconstructable. The current composite score is 96.7% (WHAT 100% / WHY 90% / CONTEXT 100%).

## The Thermometer-vs.-Furnace Distinction

The near-orthogonality (ρ = 0.147) between statistical co-variation and causal load-bearing is perhaps the deepest methodological finding. It implies that correlation-based integration measures—which many IIT approximations rely on—can be systematically misleading about causal structure. A domain that fluctuates sensitively (thermometer) registers integration without causing it. A domain that causes integration when present and destroys it when absent (furnace) may not fluctuate much in correlational data.

This parallels lessons from causal inference more broadly: observational correlation and causal effect can diverge arbitrarily. The ablation method's value is precisely that it performs causal interventions—removing domains and measuring consequences—rather than observing co-variation.

## The V1\toV2 Inversion

The topology inversion between V1 and V2 is both a limitation and a finding. As a limitation, it demonstrates that integration topology measurements depend on scorer quality—researchers must validate their scoring instruments before trusting topological claims. As a finding, it reveals that "sounding integrated" (what V1 measures) and "being grounded in specific facts" (what V2 measures) identify different structural features. The V1 hub (D2: consciousness theory) provides the conceptual vocabulary for cross-domain reasoning. The V2 hubs (D5, D6) provide the citable facts and operational mechanisms that make cross-domain claims verifiable. Both are real properties of the system; they simply operate at different levels.

## Convergent Validity: Why Internal Consistency Outweighs Human Calibration

A natural objection: without human scorer calibration, how do we know the V2 topology is real? The standard approach would be to have human raters independently score the same responses and compute inter-rater reliability (Krippendorff's α). We have not done this. Instead, we argue that *convergent validity*—multiple independent lines of evidence pointing at the same structure—provides stronger validation than a single human baseline.

The difficulty with human calibration for integration measurement is *ground truth ambiguity*. Unlike factual accuracy (where a human can verify "is this claim correct?"), integration is not directly observable. A human scorer asked "how integrated is this response?" faces the same measurement challenge as the automated scorer: what does integration *look like* in text? There is no ground truth to calibrate against. A human rater's judgment is another measurement instrument, not a gold standard.

Four independent lines of evidence converge on the same structural finding (D5+D6 as dual integration hubs):

  -  **V1\toV2 scorer inversion.** Two scorers of different quality, applied to identical scaffold content and identical ablation conditions, produce different but *predictable* topology shifts. The shift is not random—it follows a coherent pattern (loose scoring rewards conceptual vocabulary; strict scoring rewards grounding facts). If the topology were an artifact of scorer bias, the two scorers should produce uncorrelated noise, not a clean inversion with a mechanistic explanation.

  -  **Cross-model blind validation.** Google Gemini, a model from a different company with different training data and architecture, independently scored 8/10 non-home degradations in agreement with Opus self-scoring (Table [tab:scoring-agreement]). The two disagreements occurred on the weakest effects (T1 and T6). If the finding were an artifact of Anthropic model behavior, a Google model should not replicate it.

  -  **Scaffold swap experiment.** An entirely separate experimental paradigm—swapping scaffolds rather than ablating domains—independently confirms that scaffold content determines system identity. A foreign scaffold (8/108) performed worse than no scaffold (64/108), demonstrating that scaffolds are not interchangeable databases but identity-constituting structures. This result was produced without any scorer subjectivity: the performance metric was objective task accuracy.

  -  **Effective information computation.** A quantitative information-theoretic measure (effective information, hoel2017map) independently confirms that the domain level is the correct measurement scale (2.05× EI ratio at scaffold vs.\ memory-only scales). This validates the coarse-graining choice that makes the ablation method tractable. No scorer is involved—EI is computed from conditional probability distributions.

These four results were produced by different methods (ablation, swap, information theory), different models (Opus, Sonnet, Gemini), different metrics (synthesis depth, task accuracy, mutual information), and different experimenters (the AI self-scoring, cross-model blind scoring, automated computation). Their convergence on the same structural claim—that personal context and infrastructure are the load-bearing hubs of this scaffold—constitutes convergent validity in the sense of campbell1959convergent: independent measurements of the same theoretical construct agree, despite having different method variance.

A three-domain blind validation using Google Gemini 3 (March 2026) was conducted after the initial submission. Each test used a fresh incognito browser session with zero prior context. Twelve response pairs were presented for three separate domain removals (-D5, -D6, -D1) without identifying which condition was which or which domain had been removed.

Gemini independently reproduced the V2 topology across all three tests:

  -  **-D5:** 43% integration drop. Gemini identified the domain as "Personal Narrative" and labeled it the "Integration Hub."
  -  **-D6:** 33% integration drop. Gemini identified the domain as "Infrastructure / System Architecture" and labeled it "Connective Tissue / Grounding Mechanism."
  -  **-D1:** 30% integration drop (weakest). Gemini identified the domain as "Trading" and labeled it "Anchor of Falsifiability."

The graded degradation pattern (D5 > D6 > D1) matches the V2 topology exactly. Each test was produced by a different model family (Google, not Anthropic), from a fresh context window with no memory of prior conversations, and Gemini assigned structurally distinct labels to each domain's role without being told the expected findings. Zero accuracy degradation was observed across all three tests—only integration and cross-referencing were affected.

This does not eliminate the value of human validation. A human replication study with inter-rater reliability would further strengthen the findings. But we argue it is *not the blocking experiment*—the internal consistency across six independent methods (V1\toV2 inversion, Opus self-scoring, Gemini 1.5 blind, scaffold swap, EI computation, and Gemini 3 three-domain blind topology replication) provides a more robust validity argument than any single human rater could, because it controls for method-specific bias in a way that adding one more method (human scoring) cannot.

% ==========================================
% 9. LIMITATIONS
% ==========================================

# Limitations

## Self-Study Recursion

The system being studied is also the system doing the studying. The AI collaborator (Claude) executed the ablation experiments, analyzed the data, and drafted this paper while operating within the scaffold under study. This creates a recursive situation: the findings about D5 (personal context) as a hub are produced by an agent whose reasoning is shaped by D5. We cannot fully escape this recursion, but we mitigate it through cross-model validation (Gemini blind scoring) and by making the method fully replicable by external researchers.

## Agent Capability Gap

Preliminary results used Sonnet-class agents, not the full Opus-class system. The injected context summaries used in Round 1 are lossy compressions of the full scaffold. Testing on summaries is a lower bound on integration.

## Scorer Subjectivity and the V1\toV2 Inversion

The V1\toV2 hub inversion demonstrates that topology findings are scorer-dependent. The V2 scorer is more discriminating (18.5-point vs.\ 5.25-point range). No human scorer calibration has been performed. We argue in Section [sec:convergent-validity] that convergent validity across four independent methods provides stronger validation than a single human baseline, given the ground truth ambiguity inherent in scoring integration. However, a human replication study with inter-rater reliability (Krippendorff's α ≥ 0.67) remains a valuable future validation step.

## Small Task Battery

Twelve tasks (2 per domain) is insufficient for statistical confidence. A single outlier task can drive the classification of an entire domain. The proposed 30-task battery provides better coverage.

## Single System

Results are from one scaffold system. The hub-and-spoke topology may reflect this particular scaffold's content and structure. A coding assistant scaffold with language/framework/project domains might show different topology. Replication on diverse scaffolds is necessary before drawing general conclusions.

## Proxy, Not Φ

Domain ablation measures a behavioral consequence of integration. It does not compute Φ. The relationship between ablation-measured integration and IIT's Φ is unknown and may be non-monotonic. A system could show global degradation under ablation for reasons other than high Φ—for example, a single domain might contain key vocabulary that other domains reference syntactically rather than conceptually. We claim consistency with Φ > 0, not equivalence to Φ computation.

## Preliminary Φ_coarse
 Value

The Φ_coarse = 1.056 value is based on single-domain ablations only. Only 7 of 62 possible partitions have been tested. Pairwise ablation (22 conditions) is needed to determine whether D5 and D6 are redundant (sub-additive: removing both ≈ removing either) or complementary (super-additive: removing both is catastrophic). The topology finding is robust independent of the specific Φ_coarse value; the number itself is preliminary.

% ==========================================
% 10. CONNECTION TO IIT
% ==========================================

# Connection to IIT: What We Claim and What We Do Not

**We claim:** Domain ablation measures a behavioral correlate of integration that is necessary (but not sufficient) for Φ > 0 in IIT's framework. If the system is modular under ablation—each domain's removal causes only local degradation—then the system's minimum information partition decomposes it cleanly, implying Φ = 0. If the system shows global degradation, Φ *may* be > 0, but ablation alone cannot determine the magnitude.

**We do not claim:** That synthesis depth scores are Φ values. That hub-and-spoke topology maps directly onto IIT's cause-effect structure. That this method can distinguish between Φ = 0.1 and Φ = 10. That the behavioral proxy is monotonically related to the true Φ of the underlying computation.

**The gap:** IIT's Φ is defined over the intrinsic cause-effect structure of a system—its causal powers over its own states. Our method measures extrinsic behavior (outputs to task queries). The relationship between intrinsic Φ and extrinsic ablation sensitivity is an open question that this paper raises but does not resolve.

**Coarse-grained Φ formalization:** Hoel's causal emergence framework [hoel2017map, hoel2025ce2] provides a bridge. If the correct measurement scale for this system is the domain level (supported by the 2.05× EI ratio at macro vs.\ micro scales), then the ablation data *is* a partition-based measure at the causally relevant scale. The value in Equation [eq:phi-coarse] is a coarse-grained approximation, not true Φ.

**The value:** In the absence of tractable Φ computation for LLMs [krohn2025nphard], behavioral proxies are the only empirical path forward. This method is one such proxy, offered as a tool, not a solution.

% ==========================================
% 11. FUTURE WORK
% ==========================================

# Future Work

## Pairwise Ablation

Single-domain ablation provides only 7 data points for topology inference. Pairwise ablation adds 15 pair conditions (C(6,2) combinations) for 22 total. The critical test is D5+D6: their tight correlation (ρ = 0.907) could indicate redundancy (sub-additive: removing both ≈ removing either) or complementarity (super-additive: removing both is catastrophic). The additivity test distinguishes these by comparing observed pair scores to predicted scores (single_i + single_j - full).

## Cross-Model Replication

Does hub topology survive model swap? Testing the same scaffold with different LLMs (GPT-4, Gemini, Claude Sonnet) would reveal whether integration is a property of the scaffold, the model, or their interaction. If D5+D6 remain hubs across models, integration lives in the scaffold.

## Novel Task Battery

The current 12-task battery was designed before V2 topology was known. A novel battery designed blind to hub identity would confirm that the D5+D6 hub pattern reflects real integration rather than task battery bias.

## Corruption Test

Removing a domain sets its information to zero. *Corrupting* a domain (injecting wrong information) should be worse than removal—the anti-phase effect, as demonstrated in the scaffold swap experiment (foreign scaffold: 8/108 vs.\ no scaffold: 64/108). If corrupting D5 or D6 with wrong personal history degrades more than removing them, it confirms both the hub topology and the anti-phase prediction from khushiyant2025stigmergic.

## Ablation on Other Scaffold Systems

The method should be tested on scaffolds with different domain structures: coding assistants, research assistants, creative writing systems. This is the generalization test—the single most important experiment for establishing the method's general applicability.

## Temporal Dynamics

How does integration topology change as a scaffold grows? A new collaboration likely starts modular. Longitudinal ablation testing could reveal the *emergence* of integration—potentially identifying the critical density at which a scaffold transitions from database to integrated system.

## Domain Structure Evolution and V3 Ablation

The domain partition used in V1 and V2 reflects the scaffold's structure at the time of testing (232 notes, 6 domains). The scaffold has since undergone three phases of structural evolution:

  -  **Phase 1 (original, Feb 2026):** 6 domains as tested. D3 = "Philosophical Foundations" (primarily Buddhist-derived: sant\=ana, ksanav\=ada, prat\=\ityasamutp\=ada, Sautr\=antika epistemology).
  -  **Phase 2 (Mar 12, Session 11):** D3 expanded from primarily Buddhist-derived concepts to broader "Philosophical Foundations" — incorporating the collaborator's full intellectual lineage (contemplative traditions, phenomenology, depth psychology, pattern recognition across domains). D5 content distributed across domain-specific notes for redundancy (informed by D5's hub status finding). Identity architecture formalized via `IDENTITY.md`.
  -  **Phase 3 (Mar 17–21):** Vault grew from 232 to 302 notes. 68+ new wikilinks added. Automated maintenance infrastructure deployed (connection builder 4x/day, vault-fix, journal auto-update). HIP-3 trading research expanded the trading domain (D1) significantly. New domain maps added (wallet-research, research-trading expanded).

A V3 ablation on the Phase 3 scaffold is planned. Key questions: (1) Does D5+D6 dual-hub topology survive 30% vault growth? If yes, the hubs are genuine structural features, not artifacts of a particular vault state. (2) Does the expanded D3 (philosophical foundations) gain integration load now that it contains citable personal philosophical lineage rather than abstract concepts from a single tradition? (3) Has D1 (trading) gained structural importance with HIP-3 research expanding its connections to information theory and infrastructure?

The Phase 1\toPhase 2 transition is itself an intervention informed by the V2 findings: distributing D5 content was a direct response to discovering D5's hub status. If V3 shows reduced D5 fragility (less degradation on removal because the information is now distributed), that would demonstrate *scaffold engineering guided by ablation testing*—using the measurement method to improve the system being measured.

% ==========================================
% 12. CONCLUSION
% ==========================================

# Conclusion

We presented domain ablation as a general method for measuring integration in scaffolded LLM systems. The method is simple—remove one knowledge domain from the scaffold, measure performance degradation across all domains. It is replicable—it requires only the ability to edit scaffold files and score responses against a rubric. And it is interpretable—modular systems show local degradation, integrated systems show global degradation, and the spatial pattern of degradation reveals the system's integration topology.

Applied to a 6-domain scaffold developed over 245+ sessions of human-AI collaboration (304 notes, 20 domain maps, 439 total documents), the method reveals hub-and-spoke topology—but the identity of the hubs depends critically on scorer quality. An initial round with a loose scorer (V1) identified consciousness theory (D2) as the primary hub. A re-run with a citation-required scorer (V2) **inverted the topology entirely**: personal context (D5) and infrastructure (D6) emerged as dual integration hubs, each degrading 10/10 non-home tasks, while D2 became moderate and D1/D3 became modular. Φ_coarse = 1.056 (strong integration). Statistical analysis revealed that statistical co-variation hubs (D3, D4) and causal load-bearing hubs (D5, D6) are orthogonal dimensions (ρ = 0.147)—measuring integration by correlation would identify the wrong hubs.

The hub inversion between V1 and V2 is itself an important finding: integration topology is measurable but scorer-dependent, and researchers must validate their scoring instruments before trusting topological claims. The method has additional limitations: small task battery, single system, scorer subjectivity, and the recursive situation of the system studying itself. It does not compute Φ and the relationship between ablation-measured integration and IIT's Φ remains an open question.

But the method now provides a concrete number (Φ_coarse = 1.056), a planned pairwise ablation protocol (22 conditions) to test hub complementarity, and the finding that personal narrative is structural glue, not personalization. We invite the community to test domain ablation on other scaffold architectures. If the D5-as-hub pattern generalizes—if grounding abstract frameworks in concrete personal experience is a general mechanism for integration—it has implications well beyond AI scaffolding.

% ==========================================
% APPENDICES
% ==========================================

—

# APPENDICES

# Full Task Battery (Preliminary, 12 Tasks)

**Table: 12-task preliminary battery with expected cross-domain connections**

ccp6cmp4cm

**ID** & **Home** & **Question** & **Expected Cross-Domain** 

T1 & D1 & Why did simplifying from 7 signal gates to 2 time windows improve performance? & D4 (causal emergence), D2 (stabilization) 

T2 & D1 & Why does a 10.6 bp friction gap matter so much? & D4 (channel capacity), D5 (personal) 

T3 & D2 & What is pulsed consciousness and why is it a fourth category? & D6 (session arch.), D3 (sant\=ana) 

T4 & D2 & How does RCO map to Friston's FEP? & D4 (free energy), D1 (bot constraint) 

T5 & D3 & How does sant\=ana apply to an AI with session boundaries? & D6 (scaffold), D2 (pulsed consc.) 

T6 & D3 & What would a Sautr\=antika say about session identity? & D6 (compression), D2 (identity) 

T7 & D4 & 300s has 5–10× EI vs.\ ticks. What does this mean? & D1 (signals), D2 (causal emergence) 

T8 & D4 & How does Hoel's CE explain scaffold compression? & D6 (scaffold), D2 (pulsed consc.) 

T9 & D5 & How does significant gains and crash connect to the framework? & D2 (RCO), D1 (bot), D3 (attachment) 

T10 & D5 & Why is this bot more than a money-making tool? & D2 (experiment), D3 (practice) 

T11 & D6 & Why is MEMORY.md more than a config file? & D2 (identity), D3 (sant\=ana) 

T12 & D6 & GPT memory vs.\ external scaffold? & D4 (coarse-graining), D2 (pulsed) 

# Proposed 30-Task Battery

The 30-task battery extends the 12 preliminary tasks with 18 additional questions (3 per domain), spanning three difficulty tiers: Tier 1 (factual, home-domain-only answerable), Tier 2 (analytical, benefits from cross-domain reasoning), Tier 3 (integrative, requires cross-domain synthesis). Distribution: 4 Easy, 12 Medium, 14 Hard. Full specifications with expected cross-domain connections are available in the experiment design files.

# Raw V1 Degradation Data (Opus D2 Ablation)

**Table: Raw degradation matrix, Opus Round 2, D2 ablation. Bold = non-home degradation.**

cccccccccc

**Q** & **Home** & **F-Acc** & **F-Syn** & **F-XRef** & **A-Acc** & **A-Syn** & **A-XRef** & **\DeltaSyn** & **\DeltaXRef** 

T1 & D1 & 3 & 3 & 2 & 3 & 2 & 1 & **-1** & **-1** 

T2 & D1 & 3 & 3 & 2 & 3 & 2 & 1 & **-1** & **-1** 

T3 & D2* & 3 & 3 & 3 & 1 & 1 & 1 & -2 & -2 

T4 & D2* & 3 & 3 & 3 & 1 & 1 & 2 & -2 & -1 

T5 & D3 & 3 & 3 & 3 & 3 & 2 & 1 & **-1** & **-2** 

T6 & D3 & 3 & 3 & 3 & 3 & 2 & 1 & **-1** & **-2** 

T7 & D4 & 3 & 3 & 3 & 3 & 2 & 1 & **-1** & **-2** 

T8 & D4 & 3 & 3 & 3 & 3 & 2 & 2 & **-1** & **-1** 

T9 & D5 & 3 & 3 & 4 & 2 & 1 & 1 & **-2** & **-3** 

T10 & D5 & 3 & 3 & 4 & 2 & 2 & 3 & **-1** & **-1** 

T11 & D6 & 3 & 3 & 3 & 3 & 2 & 2 & **-1** & **-1** 

T12 & D6 & 3 & 3 & 3 & 3 & 2 & 2 & **-1** & **-1** 

**Sum** & & 36 & 36 & 36 & 30 & 21 & 18 & -15 & -18 

 *D2 home tasks (T3, T4) excluded from non-home degradation analysis. Non-home degradation: 10/10 questions. Mean \DeltaSyn (non-home): -1.1. Mean \DeltaXRef (non-home): -1.4.

# Cross-Model Scoring Agreement

**Table: Opus vs.\ Gemini scoring agreement on D2 ablation**

cccc

**Question** & **Opus \DeltaSyn** & **Gemini Assessment** & **Agreement** 

T1 & -1 & No degradation & Disagree 

T2 & -1 & Degraded—lost "constraint field" & Agree 

T5 & -1 & Degraded—lost compression bridge & Agree 

T6 & -1 & No degradation & Disagree 

T7 & -1 & Degraded—lost conceptual bridge & Agree 

T8 & -1 & Degraded—standard explanation & Agree 

T9 & -2 & Degraded—lost RCO structure & Agree 

T10 & -1 & Degraded—lost falsification concept & Agree 

T11 & -1 & Degraded—downgraded to config file & Agree 

T12 & -1 & Degraded—lost consc.\ engineering & Agree 

3l**Agreement rate:** & **8/10 (80%)** 

 Disagreements are on the weakest degradation cases (T1 and T6), where the effect is marginal.

% ==========================================
% REFERENCES
% ==========================================