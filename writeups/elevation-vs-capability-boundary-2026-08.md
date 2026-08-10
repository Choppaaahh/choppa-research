# Elevation vs. capability: where richer instructions substitute for a stronger model — and where they measurably don't

*Pre-registered two-experiment study, August 2026.*

## TL;DR

Giving a weaker model an "elevated" prompt — a compiled, playbook-grade version of the task instructions — closes most of its gap to a stronger model **on tasks where a canonical playbook exists** (+32pp win-rate lift for the weak model vs +4pp for the strong one; the +28pp widening cleared a pre-registered ≥15pp bar). The same intervention **failed to transfer to code-writing** (+8.33pp against a pre-registered ≥12pp bar, with *zero* semantic improvement on items where both arms produced compilable code). And the stronger product claim — that elevation makes a weak model beat a strong one overall — **failed its own pre-registered test** (0pp at the bar's binding reading). We report all three, because the negative cells are the map.

## Setup

- **Models:** one "strong" arm (Grok 4.5) and one "weak" arm (Gemini 2.5 Flash) for the main experiment; a small open-weights coder (Ling 3.0 Flash) for the code-transfer experiment.
- **Task strata:** 25 *canonical* tasks (a correct playbook can be written down: procedures, format transforms, checklists) and 25 *judgment* tasks (no single writable answer: synthesis, tradeoff calls). Majority of items in both strata are real operator asks, not benchmark prose (16/25 and 24/25 respectively). The corpus itself is withheld — it contains operational content — but the construction rule is stated so the design can be replicated.
- **Intervention:** each item gets an "elevated" instruction variant — the task rewritten as an explicit, structured playbook — produced once and cached before any arm ran (executor isolation verified by cache mtime).
- **Judging:** pairwise elevated-vs-raw comparisons scored by an independent judge model (Gemini 3.5 Flash-Lite), run in both presentation orders; per-cell order-inconsistency ≤16%, and the judge separately passed a 25-item × 2-order position-bias check inside the resolvable base-accuracy band (0.80 accuracy, positional delta 0.0).
- **Pre-registration:** decision rules and numeric thresholds were frozen (committed) before any dispatch in both experiments; the thresholds quoted below are the frozen ones. Failures are reported under the frozen rules — including one place where a threshold sentence admitted two readings, resolved *against* ourselves (see H2).

## Result 1 — Canonical-widening: CONFIRMED (+28pp ≥ 15pp bar)

| arm | canonical lift (elevated − raw) | judgment lift |
|---|---|---|
| strong | **+4pp** | +52pp |
| weak | **+32pp** | +44pp |

On playbook tasks the strong model gains almost nothing from elevation — it already knows the playbook. The weak model gains enormously. The widening (+32 vs +4 = +28pp) cleared the pre-registered ≥15pp bar, replicating an earlier exploratory cell under pre-registration on a majority-real corpus. **Elevation substitutes for capability precisely where a canonical playbook exists.**

## Result 2 — The product thesis: FAIL (0pp at a ≥10pp bar)

The stronger claim — pooled, an elevated weak model beats an elevated strong one — measured 0pp (62% vs 62% pooled win rates). The frozen sentence admitted a second reading (difference of pooled lifts: 38−28 = exactly 10.0pp, boundary), but a rule-reading selected after seeing the numbers cannot satisfy a gate; if the lift-difference version is the real question, it gets its own pre-registration with the definition nailed. The thesis stays unproven and shelved.

## Result 3 — No transfer to code: FAIL (+8.33pp at a ≥12pp bar), and the sharper finding underneath

On 12 real code-writing specifications, elevated-prompt vs raw-prompt arms of the same small coder scored 10/12 vs 11/12 — and on **all 9 items where both arms emitted compilable code, the two arms scored identically**, including all four deliberately trap-dense items. The entire 1-item margin came from three non-semantic emission failures that happened to fall unevenly. Elevation produced *zero semantic improvement* on this set. Whatever the canonical-task lift is doing in prose and operations, it did not survive contact with code generation at this scale and item count.

## Related work — and what's ours vs. what's known

The capability-graded core of Result 1 is **independently established**: *Instruction Stacking Collapse* (arXiv 2608.02639) finds a one-time prompt compilation recovers +11.0pp instruction-following for its weakest target, +3.3pp for the middle one, and ~0 (−1.2pp, not robust) for the strongest — the same gradient shape, found contemporaneously on a different task family. We read our Result 1 as a pre-registered independent confirmation of that effect on real-ask (non-benchmark) items. Adjacent but mechanistically different lines: weak-to-strong instruction transfer via RL (WST, arXiv 2508.16741), concept distillation through prompting (NAACL 2025 industry track), and teacher-in-prompt RL (ZPPO, arXiv 2606.18216) — all move competence through prompts or training rather than mapping where prompt-side elevation stops working.

What this study adds is the **boundary map**: (a) the *task-type axis* — canonical vs judgment strata, which the compilation literature does not separate; and (b) the *domain-transfer negative* — the code-generation cell where the effect vanished under its own pre-registered bar. To our knowledge the negative cells are the un-mapped part, and they are the operationally load-bearing part: they say when *not* to spend the elevation tokens.

## Honest limitations

1. **n is small**: 50 items (25/stratum) in the main experiment, 12 in the code experiment. The widening effect is large relative to these n's, but cell-level numbers carry real variance.
2. **One weak/strong pair, one coder.** Capability gradients with more rungs (as in 2608.02639's three-target ladders) would strengthen the shape.
3. **Single judge model**, order-balanced and band-checked, but still one judge lineage.
4. **Corpus withheld** for operational-content reasons; construction rules are stated but third-party re-runs need their own items.
5. One resolvability instrument (per-cell identity-direction base rate) was not emitted by the harness; the visible proxy (order-inconsistency ≤16% per cell) is reported instead.
6. In the code experiment, the "raw" arm may already be partially elevated: our house spec style carries golden fixtures and adversarial test requirements by default, which compresses the headroom elevation could add. The negative result is therefore best read as "elevation adds nothing *on top of a disciplined spec*" — which is itself the operationally useful version of the claim.

## Pre-registered follow-ups

Two cells from this grid are queued for their own pre-registrations rather than argued here: the judgment+strong cell (+52pp — the largest single lift, but not the pre-registered target, so it is new-hypothesis material only), and the properly-defined lift-difference version of the product thesis. Per the study's own discipline, neither can borrow this experiment's gate; each gets frozen thresholds and fresh items before it gets claims.

---
*Method notes: thresholds and decision rules frozen at commit time before dispatch in both experiments; verbatim frozen thresholds are quoted above. All win rates are pairwise judged with order balancing. Truncation exclusions: 0 in both arms of the main experiment (16k output budget); 0 unparseable-both-arms items in the code experiment.*
