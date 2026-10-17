"""
Pull FixMyStreet reports for Southampton, Portsmouth and Brighton (roads, potholes, pavements) via FixMyStreet's
public Open311 GeoReport v2 API, politely, and save them as CSV.

Run on your own laptop (normal internet):   python pull_fixmystreet.py
Output: data/fms_raw.csv (KEEP LOCAL: has free text),  data/fms_dedup.csv, data/summary.txt
Source: FixMyStreet (mySociety). Credit it in the README with the date you ran this.
"""
import csv, json, math, os, time, urllib.parse, urllib.request
from datetime import datetime

BASE = "https://www.fixmystreet.com/open311/v2/requests.json"
# FixMyStreet area ids and each council's own category names (checked 17 Oct 2026).
# Comment a city out to skip it. To add a city, its council must accept FixMyStreet reports:
# Bournemouth (BCP, area 152188) does not, so the API returns nothing for it.
CITIES = {
    "Southampton": ("2567", ["Potholes", "Roads/highways", "Pavements/footpaths"]),
    "Portsmouth":  ("2657", ["Potholes", "Roads/highways", "Pavements/footpaths"]),
    "Brighton":    ("2614", ["Pavement and road repairs"]),
}
ROAD_CATS = {"Potholes", "Roads/highways", "Pavement and road repairs"}
YEARS = range(2008, datetime.now().year + 1)
PAUSE = 1.5                # seconds between requests: be polite
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SURFACE_WORDS = ["pothole", "pot hole", "hole", "crater", "sunken", "sinking", "sink",
                 "tarmac", "surface", "crack", "rut", "raised", "uneven", "dip"]

def fetch(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "SotonShip26 student hackathon (contact via team)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r).get("service_requests", [])
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"  retry in {wait}s ({e})")
            time.sleep(wait)
    raise RuntimeError("giving up on " + url)

def get_range(agency, cat, start, end):
    rows = fetch({"jurisdiction_id": "fixmystreet", "agency_responsible": agency,
                  "service_code": cat, "start_date": start, "end_date": end,
                  "max_requests": 1000})
    time.sleep(PAUSE)
    if len(rows) >= 1000:   # API caps at 1000: split into months
        rows = []
        y = int(start[:4])
        for m in range(1, 13):
            s = f"{y}-{m:02d}-01"
            e = f"{y}-{m+1:02d}-01" if m < 12 else f"{y+1}-01-01"
            part = fetch({"jurisdiction_id": "fixmystreet", "agency_responsible": agency,
                          "service_code": cat, "start_date": s, "end_date": e, "max_requests": 1000})
            rows += part
            time.sleep(PAUSE)
    return rows

def haversine_m(a, b):
    R = 6371000
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def main():
    os.makedirs(OUT, exist_ok=True)
    seen, rows = set(), []
    for city, (agency, cats) in CITIES.items():
      for cat in cats:
        for y in YEARS:
            got = get_range(agency, cat, f"{y}-01-01", f"{y}-12-31")
            new = 0
            for r in got:
                rid = r.get("service_request_id")
                if rid in seen:
                    continue
                seen.add(rid); new += 1
                text = ((r.get("title") or "") + " " + (r.get("description") or "")).lower()
                rows.append({
                    "city": city,
                    "id": rid,
                    "category": r.get("service_name"),
                    "requested": r.get("requested_datetime"),
                    "updated": r.get("updated_datetime"),
                    "status": r.get("status"),
                    "lat": r.get("lat"), "lon": r.get("long"),
                    "title": (r.get("title") or "").replace("\n", " "),
                    "description": (r.get("description") or "").replace("\n", " ")[:500],
                    "surface_keyword": any(w in text for w in SURFACE_WORDS),
                })
            print(f"{city:12s} {cat:26s} {y}: {new}")
    rows.sort(key=lambda r: r["requested"] or "")
    fields = list(rows[0].keys()) if rows else []
    with open(os.path.join(OUT, "fms_raw.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    # Road-surface label: Potholes, plus general road categories whose text mentions a surface defect
    surface = [r for r in rows if r["lat"] and (r["category"] == "Potholes" or
               (r["category"] in ROAD_CATS and r["surface_keyword"]))]
    # De-duplicate per city: same defect = within 20 m and 30 days of an earlier kept report
    kept, kept_by_city = [], {}
    for r in surface:
        t = datetime.fromisoformat(r["requested"])
        p = (float(r["lat"]), float(r["lon"]))
        city_kept = kept_by_city.setdefault(r["city"], [])
        dup = False
        for k in reversed(city_kept[-300:]):
            if (t - k["_t"]).days > 30:
                break
            if haversine_m(p, k["_p"]) <= 20:
                dup = True; break
        if not dup:
            r2 = dict(r); r2["_t"], r2["_p"] = t, p
            kept.append(r2); city_kept.append(r2)
    with open(os.path.join(OUT, "fms_dedup.csv"), "w", newline="", encoding="utf-8") as f:
        # No free-text description here: it can contain personal details (names, house numbers).
        # This is the file that is safe to commit to a public repo.
        safe = [k for k in fields if k != "description"]
        w = csv.DictWriter(f, fieldnames=safe); w.writeheader()
        w.writerows([{k: v for k, v in r.items() if k in safe} for r in kept])

    by_year = {}
    for r in kept:
        key = (r["city"], r["requested"][:4])
        by_year[key] = by_year.get(key, 0) + 1
    with open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(f"Pulled {datetime.now().isoformat(timespec='minutes')} from FixMyStreet Open311\n")
        f.write(f"All road/pavement reports: {len(rows)}\n")
        f.write(f"Road-surface reports before de-dup: {len(surface)}, after: {len(kept)}\n")
        for c in CITIES:
            n_all = sum(r["city"] == c for r in rows)
            f.write(f"  {c:12s} all: {n_all}, road-surface de-duplicated: {len(kept_by_city.get(c, []))}\n")
        f.write("Road-surface (de-duplicated) by year:\n")
        for (c, y) in sorted(by_year):
            f.write(f"  {c:12s} {y}: {by_year[(c, y)]}\n")
    print(open(os.path.join(OUT, "summary.txt"), encoding="utf-8").read())

if __name__ == "__main__":
    main()
