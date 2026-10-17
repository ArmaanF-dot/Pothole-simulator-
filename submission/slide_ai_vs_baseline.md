# Slide: does the AI beat the obvious baseline?

## Headline

**On real Southampton reports, RoadSense's top 10% of roads caught 39% of next year's reported potholes. Ranking by last
year's complaints caught 34%.**

## Chart (bar, with 95% interval whiskers)

Share of real FixMyStreet pothole reports landing on the top 10% of road length, Southampton test years 2018-19
(381 reports, 8,145 segments). Source: `reports/real_risk_eval.md` (lane B), paired segment bootstrap, 1,000
resamples, seed 2026.

| Method | Capture | 95% interval |
| --- | --- | --- |
| RoadSense model (road, load, weather + past reports) | 38.6% | 31.0% to 45.3% |
| Baseline: last year's reports | 33.7% | 24.5% to 38.9% |
| Load x past reports formula | 19.8% | 14.5% to 25.2% |
| Physical features only (no past reports) | 19.9% | 12.8% to 26.4% |
| Random | 10% | |

Footnote line: **Model minus baseline +4.9 points (95% 0.9 to 12.1); model ahead in 99% of resamples.**

## Honesty box (keep it on the slide)

- Frozen 2026 check, Jan to Oct, only 33 reports: model 12.1% vs baseline 12.1%, so no difference at that size.
- Without past reports the model falls short of the baseline (19.9% vs 33.7%): the physical features alone are not
  enough, the combination is what wins.
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
