# Phase 2 Feature Extraction — Summary Report (per-carrier architecture)

Generated: 2026-08-03 16:38:37


## A_16hr

Rows: 31994 (carrier-sweeps), columns: 35, unique tracked carrier_ids: 32, sweeps covered: 1000

Carriers per sweep: mean=31.99, min=31, max=32

Carrier events: 32 appeared, 6 reappeared (reclaimed within the 10-sweep grace period), 0 disappeared (grace period expired) (out of 1000 sweeps)

Carrier lifetime (sweeps): mean=1000.0, median=1000.0, max=1000, single-sweep-only carriers: 0 (0.0%)

**Boolean flags:**

- `carrier_detected`: 100.0% True (31994/31994)
- `is_gap_transition`: 0.0% True (0/31994)

| feature | mean | std | min | max | nan_count | nan_pct |
|---|---|---|---|---|---|---|
| cn_db | 14.35 | 3.963 | 2.028 | 23.98 | 0 | 0.0% |
| noise_floor_local_dbm | -101 | 0.9627 | -102.6 | -97.65 | 0 | 0.0% |
| occupied_bw_bins | 85.08 | 62.96 | 7 | 206 | 0 | 0.0% |
| occupied_bw_hz | nan | nan | nan | nan | 31994 | 100.0% |
| symmetry_score | 0.8908 | 0.1105 | -0.3991 | 1 | 945 | 3.0% |
| n_secondary_peaks_in_span | 0.0002188 | 0.01479 | 0 | 1 | 0 | 0.0% |
| rise_width_bins | 9.886 | 4.967 | 1 | 25 | 0 | 0.0% |
| rise_steepness_db_per_bin | 1.729 | 0.9511 | 0.2365 | 6.905 | 994 | 3.1% |
| rise_smoothness_db | 1.081 | 0.5495 | 0 | 3.768 | 994 | 3.1% |
| rise_overshoot_db | 0.01011 | 0.04735 | 0 | 1.078 | 994 | 3.1% |
| plateau_width_bins | 64.11 | 55.78 | 1 | 186 | 0 | 0.0% |
| plateau_tilt_db_per_bin | -0.002148 | 0.03668 | -0.7877 | 0.6511 | 2193 | 6.9% |
| plateau_flatness_db | 0.3047 | 0.1016 | 0.0002715 | 0.7867 | 2193 | 6.9% |
| plateau_ripple_var | 0.06257 | 0.03896 | 5.773e-07 | 0.3387 | 2841 | 8.9% |
| fall_width_bins | 13.08 | 16.64 | 3 | 131 | 0 | 0.0% |
| fall_steepness_db_per_bin | 1.613 | 0.9019 | 0.003605 | 4.622 | 0 | 0.0% |
| fall_smoothness_db | 1.077 | 0.5847 | 0.1605 | 3.407 | 0 | 0.0% |
| fall_overshoot_db | 0.0169 | 0.07028 | 0 | 1.678 | 0 | 0.0% |
| rise_fall_steepness_ratio | 1.053 | 0.2469 | 0.3722 | 5.256 | 5791 | 18.1% |
| rise_fall_width_ratio | 0.9729 | 0.2646 | 0 | 5 | 0 | 0.0% |
| peak_power_dbm | -86.68 | 3.795 | -99.36 | -77.77 | 0 | 0.0% |
| peak_bin_index | 2061 | 959.2 | 0 | 3502 | 0 | 0.0% |
| peak_freq_hz | nan | nan | nan | nan | 31994 | 100.0% |
| frame_power_delta_db | -2.272e-05 | 0.6032 | -3.344 | 3.986 | 38 | 0.1% |
| frame_power_rate_db_per_s | nan | nan | nan | nan | 31994 | 100.0% |
| frame_freq_delta_bins | 0.009012 | 25.89 | -164 | 156 | 38 | 0.1% |
| frame_freq_delta_hz | nan | nan | nan | nan | 31994 | 100.0% |
| frame_freq_drift_hz_per_s | nan | nan | nan | nan | 31994 | 100.0% |
| rolling_cn_std | 0.2829 | 0.1737 | 0.003102 | 1.379 | 32 | 0.1% |

**Degenerate (near-constant) features for A_16hr:** none

**Correlation matrix (key features):**

                           peak_power_dbm  cn_db  occupied_bw_bins  symmetry_score  rise_steepness_db_per_bin  fall_steepness_db_per_bin  rise_fall_steepness_ratio  plateau_flatness_db  plateau_ripple_var  n_secondary_peaks_in_span
peak_power_dbm                       1.00   0.97              0.06            0.02                       0.26                       0.42                      -0.11                 0.26                0.32                       0.02
cn_db                                0.97   1.00             -0.08           -0.00                       0.38                       0.52                      -0.11                 0.13                0.23                       0.02
occupied_bw_bins                     0.06  -0.08              1.00           -0.16                      -0.76                      -0.74                      -0.15                 0.59                0.48                       0.01
symmetry_score                       0.02  -0.00             -0.16            1.00                       0.06                       0.07                       0.04                 0.07               -0.02                      -0.00
rise_steepness_db_per_bin            0.26   0.38             -0.76            0.06                       1.00                       0.87                       0.44                -0.58               -0.42                      -0.01
fall_steepness_db_per_bin            0.42   0.52             -0.74            0.07                       0.87                       1.00                      -0.11                -0.53               -0.39                      -0.00
rise_fall_steepness_ratio           -0.11  -0.11             -0.15            0.04                       0.44                      -0.11                       1.00                -0.11               -0.07                      -0.01
plateau_flatness_db                  0.26   0.13              0.59            0.07                      -0.58                      -0.53                      -0.11                 1.00                0.83                       0.05
plateau_ripple_var                   0.32   0.23              0.48           -0.02                      -0.42                      -0.39                      -0.07                 0.83                1.00                       0.06
n_secondary_peaks_in_span            0.02   0.02              0.01           -0.00                      -0.01                      -0.00                      -0.01                 0.05                0.06                       1.00


## B_ec02

Rows: 333995 (carrier-sweeps), columns: 35, unique tracked carrier_ids: 213, sweeps covered: 11520

Carriers per sweep: mean=28.99, min=27, max=30

Carrier events: 213 appeared, 201 reappeared (reclaimed within the 10-sweep grace period), 183 disappeared (grace period expired) (out of 11520 sweeps)

Carrier lifetime (sweeps): mean=1569.4, median=1.0, max=11520, single-sweep-only carriers: 109 (51.2%)

**Boolean flags:**

- `carrier_detected`: 100.0% True (333995/333995)
- `is_gap_transition`: 0.0% True (0/333995)

| feature | mean | std | min | max | nan_count | nan_pct |
|---|---|---|---|---|---|---|
| cn_db | 13.79 | 4.478 | 1.848 | 24.5 | 0 | 0.0% |
| noise_floor_local_dbm | -103.1 | 0.6794 | -104.3 | -100 | 0 | 0.0% |
| occupied_bw_bins | 48.99 | 32.98 | 4 | 124 | 0 | 0.0% |
| occupied_bw_hz | nan | nan | nan | nan | 333995 | 100.0% |
| symmetry_score | 0.8789 | 0.1177 | -0.5287 | 1 | 11534 | 3.5% |
| n_secondary_peaks_in_span | 0.0007186 | 0.0268 | 0 | 1 | 0 | 0.0% |
| rise_width_bins | 6.216 | 3.124 | 1 | 41 | 0 | 0.0% |
| rise_steepness_db_per_bin | 2.154 | 1.084 | -0.05912 | 9.896 | 32350 | 9.7% |
| rise_smoothness_db | 1.243 | 0.6954 | 0 | 5.703 | 32350 | 9.7% |
| rise_overshoot_db | 0.01703 | 0.06077 | 0 | 1.439 | 32350 | 9.7% |
| plateau_width_bins | 36.56 | 29.56 | 1 | 92 | 0 | 0.0% |
| plateau_tilt_db_per_bin | 0.05381 | 0.3177 | -0.7305 | 2.453 | 12600 | 3.8% |
| plateau_flatness_db | 0.3303 | 0.3307 | 0.0002014 | 2.406 | 12600 | 3.8% |
| plateau_ripple_var | 0.0393 | 0.02114 | 1.041e-10 | 0.4523 | 34698 | 10.4% |
| fall_width_bins | 8.209 | 9.774 | 1 | 107 | 0 | 0.0% |
| fall_steepness_db_per_bin | 1.985 | 1.095 | -0.005623 | 6.85 | 20980 | 6.3% |
| fall_smoothness_db | 1.203 | 0.7176 | 0 | 4.342 | 20980 | 6.3% |
| fall_overshoot_db | 0.01848 | 0.06763 | 0 | 1.365 | 20980 | 6.3% |
| rise_fall_steepness_ratio | 1.113 | 0.5581 | 0.2173 | 8.558 | 40010 | 12.0% |
| rise_fall_width_ratio | 0.9829 | 0.3915 | 0 | 33 | 20980 | 6.3% |
| peak_power_dbm | -89.36 | 4.305 | -102 | -78.77 | 0 | 0.0% |
| peak_bin_index | 1042 | 492.1 | 0 | 2046 | 0 | 0.0% |
| peak_freq_hz | nan | nan | nan | nan | 333995 | 100.0% |
| frame_power_delta_db | -2.335e-05 | 0.3417 | -11.36 | 11.65 | 414 | 0.1% |
| frame_power_rate_db_per_s | nan | nan | nan | nan | 333995 | 100.0% |
| frame_freq_delta_bins | -5.096e-05 | 14.89 | -92 | 97 | 414 | 0.1% |
| frame_freq_delta_hz | nan | nan | nan | nan | 333995 | 100.0% |
| frame_freq_drift_hz_per_s | nan | nan | nan | nan | 333995 | 100.0% |
| rolling_cn_std | 0.1588 | 0.2131 | 0.001273 | 6.292 | 213 | 0.1% |

**Degenerate (near-constant) features for B_ec02:** none

**Correlation matrix (key features):**

                           peak_power_dbm  cn_db  occupied_bw_bins  symmetry_score  rise_steepness_db_per_bin  fall_steepness_db_per_bin  rise_fall_steepness_ratio  plateau_flatness_db  plateau_ripple_var  n_secondary_peaks_in_span
peak_power_dbm                       1.00   0.99             -0.08            0.04                       0.52                       0.71                      -0.15                -0.15               -0.05                       0.04
cn_db                                0.99   1.00             -0.15            0.06                       0.55                       0.75                      -0.16                -0.16               -0.10                       0.04
occupied_bw_bins                    -0.08  -0.15              1.00           -0.22                      -0.69                      -0.57                      -0.11                -0.20                0.74                       0.03
symmetry_score                       0.04   0.06             -0.22            1.00                       0.05                       0.13                      -0.17                 0.10               -0.10                      -0.14
rise_steepness_db_per_bin            0.52   0.55             -0.69            0.05                       1.00                       0.67                       0.36                -0.47               -0.51                      -0.02
fall_steepness_db_per_bin            0.71   0.75             -0.57            0.13                       0.67                       1.00                      -0.30                -0.45               -0.46                       0.01
rise_fall_steepness_ratio           -0.15  -0.16             -0.11           -0.17                       0.36                      -0.30                       1.00                -0.02               -0.05                      -0.00
plateau_flatness_db                 -0.15  -0.16             -0.20            0.10                      -0.47                      -0.45                      -0.02                 1.00                0.78                      -0.01
plateau_ripple_var                  -0.05  -0.10              0.74           -0.10                      -0.51                      -0.46                      -0.05                 0.78                1.00                      -0.02
n_secondary_peaks_in_span            0.04   0.04              0.03           -0.14                      -0.02                       0.01                      -0.00                -0.01               -0.02                       1.00


## B_ec05

Rows: 203134 (carrier-sweeps), columns: 35, unique tracked carrier_ids: 574, sweeps covered: 11520

Carriers per sweep: mean=17.63, min=14, max=28

Carrier events: 574 appeared, 6159 reappeared (reclaimed within the 10-sweep grace period), 554 disappeared (grace period expired) (out of 11520 sweeps)

Carrier lifetime (sweeps): mean=378.8, median=12.5, max=11520, single-sweep-only carriers: 169 (29.4%)

**Boolean flags:**

- `carrier_detected`: 100.0% True (203134/203134)
- `is_gap_transition`: 0.0% True (0/203134)

| feature | mean | std | min | max | nan_count | nan_pct |
|---|---|---|---|---|---|---|
| cn_db | 12.69 | 4.505 | 2.489 | 23.37 | 0 | 0.0% |
| noise_floor_local_dbm | -98.4 | 2.179 | -102.8 | -84.64 | 0 | 0.0% |
| occupied_bw_bins | 68.64 | 71.42 | 6 | 313 | 0 | 0.0% |
| occupied_bw_hz | nan | nan | nan | nan | 203134 | 100.0% |
| symmetry_score | 0.8166 | 0.1926 | -0.4399 | 0.9999 | 1 | 0.0% |
| n_secondary_peaks_in_span | 0.009575 | 0.134 | 0 | 21 | 0 | 0.0% |
| rise_width_bins | 13.68 | 20.27 | 1 | 160 | 0 | 0.0% |
| rise_steepness_db_per_bin | 1.946 | 1.554 | -0.155 | 10.24 | 178 | 0.1% |
| rise_smoothness_db | 1.188 | 0.8025 | 0 | 5.788 | 178 | 0.1% |
| rise_overshoot_db | 0.0271 | 0.1188 | 0 | 6.176 | 178 | 0.1% |
| plateau_width_bins | 47.46 | 54.84 | 1 | 183 | 0 | 0.0% |
| plateau_tilt_db_per_bin | -0.0006748 | 0.03302 | -2.849 | 0.7714 | 51 | 0.0% |
| plateau_flatness_db | 0.2626 | 0.1205 | 0.003262 | 4.667 | 51 | 0.0% |
| plateau_ripple_var | 0.04184 | 0.07113 | 2.781e-10 | 6.851 | 835 | 0.4% |
| fall_width_bins | 9.501 | 11.1 | 1 | 219 | 0 | 0.0% |
| fall_steepness_db_per_bin | 2.051 | 1.379 | -0.07249 | 7.24 | 595 | 0.3% |
| fall_smoothness_db | 1.098 | 0.709 | 0 | 5.515 | 595 | 0.3% |
| fall_overshoot_db | 0.02695 | 0.1216 | 0 | 11.61 | 595 | 0.3% |
| rise_fall_steepness_ratio | 1.069 | 0.6148 | 0.1948 | 10.72 | 87797 | 43.2% |
| rise_fall_width_ratio | 2.149 | 4.688 | 0 | 92 | 595 | 0.3% |
| peak_power_dbm | -85.71 | 5.067 | -99.84 | -73.51 | 0 | 0.0% |
| peak_bin_index | 727.5 | 432.4 | 131 | 1952 | 0 | 0.0% |
| peak_freq_hz | nan | nan | nan | nan | 203134 | 100.0% |
| frame_power_delta_db | 0.0004322 | 0.3882 | -13.42 | 13.8 | 6733 | 3.3% |
| frame_power_rate_db_per_s | nan | nan | nan | nan | 203134 | 100.0% |
| frame_freq_delta_bins | 0.008503 | 20.94 | -174 | 150 | 6733 | 3.3% |
| frame_freq_delta_hz | nan | nan | nan | nan | 203134 | 100.0% |
| frame_freq_drift_hz_per_s | nan | nan | nan | nan | 203134 | 100.0% |
| rolling_cn_std | 0.1718 | 0.2712 | 0.0005233 | 9.993 | 574 | 0.3% |

**Degenerate (near-constant) features for B_ec05:** none

**Correlation matrix (key features):**

                           peak_power_dbm  cn_db  occupied_bw_bins  symmetry_score  rise_steepness_db_per_bin  fall_steepness_db_per_bin  rise_fall_steepness_ratio  plateau_flatness_db  plateau_ripple_var  n_secondary_peaks_in_span
peak_power_dbm                       1.00   0.90              0.25            0.12                       0.37                       0.19                       0.41                 0.26                0.15                       0.06
cn_db                                0.90   1.00              0.03            0.06                       0.51                       0.36                       0.48                 0.09                0.04                       0.02
occupied_bw_bins                     0.25   0.03              1.00           -0.05                      -0.59                      -0.56                      -0.02                 0.63                0.31                       0.06
symmetry_score                       0.12   0.06             -0.05            1.00                       0.12                       0.10                      -0.03                 0.03               -0.04                      -0.16
rise_steepness_db_per_bin            0.37   0.51             -0.59            0.12                       1.00                       0.49                       0.65                -0.43               -0.21                      -0.02
fall_steepness_db_per_bin            0.19   0.36             -0.56            0.10                       0.49                       1.00                      -0.45                -0.43               -0.21                      -0.07
rise_fall_steepness_ratio            0.41   0.48             -0.02           -0.03                       0.65                      -0.45                       1.00                -0.06               -0.02                      -0.00
plateau_flatness_db                  0.26   0.09              0.63            0.03                      -0.43                      -0.43                      -0.06                 1.00                0.69                       0.27
plateau_ripple_var                   0.15   0.04              0.31           -0.04                      -0.21                      -0.21                      -0.02                 0.69                1.00                       0.44
n_secondary_peaks_in_span            0.06   0.02              0.06           -0.16                      -0.02                      -0.07                      -0.00                 0.27                0.44                       1.00


## C_g18

Rows: 284639 (carrier-sweeps), columns: 39, unique tracked carrier_ids: 69, sweeps covered: 9551

Carriers per sweep: mean=29.80, min=27, max=30

Carrier events: 69 appeared, 12 reappeared (reclaimed within the 10-sweep grace period), 39 disappeared (grace period expired) (out of 9551 sweeps)

Carrier lifetime (sweeps): mean=4125.6, median=126.0, max=9551, single-sweep-only carriers: 0 (0.0%)

**Boolean flags:**

- `carrier_detected`: 100.0% True (284639/284639)
- `is_gap_transition`: 0.0% True (0/284639)

| feature | mean | std | min | max | nan_count | nan_pct |
|---|---|---|---|---|---|---|
| cn_db | 16.3 | 3.376 | 3.172 | 28.81 | 0 | 0.0% |
| noise_floor_local_dbm | -71.84 | 0.9257 | -73.88 | -68.43 | 0 | 0.0% |
| occupied_bw_bins | 47.35 | 9.168 | 4 | 141 | 0 | 0.0% |
| occupied_bw_hz | 4.074e+05 | 8.058e+04 | 2.63e+04 | 1.23e+06 | 0 | 0.0% |
| symmetry_score | 0.9098 | 0.09141 | -0.1565 | 0.9996 | 0 | 0.0% |
| n_secondary_peaks_in_span | 7.026e-05 | 0.008382 | 0 | 1 | 0 | 0.0% |
| rise_width_bins | 8.689 | 1.794 | 1 | 89 | 0 | 0.0% |
| rise_steepness_db_per_bin | 1.874 | 0.484 | 0.1699 | 14.13 | 113 | 0.0% |
| rise_smoothness_db | 1.372 | 0.5342 | 0 | 7.727 | 113 | 0.0% |
| rise_overshoot_db | 0.006241 | 0.03436 | 0 | 2.256 | 113 | 0.0% |
| plateau_width_bins | 31.97 | 7.432 | 1 | 47 | 0 | 0.0% |
| plateau_tilt_db_per_bin | -0.004324 | 0.05828 | -2.993 | 0.275 | 147 | 0.1% |
| plateau_flatness_db | 0.2809 | 0.119 | 0.04852 | 5.589 | 147 | 0.1% |
| plateau_ripple_var | 0.05412 | 0.02086 | 6.546e-07 | 0.3111 | 280 | 0.1% |
| fall_width_bins | 8.692 | 1.722 | 1 | 90 | 0 | 0.0% |
| fall_steepness_db_per_bin | 1.858 | 0.4661 | 0.08219 | 9.438 | 113 | 0.0% |
| fall_smoothness_db | 1.392 | 0.5632 | 0.172 | 6.397 | 113 | 0.0% |
| fall_overshoot_db | 0.008421 | 0.03903 | 0 | 1.491 | 113 | 0.0% |
| rise_fall_steepness_ratio | 1.021 | 0.1687 | 0.2441 | 4.517 | 301 | 0.1% |
| rise_fall_width_ratio | 1.019 | 0.2181 | 0.1124 | 11.5 | 113 | 0.0% |
| peak_power_dbm | -55.54 | 3.397 | -68.15 | -43.67 | 0 | 0.0% |
| peak_bin_index | 1020 | 561.8 | 129 | 2012 | 0 | 0.0% |
| peak_freq_hz | 7.896e+07 | 4.938e+06 | 7.113e+07 | 8.768e+07 | 0 | 0.0% |
| frame_power_delta_db | -9.366e-05 | 0.2938 | -6.655 | 8.951 | 81 | 0.0% |
| frame_power_rate_db_per_s | -9.44e-06 | 0.01926 | -0.4437 | 0.5594 | 81 | 0.0% |
| frame_freq_delta_bins | -0.000854 | 10.42 | -69 | 73 | 81 | 0.0% |
| frame_freq_delta_hz | -7.507 | 9.162e+04 | -6.065e+05 | 6.416e+05 | 81 | 0.0% |
| frame_freq_drift_hz_per_s | 0.6566 | 6006 | -3.926e+04 | 4.277e+04 | 81 | 0.0% |
| rolling_cn_std | 0.1912 | 0.1381 | 5.934e-05 | 4.719 | 71 | 0.0% |
| template_corr | 0.9957 | 0.007571 | 0.02381 | 1 | 144 | 0.1% |
| template_residual_energy | 0.972 | 3.076 | 0 | 150.4 | 144 | 0.1% |
| cn_ground_truth_matched_db | 15.99 | 3.389 | 2.505 | 28.51 | 0 | 0.0% |
| cn_matched_band_freq_hz | 7.897e+07 | 4.929e+06 | 7.125e+07 | 8.755e+07 | 0 | 0.0% |

**Degenerate (near-constant) features for C_g18:** none

**Correlation matrix (key features):**

                           peak_power_dbm  cn_db  occupied_bw_bins  symmetry_score  rise_steepness_db_per_bin  fall_steepness_db_per_bin  rise_fall_steepness_ratio  plateau_flatness_db  plateau_ripple_var  n_secondary_peaks_in_span
peak_power_dbm                       1.00   0.96             -0.08            0.17                       0.70                       0.73                      -0.02                 0.09               -0.03                       0.00
cn_db                                0.96   1.00              0.07            0.16                       0.67                       0.69                      -0.02                 0.12                0.01                       0.00
occupied_bw_bins                    -0.08   0.07              1.00           -0.06                      -0.43                      -0.43                      -0.02                 0.12                0.30                       0.04
symmetry_score                       0.17   0.16             -0.06            1.00                       0.16                       0.16                      -0.02                 0.02                0.01                      -0.06
rise_steepness_db_per_bin            0.70   0.67             -0.43            0.16                       1.00                       0.80                       0.28                -0.03               -0.07                      -0.02
fall_steepness_db_per_bin            0.73   0.69             -0.43            0.16                       0.80                       1.00                      -0.31                -0.06               -0.13                       0.00
rise_fall_steepness_ratio           -0.02  -0.02             -0.02           -0.02                       0.28                      -0.31                       1.00                 0.04                0.07                       0.00
plateau_flatness_db                  0.09   0.12              0.12            0.02                      -0.03                      -0.06                       0.04                 1.00                0.77                      -0.00
plateau_ripple_var                  -0.03   0.01              0.30            0.01                      -0.07                      -0.13                       0.07                 0.77                1.00                      -0.00
n_secondary_peaks_in_span            0.00   0.00              0.04           -0.06                      -0.02                       0.00                       0.00                -0.00               -0.00                       1.00


**DSP-derived C/N (LOCAL per-carrier floor) vs. instrument ground-truth CN_g18 cross-check** (n=284639 carrier-sweeps with a matched band): correlation r=0.995, mean bias=+0.32 dB (derived - ground_truth). Compare against the pre-correction whole-sweep-floor result: r=0.945, bias=-11.65dB.
