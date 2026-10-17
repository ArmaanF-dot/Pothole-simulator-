"""Score every segment and build the weekly prevention plan (M6).

    python -m roadsense.prevent.plan [--forecast-as-of 2026-10-10T06:00] [--scenario rain_then_frost]

Writes outputs/prevention_plan_<as_of>.csv: segments in the 40-69 prevention band whose p30 is
forecast to rise, ranked by expected reactive cost avoided per £ of treatment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from roadsense.prevent import inputs as I
from roadsense.prevent import treatments as T
from roadsense.prevent import urgency as U

P30_WEEKS = ["p30_w0", "p30_w1", "p30_w2", "p30_w3"]


def freshness(cfg: dict, forecast_meta: dict, forecast_as_of: str | None = None, now: datetime | None = None) -> dict:
    """STALE when the forecast is older than max_forecast_age_h; provisional when stale or missing."""
    now = now or datetime.now(timezone.utc)
    ra = forecast_as_of or forecast_meta.get("retrieved_at")
    if not ra:
        return {"forecast_retrieved_at": None, "forecast_age_h": None, "stale": False, "provisional": True,
                "message": "No live forecast yet: weeks 1-3 use 10-year weekly climatology. Plan is provisional."}
    t = pd.Timestamp(ra)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    age = (pd.Timestamp(now) - t).total_seconds() / 3600
    stale = age > cfg["plan"]["max_forecast_age_h"]
    return {"forecast_retrieved_at": t.isoformat(), "forecast_age_h": round(age, 1), "stale": bool(stale),
            "provisional": bool(stale),
            "message": (f"STALE: forecast retrieved {age:.0f} h ago (limit {cfg['plan']['max_forecast_age_h']} h). "
                        "Plan is provisional.") if stale else f"Forecast retrieved {age:.0f} h ago."}


def score(seg: pd.DataFrame, risk: pd.DataFrame, cfg: dict, feedback: dict | None = None) -> pd.DataFrame:
    """One row per segment (council and National Highways) with urgency, band and treatment.

    feedback: {segment_id: {"confirmed_open": bool, "cracking": bool, "p30_multiplier": float}}
    from approved work orders and crew outcomes. National Highways roads are kept but never scored.
    """
    feedback = feedback or {}
    keep = [c for c in ["segment_id", "osm_way_id", "name", "highway", "ward", "length_m", "lat", "lon", "geometry",
                        "owner", "bus_stop", "junction", "in_flood_area", "esal_day", "esal_confidence",
                        "cycle_route", "near_school_hospital", "bus_route", "bus_departures", "input_source"] if c in seg]
    df = seg[keep].merge(risk.drop(columns=[c for c in ["ward"] if c in risk and "ward" in seg]),
                         on="segment_id", how="left")
    nh = (df["owner"] == "national_highways") | (df["highway"] == "motorway")
    df["scored"] = ~nh & df["p30"].notna()
    for c in P30_WEEKS:
        if c not in df:
            df[c] = df["p30"]
    mult = df["segment_id"].map(lambda s: feedback.get(s, {}).get("p30_multiplier", 1.0)).astype(float)
    for c in ["p30"] + P30_WEEKS:
        df[c] = (df[c] * mult).clip(upper=0.999)
    df["confirmed_open"] = df["segment_id"].map(lambda s: bool(feedback.get(s, {}).get("confirmed_open", False)))
    df["cracking"] = df["segment_id"].map(lambda s: bool(feedback.get(s, {}).get("cracking", False)))
    df["consequence"], df["consequence_text"] = U.consequence(df, cfg)
    df["urgency"] = U.urgency(df["p30"], df["wear_pct"], df["consequence"], cfg, df["confirmed_open"])
    # an approved, not yet inspected report holds the segment at least at the report floor
    floor = df["segment_id"].map(lambda s: feedback.get(s, {}).get("urgency_floor", 0)).astype(float)
    df["urgency"] = np.maximum(df["urgency"], floor)
    df["band"] = U.band(df["urgency"], cfg)
    df.loc[~df["scored"], ["urgency", "band"]] = [np.nan, None]
    df["p30_peak"] = df[P30_WEEKS].max(axis=1)
    df["p30_rise"] = df[P30_WEEKS[1:]].max(axis=1) - df["p30_w0"]
    df["treatment"] = T.choose(df["wear_pct"], df["cracking"], df["confirmed_open"], cfg)
    df.loc[~df["scored"], "treatment"] = None
    df["treatment_label"] = df["treatment"].map(cfg["treatments"]["label"])
    df["treatment_cost_gbp"] = T.treatment_cost(df["treatment"], df["length_m"], df["highway"], cfg)
    df["expected_repairs_avoided"] = T.expected_avoided(df[P30_WEEKS].mean(axis=1), df["treatment"], cfg)
    df["reactive_cost_avoided_gbp"] = (df["expected_repairs_avoided"] * cfg["costs"]["reactive_repair"]).round(2)
    df["avoided_per_gbp"] = (df["reactive_cost_avoided_gbp"] / df["treatment_cost_gbp"]).round(4)
    df["traffic_note"] = np.where(df["esal_confidence"].eq("count"), "DfT count on this road",
                                  "modelled estimate, low confidence")
    df["status"] = np.where(nh, "National Highways road, not scored",
                            np.where(df["p30"].isna(), "no risk score", "scored"))
    return df


def build_plan(scored: pd.DataFrame, cfg: dict, ward: str | None = None) -> pd.DataFrame:
    p = scored[scored["scored"] & (scored["band"] == "prevention") & (scored["p30_rise"] > cfg["plan"]["min_rise"])]
    if ward:
        p = p[p["ward"] == ward]
    p = p.sort_values(["avoided_per_gbp", "urgency"], ascending=False).head(cfg["plan"]["top_n"]).copy()
    p.insert(0, "rank", np.arange(1, len(p) + 1))
    c = cfg["costs"]
    p["reasons"] = [" · ".join(x for x in [r.get("reason_1"), r.get("reason_2"), r.get("reason_3")] if isinstance(x, str))
                    for r in p.to_dict("records")]
    p["cost_logic"] = [
        (f"P30 {r['p30_w0']:.3f} now, peak {r['p30_peak']:.3f} in 4 weeks; "
         f"{r['treatment_label'].lower()} cuts hazard to x{cfg['treatments']['hazard_multiplier'].get(r['treatment'], 1)} "
         f"for {cfg['treatments']['benefit_years']} years = {r['expected_repairs_avoided']:.2f} reactive repairs avoided "
         f"x £{c['reactive_repair']:.2f} = £{r['reactive_cost_avoided_gbp']:.2f} for £{r['treatment_cost_gbp']:.2f} "
         f"(treatment £/m² is an assumption; planned repair £{c['planned_repair']:.2f} vs reactive £{c['reactive_repair']:.2f}, {c['source']})")
        for r in p.to_dict("records")]
    return p


PLAN_COLS = ["rank", "segment_id", "name", "ward", "highway", "urgency", "band", "wear_pct", "p30_w0", "p30_peak",
             "p30_rise", "consequence", "consequence_text", "treatment", "treatment_label", "treatment_cost_gbp",
             "reactive_cost_avoided_gbp", "avoided_per_gbp", "reasons", "cost_logic", "esal_day", "traffic_note",
             "weather_source", "model_version", "as_of", "labels_synthetic", "wear_synthetic", "inputs_mock"]


def run(cfg: dict | None = None, root: Path | None = None, forecast_as_of: str | None = None,
        scenario: str | None = None, feedback: dict | None = None, write: bool = True, verbose: bool = True) -> dict:
    cfg = cfg or I.load_config()
    seg, seg_meta = I.load_segments(cfg, root)
    risk, risk_meta = I.load_risk(cfg, root)
    if scenario:
        from roadsense.prevent.whatif import apply_scenario
        risk = apply_scenario(risk, seg, scenario, cfg, root=root)
    sc = score(seg, risk, cfg, feedback)
    plan = build_plan(sc, cfg)
    fresh = freshness(cfg, I.load_forecast_meta(cfg, root), forecast_as_of)
    plan["provisional"] = fresh["provisional"]
    out = None
    if write:
        od = I.resolve(cfg, "outputs_dir", root)
        od.mkdir(parents=True, exist_ok=True)
        tag = f"_{scenario}" if scenario else ""
        out = od / f"prevention_plan_{risk_meta['as_of']}{tag}.csv"
        plan[[c for c in PLAN_COLS + ["provisional"] if c in plan]].to_csv(out, index=False, encoding="utf-8-sig")
    if verbose:
        n = sc["scored"].sum()
        print(f"scored {n:,} segments ({seg_meta['kind']} segments, {risk_meta['kind']} risk as of {risk_meta['as_of']})")
        print("bands: " + ", ".join(f"{b} {int((sc['band'] == b).sum()):,}" for b in U.BAND_ORDER))
        print(f"prevention plan: {len(plan)} segments{'' if not scenario else f' under {scenario}'}; {fresh['message']}")
        if out:
            print(f"wrote {out}")
    return {"scored": sc, "plan": plan, "freshness": fresh, "path": out, "meta": [seg_meta, risk_meta]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None)
    ap.add_argument("--forecast-as-of", default=None, help="pretend the forecast was retrieved at this time")
    ap.add_argument("--scenario", default=None, choices=["rain_then_frost", "wet_week", "cold_snap"])
    a = ap.parse_args()
    run(root=Path(a.root) if a.root else None, forecast_as_of=a.forecast_as_of, scenario=a.scenario)


if __name__ == "__main__":
    main()
