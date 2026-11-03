"""Build processed CSVs for topic capacity_storage.

Run after parse_cea_installed_capacity.py and parse_statewise.py:
  .venv/bin/python -I scripts/capacity_storage/build_outputs.py

Every hand-transcribed value below was read from the cited source (raw copy saved under
data/raw/capacity_storage/...). Rows marked DERIVED in notes are arithmetic on other rows in
the same file (inputs kept); nothing is interpolated or estimated.
"""
import csv
import os
import re

import pandas as pd
import pdfplumber

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RAW = os.path.join(ROOT, "data", "raw", "capacity_storage")
OUT = os.path.join(ROOT, "data", "processed", "capacity_storage")
COLS = ["geography", "period_start", "period_end", "granularity", "metric", "value", "unit", "source_id", "notes"]


def fy(fy_label):
    """'2024-25' -> ('2024-04-01', '2025-03-31')"""
    y = int(fy_label[:4])
    return f"{y}-04-01", f"{y + 1}-03-31"


def row(geo, ps, pe, gran, metric, value, unit, sid, notes=""):
    return dict(zip(COLS, [geo, ps, pe, gran, metric, value, unit, sid, notes]))


def snap(date, metric, value, unit, sid, notes="", geo="India"):
    return row(geo, date, date, "snapshot", metric, value, unit, sid, notes)


# ---------------------------------------------------------------------------------------------
# 1) Monthly national series: CEA monthly reports (+ a few MNRE national monthly points)
# ---------------------------------------------------------------------------------------------
cea = pd.read_csv(os.path.join(OUT, "_cea_installed_capacity_monthly.csv"))
extra = [
    # MNRE state-wise PDF 31.01.2026, 'Total (MW)' row (solar components only; state rows misaligned)
    snap("2026-01-31", "solar_ground_mounted_capacity", 107256.75, "MW", "CAP-021", "MNRE state-wise PDF as on 31.01.2026, Total row"),
    snap("2026-01-31", "solar_rooftop_capacity", 24298.55, "MW", "CAP-021", "MNRE: RTS incl. PM-Surya Ghar; Total row"),
    snap("2026-01-31", "solar_hybrid_component_capacity", 3364.63, "MW", "CAP-021", "MNRE Total row"),
    snap("2026-01-31", "solar_offgrid_kusum_capacity", 5681.80, "MW", "CAP-021", "MNRE: Off-grid solar/KUSUM Comp.B; Total row"),
    # PIB backgrounders (MNRE figures)
    snap("2026-06-30", "solar_capacity", 162.15, "GW", "CAP-045", "PIB backgrounder 31 Jul 2026: solar 'till 30 June 2026'"),
    snap("2026-06-30", "solar_large_projects_capacity", 118.79, "GW", "CAP-045", "PIB backgrounder: 'Large solar projects contribute 118.79 GW' (date context: June 2026)"),
    snap("2026-06-30", "solar_rooftop_capacity", 27.88, "GW", "CAP-045", "PIB backgrounder: grid-connected rooftop 27.88 GW (date context: June 2026)"),
    snap("2026-07-31", "solar_capacity", 164.59, "GW", "CAP-044", "PIB backgrounder 13 Aug 2026"),
    snap("2026-07-31", "wind_capacity", 58.14, "GW", "CAP-044", "PIB backgrounder 13 Aug 2026"),
    snap("2026-07-31", "bio_power_capacity_total", 11.75, "GW", "CAP-044", "PIB backgrounder 13 Aug 2026"),
    snap("2026-07-31", "hydro_capacity_large_plus_small", 57.24, "GW", "CAP-044", "PIB: 'Cumulative capacity of hydro power is 57.24 GW (as of 31 July 2026), including large and small hydro'"),
    snap("2026-07-31", "non_fossil_capacity_total", 300.50, "GW", "CAP-044", "PIB: non-fossil 300.50 GW, 'over 54%' of total"),
    snap("2026-07-31", "total_installed_capacity", 552, "GW", "CAP-044", "PIB: 'Around 552 GW in July 2026' (rounded)"),
    snap("2026-08-12", "solar_rooftop_capacity_pm_surya_ghar", 14.8, "GW", "CAP-044", "PIB: cumulative 14.8 GW rooftop commissioned under PM Surya Ghar (as of 12.08.2026)"),
    snap("2025-11-30", "renewable_capacity_incl_large_hydro", 253.96, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2025-11-30", "solar_capacity", 132.85, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2025-11-30", "wind_capacity", 53.99, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2025-11-30", "bio_power_capacity_total", 11.61, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2025-11-30", "small_hydro_capacity", 5.16, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2025-11-30", "large_hydro_capacity", 50.35, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2025-11-30", "nuclear_capacity", 8.78, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2025-11-30", "non_fossil_capacity_total", 262.74, "GW", "CAP-041", "MNRE: 51.55% of 509.64 GW"),
    snap("2025-11-30", "thermal_capacity_total", 246.90, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2025-11-30", "total_installed_capacity", 509.64, "GW", "CAP-041", "MNRE year-end review 2025"),
    snap("2024-11-30", "renewable_capacity_incl_large_hydro", 205.52, "GW", "CAP-041", "MNRE year-end review 2025 (comparison figure)"),
    snap("2024-11-30", "solar_capacity", 94.17, "GW", "CAP-041", "MNRE year-end review 2025 (comparison figure)"),
    snap("2024-11-30", "wind_capacity", 47.96, "GW", "CAP-041", "MNRE year-end review 2025 (comparison figure)"),
]
for r in extra:
    r["granularity"] = "monthly"
monthly = pd.concat([cea, pd.DataFrame(extra)], ignore_index=True)
monthly = monthly.sort_values(["period_start", "metric", "source_id"])
monthly.to_csv(os.path.join(OUT, "re_capacity_india_monthly.csv"), index=False)

# ---------------------------------------------------------------------------------------------
# 2) FY series
# ---------------------------------------------------------------------------------------------
fyrows = []
# 2a) CEA 31-March stocks
mar = cea[cea.period_start.str.endswith("-03-31")]
for _, r in mar.iterrows():
    y = int(r.period_start[:4])
    fyrows.append(row("India", f"{y - 1}-04-01", r.period_start, "FY", r.metric + "_fy_end", r.value, "MW", "CAP-001",
                      "Stock as on 31 March (end of FY) from CEA monthly report; " + str(r.notes)))
# 2b) DERIVED net additions and shares from CEA March stocks
pv = mar.pivot_table(index="period_start", columns="metric", values="value", aggfunc="first")
dates = sorted(pv.index)
for m in ["solar_capacity", "wind_capacity", "res_mnre_capacity", "large_hydro_capacity", "total_installed_capacity"]:
    for a, b in zip(dates[:-1], dates[1:]):
        if int(b[:4]) - int(a[:4]) != 1 or pd.isna(pv.at[a, m]) or pd.isna(pv.at[b, m]):
            continue
        fyrows.append(row("India", f"{a[:4]}-04-01", b, "FY", m.replace("_capacity", "") + "_net_addition_cea_derived",
                          round(pv.at[b, m] - pv.at[a, m], 2), "MW", "CAP-001",
                          f"DERIVED: CEA {m} on {b} minus on {a} (net of retirements/revisions)"))
for d in dates:
    tot = pv.at[d, "total_installed_capacity"] if "total_installed_capacity" in pv else None
    if pd.isna(tot):
        continue
    y = int(d[:4])
    for num_m, name in [("res_mnre_capacity", "res_mnre_share_of_total_capacity_cea_derived"),
                        ("renewable_capacity_incl_large_hydro", "re_incl_large_hydro_share_of_total_capacity_cea_derived")]:
        num = pv.at[d, num_m] if num_m in pv and not pd.isna(pv.at[d, num_m]) else None
        if num_m == "renewable_capacity_incl_large_hydro" and num is None:
            if not pd.isna(pv.at[d, "res_mnre_capacity"]) and not pd.isna(pv.at[d, "large_hydro_capacity"]):
                num = pv.at[d, "res_mnre_capacity"] + pv.at[d, "large_hydro_capacity"]
        if num is None:
            continue
        fyrows.append(row("India", f"{y - 1}-04-01", d, "FY", name, round(100 * num / tot, 2), "%", "CAP-001",
                          f"DERIVED: {num_m} (or RES+hydro) / total_installed_capacity, CEA as on {d}"))
    sw = [pv.at[d, k] for k in ("solar_capacity", "wind_capacity") if k in pv]
    if len(sw) == 2 and not any(pd.isna(x) for x in sw):
        fyrows.append(row("India", f"{y - 1}-04-01", d, "FY", "solar_plus_wind_share_of_total_capacity_cea_derived",
                          round(100 * (sw[0] + sw[1]) / tot, 2), "%", "CAP-001",
                          f"DERIVED: (solar+wind from RES break-up)/total, CEA as on {d}; RES break-up date may lag"))

# 2c) MNRE RE Statistics 2024-25 Table 1.1 and Table 2.1 (GW), parsed from the PDF text
with pdfplumber.open(os.path.join(RAW, "mnre", "statewise", "20251106791170361.pdf")) as pdf:
    t11 = pdf.pages[18].extract_text()
    t21 = pdf.pages[22].extract_text()
for line in t11.split("\n"):
    m = re.match(r"^(20\d\d-\d\d) ((?:[\d.]+ ?){7,})", line)
    if m:
        v = [float(x) for x in m.group(2).split() if re.fullmatch(r"\d+(\.\d+)?", x)]
        ps, pe = fy(m.group(1))
        names = ["thermal_capacity_fy_end", "nuclear_capacity_fy_end", "non_re_capacity_fy_end", "large_hydro_capacity_fy_end",
                 "res_mnre_capacity_fy_end", "renewable_capacity_incl_large_hydro_fy_end", "total_installed_capacity_fy_end"]
        for n, x in zip(names, v[:7]):
            fyrows.append(row("India", ps, pe, "FY", n, x, "GW", "CAP-011", "MNRE RE Statistics 2024-25 Table 1.1 (sources MNRE & CEA)"))
        shares = v[-2:]
        fyrows.append(row("India", ps, pe, "FY", "res_mnre_share_of_total_capacity", shares[0], "%", "CAP-011", "MNRE RE Statistics 2024-25 Table 1.1 'Share(%) RES'"))
        fyrows.append(row("India", ps, pe, "FY", "re_incl_large_hydro_share_of_total_capacity", shares[1], "%", "CAP-011", "MNRE RE Statistics 2024-25 Table 1.1 'Share(%) RE'"))
for line in t21.split("\n"):
    m = re.match(r"^(20\d\d-\d\d) ((?:[\d.]+ ?){6,})", line)
    if m:
        v = [float(x) for x in m.group(2).split()]
        ps, pe = fy(m.group(1))
        names = ["small_hydro_capacity_fy_end", "wind_capacity_fy_end", "biomass_power_cogen_capacity_fy_end", "waste_to_energy_capacity_fy_end",
                 "solar_capacity_fy_end", "res_mnre_capacity_fy_end"]
        for n, x in zip(names, v[:6]):
            fyrows.append(row("India", ps, pe, "FY", n, x, "GW", "CAP-011", "MNRE RE Statistics 2024-25 Table 2.1"))

# 2d) MNRE FY 2025-26, 2024-25 and other MNRE/PIB FY facts
P = "PIB 08 Apr 2026 (MNRE)"
ps, pe = fy("2025-26")
for n, x in [("solar_capacity_fy_end", 150.26), ("wind_capacity_fy_end", 56.09), ("bio_power_capacity_fy_end", 11.75),
             ("small_hydro_capacity_fy_end", 5.17), ("large_hydro_capacity_fy_end", 51.41),
             ("renewable_capacity_incl_large_hydro_fy_end", 274.68), ("nuclear_capacity_fy_end", 8.78), ("non_fossil_capacity_fy_end", 283.46)]:
    fyrows.append(row("India", ps, pe, "FY", n, x, "GW", "CAP-040", f"{P}: as on 31.03.2026"))
for n, x, note in [("non_fossil_capacity_addition", 55.29, "highest ever; previous highest 29.5 GW in 2024-25"),
                   ("solar_capacity_addition", 44.61, "MNRE"), ("wind_capacity_addition", 6.05, "highest ever"),
                   ("solar_distributed_capacity_addition", 16.3, "DRE solar = 36% of 44.61 GW; includes 7.6 GW PM-KUSUM and 8.7 GW rooftop"),
                   ("solar_pm_kusum_capacity_addition", 7.6, "part of DRE"), ("solar_rooftop_capacity_addition", 8.7, "part of DRE")]:
    fyrows.append(row("India", ps, pe, "FY", n, x, "GW", "CAP-040", f"{P}: {note}"))
fyrows.append(row("India", "2013-04-01", "2014-03-31", "FY", "renewable_capacity_incl_large_hydro_fy_end", 76.38, "GW", "CAP-040", f"{P}: March 2014"))
fyrows.append(row("India", "2013-04-01", "2014-03-31", "FY", "solar_capacity_fy_end", 2.82, "GW", "CAP-040", f"{P}: March 2014"))
fyrows.append(row("India", "2013-04-01", "2014-03-31", "FY", "wind_capacity_fy_end", 21.04, "GW", "CAP-040", f"{P}: March 2014"))
ps, pe = fy("2024-25")
P = "PIB 10 Apr 2025 (MNRE)"
for n, x, note in [("renewable_capacity_incl_large_hydro_fy_end", 220.10, "as on 31.03.2025"),
                   ("renewable_capacity_addition", 29.52, "record annual addition"),
                   ("solar_capacity_addition", 23.83, ""), ("wind_capacity_addition", 4.15, ""),
                   ("solar_capacity_fy_end", 105.65, ""), ("solar_ground_mounted_capacity_fy_end", 81.01, ""),
                   ("solar_rooftop_capacity_fy_end", 17.02, ""), ("solar_hybrid_component_capacity_fy_end", 2.87, ""),
                   ("solar_offgrid_capacity_fy_end", 4.74, ""), ("wind_capacity_fy_end", 50.04, ""),
                   ("bio_power_capacity_fy_end", 11.58, "includes 0.53 GW off-grid and waste-to-energy"),
                   ("small_hydro_capacity_fy_end", 5.10, "")]:
    fyrows.append(row("India", ps, pe, "FY", n, x, "GW", "CAP-042", f"{P}; {note}".strip("; ")))
ps, pe = fy("2023-24")
fyrows.append(row("India", ps, pe, "FY", "renewable_capacity_incl_large_hydro_fy_end", 198.75, "GW", "CAP-042", "PIB 10 Apr 2025: 'up from 198.75 GW in the previous fiscal'"))
fyrows.append(row("India", ps, pe, "FY", "solar_capacity_addition", 15.03, "GW", "CAP-042", "PIB 10 Apr 2025 (previous-year comparison)"))
fyrows.append(row("India", ps, pe, "FY", "wind_capacity_addition", 3.25, "GW", "CAP-042", "PIB 10 Apr 2025 (previous-year comparison)"))
for fyl, mw in [("2023-24", 3253), ("2024-25", 4151), ("2025-26", 6057)]:
    ps, pe = fy(fyl)
    fyrows.append(row("India", ps, pe, "FY", "wind_capacity_addition", mw, "MW", "CAP-032", "PIB 22 Jul 2026 (MNRE, Lok Sabha) table"))
# MoP: FY 2025-26 additions till 31.01.2026
ps, pe = fy("2025-26")
for n, x in [("coal_capacity_addition_ytd", 8810), ("hydro_capacity_addition_ytd", 3370), ("wind_capacity_addition_ytd", 4612.58),
             ("solar_capacity_addition_ytd", 34955.24), ("bio_power_capacity_addition_ytd", 30.61), ("small_hydro_capacity_addition_ytd", 58.06),
             ("renewable_capacity_addition_ytd", 43026.49), ("nuclear_capacity_addition_ytd", 700), ("total_capacity_addition_ytd", 52536.49)]:
    fyrows.append(row("India", ps, "2026-01-31", "FY", n, x, "MW", "CAP-043", "PIB 12 Mar 2026 (MoP, Lok Sabha) Annexure-I: FY 2025-26 till 31.01.2026 (partial FY)"))
# MNRE solar sub-category breakdowns at FY end from MNRE tables (India totals)
sw = pd.read_csv(os.path.join(OUT, "re_capacity_statewise.csv"))
ind = sw[(sw.geography == "India") & sw.period_start.isin(["2024-03-31", "2025-03-31", "2026-03-31"]) &
         sw.metric.str.startswith(("solar", "wind", "small_hydro", "bio_power", "large_hydro", "re_capacity"))]
for _, r in ind.iterrows():
    y = int(r.period_start[:4])
    fyrows.append(row("India", f"{y - 1}-04-01", r.period_start, "FY", r.metric + "_fy_end", r.value, "MW", r.source_id,
                      "India total row of MNRE state-wise table; " + r.notes))
fydf = pd.DataFrame(fyrows).sort_values(["period_start", "metric", "source_id"])
fydf = fydf.drop_duplicates(subset=["period_start", "period_end", "metric", "value", "unit", "source_id"])
fydf.to_csv(os.path.join(OUT, "re_capacity_india_fy.csv"), index=False)

# ---------------------------------------------------------------------------------------------
# 3) Ember annual capacity (calendar-year end, GW) and cross-check with CEA December values
# ---------------------------------------------------------------------------------------------
e = pd.read_csv(os.path.join(RAW, "ember", "release_generation_yearly_global.csv"), low_memory=False)
e = e[(e.Area == "India") & (e.Year >= 2014) & e["Capacity (GW)"].notna()]
erows = []
for _, r in e.iterrows():
    src = r["Electricity source"]
    if src in ("Total generation", "Demand", "Net imports"):
        continue
    erows.append(row("India", f"{int(r.Year)}-01-01", f"{int(r.Year)}-12-31", "annual",
                     "capacity_" + re.sub(r"[^a-z]+", "_", src.lower()).strip("_"), r["Capacity (GW)"], "GW", "CAP-005",
                     "Ember yearly electricity data, 'Capacity (GW)' (end-of-year capacity per Ember methodology)"))
pd.DataFrame(erows).to_csv(os.path.join(OUT, "ember_capacity_india_annual.csv"), index=False)
dec = cea[cea.period_start.str.endswith("-12-31")].pivot_table(index="period_start", columns="metric", values="value", aggfunc="first")
xc = []
for _, r in e.iterrows():
    d = f"{int(r.Year)}-12-31"
    for esrc, cm in [("Solar", "solar_capacity"), ("Wind", "wind_capacity"), ("Bioenergy", "bio_power_capacity"), ("Nuclear", "nuclear_capacity")]:
        if r["Electricity source"] == esrc and d in dec.index and cm in dec and not pd.isna(dec.at[d, cm]):
            cv = dec.at[d, cm] / 1000
            xc.append({"date": d, "technology": esrc, "ember_gw": r["Capacity (GW)"], "cea_gw": round(cv, 3),
                       "diff_ember_minus_cea_gw": round(r["Capacity (GW)"] - cv, 3), "source_ids": "CAP-005;CAP-001",
                       "notes": "DERIVED comparison; CEA value from monthly report as on 31 Dec (RES break-up date may lag)"})
pd.DataFrame(xc).to_csv(os.path.join(OUT, "capacity_crosscheck_ember_vs_cea.csv"), index=False)

# ---------------------------------------------------------------------------------------------
# 4) Pipeline & targets
# ---------------------------------------------------------------------------------------------
pl = []
P = "PIB 29 Dec 2025 MNRE year-end review: table 'as on 30.11.2025'"
for sector, inst, ui, tend, tot in [("solar", 132.85, 69.12, 35.46, 237.43), ("wind", 53.99, 30.11, 1.80, 85.90),
                                     ("bio_energy", 11.61, None, None, 11.61), ("small_hydro", 5.16, 0.44, None, 5.60),
                                     ("hybrid_rtc_fdre", None, 59.24, 11.48, 70.72), ("res_subtotal", 203.61, 158.91, 48.74, 411.26),
                                     ("large_hydro", 50.35, 25.33, None, 75.68), ("total_re", 253.96, 184.24, 48.74, 486.94),
                                     ("nuclear", 8.78, 6.60, 7.00, 22.38), ("total_non_fossil", 262.74, 190.84, 55.74, 509.32)]:
    for status, v in [("installed", inst), ("under_implementation", ui), ("tendered", tend), ("installed_plus_pipeline", tot)]:
        if v is not None:
            pl.append(snap("2025-11-30", f"{sector}_{status}", v, "GW", "CAP-041", P))
P = "PIB 10 Apr 2025 (MNRE), as on 31.03.2025"
pl += [snap("2025-03-31", "total_re_under_implementation", 169.40, "GW", "CAP-042", P),
       snap("2025-03-31", "total_re_tendered", 65.06, "GW", "CAP-042", P),
       snap("2025-03-31", "hybrid_rtc_peak_thermal_bundled_in_pipeline", 65.29, "GW", "CAP-042", P + "; 'This includes 65.29 GW from emerging solutions such as hybrid systems, RTC, peaking power, thermal+RE bundling'")]
P = "PIB 02 Apr 2026 (MoP, Lok Sabha)"
pl += [snap("2026-01-31", "re_under_construction_total", 154830, "MW", "CAP-046", P + ": 'under construction (till January 2026)'"),
       snap("2026-01-31", "solar_under_construction", 64670, "MW", "CAP-046", P),
       snap("2026-01-31", "wind_under_construction", 6490, "MW", "CAP-046", P),
       snap("2026-01-31", "hybrid_under_construction", 59990, "MW", "CAP-046", P),
       snap("2026-01-31", "re_planning_stage_total", 47920, "MW", "CAP-046", P + ": 'at various stages of planning and targeted to be completed by 2029-30'"),
       snap("2026-01-31", "solar_planning_stage", 35440, "MW", "CAP-046", P),
       snap("2026-01-31", "hybrid_planning_stage", 10080, "MW", "CAP-046", P),
       snap("2025-12-31", "reia_letters_of_award_capacity", 69, "GW", "CAP-047", "PIB 03 Feb 2026: SECI, NTPC, NHPC, SJVN LoAs ~69 GW as on 31.12.2025"),
       snap("2025-12-31", "reia_ppa_signed_against_loas", 24.3, "GW", "CAP-047", "PIB 03 Feb 2026: PPAs signed ~24.3 GW against these LoAs"),
       snap("2025-09-30", "reia_loas_with_unsigned_psa", 43942, "MW", "CAP-048", "PIB 04 Nov 2025: LoAs issued where PSAs remain unsigned, as of 30.09.2025"),
       snap("2025-09-30", "reia_psa_signed_since_apr2023", 24928, "MW", "CAP-048", "PIB 04 Nov 2025: PSAs signed since April 2023"),
       snap("2026-08-13", "wind_under_implementation", 28, "GW", "CAP-044", "PIB 13 Aug 2026: 'Around 28 GW of additional wind capacity is under implementation'"),
       snap("2026-01-31", "upcoming_wind_solar_for_ists_integration", 207, "GW", "CAP-056", "PIB 09 Mar 2026: ISTS under implementation for ~207 GW upcoming wind and solar"),
       snap("2026-01-31", "re_capacity_commissioned", 263, "GW", "CAP-056", "PIB 09 Mar 2026: 'As of January 2026, the RE Capacity commissioned is around 263 GW'"),
       ]
# CEA quarterly under-construction RE (location-based state table, page 3)
UC = [("Quarterly_Report_on_Under_construction_Renewable_Energy_Proj_Q4-2026_451c8b6f.pdf", "2026-03-31"),
      ("Quarterly_Report_on_Under_construction_Renewable_Energy_Proj_Q2-2026_1759edca.pdf", "2026-09-30")]
STATES = ["Andhra Pradesh", "Assam", "Chhattisgarh", "Gujarat", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
          "Madhya Pradesh", "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana", "Uttar Pradesh",
          "West Bengal", "Location yet to be decided", "Yet to be finalized", "Grand Total"]
for fn, date in UC:
    with pdfplumber.open(os.path.join(RAW, "cea", "re_under_construction", fn)) as pdf:
        txt = pdf.pages[2].extract_text()
    flat = re.sub(r"\s+", " ", txt)
    for st in STATES:
        m = re.search(re.escape(st) + r" ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.]+)", flat, re.I)
        if not m:
            continue
        vals = [None if x == "-" else float(x) for x in m.groups()]
        hyb, sol, wnd, tot = vals
        ok = abs(sum(v for v in (hyb, sol, wnd) if v) - tot) < 1
        geo = "India" if st == "Grand Total" else ("Location not yet decided" if "decided" in st or "finalized" in st else st)
        note = f"CEA Quarterly Report on Under-construction RE Projects ({date}), location-based state summary (projects mostly >=25 MW; excludes rooftop/off-grid)"
        for name, v in [("hybrid", hyb), ("solar", sol), ("wind", wnd), ("total", tot)]:
            if v is None:
                continue
            if not ok and name == "hybrid":
                pl.append(row(geo, date, date, "snapshot", "re_under_construction_hybrid", None, "MW", "CAP-004",
                              note + f"; NOT RECORDED: extracted hybrid value {v} inconsistent with row total {tot}"))
                continue
            pl.append(row(geo, date, date, "snapshot", f"re_under_construction_{name}", v, "MW", "CAP-004", note))
# Targets / projections
P = "PIB 31 May 2023: CEA National Electricity Plan (Generation) 2022-32"
for yr, items in [("2026-27", [("coal", 235133), ("gas", 24824), ("nuclear", 13080), ("large_hydro", 52446), ("solar", 185566), ("wind", 72895),
                               ("small_hydro", 5200), ("biomass", 13000), ("pumped_storage", 7446), ("total", 609591), ("bess_mw", 8680)]),
                  ("2031-32", [("coal", 259643), ("gas", 24824), ("nuclear", 19680), ("large_hydro", 62178), ("solar", 364566), ("wind", 121895),
                               ("small_hydro", 5450), ("biomass", 15500), ("pumped_storage", 26686), ("total", 900422), ("bess_mw", 47244)])]:
    ps, pe = fy(yr)
    for k, v in items:
        pl.append(row("India", ps, pe, "FY", f"nep2023_projected_capacity_{k}", v, "MW", "CAP-049", P + f"; likely installed capacity by end of {yr}" + ("; 2031-32 total excludes 5856 MW hydro imports" if yr == "2031-32" and k == "total" else "")))
pl.append(row("India", *fy("2026-27"), "FY", "nep2023_projected_non_fossil_share_of_capacity", 57.4, "%", "CAP-049", P))
pl.append(row("India", *fy("2031-32"), "FY", "nep2023_projected_non_fossil_share_of_capacity", 68.4, "%", "CAP-049", P))
pl.append(row("India", "2023-04-01", "2023-04-30", "monthly", "non_fossil_share_of_capacity", 42.5, "%", "CAP-049", P + ": 'around 42.5% as on April 2023'"))
pl.append(row("India", *fy("2031-32"), "FY", "nep_projected_capacity_total_mop_2026_statement", 873736, "MW", "CAP-046",
              "PIB 02 Apr 2026 (MoP): NEP projects ~8,73,736 MW by 2031-32 incl. 3,64,566 solar, 1,21,895 wind, 15,500 biomass, 5,450 SHP (differs from 900,422 MW in May-2023 release)"))
pl.append(row("India", *fy("2029-30"), "FY", "target_non_fossil_capacity", 500, "GW", "CAP-041", "Government target: 500 GW non-fossil capacity by 2030 (PIB 29 Dec 2025)"))
for yl in ["2023-24", "2024-25", "2025-26", "2026-27", "2027-28"]:
    pl.append(row("India", *fy(yl), "FY", "reia_bidding_trajectory", 50, "GW", "CAP-046", "PIB 02 Apr 2026: MNRE bidding trajectory of 50 GW per annum by REIAs FY 2023-24 to FY 2027-28"))
pl.append(row("India", *fy("2029-30"), "FY", "ists_planned_to_integrate_non_fossil", 500, "GW", "CAP-056", "PIB 09 Mar 2026: GEC + ISTS planned to integrate over 500 GW non-fossil by 2030 (over 600 GW by 2032)"))
pl.append(snap("2025-06-30", "non_fossil_share_of_capacity_milestone", 50, "%", "CAP-041", "PIB 29 Dec 2025: 50% of installed capacity from non-fossil reached in June 2025"))
pdf_ = pd.DataFrame(pl)
pdf_.to_csv(os.path.join(OUT, "re_pipeline_targets.csv"), index=False)

# ---------------------------------------------------------------------------------------------
# 5) Storage capacity
# ---------------------------------------------------------------------------------------------
SCOLS = ["geography", "period_start", "period_end", "granularity", "technology", "status", "metric", "value", "unit", "source_id", "notes"]
st = []


def srow(date, tech, status, metric, value, unit, sid, notes="", ps=None, gran="snapshot", geo="India"):
    st.append(dict(zip(SCOLS, [geo, ps or date, date, gran, tech, status, metric, value, unit, sid, notes])))


# 5a) CEA BESS status reports
STATUS = {"In Operation": "operational", "Under Construction": "under_construction", "Awarded Projects": "awarded",
          "In Tender Stage": "tendered", "Total (1+2+3+4)": "total_all_stages"}
bdir = os.path.join(RAW, "cea", "bess_status")
for fn in sorted(os.listdir(bdir)):
    if not fn.endswith(".pdf"):
        continue
    with pdfplumber.open(os.path.join(bdir, fn)) as pdf:
        txt = "\n".join(p.extract_text() or "" for p in pdf.pages)
    d = re.search(r"as on (\d\d)\.(\d\d)\.(\d{4})", txt)
    date = f"{d.group(3)}-{d.group(2)}-{d.group(1)}"
    for label, status in STATUS.items():
        m = re.search(r"\d " + re.escape(label) + r"[@*#]?\s+(\d+)\s+([\d,.]+)\s+([\d,.]+)", txt)
        if not m:
            print("BESS: no match", label, fn)
            continue
        n, mw, mwh = int(m.group(1)), float(m.group(2).replace(",", "")), float(m.group(3).replace(",", ""))
        note = f"CEA 'Status of development and deployment of BESS in India' as on {date} (projects >=1 MWh; data source stated as IESA in Jun-Sep 2026 reports)"
        if status == "tendered":
            note += "; includes FDRE projects whose storage capacity is yet to be finalised"
        if status == "under_construction":
            note += "; all projects with PPA/BESPA signed are counted as under construction"
        if status == "operational":
            note += "; includes grid-connected projects in merchant sale"
        srow(date, "BESS", status, "bess_projects_count", n, "count", "CAP-002", note)
        srow(date, "BESS", status, "bess_power_capacity", mw, "MW", "CAP-002", note)
        srow(date, "BESS", status, "bess_energy_capacity", mwh, "MWh", "CAP-002", note)
    m = re.search(r"upto March(?:\s+2025)?\s+([\d.]+)\s+([\d.]+)", txt)
    if m:
        srow("2025-03-31", "BESS", "operational", "bess_power_capacity", float(m.group(1)), "MW", "CAP-002", f"CEA BESS report as on {date}: year-wise profile, commissioned up to March 2025")
        srow("2025-03-31", "BESS", "operational", "bess_energy_capacity", float(m.group(2)), "MWh", "CAP-002", f"CEA BESS report as on {date}: year-wise profile, commissioned up to March 2025")
    m = re.search(r"\n2025-26\s+([\d.]+)\s+([\d.]+)", txt)
    if m:
        srow("2026-03-31", "BESS", "commissioned_in_period", "bess_power_capacity_added", float(m.group(1)), "MW", "CAP-002", f"CEA BESS report as on {date}: commissioned during FY 2025-26 (value differs between reports)", ps="2025-04-01", gran="FY")
        srow("2026-03-31", "BESS", "commissioned_in_period", "bess_energy_capacity_added", float(m.group(2)), "MWh", "CAP-002", f"CEA BESS report as on {date}: commissioned during FY 2025-26 (value differs between reports)", ps="2025-04-01", gran="FY")
    if date == "2026-09-30":
        # expected commissioning profile by FY (latest report only)
        for yl in ["2026-27", "2027-28", "2028-29", "2029-30"]:
            mm = re.search(r"\n" + yl + r"((?:[ \t]+[\d.]+)+)", txt)
            if not mm:
                continue
            v = [float(x) for x in mm.group(1).split()]
            ps, pe = fy(yl)
            labels = (["operational_or_uc", "awarded", "tendered", "total"] if len(v) == 8 else
                      ["operational", "under_construction", "awarded", "tendered", "total"])
            # 2026-27 row has 5 pairs (in operation, UC, awarded, tendering, total); later rows 4 pairs (UC, awarded, tendering, total)
            if len(v) == 10:
                labels = ["already_commissioned", "under_construction", "awarded", "tendered", "total"]
            elif len(v) == 8:
                labels = ["under_construction", "awarded", "tendered", "total"]
            for k, lab in enumerate(labels):
                srow(pe, "BESS", "planned", f"bess_expected_commissioning_{lab}_mw", v[2 * k], "MW", "CAP-002",
                     f"CEA BESS report as on {date}: expected commissioning in FY {yl} of projects currently '{lab}' (CEA estimate per MoP guideline timelines)", ps=ps, gran="FY")
                srow(pe, "BESS", "planned", f"bess_expected_commissioning_{lab}_mwh", v[2 * k + 1], "MWh", "CAP-002",
                     f"CEA BESS report as on {date}: expected commissioning in FY {yl} of projects currently '{lab}'", ps=ps, gran="FY")

# 5b) CEA PSP status reports (MW, installed capacity > 25 MW)
PSP = {
    "2017-03-31": dict(operational=4785.60, under_construction=1080, dpr_concurred=1000),
    "2018-03-31": dict(operational=4785.60, under_construction=1205, dpr_concurred=1000),
    "2019-03-31": dict(operational=4785.60, under_construction=1205, dpr_concurred=1000, survey_investigation=3820),
    "2020-03-31": dict(operational=4785.60, under_construction=1580, dpr_concurred=1000, survey_investigation=7380),
    "2021-03-31": dict(operational=4785.60, under_construction=1580, dpr_concurred=1000, under_examination=1200, survey_investigation=7530),
    "2022-03-31": dict(operational=4745.60, under_construction=1580, dpr_concurred=2200, survey_investigation=8855),
    "2024-03-31": dict(operational=4745.60, under_construction=2780.00, dpr_concurred=2350.00),
    "2025-04-01": dict(operational=4745.60, under_construction=8950.00),
    "2026-03-31": dict(operational=7175.60, under_construction=16120.00, dpr_concurred=6580, survey_investigation=93110, potential=288595.6),
    "2026-09-30": dict(operational=7425.60, under_construction=15870, dpr_concurred=10400, survey_investigation=96500, potential=347122.6),
}
SMAP = {"operational": "operational", "under_construction": "under_construction", "dpr_concurred": "planned",
        "survey_investigation": "planned", "under_examination": "planned", "potential": "potential"}
for date, dd in PSP.items():
    for k, v in dd.items():
        note = f"CEA 'Status of Pumped Storage Development in India' report (listed month {date[:7]}); category '{k}'"
        if k == "operational":
            note += "; CEA 'in operation/constructed' list (2017-21 reports flag several units as not working in pumping mode)"
        if k == "survey_investigation":
            note += "; schemes under survey & investigation"
        if k == "potential":
            note += "; identified PSP potential"
        srow(date, "PSP", SMAP[k], f"psp_capacity_{k}", v, "MW", "CAP-003", note)
srow("2026-09-30", "PSP", "operational", "psp_projects_count", 10, "count", "CAP-003", "CEA PSP report Sep 2026: 10 PSPs in operation (8 on-stream, 2 off-stream)")
srow("2026-09-30", "PSP", "under_construction", "psp_projects_count", 11, "count", "CAP-003", "CEA PSP report Sep 2026")
# PIB PSP backgrounder Oct 2026
P = "PIB backgrounder 19 Oct 2026 (CEA data)"
srow("2026-08-31", "PSP", "operational", "psp_capacity_operational", 7.43, "GW", "CAP-055", P + ": 10 projects (>25 MW), as of August 2026")
srow("2026-08-31", "PSP", "under_construction", "psp_capacity_under_construction", 15.87, "GW", "CAP-055", P + ": 11 PSPs under construction/implementation")
srow("2026-08-31", "PSP", "planned", "psp_capacity_concurred_or_appraised", 10.40, "GW", "CAP-055", P + ": 8 projects concurred/appraised by CEA")
srow("2026-08-31", "PSP", "potential", "psp_capacity_identified_potential", 345.38, "GW", "CAP-055", P + ": 320 projects identified")
for yl, add, cum in [("2025-26", 2.68, 7.425), ("2026-27", 2.92, 10.345), ("2027-28", 1.6, 11.945), ("2028-29", 6.35, 18.295),
                     ("2029-30", 13.5, 31.795), ("2030-31", 21.19, 52.985), ("2031-32", 8.8, 61.785), ("2032-33", 14.59, 76.375),
                     ("2033-34", 11.88, 88.255), ("2034-35", 5.7, 93.955), ("2035-36", 11.6, 105.555)]:
    ps, pe = fy(yl)
    srow(pe, "PSP", "planned", "psp_capacity_addition_projected", add, "GW", "CAP-055", P + ": CEA projected PSP capacity addition pathway", ps=ps, gran="FY")
    srow(pe, "PSP", "planned", "psp_capacity_cumulative_projected", cum, "GW", "CAP-055", P + ": CEA projected cumulative PSP capacity", ps=ps, gran="FY")
srow("2025-03-31", "PSP", "operational", "psp_capacity_cumulative_projected_baseline", 4.745, "GW", "CAP-055", P + ": 'Up to 2024-25' cumulative in CEA pathway table")

# 5c) Requirements / projections
P = "PIB 31 May 2023: NEP 2022-32"
for yl, tech, mw, mwh in [("2026-27", "BESS", 8.68, 34.72), ("2026-27", "PSP", 7.45, 47.65), ("2026-27", "BESS+PSP", 16.13, 82.37),
                          ("2031-32", "BESS", 47.24, 236.22), ("2031-32", "PSP", 26.69, 175.18), ("2031-32", "BESS+PSP", 73.93, 411.4)]:
    ps, pe = fy(yl)
    srow(pe, tech, "required", "storage_power_capacity_required", mw, "GW", "CAP-049", P, ps=ps, gran="FY")
    srow(pe, tech, "required", "storage_energy_capacity_required", mwh, "GWh", "CAP-049", P, ps=ps, gran="FY")
ps, pe = fy("2029-30")
srow(pe, "BESS+PSP", "required", "storage_power_capacity_required", 60.63, "GW", "CAP-047", "PIB 03 Feb 2026: CEA 'Optimal Generation Mix 2030' requirement by 2029-30", ps=ps, gran="FY")
srow(pe, "PSP", "required", "storage_power_capacity_required", 18.98, "GW", "CAP-047", "PIB 03 Feb 2026: CEA 'Optimal Generation Mix 2030'", ps=ps, gran="FY")
srow(pe, "BESS", "required", "storage_power_capacity_required", 41.65, "GW", "CAP-047", "PIB 03 Feb 2026: CEA 'Optimal Generation Mix 2030'", ps=ps, gran="FY")
srow(pe, "BESS+PSP", "required", "storage_energy_capacity_required", 336, "GWh", "CAP-050", "PIB 18 Dec 2025: CEA estimate 'about 336 GWh by 2029-30' (and ~411 GWh by 2031-32)", ps=ps, gran="FY")
ps, pe = fy("2031-32")
srow(pe, "BESS", "required", "bess_investment_required", 3.49, "lakh crore Rs", "CAP-051", "PIB 27 Jul 2026: estimated investment for BESS by 2031-32 (NEP)", ps=ps, gran="FY")
srow(pe, "PSP", "required", "psp_investment_required", 1.29, "lakh crore Rs", "CAP-051", "PIB 27 Jul 2026: estimated investment for PSP by 2031-32 (NEP)", ps=ps, gran="FY")
srow(pe, "PSP", "planned", "psp_transmission_planned", 35.6, "GW", "CAP-056", "PIB 09 Mar 2026: NEP Vol-II transmission planned for 35.6 GW PSP up to 2031-32", ps=ps, gran="FY")
srow(pe, "BESS", "planned", "bess_considered_for_transmission_integration", 47, "GW", "CAP-056", "PIB 09 Mar 2026: ~47 GW BESS considered for integration by 2031-32", ps=ps, gran="FY")

# 5d) Market trackers (Mercom, JMK/IEEFA) and VGF progress
M = "Mercom India Research"
srow("2025-12-31", "BESS", "operational", "bess_energy_capacity_cumulative", 1082, "MWh", "CAP-062", M + " (pv magazine India 25 Mar 2026): cumulative installed as of 31 Dec 2025")
srow("2025-12-31", "BESS", "commissioned_in_period", "bess_energy_capacity_added", 547, "MWh", "CAP-062", M + ": added in calendar 2025", ps="2025-01-01", gran="annual")
srow("2024-12-31", "BESS", "commissioned_in_period", "bess_energy_capacity_added", 433, "MWh", "CAP-062", M + ": added in calendar 2024", ps="2024-01-01", gran="annual")
srow("2025-12-31", "BESS", "commissioned_in_period", "bess_energy_capacity_added", 442.7, "MWh", "CAP-060", M + " Q1 2026 report: added in Q4 2025 (note: slightly inconsistent with 547 MWh full-year figure)", ps="2025-10-01", gran="quarterly")
srow("2026-03-31", "BESS", "commissioned_in_period", "bess_energy_capacity_added", 4.6, "GWh", "CAP-060", M + ": added in Q1 2026", ps="2026-01-01", gran="quarterly")
srow("2026-03-31", "BESS", "operational", "bess_energy_capacity_cumulative", 5.9, "GWh", "CAP-060", M + ": cumulative as of March 2026; standalone 73%, solar+wind+storage (RTC) 15%, solar+storage 11%")
srow("2026-06-30", "BESS", "commissioned_in_period", "bess_energy_capacity_added", 3.6, "GWh", "CAP-061", M + ": added in Q2 2026 (standalone ~98%)", ps="2026-04-01", gran="quarterly")
srow("2026-06-30", "BESS", "commissioned_in_period", "bess_energy_capacity_added", 8.2, "GWh", "CAP-061", M + ": added in 1H 2026", ps="2026-01-01", gran="half-year")
srow("2025-06-30", "BESS", "commissioned_in_period", "bess_energy_capacity_added", 98.4, "MWh", "CAP-061", M + ": added in 1H 2025", ps="2025-01-01", gran="half-year")
srow("2026-06-30", "BESS", "operational", "bess_energy_capacity_cumulative", 9.3, "GWh", "CAP-061", M + ": cumulative at end of June 2026; standalone 83%")
for geo, sh, d, sid in [("Rajasthan", 42, "2026-03-31", "CAP-060"), ("Gujarat", 25, "2026-03-31", "CAP-060"), ("Maharashtra", 9, "2026-03-31", "CAP-060"),
                        ("Rajasthan", 36, "2026-06-30", "CAP-061"), ("Gujarat", 20, "2026-06-30", "CAP-061"), ("Maharashtra", 5, "2026-06-30", "CAP-061")]:
    srow(d, "BESS", "operational", "share_of_india_cumulative_bess_energy_capacity", sh, "%", sid, M + ": state share of cumulative installed storage", geo=geo)
srow("2026-03-31", "BESS", "pipeline", "storage_development_pipeline_energy", 69, "GWh", "CAP-060", M + ": pipeline Q1 2026 (41 GWh standalone, 11 GWh solar+wind+storage, 9 GWh solar+storage, 1 GWh RTC, 6 GWh unspecified)")
srow("2026-03-31", "BESS", "pipeline", "standalone_bess_pipeline_energy", 10, "GWh", "CAP-060", M + ": Gujarat standalone pipeline (largest)", geo="Gujarat")
srow("2026-03-31", "storage_all", "tendered", "storage_tendered_in_period", 18, "GW", "CAP-060", M + ": tenders issued in Q1 2026 (12 GW in Q4 2025)", ps="2026-01-01", gran="quarterly")
srow("2026-03-31", "BESS", "awarded", "standalone_storage_auctioned_in_period", 4, "GW", "CAP-060", M + ": 'auctioned more than 4 GW of standalone storage' in Q1 2026 (11.1 GW in Q4 2025)", ps="2026-01-01", gran="quarterly")
srow("2025-12-31", "storage_all", "tendered", "storage_tendered_in_period", 12, "GW", "CAP-060", M + ": Q4 2025 tenders", ps="2025-10-01", gran="quarterly")
srow("2025-12-31", "BESS", "awarded", "standalone_storage_auctioned_in_period", 11.1, "GW", "CAP-060", M + ": Q4 2025 auctions", ps="2025-10-01", gran="quarterly")
srow("2026-06-30", "storage_all", "tendered", "storage_tendered_in_period", 28, "GW", "CAP-061", M + ": storage tenders in 1H 2026", ps="2026-01-01", gran="half-year")
srow("2026-06-30", "storage_all", "awarded", "storage_auctioned_in_period", 9, "GW", "CAP-061", M + ": approximately 9 GW auctioned in 1H 2026", ps="2026-01-01", gran="half-year")
srow("2026-03-31", "PSP", "installed", "psp_capacity_installed", 7.2, "GW", "CAP-060", M + ": installed PSP capacity as of March 2026, of which 5.7 GW operational")
srow("2026-03-31", "PSP", "operational", "psp_capacity_operational", 5.7, "GW", "CAP-060", M)
srow("2026-03-31", "PSP", "pipeline", "psp_pipeline", 57.2, "GW", "CAP-060", M + ": PSP pipeline in various stages")
J = "JMK Research & IEEFA"
srow("2025-12-31", "BESS", "awarded", "standalone_bess_allocated_in_period", 10.4, "GW", "CAP-063", J + " (pv magazine India 19 May 2026): standalone BESS allocated in 2025 across 18 auctions; mostly 2-hour 2-cycle", ps="2025-01-01", gran="annual")
srow("2025-12-31", "storage_all", "tendered", "ess_tendered_cumulative", 90.7, "GW", "CAP-063", J + ": cumulative tendered ESS capacity grew from 6.8 GW in 2018 to 90.7 GW by 2025")
srow("2018-12-31", "storage_all", "tendered", "ess_tendered_cumulative", 6.8, "GW", "CAP-063", J)
srow("2026-03-31", "BESS", "operational", "grid_scale_bess_energy_capacity_cumulative", 1.8, "GWh", "CAP-063", J + ": 'around 1.8 GWh of grid-scale BESS capacity installed as of March 2026' (narrower scope than Mercom)")
srow("2026-08-31", "storage_all", "tendered", "storage_tendered_in_period", 3.16, "GW", "CAP-064", J + " EnergyWatts Sep 2026: tendered in August 2026 (all standalone BESS); plus 192 MW EPC tenders", ps="2026-08-01", gran="monthly")
srow("2026-08-31", "storage_all", "awarded", "storage_awarded_in_period", 3250, "MW", "CAP-064", J + ": awarded Aug 2026 = 2,500 MW FDRE + 750 MW/2,100 MWh standalone BESS (SECI 1,500 MW FDRE + 1,000 MW RTC thermal-mimic; WBSEDCL 300 MW, GUVNL 450 MW BESS)", ps="2026-08-01", gran="monthly")
srow("2026-08-31", "BESS", "commissioned_in_period", "ess_energy_capacity_added", 556, "MWh", "CAP-064", J + ": commissioned in August 2026", ps="2026-08-01", gran="monthly")
srow("2026-08-31", "BESS", "operational", "bess_energy_capacity_operational", 9.6, "GWh", "CAP-064", J + ": 'Operational energy storage capacity reached 9.6 GWh of BESS in FY2027 YTD' (wording ambiguous: cumulative vs FY-to-date)")
V = "PIB-reported Rajya Sabha reply by MoS Power (psuwatch.com 27 Jul 2026)"
for metric, val, note in [("vgf1_loa_energy", 12.7, "VGF scheme 1 (budgetary): LoAs issued"), ("vgf1_financial_closure_energy", 6.54, "VGF scheme 1: PPAs executed and financial closure"),
                          ("vgf1_commissioned_energy", 0.5, "VGF scheme 1: commissioned; Rs 168.04 crore VGF disbursed"),
                          ("vgf2_loa_energy", 22.43, "VGF scheme 2 (PSDF): LoAs issued"), ("vgf2_bespa_signed_energy", 19.65, "VGF scheme 2: BESPAs executed"),
                          ("vgf2_financial_closure_energy", 5, "VGF scheme 2: financial closure"), ("vgf_total_loa_energy", 35.1, "both schemes: LoAs"),
                          ("vgf_total_financial_closure_energy", 11.5, "both schemes: financial closure")]:
    status = "operational" if "commissioned" in metric else ("awarded" if "loa" in metric else "under_construction")
    srow("2026-07-27", "BESS", status, metric, val, "GWh", "CAP-065", f"{V}: {note}")
srow("2026-01-31", "BESS", "pipeline", "bess_capacity_cumulative_claimed", 7.5, "GWh", "CAP-065", "psuwatch related headline only: 'India's energy storage capacity surpasses 7.5 GWh & over 140 GWh in pipeline' (date not shown; treat as unverified)")
sdf = pd.DataFrame(st)
sdf = sdf[~sdf.metric.eq("bess_capacity_cumulative_claimed")]  # drop unverified headline
sdf = sdf.drop_duplicates(subset=["period_start", "period_end", "technology", "status", "metric", "value", "source_id"], keep="last")
sdf.to_csv(os.path.join(OUT, "storage_capacity.csv"), index=False)

# ---------------------------------------------------------------------------------------------
# 6) Storage policy timeline
# ---------------------------------------------------------------------------------------------
TL = ["date", "date_precision", "instrument", "issuer", "description", "parameter", "value", "unit", "source_id", "notes"]
tl = [
    ("2021-05", "month", "PLI scheme: National Programme on ACC Battery Storage", "Ministry of Heavy Industries", "50 GWh domestic ACC manufacturing; 10 GWh earmarked for grid-scale stationary storage", "outlay", 18100, "crore Rs", "CAP-054", "PIB 15 Dec 2025 says approved May 2021; PIB 18 Dec 2025 says June 2021"),
    ("2021-11", "month", "ISTS charges waiver for storage (initial)", "MoP", "Initial ISTS waiver for storage notified November 2021", "", None, "", "CAP-050", ""),
    ("2022-01", "month", "CERC: storage allowed in ancillary services", "CERC", "Storage-based resources allowed to provide secondary and tertiary reserves", "", None, "", "CAP-050", ""),
    ("2022-03", "month", "TBCB guidelines for BESS procurement", "MoP", "Tariff-based competitive bidding guidelines for procurement of BESS by distribution licensees", "", None, "", "CAP-050", ""),
    ("2022-07-22", "day", "MoP Order: RPO and Energy Storage Obligation trajectory till 2029-30", "MoP", "Introduced Energy Storage Obligation (energy basis, % of consumption; >=85% of stored energy from RE); corrigendum 19.09.2022", "", None, "", "CAP-070", "Read via MERC Statement of Reasons 2024 which reproduces the MoP ESO trajectory"),
    ("2022-10", "month", "ESS in Harmonised Master List of Infrastructure", "Ministry of Finance", "Access to long-tenure, lower-cost finance", "", None, "", "CAP-050", ""),
    ("2022-12", "month", "Electricity Rules amendment recognising ESS", "MoP", "ESS recognised across generation, transmission, distribution; DG-set users to shift to cleaner backup incl. storage", "", None, "", "CAP-050", ""),
    ("2023-03", "month", "High-Price Day-Ahead Market launched", "Power exchanges/CERC", "BESS power allowed to participate", "", None, "", "CAP-050", ""),
    ("2023-05-31", "day", "National Electricity Plan (Generation) 2022-32 notified", "CEA", "Storage need 16.13 GW/82.37 GWh by 2026-27; 73.93 GW/411.4 GWh by 2031-32", "storage_2031_32", 411.4, "GWh", "CAP-049", ""),
    ("2023-06-28", "day", "Resource Adequacy Planning guidelines", "MoP/CEA", "Energy storage included as planning resource", "", None, "", "CAP-050", ""),
    ("2023-09-06", "day", "Cabinet approves VGF scheme for BESS (scheme 1)", "Cabinet", "4,000 MWh BESS by 2030-31; VGF up to 40% of capital cost; outlay Rs 9,400 cr incl. budgetary support Rs 3,760 cr; >=85% capacity to DISCOMs", "capacity", 4000, "MWh", "CAP-053", ""),
    ("2023-09", "month", "National Framework for Promotion of Energy Storage Systems", "MoP", "Roadmap for deployment, market integration, regulation", "", None, "", "CAP-050", ""),
    ("2023-09", "month", "PSP enabling-infrastructure grant", "MoP", "Rs 1 crore/MW for first 200 MW, Rs 0.75 crore/MW thereafter", "grant_first_200MW", 1.0, "crore Rs/MW", "CAP-050", ""),
    ("2024-03", "month", "VGF scheme 1 capacity enlarged", "MoP", "Capacity raised from 4,000 MWh to 13,220 MWh within Rs 3,760 cr; VGF Rs 27 lakh/MWh (PIB Feb 2026); later stated as 13.8 GWh (Jul 2026 reply)", "capacity", 13220, "MWh", "CAP-047", "PIB 03 Apr 2025 gives 13,200 MWh and VGF reduced from Rs 96 lakh/MWh to Rs 46 lakh/MWh or 30% of capex"),
    ("2025-02", "month", "CEA advisory on co-locating ESS with solar", "CEA", "Storage of at least 10% of installed solar capacity, minimum 2 hours", "storage_share_of_solar", 10, "%", "CAP-050", ""),
    ("2025-06-09", "day", "VGF scheme 2 for BESS (PSDF)", "MoP", "30 GWh BESS; Rs 5,400 cr from PSDF; VGF Rs 18 lakh/MWh; 25 GWh to 15 states + 5 GWh NTPC", "capacity", 30, "GWh", "CAP-047", "Allocation detail from Rajya Sabha reply (CAP-065)"),
    ("2025-06-26", "day", "CERC Sharing of ISTS charges (Fourth Amendment) Regulations 2025", "CERC", "ISTS waiver trajectory for RE and BESS incl. force-majeure extension", "", None, "", "CAP-040", ""),
    ("2025-06-30", "day", "ISTS waiver: non-co-located BESS", "MoP", "100% waiver for BESS commissioned by June 2025; reduced in 25% annual steps thereafter", "", None, "", "CAP-051", ""),
    ("2028-06-30", "day", "ISTS waiver: co-located BESS and PSP", "MoP", "100% ISTS waiver (12 years) for co-located BESS commissioned up to June 2028; PSP with construction awarded by June 2028", "waiver_years", 12, "years", "CAP-054", "Deadline date, not issue date"),
    ("2025-08", "month", "CEA concurrence dispensed for closed-loop off-stream PSP", "MoP/CEA", "Statutory CEA concurrence not required for closed-loop off-stream PSPs", "", None, "", "CAP-050", ""),
    ("2025-09", "month", "CERC separate connectivity for non-solar hours; Electricity Rules amendment", "CERC/MoP", "Non-solar-hour connectivity; consumers may develop/own/lease/operate ESS", "", None, "", "CAP-050", ""),
    ("2025-12-15", "day", "BESS tariff decline reported", "MoP", "BESS cost ~Rs 10.18/kWh (2022-23 bids, 2 cycles/day) vs ~Rs 2.1/kWh recent bids without VGF (2 cycles); ~Rs 2.8/kWh at 1.5 cycles", "bess_cost_recent", 2.1, "Rs/kWh", "CAP-054", "2022-23 value 10.18 Rs/kWh"),
    ("2026-02-02", "day", "BCD exemption for Li-ion cell manufacturing capital goods (BESS)", "Ministry of Finance", "Effective 2 Feb 2026 to 31 Mar 2028", "", None, "", "CAP-040", ""),
    ("2026-03-30", "day", "CEA safety regulations amendment notified (BESS)", "CEA", "CEA (Measures relating to Safety and Electric Supply) (First Amendment) Regulations 2025 notified 30.03.2026 incl. BESS safety", "", None, "", "CAP-051", ""),
    ("2026-07-31", "day", "PM Surya Sarovar Yojana approved", "Cabinet", "5,000 MW floating solar with co-located storage >=2 h (10,000 MWh); outlay Rs 5,070 cr; sanction FY2026-27 to FY2030-31", "storage", 10000, "MWh", "CAP-044", ""),
    ("2026-08", "month", "MoP allows curtailed T-GNA power to charge co-located BESS", "MoP", "RE projects may use curtailed temporary GNA power to charge co-located BESS", "", None, "", "CAP-064", "As reported by JMK EnergyWatts Sep 2026 (Aug 2026 regulatory updates)"),
]
# ESO trajectory rows
for yl, pct in [("2024-25", 1.5), ("2025-26", 2.0), ("2026-27", 2.5), ("2027-28", 3.0), ("2028-29", 3.5), ("2029-30", 4.0)]:
    tl.append((fy(yl)[0], "FY", "Energy Storage Obligation trajectory", "MoP (order 22.07.2022)", f"ESO for FY {yl}: % of total energy consumed to be solar/wind energy with/through storage",
               "eso_share_of_consumption", pct, "%", "CAP-070", "MERC SoR 2024: trajectory 'exactly in accordance with the MoP Order'; notes the 20.10.2023 EC Act notification has no ESO trajectory; FY 2023-24 value not in this source"))
with open(os.path.join(OUT, "storage_policy_timeline.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(TL)
    for t in tl:
        w.writerow(t)

for fn in sorted(os.listdir(OUT)):
    if fn.endswith(".csv") and not fn.startswith("_"):
        n = sum(1 for _ in open(os.path.join(OUT, fn))) - 1
        print(f"{fn}: {n} rows")
