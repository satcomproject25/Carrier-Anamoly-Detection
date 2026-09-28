"""
Session 37 -- Track 2 evaluation of the PRODUCTION architecture WITH the session 36-recommended
OR-gate additions wired in: existing blended PCA+IsolationForest score OR IsolationForest-ALONE OR
per-feature independent check. Applied to all 4 stations:
  - EC03/EC06/G16: session 22/23's pooled model (16-feature), extended in-memory with the new
    if_alone_threshold/per_feature_thresholds (same monkey-patch-carrier_monitor._load_model_
    artifacts() pattern used by every pooled-model evaluation since session 24 -- no pooled-model
    artifact has ever been written to models/{station}/ for these 3 stations, and this session does
    not change that; see PROGRESS.md for the explicit reasoning).
  - EC04: its own session-29 dedicated per-source model, loaded via the DEFAULT, UNPATCHED
    carrier_monitor._load_model_artifacts() -- its thresholds.json was extended in place (session
    37's calibrate script, additive, backed up first) so the unmodified loader picks up the new
    fields automatically, no monkey-patch needed for EC04 at all.

Reuses evaluate_synthetic.py's own evaluate_source_track2()/write_report() COMPLETELY UNMODIFIED.
Writes to {source_id}_ORGATE_eval_report.md -- no existing report file touched.
"""
import os
import sys
import time

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")
from evaluate_synthetic_pooled import build_pooled_bundles  # noqa: E402
from leave_one_station_out_floor_free import NEW_SOURCE_IDS  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
import carrier_monitor  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\evaluation")
from evaluate_synthetic import evaluate_source_track2, write_report, OUT_DIR, ALL_TYPES  # noqa: E402

POOLED_STATIONS = ["EC03", "EC06", "G16"]  # EC04 uses its own on-disk dedicated model, unpatched

_ORIGINAL_LOAD_MODEL_ARTIFACTS = carrier_monitor._load_model_artifacts


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def write_summary(all_t2):
    lines = ["# Session 37 TRACK 2 -- production architecture + OR-gate (IF-alone + per-feature)\n",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "EC03/EC06/G16: session 22/23 pooled model. EC04: session 29 dedicated model. All 4 "
            "extended with session 36's OR-gate: flagged = blended_score_flagged OR IF_alone_"
            "flagged OR per_feature_flagged. Compare against session 24/29's own reports (no "
            "OR-gate) for the exact before/after this session was scoped to produce.\n"]

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

    out_path = os.path.join(OUT_DIR, "SYNTHETIC_METRICS_SUMMARY_ORGATE.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Summary written to {out_path}")


def main():
    log("Building session 22/23's pooled bundles (16-feature) for EC03/EC06/G16, extending with "
        "session 37's OR-gate thresholds...")
    bundles = build_pooled_bundles()

    import numpy as np
    sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")
    from leave_one_station_out_floor_free import FLOOR_FREE_FEATURE_COLS, load_split_rows
    RELEVANT_FEATURES = ["n_secondary_peaks_in_span", "rise_overshoot_frac_of_rise_span",
                         "fall_overshoot_frac_of_fall_span", "plateau_ripple_frac_of_plateau_range"]
    ANOMALY_PERCENTILE = 99.0

    for sid in POOLED_STATIONS:
        bundle = bundles[sid]
        th = bundle["thresholds"]
        train_df, _ = load_split_rows(sid, "train")
        X = train_df[FLOOR_FREE_FEATURE_COLS].to_numpy(dtype="float64")
        X_s = bundle["scaler"].transform(X)
        if_raw = -bundle["iso"].score_samples(X_s)
        z_if = (if_raw - th["if_score_train_mean"]) / th["if_score_train_std"]
        th["if_alone_threshold"] = float(np.percentile(z_if, ANOMALY_PERCENTILE))
        th["per_feature_thresholds"] = {
            f: float(np.percentile(train_df[f].dropna().to_numpy(dtype="float64"), ANOMALY_PERCENTILE))
            for f in RELEVANT_FEATURES
        }
        log(f"  {sid}: if_alone_threshold={th['if_alone_threshold']:.4f}, "
            f"per_feature_thresholds={th['per_feature_thresholds']}")

    def _patched(source_id):
        if source_id in POOLED_STATIONS:
            return bundles[source_id]
        return _ORIGINAL_LOAD_MODEL_ARTIFACTS(source_id)  # EC04: default loader, picks up its
                                                          # own extended, on-disk thresholds.json

    carrier_monitor._load_model_artifacts = _patched
    log("Monkey-patched carrier_monitor._load_model_artifacts for EC03/EC06/G16 only "
        "(in-memory -- no file on disk touched for these 3). EC04 uses the DEFAULT, unpatched "
        "loader, reading its already-extended on-disk thresholds.json.")

    all_t2 = []
    try:
        for source_id in NEW_SOURCE_IDS:
            t2 = evaluate_source_track2(source_id)
            write_report(f"{source_id}_ORGATE", [], t2)
            all_t2.append(t2)
    finally:
        carrier_monitor._load_model_artifacts = _ORIGINAL_LOAD_MODEL_ARTIFACTS
        log("Restored carrier_monitor._load_model_artifacts to its original implementation.")

    write_summary(all_t2)


if __name__ == "__main__":
    main()
