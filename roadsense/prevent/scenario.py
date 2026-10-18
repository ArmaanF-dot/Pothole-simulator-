"""Modelled scenario: potholes with no prevention vs with preventive treatment (Southampton).

    python -m roadsense.prevent.scenario            # writes reports/prevention_scenario.md and outputs/prevention_scenario.json

THIS IS A MODELLED SCENARIO, NOT OBSERVED EVIDENCE. Nobody has measured what happens to Southampton's potholes with
and without this plan. The numbers come from:

- each segment's expected potholes a year: the risk model's lambda_year, its share of Southampton's FOI 2025 total
  (3,113 potholes) from the model trained on real FixMyStreet reports (its history input is SYNTHETIC, see
  DATA_GAPS.md), held at that level for every year (no ageing, so "no prevention" is if anything optimistic for old
  roads);
- the treatment each segment would get, which depends on SYNTHETIC wear (there is no council condition survey);
- ASSUMED treatment effects (prevent.yaml treatments.hazard_multiplier: crack sealing and surface dressing x0.6,
  patch x0.8, resurfacing x0.3) and service lives (life_years), and ASSUMED £/m2 costs;
- ALARM 2025 average reactive repair cost (£87.80) for the money avoided.

Ranges: the effect of each treatment (1 - multiplier) is scaled by 0.5 (low), 1.0 (central) and 1.25 (high, capped
so no treatment removes all risk). Pothole counts are expected values; real years scatter around them.

Scenarios over HORIZON years:
- no prevention: reactive repairs only;
- this week's plan: the 50 plan rows treated now, nothing after;
- worth treating: the Worth treating rows treated now (confirmed potholes repaired, plus roads that pay back);
- yearly budgets: each year the budget buys preventive treatment for untreated segments in order of reactive cost
  avoided per £ (the plan's ranking); a treated segment is protected for its treatment's life, then can be bought again.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HORIZON = 5
BUDGETS = [250_000, 500_000, 1_000_000, 2_000_000]
EFFECT_SCALE = {"low": 0.5, "central": 1.0, "high": 1.25}
MIN_MULT = 0.1          # high case never takes a treatment below x0.1 of today's hazard
PREVENTIVE = ["crack_sealing", "surface_dressing", "patch", "resurface"]


def yearly_hazard(scored: pd.DataFrame) -> np.ndarray:
    """Expected potholes a year per segment: the risk model's lambda_year (its yearly share of the FOI total), else
    the plan's this-month hazard x 12 (which is seasonal: an autumn p30 under-states a whole year)."""
    if "lambda_year" in scored and scored["lambda_year"].notna().any():
        return scored["lambda_year"].astype(float).fillna(0).values
    weeks = [c for c in scored.columns if c.startswith("p30_w") and c[5:].isdigit()]
    p30 = scored[weeks].mean(axis=1) if weeks else scored["p30"]
    return 12 * -np.log1p(-np.clip(p30.astype(float).values, 0, 0.999))


def _mult(treatment: pd.Series, cfg: dict, scale: float) -> np.ndarray:
    m = treatment.map(cfg["treatments"]["hazard_multiplier"]).fillna(1.0).astype(float).values
    return np.clip(1 - (1 - m) * scale, MIN_MULT, 1.0)


def simulate(h: np.ndarray, mult: np.ndarray, life: np.ndarray, cost: np.ndarray, picks_by_year: list[np.ndarray],
             horizon: int = HORIZON) -> dict:
    """Expected potholes per year when segments in picks_by_year[y] are treated at the start of year y."""
    until = np.full(len(h), -1)          # last year (inclusive) a treatment is active
    years = []
    spent = []
    for y in range(horizon):
        p = picks_by_year[y] if y < len(picks_by_year) else np.empty(0, int)
        until[p] = y + np.maximum(life[p], 1) - 1
        spent.append(float(cost[p].sum()))
        active = until >= y
        years.append(float(np.where(active, h * mult, h).sum()))
    return {"potholes_by_year": years, "spend_by_year": spent}


def budget_picks(h, mult_central, life, cost, ratio, budget: float, horizon: int = HORIZON) -> list[np.ndarray]:
    """Greedy by the plan's ranking (avoided per £), re-buying a segment only once its treatment has expired.
    Choices use the central effect so all three ranges treat the same roads."""
    order = np.argsort(-np.nan_to_num(ratio, nan=-1))
    order = order[np.isfinite(cost[order]) & (cost[order] > 0) & (ratio[order] > 0)]
    until = np.full(len(h), -1)
    out = []
    for y in range(horizon):
        free = order[until[order] < y]
        c = np.cumsum(cost[free])
        p = free[c <= budget]
        until[p] = y + np.maximum(life[p], 1) - 1
        out.append(p)
    return out


def run_scenarios(scored: pd.DataFrame, cfg: dict, plan_ids=(), worth_ids=(), horizon: int = HORIZON) -> dict:
    s = scored[scored["scored"]].reset_index(drop=True)
    h = yearly_hazard(s)
    life = s["treatment"].map(cfg["treatments"]["life_years"]).fillna(0).astype(int).values
    cost = s["treatment_cost_gbp"].astype(float).values
    ratio = s["avoided_per_gbp"].astype(float).values
    prev = s["treatment"].isin(PREVENTIVE).values
    reactive = float(cfg["costs"]["reactive_repair"])
    idx = lambda ids: np.flatnonzero(s["segment_id"].isin(set(ids)).values)
    base = float(h.sum())
    plans = {"this_week_plan": [idx(plan_ids)], "worth_treating": [idx(worth_ids)]}
    for b in BUDGETS:
        plans[f"budget_{b}"] = budget_picks(h, _mult(s["treatment"], cfg, 1.0), life,
                                            np.where(prev, cost, np.nan), np.where(prev, ratio, np.nan), b, horizon)
    out = {"no_prevention": {"label": "No prevention (reactive repairs only)", "potholes_by_year": [base] * horizon,
                             "spend_by_year": [0.0] * horizon, "segments_treated": 0}}
    labels = {"this_week_plan": "This week's plan, treated now", "worth_treating": "Worth treating list, treated now"}
    for name, picks in plans.items():
        r = {}
        for k, sc in EFFECT_SCALE.items():
            m = _mult(s["treatment"], cfg, sc)
            # a confirmed pothole on the Worth treating list is a permanent repair: one reactive repair avoided now
            if name == "worth_treating":
                m = np.where(s["treatment"].values == "permanent_repair", 1.0, m)
            r[k] = simulate(h, m, np.where(s["treatment"].values == "permanent_repair", 0, life), cost, picks, horizon)
        cen = r["central"]
        total_base = base * horizon
        row = {"label": labels.get(name) or f"£{int(name.split('_')[1]):,} a year on preventive treatment",
               "potholes_by_year": cen["potholes_by_year"], "spend_by_year": cen["spend_by_year"],
               "segments_treated": int(sum(len(p) for p in picks)),
               "range_total": {k: float(sum(v["potholes_by_year"])) for k, v in r.items()}}
        avoided = {k: total_base - v for k, v in row["range_total"].items()}
        row["avoided_total"] = avoided
        row["reactive_cost_avoided_gbp"] = {k: v * reactive for k, v in avoided.items()}
        row["spend_total_gbp"] = float(sum(cen["spend_by_year"]))
        out[name] = row
    out["no_prevention"]["range_total"] = {k: base * horizon for k in EFFECT_SCALE}
    out["no_prevention"]["avoided_total"] = {k: 0.0 for k in EFFECT_SCALE}
    return {"horizon_years": horizon, "segments": int(len(s)), "base_potholes_year": base,
            "foi_anchor": "Southampton FOI 2025: 3,113 potholes repaired (risk model's yearly total)",
            "effect_scale": EFFECT_SCALE, "budgets": BUDGETS, "scenarios": out,
            "modelled": True, "uses_synthetic": True,
            "assumptions": [
                "Expected potholes a year per segment = the risk model's share of Southampton's FOI 2025 total (3,113), from "
                "the model trained on real FixMyStreet reports (history input SYNTHETIC), held at that level every year.",
                "Treatment per segment depends on SYNTHETIC wear (no council condition survey).",
                "Treatment effects are ASSUMED hazard multipliers: crack sealing and surface dressing x0.6, patch x0.8, "
                "resurfacing x0.3; low/central/high scale the effect by 0.5/1.0/1.25.",
                "Service lives are ASSUMED: crack sealing 3, surface dressing 8, patch 5, resurfacing 15 years.",
                "Treatment £/m2 are ASSUMED placeholders; reactive repair £87.80 is the ALARM 2025 average.",
                "Expected values only: real years scatter around them (Poisson noise and weather)."]}


def report_md(r: dict, as_of: str | None = None) -> str:
    sc = r["scenarios"]
    L = ["# Potholes with and without prevention: modelled scenario (Southampton)", "",
         f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `python -m roadsense.prevent.scenario`"
         + (f", plan as of {as_of}" if as_of else "") + "._", "",
         "**This is a modelled scenario, not observed evidence.** It applies assumed treatment effects to the risk model's "
         "expected potholes. Treatment choice uses SYNTHETIC wear. Use it to compare options, not as a forecast of counts.", "",
         f"Expected potholes needing reactive repair with no prevention: **{r['base_potholes_year']:,.0f} a year** "
         f"across {r['segments']:,} council segments ({r['foi_anchor']}).", "",
         "Treatment effects in this scenario use each segment's yearly risk; the weekly plan's own payback figure uses "
         "this month's risk, which is lower in autumn, so the two are not the same number.", "",
         f"| Scenario | Potholes over {r['horizon_years']} years (central) | Range (low to high effect) | Avoided (central) | "
         "Treatment spend | Reactive cost avoided (central) |", "|---|---|---|---|---|---|"]
    for k, v in sc.items():
        rt = v["range_total"]
        L.append(f"| {v['label']} | {rt['central']:,.0f} | {max(rt['low'], rt['high']):,.0f} to {min(rt['low'], rt['high']):,.0f} | "
                 f"{v['avoided_total']['central']:,.0f} | £{v.get('spend_total_gbp', 0):,.0f} | "
                 f"£{v.get('reactive_cost_avoided_gbp', {}).get('central', 0):,.0f} |")
    L += ["", "Year by year (central, expected potholes):", "",
          "| Scenario | " + " | ".join(f"Year {i + 1}" for i in range(r["horizon_years"])) + " |",
          "|---|" + "---|" * r["horizon_years"]]
    for v in sc.values():
        L.append(f"| {v['label']} | " + " | ".join(f"{x:,.0f}" for x in v["potholes_by_year"]) + " |")
    L += ["", "## Assumptions", ""] + [f"- {a}" for a in r["assumptions"]] + [
          "", "The ranking that picks roads for the budgets is the plan's own (reactive cost avoided per £). The held-out "
          "check of that ranking against real reports is in reports/real_risk_eval.md; there is no held-out check of the "
          "treatment effects themselves, because no council treatment-outcome data is open.", ""]
    return "\n".join(L)


def main():
    from roadsense.api.service import Service
    svc = Service()
    p = svc.plan()
    r = run_scenarios(svc.scored, svc.cfg, [x["segment_id"] for x in p["rows"]],
                      [x["segment_id"] for x in p["worth"]["rows"]])
    root = Path(svc.root)
    (root / "outputs").mkdir(exist_ok=True)
    (root / "outputs" / "prevention_scenario.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    (root / "reports" / "prevention_scenario.md").write_text(report_md(r, p.get("as_of")), encoding="utf-8")
    print(report_md(r, p.get("as_of")))


if __name__ == "__main__":
    main()
