## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)

- Positive attempts: 120 (8 types x 3 magnitudes x 5 repeats); **coverage (valid/matchable) = 96.7%** (116 valid positive examples)
- Negative (clean, non-injected) examples: 450 carriers from 15 independent held-out TEST windows
- Scoreable examples (Phase 4 could compute a score, no NaN feature): 236/566

### Real precision / recall / F1

| pipeline | precision | recall | F1 |
|---|---|---|---|
| Phase 4 score alone | 0.880 | 0.190 | 0.312 |
| Combined (score + specific-type diagnosis) | 0.875 | 0.181 | 0.300 |

- **PR-AUC**: 0.4603
- **ROC-AUC**: 0.7616
- **False positive rate** (clean carriers flagged): 0.67%
- **Type-attribution accuracy** (of flagged true positives, fraction correctly typed): 90.9% (n=22)

### Per-type / per-magnitude flag rate (positives only, outcome=OK)

| type | level | flagged | n | rate |
|---|---|---|---|---|
| ADJACENT_CARRIER | moderate | 1 | 5 | 20% |
| ADJACENT_CARRIER | obvious | 1 | 5 | 20% |
| ADJACENT_CARRIER | subtle | 1 | 5 | 20% |
| ASYMMETRIC_DISTORTION | moderate | 0 | 5 | 0% |
| ASYMMETRIC_DISTORTION | obvious | 1 | 5 | 20% |
| ASYMMETRIC_DISTORTION | subtle | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | moderate | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | obvious | 0 | 5 | 0% |
| BANDWIDTH_SHIFT | subtle | 0 | 5 | 0% |
| DROPOUT | moderate | 3 | 5 | 60% |
| DROPOUT | obvious | 5 | 5 | 100% |
| DROPOUT | subtle | 0 | 5 | 0% |
| IN_BAND_TONE | moderate | 1 | 5 | 20% |
| IN_BAND_TONE | obvious | 0 | 5 | 0% |
| IN_BAND_TONE | subtle | 0 | 5 | 0% |
| NOISE_FLOOR_RISE | moderate | 0 | 5 | 0% |
| NOISE_FLOOR_RISE | obvious | 0 | 5 | 0% |
| NOISE_FLOOR_RISE | subtle | 0 | 5 | 0% |
| SHOULDER_BUMP | moderate | 0 | 5 | 0% |
| SHOULDER_BUMP | obvious | 1 | 5 | 20% |
| SHOULDER_BUMP | subtle | 0 | 5 | 0% |
| UNAUTHORIZED_CARRIER | moderate | 4 | 5 | 80% |
| UNAUTHORIZED_CARRIER | obvious | 4 | 5 | 80% |
| UNAUTHORIZED_CARRIER | subtle | 0 | 1 | 0% |

### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)

| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |
|---|---|---|---|---|
| IN_BAND_TONE | 14 | 1 | 0 | - |
| SHOULDER_BUMP | 14 | 0 | 1 | - |
| ADJACENT_CARRIER | 12 | 0 | 2 | {'ASYMMETRIC_EDGE_DISTORTION': 3, 'SHOULDER_INTERFERENCE_SPECTRAL_REGROWTH': 3} |
| ASYMMETRIC_DISTORTION | 14 | 0 | 1 | {'BANDWIDTH_ANOMALY': 1} |
| BANDWIDTH_SHIFT | 15 | 0 | 0 | - |
| NOISE_FLOOR_RISE | 15 | 0 | 0 | - |
| DROPOUT | 7 | 0 | 8 | {'SHOULDER_INTERFERENCE_SPECTRAL_REGROWTH': 1} |
| UNAUTHORIZED_CARRIER | 3 | 0 | 8 | {'PRELIMINARY_INSTANTANEOUS_OUTLIER': 4} |

### UNAUTHORIZED_CARRIER supplementary check — one sweep later

Phase 4 cannot score a carrier on its very first (appeared) observation — temporal features are NaN by construction. Re-checked the SAME injected carrier on the immediately-following real sweep:

- 0/11 flagged one sweep later (0/11 possible on the appearance sweep itself)
