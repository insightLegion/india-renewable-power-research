"""Build the 15-minute all-India demand/generation series from the PSP 'TimeSeries' sheet / page, plus
DERIVED typical daily profiles by month and VRE-share / net-load extremes.

Input : data/processed/generation_demand/_work/psp_ts_15min.csv  (psp_parse.py)
Output: data/processed/generation_demand/hourly_india.csv            (wide; 15-min instantaneous SCADA values)
        data/processed/generation_demand/profile_by_month_derived.csv  (DERIVED)
        data/processed/generation_demand/vre_extremes_derived.csv      (DERIVED)
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "data/processed/generation_demand/_work"
OUT = ROOT / "data/processed/generation_demand"

MAP = [  # (regex on header label, standard column)
    (r"^FREQ", "frequency_hz"),
    (r"^STORAGE DEMAND", "storage_demand_mw"),
    (r"^NET DEMAND", "net_demand_met_mw"),
    (r"^DEMAND MET", "demand_met_mw"),
    (r"^NUCLEAR", "nuclear_mw"), (r"^WIND", "wind_mw"), (r"^SOLAR", "solar_mw"), (r"^HYDRO", "hydro_mw"),
    (r"^GAS", "gas_mw"), (r"^THERMAL", "thermal_mw"), (r"^STORAGE", "storage_gen_mw"), (r"^OTHERS", "others_mw"),
    (r"^TOTAL GEN", "total_generation_mw"), (r"TRANSNATIONAL", "net_transnational_mw"),
]
STD = ["demand_met_mw", "net_demand_met_mw", "solar_mw", "wind_mw", "hydro_mw", "thermal_mw", "gas_mw", "nuclear_mw",
       "storage_demand_mw", "storage_gen_mw", "others_mw", "total_generation_mw", "net_transnational_mw",
       "frequency_hz"]


def header_cols(h):
    labels = [x.strip() for x in str(h).split("|")][1:]  # drop TIME
    cols = []
    for lab in labels:
        u = lab.upper()
        std = ""
        for pat, name in MAP:
            if re.search(pat, u):
                std = name
                break
        cols.append(std)
    return cols


def main():
    ts = pd.read_csv(WORK / "psp_ts_15min.csv", dtype=str)
    ts["header"] = ts.header.fillna("")
    ts["nvals"] = ts["values"].fillna("").str.count(";") + 1
    # xls headers carry names; pdf headers do not -> borrow the xls header layout with the same value count
    xls_hdr = ts[ts.header.str.contains("DEMAND", na=False)][["date", "header", "nvals"]].drop_duplicates(["header"])
    recs = []
    hdr_by_n = {}
    for r in xls_hdr.itertuples():
        cols = header_cols(r.header)
        n_nonempty = len([c for c in cols])
        hdr_by_n.setdefault(r.nvals, (cols, r.date))
    rows = []
    for (date, hdr, f), g in ts.groupby(["date", "header", "file"], sort=False):
        if "DEMAND" in hdr:
            cols = header_cols(hdr)
            how = "xls header"
        else:
            # PDF: values omit blank spacer columns; use the xls layout with blank columns removed
            n = int(g.nvals.iloc[0])
            cand = [(c, d) for (k, (c, d)) in hdr_by_n.items() if len([x for x in c if x]) == n]
            if not cand:
                continue
            cols = [x for x in cand[0][0] if x]
            how = f"pdf; column layout from xls header of {cand[0][1]}"
        for r in g.itertuples():
            vals = r.values.split(";")
            if "DEMAND" not in hdr:
                pass
            d = {"date": date, "time": r.time, "file": f, "how": how}
            for c, v in zip(cols, vals):
                if c and v != "":
                    d[c] = float(v)
            rows.append(d)
    df = pd.DataFrame(rows)
    df["time"] = df.time.str.zfill(5)
    df["period_start"] = df.date + "T" + df.time
    df = df.sort_values(["period_start", "file"]).drop_duplicates("period_start", keep="last")
    ps = pd.to_datetime(df.period_start)
    df["period_end"] = (ps + pd.Timedelta(minutes=15)).dt.strftime("%Y-%m-%dT%H:%M")
    df["geography"] = "India"
    df["granularity"] = "15min"
    df["source_id"] = "GEN-GI-PSP-DAILY"
    df["notes"] = "instantaneous SCADA value at time stamp; " + df.file + " (" + df.how + ")"
    for c in STD:
        if c not in df:
            df[c] = np.nan
    out = df[["geography", "period_start", "period_end", "granularity"] + STD + ["source_id", "notes"]]
    out.to_csv(OUT / "hourly_india.csv", index=False)
    print("hourly_india.csv", len(out), out.period_start.min(), out.period_start.max(), df.date.nunique(), "days")

    # ------------------------------------------------------------- DERIVED profiles
    x = df.copy()
    x["month"] = x.date.str[:7]
    x["tod"] = x.time
    x["vre_mw"] = x.solar_mw + x.wind_mw
    x["net_load_mw"] = x.demand_met_mw - x.solar_mw - x.wind_mw
    x["vre_share_pct"] = 100 * x.vre_mw / x.demand_met_mw
    prof = x.groupby(["month", "tod"]).agg(
        n_days=("date", "nunique"), demand_met_mw=("demand_met_mw", "mean"), solar_mw=("solar_mw", "mean"),
        wind_mw=("wind_mw", "mean"), net_load_mw=("net_load_mw", "mean"), vre_share_pct=("vre_share_pct", "mean"),
        thermal_mw=("thermal_mw", "mean"), hydro_mw=("hydro_mw", "mean")).reset_index().round(1)
    prof.insert(0, "note", "DERIVED: mean over days of 15-min instantaneous values; net_load = demand_met - solar - wind")
    prof.to_csv(OUT / "profile_by_month_derived.csv", index=False)
    # extremes
    ext = []
    for col, asc, lab in (("vre_share_pct", False, "highest solar+wind share of demand"),
                          ("net_load_mw", True, "lowest net load (demand - solar - wind)"),
                          ("solar_mw", False, "highest solar output")):
        top = x.dropna(subset=[col]).sort_values(col, ascending=asc).head(25)
        for r in top.itertuples():
            ext.append({"criterion": lab, "period_start": r.period_start, "demand_met_mw": r.demand_met_mw,
                        "solar_mw": r.solar_mw, "wind_mw": r.wind_mw, "net_load_mw": r.net_load_mw,
                        "vre_share_pct": round(r.vre_share_pct, 2), "file": r.file})
    # monthly: block with max VRE share & min net load per month
    for m, g in x.dropna(subset=["vre_share_pct"]).groupby("month"):
        a = g.loc[g.vre_share_pct.idxmax()]
        b = g.loc[g.net_load_mw.idxmin()]
        for r, lab in ((a, "monthly max solar+wind share"), (b, "monthly min net load")):
            ext.append({"criterion": lab, "period_start": r.period_start, "demand_met_mw": r.demand_met_mw,
                        "solar_mw": r.solar_mw, "wind_mw": r.wind_mw, "net_load_mw": r.net_load_mw,
                        "vre_share_pct": round(r.vre_share_pct, 2), "file": r.file})
    e = pd.DataFrame(ext)
    e.insert(0, "note", "DERIVED from hourly_india.csv (15-min instantaneous all-India SCADA values)")
    e.to_csv(OUT / "vre_extremes_derived.csv", index=False)
    print("derived rows", len(prof), len(e))


if __name__ == "__main__":
    main()
