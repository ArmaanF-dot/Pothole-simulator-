"""Evidence chart for the pitch: share of next year's potholes found in the top 10% of roads.

    python pitch/make_evidence_chart.py

Reads the numbers from reports/risk_eval.md (real FixMyStreet test years: Southampton 2018-19,
Brighton 2023-25) and writes pitch/evidence_chart.png at 1920x1080. Chance is 10% by construction
(the top 10% of road length catches 10% of reports at random).
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "risk_eval.md"
OUT = Path(__file__).with_name("evidence_chart.png")
CHANCE = 10.0


def read_city(text: str, city: str) -> tuple[float, float]:
    """Model and last-year-baseline capture (%) from the '### <city>, test years' table."""
    m = re.search(rf"### {city}, test years\n(.*?)\n\n", text, re.S)
    if not m:
        raise SystemExit(f"'{city}, test years' section not found in {REPORT}")
    table = m.group(1)

    def value(label: str) -> float:
        row = re.search(rf"^\| {label} \| ([\d.]+)% \|", table, re.M)
        if not row:
            raise SystemExit(f"'{label}' row not found for {city} in {REPORT}")
        return float(row.group(1))

    return value("model"), value("last year reports")


def main() -> None:
    text = REPORT.read_text(encoding="utf-8")
    cities = [("Southampton", "2018-19"), ("Brighton", "2023-25")]
    vals = {c: read_city(text, c) for c, _ in cities}

    plt.rcParams.update({"font.size": 26, "font.family": "DejaVu Sans"})
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100, facecolor="white")
    ax.set_facecolor("white")
    series = [("Chance", "#bdbdbd", lambda c: CHANCE),
              ("Last year's reports", "#7a8ca5", lambda c: vals[c][1]),
              ("RoadSense model", "#1565c0", lambda c: vals[c][0])]
    width = 0.26
    xs = range(len(cities))
    for i, (label, colour, get) in enumerate(series):
        pos = [x + (i - 1) * width for x in xs]
        heights = [get(c) for c, _ in cities]
        bars = ax.bar(pos, heights, width=width * 0.95, color=colour, label=label)
        for b, h in zip(bars, heights):
            ax.text(b.get_x() + b.get_width() / 2, h + 0.8, f"{h:.1f}%" if h != CHANCE else "10%",
                    ha="center", va="bottom", fontsize=30, fontweight="bold")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{c}\n(test {years})" for c, years in cities], fontsize=30)
    ax.set_ylabel("Share of next year's reported potholes")
    ax.set_ylim(0, max(v for pair in vals.values() for v in pair) * 1.25)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_title("Share of next year's potholes found in the top 10% of roads", fontsize=36, fontweight="bold", pad=24)
    ax.legend(loc="upper right", frameon=False, fontsize=26)
    fig.text(0.01, 0.01, "Real FixMyStreet reports; top 10% of road length. Source: reports/risk_eval.md",
             fontsize=18, color="#555555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT, dpi=100, facecolor="white")
    print(f"wrote {OUT}: " + "; ".join(f"{c} model {vals[c][0]}% vs baseline {vals[c][1]}%" for c, _ in cities))


if __name__ == "__main__":
    main()
