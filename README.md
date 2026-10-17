# RoadSense: weekly pothole prevention for Southampton

RoadSense helps Southampton's highways officers decide which streets to treat this week, before potholes form.
It scores every council road segment on pothole risk from heavy-vehicle load, bus routes, flood areas,
freeze-thaw weather and past pothole history, explains each score, and ranks a weekly prevention list with a
treatment and its cost logic for an officer to approve. A "Worth treating" view shows the roads where planned
treatment costs less than the reactive repairs it avoids, plus every road with a confirmed pothole. Gemini
triages public FixMyStreet reports into draft work orders. A Brighton map shows the same model on 100% real inputs.

Built in 24 hours at SotonShip26 (AI Society, Eagle Labs Southampton), Southampton City track.

## What it does

- **Prevention plan** (Southampton): road segments ranked by reactive repair cost avoided per £ of treatment, with a
  suggested treatment and the reasons behind each ranking. Split into *All roads* and *Worth treating* (treatment pays
  for itself, or a confirmed pothole).
- **Report triage** (Southampton): real FixMyStreet pothole reports are classified (Gemini, with a keyword fallback)
  and turned into work orders that an officer approves or rejects.
- **Streetlights** (Southampton, synthetic demo data).
- **Brighton risk map**: the same risk model applied to Brighton & Hove, a city with plentiful real report data, as an
  out-of-area check.

## Quick start

Tested on Python 3.14.7, Windows 11.

```bash
git clone [PUBLIC REPO URL]
cd [REPO FOLDER]
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # add GEMINI_API_KEY (optional: triage falls back to keyword rules)
python -m roadsense.api           # open http://127.0.0.1:8000
pytest -q                         # contract + unit tests, no network
```

Needs git. `.env` holds `GEMINI_API_KEY` only (free from Google AI Studio); without it the map and plan work and triage
falls back to keyword classification. Press Ctrl+C to stop the server. `python -m roadsense.api --port 8001` changes the
port; `--forecast-as-of <ISO date>` pretends the weather forecast was fetched at that time, to show the STALE banner
and provisional plan. Data was retrieved during the event and is cached in the repo, so no download is needed to run
the app. Do not re-pull OpenStreetMap data: segment IDs would change.

Tests: `python -m pytest -q` on main (17 Oct, Python 3.11.9, Windows 11): 130 passed. The warnings are pandas/NumPy and
FastAPI deprecation notices and don't affect results.

Full pipeline (`make all`, or run the `python -m` lines in the `Makefile` on Windows):
ingest → features → synthetic → train → plan_risk → synthetic → lights → plan. Every tunable number is in
`config.yaml`, `config/synthetic.yaml` and `roadsense/prevent/prevent.yaml`. The files the three parts of the
code pass between them are specified in `schemas.md` and checked by `tests/test_contract.py`.

## How well it works

All numbers below are on **real FixMyStreet reports the model never saw**, scored as the share of that year's
reports that fall on the model's top 10% of road length (about 60 km of Southampton's 600 km; chance = 10%),
against simply re-using last year's reports. Ranges are 95% paired segment bootstrap intervals, 1,000 resamples.

| Test | Model | Last year's reports | Difference | Model ahead in |
|---|---|---|---|---|
| **Brighton 2023–25** (802 reports) | 31.2% (27.2–34.8) | 21.7% (18.6–26.4) | +9.5 (+4.9 to +12.2) | 100% |
| **Southampton 2018–19** (381 reports, 262 on non-main roads) | 41.6% (33.9–47.9) | 33.7% (24.5–38.9) | +7.9 (+3.1 to +15.5) | 100% |
| Leave-one-city-out: Southampton | 36.6% | 33.5% | +3.1 (+0.9 to +8.1) | 99% |
| Leave-one-city-out: Brighton | 18.4% | 16.5% | +1.9 (−3.0 to +6.0) | 76% |
| Leave-one-city-out: Portsmouth | 19.2% | 13.1% | +6.2 (−3.8 to +12.7) | 84% |
| Frozen 2026 check, Southampton (33 reports) | 15.2% | 12.1% | +3.0 (−12.1 to +14.8) | 52% |

What this does and doesn't show:
- With a city's own history, the model beats last year's reports in both cities tested.
- In a city it has never seen, it is only roughly level with last year's reports: it needs local history.
- Without past-report features (physical inputs only) it is no better than chance in Southampton (10.4%), so we
  don't offer it as a cold-start fallback.
- The 2026 checks are too small to judge either way. We report them anyway.
- Counts measure FixMyStreet use, not true pothole rates, so scores rank segments within one city and year.

### Limits of FixMyStreet data

FixMyStreet is one of several ways residents report problems, so its reports are only part of the picture. mySociety,
which runs it, [warns against using the data to compare or rank areas](https://www.mysociety.org/2024/02/06/statement-from-mysociety-regarding-misuse-of-fixmystreet-data/). RoadSense therefore only ranks roads *within* a
city and never compares councils. Report status relies on residents marking problems fixed, so many "open" reports
are years old. The app only treats reports from the last 120 days as open.
[FixMyStreet itself notes](https://www.fixmystreet.com/about/connecting) that local road conditions can't be inferred
from its reports alone, which is why RoadSense combines reports with physical road data (traffic, buses, segment,
weather).

**Reproducible:** `python -m roadsense.models.real_risk` (fixed seed 2026) regenerates `reports/real_risk_eval.md`.
A second team member re-ran it from a clean `main` on 17 Oct and got identical numbers.

Other evaluations: weekly weather model on synthetic labels (pipeline check only, `reports/risk_eval.md`);
streetlights (`reports/lights_eval.md`: ranks no better than install year, its value is the replacement date);
report triage against keyword rules (`reports/triage_vs_keywords.md`; keyword rules 91/100 on hand-labelled real
reports, Gemini comparison TODO); running cost (`reports/cost.md`: measured tokens at the published Gemini price, about £0.0006 per triaged report;
under £3 a year even at Southampton's full yearly repair volume of about 3,100 to 4,200 repairs, an upper bound because
these are repairs, not reports).

## What is real and what is synthetic

Everything public is real. The only synthetic parts are records the council already holds but doesn't publish.

| Part | Source | Status |
|---|---|---|
| Road network, road class, bus routes, junctions, cycle routes, schools/hospitals | OpenStreetMap | Real |
| Traffic load | DfT counts | Real for 314 Southampton segments; road-class median elsewhere, shown as "modelled estimate" |
| Flood exposure, wards, weather (history + 16-day forecast) | EA, MapIt/ONS, Open-Meteo | Real |
| Training and test labels, every number in "How well it works" | FixMyStreet | Real |
| Model that ranks the Southampton plan (`risk_latest`) | trained on real FixMyStreet reports, 3 cities | Real (`trained_on = real`) |
| Southampton's recent pothole history (2020–26) fed to that model | council repair log stand-in | **SYNTHETIC** (`history_source = synthetic`): residents moved off FixMyStreet after 2019, so real recent history is too thin |
| Week-to-week movement in the plan; what-if scenarios | synthetic-trained weekly weather model, used as a ward-level multiplier/ratio | **SYNTHETIC** |
| Road wear, resurfacing history, streetlight register and faults, crew outcomes | `data/synthetic/` (seed 2026) | **SYNTHETIC** |
| Treatment £/m² | our assumptions | Assumption, labelled in the app |
| Brighton map | real-label model with real FixMyStreet history | Real (`uses_synthetic = false`); yearly scale assumed (`scale_source`) |

Every synthetic row carries `is_synthetic = true` and a `source = "synthetic:<generator>@<version>"` tag, and every
screen that uses one shows a **SYNTHETIC** badge. The dashboard header reads "trained on real reports · history
synthetic". Confirmations from simulated crew feedback are labelled "Simulated crew report" and left out of the
confirmed-pothole count. In deployment the synthetic parts are replaced by the council's own repair log, inspection
records and asset register. All assumptions and gaps are listed in `DATA_GAPS.md`.

## Data sources and licences

All data was retrieved during the hackathon (16–18 Oct 2026). Exact retrieval timestamps are in `data/processed/sources.json`. Nothing was collected or processed before hacking started on Fri 16 Oct, 20:00.

| Source | What we use it for | Coverage / dates | Licence and attribution |
|---|---|---|---|
| **FixMyStreet** (mySociety), Open311 API `fixmystreet.com/open311/v2/requests.json` | Pothole reports, used as training and test labels. Agencies: Southampton 2567, Portsmouth 2657, Brighton & Hove 2614 | Southampton train 2015–17, test 2018–19; Brighton train ≤2022, test 2023–25; Portsmouth extra training. Retrieved 17 Oct 2026, 11:00 UTC | No licence stated. FixMyStreet names its Open311 API as the route for extracting report data (https://www.fixmystreet.com/about/connecting); we use that API, not scraping. Reports attributed to mySociety. |
| **OpenStreetMap** | Road network split into segments (22,334 across 3 cities), road class (`is_main_road`), cycle routes, schools and hospitals | Extract retrieved 17 Oct 2026, 12:03 UTC | © OpenStreetMap contributors, Open Database Licence (ODbL) 1.0. openstreetmap.org/copyright |
| **DfT road traffic statistics** | Traffic load per segment (AADF incl. HGVs). 314 Southampton segments have a direct count; the rest use road-class medians, shown in the app as "modelled estimate" | Count year up to 2025, retrieved 17 Oct 2026, 12:22 UTC | Open Government Licence v3.0. Contains public sector information licensed under the OGL v3.0 |
| **Environment Agency Flood Map for Planning: Flood Zone 3** | Flood exposure feature | Retrieved 17 Oct 2026, 12:45 UTC | Open Government Licence v3.0. © Environment Agency copyright and/or database right. Contains OS data © Crown copyright and database right |
| **Open-Meteo** | Historical weekly weather (rain, freeze–thaw) and 3-week forecast | Historical: TODO check range in `data/processed/sources.json`; forecast retrieved 17 Oct 2026, 12:36 UTC | Data CC BY 4.0. Weather data by Open-Meteo.com. Free API used for non-commercial purposes |
| **MapIt** (mySociety) | Ward boundaries, Southampton and Brighton | Retrieved 17 Oct 2026, 12:06 UTC | Boundaries derived from OS Boundary-Line, OGL v3.0. Contains OS data © Crown copyright and database right |
| **ONS ward boundaries** | Ward boundaries, Portsmouth (MapIt free quota ran out mid-hackathon) | December 2024 ward boundaries, retrieved 17 Oct 2026, 15:05 UTC | Source: Office for National Statistics, licensed under OGL v3.0. Contains OS data © Crown copyright and database right |
| **Google Gemini API** | Report triage (classification, draft work orders) | Model fallback list `gemini-3.8-flash` → `gemini-3-flash-preview` → `gemini-flash-latest` | Gemini API terms. Only public FixMyStreet text and synthetic data are sent |

### Figures quoted in the pitch (not model inputs)
- Southampton pothole repairs 2021–25 and driver survey: Blackcircles analysis of council FOI data, 18 Mar 2026
- Government pothole ratings (Southampton amber, Portsmouth green): The News, 12 Jan 2026
- Planned vs reactive repair cost (£56.94 vs £87.80) and backlog (£18.62bn): ALARM survey 2025 / 2026

## Privacy

- Residents' full report descriptions (`data/raw/fms_raw.csv`) never leave the machine that pulled them: the file is
  git-ignored and has never been committed.
- Report titles kept in the repo are redacted: house numbers become `[number]`, postcodes `[postcode]` and names
  `[name]` (`roadsense/prevent/redact_titles.py`; the ingest step redacts on every rebuild).
- Titles are redacted before they are stored, displayed or sent to Gemini; report descriptions are not stored.
- Only public FixMyStreet text and synthetic data are sent to Gemini. API keys live in `.env`, which is git-ignored.

## AI-generated code and AI in the product

All code in this repository was written with Claude Code (Anthropic), run by three team members, one per part:
data (lane A), models (lane B), product (lane C). Commits made through Claude Code carry a `Co-Authored-By: Claude`
line. Team members chose the approach, reviewed and ran the code, checked the data, and made the decisions recorded
in `STATUS.md`, `DATA_GAPS.md` and `schemas.md`. Claude (chat) was also used for planning, code review and merging.

What the team did:
- Chose the problem and user (Southampton highways officers / Balfour Beatty Living Places) and defined the build plan
  (milestones, lanes, merges) the agents worked from.
- Chose and checked the data sources, including spotting that Southampton's FixMyStreet reports collapse after 2019.
- Set the honesty rules: synthetic inputs are labelled in the app, train/test periods never overlap, and we don't claim
  results the evaluation doesn't support.
- Split the work into three lanes with a shared data contract, and reviewed and merged every branch, with tests run
  before each merge.
- Checked the evidence used in the pitch against primary sources.
- Removed personal details from public report text before publishing.

In the product, the risk model is a LightGBM classifier we trained; Google Gemini is used only for report triage: results are
cached and shown with the method used (Gemini or keyword fallback), and an officer approves or rejects every work order.
The 100 triage evaluation labels were drafted by Claude Code from report titles: TODO note who spot-checked them.

## What existed before the event

Nothing. All data was retrieved and all code written during the hackathon. The first commit is at 12:08 on
Saturday 17 October 2026, after hacking opened on Friday 16 October at 20:00.
(TODO after the history rewrite: the public repo's commit hashes differ from the working repo's; dates are unchanged.)

## Team

- Nilen Rao: data pipeline, merges
- Aryan [SURNAME]: models
- Armaan [SURNAME]: product (API, dashboard, triage)
- [NAME]: pitch
- [NAME]: pitch, video

## Who helped

[Mentors / organisers / anyone else who gave advice, or "No outside help."]
