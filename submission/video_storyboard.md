# Video storyboard (click by click, about 2:30)

Values are from `main` at 28cd723 on 17 Oct (risk model `risk@2026-10-17T17:53`, Brighton `risk@2026-10-17T18:27`).
**Do not record yet**: wait until Aryan's Brighton inspection list is merged, then re-check every name and number
below on the final build.

## Before recording

1. `python -m roadsense.api.demo_check` must print `10/10 passed`.
2. Delete `outputs/lane_c/state.json` (or `POST /demo/reset`) so the triage queue is empty.
3. `python -m roadsense.api`, wait for `warming: ...`, open http://127.0.0.1:8000 in a 1920x1080 window at 100% zoom.
4. Pan the map once so the OpenStreetMap tiles are cached.

## 0:00-0:20 Problem (voice over the map of Southampton)

- No clicks. Say: "Southampton fills about 4,000 potholes a year, mostly after they've formed. A reactive repair costs
  £87.80, a planned one £56.94. RoadSense tells the highways officer which roads to treat this week, before they fail."

## 0:20-0:50 Southampton plan

1. Point at the header: green **REAL LABELS** badge, "Weather data by Open-Meteo.com".
2. Point at the plan heading: "Model risk@2026-10-17T17:53: **trained on real reports · history synthetic**".
3. Click the **Worth treating** tab. Read the header: "11 roads pay back · 3 confirmed potholes · £21,665 treatment ·
   £29,859 reactive cost avoided". Say: "confirmed potholes come first, they're a repair we have to make; then roads
   where prevention pays for itself."
4. Click **All roads** to go back.

## 0:50-1:20 Why row 1 ranks first

1. Click row 1, **Millbrook Flyover / Redbridge Road (A33)**, Millbrook ward, badge **Pays back ×4.29**.
2. In the card, point at:
   - Urgency 46, prevention band; P30 for the next four weeks rising to 0.49 (weeks marked f = Open-Meteo forecast,
     c = climatology).
   - A-road, DfT count on the same road (heavy port traffic).
   - Reasons: potholes repaired here last year and in earlier years, and on neighbouring roads (**synthetic council log,
     scaled**; say so).
   - Treatment "Patch now, schedule resurfacing" £90 against £386 of reactive repairs avoided over its 5-year life.
3. Say: "the reasons and the cost logic are on screen; the officer decides."

## 1:20-1:50 Triage one real report

1. Click the **Report triage** tab.
2. In the dropdown pick **2026-07-29 · Large pothole** (FixMyStreet report 9864063). Click **Triage report**.
   The card shows: pothole, Gemini (model name in the card), attached to segment SOU-2235-01 (0.7 m away), draft work
   order. About 2 seconds with Gemini.
3. Click **Re-submit (duplicate)**: "merged into fms-9864063 (no new Gemini call)".
4. Click **Approve work order**: the map flies to the road, now held at urgency 70.
5. In the road card click **Pothole** under "Record crew outcome": "urgency 70 → 100, treatment permanent repair".

## 1:50-2:10 Brighton: the real-data check

1. In the header, **City** dropdown: choose **Brighton**. The map moves to Brighton; the left panel says "risk map only,
   **100% real inputs**".
2. Click **London Road** (Preston Park): "Top 1% risk in the city" and three reasons from real FixMyStreet reports.
3. Say: "on Brighton's real 2023-25 reports, our top tenth of roads caught 31% of potholes against 22% for last year's
   reports; in Southampton 42% against 34%."
4. Switch **City** back to **Southampton**.

## 2:10-2:30 Business case and one failure case

1. Click the map in the Solent (outside the city): "Outside Southampton coverage". Click the grey M271:
   "National Highways road, not scored".
2. Say: "a licence per council or contractor; Gemini triage costs about £2 a year at Southampton's volume
   (reports/cost.md); a second city needs its boundary and its own repair log."

## Re-check after Aryan's merge

- Plan row 1 name, badge and numbers; Worth treating header; the Brighton road with the top-1% band (and whatever the
  inspection list adds to the Brighton view).
- The triage report still snaps to a segment (`python -m roadsense.api.demo_check`, step 4).
