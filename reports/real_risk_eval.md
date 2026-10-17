# Real-label risk model (FixMyStreet, real data)

_Generated 2026-10-17T13:22:46+00:00 by `python -m roadsense.models.real_risk` (real-risk-v0.1)._

Labels: real FixMyStreet road-surface reports (`data\processed\fms_snapped.csv`), snapped to main-road segments within 25 m. Counts measure reporting, not pothole rates; scores rank segments within one city and year.

Score: share of that year's reports on the top 10% of road length (mean over test years, 95% paired segment bootstrap).

## Test years per city (pooled model)

### Southampton

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

## Leave-one-city-out

Not run (not enough cities or reports).

## Frozen 2026 check (Jan to Oct, small)

### Southampton

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
