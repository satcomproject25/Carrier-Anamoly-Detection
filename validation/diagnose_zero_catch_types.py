r"""
diagnose_zero_catch_types.py
==============================
STANDALONE diagnostic -- run with:

    D:\Dhyan\myenv\Scripts\python.exe validation\diagnose_zero_catch_types.py

WHY THIS SCRIPT EXISTS
-----------------------
verify_deployed_models.py's 5-seed run showed BANDWIDTH_SHIFT and NOISE_FLOOR_RISE at a FLAT 0%
catch rate across EC03/EC06/EC04 at EVERY magnitude including "obvious" -- directly contradicting
this project's own earlier finding (that these 2 types show ZERO gap between the pooled and
dedicated models, implying reliable detection). This is either a genuine, serious detection
regression, or a test/injector issue -- this script gets the RAW EVIDENCE needed to tell which,
by printing, for a handful of real attempts:
  1. The injected carrier's ACTUAL anomaly score vs. its station's threshold (is it even close,
     or nowhere near triggering at all -- these are very different findings).
  2. A genuinely clean carrier's score on the SAME sweep, for direct comparison.
  3. The ground-truth injection detail (gt dict) -- confirms exactly what was changed and by how
     much, so you can judge whether the injection itself is even a meaningful perturbation.

Does NOT touch any model, threshold, or config -- read-only, print-only.
"""

import sys
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\validation")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\features")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")

from inject_interference import run_injection_test  # noqa: E402

STATIONS_TO_CHECK = ["EC03", "EC04", "EC06", "G16"]
TYPES_TO_CHECK = ["BANDWIDTH_SHIFT", "NOISE_FLOOR_RISE"]
SEEDS_TO_CHECK = [0, 1, 2]   # a handful, not all 5 -- this is a look-under-the-hood pass


def main():
    for source_id in STATIONS_TO_CHECK:
        for itype in TYPES_TO_CHECK:
            print(f"\n{'='*70}")
            print(f"{source_id} / {itype}")
            print('='*70)
            for seed in SEEDS_TO_CHECK:
                r = run_injection_test(source_id, itype, "obvious", warmup_sweeps=150, seed=seed)
                print(f"\n  seed={seed}  outcome={r.get('outcome')}")
                print(f"    caught (expected_triggered) = {r.get('expected_triggered')}")
                print(f"    flagged (any trigger fired)  = {r.get('flagged')}")
                print(f"    anomaly_score                = {r.get('anomaly_score')}")
                print(f"    anomaly_threshold             = {r.get('anomaly_threshold')}")
                gap = None
                try:
                    gap = r.get('anomaly_threshold') - r.get('anomaly_score')
                except TypeError:
                    pass
                print(f"    threshold - score (gap)      = {gap}"
                     f"  <-- {'CLOSE, near-miss' if gap is not None and 0 < gap < 1.0 else ('WELL ABOVE threshold?? should have caught' if gap is not None and gap < 0 else 'far below threshold' if gap is not None else 'N/A')}")
                gt = r.get("ground_truth", r.get("gt"))
                if gt:
                    print(f"    ground_truth (what was actually injected): {gt}")
                unexpected = r.get("unexpected_types")
                if unexpected:
                    print(f"    unexpected_types (fired, but not the type we expected): {unexpected}")

    print("\n\n" + "="*70)
    print("HOW TO READ THIS")
    print("="*70)
    print("""
If 'threshold - score' is a SMALL positive number (a near-miss, e.g. 0.1-0.5) across most
attempts: the injection IS producing a real signal, it's just not quite strong enough at
'obvious' magnitude for THIS specific type on THESE stations -- a genuine, if surprising, recall
limitation worth reporting honestly, not a bug.

If 'threshold - score' is a LARGE positive number (score barely moves at all, e.g. gap > 2-3)
across every attempt: the injection is likely NOT perturbing anything the current 16/55-feature
set actually measures -- worth checking the ground_truth printed above against the feature list
in models/{source_id}/feature_names.json to see if the injected quantity has a real corresponding
feature at all.

If 'flagged' is True but 'caught' (expected_triggered) is False: something DID fire, just not the
type-specific check expected for this injection -- check 'unexpected_types' above; this would be
a real, different, and less alarming finding (detection is happening, just mis-attributed).
""")


if __name__ == "__main__":
    main()