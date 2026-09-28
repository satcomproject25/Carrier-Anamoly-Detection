"""
Part E: general-purpose carrier plotting tool.

`plot_sweep(source_id, sweep_index, highlight_carrier_id=None)` is the Part-E successor to
`features/segmentation_checkpoint.py`'s one-off visual checkpoint (2026-07-29, segmentation-only,
pre-Phase-4). It reuses that plot's exact visual language for the DSP segmentation itself (raw
spectrum line, floor-departure/rise-end/fall-start/floor-return boundary markers, rise/plateau/
fall sub-region shading — unchanged, zero duplicated logic, same colors/line-styles) and ADDS a
second, spatially separate visual layer: a colored STATUS STRIP above each carrier reflecting its
REAL Phase 4 + gated diagnosis outcome, which did not exist when segmentation_checkpoint.py was
written (Phase 4 didn't exist for the per-carrier architecture until Part C, and the gate into
carrier_monitor.py didn't exist until Part D). This is deliberately a NEW layer, not a repaint of
the existing shading — the existing rise/plateau/fall colors (orange/green/red) already have an
established meaning (sub-region identity) and reusing them for status too would make the two
signals visually indistinguishable. The status strip uses its own distinct color set and sits
above the spectrum, never overlapping the shaded regions.

**Runs the REAL production pipeline, not a re-implementation.** `plot_sweep()` drives
`inference/carrier_monitor.py`'s `CarrierAnomalyDetector` through a warm-up window ending at
`sweep_index` (temporal features — and therefore Phase 4 scores — are undefined without one, same
constraint documented throughout Part D), then reads that stream's own tracked-carrier state
(`det._streams[source_id].prev_tracked`, mutated in place by `segment_carriers()`/
`match_carriers()` inside the detector — it already carries every boundary bin this plot needs,
so there is no second segmentation call and no risk of it disagreeing with what the detector
actually scored) merged with the detector's own `anomaly_score`/`flagged`/`diagnosis` output for
that exact sweep. What you see on this plot is what the live pipeline actually did, not a
plausible reconstruction of it.

Status colors, TWO FAMILIES, never visually mixed (2026-08-13):
  SCORED family (a real Phase 4 score exists — `scoring_status == "SCORED"`):
    - GREEN  — scored, below threshold, not flagged.
    - YELLOW/ORANGE/RED — flagged, colored by the MAX severity across its diagnosis list
               (LOW/MODERATE/HIGH, per interference_diagnosis.py's `add()`) — a carrier flagged
               purely via the EVENT_GATED_TYPES path (UNAUTHORIZED_CARRIER, always severity
               MODERATE per that function, score genuinely None) still gets a real status color
               here despite score=None, which is itself a live demonstration of the Part D fix.
  PRELIMINARY family (score is None — `scoring_status == "PRELIMINARY"`, 2026-08-13):
    - LIGHT BLUE (hatched) — nothing unusual in the lighter-weight instantaneous-only check
               (features/instantaneous_scoring.py, see PROGRESS.md).
    - DARK NAVY (hatched) — flagged by that check.
    Deliberately a DIFFERENT hue family plus a hatch pattern, not a lighter/darker shade of the
    SCORED colors — this is a genuinely lower-confidence signal (fewer features, no trained
    ensemble) and must never be visually mistaken for a full Phase 4 verdict.
  GREY — `scoring_status` missing entirely / no result this sweep (defensive fallback; should be
    rare-to-never now that PRELIMINARY covers every `score is None` case).

Run standalone: `python plot_sweep.py` (renders a handful of demo sweeps across sources — see
`_demo()`).

**2026-08-13 refactor for Part F**: split into `get_sweep_frame_data()` (runs the detector —
expensive, stateful, must execute exactly once per sweep in sequence) and `render_frame()` (pure
matplotlib drawing given already-computed frame data — cheap, side-effect-free, can be called
independently of scoring). `plot_sweep()` itself is now a thin wrapper over these two pieces —
its signature and behavior are UNCHANGED, this is a pure refactor, not a behavior change (Part E's
own demo output is byte-for-byte reproducible). This split exists for
`validation/live_carrier_monitor.py`, which needs to (a) advance ONE continuously-running
detector across many consecutive frames instead of re-warming from scratch every frame, and
(b) resolve which `carrier_id` a synthetic injection landed on — which is only known AFTER
`get_sweep_frame_data()` scores that frame — before deciding what to highlight when rendering it.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\features")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
from extract_features import load_canonical as _load_canonical_uncached, build_source_config  # noqa: E402
from carrier_monitor import CarrierAnomalyDetector, RawSweepInput  # noqa: E402

OUT_DIR = r"D:\Dhyan\Carrier_Detection\validation\plot_sweep_demo"
DEFAULT_WARMUP_SWEEPS = 150

# 2026-08-13 bug fix: get_sweep_frame_data() calls this on EVERY frame (not just once per
# warm-up), and each source's canonical .npz is 11-73MB (the full 'sweeps' array). Uncached, a
# multi-hundred-frame sequence (live_carrier_monitor.py's build_real_sequence()) reloaded that
# same multi-tens-of-MB array from disk hundreds of times in a tight loop — real memory churn,
# root-caused (not just worked around) as the actual cause of repeated numpy MemoryErrors hit
# while testing the 2026-08-13 PRELIMINARY-check wiring (previously misattributed to generic
# "transient system pressure" earlier the same session, before this loop was traced down as the
# actual culprit). Cached per source_id — the canonical data is a fixed, read-only file for the
# lifetime of any process using it, so this is a pure, safe win, not a staleness risk.
_CANONICAL_CACHE = {}


def load_canonical(source_id):
    if source_id not in _CANONICAL_CACHE:
        _CANONICAL_CACHE[source_id] = _load_canonical_uncached(source_id)
    return _CANONICAL_CACHE[source_id]

# ---- sub-region shading + boundary markers: UNCHANGED from segmentation_checkpoint.py ----
RISE_SHADE = "#f6ad55"
PLATEAU_SHADE = "#68d391"
FALL_SHADE = "#fc8181"
DEPARTURE_LINE = "#805ad5"
RISE_END_LINE = "#dd6b20"
FALL_START_LINE = "#38a169"
RETURN_LINE = "#e53e3e"

# ---- diagnosis-status strip colors, deliberately a separate palette from the sub-region/
# boundary-marker colors above. TWO FAMILIES, never visually mixed:
#   SCORED family (grey/green/yellow/orange/red) — a real Phase 4 score exists.
#   PRELIMINARY family (blue, hatched — 2026-08-13) — score is None, only the lighter-weight
#     instantaneous-only check (features/instantaneous_scoring.py) ran. Deliberately a DIFFERENT
#     hue family (not a lighter/darker shade of the SCORED colors) PLUS a hatch pattern, so this
#     lower-confidence signal can never be mistaken for a full Phase 4 verdict at a glance — the
#     whole reason it needed its own status field (scoring_status) in carrier_monitor.py, not a
#     value squeezed into the SCORED color scale.
STATUS_COLORS = {
    "UNSCOREABLE": "#a0aec0",     # grey — no result at all this sweep (should be rare/never for a
                                  # live tracked carrier now that PRELIMINARY covers score=None;
                                  # kept as a defensive fallback, not the normal first-observation case)
    "OK": "#2f855a",             # green — SCORED, below threshold
    "LOW": "#d69e2e",            # yellow — SCORED, flagged, max severity LOW
    "MODERATE": "#dd6b20",       # orange — SCORED, flagged, max severity MODERATE
    "HIGH": "#c53030",           # red — SCORED, flagged, max severity HIGH
    "PRELIM_OK": "#63b3ed",      # light blue — PRELIMINARY, nothing unusual instantaneously
    "PRELIM_FLAGGED": "#1a365d", # dark navy — PRELIMINARY, flagged by the instantaneous check
    "FALLBACK_OK": "#9f7aea",       # violet — UNKNOWN-SOURCE FALLBACK, nothing unusual (2026-08-25)
    "FALLBACK_FLAGGED": "#553c9a",  # dark violet — UNKNOWN-SOURCE FALLBACK, flagged. Deliberately a
                                    # THIRD color family, distinct from both SCORED (green/yellow/
                                    # orange/red) and PRELIM (light/dark blue) -- fallback results
                                    # have no trained model AND no first-observation "would normally
                                    # get a real score" framing; they must never read as either.
}
STATUS_HATCH = {"PRELIM_OK": "//", "PRELIM_FLAGGED": "//",
               "FALLBACK_OK": "xx", "FALLBACK_FLAGGED": "xx"}   # extra non-color cue; FALLBACK gets
                                                                # its OWN hatch pattern (cross, not
                                                                # diagonal), not reused from PRELIM
SEVERITY_RANK = {"LOW": 0, "MODERATE": 1, "HIGH": 2}


def _carrier_status(carrier_result):
    """Maps one carrier's carrier_monitor.py result dict to (status_key, label) for the strip.
    `scoring_status` (2026-08-13) is authoritative for which family applies; falls back to the
    pre-2026-08-13 anomaly_score heuristic for any older result dict that lacks the field."""
    if carrier_result is None:
        return "UNSCOREABLE", "no result this sweep"

    scoring_status = carrier_result.get("scoring_status")
    if scoring_status is None:
        # 2026-08-25: this ALSO needs to distinguish the carrier_monitor.py UNKNOWN-SOURCE
        # FALLBACK path's tracked-carrier summaries from the matched-path's PRELIMINARY case,
        # not just infer PRELIMINARY unconditionally. Both leave `scoring_status` unset, but the
        # PRELIMINARY inference below assumes `flagged` is always a real, meaningful boolean
        # whenever that happens -- true for a matched-path first-observation carrier
        # (`flagged = score_flagged or event_gated_hit or preliminary_hit`), but NEVER true for a
        # fallback-path carrier (`_score_fallback()` hardcodes `flagged=None` unconditionally, by
        # design -- no trained score exists to compute a real boolean from). Left undetected, EVERY
        # fallback carrier fell through to "PRELIM_OK" regardless of its actual diagnosis content,
        # since `carrier_result.get("flagged") and diag` is always False when `flagged` is None --
        # found while wiring the new stations into this dashboard (see PROGRESS.md), not previously
        # exercised since no fallback-path result had ever been rendered through this function
        # before. Detected via the SAME unambiguous signature the fallback path always produces
        # (`anomaly_score` AND `flagged` both None) and routed to its own FALLBACK_* family instead,
        # driven by whether a SPECIFIC (non-GENERAL_DEGRADATION) trigger exists — the diffuse
        # catch-all fires on nearly every carrier in fallback mode (measured 71-100% of carriers,
        # prior batch-scan session), so treating it as "flagged" here would visually swamp the
        # display with red on almost every sweep, defeating the point of a distinct, meaningful
        # signal.
        if carrier_result.get("anomaly_score") is None and carrier_result.get("flagged") is None:
            diag = carrier_result.get("diagnosis", [])
            real_triggers = [d for d in diag if d.get("type") != "GENERAL_DEGRADATION"]
            if real_triggers:
                types = ", ".join(sorted({d["type"] for d in real_triggers}))
                return "FALLBACK_FLAGGED", f"LOW-CONFIDENCE FALLBACK: {types}"
            return "FALLBACK_OK", "LOW-CONFIDENCE FALLBACK: nothing unusual (or only a diffuse, non-specific trigger)"
        scoring_status = "PRELIMINARY" if carrier_result.get("anomaly_score") is None else "SCORED"

    if scoring_status == "PRELIMINARY":
        diag = carrier_result.get("diagnosis", [])
        if carrier_result.get("flagged") and diag:
            types = ", ".join(sorted({d["type"] for d in diag}))
            return "PRELIM_FLAGGED", f"PRELIMINARY (first observation, limited features): {types}"
        return "PRELIM_OK", "PRELIMINARY (first observation, limited features): nothing unusual"

    if scoring_status == "UNSCOREABLE":
        # score is None for a reason OTHER than first observation (e.g. a continuously-tracked
        # carrier with a persistently-degenerate feature) — deliberately NOT run through the
        # preliminary check (see carrier_monitor.py's 2026-08-13 scope-correction note), so this
        # stays genuinely "no verdict," not conflated with either family.
        return "UNSCOREABLE", "score=None, not a first-observation carrier (see carrier_monitor.py)"

    if carrier_result.get("flagged"):
        diag = carrier_result.get("diagnosis", [])
        if diag:
            worst = max(diag, key=lambda d: SEVERITY_RANK.get(d["severity"], -1))
            types = ", ".join(sorted({d["type"] for d in diag}))
            return worst["severity"], f"SCORED: {types} ({worst['severity']})"
        return "MODERATE", "SCORED: flagged (no diagnosis detail)"
    return "OK", f"SCORED: score={carrier_result['anomaly_score']:.2f} < threshold={carrier_result['anomaly_threshold']:.2f}"


def warm_up_detector(source_id, up_to_sweep_index, warmup_sweeps=DEFAULT_WARMUP_SWEEPS):
    """Creates a fresh CarrierAnomalyDetector and advances it through real sweeps
    [up_to_sweep_index - warmup_sweeps, up_to_sweep_index - 1] — i.e. positioned ready to process
    `up_to_sweep_index` itself as the NEXT call, not yet having processed it. Reused by
    `get_sweep_frame_data()` (single-sweep, backward-compatible default path) and by
    `live_carrier_monitor.py` (which then keeps calling `get_sweep_frame_data(..., detector=det)`
    across many consecutive frames instead of re-warming from scratch every frame)."""
    canonical = load_canonical(source_id)
    cfg = build_source_config(canonical)
    sweeps = canonical["sweeps"]
    freq_axis = canonical.get("freq_axis_hz") if cfg["freq_axis_available"] else None
    has_ts = cfg["has_timestamps"]
    timestamps = canonical.get("timestamps") if has_ts else None

    start = max(0, up_to_sweep_index - warmup_sweeps)
    det = CarrierAnomalyDetector(source_id=source_id)
    for i in range(start, up_to_sweep_index):
        raw = RawSweepInput(power_dbm=sweeps[i], freq_axis_hz=freq_axis,
                            timestamp=timestamps[i] if has_ts else None)
        det.process_sweep(raw)
    return det


def get_sweep_frame_data(source_id, sweep_index, detector=None, power_override=None,
                         warmup_sweeps=DEFAULT_WARMUP_SWEEPS):
    """Runs the REAL production detector for exactly one sweep and returns everything
    `render_frame()` needs. This is the ONLY place that calls `det.process_sweep()` — it must run
    exactly once per sweep, in order, since the detector is stateful (rolling history, tracking).

    `detector`: an existing, already-positioned CarrierAnomalyDetector (from `warm_up_detector()`
    or a prior `get_sweep_frame_data()` call) to advance by one sweep — the continuous-stream
    path `live_carrier_monitor.py` uses. If None (Part E's original single-shot behavior,
    unchanged), a fresh detector is created and warmed up first.

    `power_override`: if given, SUBSTITUTES this array for `sweep_index`'s real canonical power
    (freq axis / timestamp still come from `sweep_index`'s real canonical entry, matching how
    `inject_interference.py`'s injectors work — only the power values are synthetic) — this is
    how `live_carrier_monitor.py`'s synthetic-injection sequences feed a modified sweep through
    the exact same scoring path a real one would take.

    Returns a dict: {power, freq_axis_hz, cfg, tracked_geometry, result, warm_range, sweep_index,
    source_id, detector} — `detector` is returned so a caller with `detector=None` can keep
    reusing the one just created/warmed for subsequent frames without re-warming."""
    canonical = load_canonical(source_id)
    cfg = build_source_config(canonical)
    sweeps = canonical["sweeps"]
    n_sweeps = sweeps.shape[0]
    if not (0 <= sweep_index < n_sweeps):
        raise ValueError(f"{source_id}: sweep_index {sweep_index} out of range [0, {n_sweeps})")
    freq_axis = canonical.get("freq_axis_hz") if cfg["freq_axis_available"] else None
    has_ts = cfg["has_timestamps"]
    timestamps = canonical.get("timestamps") if has_ts else None

    warm_range = None
    if detector is None:
        start = max(0, sweep_index - warmup_sweeps)
        detector = warm_up_detector(source_id, sweep_index, warmup_sweeps)
        warm_range = (start, sweep_index - 1)

    power = power_override if power_override is not None else sweeps[sweep_index]
    raw = RawSweepInput(power_dbm=power, freq_axis_hz=freq_axis,
                        timestamp=timestamps[sweep_index] if has_ts else None)
    result = detector.process_sweep(raw)
    tracked_geometry = detector._streams[source_id].prev_tracked

    return {"power": power, "freq_axis_hz": freq_axis, "cfg": cfg,
           "tracked_geometry": tracked_geometry, "result": result, "warm_range": warm_range,
           "sweep_index": sweep_index, "source_id": source_id, "detector": detector}


BINARY_FLAGGED_COLOR = STATUS_COLORS["HIGH"]  # 2026-08-13 (session 6, live-stream mode): reused,
# not invented — per explicit user decision, live-stream mode gets its OWN separate binary
# flagged/unflagged marking (unmarked if clean, this single color if flagged, regardless of
# severity/family), while the STATIC mode keeps its existing 5-7-color severity scheme completely
# unchanged. This is a deliberate divergence between the two modes, not a "the static view is
# secretly already binary" claim — it never was; see PROGRESS.md for the full discussion.
_NOT_FLAGGED_STATUSES = ("OK", "PRELIM_OK", "UNSCOREABLE", "FALLBACK_OK")


def render_frame(frame_data, highlight_carrier_id=None, ax=None, out_path=None, title_suffix="",
                 binary_mode=False):
    """Pure rendering: draws one already-scored frame (from `get_sweep_frame_data()`). No
    detector calls here — safe to call multiple times on the same frame_data (e.g. to re-render
    with a different `highlight_carrier_id`) without affecting the detector's state at all.

    `binary_mode`: when True, draws ONLY a flagged/not-flagged status strip — no strip at all for
    OK/PRELIM_OK/UNSCOREABLE, a single reused color (`BINARY_FLAGGED_COLOR`) for ANY flagged
    status regardless of severity or SCORED-vs-PRELIMINARY family. Built for `live_viewer_app.py`
    (Streamlit)'s live-stream mode, removed 2026-08-18 (session 8) in favor of `live_dashboard.py`
    (Dash) — that replacement does its OWN separate Plotly-native binary rendering
    (`build_figure_and_carriers()`) rather than calling this matplotlib function, so no current
    caller passes `binary_mode=True` — kept here (not deleted) since it's plain matplotlib code
    with no framework dependency, still correct, and cheap to keep working. The default (False)
    reproduces the exact severity-color rendering every other caller already depends on,
    unchanged.

    Returns (fig, ax, carriers_plotted) — same shape `plot_sweep()` has always returned.
    """
    power = frame_data["power"]
    freq_axis_hz = frame_data["freq_axis_hz"]
    cfg = frame_data["cfg"]
    tracked_geometry = frame_data["tracked_geometry"]
    result = frame_data["result"]
    source_id = frame_data["source_id"]
    sweep_index = frame_data["sweep_index"]
    warm_range = frame_data["warm_range"]

    diag_by_id = {c["carrier_id"]: c for c in result["carriers"]}

    x = freq_axis_hz if (cfg["freq_axis_available"] and freq_axis_hz is not None) else np.arange(len(power))
    xlabel = "Frequency (Hz)" if cfg["freq_axis_available"] else "Bin index"

    own_fig = ax is None
    if own_fig:
        fig, ax = plt.subplots(figsize=(14, 6.2))
    else:
        fig = ax.figure

    ax.plot(x, power, lw=0.7, color="#2b6cb0", zorder=3)

    ymin, ymax = float(np.min(power)), float(np.max(power))
    strip_y = ymax + 0.06 * (ymax - ymin)
    strip_h = 0.035 * (ymax - ymin)

    carriers_plotted = []
    for c in tracked_geometry:
        fd, re_, fs, fr = c["floor_departure_bin"], c["rise_end_bin"], c["fall_start_bin"], c["floor_return_bin"]
        pid = c["persistent_id"]

        # --- unchanged sub-region shading + boundary markers (segmentation_checkpoint.py style) ---
        ax.axvspan(x[fd], x[re_], color=RISE_SHADE, alpha=0.30, zorder=1)
        ax.axvspan(x[re_], x[fs], color=PLATEAU_SHADE, alpha=0.30, zorder=1)
        ax.axvspan(x[fs], x[fr], color=FALL_SHADE, alpha=0.30, zorder=1)
        ax.axvline(x[fd], color=DEPARTURE_LINE, lw=1.3, linestyle=":", zorder=2)
        ax.axvline(x[re_], color=RISE_END_LINE, lw=1.3, linestyle="--", zorder=2)
        ax.axvline(x[fs], color=FALL_START_LINE, lw=1.3, linestyle="--", zorder=2)
        ax.axvline(x[fr], color=RETURN_LINE, lw=1.3, linestyle=":", zorder=2)

        # --- diagnosis-status strip, spatially separate from the shading above. PRELIMINARY
        # statuses get a hatch pattern on top of their distinct blue-family color (see
        # STATUS_HATCH) -- an extra non-color cue so this lower-confidence signal is never
        # mistaken for a full SCORED verdict even at a glance / in greyscale printouts.
        # (binary_mode: this whole severity-color scheme is replaced by a plain flagged/
        # not-flagged strip, drawn below instead — see the docstring's `binary_mode` note.)
        status, label = _carrier_status(diag_by_id.get(pid))
        if binary_mode:
            if status not in _NOT_FLAGGED_STATUSES:
                strip = Rectangle((x[fd], strip_y), x[fr] - x[fd], strip_h,
                                  facecolor=BINARY_FLAGGED_COLOR, edgecolor="none", zorder=4)
                ax.add_patch(strip)
        else:
            color = STATUS_COLORS[status]
            hatch = STATUS_HATCH.get(status)
            strip = Rectangle((x[fd], strip_y), x[fr] - x[fd], strip_h,
                              facecolor=color, edgecolor=("white" if hatch else "none"),
                              hatch=hatch, zorder=4)
            ax.add_patch(strip)

        if highlight_carrier_id is not None and pid == highlight_carrier_id:
            box = Rectangle((x[fd], ymin), x[fr] - x[fd], (ymax - ymin) + 2 * (strip_y - ymax) + 3 * strip_h,
                            facecolor="none", edgecolor="black", lw=1.8, linestyle="-", zorder=5)
            ax.add_patch(box)
            ax.annotate(f"carrier {pid}", (x[c["peak_bin"]], power[c["peak_bin"]]),
                       textcoords="offset points", xytext=(0, 10), fontsize=8, fontweight="bold", zorder=6)

        carriers_plotted.append({"carrier_id": pid, "status": status, "label": label,
                                 "floor_departure_bin": fd, "floor_return_bin": fr})

    n_scored_flagged = sum(1 for c in carriers_plotted if c["status"] in ("LOW", "MODERATE", "HIGH"))
    n_preliminary = sum(1 for c in carriers_plotted if c["status"] in ("PRELIM_OK", "PRELIM_FLAGGED"))
    n_preliminary_flagged = sum(1 for c in carriers_plotted if c["status"] == "PRELIM_FLAGGED")
    n_unscoreable = sum(1 for c in carriers_plotted if c["status"] == "UNSCOREABLE")
    warm_note = f" | warm-up sweeps [{warm_range[0]}..{warm_range[1]}]" if warm_range else ""
    title = (f"{source_id} sweep #{sweep_index} — {len(carriers_plotted)} carriers "
            f"({n_scored_flagged} scored-flagged, {n_preliminary} preliminary "
            f"[{n_preliminary_flagged} flagged], {n_unscoreable} unscoreable){warm_note}{title_suffix}")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Power (dBm)")
    ax.set_ylim(ymin, strip_y + strip_h + 0.02 * (ymax - ymin))

    base_legend_elems = [
        Line2D([0], [0], color="#2b6cb0", lw=1.2, label="raw spectrum"),
        Line2D([0], [0], color=DEPARTURE_LINE, lw=1.5, linestyle=":", label="floor departure"),
        Line2D([0], [0], color=RISE_END_LINE, lw=1.5, linestyle="--", label="rise end (plateau start)"),
        Line2D([0], [0], color=FALL_START_LINE, lw=1.5, linestyle="--", label="fall start (plateau end)"),
        Line2D([0], [0], color=RETURN_LINE, lw=1.5, linestyle=":", label="floor return"),
    ]
    if binary_mode:
        legend_elems = base_legend_elems + [
            Rectangle((0, 0), 1, 1, facecolor=BINARY_FLAGGED_COLOR, label="flagged (see detail panel for severity)"),
        ]
    else:
        legend_elems = base_legend_elems + [
            Rectangle((0, 0), 1, 1, facecolor=STATUS_COLORS["UNSCOREABLE"], label="SCORED family: unscoreable"),
            Rectangle((0, 0), 1, 1, facecolor=STATUS_COLORS["OK"], label="SCORED: OK (below threshold)"),
            Rectangle((0, 0), 1, 1, facecolor=STATUS_COLORS["LOW"], label="SCORED: flagged, LOW"),
            Rectangle((0, 0), 1, 1, facecolor=STATUS_COLORS["MODERATE"], label="SCORED: flagged, MODERATE"),
            Rectangle((0, 0), 1, 1, facecolor=STATUS_COLORS["HIGH"], label="SCORED: flagged, HIGH"),
            Rectangle((0, 0), 1, 1, facecolor=STATUS_COLORS["PRELIM_OK"], edgecolor="white",
                     hatch=STATUS_HATCH["PRELIM_OK"], label="PRELIMINARY: OK (limited features)"),
            Rectangle((0, 0), 1, 1, facecolor=STATUS_COLORS["PRELIM_FLAGGED"], edgecolor="white",
                     hatch=STATUS_HATCH["PRELIM_FLAGGED"], label="PRELIMINARY: flagged (limited features)"),
        ]
    ax.legend(handles=legend_elems, fontsize=6.5, loc="upper right", ncol=2)
    fig.tight_layout()

    if out_path:
        fig.savefig(out_path, dpi=115)
    if own_fig and out_path:
        plt.close(fig)

    return fig, ax, carriers_plotted


def plot_sweep(source_id, sweep_index, highlight_carrier_id=None,
              warmup_sweeps=DEFAULT_WARMUP_SWEEPS, out_path=None, ax=None):
    """The Part-E reusable plotting function — UNCHANGED signature/behavior since Part E, now
    implemented as a thin wrapper over `get_sweep_frame_data()` + `render_frame()` (see module
    docstring for why). Renders sweep `sweep_index` of `source_id` with the established
    segmentation visual style PLUS a live diagnosis-status strip per carrier, computed by
    actually running the gated production pipeline.

    Returns (fig, ax, carriers_plotted) where `carriers_plotted` is a list of
    {carrier_id, status, label, floor_departure_bin, floor_return_bin} for programmatic
    inspection/testing, in addition to the rendered figure.
    """
    frame_data = get_sweep_frame_data(source_id, sweep_index, warmup_sweeps=warmup_sweeps)
    return render_frame(frame_data, highlight_carrier_id=highlight_carrier_id, ax=ax, out_path=out_path)


def _demo():
    os.makedirs(OUT_DIR, exist_ok=True)
    demo_targets = [
        ("A_16hr", 500),
        ("B_ec02", 7000),
        ("B_ec05", 5000),
        ("C_g18", 4300),   # inside the flagged Part-5 sweep #4247-4497 window, deliberately
    ]
    for source_id, sweep_index in demo_targets:
        out_path = os.path.join(OUT_DIR, f"{source_id}_sweep{sweep_index}.png")
        fig, ax, carriers = plot_sweep(source_id, sweep_index, out_path=out_path)
        not_concerning = ("OK", "UNSCOREABLE", "PRELIM_OK")
        n_flagged = sum(1 for c in carriers if c["status"] not in not_concerning)
        print(f"{source_id} sweep #{sweep_index}: {len(carriers)} carriers, {n_flagged} flagged -> {out_path}")
        for c in carriers:
            if c["status"] not in not_concerning:
                print(f"    carrier {c['carrier_id']}: {c['status']} — {c['label']}")


if __name__ == "__main__":
    _demo()
