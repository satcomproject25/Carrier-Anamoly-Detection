# Session 24 TRACK 2 -- Pooled, transponder-blind model + per-station threshold

Generated: 2026-09-02 17:39:13

Same single pooled IsolationForest+PCA ensemble (session 22) for all 4 stations, session 21's floor-free feature set, session 23's per-station threshold calibration. Compare against SYNTHETIC_METRICS_SUMMARY_NEW_STATIONS.md (session 18 per-source models, single-day data) and SYNTHETIC_METRICS_SUMMARY.md (original 4 sources).

## Headline metrics per source

| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |
|---|---|---|---|---|---|---|---|
| EC03 | 90.0% | 0.90/0.26/0.40 | 0.93/0.26/0.41 | 0.371 | 0.683 | 0.67% | 92.9% |
| EC04 | 95.0% | 0.67/0.18/0.28 | 0.80/0.18/0.29 | 0.387 | 0.646 | 4.41% | 60.0% |
| EC06 | 88.3% | 0.55/0.22/0.31 | 0.55/0.22/0.31 | 0.369 | 0.442 | 13.48% | 82.6% |
| G16 | 81.7% | 0.58/0.19/0.29 | 0.56/0.18/0.28 | 0.665 | 0.570 | 17.28% | 84.2% |

## Per-type flag rate at 'obvious' magnitude

| type | EC03 | EC04 | EC06 | G16 |
|---|---|---|---|---|
| IN_BAND_TONE | 20% (n=5) | 0% (n=5) | 0% (n=5) | 0% (n=5) |
| SHOULDER_BUMP | 0% (n=5) | 0% (n=5) | 0% (n=4) | 20% (n=5) |
| ADJACENT_CARRIER | 100% (n=4) | 20% (n=5) | 0% (n=5) | 0% (n=3) |
| ASYMMETRIC_DISTORTION | 33% (n=3) | 0% (n=4) | 0% (n=4) | 0% (n=3) |
| BANDWIDTH_SHIFT | 0% (n=5) | 0% (n=5) | 0% (n=4) | 0% (n=5) |
| NOISE_FLOOR_RISE | 20% (n=5) | 40% (n=5) | 20% (n=5) | 20% (n=5) |
| DROPOUT | 100% (n=5) | 80% (n=5) | 100% (n=4) | 75% (n=4) |
| UNAUTHORIZED_CARRIER | 80% (n=5) | 80% (n=5) | 80% (n=5) | 100% (n=5) |