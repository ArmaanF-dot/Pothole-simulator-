# Lane C copies of other lanes' files (until the merge)

Copied without merging so the officer page runs on real inputs. **Delete this folder at the merge**: the
loaders then read `data/processed/`, `outputs/` and `data/synthetic/` instead.

| File | Copied from | Commit |
| --- | --- | --- |
| segments.parquet, load.parquet, weather_weekly.parquet, weather_forecast_weekly.parquet, wards.geojson, sources.json, segment_context.parquet | `lane-a-data:data/processed/` | e4e6dc3 |
| risk_latest.parquet, lights_latest.parquet | `lane-b-models:outputs/` | 1496843 |
| crew_outcomes.csv, _meta.json | `lane-b-models:data/synthetic/` | 1496843 |

Risk labels, wear, lamps and crew outcomes are SYNTHETIC (lane B). Segments, load and weather are real.
