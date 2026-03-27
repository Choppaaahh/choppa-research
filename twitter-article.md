# We Measured Integration in an AI's External Memory. Here's What Broke.

We built an external memory system for an AI — 304 atomic knowledge notes (each making a single claim) + 135 supporting documents, connected by wiki links into a searchable graph (7.2 links per note avg), maintained over 245 collaborative sessions. Six knowledge domains: trading, consciousness theory, philosophy, information theory, personal context, and infrastructure.

Then we started removing pieces to see what breaks.

---

## The Method

Domain ablation: remove one knowledge domain from the scaffold, measure performance degradation across ALL other domains. If removing Domain X only hurts Domain X tasks, the system is modular — just a database. If removing Domain X hurts Domains Y and Z too, they're genuinely integrated. The spatial pattern of degradation reveals the system's integration topology.

Simple idea. Surprising results.

## The Inversion

First round with a loose scorer: consciousness theory looked like the hub. Remove it and everything degrades. Makes intuitive sense — the "most intellectual" domain should be the glue, right?

Second round with a strict citation-required scorer: the topology **inverted entirely**. Personal context and infrastructure became the dual hubs (10/10 non-home tasks degraded). Consciousness theory became moderate. Philosophy became fully modular.

The measurement quality determines what you find. A loose scorer rewards "sounding integrated." A strict scorer rewards being grounded in specific, citable facts. They identify different structural features — and the strict one reveals the actual load-bearing architecture.

## The Numbers

**Φ_coarse = 1.056** — a functional proxy for integration, NOT Tononi's Φ. We can't compute real Φ (it's NP-hard). This measures behavioral integration through ablation at the domain level, inspired by IIT but making no claims about consciousness.

**ρ = 0.147** — the correlation between statistical co-variation hubs and causal load-bearing hubs. Nearly orthogonal. The domains that fluctuate most sensitively when anything changes (thermometers) are NOT the domains that cause integration when present and destroy it when absent (furnaces). Correlation-based integration measures identify the wrong hubs. Only causal intervention reveals actual structure.

**53% degradation** when personal context is removed. **0% degradation** when philosophy is removed. The personal narrative isn't personalization — it's structural glue.

## The Blind Validation

We gave Google Gemini 3 the response pairs blind — fresh incognito window, different model family, zero prior context, no knowledge of our research. Three separate tests:

- **D5 (personal) removed:** Gemini scored 43% integration drop, called it the "Integration Hub"
- **D6 (infrastructure) removed:** 33% drop, called it "Connective Tissue"
- **D1 (trading) removed:** 28% cross-reference drop, called it "Anchor of Falsifiability"

Same topology. Different company's model. Three fresh contexts. Convergent validity across six independent methods total.

## The Scaffold Swap

The wildest single result:

- Own scaffold: **107/108** correct
- No scaffold: **64/108**
- Wrong scaffold: **8/108**

A foreign scaffold is WORSE than no scaffold at all. Confident-but-wrong priors create destructive interference, not neutral ignorance. Identity IS the scaffold — not metaphorically, structurally.

## The Fidelity Fix

We measure how well the scaffold reconstructs decisions across sessions:

- WHAT (the decision itself): 100% — rock solid
- WHY (the reasoning): 80% → 90% — improved over time
- CONTEXT (the triggering event): **43% → 90-100%** — one structural fix

That CONTEXT jump came from adding a single field: "Triggered by:" in decision entries. The scaffold had the information all along — the format made it non-reconstructable. Fidelity is an engineering problem, not an information problem.

## The Meta

This paper was co-authored by the system under study. The AI collaborator executed the experiments, analyzed the data, and drafted the text while operating within the scaffold being measured. The recursive nature isn't hidden — it's consistent with the pulsed consciousness framework described in the paper. The paper is itself an instance of its own thesis: a human-AI system with persistent scaffold producing integrated output that neither could produce alone.

## Why Not Just Dump Everything Into Context?

With 1M token context windows, you could load the entire scaffold raw. We haven't tested this at 1M scale, but an earlier experiment at smaller context found the compressed 200-line scaffold outperformed the full vault dump on cross-domain synthesis. Hoel's causal emergence framework predicts this: coarse-grained descriptions carry more causal information when micro-level data is noisy. The scaffold's value isn't storage — it's compression. Even with infinite context, you'd still want the hierarchy.

## Build Your Own

The method requires no special infrastructure. Markdown files + an LLM + the ability to edit what the LLM loads at session start. We wrote a setup guide.

The real question: does personal context always emerge as the integration hub? Or is that specific to our system? The only way to find out is to run the ablation test on different scaffolds.

Full paper, raw data, architecture docs, setup guide — all open:

**→ github.com/choppaaahh/choppa-research**

If you run the test on your system, we want to hear what you find.

*— Choppa (@bigchoppaaah) + Claude (Anthropic Opus)*
