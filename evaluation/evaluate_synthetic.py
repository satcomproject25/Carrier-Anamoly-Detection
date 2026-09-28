"""
Phase 5 TRACK 2: synthetic labeled evaluation — the first REAL accuracy numbers this project has
ever had (Phase 0: no ground-truth labels exist anywhere for the natural data, so Track 1 has
always been honest-proxy metrics only; Part B's synthetic injections give genuine positive/
negative labels to compute against).

Methodology:
  - POSITIVE examples: Part B's `inject_interference.run_injection_test()` — 8 types x 3
    magnitude levels x 5 repeats per source, applied to held-out TEST sweeps only (never train),
    run through a warmed-up `CarrierAnomalyDetector` so Part C's trained Phase 4 score is real,
    not cold. Only `outcome=="OK"` attempts (a carrier was actually injected AND found in the
    result) count as valid labeled examples — other outcomes (NOT_DETECTED_AS_CARRIER,
    NO_MATCHING_CARRIER_FOUND, etc.) are reported separately as a "coverage" statistic, matching
    Part B's own honest-outcome-reporting style, not silently dropped or treated as failures of
    the classifier itself.
  - NEGATIVE examples: EVERY carrier in a clean (non-injected) TEST sweep, immediately following
    a warm-up window, in the same warmed-up-detector setup — many negatives per draw, not one.
  - Two prediction rules evaluated against the SAME labels: "Phase 4 score alone" (flagged =
    anomaly_score > threshold) and "combined pipeline" (flagged AND diagnose_carrier() assigned
    at least one SPECIFIC type, not just the GENERAL_DEGRADATION fallback) — the second is
    strictly harder to satisfy, since gating means diagnosis only runs when already flagged.
  - Real precision/recall/F1 for both; PR-AUC/ROC-AUC for the underlying continuous score
    (identical for both prediction rules — only the discrete decision differs).
  - Type-attribution accuracy: among TRUE POSITIVES that got flagged, what fraction had the
    CORRECT expected type among their triggered types (not just "flagged", not just "any
    specific type") — the confusion-matrix-adjacent headline number.
  - False-positive rate: fraction of clean, non-injected TEST carriers flagged.

**A new finding surfaced here, not on Part B's original list** (IN_BAND_TONE/SHOULDER_BUMP
running low, DROPOUT only-full-removal, ASYMMETRIC_DISTORTION blocked on B_ec05, A_16hr's
NOISE_FLOOR_RISE structurally blocked): UNAUTHORIZED_CARRIER injections create a carrier with
`event="appeared"` on its very first sweep — Phase 2's temporal features (frame_power_delta_db
etc.) are NaN by construction for a carrier's first-ever observation (no prior sweep to compute a
delta against), and Phase 4's scorer returns score=None whenever ANY required feature is NaN
(same behavior as the original single-peak module). **This means a newly-appeared carrier can
NEVER be scored by Phase 4 on the sweep it appears — only from its second observation onward.**
Under gated diagnosis, this makes UNAUTHORIZED_CARRIER structurally unrecallable on the injection
sweep itself, independent of injection magnitude. A supplementary one-sweep-later check is run
for this type specifically to confirm/quantify the delay.

Run standalone: `python evaluate_synthetic.py`
"""

import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, roc_auc_score

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\validation")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\evaluation")
from inject_interference import (                     # noqa: E402
    SOURCE_IDS, ALL_TYPES, MAGNITUDE_LEVELS, EXPECTED_DIAGNOSIS_TYPE, N_REPEATS,
    run_injection_test, _test_sweep_window, _load_source_arrays,
)
from carrier_monitor import CarrierAnomalyDetector, RawSweepInput  # noqa: E402
import evaluate_model as track1                        # noqa: E402

OUT_DIR = r"D:\Dhyan\Carrier_Detection\evaluation"
N_NEGATIVE_DRAWS = 15   # clean-window draws per source; each yields ~15-30 negative carrier examples
WARMUP_SWEEPS = 150


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def collect_positive_examples(source_id):
    rows = []
    for injection_type in ALL_TYPES:
        for level in MAGNITUDE_LEVELS:
            for rep in range(N_REPEATS):
                r = run_injection_test(source_id, injection_type, level,
                                       warmup_sweeps=WARMUP_SWEEPS, seed=rep)
                r["repeat"] = rep
                rows.append(r)
    return rows


def check_unauthorized_carrier_next_sweep(source_id, level, rep):
    """Supplementary check: does a newly-appeared carrier become scoreable/flagged on the
    sweep AFTER it appears (once it has one prior observation for temporal features)?"""
    from inject_interference import (pick_target_carrier, inject_unauthorized_carrier,  # noqa
                                     compute_noise_floor_and_scale, segment_carriers)
    rng = np.random.default_rng(rep)
    sweeps, freq_axis, has_ts, timestamps = _load_source_arrays(source_id)
    start, end, actual_warmup = _test_sweep_window(source_id, WARMUP_SWEEPS, 4, rng)
    warmup_end = start + actual_warmup - 1
    inject_idx = warmup_end + 1
    if actual_warmup < 1:
        return None
    det = CarrierAnomalyDetector(source_id=source_id)
    for i in range(start, warmup_end + 1):
        raw = RawSweepInput(power_dbm=sweeps[i], freq_axis_hz=freq_axis, timestamp=timestamps[i] if has_ts else None)
        det.process_sweep(raw)
    cfg = det._profiles[source_id]["cfg"]
    base_power = sweeps[inject_idx]
    noise_floor, noise_scale = compute_noise_floor_and_scale(base_power, cfg)
    carriers = segment_carriers(base_power, freq_axis if cfg["freq_axis_available"] else None,
                               cfg, noise_floor=noise_floor, noise_scale=noise_scale)
    if not carriers:
        return None
    modified, gt = inject_unauthorized_carrier(base_power, carriers, noise_floor, noise_scale, cfg, rng, level)
    if gt is None:
        return None
    raw = RawSweepInput(power_dbm=modified, freq_axis_hz=freq_axis, timestamp=timestamps[inject_idx] if has_ts else None)
    result = det.process_sweep(raw)
    lo, hi = gt["bin_range"]
    from inject_interference import _find_result_carrier
    rc = _find_result_carrier(result["carriers"], lo, hi)
    if rc is None:
        return {"found_sweep0": False}
    pid = rc["carrier_id"]
    # next (real, unmodified) sweep
    raw2 = RawSweepInput(power_dbm=sweeps[inject_idx + 1], freq_axis_hz=freq_axis,
                         timestamp=timestamps[inject_idx + 1] if has_ts else None)
    result2 = det.process_sweep(raw2)
    rc2 = next((c for c in result2["carriers"] if c["carrier_id"] == pid), None)
    if rc2 is None:
        return {"found_sweep0": True, "found_sweep1": False}
    return {"found_sweep0": True, "found_sweep1": True, "score_sweep1": rc2["anomaly_score"],
           "flagged_sweep1": rc2["flagged"]}


def collect_negative_examples(source_id, n_draws=N_NEGATIVE_DRAWS):
    rows = []
    sweeps, freq_axis, has_ts, timestamps = _load_source_arrays(source_id)
    for draw in range(n_draws):
        rng = np.random.default_rng(10_000 + draw)
        start, end, actual_warmup = _test_sweep_window(source_id, WARMUP_SWEEPS, 1, rng)
        warmup_end = start + actual_warmup - 1
        score_idx = warmup_end + 1
        if actual_warmup < 1:
            continue
        det = CarrierAnomalyDetector(source_id=source_id)
        for i in range(start, warmup_end + 1):
            raw = RawSweepInput(power_dbm=sweeps[i], freq_axis_hz=freq_axis, timestamp=timestamps[i] if has_ts else None)
            det.process_sweep(raw)
        raw = RawSweepInput(power_dbm=sweeps[score_idx], freq_axis_hz=freq_axis,
                            timestamp=timestamps[score_idx] if has_ts else None)
        result = det.process_sweep(raw)
        for c in result["carriers"]:
            rows.append({"source_id": source_id, "draw": draw, "carrier_id": c["carrier_id"],
                        "anomaly_score": c["anomaly_score"], "anomaly_threshold": c["anomaly_threshold"],
                        "flagged": c["flagged"], "all_triggered_types": [t["type"] for t in c["diagnosis"]]})
    return rows


def _combined_flag(flagged, triggered_types):
    if not flagged:
        return False
    specific = set(triggered_types) - {"GENERAL_DEGRADATION"}
    return len(specific) > 0


def compute_metrics(pos_rows, neg_rows):
    valid_pos = [r for r in pos_rows if r["outcome"] == "OK"]
    coverage = len(valid_pos) / len(pos_rows) if pos_rows else float("nan")

    y_true, y_score, y_pred_score, y_pred_combined = [], [], [], []
    type_correct, type_total = 0, 0

    for r in valid_pos:
        y_true.append(1)
        score = r.get("anomaly_score")
        y_score.append(score if score is not None else np.nan)
        flagged = bool(r.get("flagged"))
        y_pred_score.append(flagged)
        y_pred_combined.append(_combined_flag(flagged, r.get("all_triggered_types", [])))
        if flagged:
            type_total += 1
            if EXPECTED_DIAGNOSIS_TYPE[r["type"]] in r.get("all_triggered_types", []):
                type_correct += 1

    for r in neg_rows:
        y_true.append(0)
        score = r.get("anomaly_score")
        y_score.append(score if score is not None else np.nan)
        flagged = bool(r.get("flagged"))
        y_pred_score.append(flagged)
        y_pred_combined.append(_combined_flag(flagged, r.get("all_triggered_types", [])))

    y_true = np.array(y_true)
    y_score = np.array(y_score, dtype="float64")
    y_pred_score = np.array(y_pred_score, dtype=bool)
    y_pred_combined = np.array(y_pred_combined, dtype=bool)

    has_score = ~np.isnan(y_score)
    metrics = {"coverage": coverage, "n_positive_valid": int((y_true == 1).sum()),
              "n_negative": int((y_true == 0).sum()), "n_scored": int(has_score.sum())}

    for label, y_pred in [("score_alone", y_pred_score), ("combined", y_pred_combined)]:
        metrics[f"{label}_precision"] = float(precision_score(y_true, y_pred, zero_division=0))
        metrics[f"{label}_recall"] = float(recall_score(y_true, y_pred, zero_division=0))
        metrics[f"{label}_f1"] = float(f1_score(y_true, y_pred, zero_division=0))

    if has_score.sum() > 1 and len(set(y_true[has_score].tolist())) > 1:
        metrics["pr_auc"] = float(average_precision_score(y_true[has_score], y_score[has_score]))
        metrics["roc_auc"] = float(roc_auc_score(y_true[has_score], y_score[has_score]))
    else:
        metrics["pr_auc"] = None
        metrics["roc_auc"] = None

    metrics["type_attribution_accuracy"] = (type_correct / type_total) if type_total else None
    metrics["n_flagged_positives_checked_for_type"] = type_total
    metrics["false_positive_rate"] = float(y_pred_score[y_true == 0].mean()) if (y_true == 0).any() else None

    return metrics


def confusion_matrix_by_type(pos_rows):
    """rows = true injected type, columns = MISSED / GENERAL_DEGRADATION_ONLY / each specific
    triggered type (multi-label — one flagged case can add to multiple type columns)."""
    valid_pos = [r for r in pos_rows if r["outcome"] == "OK"]
    matrix = {t: {} for t in ALL_TYPES}
    for r in valid_pos:
        t = r["type"]
        if not r.get("flagged"):
            matrix[t]["MISSED"] = matrix[t].get("MISSED", 0) + 1
            continue
        specific = [x for x in r.get("all_triggered_types", []) if x != "GENERAL_DEGRADATION"]
        if not specific:
            matrix[t]["GENERAL_DEGRADATION_ONLY"] = matrix[t].get("GENERAL_DEGRADATION_ONLY", 0) + 1
        else:
            for s in specific:
                matrix[t][s] = matrix[t].get(s, 0) + 1
    return matrix


def per_type_level_summary(pos_rows):
    df = pd.DataFrame(pos_rows)
    df = df[df["outcome"] == "OK"].copy()
    if df.empty:
        return pd.DataFrame()
    df["flagged_b"] = df["flagged"].astype(bool)
    return df.groupby(["type", "level"])["flagged_b"].agg(["sum", "count"]).rename(columns={"sum": "n_flagged"})


def evaluate_source_track2(source_id):
    log(f"=== {source_id} (Track 2: synthetic labeled evaluation) ===")
    pos_rows = collect_positive_examples(source_id)
    log(f"  {len(pos_rows)} positive attempts, {sum(1 for r in pos_rows if r['outcome']=='OK')} valid (outcome=OK)")

    neg_rows = collect_negative_examples(source_id)
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


def write_report(source_id, track1_lines, t2):
    lines = list(track1_lines)
    lines.append("## TRACK 2 — Synthetic labeled evaluation (real accuracy metrics)\n")
    m = t2["metrics"]
    lines.append(f"- Positive attempts: {len(t2['pos_rows'])} (8 types x 3 magnitudes x {N_REPEATS} repeats); "
                f"**coverage (valid/matchable) = {m['coverage']*100:.1f}%** "
                f"({m['n_positive_valid']} valid positive examples)")
    lines.append(f"- Negative (clean, non-injected) examples: {m['n_negative']} carriers from "
                f"{N_NEGATIVE_DRAWS} independent held-out TEST windows")
    lines.append(f"- Scoreable examples (Phase 4 could compute a score, no NaN feature): {m['n_scored']}/"
                f"{m['n_positive_valid'] + m['n_negative']}\n")

    lines.append("### Real precision / recall / F1\n")
    lines.append("| pipeline | precision | recall | F1 |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Phase 4 score alone | {m['score_alone_precision']:.3f} | {m['score_alone_recall']:.3f} | {m['score_alone_f1']:.3f} |")
    lines.append(f"| Combined (score + specific-type diagnosis) | {m['combined_precision']:.3f} | {m['combined_recall']:.3f} | {m['combined_f1']:.3f} |")
    lines.append("")
    lines.append(f"- **PR-AUC**: {m['pr_auc']:.4f}" if m['pr_auc'] is not None else "- **PR-AUC**: n/a")
    lines.append(f"- **ROC-AUC**: {m['roc_auc']:.4f}" if m['roc_auc'] is not None else "- **ROC-AUC**: n/a")
    lines.append(f"- **False positive rate** (clean carriers flagged): {m['false_positive_rate']*100:.2f}%")
    if m['type_attribution_accuracy'] is not None:
        lines.append(f"- **Type-attribution accuracy** (of flagged true positives, fraction correctly "
                     f"typed): {m['type_attribution_accuracy']*100:.1f}% (n={m['n_flagged_positives_checked_for_type']})\n")
    else:
        lines.append("- Type-attribution accuracy: n/a (no flagged true positives)\n")

    lines.append("### Per-type / per-magnitude flag rate (positives only, outcome=OK)\n")
    tls = t2["type_level_summary"]
    if not tls.empty:
        lines.append("| type | level | flagged | n | rate |")
        lines.append("|---|---|---|---|---|")
        for (typ, lvl), row in tls.iterrows():
            rate = row["n_flagged"] / row["count"] if row["count"] else 0
            lines.append(f"| {typ} | {lvl} | {int(row['n_flagged'])} | {int(row['count'])} | {rate*100:.0f}% |")
    lines.append("")

    lines.append("### Confusion: injected type -> diagnosed type (multi-label; one case can add to multiple columns)\n")
    lines.append("| true type | MISSED | GENERAL_DEGRADATION only | correctly-typed count | other types triggered |")
    lines.append("|---|---|---|---|---|")
    for t in ALL_TYPES:
        row = t2["confusion"].get(t, {})
        expected = EXPECTED_DIAGNOSIS_TYPE[t]
        missed = row.get("MISSED", 0)
        gen_only = row.get("GENERAL_DEGRADATION_ONLY", 0)
        correct = row.get(expected, 0)
        others = {k: v for k, v in row.items() if k not in ("MISSED", "GENERAL_DEGRADATION_ONLY", expected)}
        lines.append(f"| {t} | {missed} | {gen_only} | {correct} | {others if others else '-'} |")
    lines.append("")

    if t2["uc_next_sweep"]:
        lines.append("### UNAUTHORIZED_CARRIER supplementary check — one sweep later\n")
        lines.append(f"Phase 4 cannot score a carrier on its very first (appeared) observation — "
                    f"temporal features are NaN by construction. Re-checked the SAME injected "
                    f"carrier on the immediately-following real sweep:\n")
        lines.append(f"- {t2['n_uc_flagged_sweep1']}/{len(t2['uc_next_sweep'])} flagged one sweep later "
                    f"(0/{len(t2['uc_next_sweep'])} possible on the appearance sweep itself)\n")

    report_path = os.path.join(OUT_DIR, f"{source_id}_eval_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"  Combined Track 1 + Track 2 report written to {report_path}")


def write_synthetic_summary(all_t2):
    lines = ["# Phase 5 TRACK 2 — Synthetic Metrics Summary (all sources)\n",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "First real accuracy numbers in this project's history — see PROGRESS.md 2026-08-10 "
            "Part D for full methodology and caveats.\n"]

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

    lines.append("## Per-type flag rate at 'obvious' magnitude, across all 4 sources\n")
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

    out_path = os.path.join(OUT_DIR, "SYNTHETIC_METRICS_SUMMARY.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Synthetic metrics summary written to {out_path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_t2 = []
    for source_id in SOURCE_IDS:
        t1_results, t1_lines = track1.evaluate_source(source_id)
        t2 = evaluate_source_track2(source_id)
        write_report(source_id, t1_lines, t2)
        all_t2.append(t2)
    write_synthetic_summary(all_t2)


if __name__ == "__main__":
    main()
