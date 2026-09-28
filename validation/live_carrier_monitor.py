"""
Part F: live/continuous visualization — the full intended pipeline (detect -> score -> gate ->
diagnose -> display) running end to end, exactly as originally designed, for the first time in
this project's history. Everything upstream of "display" already existed and was already
independently verified (Phase 2 segmentation/features, Phase 3 splits, Phase 4 training, Part D's
gating fix, Part E's single-frame rendering) — this module is the last piece: stepping that same
real pipeline through a SEQUENCE of sweeps and animating it, reusing Part E's `plot_sweep.py` as
the rendering core with ZERO duplicated drawing logic (see module docstring there for the
get_sweep_frame_data()/render_frame() split this relies on).

Two sequence-building modes:
  (a) `build_real_sequence()` — replay a contiguous stretch of REAL recorded sweeps. Use this to
      watch a real stretch of activity unfold, e.g. C_g18's still-unresolved #4247-4497
      spectral-shape-anomaly window (Phase 5 / Part D Track 1) across many consecutive sweeps
      rather than Part E's single #4300 snapshot.
  (b) `build_synthetic_sequence()` — warms up on real sweeps, then applies ONE of Part B's
      injectors (`validation/inject_interference.py`, imported directly — zero duplicated
      injection logic) to build a short "before -> injected -> after" sequence, so a synthetic
      anomaly's appearance and the model's real-time response (score crossing threshold, gate
      opening, diagnosis attaching) can be watched frame by frame, not just read off an aggregate
      metrics table.

Both modes pre-run the ONE continuously-advancing `CarrierAnomalyDetector` through the whole
sequence up front (via repeated `get_sweep_frame_data(..., detector=det)` calls, never
re-warming) — this is not a shortcut relative to true real-time streaming, it IS what true
real-time streaming does: process each sweep once, in order, as it arrives. Pre-running it here
just lets the SAME deterministic result be scrubbed/animated/exported at whatever playback rate
is convenient, without needing a live spectrum analyzer attached to this machine.

Playback / export:
  - `run_live(frame_data, fps=4, show=False, out_path=None)` builds a `matplotlib.animation.
    FuncAnimation` that calls `plot_sweep.render_frame()` once per frame (pure rendering, no
    further detector calls — the detector already ran once, above).
  - `show=True` attempts to switch to an interactive GUI backend and open a live window;
    reports clearly (not a crash) if this environment has no display to open one on.
  - `out_path` ending in `.mp4` uses ffmpeg if available, else falls back to `.gif` (via
    matplotlib's bundled Pillow writer) with a clear message — this machine has no ffmpeg
    installed, confirmed before writing this module, so the demo runs below produce `.gif`.

Run standalone: `python live_carrier_monitor.py` — renders and saves the two demo sequences the
project asked for (see `_demo()`): a real C_g18 #4247-4497-window stretch, and a synthetic
UNAUTHORIZED_CARRIER injection on A_16hr.
"""

import os
import sys
import time
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\validation")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\features")
sys.path.insert(0, r"D:\Dhyan\Carrier_Detection\inference")
from plot_sweep import (                                            # noqa: E402
    get_sweep_frame_data, render_frame, warm_up_detector, load_canonical, build_source_config,
    DEFAULT_WARMUP_SWEEPS,
)
from inject_interference import (                                    # noqa: E402
    _load_source_arrays, _test_sweep_window, pick_target_carrier, compute_noise_floor_and_scale,
    segment_carriers, get_sweep_cn_drift_stats, INJECTORS_SIMPLE, INJECTORS_DRIFT_SCALED,
    inject_unauthorized_carrier, inject_dropout_single_sweep, DROPOUT_N_SWEEPS,
)

OUT_DIR = r"D:\Dhyan\Carrier_Detection\validation\live_monitor_demo"
DEFAULT_FPS = 4


# =====================================================================
# sequence builders
# =====================================================================

def build_real_sequence(source_id, start_sweep, end_sweep, warmup_sweeps=DEFAULT_WARMUP_SWEEPS):
    """MODE (a): a contiguous stretch of REAL recorded sweeps [start_sweep, end_sweep], warmed up
    on the `warmup_sweeps` real sweeps immediately before `start_sweep`. Returns a list of
    {frame_data, highlight} dicts ready for `run_live()`."""
    det = warm_up_detector(source_id, start_sweep, warmup_sweeps=warmup_sweeps)
    sequence = []
    for i in range(start_sweep, end_sweep + 1):
        fd = get_sweep_frame_data(source_id, i, detector=det)
        sequence.append({"frame_data": fd, "highlight": None})
    return sequence


def _best_overlap_pid(tracked_geometry, lo, hi):
    """Exact floor-departure/floor-return overlap match — simpler and more precise than
    inject_interference.py's `_find_result_carrier` (that one only has access to
    center_bin_index +/- occupied_bw/2 from carrier_monitor's summary output; here we have the
    real boundary bins directly off tracked_geometry, so no approximation is needed)."""
    best_pid, best_overlap = None, 0
    for c in tracked_geometry:
        fd, fr = c["floor_departure_bin"], c["floor_return_bin"]
        overlap = max(0, min(fr, hi) - max(fd, lo))
        if overlap > best_overlap:
            best_pid, best_overlap = c["persistent_id"], overlap
    return best_pid


def build_synthetic_sequence(source_id, injection_type, level, seed=0, n_before=10, n_after=15,
                             warmup_sweeps=DEFAULT_WARMUP_SWEEPS):
    """MODE (b): real 'before' sweeps -> Part B's injector applied (reused directly, not
    reimplemented) -> real 'after' sweeps. Returns (sequence, meta) where `meta` describes what
    was injected (type/level/sweep index/target bin range) for titling/logging."""
    rng = np.random.default_rng(seed)
    sweeps, freq_axis, has_ts, timestamps = _load_source_arrays(source_id)
    extra_room = (DROPOUT_N_SWEEPS if injection_type == "DROPOUT" else 1) + n_after + 2
    start, end, actual_warmup = _test_sweep_window(source_id, warmup_sweeps, extra_room, rng)
    warmup_end = start + actual_warmup - 1
    inject_idx = warmup_end + 1
    if actual_warmup < 1:
        raise RuntimeError(f"{source_id}: no test block large enough for any warm-up at seed={seed}")

    before_start = max(start, warmup_end - n_before + 1)
    det = warm_up_detector(source_id, before_start, warmup_sweeps=(before_start - start))

    sequence = []
    for i in range(before_start, warmup_end + 1):
        fd = get_sweep_frame_data(source_id, i, detector=det)
        sequence.append({"frame_data": fd, "highlight": None})

    cfg = build_source_config(load_canonical(source_id))
    base_power = sweeps[inject_idx]
    noise_floor, noise_scale = compute_noise_floor_and_scale(base_power, cfg)
    carriers = segment_carriers(base_power, freq_axis if cfg["freq_axis_available"] else None,
                               cfg, noise_floor=noise_floor, noise_scale=noise_scale)
    if not carriers:
        raise RuntimeError(f"{source_id}: no carriers in the base injection sweep at seed={seed}")

    highlight_pid = None
    if injection_type == "DROPOUT":
        target = pick_target_carrier(carriers, rng)
        target_lo, target_hi = target["floor_departure_bin"], target["floor_return_bin"]
        for k in range(DROPOUT_N_SWEEPS):
            i = inject_idx + k
            nf, _ = compute_noise_floor_and_scale(sweeps[i], cfg)
            modified = inject_dropout_single_sweep(sweeps[i], target, nf, level)
            fd = get_sweep_frame_data(source_id, i, detector=det, power_override=modified)
            if highlight_pid is None:
                highlight_pid = _best_overlap_pid(fd["tracked_geometry"], target_lo, target_hi)
            sequence.append({"frame_data": fd, "highlight": highlight_pid})
        after_start = inject_idx + DROPOUT_N_SWEEPS
        gt = {"target_bin_range": (target_lo, target_hi)}
    else:
        if injection_type == "UNAUTHORIZED_CARRIER":
            modified, gt = inject_unauthorized_carrier(base_power, carriers, noise_floor, noise_scale, cfg, rng, level)
        elif injection_type in INJECTORS_SIMPLE:
            modified, gt = INJECTORS_SIMPLE[injection_type](base_power, carriers, noise_floor, noise_scale, cfg, rng, level)
        else:
            drift_stats = get_sweep_cn_drift_stats(source_id)
            modified, gt = INJECTORS_DRIFT_SCALED[injection_type](base_power, carriers, noise_floor, noise_scale, cfg, rng, level, drift_stats)
        if gt is None:
            raise RuntimeError(f"{source_id}: injector found no valid target/region at seed={seed}")
        target_lo, target_hi = gt.get("bin_range", gt.get("target_carrier_span"))
        fd = get_sweep_frame_data(source_id, inject_idx, detector=det, power_override=modified)
        highlight_pid = _best_overlap_pid(fd["tracked_geometry"], target_lo, target_hi)
        sequence.append({"frame_data": fd, "highlight": highlight_pid})
        after_start = inject_idx + 1

    after_end = min(after_start + n_after - 1, len(sweeps) - 1, end)
    for i in range(after_start, after_end + 1):
        fd = get_sweep_frame_data(source_id, i, detector=det)
        sequence.append({"frame_data": fd, "highlight": highlight_pid})

    meta = {"source_id": source_id, "injection_type": injection_type, "level": level,
           "inject_idx": inject_idx, "highlight_carrier_id": highlight_pid, **gt}
    return sequence, meta


# =====================================================================
# playback / export
# =====================================================================

def _try_interactive_backend():
    for backend in ("TkAgg", "Qt5Agg"):
        try:
            plt.switch_backend(backend)
            return backend
        except Exception:
            continue
    return None


def _export_animation(anim, out_path, fps):
    ext = os.path.splitext(out_path)[1].lower()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if ext == ".mp4":
        try:
            from matplotlib.animation import FFMpegWriter
            anim.save(out_path, writer=FFMpegWriter(fps=fps))
            return out_path
        except Exception as e:
            gif_path = os.path.splitext(out_path)[0] + ".gif"
            print(f"[live_carrier_monitor] ffmpeg unavailable ({e.__class__.__name__}: {e}) "
                 f"-- saved as GIF instead: {gif_path}")
            anim.save(gif_path, writer=PillowWriter(fps=fps))
            return gif_path
    elif ext == ".gif":
        anim.save(out_path, writer=PillowWriter(fps=fps))
        return out_path
    else:
        raise ValueError(f"unsupported export extension '{ext}' — use .mp4 or .gif")


def run_live(sequence, title_prefix="", fps=DEFAULT_FPS, show=False, out_path=None):
    """Animates an already-built sequence (from build_real_sequence()/build_synthetic_sequence())
    by calling plot_sweep.render_frame() once per frame — no further detector calls happen here,
    the pipeline already ran once when the sequence was built. Returns the FuncAnimation object.
    """
    if show:
        backend = _try_interactive_backend()
        if backend is None:
            print("[live_carrier_monitor] no interactive display available in this environment "
                 "(tried TkAgg, Qt5Agg) — falling back to out_path export only.")
            show = False

    fig, ax = plt.subplots(figsize=(14, 6.2))

    def update(i):
        ax.clear()
        entry = sequence[i]
        render_frame(entry["frame_data"], highlight_carrier_id=entry["highlight"], ax=ax,
                    title_suffix=f" {title_prefix}" if title_prefix else "")
        return []

    anim = FuncAnimation(fig, update, frames=len(sequence), interval=1000.0 / fps,
                        blit=False, repeat=False)

    saved_path = None
    if out_path:
        t0 = time.time()
        saved_path = _export_animation(anim, out_path, fps)
        print(f"[live_carrier_monitor] saved {len(sequence)} frames @ {fps}fps -> {saved_path} "
             f"({time.time() - t0:.1f}s)")

    if show:
        plt.show()

    plt.close(fig)
    return anim, saved_path


# =====================================================================
# demo
# =====================================================================

def _demo():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=== MODE (a): real sequence — C_g18, inside the #4247-4497 window ===")
    real_seq = build_real_sequence("C_g18", 4280, 4340, warmup_sweeps=150)
    n_flagged_frames = sum(1 for e in real_seq
                          if any(c.get("flagged") for c in e["frame_data"]["result"]["carriers"]))
    print(f"  {len(real_seq)} frames built, {n_flagged_frames} frames contain >=1 flagged carrier")
    run_live(real_seq, title_prefix="[C_g18 real replay, #4247-4497 window]", fps=4,
            out_path=os.path.join(OUT_DIR, "C_g18_4247_4497_window.mp4"))

    print("\n=== MODE (b): synthetic sequence — A_16hr, UNAUTHORIZED_CARRIER, obvious ===")
    synth_seq, meta = build_synthetic_sequence("A_16hr", "UNAUTHORIZED_CARRIER", "obvious",
                                              seed=1, n_before=10, n_after=15)
    print(f"  injected at sweep #{meta['inject_idx']}, highlight_carrier_id={meta['highlight_carrier_id']}")
    run_live(synth_seq, title_prefix=f"[A_16hr synthetic UNAUTHORIZED_CARRIER/obvious]", fps=3,
            out_path=os.path.join(OUT_DIR, "A_16hr_unauthorized_carrier_obvious.mp4"))


if __name__ == "__main__":
    _demo()
