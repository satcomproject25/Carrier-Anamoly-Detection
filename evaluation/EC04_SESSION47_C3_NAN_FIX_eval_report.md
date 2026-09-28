## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)

- Positive attempts: 120 (8 types x 3 magnitudes x 5 repeats); **coverage (valid/matchable) = 95.0%** (114 valid positive examples)
- Negative (clean, non-injected) examples: 227 carriers from 15 independent held-out TEST windows
- Scoreable examples (Phase 4 could compute a score, no NaN feature): 304/341

### Real precision / recall / F1

| pipeline | precision | recall | F1 |
|---|---|---|---|
| Phase 4 score alone | 0.421 | 0.605 | 0.496 |
| Combined (score + specific-type diagnosis) | 0.439 | 0.605 | 0.509 |

- **PR-AUC**: 0.3115
- **ROC-AUC**: 0.5851
- **False positive rate** (clean carriers flagged): 41.85%
- **Type-attribution accuracy** (of flagged true positives, fraction correctly typed): 37.7% (n=69)

### Per-type / per-magnitude flag rate (positives only, outcome=OK)

| type | level | flagged | n | rate |
|---|---|---|---|---|
| ADJACENT_CARRIER | moderate | 5 | 5 | 100% |
| ADJACENT_CARRIER | obvious | 5 | 5 | 100% |
| ADJACENT_CARRIER | subtle | 3 | 4 | 75% |
| ASYMMETRIC_DISTORTION | moderate | 1 | 5 | 20% |
| ASYMMETRIC_DISTORTION | obvious | 0 | 4 | 0% |
| ASYMMETRIC_DISTORTION | subtle | 1 | 5 | 20% |
| BANDWIDTH_SHIFT | moderate | 2 | 5 | 40% |
| BANDWIDTH_SHIFT | obvious | 2 | 5 | 40% |
| BANDWIDTH_SHIFT | subtle | 2 | 5 | 40% |
| DROPOUT | moderate | 0 | 5 | 0% |
| DROPOUT | obvious | 4 | 5 | 80% |
| DROPOUT | subtle | 0 | 5 | 0% |
| IN_BAND_TONE | moderate | 3 | 5 | 60% |
| IN_BAND_TONE | obvious | 4 | 5 | 80% |
| IN_BAND_TONE | subtle | 2 | 5 | 40% |
| NOISE_FLOOR_RISE | moderate | 5 | 5 | 100% |
| NOISE_FLOOR_RISE | obvious | 5 | 5 | 100% |
| NOISE_FLOOR_RISE | subtle | 5 | 5 | 100% |
| SHOULDER_BUMP | moderate | 3 | 5 | 60% |
| SHOULDER_BUMP | obvious | 5 | 5 | 100% |
| SHOULDER_BUMP | subtle | 1 | 5 | 20% |
| UNAUTHORIZED_CARRIER | moderate | 5 | 5 | 100% |
| UNAUTHORIZED_CARRIER | obvious | 5 | 5 | 100% |
| UNAUTHORIZED_CARRIER | subtle | 1 | 1 | 100% |

### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)

| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |
|---|---|---|---|---|
| IN_BAND_TONE | 6 | 0 | 0 | {'CARRIER_DRIFT': 4, 'ISOLATION_FOREST_ALONE_OUTLIER': 9, 'NOISE_FLOOR_RISE_POSSIBLE_JAMMING': 6, 'PER_FEATURE_INDEPENDENT_OUTLIER': 3, 'ASYMMETRIC_EDGE_DISTORTION': 1} |
| SHOULDER_BUMP | 6 | 0 | 1 | {'CARRIER_DRIFT': 5, 'ISOLATION_FOREST_ALONE_OUTLIER': 8, 'NOISE_FLOOR_RISE_POSSIBLE_JAMMING': 3, 'PER_FEATURE_INDEPENDENT_OUTLIER': 9} |
| ADJACENT_CARRIER | 1 | 0 | 0 | {'ASYMMETRIC_EDGE_DISTORTION': 7, 'ISOLATION_FOREST_ALONE_OUTLIER': 6, 'PER_FEATURE_INDEPENDENT_OUTLIER': 9, 'CARRIER_DRIFT': 3, 'PRELIMINARY_INSTANTANEOUS_OUTLIER': 2, 'UNAUTHORIZED_CARRIER': 2} |
| ASYMMETRIC_DISTORTION | 12 | 0 | 1 | {'BANDWIDTH_ANOMALY': 2, 'CARRIER_DRIFT': 2, 'ISOLATION_FOREST_ALONE_OUTLIER': 2, 'NOISE_FLOOR_RISE_POSSIBLE_JAMMING': 2, 'PER_FEATURE_INDEPENDENT_OUTLIER': 2} |
| BANDWIDTH_SHIFT | 9 | 0 | 6 | {'ASYMMETRIC_EDGE_DISTORTION': 3, 'CARRIER_DRIFT': 6, 'ISOLATION_FOREST_ALONE_OUTLIER': 5, 'NOISE_FLOOR_RISE_POSSIBLE_JAMMING': 6, 'PER_FEATURE_INDEPENDENT_OUTLIER': 3} |
| NOISE_FLOOR_RISE | 0 | 0 | 6 | {'ASYMMETRIC_EDGE_DISTORTION': 8, 'BANDWIDTH_ANOMALY': 3, 'CARRIER_DRIFT': 6, 'ISOLATION_FOREST_ALONE_OUTLIER': 9, 'PER_FEATURE_INDEPENDENT_OUTLIER': 6, 'IN_BAND_INTERFERENCE': 1, 'PRELIMINARY_INSTANTANEOUS_OUTLIER': 6, 'UNAUTHORIZED_CARRIER': 6} |
| DROPOUT | 11 | 0 | 4 | - |
| UNAUTHORIZED_CARRIER | 0 | 0 | 8 | {'ASYMMETRIC_EDGE_DISTORTION': 3, 'CARRIER_DRIFT': 3, 'ISOLATION_FOREST_ALONE_OUTLIER': 3, 'NOISE_FLOOR_RISE_POSSIBLE_JAMMING': 3, 'PER_FEATURE_INDEPENDENT_OUTLIER': 3, 'BANDWIDTH_ANOMALY': 2, 'PRELIMINARY_INSTANTANEOUS_OUTLIER': 1} |

### UNAUTHORIZED_CARRIER supplementary check — one sweep later

Phase 4 cannot score a carrier on its very first (appeared) observation — temporal features are NaN by construction. Re-checked the SAME injected carrier on the immediately-following real sweep:

- 3/11 flagged one sweep later (0/11 possible on the appearance sweep itself)
