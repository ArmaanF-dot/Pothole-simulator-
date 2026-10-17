"""Real-label model tests on a lane-A-shaped fixture (two mock cities, fake reports, no network)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest_lane_b import small_config
from roadsense.models import real_risk
from roadsense.synthetic.mock import mock_esal, mock_segments

CFG_A = {"labels": {"snap_m": 25, "frozen_year": 2026, "windows": {
    "Southampton": {"usable": [2015, 2019], "train": [2015, 2017], "test": [2018, 2019]},
    "Brighton": {"usable": [2015, 2025], "train": [2015, 2022], "test": [2023, 2025]}}}}


def _city(cfg, name, dlon, seed):
    c = {**cfg, "seed": seed, "mock": {**cfg["mock"], "bbox": [b + (dlon if i % 2 == 0 else 0) for i, b in enumerate(cfg["mock"]["bbox"])]}}
    s = mock_segments(c)
    s["esal_day"] = mock_esal(s, c)
    s["city"] = name
    s["segment_id"] = name[:3].upper() + "-" + s["segment_id"]
    s["is_main_road"] = s["highway"].isin(["primary", "secondary", "tertiary"])
    s["bus_routes"] = (s["bus_stop"] * 2).astype(int)
    return s


@pytest.fixture(scope="module")
def world():
    cfg = small_config()
    seg = pd.concat([_city(cfg, "Southampton", 0, 1), _city(cfg, "Brighton", 1.0, 2)], ignore_index=True)
    rng = np.random.default_rng(3)
    main = seg[seg["is_main_road"]].reset_index(drop=True)
    rate = 0.02 * (1 + np.log1p(main["esal_day"].values)) * rng.lognormal(0, 0.5, len(main))   # persistent hot spots
    rows = []
    for y in range(2015, 2027):
        n = rng.poisson(rate)
        for i in np.flatnonzero(n):
            for _ in range(n[i]):
                rows.append((main.at[i, "city"], main.at[i, "segment_id"], f"{y}-03-01T10:00:00+00:00", 3.0))
    rep = pd.DataFrame(rows, columns=["city", "segment_id", "requested", "snap_dist_m"])
    return cfg, seg, rep


def test_split_windows():
    assert real_risk.split_for("Southampton", 2016, CFG_A) == "train"
    assert real_risk.split_for("Southampton", 2019, CFG_A) == "test"
    assert real_risk.split_for("Southampton", 2021, CFG_A) == "excluded"
    assert real_risk.split_for("Brighton", 2026, CFG_A) == "frozen_2026"


def test_history_features_use_earlier_years_only(world):
    _, seg, rep = world
    lab = real_risk.labels_from_reports(rep, seg, CFG_A, 25)
    t = real_risk.build_table(seg, lab)
    r = t[(t["city"] == "Southampton")].sort_values(["segment_id", "year"])
    nxt = r.groupby("segment_id")["n_reports"].shift(1)
    m = r["rep_prev1"].notna()
    assert (r.loc[m, "rep_prev1"] == nxt[m]).all()
    assert t.loc[t["year"] == 2015, "rep_prev1"].isna().all()


def test_city_weights_equalise_positive_weight(world):
    _, seg, rep = world
    t = real_risk.build_table(seg, real_risk.labels_from_reports(rep, seg, CFG_A, 25))
    w = real_risk.city_weights(t)
    pw = pd.Series(w * t["had_report"].values).groupby(t["city"].values).sum()
    assert pw.max() == pytest.approx(pw.min(), rel=1e-9)


def test_capture_metric():
    df = pd.DataFrame({"length_m": [100.0] * 10, "n_reports": [5, 0, 0, 0, 0, 0, 0, 0, 0, 5]})
    assert real_risk.capture_top_length(df, np.arange(10)[::-1]) == pytest.approx(0.5)


def test_run_end_to_end(world, tmp_path):
    cfg, seg, rep = world
    (tmp_path / "config.yaml").write_text(__import__("yaml").safe_dump(CFG_A))
    res = real_risk.run(cfg, root=tmp_path, verbose=False, inputs={"seg": seg, "labels": None, "reports": rep})
    assert set(res["cities"]) == {"Southampton", "Brighton"}
    assert set(res["loco"]) == {"Southampton", "Brighton"}
    sou = res["cities"]["Southampton"]
    assert sou["model"]["capture_top10_length"] > 0.1           # beats random length share on persistent hot spots
    assert (tmp_path / "reports" / "real_risk_eval.md").exists()


def test_waits_for_segments(tmp_path):
    res = real_risk.run(small_config(), root=tmp_path, verbose=False)
    assert "Waiting for lane A" in res["status"]


def _tiny_test_set():
    rng = np.random.default_rng(5)
    rows = []
    for y in (2018, 2019):
        for i in range(60):
            rows.append({"segment_id": f"S{i:03d}", "year": y, "length_m": float(rng.uniform(20, 200)),
                         "n_reports": int(rng.poisson(0.4 + (i < 8) * 2))})
    df = pd.DataFrame(rows)
    hot = (df["segment_id"].str[1:].astype(int) < 8).astype(float)
    scores = {"model": hot + rng.random(len(df)) * 0.5, "last_year_reports": rng.random(len(df)),
              "load_x_past_reports": rng.random(len(df))}
    return df, scores


def test_paired_bootstrap_reproducible_with_seed():
    df, scores = _tiny_test_set()
    a = real_risk.paired_bootstrap(df, scores, n=200, seed=2026)
    b = real_risk.paired_bootstrap(df, scores, n=200, seed=2026)
    c = real_risk.paired_bootstrap(df, scores, n=200, seed=7)
    assert a == b
    assert a["model"]["ci95"] != c["model"]["ci95"]
    lo, hi = a["model"]["ci95"]
    assert lo <= a["model"]["capture_top10_length"] <= hi
    assert a["_n"] == {"reports": int(df["n_reports"].sum()), "segments": 60, "rows": 120, "years": [2018, 2019],
                       "resamples": 200, "seed": 2026}
    assert 0 <= a["_diff_model_minus_last_year"]["share_model_ahead"] <= 1
    assert a["_diff_model_minus_last_year"]["ci95"][0] > 0          # the planted hot spots are found


def test_summary_sentence_says_matches_when_interval_spans_zero():
    r = {"model": {"capture_top10_length": 0.38, "ci95": [0.30, 0.45]},
         "last_year_reports": {"capture_top10_length": 0.34, "ci95": [0.25, 0.39]},
         "_diff_model_minus_last_year": {"point": 0.04, "ci95": [-0.03, 0.11], "share_model_ahead": 0.85},
         "_n": {"reports": 381}}
    s = real_risk.summary_sentence("Southampton", r, "test years")
    assert "matches the baseline rather than beats it" in s and "85%" in s
