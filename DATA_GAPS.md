# Data gaps and cuts

## Lane A (data)
- **Bournemouth (BCP) has no FixMyStreet data.** BCP Council (MapIt area 152188) does not take FixMyStreet reports: every report there shows "Not reported to council", and the Open311 API returns nothing for that agency (checked 17 Oct 2026). Dropped from all lanes.
- **Southampton labels only from 2015.** 2011–14 came through the council's old FixMyStreet-branded site, which inflates counts. 2020–2022 has no reports at all. Usable window 2015–2019 (`config.yaml: labels.windows`). Train 2015–17, test 2018–19.
- **Brighton road reports fall away from mid-2025.** Only one "Pavement and road repairs" report in May–June 2026. Usable window to 2025. Test 2023–25.
- **2026 is partial (Jan–Oct) and small** (Southampton 35, Portsmouth 46, Brighton 32 road-surface reports). It is a "frozen model" check only, reported with n and a bootstrap range.
- **Portsmouth is small** (321 labels after cleaning). It is extra training data / a transfer test, not a headline result.
- **Counts measure FixMyStreet use, not pothole rates.** Scores rank segments within each city and year. Raw totals are never compared across cities.
- **Pavement filter is keyword-based.** A hand check of 25 Brighton reports each way found about 24/25 kept reports were genuine road defects and 22/25 removed ones genuine pavement defects. Some error stays in the labels.
- **Labels cover all road classes** (decided 17 Oct). Only 27% of Southampton 2015–19 reports are on A/B roads, so main-road-only labels would drop most of them. Reports more than 25 m from any drivable road (about 2%) are dropped as off-road/pavement.
- **No flood layer yet.** `in_flood_area` is false for every segment until the Environment Agency flood zones are added.
- **Junction = 4+ streets or a mini-roundabout/signal node.** In OSM's simplified graph almost every edge ends at a 3-way meet, so those are not counted (16% of Southampton segments are junctions).
- **National Highways roads = motorways only** (10 Southampton segments, M27/M271). OSM doesn't say who owns trunk A-roads.
- **B-roads often lack a `ref` in OSM** (64 km of Southampton main road has no ref). They are still `is_main_road` by highway class.
