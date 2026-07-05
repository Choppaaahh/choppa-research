# Pre-Registered Benchmark Freezes (commit-reveal)

Each row is the sha256 of a canonical JSON dump of a FROZEN probe set for the
co-failure decorrelation benchmark, published BEFORE the model sweep runs. The
GOLD hash commits to the probes *and* their reference answers; the PUBLIC hash
commits to the questions only. This prevents post-hoc probe/answer editing —
the sweep results can be verified against these commitments after reveal.

Probe content and answers are NOT published here (hash-only). Only sha256
commitments + set sizes.

| benchmark | published (UTC) | n | axes | GOLD sha256 | PUBLIC sha256 |
|---|---|---|---|---|---|
| hard_battery_v2 | 2026-07-05T13:46:57Z | 55 | code11/math10/fact19/security15 | 9c463ee347240500 | 5375336fcc932e34 |
