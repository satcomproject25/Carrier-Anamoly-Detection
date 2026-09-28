## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)

- Positive attempts: 120 (8 types x 3 magnitudes x 5 repeats); **coverage (valid/matchable) = 90.0%** (108 valid positive examples)
- Negative (clean, non-injected) examples: 450 carriers from 15 independent held-out TEST windows
- Scoreable examples (Phase 4 could compute a score, no NaN feature): 502/558

### Real precision / recall / F1

| pipeline | precision | recall | F1 |
|---|---|---|---|
| Phase 4 score alone | 0.596 | 0.287 | 0.388 |
| Combined (score + specific-type diagnosis) | 0.596 | 0.287 | 0.388 |

- **PR-AUC**: 0.3709
- **ROC-AUC**: 0.6835
- **False positive rate** (clean carriers flagged): 4.67%
- **Type-attribution accuracy** (of flagged true positives, fraction correctly typed): 83.9% (n=31)

### Per-type / per-magnitude flag rate (positives only, outcome=OK)

| type | level | flagged | n | rate |
|---|---|---|---|---|
| ADJACENT_CARRIER | moderate | 4 | 4 | 100% |
| ADJACENT_CARRIER | obvious | 4 | 4 | 100% |
| ADJACENT_CARRIER | subtle | 0 | 4 | 0% |
| ASYMMETRIC_DISTORTION | moderate | 0 | 3 | 0% |
| ASYMMETRIC_DISTORTION | obvious | 1 | 3 | 33% |
| ASYMMETRIC_DISTORTION | subtle | 0 | 4 | 0% |
| BANDWIDTH_SHIFT | moderate | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | obvious | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | subtle | 0 | 5 | 0% |
| DROPOUT | moderate | 3 | 5 | 60% |
| DROPOUT | obvious | 5 | 5 | 100% |
| DROPOUT | subtle | 0 | 5 | 0% |
| IN_BAND_TONE | moderate | 0 | 5 | 0% |
| IN_BAND_TONE | obvious | 1 | 5 | 20% |
| IN_BAND_TONE | subtle | 0 | 5 | 0% |
| NOISE_FLOOR_RISE | moderate | 1 | 5 | 20% |
| NOISE_FLOOR_RISE | obvious | 1 | 5 | 20% |
| NOISE_FLOOR_RISE | subtle | 0 | 5 | 0% |
| SHOULDER_BUMP | moderate | 2 | 5 | 40% |
| SHOULDER_BUMP | obvious | 1 | 5 | 20% |
| SHOULDER_BUMP | subtle | 0 | 5 | 0% |
| UNAUTHORIZED_CARRIER | moderate | 4 | 5 | 80% |
| UNAUTHORIZED_CARRIER | obvious | 4 | 5 | 80% |
| UNAUTHORIZED_CARRIER | subtle | 0 | 1 | 0% |

### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)

| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |
|---|---|---|---|---|
| IN_BAND_TONE | 14 | 0 | 1 | {'ASYMMETRIC_EDGE_DISTORTION': 1, 'ISOLATION_FOREST_ALONE_OUTLIER': 1, 'PER_FEATURE_INDEPENDENT_OUTLIER': 1, 'SHOULDER_INTERFERENCE_SPECTRAL_REGROWTH': 1} |
| SHOULDER_BUMP | 12 | 0 | 0 | {'PER_FEATURE_INDEPENDENT_OUTLIER': 3} |
| ADJACENT_CARRIER | 4 | 0 | 8 | {'NOISE_FLOOR_RISE_POSSIBLE_JAMMING': 2, 'PER_FEATURE_INDEPENDENT_OUTLIER': 8, 'ASYMMETRIC_EDGE_DISTORTION': 2} |
| ASYMMETRIC_DISTORTION | 9 | 0 | 1 | {'BANDWIDTH_ANOMALY': 1} |
| BANDWIDTH_SHIFT | 15 | 0 | 0 | - |
| NOISE_FLOOR_RISE | 13 | 0 | 0 | {'PER_FEATURE_INDEPENDENT_OUTLIER': 2, 'PRELIMINARY_INSTANTANEOUS_OUTLIER': 2, 'UNAUTHORIZED_CARRIER': 2} |
| DROPOUT | 7 | 0 | 8 | - |
| UNAUTHORIZED_CARRIER | 3 | 0 | 8 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 4} |

### UNAUTHORIZED_CARRIER supplementary check — one sweep later

Phase 4 cannot score a carrier on its very first (appeared) observation — temporal features are NaN by construction. Re-checked the SAME injected carrier on the immediately-following real sweep:

- 0/11 flagged one sweep later (0/11 possible on the appearance sweep itself)
