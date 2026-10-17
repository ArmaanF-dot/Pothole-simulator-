# Data gaps and cuts

## Lane B (models)
- **Lane A inputs mocked (M4, 2026-10-17).** Segments, esal_day and weekly weather were not on main when M4 was built, so the generators ran on deterministic mocks (`data/synthetic/mock_inputs/`, `input_source=mock`, about 7,900 grid segments in 17 mock wards). Re-run `python -m roadsense.synthetic` after Merge 1 to regenerate on the real segment map, weather and load.
- **Resurfacing age before the recorded date.** Generator 1 records one last_resurfaced date per segment. For weeks before that date, age is assumed to be the class maximum (15/25/40 years) plus the time since, i.e. the segment was on its previous cycle. Assumption, not council data.
- **Pothole labels by segment_id.** Synthetic potholes are generated on a segment and jittered up to 10 m, so labels join on segment_id rather than a 15 m spatial search. FixMyStreet points are snapped to the nearest segment within 15 m.
- **Crew outcomes selection.** Generator 5 uses the latest outputs/risk_*.parquet when it exists; before M5 it falls back to a public proxy (recorded potholes in the last 12 months, then esal_day). Re-run after M5 to select from the model.
- **Synthetic seasonality is strongly winter-peaked.** With the spec's coefficients (0.4 per freeze-thaw crossing, 0.8 per rain-then-frost day) about 75% of synthetic potholes fall in December to March. This matches the Brighton and Hove late-winter spike but may overstate it.
