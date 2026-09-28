# Carrier Anomaly / Interference Detection Pipeline

Carrier-level anomaly detection built from three raw spectrum-analyzer capture files (different
schemas, different RF chains). Four independent per-source pipelines (A_16hr, B_ec02, B_ec05,
C_g18) — no ground-truth labels exist in any source data, so this is designed to be a fully
unsupervised pipeline once training is (re-)built. See the status banner below for exactly what
is and isn't done right now.

> ## ⚠️ Current status (2026-08-10) — READ THIS BEFORE USING ANYTHING HERE
>
> **The architecture was corrected mid-project** (2026-07-29): the original design analyzed one
> dominant peak per sweep, which turned out to be structurally wrong — real sweeps contain
> 10-32 simultaneously active carriers. The pipeline now segments and tracks EVERY carrier per
> sweep (`features/extract_features.py`'s `segment_carriers()`/`match_carriers()`), one feature
> row per **(sweep, carrier)**, not one row per sweep.
>
> | Phase | Status on the per-carrier architecture |
> |---|---|
> | 0 — Audit | Done (architecture-independent finding: no labels anywhere) |
> | 1 — Canonical ingestion | Done (architecture-independent) |
> | 2 — DSP feature extraction | **Done**, per-carrier, 4 rounds of checkpoint-verified bug fixes |
> | Interference-type diagnosis layer | **Done**, rule-based, validated — see below |
> | Synthetic interference generator | **Done** — 8 injection types, `validation/inject_interference.py`, 480-test validation matrix |
> | 3 — Leak-proof split | **Done, rebuilt 2026-08-10** for the per-carrier feature tables — `data/splits/*.json` current |
> | 4 — Model training | **Done, rebuilt 2026-08-10** — IsolationForest+PCA per source, trained on TRAIN split only, `models/{source}/*` current |
> | 5 — Held-out evaluation | **NOT DONE YET** |
> | 6 — Production inference | Rewritten and working, but **still runs the diagnosis layer UNGATED** — see below |
>
> **Phase 4 now exists and is real — but `inference/carrier_monitor.py` does not load it yet.**
> The trained models (`models/{source}/model.pkl` etc.) are current, real, and trained on the
> corrected per-carrier features — but wiring them into live inference as a proper gate for the
> diagnosis layer is separate work that hasn't happened yet. Until it does,
> `features/interference_diagnosis.py`'s `diagnose_carrier()` — a rule-based, multi-label
> interference-TYPE attribution layer — still runs **unconditionally on every tracked carrier** in
> `carrier_monitor.py`. Every live-inference result still carries a `diagnosis_layer_status` field
> stating this explicitly — that field remains accurate for now, but will need updating once the
> Phase 4 score is wired in as a real gate. **This is provisional by design, not a finished
> production system.** Next real step: Phase 5 evaluation (real + synthetic metrics), and wiring
> Phase 4's score into `carrier_monitor.py`. See `PROGRESS.md`'s own standing banner for the same
> note, kept in sync with this one.

## Quick facts

- **No labels anywhere.** Despite "_labeled" in the source filenames, that refers only
  to human-readable row/column headers, not classification ground truth (Phase 0
  audit, confirmed by reading the conversion script + an exhaustive keyword scan).
- **4 sources, kept separate, never merged.** Different absolute power levels, gain
  settings, and (for A/B) no real frequency axis or timestamps at all — confirmed by
  the (now-superseded) old-architecture Phase 4 cross-dataset generalization test, which showed
  near-total failure (~100% false-flag rate) when a model trained on one source scored another.
  Expected to hold again once Phase 4 is rebuilt, not yet re-verified on the new architecture.
- **C_g18 is the only source with real timestamps/frequency axis.** A_16hr, B_ec02,
  B_ec05 use bin-index and sweep-order-only (ordinal) features throughout — this is a
  deliberate, data-driven decision (Phase 0 found no timestamp data anywhere for those
  3 sources, not in the labeled Excel files or the raw `.mat` originals), not an
  oversight.
- **Unit of analysis is (sweep, carrier), not sweep.** Every sweep is segmented into its
  individually-tracked carriers (persistent IDs survive across sweeps, with a grace-period
  reclaim mechanism for carriers that briefly drop below the detection threshold — see
  PROGRESS.md's B_ec05 carrier-churn investigation). Every feature, and the diagnosis layer, is
  computed per carrier.

## Folder map

```
Carrier_Detection/
├── PROGRESS.md              <- session continuity log — READ THIS FIRST, every session (has its own status banner)
├── audit/                   <- Phase 0: schema/label/anomaly audit of the 3 raw workbooks
│   ├── audit_workbooks.py
│   └── audit_report.md
├── ingestion/                <- Phase 1: raw Excel -> canonical .npz per source
│   └── canonical_loader.py
├── features/                 <- Phase 2 (per-carrier) + the diagnosis layer — SHARED module, training AND inference import these
│   ├── extract_features.py          <- segmentation, tracking, per-carrier feature extraction
│   ├── interference_diagnosis.py    <- rule-based interference-TYPE attribution (diagnose_carrier())
│   └── segmentation_checkpoint/     <- one-off visual verification artifacts (not production code)
├── data/
│   ├── canonical/{source_id}.npz            <- Phase 1 output
│   ├── features/{source_id}_features.parquet         <- Phase 2 output, ONE ROW PER (sweep, carrier)
│   ├── features/{source_id}_carrier_events.parquet   <- appeared/reappeared/disappeared event log
│   └── splits/{source_id}_split.json         <- Phase 3 output, REBUILT 2026-08-10 for per-carrier
│                                                 data — blocks are SWEEP-index ranges; every carrier
│                                                 in a sweep shares that sweep's split assignment
├── utils/                    <- Phase 3, rebuilt 2026-08-10 for per-carrier data
│   ├── build_splits.py       <- true n_sweeps from canonical .npz; ACF computed on the per-sweep
│   │                            MEAN cn_db across all carriers (not a raw per-carrier column,
│   │                            which isn't a single time series once multiple carriers share a
│   │                            sweep_index)
│   └── verify_no_leakage.py  <- unchanged — always operated on sweep-index block ranges already
├── models/{source_id}/       <- Phase 4 output, REBUILT 2026-08-10 — IsolationForest+PCA per
│   │                            source, trained on the per-carrier feature tables (TRAIN split
│   │                            only). NOT YET loaded by carrier_monitor.py (separate work).
│   └── train_models.py
├── validation/                <- Synthetic interference generator + (planned) visualization tools
│   ├── inject_interference.py       <- 8 injection types, magnitude scaled from each source's own stats
│   └── INJECTION_VALIDATION_RESULTS.csv  <- 480-test validation matrix (8 types x 3 magnitudes x 4 sources x 5 repeats)
├── evaluation/                <- STALE — Phase 5 output for the OLD single-peak architecture only;
│                                  not yet rebuilt for per-carrier data
│   ├── evaluate_model.py
│   ├── {source_id}_eval_report.md
│   └── {source_id}_plots/
└── inference/                 <- Phase 6: production module, REWRITTEN 2026-08-07 for per-carrier
    ├── carrier_monitor.py     <- RawSweepInput + CarrierAnomalyDetector, streams per-carrier results
    ├── test_live_replay.py    <- streaming-vs-batch exact-match verification + fallback/width-downgrade demos
    ├── logs/unmatched_source_events.jsonl
    └── REPLAY_SUMMARY.md
```

Source data lives outside this project, at `D:\Dhyan\VK\` — only the `_labeled.xlsx`
files are ever read (never the `.mat` originals, per explicit standing instruction).

## How to resume an interrupted build

This environment has **no git** — `PROGRESS.md` plus the files actually on disk are
the only continuity mechanism across sessions. Every session should:
1. Read `PROGRESS.md` in full, including its standing status banner at the top.
2. List the actual directory contents and cross-check against what PROGRESS.md
   claims — trust disk over the log if they disagree (the log is a log, not ground
   truth; a claimed-done file that's missing or empty means it isn't actually done).
3. Resume from the next incomplete step logged there — currently: **Phase 5 evaluation (real +
   synthetic metrics), and wiring Phase 4's trained score into `carrier_monitor.py` as a gate.**

## How to retrain from scratch

**Phases 0-4 are current and safe to re-run as-is. Phase 5 (`evaluation/`) is STALE (built for
the OLD single-peak architecture) and has not been rebuilt for per-carrier data yet.**

```
python audit/audit_workbooks.py          # optional — one-time schema audit, already done
python ingestion/canonical_loader.py     # -> data/canonical/*.npz
python features/extract_features.py      # -> data/features/*.parquet (one row per sweep+carrier)
python utils/build_splits.py             # -> data/splits/*.json (sweep-index blocks)
python utils/verify_no_leakage.py        # MUST print "ALL CHECKS PASSED" before training
python models/train_models.py            # -> models/{source_id}/* (IsolationForest+PCA per source)
# --- Phase 5 below is STALE for the per-carrier architecture, do not run as-is ---
python evaluation/evaluate_model.py
```

`utils/verify_no_leakage.py` failing means something changed upstream in a way that broke
train/test separation — do not proceed to training until it passes again.
`models/train_models.py` independently re-verifies the split hash before touching any data (see
PROGRESS.md 2026-08-10) — it will hard-fail rather than silently train on a drifted split.

Once Phase 3 is redesigned/re-run and passes `verify_no_leakage.py`, Phase 4 (`train_models.py`)
also needs adapting to the new ~20-column per-carrier feature schema before it can produce a
real trained model — see the status banner at the top of this file.

`inference/test_live_replay.py` can be run any time after Phase 2 — it only depends on
`extract_features.py` + `interference_diagnosis.py` + the Phase 2 parquet files, none of which
need Phase 3-5 to exist.

## How to run live inference

```python
from inference.carrier_monitor import CarrierAnomalyDetector, RawSweepInput
import numpy as np

# locked to a known source (fastest, most confident — use this whenever you know
# which physical feed you're monitoring):
det = CarrierAnomalyDetector(source_id="C_g18")

# or auto-select across all 4 known sources (falls back to a generic reference built from the
# incoming stream's own accumulated carrier history if nothing matches confidently):
det = CarrierAnomalyDetector()

result = det.process_sweep(RawSweepInput(
    power_dbm=my_sweep_array,        # required
    freq_axis_hz=my_freq_axis,       # optional — omit for bin-index-only sources
    timestamp=np.datetime64("now"),  # optional — omit for sources with no real timestamps
))
# result = {
#   "matched_source_id": "C_g18" | None,
#   "confidence_label": str,
#   "n_carriers_detected": int,
#   "carriers": [                          # ONE ENTRY PER TRACKED CARRIER THIS SWEEP
#       {"carrier_id": int, "event": "appeared"|"reappeared"|None,
#        "peak_power_dbm": float, "cn_db": float, "occupied_bw_bins"/"_hz": float,
#        "center_bin_index"/"center_freq_hz": float,
#        "diagnosis": [{"type": "IN_BAND_INTERFERENCE"|..., "severity": "HIGH"|"MODERATE"|"LOW",
#                       "feature": str|None, "z_score": float|None, "value": ..., "note": str}, ...]},
#       ...
#   ],
#   "disappeared_carriers": [...],         # carriers whose grace period just expired this sweep
#   "diagnosis_layer_status": str,         # ALWAYS explains the "no Phase 4 score yet" provisional status
#   "latency_ms": float,
# }

# batch / streaming replay (same detector instance keeps its rolling state across calls):
results = det.process_batch([raw1, raw2, raw3, ...])
```

Production input is **always unlabeled** — `RawSweepInput` has no ground-truth field of any
kind.

### The interference-type diagnosis layer

Each carrier's `diagnosis` list can contain multiple triggered types, each with its own
severity — a carrier can simultaneously show e.g. shoulder interference AND drift. Ten types:
`IN_BAND_INTERFERENCE`, `SHOULDER_INTERFERENCE_SPECTRAL_REGROWTH`,
`ADJACENT_CHANNEL_INTERFERENCE`, `ASYMMETRIC_EDGE_DISTORTION`, `UNAUTHORIZED_CARRIER`,
`CARRIER_DROPOUT`, `CARRIER_DRIFT`, `BANDWIDTH_ANOMALY`, `NOISE_FLOOR_RISE_POSSIBLE_JAMMING`,
`GENERAL_DEGRADATION` (fallback). Each trigger explains itself: which feature was an outlier,
its z-score against that source's own training distribution (or that carrier's/source's own
rolling history for the two baseline-driven types), and the raw value.

**Known limitation, fixed for its main case**: `NOISE_FLOOR_RISE_POSSIBLE_JAMMING` can be biased
by a carrier's own width (a carrier wider than ~80% of the noise-floor estimation window can
push the local floor estimate up even with no real interference) — confirmed to matter
substantially for B_ec05 (over half its triggers were affected before the fix), negligible for
the other 3 sources. Triggers on carriers above that width fraction are automatically downgraded
to `LOW` severity with an explanatory note rather than reported at full confidence. See
PROGRESS.md 2026-08-07 for the full before/after evidence.

### Unknown-source fallback

If no known source matches confidently (checked on bin count first, then a noise-floor z-score
match), the detector does **not** force the sweep through a mismatched source's calibration —
segmentation/tracking/feature-extraction still run the same way, but the diagnosis layer's
reference distribution is built from the incoming stream's OWN accumulated carrier-observation
history instead of a trained source's. `BANDWIDTH_ANOMALY`/`NOISE_FLOOR_RISE_POSSIBLE_JAMMING`
are not available in fallback mode (no canonical noise-floor window exists for an unmatched
source) — this is stated in the result, not silently skipped. Every unmatched-source event is
logged to `inference/logs/unmatched_source_events.jsonl`.

## Verified consistency: streaming reproduces batch exactly

`test_live_replay.py` replays each source's FULL sweep sequence (full chronological order, not
just a subset — temporal/rolling features need each carrier's true immediately-preceding
observation) through a source-locked `CarrierAnomalyDetector`, then cross-checks EVERY streamed
(sweep, carrier) row against `features/extract_features.py`'s batch output
(`data/features/{source}_features.parquet` + `_carrier_events.parquet`) and
`features/interference_diagnosis.py`'s offline `diagnose_source()` — feature values, tracking
events, AND diagnosis trigger types/severities, not just an aggregate rate. As of the last
verified run:

| source | n_sweeps | rows matched | stream-only | batch-only | event mismatches | feature mismatches | diagnosis mismatches | result |
|---|---|---|---|---|---|---|---|---|
| A_16hr | 1,000 | 31,994 | 0 | 0 | 0 | 0 | 0/31,994 | PASS |
| B_ec02 | 11,520 | 334,178 | 0 | 0 | 0 | 0 | 0/333,995 | PASS |
| B_ec05 | 11,520 | 203,688 | 0 | 0 | 0 | 0 | 0/203,134 | PASS |
| C_g18 | 9,551 | 284,678 | 0 | 0 | 0 | 0 | 0/284,639 | PASS |

**All 4 sources match exactly** — zero mismatches on tracking events, every feature value (`cn_db`,
`occupied_bw_bins`, `peak_bin_index`, `noise_floor_local_dbm`), and every diagnosis trigger
type+severity, across 854,756 total (sweep, carrier) rows. `"rows matched"` exceeds the
`{source}_features.parquet` row count because it also counts each source's `disappeared` events
(which have no feature row of their own).

**Unknown-source fallback**: 10/10 B_ec02 sweeps fed to a detector restricted to A_16hr's profile
correctly fell back (`matched_source_id: None`, hard n_bins mismatch 2048 vs 4096), logged to
`inference/logs/unmatched_source_events.jsonl`.

**Width-downgrade fix, confirmed live**: B_ec05 sweep #7539's three wide carriers (bw=200/208/215
bins) correctly downgrade to LOW confidence in the streaming path — 345 downgraded / 612 kept at
full confidence across the 145-sweep replay window, identical to the offline batch validation.

**Latency** (warm): matched-source path (C_g18) mean=30.7ms, p95=42.8ms; unknown-source fallback
mean=29.3ms, p95=37.4ms.

Full detail: `inference/REPLAY_SUMMARY.md` (regenerated by `test_live_replay.py` on every run).

### A caution for anyone adding new streaming features later

This exact-match discipline has already caught THREE real bugs during development (not
hypothetical — all three actually shipped and were caught here, not elsewhere):
1. **(Original, single-peak architecture) A `ddof` mismatch**: streaming used `np.std()`
   (population std, `ddof=0`) for a rolling feature while Phase 2's batch training used pandas'
   `.rolling().std()` (sample std, `ddof=1` by default) — silently shifted the combined anomaly
   score on nearly every sweep and occasionally flipped a borderline flag decision. Only caught
   because the replay checked exact values, not aggregate rates.
2. **(Per-carrier architecture, 2026-08-07) A float32-vs-float64 precision mismatch**: the
   rewritten streaming path cast incoming `power_dbm` to `float64`, while Phase 2's batch driver
   reads sweeps directly out of the `float32` canonical `.npz` with no upcast — a ~1e-5 dB
   drift on every feature, invisible at any reasonable rounding but a real divergence between
   training and inference precision. Fixed by casting to `float32` in `carrier_monitor.py` to
   match the canonical storage dtype exactly. Caught immediately by this same exact-match check.
3. **(Per-carrier architecture, 2026-08-07) A near-zero-variance z-score blow-up**: for a carrier
   whose bandwidth stayed exactly constant across its whole rolling window, the true std is
   effectively zero — but pandas' `.rolling().std()` (offline batch) and a plain numpy
   `.std(ddof=1)` over a materialized deque (streaming) aren't bit-identical algorithms, so one
   path could land on exactly `0.0` (correctly suppressed by a `std<=0` guard) while the other
   landed on a tiny positive floating-point epsilon (NOT caught by that guard) — producing a
   z-score of **11,445,408** for a 1-bin bandwidth change in one path and a suppressed `NaN` in
   the other. Fixed with a minimum-std floor (`MIN_BANDWIDTH_STD_BINS=1.0`,
   `MIN_NOISE_FLOOR_STD_DB=0.05` in `interference_diagnosis.py`) so a real but small change
   produces a bounded, sane z-score instead of an uninterpretable spike in either path. Same bug
   *class* as the zero-inflation issue already fixed in the diagnosis layer's source-distribution
   checks (`n_secondary_peaks_in_span` etc.) — near-zero variance/mass breaks naive z-scoring the
   same way regardless of which caused the near-zero denominator.

**Any new rolling/temporal statistic or dtype choice added to `carrier_monitor.py` or
`interference_diagnosis.py` must match its batch-training equivalent exactly** (estimator,
window edge inclusion, floating-point precision) AND **must have a minimum-variance floor if it
feeds a z-score** — visual resemblance to the training-time formula is not enough; re-run
`test_live_replay.py` after any such change.

## Documented limitations (historical — from the OLD single-peak architecture's Phase 5, superseded)

These findings predate the 2026-07-29 architecture correction and describe the OLD model. Kept
here for historical continuity only — they do not describe the current (Phase 4-less)
per-carrier pipeline, and should be re-derived once Phase 4 is rebuilt on the corrected features.

**C_g18 sweep #4247-4497 — unverified spectral-shape anomaly.** The old model flagged a tight
cluster of sweeps in this ~62-minute window. The instrument's own fixed-band CN_g18 metric
showed no difference between flagged and passed sweeps (21.52dB vs 21.43dB mean) — plausibly a
genuine bandwidth/shape-related deviation the scalar instrument metric wouldn't catch, never
confirmed against a domain/ops log either way.

**B_ec02 — coarse block-based test split, high-variance metrics.** Only 10 independent
train/val/test blocks existed under the old architecture (C/N autocorrelation never decorrelated
within the search window — genuine slow drift over the 50-hour capture, not a bug). Will need
re-deriving once Phase 3 is rebuilt for per-carrier data; may or may not recur with the new
feature set.

## Pipeline history (summary — see PROGRESS.md for full detail)

| Phase | What | Status | Key finding |
|---|---|---|---|
| 0 | Audit 3 raw workbooks | Done | No labels anywhere; only C_g18 has real timestamps/freq axis |
| 1 | Canonical `.npz` per source | Done | 4 sources, kept separate; C_g18 gets verified `delta_t` |
| 2 (v1) | DSP feature extraction, single-peak | Superseded | Real sweeps have 10-32 simultaneous carriers — the single-peak unit of analysis was structurally wrong |
| — | **Architecture correction** | Done | Per-carrier segmentation (`segment_carriers()`), IoU tracking with grace-period reclaim, per-carrier feature set — 4 rounds of checkpoint-verified bug fixes (floor contamination, duplicate spans, carrier-churn flicker, rise/plateau/fall split) |
| 2 (v2) | DSP feature extraction, per-carrier | **Done** | One row per (sweep, carrier); local-floor C/N redesign tightened C_g18's C/N correlation vs. instrument ground truth from r=0.945/-11.65dB bias to r=0.995/+0.32dB |
| — | Interference-type diagnosis layer | **Done** | Rule-based multi-label attribution (`diagnose_carrier()`); found + fixed a naive-mean/std bug on zero-inflated features and a carrier-width bias in NOISE_FLOOR_RISE |
| — | Synthetic interference generator | **Done, 2026-08-10** | 8 injection types (`validation/inject_interference.py`), magnitude scaled from each source's own stats; 480-test validation matrix; found + fixed 6 real bugs in injection mechanics/test harness |
| 3 | Leak-proof train/val/test split | **Rebuilt 2026-08-10** | Blocking moved to the sweep level (true `n_sweeps`, ACF on per-sweep mean `cn_db`); found + fixed a latent trailing-remainder-block bug that gave C_g18 an 11-sweep val set; B_ec05 now shows the same coarse slow-drift blocking as B_ec02 once carrier-level noise is averaged out |
| 4 | Unsupervised model training | **Rebuilt 2026-08-10** | IsolationForest+PCA per source on the per-carrier features; cross-generalization re-confirms source-aware models are necessary (diagonal 0.16-0.93%, off-diagonal mostly 100%, a few partial 15-72% — real, not the old report reasserted unchecked) |
| 5 | Held-out test evaluation | **NOT DONE yet** | Next step — real + synthetic (injection-based) metrics |
| 6 | Production inference module | **Rewritten 2026-08-07** | Streaming verified to exactly reproduce batch feature values/events/diagnosis on all 4 sources (see above); diagnosis layer still runs ungated — Phase 4 exists now but isn't wired in as a gate yet |
