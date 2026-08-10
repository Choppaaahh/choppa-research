# SHIP LOG

*Dated one-liners of public work — research, evals, benchmarks, builds. Newest first. Each line links an artifact in this repo (or will, when its writeup lands). Sanitized: methodology + measurements only.*

---

- **2026-08-10** — [Elevation-vs-capability boundary study](writeups/elevation-vs-capability-boundary-2026-08.md) published: pre-registered, +28pp canonical-widening confirmed, product thesis and code-transfer both FAILED their own bars and are reported as such. Prior art independently establishing the core effect is credited, not buried.
- **2026-08-10** — Three standalone tools published to `implementation/` (corpus-calibrated dedup gate, saturation detector, counterfactual retrieval-poison scorer) — paper → built → golden-fixture tested → published inside 12 hours.
- **2026-08-10** — The commit gate audited itself: all invariants ranked by lifetime blocks (1,217 total; top 9 carry 96.8%). Two retired with receipts; one added after discovering the gate's own freshness self-test had failed *correctly* into an unread weekly cron for 13 days. Auditor: a cross-model delegate — maker never checks its own work.
- **2026-08-09** — Audit-day finding, named as a failure class: instruments that *exist, pass shallow checks, and do nothing* (n=7 in one sweep, longest 54 days). The fix pattern: verify the instrument moves before trusting its readings.
- **2026-07-09** — `agent_01` built: work-agent skeleton with *governed* memory — provenance quarantine, preservation gate, audit log, echo-proof self-consolidation (self-derived patterns quarantined at birth). 15 verification claims, every README claim = a named runnable test. Repo public soon.
- **2026-07-09** — Agent-memory market scan: provenance/trust-tiers/quarantine/poisoning-defense = recommended everywhere (OWASP ASI06, MemoryGraft/MINJA), shipped as core features by nobody. Governance is the white-space.
- **2026-07-08** — grok-4.5 day-one eval: co-failure similarity 0.150 vs its predecessor = same-lineage clone territory (cf. opus↔sonnet 0.152). New model ≠ new decorrelation. Bloc-membership hypothesis (H3) refuted on the wider fold.
- **2026-07-08** — 10 paper deepdives in one day at ~$0.21 total via routed cheap-model orchestration; highlights: NLT fallback +14.9pp tool-success, semantic-memory 70→89.7%, distillation suppresses fork-rate −17%.
- **2026-07-07** — Search-backend A/B (2 rounds, pre-registered ground truth): answer-class engines (5/5) beat retrieval-class (4/5) only on *derived* facts; a synthesis layer over retrieval closes the gap. Routing locked accordingly.
- **2026-07-05** — Co-failure benchmark v2 result: β̂ = 0.582 — frontier models share blind-spots far above independence; naive ensembling buys ~3.6pts, not the ~15 independence predicts. Commit-reveal pre-registered (hash before results).
- **2026-07-04** — v1 self-falsified honestly: β̂=0 read was underpowered, method survived, v2 designed. Negative results published like positive ones.
- **2026-06-25** — Decorrelated adversarial review: cross-lab reviewer pairs catch complementary defects (each solo reviewer missed what the other caught). Reviewer diversity > reviewer strength.
- **2026-06-17** — Reasoning-model vs coder-model on ambiguous specs (n=3, held-out adversarial fixtures): reasoning model 0 defects, coder 2-of-3 — the edge appears *only* where the spec has trap-density. Route by ambiguity, not by size.
- **2026-06-13** — Golden-fixtures discipline: hand-computed ground-truth pairs asserted verbatim in generated code kill the "test passes because it's wrong the same way the code is" defect class. First zero-defect generated batch at n=5 followed (2026-07-09).
- **2026-06** — Retrieval embedder v9 (multiview finetune) promoted through a locked A/B gate: challenger must beat incumbent on r@1 AND r@5 AND r@15 before going live. No vibes-promotions.
- **ongoing, weekly** — Pre-registered research predictions: hash committed before the week, outcomes revealed after. `preregistered_signal_freezes.md`.
