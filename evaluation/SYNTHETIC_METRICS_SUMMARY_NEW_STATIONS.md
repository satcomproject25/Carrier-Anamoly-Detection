# Stage 2c TRACK 2 — Synthetic Metrics Summary (new stations)

Generated: 2026-08-25 18:42:09

## Headline metrics per source

| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |
|---|---|---|---|---|---|---|---|
| EC03 | 96.7% | 0.88/0.19/0.31 | 0.88/0.18/0.30 | 0.460 | 0.762 | 0.67% | 90.9% |
| EC04 | 85.0% | 0.93/0.36/0.52 | 0.94/0.29/0.45 | 0.806 | 0.857 | 1.42% | 45.9% |
| EC06 | 93.3% | 0.47/0.23/0.31 | 0.47/0.23/0.31 | n/a | n/a | 16.67% | 61.5% |
| G16 | 60.0% | 1.00/0.17/0.29 | 1.00/0.17/0.29 | n/a | n/a | 0.00% | 100.0% |

## Per-type flag rate at 'obvious' magnitude, across all 4 new stations

| type | EC03 | EC04 | EC06 | G16 |
|---|---|---|---|---|
| IN_BAND_TONE | 0% (n=5) | 40% (n=5) | 20% (n=5) | 0% (n=5) |
| SHOULDER_BUMP | 20% (n=5) | 50% (n=4) | 0% (n=5) | 0% (n=2) |
| ADJACENT_CARRIER | 20% (n=5) | 75% (n=4) | 40% (n=5) | 0% (n=2) |
| ASYMMETRIC_DISTORTION | 20% (n=5) | 67% (n=3) | 20% (n=5) | 0% (n=2) |
| BANDWIDTH_SHIFT | 0% (n=5) | 0% (n=5) | 0% (n=5) | 0% (n=5) |
| NOISE_FLOOR_RISE | 0% (n=5) | 40% (n=5) | 0% (n=5) | n/a |
| DROPOUT | 100% (n=5) | 80% (n=5) | 75% (n=4) | 100% (n=4) |
| UNAUTHORIZED_CARRIER | 80% (n=5) | 80% (n=5) | 100% (n=5) | 60% (n=5) |