"""
Session 34 -- Track 2 evaluation of the pooled model with bw_ratio_to_recent_median added as a
17th feature, across all 4 stations (EC03/EC04/EC06/G16), same per-station threshold calibration
principle as session 23.

Reuses evaluate_synthetic.py's own evaluate_source_track2()/write_report() COMPLETELY UNMODIFIED,
via the same monkey-patch-carrier_monitor._load_model_artifacts() technique as
evaluate_synthetic_pooled.py (session 24) -- no file on disk read/written/overwritten by the
substitution, models/{station}/ per-source bundles untouched, session 24's own
{source_id}_POOLED_eval_report.md untouched (writes to {source_id}_BWRATIO_eval_report.md).
"""
import os
import sys
import time

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")
from pooled_bw_ratio import build_pooled_bwratio_bundles  # noqa: E402
from leave_one_station_out_floor_free import NEW_SOURCE_IDS  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
import carrier_monitor  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\evaluation")
from evaluate_synthetic import evaluate_source_track2, write_report, OUT_DIR, ALL_TYPES  # noqa: E402

_ORIGINAL_LOAD_MODEL_ARTIFACTS = carrier_monitor._load_model_artifacts


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def write_summary(all_t2):
    lines = ["# Session 34 TRACK 2 -- Pooled model + bw_ratio_to_recent_median (17th feature)\n",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "Same IsolationForest+PCA architecture, same pooled TRAIN, same per-station p99 "
            "threshold calibration (session 23) as session 22-31's 16-feature pooled model -- "
            "ONLY change is the addition of bw_ratio_to_recent_median (occupied_bw_bins / rolling "
            "median of the last 100 carrier observations on that stream, population-level, no "
            "absolute value, no station identity). Compare against SYNTHETIC_METRICS_SUMMARY_"
            "POOLED_NEW_STATIONS.md (session 24, 16-feature version).\n"]

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

    out_path = os.path.join(OUT_DIR, "SYNTHETIC_METRICS_SUMMARY_BWRATIO.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Summary written to {out_path}")


def main():
    log("Building session 34's pooled 17-feature (bw_ratio) ensemble + per-station thresholds...")
    bundles, _ = build_pooled_bwratio_bundles()

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
            write_report(f"{source_id}_BWRATIO", [], t2)
            all_t2.append(t2)
    finally:
        carrier_monitor._load_model_artifacts = _ORIGINAL_LOAD_MODEL_ARTIFACTS
        log("Restored carrier_monitor._load_model_artifacts to its original implementation.")

    write_summary(all_t2)


if __name__ == "__main__":
    main()
