# Potholes with and without prevention: modelled scenario (Southampton)

_Generated 2026-10-18T02:56:48+00:00 by `python -m roadsense.prevent.scenario`, plan as of 2026-10-12._

**This is a modelled scenario, not observed evidence.** It applies assumed treatment effects to the risk model's expected potholes. Treatment choice uses SYNTHETIC wear. Use it to compare options, not as a forecast of counts.

Expected potholes needing reactive repair with no prevention: **3,113 a year** across 8,135 council segments (Southampton FOI 2025: 3,113 potholes repaired (risk model's yearly total)).

Treatment effects in this scenario use each segment's yearly risk; the weekly plan's own payback figure uses this month's risk, which is lower in autumn, so the two are not the same number.

| Scenario | Potholes over 5 years (central) | Range (low to high effect) | Avoided (central) | Treatment spend | Reactive cost avoided (central) |
|---|---|---|---|---|---|
| No prevention (reactive repairs only) | 15,565 | 15,565 to 15,565 | 0 | £0 | £0 |
| This week's plan, treated now | 14,932 | 15,248 to 14,774 | 633 | £101,662 | £55,592 |
| Worth treating list, treated now | 15,188 | 15,377 to 15,094 | 377 | £21,665 | £33,100 |
| £250,000 a year on preventive treatment | 13,751 | 14,658 to 13,297 | 1,814 | £1,202,803 | £159,305 |
| £500,000 a year on preventive treatment | 13,134 | 14,350 to 12,527 | 2,431 | £2,440,356 | £213,423 |
| £1,000,000 a year on preventive treatment | 12,413 | 13,989 to 11,625 | 3,152 | £4,941,541 | £276,734 |
| £2,000,000 a year on preventive treatment | 11,515 | 13,540 to 10,502 | 4,050 | £9,961,640 | £355,609 |

Year by year (central, expected potholes):

| Scenario | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|---|---|---|---|---|---|
| No prevention (reactive repairs only) | 3,113 | 3,113 | 3,113 | 3,113 | 3,113 |
| This week's plan, treated now | 2,986 | 2,986 | 2,986 | 2,986 | 2,986 |
| Worth treating list, treated now | 3,038 | 3,038 | 3,038 | 3,038 | 3,038 |
| £250,000 a year on preventive treatment | 2,881 | 2,791 | 2,740 | 2,690 | 2,648 |
| £500,000 a year on preventive treatment | 2,791 | 2,689 | 2,609 | 2,547 | 2,498 |
| £1,000,000 a year on preventive treatment | 2,689 | 2,544 | 2,455 | 2,391 | 2,334 |
| £2,000,000 a year on preventive treatment | 2,541 | 2,387 | 2,276 | 2,189 | 2,122 |

## Assumptions

- Expected potholes a year per segment = the risk model's share of Southampton's FOI 2025 total (3,113), from the model trained on real FixMyStreet reports (history input SYNTHETIC), held at that level every year.
- Treatment per segment depends on SYNTHETIC wear (no council condition survey).
- Treatment effects are ASSUMED hazard multipliers: crack sealing and surface dressing x0.6, patch x0.8, resurfacing x0.3; low/central/high scale the effect by 0.5/1.0/1.25.
- Service lives are ASSUMED: crack sealing 3, surface dressing 8, patch 5, resurfacing 15 years.
- Treatment £/m2 are ASSUMED placeholders; reactive repair £87.80 is the ALARM 2025 average.
- Expected values only: real years scatter around them (Poisson noise and weather).

The ranking that picks roads for the budgets is the plan's own (reactive cost avoided per £). The held-out check of that ranking against real reports is in reports/real_risk_eval.md; there is no held-out check of the treatment effects themselves, because no council treatment-outcome data is open.
