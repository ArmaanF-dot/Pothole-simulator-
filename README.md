# RoadSense

## Data sources and licences

All data was retrieved during the hackathon (16–18 Oct 2026). Exact retrieval timestamps are in `data/processed/sources.json`. Nothing was collected or processed before hacking started on Fri 16 Oct, 20:00.

| Source | What we use it for | Coverage / dates | Licence and attribution |
|---|---|---|---|
| **FixMyStreet** (mySociety), Open311 API `fixmystreet.com/open311/v2/requests.json` | Pothole reports, used as training and test labels. Agencies: Southampton 2567, Portsmouth 2657, Brighton & Hove 2614 | Southampton train 2015–17, test 2018–19; Brighton train ≤2022, test 2023–25; Portsmouth extra training. Retrieved 17 Oct 2026, 11:00 UTC | Publicly published reports from mySociety's FixMyStreet. We found no explicit open-data licence, so we use them for non-commercial research only and keep only location, category, status and date. Credit: FixMyStreet / mySociety |
| **OpenStreetMap** | Road network split into segments (22,334 across 3 cities), road class (`is_main_road`), cycle routes, schools and hospitals | Extract retrieved 17 Oct 2026, 12:03 UTC | © OpenStreetMap contributors, Open Database Licence (ODbL) 1.0. openstreetmap.org/copyright |
| **DfT road traffic statistics** | Traffic load per segment (AADF incl. HGVs). 314 Southampton segments have a direct count; the rest use road-class medians, shown in the app as "modelled estimate" | Count year up to 2025, retrieved 17 Oct 2026, 12:22 UTC | Open Government Licence v3.0. Contains public sector information licensed under the OGL v3.0 |
| **Environment Agency Flood Map for Planning: Flood Zone 3** | Flood exposure feature | Retrieved 17 Oct 2026, 12:45 UTC | Open Government Licence v3.0. © Environment Agency copyright and/or database right. Contains OS data © Crown copyright and database right |
| **Open-Meteo** | Historical weekly weather (rain, freeze–thaw) and 3-week forecast | Historical TODO; forecast retrieved 17 Oct 2026, 12:36 UTC | Data CC BY 4.0. Weather data by Open-Meteo.com. Free API used for non-commercial purposes |
| **MapIt** (mySociety) | Ward boundaries, Southampton and Brighton | Retrieved 17 Oct 2026, 12:06 UTC | Boundaries derived from OS Boundary-Line, OGL v3.0. Contains OS data © Crown copyright and database right |
| **ONS ward boundaries** | Ward boundaries, Portsmouth (MapIt free quota ran out mid-hackathon) | December 2024 ward boundaries, retrieved 17 Oct 2026, 15:05 UTC | Source: Office for National Statistics, licensed under OGL v3.0. Contains OS data © Crown copyright and database right |

### Synthetic data
Southampton City Council's own inspection and repair records are not public, so lane B generated **synthetic council data** (inspection outcomes, repair history, crew feedback) to demonstrate the workflow (`roadsense/synthetic/`). Synthetic data is never used to compute the evaluation numbers. Those use real FixMyStreet reports only. In the app, any confirmation from simulated crew feedback is labelled **"Simulated crew report"** and is excluded from the confirmed-pothole count.

### Figures quoted in the pitch (not model inputs)
- Southampton pothole repairs 2021–25 and driver survey: Blackcircles analysis of council FOI data, 18 Mar 2026
- Government pothole ratings (Southampton amber, Portsmouth green): The News, 12 Jan 2026
- Planned vs reactive repair cost (£56.94 vs £87.80) and backlog (£18.62bn): ALARM survey 2025 / 2026
