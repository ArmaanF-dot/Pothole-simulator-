# Data gaps and cuts

## Lane A (data)
- **Bournemouth (BCP) has no FixMyStreet data.** BCP Council (MapIt area 152188) does not take FixMyStreet reports: every report there shows "Not reported to council", and the Open311 API returns nothing for that agency (checked 17 Oct 2026). Dropped from all lanes.
- **Southampton labels only from 2015.** 2011–14 came through the council's old FixMyStreet-branded site, which inflates counts. 2020–2022 has no reports at all. Usable window 2015–2019 (`config.yaml: labels.windows`). Train 2015–17, test 2018–19.
- **Brighton road reports fall away from mid-2025.** Only one "Pavement and road repairs" report in May–June 2026. Usable window to 2025. Test 2023–25.
- **2026 is partial (Jan–Oct) and small** (Southampton 35, Portsmouth 46, Brighton 32 road-surface reports). It is a "frozen model" check only, reported with n and a bootstrap range.
- **Portsmouth is small** (321 labels after cleaning). It is extra training data / a transfer test, not a headline result.
- **Counts measure FixMyStreet use, not pothole rates.** Scores rank segments within each city and year. Raw totals are never compared across cities.
- **Pavement filter is keyword-based.** A hand check of 25 Brighton reports each way found about 24/25 kept reports were genuine road defects and 22/25 removed ones genuine pavement defects. Some error stays in the labels.

## Lane B (models)
- **Lane B outputs built from lane A's branch before Merge 1 (17 Oct, 14:50).** Synthetic data, risk and lights were regenerated on lane A's real Southampton segments, load and Open-Meteo weather, read from `lane-a-data` without merging it. Re-run after Merge 1 so the inputs come from main.
- **Resurfacing age before the recorded date.** Generator 1 records one last_resurfaced date per segment. For weeks before that date, age is assumed to be the class maximum (15/25/40 years) plus the time since, i.e. the segment was on its previous cycle. Assumption, not council data.
- **Pothole labels by segment_id.** Synthetic potholes are generated on a segment and jittered up to 10 m, so labels join on segment_id rather than a 15 m spatial search. FixMyStreet points are snapped to the nearest segment within 15 m.
- **Crew outcomes selection.** Generator 5 picks its 200 top segments from the latest outputs/risk_*.parquet, so run synthetic, then train, then synthetic again.
- **Weather terms capped in the synthetic hazard (assumption).** With the spec's coefficients and real Open-Meteo weather, one cold snap (December 2022, 20+ freeze-thaw crossings in 14 days) multiplied hazard by about e^8 and left almost no potholes outside winter (12 in all Octobers). freeze_thaw_14d is capped at 6 and rain_then_frost_7d at 2 in config/synthetic.yaml; synthetic potholes still peak in February (Brighton-style late-winter spike) with about 350 a month in summer.
- **Real-label risk model skipped (M5).** Southampton has 3,266 FixMyStreet road-surface reports, but almost all predate the synthetic log window (2021 onwards) and there are none from 2020 to 2022, so too few dated reports overlap the feature table to train on. Synthetic labels carry training; FixMyStreet carries the live layer and the real-world check.
- **Leave-one-city-out not run (M5).** The table only has Southampton until lane A's port-city features land; the code runs it automatically once a `city` column with two or more cities is present.
- **Real-world check is small (M5).** On real segments, 38 of the 41 Southampton FixMyStreet reports from the last 12 months snap within 15 m; numbers in reports/risk_eval.md are noisy at that size.
- **Forward weather (M5).** Weeks 1 to 3 use lane A's Open-Meteo forecast rows; week 4 is beyond the 16-day forecast and uses 10-year weekly climatology (weather_basis = climatology_10y, uses_forecast = false).
- **Wear saturates.** Synthetic potholes average about one per segment every two years, so "time to first pothole" is short and wear is above 90% on many older segments. Pipeline-correct for the synthetic world, but worth recalibrating against a real repair log.
- **Legacy lamps barely survive into the fault log (M7).** Legacy units (20,000 h scale) burn out within about five years and are replaced with LEDs, so almost all legacy burnouts happen before the log starts in 2016. Only 11 legacy units are in the fit; the LED fit recovers the generator's 60,000 h / shape 3.
- **Streetlight model does not beat the install-year baseline (M7).** Every unit runs on the same burn-hour clock, so burn hours and install year rank lamps the same way; precision in the top 5% is within noise of the baseline (reports/lights_eval.md).
