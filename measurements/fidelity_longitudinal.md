# Fidelity Longitudinal Data — F1 through F13

Scaffold reconstruction fidelity measured across 13 independent tests over 5 weeks. Each test samples 5 recent decisions and scores on 4 dimensions (0-1 scale).

## Results

| Test | Date | WHAT | WHY | CONTEXT | BRIDGE | Notes |
|------|------|------|-----|---------|--------|-------|
| F1 | 03/10 | 1.00 | 0.93 | 0.60 | — | Major decisions only (selection bias) |
| F2 | 03/15 | 1.00 | 0.80 | 0.50 | — | Mixed operational decisions |
| F3 | 03/20 | 0.73 | 0.53 | 0.53 | — | Unlogged sprint (no breadcrumbs) |
| F3-fix | 03/20 | 1.00 | 0.87 | 0.87 | — | After 7 breadcrumb lines added |
| F4 | 03/24 | 0.84 | 0.65 | 0.60 | 0.40 | BRIDGE dimension added |
| F5 | 03/28 | 0.82 | 0.88 | 0.93 | 0.82 | All-time highs on WHY/CONTEXT/BRIDGE |
| F6 | 03/29 | 1.00 | 0.85 | 0.85 | 0.65 | WHAT ceiling. Infrastructure = low BRIDGE |
| F7 | 03/30 | 0.94 | 0.85 | 0.88 | 0.83 | Cross-domain session = high BRIDGE |
| F8 | 03/31 | 0.85 | 0.84 | 0.88 | 0.78 | Build blitz, hot-tier falling behind |
| F9 | 04/01 | **0.60** | 0.82 | 0.88 | 0.55 | **WHAT CRISIS** — build blitz without MD update |
| F10 | 04/02 | 0.84 | 0.84 | 0.90 | 0.66 | WHAT recovered after prescription |
| F11 | 04/03 | 0.67 | 0.83 | 0.87 | 0.60 | WHAT relapse — same root cause |
| **F12** | **04/04** | **1.00** | **1.00** | **0.90** | **0.70** | **WHAT+WHY ceiling after MD sweep** |
| **F13** | **04/04** | **0.90** | **0.80** | **0.60** | **0.90** | **BRIDGE all-time high. CONTEXT crashed (build marathon)** |

## The Sawtooth Pattern (F9-F13)

The most significant finding from the longitudinal data: WHAT and CONTEXT exhibit a sawtooth pattern correlated with build intensity.

```
Build hard → WHAT/CONTEXT crash (changes outrun documentation)
→ MD update sweep → WHAT/CONTEXT recover
→ Build hard again → crash again
```

F9 (0.60), F10 (0.84), F11 (0.67), F12 (1.00), F13 (0.90) — the oscillation is predictable. The fix isn't behavioral ("remember to update docs") — it's infrastructure: hooks that detect stale documentation and warn before commits.

Two hooks were wired to address this:
1. **MD staleness check** — warns on `git commit` if identity docs >30min stale
2. **Breadcrumb WHY nudge** — prompts for triggering context on every significant edit

WHAT improved from 0.60 (F9 crisis) to 0.90 (F13 with hooks). CONTEXT remains the weakest dimension — triggering events still require deliberate capture.

## BRIDGE — The Scaffold Priming Effect

BRIDGE (cross-domain connections) is the most interesting dimension. It correlates with session type:

| Session Type | Typical BRIDGE | Examples |
|---|---|---|
| Infrastructure-only | 0.55-0.65 | F6 (launchd), F9 (build blitz) |
| Cross-domain research | 0.80-0.90 | F5 (crisis analysis), F7 (autopoiesis), **F13 (8 papers)** |

F13 achieved the all-time BRIDGE high (0.90) after a session that deep-dived 8 research papers across multiple domains. The behavior patterns from these papers created explicit cross-domain bridges that the fidelity test could reconstruct.

This correlates with the R14 finding: loading behavior patterns (which encode cross-domain reasoning templates) improved BRIDGE from 0.30→0.50→0.80. The fidelity data independently confirms that cross-domain activity produces durable BRIDGE scores.

## Key Findings

### 1. WHAT is fixable with hooks (0.60 → 0.90-1.00)
Hot-tier document staleness is the sole cause of WHAT crashes. Automated staleness detection prevents the crash.

### 2. WHY stabilized above baseline (0.70 → 0.80-1.00)
Breadcrumb capture + reasoning chain logging took WHY from a chronic weakness to a stable strength. Infrastructure changes, not discipline.

### 3. CONTEXT remains the weakest dimension (0.60-0.90)
Triggering events require deliberate capture that no hook fully automates. The breadcrumb system helps but doesn't solve the "why did you make this specific decision" question. A mandatory trigger clause in identity document entries was wired to address this.

### 4. BRIDGE depends on cross-domain activity (0.40-0.90)
You can't score high on BRIDGE during a single-domain session. The dimension rewards sessions that connect trading to research, patterns to papers, operations to theory. Behavior pattern priming (R14: +18.5%) is the mechanism that makes BRIDGE scores durable.

### 5. Measurement tool quality matters
F3-F4 scores were depressed by measurement bugs (test only reading 2/5 scaffold sources). After fixing: CONTEXT jumped from 0.60 to 0.93. Always measure your measurement.

## Methodology

- **Scorer:** AI model (same family as scaffold agent). Goodhart caveat applies.
- **Decisions sampled:** 5 per test, drawn from recent operational decisions.
- **Dimensions:** WHAT (decision stated?), WHY (reasoning documented?), CONTEXT (triggering event captured?), BRIDGE (cross-domain connections visible?).
- **Sources:** 5 scaffold documents (identity doc, operating rules, live breadcrumbs, task list, domain map).
- **Frequency:** ~1 per day during active development sessions.
