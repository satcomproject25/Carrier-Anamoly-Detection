# Phase 1 Canonical Loader — Summary

### A_16hr
- sweeps: (1000, 4096) (n_sweeps x n_bins), dtype=float32
- power range: min=-103.42 dBm, max=-77.77 dBm, mean=-92.90 dBm
- freq_axis_hz: NOT AVAILABLE (bin-index only, 0..4095)
- labels: None (unsupervised — no ground truth found in Phase 0)
- reference_spectrum: absent
- ground_truth_cn: absent
- ground_truth_carrier_power: absent
- has_timestamps: False — NO TIMESTAMP DATA EXISTS ON DISK for this source (confirmed Phase 0: absent from both the labeled xlsx and the raw .mat). delta_t_s cannot be computed. Rate-based/time-windowed Phase 2 features are UNAVAILABLE for this source pending user-supplied timestamps.

### B_ec02
- sweeps: (11520, 2048) (n_sweeps x n_bins), dtype=float32
- power range: min=-105.04 dBm, max=-78.77 dBm, mean=-95.01 dBm
- freq_axis_hz: NOT AVAILABLE (bin-index only, 0..2047)
- labels: None (unsupervised — no ground truth found in Phase 0)
- reference_spectrum: absent
- ground_truth_cn: absent
- ground_truth_carrier_power: absent
- has_timestamps: False — NO TIMESTAMP DATA EXISTS ON DISK for this source (confirmed Phase 0: absent from both the labeled xlsx and the raw .mat). delta_t_s cannot be computed. Rate-based/time-windowed Phase 2 features are UNAVAILABLE for this source pending user-supplied timestamps.

### B_ec05
- sweeps: (11520, 2048) (n_sweeps x n_bins), dtype=float32
- power range: min=-103.75 dBm, max=-73.51 dBm, mean=-92.24 dBm
- freq_axis_hz: NOT AVAILABLE (bin-index only, 0..2047)
- labels: None (unsupervised — no ground truth found in Phase 0)
- reference_spectrum: absent
- ground_truth_cn: absent
- ground_truth_carrier_power: absent
- has_timestamps: False — NO TIMESTAMP DATA EXISTS ON DISK for this source (confirmed Phase 0: absent from both the labeled xlsx and the raw .mat). delta_t_s cannot be computed. Rate-based/time-windowed Phase 2 features are UNAVAILABLE for this source pending user-supplied timestamps.

### C_g18
- sweeps: (9551, 2048) (n_sweeps x n_bins), dtype=float32
- power range: min=-74.57 dBm, max=-43.67 dBm, mean=-62.35 dBm
- freq_axis_hz: [70,000,000, 87,991,200] Hz (2048 bins)
- labels: None (unsupervised — no ground truth found in Phase 0)
- reference_spectrum: present
- ground_truth_cn: present, shape (9551, 32)
- ground_truth_carrier_power: present, shape (9551, 32)
- has_timestamps: True
- delta_t_s distribution (n=9550, excludes first-sweep NaN): min=15.00s, max=16.00s, median=15.00s, mean=15.27s, std=0.44s
- sample_interval_s_median (REPORTING STAT ONLY, not used downstream): 15.00s
