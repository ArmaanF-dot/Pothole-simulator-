# Slide: does the AI beat the obvious baseline?

## Headline

**On real Southampton reports, RoadSense's top 10% of roads caught 37% of next year's reported potholes. Ranking by last
year's complaints caught 34%. In Brighton: 32% against 22%.**

## Chart (bar, with 95% interval whiskers)

Share of real FixMyStreet pothole reports landing on the top 10% of road length, Southampton test years 2018-19
(381 reports, 8,145 segments). Source: `reports/real_risk_eval.md` (lane B), paired segment bootstrap, 1,000
resamples, seed 2026.

| Method | Capture | 95% interval |
| --- | --- | --- |
| RoadSense model (road, load, weather, building sites, digs + past reports) | 37.1% | 29.7% to 43.9% |
| Baseline: last year's reports | 33.7% | 24.5% to 38.9% |
| Load x past reports formula | 19.8% | 14.5% to 25.2% |
| Physical features only (no past reports) | 10.4% | 7.1% to 14.3% |
| Random | 10% | |

Footnote line: **Model minus baseline +3.4 points (95% -1.0 to 11.5); model ahead in 94% of resamples.** Brighton
2023-25: 31.8% vs 21.7% (+10.1, 5.6 to 12.9), ahead in 100%: the clear result. Trained without Southampton, the model
is level with the baseline there (34.8% vs 33.5%, +1.3, -0.9 to 6.0).

## Honesty box (keep it on the slide)

- Frozen 2026 check, Jan to Oct, only 33 reports: model 21.2% vs baseline 12.1% (+9.1, -7.4 to 24.0), so no clear
  difference at that size.
- Building sites and utility digs went into the model on 18 Oct; on the test years they cost Southampton 4.5 points
  (41.6% without them) and added 0.6 in Brighton (`reports/context_eval.md`).
- Without past reports the model falls short of the baseline (10.4% vs 33.7%): the physical features alone are not
  enough, the combination is what wins.
- Leave-one-city-out is ahead of the baseline in all three cities, but clearly in none (Southampton +1.3, -0.9 to 6.0;
  Brighton +3.0, -2.1 to 7.7; Portsmouth +6.8, -3.6 to 13.8).
- FixMyStreet counts measure who reports, not where the damage is, and Southampton has no reports for 2020 to 2022.
- The live plan is ranked by this real-report model ("trained on real reports · history synthetic": its recent
  pothole history comes from the SYNTHETIC repair log because council logs are not public). The weekly weather model
  is trained on synthetic labels; on those it scores PR-AUC 0.253 against 0.095 for prior pothole count: a pipeline
  check, not proof.

## Why it matters (one line, from the research doc)

At ALARM 2025 rates, Southampton's 4,247 fills in 2024/25 cost about £373k if all reactive vs about £242k if all
planned: roughly £130k a year of difference before claims or road life (team calculation, not a council figure;
Southampton Transparency Report June 2025, ALARM 2025).

## Not on the slide (missing numbers)

- Gemini triage vs keyword rules: keyword rules score 91/100 on hand-labelled real reports; the Gemini run stopped on
  the free-tier quota after 16 of 100, so there is no Gemini accuracy yet.
- Brighton 2023-25 and leave-one-city-out: waiting for lane A's Brighton labels.
