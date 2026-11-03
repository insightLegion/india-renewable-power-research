"""Extract demand history / projections from CEA LGBR 2026-27 and NEP 2022-32 (Vol I) text, and the
Grid-India monthly report (Sep 2026) 'All Time Highest' table.

Inputs: pdftotext -layout outputs created on the fly from
  data/raw/generation_demand/cea/10003/2027_Load_Generation_Balance_Report_951.pdf  (LGBR 2026-27)
  data/raw/generation_demand/cea/nep/NEP_2022-32_Vol1_Generation_2023.pdf
  data/raw/generation_demand/monthly_report_samples/Monthly_Report_Sep_2026_113.pdf
Outputs: data/processed/generation_demand/_work/{lgbr_fy.csv, demand_projections.csv, all_time_highs.csv}
"""
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/generation_demand"
WORK = ROOT / "data/processed/generation_demand/_work"
COLS = ["geography", "period_start", "period_end", "granularity", "metric", "value", "unit", "source_id", "notes"]
INUM = r"\(-\)\s*[\d,]+(?:\.\d+)?|-?[\d,]+(?:\.\d+)?"


def txt(pdf, first=None, last=None):
    cmd = ["pdftotext", "-layout"]
    if first:
        cmd += ["-f", str(first)]
    if last:
        cmd += ["-l", str(last)]
    return subprocess.run(cmd + [str(pdf), "-"], capture_output=True, timeout=300).stdout.decode("utf-8", "ignore")


def n(s):
    s = s.replace(",", "").replace(" ", "")
    neg = s.startswith("(-)")
    v = float(s.replace("(-)", ""))
    return -v if neg else v


def fy_label_to_start(lbl):
    return f"{lbl[:4]}-04-01", f"{int(lbl[:4]) + 1}-03-31"


def chart_values(lines, start_pat, min_value):
    """Numbers in a layout-rendered bar chart -> ordered by column position; FY labels from axis line."""
    i0 = next(i for i, ln in enumerate(lines) if re.search(start_pat, ln))
    pts = []
    for ln in lines[i0 + 1:i0 + 40]:
        if re.search(r"20\d\d-\d\d", ln):
            fys = [(m.start(), m.group(0)) for m in re.finditer(r"20\d\d-\d\d\*?", ln)]
            break
        for m in re.finditer(r"[\d,]{7,}", ln):
            v = n(m.group(0))
            if v >= min_value and m.start() > 14:  # skip y-axis tick labels at line start
                pts.append((m.start() + len(m.group(0)) / 2, v))
    pts.sort()
    # bar labels sit above bars left-to-right; one label per FY -> zip in x order (checked: counts must match)
    if len(pts) != len(fys):
        raise ValueError(f"chart parse mismatch: {len(pts)} values vs {len(fys)} FY labels")
    return {lbl: v for (x, v), (_, lbl) in zip(pts, fys)}


def lgbr():
    pdf = RAW / "cea/10003/2027_Load_Generation_Balance_Report_951.pdf"
    lines = txt(pdf, 1, 12).splitlines()
    rows = []
    for pat, metric, unit, mn in ((r"All India Energy Requirement \(MU\)", "energy_requirement", "MU", 1_000_000),
                                  (r"All India Peak Demand \(MW\)", "peak_demand", "MW", 100_000)):
        vals = chart_values(lines, pat, mn)
        for lbl, v in vals.items():
            ps, pe = fy_label_to_start(lbl)
            ant = lbl.endswith("*") and lbl.startswith("2026")
            rows.append(["India", ps, pe, "FY", metric + ("_anticipated" if ant else ""), v, unit,
                         "GEN-CEA-LGBR-2026-27",
                         "LGBR 2026-27 executive-summary trend chart (actual FY values"
                         + ("; 2026-27 anticipated)" if ant else ")") + (" - chart label marked * " if lbl.endswith("*") else "")])
    # anticipated regional table 2026-27
    t = "\n".join(lines)
    blk = t[t.find("Anticipated All India Power Supply Position for the year 2026-27"):]
    for reg in ["Northern", "Western", "Southern", "Eastern", "North-Eastern", "All India"]:
        m = re.search(rf"^\s*{reg}\s+(.*)$", blk, re.M)
        if not m:
            continue
        vals = [n(x) for x in re.findall(INUM, m.group(1))]
        if len(vals) < 8:
            continue
        geo = reg + " Region" if reg != "All India" else "India"
        names = [("energy_requirement_anticipated", "MU"), ("energy_availability_anticipated", "MU"),
                 ("energy_surplus_deficit_anticipated", "MU"), ("energy_surplus_deficit_anticipated_pct", "%"),
                 ("peak_demand_anticipated", "MW"), ("peak_availability_anticipated", "MW"),
                 ("peak_surplus_deficit_anticipated", "MW"), ("peak_surplus_deficit_anticipated_pct", "%")]
        for (mt, u), v in zip(names, vals[:8]):
            rows.append([geo, "2026-04-01", "2027-03-31", "FY", mt, v, u, "GEN-CEA-LGBR-2026-27",
                         "LGBR 2026-27 Executive Summary table 'Anticipated All India Power Supply Position'"])
    return rows


def nep():
    pdf = RAW / "cea/nep/NEP_2022-32_Vol1_Generation_2023.pdf"
    t = txt(pdf)
    rows = []
    i = t.find("Region-wise energy requirement & peak demand for the years 2021-22, 2026-27 and 2031-32")
    blk = t[i:i + 3000]
    yrs = [("2021-04-01", "2022-03-31"), ("2026-04-01", "2027-03-31"), ("2031-04-01", "2032-03-31")]
    for reg in ["Northern Region", "Western Region", "Southern Region", "Eastern Region", "North Eastern Region",
                "All India"]:
        m = re.search(rf"^\s*{reg}\s+(.*)$", blk, re.M)
        vals = [n(x) for x in re.findall(r"[\d,]+", m.group(1))]
        geo = "India" if reg == "All India" else reg.replace("North Eastern", "North-Eastern")
        for k, (ps, pe) in enumerate(yrs):
            note = "NEP 2022-32 Vol I Table 4.2 (as per 20th EPS); 2021-22 = EPS base-year value"
            rows.append([geo, ps, pe, "FY", "energy_requirement_projected_20th_EPS", vals[k], "MU",
                         "GEN-CEA-NEP-2023", note])
            rows.append([geo, ps, pe, "FY", "peak_demand_projected_20th_EPS", vals[3 + k], "MW",
                         "GEN-CEA-NEP-2023", note])
    # Table 5.11 / 5.12 likely gross generation
    for tab, (ps, pe) in (("Source Wise Likely Gross Generation (BU) in 2026-27", ("2026-04-01", "2027-03-31")),
                          ("Source Wise Likely Gross Generation (BU) in 2031-32", ("2031-04-01", "2032-03-31"))):
        j = t.find(tab)
        blk = t[j:j + 1500].splitlines()[1:14]
        for ln in blk:
            m = re.match(r"^\s*([A-Za-z+# ]+?)\s+([\d.]+)\s+([\d.]+)%", ln)
            if m:
                src = re.sub(r"[^a-z]+", "_", m.group(1).strip().lower()).strip("_")
                rows.append(["India", ps, pe, "FY", f"gen_{src}_likely_NEP", float(m.group(2)), "BU",
                             "GEN-CEA-NEP-2023", f"NEP 2022-32 Vol I '{tab}' (hydro incl. hydro imports)"])
                rows.append(["India", ps, pe, "FY", f"share_{src}_likely_NEP", float(m.group(3)), "%",
                             "GEN-CEA-NEP-2023", f"NEP 2022-32 Vol I '{tab}'"])
    return rows


def all_time_highs():
    pdf = RAW / "monthly_report_samples/Monthly_Report_Sep_2026_113.pdf"
    t = txt(pdf)
    i = t.find("23. ALL TIME HIGHEST")
    lines = t[i:i + 4000].splitlines()
    names = [("max_demand_met_solar_hours_all_time_high", "MW"), ("max_demand_met_nonsolar_hours_all_time_high", "MW"),
             ("energy_met_all_time_high", "MU"), ("hydro_gen_all_time_high", "MU"), ("wind_gen_all_time_high", "MU"),
             ("solar_gen_all_time_high", "MU")]
    rows = []
    regs = {"NR": "Northern Region", "WR": "Western Region", "SR": "Southern Region", "ER": "Eastern Region",
            "NER": "North-Eastern Region", "All India": "India"}
    for k, ln in enumerate(lines):
        s = ln.strip()
        if s in regs:
            vals_ln, dates_ln = lines[k - 1], lines[k + 1]
            vals = re.findall(r"(?<!\S)(-|[\d.]+)(?!\S)", vals_ln)
            dates = [(m.start(), m.group(0)) for m in re.finditer(r"\d{2}-\d{2}-\d{4}", dates_ln)]
            vpos = [(m.start(), m.group(0)) for m in re.finditer(r"(?<!\S)(-|[\d.]+)(?!\S)", vals_ln)]
            for (pos, v), (mt, u) in zip(vpos, names):
                if v == "-":
                    continue
                d = min(dates, key=lambda x: abs(x[0] - pos)) if dates else (0, "")
                dd = d[1]
                iso = f"{dd[6:]}-{dd[3:5]}-{dd[:2]}" if dd else ""
                rows.append([regs[s], iso, iso, "snapshot", mt, float(v), u, "GEN-GI-MONTHLY-2026-09",
                             f"Grid-India NLDC Monthly Operational Report Sep 2026, 'All Time Highest' table; "
                             f"record date {dd}; status as of 30-Sep-2026"])
    return rows


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(lgbr(), columns=COLS).to_csv(WORK / "lgbr_fy.csv", index=False)
    pd.DataFrame(nep(), columns=COLS).to_csv(WORK / "nep_projections.csv", index=False)
    pd.DataFrame(all_time_highs(), columns=COLS).to_csv(WORK / "all_time_highs.csv", index=False)
    for f in ("lgbr_fy.csv", "nep_projections.csv", "all_time_highs.csv"):
        print(open(WORK / f).read())


if __name__ == "__main__":
    main()
