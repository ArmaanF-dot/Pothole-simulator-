# Risk model evaluation

_Generated 2026-10-17T13:48:31+00:00 by `python -m roadsense.models.risk` (risk-v0.1). as_of 2026-10-12._

**Labels are SYNTHETIC** (Generator 2, seed 2026). Scores on synthetic labels are a pipeline check, not proof the model works on real roads. The real-world check below uses real FixMyStreet reports.

Inputs: segments `data/processed/segments.parquet`, weather `data/processed/weather_weekly.parquet`, esal_day `data/processed/load.parquet`. 

Model: LightGBM, monotone +1 on load, rain, freeze-thaw and rain-then-frost, -1 on recent preventive treatment; scale_pos_weight for imbalance; isotonic calibration on the last 15% of training weeks. Top 5% = mean over weeks of precision among that week's top 5% of segments.

## Time split (last 12 months held out, 30-day gap)

**y7** (test rows 390,480, base rate 0.0078)

| Scorer | PR-AUC | Precision in top 5% | Brier |
|---|---|---|---|
| model | 0.083 | 0.045 | 0.00779 |
| road age only | 0.009 | 0.012 | 0.00778 |
| prior pothole count only | 0.029 | 0.041 | 0.00768 |

**y30** (test rows 390,480, base rate 0.0308)

| Scorer | PR-AUC | Precision in top 5% | Brier |
|---|---|---|---|
| model | 0.253 | 0.164 | 0.02613 |
| road age only | 0.036 | 0.048 | 0.02987 |
| prior pothole count only | 0.095 | 0.146 | 0.02875 |

## Spatial split (wards held out: Banister & Polygon, Bassett, Shirley)

**y7** (test rows 61,920, base rate 0.0058)

| Scorer | PR-AUC | Precision in top 5% | Brier |
|---|---|---|---|
| model | 0.054 | 0.030 | 0.00584 |
| road age only | 0.006 | 0.007 | 0.00582 |
| prior pothole count only | 0.014 | 0.026 | 0.00579 |

**y30** (test rows 61,920, base rate 0.0236)

| Scorer | PR-AUC | Precision in top 5% | Brier |
|---|---|---|---|
| model | 0.165 | 0.118 | 0.02121 |
| road age only | 0.026 | 0.025 | 0.02315 |
| prior pothole count only | 0.050 | 0.095 | 0.02276 |

## Leave-one-city-out

Not run: only Southampton is in the table. Port-city features come from lane A; logged in DATA_GAPS.md.

## Calibration (time split, y30)

![calibration](risk_calibration.png)

| Mean predicted | Observed | Rows |
|---|---|---|
| 0.0004 | 0.0012 | 24,235 |
| 0.0014 | 0.0022 | 48,329 |
| 0.0028 | 0.0031 | 33,252 |
| 0.0039 | 0.0054 | 87,551 |
| 0.0087 | 0.0121 | 30,617 |
| 0.0122 | 0.0154 | 37,268 |
| 0.0204 | 0.0272 | 40,687 |
| 0.0393 | 0.0459 | 42,698 |
| 0.1467 | 0.1598 | 45,843 |

## Real-world check: FixMyStreet Southampton (real data)

Hold-out: real FixMyStreet road-surface reports from 2025-10-12 to 2026-10-12 (`data\processed\fms_roads_clean.csv`), never used in training. 40 reports, 38 within 15 m of a scored segment. Segments ranked as at 2025-10-06.

| Scorer | Reports in top 10% of segments | Share | Lift vs random (0.10) |
|---|---|---|---|
| model | 7 | 0.184 | 1.842 |
| road age only | 6 | 0.158 | 1.579 |
| prior pothole count only | 5 | 0.132 | 1.316 |

Caveat: only 38 hold-out reports, so the lift is very noisy. Southampton FixMyStreet volume is low (no reports 2020 to 2022).

## Wear model (Weibull AFT, lifelines)

Fitted on 1,464 segments resurfaced inside the log window (531 with a first pothole). Shape rho = 0.87. Coefficients (log scale of time-to-first-pothole; negative = wears faster): log_esal_day -0.606, freeze_thaw_rate +0.100, in_flood_area -0.291. Resurfacing history is SYNTHETIC, so wear is too.

## Not done (see DATA_GAPS.md)

- Synthetic plus real labels in one model: not done; the real-label model is separate (section below).
- Leave-one-city-out: waits on lane A's port-city data.

<!-- real-label-eval:start -->
## Real-label evaluation with uncertainty (FixMyStreet, real data)

Model trained on real FixMyStreet labels (`data\processed\fms_snapped.csv`), lane-a-data commit d3cb9a9, run read-only (lane A files not committed here). Score = share of a year's reports that land on the top 10% of road length, averaged over the test years. Ranges: paired cluster bootstrap that resamples test **segments** with replacement (1,000 resamples, seed 2026) and scores every method on the same resample. FixMyStreet counts measure reporting, not true pothole rates.

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
