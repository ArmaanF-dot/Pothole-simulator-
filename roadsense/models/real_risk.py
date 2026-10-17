"""Real-label "where" model on FixMyStreet reports from several port cities (M5, real data).

Follows lane A's schema (schemas.md) and agreed windows (config.yaml: labels.windows):
row = main-road segment x year, label had_report, features use only earlier years.
Pooled across cities with city as a categorical feature, and sample weights so each city
contributes equal total positive weight. Validated per city on its test years and
leave-one-city-out; scored as lane A agreed: share of a year's reports that fall on the top
10% of road length, against last-year's-reports and load x past-reports baselines, with a
bootstrap range. The 2026 (Jan-Oct) "frozen model" check trains on everything up to 2025.

Usage: python -m roadsense.models.real_risk [--root PATH]
FixMyStreet counts measure reporting, not true pothole rates, so scores rank segments
within a city and year and are never compared as raw totals across cities.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from roadsense.synthetic.common import ROOT, load_config, neighbours, resolve, to_xy

MODEL_VERSION = "real-risk-v0.1"
HIGHWAY_CODE = {"primary": 3, "primary_link": 3, "trunk": 4, "trunk_link": 4, "secondary": 2, "secondary_link": 2,
                "tertiary": 1, "tertiary_link": 1}
STATIC = ["log_esal_day", "log_hgv_bus_aadf", "bus_routes", "bus_stop", "junction", "in_flood_area", "length_m", "highway_code",
          "is_main_road"]
HISTORY = ["rep_prev1", "rep_prev2_3", "rep_nb_prev1", "rep_prev1_per_km"]
FEATURES = STATIC + HISTORY + ["city_code"]
MONOTONE = {"log_esal_day": 1, "log_hgv_bus_aadf": 1}
TOP_LENGTH_FRAC = 0.10


def lane_a_config(root: Path) -> dict:
    p = root / "config.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


# --- inputs ---------------------------------------------------------------------------------
def load_inputs(root: Path) -> dict | None:
    proc = root / "data" / "processed"
    seg_p = proc / "segments.parquet"
    if not seg_p.exists():
        return None
    seg = pd.read_parquet(seg_p)
    seg["segment_id"] = seg["segment_id"].astype(str)
    load_p = proc / "load.parquet"
    if load_p.exists() and "esal_day" not in seg:
        ld = pd.read_parquet(load_p)
        ld["segment_id"] = ld["segment_id"].astype(str)
        seg = seg.merge(ld[[c for c in ["segment_id", "esal_day", "hgv_bus_aadf", "load_source"] if c in ld]], on="segment_id", how="left")
    lab_p = proc / "labels_segment_year.csv"
    labels = pd.read_csv(lab_p) if lab_p.exists() else None
    reports = None
    for p in [proc / "fms_snapped.csv", proc / "fms_roads_clean.csv"]:
        if p.exists():
            reports = pd.read_csv(p)
            reports.attrs["path"] = str(p.relative_to(root))
            break
    return {"seg": seg, "labels": labels, "reports": reports}


def snap_reports(reports: pd.DataFrame, seg: pd.DataFrame, radius_m: float) -> pd.DataFrame:
    """segment_id of the nearest segment (same city) within radius_m, else blank."""
    if "segment_id" in reports and "snap_dist_m" in reports:
        r = reports.copy()
        r.loc[r["snap_dist_m"] > radius_m, "segment_id"] = np.nan
        return r
    from roadsense.models.risk import snap
    r = reports.copy()
    r["segment_id"] = np.nan
    for city, g in r.groupby("city"):
        s = seg[seg["city"] == city].reset_index(drop=True)
        if s.empty:
            continue
        j = snap(g, s, radius_m)
        r.loc[g.index[j >= 0], "segment_id"] = s["segment_id"].values[j[j >= 0]]
    return r


def labels_from_reports(reports: pd.DataFrame, seg: pd.DataFrame, cfg_a: dict, radius_m: float) -> pd.DataFrame:
    r = snap_reports(reports, seg, radius_m)
    r["year"] = pd.to_datetime(r["requested"], utc=True, format="mixed").dt.year
    cnt = r.dropna(subset=["segment_id"]).groupby(["segment_id", "year"]).size().rename("n_reports")
    main = seg[seg.get("is_main_road", True)] if "is_main_road" in seg else seg
    windows = cfg_a.get("labels", {}).get("windows", {})
    rows = []
    for city, g in main.groupby("city"):
        w = windows.get(city)
        yrs = sorted(r.loc[r["city"] == city, "year"].unique()) if w is None else range(w["usable"][0], w["usable"][1] + 1)
        frozen = cfg_a.get("labels", {}).get("frozen_year")
        yrs = list(yrs) + ([frozen] if frozen and frozen not in yrs else [])
        for y in yrs:
            rows.append(pd.DataFrame({"city": city, "segment_id": g["segment_id"].values, "year": y}))
    lab = pd.concat(rows, ignore_index=True)
    lab["n_reports"] = lab.set_index(["segment_id", "year"]).index.map(cnt).fillna(0).astype(int)
    lab["had_report"] = (lab["n_reports"] > 0).astype(int)
    lab["split"] = [split_for(c, y, cfg_a) for c, y in zip(lab["city"], lab["year"])]
    return lab


def split_for(city: str, year: int, cfg_a: dict) -> str:
    lc = cfg_a.get("labels", {})
    if year == lc.get("frozen_year"):
        return "frozen_2026"
    w = lc.get("windows", {}).get(city)
    if w is None:
        return "train"
    if not (w["usable"][0] <= year <= w["usable"][1]):
        return "excluded"
    if w.get("test") and w["test"][0] <= year <= w["test"][1]:
        return "test"
    return "train"


# --- table ----------------------------------------------------------------------------------
def build_table(seg: pd.DataFrame, labels: pd.DataFrame, nb_radius_m: float = 220.0) -> pd.DataFrame:
    """Segment-year rows; history features use only the segment's earlier years."""
    seg = seg.copy()
    if "city" not in seg:
        seg["city"] = "Southampton"
    s = pd.DataFrame({
        "segment_id": seg["segment_id"].values, "city": seg["city"].values,
        "log_esal_day": np.log1p(seg["esal_day"].astype(float).values) if "esal_day" in seg else np.nan,
        "log_hgv_bus_aadf": np.log1p(seg["hgv_bus_aadf"].astype(float).values) if "hgv_bus_aadf" in seg else np.nan,
        "bus_routes": seg["bus_routes"].astype(float).values if "bus_routes" in seg else np.nan,
        "bus_stop": seg["bus_stop"].astype(float).values if "bus_stop" in seg else np.nan,
        "junction": seg["junction"].astype(float).values if "junction" in seg else np.nan,
        "in_flood_area": seg["in_flood_area"].astype(float).values if "in_flood_area" in seg else np.nan,
        "length_m": seg["length_m"].astype(float).values,
        "highway_code": seg["highway"].map(HIGHWAY_CODE).fillna(0).astype(float).values,
        "is_main_road": seg["is_main_road"].astype(float).values if "is_main_road" in seg else np.nan,
    })
    lab = labels[labels["split"] != "excluded"].drop(columns=["is_main_road"], errors="ignore").copy()
    lab["segment_id"] = lab["segment_id"].astype(str)
    piv = lab.pivot_table(index="segment_id", columns="year", values="n_reports", aggfunc="sum")
    # neighbour sums per city (graph-neighbour proxy: midpoints within nb_radius_m)
    nb_map = {}
    for city, g in seg.groupby("city"):
        g = g.reset_index(drop=True)
        nbs = neighbours(g, nb_radius_m)
        ids = g["segment_id"].values
        for i, sid in enumerate(ids):
            nb_map[sid] = ids[nbs[i]]
    df = lab.merge(s, on=["segment_id", "city"], how="left")

    # k-th earlier labelled year for that city (the frozen 2026 year looks back to the last usable year)
    city_years = lab.groupby("city")["year"].apply(lambda s: sorted(s.unique())).to_dict()

    def earlier(city, y, k):
        ys = [x for x in city_years.get(city, []) if x < y]
        return ys[-k] if len(ys) >= k else None

    def prev(sid, city, y, k):
        e = earlier(city, y, k)
        if sid not in piv.index or e is None:
            return np.nan
        return piv.at[sid, e]

    keys = list(zip(df["segment_id"], df["city"], df["year"]))
    df["rep_prev1"] = [prev(a, c, y, 1) for a, c, y in keys]
    p2 = np.array([prev(a, c, y, 2) for a, c, y in keys], float)
    p3 = np.array([prev(a, c, y, 3) for a, c, y in keys], float)
    df["rep_prev2_3"] = np.where(np.isnan(p2) & np.isnan(p3), np.nan, np.nan_to_num(p2) + np.nan_to_num(p3))
    nb_vals = []
    for a, c, y in keys:
        e = earlier(c, y, 1)
        if e is None:
            nb_vals.append(np.nan)
            continue
        ids = [n for n in nb_map.get(a, []) if n in piv.index]
        nb_vals.append(float(piv.loc[ids, e].fillna(0).sum()) if ids else 0.0)
    df["rep_nb_prev1"] = nb_vals
    df["rep_prev1_per_km"] = df["rep_prev1"] / (df["length_m"] / 1000.0)
    df["city_code"] = pd.Categorical(df["city"])
    return df


# --- scoring --------------------------------------------------------------------------------
def capture_top_length(df: pd.DataFrame, score: np.ndarray, frac: float = TOP_LENGTH_FRAC) -> float:
    """Share of reports that fall on the top `frac` of road length ranked by score (one city-year)."""
    total = df["n_reports"].sum()
    if total == 0:
        return float("nan")
    jitter = 1e-9 * np.random.default_rng(0).random(len(df))
    o = np.argsort(-(np.asarray(score, float) + jitter))
    L = df["length_m"].values[o]
    take = np.cumsum(L) <= frac * L.sum()
    take[0] = True
    return float(df["n_reports"].values[o][take].sum() / total)


def bootstrap_capture(df, score, n=300, seed=0):
    rng = np.random.default_rng(seed)
    score = np.asarray(score, float)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(df), len(df))
        vals.append(capture_top_length(df.iloc[i], score[i]))
    v = np.array([x for x in vals if x == x])
    return (float(np.percentile(v, 5)), float(np.percentile(v, 95))) if len(v) else (float("nan"), float("nan"))


def baseline_scores(df: pd.DataFrame) -> dict:
    last = df["rep_prev1"].fillna(0).values
    load = np.expm1(df["log_esal_day"].fillna(df["log_esal_day"].median() if df["log_esal_day"].notna().any() else 0)).values
    return {"last_year_reports": last, "load_x_past_reports": (1 + load) * (1 + last + df["rep_prev2_3"].fillna(0).values)}


def city_weights(df: pd.DataFrame) -> np.ndarray:
    """Weight each row so every city's positives sum to the same total."""
    pos = df.groupby("city")["had_report"].sum()
    target = pos[pos > 0].mean() if (pos > 0).any() else 1.0
    f = (target / pos.replace(0, np.nan)).fillna(1.0)
    return df["city"].map(f).values.astype(float)


def fit(train: pd.DataFrame, cfg: dict):
    import lightgbm as lgb
    params = dict(cfg["risk"]["lgbm"])
    params.update(objective="binary", monotone_constraints=[MONOTONE.get(f, 0) for f in FEATURES],
                  random_state=cfg["seed"], deterministic=True, force_row_wise=True, n_jobs=4,
                  min_child_samples=min(params.get("min_child_samples", 20), max(5, len(train) // 50)))
    m = lgb.LGBMClassifier(**params)
    m.fit(train[FEATURES], train["had_report"].values, sample_weight=city_weights(train))
    return m


def evaluate(model, test: pd.DataFrame) -> dict:
    """Mean capture over the test city-years, for the model and both baselines."""
    out = {}
    scorers = {"model": model.predict_proba(test[FEATURES])[:, 1], **baseline_scores(test)}
    for name, s in scorers.items():
        caps, lo, hi = [], [], []
        for (_, _), idx in test.groupby(["city", "year"]).groups.items():
            ii = test.index.get_indexer(idx)
            sub = test.iloc[ii]
            if sub["n_reports"].sum() == 0:
                continue
            caps.append(capture_top_length(sub, s[ii]))
            b = bootstrap_capture(sub, s[ii], n=200)
            lo.append(b[0]); hi.append(b[1])
        out[name] = {"capture_top10_length": float(np.mean(caps)) if caps else float("nan"),
                     "range_90": [float(np.mean(lo)) if lo else float("nan"), float(np.mean(hi)) if hi else float("nan")],
                     "city_years": len(caps)}
    out["_n"] = {"rows": int(len(test)), "reports": int(test["n_reports"].sum())}
    return out


def run(cfg: dict | None = None, root: Path | None = None, verbose: bool = True, inputs: dict | None = None) -> dict:
    cfg = cfg or load_config()
    root = Path(root or ROOT)
    cfg_a = lane_a_config(root)
    inp = inputs or load_inputs(root)
    rd = resolve(cfg, "reports_dir", root)
    rd.mkdir(parents=True, exist_ok=True)
    if inp is None:
        msg = "Waiting for lane A: data/processed/segments.parquet is not on this branch yet."
        if verbose:
            print(msg)
        return {"status": msg}
    seg = inp["seg"]
    if "city" not in seg:
        seg["city"] = "Southampton"
    radius = cfg_a.get("labels", {}).get("snap_m", 25)
    labels = inp["labels"] if inp.get("labels") is not None else labels_from_reports(inp["reports"], seg, cfg_a, radius)
    table = build_table(seg, labels)
    usable = table[table["rep_prev1"].notna()]
    res = {"cities": {}, "loco": {}, "frozen_2026": None}
    train = usable[usable["split"] == "train"]
    model = fit(train, cfg)
    for city in sorted(usable["city"].unique()):
        te = usable[(usable["city"] == city) & (usable["split"] == "test")]
        if len(te):
            res["cities"][city] = evaluate(model, te.reset_index(drop=True))
    if usable["city"].nunique() >= 2:
        for city in sorted(usable["city"].unique()):
            tr = usable[(usable["city"] != city) & usable["split"].isin(["train", "test"])]
            te = usable[(usable["city"] == city) & usable["split"].isin(["train", "test"])]
            if tr["had_report"].sum() and te["n_reports"].sum():
                res["loco"][city] = evaluate(fit(tr, cfg), te.reset_index(drop=True))
    fz = usable[usable["split"] == "frozen_2026"]
    if len(fz) and fz["n_reports"].sum():
        full = fit(usable[usable["split"].isin(["train", "test"])], cfg)
        res["frozen_2026"] = {c: evaluate(full, g.reset_index(drop=True)) for c, g in fz.groupby("city")}
    md = resolve(cfg, "models_dir", root)
    md.mkdir(parents=True, exist_ok=True)
    (md / "real_risk_eval.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    write_report(rd / "real_risk_eval.md", res, table, radius, inp)
    if verbose:
        print(json.dumps({c: {k: v["capture_top10_length"] for k, v in r.items() if not k.startswith("_")} for c, r in res["cities"].items()}, indent=1))
    return res


def write_report(path: Path, res: dict, table: pd.DataFrame, radius, inp):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    src = inp["reports"].attrs.get("path") if inp.get("reports") is not None else "data/processed/labels_segment_year.csv"
    L = ["# Real-label risk model (FixMyStreet, real data)", "",
         f"_Generated {now} by `python -m roadsense.models.real_risk` ({MODEL_VERSION})._", "",
         f"Labels: real FixMyStreet road-surface reports (`{src}`), snapped to main-road segments within {radius} m. "
         "Counts measure reporting, not pothole rates; scores rank segments within one city and year.", "",
         "Score: share of that year's reports on the top 10% of road length (mean over test city-years, 90% bootstrap range).", ""]

    def table_md(r):
        rows = ["| Scorer | Capture, top 10% of length | 90% range |", "|---|---|---|"]
        for name in ["model", "last_year_reports", "load_x_past_reports"]:
            if name in r:
                v = r[name]
                rows.append(f"| {name.replace('_', ' ')} | {v['capture_top10_length']:.3f} | {v['range_90'][0]:.3f} to {v['range_90'][1]:.3f} |")
        return rows + [f"", f"{r['_n']['reports']:,} reports on {r['_n']['rows']:,} segment-years.", ""]

    for title, block in [("Test years per city (pooled model)", res["cities"]), ("Leave-one-city-out", res["loco"]),
                         ("Frozen 2026 check (Jan to Oct, small)", res["frozen_2026"] or {})]:
        L += [f"## {title}", ""]
        if not block:
            L += ["Not run (not enough cities or reports).", ""]
        for c, r in block.items():
            L += [f"### {c}", ""] + table_md(r)
    path.write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None)
    run(root=ap.parse_args().root)


if __name__ == "__main__":
    main()
