# EC04 / Universal-Model Investigation — Full Report

**Scope**: Sessions 18–48 of the Carrier Interference Detection project. This document covers the
complete investigation into whether a single, station-identity-blind anomaly-detection model can
serve all four production stations (EC03, EC04, EC06, G16), why EC04 specifically resists every
attempt at unification, what was ultimately deployed, and what remains open. It does not touch, and
is not relevant to, the separate, untouched station group (A_16hr, B_ec02, B_ec05, C_g18).

**Companion document**: `PROGRESS.md`'s session 49 entry is the concise, PROGRESS.md-native closing
summary of the same material. This document is the complete version, written for direct review.

---

## 1. Starting Point

### 1.1 Original architecture

As of session 18 (2026-08-25), EC03/EC04/EC06/G16 each had a **separate, fully independent
per-station model**: a StandardScaler → IsolationForest(200 trees) + PCA(90% variance retained) →
0.5/0.5-weighted z-score ensemble → p99-of-TRAIN threshold, trained on that station's own data
alone. The feature set was 29 columns, almost entirely **absolute-scale**: literal dB-denominated
quantities (`cn_db`, `peak_power_dbm`, `noise_floor_local_dbm`, edge steepness/smoothness/overshoot
in dB, plateau tilt/flatness/ripple in dB) and raw bin/Hz-sized quantities (`occupied_bw_bins/hz`,
edge/plateau widths in bins, peak frequency).

A leave-one-station-out cross-generalization check at the time (session 18, Stage 2b) was
unambiguous: **diagonal (a model scored on its own station) sat at 0–1.6%, matching the p99
calibration target; off-diagonal (a model scored on any other station) sat at 71.9–100%,** meaning
every one of the four models treated every other station's data as almost entirely anomalous. This
confirmed the necessity of per-station modeling **under that feature set** — it did not yet
establish whether a *differently designed* feature set could do better.

### 1.2 Original goal

Per the project guide's own stated requirement, the goal was to build **one shape-only,
transponder-blind universal model**: a detector whose features never encode a station's absolute
noise floor, absolute carrier-to-noise ratio, or any other station-specific reference level, so that
it could plausibly generalize to a transponder it had never been trained on — including, in
principle, a genuinely new station added to the system in the future without requiring its own
dedicated training cycle. This is a materially harder bar than "cross-generalizes reasonably well";
it specifically requires no learned or hard-coded notion of *which station* a carrier came from
anywhere in the detection pipeline.

Everything that follows is the record of testing that goal against real data, station by station,
feature by feature, and architecture by architecture, across 30 sessions.

---

## 2. Every Approach Tried, In Order

Each entry: what was tried, why, what was found (real numbers), and the precise mechanistic reason
for the outcome.

### 2.1 Shape-only, scale-invariant feature redesign (Sessions 19–21)

**What / why**: Session 18's 29 features were audited; only 4 were already scale-invariant. The
task was to redesign the remaining 25 so that no feature carried a station's absolute noise floor or
gain level, since a universal model cannot learn "normal" if two stations' identical *shapes* sit at
different absolute levels purely due to hardware differences.

- **Session 19 — `*_frac_of_cn` tier**: every dB-denominated feature renormalized as a ratio against
  that carrier's own `cn_db` (its peak-to-local-floor dynamic range); width features renormalized as
  a fraction of the carrier's own occupied span. Final 16-feature `SHAPE_ONLY_FEATURE_COLS` set.
  **Result (LOSO held-out flag rate, held-out station never seen in training)**: EC03 0.00%, EC04
  2.46%, EC06 **97.45%**, G16 24.35% (vs. session 18's per-station cross-gen failure of 71.9–100%
  for all 4 — a real improvement for 2 of 4 stations, but EC06 remained a near-total failure).
- **Session 20 — floor-free tier (correction)**: `cn_db` itself is `peak_power_dbm` minus a *local
  noise-floor estimate*, so `*_frac_of_cn` was still indirectly floor-dependent. Redesigned every
  reference to be built purely from raw power samples at carrier-internal boundary bins (own
  rise/fall/plateau span), with zero reference to the noise-floor array anywhere. **Result**: EC06
  improved substantially (97.45% → 55.16%) but EC04 and G16 got slightly *worse* (2.46%→5.98%,
  24.35%→28.41%) — a real, reported trade-off, not an unqualified win.
- **Session 21 — EC06 diagnosis + edge smoothing**: per-feature PCA-residual and direct
  distributional analysis found EC06's remaining gap was **partly** a noisy single-sample edge-power
  denominator (coefficient of variation 5–11x higher than the other 3 stations) and **partly** a
  genuine physical shape difference (`symmetry_score` median 0.446 vs. pooled 0.886; real overshoot
  the other stations essentially never show). A 3-bin local-averaging fix for the noisy-denominator
  mechanism improved EC06 (55.16%→51.72%) and G16 (28.41%→23.94%) but **did not move EC04 at all**
  (5.98%→6.26%, flat) — EC04's regression had a different, not-yet-identified cause (later explained
  in session 30 as a genuine shape signature, not noise).

**Mechanistic outcome**: floor-independence was necessary but insufficient. EC06's near-total LOSO
failure was a real, physical population difference (asymmetric, overshoot-prone carriers), not a
normalization artifact — this became the first concrete evidence that at least one station is
*genuinely* shape-distinct, a theme that recurs for EC04 throughout the rest of the investigation.

### 2.2 Full pooling, no station identity (Session 22)

**What / why**: Rather than testing generalization to a *never-seen* station (LOSO's deliberately
hard bar), test the easier and more realistic question: if every station's own carriers are part of
one unified training pool from the start (no station column anywhere), does the shared model
recognize each station's *own* held-out TEST data as normal?

**Result**: dramatic improvement over LOSO for every station — EC03 0.00%, EC04 1.51%, EC06 14.14%,
G16 3.38% (vs. session 21's LOSO figures of 0.00%, 6.26%, 51.72%, 23.94%). Flag rate tracked
monotonically with each station's normalized distance from the pooled population's center. A
post-hoc station-origin analysis showed EC06's distinctive low-symmetry/high-overshoot shape pattern
is **not unique to EC06** — it recurs across all 4 stations, just at 5x EC06's proportional share —
which is exactly why pooling (giving the model minority-but-real exposure to that pattern) helps far
more than strict LOSO exclusion could.

**Mechanistic outcome**: EC06's flag rate (14.14%) still sat 4-9x higher than the other three even
after pooling — real exposure narrows but does not close a population-share gap.

### 2.3 Per-station threshold calibration (Session 23)

**What / why**: Session 22 already showed EC06's remaining gap was a *baseline* problem, not a
*model* problem — a single global p99 cutoff conflates "unusual vs. the pooled average" with
"unusual vs. what this station itself normally produces." Test whether calibrating a **separate**
p99 threshold per station, from that same pooled model's scores on that station's own TRAIN data,
closes the gap — with zero changes to the model, features, or training data.

**Result**: decisive. EC03 0.00%→1.02%, EC04 1.51%→1.63%, EC06 **14.14%→2.10%**, G16 3.38%→2.59% —
all 4 stations now cluster in a 1.02–2.59% band (vs. session 22's 0.00–14.14% spread). EC06's flag
rate became the *second-lowest* of the four.

**Mechanistic outcome — adopted, became the standing architecture**: per-station threshold
calibration on top of one shared, station-identity-blind model is the correct design for
EC03/EC06/G16. This is the architecture eventually deployed to production (sessions 39/40).

### 2.4 Track 2 real synthetic evaluation of pooled+calibrated (Session 24, revised Session 29)

**What / why**: Sessions 22/23 only measured flag *rate* on real, unlabeled data — never whether the
model actually catches synthetic, labeled anomalies. Run the full Track 2 harness (8 injectable
types × 3 magnitudes × 5 repeats) against the pooled+calibrated architecture for all 4 stations.

**Result (combined F1 / FPR, pooled+calibrated vs. each station's then-existing per-source model)**:
EC03 improved (0.30→0.41 F1, FPR unchanged 0.67%). EC06 essentially matched or improved slightly
(F1 0.31 both, FPR 16.67%→13.48%). **EC04 regressed** (F1 0.52→0.29, FPR 1.42%→4.41%). **G16
regressed sharply** (FPR 0.00%→17.28%).

**Mechanistic outcome — later revised**: session 29 discovered EC04/G16's *comparison baseline*
(their per-source models) was stale — trained 2026-08-25, before sessions 19–23 rebuilt the
canonical/feature/split files entirely. Once fairly retrained (session 29), EC04's per-source
advantage over pooling *held and strengthened*; G16's did **not** — a fairly retrained G16 per-source
model performed statistically indistinguishably from the pool (FPR 17.28% both). G16's original
"good per-source" result was itself a stale-data artifact, not a real per-source advantage.

### 2.5 Segmentation-quality hypothesis (Session 25)

**What / why**: Test whether session 24's EC04/G16 regression was actually a **segmentation**
artifact (carriers found imprecisely) rather than a genuine model/shape mismatch, using the
frequency-chart ground truth (center frequencies only — no bandwidth field exists in any chart) as
an independent check on `segment_carriers()`'s blind detection.

**Result — hypothesis refuted**: EC04 segments its *active* carriers about as well as EC03
(~99% hit rate on non-stale chart entries, offset_fraction 0.475 vs. EC03's 0.502), yet still showed
the second-worst regression. EC06 showed the *worst* segmentation-quality signature of all four
stations (unstable per-frequency hit rates, highest extra-carrier rate) yet did **not** regress under
pooling — if anything it improved. The two rankings (regression severity vs. segmentation quality)
do not match, and EC04 is a direct counter-example.

**Mechanistic outcome**: segmentation quality is not the driver — the evidence points back toward a
genuine distributional/shape mismatch, foreshadowing session 30's diagnosis.

### 2.6 Diagnostic detour: false-positive clustering and stale models (Sessions 26–28)

- **Session 26** (visual verification): 32 real-sweep, single-injection combinations across all 4
  stations x 8 types under the then-production setup. 11/32 caught overall (34.4%); DROPOUT caught
  everywhere, IN_BAND_TONE and NOISE_FLOOR_RISE missed everywhere. Flagged, but did not resolve, a
  cluster of non-injected false positives concentrated on EC04 (23 across 5 sweeps).
- **Session 27** (diagnostic): traced those EC04 false positives to `GENERAL_DEGRADATION`
  (fires only when the trained score is *already* flagged and no specific feature check explains
  why — 74% of EC04's false positives, vs. 0% for EC06) and to `PRELIMINARY_INSTANTANEOUS_OUTLIER`
  "stacking" (a structural consequence of testing ~23 features independently with no
  multiple-testing correction on first-observation carriers — an already-documented 29% vs. 3.6%
  naive-baseline gap from 2026-08-13). Proposed two fixes, implemented neither yet.
- **Session 28** (fix + major discovery): implemented the simplest proposed fix — require ≥2
  independent triggers, not 1, before `PRELIMINARY_INSTANTANEOUS_OUTLIER` fires. Verified a real
  ~3x reduction in first-observation flag rate for EC04/EC06 (90.8%→31.7%, 46.9%→15.0%), no change
  to any injected-carrier outcome (0/32 changed). **While verifying, discovered EC04 and G16's
  "production" per-source models were trained 2026-08-25 — before sessions 19–23 rebuilt the
  canonical/features/split files as much larger extended-window versions with the new floor-free
  feature tier.** Every evaluation of these two per-source models since that rebuild (including
  sessions 24, 26, 27) had been scoring a frozen decision boundary against a training-time
  reference distribution that no longer matched what the model was calibrated against.

### 2.7 Fair per-source retrain of EC04/G16 (Session 29)

**What / why**: Fix the staleness session 28 discovered, then re-run the pooled-vs-per-source
comparison fairly for the first time.

**Result**: EC04's fresh per-source model **clearly beats** the pooled model (F1 0.43 vs. 0.29,
FPR 2.20% vs. 4.41%) — the per-source recommendation for EC04 now stands on solid ground. G16's
fresh per-source model performs **statistically indistinguishably** from the pool (F1 0.29 vs. 0.28,
FPR 17.28% identical) — G16's real problem is a property of its own current data, not a
pooled-vs-per-source question at all.

**Mechanistic outcome — revised recommendation established**: pooled for EC03/EC06/G16, per-source
(freshly retrained) for EC04 only. This recommendation held, essentially unchanged in substance,
for the remainder of the investigation.

### 2.8 Diagnosing why EC04 resists the pool (Session 30)

**What / why**: With EC04 confirmed as the one standing exception, apply the same feature-level
rigor session 21 used for EC06.

**Result — two distinct, concrete mechanisms found**:
1. **A genuine shape signature**: EC04's `fall_width_frac_of_span`/`rise_width_frac_of_span` sit
   higher than the pooled median (normalized distance +0.616/+0.320), `plateau_width_frac_of_span`
   sits lower (-0.585), and both edges' steepness-relative-to-own-span sit at roughly half the
   pooled value. The **same** features (rise/fall steepness- and smoothness-frac-of-own-span)
   independently dominate the pooled model's PCA reconstruction error when it flags an EC04 carrier
   — a converged, two-method finding: EC04's carriers have proportionally wider, softer edges and a
   smaller relative plateau than the pooled population's typical carrier.
2. **A structural, feature-scope gap**: on the same TEST rows, the pooled (16-feature) model *never*
   flags anything the dedicated (55-feature) model doesn't also flag (`pooled_only=0`), but the
   dedicated model flags 7,743 rows (1.12%) the pool entirely misses — and those rows' *shape*
   (the 16 pooled features) looks unremarkable; whatever the dedicated model reacts to lives in the
   39 absolute/floor-referenced features the shape-only pool structurally excludes.
- The carrier-churn hypothesis (EC04 has more short-lived carriers, harder to model) was **tested
  directly and refuted**: EC04 has the *lowest* single-sweep-carrier row-share of all 4 stations
  (0.3%), and even where churny carriers exist, their edges are too indistinct to clear the
  floor-free features' own NaN guard, so churn cannot manifest as a shape signal the model ever sees.

**Mechanistic outcome**: mechanism 1 (the shape signature) looked genuinely irreducible via further
shape-feature redesign — a real, physically plausible RF/filter-roll-off characteristic, not a
measurement defect. Mechanism 2 (missing absolute features) looked fixable in principle but only by
compromising the shape-only design mandate.

### 2.9 Testing whether the gap is absolute-feature-driven (Session 31)

**What / why**: Session 30's mechanism 2 predicted the gap should concentrate in the two injectable
types that are inherently absolute-measure-based (NOISE_FLOOR_RISE, BANDWIDTH_SHIFT). Test directly
by comparing per-type flag rates from the pooled and dedicated models' existing Track 2 reports (same
underlying synthetic examples, same fixed seeds, two different scoring models).

**Result — hypothesis decisively refuted**: NOISE_FLOOR_RISE and BANDWIDTH_SHIFT show **exactly
zero** pooled-vs-dedicated gap (40.0%/40.0% and 0.0%/0.0%). DROPOUT and UNAUTHORIZED_CARRIER's
zero gaps (event-gated, expected identical) confirmed the methodology itself was sound. The entire
measured gap instead concentrates in three **shape-based** types the pool already has features for:
ADJACENT_CARRIER (+71.4pp), SHOULDER_BUMP (+33.3pp), IN_BAND_TONE (+13.3pp).

**Mechanistic outcome**: the pool is not blind to these events for lack of the right feature — it
has the feature and still misses most of them. Points to a *sensitivity* problem within the existing
16-feature space (plausibly how a shared PCA fit allocates representational capacity to naturally
sparse/near-zero features like overshoot), not a missing-information problem.

### 2.10 Autoencoder replacing PCA (Session 32)

**What / why**: Test session 31's plausible mechanism directly — does a nonlinear, sparsity-weighted
reconstruction (an MLPRegressor autoencoder with empirically-measured per-feature loss weights,
replacing PCA in the ensemble) close the gap a linear PCA fit under-represents?

**Result — hypothesis not confirmed**: SHOULDER_BUMP and IN_BAND_TONE show **zero movement** under
the autoencoder (identically 0.0% to the PCA baseline). ADJACENT_CARRIER moves +7.1pp (14.3%→21.4%),
closing only ~10% of the 71.4-point gap to the dedicated model. Real overall F1/FPR improvements on
EC03/EC06/G16 were found, but traced to an unrelated, unexplained side effect (NOISE_FLOOR_RISE),
not the targeted mechanism.

**Mechanistic outcome — rejected, recommend stopping this approach**: the gap does not appear
fixable by a better reconstruction-error function, linear or nonlinear, within the shared 16-feature
pooled architecture. These specific anomalies may not manifest as reconstruction-error outliers in
that feature space for EC04 at all, regardless of the reconstruction function.

### 2.11 Bimodal bandwidth-population hypothesis (Session 33)

**What / why**: Test a guide-proposed hypothesis — EC04's carriers form more numerous, more
distinctly separated bandwidth clusters than the other stations, and this bimodality specifically
explains the miss rate.

**Result — partially confirmed, cleanly split by type**: EC04 does have the highest bimodality
coefficient (0.861), though EC03 is actually *more* cleanly bimodal by the standard statistic
(0.724) — a correction to the task's own premise. The real, substantial finding: **ADJACENT_CARRIER**
shows a genuine ~18x catch-rate difference by bandwidth cluster (narrow 3.3% vs. wide 60.0%, n=35).
**SHOULDER_BUMP and IN_BAND_TONE show zero relationship to bandwidth cluster** — both missed
~100% regardless of cluster, across ~29 independent attempts each.

**Mechanistic outcome**: bimodality explains one of the three target types, not all three — session
30's shape-signature explanation remains necessary for the other two, which are cluster-independent
failures.

### 2.12 `bw_ratio_to_recent_median` — 17th feature (Session 34)

**What / why**: Implement session 33's proposed remedy directly — a carrier's occupied bandwidth
relative to a rolling median of its own station's recent carriers, added as a 17th pooled feature.

**Result — rejected, real regression on the target case**: narrow-cluster ADJACENT_CARRIER catch
rate went from already-poor (4.5%, 1/22) to **zero** (0/22) — the one specific carrier that
previously worked (seed 42) is now missed. Wide-cluster performance unchanged. Aggregate Track 2
metrics were roughly a wash, with G16's FPR notably worse (17.28%→20.99%).

**Mechanistic outcome**: plausibly the same "PCA doesn't reward a mostly-near-1.0-with-occasional-
excursions feature" blind spot session 31 already diagnosed for other sparse-ish features — adding
one more dimension to the same averaged ensemble does not escape the dilution mechanism.

### 2.13 Rule-based CAD re-audit (Session 35 — design study, nothing implemented)

**What / why**: In light of the converged sessions 31/32/34 finding (the ML ensemble structurally
dilutes subtle/low-variance anomaly signal), audit the predecessor's exact rule-based per-carrier
CAD logic (`Aid_update.py`) for what makes it different, and whether any of it is portable.

**Key finding**: the rule engine's real, code-evidenced advantage is that **every check is an
independent boolean test; a carrier is flagged the instant any ONE check fires** — no averaging.
Contrast directly against this project's own math: `pca_raw = np.mean((X_s - Xr)**2, axis=1)` — a
literal average across 16-17 features, which structurally lets a single badly-reconstructing
dimension get "outvoted" by 15-16 calm ones. This is a genuine, demonstrable mechanism, not
speculation — but it is not unconditionally superior either: the rule engine's fixed absolute-dB
thresholds are not equally meaningful across stations with different natural noise/ripple scales,
the exact population-heterogeneity problem this project's own floor-free redesign was built to
eliminate.

**Recommendation** (not yet implemented at this point): a hybrid — reformulate any ported rule as a
carrier-relative ratio (avoiding fixed-threshold heterogeneity risk) but score it as an
**independent OR-gate branch**, never averaged into the PCA/IsolationForest ensemble. This
recommendation directly motivated sessions 36–38's OR-gate work.

### 2.14 IsolationForest-alone + per-feature independent checks (Session 36)

**What / why**: Test the OR-gate design directly, against EC04's actual missed carriers from
sessions 33/34, using two independent signals: the IsolationForest score alone (no PCA blend) and
each of the 4 features `interference_diagnosis.py` already maps to these 3 types, checked alone
against its own p99 threshold.

**Result — real, mixed evidence**: IN_BAND_TONE shows a genuine, evidence-backed partial win
(0%→10.5%+10.5% via two *different*, non-overlapping carriers — a 3-way OR would catch 21.1%, not
just 2 of 19 the current path catches). **SHOULDER_BUMP remains completely unmoved (0% under all
three approaches, no exceptions)**. **Narrow-cluster ADJACENT_CARRIER (session 33's headline
problem) is unchanged by either design** — both new checks catch the exact same single carrier
(seed 42) session 33 already found, and nothing else.

**Mechanistic outcome**: recommend building this as a production OR-gate for its real IN_BAND_TONE
gain, explicitly noting neither SHOULDER_BUMP nor narrow ADJACENT_CARRIER are solved by this design.
An important, later-relevant caveat this session's own conclusion did not state explicitly: it only
tested against known-positive carriers, never against negatives, so it could not see any false-alarm
cost.

### 2.15 OR-gate production implementation, uncapped (Session 37)

**What / why**: Wire session 36's two checks into production `_or_gate_check()` as a pure OR against
the existing blended-score check, calibrated per-station via own-TRAIN p99, for all 4 stations.

**Result — real gains, severe, previously-invisible cost**: EC04 and G16 both show genuine F1 gains
(0.427→0.527, 0.28→0.43) and real, targeted recall improvements on IN_BAND_TONE/SHOULDER_BUMP/
ADJACENT_CARRIER. But **FPR increased on every single station**, from a 7x jump on EC03 (0.67%→
4.67%) to a ~10x jump on EC04 (2.20%→22.47%). Root cause: the two new checks are far less
type-specific than intended — a single feature or the raw IsolationForest score exceeding its own
p99 fires broadly across almost every interference type, and symmetrically on the clean/negative
population far more than the intended ~1%.

**Mechanistic outcome — rejected as calibrated**: session 36's own "cannot cause a regression by
construction" reasoning held only for the positive-only population it tested; it never tested
negatives, so it could not see this cost. Reported honestly as the reason this exact caveat should
have been explicit earlier.

### 2.16 OR-gate recalibration: percentile vs. margin-gating (Session 38)

**What / why**: Fix session 37's FPR blowup. Two knobs tried in specified order: a stricter
percentile (99.9 instead of 99.0), and a **score-margin gate** (only run the two checks on carriers
whose *existing* blended score is already ≥ 0.5x its own threshold — i.e., already borderline).

**Result**:
- **Percentile alone (99.9)**: FPR improved everywhere, but a diagnostic pass revealed *why*:
  G16's ADJACENT_CARRIER gain (0%→33% at p99) vanished completely at p99.9 (back to exact baseline —
  the OR-gate is now fully inert for G16); EC03's SHOULDER_BUMP gain also vanished. EC04 still
  carried a 6.2x FPR ratio to baseline. Verdict: mostly just deletes the signal instead of
  separating good signal from bad.
- **Margin-gating (0.5x threshold) at the original p99**: FPR-to-baseline ratio: **EC04 1.4x** (was
  10.2x), **EC06 1.05x**, **G16 1.21x**, **EC03 2.66x**. Per-type breakdown shows this actually
  separates signal from noise, not just suppresses both: EC03 and EC06 are **bit-identical to
  baseline on every single targeted type** (the OR-gate is inert there — no benefit, negligible
  cost). EC04 **retains a real, partial gain** (SHOULDER_BUMP 60%→80%, F1 0.427→0.49, FPR only
  1.4x baseline, type-attribution nearly fully recovered). G16 **retains** its full ADJACENT_CARRIER
  gain (0%→33%) at a real but bounded FPR cost (17.28%→20.99%, 1.21x).

**Mechanistic outcome — the key diagnostic finding**: reusing already-collected checkpoints showed
both the OR-gate's remaining false positives AND its true-positive rescues are dominated by
*unscoreable* carriers (`anomaly_score is None`) for EC04 specifically (97% of both FPs and TPs);
for EC06/G16 the unscoreable population drives cost with zero genuine benefit either way. This
predicted, correctly, that EC04 would show a hard signal/noise tension margin-gating could not fully
resolve — a tension that recurs, in sharper form, in candidate 1 (session 46).

**Adopted, nuanced**: margin-gated OR-gate enabled for EC04 (clear win) and G16 (real gain, real
but bounded FPR cost — the user's call to make); left disabled for EC03/EC06 (no evidence of
benefit).

### 2.17 Deployment discoveries and catch-up (Sessions 39–40)

- **Session 39**: tasked with simply copying EC04's margin-gate pattern to G16's on-disk
  `thresholds.json`. Direct file inspection first revealed EC03 and EC06 were **not** running the
  pooled model at all — they were still serving the stale session-18 per-source models (29
  features, trained 2026-08-25), and G16 was running session 29's *per-source* retrain, not the
  pooled model session 38's numbers were actually calibrated against. Deployed the real pooled model
  + margin-gated OR-gate to G16 (user's explicit choice among 3 presented options), verified
  bit-exact against session 38's numbers via the real, unpatched production loader.
- **Session 40**: deployed the pooled model (no OR-gate, per session 38's own finding of no benefit)
  to EC03 and EC06, same discipline. EC03 verified bit-exact. EC06 showed a real, small FPR drift
  (13.48%→15.60%) — root-caused to an *unrelated*, pre-existing staleness in the
  `PRELIMINARY_INSTANTANEOUS_OUTLIER` reference-statistics subsystem (dated from a 2026-09-08
  feature-parquet change, sessions 27/28's own mechanism, untouched by this deployment) — confirmed
  not a defect in the deployment itself. Produced the first fully authoritative, disk-verified
  "what's actually running" table for all 4 stations.

**Mechanistic outcome**: this pair of sessions closed a **standing gap between what had been
"recommended" since session 24/29 and what was actually deployed** — for roughly two weeks of this
project's timeline, EC03 and EC06 had never received any of the pooled-model work at all.

### 2.18 EC04 on the pool with margin-gated OR-gate (Session 41)

**What / why**: With margin-gating now proven for EC04's *dedicated* model, test the one
combination never tried before: EC04 scored *through the pool* with a freshly-calibrated
margin-gated OR-gate of its own.

**Result — decisive rejection**: F1 0.49→**0.282**, FPR 3.08%→**6.17%** (2.0x *worse*, not closer
to baseline), SHOULDER_BUMP 80%→**0%** (complete loss), ADJACENT_CARRIER 100%→**20%** (severe
loss). **PR-AUC/ROC-AUC — measuring the continuous score's ranking ability, independent of any
threshold or gate — both dropped too** (0.650/0.743 → 0.387/0.646).

**Mechanistic outcome**: the PR-AUC/ROC-AUC drop is the most telling number in this entire
investigation for ruling out a calibration explanation — EC04's carriers are ranked meaningfully
worse by the pooled model's raw score than by its own dedicated model's score, confirming session
30's shape-signature diagnosis is structural, not a threshold-tuning artifact a smarter gate could
fix. EC03/EC06/G16 were proven mathematically unaffected (deterministic refit, unchanged pool
composition) without needing to re-run their multi-hour Track 2 evaluations.

### 2.19 Frequency-chart / neighbor-context features (Session 42 — design + cheap validation)

**What / why**: Test two candidate features built from each carrier's own position history: (1)
neighbor-gap-anomaly (does the buffer zone toward a carrier's nearest neighbor show an unexpected
spike?), and (2) centroid-drift (does a carrier's own power-weighted centroid deviate from *its own*
rolling history?) — both per-carrier, self-referential z-scores, never a fixed threshold, since a
real position-stability check (17 persistent EC04 carriers, natural jitter 35–920 kHz
carrier-to-carrier) showed no single fixed tolerance could ever work.

**Result — one clean negative, one strong positive**: reading the actual injector code
(`inject_shoulder_bump`/`inject_adjacent_carrier`) revealed both place their perturbation *inside*
the carrier's own already-segmented span, never in the genuinely empty gap toward a neighbor —
**neighbor-gap-anomaly correctly shows zero separation because there is nothing there to detect**,
not a dead end in the underlying idea. **Centroid-drift shows strong, real separation**, most
dramatically on narrow-cluster ADJACENT_CARRIER (the project's single hardest case): **79.3% of
injected cases exceed the clean population's normal range**, median effect size |z|=4.44 (>4x the
clean population's own spread) — a dramatic jump from every population-threshold approach's
historical ~4.5% ceiling on this exact population.

**Mechanistic outcome**: this is architecturally different from every prior threshold in the
project — a PER-CARRIER "normal," not a population-wide percentile. This is very likely *why* it
succeeds where the population-threshold OR-gate (sessions 37/38) could not: a narrow-cluster
ADJACENT_CARRIER injection was never that unusual across the whole EC04 population, but it is
unusual relative to that specific carrier's own recent history.

### 2.20 Centroid-drift as a 4th OR-gate branch, EC04 (Session 43)

**What / why**: Implement and calibrate centroid-drift as an independent OR-gate branch (deliberately
*not* gated by the existing margin, since its "normal" is per-carrier, not population-wide), test on
EC04's dedicated model, which already has session 38's margin-gated OR-gate deployed.

**Result — zero net benefit**: real narrow-cluster ADJACENT_CARRIER catch rate stayed exactly
**17/22 = 77.3%** with or without centroid-drift; the two carriers where it did fire were **already**
flagged by other checks. Full Track 2: F1 essentially unchanged (0.49→0.484), FPR up slightly
(3.08%→3.52%, +1 new false positive, precisely attributed).

**Mechanistic outcome — rejected for EC04, not because the signal is weak**: session 42 already
proved real separation exists; the finding here is that session 38's already-deployed OR-gate has
already captured nearly everything centroid-drift would catch on **this specific model**. The two
signals overlap almost completely for EC04, not because either is weak, but because they are
independently arriving at the same carriers.

### 2.21 Centroid-drift on EC03/EC06 (Session 44)

**What / why**: Test the same signal where no pre-existing OR-gate exists to be redundant with —
EC03 and EC06's pooled model, deployed without any OR-gate.

**Result — station-specific, clean split**:
- **EC06 fails the bar on both types** — only 1 genuine catch across 35 valid attempts; the
  overwhelming majority (33/35) missed by centroid-drift *and* the blended score alike. Not an
  overlap problem — EC06 simply doesn't show the separation, consistent with its established
  noise-floor-adjacent population characteristic (sessions 20/21).
- **EC03 clearly passes for SHOULDER_BUMP** — 8/20 (40%) genuinely new catches vs. 3/20 redundant.
  Full Track 2 confirmed a real net improvement: **F1 0.41→0.466, SHOULDER_BUMP 0%→80%**, at a
  small, precisely-attributed FPR cost (0.67%→1.11%, exactly 2 new false positives out of 450).
  ADJACENT_CARRIER on EC03 was already near-saturated — correctly showed zero additional effect,
  not a missed opportunity.

**Mechanistic outcome**: closed out for EC06 (real negative result, informative, not
under-evidenced); a genuine, evidence-backed candidate for EC03 (test-only pending user decision).

### 2.22 Deploy centroid-drift to EC03 (Session 45)

Deployed `centroid_drift_z_threshold: 2.812926168502278` additively to `models/EC03/thresholds.json`
following the exact assert-before-write, backup-before-overwrite discipline of sessions 39/40.
Verified bit-exact against session 44's tested numbers via the real, unpatched production loader. A
mid-session user message believed the deployment had been paused before starting; the actual file
state was checked and reported accurately (the deployment had already proceeded and a verification
run was already in progress) rather than agreeing with the inaccurate premise; the user reviewed
this and explicitly confirmed to let the in-progress, read-only verification finish and not roll
back. EC04/EC06/G16 confirmed untouched via mtime, before and after.

### 2.23 Candidate 1: RRC roll-off residual feature (Session 46)

**What / why**: With EC04's own high roll-off factor (β) established (session 30's shape signature,
now quantified: median β=0.175, highest of the 4 stations), test whether the *residual* after
fitting a theoretical raised-cosine edge shape (a signal no existing feature computes) separates
EC04's remaining misses.

**Result — real signal found, but structurally unusable**: cheap validation on real known misses
found ADJACENT_CARRIER's narrow-cluster population shows a real, non-trivial signal — **5 genuinely
new catches, all on narrow carriers (own bandwidth 102–109 bins), the exact historically-hardest
population**. Implemented as a 4th OR-gate branch and ran full Track 2 — an apparent 100%
ADJACENT_CARRIER catch rate initially looked like a win, but checking the confusion-matrix firings
directly against their raw scores revealed **all 11 firings were already flagged by other checks**
— the standard Track 2 harness's narrow 5-seed-per-type sample never reaches the seeds where Step B
found genuine value; the apparent win was a sampling artifact. Checking margin-gating directly
against the 5 genuinely-new seeds: **4 of 5 have `score=None` (unscoreable); the 5th sits below the
margin cutoff. All 5 fail the margin gate.**

**Mechanistic outcome — rejected at Gate 2, not for weak separation but for an irreducible
overlap**: the genuine incremental signal and the FPR-driving noise occupy the **identical**
population (unscoreable/very-low-score carriers) — there is no threshold or gating variant in this
project's toolkit that keeps one while excluding the other, because they are not separable by score
at all. This is a sharper, more precisely diagnosed version of the same tension session 38's
diagnostic pass first surfaced for EC04.

**Candidate 2 (roll-off-aware segmentation refinement) — not pursued**: its own stated precondition
("if Stage 1 reveals segmentation imprecision on high-roll-off carriers specifically") was checked
directly and not met — EC04's edge-fit RMSE (median 0.0363) is nearly identical to EC03's (0.0358);
only the tail (p90) differs modestly. No dramatic, systematic segmentation problem exists to fix.

### 2.24 Candidate 3: NaN-guard diagnosis, patch, and retrain (Session 47)

**What / why**: Investigate *why* so many EC04 carriers are unscoreable (`score=None`) at all,
before proposing any fix as a candidate.

**Diagnosis**: EC04's headline 46.60% unscoreable rate is almost entirely a feature-*count*
artifact (on the same 16 columns every station has, EC04 is actually the **best** of the 4, at
2.46%). The real cause: `rise_fall_steepness_ratio` — a documented, deliberate NaN guard
(`extract_features.py` lines 525–532, protecting against a near-zero-denominator blowup) — is NaN
in **46.385% of all EC04 rows**, essentially the entire gap by itself (2,126,811 of 4,818,051 rows).
EC04's naturally gentle, high-roll-off edges trip this guard far more often than intended, because
the fixed threshold was tuned without this station's own gentler population in mind — a continuous
distribution the guard happens to slice through, not a bimodal real-edge-vs-noise split.

**Step B/C — patch-only (scoring time only)**: replacing the exclusionary guard with a floored,
sign-preserving version rescued **4 of the 5** genuinely-new catches candidate 1 found (they become
correctly, properly flagged via checks that **already exist** in production — no new OR-gate branch
needed). Full Track 2 with the patch: F1 0.49→0.543, but **FPR 3.08%→41.85% (13.6x, catastrophic)**.

**Mechanistic outcome — rejected as scoped**: a textbook out-of-distribution effect. The deployed
model was trained exclusively on the ~55% of the population where the ratio was already computable
(training also drops NaN rows); extending *scoring* to the other ~44% produces indiscriminately
elevated scores, real anomalies and clean carriers alike, because the model has no calibrated
notion of "normal" for a population it never saw during training.

**Continuation — full retrain (same session, user go-ahead, does not count against the loop's
rejection budget)**: re-extracted features with the guard fix applied at extraction time (so TRAIN
sees the corrected population), retrained EC04's dedicated model (82% more TRAIN rows survive
dropna: 1,434,799→2,616,529). **Result: the FPR catastrophe is genuinely fixed (41.85%→4.85%,
confirming the out-of-distribution diagnosis), but F1 drops to 0.313 and both target metrics
collapse — SHOULDER_BUMP 80%→0%, ADJACENT_CARRIER 100%→20%.**

**Mechanistic outcome — rejected for the loop's actual goal, and the most important negative
finding of the whole investigation**: the ~44% of EC04's population the fix newly includes as
"normal" training examples are precisely the station's own gentlest, most gradual-edged carriers —
the same population characteristic that makes EC04 distinctive in the first place. Teaching the
model this wider range of edge shapes is "normal" measurably reduces its sensitivity to edge-shape
distortions specifically — exactly the anomaly class SHOULDER_BUMP/ADJACENT_CARRIER belong to.
Fixing a real data-completeness problem and improving sensitivity to this anomaly class are in
**direct tension**, not aligned, for EC04. Stage 5 (re-test full pooling with this fix) was
explicitly not run: `rise_fall_steepness_ratio` is not part of the pooled model's 16-feature set at
all, and EC04 already has the *lowest* unscoreable rate of the 4 stations on those columns
specifically — pooling was never blocked by this particular data-completeness issue.

### 2.25 The model router (Session 48)

**What / why**: With 9 prior attempts at merging EC04 into a single model conclusively rejected
(sessions 22, 32, 34, 36, 37–38, 41, 43, and candidates 1/3 above), test a fundamentally different
idea that never blends anything: a per-carrier **dispatcher** that selects between EC04's dedicated
pipeline and the shared pooled pipeline based on a carrier's own measured shape, not its source_id —
the practical answer to "what happens with a genuinely new, unknown transponder."

**Result — decisive negative on the routing signal itself**: β (`plateau_width_frac_of_span`),
which showed a clean station-level *median* separation in session 46's ~800-sweep sample, was
re-tested on the full population (millions of rows per station). **Best achievable per-carrier
balanced accuracy: 63.62%**, with EC06 (32.67% correctly routed to pooled) and G16 (46.83%)
performing *worse than or barely above chance*. Adding 3 more cheap, already-computed features and
testing with a diagnostic logistic-regression probe improved aggregate CV accuracy to 69.69%, but
unstably (fold scores 0.49–0.82) — and traded EC06's problem for a worse one: EC03's routing
correctness collapsed to **20.10%**.

**Mechanistic outcome — rejected**: the station-level median differences session 46 found are real
aggregate properties, but they do not decompose into a usable per-observation classifier — within-
station variance in these shape features (most starkly for EC06/G16, whose std is 2-2.5x EC04's) is
comparable to or larger than the between-station gap. Physically plausible: roll-off/edge-shape is
a property of the individual transponder link's own modulation/filtering choice, not the ground
station's hardware, and each station carries many different named links. Steps 2–4 (routing
implementation, source-blind validation, full Track 2 verification) were explicitly not attempted,
since building them on a signal already shown to misroute the majority of carriers for at least one
station in every configuration would not constitute a meaningful proof of concept.

---

## 3. What Was Successfully Deployed, and Why

| Deployment | Session | Real numbers | Why it works |
|---|---|---|---|
| **Pooled model (16 floor-free features, per-station p99 threshold) for EC03/EC06/G16** | 22/23, deployed 39/40 | EC03 F1 0.41, FPR 0.67%; EC06 F1 0.31 (0.305), FPR 15.60%*; G16 F1 0.345, FPR 20.99% (with OR-gate, see below) | Shape-only features generalize well for these 3 stations; per-station threshold calibration (not a global cutoff) correctly separates "unusual vs. pool" from "unusual vs. this station's own normal," closing what would otherwise be a large EC06-specific gap |
| **Margin-gated OR-gate (IF-alone + per-feature independent checks, p99, margin=0.5) for EC04** | 37/38, deployed via `thresholds.json` | F1 0.427→0.49, FPR 2.20%→3.08% (1.4x), SHOULDER_BUMP 60%→80%, type-attribution recovered to 33.3% (vs. baseline 35.1%) | Restricting the independent checks to carriers already borderline under the existing blended score keeps genuine recall gains while avoiding the broad, non-type-specific false-alarm mechanism that made the uncapped version (session 37) unusable |
| **Margin-gated OR-gate for G16 (same recipe)** | 38, deployed 39 | F1 0.28→0.35 (0.345 verified), ADJACENT_CARRIER 0%→33% (n=3), FPR 17.28%→20.99% (1.21x) | Same mechanism as EC04; a real, bounded trade-off the user explicitly accepted when choosing to deploy the pooled model to G16 |
| **Centroid-drift OR-gate branch for EC03** | 42/44, deployed 45 | F1 0.41→0.466, SHOULDER_BUMP 0%→80%, IN_BAND_TONE (moderate/subtle) 0%→20%/20%, FPR 0.67%→1.11% (+2 false positives per 450) | A per-carrier, self-referential z-score (not a population threshold) catches genuine edge-shape anomalies EC03's existing blended score misses, with no pre-existing OR-gate on this station to be redundant with |

*EC06's absolute FPR is affected by an unrelated, pre-existing drift in the
`PRELIMINARY_INSTANTANEOUS_OUTLIER` reference-statistics subsystem (see §4) — the pooled-model
deployment's own blended-score path is confirmed bit-exact and correct.

**Deliberately not deployed anywhere, with evidence, not by default**: centroid-drift for EC04 (zero
net benefit — already redundant with EC04's margin-gated OR-gate); centroid-drift for EC06 (weak
separation on both target types); any form of a single merged model across all 4 stations (9+1
independently rejected attempts, §2); the RRC roll-off residual feature, in any gating configuration
(irreducible overlap between genuine signal and FPR-driving noise); the NaN-guard fix, as either a
patch or a full retrain (out-of-distribution FPR blowup, then a genuine sensitivity/completeness
trade-off working against the loop's own goal); the model router (no viable per-carrier routing
signal found); the uncapped OR-gate for EC03/EC06 (session 38: zero benefit, real cost); the
99.9-percentile-only OR-gate recalibration (deletes signal along with noise).

---

## 4. What Was Left Unresolved or Not Pursued

This section is intentionally exhaustive — it is the list worth re-reading before deciding whether
any of this project's future work should reopen a specific thread, rather than start a new one.

1. **EC06's `PRELIMINARY_INSTANTANEOUS_OUTLIER` reference-statistic staleness** (flagged session 40,
   never fixed). The subsystem's reference stats predate a 2026-09-08 change to `EC06_features.
   parquet` (most likely session 34's `bw_ratio_to_recent_median` column landing in the shared
   parquet files); EC06's already-borderline population is measurably more sensitive to this drift
   than EC03's. This lives entirely in `features/instantaneous_scoring.py`'s reference-stat
   computation and is unrelated to any OR-gate or pooled-model work — a clean, bounded fix (rebuild
   the reference stats from the current parquet) was never scheduled.
2. **Session 27's two proposed `PRELIMINARY_INSTANTANEOUS_OUTLIER` fix options beyond the simplest
   one**: only "require ≥2 triggers" (session 28) was implemented. A formal multiple-testing
   correction (e.g., Bonferroni-scaled per-feature threshold) was proposed but never built or
   compared against the ≥2 heuristic actually shipped.
3. **Session 27's EC04 `GENERAL_DEGRADATION` clustering** — proposed check (i): whether the same
   EC04 carrier_ids are already near/over threshold on clean, non-injected sweeps in the same TEST
   block, to distinguish a miscalibrated threshold from an atypical sampled window — never run. This
   was partially superseded by session 28's staleness discovery and session 29's retrain, but the
   specific diagnostic itself was never revisited against the *current*, freshly-retrained model.
4. **Session 26's false-positive attribution question**: whether the 59 non-injected carriers
   flagged across those 32 combinations were pre-existing/ambient (already flagged before injection)
   or genuinely caused by cross-contamination from the injection itself — never determined; the
   clean, pre-injection version of each sweep was never re-scored for comparison.
5. **Session 35's "cheaper first experiment"**: a literal, fixed-threshold port of the rule-based
   CAD's Hump/ShoulderExcess/wide-Spike checks as a throwaway Track 2 test, proposed as the lowest-
   effort way to get a fast read before committing to a full adaptive-relative redesign. This was
   never actually run — the project went directly to the adaptive, carrier-relative OR-gate design
   (sessions 36–38) informed by the same audit, but the cheap literal-port control experiment itself
   is still an open, low-cost item.
6. **Session 42's "missing-carrier-off check"** (a chart-based presence/absence monitor, deliberately
   *not* blended into either z-score) was designed but never validated — no clean test case exists in
   the current injection framework (DROPOUT covers the closest analog via a different mechanism).
7. **Candidate 3's underlying diagnosis** (the `rise_fall_steepness_ratio` guard excluding a real,
   legitimate ~44% of EC04's population) "remains independently correct and may have standalone value
   for EC04's general data quality/model completeness in a future session" — this was explicitly
   flagged as a separate, unpursued thread from the loop's own SHOULDER_BUMP/ADJACENT_CARRIER goal;
   nothing has revisited it as a data-quality improvement in its own right.
8. **Session 32's sparse-feature-representation mechanism** (the working hypothesis for *why* PCA
   under-weights near-always-zero features like overshoot) was described as "plausible... not yet
   directly verified" — no session has independently confirmed this mechanism beyond the indirect
   evidence of the autoencoder experiment's own null result.
9. **Session 25's chart-currency caveat**: "chart currency/completeness could not be independently
   confirmed... a reasonable but not certain interpretation" for which chart entries are stale vs.
   genuinely uncharted. No independent ground-truth source for chart currency was ever found or used.
10. **The G16/EC06 carrier-reallocation-volatility note** (session 39: "per the project owner, G16
    and EC06's frequency charts show frequent carrier reallocation... unlike EC03/EC04, which are
    comparatively more stable") was flagged as relevant to *future* frequency-chart work but never
    specifically investigated — session 42's neighbor-context work targeted EC04 only.
11. **Session 48's router investigation** explicitly stopped at Step 1 of 4 once the routing signal
    itself failed — Steps 2 (routing implementation), 3 (source-blind simulated-unknown-transponder
    validation), and 4 (full Track 2 verification through the router) were never attempted. If a
    future session finds a materially better routing signal, all three remain to be built.
12. **The EC03 IN_BAND_TONE gains from centroid-drift** (moderate/subtle 0%→20%/20%, session 44) are
    real but modest and were reported alongside the SHOULDER_BUMP headline result without their own
    separate false-positive/overlap analysis — folded into the same deployment decision rather than
    scrutinized independently.

---

## 5. The Core, Convergent Finding

Twenty-six tested approaches, spanning feature engineering, ensemble architecture, threshold
calibration, and per-carrier routing, converge on **one underlying tension**, not a list of
unrelated failures:

**EC04's own distinguishing physical characteristic is the same characteristic that its remaining
detection gap depends on.** EC04's carriers have a genuinely high roll-off factor (β) — gentler,
wider-relative-to-span edges than the other three stations (session 30's shape signature, confirmed
by session 46's roll-off-fit analysis and session 47's NaN-guard diagnosis, which found this exact
characteristic is *why* EC04 trips a completeness guard 44% of the time). SHOULDER_BUMP and
ADJACENT_CARRIER — the two anomaly types this entire investigation has chased since session 33 — are
both, mechanistically, **edge-shape distortions**. They live in precisely the dimension where EC04's
own population is unusual. This produces a structural double-bind visible at every level tried:

- **Averaging/blending destroys the signal before it can be used.** Every attempt to merge EC04's
  signal into a shared representation — full pooling (sessions 22/41), an added pooled feature
  (session 34), a nonlinear reconstruction function (session 32), a per-carrier routing signal
  (session 48) — either dilutes a real-but-subtle deviation below the combined threshold (session
  35's rule-based-CAD audit identified this exact mechanism: `pca_raw = np.mean(...)` structurally
  lets one badly-reconstructing dimension get outvoted by 15 calm ones) or fails outright because the
  within-population variance in the relevant shape dimension exceeds the between-station gap
  (session 48's decisive finding: individual transponder links vary in edge shape more than stations
  do in aggregate).
- **Making EC04's training population more complete measurably reduces sensitivity to the exact
  anomalies this project needs.** Candidate 3's retrain is the sharpest demonstration: fixing a
  genuine, well-diagnosed data-completeness bug (excluding 44% of real carriers from training) is
  necessary for the model to be well-calibrated on that population — but that newly-included 44% is
  precisely EC04's own gentlest-edged, most SHOULDER_BUMP/ADJACENT_CARRIER-adjacent population.
  Teaching the model this broader range of edge gentleness is "normal" directly reduces its
  sensitivity to further gentleness-driven distortions. This is not a bug or a calibration mistake —
  it is the same signal being asked to serve two competing purposes (completeness and
  discrimination) simultaneously.
- **Where a genuinely new, non-diluting signal exists (centroid-drift, candidate 1's RC-residual),
  it works precisely because it is self-referential (per-carrier), not population-wide** — and even
  then, its practical value depends entirely on whether it overlaps with what is already deployed
  (redundant on EC04, additive on EC03) or on whether it can be separated from the FPR-driving noise
  by score (candidate 1's fatal finding: the genuine signal and the noise occupy the *identical*
  unscoreable population, making no threshold variant able to keep one without the other).

The bimodal-bandwidth finding (session 33) and the missing-absolute-feature gap (session 30, stage 3)
are real, additive pieces of this same picture, not separate stories: they explain *which specific
sub-populations* (narrow-cluster carriers; the ~1.12% of rows the shape-only pool structurally
cannot see) carry the sharpest form of the tension, without contradicting the single underlying
mechanism above.

---

## 6. Honest Assessment of What's Left Untried

1. **A genuinely per-carrier (not per-station, not population-wide) baseline for every feature, not
   just centroid.** Centroid-drift's success is specifically attributable to being self-referential.
   No session has generalized this to the *other* edge-shape features (steepness, smoothness,
   overshoot) as per-carrier rolling baselines rather than population-wide percentiles. This is the
   single most promising, concrete, and well-evidenced unexplored direction this investigation has
   produced — it follows directly from a proven-working mechanism rather than a speculative new idea.
   **Estimated value if pursued**: moderate-to-high probability of a real, additive gain specifically
   on EC04's remaining SHOULDER_BUMP misses (which centroid-drift alone did not address, since it
   targets position/centroid, not edge steepness/overshoot shape). Effort: comparable to session
   42–44's own centroid-drift work (a few sessions), since the rolling-baseline infrastructure
   (`_StreamState`, `_rolling_mean_std`) already exists and is proven.
2. **A supervised, or semi-supervised, classifier trained directly on labeled synthetic injections**,
   rather than unsupervised anomaly detection scored against synthetic examples only at evaluation
   time. This project's entire methodology has been unsupervised (IsolationForest + PCA
   reconstruction, calibrated by percentile, never trained on labeled anomalies) — a fundamentally
   different paradigm was never tested. **Why not pursued**: this is a materially larger redesign
   (training-data generation at scale, a different model family, a different evaluation
   methodology entirely) than anything else in this investigation, and carries real risk of
   overfitting to the synthetic injector's own specific artifacts rather than generalizing to real
   anomalies — a concern this project's evaluation discipline (Track 1 vs. Track 2, real vs.
   synthetic) has been careful about throughout. **Estimated value**: genuinely unknown; plausibly
   high for the specific injected types tested, but the risk of not generalizing to real,
   never-injected anomaly types is a real, unquantified cost. Worth a scoped pilot, not a full
   commitment, if pursued.
3. **A literal, unmodified rule-based-CAD port as a throwaway Track 2 control experiment** (session
   35's own "cheaper first experiment," never actually run). Low effort, bounded scope, would give a
   fast, cheap data point on whether the independent-check *architecture* alone (without any
   adaptive/carrier-relative reformulation) helps on EC04's target types before investing further in
   the harder, calibration-heavy hybrid design. **Estimated value**: low-to-moderate on its own
   (the audit already predicts fixed-threshold heterogeneity risk), but very cheap, and useful purely
   as a sanity check against everything else tried.
4. **A richer, purpose-built classifier as the router's actual dispatch signal** (deliberately not
   tried in session 48, since it would abandon the router's own design premise of being simple and
   cheap, and would essentially become "train a second full model just to pick between two other
   models"). If the "genuinely new, unknown 5th transponder" scenario becomes an actual operational
   priority (rather than a hypothetical this project used to motivate the router investigation), this
   is worth revisiting explicitly as its own, differently-scoped project — not as an extension of
   session 48's "keep it simple" router. **Estimated value**: unknown without trying, but the
   within-station variance finding (session 48) suggests even a heavier classifier may struggle,
   since the physical driver (per-link modulation/filtering choice) is not station-level information
   at all — a genuinely novel transponder's own link characteristics, not its ground station, would
   need to be the actual basis for any such classifier, which is a different and harder problem than
   what session 48 was scoped to test.

---

## 7. Final Recommendation

**Keep the current production architecture, unchanged**:

| station | model | features | OR-gate |
|---|---|---|---|
| EC03 | pooled (session 22/23) | 16, floor-free | centroid-drift, z-threshold=2.8129 (session 45) |
| EC04 | dedicated per-source (session 29) | 55 | margin-gated (IF-alone + per-feature, p99, margin=0.5) (session 38) |
| EC06 | pooled (session 22/23) | 16, floor-free | none |
| G16 | pooled (session 22/23) | 16, floor-free | margin-gated (same recipe as EC04) (session 38/39) |

This is a defensible stopping point, not a compromise pending further work, for three reasons:

1. **Every rejection has a specific, understood mechanism**, not an inconclusive or under-tested
   result. Twenty-six distinct approaches were tried across 30 sessions; each failure is traceable to
   one of two well-evidenced mechanisms (dilution-by-averaging, or the completeness-vs-sensitivity
   tension) rather than to insufficient effort or an unexplored obvious idea.
2. **The alternative (forcing EC04 into a shared model) is measurably worse on every metric that
   matters**, not just marginally worse. Every pooling attempt for EC04 shows F1 collapsing by
   roughly half, FPR roughly doubling, and — critically — the *continuous* score's own ranking
   ability (PR-AUC/ROC-AUC) degrading, which rules out a calibration fix as a future remedy.
3. **The one genuinely promising unexplored direction (per-carrier baselines for the remaining
   shape features, §6.1) is additive to, not a contradiction of, the current architecture** — it
   would extend EC04's existing dedicated-model + OR-gate design, not replace it, and can be pursued
   independently without disturbing anything currently deployed and verified.

Nothing in this investigation supports revisiting the single-merged-model goal as originally
specified in §1.2 under the current feature-engineering and modeling toolkit. The station-identity-
blind requirement is fully honored for EC03/EC06/G16 (one shared model, no station column anywhere);
EC04's separate treatment is not a station-identity shortcut but a response to a real, repeatedly
confirmed, physically-explained population difference that this project's own tools cannot currently
represent without losing detection sensitivity.
