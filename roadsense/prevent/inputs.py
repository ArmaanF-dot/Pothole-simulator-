"""Lane C inputs: config, and loaders for the other lanes' outputs with labelled fallbacks.

Segments: lane A's data/processed/ (after the merge), then lane C's copy of lane A's real
Southampton files in roadsense/prevent/mock_data/, then lane B's mock, then a small lane C mock.
Risk and lights: lane B's outputs when their segment ids match the segments in use, otherwise a
labelled mock in the contract's columns (docs/contract_outputs.md sections 7-8) on those segments.
Every frame carries where it came from so the API and page can show SYNTHETIC, MOCK and
"cached, retrieved <date>" labels. Nothing here invents real data.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(__file__).with_name("prevent.yaml")
LOAD_CONFIDENCE = {"count": "high", "same_road": "medium", "class_median": "low"}

# local metric projection, same constants as lane B (good enough at city scale)
LAT0 = 50.92
M_PER_DEG_LAT = 110_540.0
M_PER_DEG_LON = 111_320.0 * np.cos(np.radians(LAT0))


def load_config(path: Path | str | None = None) -> dict:
    with open(path or CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(cfg: dict, key: str, root: Path | None = None) -> Path:
    return Path(root or ROOT) / cfg["paths"][key]


def to_xy(lon, lat):
    return (np.asarray(lon, float) * M_PER_DEG_LON, np.asarray(lat, float) * M_PER_DEG_LAT)


def _mtime(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def _rel(p: Path, root: Path | None) -> str:
    try:
        return p.relative_to(Path(root or ROOT)).as_posix()
    except ValueError:
        try:
            return p.relative_to(ROOT).as_posix()
        except ValueError:
            return str(p)


def latest(folder: Path, prefix: str) -> Path | None:
    """`<prefix>_latest.parquet` if lane B wrote one, else the newest dated file."""
    if (folder / f"{prefix}_latest.parquet").exists():
        return folder / f"{prefix}_latest.parquet"
    files = sorted(p for p in folder.glob(f"{prefix}_*.parquet") if not p.stem.endswith("_latest"))
    return files[-1] if files else None


# --- segments ---------------------------------------------------------------------------------
def load_segments(cfg: dict, root: Path | None = None) -> tuple[pd.DataFrame, dict]:
    for d, kind in [(resolve(cfg, "processed_dir", root), "real"), (resolve(cfg, "lane_c_copy_dir", root), "real"),
                    (resolve(cfg, "lane_b_mock_dir", root), "mock")]:
        p = d / "segments.parquet"
        if not p.exists():
            continue
        seg = pd.read_parquet(p)
        if "city" in seg:
            seg = seg[seg["city"] == cfg["coverage"]["city"]]
        lp = d / "load.parquet"
        if lp.exists():
            load = pd.read_parquet(lp)
            keep = [c for c in ["segment_id", "esal_day", "hgv_bus_aadf", "load_source", "count_point_id", "count_year"]
                    if c in load]
            seg = seg.drop(columns=[c for c in keep if c != "segment_id" and c in seg]).merge(
                load[keep], on="segment_id", how="left")
        meta = {"name": "segments", "path": _rel(p, root), "kind": kind, "retrieved_at": _mtime(p),
                "load_path": _rel(lp, root) if lp.exists() else None}
        return _segment_defaults(seg), meta
    from roadsense.prevent.mock import mock_world
    return _segment_defaults(mock_world(cfg)["segments"]), {"name": "segments", "path": None, "kind": "mock",
                                                            "retrieved_at": None, "load_path": None}


def _segment_defaults(seg: pd.DataFrame) -> pd.DataFrame:
    seg = seg.reset_index(drop=True).copy()
    if "lat" not in seg or "lon" not in seg:
        mids = seg["geometry"].map(_midpoint)
        seg["lon"], seg["lat"] = [m[0] for m in mids], [m[1] for m in mids]
    for c, v in [("owner", "council"), ("bus_stop", False), ("junction", False), ("in_flood_area", False),
                 ("esal_day", np.nan), ("ward", None), ("ref", ""), ("bus_routes", 0), ("name", "")]:
        if c not in seg:
            seg[c] = v
    seg["name"] = seg["name"].fillna("")
    seg["ref"] = seg["ref"].fillna("")
    seg["name"] = seg["name"].where(seg["name"] != "", seg["ref"])
    seg["name"] = seg["name"].where(seg["name"] != "", "Unnamed " + seg["highway"].astype(str) + " road")
    if "load_source" not in seg:
        seg["load_source"] = None
    seg["load_source"] = seg["load_source"].fillna("class_median")
    seg["load_confidence"] = seg["load_source"].map(LOAD_CONFIDENCE).fillna("low")
    if "input_source" not in seg:
        seg["input_source"] = "real"
    return seg


def _coords(geom) -> list[tuple[float, float]]:
    if geom is None:
        return []
    if not isinstance(geom, str):
        try:
            from shapely import wkb
            return [tuple(c[:2]) for c in wkb.loads(bytes(geom)).coords]
        except Exception:
            return []
    inner = geom[geom.index("(") + 1: geom.rindex(")")].replace("(", "").replace(")", "")
    return [tuple(map(float, p.split()[:2])) for p in inner.split(",") if p.strip()]


def _midpoint(geom) -> tuple[float, float]:
    c = _coords(geom)
    if not c:
        return (np.nan, np.nan)
    return tuple(np.array(c).mean(0))


# --- risk and lights --------------------------------------------------------------------------
def normalise_risk(r: pd.DataFrame) -> pd.DataFrame:
    """Contract section 7 (one row per segment per forecast week, `wear`, `uses_synthetic`) to one
    row per segment with p30_w0..p30_w3. Also accepts lane B's older wide file."""
    r = r.copy()
    if "horizon_week" in r:
        r["horizon_week"] = r["horizon_week"].astype(int)
        piv = r.pivot_table(index="segment_id", columns="horizon_week", values="p30")
        fc = r.groupby("segment_id")["uses_forecast"].any() if "uses_forecast" in r else None
        r = r[r["horizon_week"] == r["horizon_week"].min()].copy()
        for k in piv.columns:
            r[f"p30_w{k}"] = r["segment_id"].map(piv[k])
        if fc is not None:
            r["uses_forecast"] = r["segment_id"].map(fc)
    if "wear_pct" not in r and "wear" in r:
        r["wear_pct"] = r["wear"]
    if "uses_synthetic" in r:
        r["labels_synthetic"] = r["uses_synthetic"].astype(bool)
        r["wear_synthetic"] = r["uses_synthetic"].astype(bool)
    for c, v in [("labels_synthetic", True), ("wear_synthetic", True), ("inputs_mock", False),
                 ("uses_synthetic", True), ("weather_source", "unknown"), ("weather_data_date", None)]:
        if c not in r:
            r[c] = v
    if "p30_w0" not in r:
        r["p30_w0"] = r["p30"]
    weeks = [c for c in ["p30_w0", "p30_w1", "p30_w2", "p30_w3"] if c in r]
    r["p30_trend"] = r[weeks[-1]] - r["p30_w0"]
    return r.reset_index(drop=True)


def _overlap(ids: pd.Series, seg: pd.DataFrame | None) -> float:
    return 1.0 if seg is None else float(ids.isin(seg["segment_id"]).mean() if len(ids) else 0)


def load_risk(cfg: dict, root: Path | None = None, seg: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Lane B's risk file when its segment ids match `seg`; otherwise a labelled mock on `seg`
    (lane B still runs on mock segments until lane A's files are merged)."""
    p = latest(resolve(cfg, "outputs_dir", root), "risk")
    if p is not None:
        r = normalise_risk(pd.read_parquet(p))
        if _overlap(r["segment_id"], seg) >= 0.5:
            kind = "mock" if bool(r["inputs_mock"].any()) else "real"
            return r, {"name": "risk", "path": _rel(p, root), "kind": kind, "retrieved_at": _mtime(p),
                       "as_of": str(r["as_of"].iloc[0]) if "as_of" in r else None}
    from roadsense.prevent.mock import mock_risk, mock_world
    r = normalise_risk(mock_risk(seg, cfg) if seg is not None else mock_world(cfg)["risk"])
    return r, {"name": "risk", "path": None, "kind": "mock", "retrieved_at": None, "as_of": str(r["as_of"].iloc[0]),
               "note": "lane B's risk file uses other segment ids" if p is not None else "no lane B risk file"}


def normalise_lights(l: pd.DataFrame) -> pd.DataFrame:
    """Contract section 8 names (lamp_type, replace_by, dark_source); accepts lane B's older names."""
    l = l.copy()
    for new, old in [("lamp_type", "unit_type"), ("replace_by", "predicted_replacement_date")]:
        if new not in l and old in l:
            l[new] = l[old]
    for c, v in [("dark_source", None), ("uses_synthetic", True), ("replacement_overdue", False), ("dark_since", None),
                 ("as_of", None), ("source", None)]:
        if c not in l:
            l[c] = v
    if "due_90d" not in l:
        l["due_90d"] = pd.to_datetime(l["replace_by"]) <= pd.to_datetime(l["as_of"]) + pd.Timedelta(days=90)
    return l


def load_lights(cfg: dict, root: Path | None = None, seg: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    p = latest(resolve(cfg, "outputs_dir", root), "lights")
    if p is not None:
        l = normalise_lights(pd.read_parquet(p))
        if _overlap(l["segment_id"], seg) >= 0.5:
            return l, {"name": "lights", "path": _rel(p, root), "kind": "synthetic", "retrieved_at": _mtime(p),
                       "as_of": str(l["as_of"].iloc[0]) if len(l) else None}
    from roadsense.prevent.mock import mock_lights, mock_world
    l = normalise_lights(mock_lights(seg) if seg is not None else mock_world(cfg)["lights"])
    return l, {"name": "lights", "path": None, "kind": "mock", "retrieved_at": None, "as_of": str(l["as_of"].iloc[0])}


def load_forecast_meta(cfg: dict, root: Path | None = None) -> dict:
    """When the weather forecast was retrieved. Lane A writes weather_forecast_weekly.parquet with
    a retrieved_at column; until then the risk file's weeks 1-3 are climatology (no forecast)."""
    p = resolve(cfg, "processed_dir", root) / "weather_forecast_weekly.parquet"
    if not p.exists():
        return {"available": False, "retrieved_at": None, "path": None}
    fc = pd.read_parquet(p)
    ra = str(fc["retrieved_at"].max()) if "retrieved_at" in fc else _mtime(p)
    return {"available": True, "retrieved_at": ra, "path": _rel(p, root)}


def load_fms(cfg: dict, root: Path | None = None, city: str = "Southampton", all_reports: bool = False) -> pd.DataFrame:
    """Real FixMyStreet reports (public). Location, date, category, title and status only."""
    p = resolve(cfg, "fms_all_csv" if all_reports else "fms_csv", root)
    if not p.exists():
        return pd.DataFrame(columns=["id", "category", "requested", "status", "lat", "lon", "title", "source", "retrieved_at"])
    d = pd.read_csv(p)
    d = d[d["city"] == city].copy()
    d["requested"] = pd.to_datetime(d["requested"], utc=True).dt.tz_localize(None)
    d["source"] = "fixmystreet"
    d["retrieved_at"] = _mtime(p)
    return d[["id", "category", "requested", "status", "lat", "lon", "title", "source", "retrieved_at"]]


def synthetic_meta(cfg: dict, root: Path | None = None) -> dict | None:
    p = resolve(cfg, "synthetic_dir", root) / "_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# --- spatial helpers ----------------------------------------------------------------------------
class SegmentIndex:
    """Nearest-segment lookup on segment polylines (point-to-line distance in metres)."""

    def __init__(self, seg: pd.DataFrame):
        self.seg = seg.reset_index(drop=True)
        a, b, idx = [], [], []
        for i, g in enumerate(self.seg["geometry"]):
            c = _coords(g)
            for p, q in zip(c[:-1], c[1:]):
                a.append(p), b.append(q), idx.append(i)
        if not a:  # no geometry: fall back to midpoints
            mx, my = to_xy(self.seg["lon"], self.seg["lat"])
            self.ax, self.ay, self.bx, self.by = mx, my, mx, my
            self.idx = np.arange(len(self.seg))
            return
        a, b = np.array(a), np.array(b)
        self.ax, self.ay = to_xy(a[:, 0], a[:, 1])
        self.bx, self.by = to_xy(b[:, 0], b[:, 1])
        self.idx = np.array(idx)

    def nearest(self, lon: float, lat: float, mask: np.ndarray | None = None) -> tuple[int | None, float]:
        px, py = to_xy(lon, lat)
        dx, dy = self.bx - self.ax, self.by - self.ay
        L2 = dx * dx + dy * dy
        t = np.where(L2 > 0, ((px - self.ax) * dx + (py - self.ay) * dy) / np.where(L2 > 0, L2, 1), 0).clip(0, 1)
        d = np.hypot(self.ax + t * dx - px, self.ay + t * dy - py)
        if mask is not None:
            d = np.where(mask[self.idx], d, np.inf)
        if not len(d) or not np.isfinite(d.min()):
            return None, float("inf")
        j = int(d.argmin())
        return int(self.idx[j]), float(d[j])


def distance_m(lon1, lat1, lon2, lat2) -> np.ndarray:
    x1, y1 = to_xy(lon1, lat1)
    x2, y2 = to_xy(lon2, lat2)
    return np.hypot(x1 - x2, y1 - y2)


def in_coverage(lon: float, lat: float, cfg: dict) -> bool:
    lon0, lat0, lon1, lat1 = cfg["coverage"]["bbox"]
    return lon0 <= lon <= lon1 and lat0 <= lat <= lat1
