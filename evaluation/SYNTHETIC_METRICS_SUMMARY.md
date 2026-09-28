# Phase 5 TRACK 2 — Synthetic Metrics Summary (all sources)

Generated: 2026-08-11 18:47:09 — **CORRECTED 2026-08-13** for the UNAUTHORIZED_CARRIER
event-gating fix (see PROGRESS.md 2026-08-12/13 entries). Only the UNAUTHORIZED_CARRIER row/cells
and the aggregate columns that include it (score-alone & combined P/R/F1, FPR, type-attrib acc,
coverage) changed. PR-AUC and ROC-AUC are UNCHANGED and NOT recomputed — proven algebraically
unaffected by the fix, since UNAUTHORIZED_CARRIER's `anomaly_score` is `None` both before and
after (the fix adds an event-gated OR condition to the binary `flagged` decision; it never
touches any example's continuous score), so its rows were excluded from the AUC calculation
both times. The other 7 injection types' numbers are unchanged, reused from the original run
(confirmed unaffected — their target carriers never have `event=="appeared"`, so the fixed code
path never executes for them).

First real accuracy numbers in this project's history — see PROGRESS.md 2026-08-10 Part D for full methodology and caveats.

## Headline metrics per source

| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |
|---|---|---|---|---|---|---|---|
| A_16hr | 83.3% | 1.00/0.32/0.48 | 1.00/0.32/0.48 | 0.489 | 0.605 | 0.00% | 87.5% |
| B_ec02 | 90.0% | 0.83/0.32/0.47 | 0.82/0.31/0.45 | 0.430 | 0.680 | 1.61% | 85.7% |
| B_ec05 | 85.8% | 1.00/0.17/0.30 | 1.00/0.17/0.28 | 0.450 | 0.735 | 0.00% | 94.4% |
| C_g18 | 93.3% | 0.92/0.42/0.58 | 0.91/0.38/0.54 | 0.670 | 0.834 | 0.90% | 74.5% |

(Pre-fix, for reference: A_16hr 1.00/0.22/0.36 · B_ec02 0.78/0.23/0.36 · B_ec05 1.00/0.10/0.18 ·
C_g18 0.90/0.33/0.48 score-alone P/R/F1 — recall rose on every source once UNAUTHORIZED_CARRIER
could actually be counted; FPR is identical pre/post-fix on every source, confirming the fix adds
no false alarms.)

## Per-type flag rate at 'obvious' magnitude, across all 4 sources

| type | A_16hr | B_ec02 | B_ec05 | C_g18 |
|---|---|---|---|---|
| IN_BAND_TONE | 0% (n=5) | 60% (n=5) | 0% (n=5) | 40% (n=5) |
| SHOULDER_BUMP | 0% (n=5) | 20% (n=5) | 20% (n=5) | 20% (n=5) |
| ADJACENT_CARRIER | 80% (n=5) | 50% (n=4) | 0% (n=4) | 100% (n=5) |
| ASYMMETRIC_DISTORTION | 60% (n=5) | 75% (n=4) | 0% (n=4) | 100% (n=3) |
| BANDWIDTH_SHIFT | 0% (n=5) | 20% (n=5) | 0% (n=4) | 20% (n=5) |
| NOISE_FLOOR_RISE | n/a | 40% (n=5) | 0% (n=5) | 20% (n=5) |
| DROPOUT | 80% (n=5) | 100% (n=5) | 80% (n=5) | 100% (n=5) |
| UNAUTHORIZED_CARRIER | 100% (n=5) | 100% (n=5) | 100% (n=5) | 100% (n=5) |

UNAUTHORIZED_CARRIER at "obvious" magnitude is now 100% on every source (was 0% pre-fix) — the
fix closes the gap completely at this magnitude. "subtle" remains 0% on every source (a separate,
pre-existing detection-threshold limitation — the injected carrier isn't even segmented as a
candidate at that magnitude, `NOT_DETECTED_AS_CARRIER`, unrelated to gating). "moderate" is 100%
on every source except B_ec05 (60%, 3/5 — 2 of 5 also `NOT_DETECTED_AS_CARRIER` at that source's
own detection threshold).