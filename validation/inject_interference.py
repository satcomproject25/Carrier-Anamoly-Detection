"""
Part B: synthetic interference generator, for Phase 5 Track 2 (real accuracy metrics) and for
directly validating the interference-diagnosis layer's sensitivity per type/source.

Design principle (per explicit project policy — no hardcoded absolute thresholds): every
injection's magnitude is derived from THAT SWEEP/SOURCE's own statistics, never a fixed dB
number applied identically across sources. Three magnitude scaling families are used, each tied
to the specific mechanism the corresponding diagnosis type actually checks:

1. **Amplitude injections evaluated by a SOFT z-score gate** (IN_BAND_TONE -> plateau_ripple_var,
   SHOULDER_BUMP -> rise/fall_overshoot_db): amplitude = {2,4,6} x this SWEEP's own robust
   noise_scale (the same adaptive scale `segment_carriers()` itself uses for K_detect/K_boundary
   — reusing an already-established, per-sweep, per-source statistic rather than inventing a new
   one).
2. **Injections gated by a HARD detection threshold before the diagnosis layer ever sees them**
   (ADJACENT_CARRIER -> must clear `SECONDARY_PEAK_MULT=8.0` x noise_scale prominence to register
   as a secondary peak at all; UNAUTHORIZED_CARRIER -> must clear `K_DETECT_DEFAULT=6.0` x
   noise_scale to be segmented as a carrier at all): magnitude is expressed as a FRACTION of that
   specific hard threshold ({0.75, 1.25, 2.0}x), deliberately straddling it — "subtle" sits BELOW
   the detection floor (a genuine test of "does this even get seen"), "moderate"/"obvious" sit
   above. A uniform 2x/4x/6x-of-noise_scale scheme would either always miss (if below the gate)
   or always hit (if using the same multiples as the amplitude types, given the gate is 6-8x) —
   neither produces a meaningful sensitivity curve, so these two types are deliberately scaled
   relative to their OWN gate instead.
3. **Geometric/temporal transforms with no natural "std" of their own** (ASYMMETRIC_DISTORTION —
   edge width compression; DROPOUT — fractional reduction toward floor): magnitude is a fraction
   of that SAME carrier's own existing geometry ({0.25, 0.5, 0.75} width compression; {0.5, 0.8,
   1.0} amplitude reduction) — inherently relative, not an arbitrary fixed value, just not a
   z-score since there's no comparable "normal variation in edge width" distribution to draw one
   from.
4. **NOISE_FLOOR_RISE / BANDWIDTH_SHIFT** — per explicit instruction (2026-08-10, given Part A
   revealed B_ec02 AND B_ec05 both now show coarse, slow-drift block structure): scaled from the
   std of `df.groupby("sweep_index")["cn_db"].mean()` — the EXACT per-sweep-averaged C/N series
   Phase 3's ACF used — rather than any single-carrier statistic, so injected magnitudes are
   realistic relative to each source's own recently-characterized drift behavior. NOISE_FLOOR_RISE
   uses this std directly as a dB magnitude; BANDWIDTH_SHIFT converts it to a relative-volatility
   fraction (std / |mean|) applied to the target carrier's own plateau width.

DROPOUT is the one type requiring MULTIPLE consecutive sweeps to test correctly: CARRIER_DROPOUT
is an EVENT type that only fires once a carrier's grace period (`GRACE_PERIOD_SWEEPS=10` sweeps)
fully expires with no reclaim (see `match_carriers()`) — a single-sweep zeroing would just look
like ordinary flicker and get silently reclaimed, never reaching CARRIER_DROPOUT at all. The
orchestrator applies DROPOUT across >=`GRACE_PERIOD_SWEEPS+1` consecutive sweeps.

Run standalone: `python inject_interference.py` (runs the Part B validation matrix: 8 types x 3
magnitudes x 4 sources, reports a results table).
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\features")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
from extract_features import (                                      # noqa: E402
    segment_carriers, compute_noise_floor_and_scale, build_source_config,
    K_DETECT_DEFAULT, SECONDARY_PEAK_MULT, GRACE_PERIOD_SWEEPS, MIN_CARRIER_WIDTH_BINS,
)
from carrier_monitor import CarrierAnomalyDetector, RawSweepInput          # noqa: E402

CANONICAL_DIR = r"D:\Dhyan\Carrier_Detection\data\canonical"
FEATURES_DIR = r"D:\Dhyan\Carrier_Detection\data\features"
SPLITS_DIR = r"D:\Dhyan\Carrier_Detection\data\splits"

SOURCE_IDS = ["A_16hr", "B_ec02", "B_ec05", "C_g18"]
MAGNITUDE_LEVELS = ["subtle", "moderate", "obvious"]
MAGNITUDE_MULT = {"subtle": 2.0, "moderate": 4.0, "obvious": 6.0}
GATE_FRAC = {"subtle": 0.75, "moderate": 1.25, "obvious": 2.0}     # for the two hard-gated types
GEOM_FRAC = {"subtle": 0.25, "moderate": 0.5, "obvious": 0.75}     # ASYMMETRIC_DISTORTION edge compression
DROPOUT_FRAC = {"subtle": 0.5, "moderate": 0.8, "obvious": 1.0}    # fraction toward floor
DROPOUT_N_SWEEPS = GRACE_PERIOD_SWEEPS + 2                          # must exceed the grace period to confirm CARRIER_DROPOUT

ALL_TYPES = ["IN_BAND_TONE", "SHOULDER_BUMP", "ADJACENT_CARRIER", "ASYMMETRIC_DISTORTION",
            "BANDWIDTH_SHIFT", "NOISE_FLOOR_RISE", "DROPOUT", "UNAUTHORIZED_CARRIER"]

EXPECTED_DIAGNOSIS_TYPE = {
    "IN_BAND_TONE": "IN_BAND_INTERFERENCE",
    "SHOULDER_BUMP": "SHOULDER_INTERFERENCE_SPECTRAL_REGROWTH",
    "ADJACENT_CARRIER": "ADJACENT_CHANNEL_INTERFERENCE",
    "ASYMMETRIC_DISTORTION": "ASYMMETRIC_EDGE_DISTORTION",
    "BANDWIDTH_SHIFT": "BANDWIDTH_ANOMALY",
    "NOISE_FLOOR_RISE": "NOISE_FLOOR_RISE_POSSIBLE_JAMMING",
    "DROPOUT": "CARRIER_DROPOUT",
    "UNAUTHORIZED_CARRIER": "UNAUTHORIZED_CARRIER",
}

_SWEEP_CN_DRIFT_CACHE = {}


def get_sweep_cn_drift_stats(source_id):
    """std/mean of the per-SWEEP-averaged cn_db series — the exact aggregate Phase 3's ACF used
    (see utils/build_splits.py) — the reference for NOISE_FLOOR_RISE/BANDWIDTH_SHIFT magnitude,
    per explicit instruction to use each source's own recently-characterized drift behavior."""
    if source_id not in _SWEEP_CN_DRIFT_CACHE:
        df = pd.read_parquet(os.path.join(FEATURES_DIR, f"{source_id}_features.parquet"),
                             columns=["sweep_index", "cn_db"])
        sweep_cn = df.groupby("sweep_index")["cn_db"].mean()
        _SWEEP_CN_DRIFT_CACHE[source_id] = {"std": float(sweep_cn.std()), "mean": float(sweep_cn.mean())}
    return _SWEEP_CN_DRIFT_CACHE[source_id]


# =====================================================================
# Target selection helpers
# =====================================================================

def pick_target_carrier(carriers, rng, min_width=15):
    candidates = [c for c in carriers if (c["floor_return_bin"] - c["floor_departure_bin"] + 1) >= min_width]
    if not candidates:
        candidates = carriers
    return candidates[int(rng.integers(len(candidates)))]


def find_empty_regions(n_bins, carriers, min_width=30, margin=10):
    """Bin ranges with no carrier (+ margin), wide enough for a synthetic carrier."""
    occupied = np.zeros(n_bins, dtype=bool)
    for c in carriers:
        lo = max(0, c["floor_departure_bin"] - margin)
        hi = min(n_bins, c["floor_return_bin"] + margin + 1)
        occupied[lo:hi] = True
    regions, start = [], None
    for i in range(n_bins):
        if not occupied[i]:
            if start is None:
                start = i
        elif start is not None:
            if i - start >= min_width:
                regions.append((start, i - 1))
            start = None
    if start is not None and n_bins - start >= min_width:
        regions.append((start, n_bins - 1))
    return regions


def _gaussian_bump(n_bins, center, sigma, amplitude):
    x = np.arange(n_bins)
    return amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)


# =====================================================================
# 8 injection types
# =====================================================================

def inject_in_band_tone(power, carriers, noise_floor, noise_scale, cfg, rng, level):
    target = pick_target_carrier(carriers, rng)
    lo, hi = target["rise_end_bin"], target["fall_start_bin"]
    if hi - lo < 6:
        lo, hi = target["floor_departure_bin"], target["floor_return_bin"]
    center = int(rng.integers(lo + 2, hi - 1)) if hi - lo > 3 else (lo + hi) // 2
    sigma = 1.5
    amp = MAGNITUDE_MULT[level] * noise_scale
    new_power = power.astype("float64") + _gaussian_bump(len(power), center, sigma, amp)
    gt = {"type": "IN_BAND_TONE", "magnitude_level": level, "magnitude_db": float(amp),
         "target_carrier_span": (target["floor_departure_bin"], target["floor_return_bin"]),
         "bin_range": (int(center - 3 * sigma), int(center + 3 * sigma)),
         "expected_diagnosis_types": [EXPECTED_DIAGNOSIS_TYPE["IN_BAND_TONE"]]}
    return new_power.astype(power.dtype), gt


def inject_shoulder_bump(power, carriers, noise_floor, noise_scale, cfg, rng, level):
    """`fall_overshoot_db` = max(fall_seg) - fall_seg[-1], where fall_seg is REVERSED so
    index -1 is the plateau-adjacent endpoint (fall_start_bin) — i.e. it only registers a bump
    that exceeds the edge's OWN settled endpoint value, which physically means the bump must sit
    very close to fall_start_bin (a bump deep in the skirt, near the floor end, would need to be
    taller than the entire carrier to ever exceed that endpoint — never realistic). Confirmed by
    direct testing: a bump at the geometric midpoint of the fall span produced ZERO overshoot
    (instead spuriously triggering ASYMMETRIC_EDGE_DISTORTION, since it just reshaped the edge).
    Placing the bump right at the plateau-adjacent end, a few bins into the fall from fs, is the
    only placement that actually exceeds fall_seg[-1] and registers as overshoot."""
    target = pick_target_carrier(carriers, rng)
    fs, fr = target["fall_start_bin"], target["floor_return_bin"]
    if fr - fs < 3:
        fs, fr = target["floor_departure_bin"], target["rise_end_bin"]
    offset = min(3, max(1, (fr - fs) // 4))
    center = fs + offset
    sigma = 1.0
    amp = MAGNITUDE_MULT[level] * noise_scale
    new_power = power.astype("float64") + _gaussian_bump(len(power), center, sigma, amp)
    gt = {"type": "SHOULDER_BUMP", "magnitude_level": level, "magnitude_db": float(amp),
         "target_carrier_span": (target["floor_departure_bin"], target["floor_return_bin"]),
         "bin_range": (fs, min(fr, center + 3)),
         "expected_diagnosis_types": [EXPECTED_DIAGNOSIS_TYPE["SHOULDER_BUMP"]]}
    return new_power.astype(power.dtype), gt


def inject_adjacent_carrier(power, carriers, noise_floor, noise_scale, cfg, rng, level):
    """Amplitude must clear SECONDARY_PEAK_MULT=8.0x noise_scale PROMINENCE (scipy's find_peaks
    definition: height above the higher of the two neighboring valleys) to register as a
    secondary peak at all, but must also stay BELOW the target carrier's own TRUE peak or it
    becomes the carrier's new dominant peak instead of a genuine secondary — collapsing
    `n_secondary_peaks_in_span` back to 0 (only one peak found overall) rather than 1.

    Two real bugs found here by direct tracing before this cap was correct:
    1. Adding a Gaussian bump on top of the fall edge's own descending slope dilutes its measured
       prominence well below the injected amplitude (scipy measures prominence against the higher
       neighboring valley, which on a monotonic descent sits partway back up toward the main
       peak). Fixed by flattening a small local neighborhood to its own minimum first, then adding
       the bump on top of THAT baseline — prominence now closely tracks the injected amplitude.
    2. The resulting cap must be relative to that SAME local `baseline`, not the carrier's
       whole-span local floor — a carrier's fall skirt sits well above the true floor partway
       down, so capping amplitude against `peak - floor` (a much bigger number) let the injected
       peak's ABSOLUTE level exceed the carrier's true peak even while "under the cap" — traced
       directly: baseline=-88.7dBm, true peak=-87.0dBm, but an amp capped at 0.6*(peak-floor)=6.8
       gave an absolute injected level of -83.3dBm, comfortably ABOVE the true peak, so it became
       the new dominant peak (CARRIER_DRIFT) instead of a secondary. Fixed by capping against
       `true_peak - baseline` (the actual local margin available), not `true_peak - whole_floor`.
    """
    target = pick_target_carrier(carriers, rng, min_width=25)
    fd, fr = target["floor_departure_bin"], target["floor_return_bin"]
    # Deep in the skirt, close to floor_return_bin — NOT a fixed fraction back from fr: tried
    # 15%-of-span-back-from-fr first, but on a wide carrier that position hadn't fully descended
    # to the true floor yet (traced directly: baseline=-88.7dBm there vs. true floor=-98.4dBm,
    # only 1.76dB of local margin below the true peak — not enough room to inject a detectable-
    # yet-clearly-secondary bump). A small FIXED offset from fr lands much closer to the true
    # local floor regardless of carrier width, giving genuine headroom.
    center = max(fd + 5, fr - 6)
    sigma = 1.2
    n = len(power)
    radius = int(3 * sigma) + 2
    lo, hi = max(0, center - radius), min(n, center + radius + 1)
    baseline = float(np.min(power[lo:hi]))

    local_margin = target["peak_power_dbm"] - baseline   # actual headroom below the TRUE peak at this local baseline
    amp = min(GATE_FRAC[level] * SECONDARY_PEAK_MULT * noise_scale, 0.7 * local_margin)

    new_power = power.astype("float64").copy()
    new_power[lo:hi] = baseline
    new_power += _gaussian_bump(n, center, sigma, amp)

    gt = {"type": "ADJACENT_CARRIER", "magnitude_level": level, "magnitude_db": float(amp),
         "gate_fraction_of_secondary_peak_mult": GATE_FRAC[level], "local_margin_db": float(local_margin),
         "capped_by_margin": amp < GATE_FRAC[level] * SECONDARY_PEAK_MULT * noise_scale,
         "target_carrier_span": (fd, fr), "bin_range": (lo, hi),
         "expected_diagnosis_types": [EXPECTED_DIAGNOSIS_TYPE["ADJACENT_CARRIER"]]}
    return new_power.astype(power.dtype), gt


def inject_asymmetric_distortion(power, carriers, noise_floor, noise_scale, cfg, rng, level):
    target = pick_target_carrier(carriers, rng, min_width=20)
    fd, re_, fs, fr = (target["floor_departure_bin"], target["rise_end_bin"],
                       target["fall_start_bin"], target["floor_return_bin"])
    new_power = power.astype("float64").copy()
    fall_w = fr - fs
    if fall_w < 4:
        gt = {"type": "ASYMMETRIC_DISTORTION", "magnitude_level": level, "note": "fall edge too narrow, no-op",
             "target_carrier_span": (fd, fr), "expected_diagnosis_types": [EXPECTED_DIAGNOSIS_TYPE["ASYMMETRIC_DISTORTION"]]}
        return power, gt
    compress_frac = GEOM_FRAC[level]
    new_fall_w = max(2, int(round(fall_w * (1 - compress_frac))))
    orig_profile = power[fs:fr + 1].astype("float64")
    # resample the falling edge's power profile into a narrower span (steeper effective slope)
    x_old = np.linspace(0, 1, len(orig_profile))
    x_new = np.linspace(0, 1, new_fall_w + 1)
    compressed = np.interp(x_new, x_old, orig_profile)
    floor_val = float(noise_floor[fr])
    new_power[fs:fr + 1] = floor_val  # clear the original span to floor first
    new_power[fs:fs + len(compressed)] = compressed
    gt = {"type": "ASYMMETRIC_DISTORTION", "magnitude_level": level, "compress_frac": compress_frac,
         "orig_fall_width_bins": fall_w, "new_fall_width_bins": new_fall_w,
         "target_carrier_span": (fd, fr), "bin_range": (fs, fr),
         "expected_diagnosis_types": [EXPECTED_DIAGNOSIS_TYPE["ASYMMETRIC_DISTORTION"]]}
    return new_power.astype(power.dtype), gt


def inject_bandwidth_shift(power, carriers, noise_floor, noise_scale, cfg, rng, level, drift_stats):
    """`occupied_bw_bins` is derived from floor_departure_bin/floor_return_bin — the RE-SEGMENTED
    boundary crossing on the injected sweep, not anything internal to the original plateau/edge
    split. An earlier version of this function only rewrote power WITHIN the original [fd, fr]
    span (extending the internal plateau at the expense of the rise/fall edges) — confirmed by
    direct testing that this leaves floor_departure/floor_return, and therefore occupied_bw_bins,
    COMPLETELY UNCHANGED on re-segmentation (BANDWIDTH_ANOMALY never triggered). Fixed: stretch
    each edge's own profile (preserving its shape) to extend genuinely PAST the original fd/fr,
    so the true floor-to-floor span grows on re-segmentation."""
    target = pick_target_carrier(carriers, rng, min_width=20)
    fd, re_, fs, fr = (target["floor_departure_bin"], target["rise_end_bin"],
                       target["fall_start_bin"], target["floor_return_bin"])
    rel_volatility = float(np.clip(drift_stats["std"] / max(abs(drift_stats["mean"]), 1e-6), 0.02, 0.5))
    width_change_frac = MAGNITUDE_MULT[level] * rel_volatility
    plateau_w = max(1, fs - re_)
    delta_bins = max(2, int(round(width_change_frac * plateau_w)))
    half = max(1, delta_bins // 2)
    n = len(power)
    new_power = power.astype("float64").copy()

    rise_orig = power[fd:re_ + 1].astype("float64")
    new_left = max(0, fd - half)
    if len(rise_orig) >= 2 and new_left < re_:
        x_old = np.linspace(0, 1, len(rise_orig))
        x_new = np.linspace(0, 1, re_ - new_left + 1)
        new_power[new_left:re_ + 1] = np.interp(x_new, x_old, rise_orig)

    fall_orig = power[fs:fr + 1].astype("float64")
    new_right = min(n - 1, fr + half)
    if len(fall_orig) >= 2 and fs < new_right:
        x_old2 = np.linspace(0, 1, len(fall_orig))
        x_new2 = np.linspace(0, 1, new_right - fs + 1)
        new_power[fs:new_right + 1] = np.interp(x_new2, x_old2, fall_orig)

    gt = {"type": "BANDWIDTH_SHIFT", "magnitude_level": level, "rel_volatility": rel_volatility,
         "width_change_frac": width_change_frac, "orig_occupied_bw_bins": fr - fd + 1,
         "delta_bins_per_side": half, "target_carrier_span": (fd, fr), "bin_range": (new_left, new_right),
         "expected_diagnosis_types": [EXPECTED_DIAGNOSIS_TYPE["BANDWIDTH_SHIFT"]]}
    return new_power.astype(power.dtype), gt


def inject_noise_floor_rise(power, carriers, noise_floor, noise_scale, cfg, rng, level, drift_stats):
    target = pick_target_carrier(carriers, rng, min_width=15)
    fd, fr = target["floor_departure_bin"], target["floor_return_bin"]
    n = len(power)
    band_width = max(fr - fd + 1, int(n * 0.15))
    center = (fd + fr) // 2
    lo = max(0, center - band_width // 2)
    hi = min(n, center + band_width // 2)
    magnitude_db = MAGNITUDE_MULT[level] * drift_stats["std"]
    new_power = power.astype("float64").copy()
    new_power[lo:hi] += magnitude_db
    gt = {"type": "NOISE_FLOOR_RISE", "magnitude_level": level, "magnitude_db": float(magnitude_db),
         "sweep_cn_std_used": drift_stats["std"], "target_carrier_span": (fd, fr), "bin_range": (lo, hi),
         "expected_diagnosis_types": [EXPECTED_DIAGNOSIS_TYPE["NOISE_FLOOR_RISE"]]}
    return new_power.astype(power.dtype), gt


def inject_dropout_single_sweep(power, target, noise_floor, level):
    """Applies ONE sweep's worth of the dropout transform to a FIXED target span (the same
    target/plan reused across DROPOUT_N_SWEEPS consecutive sweeps by the orchestrator)."""
    fd, fr = target["floor_departure_bin"], target["floor_return_bin"]
    frac = DROPOUT_FRAC[level]
    new_power = power.astype("float64").copy()
    seg = power[fd:fr + 1].astype("float64")
    floor_seg = noise_floor[fd:fr + 1]
    new_power[fd:fr + 1] = seg + frac * (floor_seg - seg)
    return new_power.astype(power.dtype)


def inject_unauthorized_carrier(power, carriers, noise_floor, noise_scale, cfg, rng, level):
    n = len(power)
    regions = find_empty_regions(n, carriers, min_width=30)
    if not regions:
        return power, None
    region = regions[int(rng.integers(len(regions)))]
    lo, hi = region
    width = min(hi - lo, 40)
    start = lo + (hi - lo - width) // 2
    rise_w = max(3, width // 5)
    fall_w = max(3, width // 5)
    plateau_w = width - rise_w - fall_w
    amp = GATE_FRAC[level] * K_DETECT_DEFAULT * noise_scale
    floor_val = float(np.median(noise_floor[start:start + width + 1]))
    peak_val = floor_val + amp
    profile = np.concatenate([
        np.linspace(floor_val, peak_val, rise_w),
        np.full(max(plateau_w, 1), peak_val),
        np.linspace(peak_val, floor_val, fall_w),
    ])
    new_power = power.astype("float64").copy()
    end = min(n, start + len(profile))
    new_power[start:end] = profile[:end - start]
    gt = {"type": "UNAUTHORIZED_CARRIER", "magnitude_level": level, "magnitude_db": float(amp),
         "gate_fraction_of_k_detect": GATE_FRAC[level], "bin_range": (start, end - 1),
         "expected_diagnosis_types": [EXPECTED_DIAGNOSIS_TYPE["UNAUTHORIZED_CARRIER"]]}
    return new_power.astype(power.dtype), gt


# =====================================================================
# Test harness: wire an injection through a WARMED-UP CarrierAnomalyDetector, so
# baseline-driven types (BANDWIDTH_ANOMALY, NOISE_FLOOR_RISE_POSSIBLE_JAMMING) have a real
# per-carrier-id / per-source rolling history to compare against, exactly as they would in
# production, rather than an empty/cold baseline that could never trigger those two types at all.
# =====================================================================

# 2026-09-02 (session 24): process-local, SINGLE-SLOT cache -- `run_injection_test()` calls this
# function once per (type, level, repeat) attempt (120+ times per station for a full Track 2 run),
# and `collect_negative_examples()` calls it once per draw on top of that. Reloading/decompressing
# a station's full canonical .npz from disk EVERY call was fine when this was written against the
# original single-day canonical files (small), but sessions 19-23's extended-window canonical files
# are 3.9-4.9GB each -- unchanged, this made a full 4-station Track 2 run take an estimated
# ~12-14 hours purely on redundant disk reloads, confirmed by direct process monitoring (a
# load-to-load cycle took ~60-90s). Caching the loaded arrays changes NOTHING about what data is
# used or how (same arrays, same values, every injector already returns a fresh copy via
# `.astype()`/explicit `.copy()` rather than mutating `power`/`sweeps` in place -- verified across
# every INJECTORS_SIMPLE/INJECTORS_DRIFT_SCALED function before adding this) -- purely a wall-clock
# fix, byte-identical results either way. SINGLE-SLOT (not one entry per source_id): a full 4-source
# Track 2 run evaluates one station to completion before moving to the next, so caching all 4
# simultaneously would hold ~18GB resident for no benefit -- one slot, evicted whenever a
# DIFFERENT source_id is requested, gets the same speedup with bounded memory.
_SOURCE_ARRAYS_CACHE = {"source_id": None, "arrays": None}


def _load_source_arrays(source_id):
    if _SOURCE_ARRAYS_CACHE["source_id"] == source_id:
        return _SOURCE_ARRAYS_CACHE["arrays"]
    with np.load(os.path.join(CANONICAL_DIR, f"{source_id}.npz")) as npz:
        sweeps = npz["sweeps"]
        freq_axis_available = bool(npz["freq_axis_available"]) if "freq_axis_available" in npz.files else False
        freq_axis = npz["freq_axis_hz"] if freq_axis_available else None
        has_ts = bool(npz["has_timestamps"]) if "has_timestamps" in npz.files else False
        timestamps = npz["timestamps"] if has_ts else None
    arrays = (sweeps, freq_axis, has_ts, timestamps)
    _SOURCE_ARRAYS_CACHE["source_id"] = source_id
    _SOURCE_ARRAYS_CACHE["arrays"] = arrays
    return arrays


def _test_sweep_window(source_id, warmup_sweeps, extra_room, rng):
    """Picks a contiguous window entirely within the TEST split (never train/val — synthetic
    injections are for evaluation, not training, per the project's own standing methodology),
    long enough for `warmup_sweeps` of real history plus `extra_room` injected sweeps. Returns
    (start, end, actual_warmup_sweeps).

    **Real bug found and fixed here**: A_16hr's test split is made of block_size=20-sweep blocks
    (its OWN near-zero-autocorrelation block size from Part A) — far smaller than a 150-sweep
    warm-up request. The original version clamped `needed` locally in the no-large-enough-block
    fallback but never told the CALLER, which kept using its own fixed `warmup_sweeps=150`
    regardless — walking `inject_idx` straight past the end of the sweep array (IndexError).
    Now returns the ACTUAL achievable warm-up length so the caller uses it, not the request.
    Also means NOISE_FLOOR_RISE testing (needs NOISE_FLOOR_SOURCE_MIN_HISTORY=30 sweeps of
    per-source history) is structurally limited on A_16hr specifically within a single test
    block — a real, reportable consequence of that source's own fine-grained split, not a harness
    defect; the caller checks and reports this rather than silently testing on an unwarmed
    baseline."""
    import json
    with open(os.path.join(SPLITS_DIR, f"{source_id}_split.json"), "r", encoding="utf-8") as f:
        sj = json.load(f)
    test_ranges = [(b["core_start"], b["core_end"]) for b in sj["blocks"] if b["split"] == "test"]
    needed = warmup_sweeps + extra_room
    candidates = [(lo, hi) for lo, hi in test_ranges if hi - lo + 1 >= needed]
    if candidates:
        lo, hi = candidates[int(rng.integers(len(candidates)))]
        start = lo + int(rng.integers(0, hi - lo + 1 - needed + 1))
        return start, start + needed - 1, warmup_sweeps

    lo, hi = max(test_ranges, key=lambda r: r[1] - r[0])
    block_len = hi - lo + 1
    actual_warmup = max(0, block_len - extra_room)
    return lo, lo + block_len - 1, actual_warmup


def _find_result_carrier(carriers_list, target_lo, target_hi):
    """Picks the carrier in a process_sweep() result's 'carriers' list with the most bin overlap
    against (target_lo, target_hi), approximating span as peak_bin +/- occupied_bw/2 (the
    features output doesn't carry the raw floor_departure/return span — same approximation used
    in the B_ec05 reclaim-evidence check, see PROGRESS.md)."""
    best, best_overlap = None, 0
    for c in carriers_list:
        half = (c["occupied_bw_bins"] or 0) / 2.0
        lo, hi = c["center_bin_index"] - half, c["center_bin_index"] + half
        overlap = max(0, min(hi, target_hi) - max(lo, target_lo))
        if overlap > best_overlap:
            best, best_overlap = c, overlap
    return best


INJECTORS_SIMPLE = {
    "IN_BAND_TONE": inject_in_band_tone,
    "SHOULDER_BUMP": inject_shoulder_bump,
    "ADJACENT_CARRIER": inject_adjacent_carrier,
    "ASYMMETRIC_DISTORTION": inject_asymmetric_distortion,
}
INJECTORS_DRIFT_SCALED = {
    "BANDWIDTH_SHIFT": inject_bandwidth_shift,
    "NOISE_FLOOR_RISE": inject_noise_floor_rise,
}


def run_injection_test(source_id, injection_type, level, warmup_sweeps=150, seed=0):
    """Returns a result dict: triggered types on the target carrier, whether the expected type
    fired, any unexpected types, and enough detail to explain why."""
    rng = np.random.default_rng(seed)
    sweeps, freq_axis, has_ts, timestamps = _load_source_arrays(source_id)
    extra_room = DROPOUT_N_SWEEPS + 2 if injection_type == "DROPOUT" else 3
    start, end, actual_warmup = _test_sweep_window(source_id, warmup_sweeps, extra_room, rng)
    warmup_end = start + actual_warmup - 1
    inject_idx = warmup_end + 1

    warmup_shrunk = actual_warmup < warmup_sweeps
    if actual_warmup < 1:
        return {"source_id": source_id, "type": injection_type, "level": level,
               "outcome": "NO_TEST_BLOCK_LARGE_ENOUGH_FOR_ANY_WARMUP", "expected_triggered": False,
               "unexpected_types": []}
    # NOISE_FLOOR_RISE_POSSIBLE_JAMMING's source-level baseline needs NOISE_FLOOR_SOURCE_MIN_HISTORY
    # sweeps of history — if the achievable warm-up on this source's own test blocks can't reach
    # that (a real, structural consequence of a finely-fragmented split like A_16hr's, not a bug),
    # report it explicitly rather than silently testing against an unwarmed/all-NaN baseline.
    from interference_diagnosis import NOISE_FLOOR_SOURCE_MIN_HISTORY
    if injection_type == "NOISE_FLOOR_RISE" and actual_warmup < NOISE_FLOOR_SOURCE_MIN_HISTORY:
        return {"source_id": source_id, "type": injection_type, "level": level,
               "outcome": f"INSUFFICIENT_WARMUP_FOR_SOURCE_BASELINE (got {actual_warmup}, "
                          f"need >={NOISE_FLOOR_SOURCE_MIN_HISTORY})",
               "expected_triggered": False, "unexpected_types": []}

    det = CarrierAnomalyDetector(source_id=source_id)
    for i in range(start, warmup_end + 1):
        raw = RawSweepInput(power_dbm=sweeps[i], freq_axis_hz=freq_axis,
                            timestamp=timestamps[i] if has_ts else None)
        det.process_sweep(raw)

    cfg = det._profiles[source_id]["cfg"]
    base_power = sweeps[inject_idx]
    noise_floor, noise_scale = compute_noise_floor_and_scale(base_power, cfg)
    carriers = segment_carriers(base_power, freq_axis if cfg["freq_axis_available"] else None,
                               cfg, noise_floor=noise_floor, noise_scale=noise_scale)
    if not carriers:
        return {"source_id": source_id, "type": injection_type, "level": level,
               "outcome": "NO_CARRIERS_IN_BASE_SWEEP", "expected_triggered": False, "unexpected_types": []}

    expected_type = EXPECTED_DIAGNOSIS_TYPE[injection_type]

    if injection_type == "DROPOUT":
        target = pick_target_carrier(carriers, rng)
        target_pid = None
        # identify this carrier's persistent_id from the just-warmed-up tracker state
        for c in det._streams[source_id].prev_tracked:
            half = 0
            if c["floor_departure_bin"] <= target["peak_bin"] <= c["floor_return_bin"]:
                target_pid = c["persistent_id"]
                break
        triggered_types, last_result = set(), None
        for k in range(DROPOUT_N_SWEEPS):
            i = inject_idx + k
            p = sweeps[i]
            nf, _ = compute_noise_floor_and_scale(p, cfg)
            modified = inject_dropout_single_sweep(p, target, nf, level)
            raw = RawSweepInput(power_dbm=modified, freq_axis_hz=freq_axis,
                                timestamp=timestamps[i] if has_ts else None)
            result = det.process_sweep(raw)
            last_result = result
            for dc in result["disappeared_carriers"]:
                if target_pid is not None and dc["carrier_id"] == target_pid:
                    triggered_types.update(t["type"] for t in dc["diagnosis"])
        expected_hit = expected_type in triggered_types
        return {"source_id": source_id, "type": injection_type, "level": level,
               "outcome": "OK" if target_pid is not None else "TARGET_ID_NOT_FOUND",
               "expected_triggered": expected_hit,
               "unexpected_types": sorted(triggered_types - {expected_type}),
               "all_triggered_types": sorted(triggered_types), "target_persistent_id": target_pid,
               # CARRIER_DROPOUT is event-gated (grace-period expiry), not score-gated — there is
               # no live feature row for a disappeared carrier to score against Phase 4, so
               # "flagged" here is defined as "the diagnosis fired", the closest analogue
               "anomaly_score": None, "anomaly_threshold": None, "flagged": expected_hit}

    if injection_type == "UNAUTHORIZED_CARRIER":
        modified, gt = inject_unauthorized_carrier(base_power, carriers, noise_floor, noise_scale, cfg, rng, level)
        if gt is None:
            return {"source_id": source_id, "type": injection_type, "level": level,
                   "outcome": "NO_EMPTY_REGION_FOUND", "expected_triggered": False, "unexpected_types": []}
    elif injection_type in INJECTORS_DRIFT_SCALED:
        drift_stats = get_sweep_cn_drift_stats(source_id)
        modified, gt = INJECTORS_DRIFT_SCALED[injection_type](
            base_power, carriers, noise_floor, noise_scale, cfg, rng, level, drift_stats)
    else:
        modified, gt = INJECTORS_SIMPLE[injection_type](base_power, carriers, noise_floor, noise_scale, cfg, rng, level)

    raw = RawSweepInput(power_dbm=modified, freq_axis_hz=freq_axis,
                        timestamp=timestamps[inject_idx] if has_ts else None)
    result = det.process_sweep(raw)

    target_lo, target_hi = gt.get("bin_range", gt.get("target_carrier_span"))
    result_carrier = _find_result_carrier(result["carriers"], target_lo, target_hi)
    if result_carrier is None:
        outcome = "NOT_DETECTED_AS_CARRIER" if injection_type in ("UNAUTHORIZED_CARRIER", "ADJACENT_CARRIER") else "NO_MATCHING_CARRIER_FOUND"
        return {"source_id": source_id, "type": injection_type, "level": level, "outcome": outcome,
               "expected_triggered": False, "unexpected_types": [], "ground_truth": gt}

    triggered_types = {t["type"] for t in result_carrier["diagnosis"]}

    # NOISE_FLOOR_RISE_POSSIBLE_JAMMING is a SOURCE-LEVEL feature broadcast to every carrier in
    # a sweep — confirmed by direct testing that it can be entirely AMBIENT (present on a clean,
    # unmodified sweep with no injection at all, e.g. early in a source's recording before its
    # 300-sweep rolling baseline settles — the same effect already documented in PROGRESS.md for
    # A_16hr #88). If most OTHER carriers in this same sweep also show it, it's pre-existing in
    # this test window, not caused by this specific injection — excluded from "unexpected" so
    # that field only reflects genuine injection-caused cross-contamination.
    other_carriers = [c for c in result["carriers"] if c is not result_carrier]
    ambient_nfr = False
    if other_carriers:
        n_other_with_nfr = sum(1 for c in other_carriers
                              if any(t["type"] == "NOISE_FLOOR_RISE_POSSIBLE_JAMMING" for t in c["diagnosis"]))
        ambient_nfr = n_other_with_nfr / len(other_carriers) > 0.25
    unexpected = triggered_types - {expected_type, "GENERAL_DEGRADATION"}
    if ambient_nfr:
        unexpected -= {"NOISE_FLOOR_RISE_POSSIBLE_JAMMING"}

    return {"source_id": source_id, "type": injection_type, "level": level, "outcome": "OK",
           "expected_triggered": expected_type in triggered_types,
           "unexpected_types": sorted(unexpected),
           "all_triggered_types": sorted(triggered_types), "ambient_noise_floor_rise": ambient_nfr,
           "ground_truth": gt, "matched_carrier_event": result_carrier["event"],
           "anomaly_score": result_carrier.get("anomaly_score"),
           "anomaly_threshold": result_carrier.get("anomaly_threshold"),
           "flagged": result_carrier.get("flagged")}


N_REPEATS = 5   # different random target-carrier picks per (source, type, level) combo — found by
                # direct testing that a SINGLE random pick is too noisy to be a meaningful result
                # (the same "obvious"-magnitude IN_BAND_TONE injection triggered on 1/5 different
                # randomly-picked A_16hr carriers and not the other 4 — real carrier-to-carrier
                # variance in baseline ripple/noise characteristics, not a bug). Reporting a
                # trigger RATE across repeats is the honest representation; a single Y/N would
                # just be reporting which carrier got picked, not the injection's real sensitivity.


def run_full_matrix(warmup_sweeps=150, n_repeats=N_REPEATS):
    rows = []
    for source_id in SOURCE_IDS:
        for injection_type in ALL_TYPES:
            for level in MAGNITUDE_LEVELS:
                for rep in range(n_repeats):
                    r = run_injection_test(source_id, injection_type, level,
                                          warmup_sweeps=warmup_sweeps, seed=rep)
                    r["repeat"] = rep
                    rows.append(r)
                triggered = sum(1 for r in rows[-n_repeats:] if r["expected_triggered"])
                outcomes = {r["outcome"] for r in rows[-n_repeats:]}
                print(f"[{source_id:8s}] {injection_type:22s} {level:9s} -> "
                     f"triggered={triggered}/{n_repeats}  outcomes={outcomes}", flush=True)
    return rows


if __name__ == "__main__":
    results = run_full_matrix()
    df = pd.DataFrame(results)
    out_path = r"D:\Dhyan\Carrier_Detection\validation\INJECTION_VALIDATION_RESULTS.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")

    print("\n=== Summary: expected-type trigger RATE by (source, type, level), "
         f"{N_REPEATS} repeats each ===")
    summary = df.groupby(["source_id", "type", "level"])["expected_triggered"].agg(["sum", "count"])
    summary["rate"] = summary["sum"] / summary["count"]
    print(summary)
