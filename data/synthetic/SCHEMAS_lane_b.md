# Lane B data shapes (draft, pending schemas.md)

`schemas.md` was not on main when lane B started, so these are the shapes lane B reads and
writes. Everything in `data/synthetic/` is **SYNTHETIC** (`is_synthetic=true`,
`source="synthetic:<generator>@<version>"`). Regenerate with `python -m roadsense.synthetic`
(Makefile target `synthetic` to be added at the merge).

## Inputs lane B expects from lane A (`data/processed/`)
| File | Columns lane B uses |
|---|---|
| `segments.parquet` | segment_id, osm_way_id, name, highway, ward, length_m, geometry (WKT or WKB, EPSG:4326), bus_stop (bool), junction (bool), in_flood_area (bool), owner (`council`/`national_highways`); optional lat, lon (midpoint), esal_day |
| `load.parquet` (or `esal_day.parquet`) | segment_id, esal_day (only if esal_day is not already on segments) |
| `weather_weekly.parquet` | ward, week_start (Monday), rain_3d, rain_7d, rain_30d, rain_90d, hours_below_0_7d, freeze_thaw_14d, freeze_thaw_30d, rain_then_frost_7d, hot_days_7d. Every window covers only hours **before** week_start |
| `street_lamps.parquet` (optional) | lon, lat of OSM highway=street_lamp nodes in coverage |

Until those exist, deterministic mocks are written to `data/synthetic/mock_inputs/` and every
mock row carries `input_source="mock"`. Mock wards are named "Mock ward 01..17".

## Outputs
| File | Columns |
|---|---|
| `resurfacing.csv` | segment_id, date, treatment (`last_resurfaced`, `surface_dressing`, `crack_sealing`, `full_resurfacing`), road_class, is_synthetic, source |
| `potholes.csv` | event_id, segment_id, lat, lon, reported_date, repaired_date (blank = still open), depth_mm, width_mm, repair_type (`reactive`/`planned`), is_synthetic, source |
| `streetlights.csv` | lamp_id, segment_id, lat, lon, lamp_type (`LED`/`legacy`), install_date, position_source, current_unit_type, current_unit_install_date, is_synthetic, source |
| `light_faults.csv` | fault_id, lamp_id, fault_date, repaired_date (blank = open), status (`repaired`/`open`), fault_type (`burnout`/`electrical`/`damage`), unit_type, unit_install_date, burn_hours_at_fault, is_synthetic, source |
| `crew_outcomes.csv` | outcome_id, segment_id, inspection_date, selection (`model_top:<file>`/`proxy_top:...`/`random`), outcome (`pothole`/`cracking`/`none`), is_synthetic, source |
| `_truth.json` | hidden generator truth. **Never read by roadsense/models or roadsense/features** (test enforced) |
| `_meta.json` | seed, version, as_of, which inputs were mock, row counts |

"Currently dark" lamps = `light_faults.csv` rows with status `open` and fault_date in the last 30 days.

## Model outputs
| File | Columns |
|---|---|
| `outputs/risk_<as_of>.parquet` | segment_id, ward, week_start, p7, p30, p30_w0..p30_w3 (this week and the next 3), p30_trend, wear_pct (0-100), reason_1..reason_3 (plain text, SHAP), weather_source, labels_synthetic, wear_synthetic, inputs_mock, model_version, as_of |
| `outputs/lights_<as_of>.parquet` | lamp_id, segment_id, lat, lon, unit_type, unit_install_date, burn_hours, p_fail_90d, predicted_replacement_date, replacement_overdue, due_90d, currently_dark, dark_since, is_synthetic, source, as_of |
| `data/models/` | risk_y7.txt / risk_y30.txt (LightGBM), *_calibrator.pkl (isotonic), risk_eval.json, lights_weibull.json |

## Needed at the merge (shared files)
- Makefile: `synthetic: python -m roadsense.synthetic`, `train: python -m roadsense.models.risk`, `lights: python -m roadsense.models.lights`. Run order: synthetic, train, then synthetic again so crew outcomes select from the model.
- requirements.txt: numpy, pandas, pyarrow, pyyaml, scipy, shapely, lightgbm, scikit-learn, lifelines, shap, astral, tzdata, matplotlib, pytest.
