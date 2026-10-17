# Risk model evaluation

_Generated 2026-10-17T12:56:04+00:00 by `python -m roadsense.models.risk` (risk-v0.1). as_of 2026-10-12._

**Labels are SYNTHETIC** (Generator 2, seed 2026). Scores on synthetic labels are a pipeline check, not proof the model works on real roads. The real-world check below uses real FixMyStreet reports.

Inputs: segments `mock`, weather `mock`, esal_day `mock`. **Lane A inputs were mocked for this run**, so rerun after Merge 1.

Model: LightGBM, monotone +1 on load, rain, freeze-thaw and rain-then-frost, -1 on recent preventive treatment; scale_pos_weight for imbalance; isotonic calibration on the last 15% of training weeks. Top 5% = mean over weeks of precision among that week's top 5% of segments.

## Time split (last 12 months held out, 30-day gap)

**y7** (test rows 373,728, base rate 0.0069)

| Scorer | PR-AUC | Precision in top 5% | Brier |
|---|---|---|---|
| model | 0.068 | 0.036 | 0.00671 |
| road age only | 0.007 | 0.009 | 0.00689 |
| prior pothole count only | 0.018 | 0.028 | 0.00684 |

**y30** (test rows 373,728, base rate 0.0288)

| Scorer | PR-AUC | Precision in top 5% | Brier |
|---|---|---|---|
| model | 0.228 | 0.142 | 0.02615 |
| road age only | 0.031 | 0.039 | 0.02796 |
| prior pothole count only | 0.073 | 0.114 | 0.02720 |

## Spatial split (wards held out: Mock ward 01, Mock ward 03, Mock ward 13)

**y7** (test rows 76,752, base rate 0.0078)

| Scorer | PR-AUC | Precision in top 5% | Brier |
|---|---|---|---|
| model | 0.067 | 0.040 | 0.00753 |
| road age only | 0.008 | 0.010 | 0.00774 |
| prior pothole count only | 0.020 | 0.031 | 0.00769 |

**y30** (test rows 76,752, base rate 0.0320)

| Scorer | PR-AUC | Precision in top 5% | Brier |
|---|---|---|---|
| model | 0.236 | 0.164 | 0.02860 |
| road age only | 0.032 | 0.041 | 0.03099 |
| prior pothole count only | 0.079 | 0.130 | 0.03011 |

## Leave-one-city-out

Not run: only Southampton is in the table. Port-city features come from lane A; logged in DATA_GAPS.md.

## Calibration (time split, y30)

![calibration](risk_calibration.png)

| Mean predicted | Observed | Rows |
|---|---|---|
| 0.0001 | 0.0013 | 30,519 |
| 0.0005 | 0.0015 | 24,962 |
| 0.0005 | 0.0028 | 54,800 |
| 0.0008 | 0.0045 | 33,376 |
| 0.0009 | 0.0053 | 43,065 |
| 0.0013 | 0.0086 | 34,259 |
| 0.0024 | 0.0156 | 40,216 |
| 0.0043 | 0.0272 | 30,224 |
| 0.0106 | 0.0494 | 44,457 |
| 0.0650 | 0.1638 | 37,850 |

## Real-world check: FixMyStreet Southampton (real data)

Hold-out: real FixMyStreet road-surface reports from 2025-10-12 to 2026-10-12 (`data\processed\fms_roads_clean.csv`), never used in training. 40 reports, 10 within 15 m of a scored segment. Segments ranked as at 2025-10-06.

| Scorer | Reports in top 10% of segments | Share | Lift vs random (0.10) |
|---|---|---|---|
| model | 0 | 0.000 | 0.000 |
| road age only | 0 | 0.000 | 0.000 |
| prior pothole count only | 0 | 0.000 | 0.000 |

Caveat: segments are mocked, so real report locations do not line up with real streets. This check is only meaningful after lane A's segments land.

Caveat: only 10 hold-out reports, so the lift is very noisy. Southampton FixMyStreet volume is low (no reports 2020 to 2022).

## Wear model (Weibull AFT, lifelines)

Fitted on 1,523 segments resurfaced inside the log window (630 with a first pothole). Shape rho = 0.92. Coefficients (log scale of time-to-first-pothole; negative = wears faster): log_esal_day -0.510, freeze_thaw_rate -0.146, in_flood_area -0.444. Resurfacing history is SYNTHETIC, so wear is too.

## Not done (see DATA_GAPS.md)

- Model trained on synthetic plus real FixMyStreet labels: skipped, too few dated Southampton reports overlap the feature window.
- Leave-one-city-out: waits on lane A's port-city data.

<!-- real-label-eval:start -->
## Real-label evaluation with uncertainty (FixMyStreet, real data)

Model trained on real FixMyStreet labels (`data\processed\fms_snapped.csv`), lane-a-data commit 2a2bbac, run read-only (lane A files not committed here). Score = share of a year's reports that land on the top 10% of road length, averaged over the test years. Ranges: paired cluster bootstrap that resamples test **segments** with replacement (1,000 resamples, seed 2026) and scores every method on the same resample. FixMyStreet counts measure reporting, not true pothole rates.

**Full model** = physical features + past-report features (reports on the segment and its neighbours in earlier years). **Physical only** = same setup with no past-report feature at all: traffic load (esal_day, DfT HGV and bus flow), bus routes, bus stop, junction, flood area, highway class, road length, and the previous year's ward weather (rain, freeze-thaw, frost hours, rain-then-frost, hot days).

### Southampton, test years

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 38.6% | 31.0% to 45.3% |
| physical only | 19.9% | 12.8% to 26.4% |
| last year reports | 33.7% | 24.5% to 38.9% |
| load x past reports | 19.8% | 14.5% to 25.2% |
| model minus last-year (paired) | 4.9% | 0.9% to 12.1% |
| physical-only minus last-year (paired) | -13.7% | -20.1% to -4.1% |
| model minus physical-only (paired) | 18.7% | 12.4% to 25.4% |

n = 381 test reports on 8,145 test segments (2018, 2019). Model ahead of the last-year baseline in 99% of 1,000 resamples (seed 2026).

Southampton, test years: model 39% (31%-45%) vs last-year baseline 34% (24%-39%); model ahead in 99% of resamples. The difference 5% (95% 1% to 12%) excludes 0, so the model beats the baseline. Physical-only model (no past reports): 20% (13%-26%); vs last-year baseline -14% (95% -20% to -4%), so it falls short of the baseline. Full model vs physical-only: 19% (95% 12% to 25%), past reports add real signal.

Feature reliance (full model, share of mean |SHAP| on 16,290 test rows): past-report features **14%**; by group: road class and length 47%, weather 25%, past reports 14%, bus, junction, flood 8%, traffic load 6%, city 0%. Top features: length_m 43%, wx_frost_hours 11%, rep_nb_prev1 7%. Mean |SHAP| averages over every segment, most of which have no report history, so it understates how much the top of the ranking leans on past reports; the paired model-minus-physical-only difference above is the direct measure. Weather is a ward-year summary with few distinct years in training, so its share partly reflects year-to-year differences in reporting.

### Southampton, frozen 2026 check (Jan to Oct)

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 12.1% | 2.6% to 24.1% |
| physical only | 30.3% | 14.8% to 48.7% |
| last year reports | 12.1% | 2.8% to 26.9% |
| load x past reports | 21.2% | 8.3% to 40.7% |
| model minus last-year (paired) | 0.0% | -14.3% to 10.7% |
| physical-only minus last-year (paired) | 18.2% | 0.0% to 36.4% |
| model minus physical-only (paired) | -18.2% | -36.7% to 0.0% |

n = 33 test reports on 8,145 test segments (2026). Model ahead of the last-year baseline in 32% of 1,000 resamples (seed 2026).

Southampton, frozen 2026 check (Jan to Oct): model 12% (3%-24%) vs last-year baseline 12% (3%-27%); model ahead in 32% of resamples. The difference 0% (95% -14% to 11%) includes 0, so the model matches the baseline rather than beats it. Physical-only model (no past reports): 30% (15%-49%); vs last-year baseline 18% (95% 0% to 36%), so it matches the baseline rather than beats it. Full model vs physical-only: -18% (95% -37% to 0%), past reports add no clear signal. Only 33 reports, so the interval is wide.

Brighton 2023 to 2025: waiting for lane A's Brighton labels. The same code runs once they land.

<!-- real-label-eval:end -->
