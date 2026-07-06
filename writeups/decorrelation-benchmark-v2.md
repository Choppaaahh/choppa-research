# When the frontier fails together: a co-failure benchmark (v1 → v2)

*A short writeup of the decorrelation co-failure benchmark — including the part where v1 found nothing, said so, and got rebuilt.*

## The question

If you route a hard question to ten cross-lineage LLMs (spanning eight labs) and take the best answer, how often does *every one of them* still get it wrong? That number — call it **β**, the joint-failure rate — bounds what mixing models can ever buy you. Models that fail *independently* are recoverable by an ensemble: someone gets it right, you route to them. Models that fail *together* — same blind spot, inherited from overlapping training data or a shared architectural bias — are not. No amount of voting, routing, or cascading helps when they all miss the same probe.

Everyone reports single-model accuracy. Almost nobody reports β. This benchmark targets it directly, and reports one derived number that we think matters more than any leaderboard rank:

```
G  =  (1 − β)  −  best_single_model_accuracy
```

**G is the gain-ceiling** — an oracle that picks a correct model whenever *any* model is right scores `1 − β`, so G is the most accuracy that oracle adds over just always using the single best model. If G is small, model-mixing is a rounding error on hard problems, no matter how clever the router.

## v1: we found nothing, and said so

The first version measured **β̂ = 0** with a wide confidence interval. Zero joint-failures. Taken at face value that reads like great news — "the models are beautifully decorrelated!" It isn't. It's what an *underpowered* co-failure benchmark looks like: if your probes aren't hard enough, or your screening quietly drops the hardest ones, the joint-failure tail you're trying to measure never shows up in the sample. We wrote that limitation down as the headline finding rather than shipping "β=0, decorrelation confirmed." An honest null is a result; a laundered one is a liability.

Then we rebuilt.

## v2: what changed

Three design changes, each aimed at keeping the hard tail *in* the sample:

1. **Cross-lineage probe authorship.** Probes are written by models from distinct labs — code by one Chinese lab, math by one US lab, fact by another US lab, security by another Chinese lab (2 US + 2 CN, four lineages). No single lineage shapes the whole set, so no single lineage's blind spots define "hard."
2. **Flag-don't-drop screening.** Trivially-easy probes (whole panel correct) are dropped. Probes the panel *all* fail are **flagged for verification, not discarded** — because naively dropping all-fail probes is the exact mechanism that collapses β̂ to zero. The joint-failures are the signal.
3. **Independent gold-verification.** Every reference answer is checked before it counts — math/code by computation, external facts against *independent sources* (web search), critically **not** by a model from the probe-author's lineage. This guards the subtle failure where the author's lineage and the grader's lineage share the same wrong belief. One probe whose "gold" turned out to be a leaked placeholder was dropped here.

The frozen 55-probe set was **hash-committed and published before the sweep ran** (commit-reveal pre-registration) — so the results can't be cherry-picked after the fact.

The honest objection to all this: *every one of those changes also mechanically raises β, and we chose them knowing v1 read zero.* True — that's the researcher-degrees-of-freedom problem, and pre-registering a set we already believed was harder doesn't dissolve it. What closes it is that we froze the **method**, not just this set: the next batch, authored the same way, is an out-of-sample test of whether β stays high. This writeup is one data point with its knobs disclosed, not a law.

## v2 result

**β̂ = 0.582** (on the constructed hard set), 95% CI [0.441, 0.714]. **32 of 55** probes had all ten cross-lineage models wrong at once. Best single model: 38.2%.

The robust finding is that **β**: on this deliberately-hard set the frontier co-fails *a lot* — mixing models does far less than the ensemble / MoA / routing pitch assumes, because the models are hard *in the same places.* The gain-ceiling **G = 0.036** points the same way — a perfect router over the ten models (spanning eight labs) beats the best single by ~3.6 points — **but G is a 2-probe margin** (oracle 23/55 correct vs best-single 21/55) with a wide interval (~[0.01, 0.12]). So "mixing buys almost nothing" is the *point estimate*, not a settled result: at n=55 we can't rule out an oracle adding up to ~12 points, which would be worthwhile. We report G with that uncertainty rather than lean on it. The high co-failure rate is the solid part; the "ensembling is futile" corollary is the part that needs a bigger sample.

Per-axis, the co-failure rate ranges from **math 0.40** (verifiable single answers let models converge on the *correct* answer, not just a shared wrong one) up to **code 0.73** (they fail together most).

## Honest weaknesses

- **G is a 2-probe margin.** The gain-ceiling that powers "mixing is futile" is the net of 2 discordant probes (oracle 23/55 vs best-single 21/55); its interval (~[0.01, 0.12]) is wide enough to include a worthwhile router gain. The robust result is *high β*, not *small G* — we can't tighten G at n=55.
- **Small n, not rarity.** β̂ = 0.582 is a *majority* event; the wide CI is small-sample variance at p≈0.5, not a rare-event tail. (0.58 is a real signal, not a decimal dressed as certainty — we report the interval.)
- **Distribution.** β is co-failure *on the hard cross-lineage distribution this benchmark constructs.* It is **not** "58% of all questions stump every model." That's the thing the benchmark measures on purpose; it's not a claim about your day-to-day prompts.
- **Grader.** Open-ended probes (fact + security) are scored by an LLM referee — `gemini-2.5-flash`, with `qwen3-max` as a decorrelated fallback; math + code are matched deterministically. A large share of the joint-fails are referee-conditional; a harsher referee moves β.
- **Answer budget + silent failure.** Answers ran at a bounded token budget; a reasoner that exhausts it and returns empty/truncated is scored *wrong*, which can inflate β. Not fully controlled.
- **Residual gold error.** Verification reduces but doesn't eliminate wrong-but-"verified" golds — and the 32 hard-tail probes are exactly where one would mint a false joint-fail.
- **Probe-design blind spot.** The set tests the *kinds* of hard its authors could imagine. Cross-lineage authorship widens that; it can't close it.

## The meta-lesson

The most transferable finding isn't 0.58. It's the shape of the v1→v2 arc: **a co-failure benchmark that reports β≈0 is almost always underpowered, not evidence of decorrelation.** If you build one and it says the models never fail together, don't publish "decorrelation confirmed" — check whether your probes were ever hard enough to find the tail. We didn't know that until v1 handed us a zero and we resisted the urge to like it.

*Be honest about your own failure modes, in public, before you know the answer. The hashes went up before the sweep; the null got reported as a null; the numbers are what they are.*
