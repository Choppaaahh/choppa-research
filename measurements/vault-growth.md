# Vault Growth

Knowledge graph topology over time. Measures structural health and integration.

## Data

| Date | Notes | Links/Note | Domains | Orphans | Echo Chambers (<0.40) |
|------|-------|-----------|---------|---------|----------------------|
| 03/10 | ~170 | ~4.0 | 12 | ? | ? |
| 03/15 | ~220 | ~5.5 | 14 | ? | ? |
| 03/22 | ~325 | ~7.2 | 17 | 0 | ? |
| 03/25 | 346 | 7.2 | 17 | 0 | 1 domain (0.32) |
| 03/26 | 373 | 7.8 | 17 | 0 | 1 domain (0.34) |
| 03/27 | 386 | 8.1 | 17 | 0 | 2 domains (0.34, 0.32) |
| 03/28 | 394 | 8.1+ | 18 | 0 | 1 clearing, 1 cleared |
| 03/29 | 414 | 9.0 | 18 | 0 | 0 — both cleared via bridge sweep |
| 03/30 | 461 | — | 18 | 0 | 0 |
| 03/31 | 474 | — | 18 | 0 | 0 |
| 04/01 | 490 | — | 18 | 0 | 0 |
| 04/02 | 506 | — | 18 | 0 | 0 |
| **04/04** | **529** | **—** | **18** | **0** | **0** |

## Growth Rate

- **Total:** 170 → 529 notes in 25 days (~14 notes/day average)
- **April 4 alone:** 20+ notes created in one session (biggest single-day output)
- **Zero orphans** maintained through continuous Archivist monitoring
- **Echo chambers** eliminated by 03/29 and held at 0 through bridge campaigns

## Promoted Patterns Growth

| Date | Patterns | Phase Forks | Total | Compile # |
|------|----------|-------------|-------|-----------|
| 03/26 | 5 | 0 | 5 | #1 |
| 03/27 | 14 | 0 | 14 | #5 |
| 03/28 | 19 | 0 | 19 | #9 |
| 03/29 | 25 | 0 | 25 | #11 |
| 03/30 | 30 | 0 | 30 | #15 |
| 04/01 | 33 | 0 | 33 | #18 |
| 04/03 | 36 | 12 | 48 | #24 |
| **04/04** | **38** | **12** | **50** | **#25** |

Phase transition forks (n=1 promotion via topical influence) were introduced on 04/03, adding 12 structural forks in one session. This represents a second knowledge type with a different promotion mechanism.

## Structural Health Indicators

- **Links per note:** Started at ~4.0, now ~9.0+. Target: 3+ (exceeded).
- **Orphan rate:** 0% (continuously maintained)
- **Echo chamber count:** 0 (cleared 03/29, maintained)
- **Cross-domain reuse:** Scout→team-lead at 1 reference (identified gap 04/04). CORAL-inspired cross-agent flow rule wired.
- **Demand signals:** Dangling links tracked via vault_research_suggestions.py. Top demand: "arpeggio-chord-in-practice" (4 references, now created).

## Key Takeaway

Vault growth is monotonic (notes only increase) but integration quality oscillates. The health metrics (links/note, orphan rate, echo chambers) are the real signal — raw note count is vanity. The Archivist agent + automated health checks are what keep integration quality high during rapid growth periods.
