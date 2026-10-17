"""
Make data/fms_roads_clean.csv: road-surface reports only (pavement/footway defects removed).
Rule (transparent on purpose, so it can be explained to judges):
  - PAVEMENT words in the title  -> drop, unless the title also names a ROAD word (e.g. "pothole in road by kerb")
  - title says nothing either way -> decide from the description the same way
  - otherwise keep
Needs data/fms_raw.csv (local only) for descriptions. Output has no free text.
"""
import re, pandas as pd
PAVE = r"\b(pavements?|footpaths?|footways?|paving|slabs?|kerbs?|curbs?|kerbstones?|dropped kerb|walkways?|path|trip (hazard|risk))\b"
# Street names ("Tisbury Road", "Hill Lane") must not count as evidence of a road defect
STREET = r"\b[A-Z][a-z]+ (Road|Lane|Street|Avenue|Way|Drive|Hill|Rise|Close)\b"
ROAD = r"\b(road|carriageway|lane|junction|roundabout|street surface|bus stop|traffic|cars?|drivers?|cyclists?|tarmac road)\b"

def classify(title, desc):
    t = re.sub(STREET, " ", str(title or "")).lower()
    d = re.sub(STREET, " ", str(desc or "")).lower()
    pt, rt = bool(re.search(PAVE, t)), bool(re.search(ROAD, t))
    if pt and not rt: return "pavement"
    if rt: return "road"
    pd_, rd = bool(re.search(PAVE, d)), bool(re.search(ROAD, d))
    if pd_ and not rd: return "pavement"
    return "road"

dedup = pd.read_csv("data/fms_dedup.csv")
raw = pd.read_csv("data/fms_raw.csv", usecols=["id", "description"]).drop_duplicates("id")
m = dedup.merge(raw, on="id", how="left")
m["surface"] = [classify(t, d) for t, d in zip(m.title, m.description)]
clean = m[m.surface == "road"].drop(columns=["description", "surface"])
clean.to_csv("data/fms_roads_clean.csv", index=False)

summary = m.groupby(["city", "surface"]).size().unstack(fill_value=0)
summary["kept_%"] = (100 * summary["road"] / summary.sum(axis=1)).round(1)
print(summary.to_string())
# Samples for a hand check (titles only)
for lab in ["pavement", "road"]:
    s = m[(m.city == "Brighton") & (m.surface == lab)].sample(25, random_state=1)
    print(f"\n--- Brighton sample classified {lab}:")
    for t in s.title: print("  ", str(t)[:80])
