"""Monthly congestion indicators for IEX DAM and RTM from the 15-min market snapshot.

Input: data/raw/transmission/iex/snapshot/<mkt>_<YYYY-MM>.rsc.gz (see 02_download_iex_snapshot.py).
Each 15-min block has MCV (MW, unconstrained market clearing volume), final_scheduled_volume (FSV, MW, after market
splitting) and congestion = YES/NO (IEX flag).

DERIVED metrics (computed here, documented in notes/transmission.md):
  blocks_total, blocks_congested, share_of_blocks_congested (%)
  mcv_total_MU, fsv_total_MU                         = sum(MW) * 0.25 h / 1000
  volume_curtailed_due_to_congestion_MU              = sum over congested blocks of max(MCV - FSV, 0) * 0.25 / 1000
Also writes the per-block flags to data/processed/transmission/iex_congestion_blocks_<mkt>.csv.gz (wide, compact).
"""
import csv, glob, gzip, json, os, re
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission/iex/snapshot")
OUT = os.path.join(ROOT, "data/processed/transmission")
REC = re.compile(r'\{"date":"(\d\d-\d\d-\d{4})","period":"(\d\d:\d\d)\s*-\s*(\d\d:\d\d)","purchase_bid":"([^"]*)","sell_bid":"([^"]*)","mcv":"([^"]*)","final_scheduled_volume":"([^"]*)","mcp":"([^"]*)","congestion":"([A-Z]*)"\}')
SID = {"dam": "TRN-IEX-DAM-SNAP", "rtm": "TRN-IEX-RTM-SNAP"}
NAME = {"dam": "IEX Day-Ahead Market", "rtm": "IEX Real-Time Market"}
rows = []
for mk in ("dam", "rtm"):
    bw = gzip.open(os.path.join(OUT, f"iex_congestion_blocks_{mk}.csv.gz"), "wt", newline="")
    bwc = csv.writer(bw); bwc.writerow(["date", "block_start", "mcv_MW", "fsv_MW", "mcp_Rs_per_MWh", "congestion"])
    for f in sorted(glob.glob(os.path.join(RAW, f"{mk}_*.rsc.gz"))):
        ym = re.search(r"_(\d{4}-\d{2})\.rsc", f).group(1)
        s = gzip.open(f, "rt", encoding="utf-8").read()
        recs = {}
        for m in REC.finditer(s):
            d, a, b, pb, sb, mcv, fsv, mcp, cg = m.groups()
            iso = f"{d[6:]}-{d[3:5]}-{d[:2]}"
            if iso[:7] != ym:
                continue
            recs[(iso, a)] = (float(mcv or 0), float(fsv or 0), mcp, cg)
        if not recs:
            continue
        n = len(recs); nc = sum(1 for v in recs.values() if v[3] == "YES")
        mcv = sum(v[0] for v in recs.values()) * 0.25 / 1000
        fsv = sum(v[1] for v in recs.values()) * 0.25 / 1000
        lost = sum(max(v[0] - v[1], 0) for v in recs.values() if v[3] == "YES") * 0.25 / 1000
        days = len({k[0] for k in recs})
        y, m = map(int, ym.split("-"))
        import calendar
        ps, pe = f"{ym}-01", f"{ym}-{calendar.monthrange(y, m)[1]:02d}"
        note = f"{NAME[mk]}; derived from {n} 15-min blocks over {days} days of the IEX market snapshot"
        for metric, val, unit in (("blocks_total", n, "count"), ("blocks_congested", nc, "count"),
                                  ("share_of_blocks_congested", round(100 * nc / n, 2), "%"),
                                  ("mcv_total", round(mcv, 3), "MU"), ("fsv_total", round(fsv, 3), "MU"),
                                  ("volume_curtailed_due_to_congestion", round(lost, 3), "MU"),
                                  ("volume_curtailed_due_to_congestion_share_of_mcv", round(100 * lost / mcv, 3) if mcv else "", "%")):
            rows.append(dict(geography="India", period_start=ps, period_end=pe, granularity="monthly",
                             metric=f"{mk}_{metric}", value=val, unit=unit, source_id=SID[mk],
                             notes=note + ("; DERIVED" if metric != "blocks_total" else "")))
        for (iso, a), v in sorted(recs.items()):
            bwc.writerow([iso, a, v[0], v[1], v[2], v[3]])
    bw.close()

cerc = os.path.join(OUT, "_cerc_congestion_rows.csv")   # written by 12_parse_cerc_mmc.py, merged here if present
if os.path.exists(cerc):
    rows += list(csv.DictReader(open(cerc)))
with open(os.path.join(OUT, "market_congestion_monthly.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["geography", "period_start", "period_end", "granularity", "metric", "value", "unit", "source_id", "notes"])
    w.writeheader(); w.writerows(rows)
print("rows", len(rows))
