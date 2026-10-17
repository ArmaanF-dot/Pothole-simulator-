# Status

_Last updated: 17 Oct 2026_

## Done
- `pull_fixmystreet.py` pulls FixMyStreet road/pavement reports for Southampton, Portsmouth and Brighton (2008–2026).
- Ran it: 9,035 reports → 5,406 road-surface defects after de-dup (Southampton 3,266 · Portsmouth 333 · Brighton 1,807).
- Pushed `data/fms_dedup.csv`, `data/README.md`, `data/summary.txt` and the script to `main` on
  [ArmaanF-dot/Pothole-simulator-](https://github.com/ArmaanF-dot/Pothole-simulator-).

## Next
- Start analysis / simulator work from `data/fms_dedup.csv`.
- Credit FixMyStreet (mySociety) with the pull date in the main README.
- Decide how to handle the data gaps below in any city comparison.

## Decisions
- **Bournemouth dropped.** BCP Council doesn't take FixMyStreet reports ("Not reported to council"), so the API has no data.
- **`fms_raw.csv` stays local** (in `.gitignore`): it has free-text descriptions that can include names or house numbers. Only the de-duplicated file without descriptions goes on GitHub.
- **Duplicate = same city, within 20 m and 30 days** of an earlier report.
- **Compare trends within a city, not raw totals between cities.** Counts reflect FixMyStreet use, not true pothole rates.

## Known gaps
- Southampton: no reports 2020–2022.
- Brighton: road reports almost stop in 2026.
