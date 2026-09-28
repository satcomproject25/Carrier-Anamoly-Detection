# Session 34 TRACK 2 -- Pooled model + bw_ratio_to_recent_median (17th feature)

Generated: 2026-09-08 19:59:13

Same IsolationForest+PCA architecture, same pooled TRAIN, same per-station p99 threshold calibration (session 23) as session 22-31's 16-feature pooled model -- ONLY change is the addition of bw_ratio_to_recent_median (occupied_bw_bins / rolling median of the last 100 carrier observations on that stream, population-level, no absolute value, no station identity). Compare against SYNTHETIC_METRICS_SUMMARY_POOLED_NEW_STATIONS.md (session 24, 16-feature version).

## Headline metrics per source

| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |
|---|---|---|---|---|---|---|---|
| EC03 | 90.0% | 0.88/0.26/0.40 | 0.97/0.26/0.41 | 0.369 | 0.689 | 0.89% | 92.9% |
| EC04 | 95.0% | 0.65/0.18/0.28 | 0.77/0.18/0.29 | 0.383 | 0.636 | 4.85% | 60.0% |
| EC06 | 88.3% | 0.59/0.22/0.32 | 0.59/0.22/0.32 | 0.364 | 0.449 | 11.35% | 82.6% |
| G16 | 81.7% | 0.56/0.22/0.32 | 0.57/0.21/0.31 | 0.653 | 0.552 | 20.99% | 86.4% |

## Per-type flag rate at 'obvious' magnitude

| type | EC03 | EC04 | EC06 | G16 |
|---|---|---|---|---|
| IN_BAND_TONE | 20% (n=5) | 0% (n=5) | 0% (n=5) | 0% (n=5) |
| SHOULDER_BUMP | 0% (n=5) | 0% (n=5) | 0% (n=4) | 20% (n=5) |
| ADJACENT_CARRIER | 100% (n=4) | 20% (n=5) | 0% (n=5) | 0% (n=3) |
| ASYMMETRIC_DISTORTION | 33% (n=3) | 0% (n=4) | 0% (n=4) | 0% (n=3) |
| BANDWIDTH_SHIFT | 0% (n=5) | 0% (n=5) | 0% (n=4) | 0% (n=5) |
| NOISE_FLOOR_RISE | 20% (n=5) | 40% (n=5) | 20% (n=5) | 40% (n=5) |
| DROPOUT | 100% (n=5) | 80% (n=5) | 100% (n=4) | 75% (n=4) |
| UNAUTHORIZED_CARRIER | 80% (n=5) | 80% (n=5) | 80% (n=5) | 100% (n=5) |