# Risk model evaluation

_Generated 2026-10-17T17:52:38+00:00 by `python -m roadsense.models.risk` (risk-v0.1). as_of 2026-10-12._

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

Not applicable to this synthetic-label model: synthetic council data exists for Southampton only. Leave-one-city-out on real labels (Southampton, Brighton, Portsmouth) is in the real-label section below.

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
- Leave-one-city-out for this synthetic-label model: not applicable (Southampton-only synthetic data); see the real-label section.

<!-- real-label-eval:start -->
## Real-label evaluation with uncertainty (FixMyStreet, real data)

Model trained on real FixMyStreet labels (`data\processed\fms_snapped.csv`). Score = share of a year's reports that land on the top 10% of road length, averaged over the test years. Ranges: paired cluster bootstrap that resamples test **segments** with replacement (1,000 resamples, seed 2026) and scores every method on the same resample. FixMyStreet counts measure reporting, not true pothole rates.

**Full model** = physical features + past-report features (reports on the segment and its neighbours in earlier years). **Physical only** = same setup with no past-report feature at all: traffic load (esal_day, DfT HGV and bus flow), bus routes, bus stop, junction, flood area, highway class, road length, and the previous year's ward weather (rain, freeze-thaw, frost hours, rain-then-frost, hot days).

### Brighton, test years

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 31.2% | 27.2% to 34.8% |
| physical only | 21.2% | 17.7% to 24.6% |
| last year reports | 21.7% | 18.6% to 26.4% |
| load x past reports | 13.6% | 10.8% to 18.5% |
| model minus last-year (paired) | 9.5% | 4.9% to 12.2% |
| physical-only minus last-year (paired) | -0.5% | -7.0% to 3.6% |
| model minus physical-only (paired) | 10.1% | 5.8% to 14.1% |

n = 802 test reports on 8,179 test segments (2023, 2024, 2025). Model ahead of the last-year baseline in 100% of 1,000 resamples (seed 2026).

Brighton, test years: model 31% (27%-35%) vs last-year baseline 22% (19%-26%); model ahead in 100% of resamples. The difference 10% (95% 5% to 12%) excludes 0, so the model beats the baseline. Physical-only model (no past reports): 21% (18%-25%); vs last-year baseline -1% (95% -7% to 4%), so it matches the baseline rather than beats it. Full model vs physical-only: 10% (95% 6% to 14%), past reports add real signal.

Feature reliance (full model, share of mean |SHAP| on 24,537 test rows): past-report features **12%**; by group: weather 34%, road class and length 30%, past reports 12%, bus, junction, flood 12%, traffic load 6%, city 5%. Top features: length_m 27%, wx_rain_30d_mean 18%, rep_nb_prev1 9%. Mean |SHAP| averages over every segment, most of which have no report history, so it understates how much the top of the ranking leans on past reports; the paired model-minus-physical-only difference above is the direct measure. Weather is a ward-year summary with few distinct years in training, so its share partly reflects year-to-year differences in reporting.

### Southampton, test years

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 41.6% | 33.9% to 47.9% |
| physical only | 10.4% | 7.1% to 14.3% |
| last year reports | 33.7% | 24.5% to 38.9% |
| load x past reports | 19.8% | 14.5% to 25.2% |
| model minus last-year (paired) | 7.9% | 3.1% to 15.5% |
| physical-only minus last-year (paired) | -23.3% | -29.3% to -13.0% |
| model minus physical-only (paired) | 31.2% | 23.1% to 38.1% |

n = 381 test reports on 8,145 test segments (2018, 2019). Model ahead of the last-year baseline in 100% of 1,000 resamples (seed 2026).

Southampton, test years: model 42% (34%-48%) vs last-year baseline 34% (24%-39%); model ahead in 100% of resamples. The difference 8% (95% 3% to 15%) excludes 0, so the model beats the baseline. Physical-only model (no past reports): 10% (7%-14%); vs last-year baseline -23% (95% -29% to -13%), so it falls short of the baseline. Full model vs physical-only: 31% (95% 23% to 38%), past reports add real signal.

Feature reliance (full model, share of mean |SHAP| on 16,290 test rows): past-report features **10%**; by group: weather 29%, road class and length 25%, city 22%, past reports 10%, bus, junction, flood 8%, traffic load 5%. Top features: length_m 23%, city_code 22%, wx_rain_30d_mean 17%. Mean |SHAP| averages over every segment, most of which have no report history, so it understates how much the top of the ranking leans on past reports; the paired model-minus-physical-only difference above is the direct measure. Weather is a ward-year summary with few distinct years in training, so its share partly reflects year-to-year differences in reporting.

### Brighton, leave-one-city-out (trained on the other cities, all usable years)

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 18.4% | 15.9% to 21.1% |
| physical only | 12.3% | 10.0% to 14.6% |
| last year reports | 16.5% | 12.9% to 21.2% |
| load x past reports | 16.6% | 13.4% to 20.0% |
| model minus last-year (paired) | 1.9% | -3.0% to 6.0% |
| physical-only minus last-year (paired) | -4.2% | -9.4% to -0.0% |
| model minus physical-only (paired) | 6.1% | 3.7% to 9.0% |

n = 1,512 test reports on 8,179 test segments (2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025). Model ahead of the last-year baseline in 76% of 1,000 resamples (seed 2026).

Brighton, leave-one-city-out (trained on the other cities, all usable years): model 18% (16%-21%) vs last-year baseline 16% (13%-21%); model ahead in 76% of resamples. The difference 2% (95% -3% to 6%) includes 0, so the model matches the baseline rather than beats it. Physical-only model (no past reports): 12% (10%-15%); vs last-year baseline -4% (95% -9% to -0%), so it falls short of the baseline. Full model vs physical-only: 6% (95% 4% to 9%), past reports add real signal.

### Portsmouth, leave-one-city-out (trained on the other cities, all usable years)

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 19.2% | 12.8% to 25.9% |
| physical only | 15.2% | 9.2% to 21.6% |
| last year reports | 13.1% | 9.8% to 21.1% |
| load x past reports | 9.7% | 4.6% to 14.4% |
| model minus last-year (paired) | 6.2% | -3.8% to 12.7% |
| physical-only minus last-year (paired) | 2.1% | -8.1% to 8.7% |
| model minus physical-only (paired) | 4.0% | -0.1% to 8.3% |

n = 257 test reports on 6,010 test segments (2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025). Model ahead of the last-year baseline in 84% of 1,000 resamples (seed 2026).

Portsmouth, leave-one-city-out (trained on the other cities, all usable years): model 19% (13%-26%) vs last-year baseline 13% (10%-21%); model ahead in 84% of resamples. The difference 6% (95% -4% to 13%) includes 0, so the model matches the baseline rather than beats it. Physical-only model (no past reports): 15% (9%-22%); vs last-year baseline 2% (95% -8% to 9%), so it matches the baseline rather than beats it. Full model vs physical-only: 4% (95% -0% to 8%), past reports add no clear signal.

### Southampton, leave-one-city-out (trained on the other cities, all usable years)

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 36.6% | 32.0% to 41.3% |
| physical only | 13.7% | 10.9% to 16.7% |
| last year reports | 33.5% | 27.2% to 36.7% |
| load x past reports | 18.3% | 15.0% to 21.9% |
| model minus last-year (paired) | 3.1% | 0.9% to 8.1% |
| physical-only minus last-year (paired) | -19.8% | -24.1% to -12.1% |
| model minus physical-only (paired) | 22.9% | 17.6% to 27.9% |

n = 819 test reports on 8,145 test segments (2016, 2017, 2018, 2019). Model ahead of the last-year baseline in 99% of 1,000 resamples (seed 2026).

Southampton, leave-one-city-out (trained on the other cities, all usable years): model 37% (32%-41%) vs last-year baseline 33% (27%-37%); model ahead in 99% of resamples. The difference 3% (95% 1% to 8%) excludes 0, so the model beats the baseline. Physical-only model (no past reports): 14% (11%-17%); vs last-year baseline -20% (95% -24% to -12%), so it falls short of the baseline. Full model vs physical-only: 23% (95% 18% to 28%), past reports add real signal.

### Brighton, frozen 2026 check (Jan to Oct)

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 26.7% | 10.7% to 44.4% |
| physical only | 20.0% | 6.4% to 35.3% |
| last year reports | 16.7% | 3.3% to 27.3% |
| load x past reports | 13.3% | 2.9% to 26.7% |
| model minus last-year (paired) | 10.0% | -5.9% to 32.3% |
| physical-only minus last-year (paired) | 3.3% | -12.5% to 24.0% |
| model minus physical-only (paired) | 6.7% | -11.1% to 25.0% |

n = 30 test reports on 8,179 test segments (2026). Model ahead of the last-year baseline in 88% of 1,000 resamples (seed 2026).

Brighton, frozen 2026 check (Jan to Oct): model 27% (11%-44%) vs last-year baseline 17% (3%-27%); model ahead in 88% of resamples. The difference 10% (95% -6% to 32%) includes 0, so the model matches the baseline rather than beats it. Physical-only model (no past reports): 20% (6%-35%); vs last-year baseline 3% (95% -12% to 24%), so it matches the baseline rather than beats it. Full model vs physical-only: 7% (95% -11% to 25%), past reports add no clear signal. Only 30 reports, so the interval is wide.

### Portsmouth, frozen 2026 check (Jan to Oct)

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 26.2% | 10.5% to 40.0% |
| physical only | 19.0% | 7.5% to 33.3% |
| last year reports | 26.2% | 2.9% to 27.0% |
| load x past reports | 21.4% | 8.3% to 36.7% |
| model minus last-year (paired) | 0.0% | -4.9% to 27.9% |
| physical-only minus last-year (paired) | -7.1% | -9.1% to 19.6% |
| model minus physical-only (paired) | 7.1% | -4.4% to 18.2% |

n = 42 test reports on 6,010 test segments (2026). Model ahead of the last-year baseline in 87% of 1,000 resamples (seed 2026).

Portsmouth, frozen 2026 check (Jan to Oct): model 26% (11%-40%) vs last-year baseline 26% (3%-27%); model ahead in 87% of resamples. The difference 0% (95% -5% to 28%) includes 0, so the model matches the baseline rather than beats it. Physical-only model (no past reports): 19% (7%-33%); vs last-year baseline -7% (95% -9% to 20%), so it matches the baseline rather than beats it. Full model vs physical-only: 7% (95% -4% to 18%), past reports add no clear signal. Only 42 reports, so the interval is wide.

### Southampton, frozen 2026 check (Jan to Oct)

| Method | Capture, top 10% of road length | 95% interval |
|---|---|---|
| model | 15.2% | 3.6% to 28.0% |
| physical only | 15.2% | 2.7% to 29.7% |
| last year reports | 12.1% | 2.8% to 26.9% |
| load x past reports | 21.2% | 8.3% to 40.7% |
| model minus last-year (paired) | 3.0% | -12.1% to 14.8% |
| physical-only minus last-year (paired) | 3.0% | -16.1% to 20.0% |
| model minus physical-only (paired) | 0.0% | -16.1% to 15.4% |

n = 33 test reports on 8,145 test segments (2026). Model ahead of the last-year baseline in 52% of 1,000 resamples (seed 2026).

Southampton, frozen 2026 check (Jan to Oct): model 15% (4%-28%) vs last-year baseline 12% (3%-27%); model ahead in 52% of resamples. The difference 3% (95% -12% to 15%) includes 0, so the model matches the baseline rather than beats it. Physical-only model (no past reports): 15% (3%-30%); vs last-year baseline 3% (95% -16% to 20%), so it matches the baseline rather than beats it. Full model vs physical-only: 0% (95% -16% to 15%), past reports add no clear signal. Only 33 reports, so the interval is wide.

<!-- real-label-eval:end -->

<!-- eval-ci:start -->
## Live model: bootstrap ranges, 2026 check and top features

_Generated 2026-10-17T21:15:21+00:00 by `python -m roadsense.models.eval_ci`. Scores the real-label model exactly as saved for the live plan (`data/models/real_risk_model.txt`), with no retraining._

Metric: share of a test year's FixMyStreet reports that fall on the top 10% of road length, averaged over the test years. Baseline: rank by last year's reports. Ranges: paired cluster bootstrap over **wards** (1,000 resamples, seed 2026); reports cluster in space, so whole wards are resampled rather than single roads or weeks, which would understate the noise.

**Caveat:** the live model was fitted on every usable year, including these test years, so the first table is an in-sample score and reads higher than a true hold-out. The held-out results are the real-label tables above; the 2026 check below is out of sample.

### Test years (live model)

| City | Model | Baseline (last year's reports) | Model minus baseline | Model ahead | Reports / wards |
|---|---|---|---|---|---|
| Southampton 2018-19 | 64.8% (56.3% to 74.6%) | 33.7% (23.1% to 40.1%) | 31.2% (27.2% to 40.3%) | 100% | 381 / 17 |
| Brighton 2023-25 | 50.7% (45.0% to 55.0%) | 21.7% (17.9% to 26.6%) | 29.0% (23.3% to 32.0%) | 100% | 802 / 23 |

### Frozen 2026 check (January to October, out of sample)

| City | Reports | Model | Baseline | Model minus baseline | Model ahead |
|---|---|---|---|---|---|
| Southampton | 33 | 15.2% (4.2% to 30.4%) | 12.1% (2.9% to 27.6%) | 3.0% (-11.1% to 16.2%) | 56% |
| Brighton | 30 | 26.7% (11.4% to 50.0%) | 16.7% (2.8% to 29.4%) | 10.0% (-3.1% to 34.6%) | 91% |

- Southampton: only 33 reports in January to October 2026, too few for this result to mean anything (model 15% vs baseline 12%).
- Brighton: only 30 reports in January to October 2026, too few for this result to mean anything (model 27% vs baseline 17%).

### Top 5 features (mean absolute SHAP over both cities' test rows)

1. **Length of the road segment (longer pieces have more surface to fail)** (`length_m`, 24% of the model's total attribution)
2. **Which city (reporting habits differ between cities)** (`city_code`, 15% of the model's total attribution)
3. **Frost hours in the area last year** (`wx_frost_hours`, 12% of the model's total attribution)
4. **Potholes reported on the neighbouring roads last year** (`rep_nb_prev1`, 8% of the model's total attribution)
5. **Number of bus routes using the road** (`bus_routes`, 7% of the model's total attribution)

<!-- eval-ci:end -->
