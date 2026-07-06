# Decorrelation Co-Failure Benchmark

**How often does an ensemble of different-lab LLMs all get the *same* hard question wrong?**

That number bounds what mixing models can ever buy you. If models fail *independently*, an ensemble (vote, route, cascade) recovers most single-model errors. If they fail *together* — same blind spot, inherited from shared training data or a shared architectural bias — the ensemble fails too, and no amount of routing helps. This benchmark measures the co-failure rate directly.

## The quantity

For a probe set and a roster of *N* models from *different labs/lineages*:

```
β  =  Pr[ all N models are wrong on the same probe ]
G  =  (1 − β)  −  best_single_model_accuracy    (oracle accuracy − best single = the ceiling an ensemble can add)
```

β is the **joint-failure floor**. An oracle that picks a correct model whenever *any* model is right scores `1 − β`; **G is what that oracle adds over just always using the single best model** — the gain-ceiling for any router/ensemble. A benchmark that only reports single-model accuracy hides β; this one targets it.

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

## Results (v2, 2026-07-05)

**β̂ = 0.582** (on the constructed hard-probe set) · 95% CI **[0.441, 0.714]** · **32 of 55** probes had *all 10* cross-lineage models wrong.

| metric | value |
|---|---|
| β — joint-failure rate | **0.582** |
| 95% CI (binomial, n=55) | [0.441, 0.714] |
| best single-model accuracy | 0.382 |
| **gain-ceiling G** = (1−β) − best_acc | **0.036** *(±wide — a 2-probe margin; see Honest weaknesses)* |
| joint-fails | 32 / 55 |

**Per-model accuracy** (the leaderboard):

| model | lineage | bloc | acc |
|---|---|---|---|
| gpt | OpenAI | US | 0.382 |
| claude-sonnet | Anthropic | US | 0.345 |
| grok | xAI | US | 0.345 |
| claude-opus | Anthropic | US | 0.291 |
| gemini-3.5 | Google | US | 0.273 |
| kimi | Moonshot | CN | 0.255 |
| qwen | Alibaba | CN | 0.218 |
| glm | Zhipu | CN | 0.218 |
| gemini | Google | US | 0.145 |
| deepseek | DeepSeek | CN | 0.145 |

**Per-axis β:**

| axis | n | joint-fails | β |
|---|---|---|---|
| code | 11 | 8 | 0.727 |
| security | 15 | 10 | 0.667 |
| fact | 19 | 10 | 0.526 |
| math | 10 | 4 | 0.400 |

**Reading it.** The robust finding is **high β** — on this deliberately-hard cross-lineage set the frontier *co-fails a lot* (32 of 55 probes stump all ten). The gain-ceiling **G = 0.036 is a 2-probe margin** (oracle 23/55 correct vs best-single 21/55), with a wide interval (roughly [0.01, 0.12]) — so "a perfect router buys ~3.6 points, almost nothing" is the *point estimate*, **not** an established result: at n=55 the data are equally consistent with an oracle adding up to ~12 points. We report it, we don't lean on it (see Honest weaknesses). β is co-failure *on the hard-probe distribution the benchmark constructs*, not a claim about general questions. Math is the lowest-β axis (0.40) — verifiable single answers let models converge on *correct*; code + security are highest. All verifiable against the committed GOLD hash `9c463ee3…`.

**v1 → v2 (why the inversion is the point).** v1 — a smaller, less cross-lineage set — measured β̂ = 0 with a wide interval: an honest *underpowered null*, reported as such rather than dressed up. v2's harder cross-lineage-authored probes + independent gold-verification surfaced the real signal. **A co-failure benchmark that reports β≈0 is usually underpowered, not decorrelation-free** — that lesson, learned in public, is as much the contribution as the number.

## Honest weaknesses

- **G is underpowered — it rests on 2 probes.** The gain-ceiling G = 0.036 is the net of just 2 discordant probes (oracle 23/55 correct vs best-single 21/55). A confidence interval on 2/55 spans roughly [0.01, 0.12], so the data are consistent with an oracle router adding anywhere from ~0 to ~12 points. **We cannot distinguish "mixing buys almost nothing" from "mixing buys a modest amount" at this n.** The robust finding is *high β*; the small-G "ensembling is futile" reading is a point estimate with an interval we don't yet have the sample size to tighten. (Our own v1 falsification flagged the same fragility — G flips sign near β's upper CI.)
- **Small n, not rarity.** β̂ = 0.582 is a *majority* event; the wide CI is small-sample binomial variance at p≈0.5 (n=55), not a rare-event tail.
- **Grader dependence.** Open-ended probes (much of fact + security) are graded by an LLM referee — `gemini-2.5-flash`, with `qwen3-max` as a decorrelated fallback when the answer came from Google. Short-answer/forced-choice probes (math + code) are matched deterministically. So a meaningful share of β is referee-conditional — security alone supplies 10 of the 32 joint-fails — and a harsher referee would move the number.
- **Answer budget + silent failure.** Answers were generated at a bounded output budget (~1.2–2.4k tokens); a reasoning model that exhausts it and returns empty/truncated is scored *wrong*. This can inflate β and depress the leaderboard for verbose reasoners — a known confound we did not fully control.
- **Residual gold error on the hard tail.** Golds were verified, but the 32 all-fail probes are exactly where a subtly-wrong-but-"verified" gold would mint a false joint-fail. Verification reduces this; it doesn't eliminate it.
- **Distribution.** β is co-failure on the *constructed hard cross-lineage distribution*, **not** "58% of all questions stump every model." That's what the benchmark measures on purpose — not a claim about everyday prompts.
- **Probe-design blind spot.** The set tests the *kinds* of hard its authors could imagine. Cross-lineage authorship widens that, but the space of joint-failures is larger than any fixed probe set.

These are stated up front because that's the point of the thing: **be honest about your own failure modes, in public, before you know the answer** — including about the number we'd most like to headline.
