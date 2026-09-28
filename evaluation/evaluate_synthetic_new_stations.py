"""
Stage 2c driver for the 4 new stations (EC03, EC04, EC06, G16). Reuses evaluate_synthetic.py's
OWN evaluate_source_track2()/write_report() UNMODIFIED (already parameterized by source_id --
write_report() writes to {source_id}_eval_report.md, no collision with the 4 existing sources'
reports). Track 1 (real held-out flag rate) is NOT run here -- the task only asked for Track 2
(synthetic injection); write_report() is called with an empty track1_lines list, so each new
station's report contains only the Track 2 section.

write_synthetic_summary() is NOT reused as-is (it hardcodes SYNTHETIC_METRICS_SUMMARY.md, which
would overwrite the 4 existing sources' summary) -- this file writes its own summary to
SYNTHETIC_METRICS_SUMMARY_NEW_STATIONS.md instead, with the identical table format.

Run standalone: `python evaluate_synthetic_new_stations.py`
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate_synthetic import evaluate_source_track2, write_report, OUT_DIR, ALL_TYPES  # noqa: E402

NEW_SOURCE_IDS = ["EC03", "EC04", "EC06", "G16"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def write_synthetic_summary_new_stations(all_t2):
    lines = ["# Stage 2c TRACK 2 — Synthetic Metrics Summary (new stations)\n",
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

    lines.append("## Per-type flag rate at 'obvious' magnitude, across all 4 new stations\n")
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

    out_path = os.path.join(OUT_DIR, "SYNTHETIC_METRICS_SUMMARY_NEW_STATIONS.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Synthetic metrics summary written to {out_path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_t2 = []
    for source_id in NEW_SOURCE_IDS:
        t2 = evaluate_source_track2(source_id)
        write_report(source_id, [], t2)
        all_t2.append(t2)
    write_synthetic_summary_new_stations(all_t2)


if __name__ == "__main__":
    main()
