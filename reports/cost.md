# Running cost per officer

_Generated 2026-10-17T12:16:51+00:00 by `python -m roadsense.agent.cost` from the token log (`outputs/lane_c/token_log.jsonl`). Token counts are what the Gemini API reported (`usage_metadata`), not estimates._

**No live Gemini calls logged yet**, so there is no measured cost. Add `GEMINI_API_KEY` to `.env`, then run `python -m roadsense.agent.triage` (100 real reports) and `python -m roadsense.agent.cost`.

## Assumptions (config, not measured)

- Price: $0.3/M input and $2.5/M output tokens (gemini-2.5-flash paid tier; check ai.google.dev/pricing), $1=£0.75.
- Volume: 300 reports a month city-wide (about 3,600 Southampton pothole repairs a year, FOI 2021-2025), shared by 4 officers; 4.33 weekly plans per officer a month.
- Hosting: £25 a month for one small VM running the API and page, shared by all officers.
- The weekly plan itself is computed without an LLM; only report triage calls Gemini.
- The free tier costs nothing but may use prompts to improve Google's products, so only public reports and synthetic data are sent.
