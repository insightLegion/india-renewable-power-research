"""Parse CEA monthly Power Supply Position reports (Energy: page 10010, Peak: page 10011) PDFs.

Each report has, per state/region/All India: month values and FY-to-date (April..month) values.
Energy: requirement, supplied, not supplied (MU), not supplied (%).
Peak:   peak demand, peak met, demand not met (MW), (%).
Output: data/processed/generation_demand/_work/cea_psp_monthly.csv
"""
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CEA = ROOT / "data/raw/generation_demand/cea"
WORK = ROOT / "data/processed/generation_demand/_work"
NUM = r"-?[\d,]+(?:\.\d+)?"
ROWRE = re.compile(rf"^(.*?)\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$")
ROW4 = re.compile(rf"^(.*?)\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$")


def num(s):
    return float(s.replace(",", ""))


def english_label(s):
    s = s.strip()
    if "/" in s:
        parts = [p.strip() for p in s.split("/")]
        # take the last part that contains latin letters
        lat = [p for p in parts if re.search(r"[A-Za-z]", p)]
        s = lat[-1] if lat else ""
        if len(lat) >= 2 and lat[-1].startswith("(") is False and re.match(r"^[A-Z][a-z]", lat[-1]) is None:
            s = " / ".join(lat)
    s = re.sub(r"[^\x20-\x7E]", "", s).strip()
    return re.sub(r"\s+", " ", s)


def parse(path, kind):
    txt = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, timeout=120).stdout.decode(
        "utf-8", errors="ignore")
    # keep only PSP pages (some files also carry CEA gross-generation tables on other pages)
    pages = [pg for pg in txt.split("\f")
             if re.search(r"Power Supply Position", pg, re.I) and not re.search(r"GROSS GENERATION", pg, re.I)]
    txt = "\n".join(pages)
    status = "revised" if re.search(r"revised", txt, re.I) else ("provisional" if re.search(r"provisional|tentative", txt, re.I) else "")
    surplus_era = bool(re.search(r"Surplus\s*/\s*Deficit", txt, re.I))
    lines = txt.splitlines()
    recs = []
    pending_vals = None
    n8 = sum(1 for ln in lines if ROWRE.match(ln))
    for i, ln in enumerate(lines):
        m = ROWRE.match(ln)
        if not m and n8 < 5:
            m4 = ROW4.match(ln)
            if m4:
                lab = english_label(m4.group(1))
                if not lab:
                    for k in (i + 1, i - 1):
                        if 0 <= k < len(lines) and not ROW4.match(lines[k]):
                            cand = english_label(lines[k])
                            if cand and len(cand) < 60:
                                lab = cand
                                break
                if re.search(r"\d", lab):
                    continue
                recs.append((lab, [num(m4.group(k)) for k in range(2, 6)]))
            continue
        if m:
            lab = english_label(m.group(1))
            vals = [num(m.group(k)) for k in range(2, 10)]
            if not lab:
                # label on following / previous line(s)
                for k in (i + 1, i - 1):
                    if 0 <= k < len(lines) and not ROWRE.match(lines[k]):
                        cand = english_label(lines[k])
                        if cand and len(cand) < 60:
                            lab = cand
                            break
            recs.append((lab, vals))
    out = []
    names = (["energy_requirement", "energy_supplied", "energy_not_supplied", "energy_not_supplied_pct"]
             if kind == "energy" else ["peak_demand", "peak_met", "peak_demand_not_met", "peak_demand_not_met_pct"])
    units = ["MU", "MU", "MU", "%"] if kind == "energy" else ["MW", "MW", "MW", "%"]
    if surplus_era:
        # older reports: 'Requirement, Availability, Surplus/Deficit(-)' -> keep the sign convention as printed
        names = (["energy_requirement", "energy_availability", "energy_surplus_deficit", "energy_surplus_deficit_pct"]
                 if kind == "energy" else ["peak_demand", "peak_met", "peak_surplus_deficit", "peak_surplus_deficit_pct"])
    for lab, vals in recs:
        for k in range(4):
            out.append({"entity_raw": lab, "scope": "month", "metric": names[k], "value": vals[k], "unit": units[k],
                        "status": status})
            if len(vals) == 8:
                out.append({"entity_raw": lab, "scope": "fytd", "metric": names[k], "value": vals[4 + k],
                            "unit": units[k], "status": status})
    return out


def main():
    rows = []
    for page, kind in (("10010", "energy"), ("10011", "peak")):
        for f in sorted((CEA / page).glob("*.pdf")):
            ym = f.name[:7]
            try:
                recs = parse(f, kind)
            except Exception as e:  # noqa
                print("ERR", f.name, e)
                continue
            if not recs:
                print("no rows", f.name)
            for r in recs:
                r.update({"report_month": ym, "kind": kind, "file": f.name})
                rows.append(r)
    df = pd.DataFrame(rows)
    WORK.mkdir(parents=True, exist_ok=True)
    df.to_csv(WORK / "cea_psp_monthly.csv", index=False)
    print(len(df))
    print(df.groupby(["kind"]).report_month.agg(["min", "max", "nunique"]))


if __name__ == "__main__":
    main()
