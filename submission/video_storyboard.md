# Video storyboard (click by click, about 2:30)

Values are from `main` at e93b828 (after the daily refresh) on 17 Oct, with row-click-zoom applied (risk model
`risk@2026-10-17T20:44` for Southampton and Brighton, plan as of 2026-10-12). **Do not record yet**: wait for the
recently-treated flag to be merged and for the go-ahead, then re-check every name and number below on the final build.

## Before recording

1. `python -m roadsense.api.demo_check` must print `10/10 passed`.
2. Delete `outputs/lane_c/state.json` (or `POST /demo/reset`) so the triage queue is empty.
3. `python -m roadsense.api`, wait for `warming: ...`, open http://127.0.0.1:8000 in a 1920x1080 window at 100% zoom.
4. Pan the map once so the OpenStreetMap tiles are cached.

## 0:00-0:20 Problem (voice over the map of Southampton)

- No clicks. Say: "Southampton fills about 4,000 potholes a year, mostly after they've formed. A reactive repair costs
  £87.80, a planned one £56.94. RoadSense tells the highways officer which roads to treat this week, before they fail."

## 0:20-0:40 Southampton plan and payback

1. Point at the header: green **REAL LABELS** badge, "Data updated: 17 Oct 2026, 16:05 (committed snapshot)",
   "Weather data by Open-Meteo.com".
2. Point at the plan: "50 segments to treat this week, as of 2026-10-12"; model "trained on real reports · history
   synthetic".
3. Click the **Worth treating** tab. Read the header: "11 roads pay back · 3 confirmed potholes · £21,665 treatment ·
   £29,859 reactive cost avoided". Say: "confirmed potholes come first, they're a repair we have to make; then roads
   where prevention pays for itself."

## 0:40-1:15 Why this road? Castle Road, then triage its report live

1. Still in **Worth treating**, click row 1, **Castle Road** (Bitterne Park, `SOU-2235-01`), badge **Confirmed: must
   fix ×1.54**. The map flies to the road, outlines it and opens its card.
2. In the card, point at:
   - Urgency **70**, high band.
   - Reasons, all real: "open FixMyStreet report, confirmed by keyword", "long segment (178 m)", "busy junction".
   - Treatment "Permanent pothole repair" £57: £56.94 planned now instead of £87.80 reactive later (ALARM 2025).
   - Wear 23% carries the **SYNTHETIC** badge: wear is part of urgency and is a stand-in; the reasons are real.
3. Say: "Castle Road is first because a resident reported a pothole here and it's confirmed: a repair we have to make,
   and a planned repair costs a third less than a reactive one." (Its own model risk is low, P30 0.005; don't call it
   high risk.)
4. Click the **Report triage** tab. In the dropdown pick **2026-07-29 · Large pothole** (FixMyStreet report 9864063,
   the report behind Castle Road). Click **Triage report**. The card shows: pothole, Gemini (model name in the card),
   attached to segment SOU-2235-01 (0.7 m away), draft work order. About 2 seconds with Gemini. (Without a key it says
   keyword triage; record with the key set.)
5. Click **Re-submit (duplicate)**: "merged into fms-9864063 (no new Gemini call)".
6. Click **Approve work order**: the map flies to Castle Road, held at urgency 70.
7. In the road card click **Pothole** under "Record crew outcome": "urgency 70 → 100, treatment permanent repair".

## 1:15-1:45 Flagged, but don't spend yet: The Avenue

1. Click the **Prevention plan** tab, **All roads**. **Ward** dropdown: choose **Portswood**. Click row 4, **The
   Avenue** (A33, the 186 m segment, `SOU-153759797-01`), badge **Loss maker ×0.19**.
2. In the card, point at:
   - Reasons, all from real data: "HGV and bus flow 577 a day", "heavy axle load (802 ESAL/day)", "long segment (186 m)".
   - Traffic: "DfT count on this segment" (2022 count, high confidence). Consequence: A-road, bus route, cycle route.
   - Urgency 40.5, prevention band; P30 for the next four weeks 0.007 rising to 0.028 (weeks 1-3 Open-Meteo forecast,
     week 4 climatology). Wear (88%, part of urgency) carries the **SYNTHETIC** badge: only the reasons are real.
   - Cost logic: "Patch now, schedule resurfacing" £90 against £16.67 of reactive repairs avoided over its 5-year life.
3. Say: "real traffic and axle load flag this road, but the tool says don't spend yet, so it's not in Worth treating.
   The reasons and the numbers are on screen; the officer decides." (Say "flagged", not "high risk": in the app "High"
   is the 70-89 urgency band.)
   - Alternative with bus routes as a reason: Portswood row 2, the other **The Avenue** (173 m, `SOU-229102664-00`):
     "8 bus routes use this road", "HGV and bus flow 769 a day", DfT count on the same road, **Loss maker ×0.27**
     (£90 against £23.99).
4. **Ward** back to **All wards**. Do not open Millbrook Flyover (row 1 in All roads, row 4 in Worth treating): its top
   three reasons are all from the synthetic council repair log.

## 1:45-2:10 Brighton: the same model on real data only

1. In the header, **City** dropdown: choose **Brighton**. The title changes to "Brighton & Hove highways · inspection
   list"; the left panel says "Brighton: inspection list (real data)" with the **100% real inputs** badge.
2. Click the **Prevention plan** tab: "Brighton inspection list: ranked by risk from real FixMyStreet reports. No wear
   model for Brighton, so treatments are chosen on inspection." 55 segments: 5 with an open report in the last 120 days,
   then the top 50 by risk.
3. Under **Open reports (inspect first)**, click row 1, **Tisbury Road** (Central Hove), **Top 5%**: open report
   2026-09-11 "Large pothole, & degraded road surface"; reasons "21 bus routes use this road", "long segment (160 m)",
   "bus stop on this segment". All real.
4. Say: "Southampton's council repair history isn't public, so it's a labelled stand-in; in Brighton, where the real
   history exists, the same model runs on real data only."
5. Switch **City** back to **Southampton**.

## 2:10-2:30 Evidence, business case and one failure case

1. Say (held-out test years only): "On reports it never saw, our top tenth of roads caught 41.6% of Southampton's
   potholes against 33.7% for last year's reports, and 31.2% against 21.7% in Brighton. Chance is 10%. The model wins in
   99% and 100% of 1,000 ward resamples."
2. Click the map in the Solent (outside the city): "Outside coverage". Click the grey M271:
   "National Highways road, not scored".
3. Say: "a licence per council or contractor; Gemini triage costs under £3 a year even at Southampton's full yearly
   repair volume (reports/cost.md); a second city needs its boundary and its own repair log."

## Sources for the numbers

- Plan, Worth treating header, Castle Road and The Avenue cards, Tisbury Road row: `/plan/prevention`,
  `/segments/{id}` and `/plan/inspection?city=Brighton` on e93b828; "Data updated" from `/meta`.
- Evidence: `data/models/eval_ci.json` (`test`: Southampton 2018-19, 381 reports, 17 wards, model ahead in 99% of
  resamples; Brighton 2023-25, 802 reports, 23 wards, 100%), also `reports/risk_eval.md` "Held-out ranges by ward".
  Not the 2026 frozen check (33 and 30 reports, too few).
- Cost: `reports/cost.md` (£0.00056 per report; £1.74 to £2.32 a year over 3,113 to 4,162 repairs a year, 2021-25).

## Re-check before recording

- The "Data updated" line in the header (its time changes with each refresh).
- Plan count and as-of date, the Worth treating header and Castle Road at row 1, The Avenue's row number in Portswood
  and its numbers, and whatever the recently-treated flag shows on these rows.
- Tisbury Road is still first under Open reports (its report must still be inside the 120-day window).
- The triage report still snaps to a segment (`python -m roadsense.api.demo_check`, step 4).
