# Status

_Last updated: 17 Oct 2026, 12:55_

## Done
- `pull_fixmystreet.py` pulls FixMyStreet road/pavement reports for Southampton, Portsmouth and Brighton (2008–2026).
- Ran it: 9,035 reports → 5,406 road-surface defects after de-dup (Southampton 3,266 · Portsmouth 333 · Brighton 1,807).
- Pushed `data/fms_dedup.csv`, `data/README.md`, `data/summary.txt` and the script to `main` on
  [ArmaanF-dot/Pothole-simulator-](https://github.com/ArmaanF-dot/Pothole-simulator-).
- **Labels cleaned** (`clean_labels.py` → `data/fms_roads_clean.csv`, 5,127 reports): pavement/footway
  defects removed using title (then description) keywords; street names like "Tisbury Road" ignored.
  Removed: Brighton 203, Portsmouth 12, Southampton 64. Hand check of 25 each (Brighton):
  kept ≈ 24/25 genuine road defects, removed ≈ 22/25 genuine pavement. **Train on this file, not fms_dedup.csv.**
- **Lane A, branch `lane-a-data` (not merged yet):**
  - **M0 done:** `schemas.md` is the data contract for lane B (segments, load, weekly weather, labels). It uses lane B's
    column names and lists 3 open questions for them (snap 15 vs 25 m, segment length, residential roads).
  - FixMyStreet ingest moved to `roadsense/ingest/fixmystreet.py` (`python -m roadsense.ingest.fixmystreet`). It replaces
    `pull_fixmystreet.py` + `clean_labels.py` and rebuilds the same 5,127 labels exactly.
    New outputs go to `data/processed/` (labels now have `in_window`). Settings are in `config.yaml`. Raw pulls go to `data/raw/` (git-ignored).
  - Southampton "Street lighting" reports added: `data/processed/fms_streetlights.csv` (211), for lane B's streetlight check.
  - BCP and the other data gaps logged in `DATA_GAPS.md`.

## Next (in order)
0. Lane B to answer the open questions in `schemas.md`. At merge, delete the old `data/fms_*.csv` (lane B still points at `data/fms_dedup.csv`).
   Lane A milestones M1–M3 follow steps 1–4 below and write to `data/processed/` as `schemas.md` describes.
1. **Road segments (OpenStreetMap, ODbL):** `osmnx.graph_from_place("Southampton, UK", network_type="drive")`;
   keep highway = primary/secondary/tertiary (≈ A/B roads); project to EPSG:27700; cut into ~200 m segments;
   save `data/segments_southampton.gpkg` (id, road name, ref, highway, length_m, geometry).
2. **Bus routes (OSM `route=bus` relations):** count routes per segment → `bus_routes` column.
3. **Snap reports to segments:** nearest segment within 25 m (EPSG:27700); further away = side street/pavement, drop.
   Output: label table segment × year → `had_report` (0/1).
4. **Traffic load (DfT road traffic statistics, OGL):** count points with HGV/bus AADF; join to nearest segment on the
   same road; fill gaps from nearest count point on that road. Feature: `hgv_bus_aadf`.
5. **Baseline first:** rank segments by last year's reports → top-10% capture on the test window.
6. **Model:** gradient boosting on [hgv_bus_aadf, bus_routes, highway class, length, reports in previous 1–3 yrs].
   Compare to baseline + simple formula (load × past reports). Bootstrap the test set for a range.
7. **"When" model (city-month):** monthly report totals vs freeze-thaw days + rainfall (historical weather source: TBC, check licence).
8. Repeat 1–4 for Brighton, then Portsmouth, only after Southampton runs end to end (target 18:00).
- Credit FixMyStreet (mySociety) with the pull date in the main README.
- Decide how to handle the data gaps below in any city comparison.

## Decisions
- **Bournemouth dropped.** BCP Council doesn't take FixMyStreet reports ("Not reported to council"), so the API has no data.
- **`fms_raw.csv` stays local** (in `.gitignore`): it has free-text descriptions that can include names or house numbers. Only the de-duplicated file without descriptions goes on GitHub.
- **Duplicate = same city, within 20 m and 30 days** of an earlier report.
- **Compare trends within a city, not raw totals between cities.** Counts reflect FixMyStreet use, not true pothole rates.

## Train/test windows (agreed)
- **Southampton:** use 2015–2019 only (2011–14 was the council's old FixMyStreet-branded site: inflated counts).
  Train 2015–2017, test 2018–2019.
- **Brighton:** train ≤2022, test 2023–2025 (its reports fall away from mid-2025).
- **Score = rank within each city and year** (share of next-year reports on the top 10% of road length), never raw counts across cities.
- **2026 so far = extra "frozen model" check, not the main test.** Train on everything up to 2025, predict 2026,
  compare with Jan–Oct 2026 reports. Small (Southampton 35, Portsmouth 46, Brighton 32) and missing Nov–Dec, so report
  it with its sample size and a bootstrap range; compare against the same Jan–Oct months in earlier years.
- **Portsmouth:** extra training data / small transfer test only (333 reports total).

## Known gaps
- Southampton: no reports 2020–2022.
- Brighton: road reports almost stop in 2026.
