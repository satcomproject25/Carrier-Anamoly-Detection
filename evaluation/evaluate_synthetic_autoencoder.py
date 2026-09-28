"""
Session 32 -- Track 2 evaluation of the pooled AUTOENCODER ensemble (IsolationForest unchanged +
MLPRegressor-based, sparsity-weighted-loss autoencoder replacing PCA) across all 4 stations
(EC03/EC04/EC06/G16), same per-station threshold calibration principle as session 23.

Reuses evaluate_synthetic.py's own evaluate_source_track2()/write_report() COMPLETELY UNMODIFIED,
via the same monkey-patch-carrier_monitor._load_model_artifacts() technique as
evaluate_synthetic_pooled.py (session 24) -- no file on disk read/written/overwritten by the
substitution, models/{station}/ per-source bundles untouched, session 24's own
{source_id}_POOLED_eval_report.md untouched (this writes to {source_id}_AUTOENCODER_eval_report.md).
"""
import os
import sys
import time

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")
from pooled_autoencoder import build_pooled_autoencoder_bundles  # noqa: E402
from leave_one_station_out_floor_free import NEW_SOURCE_IDS  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
import carrier_monitor  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\evaluation")
from evaluate_synthetic import evaluate_source_track2, write_report, OUT_DIR, ALL_TYPES  # noqa: E402

_ORIGINAL_LOAD_MODEL_ARTIFACTS = carrier_monitor._load_model_artifacts


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def write_summary(all_t2):
    lines = ["# Session 32 TRACK 2 -- Pooled ensemble with autoencoder replacing PCA\n",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "IsolationForest half UNCHANGED from session 22; PCA-reconstruction-error half "
            "replaced by a sparsity-weighted-loss MLPRegressor autoencoder. Same 16 floor-free "
            "features, same pooled TRAIN, same per-station p99 threshold calibration (session 23). "
            "Compare against SYNTHETIC_METRICS_SUMMARY_POOLED_NEW_STATIONS.md (session 24, PCA "
            "version) and EC04/G16's own dedicated per-source models (session 29).\n"]

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

    out_path = os.path.join(OUT_DIR, "SYNTHETIC_METRICS_SUMMARY_AUTOENCODER.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Summary written to {out_path}")


def main():
    log("Building session 32's pooled autoencoder ensemble + per-station thresholds...")
    bundles, _ = build_pooled_autoencoder_bundles()

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
            write_report(f"{source_id}_AUTOENCODER", [], t2)
            all_t2.append(t2)
    finally:
        carrier_monitor._load_model_artifacts = _ORIGINAL_LOAD_MODEL_ARTIFACTS
        log("Restored carrier_monitor._load_model_artifacts to its original implementation.")

    write_summary(all_t2)


if __name__ == "__main__":
    main()
