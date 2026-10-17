"""Running cost per officer (M8): reads the real token log and writes reports/cost.md.

    python -m roadsense.agent.cost

Token counts come only from outputs/lane_c/token_log.jsonl (what Gemini reported for each call).
Prices, volumes and hosting are config ASSUMPTIONS and are printed as such.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from roadsense.prevent import inputs as I


def read_log(cfg: dict, root: Path | None = None) -> pd.DataFrame:
    p = I.resolve(cfg, "state_dir", root) / "token_log.jsonl"
    if not p.exists():
        return pd.DataFrame(columns=["ts", "kind", "model", "ref", "prompt_tokens", "output_tokens", "thoughts_tokens",
                                     "total_tokens", "calls"])
    return pd.DataFrame([json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()])


def compute(cfg: dict, log: pd.DataFrame) -> dict:
    c = cfg["cost"]
    price_in = c["price_per_mtok_usd"]["input"] * c["usd_to_gbp"] / 1e6
    price_out = c["price_per_mtok_usd"]["output"] * c["usd_to_gbp"] / 1e6
    out = {"n_calls_logged": len(log)}
    per = {}
    for kind in ["triage", "triage_eval", "weekly_plan"]:
        k = log[log["kind"] == kind]
        if len(k):
            inp = k["prompt_tokens"].mean()
            outp = (k["output_tokens"] + k["thoughts_tokens"].fillna(0)).mean()
            per[kind] = {"n": len(k), "input_tokens": float(inp), "output_tokens": float(outp),
                         "calls": float(k["calls"].mean()) if "calls" in k else None,
                         "gbp": float(inp * price_in + outp * price_out),
                         "models": sorted(k["model"].dropna().unique().tolist())}
    out["per_item"] = per
    if "triage" in per:
        tri = per["triage"]["gbp"] * c["reports_per_month"] / c["officers"]
        plan = per.get("weekly_plan", {"gbp": 0.0})["gbp"] * c["plans_per_officer_per_month"]
        host = c["hosting_gbp_per_month"] / c["officers"]
        out.update(llm_gbp_per_officer_month=tri + plan, hosting_gbp_per_officer_month=host,
                   total_gbp_per_officer_month=tri + plan + host)
    return out


LABEL = {"triage": "Full triage (agent loop: lookup, duplicates, risk, work order)",
         "triage_eval": "Classification only (one call, used by the 100-report eval)",
         "weekly_plan": "Weekly plan summary"}


def write_cost_report(cfg: dict | None = None, root: Path | None = None) -> Path:
    cfg = cfg or I.load_config()
    log = read_log(cfg, root)
    r = compute(cfg, log)
    c = cfg["cost"]
    pi, po, fx = c["price_per_mtok_usd"]["input"], c["price_per_mtok_usd"]["output"], c["usd_to_gbp"]
    L = ["# Running cost per officer", "",
         f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `python -m roadsense.agent.cost` "
         "from the token log (`outputs/lane_c/token_log.jsonl`). Re-run it after any live Gemini run and this page updates._", "",
         "## Measured", "",
         "Token counts below are what the Gemini API returned in `usage_metadata` for each call: real counts, not estimates."]
    if not r["per_item"]:
        L += ["", "**Nothing measured yet:** no live Gemini call is in the log. Add `GEMINI_API_KEY` to `.env`, then run "
              "`python -m roadsense.agent.triage` and `python -m roadsense.agent.cost`."]
    else:
        L += ["", "| What | Logged | Model | Mean input tokens | Mean output tokens (incl. thinking) | API calls each | £ each at the assumed price |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
        for k, v in r["per_item"].items():
            L.append(f"| {LABEL.get(k, k)} | {v['n']} | {', '.join(v['models'])} | {v['input_tokens']:,.0f} | "
                     f"{v['output_tokens']:,.0f} | {v['calls'] if v['calls'] is not None else 'n/a'} | £{v['gbp']:.5f} |")
        n_full = r["per_item"].get("triage", {}).get("n", 0)
        L += ["", f"Sample size: **{n_full} full triage run(s)**"
              + (" only, so the per-report figure is indicative. Run more reports through `POST /reports` with Gemini on to firm it up."
                 if n_full < 20 else ".")]
    L += ["", "## Formula", "",
          "```",
          "£ per report     = (input_tokens x P_in + output_tokens x P_out) / 1,000,000 x FX",
          "LLM £/officer/mo = £ per report x reports_per_month / officers  (+ £ per plan x plans per officer, 0 today)",
          "Total            = LLM £/officer/mo + hosting £/month / officers",
          "```", "",
          f"with P_in = ${pi}, P_out = ${po} per million tokens, FX = £{fx} per $, reports_per_month = {c['reports_per_month']}, "
          f"officers = {c['officers']}, hosting = £{c['hosting_gbp_per_month']}/month.", ""]
    if "total_gbp_per_officer_month" in r:
        t = r["per_item"]["triage"]
        L += ["## Result", "",
              f"£{t['gbp']:.5f} per report x {c['reports_per_month']} / {c['officers']} = "
              f"**£{r['llm_gbp_per_officer_month']:.2f} LLM** + £{r['hosting_gbp_per_officer_month']:.2f} hosting = "
              f"**£{r['total_gbp_per_officer_month']:.2f} per officer per month** "
              f"(from {t['n']} measured full triage run(s); the token count is measured, the price and volumes are assumptions).", ""]
    else:
        L += ["## Result", "", "**Not measured yet:** the formula above fills in once a full triage run is logged.", ""]
    life = cfg["treatments"]["life_years"]
    L += ["## Plan value horizon (avoided_per_gbp)", "",
          "Expected reactive repairs avoided over each treatment's service life, x £" + f"{cfg['costs']['reactive_repair']:.2f}"
          + ", per £ of treatment. Service lives (assumptions, typical UK ranges): "
          + ", ".join(f"{k.replace('_', ' ')} {v} years" for k, v in life.items())
          + ". Hazard is held at today's level, no discounting. A confirmed pothole is costed as one permanent repair: "
          f"£{cfg['costs']['reactive_repair']:.2f} reactive avoided / £{cfg['costs']['planned_repair']:.2f} planned = "
          f"×{cfg['costs']['reactive_repair'] / cfg['costs']['planned_repair']:.2f} (ALARM 2025).", ""]
    L += ["## Not measured (config assumptions)", "",
          f"- **Price:** ${pi}/M input and ${po}/M output is the Gemini 2.5 Flash paid-tier list price, applied to every model. "
          f"Triage falls back through {', '.join(f'`{m}`' for m in cfg['triage'].get('models') or [cfg['triage']['model']])}; "
          "the table shows which model answered each call. None of their prices has been checked, so confirm each on "
          "ai.google.dev/pricing before quoting the £ figure.",
          f"- **Volume:** {c['reports_per_month']} reports a month city-wide (about 3,600 Southampton pothole repairs a year, FOI 2021-2025) "
          f"shared by {c['officers']} officers. Both are assumptions.",
          f"- **Hosting:** £{c['hosting_gbp_per_month']} a month for one small VM running the API and page. Assumption.",
          "- **The weekly plan uses no LLM**, so it adds no token cost.",
          "- **The free tier** costs nothing but is rate-limited (5 requests a minute; a live run hit the daily quota on 17 Oct) "
          "and may use prompts to improve Google's products, so only public reports and synthetic data are sent.", ""]
    p = I.resolve(cfg, "reports_dir", root) / "cost.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L), encoding="utf-8")
    return p


def write_triage_report(res: dict, cfg: dict | None = None, root: Path | None = None) -> Path:
    """Triage against the keyword baseline, appended to reports/cost.md's folder as triage_vs_keywords.md."""
    cfg = cfg or I.load_config()
    L = ["# Report triage against a keyword baseline", "",
         f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `python -m roadsense.agent.triage`._", "",
         f"{res['n']} real Southampton FixMyStreet reports, title text only ({res['labels']}). Labels: "
         "`roadsense/agent/eval/triage_labels.csv`, hand-labelled by Claude Code from the titles (pothole = defect in the "
         "carriageway surface; other = pavement, kerb, drain, cycle path, flooding or unclear). A teammate should spot-check them. "
         "The pull holds road-surface categories only, so there are no streetlight reports in the sample.", "",
         "| Method | Accuracy | Recall per class |", "| --- | --- | --- |"]
    for name in ["keyword_baseline", "gemini"]:
        if name in res:
            r = res[name]
            L.append(f"| {name.replace('_', ' ')} | {r['accuracy']:.2f} | "
                     + ", ".join(f"{k} {v:.2f}" for k, v in r["per_class_recall"].items()) + " |")
    if "gemini" not in res:
        L += ["", "Gemini has not been run yet (no `GEMINI_API_KEY`). Only the baseline is shown."]
    else:
        L += ["", f"Gemini model {res['gemini']['model']}, mean {res['gemini']['mean_tokens_per_report']:,.0f} tokens per report.",
              "", "## Disagreements", "", "| FMS id | Title | Label | Keyword | Gemini |", "| --- | --- | --- | --- | --- |"]
        for d in res.get("disagreements", []):
            L.append(f"| {d['fms_id']} | {str(d['title']).replace('|', '/')} | {d['label']} | {d['keyword']} | {d['gemini']} |")
    p = I.resolve(cfg, "reports_dir", root) / "triage_vs_keywords.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


if __name__ == "__main__":
    path = write_cost_report()
    print(path.read_text(encoding="utf-8"))
