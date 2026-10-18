# Potholes with and without prevention: modelled scenario (Southampton)

_Generated 2026-10-18T05:13:35+00:00 by `python -m roadsense.prevent.scenario`, plan as of 2026-10-12._

**This is a modelled scenario, not observed evidence.** It applies assumed treatment effects to the risk model's expected potholes. Treatment choice uses SYNTHETIC wear. Use it to compare options, not as a forecast of counts.

Expected potholes needing reactive repair with no prevention: **3,113 a year** across 8,135 council segments (Southampton FOI 2025: 3,113 potholes repaired (risk model's yearly total)).

Treatment effects in this scenario use each segment's yearly risk; the weekly plan's own payback figure uses this month's risk, which is lower in autumn, so the two are not the same number.

| Scenario | Potholes over 5 years (central) | Range (low to high effect) | Avoided (central) | Treatment spend | Reactive cost avoided (central) |
|---|---|---|---|---|---|
| No prevention (reactive repairs only) | 15,565 | 15,565 to 15,565 | 0 | £0 | £0 |
| This week's plan, treated now | 14,982 | 15,274 to 14,837 | 583 | £89,748 | £51,167 |
| Worth treating list, treated now | 15,426 | 15,495 to 15,391 | 139 | £7,429 | £12,229 |
| £250,000 a year on preventive treatment | 13,827 | 14,696 to 13,393 | 1,738 | £1,229,459 | £152,571 |
| £500,000 a year on preventive treatment | 13,272 | 14,418 to 12,698 | 2,293 | £2,470,621 | £201,348 |
| £1,000,000 a year on preventive treatment | 12,516 | 14,040 to 11,753 | 3,049 | £4,961,110 | £267,720 |
| £2,000,000 a year on preventive treatment | 11,529 | 13,547 to 10,520 | 4,036 | £9,947,899 | £354,381 |

Year by year (central, expected potholes):

| Scenario | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|---|---|---|---|---|---|
| No prevention (reactive repairs only) | 3,113 | 3,113 | 3,113 | 3,113 | 3,113 |
| This week's plan, treated now | 2,996 | 2,996 | 2,996 | 2,996 | 2,996 |
| Worth treating list, treated now | 3,085 | 3,085 | 3,085 | 3,085 | 3,085 |
| £250,000 a year on preventive treatment | 2,878 | 2,803 | 2,755 | 2,714 | 2,677 |
| £500,000 a year on preventive treatment | 2,801 | 2,714 | 2,642 | 2,583 | 2,531 |
| £1,000,000 a year on preventive treatment | 2,714 | 2,582 | 2,483 | 2,402 | 2,334 |
| £2,000,000 a year on preventive treatment | 2,582 | 2,401 | 2,274 | 2,176 | 2,095 |

## Assumptions

- Expected potholes a year per segment = the risk model's share of Southampton's FOI 2025 total (3,113), from the model trained on real FixMyStreet reports (history input SYNTHETIC), held at that level every year.
- Treatment per segment depends on SYNTHETIC wear (no council condition survey).
- Treatment effects are ASSUMED hazard multipliers: crack sealing and surface dressing x0.6, patch x0.8, resurfacing x0.3; low/central/high scale the effect by 0.5/1.0/1.25.
- Service lives are ASSUMED: crack sealing 3, surface dressing 8, patch 5, resurfacing 15 years.
- Treatment £/m2 are ASSUMED placeholders; reactive repair £87.80 is the ALARM 2025 average.
- Expected values only: real years scatter around them (Poisson noise and weather).

The ranking that picks roads for the budgets is the plan's own (reactive cost avoided per £). The held-out check of that ranking against real reports is in reports/real_risk_eval.md; there is no held-out check of the treatment effects themselves, because no council treatment-outcome data is open.
