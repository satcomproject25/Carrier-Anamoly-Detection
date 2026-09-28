# Session 38 TRACK 2 -- OR-gate recalibration attempt 'M050' (percentile=99.0, margin=0.5)

Generated: 2026-09-10 22:29:48

## Headline metrics per source

| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |
|---|---|---|---|---|---|---|---|
| EC03 | 90.0% | 0.78/0.26/0.39 | 0.78/0.26/0.39 | 0.371 | 0.683 | 1.78% | 92.9% |
| EC04 | 95.0% | 0.85/0.34/0.49 | 0.85/0.34/0.49 | 0.650 | 0.743 | 3.08% | 33.3% |
| EC06 | 88.3% | 0.55/0.23/0.32 | 0.55/0.23/0.32 | 0.369 | 0.442 | 14.18% | 79.2% |
| G16 | 81.7% | 0.59/0.24/0.35 | 0.59/0.24/0.35 | 0.665 | 0.570 | 20.99% | 66.7% |

## Per-type flag rate at 'obvious' magnitude

| type | EC03 | EC04 | EC06 | G16 |
|---|---|---|---|---|
| IN_BAND_TONE | 20% (n=5) | 20% (n=5) | 0% (n=5) | 0% (n=5) |
| SHOULDER_BUMP | 0% (n=5) | 80% (n=5) | 0% (n=4) | 20% (n=5) |
| ADJACENT_CARRIER | 100% (n=4) | 100% (n=5) | 0% (n=5) | 33% (n=3) |
| ASYMMETRIC_DISTORTION | 33% (n=3) | 0% (n=4) | 0% (n=4) | 0% (n=3) |
| BANDWIDTH_SHIFT | 0% (n=5) | 0% (n=5) | 0% (n=4) | 0% (n=5) |
| NOISE_FLOOR_RISE | 20% (n=5) | 40% (n=5) | 20% (n=5) | 40% (n=5) |
| DROPOUT | 100% (n=5) | 80% (n=5) | 100% (n=4) | 75% (n=4) |
| UNAUTHORIZED_CARRIER | 80% (n=5) | 80% (n=5) | 80% (n=5) | 100% (n=5) |