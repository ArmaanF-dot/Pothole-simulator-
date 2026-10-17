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
    for kind in ["triage", "weekly_plan"]:
        k = log[log["kind"] == kind]
        if len(k):
            inp = k["prompt_tokens"].mean()
            outp = (k["output_tokens"] + k["thoughts_tokens"].fillna(0)).mean()
            per[kind] = {"n": len(k), "input_tokens": float(inp), "output_tokens": float(outp),
                         "gbp": float(inp * price_in + outp * price_out)}
    out["per_item"] = per
    if "triage" in per:
        tri = per["triage"]["gbp"] * c["reports_per_month"] / c["officers"]
        plan = per.get("weekly_plan", {"gbp": 0.0})["gbp"] * c["plans_per_officer_per_month"]
        host = c["hosting_gbp_per_month"] / c["officers"]
        out.update(llm_gbp_per_officer_month=tri + plan, hosting_gbp_per_officer_month=host,
                   total_gbp_per_officer_month=tri + plan + host)
    return out


def write_cost_report(cfg: dict | None = None, root: Path | None = None) -> Path:
    cfg = cfg or I.load_config()
    log = read_log(cfg, root)
    r = compute(cfg, log)
    c = cfg["cost"]
    L = ["# Running cost per officer", "",
         f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `python -m roadsense.agent.cost` "
         "from the token log (`outputs/lane_c/token_log.jsonl`). Token counts are what the Gemini API reported "
         "(`usage_metadata`), not estimates._", ""]
    if "triage" not in r["per_item"]:
        L += ["**No live Gemini calls logged yet**, so there is no measured cost. Add `GEMINI_API_KEY` to `.env`, then run "
              "`python -m roadsense.agent.triage` (100 real reports) and `python -m roadsense.agent.cost`.", ""]
    else:
        L += ["| Item | Calls logged | Mean input tokens | Mean output tokens (incl. thinking) | £ per item |",
              "| --- | --- | --- | --- | --- |"]
        for k, v in r["per_item"].items():
            L.append(f"| {k.replace('_', ' ')} | {v['n']} | {v['input_tokens']:,.0f} | {v['output_tokens']:,.0f} | £{v['gbp']:.5f} |")
        L += ["", f"**£{r['total_gbp_per_officer_month']:.2f} per officer per month**: "
              f"LLM £{r['llm_gbp_per_officer_month']:.2f} + hosting £{r['hosting_gbp_per_officer_month']:.2f}.", ""]
    L += ["## Assumptions (config, not measured)", "",
          f"- Price: ${c['price_per_mtok_usd']['input']}/M input and ${c['price_per_mtok_usd']['output']}/M output tokens "
          f"({cfg['triage']['model']} paid tier; check ai.google.dev/pricing), ${1}=£{c['usd_to_gbp']}.",
          f"- Volume: {c['reports_per_month']} reports a month city-wide (about 3,600 Southampton pothole repairs a year, "
          f"FOI 2021-2025), shared by {c['officers']} officers; {c['plans_per_officer_per_month']} weekly plans per officer a month.",
          f"- Hosting: £{c['hosting_gbp_per_month']} a month for one small VM running the API and page, shared by all officers.",
          "- The weekly plan itself is computed without an LLM; only report triage calls Gemini.",
          "- The free tier costs nothing but may use prompts to improve Google's products, so only public reports and "
          "synthetic data are sent.", ""]
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
