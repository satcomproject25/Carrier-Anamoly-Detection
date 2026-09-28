## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)

- Positive attempts: 120 (8 types x 3 magnitudes x 5 repeats); **coverage (valid/matchable) = 85.0%** (102 valid positive examples)
- Negative (clean, non-injected) examples: 211 carriers from 15 independent held-out TEST windows
- Scoreable examples (Phase 4 could compute a score, no NaN feature): 164/313

### Real precision / recall / F1

| pipeline | precision | recall | F1 |
|---|---|---|---|
| Phase 4 score alone | 0.925 | 0.363 | 0.521 |
| Combined (score + specific-type diagnosis) | 0.938 | 0.294 | 0.448 |

- **PR-AUC**: 0.8064
- **ROC-AUC**: 0.8574
- **False positive rate** (clean carriers flagged): 1.42%
- **Type-attribution accuracy** (of flagged true positives, fraction correctly typed): 45.9% (n=37)

### Per-type / per-magnitude flag rate (positives only, outcome=OK)

| type | level | flagged | n | rate |
|---|---|---|---|---|
| ADJACENT_CARRIER | moderate | 3 | 4 | 75% |
| ADJACENT_CARRIER | obvious | 3 | 4 | 75% |
| ADJACENT_CARRIER | subtle | 2 | 3 | 67% |
| ASYMMETRIC_DISTORTION | moderate | 1 | 3 | 33% |
| ASYMMETRIC_DISTORTION | obvious | 2 | 3 | 67% |
| ASYMMETRIC_DISTORTION | subtle | 0 | 3 | 0% |
| BANDWIDTH_SHIFT | moderate | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | obvious | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | subtle | 0 | 5 | 0% |
| DROPOUT | moderate | 0 | 5 | 0% |
| DROPOUT | obvious | 4 | 5 | 80% |
| DROPOUT | subtle | 0 | 5 | 0% |
| IN_BAND_TONE | moderate | 1 | 5 | 20% |
| IN_BAND_TONE | obvious | 2 | 5 | 40% |
| IN_BAND_TONE | subtle | 1 | 5 | 20% |
| NOISE_FLOOR_RISE | moderate | 2 | 5 | 40% |
| NOISE_FLOOR_RISE | obvious | 2 | 5 | 40% |
| NOISE_FLOOR_RISE | subtle | 1 | 5 | 20% |
| SHOULDER_BUMP | moderate | 2 | 4 | 50% |
| SHOULDER_BUMP | obvious | 2 | 4 | 50% |
| SHOULDER_BUMP | subtle | 1 | 3 | 33% |
| UNAUTHORIZED_CARRIER | moderate | 4 | 5 | 80% |
| UNAUTHORIZED_CARRIER | obvious | 4 | 5 | 80% |
| UNAUTHORIZED_CARRIER | subtle | 0 | 1 | 0% |

### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)

| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |
|---|---|---|---|---|
| IN_BAND_TONE | 11 | 3 | 1 | - |
| SHOULDER_BUMP | 6 | 4 | 1 | - |
| ADJACENT_CARRIER | 3 | 0 | 0 | {'ASYMMETRIC_EDGE_DISTORTION': 6, 'PRELIMINARY_INSTANTANEOUS_OUTLIER': 2, 'UNAUTHORIZED_CARRIER': 2} |
| ASYMMETRIC_DISTORTION | 6 | 0 | 3 | {'BANDWIDTH_ANOMALY': 1} |
| BANDWIDTH_SHIFT | 15 | 0 | 0 | - |
| NOISE_FLOOR_RISE | 10 | 0 | 0 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 5, 'UNAUTHORIZED_CARRIER': 5} |
| DROPOUT | 11 | 0 | 4 | - |
| UNAUTHORIZED_CARRIER | 3 | 0 | 8 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 8} |

### UNAUTHORIZED_CARRIER supplementary check — one sweep later

Phase 4 cannot score a carrier on its very first (appeared) observation — temporal features are NaN by construction. Re-checked the SAME injected carrier on the immediately-following real sweep:

- 0/11 flagged one sweep later (0/11 possible on the appearance sweep itself)
