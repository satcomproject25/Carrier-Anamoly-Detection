# Session 38 TRACK 2 -- OR-gate recalibration attempt 'P999' (percentile=99.9, margin=None)

Generated: 2026-09-10 16:56:01

## Headline metrics per source

| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |
|---|---|---|---|---|---|---|---|
| EC03 | 90.0% | 0.86/0.28/0.42 | 0.88/0.28/0.42 | 0.371 | 0.683 | 1.11% | 86.7% |
| EC04 | 95.0% | 0.64/0.48/0.55 | 0.63/0.46/0.53 | 0.650 | 0.743 | 13.66% | 23.6% |
| EC06 | 88.3% | 0.59/0.22/0.32 | 0.59/0.22/0.32 | 0.369 | 0.442 | 11.35% | 82.6% |
| G16 | 81.7% | 0.58/0.19/0.29 | 0.56/0.18/0.28 | 0.665 | 0.570 | 17.28% | 84.2% |

## Per-type flag rate at 'obvious' magnitude

| type | EC03 | EC04 | EC06 | G16 |
|---|---|---|---|---|
| IN_BAND_TONE | 20% (n=5) | 20% (n=5) | 0% (n=5) | 0% (n=5) |
| SHOULDER_BUMP | 0% (n=5) | 80% (n=5) | 0% (n=4) | 20% (n=5) |
| ADJACENT_CARRIER | 100% (n=4) | 100% (n=5) | 0% (n=5) | 0% (n=3) |
| ASYMMETRIC_DISTORTION | 33% (n=3) | 0% (n=4) | 0% (n=4) | 0% (n=3) |
| BANDWIDTH_SHIFT | 0% (n=5) | 20% (n=5) | 0% (n=4) | 0% (n=5) |
| NOISE_FLOOR_RISE | 20% (n=5) | 80% (n=5) | 20% (n=5) | 20% (n=5) |
| DROPOUT | 100% (n=5) | 80% (n=5) | 100% (n=4) | 75% (n=4) |
| UNAUTHORIZED_CARRIER | 80% (n=5) | 100% (n=5) | 80% (n=5) | 100% (n=5) |