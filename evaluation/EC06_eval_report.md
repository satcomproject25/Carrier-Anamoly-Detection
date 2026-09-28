## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)

- Positive attempts: 120 (8 types x 3 magnitudes x 5 repeats); **coverage (valid/matchable) = 93.3%** (112 valid positive examples)
- Negative (clean, non-injected) examples: 174 carriers from 15 independent held-out TEST windows
- Scoreable examples (Phase 4 could compute a score, no NaN feature): 0/286

### Real precision / recall / F1

| pipeline | precision | recall | F1 |
|---|---|---|---|
| Phase 4 score alone | 0.473 | 0.232 | 0.311 |
| Combined (score + specific-type diagnosis) | 0.473 | 0.232 | 0.311 |

- **PR-AUC**: n/a
- **ROC-AUC**: n/a
- **False positive rate** (clean carriers flagged): 16.67%
- **Type-attribution accuracy** (of flagged true positives, fraction correctly typed): 61.5% (n=26)

### Per-type / per-magnitude flag rate (positives only, outcome=OK)

| type | level | flagged | n | rate |
|---|---|---|---|---|
| ADJACENT_CARRIER | moderate | 2 | 5 | 40% |
| ADJACENT_CARRIER | obvious | 2 | 5 | 40% |
| ADJACENT_CARRIER | subtle | 2 | 5 | 40% |
| ASYMMETRIC_DISTORTION | moderate | 1 | 5 | 20% |
| ASYMMETRIC_DISTORTION | obvious | 1 | 5 | 20% |
| ASYMMETRIC_DISTORTION | subtle | 1 | 5 | 20% |
| BANDWIDTH_SHIFT | moderate | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | obvious | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | subtle | 0 | 5 | 0% |
| DROPOUT | moderate | 3 | 4 | 75% |
| DROPOUT | obvious | 3 | 4 | 75% |
| DROPOUT | subtle | 0 | 4 | 0% |
| IN_BAND_TONE | moderate | 0 | 5 | 0% |
| IN_BAND_TONE | obvious | 1 | 5 | 20% |
| IN_BAND_TONE | subtle | 0 | 5 | 0% |
| NOISE_FLOOR_RISE | moderate | 0 | 5 | 0% |
| NOISE_FLOOR_RISE | obvious | 0 | 5 | 0% |
| NOISE_FLOOR_RISE | subtle | 0 | 5 | 0% |
| SHOULDER_BUMP | moderate | 0 | 5 | 0% |
| SHOULDER_BUMP | obvious | 0 | 5 | 0% |
| SHOULDER_BUMP | subtle | 0 | 4 | 0% |
| UNAUTHORIZED_CARRIER | moderate | 5 | 5 | 100% |
| UNAUTHORIZED_CARRIER | obvious | 5 | 5 | 100% |
| UNAUTHORIZED_CARRIER | subtle | 0 | 1 | 0% |

### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)

| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |
|---|---|---|---|---|
| IN_BAND_TONE | 14 | 0 | 0 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 1} |
| SHOULDER_BUMP | 14 | 0 | 0 | - |
| ADJACENT_CARRIER | 9 | 0 | 0 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 6} |
| ASYMMETRIC_DISTORTION | 12 | 0 | 0 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 3} |
| BANDWIDTH_SHIFT | 15 | 0 | 0 | - |
| NOISE_FLOOR_RISE | 15 | 0 | 0 | - |
| DROPOUT | 6 | 0 | 6 | - |
| UNAUTHORIZED_CARRIER | 1 | 0 | 10 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 10} |

### UNAUTHORIZED_CARRIER supplementary check — one sweep later

Phase 4 cannot score a carrier on its very first (appeared) observation — temporal features are NaN by construction. Re-checked the SAME injected carrier on the immediately-following real sweep:

- 0/11 flagged one sweep later (0/11 possible on the appearance sweep itself)
