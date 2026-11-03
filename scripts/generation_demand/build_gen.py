"""Assemble monthly / FY / state-wise generation and demand CSVs (tasks 3 and 4).

Inputs (run first): cea_re_parse.py, cea_psp_parse.py; Ember CSVs in data/raw/generation_demand/ember/;
NEP / LGBR text extracts in data/raw/generation_demand/cea/.
Outputs in data/processed/generation_demand/:
  gen_monthly_india.csv, gen_fy_india.csv, gen_statewise.csv,
  demand_cea_psp_monthly.csv, demand_fy.csv, demand_projections.csv
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/generation_demand"
WORK = ROOT / "data/processed/generation_demand/_work"
OUT = ROOT / "data/processed/generation_demand"
COLS = ["geography", "period_start", "period_end", "granularity", "metric", "value", "unit", "source_id", "notes"]

STATE_FIX = {
    "J & K": "Jammu and Kashmir", "Jammu & Kashmir": "Jammu and Kashmir", "UT of J&K and Ladakh": "Jammu and Kashmir and Ladakh",
    "Andaman & Nicobar": "Andaman and Nicobar Islands", "Andaman Nicobar": "Andaman and Nicobar Islands",
    "Andaman & Nicobar Islands": "Andaman and Nicobar Islands", "Andaman- Nicobar": "Andaman and Nicobar Islands",
    "Andaman and Nicobar": "Andaman and Nicobar Islands",
    "Orissa": "Odisha", "Keralam": "Kerala", "Daman & Diu": "Daman and Diu",
    "Dadra & Nagar Haveli and Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Dadra & Nagar Haveli": "Dadra and Nagar Haveli", "Pondicherry": "Puducherry",
    "All India Total": "India", "All India": "India", "India Total": "India",
    "North Eastern Region": "North-Eastern Region", "North-Eastern Region": "North-Eastern Region",
    "DVC": "Damodar Valley Corporation (DVC)", "Haveli": "Dadra and Nagar Haveli", "Nagar Haveli": "Dadra and Nagar Haveli",
    "North-Eastern": "North-Eastern Region", "Andaman-": "Andaman and Nicobar Islands",
    "Andaman- Nicobar": "Andaman and Nicobar Islands", "Telenagana": "Telangana",
    "U T of J &K and Ladakh": "Jammu and Kashmir and Ladakh", "Others": "Others (misc. ISTS entities)",
    "Arunachal": "Arunachal Pradesh", "Nicobar": "Andaman and Nicobar Islands",
    "Region": "North-Eastern Region",  # wrapped label 'North-Eastern / Region' in 2015-17 peak reports (checked)
}


def norm_state(s):
    s0 = str(s).strip()
    flag = ""
    if re.search(r"[*#$]|\(#+\)|\(\*\)", s0):
        flag = s0
    s1 = re.sub(r"\([#*$ ]+\)|[*#$]", "", s0).strip()
    s1 = re.sub(r"^d\s*/\s*", "", s1).strip()
    if re.search(r"DVC$", s1):
        s1 = "DVC"
    s1 = re.sub(r"\s+", " ", s1)
    return STATE_FIX.get(s1, s1), flag


def month_end(ym):
    p = pd.Period(ym, "M")
    return p.start_time.strftime("%Y-%m-%d"), p.end_time.strftime("%Y-%m-%d")


def fy_bounds(start_ym):
    y = int(start_ym[:4])
    return f"{y}-04-01", f"{y + 1}-03-31"


# --------------------------------------------------------------------------- CEA RE monthly
def cea_re():
    ov = pd.read_csv(WORK / "cea_re_overview.csv")
    ov["fmt"] = "xls"
    pdf = pd.read_csv(WORK / "cea_re_overview_pdf.csv")
    # only PDFs in the 7-category summary layout (2019-08 onward) parse reliably; earlier layouts skipped
    full = pdf.groupby("report_month").category.apply(lambda c: {"Small Hydro", "Others"} <= set(c))
    pdf = pdf[pdf.report_month.isin(full[full].index) & (pdf.report_month >= "2019-08")]
    pdf = pdf[~pdf.report_month.isin(set(ov.report_month))]
    pdf["fmt"] = "pdf"
    ov = pd.concat([ov[ov.kind != "capacity"], pdf.drop(columns=["how"])], ignore_index=True)
    sw = pd.read_csv(WORK / "cea_re_statewise.csv")
    monthly, fy, state = [], [], []
    srcmap = {"Wind": "wind", "Solar": "solar", "Biomass": "biomass", "Bagasse": "bagasse",
              "Small Hydro": "small_hydro", "Others": "other_re", "Large Hydro": "large_hydro",
              "Total": "re_total", "Total Including Large Hydro": "re_total_incl_large_hydro",
              "Total Excluding Large Hydro": "re_total_excl_large_hydro"}
    ov["metric"] = ov.category.map(srcmap)
    ov = ov[ov.metric.notna()]
    # Overview "Total" = RE excl. large hydro in reports before Large Hydro was added (pre 2023-07 overview)
    # ... and RE incl. large hydro in reports that list a Large Hydro row (checked: 2024-03 Total = sum incl. large hydro)
    with_lh = set(ov[ov.category == "Large Hydro"].report_month)
    ov.loc[(ov.metric == "re_total") & ov.report_month.isin(with_lh), "metric"] = "re_total_incl_large_hydro"
    ov.loc[ov.metric == "re_total", "metric"] = "re_total_excl_large_hydro"
    # monthly: prefer the value printed as the report's own month; else latest report quoting it as previous year
    m = ov[ov.kind == "month"].copy()
    m["own"] = m.start == m.report_month
    m = m.sort_values(["metric", "start", "own", "report_month"], ascending=[True, True, False, False])
    m = m.drop_duplicates(["metric", "start"])
    for r in m.itertuples():
        ps, pe = month_end(r.start)
        note = (f"CEA RE report {r.report_month} ({r.file}, {r.fmt}); "
                + ("current-month column" if r.own else "previous-year comparison column (no own-month Excel report)"))
        monthly.append(["India", ps, pe, "monthly", f"gen_{r.metric}", r.value, "MU", "GEN-CEA-RE-MONTHLY", note])
    # FY totals: ranges Apr..Mar
    f = ov[(ov.kind == "range") & (ov.start.str[5:] == "04") & (ov.end.str[5:] == "03")].copy()
    f["own"] = f.end == f.report_month
    f = f.sort_values(["metric", "start", "own", "report_month"], ascending=[True, True, False, False])
    f = f.drop_duplicates(["metric", "start"])
    for r in f.itertuples():
        ps, pe = fy_bounds(r.start)
        note = f"CEA RE report {r.report_month} ({r.file}, {r.fmt}); April-March cumulative column" + (
            "" if r.own else " (previous-FY comparison column)")
        fy.append(["India", ps, pe, "FY", f"gen_{r.metric}", r.value, "MU", "GEN-CEA-RE-MONTHLY", note])
    # state-wise
    sw["metric"] = sw.source.map(srcmap)
    sw["geo"], sw["flag"] = zip(*sw.state.map(norm_state))
    sw = sw[~sw.geo.str.startswith("#")]
    # 2023-10 report: Large Hydro column is all zero in the source-wise sheet while the overview shows 11240 MU ->
    # treat as a source artefact: drop those rows so the 2024-10 report's previous-year column is used instead
    bad = sw[(sw.geo == "India") & (sw.metric == "large_hydro") & (sw.which == "current") & (sw.value == 0)].report_month
    sw = sw[~((sw.metric == "large_hydro") & sw.report_month.isin(set(bad)))]
    sw["own"] = sw.which == "current"
    sw = sw.sort_values(["geo", "metric", "period", "own", "report_month"], ascending=[True, True, True, False, False])
    sw = sw.drop_duplicates(["geo", "metric", "period"])
    for r in sw.itertuples():
        ps, pe = month_end(r.period)
        note = f"CEA RE report {r.report_month}; " + ("current-month column" if r.own else "previous-year column")
        if r.flag:
            note += f"; source label '{r.flag}' (CEA: * = provisional/carried from earlier report; # see report note)"
        if r.metric == "re_total":
            note += "; state total = sum of sources shown (includes Large Hydro from 2023-07 reports onward)"
        state.append([r.geo, ps, pe, "monthly", f"gen_{r.metric}", r.value, "MU", "GEN-CEA-RE-MONTHLY", note])
    return monthly, fy, state


# --------------------------------------------------------------------------- Ember
def ember():
    monthly, yearly, state = [], [], []
    g = pd.read_csv(RAW / "ember/release_generation_monthly_global.csv")
    g = g[g["Area"] == "India"]
    for r in g.itertuples(index=False):
        src = re.sub(r"[^a-z0-9]+", "_", r[4].lower()).strip("_")
        ps, pe = month_end(r[2][:7])
        if pd.notna(r[6]):
            monthly.append(["India", ps, pe, "monthly", f"gen_{src}" if src != "demand" else "demand", r[6], "TWh",
                            "GEN-EMBER-MONTHLY-GLOBAL", "Ember monthly electricity data (India); 'Generation (TWh)'"])
        if pd.notna(r[9]) and src not in ("demand",):
            monthly.append(["India", ps, pe, "monthly", f"share_{src}", r[9], "%", "GEN-EMBER-MONTHLY-GLOBAL",
                            "Ember 'Share of generation (%)'"])
    y = pd.read_csv(RAW / "ember/release_generation_yearly_global.csv")
    y = y[(y["Area"] == "India") & (y["Year"] >= 2010)]
    for r in y.itertuples(index=False):
        src = re.sub(r"[^a-z0-9]+", "_", r[4].lower()).strip("_")
        ps, pe = f"{r[2]}-01-01", f"{r[2]}-12-31"
        if pd.notna(r[6]):
            yearly.append(["India", ps, pe, "annual", f"gen_{src}" if src != "demand" else "demand", r[6], "TWh",
                           "GEN-EMBER-YEARLY-GLOBAL", "Ember yearly electricity data (India), calendar year"])
        if pd.notna(r[9]) and src != "demand":
            yearly.append(["India", ps, pe, "annual", f"share_{src}", r[9], "%", "GEN-EMBER-YEARLY-GLOBAL",
                           "Ember 'Share of generation (%)', calendar year"])
    # India state-level (Ember India dataset)
    for fn, gran in (("india_monthly_full_release_long_format.csv", "monthly"),
                     ("india_yearly_full_release_long_format.csv", "annual")):
        s = pd.read_csv(RAW / "ember" / fn)
        s = s[(s.Category == "Electricity generation") & (s.Value.notna())]
        sid = "GEN-EMBER-INDIA-STATES-M" if gran == "monthly" else "GEN-EMBER-INDIA-STATES-Y"
        for r in s.itertuples(index=False):
            geo, _ = norm_state(r.State)
            if gran == "monthly":
                ps, pe = month_end(r.Date[:7])
            else:
                ps, pe = f"{r.Year}-01-01", f"{r.Year}-12-31"
            v = re.sub(r"[^a-z0-9]+", "_", r.Variable.lower()).strip("_")
            metric = (f"gen_{v}" if r.Unit == "GWh" else f"share_{v}")
            unit = "MU" if r.Unit == "GWh" else r.Unit
            state.append([geo, ps, pe, gran, metric, r.Value, unit, sid,
                          f"Ember India state data ({r.Unit}; GWh = MU); state type: {r[4]}"])
    return monthly, yearly, state


# --------------------------------------------------------------------------- CEA PSP (energy requirement / peak)
REGION_LABELS = {"Northern Region": "Northern Region", "Western Region": "Western Region",
                 "Southern Region": "Southern Region", "Eastern Region": "Eastern Region",
                 "North-Eastern Region": "North-Eastern Region", "North Eastern Region": "North-Eastern Region"}


def cea_psp():
    d = pd.read_csv(WORK / "cea_psp_monthly.csv")
    d = d[d.entity_raw.notna() & (d.entity_raw.str.len() > 1)]
    d["geo"], d["flag"] = zip(*d.entity_raw.map(norm_state))
    d["geo"] = d.geo.map(lambda x: STATE_FIX.get(x, x))
    monthly, fyrows = [], []
    sid = {"energy": "GEN-CEA-PSP-ENERGY", "peak": "GEN-CEA-PSP-PEAK"}
    for r in d.itertuples():
        if r.scope == "month":
            ps, pe = month_end(r.report_month)
            sign = ("; NB value printed negative in source (deficit sign convention)"
                    if "not_" in r.metric and r.value < 0 else "")
            monthly.append([r.geo, ps, pe, "monthly", r.metric, r.value, r.unit, sid[r.kind],
                            f"CEA PSP {r.kind} report {r.report_month} ({r.status or 'status n/a'}); label '{r.entity_raw}'{sign}"])
        else:
            y, mo = int(r.report_month[:4]), int(r.report_month[5:])
            fy0 = y if mo >= 4 else y - 1
            ps = f"{fy0}-04-01"
            pe = pd.Period(r.report_month, "M").end_time.strftime("%Y-%m-%d")
            if mo == 3:
                fyrows.append([r.geo, ps, pe, "FY", r.metric, r.value, r.unit, sid[r.kind],
                               f"CEA PSP {r.kind} report {r.report_month} ({r.status or 'status n/a'}), April-March cumulative"
                               + ("; peak = max of the FY" if r.kind == "peak" else "")
                               + ("; NB value printed negative in source (deficit sign convention)"
                                  if "not_" in r.metric and r.value < 0 else "")])
    return monthly, fyrows


def write(rows, name):
    df = pd.DataFrame(rows, columns=COLS)
    df = df.drop_duplicates()
    df.to_csv(OUT / name, index=False)
    print(name, len(df))
    return df


def main():
    m1, f1, s1 = cea_re()
    m2, y2, s2 = ember()
    write(m1 + m2, "gen_monthly_india.csv")
    write(f1 + y2, "gen_fy_india.csv")
    write(s1 + s2, "gen_statewise.csv")
    pm, pf = cea_psp()
    write(pm, "demand_cea_psp_monthly.csv")
    lg = pd.read_csv(WORK / "lgbr_fy.csv")
    nep = pd.read_csv(WORK / "nep_projections.csv")
    nep["metric"] = nep.metric.str.replace("_nucl_", "_nuclear_").str.replace("_pv_", "_solar_pv_").str.replace(
        "_wind_power_", "_wind_")
    act = lg[~lg.metric.str.contains("anticipated")]
    write(pf + act.values.tolist(), "demand_fy.csv")
    write(lg[lg.metric.str.contains("anticipated")].values.tolist() + nep.values.tolist(), "demand_projections.csv")
    write(pd.read_csv(WORK / "all_time_highs.csv").values.tolist(), "all_time_highs_snapshot.csv")


if __name__ == "__main__":
    main()
