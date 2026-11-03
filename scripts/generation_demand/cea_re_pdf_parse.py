"""Parse the all-India overview table (page 'Summary of All India ... RE Generation') of CEA monthly RE
generation PDF reports, for months that have no Excel version.

Each row ends with: month_A, month_B, pct, ytd_A, ytd_B, pct  (A/B = current/previous year, order varies);
the order is resolved with the printed % column (= current / previous * 100).
Output: data/processed/generation_demand/_work/cea_re_overview_pdf.csv (same columns as cea_re_overview.csv)
"""
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/raw/generation_demand/cea/10068"
WORK = ROOT / "data/processed/generation_demand/_work"
NUM = r"-?\d[\d,]*(?:\.\d+)?"
CATS = [("Total Including Large Hydro", r"including"), ("Total Excluding Large Hydro", r"excluding"),
        ("Small Hydro", r"small\s*hydro|small"), ("Large Hydro", r"large\s*hydro|large"), ("Wind", r"wind"),
        ("Solar", r"solar"), ("Biomass", r"biomass"), ("Bagasse", r"bagasse"), ("Others", r"others"),
        ("Total", r"total")]


def order(a, b, pct):
    """return (current, previous)"""
    if pct and a and b:
        e1 = abs(a / b * 100 - pct)
        e2 = abs(b / a * 100 - pct)
        return (a, b, "pct-check") if e1 <= e2 else (b, a, "pct-check")
    return a, b, "assumed current-first"


def main():
    rows = []
    for f in sorted(SRC.glob("*Renewable*Generation*.pdf")):
        ym = f.name[:7]
        y, m = int(ym[:4]), int(ym[5:])
        fy0 = y if m >= 4 else y - 1
        txt = subprocess.run(["pdftotext", "-layout", "-l", "6", str(f), "-"], capture_output=True,
                             timeout=120).stdout.decode("utf-8", "ignore")
        def has_wind_row(p):
            return any("Wind" in ln and len(re.findall(rf"(?<![\w.]){NUM}(?![\w.])", ln)) >= 6
                       for ln in p.splitlines())
        pages = [p for p in txt.split("\f") if re.search(r"SUMMARY|Summary", p) and has_wind_row(p)]
        if not pages:
            print("no summary page", f.name)
            continue
        lines = pages[0].splitlines()
        seen = set()
        for i, ln in enumerate(lines):
            nums = re.findall(rf"(?<![\w.]){NUM}(?![\w.])", ln)
            if len(nums) < 6:
                continue
            cat = None
            follow = []
            for k in range(i + 1, min(i + 4, len(lines))):
                if len(re.findall(rf"(?<![\w.]){NUM}(?![\w.])", lines[k])) >= 6:
                    break
                if lines[k].strip():
                    follow.append(lines[k])
            for txtpart in [ln] + follow[:2]:
                low = re.sub(r"[^\x20-\x7E]", " ", re.sub(rf"{NUM}", " ", txtpart)).lower()
                for c, pat in CATS:
                    if re.search(pat, low):
                        cat = c
                        break
                if cat:
                    break
            if not cat or cat in seen:
                continue
            seen.add(cat)
            v = [float(x.replace(",", "")) for x in nums[-6:]]
            mc, mp, how1 = order(v[0], v[1], v[2])
            yc, yp, how2 = order(v[3], v[4], v[5])
            prev_m = f"{y - 1}-{m:02d}"
            base = {"report_month": ym, "category": cat, "file": f.name}
            rows.append({**base, "kind": "month", "start": ym, "end": ym, "value": mc, "how": how1})
            rows.append({**base, "kind": "month", "start": prev_m, "end": prev_m, "value": mp, "how": how1})
            rows.append({**base, "kind": "range", "start": f"{fy0}-04", "end": ym, "value": yc, "how": how2})
            rows.append({**base, "kind": "range", "start": f"{fy0 - 1}-04", "end": prev_m, "value": yp,
                         "how": how2})
    df = pd.DataFrame(rows)
    df.to_csv(WORK / "cea_re_overview_pdf.csv", index=False)
    print(len(df), df.report_month.nunique() if len(df) else 0)


if __name__ == "__main__":
    main()
