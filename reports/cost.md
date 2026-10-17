# Running cost per officer

_Generated 2026-10-17T15:11:13+00:00 by `python -m roadsense.agent.cost` from the token log (`outputs/lane_c/token_log.jsonl`). Re-run it after any live Gemini run and this page updates._

## Measured

Token counts below are what the Gemini API returned in `usage_metadata` for each call: real counts, not estimates.

| What | Logged | Model | Mean input tokens | Mean output tokens (incl. thinking) | API calls each | £ each at the assumed price |
| --- | --- | --- | --- | --- | --- | --- |
| Full triage (agent loop: lookup, duplicates, risk, work order) | 1 | gemini-3.8-flash | 3,254 | 194 | 4.0 | £0.00110 |
| Classification only (one call, used by the 100-report eval) | 16 | gemini-3.8-flash | 674 | 105 | 1.0 | £0.00035 |

Sample size: **1 full triage run(s)** only, so the per-report figure is indicative. Run more reports through `POST /reports` with Gemini on to firm it up.

## Formula

```
£ per report     = (input_tokens x P_in + output_tokens x P_out) / 1,000,000 x FX
LLM £/officer/mo = £ per report x reports_per_month / officers  (+ £ per plan x plans per officer, 0 today)
Total            = LLM £/officer/mo + hosting £/month / officers
```

with P_in = $0.3, P_out = $2.5 per million tokens, FX = £0.75 per $, reports_per_month = 300, officers = 4, hosting = £25/month.

## Result

£0.00110 per report x 300 / 4 = **£0.08 LLM** + £6.25 hosting = **£6.33 per officer per month** (from 1 measured full triage run(s); the token count is measured, the price and volumes are assumptions).

## Not measured (config assumptions)

- **Price:** $0.3/M input and $2.5/M output is the Gemini 2.5 Flash paid-tier list price. The logged model is `gemini-3.8-flash`; its price has not been checked, so confirm on ai.google.dev/pricing before quoting the £ figure.
- **Volume:** 300 reports a month city-wide (about 3,600 Southampton pothole repairs a year, FOI 2021-2025) shared by 4 officers. Both are assumptions.
- **Hosting:** £25 a month for one small VM running the API and page. Assumption.
- **The weekly plan uses no LLM**, so it adds no token cost.
- **The free tier** costs nothing but is rate-limited (5 requests a minute; a live run hit the daily quota on 17 Oct) and may use prompts to improve Google's products, so only public reports and synthetic data are sent.
