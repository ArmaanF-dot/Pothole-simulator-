"""Map-only view of a second city (Brighton) from lane B's real-label risk (outputs/risk_<city>_latest.parquet).

The plan, lights and triage stay Southampton only. Segments are coloured by their risk rank within the
city (top 1%, 5%, 10%), not by Southampton's urgency bands: there is no wear or consequence data for the
second city, so urgency would not be comparable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from roadsense.prevent import inputs as I

RANK_BANDS = [(0.99, "top1"), (0.95, "top5"), (0.90, "top10")]
RANK_LABEL = {"top1": "Top 1% risk in the city", "top5": "Top 5%", "top10": "Top 10%", "rest": "Lower risk"}


def available(cfg: dict, root: Path | None = None) -> list[str]:
    od = I.resolve(cfg, "outputs_dir", root)
    out = []
    for p in sorted(od.glob("risk_*_latest.parquet")):
        city = p.stem[len("risk_"):-len("_latest")]
        if city not in ("synthetic",):
            out.append(city.capitalize())
    return out


class CityView:
    def __init__(self, cfg: dict, city: str, root: Path | None = None):
        self.city = city
        od = I.resolve(cfg, "outputs_dir", root)
        p = od / f"risk_{city.lower()}_latest.parquet"
        if not p.exists():
            raise FileNotFoundError(p)
        raw = pd.read_parquet(p)
        self.meta = {"model_version": str(raw["model_version"].iloc[0]) if "model_version" in raw else None,
                     "trained_on": str(raw["trained_on"].iloc[0]) if "trained_on" in raw else None,
                     "uses_synthetic": bool(raw["uses_synthetic"].any()) if "uses_synthetic" in raw else True,
                     "history_source": str(raw["history_source"].iloc[0]) if "history_source" in raw else None,
                     "as_of": str(raw["as_of"].iloc[0]) if "as_of" in raw else None, "path": I._rel(p, root)}
        risk = I.normalise_risk(raw)
        seg = None
        for d in [I.resolve(cfg, "processed_dir", root), I.resolve(cfg, "lane_c_copy_dir", root)]:
            if (d / "segments.parquet").exists():
                s = pd.read_parquet(d / "segments.parquet")
                seg = s[s["city"] == city] if "city" in s else s
                break
        if seg is None:
            raise FileNotFoundError("segments.parquet")
        cols = [c for c in ["segment_id", "name", "ref", "highway", "ward", "geometry", "lat", "lon", "owner"] if c in seg]
        df = seg[cols].merge(risk.drop(columns=[c for c in ["ward"] if c in risk]), on="segment_id", how="inner")
        df = df.reset_index(drop=True)
        df["name"] = I.display_names(df)
        pct = df["rank_pct"] if "rank_pct" in df and df["rank_pct"].notna().any() else df["p30"].rank(pct=True)
        df["rank_pct"] = pct.astype(float)
        df["risk_band"] = np.select([df["rank_pct"] >= t for t, _ in RANK_BANDS], [b for _, b in RANK_BANDS], "rest")
        self.df = df.reset_index(drop=True)
        self._geom = {sid: [[round(x, 6), round(y, 6)] for x, y in I._coords(g)]
                      for sid, g in zip(self.df["segment_id"], self.df["geometry"])}

    @property
    def real_inputs(self) -> bool:
        return self.meta["trained_on"] == "real" and not self.meta["uses_synthetic"]

    def badge(self) -> str:
        return "100% real inputs" if self.real_inputs else "includes synthetic inputs"

    def geojson(self) -> dict:
        feats = []
        # bands and reasons only: no P30 or rank numbers for the second city (map view, not a forecast)
        for r in self.df[["segment_id", "name", "ward", "highway", "risk_band"]].to_dict("records"):
            r = {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.items()}
            r["band"] = {"top1": "critical", "top5": "high", "top10": "prevention"}.get(r["risk_band"], "monitor")
            feats.append({"type": "Feature", "properties": r,
                          "geometry": {"type": "LineString", "coordinates": self._geom.get(r["segment_id"], [])}})
        return {"type": "FeatureCollection", "features": feats,
                "meta": {"city": self.city, "count": len(feats), "badge": self.badge(), **self.meta,
                         "bands": {b: int((self.df["risk_band"] == b).sum()) for b in ["top1", "top5", "top10", "rest"]}}}

    def segment(self, sid: str) -> dict | None:
        r = self.df[self.df["segment_id"] == sid]
        if r.empty:
            return None
        r = r.iloc[0]
        clean = lambda v: None if v is None or (isinstance(v, float) and not np.isfinite(v)) else (
            v.item() if hasattr(v, "item") else v)
        return {"city": self.city, "segment_id": sid, "name": r["name"], "ward": r.get("ward"), "highway": r["highway"],
                "risk_band": r["risk_band"], "risk_label": RANK_LABEL[r["risk_band"]],
                "reasons": [x for x in [r.get("reason_1"), r.get("reason_2"), r.get("reason_3")] if isinstance(x, str)],
                "badge": self.badge(), **self.meta,
                "note": f"Map only: the prevention plan, streetlights and triage cover Southampton only."}

    INSPECT_HEADER = ("{city} inspection list: ranked by risk from real FixMyStreet reports. "
                      "No wear model for {city}, so treatments are chosen on inspection.")

    def inspection_list(self, open_reports: pd.DataFrame, cfg: dict, top_n: int = 50) -> dict:
        """Segments to inspect: any council segment with an open FixMyStreet report in the open window
        (first, marked "open report"), then the top_n by within-city risk rank. Bands and reasons only,
        like the map card: no P30, no treatment, no money (no wear or cost model for this city)."""
        from roadsense.prevent.inputs import SegmentIndex
        df = self.df
        owner = df["owner"] if "owner" in df else pd.Series("council", index=df.index)
        council = ((owner != "national_highways") & (df["highway"] != "motorway")).values
        reports: dict[str, list] = {}
        if open_reports is not None and len(open_reports):
            idx = SegmentIndex(df)
            for r in open_reports.itertuples():
                j, d = idx.nearest(float(r.lon), float(r.lat), mask=council)
                if j is not None and d <= cfg["triage"]["snap_radius_m"]:
                    reports.setdefault(df.iloc[j]["segment_id"], []).append(
                        {"id": int(r.id), "reported_at": str(r.reported_at)[:10], "title": str(r.title)})
        c = df[council]
        opened = c[c["segment_id"].isin(reports)].sort_values("rank_pct", ascending=False)
        rest = c[~c["segment_id"].isin(reports)].sort_values("rank_pct", ascending=False).head(top_n)
        rows = []
        for k, r in enumerate(pd.concat([opened, rest]).to_dict("records"), start=1):
            reps = sorted(reports.get(r["segment_id"], []), key=lambda x: x["reported_at"], reverse=True)
            rows.append({"rank": k, "section": "open" if reps else "risk",
                         "segment_id": r["segment_id"], "name": r["name"], "ward": r.get("ward"),
                         "highway": r["highway"], "risk_band": r["risk_band"], "risk_label": RANK_LABEL[r["risk_band"]],
                         "reasons": [x for x in [r.get("reason_1"), r.get("reason_2"), r.get("reason_3")] if isinstance(x, str)],
                         "action": "Inspect", "open_report": bool(reps), "open_reports": reps,
                         "history_source": self.meta["history_source"], "uses_synthetic": bool(self.meta["uses_synthetic"])})
        sections = [{"key": "open", "label": "Open reports (inspect first)", "count": len(opened),
                     "note": "ranked by predicted risk within the section"},
                    {"key": "risk", "label": "Highest predicted risk", "count": len(rest), "note": f"top {top_n} by risk rank"}]
        return {"city": self.city, "header": self.INSPECT_HEADER.format(city=self.city), "badge": self.badge(),
                "sections": sections,
                "count": len(rows), "open_report_rows": len(opened), "top_n": top_n,
                "window_days": cfg["triage"]["open_report_days"], **self.meta, "rows": rows}

