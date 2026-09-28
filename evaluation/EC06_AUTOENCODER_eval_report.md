## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)

- Positive attempts: 120 (8 types x 3 magnitudes x 5 repeats); **coverage (valid/matchable) = 88.3%** (106 valid positive examples)
- Negative (clean, non-injected) examples: 141 carriers from 15 independent held-out TEST windows
- Scoreable examples (Phase 4 could compute a score, no NaN feature): 161/247

### Real precision / recall / F1

| pipeline | precision | recall | F1 |
|---|---|---|---|
| Phase 4 score alone | 0.682 | 0.283 | 0.400 |
| Combined (score + specific-type diagnosis) | 0.698 | 0.283 | 0.403 |

- **PR-AUC**: 0.4605
- **ROC-AUC**: 0.5075
- **False positive rate** (clean carriers flagged): 9.93%
- **Type-attribution accuracy** (of flagged true positives, fraction correctly typed): 86.7% (n=30)

### Per-type / per-magnitude flag rate (positives only, outcome=OK)

| type | level | flagged | n | rate |
|---|---|---|---|---|
| ADJACENT_CARRIER | moderate | 0 | 5 | 0% |
| ADJACENT_CARRIER | obvious | 0 | 5 | 0% |
| ADJACENT_CARRIER | subtle | 0 | 5 | 0% |
| ASYMMETRIC_DISTORTION | moderate | 0 | 4 | 0% |
| ASYMMETRIC_DISTORTION | obvious | 0 | 4 | 0% |
| ASYMMETRIC_DISTORTION | subtle | 0 | 4 | 0% |
| BANDWIDTH_SHIFT | moderate | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | obvious | 0 | 4 | 0% |
| BANDWIDTH_SHIFT | subtle | 1 | 5 | 20% |
| DROPOUT | moderate | 4 | 4 | 100% |
| DROPOUT | obvious | 4 | 4 | 100% |
| DROPOUT | subtle | 3 | 4 | 75% |
| IN_BAND_TONE | moderate | 0 | 5 | 0% |
| IN_BAND_TONE | obvious | 0 | 5 | 0% |
| IN_BAND_TONE | subtle | 0 | 5 | 0% |
| NOISE_FLOOR_RISE | moderate | 3 | 5 | 60% |
| NOISE_FLOOR_RISE | obvious | 3 | 5 | 60% |
| NOISE_FLOOR_RISE | subtle | 4 | 5 | 80% |
| SHOULDER_BUMP | moderate | 0 | 4 | 0% |
| SHOULDER_BUMP | obvious | 0 | 4 | 0% |
| SHOULDER_BUMP | subtle | 0 | 3 | 0% |
| UNAUTHORIZED_CARRIER | moderate | 4 | 5 | 80% |
| UNAUTHORIZED_CARRIER | obvious | 4 | 5 | 80% |
| UNAUTHORIZED_CARRIER | subtle | 0 | 2 | 0% |

### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)

| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |
|---|---|---|---|---|
| IN_BAND_TONE | 15 | 0 | 0 | - |
| SHOULDER_BUMP | 11 | 0 | 0 | - |
| ADJACENT_CARRIER | 15 | 0 | 0 | - |
| ASYMMETRIC_DISTORTION | 12 | 0 | 0 | - |
| BANDWIDTH_SHIFT | 13 | 0 | 0 | {'ADJACENT_CHANNEL_INTERFERENCE': 1, 'NOISE_FLOOR_RISE_POSSIBLE_JAMMING': 1} |
| NOISE_FLOOR_RISE | 5 | 0 | 7 | {'BANDWIDTH_ANOMALY': 4, 'UNAUTHORIZED_CARRIER': 3, 'IN_BAND_INTERFERENCE': 5} |
| DROPOUT | 1 | 0 | 11 | - |
| UNAUTHORIZED_CARRIER | 4 | 0 | 8 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 8} |

### UNAUTHORIZED_CARRIER supplementary check — one sweep later

Phase 4 cannot score a carrier on its very first (appeared) observation — temporal features are NaN by construction. Re-checked the SAME injected carrier on the immediately-following real sweep:

- 0/12 flagged one sweep later (0/12 possible on the appearance sweep itself)
