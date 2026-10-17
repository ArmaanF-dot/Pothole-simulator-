# RoadSense: weekly pothole prevention for Southampton

> Draft for the merge PR (README.md is a shared file, so it changes only at a merge). Written by lane 3 on
> 17 Oct 2026 from the three branches as they stood at lane-a-data `e4e6dc3`, lane-b-models `1496843`,
> lane-c-product (this branch). Re-check the numbers after Merge 3.

RoadSense helps Southampton's highways officers decide which streets to treat this week, before potholes
form. It scores every council road segment on pothole risk from heavy-vehicle load, bus routes, flood areas
and freeze-thaw weather, explains each score, and produces a ranked weekly prevention list with a treatment
and its cost logic for an officer to approve. It also flags streetlights due for replacement and triages
public FixMyStreet reports into draft work orders.

## Setup

Python 3.11 (geospatial wheels install most cleanly on 3.11).

```bash
py -3.11 -m venv .venv            # macOS/Linux: python3.11 -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # then add GEMINI_API_KEY (optional: triage falls back to keyword rules)
```

Run the officer page with `make serve` (or `python -m roadsense.api`) and open http://127.0.0.1:8000.
The pipeline in order: `make ingest`, `make features`, `make synthetic`, `make train`, `make lights`, `make plan`.
Every number we tune lives in `config.yaml`, `config/synthetic.yaml` and `roadsense/prevent/prevent.yaml`.
Tests: `pytest` (small fixtures, no network).

## Data sources

Real data, from `data/processed/sources.json` (lane A). Every screen shows these with their retrieval date.

| Source | Used for | Licence | Retrieved | Data date |
| --- | --- | --- | --- | --- |
| OpenStreetMap | road segments, bus stops, bus routes, junctions, cycle routes, schools and hospitals | ODbL 1.0, © OpenStreetMap contributors | 17 Oct 2026 12:03 | 2026-10-17 |
| MapIt (mySociety) ward boundaries | 17 wards (May 2023), coverage check | OGL v3, contains OS data © Crown copyright | 17 Oct 2026 12:06 | May 2023 boundaries |
| DfT road traffic statistics | HGV and bus load (`esal_day`) | OGL v3 | 17 Oct 2026 12:22 | count years up to 2025 |
| Open-Meteo | rain, freeze-thaw, rain-then-frost; 16-day forecast | CC BY 4.0, free tier, non-commercial | 17 Oct 2026 12:36 | to 2026-11-01 23:00 |
| Environment Agency Flood Map for Planning | `in_flood_area` (Flood Zone 3, rivers and sea) | OGL v3 | 17 Oct 2026 12:45 | 2026-10-17 |
| FixMyStreet (mySociety) | real pothole labels, live open-report layer, report triage | public reports; credit mySociety | 17 Oct 2026 11:00 | latest report 2026-09-05 |
| Google Gemini API | report triage (classification, work-order drafting) | Gemini API terms; free tier may use prompts, so only public reports and synthetic data are sent | n/a | model `gemini-3.8-flash` |

Repair cost figures: planned £56.94 vs reactive £87.80 per pothole (ALARM 2025, Asphalt Industry Alliance).
Treatment costs per m² are our assumptions and are labelled as such in the app.

Not used: UKHO tides, Defra UK-AIR (not relevant to road wear), Southampton VTS cruise schedules (no clear link in the time).
Bournemouth (BCP) was dropped: the council takes no FixMyStreet reports.

## What is synthetic, and why

Council-held records could not be obtained before Sunday 13:00, so lane B generates them (seed 2026) on the real
segments, weather and load. Every synthetic row carries `is_synthetic=true` and a `source="synthetic:<generator>@<version>"`
tag, and every screen that uses one shows a **SYNTHETIC** badge.

| File | Replaces |
| --- | --- |
| `data/synthetic/resurfacing.csv` | resurfacing and surface-dressing history |
| `data/synthetic/potholes.csv` | the pothole repair log (yearly totals match Southampton's FOI figures; where and when within a year is synthetic) |
| `data/synthetic/streetlights.csv`, `light_faults.csv` | the lighting asset register and fault history |
| `data/synthetic/crew_outcomes.csv` | inspection results for the feedback loop |

The live plan's risk ranking is **trained on real FixMyStreet reports**; only its recent pothole history (mapped
from the synthetic repair log, because real 2020-26 reports are too thin), road wear and the lighting register are
synthetic. The dashboard says "trained on real reports · history synthetic". The weekly weather model is trained on
synthetic labels, so its accuracy is a pipeline check, not proof; the real-data tests are below. Every assumption is in
`config/synthetic.yaml` and `DATA_GAPS.md`.

## How well it works

- **Real FixMyStreet test, Southampton 2018-19 (381 reports):** the real-label model (trained on Southampton,
  Brighton and Portsmouth) put 41.6% of the next year's reports on the top 10% of road length (95% interval 33.9% to
  47.9%) against 33.7% for "last year's reports" (24.5% to 38.9%). Paired difference +7.9 points (3.1 to 15.5); the
  model was ahead in 100% of 1,000 bootstrap resamples. Source: `reports/real_risk_eval.md`.
- **Brighton 2023-25 (802 reports):** 31.2% (27.2% to 34.8%) against 21.7% for last year's reports, +9.5 points
  (4.9 to 12.2).
- **Second-city test (leave one city out, trained without that city):** Southampton 36.6% vs 33.5% (+3.1, 0.9 to 8.1);
  Brighton 18.4% vs 16.5% (+1.9, -3.0 to 6.0); Portsmouth 19.2% vs 13.1% (+6.2, -3.8 to 12.7). Ahead in all three,
  clearly so only for Southampton.
- **Frozen 2026 check (Jan to Oct, 33 Southampton reports):** model 15.2% vs last-year baseline 12.1% (+3.0, -12.1 to
  14.8), so no clear difference at that sample size. We report it anyway.
- **Weekly weather model on synthetic labels (time split, used for week-to-week movement and the what-if):** PR-AUC 0.253 for 30-day risk vs 0.095 for prior pothole
  count and 0.036 for road age. Pipeline check only. Source: `reports/risk_eval.md`.
- **Streetlights:** the Weibull model ranks no better than install year (precision in the top 5%: 0.039 vs
  0.036); its value is the replacement date. Source: `reports/lights_eval.md`.
- **Report triage:** keyword rules classify 91 of 100 hand-labelled real reports correctly
  (`reports/triage_vs_keywords.md`). The Gemini comparison is still to run in full (free-tier quota).
- **Running cost:** `reports/cost.md` (measured token counts; prices and volumes are assumptions).

## AI-generated code

All code in this repository was written with Claude Code (Anthropic), run by three team members, one per lane:
data (lane A), models (lane B), product (lane C). Every commit made through Claude Code carries a
`Co-Authored-By: Claude` line. Team members chose the approach, reviewed and ran the code, checked the data and made
the decisions recorded in `STATUS.md` and `DATA_GAPS.md`.

## What existed before the event

Nothing. The repository was created after hacking opened on Friday 16 October 2026 at 20:00; its first commit is
`5efc5de` at 12:08 on Saturday 17 October 2026.

## Who helped

_To fill in by the team: names and roles (lane A data, lane B models, lane C product), plus anyone else who helped._
