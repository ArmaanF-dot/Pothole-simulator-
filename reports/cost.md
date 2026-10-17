# Running cost of report triage (Gemini)

_Measured 2026-10-17 20:37 UTC: 10 real Southampton FixMyStreet reports (the 10 most recent in `data/processed/fms_roads_clean.csv`) triaged live through `Service.triage_report`, the same path as `POST /reports` and the demo (one-call "fast" mode). Token counts are what the Gemini API returned in `usage_metadata`._

## Measured token counts

| FixMyStreet report | Model that answered | Input tokens | Output tokens | Thinking tokens |
| --- | --- | --- | --- | --- |
| fms-10054415 | gemini-3-flash-preview | 910 | 100 | 0 |
| fms-9996017 | gemini-3-flash-preview | 921 | 106 | 0 |
| fms-9913130 | gemini-3-flash-preview | 926 | 104 | 0 |
| fms-9864063 | gemini-3-flash-preview | 892 | 90 | 0 |
| fms-9815538 | gemini-3-flash-preview | 899 | 93 | 0 |
| fms-9658382 | gemini-3-flash-preview | 911 | 103 | 0 |
| fms-9374920 | gemini-3-flash-preview | 900 | 98 | 0 |
| fms-9313325 | gemini-3-flash-preview | 743 | 90 | 0 |
| fms-9291752 | gemini-3-flash-preview | 910 | 99 | 0 |
| fms-9187098 | gemini-3-flash-preview | 919 | 106 | 0 |

Mean per triaged report: **893 input tokens** and **99 output tokens** (thinking off, one API call per report).

## Cost

Price of the model that answered every call, `gemini-3-flash-preview`, paid tier: **$0.50 per 1M input tokens, $3.00 per 1M output tokens (incl. thinking)**. Source: Google AI for Developers, Gemini API pricing, https://ai.google.dev/gemini-api/docs/pricing (page "last updated 2026-10-16 UTC", read 17 Oct 2026).

```
£ per report = (input tokens x $0.50 + output tokens x $3.00) / 1,000,000 x 0.75 £/$
             = (893 x 0.50 + 99 x 3.00) / 1,000,000 x 0.75 = £0.000557
£ per year   = £ per report x 3,775 reports a year = £2.10
```

- **£0.00056 per triaged report** (about £0.56 per 1,000 reports).
- **£2.10 a year at Southampton's volume:** 3,775 reports a year, the mean of Southampton's pothole repairs 2021-2025 (4,002 / 3,972 / 3,627 / 4,162 / 3,113; council FOI via Blackcircles, March 2026), assuming one triaged report per repair.
- If the first model in the fallback list (`gemini-3.8-flash`, $0.75 / $3.75 until 31 Dec 2026, same source) answered instead: £0.00078 per report, £2.95 a year.
- Duplicates within 15 m and 14 days reuse the original's triage with no Gemini call, so the real yearly call count is lower.

## Assumptions (not measured)

- Exchange rate 0.75 £/$ (assumption; not a quoted rate).
- One triaged report per pothole repair; FixMyStreet volume in Southampton is far lower since 2020, so this is an upper bound for FixMyStreet-only triage.
- Free tier: the same calls cost £0 but are rate-limited (5 requests a minute per model) and Google may use the prompts to improve its products, so only public reports and synthetic data are sent.
- Hosting (one small VM for the API and page) is not included above; it is the same whatever the report volume.
