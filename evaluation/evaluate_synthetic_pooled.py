"""
Session 24 -- Track 2 (real synthetic-injection precision/recall/F1/PR-AUC/ROC-AUC/FPR) for the
FINAL validated architecture from sessions 19-23: session 22's single pooled, transponder-blind
IsolationForest+PCA ensemble (fit on all 4 stations' TRAIN carriers combined, session 21's
floor-free/internally-referenced feature set, station identity never used as a feature) combined
with session 23's per-station threshold calibration (each station's own p99 of the pooled model's
scores on that station's own TRAIN data).

Reuses evaluate_synthetic.py's own evaluate_source_track2()/write_report() COMPLETELY UNMODIFIED --
these already drive everything (injection, negative sampling, scoring, diagnosis, metrics) through
carrier_monitor.CarrierAnomalyDetector, which loads its per-source model bundle via the MODULE-LEVEL
function carrier_monitor._load_model_artifacts(source_id). Rather than touching carrier_monitor.py
or overwriting the existing models/{source_id}/ bundle files on disk (which back the session-18
per-source Track 2 numbers this session compares against -- those must not be disturbed), this
script MONKEY-PATCHES that one function, in-memory only, for the duration of this run: for
EC03/EC04/EC06/G16 it returns the pooled model + that station's own calibrated threshold instead of
reading a per-source bundle from disk; every other source_id falls through to the original,
unpatched loader. No file on disk is read, written, or overwritten by this substitution.

Rebuilds the EXACT session-22/23 pooled model deterministically (same fixed SEED, same pooled
TRAIN input, via leave_one_station_out_floor_free.py's own fit_ensemble()) and the exact
session-23 per-station thresholds (via pooled_per_station_threshold.py's own combined_scores()) --
both reused unmodified, not recomputed with new logic.

Writes to {source_id}_POOLED_eval_report.md (NOT {source_id}_eval_report.md) so session 18's
existing per-source reports for these 4 stations are never overwritten.

Run standalone: `python evaluate_synthetic_pooled.py`
"""
import os
import sys
import time
import numpy as np
import pandas as pd

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")
from leave_one_station_out_floor_free import (  # noqa: E402
    FLOOR_FREE_FEATURE_COLS, load_split_rows, fit_ensemble, NEW_SOURCE_IDS, ANOMALY_PERCENTILE,
    ENSEMBLE_WEIGHTS,
)
from pooled_per_station_threshold import combined_scores  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
import carrier_monitor  # noqa: E402 -- imported as a MODULE so its function can be monkey-patched

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\evaluation")
from evaluate_synthetic import evaluate_source_track2, write_report, OUT_DIR, ALL_TYPES  # noqa: E402

_ORIGINAL_LOAD_MODEL_ARTIFACTS = carrier_monitor._load_model_artifacts


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_pooled_bundles():
    """Rebuilds session 22's pooled model + session 23's per-station thresholds, byte-identical
    to those sessions (same fixed SEED, same pooled TRAIN input, same fit_ensemble()/
    combined_scores() code, unmodified). Returns {station: bundle_dict} in EXACTLY the shape
    carrier_monitor._load_model_artifacts() normally returns, so _score_carrier() needs zero
    changes to consume it."""
    train_rows = {}
    for sid in NEW_SOURCE_IDS:
        train_rows[sid], n_raw = load_split_rows(sid, "train")
        log(f"  {sid}: train {n_raw} -> {len(train_rows[sid])} post-dropna")

    pooled_train = pd.concat([train_rows[s] for s in NEW_SOURCE_IDS], ignore_index=True)
    model = fit_ensemble(pooled_train.to_numpy(dtype="float64"))
    log(f"  pooled model: PCA {model['pca_n_components']} components, "
        f"global threshold(p{ANOMALY_PERCENTILE})={model['threshold']:.4f} (session 22's own value)")

    bundles = {}
    for sid in NEW_SOURCE_IDS:
        train_scores = combined_scores(model, train_rows[sid].to_numpy(dtype="float64"))
        station_threshold = float(np.percentile(train_scores, ANOMALY_PERCENTILE))
        log(f"  {sid}: own-train p{ANOMALY_PERCENTILE} threshold={station_threshold:.4f} "
            f"(session 23's own value)")
        bundles[sid] = {
            "iso": model["iso"], "pca": model["pca"], "scaler": model["scaler"],
            "feature_cols": FLOOR_FREE_FEATURE_COLS,
            "thresholds": {
                "combined_score_threshold": station_threshold,
                "if_score_train_mean": model["if_mean"], "if_score_train_std": model["if_std"],
                "pca_error_train_mean": model["pca_mean"], "pca_error_train_std": model["pca_std"],
                "ensemble_weights": ENSEMBLE_WEIGHTS,
            },
        }
    return bundles


def write_summary(all_t2):
    lines = ["# Session 24 TRACK 2 -- Pooled, transponder-blind model + per-station threshold\n",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "Same single pooled IsolationForest+PCA ensemble (session 22) for all 4 stations, "
            "session 21's floor-free feature set, session 23's per-station threshold calibration. "
            "Compare against SYNTHETIC_METRICS_SUMMARY_NEW_STATIONS.md (session 18 per-source "
            "models, single-day data) and SYNTHETIC_METRICS_SUMMARY.md (original 4 sources).\n"]

    lines.append("## Headline metrics per source\n")
    lines.append("| source | coverage | score-alone P/R/F1 | combined P/R/F1 | PR-AUC | ROC-AUC | FPR | type-attrib acc |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for t2 in all_t2:
        m = t2["metrics"]
        pr_auc = f"{m['pr_auc']:.3f}" if m['pr_auc'] is not None else "n/a"
        roc_auc = f"{m['roc_auc']:.3f}" if m['roc_auc'] is not None else "n/a"
        tacc = f"{m['type_attribution_accuracy']*100:.1f}%" if m['type_attribution_accuracy'] is not None else "n/a"
        lines.append(f"| {t2['source_id']} | {m['coverage']*100:.1f}% | "
                     f"{m['score_alone_precision']:.2f}/{m['score_alone_recall']:.2f}/{m['score_alone_f1']:.2f} | "
                     f"{m['combined_precision']:.2f}/{m['combined_recall']:.2f}/{m['combined_f1']:.2f} | "
                     f"{pr_auc} | {roc_auc} | {m['false_positive_rate']*100:.2f}% | {tacc} |")
    lines.append("")

    lines.append("## Per-type flag rate at 'obvious' magnitude\n")
    lines.append("| type | " + " | ".join(t2["source_id"] for t2 in all_t2) + " |")
    lines.append("|---|" + "---|" * len(all_t2))
    for typ in ALL_TYPES:
        cells = []
        for t2 in all_t2:
            tls = t2["type_level_summary"]
            try:
                row = tls.loc[(typ, "obvious")]
                rate = row["n_flagged"] / row["count"] if row["count"] else 0
                cells.append(f"{rate*100:.0f}% (n={int(row['count'])})")
            except KeyError:
                cells.append("n/a")
        lines.append(f"| {typ} | " + " | ".join(cells) + " |")

    out_path = os.path.join(OUT_DIR, "SYNTHETIC_METRICS_SUMMARY_POOLED_NEW_STATIONS.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Summary written to {out_path}")


def main():
    log("Rebuilding session 22/23's pooled model + per-station thresholds (unmodified logic)...")
    bundles = build_pooled_bundles()

    def _patched(source_id):
        if source_id in bundles:
            return bundles[source_id]
        return _ORIGINAL_LOAD_MODEL_ARTIFACTS(source_id)

    carrier_monitor._load_model_artifacts = _patched
    log("Monkey-patched carrier_monitor._load_model_artifacts for EC03/EC04/EC06/G16 only "
        "(in-memory only -- no file on disk touched, models/{station}/ bundles untouched).")

    all_t2 = []
    try:
        for source_id in NEW_SOURCE_IDS:
            t2 = evaluate_source_track2(source_id)
            write_report(f"{source_id}_POOLED", [], t2)
            all_t2.append(t2)
    finally:
        carrier_monitor._load_model_artifacts = _ORIGINAL_LOAD_MODEL_ARTIFACTS
        log("Restored carrier_monitor._load_model_artifacts to its original implementation.")

    write_summary(all_t2)


if __name__ == "__main__":
    main()
