# Contract: lane B outputs → lane C (DRAFT for agreement)

_Draft 17 Oct 2026, 13:35. Fold into `schemas.md` (sections 7–10) once lanes B and C agree.
Built from the build spec (M5, M6, M7, M8). Checked by `tests/test_contract.py::test_risk_output_links`._

Conventions are the same as `schemas.md`: string `segment_id`, EPSG:4326, ISO dates, `week_start` = Monday.
**Every output says whether synthetic data went into it**, so the UI can show the SYNTHETIC badge.

## 7. Risk and wear: `outputs/risk_<YYYY-MM-DD>.parquet` (lane B writes, lane C reads)
One row per scored segment per forecast week (next 4 weeks). Motorways (`owner = national_highways`) are not scored.
| Column | Type | Notes |
|---|---|---|
| segment_id | str | joins `segments.parquet` |
| week_start | date | forecast week |
| p7 | float 0–1 | calibrated probability of a pothole in the next 7 days |
| p30 | float 0–1 | … next 30 days |
| wear | float 0–100 | % cumulative failure probability at current age (SYNTHETIC: needs resurfacing history) |
| reason_1, reason_2, reason_3 | str | plain-English top SHAP reasons, e.g. "High HGV + bus load (A33)" |
| model_version | str | e.g. `risk@2026-10-17T22:40` |
| trained_on | str | `synthetic`, `real`, or `synthetic+real` |
| uses_synthetic | bool | true if any synthetic input/label was used |
| weather_data_date | str | latest weather hour used (for the STALE banner) |
| uses_forecast | bool | the row depends on forecast weather |

## 8. Street lights: `outputs/lights_<YYYY-MM-DD>.parquet` (lane B → C)
| Column | Type | Notes |
|---|---|---|
| lamp_id | str | |
| segment_id | str | |
| lat, lon | float | |
| lamp_type | str | `LED` / `legacy` |
| p_fail_90d | float 0–1 | |
| replace_by | date | date cumulative failure reaches 0.5 |
| currently_dark | bool | open fault in the last 30 days (synthetic) or open FixMyStreet street-lighting report (real) |
| dark_source | str | `synthetic` / `fixmystreet` / blank |
| uses_synthetic | bool | |

## 9. Prevention plan rows: `outputs/prevention_plan_<YYYY-MM-DD>.csv` (lane C writes, from 7)
`rank, segment_id, ward, name, ref, band (critical/high/prevention/monitor), urgency (0–100), p30, wear,
treatment (crack_sealing/surface_dressing/patch/resurface/permanent_repair), reason_1..3,
cost_planned_gbp, cost_reactive_avoided_gbp, open_fms_report (bool), uses_synthetic, data_dates (json: source → date)`

## 10. API JSON (lane C serves; field names = the columns above)
- `GET /segments?ward=&band=` → GeoJSON FeatureCollection; properties = segments.parquet fields (no geometry column)
  + latest risk row + `urgency`, `band`, `load_confidence` (high/medium/low from `load_source`).
- `GET /segments/{id}` → one Feature plus `risk_weeks: [...]`, `load: {...}`, `reports: [...]`.
- `GET /plan/prevention?ward=` → `{as_of, provisional (bool, true if forecast > 24 h old), rows: [section 9]}`
- `GET /lights?due_days=90` → section 8 rows.
- `POST /reports` / `POST /outcomes` → as in the spec (M8).
- `GET /sources` → `[{name, used_for, licence, retrieved_at, data_date, is_synthetic}]` for the footer.

## Open points for B and C to settle
1. Is `wear` shown for all cities or Southampton only (it needs synthetic resurfacing history)?
2. Forecast horizon: 4 weekly rows per segment, or just next week for the plan?
3. File naming: one file per run date (above) vs a fixed `risk_latest.parquet` symlink/copy for the API.
