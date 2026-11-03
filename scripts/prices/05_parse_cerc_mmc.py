"""Extract IEX price (min/max/weighted average ACP) and bid volume statistics from CERC Market Monitoring Cell
monthly short-term market reports (text extracted by 02_pdf_to_text.py).

Output: data/processed/prices/cerc_mmc_monthly_iex_stats.csv (long, CONVENTIONS columns)
Usage: .venv/bin/python -I scripts/prices/05_parse_cerc_mmc.py
"""
import calendar
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TXT = ROOT / "data" / "raw" / "prices" / "cerc" / "txt"
OUT = ROOT / "data" / "processed" / "prices" / "cerc_mmc_monthly_iex_stats.csv"
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTHS["februrary"] = 2

# source ids assigned in sources/prices_sources.csv
SRC = {}


def month_of(name):
    m = re.search(r"(January|Februrary|February|March|April|May|June|July|August|September|October|November|December|"
                  r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)_?(\d{4})", name)
    return int(m.group(2)), MONTHS[m.group(1).lower()]


SEG = {"DAY AHEAD MARKET": "DAM", "GREEN DAY AHEAD MARKET": "GDAM", "REAL TIME MARKET": "RTM"}


def main(src_map):
    rows = []
    for f in sorted(TXT.glob("MMC_Report*.txt")):
        y, mo = month_of(f.stem)
        ps = f"{y}-{mo:02d}-01"
        pe = f"{y}-{mo:02d}-{calendar.monthrange(y, mo)[1]:02d}"
        t = f.read_text()
        sid = src_map[f.stem]
        for title, seg in SEG.items():
            m = re.search(r"PRICE OF ELECTRICITY TRANSACTED IN " + title + r", [A-Z]+ \d{4}.*?\n1 Minimum ([\d.\-]+).*?\n2 Maximum ([\d.\-]+).*?\n3 Weighted Average ([\d.\-]+)",
                          t, re.S)
            if not m:
                print("no price table", f.name, seg)
                continue
            for metric, v in zip(("min_acp", "max_acp", "weighted_avg_acp"), m.groups()):
                if v == "-":
                    continue
                rows.append({"geography": "India", "market": f"IEX {seg}", "period_start": ps, "period_end": pe,
                             "granularity": "monthly", "metric": metric, "value": float(v), "unit": "Rs/kWh",
                             "source_id": sid, "notes": f"CERC MMC monthly report table 'Price of electricity transacted in {title.title()}' (IEX column; ACP = area clearing price)"})
        flat = re.sub(r"\s+", " ", t)
        for seg, key in (("DAM", r"transacted in the DAM (?:segment )?of IEX"), ("RTM", r"transacted in the RTM (?:segment )?of IEX"),
                         ("GDAM", r"transacted in the G-?DAM of IEX")):
            m = re.search(key + r"[^.]*?was ([\d.]+) ?MU.{0,200}?buy bids and sell bids was ([\d.]+) MU and ([\d.]+) MU, respectively,? in IEX", flat)
            if not m:
                print("no volume para", f.name, seg)
                continue
            for metric, v in zip(("traded_volume", "buy_bid_volume", "sell_bid_volume"), m.groups()):
                rows.append({"geography": "India", "market": f"IEX {seg}", "period_start": ps, "period_end": pe,
                             "granularity": "monthly", "metric": metric, "value": float(v), "unit": "MU",
                             "source_id": sid, "notes": "CERC MMC monthly report, section 2 text"})
            rows.append({"geography": "India", "market": f"IEX {seg}", "period_start": ps, "period_end": pe,
                         "granularity": "monthly", "metric": "sell_buy_bid_ratio", "value": round(float(m.group(3)) / float(m.group(2)), 3),
                         "unit": "ratio", "source_id": sid, "notes": "DERIVED: sell_bid_volume / buy_bid_volume from the same report"})
    df = pd.DataFrame(rows).sort_values(["market", "period_start", "metric"])
    df.to_csv(OUT, index=False)
    print(len(df), "rows")


if __name__ == "__main__":
    reg = pd.read_csv(ROOT / "sources" / "prices_sources.csv")
    src_map = {}
    for _, r in reg.iterrows():
        if isinstance(r["notes"], str) and "local:" in r["notes"]:
            stem = r["notes"].split("local:")[1].split(";")[0].strip()
            src_map[stem] = r["source_id"]
    main(src_map)
