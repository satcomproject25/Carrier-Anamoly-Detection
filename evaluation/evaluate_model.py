"""
Phase 5 TRACK 1: evaluation on the held-out TEST split — touched exactly once, here, for the
first time since Phase 3 defined it (Phase 4 only read train/val). REBUILT 2026-08-10 for the
per-carrier feature schema (one row per (sweep, carrier)) — see PROGRESS.md Part D.

**Same schema bug pattern fixed here as Parts A/C**: the old version selected test rows via
`df.iloc[test_idx]` — positional indexing, broken the moment row position stopped equalling
sweep_index. Fixed via `sweep_index.isin(...)` membership, matching `utils/build_splits.py` /
`models/train_models.py`.

**Old single-peak-era example plots DROPPED, not ported.** They plotted "the" peak/approximate
-10dB region for one dominant peak per sweep — structurally incompatible with a sweep containing
10-32 simultaneously tracked carriers. `validation/plot_sweep.py` (Part E) is the correct
successor — general-purpose, all-carriers-marked, status-color-coded — and supersedes this
script's old plotting responsibility entirely rather than duplicating a broken visual.

This is TRACK 1 of Phase 5 — real ground-truth metrics are still not possible for the natural
test-set carriers (Phase 0: no labels exist anywhere), so this substitutes the same honest
equivalents as before:
  - test flag rate vs. the train/val flag rates already recorded in thresholds.json
  - a threshold-SENSITIVITY table (flag rate on test at several candidate percentile thresholds,
    recomputed from train) in place of a PR curve
  - for C_g18 only: a post-hoc cross-check of flagged vs. passed carriers against the
    instrument's own ground-truth CN_g18 — NOT used to tune anything
  - explicit, re-derived confirmation that the test indices used here match the persisted split
    file and are disjoint from train/val

TRACK 2 (real precision/recall/F1/PR-AUC/ROC-AUC via synthetic injections) is a separate script,
`evaluate_synthetic.py`, which imports this module's `evaluate_source()` and appends its own
section to the same per-source report.

Run standalone: `python evaluate_model.py` (Track 1 only)
"""

import os
import sys
import json
import time
import hashlib
import numpy as np
import pandas as pd
import joblib

FEATURES_DIR = r"D:\Dhyan\Carrier_Detection\data\features"
SPLITS_DIR = r"D:\Dhyan\Carrier_Detection\data\splits"
MODELS_DIR = r"D:\Dhyan\Carrier_Detection\models"
OUT_DIR = r"D:\Dhyan\Carrier_Detection\evaluation"

SOURCE_IDS = ["A_16hr", "B_ec02", "B_ec05", "C_g18"]
SEED = 42
SENSITIVITY_PERCENTILES = [90, 95, 97, 99, 99.5, 99.9]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def indices_for_split(split_json, split_name):
    idx = []
    for b in split_json["blocks"]:
        if b["split"] == split_name:
            idx.extend(range(b["core_start"], b["core_end"] + 1))
    return sorted(idx)


def sha256_of_indices(indices):
    arr = np.sort(np.asarray(indices, dtype=np.int64))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def rows_for_sweep_idx(df, sweep_idx):
    """Selects carrier-level ROWS by sweep_index MEMBERSHIP — never `.iloc` positional
    indexing, which silently breaks once a sweep can have multiple carrier rows."""
    return df[df["sweep_index"].isin(sweep_idx)]


def load_model_artifacts(source_id):
    d = os.path.join(MODELS_DIR, source_id)
    bundle = joblib.load(os.path.join(d, "model.pkl"))
    scaler = joblib.load(os.path.join(d, "scaler.pkl"))
    with open(os.path.join(d, "feature_names.json"), "r", encoding="utf-8") as f:
        feature_cols = json.load(f)
    with open(os.path.join(d, "thresholds.json"), "r", encoding="utf-8") as f:
        thresholds = json.load(f)
    return bundle["isolation_forest"], bundle["pca"], scaler, feature_cols, thresholds


def combined_score(if_raw, pca_raw, th):
    z_if = (if_raw - th["if_score_train_mean"]) / th["if_score_train_std"]
    z_pca = (pca_raw - th["pca_error_train_mean"]) / th["pca_error_train_std"]
    return th["ensemble_weights"]["isolation_forest"] * z_if + th["ensemble_weights"]["pca_reconstruction"] * z_pca


def score_matrix(X, iso, pca, scaler):
    Xs = scaler.transform(X)
    if_raw = -iso.score_samples(Xs)
    Xr = pca.inverse_transform(pca.transform(Xs))
    pca_raw = np.mean((Xs - Xr) ** 2, axis=1)
    return if_raw, pca_raw


def evaluate_source(source_id):
    """Runs Track 1 for one source. Returns (results_dict, markdown_lines) — does NOT write the
    report file itself, so `evaluate_synthetic.py` can append Track 2's section to the same
    file. `main()` below writes the Track-1-only file when this script runs standalone."""
    log(f"=== {source_id} (Track 1: real held-out test set) ===")
    df = pd.read_parquet(os.path.join(FEATURES_DIR, f"{source_id}_features.parquet"))
    with open(os.path.join(SPLITS_DIR, f"{source_id}_split.json"), "r", encoding="utf-8") as f:
        split_json = json.load(f)

    # ---- explicit, re-derived confirmation the test set is untouched and matches the split file ----
    train_idx = indices_for_split(split_json, "train")
    val_idx = indices_for_split(split_json, "val")
    test_idx = indices_for_split(split_json, "test")
    sha_ok = sha256_of_indices(test_idx) == split_json["test_sha256"]
    disjoint_ok = (len(set(test_idx) & set(train_idx)) == 0) and (len(set(test_idx) & set(val_idx)) == 0)
    assert sha_ok, f"{source_id}: reconstructed test indices don't match the persisted split file's SHA256!"
    assert disjoint_ok, f"{source_id}: test indices overlap train/val!"
    log(f"  Test-set integrity CONFIRMED: {len(test_idx)} sweeps, SHA256 matches split file, "
        f"zero overlap with train({len(train_idx)})/val({len(val_idx)}).")

    iso, pca, scaler, feature_cols, th = load_model_artifacts(source_id)

    test_rows = rows_for_sweep_idx(df, test_idx)[feature_cols + ["sweep_index", "carrier_id"]]
    n_test_raw = len(test_rows)
    test_rows = test_rows.dropna(subset=feature_cols)
    log(f"  test carrier-rows: {n_test_raw} -> {len(test_rows)} after dropping NaN "
        f"({n_test_raw - len(test_rows)} dropped)")

    X_test = test_rows[feature_cols].to_numpy(dtype="float64")
    if_raw, pca_raw = score_matrix(X_test, iso, pca, scaler)
    combined = combined_score(if_raw, pca_raw, th)
    threshold = th["combined_score_threshold"]
    flagged = combined > threshold
    test_flag_rate = float(flagged.mean())

    log(f"  test flag rate = {test_flag_rate*100:.2f}% (train={th['train_flag_rate']*100:.2f}%, "
        f"val={th['val_flag_rate']*100:.2f}%) at threshold={threshold:.4f}")

    # ---- threshold sensitivity table (substitutes for a PR curve — no labels to compute one) ----
    train_rows = rows_for_sweep_idx(df, train_idx)[feature_cols].dropna()
    X_train = train_rows.to_numpy(dtype="float64")
    if_tr, pca_tr = score_matrix(X_train, iso, pca, scaler)
    combined_tr = combined_score(if_tr, pca_tr, th)
    sensitivity = {}
    for p in SENSITIVITY_PERCENTILES:
        t = float(np.percentile(combined_tr, p))
        sensitivity[p] = {"threshold": t, "test_flag_rate": float((combined > t).mean())}
    log(f"  sensitivity table: { {p: round(v['test_flag_rate']*100, 2) for p, v in sensitivity.items()} }")

    # ---- C_g18-only: post-hoc cross-check against instrument ground-truth CN ----
    gt_check = None
    if "cn_ground_truth_matched_db" in df.columns:
        gt_col = rows_for_sweep_idx(df, test_idx).loc[test_rows.index, "cn_ground_truth_matched_db"]
        gt_flagged = gt_col[flagged]
        gt_passed = gt_col[~flagged]
        gt_flagged, gt_passed = gt_flagged.dropna(), gt_passed.dropna()
        if len(gt_flagged) > 0 and len(gt_passed) > 0:
            gt_check = {
                "n_flagged": int(len(gt_flagged)), "n_passed": int(len(gt_passed)),
                "gt_cn_mean_flagged": float(gt_flagged.mean()), "gt_cn_std_flagged": float(gt_flagged.std()),
                "gt_cn_mean_passed": float(gt_passed.mean()), "gt_cn_std_passed": float(gt_passed.std()),
            }
            log(f"  ground-truth CN cross-check: flagged carriers mean CN={gt_check['gt_cn_mean_flagged']:.2f}dB "
                f"(n={gt_check['n_flagged']}), passed carriers mean CN={gt_check['gt_cn_mean_passed']:.2f}dB "
                f"(n={gt_check['n_passed']})")

    lines = [f"# Phase 5 Evaluation Report — {source_id}\n", f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"]
    lines.append("## TRACK 1 — Real held-out test set (honest-proxy metrics)\n")
    lines.append("### Test-set integrity confirmation\n")
    lines.append(f"- Test sweeps: **{len(test_idx)}** ({len(test_rows)} carrier-rows after dropping NaN features)")
    lines.append(f"- SHA256 of reconstructed test indices matches `data/splits/{source_id}_split.json`: **{sha_ok}**")
    lines.append(f"- Zero index overlap with train({len(train_idx)})/val({len(val_idx)}): **{disjoint_ok}**")
    lines.append(f"- First and only time the test set has been used — `models/train_models.py` "
                f"reads only train/val indices.\n")

    lines.append("### Metrics (unsupervised substitutes — no ground-truth labels for the natural test set)\n")
    lines.append(f"- **Test flag rate: {test_flag_rate*100:.2f}%** vs. train {th['train_flag_rate']*100:.2f}% "
                f"/ val {th['val_flag_rate']*100:.2f}% (from Phase 4). Similar order of magnitude indicates "
                f"the test set is distributionally consistent with train/val, not a different regime.")
    lines.append(f"- Operating threshold used: {threshold:.4f} (99th percentile of TRAIN combined score, "
                f"tunable — see `models/{source_id}/thresholds.json`).\n")

    lines.append("#### Threshold sensitivity table (substitutes for a PR curve)\n")
    lines.append("| train percentile | threshold | test flag rate |")
    lines.append("|---|---|---|")
    for p in SENSITIVITY_PERCENTILES:
        v = sensitivity[p]
        lines.append(f"| p{p} | {v['threshold']:.4f} | {v['test_flag_rate']*100:.2f}% |")
    lines.append("")

    if gt_check:
        lines.append("#### Post-hoc cross-check against instrument ground-truth CN (C_g18 only)\n")
        lines.append(f"- Flagged carriers (n={gt_check['n_flagged']}): ground-truth CN mean="
                     f"{gt_check['gt_cn_mean_flagged']:.2f}dB, std={gt_check['gt_cn_std_flagged']:.2f}dB")
        lines.append(f"- Passed carriers (n={gt_check['n_passed']}): ground-truth CN mean="
                     f"{gt_check['gt_cn_mean_passed']:.2f}dB, std={gt_check['gt_cn_std_passed']:.2f}dB")
        diff = gt_check['gt_cn_mean_flagged'] - gt_check['gt_cn_mean_passed']
        lines.append(f"- Difference (flagged - passed): {diff:+.2f}dB. Post-hoc sanity signal only "
                     f"(never used to tune the threshold).\n")

    results = {
        "source_id": source_id, "n_test": len(test_idx), "n_test_rows": len(test_rows),
        "test_flag_rate": test_flag_rate, "train_flag_rate": th["train_flag_rate"],
        "val_flag_rate": th["val_flag_rate"], "sha_ok": sha_ok, "disjoint_ok": disjoint_ok,
        "gt_check": gt_check,
    }
    return results, lines


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    for source_id in SOURCE_IDS:
        r, lines = evaluate_source(source_id)
        results.append(r)
        report_path = os.path.join(OUT_DIR, f"{source_id}_eval_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log(f"  Track 1 report written to {report_path} (Track 2 not run — see evaluate_synthetic.py)")

    summary_path = os.path.join(OUT_DIR, "EVALUATION_SUMMARY.md")
    lines = ["# Phase 5 Evaluation — Track 1 Summary\n", f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"]
    lines.append("| source | n_test | test flag% | train flag% | val flag% | integrity check |")
    lines.append("|---|---|---|---|---|---|")
    for r in results:
        ok = "PASS" if (r["sha_ok"] and r["disjoint_ok"]) else "FAIL"
        lines.append(f"| {r['source_id']} | {r['n_test']} | {r['test_flag_rate']*100:.2f}% | "
                     f"{r['train_flag_rate']*100:.2f}% | {r['val_flag_rate']*100:.2f}% | {ok} |")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Evaluation summary written to {summary_path}")
    return results


if __name__ == "__main__":
    main()
