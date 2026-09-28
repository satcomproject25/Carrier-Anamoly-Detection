"""
Pure WHERE/WHAT/WHY/CONFIDENCE formatting logic for the detail panel — originally split out for
`live_viewer_app.py` (Streamlit, removed 2026-08-18 session 8, replaced by `live_dashboard.py`
/Dash) specifically so it has ZERO dependency on any UI framework and can be unit-tested directly
with plain Python. Still used unchanged by `live_dashboard.py` today. Every function here is a
pure formatter: it takes an existing `diagnose_carrier()`/`instantaneous_check()` trigger dict (or
a `plot_sweep.py` carrier-summary dict) and returns a string — nothing is recomputed, nothing
touches the detector, segmentation, or trained models.
"""

import numpy as np

from interference_diagnosis import OUTLIER_STD_THRESHOLD  # noqa: E402 — reused, not duplicated

# WHAT: plain-language description per diagnosis type, reproduced from the feature -> type
# mapping already documented in interference_diagnosis.py's own module docstring (not a new
# design decision, just written out for a non-expert reading the app).
TYPE_DESCRIPTIONS = {
    "IN_BAND_INTERFERENCE": "Elevated ripple inside the carrier's own plateau region — a "
        "signal-shaped disturbance sitting within this carrier's occupied bandwidth.",
    "SHOULDER_INTERFERENCE_SPECTRAL_REGROWTH": "Power bulging past the carrier's edge before "
        "settling onto the plateau — the shoulder/spectral-regrowth signature of nonlinear "
        "distortion or nearby interference bleeding in.",
    "ADJACENT_CHANNEL_INTERFERENCE": "An unusual number of secondary peaks inside this carrier's "
        "own span — consistent with a nearby channel's energy leaking into this carrier's range.",
    "ASYMMETRIC_EDGE_DISTORTION": "This carrier's rising and falling edges are shaped very "
        "differently (steepness or width ratio far from 1) — asymmetric distortion inconsistent "
        "with a clean, well-formed carrier.",
    "CARRIER_DRIFT": "This carrier's peak frequency moved further sweep-to-sweep than is typical "
        "for this source — consistent with frequency drift.",
    "BANDWIDTH_ANOMALY": "This carrier's occupied bandwidth is far outside ITS OWN historical "
        "range — a sudden widening or narrowing of the signal.",
    "NOISE_FLOOR_RISE_POSSIBLE_JAMMING": "The broadband noise floor across this whole source has "
        "risen well above its own recent history — a source-wide effect, not specific to one "
        "carrier, consistent with possible jamming or a broadband interferer.",
    "UNAUTHORIZED_CARRIER": "A brand-new carrier identity appeared with no reclaimable "
        "predecessor — consistent with an unauthorized/unexpected transmitter coming on air.",
    "CARRIER_DROPOUT": "A previously-tracked carrier's grace period expired with no successor "
        "reclaiming its identity — the carrier has genuinely disappeared.",
    "GENERAL_DEGRADATION": "Flagged anomalous by the trained model, but no single feature is an "
        "extreme individual outlier — a diffuse, non-specific degradation.",
    "PRELIMINARY_INSTANTANEOUS_OUTLIER": "First-observation carrier (no trained-model score "
        "available yet) whose instantaneous shape/level already looks statistically unusual "
        "compared to this source's typical carrier — a lighter-confidence, single-sweep signal.",
}

EVENT_BASED_TYPES = {"UNAUTHORIZED_CARRIER", "CARRIER_DROPOUT"}


def where(carrier_entry, cfg, freq_axis_hz, sweep_index):
    fd, fr = carrier_entry["floor_departure_bin"], carrier_entry["floor_return_bin"]
    parts = [f"sweep #{sweep_index}", f"carrier_id={carrier_entry['carrier_id']}",
            f"bins [{fd}, {fr}]"]
    if cfg["freq_axis_available"] and freq_axis_hz is not None:
        parts.append(f"[{freq_axis_hz[fd]/1e6:.4f}, {freq_axis_hz[fr]/1e6:.4f}] MHz")
    return " | ".join(parts)


def where_disappeared(carrier_entry, cfg, sweep_index):
    """WHERE for a DISAPPEARED carrier — a genuinely different shape from a live tracked
    carrier's summary (`carrier_monitor.py`'s `_carrier_summary()` only has a last-known CENTER
    point — `center_bin_index`/`center_freq_hz` — not a floor-departure/floor-return span, since
    there's no current-sweep geometry for a carrier that's gone). Using `where()` on this shape
    would KeyError; this is the correct formatter for `disappeared_carriers` entries."""
    center_bin = carrier_entry.get("center_bin_index")
    parts = [f"sweep #{sweep_index} (grace period expired THIS sweep)",
            f"carrier_id={carrier_entry['carrier_id']}",
            f"last-known center bin={center_bin}"]
    center_freq = carrier_entry.get("center_freq_hz")
    if cfg["freq_axis_available"] and center_freq is not None and center_freq == center_freq:  # not NaN
        parts.append(f"~{center_freq/1e6:.4f} MHz")
    return " | ".join(parts)


def why(trigger, ref_stats):
    """Note the THREE distinct baseline mechanisms diagnose_carrier() actually uses, and this
    function must distinguish, not conflate (a real bug caught by testing on C_g18 sweep #4300 —
    NOISE_FLOOR_RISE_POSSIBLE_JAMMING was initially mislabeled "event-based" here, since its
    baseline isn't in `ref_stats` — but it DOES have a real feature/value/z, it's just scored
    against a different, ROLLING per-source/per-carrier-id baseline (built fresh at scoring time
    in carrier_monitor.py, not the static TRAIN/all-data `ref_stats` dict), for
    BANDWIDTH_ANOMALY/NOISE_FLOOR_RISE_POSSIBLE_JAMMING specifically):
      1. feature IS in `ref_stats` (the static per-source or TRAIN-split reference passed in) —
         most types — format the z/log_z/percentile range directly from that spec.
      2. feature has a real value/z but ISN'T in `ref_stats` — BANDWIDTH_ANOMALY / NOISE_FLOOR_
         RISE_POSSIBLE_JAMMING's rolling baseline — diagnose_carrier() already wrote a
         human-readable description of THAT baseline into `note`; surface it directly rather
         than guessing or mislabeling this "event-based" (it manifestly isn't — it has a score).
      3. GENERAL_DEGRADATION fallback — no single feature, diffuse combination.
      4. Genuinely event-based (UNAUTHORIZED_CARRIER/CARRIER_DROPOUT) — feature AND value are
         both None, nothing to format.
    """
    feature, value, z = trigger.get("feature"), trigger.get("value"), trigger.get("z_score")

    if feature is not None and ref_stats is not None and feature in ref_stats:
        spec = ref_stats[feature]
        val_str = f"{value:.4g}" if isinstance(value, (int, float)) else str(value)
        if spec["kind"] in ("z", "log_z"):
            center, scale = spec["center"], spec["scale"]
            if spec["kind"] == "log_z":
                lo = float(np.exp(center - OUTLIER_STD_THRESHOLD * scale))
                hi = float(np.exp(center + OUTLIER_STD_THRESHOLD * scale))
            else:
                lo, hi = center - OUTLIER_STD_THRESHOLD * scale, center + OUTLIER_STD_THRESHOLD * scale
            return f"{feature} = {val_str} (z={z}) — this source's normal range: [{lo:.4g}, {hi:.4g}]"
        if spec["kind"] == "percentile":
            return f"{feature} = {val_str} — exceeds this source's own 99th-percentile threshold of {spec['threshold']:.4g}"

    if feature is not None and value is not None:
        val_str = f"{value:.4g}" if isinstance(value, (int, float)) else str(value)
        z_str = f" (z={z})" if z is not None else ""
        note = trigger.get("note") or "compared against its own rolling baseline"
        return f"{feature} = {val_str}{z_str} — {note}"

    if trigger["type"] == "GENERAL_DEGRADATION":
        return ("No single feature is significantly outside its normal range — a diffuse "
                "combination across the whole feature set, not attributable to one cause.")

    return (f"Event-based trigger — {trigger.get('note') or 'the tracking event itself is the signal'}; "
           "no feature value or baseline applies.")


def confidence(trigger):
    if trigger.get("z_score") is None and trigger["type"] in EVENT_BASED_TYPES:
        return f"{trigger['severity']} — event-based, no score (not a feature z-test)"
    if trigger.get("z_score") is None:
        return f"{trigger['severity']} — no z-score computed"
    return f"{trigger['severity']} (z={trigger['z_score']})"


def what(trigger_type):
    return TYPE_DESCRIPTIONS.get(trigger_type, "(no description on file for this type)")
