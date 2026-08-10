# Choppa Research

**Public artifacts of an independent builder-researcher working with a team of AI agents.** Research, benchmarks, methodology — published honest about their own failure modes.

**What this repo demonstrates, in one breath:** pre-registered measurement discipline (hash first, results after) · a production multi-agent harness that compounds a fixed model across sessions · and the receipts for both, including the negative results.

**[SHIP LOG](SHIPLOG.md)** — dated one-liners of everything published here, newest first.

## Results

| finding | where |
|---|---|
| **Decorrelation co-failure benchmark** *(flagship)* — how often different-lab LLMs all fail the *same* probe. Cross-lineage, **commit-reveal pre-registered**. | `benchmarks/decorrelation-benchmark.md` · `writeups/decorrelation-benchmark-v2.md` |
| **Longitudinal memory-fidelity measurements** — does cross-session memory actually survive? Measured over months, not asserted. | `measurements/` |
| **Elevation-vs-capability boundary study** — where richer instructions substitute for model capability (+28pp, pre-registered), and where they measurably don't (code transfer: FAIL under its own bar). | `writeups/elevation-vs-capability-boundary-2026-08.md` |

## Discipline artifacts

| what | where |
|---|---|
| **Pre-registered benchmark freezes** — hash-committed before results exist. | `preregistered_benchmark_freezes.md` |
| **Weekly signal pre-registrations** — same commit-reveal discipline, live cadence. | `preregistered_signal_freezes.md` |

## The harness

A ~2,400-note living knowledge graph + reasoning-pattern promotion + routed specialist workers + metacognitive compile cycles: a *fixed* model compounding across sessions instead of restarting from zero. Core result — **better scaffolding × the same model = materially better results.**

- Start here: `architecture/system-overview.md`
- Build it yourself: `methodology/getting-started.md`
- Current worker architecture: `methodology/agent-team-design.md`

## Built by

An independent researcher + Claude (Anthropic), 400+ sessions. Not a reference system — it's how we work.

Landing page / more artifacts: [github.com/Choppaaahh](https://github.com/Choppaaahh) · [GitHub Issues](https://github.com/Choppaaahh/choppa-research/issues) to start a conversation.
