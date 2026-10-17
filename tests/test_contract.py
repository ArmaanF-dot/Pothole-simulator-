"""
Contract test: the files lanes A, B and C pass between them match schemas.md and link up.
Run at every merge:  pytest -q tests/test_contract.py
Reads the real processed files (no network). A missing file is SKIPPED, not failed, so each lane
can run it before the others have delivered; at Merge 1 nothing should be skipped.
"""
import os

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "processed")
SYN = os.path.join(ROOT, "data", "synthetic")
OUT = os.path.join(ROOT, "outputs")

SEGMENTS = ["segment_id", "city", "osm_way_id", "name", "ref", "highway", "is_main_road", "ward", "length_m",
            "lat", "lon", "bus_stop", "bus_routes", "junction", "in_flood_area", "owner", "geometry", "source",
            "cycle_route", "near_school_hospital"]
LOAD = ["segment_id", "hgv_bus_aadf", "esal_day", "count_point_id", "count_year", "load_source", "source"]
LABELS = ["city", "segment_id", "year", "n_reports", "had_report", "split"]
WEATHER = ["ward", "week_start", "rain_3d", "rain_7d", "rain_30d", "rain_90d", "hours_below_0_7d",
           "freeze_thaw_14d", "freeze_thaw_30d", "rain_then_frost_7d", "hot_days_7d", "source"]
RISK = ["segment_id", "ward", "week_start", "horizon_week", "p7", "p30", "p30_trend", "wear",
        "weather_source", "uses_synthetic", "uses_forecast"]          # lane B -> lane C (schemas.md section 7)


def load(path):
    if not os.path.exists(path):
        pytest.skip(f"not delivered yet: {os.path.relpath(path, ROOT)}")
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


@pytest.fixture(scope="module")
def seg():
    return load(os.path.join(P, "segments.parquet"))


def missing(df, cols):
    return [c for c in cols if c not in df.columns]


def test_segments_shape(seg):
    assert not missing(seg, SEGMENTS)
    assert seg.segment_id.is_unique
    assert seg.ward.notna().all(), "every segment needs a ward (weather joins on it)"
    assert set(seg.owner.unique()) <= {"council", "national_highways"}
    assert (seg.length_m > 0).all()


def test_load_links_to_segments(seg):
    ld = load(os.path.join(P, "load.parquet"))
    assert not missing(ld, LOAD)
    assert ld.segment_id.is_unique
    assert set(ld.segment_id) <= set(seg.segment_id), "load has segment_ids not in segments.parquet"
    assert ld.esal_day.notna().all() and (ld.esal_day >= 0).all()
    assert set(ld.load_source.unique()) <= {"count", "same_road", "class_median"}


def test_labels_link_to_segments(seg):
    lb = load(os.path.join(P, "labels_segment_year.csv"))
    assert not missing(lb, LABELS)
    assert set(lb.segment_id) <= set(seg.segment_id)
    assert set(lb.split.unique()) <= {"train", "test", "frozen_2026", "excluded"}
    assert not lb.duplicated(["segment_id", "year"]).any()


def test_weather_covers_every_segment_ward(seg):
    wx = load(os.path.join(P, "weather_weekly.parquet"))
    assert not missing(wx, WEATHER)
    assert set(seg.ward.unique()) <= set(wx.ward.unique()), "ward names differ between segments and weather"
    wk = pd.to_datetime(wx.week_start)
    assert (wk.dt.weekday == 0).all(), "week_start must be a Monday"
    assert not wx.duplicated(["ward", "week_start"]).any()


def test_forecast_weather_matches_segment_wards(seg):
    fc = load(os.path.join(P, "weather_forecast_weekly.parquet"))
    assert not missing(fc, WEATHER + ["uses_forecast"])
    assert len(fc), "no forecast weeks"
    wk = pd.to_datetime(fc.week_start)
    assert (wk.dt.weekday == 0).all(), "week_start must be a Monday"
    assert (wk.dt.date > pd.Timestamp(fc.retrieved_at.min()[:10]).date()).all(), "forecast weeks must start after the pull date"
    assert not fc.duplicated(["ward", "week_start"]).any()
    for city, f in fc.groupby("city"):
        seg_wards = set(seg.loc[seg.city == city, "ward"])
        assert set(f.ward) == seg_wards, f"{city}: forecast ward names differ from segments.parquet"
        assert (f.groupby("ward").week_start.nunique() == f.week_start.nunique()).all(), f"{city}: wards cover different weeks"


def test_snapped_reports_link(seg):
    sn = load(os.path.join(P, "fms_snapped.csv"))
    ids = sn.segment_id.dropna()
    assert set(ids) <= set(seg.segment_id)
    assert "description" not in sn.columns, "no free text outside data/raw"


@pytest.mark.parametrize("fname", ["potholes.csv", "resurfacing.csv", "streetlights.csv", "crew_outcomes.csv"])
def test_synthetic_files_use_real_segments(seg, fname):
    df = load(os.path.join(SYN, fname))
    assert df["is_synthetic"].astype(str).str.lower().isin(["true", "1"]).all()
    assert df["source"].astype(str).str.startswith("synthetic:").all()
    ids = df.segment_id.dropna()
    stale = set(ids) - set(seg.segment_id)
    assert not stale, f"{fname}: {len(stale)} segment_ids not in segments.parquet: regenerate synthetic data on real segments"


def test_risk_output_links(seg):
    files = sorted(f for f in os.listdir(OUT) if f.startswith("risk_") and f.endswith(".parquet")) if os.path.isdir(OUT) else []
    if not files:
        pytest.skip("no outputs/risk_*.parquet yet")
    r = pd.read_parquet(os.path.join(OUT, files[-1]))
    assert not missing(r, RISK)
    assert set(r.segment_id) <= set(seg.segment_id)
    assert r[["p7", "p30"]].apply(lambda c: c.between(0, 1)).all().all()
    assert (r.groupby("segment_id").size() == 4).all(), "4 weekly rows per scored segment"
    assert set(r.horizon_week.unique()) <= {1, 2, 3, 4}


CONFIRMED_BY = {"", "keyword", "gemini", "crew"}


def test_plan_confirmations():
    """schemas.md section 9: confirmed_by / confirmed_source_id / confirmed_is_synthetic."""
    path = os.path.join(OUT, "prevention_plan_latest.csv")
    if not os.path.exists(path):
        pytest.skip("no outputs/prevention_plan_latest.csv yet")
    plan = pd.read_csv(path, dtype={"confirmed_by": str, "confirmed_source_id": str}, keep_default_na=False)
    assert not missing(plan, ["confirmed_by", "confirmed_source_id", "confirmed_is_synthetic"])
    by = plan["confirmed_by"].str.strip()
    assert set(by.unique()) <= CONFIRMED_BY, f"confirmed_by outside {sorted(CONFIRMED_BY)}: {set(by) - CONFIRMED_BY}"
    confirmed = by != ""
    assert (plan.loc[confirmed, "confirmed_source_id"].str.strip() != "").all(), \
        "confirmed_source_id is required when confirmed_by is set"
    crew = plan.loc[by == "crew", "confirmed_is_synthetic"].astype(str).str.strip().str.lower()
    assert crew.isin(["true", "false", "1", "0"]).all(), "confirmed_is_synthetic must be true/false on crew rows"
