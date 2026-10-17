"""Uncertainty for the LIVE real-label model (the one that ranks the plan), without retraining.

Rerun:  python -m roadsense.models.eval_ci
Reads data/models/real_risk_model.txt (+ .json) as saved by roadsense.models.plan_risk and lane A's
data/processed files; writes the "eval-ci" section of reports/risk_eval.md and
data/models/eval_ci.json. Touches no risk, plan or app output.

Resampling unit: wards (cluster bootstrap). Reports and risk cluster in space (neighbouring segments
share traffic, history and who reports), so resampling single segments or weeks would treat
correlated roads as independent and understate the noise; resampling whole wards keeps that.

Caveat (stated in the report): the live model was fitted on every usable year, including the
Southampton 2018-19 and Brighton 2023-25 test years, so on those years it is an in-sample score.
The held-out numbers are the "Real-label evaluation" tables above. 2026 is out of sample.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from roadsense.models import real_risk as rr
from roadsense.synthetic.common import ROOT, load_config, resolve

SEED, N_BOOT = 2026, 1000
SECTION_START, SECTION_END = "<!-- eval-ci:start -->", "<!-- eval-ci:end -->"
PLAIN = {
    "rep_prev1": "Potholes reported on this road last year",
    "rep_prev2_3": "Potholes reported on this road in the two years before that",
    "rep_nb_prev1": "Potholes reported on the neighbouring roads last year",
    "rep_prev1_per_km": "How dense last year's reports were along this road",
    "length_m": "Length of the road segment (longer pieces have more surface to fail)",
    "log_esal_day": "Heavy axle load (HGVs and buses wear roads fastest)",
    "log_hgv_bus_aadf": "Daily HGV and bus traffic",
    "bus_routes": "Number of bus routes using the road",
    "bus_stop": "Bus stop on the segment (braking and pulling away)",
    "junction": "Busy junction (turning and braking)",
    "in_flood_area": "Inside an Environment Agency flood zone",
    "highway_code": "Road class (A road, B road, minor road)",
    "is_main_road": "Main road (A or B road)",
    "wx_rain_30d_mean": "How wet the area was last year",
    "wx_freeze_thaw": "Freeze-thaw cycles in the area last year",
    "wx_frost_hours": "Frost hours in the area last year",
    "wx_rain_then_frost": "Rain followed by frost in the area last year",
    "wx_hot_days": "Hot days in the area last year",
    "city_code": "Which city (reporting habits differ between cities)",
}


def load_live_model(root: Path):
    import lightgbm as lgb
    md = root / "data" / "models"
    booster = lgb.Booster(model_str=(md / "real_risk_model.txt").read_text(encoding="utf-8").replace("\r\n", "\n"))
    meta = json.loads((md / "real_risk_model.json").read_text(encoding="utf-8"))
    return booster, meta


def score_rows(booster, meta, rows: pd.DataFrame) -> np.ndarray:
    X = rows[meta["features"]].copy()
    X["city_code"] = pd.Categorical(rows["city"], categories=meta["city_categories"])
    return booster.predict(X)


def mean_capture(df: pd.DataFrame, s: np.ndarray) -> float:
    caps = []
    for y in sorted(df["year"].unique()):
        m = (df["year"] == y).values
        c = rr.capture_top_length(df[m], s[m])
        if c == c:
            caps.append(c)
    return float(np.mean(caps)) if caps else float("nan")


def ward_bootstrap(df: pd.DataFrame, scores: dict, n: int = N_BOOT, seed: int = SEED) -> dict:
    """Paired cluster bootstrap over wards: model and baseline scored on the same resampled wards."""
    df = df.reset_index(drop=True)
    wards = df["ward"].fillna("unknown").values
    uw = np.unique(wards)
    rows_of = {w: np.flatnonzero(wards == w) for w in uw}
    point = {k: mean_capture(df, v) for k, v in scores.items()}
    rng = np.random.default_rng(seed)
    draws = {k: np.empty(n) for k in scores}
    for b in range(n):
        idx = np.concatenate([rows_of[w] for w in rng.choice(uw, size=len(uw), replace=True)])
        sub = df.iloc[idx].reset_index(drop=True)
        for k, v in scores.items():
            draws[k][b] = mean_capture(sub, v[idx])
    ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
    d = draws["model"] - draws["baseline"]
    return {"model": {"point": point["model"], "ci95": ci(draws["model"])},
            "baseline": {"point": point["baseline"], "ci95": ci(draws["baseline"])},
            "diff": {"point": point["model"] - point["baseline"], "ci95": ci(d)},
            "share_model_beats_baseline": float(np.mean(d > 0)),
            "n": {"reports": int(df["n_reports"].sum()), "segments": int(df["segment_id"].nunique()),
                  "wards": int(len(uw)), "years": [int(y) for y in sorted(df["year"].unique())],
                  "resamples": n, "seed": seed}}


def global_importance(booster, meta, rows: pd.DataFrame, k: int = 5) -> list[dict]:
    """Mean absolute SHAP value (LightGBM exact tree contributions) per feature."""
    X = rows[meta["features"]].copy()
    X["city_code"] = pd.Categorical(rows["city"], categories=meta["city_categories"])
    contrib = booster.predict(X, pred_contrib=True)[:, :-1]
    imp = np.abs(contrib).mean(axis=0)
    share = imp / imp.sum()
    order = np.argsort(-imp)[:k]
    return [{"feature": meta["features"][j], "share": float(share[j]), "plain": PLAIN.get(meta["features"][j], meta["features"][j])}
            for j in order]


def _pct(x, dp=0):
    return f"{100 * x:.{dp}f}%"


def section(res: dict) -> str:
    L = [SECTION_START, "## Live model: bootstrap ranges, 2026 check and top features", "",
         f"_Generated {res['generated_at']} by `python -m roadsense.models.eval_ci`. Scores the real-label model exactly as "
         "saved for the live plan (`data/models/real_risk_model.txt`), with no retraining._", "",
         "Metric: share of a test year's FixMyStreet reports that fall on the top 10% of road length, averaged over the test "
         "years. Baseline: rank by last year's reports. Ranges: paired cluster bootstrap over **wards** "
         f"({N_BOOT:,} resamples, seed {SEED}); reports cluster in space, so whole wards are resampled rather than single "
         "roads or weeks, which would understate the noise.", "",
         "**Caveat:** the live model was fitted on every usable year, including these test years, so the first table is an "
         "in-sample score and reads higher than a true hold-out. The held-out results are the real-label tables above; "
         "the 2026 check below is out of sample.", "",
         "### Test years (live model)", "",
         "| City | Model | Baseline (last year's reports) | Model minus baseline | Model ahead | Reports / wards |",
         "|---|---|---|---|---|---|"]
    for c, r in res["test"].items():
        L.append(f"| {c} {r['n']['years'][0]}-{str(r['n']['years'][-1])[2:]} | {_pct(r['model']['point'], 1)} "
                 f"({_pct(r['model']['ci95'][0], 1)} to {_pct(r['model']['ci95'][1], 1)}) | {_pct(r['baseline']['point'], 1)} "
                 f"({_pct(r['baseline']['ci95'][0], 1)} to {_pct(r['baseline']['ci95'][1], 1)}) | {_pct(r['diff']['point'], 1)} "
                 f"({_pct(r['diff']['ci95'][0], 1)} to {_pct(r['diff']['ci95'][1], 1)}) | {_pct(r['share_model_beats_baseline'])} "
                 f"| {r['n']['reports']} / {r['n']['wards']} |")
    L += ["", "### Frozen 2026 check (January to October, out of sample)", "",
          "| City | Reports | Model | Baseline | Model minus baseline | Model ahead |", "|---|---|---|---|---|---|"]
    for c, r in res["frozen_2026"].items():
        L.append(f"| {c} | {r['n']['reports']} | {_pct(r['model']['point'], 1)} ({_pct(r['model']['ci95'][0], 1)} to "
                 f"{_pct(r['model']['ci95'][1], 1)}) | {_pct(r['baseline']['point'], 1)} ({_pct(r['baseline']['ci95'][0], 1)} "
                 f"to {_pct(r['baseline']['ci95'][1], 1)}) | {_pct(r['diff']['point'], 1)} ({_pct(r['diff']['ci95'][0], 1)} to "
                 f"{_pct(r['diff']['ci95'][1], 1)}) | {_pct(r['share_model_beats_baseline'])} |")
    L += [""] + [f"- {s}" for s in res["frozen_sentences"]] + ["",
          "### Top 5 features (mean absolute SHAP over both cities' test rows)", ""]
    for i, f in enumerate(res["top_features"], start=1):
        L.append(f"{i}. **{f['plain']}** (`{f['feature']}`, {_pct(f['share'])} of the model's total attribution)")
    L += ["", SECTION_END]
    return "\n".join(L)


def frozen_sentence(city: str, r: dict) -> str:
    n = r["n"]["reports"]
    if n < 100:
        return (f"{city}: only {n} reports in January to October 2026, too few for this result to mean anything "
                f"(model {_pct(r['model']['point'])} vs baseline {_pct(r['baseline']['point'])}).")
    lo, hi = r["diff"]["ci95"]
    verdict = "beats" if lo > 0 else ("falls short of" if hi < 0 else "matches")
    return f"{city}: {n} reports; the model {verdict} the baseline ({_pct(r['diff']['point'])}, 95% {_pct(lo)} to {_pct(hi)})."


def update_report(path: Path, text: str):
    txt = path.read_text(encoding="utf-8")
    if SECTION_START in txt and SECTION_END in txt:
        txt = txt[:txt.index(SECTION_START)] + text + txt[txt.index(SECTION_END) + len(SECTION_END):]
    else:
        txt = txt.rstrip() + "\n\n" + text + "\n"
    path.write_text(txt, encoding="utf-8")


def run(cfg: dict | None = None, root: Path | None = None, verbose: bool = True) -> dict:
    cfg = cfg or load_config()
    root = Path(root or ROOT)
    inp = rr.load_inputs(root)
    seg = inp["seg"]
    cfg_a = rr.lane_a_config(root)
    labels = inp["labels"] if inp.get("labels") is not None else rr.labels_from_reports(
        inp["reports"], seg, cfg_a, cfg_a.get("labels", {}).get("snap_m", 25))
    table = rr.build_table(seg, labels, wx=inp.get("wx"))
    table = table[table["rep_prev1"].notna()].reset_index(drop=True)
    booster, meta = load_live_model(root)
    table["live_score"] = score_rows(booster, meta, table)
    res = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "test": {}, "frozen_2026": {}}
    for city in ["Southampton", "Brighton"]:
        for split, key in [("test", "test"), ("frozen_2026", "frozen_2026")]:
            df = table[(table["city"] == city) & (table["split"] == split)].reset_index(drop=True)
            if len(df) and df["n_reports"].sum():
                res[key][city] = ward_bootstrap(df, {"model": df["live_score"].values,
                                                     "baseline": df["rep_prev1"].fillna(0).values})
    res["frozen_sentences"] = [frozen_sentence(c, r) for c, r in res["frozen_2026"].items()]
    test_rows = table[table["city"].isin(["Southampton", "Brighton"]) & (table["split"] == "test")]
    res["top_features"] = global_importance(booster, meta, test_rows)
    rd = resolve(cfg, "reports_dir", root)
    update_report(rd / "risk_eval.md", section(res))
    (resolve(cfg, "models_dir", root) / "eval_ci.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if verbose:
        print(json.dumps({k: res[k] for k in ["test", "frozen_2026"]}, indent=1)[:3000])
        print(res["frozen_sentences"], [f["feature"] for f in res["top_features"]])
    return res


if __name__ == "__main__":
    run()
