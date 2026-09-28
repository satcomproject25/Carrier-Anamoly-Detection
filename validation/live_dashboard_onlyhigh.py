r"""
============================================================================================
RUN THIS WITH:  D:\Dhyan\myenv\Scripts\python.exe validation\live_dashboard.py
                (plain `python`, run from the project's venv -- see full path above)
DO NOT run with `streamlit run ...` -- this is a DASH app, not Streamlit. Streamlit was fully
uninstalled from this project's venv in session 8; `streamlit run` will fail with
ModuleNotFoundError there, and would be the wrong tool for this file even if some OTHER Python
environment (e.g. an Anaconda "base" env) happens to still have streamlit installed globally --
using a different environment than the project's venv is also its own separate way to get
ModuleNotFoundError (for `dash`, this time), so launch from D:\Dhyan\myenv specifically.
============================================================================================

Live carrier-anomaly monitoring dashboard — Dash/Plotly replacement for the removed
`live_viewer_app.py` (Streamlit). NEW as of 2026-08-18 (session 8) — full replacement, not a
parallel build; Streamlit is fully removed from this project (see PROGRESS.md).

Why the switch: Streamlit has no client-side timer/animation API. Its "live" mode
(`live_viewer_app.py`'s session-6 build) was a server-side `st.rerun()`-inside-`time.sleep()` loop
-- functionally an auto-advancing slideshow of regenerated matplotlib images, not a genuinely live
feed, and it blocked the whole script for the sleep duration every cycle. Dash is built for this:
`dcc.Interval` is a REAL client-side timer (the browser fires it, not a blocked Python sleep), and
`dcc.Graph` is Plotly's native interactive graph object -- updating its `figure` prop patches the
existing chart in place (preserving zoom/pan via `uirevision`) instead of swapping a regenerated
raster image.

Reuses the existing pipeline directly, zero duplicated DSP/scoring/diagnosis logic:
  - `plot_sweep.py`: `get_sweep_frame_data()` / `warm_up_detector()` / `load_canonical()` /
    `build_source_config()` (the real, gated `CarrierAnomalyDetector` pipeline) and
    `_carrier_status()` / `_NOT_FLAGGED_STATUSES` (built for binary-only rendering in session 6's
    Live-stream mode -- reused unchanged here, not reinvented; this file's own flagged-marker
    COLOR is a local override as of session 12's dark-theme redesign, kept separate from
    `plot_sweep.py`'s shared STATUS_COLORS so other tools built on that module are unaffected).
  - `live_carrier_monitor.py`: `build_synthetic_sequence()` (Part B's injectors, unchanged).
  - `diagnosis_panel.py`: `where()` / `where_disappeared()` / `what()` / `why()` / `confidence()`
    (pure, Streamlit-independent formatters -- work identically here with zero changes).

Genuinely NEW here is only the Dash UI chrome: layout, callbacks, and a Plotly-native rendering
function (`build_figure_and_carriers()`) that adapts the SAME segmentation/status data
`render_frame()` (matplotlib) draws into `go.Figure` shapes/traces instead -- a rendering-backend
swap, not a re-derivation of what gets drawn.

Coloring is binary-only, everywhere, all the time (no static severity-color mode exists in this
app -- that distinction only mattered when Streamlit had two separate modes; this IS the only live
view now): unmarked if clean, one reused color (`FLAGGED_BORDER`/`FLAGGED_FILL`, this file's own
dark-theme palette) if flagged, regardless of severity/family. Full severity/z-score detail lives
in the WHERE/WHAT/WHY/CONFIDENCE panel below the graph, unchanged from before.

Server-side state model: this is a single-operator local-network tool (per the request: "local
network only, no internet dependency"), so playback state (the persistent per-source detector for
real-sweep continuous replay, and built synthetic sequences) lives in module-level dicts in this
one long-running process, keyed by source_id / a params-derived cache key -- not per-browser-
session isolated state. `dcc.Store` holds only small, JSON-serializable identifiers (which cache
key, which frame index), never the detector/sequence objects themselves (those aren't
JSON-serializable and don't need to cross the network).

Run: `python validation/live_dashboard.py` (from the project's venv --
`D:\Dhyan\myenv\Scripts\python.exe validation\live_dashboard.py` if not on PATH). Binds to
0.0.0.0:8050 -- reachable from other devices on the local network at
`http://<this-machine's-LAN-IP>:8050`, not just `localhost:8050`.
"""

import sys
import json
import csv
import os
from datetime import datetime, timezone
import numpy as np
import plotly.graph_objects as go
import dash
from dash import Dash, dcc, html, Input, Output, State, ctx

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\validation")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\features")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\models")

from plot_sweep import (                                              # noqa: E402
    get_sweep_frame_data, warm_up_detector, load_canonical, build_source_config,
    DEFAULT_WARMUP_SWEEPS, _carrier_status, _NOT_FLAGGED_STATUSES,
)
from live_carrier_monitor import build_synthetic_sequence                # noqa: E402
from inject_interference import ALL_TYPES, MAGNITUDE_LEVELS              # noqa: E402
from carrier_monitor import CarrierAnomalyDetector, RawSweepInput        # noqa: E402
import diagnosis_panel as dp                                             # noqa: E402

SOURCE_IDS = ["A_16hr", "B_ec02", "B_ec05", "C_g18", "EC03", "EC04", "EC06", "G16"]

# EC03/EC04/EC06/G16 (originally onboarded 2026-08-25 as raw-spectrum-only, unknown-source-
# fallback stations -- n_bins=5000, streamed from 541-753MB .jsonl files, no trained model)
# now have FULL trained, deployed models (data/canonical/{EC03,EC04,EC06,G16}.npz +
# models/{EC03,EC04,EC06,G16}/, verified bit-exact per PROGRESS.md sessions 39/40/45/51) and are
# therefore promoted into SOURCE_IDS above, using the SAME load_canonical()/warm_up_detector()
# trained-model path as the original 4 stations -- no separate fallback machinery needed for them
# anymore. NEW_SOURCE_IDS is kept as an empty list (not deleted) purely so every other reference
# to it below (the now-dead _advance_new_source()/_NEW_SOURCE_STREAM fallback-streaming path, and
# the is_fallback UI styling, which is driven by matched_source_id, not this list) keeps working
# unchanged -- for these 4 stations, matched_source_id will now correctly come back populated,
# so is_fallback naturally evaluates False for them with zero further code changes.
NEW_SOURCE_IDS = []
_NEW_SOURCE_FILES = {}
REAL_SOURCE_IDS = SOURCE_IDS + NEW_SOURCE_IDS

# =====================================================================
# severity filtering -- LOW and MODERATE-severity triggers are still computed by the real model
# (so the validated F1/FPR/recall numbers in PROGRESS.md and the report are completely
# unaffected -- this is a DISPLAY/LOGGING filter only, not a change to the underlying model or
# threshold), but are no longer treated as "flagged" for display/counting/logging purposes, per
# explicit request: given the report's own honestly-documented moderate recall, only HIGH-
# confidence flags are surfaced in live production/demo use, trading further recall for fewer,
# more trustworthy alerts. A carrier only counts as flagged here if it has AT LEAST ONE HIGH-
# severity trigger; a carrier whose only trigger(s) are LOW or MODERATE is treated as visually
# clean, exactly like a carrier with zero triggers at all -- SEVERITY_DISPLAY_MIN below is the
# single place this threshold lives, so it (and thus how much of the real recall/FPR trade-off is
# exposed to an operator) can be changed without touching any other logic. Was "MODERATE" through
# session-50-era work; changed to "HIGH" per explicit request after reviewing the deployed-model
# verification's real, magnitude-broken-down catch rates.
SEVERITY_RANK = {"LOW": 0, "MODERATE": 1, "HIGH": 2}
SEVERITY_DISPLAY_MIN = "HIGH"


def _carrier_diagnosis_triggers(result, carrier_id):
    """Returns carrier_id's raw diagnosis trigger list from a result dict (result["carriers"]),
    or [] if the carrier isn't present / has no diagnosis field -- a carrier can have zero, one,
    or several triggers (one per diagnosis type that independently fired)."""
    diag_by_id = {c["carrier_id"]: c for c in result.get("carriers", [])}
    return diag_by_id.get(carrier_id, {}).get("diagnosis", [])


def _carrier_display_flagged(result, carrier_id):
    """True only if carrier_id has at least one trigger at or above SEVERITY_DISPLAY_MIN --
    the single gate every display/count/CSV-logging decision below goes through, so LOW-only
    carriers are suppressed consistently everywhere, not just in one place."""
    min_rank = SEVERITY_RANK[SEVERITY_DISPLAY_MIN]
    return any(SEVERITY_RANK.get(t.get("severity"), -1) >= min_rank
              for t in _carrier_diagnosis_triggers(result, carrier_id))


# =====================================================================
# CSV flag logging -- one row per (carrier, trigger) the first time it's SEEN at
# display-flagged severity (MODERATE/HIGH) in a given sweep. One file per station, created on
# first write; append-only, header written once. Column order deliberately matches what an
# operator/report would want to scan first (when/where/what/how-confident) before the raw
# numeric payload.
# =====================================================================
_CSV_LOG_DIR = r"D:\Dhyan\Carrier_Detection\logs\flags"
_CSV_HEADER = ["logged_at_utc", "source_id", "sweep_index", "carrier_id", "bin_start", "bin_end",
              "severity", "diagnosis_type", "z_score", "what", "why"]
_CSV_ALREADY_INITIALISED = set()   # source_id -> True, once this run has confirmed/created its file


def _csv_path_for_source(source_id):
    return os.path.join(_CSV_LOG_DIR, f"{source_id}_flags.csv")


def _ensure_csv_ready(source_id):
    os.makedirs(_CSV_LOG_DIR, exist_ok=True)
    path = _csv_path_for_source(source_id)
    if source_id not in _CSV_ALREADY_INITIALISED:
        write_header = not os.path.exists(path)
        if write_header:
            with open(path, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(_CSV_HEADER)
        _CSV_ALREADY_INITIALISED.add(source_id)
    return path


def log_flagged_carriers_to_csv(frame_data, carriers_plotted):
    """Appends one CSV row per (carrier, trigger) that is display-flagged (MODERATE/HIGH) in this
    sweep. Called once per rendered frame from render() -- safe to call every frame; a clean
    sweep with nothing display-flagged writes nothing (not even a header-only touch beyond the
    one-time _ensure_csv_ready() call).

    WHY/CONFIDENCE text is produced via dp.why()/dp.confidence() -- the SAME diagnosis_panel.py
    formatters the on-screen detail panel already uses -- rather than reading raw trigger dict
    keys directly, so this stays correct even if diagnosis_panel.py's internal trigger schema
    changes; z_score is read defensively via .get() with a couple of plausible key names, since
    the exact key wasn't independently confirmed here."""
    result = frame_data["result"]
    source_id = frame_data["source_id"]
    sweep_index = frame_data["sweep_index"]
    cfg = frame_data["cfg"]
    detector = frame_data["detector"]
    is_fallback = result.get("matched_source_id") is None
    ref_stats_by_type = ({"instantaneous": None, "source": None} if is_fallback else
                         {"instantaneous": detector._profiles[source_id]["instantaneous_stats"],
                          "source": detector._profiles[source_id]["source_stats"]})

    flagged = [c for c in carriers_plotted if c["status"] not in _NOT_FLAGGED_STATUSES]
    if not flagged:
        return
    path = _ensure_csv_ready(source_id)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for c in flagged:
        cid = c["carrier_id"]
        for trig in _carrier_diagnosis_triggers(result, cid):
            if SEVERITY_RANK.get(trig.get("severity"), -1) < SEVERITY_RANK[SEVERITY_DISPLAY_MIN]:
                continue   # this specific trigger is LOW even though the carrier has >=1 qualifying one
            ref_stats = ref_stats_by_type.get(trig.get("scope", "source"))
            z_val = trig.get("z", trig.get("z_score", ""))
            rows.append([
                now, source_id, sweep_index, cid,
                c.get("floor_departure_bin"), c.get("floor_return_bin"),
                trig.get("severity"), trig.get("type"), z_val,
                dp.what(trig.get("type")),
                dp.why(trig, ref_stats),
            ])
    if rows:
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
# Dark ops-console palette (session 12) -- kept local to this file rather than changed in
# plot_sweep.py, since that module's own STATUS_COLORS/BINARY_FLAGGED_COLOR are shared with other
# (non-redesigned) tools; this dashboard overrides colors for its own rendering only.
RAW_LINE_COLOR = "#00d4ff"           # cyan spectrum trace
PLOT_BG = "#131820"                  # matches --surface
PLOT_GRID = "#1e2530"                # matches --border
PLOT_INK = "#e8edf2"                 # matches --ink
FLAGGED_FILL = "rgba(255, 61, 61, 0.25)"
FLAGGED_BORDER = "#ff3d3d"
# 2026-08-25: LOW-CONFIDENCE FALLBACK marking for the 4 new stations -- deliberately a THIRD,
# distinct color family (violet), not a shade of FLAGGED_* (red, SCORED-source flagged carriers)
# or the sidebar's own --accent amber (already used pervasively for UI chrome, not carrier
# status) -- see build_figure_and_carriers()/build_detail_children() for where this is used, and
# plot_sweep.py's matching FALLBACK_OK/FALLBACK_FLAGGED STATUS_COLORS entries for the underlying
# status-family split this mirrors.
FALLBACK_FLAGGED_FILL = "rgba(168, 85, 247, 0.25)"
FALLBACK_FLAGGED_BORDER = "#a855f7"


def _empty_dark_figure():
    """Dark-themed placeholder so the graph's IDLE state (before any Play click) shows the panel
    background, not Plotly's own default white canvas -- confirmed live as a jarring bright
    rectangle against the rest of the dark UI before this was added."""
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, font=dict(color=PLOT_INK),
        xaxis=dict(showgrid=True, gridcolor=PLOT_GRID, zeroline=False, color=PLOT_INK),
        yaxis=dict(showgrid=True, gridcolor=PLOT_GRID, zeroline=False, color=PLOT_INK),
        height=560, margin=dict(l=60, r=20, t=60, b=50),
        annotations=[dict(text="Select a mode and click Play to begin", showarrow=False,
                          xref="paper", yref="paper", x=0.5, y=0.5, font=dict(size=15, color="#8a94a3"))],
    )
    return fig


EMPTY_DARK_FIGURE = _empty_dark_figure()

# =====================================================================
# server-side state (this process only -- see module docstring)
# =====================================================================
_REAL_STATE = {}    # source_id -> {"detector":..., "idx": int, "origin_start": int}
_SYNTH_CACHE = {}   # cache_key -> {"seq": [...], "meta": {...}}


def _advance_real(source_id, real_start, advance):
    """(Re)warms a persistent per-source detector the first time `real_start` is seen (or changes
    -- an explicit restart), otherwise just continues it. `advance=False` renders the CURRENT
    position without moving forward (used for the immediate frame a Play click shows before the
    first timer tick); `advance=True` is the normal per-tick step."""
    canonical = load_canonical(source_id)
    n_sweeps = int(canonical["n_sweeps"])
    real_start = int(real_start) if real_start is not None else 0
    state = _REAL_STATE.get(source_id)
    just_warmed_up = state is None or state.get("origin_start") != real_start
    if just_warmed_up:
        # This is the slow path -- DEFAULT_WARMUP_SWEEPS sequential process_sweep() calls,
        # measured at roughly 15-30s per source (up to ~70s on the very first request after this
        # process starts, one-time model/import cost). `render()` uses `just_warmed_up` to keep
        # the client-side dcc.Interval OFF across this call, rather than arming it before this
        # blocking work starts -- see the fix note on `toggle_play()` for why that ordering
        # mattered (a live-tested backlog bug, not a hypothetical one).
        det = warm_up_detector(source_id, real_start, warmup_sweeps=DEFAULT_WARMUP_SWEEPS)
        state = {"detector": det, "idx": real_start, "origin_start": real_start}
        _REAL_STATE[source_id] = state
    idx = min(state["idx"], n_sweeps - 1)
    frame_data = get_sweep_frame_data(source_id, idx, detector=state["detector"])
    if advance:
        state["idx"] = min(idx + 1, n_sweeps - 1)
    return frame_data, (idx >= n_sweeps - 1), just_warmed_up


# ---------------------------------------------------------------------------------------------
# New stations (2026-08-25): streamed from .jsonl (no canonical .npz, no random access -- files
# are 541-753MB, memory-unsafe to load fully) through carrier_monitor.py's UNKNOWN-SOURCE
# FALLBACK path, one independent CarrierAnomalyDetector() stream per station. Mirrors
# _advance_real()'s exact (frame_data, at_end, just_warmed_up) contract so render()'s call site
# only needs a one-line dispatch, not a rewrite -- everything downstream of that call
# (build_figure_and_carriers/build_detail_children/status-line formatting) is unchanged code.
# ---------------------------------------------------------------------------------------------
_NEW_SOURCE_STREAM = {}   # source_id -> {"file", "detector", "origin_start", "next_line_idx",
                          #               "last_frame_data", "eof"}

# "Priming" -- NOT the same kind of warm-up _advance_real() does, and deliberately named
# differently. Reasoning (see also the PROGRESS.md session entry for this task):
#   1. The fallback path has NO pre-trained, pre-computed reference distribution to align the
#      detector's rolling state with (unlike the matched path's `prof["source_stats"]`, loaded
#      once from a TRAIN-split parquet at profile-load time) -- its own `source_stats` is built
#      INCREMENTALLY from the live stream itself (`_score_fallback()`'s `fallback_carrier_buf`),
#      starting from whatever sweep streaming begins at, warm-up phase or not.
#   2. Confirmed via the prior batch-scan session: these 4 stations carry ~30+ simultaneously-
#      tracked carriers per sweep, so `MIN_BASELINE_CARRIER_OBS=30` (carrier_monitor.py) is
#      satisfied WITHIN THE FIRST SWEEP of any fresh stream -- inserting a silent priming phase
#      before the user's chosen start index does NOT change when the fallback reference distribution
#      becomes usable; that happens immediately regardless of where streaming starts.
#   3. What a short priming phase DOES still buy: TEMPORAL features (frame_freq_delta_*,
#      rolling_cn_std, per-carrier bandwidth history) need at least one, and ideally several, PRIOR
#      sweeps of the SAME persistent_id to be non-NaN/non-degenerate -- without any priming, the
#      first VISIBLE frame's carriers would all look cold-started even though real prior sweeps
#      exist in the file. Reusing DEFAULT_WARMUP_SWEEPS (150) as the priming length keeps this
#      predictable and consistent with the existing sources' own UX, mentally, even though its
#      COST PROFILE is very different: measured at ~18-30ms/sweep for this exact fallback path on
#      these exact 4 files (prior batch-scan session), so 150 sweeps costs roughly 3-5 seconds
#      here, not the existing sources' 15-90s (that cost is inherent to warm_up_detector()'s own
#      per-sweep work on the MATCHED path -- this path's per-sweep cost is simply cheaper).
NEW_SOURCE_PRIMING_SWEEPS = DEFAULT_WARMUP_SWEEPS


def _new_source_record_to_raw(rec):
    """Ported UNCHANGED from the prior batch-scan session's phase2_harness.py record_to_raw() --
    reused, not rebuilt, per this task's explicit instruction. amplitude_data -> power_dbm;
    center_mhz/span_mhz -> a derived freq_axis_hz (no explicit frequency array in this data);
    string timestamp -> np.datetime64."""
    power = np.asarray(rec["amplitude_data"], dtype="float32")
    n_points = rec["n_points"]
    center_mhz = rec["center_mhz"]
    span_mhz = rec["span_mhz"]
    freq_axis_hz = np.linspace(center_mhz - span_mhz / 2.0, center_mhz + span_mhz / 2.0,
                               n_points, dtype="float64") * 1e6
    ts = np.datetime64(rec["timestamp"].replace(" ", "T"))
    return power, freq_axis_hz, ts


def _new_source_read_sweep(f, det, source_id, cfg, line_idx):
    """Reads and scores exactly ONE line -- returns a frame_data dict matching
    get_sweep_frame_data()'s exact shape ({power, freq_axis_hz, cfg, tracked_geometry, result,
    warm_range, sweep_index, source_id, detector}), or None at EOF/a blank line."""
    line = f.readline()
    if not line or not line.strip():
        return None
    rec = json.loads(line)
    power, freq_axis_hz, ts = _new_source_record_to_raw(rec)
    raw = RawSweepInput(power_dbm=power, freq_axis_hz=freq_axis_hz, timestamp=ts)
    result = det.process_sweep(raw)
    # carrier_monitor.py's unknown-source fallback stream state always lives under the literal
    # key "__unknown__", regardless of this station's own source_id (see _score_fallback()) --
    # NOT det._streams[source_id], which would KeyError (no matched-source stream was ever created).
    tracked_geometry = det._streams["__unknown__"].prev_tracked
    return {"power": power, "freq_axis_hz": freq_axis_hz, "cfg": cfg,
           "tracked_geometry": tracked_geometry, "result": result, "warm_range": None,
           "sweep_index": line_idx, "source_id": source_id, "detector": det}


def _advance_new_source(source_id, real_start, advance):
    """Streaming equivalent of _advance_real() for the 4 new .jsonl-backed stations. Same
    (frame_data, at_end, just_warmed_up) return contract."""
    real_start = int(real_start) if real_start is not None else 0
    state = _NEW_SOURCE_STREAM.get(source_id)
    just_reopened = state is None or state.get("origin_start") != real_start

    if just_reopened:
        old_file = state.get("file") if state else None
        if old_file is not None:
            old_file.close()
        path = _NEW_SOURCE_FILES[source_id]

        # cfg (n_bins/freq-axis-available/has_timestamps) is static for the whole file (Phase 1
        # of the prior batch-scan session confirmed n_points/center_mhz/span_mhz are constant
        # per station) -- peek the FIRST line once, separately from the real streaming handle
        # below, purely to build it. Cheap (one ~50-75KB line) and far simpler/safer than trying
        # to derive it lazily mid-skip on a text-mode file handle (tell()/seek() on text streams
        # is not a reliable arbitrary-byte-offset API).
        with open(path, "r", encoding="utf-8") as peek:
            first_line = peek.readline()
        if not first_line.strip():
            raise ValueError(f"{source_id}: {path} is empty or unreadable")
        n_points = json.loads(first_line)["n_points"]
        cfg = build_source_config({"source_id": source_id, "n_bins": n_points,
                                  "freq_axis_hz": None, "freq_axis_available": True,
                                  "has_timestamps": True})

        f = open(path, "r", encoding="utf-8")
        # Fresh, INDEPENDENT fallback stream for this one station -- deliberately NOT shared
        # across the 4 new stations (or reused across restarts): _score_fallback()'s internal
        # state (fallback_carrier_buf, prev_tracked, its own sweep_index counter) all live under
        # the single "__unknown__" key on ONE CarrierAnomalyDetector instance, so sharing one
        # detector across stations would silently conflate their carrier histories.
        det = CarrierAnomalyDetector()
        skip_to = max(0, real_start - NEW_SOURCE_PRIMING_SWEEPS)
        # Track the ACTUAL number of lines skipped, not the requested count -- if real_start is
        # beyond this file's true length (~10.8K-14.4K sweeps/file), readline() hits EOF partway
        # through and `line_idx` must reflect that, not silently assume every requested line was
        # consumed (that mismatch would leave line_idx pointing past where the handle actually is).
        line_idx = 0
        hit_eof_while_skipping = False
        for _ in range(skip_to):
            if not f.readline():
                hit_eof_while_skipping = True
                break
            line_idx += 1
        last_fd = None
        if not hit_eof_while_skipping:
            while line_idx < real_start:
                fd = _new_source_read_sweep(f, det, source_id, cfg, line_idx)
                if fd is None:
                    break
                last_fd = fd
                line_idx += 1
        state = {"file": f, "detector": det, "origin_start": real_start, "cfg": cfg,
                "next_line_idx": line_idx, "last_frame_data": last_fd, "eof": False}
        _NEW_SOURCE_STREAM[source_id] = state

    if state["eof"]:
        # Already exhausted this file -- mirrors _advance_real()'s own idx-clamping behavior at
        # n_sweeps-1: no error, no new content, just keep showing the last real frame. May be
        # None (real_start was beyond EOF from the very first call for this combination, so
        # nothing was ever primed) -- render()'s caller must treat a None frame_data as "no data
        # yet", the same way synth mode treats "no sequence built yet".
        return state["last_frame_data"], True, just_reopened

    fd = _new_source_read_sweep(state["file"], state["detector"], source_id, state["cfg"],
                                state["next_line_idx"])
    if fd is None:
        state["eof"] = True
        state["file"].close()
        state["file"] = None
        return state["last_frame_data"], True, just_reopened

    state["last_frame_data"] = fd
    if advance:
        state["next_line_idx"] += 1
    return fd, False, just_reopened


# =====================================================================
# Plotly-native rendering -- adapts what render_frame() (matplotlib) draws into go.Figure
# shapes/traces. Binary-only: no strip at all for a clean carrier, one reused color for any
# flagged one, regardless of severity/family (full detail is the panel below, not this plot).
# =====================================================================

def build_figure_and_carriers(frame_data):
    power = np.asarray(frame_data["power"], dtype=float)
    freq_axis_hz = frame_data["freq_axis_hz"]
    cfg = frame_data["cfg"]
    tracked_geometry = frame_data["tracked_geometry"]
    result = frame_data["result"]
    source_id = frame_data["source_id"]
    sweep_index = frame_data["sweep_index"]

    # 2026-08-25: LOW-CONFIDENCE FALLBACK sources (the 4 new stations) must never render
    # indistinguishably from a SCORED source's flagged carriers -- a real demo-confusion risk the
    # task explicitly called out. matched_source_id is None ONLY on the unknown-source fallback
    # path (see carrier_monitor.py's _score_fallback()); every one of the 4 established sources
    # always sets it to their own source_id.
    is_fallback = result.get("matched_source_id") is None
    flagged_fill = FALLBACK_FLAGGED_FILL if is_fallback else FLAGGED_FILL
    flagged_border = FALLBACK_FLAGGED_BORDER if is_fallback else FLAGGED_BORDER
    flagged_line_dash = "dash" if is_fallback else "solid"  # non-color cue too, not color-alone

    diag_by_id = {c["carrier_id"]: c for c in result["carriers"]}
    if cfg["freq_axis_available"] and freq_axis_hz is not None:
        x = np.asarray(freq_axis_hz, dtype=float)
        xlabel = "Frequency (Hz)"
    else:
        x = np.arange(len(power), dtype=float)
        xlabel = "Bin index"

    ymin, ymax = float(np.min(power)), float(np.max(power))

    shapes = []
    carriers_plotted = []
    any_flagged = False
    for c in tracked_geometry:
        fd, fr = c["floor_departure_bin"], c["floor_return_bin"]
        pid = c["persistent_id"]

        # ONLY a flagged carrier gets any marking at all -- a clean carrier is the plain spectrum
        # line and nothing else (session 10 fix: the 4 per-carrier boundary-marker lines kept
        # intentionally in session 9's shading-removal fix -- departure/rise-end/fall-start/return,
        # dotted/dashed -- still cluttered a busy REAL sweep at scale: 4 lines x 32 carriers = 128
        # overlaid lines on one A_16hr frame, confirmed via live screenshot at start_sweep_index=500,
        # drowning out the one flagged carrier. Removed entirely, not thinned -- this view's whole
        # design point (session 8) is binary flagged/unflagged; boundary-shape detail belongs to
        # validation/plot_sweep.py's own static severity-color tool, not this live view).
        status, label = _carrier_status(diag_by_id.get(pid))
        # Per explicit request: LOW-severity SCORED flags are suppressed from display/counting/
        # logging (still computed by the real model underneath -- this is display-only, the
        # validated F1/FPR/recall figures in PROGRESS.md/the report are unaffected). Deliberately
        # narrow: only the SCORED-family "LOW" status is touched here -- PRELIM_FLAGGED and
        # FALLBACK_FLAGGED are untouched, since those are a different confidence family entirely
        # (see plot_sweep.py's _carrier_status()), not a severity level this request was about.
        display_status = "OK" if status == "LOW" else status
        if display_status not in _NOT_FLAGGED_STATUSES:
            any_flagged = True
            # A semi-transparent fill spanning the carrier's REAL bin span, so it reads as a
            # highlighted region attached to the carrier's actual position -- replaces the prior
            # thin strip floating near the top of the y-axis, which was disconnected from the
            # carrier's own position and easy to miss on a busy sweep. session 12: given a bright
            # 2px border (--flagged, #ff3d3d) for salience on a busy 32-carrier sweep, drawn
            # `layer="above"` (not "below") so the border renders crisp and unbroken rather than
            # partly occluded by the spectrum trace wherever the two cross -- the fill stays only
            # 25% opaque, so the cyan trace still reads clearly through it either way. Only the
            # styling changed here; x0/x1 are still the exact floor_departure/floor_return bins
            # segmentation returned, unchanged from session 10.
            shapes.append(dict(type="rect", xref="x", yref="y", x0=x[fd], x1=x[fr],
                               y0=ymin, y1=ymax, fillcolor=flagged_fill,
                               line=dict(color=flagged_border, width=2, dash=flagged_line_dash),
                               layer="above"))

        carriers_plotted.append({"carrier_id": pid, "status": display_status, "label": label,
                                 "floor_departure_bin": fd, "floor_return_bin": fr})

    n_flagged = sum(1 for c in carriers_plotted if c["status"] not in _NOT_FLAGGED_STATUSES)
    title = f"{source_id} — sweep #{sweep_index} — {len(carriers_plotted)} carriers, {n_flagged} flagged"
    if is_fallback:
        title += "  ⚠ LOW-CONFIDENCE FALLBACK (no trained model)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=power, mode="lines", line=dict(color=RAW_LINE_COLOR, width=1.5),
        name="raw spectrum", hovertemplate="%{x:,.0f}<br>%{y:.2f} dBm<extra></extra>",
    ))
    # a real (invisible) trace purely so "flagged" gets a legend entry -- shapes never appear in
    # a Plotly legend on their own, and identity must never be color-alone (only entity here).
    if True:  # always show the legend key, even on a frame with 0 flagged carriers -- consistent UI
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=11, color=flagged_border, symbol="square"),
            name=("flagged (LOW-CONFIDENCE FALLBACK, see panel below)" if is_fallback
                 else "flagged (see panel below for severity)"),
        ))

    fig.update_layout(
        shapes=shapes, title=dict(text=title, font=dict(size=14, color=PLOT_INK)),
        paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, font=dict(color=PLOT_INK),
        xaxis=dict(title=xlabel, showgrid=True, gridcolor=PLOT_GRID, zeroline=False, color=PLOT_INK,
                  linecolor=PLOT_GRID),
        yaxis=dict(title="Power (dBm)", range=[ymin, ymax + 0.05 * (ymax - ymin)],
                  showgrid=True, gridcolor=PLOT_GRID, zeroline=False, color=PLOT_INK,
                  linecolor=PLOT_GRID),
        height=560, margin=dict(l=60, r=20, t=60, b=50),
        showlegend=True, legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                                     bgcolor="rgba(0,0,0,0)", font=dict(color=PLOT_INK)),
        hovermode="closest",
        hoverlabel=dict(bgcolor=PLOT_BG, font_color=PLOT_INK, bordercolor=PLOT_GRID),
        uirevision="keep-zoom",  # keeps the user's zoom/pan across every auto-refresh -- a
                                 # genuinely live chart must not yank the view back on every update
    )
    return fig, carriers_plotted, any_flagged


# =====================================================================
# detail panel -- reuses diagnosis_panel.py's pure formatters directly, zero duplicated logic
# =====================================================================

def _one_carrier_panel(carrier_id, status_label, where_str, diagnosis, ref_stats):
    trig_blocks = []
    for trig in diagnosis:
        trig_blocks.append(html.Details([
            html.Summary(f"{trig['type']}  ({trig['severity']})", className="trigger-summary"),
            # WHAT is prose (regular font); WHERE/WHY/CONFIDENCE carry the numeric payload
            # (bin ranges, z-scores, ratios) and get the monospace treatment (session 12) so they
            # read as instrument-grade data rather than generic text -- styling only, the strings
            # themselves still come unchanged from diagnosis_panel.py's own formatters.
            html.Div([
                html.Div([html.Div("WHAT", className="field-label"),
                         html.P(dp.what(trig["type"]), className="field-value")]),
                html.Div([html.Div("WHERE", className="field-label"),
                         html.P(where_str, className="field-value-mono")]),
                html.Div([html.Div("WHY", className="field-label"),
                         html.P(dp.why(trig, ref_stats), className="field-value-mono")]),
                html.Div([html.Div("CONFIDENCE", className="field-label"),
                         html.P(dp.confidence(trig), className="field-value-mono")]),
            ], className="detail-grid"),
        ], open=True, className="trigger-details"))
    return html.Div([
        html.H4(f"Carrier {carrier_id} — {status_label}"),
        html.P(where_str, className="where-caption"),
        *trig_blocks,
    ], className="carrier-panel")


def build_detail_children(frame_data, carriers_plotted):
    result = frame_data["result"]
    cfg = frame_data["cfg"]
    freq_axis_hz = frame_data["freq_axis_hz"]
    sweep_index = frame_data["sweep_index"]
    source_id = frame_data["source_id"]
    detector = frame_data["detector"]
    is_fallback = result.get("matched_source_id") is None
    if is_fallback:
        # LOW-CONFIDENCE FALLBACK: detector._profiles only holds the 4 TRAINED sources
        # (CarrierAnomalyDetector() loads those as its match candidates, never source_id itself,
        # since no trained profile exists for it) -- detector._profiles[source_id] would KeyError
        # here. diagnosis_panel.why() already handles ref_stats=None gracefully (falls through to
        # formatting directly from the trigger's own feature/value/z/note, which every fallback
        # trigger already carries -- see diagnosis_panel.py's own docstring) -- arguably MORE
        # honest for fallback results than the "this source's normal range: [...]" framing the
        # ref_stats-based path implies, since that reference is far less validated here.
        ref_stats_by_type = {"instantaneous": None, "source": None}
    else:
        ref_stats_by_type = {
            "instantaneous": detector._profiles[source_id]["instantaneous_stats"],
            "source": detector._profiles[source_id]["source_stats"],
        }

    children = [html.H3("Flagged carrier details")]
    if is_fallback:
        children.append(html.Div([
            html.Span("⚠ LOW-CONFIDENCE FALLBACK SCORING", className="fallback-badge"),
            html.P("No trained model exists for this station yet. Results use only the stream's "
                  f"own recently-accumulated carrier history ({result.get('confidence_label', '')})"
                  " — not a validated detection. Do not present as equivalent to the 4 scored "
                  "sources.", className="fallback-note"),
        ], className="fallback-warning-banner"))
    flagged = [c for c in carriers_plotted if c["status"] not in _NOT_FLAGGED_STATUSES]
    if not flagged:
        children.append(html.P("No flagged carriers this sweep.", className="empty-note"))
    else:
        diag_by_id = {c["carrier_id"]: c for c in result["carriers"]}
        for entry in flagged:
            dr = diag_by_id.get(entry["carrier_id"], {})
            diagnosis = dr.get("diagnosis", [])
            ref_stats = (ref_stats_by_type["instantaneous"] if entry["status"] == "PRELIM_FLAGGED"
                        else ref_stats_by_type["source"])
            where_str = dp.where(entry, cfg, freq_axis_hz, sweep_index)
            children.append(_one_carrier_panel(entry["carrier_id"], entry["status"], where_str,
                                              diagnosis, ref_stats))

    children.append(html.H3("Carriers that disappeared this sweep"))
    disappeared = [c for c in result.get("disappeared_carriers", []) if c.get("diagnosis")]
    if not disappeared:
        children.append(html.P("No carriers disappeared (grace period expired) this sweep.",
                              className="empty-note"))
    else:
        for entry in disappeared:
            where_str = dp.where_disappeared(entry, cfg, sweep_index)
            children.append(_one_carrier_panel(entry["carrier_id"], "DISAPPEARED", where_str,
                                              entry["diagnosis"], ref_stats_by_type["source"]))
    return children


# =====================================================================
# app / layout
# =====================================================================

app = Dash(__name__)
app.title = "Carrier Anomaly Live Dashboard"

app.layout = html.Div([
    html.Div([
        html.H1("Carrier Anomaly Live Dashboard"),
        html.P("Genuinely live: dcc.Interval (client-side timer) drives every update — no page "
              "reload, no server-blocking sleep loop.", className="subtitle"),
    ], className="header"),

    # ---- top status bar (session 12): the at-a-glance readout, separate from the plot's own
    # title -- large enough to read from across a room. State dot/text is driven by its own small
    # callback (update_run_state, below) off play-btn's label + whether anything has rendered yet;
    # source/sweep/flags come from render()'s own per-frame computation, the same numbers the
    # sidebar status-line and plot title already show, just surfaced here more prominently.
    html.Div([
        html.Div([
            html.Div(id="status-dot", className="status-dot status-dot-idle"),
            html.Span("IDLE", id="topbar-state-text", className="topbar-state-text"),
        ], className="status-state"),
        html.Div(className="topbar-divider"),
        html.Div([html.Span("SOURCE", className="topbar-label"),
                 html.Span("—", id="topbar-source", className="topbar-value")], className="topbar-field"),
        html.Div([html.Span("SWEEP", className="topbar-label"),
                 html.Span("—", id="topbar-sweep", className="topbar-value")], className="topbar-field"),
        html.Div([html.Span("FLAGGED THIS SWEEP", className="topbar-label"),
                 html.Span("0", id="topbar-flags", className="topbar-value")], className="topbar-field"),
    ], className="top-status-bar"),

    html.Div([
        html.Div([
            html.Div([
                html.Div("MODE", className="sidebar-section-title"),
                dcc.RadioItems(
                    id="mode-radio",
                    options=[{"label": " Real sweep (continuous replay)", "value": "real"},
                            {"label": " Synthetic injection demo", "value": "synth"}],
                    value="real", labelStyle={"display": "block", "marginBottom": "4px"}),
            ], className="sidebar-section"),

            # Source is a separate control per mode (source-dropdown for Real sweep,
            # synth-source-dropdown for Synthetic injection demo) so each mode's controls are
            # fully self-contained, and so synth-source-dropdown can be wired as one of
            # do_build()'s auto-rebuild Inputs below without also affecting Real-sweep mode's own
            # source selection.
            html.Div([
                html.Div("SOURCE", className="sidebar-section-title"),
                html.Div(id="real-source-controls", children=[
                    dcc.RadioItems(
                        id="source-dropdown",
                        # All 8 stations now have full trained, deployed models (see the
                        # SOURCE_IDS/NEW_SOURCE_IDS comment above) -- one flat RadioItems, no
                        # fallback-labelled subset anymore. The limitation-note paragraph that
                        # used to explain the "⚠ fallback" marking is removed for the same
                        # reason; nothing below (build_figure_and_carriers()/
                        # build_detail_children()/render()) needed to change, since those all key
                        # off matched_source_id, not this list.
                        options=[{"label": f" {s}", "value": s} for s in SOURCE_IDS],
                        value=SOURCE_IDS[0], labelStyle={"display": "block", "marginBottom": "2px"}),
                ]),
                html.Div(id="synth-source-controls", style={"display": "none"}, children=[
                    dcc.RadioItems(id="synth-source-dropdown",
                                  options=[{"label": f" {s}", "value": s} for s in SOURCE_IDS],
                                  value=SOURCE_IDS[0], labelStyle={"display": "block", "marginBottom": "2px"}),
                    html.Label("Injection type", style={"marginTop": "8px"}),
                    dcc.Dropdown(id="injection-type-dropdown",
                                options=[{"label": t, "value": t} for t in ALL_TYPES],
                                value="UNAUTHORIZED_CARRIER", clearable=False),
                    html.Label("Magnitude", style={"marginTop": "8px"}),
                    dcc.Dropdown(id="magnitude-dropdown",
                                options=[{"label": m, "value": m} for m in MAGNITUDE_LEVELS],
                                value="obvious", clearable=False),
                    html.Label("Seed", style={"marginTop": "8px"}),
                    # max is required, not optional, despite seed having no real upper bound: Dash
                    # 4.4.1's native +/- stepper buttons clear the field entirely when clicked on a
                    # number input with no `max` set (confirmed live -- interval-seconds-input,
                    # the one number field in this layout that already had `max=30`, was the only
                    # one whose stepper worked; both seed-input and real-start-input, neither of
                    # which had a `max`, cleared to empty on a single click with ZERO network
                    # activity, proving the bug is entirely client-side in Dash's own stepper JS,
                    # not anything in this file's callbacks). 999999 is far beyond any seed value
                    # that would ever meaningfully matter here -- purely there to give the stepper
                    # a non-undefined max to clamp against.
                    dcc.Input(id="seed-input", type="number", value=1, min=0, max=999999, step=1,
                             className="text-input"),
                    html.Button("Regenerate", id="build-btn", n_clicks=0, className="btn btn-secondary",
                              style={"marginTop": "10px"}),
                    html.P("Sequence rebuilds automatically whenever Source/Injection type/Magnitude/"
                          "Seed change above -- \"Regenerate\" is only for forcing a fresh rebuild "
                          "with the exact same settings.", className="limitation-note",
                          style={"marginTop": "6px"}),
                    html.Div(id="build-status", className="build-status"),
                ]),
            ], className="sidebar-section"),

            html.Div([
                html.Div("SWEEP CONTROLS", className="sidebar-section-title"),
                html.Div(id="real-sweep-controls", className="control-block", children=[
                    html.Label("Start sweep index"),
                    # max required for the same reason as seed-input above (see its comment) --
                    # 1000000 comfortably exceeds every source's real sweep count (the largest,
                    # B_ec02, has roughly 334,000 rows) with generous headroom, purely to give the
                    # native stepper a real number to clamp against instead of undefined.
                    dcc.Input(id="real-start-input", type="number", value=500, min=0, max=1000000,
                             step=1, className="text-input"),
                ]),
                html.Div(id="synth-sweep-controls", style={"display": "none"}, children=[
                    html.Div(id="step-controls", className="control-block", children=[
                        html.Button("<< step back", id="step-back-btn", n_clicks=0, className="btn"),
                        html.Button("step forward >>", id="step-fwd-btn", n_clicks=0, className="btn"),
                    ]),
                    html.Div(id="synth-slider-block", className="control-block", children=[
                        html.Label("Frame in built sequence"),
                        dcc.Slider(id="synth-frame-slider", min=0, max=0, step=1, value=0,
                                  tooltip={"placement": "bottom", "always_visible": False}),
                    ]),
                ]),
                html.Div([
                    html.Label("Update interval (seconds)"),
                    dcc.Input(id="interval-seconds-input", type="number", value=5, min=1, max=30, step=1,
                             className="text-input"),
                ], className="control-block", style={"marginTop": "14px"}),
            ], className="sidebar-section"),

            html.Div([
                html.Div("PLAYBACK", className="sidebar-section-title"),
                html.Div([
                    html.Button("Play", id="play-btn", n_clicks=0, className="btn btn-primary"),
                ], className="control-block"),

                html.Div(id="status-line", className="status-line"),

                html.Div([
                    html.P("Known limitation: Real-sweep continuous replay is a REPLAY of fixed "
                          "recorded datasets, not a live instrument feed — it advances forward "
                          "through real historical sweeps automatically, one per interval tick, "
                          "until reaching the end of that source's data, then stops. The client-side "
                          "timer mechanism itself (dcc.Interval) is genuinely the same one a real "
                          "live feed would use.", className="limitation-note"),
                    html.P("Expect a real delay (spinner shown) the first time you Play a source, or "
                          "after changing Start sweep index: the detector must process 150 real prior "
                          "sweeps of history before it can score anything, which genuinely takes "
                          "roughly 15-30 seconds (measured) — and up to about a minute on the very "
                          "first request after this dashboard was started (one-time Python/model-"
                          "loading cost). The server handles one request at a time, so nothing else "
                          "updates during that window — this is expected, not a hang. Every sweep "
                          "after that first one renders in well under a second.",
                          className="limitation-note", style={"marginTop": "6px"}),
                    html.P("⚠ stations (EC03/EC04/EC06/G16) have a shorter delay of the SAME kind "
                          "(~3-5 seconds, not 15-30) — their per-sweep cost is intrinsically "
                          "cheaper, not because less work happens. They are streamed directly from "
                          "large files rather than a prebuilt dataset, so changing Start sweep index "
                          "re-reads from that position each time.",
                          className="limitation-note", style={"marginTop": "6px"}),
                ], className="control-block"),
            ], className="sidebar-section"),
        ], className="sidebar"),

        html.Div([
            dcc.Loading(
                id="loading-graph",
                type="circle",
                # delay_show: render() is ONE callback for both the slow cold warm-up (13-90s,
                # session 10) AND every fast post-warmup tick (~0.5s, per session 10's own
                # profiling) -- dcc.Loading has no notion of "which trigger caused this", it just
                # shows the moment ANY pending request targets a wrapped component, by default
                # with zero delay. That fired the spinner on every single tick, not just the slow
                # first one (found live, session 11). delay_show=700 (ms) means a request has to
                # still be pending after 700ms to show anything -- comfortably above the measured
                # ~0.5s per-tick cost (so normal replay never flickers) but far below the
                # multi-second-to-90s warm-up path (so that still shows it). delay_hide=200 avoids
                # an instant flash-off on the rare occasions it does appear.
                delay_show=700,
                delay_hide=200,
                children=[
                    dcc.Graph(id="spectrum-graph", config={"displaylogo": False},
                             figure=EMPTY_DARK_FIGURE),
                    html.Div(id="detail-panel", className="detail-panel"),
                ],
            ),
        ], className="main-panel"),
    ], className="body-row"),

    dcc.Interval(id="interval-component", interval=5000, n_intervals=0, disabled=True),
    dcc.Store(id="app-store", data={"synth_cache_key": None, "synth_frame_idx": 0}),
], className="app-container")


# =====================================================================
# callbacks
# =====================================================================

@app.callback(
    Output("real-source-controls", "style"),
    Output("synth-source-controls", "style"),
    Output("real-sweep-controls", "style"),
    Output("synth-sweep-controls", "style"),
    Input("mode-radio", "value"),
)
def toggle_mode_controls(mode):
    if mode == "real":
        return {"display": "block"}, {"display": "none"}, {"display": "block"}, {"display": "none"}
    return {"display": "none"}, {"display": "block"}, {"display": "none"}, {"display": "block"}


@app.callback(
    Output("status-dot", "className"),
    Output("topbar-state-text", "children"),
    Input("play-btn", "children"),
    Input("status-line", "children"),
)
def update_run_state(play_label, status_text):
    # Derived purely from EXISTING outputs, not from render() -- deliberately: render() is a
    # full no-op on a Pause click (session 12's fix), so a dot driven by render()'s own outputs
    # would not update the instant Pause is clicked. toggle_play() DOES update play-btn's label
    # immediately on every click regardless of direction, which is exactly the signal this needs.
    has_rendered = bool(status_text) and status_text not in ("No sequence built yet.",)
    if not has_rendered:
        return "status-dot status-dot-idle", "IDLE"
    if play_label == "Pause":
        return "status-dot status-dot-running", "RUNNING"
    return "status-dot status-dot-paused", "PAUSED"


@app.callback(
    Output("interval-component", "interval"),
    Input("interval-seconds-input", "value"),
)
def set_interval_seconds(seconds):
    seconds = seconds if seconds and seconds > 0 else 5
    return int(seconds * 1000)


@app.callback(
    Output("interval-component", "disabled"),
    Output("play-btn", "children"),
    Input("play-btn", "n_clicks"),
    State("interval-component", "disabled"),
    prevent_initial_call=True,
)
def toggle_play(n_clicks, currently_disabled):
    now_playing = bool(currently_disabled)  # currently disabled -> we're about to enable -> play
    if now_playing:
        # Do NOT arm the interval here, in EITHER mode. Real-sweep mode: found via live testing
        # (session 10) -- arming it immediately let the client's timer queue ticks against the
        # single-threaded server while `render()`'s own first call was still blocked on the
        # (15-70s) detector warm-up, and the backlog then drained in a rapid-fire burst the moment
        # the server freed up, silently skipping the requested start sweep ahead by dozens of
        # frames. Synthetic mode: the SAME class of race, found live (session 14) -- arming the
        # interval immediately let the FIRST tick queue and land before the click's own "show
        # frame 0" response had even arrived under slow server response times, so the very first
        # frame was overwritten before it was ever visibly rendered (a genuinely-completed 4-frame
        # playthrough measured as showing only frames 1-3). `render()` now arms the interval
        # itself, in EITHER mode, in the SAME response that returns the first real frame.
        return dash.no_update, "Pause"
    return (not now_playing), ("Pause" if now_playing else "Play")


@app.callback(
    Output("synth-frame-slider", "min"),
    Output("synth-frame-slider", "max"),
    Output("synth-frame-slider", "value"),
    Output("app-store", "data", allow_duplicate=True),
    Output("build-status", "children"),
    Output("interval-component", "disabled", allow_duplicate=True),
    Output("play-btn", "children", allow_duplicate=True),
    Input("build-btn", "n_clicks"),
    # source/injection-type/magnitude/seed are Inputs, not State -- auto-rebuild whenever any of
    # them changes, no separate "click Build" step required. Building is real, potentially
    # multi-second work (a cold source needs its own warm-up), and the server runs single-
    # threaded (see the note on `threaded=False` below) -- changing several controls in quick
    # succession queues each rebuild rather than dropping any of them, so the LAST change made
    # always wins once the queue drains, same as a human waiting for one build before the next.
    Input("synth-source-dropdown", "value"),
    Input("injection-type-dropdown", "value"),
    Input("magnitude-dropdown", "value"),
    Input("seed-input", "value"),
    State("app-store", "data"),
    prevent_initial_call=True,
)
def do_build(n_clicks, source_id, injection_type, level, seed, store):
    seed = int(seed) if seed is not None else 0
    cache_key = f"{source_id}_{injection_type}_{level}_{seed}"
    # Session 15 fix: this cache_key was computed and even written to _SYNTH_CACHE below on every
    # call, but never CHECKED first -- every build (whether from clicking "Regenerate" with
    # unchanged settings, or an auto-rebuild landing back on a combination already built earlier
    # this session, e.g. toggling Seed A->B->A) unconditionally re-ran build_synthetic_sequence(),
    # re-paying its warm_up_detector() cost (measured live at ~70-80s for B_ec02) from scratch.
    # build_synthetic_sequence() is deterministic in (source_id, injection_type, level, seed) --
    # same seed means _test_sweep_window()'s internal RNG picks the identical warm-up window every
    # time -- so re-using a cached result for an identical cache_key changes nothing about
    # correctness, only skips redundant work. This does NOT speed up a genuinely NEW seed/param
    # combination (each still needs its own real warm-up, since a different seed's RNG picks a
    # different, unrelated warm-up window -- reusing another seed's warmed detector would corrupt
    # the rolling history baselines with the wrong preceding sweeps).
    if cache_key in _SYNTH_CACHE:
        cached = _SYNTH_CACHE[cache_key]
        seq, meta = cached["seq"], cached["meta"]
    else:
        try:
            seq, meta = build_synthetic_sequence(source_id, injection_type, level, seed=seed,
                                                 n_before=3, n_after=0)
        except Exception as e:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, \
                html.Div(f"Could not build this injection: {e}", className="error-note"), \
                dash.no_update, dash.no_update

    _SYNTH_CACHE[cache_key] = {"seq": seq, "meta": meta}
    store = dict(store)
    store["synth_cache_key"] = cache_key
    n_frames = len(seq)
    # Session 13 fix: ALWAYS reset to frame 0 and force playback fully stopped here, regardless
    # of Play/Pause history going in. Two real, confirmed problems this closes:
    #  (1) This callback used to reset synth_frame_idx to `default_idx` -- the index of the
    #      INJECTION frame, which with n_before=3/n_after=0 is always the LAST frame in the
    #      sequence (there are zero "after" frames by construction). So every build, fresh or a
    #      rebuild, already started playback pinned at the final frame -- clicking Play could
    #      advance at most one wasted tick before immediately hitting the "already at the end"
    #      stop condition. Reproduced live (B_ec05): a rebuild triggered by changing Seed while
    #      PAUSED left the app paused at the new sequence's last frame; clicking Play then showed
    #      zero further frame content, one tick (~5s), then stopped -- easy to misread as "broken"
    #      immediately after a reseed even though the exact same one-tick-then-stop behavior was
    #      already latent on the very first build too, just less noticeable there.
    #  (2) Nothing here ever touched `interval-component.disabled` or `play-btn.children`, so a
    #      rebuild triggered WHILE ALREADY PLAYING (not paused) left the interval armed and
    #      ticking straight through this call's own blocking, potentially 10-30s+ warm-up (a
    #      fresh source needs its own `warm_up_detector()` call) -- the same single-threaded
    #      backlog-pileup risk session 10 fixed for real-sweep mode's warm-up, never guarded here.
    # Forcing disabled=True/"Play" here means EVERY successful rebuild converges to the same
    # state -- paused, frame 0 of the new sequence -- so clicking Play afterward always behaves
    # identically to a fresh Play on a newly-selected combination, regardless of what the
    # Play/Pause history was beforehand.
    store["synth_frame_idx"] = 0
    status = html.Div(f"Built {n_frames} frames. Injected {meta['injection_type']} "
                      f"({meta['level']}) at sweep #{meta['inject_idx']} on {source_id} — "
                      f"target carrier_id={meta['highlight_carrier_id']}.")
    return 0, max(n_frames - 1, 0), 0, store, status, True, "Play"


@app.callback(
    Output("spectrum-graph", "figure"),
    Output("detail-panel", "children"),
    Output("status-line", "children"),
    Output("app-store", "data", allow_duplicate=True),
    Output("interval-component", "disabled", allow_duplicate=True),
    Output("play-btn", "children", allow_duplicate=True),
    Output("topbar-source", "children"),
    Output("topbar-sweep", "children"),
    Output("topbar-flags", "children"),
    Output("topbar-flags", "className"),
    Input("interval-component", "n_intervals"),
    Input("play-btn", "n_clicks"),
    Input("step-back-btn", "n_clicks"),
    Input("step-fwd-btn", "n_clicks"),
    Input("synth-frame-slider", "value"),
    State("mode-radio", "value"),
    State("source-dropdown", "value"),
    State("synth-source-dropdown", "value"),
    State("real-start-input", "value"),
    State("app-store", "data"),
    State("interval-component", "disabled"),
    prevent_initial_call=True,
)
def render(n_intervals, play_clicks, back_clicks, fwd_clicks, slider_value,
          mode, source_id, synth_source_id, real_start, store, interval_was_disabled):
    store = dict(store)
    triggered = ctx.triggered_id
    stop_interval = dash.no_update
    play_label = dash.no_update

    if triggered == "play-btn" and not interval_was_disabled:
        # This click is PAUSING (the interval was already armed/running going into this click,
        # per the pre-click State captured above) -- toggle_play() is the SOLE owner of disabling
        # the interval and flipping the button label for a pause action; this callback must do
        # nothing at all, in EITHER mode. Found live (session 12, real-mode): both toggle_play()
        # and this callback are wired to the same Input("play-btn", "n_clicks"), so a Pause click
        # fires BOTH -- and this callback's own arm-the-interval branch below used to
        # unconditionally re-arm the interval and reset the label back to "Pause" regardless of
        # which direction the click was, racing against toggle_play()'s own (correct) pause and
        # frequently winning: reproduced live as sweep advancing 4+ more ticks over 20s after
        # clicking Pause, with the button visibly flipping back from "Play" to "Pause" on its own.
        # This guard was originally scoped to `mode == "real"` only; generalized to both modes in
        # session 14 once toggle_play() stopped arming the interval immediately in synth mode too.
        return (dash.no_update, dash.no_update, dash.no_update, store,
                dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, dash.no_update)

    if mode == "real":
        # unlike synth mode, "play-btn" also advances here -- there's no meaningful "current
        # position" to preview without moving in a growing continuous replay, and NOT advancing
        # on the click just meant the immediately-following first tick re-rendered the exact same
        # sweep a second time before finally moving on. (The pause case is fully handled by the
        # early return above, so by this point any "play-btn" trigger is genuinely a START click.)
        advance = triggered in ("interval-component", "play-btn")
        if source_id in NEW_SOURCE_IDS:
            frame_data, at_end, just_warmed_up = _advance_new_source(source_id, real_start, advance=advance)
        else:
            frame_data, at_end, just_warmed_up = _advance_real(source_id, real_start, advance=advance)
        if frame_data is None:
            # Only reachable for a new station whose chosen "Start sweep index" is beyond this
            # file's actual length (~10.8K-14.4K sweeps/file) -- nothing was ever primed. Mirrors
            # synth mode's "nothing built yet" response rather than crashing on a None frame_data.
            return dash.no_update, html.Div(
                f"{source_id}: Start sweep index {real_start} is beyond this file's data — pick a smaller value."), \
                "No data at this Start sweep index.", store, True, "Play", \
                dash.no_update, dash.no_update, dash.no_update, dash.no_update
        if at_end and triggered == "interval-component":
            stop_interval, play_label = True, "Play"
        elif triggered == "play-btn" and not at_end:
            # First real frame after a Play click is ready NOW -- safe to arm the interval as
            # part of this same response (see toggle_play()'s note: it deliberately does not).
            stop_interval, play_label = False, "Pause"
        elif just_warmed_up and triggered == "interval-component":
            # A mid-play source/start-index change can still trigger a fresh warm-up from an
            # already-ticking interval (the click-time guard above only covers the Play-button
            # path). Rather than let further ticks pile up against this same blocking call,
            # auto-pause here -- the user sees "Play" and can resume with one click once ready,
            # instead of the UI silently skipping ahead through a queued backlog.
            stop_interval, play_label = True, "Play"
    else:
        cache_key = store.get("synth_cache_key")
        if cache_key is None or cache_key not in _SYNTH_CACHE:
            return dash.no_update, html.Div("Build a sequence first (see the sidebar)."), \
                "No sequence built yet.", store, dash.no_update, dash.no_update, \
                dash.no_update, dash.no_update, dash.no_update, dash.no_update
        cached = _SYNTH_CACHE[cache_key]
        seq, meta = cached["seq"], cached["meta"]
        frame_idx = store.get("synth_frame_idx", 0)
        if triggered == "step-back-btn":
            frame_idx = max(0, frame_idx - 1)
        elif triggered == "step-fwd-btn":
            frame_idx = min(len(seq) - 1, frame_idx + 1)
        elif triggered == "synth-frame-slider":
            frame_idx = int(slider_value)
        elif triggered == "interval-component":
            if frame_idx < len(seq) - 1:
                frame_idx += 1
            else:
                stop_interval, play_label = True, "Play"
        elif triggered == "play-btn":
            # First real frame after a Play click is ready NOW -- safe to arm the interval as
            # part of this same response (mirrors real-mode's identical fix; see toggle_play()'s
            # note for why arming it immediately on click, before this response lands, is unsafe).
            # frame_idx itself does NOT advance here -- unlike real-mode, Play in synth mode
            # previews the CURRENT position rather than moving forward on the click -- EXCEPT when
            # already sitting on the last frame (session 15 fix): the original guard here was
            # `and frame_idx < len(seq) - 1`, added so clicking Play wouldn't arm an interval with
            # nothing left to advance to. That correctly covered a fresh build (frame_idx starts at
            # 0), but the auto-stop-at-sequence-end path (the `interval-component` branch's `else`
            # above) leaves frame_idx PINNED at len(seq)-1 forever -- it's never reset back to 0
            # anywhere outside do_build()'s own rebuild. So a SECOND Play click after reaching the
            # natural end could never satisfy that guard, permanently: toggle_play() still flips
            # the button label to "Pause", but this callback's own stop_interval/play_label stayed
            # at their `dash.no_update` defaults, so the interval never re-armed -- a genuinely
            # stuck "Pause" button that does nothing, reproduced live (frames 934-937 played
            # correctly, then a second Play click produced zero status-line change over 12s while
            # the button still claimed "Pause"). Fixed by treating "Play clicked while already at
            # the last frame" as an explicit restart: reset to frame 0, then arm the interval same
            # as any other fresh Play.
            if frame_idx >= len(seq) - 1:
                frame_idx = 0
            stop_interval, play_label = False, "Pause"
        store["synth_frame_idx"] = frame_idx
        entry = seq[frame_idx]
        frame_data = entry["frame_data"]

    fig, carriers_plotted, any_flagged = build_figure_and_carriers(frame_data)
    detail_children = build_detail_children(frame_data, carriers_plotted)
    log_flagged_carriers_to_csv(frame_data, carriers_plotted)
    n_flagged = sum(1 for c in carriers_plotted if c["status"] not in _NOT_FLAGGED_STATUSES)
    is_fallback = frame_data["result"].get("matched_source_id") is None
    status = (f"{frame_data['source_id']} — sweep #{frame_data['sweep_index']} — "
             f"{len(carriers_plotted)} carriers, {n_flagged} flagged"
             f"{'  ⚠ FLAGGED THIS FRAME' if any_flagged else ''}"
             f"{'  [LOW-CONFIDENCE FALLBACK]' if is_fallback else ''}")
    # top status bar values -- same underlying data as `status` above, split into the separate
    # at-a-glance fields the redesigned top bar shows (source 12). topbar-source's TEXT (not a
    # new Output/className) carries the fallback marker -- keeps this callback's Output count/
    # order completely unchanged, lower risk than adding a new Output for a className swap.
    topbar_flags_class = "topbar-value topbar-value-flagged" if n_flagged else "topbar-value"
    topbar_source_text = f"{frame_data['source_id']} ⚠" if is_fallback else frame_data["source_id"]
    return (fig, detail_children, status, store, stop_interval, play_label,
           topbar_source_text, f"#{frame_data['sweep_index']}", str(n_flagged),
           topbar_flags_class)


if __name__ == "__main__":
    # Launch with: D:\Dhyan\myenv\Scripts\python.exe validation\live_dashboard.py
    # NOT `streamlit run ...` -- this is a Dash app (see the module docstring's launch banner).
    import os
    debug = os.environ.get("DASH_DEBUG") == "1"
    # threaded=False deliberately: _REAL_STATE/_SYNTH_CACHE are plain module-level dicts with no
    # locking, and this app's whole design assumes callbacks run one at a time (matching a
    # single-operator local tool) -- concurrent requests (Flask's dev server threads by default)
    # could otherwise race to redundantly re-warm the same detector in parallel. Found via genuine
    # browser testing (session 8): with threading on, a real-sweep Play click's cold ~28s warm-up
    # never visibly completed even after 65+s, consistent with several concurrent duplicate
    # warm-ups GIL-serializing into a much longer wait.
    app.run(host="0.0.0.0", port=8050, debug=debug, use_reloader=False, threaded=False)