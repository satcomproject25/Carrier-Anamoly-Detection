# Session 37 TRACK 2 -- production architecture + OR-gate (IF-alone + per-feature)

Generated: 2026-09-09 16:01:10

EC03/EC06/G16: session 22/23 pooled model. EC04: session 29 dedicated model. All 4 extended with session 36's OR-gate: flagged = blended_score_flagged OR IF_alone_flagged OR per_feature_flagged. Compare against session 24/29's own reports (no OR-gate) for the exact before/after this session was scoped to produce.

## Headline metrics per source

| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |
|---|---|---|---|---|---|---|---|
| EC03 | 90.0% | 0.60/0.29/0.39 | 0.60/0.29/0.39 | 0.371 | 0.683 | 4.67% | 83.9% |
| EC04 | 95.0% | 0.54/0.52/0.53 | 0.54/0.52/0.53 | 0.650 | 0.743 | 22.47% | 22.0% |
| EC06 | 88.3% | 0.49/0.23/0.31 | 0.49/0.23/0.31 | 0.369 | 0.442 | 17.73% | 79.2% |
| G16 | 81.7% | 0.63/0.33/0.43 | 0.63/0.33/0.43 | 0.665 | 0.570 | 23.46% | 50.0% |

## Per-type flag rate at 'obvious' magnitude

| type | EC03 | EC04 | EC06 | G16 |
|---|---|---|---|---|
| IN_BAND_TONE | 20% (n=5) | 40% (n=5) | 0% (n=5) | 0% (n=5) |
| SHOULDER_BUMP | 20% (n=5) | 100% (n=5) | 0% (n=4) | 20% (n=5) |
| ADJACENT_CARRIER | 100% (n=4) | 100% (n=5) | 0% (n=5) | 33% (n=3) |
| ASYMMETRIC_DISTORTION | 33% (n=3) | 0% (n=4) | 0% (n=4) | 33% (n=3) |
| BANDWIDTH_SHIFT | 0% (n=5) | 20% (n=5) | 0% (n=4) | 20% (n=5) |
| NOISE_FLOOR_RISE | 20% (n=5) | 80% (n=5) | 20% (n=5) | 40% (n=5) |
| DROPOUT | 100% (n=5) | 80% (n=5) | 100% (n=4) | 75% (n=4) |
| UNAUTHORIZED_CARRIER | 80% (n=5) | 100% (n=5) | 80% (n=5) | 100% (n=5) |