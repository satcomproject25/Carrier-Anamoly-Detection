## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)

- Positive attempts: 120 (8 types x 3 magnitudes x 5 repeats); **coverage (valid/matchable) = 81.7%** (98 valid positive examples)
- Negative (clean, non-injected) examples: 81 carriers from 15 independent held-out TEST windows
- Scoreable examples (Phase 4 could compute a score, no NaN feature): 92/179

### Real precision / recall / F1

| pipeline | precision | recall | F1 |
|---|---|---|---|
| Phase 4 score alone | 0.627 | 0.327 | 0.430 |
| Combined (score + specific-type diagnosis) | 0.627 | 0.327 | 0.430 |

- **PR-AUC**: 0.6646
- **ROC-AUC**: 0.5702
- **False positive rate** (clean carriers flagged): 23.46%
- **Type-attribution accuracy** (of flagged true positives, fraction correctly typed): 50.0% (n=32)

### Per-type / per-magnitude flag rate (positives only, outcome=OK)

| type | level | flagged | n | rate |
|---|---|---|---|---|
| ADJACENT_CARRIER | moderate | 1 | 3 | 33% |
| ADJACENT_CARRIER | obvious | 1 | 3 | 33% |
| ADJACENT_CARRIER | subtle | 0 | 3 | 0% |
| ASYMMETRIC_DISTORTION | moderate | 1 | 4 | 25% |
| ASYMMETRIC_DISTORTION | obvious | 1 | 3 | 33% |
| ASYMMETRIC_DISTORTION | subtle | 1 | 4 | 25% |
| BANDWIDTH_SHIFT | moderate | 1 | 5 | 20% |
| BANDWIDTH_SHIFT | obvious | 1 | 5 | 20% |
| BANDWIDTH_SHIFT | subtle | 1 | 5 | 20% |
| DROPOUT | moderate | 1 | 4 | 25% |
| DROPOUT | obvious | 3 | 4 | 75% |
| DROPOUT | subtle | 1 | 4 | 25% |
| IN_BAND_TONE | moderate | 0 | 4 | 0% |
| IN_BAND_TONE | obvious | 0 | 5 | 0% |
| IN_BAND_TONE | subtle | 1 | 4 | 25% |
| NOISE_FLOOR_RISE | moderate | 2 | 5 | 40% |
| NOISE_FLOOR_RISE | obvious | 2 | 5 | 40% |
| NOISE_FLOOR_RISE | subtle | 2 | 5 | 40% |
| SHOULDER_BUMP | moderate | 0 | 4 | 0% |
| SHOULDER_BUMP | obvious | 1 | 5 | 20% |
| SHOULDER_BUMP | subtle | 1 | 4 | 25% |
| UNAUTHORIZED_CARRIER | moderate | 5 | 5 | 100% |
| UNAUTHORIZED_CARRIER | obvious | 5 | 5 | 100% |

### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)

| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |
|---|---|---|---|---|
| IN_BAND_TONE | 12 | 0 | 0 | {'PER_FEATURE_INDEPENDENT_OUTLIER': 1} |
| SHOULDER_BUMP | 11 | 0 | 0 | {'PER_FEATURE_INDEPENDENT_OUTLIER': 1, 'ISOLATION_FOREST_ALONE_OUTLIER': 1} |
| ADJACENT_CARRIER | 7 | 0 | 0 | {'PER_FEATURE_INDEPENDENT_OUTLIER': 2} |
| ASYMMETRIC_DISTORTION | 8 | 0 | 0 | {'PER_FEATURE_INDEPENDENT_OUTLIER': 3} |
| BANDWIDTH_SHIFT | 12 | 0 | 0 | {'PER_FEATURE_INDEPENDENT_OUTLIER': 3} |
| NOISE_FLOOR_RISE | 9 | 0 | 2 | {'ISOLATION_FOREST_ALONE_OUTLIER': 5, 'PER_FEATURE_INDEPENDENT_OUTLIER': 5, 'ADJACENT_CHANNEL_INTERFERENCE': 2, 'ASYMMETRIC_EDGE_DISTORTION': 2, 'CARRIER_DRIFT': 2, 'PRELIMINARY_INSTANTANEOUS_OUTLIER': 1, 'UNAUTHORIZED_CARRIER': 1} |
| DROPOUT | 7 | 0 | 5 | - |
| UNAUTHORIZED_CARRIER | 0 | 0 | 9 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 10} |

### UNAUTHORIZED_CARRIER supplementary check — one sweep later

Phase 4 cannot score a carrier on its very first (appeared) observation — temporal features are NaN by construction. Re-checked the SAME injected carrier on the immediately-following real sweep:

- 0/10 flagged one sweep later (0/10 possible on the appearance sweep itself)
