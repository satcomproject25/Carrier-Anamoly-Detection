## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)

- Positive attempts: 120 (8 types x 3 magnitudes x 5 repeats); **coverage (valid/matchable) = 60.0%** (72 valid positive examples)
- Negative (clean, non-injected) examples: 60 carriers from 15 independent held-out TEST windows
- Scoreable examples (Phase 4 could compute a score, no NaN feature): 15/132

### Real precision / recall / F1

| pipeline | precision | recall | F1 |
|---|---|---|---|
| Phase 4 score alone | 1.000 | 0.167 | 0.286 |
| Combined (score + specific-type diagnosis) | 1.000 | 0.167 | 0.286 |

- **PR-AUC**: n/a
- **ROC-AUC**: n/a
- **False positive rate** (clean carriers flagged): 0.00%
- **Type-attribution accuracy** (of flagged true positives, fraction correctly typed): 100.0% (n=12)

### Per-type / per-magnitude flag rate (positives only, outcome=OK)

| type | level | flagged | n | rate |
|---|---|---|---|---|
| ADJACENT_CARRIER | moderate | 0 | 2 | 0% |
| ADJACENT_CARRIER | obvious | 0 | 2 | 0% |
| ADJACENT_CARRIER | subtle | 0 | 2 | 0% |
| ASYMMETRIC_DISTORTION | moderate | 0 | 2 | 0% |
| ASYMMETRIC_DISTORTION | obvious | 0 | 2 | 0% |
| ASYMMETRIC_DISTORTION | subtle | 0 | 2 | 0% |
| BANDWIDTH_SHIFT | moderate | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | obvious | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | subtle | 0 | 5 | 0% |
| DROPOUT | moderate | 1 | 4 | 25% |
| DROPOUT | obvious | 4 | 4 | 100% |
| DROPOUT | subtle | 1 | 4 | 25% |
| IN_BAND_TONE | moderate | 0 | 5 | 0% |
| IN_BAND_TONE | obvious | 0 | 5 | 0% |
| IN_BAND_TONE | subtle | 0 | 5 | 0% |
| SHOULDER_BUMP | moderate | 0 | 2 | 0% |
| SHOULDER_BUMP | obvious | 0 | 2 | 0% |
| SHOULDER_BUMP | subtle | 0 | 2 | 0% |
| UNAUTHORIZED_CARRIER | moderate | 3 | 5 | 60% |
| UNAUTHORIZED_CARRIER | obvious | 3 | 5 | 60% |
| UNAUTHORIZED_CARRIER | subtle | 0 | 2 | 0% |

### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)

| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |
|---|---|---|---|---|
| IN_BAND_TONE | 15 | 0 | 0 | - |
| SHOULDER_BUMP | 6 | 0 | 0 | - |
| ADJACENT_CARRIER | 6 | 0 | 0 | - |
| ASYMMETRIC_DISTORTION | 6 | 0 | 0 | - |
| BANDWIDTH_SHIFT | 15 | 0 | 0 | - |
| NOISE_FLOOR_RISE | 0 | 0 | 0 | - |
| DROPOUT | 6 | 0 | 6 | - |
| UNAUTHORIZED_CARRIER | 6 | 0 | 6 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 6} |

### UNAUTHORIZED_CARRIER supplementary check — one sweep later

Phase 4 cannot score a carrier on its very first (appeared) observation — temporal features are NaN by construction. Re-checked the SAME injected carrier on the immediately-following real sweep:

- 0/12 flagged one sweep later (0/12 possible on the appearance sweep itself)
