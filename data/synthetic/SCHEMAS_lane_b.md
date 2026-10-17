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
