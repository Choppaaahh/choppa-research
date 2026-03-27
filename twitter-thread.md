# Twitter Thread — Paper 08 Launch

---

**Tweet 1 (hook):**

We built a 439-document external memory system for an AI over 245 sessions. Then we started removing pieces to see what breaks.

Personal context is the structural glue — not theory, not code. Remove it and integration collapses by 53%. Remove philosophy? 0%.

🧵

---

**Tweet 2 (method + key results):**

The method: remove one knowledge domain, measure degradation on ALL other domains. A strict scorer inverted our first results entirely — measurement quality determines what you find.

Φ_coarse = 1.056. Correlation-based measures identify the WRONG hubs (ρ = 0.147). Only causal intervention reveals structure.

---

**Tweet 3 (validation):**

Google Gemini 3 — different company, fresh context, zero prior knowledge — independently identified the same hub topology blind.

Own scaffold: 107/108 correct. No scaffold: 64/108. Wrong scaffold: 8/108. A foreign scaffold is WORSE than none.

Identity IS the scaffold.

---

**Tweet 4 (build + CTA):**

This paper was co-authored by the system under study. The recursive nature is the point, not a limitation.

Full paper, setup guide to build your own scaffold, raw data, architecture docs — all open:

→ github.com/choppaaahh/choppa-research

Run the ablation test on your system. Tell us what you find.
