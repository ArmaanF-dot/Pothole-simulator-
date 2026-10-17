# Data schemas (M0)

The contract between lane A (data) and lane B (models). Lane A writes these files, lane B reads them.
It covers every input listed in lane B's draft (`data/synthetic/SCHEMAS_lane_b.md` on `lane-b-models`)
using the same column names, plus the real FixMyStreet labels.
Any change to a column needs a note here and a message to the other lane.

_v1, 17 Oct 2026. Owner: lane A._

## Conventions
- **Cities:** `Southampton`, `Portsmouth`, `Brighton`. `city_code`: `SOU`, `POR`, `BRI`. Bournemouth (BCP) has no data: see `DATA_GAPS.md`.
- **Geometry:** stored as WKB in a `geometry` column, **EPSG:4326** (lon/lat). Distances, lengths and snapping are computed in **EPSG:27700** (British National Grid, metres).
- **Times:** ISO 8601. Report timestamps keep FixMyStreet's UTC offset. `date` columns are `YYYY-MM-DD`. `week_start` is a Monday.
- **IDs are strings.** `segment_id` = `{city_code}-{osm_way_id}-{part}`, e.g. `SOU-4256781-02` (part = position along the OSM way, from 00). It stays stable as long as the OSM extract doesn't change.
- **Formats:** `data/processed/*.parquet` for model inputs; CSV for label tables that people open by hand.
- **Provenance:** every processed file has a `source` column (`fixmystreet`, `osm`, `dft`, `mock` …). Real data never sets `is_synthetic`. Lane B's synthetic files always do.
- **Privacy:** no free-text descriptions outside `data/raw/` (which is git-ignored).
- **Settings** (cities, windows, snap distance, segment length) live in `config.yaml`, never hard-coded.

## Folders
| Folder | In git? | Contents |
|---|---|---|
| `data/raw/` | no (except small reference files) | API pulls exactly as received, plus free text |
| `data/processed/` | yes | the files below |

## 1. FixMyStreet reports
### `data/raw/fms_raw.csv` (local only)
Every report in the configured categories, one row per FixMyStreet report.
`city, id, category, requested, updated, status, lat, lon, title, description, surface_keyword`
- `description` is cut to 500 characters. **Never commit this file.**

### `data/processed/fms_roads_clean.csv`: the road-defect labels
Road-surface reports only: duplicates removed (same city, ≤20 m and ≤30 days apart) and pavement/footway reports dropped.
| Column | Type | Notes |
|---|---|---|
| city | str | |
| id | int | FixMyStreet report id |
| category | str | council's own category name |
| requested | datetime | report time (label date) |
| updated | datetime | last update on FixMyStreet |
| status | str | `open` / `closed` |
| lat, lon | float | EPSG:4326 |
| title | str | short title only, no description |
| surface_keyword | bool | title/description mentions a surface word |
| in_window | bool | inside that city's usable label window (`config.yaml: labels.windows`) |

Same columns and rows as the existing `data/fms_roads_clean.csv` (5,127 rows), plus `in_window`.

### `data/processed/fms_streetlights.csv`: Southampton street-lighting reports
Same columns as above, minus `surface_keyword`. Category `Street lighting`. For lane B to check the streetlight fault generator. These are not used as road labels.

### `data/processed/fms_snapped.csv` (M2)
`fms_roads_clean.csv` columns + `segment_id` (blank if none within the snap distance) and `snap_dist_m` (float).
Keeping the distance lets lane B use its 15 m radius and lane A its 25 m without a second snap.

## 2. Road segments: `data/processed/segments.parquet` (M1)
One row per piece of road, all cities stacked. Built from OSM (ODbL) `network_type="drive"`.
| Column | Type | Notes |
|---|---|---|
| segment_id | str | see conventions |
| city | str | |
| osm_way_id | int64 | |
| name | str | blank if unnamed |
| ref | str | e.g. `A33`; blank if none |
| highway | str | OSM class (`primary`, `secondary`, `tertiary`, `residential`, …) |
| is_main_road | bool | highway in primary/secondary/tertiary (+ `_link`): the A/B roads the FixMyStreet labels are scored on |
| ward | str | council ward the midpoint falls in |
| length_m | float | ≤ `segments.max_length_m` (200) |
| lat, lon | float | midpoint |
| bus_stop | bool | OSM bus stop within 20 m |
| bus_routes | int | number of OSM `route=bus` relations using the way |
| junction | bool | segment ends at a node where ≥4 streets meet, or a mini-roundabout/traffic-signal node (3-way meets are left out: nearly every edge ends at one) |
| in_flood_area | bool | midpoint in an EA Flood Zone 3 polygon (false if the layer is unavailable; logged) |
| owner | str | `council` / `national_highways` (motorway or trunk with a National Highways ref) |
| geometry | WKB | EPSG:4326 LineString |
| source | str | `osm` |

## 3. Traffic load: `data/processed/load.parquet` (M3)
| Column | Type | Notes |
|---|---|---|
| segment_id | str | |
| hgv_bus_aadf | float | HGV + bus annual average daily flow (DfT, OGL) |
| esal_day | float | standard axles per day, from the HGV/bus flow (factors in `config.yaml: load.esal_factors`) |
| count_point_id | int | DfT count point used |
| count_year | int | |
| load_source | str | `count` (point on this segment), `same_road` (nearest point on the same road), `class_median` (no point on the road) |
| source | str | `dft` |

## 4. Weather: `data/processed/weather_weekly.parquet` (M3)
One row per ward × week, exactly as lane B asked for. **Every window uses only hours before `week_start`.**
`ward, week_start, rain_3d, rain_7d, rain_30d, rain_90d, hours_below_0_7d, freeze_thaw_14d, freeze_thaw_30d, rain_then_frost_7d, hot_days_7d, source`
- Rain is in mm, plus counts of hours/days. A freeze-thaw crossing is the temperature passing 0 °C in either direction.
- Weather source still to be confirmed (licence check). Until then lane B keeps using its mock.

## 5. Labels for the "where" model: `data/processed/labels_segment_year.csv` (M2)
| Column | Type | Notes |
|---|---|---|
| city | str | |
| segment_id | str | main roads only (`is_main_road`) |
| year | int | |
| n_reports | int | snapped reports in that year |
| had_report | int | 0/1 |
| split | str | `train` / `test` / `frozen_2026` / `excluded`, from `config.yaml: labels.windows` |

## 6. Street lamps (optional): `data/processed/street_lamps.parquet`
`osm_node_id, city, lon, lat, source` (OSM `highway=street_lamp` nodes).

## Splits (as agreed in STATUS.md)
| City | Usable labels | Train | Test |
|---|---|---|---|
| Southampton | 2015–2019 | 2015–2017 | 2018–2019 |
| Brighton | to 2025 | ≤2022 | 2023–2025 |
| Portsmouth | all | extra training / small transfer test | — |
| All | 2026 Jan–Oct | — | `frozen_2026` check only, report n and a bootstrap range |

## Open questions for lane B
1. **Snap radius:** your draft uses 15 m and STATUS.md says 25 m. `snap_dist_m` is stored so either works. Pick one for the headline numbers.
2. **Segment length:** lane A cuts to ≤200 m (STATUS.md). Your mock uses 75 m. Tell us if the models need shorter pieces.
3. **Residential roads:** they are kept in `segments.parquet` for your synthetic generators. The FixMyStreet scores use `is_main_road` only.
4. **Label roads (team decision):** only 27% of Southampton 2015–19 reports (261 of 997) snap to main roads (≤25 m). Main-road-only labels keep that 27%. All roads keep about 98%. `labels_segment_year.csv` says main roads only for now, until this is decided.
