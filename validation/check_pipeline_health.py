r"""
check_pipeline_health.py
=========================
STANDALONE, MANUAL, FAST pipeline-correctness check -- run this yourself with:

    D:\Dhyan\myenv\Scripts\python.exe validation\check_pipeline_health.py

WHY THIS IS DIFFERENT FROM verify_deployed_models.py
------------------------------------------------------
That script answers "how accurate is detection" -- a real question, but slow (5 seeds x 8 types
x 3 magnitudes x 4 stations = 480 real 150-sweep warm-ups) and inherently noisy at low magnitude,
by this project's own documented finding.

THIS script answers a narrower, faster, more basic question: "is the pipeline itself -- carrier
segmentation, cross-sweep tracking, injection/matching, and model loading -- STRUCTURALLY SOUND
for all 4 stations, both model types (universal pooled + EC04 dedicated), before worrying about
exactly how accurate it is." It does this two ways, both cheap:

  1. EVENT-GATED TYPES ONLY (DROPOUT, UNAUTHORIZED_CARRIER) -- these do NOT depend on the trained
     anomaly score at all (see inject_interference.py's own comment on DROPOUT: "there is no live
     feature row for a disappeared carrier to score against -- flagged is defined as the
     diagnosis fired"). If these fail, the problem is in segmentation/tracking/matching, not
     model accuracy -- a structural signal, not a noisy one.
  2. OUTCOME-PATTERN CHECK across ALL 8 types (1 seed each, fast) -- specifically counts how many
     attempts return a clean "OK" outcome (pipeline ran fine, whether or not it caught the
     injection) versus a structural failure outcome (NOT_DETECTED_AS_CARRIER,
     NO_MATCHING_CARRIER_FOUND, NO_CARRIERS_IN_BASE_SWEEP, etc.) -- a high OK-rate with some
     misses is a healthy pipeline with an honest recall limitation; a high non-OK rate is a real
     pipeline problem worth chasing.

Runtime: ~2 (event-gated types, 5 seeds) + 8 (all types, 1 seed) = 10 real attempts per station,
40 total across all 4 stations -- a small fraction of the full verification script's 480.

OUTPUT
------
Prints a clear PASS/FAIL-style summary to the console AND saves a CSV:
D:\Dhyan\Carrier_Detection\validation\PIPELINE_HEALTH_CHECK_<timestamp>.csv
"""

import sys
import csv
from datetime import datetime, timezone

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\validation")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\features")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")

from inject_interference import run_injection_test, ALL_TYPES  # noqa: E402

UNIVERSAL_MODEL_SOURCES = ["EC03", "EC06", "G16"]
DEDICATED_MODEL_SOURCES = ["EC04"]
ALL_SOURCES = UNIVERSAL_MODEL_SOURCES + DEDICATED_MODEL_SOURCES

EVENT_GATED_TYPES = ["DROPOUT", "UNAUTHORIZED_CARRIER"]
EVENT_GATED_SEEDS = 5     # cheap enough to afford the full N_REPEATS convention here
ALL_TYPES_SEED = 0        # one seed, "obvious" magnitude only, for the broad outcome-pattern scan
STRUCTURAL_FAILURE_OUTCOMES = {
    "NOT_DETECTED_AS_CARRIER", "NO_MATCHING_CARRIER_FOUND", "NO_CARRIERS_IN_BASE_SWEEP",
    "NO_EMPTY_REGION_FOUND", "NO_TEST_BLOCK_LARGE_ENOUGH_FOR_ANY_WARMUP", "TARGET_ID_NOT_FOUND",
}

OUT_PATH_TEMPLATE = r"D:\Dhyan\Carrier_Detection\validation\PIPELINE_HEALTH_CHECK_{ts}.csv"


def check_event_gated(source_id):
    """DROPOUT + UNAUTHORIZED_CARRIER, EVENT_GATED_SEEDS repeats each, 'obvious' magnitude
    (the least ambiguous case -- if the pipeline can't catch an OBVIOUS, fully event-gated
    anomaly reliably, that's a real structural signal, not a subtlety issue)."""
    rows = []
    for itype in EVENT_GATED_TYPES:
        caught = 0
        structural_fail = 0
        for seed in range(EVENT_GATED_SEEDS):
            r = run_injection_test(source_id, itype, "obvious", warmup_sweeps=150, seed=seed)
            is_structural_fail = r["outcome"] in STRUCTURAL_FAILURE_OUTCOMES
            if is_structural_fail:
                structural_fail += 1
            elif r.get("expected_triggered"):
                caught += 1
            rows.append({"source_id": source_id, "check": "EVENT_GATED", "type": itype,
                        "seed": seed, "outcome": r["outcome"],
                        "caught": bool(r.get("expected_triggered"))})
        print(f"  [{source_id:5s}] {itype:22s} (event-gated, obvious, {EVENT_GATED_SEEDS} seeds) "
             f"-> caught {caught}/{EVENT_GATED_SEEDS}, structural_fail {structural_fail}/{EVENT_GATED_SEEDS}",
             flush=True)
    return rows


def check_outcome_pattern(source_id):
    """All 8 types, 1 seed, 'obvious' magnitude -- fast breadth check of whether the pipeline
    runs CLEANLY (outcome == OK) across every injection type, regardless of catch/miss."""
    rows = []
    n_ok, n_structural_fail = 0, 0
    for itype in ALL_TYPES:
        r = run_injection_test(source_id, itype, "obvious", warmup_sweeps=150, seed=ALL_TYPES_SEED)
        is_structural_fail = r["outcome"] in STRUCTURAL_FAILURE_OUTCOMES
        if is_structural_fail:
            n_structural_fail += 1
        elif r["outcome"] == "OK":
            n_ok += 1
        rows.append({"source_id": source_id, "check": "OUTCOME_PATTERN", "type": itype,
                    "seed": ALL_TYPES_SEED, "outcome": r["outcome"],
                    "caught": bool(r.get("expected_triggered"))})
    print(f"  [{source_id:5s}] outcome pattern (8 types, 1 seed, obvious): "
         f"{n_ok}/8 clean OK, {n_structural_fail}/8 structural failures", flush=True)
    return rows, n_ok, n_structural_fail


def main():
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_PATH_TEMPLATE.format(ts=ts)
    all_rows = []
    verdicts = {}

    for group_name, sources in [("UNIVERSAL MODEL", UNIVERSAL_MODEL_SOURCES),
                                ("EC04 DEDICATED MODEL", DEDICATED_MODEL_SOURCES)]:
        print(f"\n=== {group_name} ===", flush=True)
        for source_id in sources:
            print(f"\n-- {source_id} --", flush=True)
            eg_rows = check_event_gated(source_id)
            op_rows, n_ok, n_structural_fail = check_outcome_pattern(source_id)
            all_rows.extend(eg_rows)
            all_rows.extend(op_rows)

            eg_caught = sum(1 for r in eg_rows if r["caught"])
            eg_total = len(eg_rows)
            verdict = "PASS" if (n_structural_fail == 0 and eg_caught >= eg_total * 0.6) else \
                     "CHECK" if n_structural_fail <= 1 else "FAIL"
            verdicts[source_id] = (verdict, eg_caught, eg_total, n_ok, n_structural_fail)

    print("\n\n=== SUMMARY ===")
    print(f"{'Station':8s} {'Model':22s} {'Verdict':8s} {'Event-gated':14s} {'Outcome-OK':12s}")
    for group_name, sources in [("Universal (pooled)", UNIVERSAL_MODEL_SOURCES),
                                ("EC04 dedicated", DEDICATED_MODEL_SOURCES)]:
        for source_id in sources:
            v, caught, total, n_ok, n_fail = verdicts[source_id]
            print(f"{source_id:8s} {group_name:22s} {v:8s} {caught}/{total:<12} {n_ok}/8")

    print("\nPASS  = event-gated caught >=60% AND zero structural failures in the outcome scan")
    print("CHECK = at most 1 structural failure -- worth a look, not necessarily broken")
    print("FAIL  = 2+ structural failures in the 8-type scan -- real pipeline issue, investigate")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_id", "check", "type", "seed", "outcome", "caught"])
        for r in all_rows:
            writer.writerow([r["source_id"], r["check"], r["type"], r["seed"], r["outcome"], r["caught"]])
        writer.writerow([])
        writer.writerow(["station", "model_group", "verdict", "event_gated_caught",
                        "event_gated_total", "outcome_ok", "outcome_structural_fail"])
        for group_name, sources in [("universal_pooled", UNIVERSAL_MODEL_SOURCES),
                                    ("ec04_dedicated", DEDICATED_MODEL_SOURCES)]:
            for source_id in sources:
                v, caught, total, n_ok, n_fail = verdicts[source_id]
                writer.writerow([source_id, group_name, v, caught, total, n_ok, n_fail])

    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()