"""
Session 38 -- recalibration harness for session 37's OR-gate (IsolationForest-alone +
per-feature independent threshold), attempting to close the severe FPR regression session 37's
full Track 2 run found, while preserving the real recall gains on IN_BAND_TONE/SHOULDER_BUMP/
ADJACENT_CARRIER. Two independent knobs, both optional and CLI-driven so no code edit is needed
between attempts:

  --percentile P     calibrate if_alone_threshold/per_feature_thresholds at P instead of session
                     37's 99.0 (try 99.9 first, per the user's own ordering: cheapest to test).
  --margin M         session 38's NEW `or_gate_score_margin_frac` gate in carrier_monitor.py's
                     `_or_gate_check()`: skip both checks entirely unless the carrier's own
                     blended score is already >= M * its own blended threshold. Omit for no gate
                     (matches session 37's unconditional behavior at whatever --percentile is set).

Deliberately does NOT touch models/EC04/thresholds.json on disk (unlike session 37's calibrate
script) -- ALL 4 stations, including EC04, are monkey-patched in-memory for the duration of this
run only, so repeated recalibration attempts never mutate a production file until/unless a config
is actually chosen for adoption. EC04's blended-score thresholds (the original 9 keys) are read
from its on-disk thresholds.json unchanged; only the two OR-gate keys (plus the new margin key)
are computed fresh in-memory each run.

Reuses evaluate_synthetic.py's own collect_positive_examples()/collect_negative_examples()/
compute_metrics()/confusion_matrix_by_type()/per_type_level_summary()/write_report() COMPLETELY
UNMODIFIED -- only the outer orchestration (evaluate_source_track2) is reimplemented here, to add
a disk checkpoint after each of the two collection phases (session 38 addition, prompted by a real
interruption: neither evaluate_synthetic.py nor session 37's harness persisted anything to disk
until the very end of a station's run, so a killed process anywhere in a 2-4 hour run loses ALL of
it -- positive attempts AND negative examples alike, with no way to resume). Checkpoints are
tag-scoped (`_checkpoints/{source_id}_{tag}_{phase}.pkl`) so different recalibration attempts never
collide, and a re-run with the SAME tag after an interruption skips whichever phase(s) already
completed rather than redoing them.
Writes to {source_id}_ORGATE_{tag}_eval_report.md -- no existing report file touched.
"""
import argparse
import json
import os
import sys
import time

import joblib
import numpy as np

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")
from evaluate_synthetic_pooled import build_pooled_bundles  # noqa: E402
from leave_one_station_out_floor_free import (FLOOR_FREE_FEATURE_COLS, load_split_rows,  # noqa: E402
                                              NEW_SOURCE_IDS)
from train_models import load_source, rows_for_split  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
import carrier_monitor  # noqa: E402

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\evaluation")
from evaluate_synthetic import (collect_positive_examples, collect_negative_examples,  # noqa: E402
                                check_unauthorized_carrier_next_sweep, compute_metrics,
                                confusion_matrix_by_type, per_type_level_summary, write_report,
                                OUT_DIR, ALL_TYPES, N_NEGATIVE_DRAWS)

CHECKPOINT_DIR = os.path.join(OUT_DIR, "_checkpoints")
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

POOLED_STATIONS = ["EC03", "EC06", "G16"]
RELEVANT_FEATURES = ["n_secondary_peaks_in_span", "rise_overshoot_frac_of_rise_span",
                     "fall_overshoot_frac_of_fall_span", "plateau_ripple_frac_of_plateau_range"]
MODELS_DIR = r"D:\Dhyan\Carrier_Detection\models"

_ORIGINAL_LOAD_MODEL_ARTIFACTS = carrier_monitor._load_model_artifacts


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _checkpoint_path(source_id, tag, phase):
    return os.path.join(CHECKPOINT_DIR, f"{source_id}_{tag}_{phase}.pkl")


def collect_positive_examples_ckpt(source_id, tag):
    path = _checkpoint_path(source_id, tag, "pos_rows")
    if os.path.exists(path):
        rows = joblib.load(path)
        log(f"  {source_id}: RESUMED {len(rows)} positive attempts from checkpoint {path}")
        return rows
    rows = collect_positive_examples(source_id)
    joblib.dump(rows, path)
    log(f"  {source_id}: checkpointed {len(rows)} positive attempts -> {path}")
    return rows


def collect_negative_examples_ckpt(source_id, tag):
    path = _checkpoint_path(source_id, tag, "neg_rows")
    if os.path.exists(path):
        rows = joblib.load(path)
        log(f"  {source_id}: RESUMED {len(rows)} negative examples from checkpoint {path}")
        return rows
    rows = collect_negative_examples(source_id)
    joblib.dump(rows, path)
    log(f"  {source_id}: checkpointed {len(rows)} negative examples -> {path}")
    return rows


def evaluate_source_track2_ckpt(source_id, tag):
    """Reimplements evaluate_synthetic.py's own evaluate_source_track2() line-for-line, with the
    two collection phases routed through the checkpointed wrappers above. Everything downstream
    (uc_next_sweep check, compute_metrics/confusion_matrix_by_type/per_type_level_summary, the
    returned dict shape) is IDENTICAL and reuses those functions unmodified, so write_report() and
    every metric are bit-for-bit the same as the original for any run that completes uninterrupted."""
    log(f"=== {source_id} (Track 2: synthetic labeled evaluation, checkpointed, tag={tag}) ===")
    pos_rows = collect_positive_examples_ckpt(source_id, tag)
    log(f"  {len(pos_rows)} positive attempts, {sum(1 for r in pos_rows if r['outcome']=='OK')} valid (outcome=OK)")

    neg_rows = collect_negative_examples_ckpt(source_id, tag)
    log(f"  {len(neg_rows)} negative (clean) carrier examples from {N_NEGATIVE_DRAWS} draws")

    uc_rows = [r for r in pos_rows if r["type"] == "UNAUTHORIZED_CARRIER" and r["outcome"] == "OK"]
    uc_next_sweep = []
    for r in uc_rows:
        chk = check_unauthorized_carrier_next_sweep(source_id, r["level"], r["repeat"])
        if chk is not None:
            uc_next_sweep.append(chk)
    n_uc_flagged_sweep1 = sum(1 for c in uc_next_sweep if c.get("flagged_sweep1"))
    log(f"  UNAUTHORIZED_CARRIER supplementary check: {n_uc_flagged_sweep1}/{len(uc_next_sweep)} "
        f"flagged on the sweep AFTER appearing (vs. 0 possible on the appearance sweep itself, "
        f"due to NaN temporal features on first observation)")

    metrics = compute_metrics(pos_rows, neg_rows)
    confusion = confusion_matrix_by_type(pos_rows)
    type_level_summary = per_type_level_summary(pos_rows)

    log(f"  score-alone: P={metrics['score_alone_precision']:.3f} R={metrics['score_alone_recall']:.3f} "
        f"F1={metrics['score_alone_f1']:.3f} | combined: P={metrics['combined_precision']:.3f} "
        f"R={metrics['combined_recall']:.3f} F1={metrics['combined_f1']:.3f}")
    log(f"  PR-AUC={metrics['pr_auc']} ROC-AUC={metrics['roc_auc']} "
        f"FPR={metrics['false_positive_rate']:.4f} type_attribution_acc={metrics['type_attribution_accuracy']}")

    return {
        "source_id": source_id, "pos_rows": pos_rows, "neg_rows": neg_rows, "metrics": metrics,
        "confusion": confusion, "type_level_summary": type_level_summary,
        "uc_next_sweep": uc_next_sweep, "n_uc_flagged_sweep1": n_uc_flagged_sweep1,
    }


def calibrate_if_alone(iso, scaler, feature_cols, train_df, if_mean, if_std, percentile):
    X = train_df[feature_cols].to_numpy(dtype="float64")
    X_s = scaler.transform(X)
    if_raw = -iso.score_samples(X_s)
    z_if = (if_raw - if_mean) / if_std
    return float(np.percentile(z_if, percentile))


def calibrate_per_feature(train_df, percentile):
    return {f: float(np.percentile(train_df[f].dropna().to_numpy(dtype="float64"), percentile))
           for f in RELEVANT_FEATURES}


def build_ec04_bundle(percentile, margin):
    ec04_dir = os.path.join(MODELS_DIR, "EC04")
    bundle_pkl = joblib.load(os.path.join(ec04_dir, "model.pkl"))
    scaler = joblib.load(os.path.join(ec04_dir, "scaler.pkl"))
    with open(os.path.join(ec04_dir, "feature_names.json"), "r", encoding="utf-8") as f:
        feature_cols = json.load(f)
    with open(os.path.join(ec04_dir, "thresholds_pre_session37_backup.json"), "r", encoding="utf-8") as f:
        thresholds = json.load(f)  # ORIGINAL 9 keys only -- session 37/38's OR-gate keys computed fresh below

    df, split_json = load_source("EC04")
    needed_cols = list(dict.fromkeys(feature_cols + RELEVANT_FEATURES))
    train_df = rows_for_split(df, split_json, "train")[needed_cols].dropna()

    thresholds["if_alone_threshold"] = calibrate_if_alone(
        bundle_pkl["isolation_forest"], scaler, feature_cols, train_df,
        thresholds["if_score_train_mean"], thresholds["if_score_train_std"], percentile)
    thresholds["per_feature_thresholds"] = calibrate_per_feature(train_df, percentile)
    if margin is not None:
        thresholds["or_gate_score_margin_frac"] = margin

    return {
        "iso": bundle_pkl["isolation_forest"], "pca": bundle_pkl["pca"], "scaler": scaler,
        "feature_cols": feature_cols, "thresholds": thresholds,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--percentile", type=float, default=99.9)
    ap.add_argument("--margin", type=float, default=None)
    ap.add_argument("--tag", type=str, required=True)
    args = ap.parse_args()

    log(f"Recalibrating OR-gate thresholds at p{args.percentile} "
        f"{'with margin='+str(args.margin) if args.margin is not None else '(no score-margin gate)'} "
        f"for all 4 stations, tag={args.tag}...")

    log("Building session 22/23's pooled bundles (16-feature) for EC03/EC06/G16...")
    bundles = build_pooled_bundles()

    for sid in POOLED_STATIONS:
        bundle = bundles[sid]
        th = bundle["thresholds"]
        train_df, _ = load_split_rows(sid, "train")
        th["if_alone_threshold"] = calibrate_if_alone(
            bundle["iso"], bundle["scaler"], FLOOR_FREE_FEATURE_COLS, train_df,
            th["if_score_train_mean"], th["if_score_train_std"], args.percentile)
        th["per_feature_thresholds"] = calibrate_per_feature(train_df, args.percentile)
        if args.margin is not None:
            th["or_gate_score_margin_frac"] = args.margin
        log(f"  {sid}: if_alone_threshold={th['if_alone_threshold']:.4f}, "
            f"per_feature_thresholds={th['per_feature_thresholds']}")

    log("Building EC04's dedicated bundle in-memory (base thresholds from the session-37 backup, "
        "OR-gate keys recalibrated fresh -- models/EC04/thresholds.json NOT touched)...")
    bundles["EC04"] = build_ec04_bundle(args.percentile, args.margin)
    th = bundles["EC04"]["thresholds"]
    log(f"  EC04: if_alone_threshold={th['if_alone_threshold']:.4f}, "
        f"per_feature_thresholds={th['per_feature_thresholds']}")

    def _patched(source_id):
        return bundles[source_id]

    carrier_monitor._load_model_artifacts = _patched
    log("Monkey-patched carrier_monitor._load_model_artifacts for ALL 4 stations (in-memory only "
        "-- no file on disk read for OR-gate keys, no file on disk written).")

    all_t2 = []
    try:
        for source_id in NEW_SOURCE_IDS:
            t2 = evaluate_source_track2_ckpt(source_id, args.tag)
            write_report(f"{source_id}_ORGATE_{args.tag}", [], t2)
            all_t2.append(t2)
    finally:
        carrier_monitor._load_model_artifacts = _ORIGINAL_LOAD_MODEL_ARTIFACTS
        log("Restored carrier_monitor._load_model_artifacts to its original implementation.")

    lines = [f"# Session 38 TRACK 2 -- OR-gate recalibration attempt '{args.tag}' "
            f"(percentile={args.percentile}, margin={args.margin})\n",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"]
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

    out_path = os.path.join(OUT_DIR, f"SYNTHETIC_METRICS_SUMMARY_ORGATE_{args.tag}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Summary written to {out_path}")


if __name__ == "__main__":
    main()
