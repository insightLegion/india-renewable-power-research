"""Assemble Daily PSP outputs from _work/psp_parsed.csv (output of psp_parse.py).

Outputs (data/processed/generation_demand/):
  psp_daily_india.csv, psp_daily_regions.csv, psp_daily_states.csv  (long, conventions format)
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "data/processed/generation_demand/_work"
OUT = ROOT / "data/processed/generation_demand"
COLS = ["geography", "period_start", "period_end", "granularity", "metric", "value", "unit", "source_id", "notes"]

STATES = {
    # PSP label -> (full name, region)
    "Punjab": ("Punjab", "NR"), "Haryana": ("Haryana", "NR"), "Rajasthan": ("Rajasthan", "NR"),
    "Delhi": ("Delhi", "NR"), "UP": ("Uttar Pradesh", "NR"), "Uttarakhand": ("Uttarakhand", "NR"),
    "HP": ("Himachal Pradesh", "NR"), "J&K": ("Jammu and Kashmir", "NR"),
    "J&K(UT) & Ladakh(UT)": ("Jammu and Kashmir and Ladakh", "NR"),
    "J&K(UT) and Ladakh(UT)": ("Jammu and Kashmir and Ladakh", "NR"),
    "Chandigarh": ("Chandigarh", "NR"), "Railways_NR ISTS": ("Railways (ISTS, NR)", "NR"),
    "Bulk Consumer_NR ISTS": ("Bulk consumers (ISTS, NR)", "NR"),
    "Chhattisgarh": ("Chhattisgarh", "WR"), "Gujarat": ("Gujarat", "WR"), "MP": ("Madhya Pradesh", "WR"),
    "Maharashtra": ("Maharashtra", "WR"), "Goa": ("Goa", "WR"), "DD": ("Daman and Diu", "WR"),
    "DNH": ("Dadra and Nagar Haveli", "WR"), "DNHDDPDCL": ("Dadra and Nagar Haveli and Daman and Diu", "WR"),
    "Essar steel": ("Essar Steel (bulk consumer)", "WR"), "BALCO": ("BALCO (ISTS bulk consumer)", "WR"),
    "RIL JAMNAGAR": ("RIL Jamnagar (ISTS bulk consumer)", "WR"), "RIL Jamnagar": ("RIL Jamnagar (ISTS bulk consumer)", "WR"), "AMNSIL": ("AM/NS India (bulk consumer)", "WR"),
    "Bulk Consumer_WR ISTS": ("Bulk consumers (ISTS, WR)", "WR"),
    "Andhra Pradesh": ("Andhra Pradesh", "SR"), "Telangana": ("Telangana", "SR"), "Karnataka": ("Karnataka", "SR"),
    "Kerala": ("Kerala", "SR"), "Tamil Nadu": ("Tamil Nadu", "SR"), "Pondy": ("Puducherry", "SR"),
    "Puducherry": ("Puducherry", "SR"), "Bulk Consumer_SR ISTS": ("Bulk consumers (ISTS, SR)", "SR"),
    "Bihar": ("Bihar", "ER"), "DVC": ("Damodar Valley Corporation (DVC)", "ER"), "Jharkhand": ("Jharkhand", "ER"),
    "Odisha": ("Odisha", "ER"), "West Bengal": ("West Bengal", "ER"), "Sikkim": ("Sikkim", "ER"),
    "Bulk Consumer_ER ISTS": ("Bulk consumers (ISTS, ER)", "ER"), "Railways_ER ISTS": ("Railways (ISTS, ER)", "ER"),
    "Arunachal Pradesh": ("Arunachal Pradesh", "NER"), "Assam": ("Assam", "NER"), "Manipur": ("Manipur", "NER"),
    "Meghalaya": ("Meghalaya", "NER"), "Mizoram": ("Mizoram", "NER"), "Nagaland": ("Nagaland", "NER"),
    "Tripura": ("Tripura", "NER"), "Bulk Consumer_NER ISTS": ("Bulk consumers (ISTS, NER)", "NER"),
}
UNIT_FIX = {"HH:MM": "HH:MM (IST)"}


def main():
    d = pd.read_csv(WORK / "psp_parsed.csv", dtype={"value": str})
    # Year typos in 'Date of Reporting' (e.g. early-Jan-2014 reports print 2013): if the printed date is ~1 year
    # away from the file-title date but day/month agree, take the year from the file title.
    title = pd.to_datetime(d.file.str[:10], errors="coerce")
    rep = pd.to_datetime(d.report_date)
    gap = (title - rep).dt.days.abs()
    fix = gap.between(300, 400) & (title.dt.strftime("%m-%d") == rep.dt.strftime("%m-%d"))
    fix |= gap.between(300, 400) & (title.dt.strftime("%m-%d") == (rep + pd.Timedelta(days=1)).dt.strftime("%m-%d"))
    newrep = pd.Series([r.replace(year=t.year) if f else r for r, t, f in zip(rep, title, fix)], index=d.index)
    d["year_fixed"] = fix
    d["report_date"] = newrep.dt.strftime("%Y-%m-%d")
    d["date"] = (newrep - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    print("report-date year typos fixed:", d.loc[fix, "file"].nunique(), "files")
    d = d[d.date >= "2010-01-01"]
    # one report per data date: prefer xls over pdf, then the latest-uploaded file
    d["is_xls"] = d.file.str.contains(r"\.xlsx?$", case=False)
    files = d[["date", "file", "is_xls"]].drop_duplicates()
    files = files.sort_values(["date", "is_xls", "file"], ascending=[True, False, False])
    keep = files.drop_duplicates("date")
    dropped = files[~files.file.isin(keep.file)]
    if len(dropped):
        dropped.to_csv(WORK / "psp_duplicate_reports_dropped.csv", index=False)
    d = d[d.file.isin(keep.file)]
    d["period_start"] = d["date"]
    d["period_end"] = d["date"]
    d["granularity"] = "daily"
    d["source_id"] = "GEN-GI-PSP-DAILY"
    d["unit"] = d.unit.map(lambda u: UNIT_FIX.get(u, u))
    d["notes"] = "report dated " + d.report_date + "; file " + d.file + d.year_fixed.map(
        {True: "; printed reporting year corrected to file-title year (typo in report)", False: ""})
    d = d.drop_duplicates(["date", "level", "entity", "metric"])
    # flag printed RES share that disagrees with printed RES / total generation (source errors, e.g. 2024-03-12)
    num = pd.to_numeric(d.value, errors="coerce")
    k = ["date", "entity"]
    res = d[d.metric == "gen_res_wind_solar_biomass_others"].assign(r=num).set_index(k).r
    tot = d[d.metric == "gen_total"].assign(t=num).set_index(k).t
    chk = (100 * res / tot).rename("calc")
    sh = d[d.metric == "share_res_in_total_gen"].join(chk, on=k)
    badidx = sh.index[(pd.to_numeric(sh.value, errors="coerce") - sh.calc).abs() > 2]
    d.loc[badidx, "notes"] += "; WARNING printed share inconsistent with printed RES/Total generation (source error?)"
    print("inconsistent RES-share rows flagged:", len(badidx))
    ind = d[d.level == "India"].assign(geography="India")
    reg = d[d.level == "region"].assign(geography=d.entity)
    st = d[d.level == "state"].copy()
    unk = sorted(set(st.entity) - set(STATES))
    if unk:
        print("unmapped state labels:", unk)
    st["geography"] = st.entity.map(lambda e: STATES.get(e, (e, ""))[0])
    st["notes"] = ("region " + st.entity.map(lambda e: STATES.get(e, ("", "?"))[1]) + "; PSP label '" + st.entity
                   + "'; " + st.notes)
    for df, name in ((ind, "psp_daily_india.csv"), (reg, "psp_daily_regions.csv"), (st, "psp_daily_states.csv")):
        df = df.sort_values(["geography", "period_start", "metric"])
        df[COLS].to_csv(OUT / name, index=False)
        print(name, len(df), df.period_start.min(), df.period_start.max(), df.period_start.nunique())


if __name__ == "__main__":
    main()
