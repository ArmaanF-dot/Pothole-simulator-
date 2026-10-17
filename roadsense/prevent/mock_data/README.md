# Lane C copies of other lanes' files (until the merge)

Copied without merging so the officer page runs on real inputs. **Delete this folder at the merge**: the
loaders then read `data/processed/`, `outputs/` and `data/synthetic/` instead.

| File | Copied from | Commit |
| --- | --- | --- |
| segments.parquet, load.parquet, weather_weekly.parquet | `lane-a-data:data/processed/` | 2a2bbac / d3cb9a9 |
| risk_latest.parquet, lights_latest.parquet | `lane-b-models:outputs/` | 1496843 |
| crew_outcomes.csv, _meta.json | `lane-b-models:data/synthetic/` | 1496843 |

Risk labels, wear, lamps and crew outcomes are SYNTHETIC (lane B). Segments, load and weather are real.
