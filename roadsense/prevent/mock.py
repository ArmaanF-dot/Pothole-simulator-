"""Small deterministic mock world in the shapes of schemas (lane A segments, lane B risk/lights).

Only used when neither the real files nor lane B's mocks are on disk, and in tests. Every row
carries input_source='mock' / inputs_mock=True so the page shows MOCK, never real.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from roadsense.prevent.inputs import M_PER_DEG_LAT, M_PER_DEG_LON

HIGHWAYS = ["residential", "residential", "residential", "tertiary", "secondary", "primary", "trunk", "motorway"]


def mock_world(cfg: dict | None = None, n_ways: int = 12, per_way: int = 10, seed: int = 2026,
               as_of: str = "2026-10-12") -> dict:
    rng = np.random.default_rng(seed)
    lon0, lat0 = -1.44, 50.90
    L = 75.0
    rows = []
    for w in range(n_ways):
        hw = HIGHWAYS[w % len(HIGHWAYS)]
        lat = lat0 + (w * 240) / M_PER_DEG_LAT
        for k in range(per_way):
            a = lon0 + (k * L) / M_PER_DEG_LON
            b = lon0 + ((k + 1) * L) / M_PER_DEG_LON
            esal = {"motorway": 4000, "trunk": 2500, "primary": 900, "secondary": 300, "tertiary": 90}.get(hw, 8)
            rows.append({
                "segment_id": f"X{w:03d}-{k:03d}", "osm_way_id": w + 1, "name": f"Mock Road {w + 1}",
                "highway": hw, "ward": f"Mock ward {w % 3 + 1:02d}", "length_m": L,
                "geometry": f"LINESTRING ({a:.6f} {lat:.6f}, {b:.6f} {lat:.6f})",
                "lat": lat, "lon": (a + b) / 2, "bus_stop": bool(rng.random() < 0.15),
                "junction": k in (0, per_way - 1), "in_flood_area": bool(rng.random() < 0.1),
                "owner": "national_highways" if hw == "motorway" else "council",
                "esal_day": float(esal * rng.lognormal(0, 0.4)),
                "esal_confidence": "count" if hw in ("primary", "trunk") and k == 0 else "modelled",
                "input_source": "mock",
            })
    seg = pd.DataFrame(rows)
    sc = seg[seg["owner"] == "council"].reset_index(drop=True)
    n = len(sc)
    base = 0.002 + 0.03 * np.log1p(sc["esal_day"].values) / np.log1p(2500) + rng.uniform(0, 0.02, n)
    rise = rng.normal(0.004, 0.006, n)
    p30 = {f"p30_w{k}": np.clip(base + rise * k / 3, 0.0005, 0.9) for k in range(4)}
    wear = np.clip(rng.uniform(5, 98, n), 0, 100).round(1)
    risk = pd.DataFrame({
        "segment_id": sc["segment_id"], "ward": sc["ward"], "week_start": pd.Timestamp(as_of),
        "p7": base * 0.3, "p30": p30["p30_w0"], **p30,
        "p30_trend": p30["p30_w3"] - p30["p30_w0"], "wear_pct": wear,
        "reason_1": [f"heavy axle load ({e:,.0f} ESAL/day)" for e in sc["esal_day"]],
        "reason_2": "12 mm rain in the last 7 days", "reason_3": None,
        "weather_source": "w0:observed,w1:climatology_10y,w2:climatology_10y,w3:climatology_10y",
        "labels_synthetic": True, "wear_synthetic": True, "inputs_mock": True,
        "model_version": "mock", "as_of": as_of,
    })
    lamps = []
    for i, r in sc.iterrows():
        for j in range(2):
            p = float(rng.beta(1, 30))
            lamps.append({
                "lamp_id": f"XL{i:04d}{j}", "segment_id": r["segment_id"], "lat": r["lat"],
                "lon": r["lon"] + (j - 0.5) * 30 / M_PER_DEG_LON, "unit_type": "LED",
                "unit_install_date": "2013-06-01", "burn_hours": 45000.0, "p_fail_90d": p,
                "predicted_replacement_date": "2028-01-01", "replacement_overdue": False,
                "due_90d": p > 0.08, "currently_dark": bool(rng.random() < 0.02), "dark_since": None,
                "is_synthetic": True, "source": "mock:lane_c", "as_of": as_of,
            })
    return {"segments": seg, "risk": risk, "lights": pd.DataFrame(lamps)}
