"""Parse CEA 'Monthly Report of Renewable Generation' Excel files (RE Project Monitoring Division).

Input:  data/raw/generation_demand/cea/10068/*Monthly_Report_of_Renewable_Generation*.xls[x]
Output: data/processed/generation_demand/_work/cea_re_overview.csv   (all-India by source; month & FY-to-date cols)
        data/processed/generation_demand/_work/cea_re_statewise.csv  (state x source, current & prev-year month)
"""
import calendar
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/raw/generation_demand/cea/10068"
WORK = ROOT / "data/processed/generation_demand/_work"

MON = {}
for i in range(1, 13):
    MON[calendar.month_name[i].lower()] = i
    MON[calendar.month_abbr[i].lower()] = i
MON["sept"] = 9
MON["june"] = 6
MON["july"] = 7


def parse_month_tokens(s):
    """Find (month, year) pairs in a header string, in order."""
    s = s.replace("\n", " ")
    out = []
    for m in re.finditer(r"([A-Za-z]{3,9})\s*[',.\-]?\s*,?\s*'?\s*(\d{4}|\d{2})\b", s):
        mo = MON.get(m.group(1).lower())
        if mo:
            y = int(m.group(2))
            y = y + 2000 if y < 100 else y
            out.append((y, mo))
    return out


def clean_cat(s):
    s = str(s).replace("\n", " ").strip()
    if "/" in s:
        s = s.split("/")[-1].strip() if not s.lower().startswith("total") else s
    s = re.sub(r"\(\$\)|\*|\(.*?\)", "", s).strip()
    return s


def parse_overview(df, rep_ym, fname):
    recs = []
    hdr_i = None
    for i in range(min(25, len(df))):
        row = [str(x) for x in df.iloc[i].tolist()]
        if any("Category" in x for x in row) and any("RE Generation" in x for x in row):
            hdr_i = i
            break
    if hdr_i is None:
        return recs
    hdr = df.iloc[hdr_i].tolist()
    cols = {}
    for j, h in enumerate(hdr):
        h = str(h)
        if "RE Generation" in h:
            toks = parse_month_tokens(h)
            if len(toks) == 1:
                cols[j] = ("month", toks[0], toks[0])
            elif len(toks) >= 2:
                cols[j] = ("range", toks[0], toks[-1])
        elif "Installed Capacity" in h and "SLDC" not in h and "Monitored" not in h:
            cols[j] = ("capacity", None, None)
    cat_j = [j for j, h in enumerate(hdr) if "Category" in str(h)][0]
    for i in range(hdr_i + 1, min(hdr_i + 20, len(df))):
        cat = df.iat[i, cat_j]
        if not isinstance(cat, str) or not cat.strip():
            continue
        c = clean_cat(cat)
        if c.lower().startswith("note") or len(c) > 60:
            continue
        for j, (kind, a, b) in cols.items():
            v = pd.to_numeric(df.iat[i, j], errors="coerce")
            if pd.isna(v):
                continue
            recs.append({"report_month": f"{rep_ym[0]}-{rep_ym[1]:02d}", "category": c, "kind": kind,
                         "start": f"{a[0]}-{a[1]:02d}" if a else "", "end": f"{b[0]}-{b[1]:02d}" if b else "",
                         "value": float(v), "file": fname})
    return recs


def parse_sourcewise(df, rep_ym, fname):
    recs = []
    src_i = None
    for i in range(min(15, len(df))):
        row = [str(x).strip() for x in df.iloc[i].tolist()]
        if "Wind" in row and "Solar" in row:
            src_i = i
            break
    if src_i is None:
        return recs
    srow = df.iloc[src_i].tolist()
    yrow = df.iloc[src_i + 1].tolist()
    name_j = None
    for i in range(src_i - 2, src_i + 2):
        for j, x in enumerate(df.iloc[i].tolist()):
            if "Name of State" in str(x):
                name_j = j
    if name_j is None:
        name_j = 0
    colmap = {}
    cur, cur_j = None, -9
    for j in range(len(srow)):
        s = str(srow[j]).strip()
        if s and s != "nan":
            cur, cur_j = s, j
        y = str(yrow[j])
        if "Current" in y or "Previous" in y:
            which = "current" if "Current" in y else "previous"
            # each source label spans its two columns; an unlabeled trailing pair is the state total
            src = cur if (cur and j - cur_j <= 1) else "Total"
            colmap[j] = (src, which)
    # if last pair has no label it is the total
    for i in range(src_i + 2, len(df)):
        nm = df.iat[i, name_j]
        if not isinstance(nm, str) or not nm.strip():
            continue
        nm = re.sub(r"\s+", " ", nm).strip()
        if len(nm) > 60:
            continue
        for j, (src, which) in colmap.items():
            v = pd.to_numeric(df.iat[i, j], errors="coerce")
            if pd.isna(v):
                continue
            y, m = rep_ym
            if which == "previous":
                y -= 1
            recs.append({"report_month": f"{rep_ym[0]}-{rep_ym[1]:02d}", "state": nm, "source": src,
                         "which": which, "period": f"{y}-{m:02d}", "value": float(v), "file": fname})
    return recs


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    ov, sw = [], []
    for f in sorted([*SRC.glob("*Monthly_Report_of_Renewable_Generation*.xls*"), *SRC.glob("*Monthly_Renewable_Energy_Generation*.xls*")]):
        ym = tuple(int(x) for x in f.name[:7].split("-"))
        try:
            x = pd.ExcelFile(f)
        except Exception as e:  # noqa
            print("ERR", f.name, e)
            continue
        s_ov = [s for s in x.sheet_names if s.lower().startswith("overview")]
        s_sw = [s for s in x.sheet_names if s.lower().startswith("source wise") and str(ym[0]) in s or
                s.lower().startswith("source wise") and len([t for t in x.sheet_names if t.lower().startswith("source wise")]) == 1]
        if s_ov:
            ov += parse_overview(x.parse(s_ov[0], header=None), ym, f.name)
        if s_sw:
            sw += parse_sourcewise(x.parse(s_sw[0], header=None), ym, f.name)
        else:
            print("no source-wise sheet", f.name, x.sheet_names)
    pd.DataFrame(ov).to_csv(WORK / "cea_re_overview.csv", index=False)
    pd.DataFrame(sw).to_csv(WORK / "cea_re_statewise.csv", index=False)
    print(len(ov), len(sw))


if __name__ == "__main__":
    main()
