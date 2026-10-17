"""Lane C inputs: config, and loaders for the other lanes' outputs with labelled fallbacks.

Order for each input: the real file from lane A or B, then lane B's mock, then a small
deterministic lane C mock. Every frame carries where it came from so the API and page can show
SYNTHETIC, MOCK and "cached, retrieved <date>" labels. Nothing here invents real data.
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


def latest(folder: Path, prefix: str) -> Path | None:
    files = sorted(folder.glob(f"{prefix}_*.parquet"))
    return files[-1] if files else None


# --- loaders ----------------------------------------------------------------------------------
def load_segments(cfg: dict, root: Path | None = None) -> tuple[pd.DataFrame, dict]:
    for p, kind in [(resolve(cfg, "processed_dir", root) / "segments.parquet", "real"),
                    (resolve(cfg, "lane_b_mock_dir", root) / "segments.parquet", "mock")]:
        if p.exists():
            seg = pd.read_parquet(p)
            return _segment_defaults(seg), {"name": "segments", "path": str(p.relative_to(Path(root or ROOT))),
                                            "kind": kind, "retrieved_at": _mtime(p)}
    from roadsense.prevent.mock import mock_world
    return _segment_defaults(mock_world(cfg)["segments"]), {"name": "segments", "path": None, "kind": "mock",
                                                            "retrieved_at": None}


def _segment_defaults(seg: pd.DataFrame) -> pd.DataFrame:
    seg = seg.copy()
    if "lat" not in seg or "lon" not in seg:
        mids = seg["geometry"].map(_midpoint)
        seg["lon"], seg["lat"] = [m[0] for m in mids], [m[1] for m in mids]
    for c, v in [("owner", "council"), ("bus_stop", False), ("junction", False), ("in_flood_area", False),
                 ("esal_day", np.nan), ("ward", None)]:
        if c not in seg:
            seg[c] = v
    if "esal_confidence" not in seg:
        # lane A: "count" when a DfT count point is on the segment's road, else "modelled"
        seg["esal_confidence"] = "modelled"
    if "input_source" not in seg:
        seg["input_source"] = "real"
    return seg


def _coords(wkt) -> list[tuple[float, float]]:
    if not isinstance(wkt, str):
        try:
            from shapely import wkb
            return list(wkb.loads(wkt).coords)
        except Exception:
            return []
    inner = wkt[wkt.index("(") + 1: wkt.rindex(")")].replace("(", "").replace(")", "")
    return [tuple(map(float, p.split()[:2])) for p in inner.split(",") if p.strip()]


def _midpoint(wkt) -> tuple[float, float]:
    c = _coords(wkt)
    if not c:
        return (np.nan, np.nan)
    a = np.array(c)
    return tuple(a.mean(0))


def load_risk(cfg: dict, root: Path | None = None) -> tuple[pd.DataFrame, dict]:
    p = latest(resolve(cfg, "outputs_dir", root), "risk")
    if p is not None:
        r = pd.read_parquet(p)
        kind = "mock" if bool(r.get("inputs_mock", pd.Series([False])).any()) else "real"
        return r, {"name": "risk", "path": str(p.relative_to(Path(root or ROOT))), "kind": kind,
                   "retrieved_at": _mtime(p), "as_of": str(r["as_of"].iloc[0]) if "as_of" in r else None}
    from roadsense.prevent.mock import mock_world
    r = mock_world(cfg)["risk"]
    return r, {"name": "risk", "path": None, "kind": "mock", "retrieved_at": None, "as_of": str(r["as_of"].iloc[0])}


def load_lights(cfg: dict, root: Path | None = None) -> tuple[pd.DataFrame, dict]:
    p = latest(resolve(cfg, "outputs_dir", root), "lights")
    if p is not None:
        return pd.read_parquet(p), {"name": "lights", "path": str(p.relative_to(Path(root or ROOT))),
                                    "kind": "synthetic", "retrieved_at": _mtime(p)}
    from roadsense.prevent.mock import mock_world
    return mock_world(cfg)["lights"], {"name": "lights", "path": None, "kind": "mock", "retrieved_at": None}


def load_forecast_meta(cfg: dict, root: Path | None = None) -> dict:
    """When the weather forecast was retrieved. Lane A writes weather_forecast_weekly.parquet with
    a retrieved_at column; until then the risk file's weeks 1-3 are climatology (no forecast)."""
    p = resolve(cfg, "processed_dir", root) / "weather_forecast_weekly.parquet"
    if not p.exists():
        return {"available": False, "retrieved_at": None, "path": None}
    fc = pd.read_parquet(p)
    ra = str(fc["retrieved_at"].max()) if "retrieved_at" in fc else _mtime(p)
    return {"available": True, "retrieved_at": ra, "path": str(p.relative_to(Path(root or ROOT)))}


def load_fms(cfg: dict, root: Path | None = None, city: str = "Southampton", all_reports: bool = False) -> pd.DataFrame:
    """Real FixMyStreet reports (public). Location, date, category, title and status only."""
    p = resolve(cfg, "fms_all_csv" if all_reports else "fms_csv", root)
    if not p.exists():
        return pd.DataFrame(columns=["id", "category", "requested", "status", "lat", "lon", "title"])
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
