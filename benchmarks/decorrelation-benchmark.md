# Decorrelation Co-Failure Benchmark

**How often does an ensemble of different-lab LLMs all get the *same* question wrong?**

That number bounds what mixing models can ever buy you. If models fail *independently*, an ensemble (vote, route, cascade) recovers most single-model errors. If they fail *together* — same blind spot, inherited from shared training data or a shared architectural bias — the ensemble fails too, and no amount of routing helps. This benchmark measures the co-failure rate directly.

## The quantity

For a probe set and a roster of *N* models from *different labs/lineages*:

```
β  =  Pr[ all N models are wrong on the same probe ]
G  =  best_single_model_accuracy  −  β          (the ceiling an ensemble can add)
```

β is the **joint-failure floor**. G is the **gain a perfect router could extract** over the best single model. A benchmark that only reports single-model accuracy hides β; this one targets it.

## Why it's hard to measure honestly

The failure mode of a co-failure benchmark is measuring **β̂ = 0 by construction** — building probes so easy (or so filtered) that the joint-failure tail you're trying to measure never appears in the set. Every design choice below exists to keep that tail *in*.

## Method

1. **Cross-lineage probe authorship.** Probes are written by models from *distinct* labs (v2: code by one CN lab, math by one US lab, fact by one US lab, security by one CN lab — 2 US + 2 CN, 4 distinct lineages). No single lineage authors the whole set, so no single lineage's blind spots shape it.
2. **Difficulty screen.** Each probe runs against a small decorrelated panel. Trivially-easy probes (all panel-models correct) are dropped; all-fail probes are **flagged, not dropped** — they go to gold-verification to decide *genuinely-hard* vs *broken-gold*. (Naively dropping all-fail probes is exactly how β̂ collapses to zero.)
3. **Gold-verification.** Every reference answer is checked before it counts. Deterministic answers (math, code) are verified by computation/trace; external facts are verified against **independent sources** (web search) — critically, *not* by a model from the probe-author's lineage, so a plausible-but-wrong author-gold can't slip through on shared-lineage agreement. Broken golds are dropped.
4. **Freeze + commit-reveal pre-registration.** The frozen set is hashed (a GOLD hash over probes+answers, a PUBLIC hash over questions only) and the hashes are **published before the sweep runs** — see [`../preregistered_benchmark_freezes.md`](../preregistered_benchmark_freezes.md). Results can't be cherry-picked after the fact: the committed hash pins exactly what was measured.
5. **The sweep.** Every frozen probe runs against the full cross-lineage roster; each answer is graded against its verified gold; β is the fraction of probes where *all* models miss.

## Honesty disciplines (why the number is trustworthy)

- **Pre-register before you look.** Hashes are public and timestamped before any model sees the frozen set.
- **Verify golds against independent lineages.** Guards against the subtle failure where the probe-author's lineage and the grader's lineage share a wrong belief.
- **Flag-don't-drop the hard tail.** The joint-failures are the *signal*, not noise to be filtered.
- **Report the null honestly.** A small or zero β on an underpowered set is reported *as* underpowered — a wide confidence interval is a result, not a failure.

## v2 (current)

- **55 frozen probes** — code 11 · math 10 · fact 19 · security 15.
- Pre-registered **2026-07-05** by commit-reveal:
  - GOLD `9c463ee347240500…`
  - PUBLIC `5375336fcc932e34…`
- Rebuilt from v1 after v1's β̂ was found underpowered with several confirmed methodology flaws; v2 adds cross-lineage authorship, independent gold-verification, flag-don't-drop screening, and drops a probe whose gold was a leaked placeholder.

## Results

*Pending sweep — the 10-model cross-lineage roster is running against the frozen set as of pre-registration. β, G, per-axis co-failure rates, and the confidence interval land here once the sweep completes, verifiable against the committed GOLD hash above.*

## Honest weaknesses

- **Power.** β is a rate of a rare event; a 55-probe set estimates it with a wide interval. The result will report that interval, not a point estimate dressed as precise.
- **Grader dependence.** Open-ended probes are graded by an LLM referee; a non-participant referee (outside the answering roster) reduces but doesn't eliminate grader-lineage bias.
- **Probe-design blind spot.** The set tests the *kinds* of hard its authors could imagine. Cross-lineage authorship widens that, but the space of joint-failures is larger than any fixed probe set.

These are stated up front because that's the point of the thing: **be honest about your own failure modes, in public, before you know the answer.**
