# Session 32 TRACK 2 -- Pooled ensemble with autoencoder replacing PCA

Generated: 2026-09-07 19:55:07

IsolationForest half UNCHANGED from session 22; PCA-reconstruction-error half replaced by a sparsity-weighted-loss MLPRegressor autoencoder. Same 16 floor-free features, same pooled TRAIN, same per-station p99 threshold calibration (session 23). Compare against SYNTHETIC_METRICS_SUMMARY_POOLED_NEW_STATIONS.md (session 24, PCA version) and EC04/G16's own dedicated per-source models (session 29).

## Headline metrics per source

| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |
|---|---|---|---|---|---|---|---|
| EC03 | 90.0% | 0.91/0.28/0.43 | 1.00/0.28/0.43 | 0.438 | 0.709 | 0.67% | 93.3% |
| EC04 | 95.0% | 0.70/0.18/0.29 | 0.78/0.18/0.30 | 0.399 | 0.650 | 3.96% | 57.1% |
| EC06 | 88.3% | 0.68/0.28/0.40 | 0.70/0.28/0.40 | 0.460 | 0.507 | 9.93% | 86.7% |
| G16 | 81.7% | 0.64/0.29/0.39 | 0.61/0.26/0.36 | 0.717 | 0.612 | 19.75% | 82.1% |

## Per-type flag rate at 'obvious' magnitude

| type | EC03 | EC04 | EC06 | G16 |
|---|---|---|---|---|
| IN_BAND_TONE | 20% (n=5) | 0% (n=5) | 0% (n=5) | 0% (n=5) |
| SHOULDER_BUMP | 0% (n=5) | 0% (n=5) | 0% (n=4) | 20% (n=5) |
| ADJACENT_CARRIER | 75% (n=4) | 40% (n=5) | 0% (n=5) | 33% (n=3) |
| ASYMMETRIC_DISTORTION | 33% (n=3) | 0% (n=4) | 0% (n=4) | 0% (n=3) |
| BANDWIDTH_SHIFT | 0% (n=5) | 0% (n=5) | 0% (n=4) | 0% (n=5) |
| NOISE_FLOOR_RISE | 80% (n=5) | 40% (n=5) | 60% (n=5) | 80% (n=5) |
| DROPOUT | 100% (n=5) | 80% (n=5) | 100% (n=4) | 75% (n=4) |
| UNAUTHORIZED_CARRIER | 80% (n=5) | 80% (n=5) | 80% (n=5) | 100% (n=5) |