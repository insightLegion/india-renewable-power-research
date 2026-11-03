"""Parse Grid-India / POSOCO NLDC Daily PSP reports (xls or pdf) into long tables.

Reads files listed in data/raw/generation_demand/daily_psp_report/ (one per report date).
Data date = "Date of Reporting" printed in the report minus one day ("Report for previous day").

Outputs (scratch, then assembled by psp_build.py):
  data/processed/generation_demand/_work/psp_parsed.csv  (date, level, entity, region, metric, value, unit, file)
  data/processed/generation_demand/_work/psp_ts_15min.csv (date, time, column_label, value, file)  [time series page/sheet]
  data/processed/generation_demand/_work/psp_parse_log.csv

Usage: .venv/bin/python -I scripts/generation_demand/psp_parse.py [--limit N] [--only-xls] [--workers 3]
"""
import csv
import datetime as dt
import re
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/generation_demand/daily_psp_report"
WORK = ROOT / "data/processed/generation_demand/_work"

NUM = re.compile(r"^[-+]?\d+(?:,\d{3})*(?:\.\d+)?$")
DASH = re.compile(r"^-{1,}$|^—$|^NA$|^N/A$")
TIME = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
REGIONS = ["Northern Region", "Western Region", "Southern Region", "Eastern Region", "North-Eastern Region", "India"]
RCODE = {"NR": "Northern Region", "WR": "Western Region", "SR": "Southern Region", "ER": "Eastern Region",
         "NER": "North-Eastern Region"}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                      "dec"], 1)}


def parse_date(s):
    s = str(s).strip()
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                "%d.%m.%y", "%d-%B-%Y", "%d %b %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def tofloat(t):
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t) if t == t else None
    t = str(t).strip().replace(",", "")
    if NUM.match(t):
        return float(t)
    return None


# ---------------------------------------------------------------- line model
def split_line(tokens):
    """tokens -> (label, values) where values is the trailing run of numeric/dash/time tokens."""
    vals = []
    i = len(tokens)
    while i > 0:
        t = str(tokens[i - 1]).strip()
        if NUM.match(t.replace(",", "")) or DASH.match(t) or TIME.match(t):
            vals.insert(0, t)
            i -= 1
        else:
            break
    label = " ".join(str(x).strip() for x in tokens[:i]).strip()
    return label, vals


def lines_from_pdf(path):
    """Return (pages_text list) using pdftotext -layout."""
    out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, timeout=120)
    txt = out.stdout.decode("utf-8", errors="ignore")
    return txt.split("\f")


def rows_from_xls(path):
    xl = pd.ExcelFile(path)
    sheets = {}
    for sn in xl.sheet_names:
        df = xl.parse(sn, header=None, dtype=object)
        rows = []
        for _, r in df.iterrows():
            cells = []
            for v in r.tolist():
                if v is None or (isinstance(v, float) and v != v):
                    continue
                if isinstance(v, float) and v.is_integer() and abs(v) < 1e12:
                    cells.append(v)
                elif isinstance(v, (dt.time,)):
                    cells.append(v.strftime("%H:%M"))
                elif isinstance(v, (dt.datetime, pd.Timestamp)):
                    cells.append(v.strftime("%d-%b-%Y"))
                else:
                    cells.append(v)
            rows.append(cells)
        sheets[sn] = rows
    return sheets


def cell_str(c):
    if isinstance(c, float):
        return repr(c) if not c.is_integer() else str(int(c))
    return str(c).replace("\n", " ").strip()


# ---------------------------------------------------------------- main page parser
A_METRICS = [
    (lambda l: "demand met" in l and "evening" in l, "demand_met_evening_peak", "MW"),
    (lambda l: ("shortage" in l or "shoratge" in l) and ("peak" in l) and "energy" not in l, "shortage_evening_peak", "MW"),
    (lambda l: l.startswith("energy met"), "energy_met", "MU"),
    (lambda l: l.startswith("hydro gen"), "hydro_gen", "MU"),
    (lambda l: l.startswith("wind gen"), "wind_gen", "MU"),
    (lambda l: l.startswith("solar gen"), "solar_gen", "MU"),
    (lambda l: l.startswith("energy shortage"), "energy_shortage", "MU"),
    (lambda l: "maximum demand met" in l or "max demand met" in l or "(from nldc scada" in l, "max_demand_met_day", "MW"),
]
G_METRICS = [
    (lambda l: l.startswith("thermal"), "gen_thermal_coal_lignite", "MU"),
    (lambda l: l.startswith("coal"), "gen_coal", "MU"),
    (lambda l: l.startswith("lignite"), "gen_lignite", "MU"),
    (lambda l: l.startswith("hydro"), "gen_hydro", "MU"),
    (lambda l: l.startswith("nuclear"), "gen_nuclear", "MU"),
    (lambda l: l.startswith("gas"), "gen_gas_naptha_diesel", "MU"),
    (lambda l: l.startswith("res"), "gen_res_wind_solar_biomass_others", "MU"),
    (lambda l: l.startswith("total"), "gen_total", "MU"),
    (lambda l: l.startswith("share of res"), "share_res_in_total_gen", "%"),
    (lambda l: l.startswith("share of non") or l.startswith("total generation(%)") or l.startswith("total generation (%)"),
     "share_nonfossil_in_total_gen", "%"),
]


def parse_main(rows, fname):
    """rows: list of token lists (one per visual row). Returns (report_date, records, log)."""
    recs, log = [], []
    rep_date = None
    section = None
    pending = None
    state_hdr = None
    region_ctx = None
    for toks in rows:
        toks = [cell_str(t) for t in toks if cell_str(t) != ""]
        if not toks:
            continue
        joined = " ".join(toks)
        low = joined.lower()
        if rep_date is None:
            m = re.search(r"date of reporting\s*:?\s*([0-9]{1,2}[-./ ][A-Za-z0-9]{2,9}[-./ ][0-9]{2,4})", joined, re.I)
            if m:
                rep_date = parse_date(m.group(1).replace(" ", "-"))
            elif "date of reporting" in low:
                for t in toks:
                    d = parse_date(t)
                    if d:
                        rep_date = d
        m = re.match(r"^([A-J])\.\s*(.*)", joined)
        if m:
            section = m.group(1)
            pending = None
            region_ctx = None
            # section I may share a row with section H (xls & pdf layout)
            if "I. All India Peak Demand" in joined:
                pass
        # solar / non-solar hour peak (section I) - regex over the whole row
        for mm in re.finditer(r"(Non-Solar hr|Solar hr)\s+(\d+(?:\.\d+)?)\s+(\d{1,2}:\d{2})\s+(-?\d+(?:\.\d+)?)", joined):
            key = "nonsolar" if mm.group(1).lower().startswith("non") else "solar"
            recs.append(("India", "India", f"max_demand_met_{key}_hr", float(mm.group(2)), "MW"))
            recs.append(("India", "India", f"time_max_demand_met_{key}_hr", mm.group(3), "HH:MM"))
            recs.append(("India", "India", f"shortage_at_max_demand_{key}_hr", float(mm.group(4)), "MW"))
        if section not in ("A", "C", "G"):
            continue
        label, vals = split_line(toks)
        llow = label.lower()
        if section == "A":
            if vals and all(TIME.match(v) for v in vals) and len(vals) >= 6:
                for reg, v in zip(REGIONS, vals[:6]):
                    recs.append(("region" if reg != "India" else "India", reg, "time_max_demand_met_day", v, "HH:MM"))
                pending = None
                continue
            if label and not vals:
                pending = label
                continue
            use = label
            if (not label or label.startswith("(")) and pending:
                use = pending + " " + label
            ulow = use.lower()
            if len(vals) >= 6:
                hit = None
                for f, name, unit in A_METRICS:
                    if f(ulow):
                        hit = (name, unit)
                        break
                if hit:
                    for reg, v in zip(REGIONS, vals[:6]):
                        x = tofloat(v)
                        if x is not None:
                            recs.append(("region" if reg != "India" else "India", reg, hit[0], x, hit[1]))
                else:
                    log.append((fname, "A_unmatched", use[:80]))
                pending = None
        elif section == "G":
            if label and not vals:
                pending = label
                continue
            use = label if label else (pending or "")
            if pending and label.lower().startswith("total generation"):
                use = pending
            ulow = use.lower()
            if len(vals) >= 6:
                hit = None
                for f, name, unit in G_METRICS:
                    if f(ulow):
                        hit = (name, unit)
                        break
                if hit:
                    for reg, v in zip(REGIONS, vals[:6]):
                        x = tofloat(v)
                        if x is not None:
                            recs.append(("region" if reg != "India" else "India", reg, hit[0], x, hit[1]))
                else:
                    log.append((fname, "G_unmatched", use[:80]))
                pending = None if label else pending
        elif section == "C":
            if "energy shortage" in low or "shortage (mu)" in low:
                state_hdr = "with_energy_shortage"
            # state rows: tokens = [region?] name... then numbers
            t = list(toks)
            if t and t[0] in RCODE:
                region_ctx = RCODE[t[0]]
                t = t[1:]
            if len(t) == 0:
                continue
            # label = leading non-numeric tokens
            i = 0
            while i < len(t) and tofloat(t[i]) is None:
                i += 1
            name = " ".join(t[:i]).strip()
            rest = t[i:]
            if name in RCODE:
                region_ctx = RCODE[name]
                continue
            nums = [tofloat(x) for x in rest]
            if not name or len(rest) < 3 or any(n is None for n in nums[:3]):
                continue
            if re.search(r"region|states|max\.?\s*demand|schedule", name, re.I):
                continue
            recs.append(("state", name, "max_demand_met_day", nums[0], "MW", region_ctx))
            recs.append(("state", name, "shortage_at_max_demand", nums[1], "MW", region_ctx))
            recs.append(("state", name, "energy_met", nums[2], "MU", region_ctx))
            if state_hdr == "with_energy_shortage" and len(rest) >= 7:
                x = tofloat(rest[-1])
                if x is not None:
                    recs.append(("state", name, "energy_shortage", x, "MU", region_ctx))
    return rep_date, recs, log


# ---------------------------------------------------------------- time series (15-min) page
def parse_ts_rows(rows):
    """Return list of (time, [values]) rows from a 15-min time-series table."""
    out = []
    for toks in rows:
        toks = [cell_str(t) for t in toks if cell_str(t) != ""]
        if len(toks) >= 4 and TIME.match(toks[0]):
            vals = [tofloat(x) for x in toks[1:]]
            out.append((toks[0][:5], vals))
    return out


def process(path):
    path = Path(path)
    fname = path.name
    res = {"file": fname, "recs": [], "ts": [], "ts_header": "", "log": [], "rep_date": None}
    try:
        if path.suffix.lower() in (".xls", ".xlsx"):
            sheets = rows_from_xls(path)
            main_rows = []
            for sn, rows in sheets.items():
                if sn.upper().startswith("MOP_E") or sn.upper().startswith("MOP"):
                    main_rows += rows
            if not main_rows:
                main_rows = list(sheets.values())[0]
            rep, recs, log = parse_main(main_rows, fname)
            for sn in pd.ExcelFile(path).sheet_names:
                if "time" in sn.lower():
                    df = pd.read_excel(path, sheet_name=sn, header=None, dtype=object)
                    hi = next((i for i in range(min(10, len(df)))
                               if str(df.iat[i, 0]).strip().upper() == "TIME"), None)
                    if hi is None:
                        continue
                    names = [re.sub(r"\s+", " ", str(c)).strip() if str(c) != "nan" else "" for c in df.iloc[hi].tolist()]
                    res["ts_header"] = " | ".join(names)
                    out = []
                    for _, r in df.iloc[hi + 1:].iterrows():
                        t0 = r.iloc[0]
                        if isinstance(t0, (dt.time, dt.datetime)):
                            tm = t0.strftime("%H:%M")
                        else:
                            tm = str(t0).strip()
                            if not TIME.match(tm):
                                continue
                            tm = tm[:5] if len(tm.split(":")[0]) == 2 else "0" + tm[:4]
                        vals = [tofloat(v) for v in r.iloc[1:len(names)].tolist()]
                        out.append((tm, vals))
                    res["ts"] = out
        else:
            pages = lines_from_pdf(path)
            main_rows, ts_rows, ts_hdr = [], [], ""
            for pg in pages:
                if "Report for previous day" in pg or "A. Maximum Demand" in pg or "Power Supply Position at All India" in pg:
                    main_rows += [ln.split() for ln in pg.splitlines()]
                if "15 Min" in pg or "15 MIN" in pg or "TIME SERIES" in pg.upper():
                    ts_rows += [ln.split() for ln in pg.splitlines()]
                    hl = [ln for ln in pg.splitlines() if "(A)" in ln or "(K)" in ln]
                    ts_hdr = hl[0].strip() if hl else ""
            rep, recs, log = parse_main(main_rows, fname)
            res["ts"] = parse_ts_rows(ts_rows)
            res["ts_header"] = ts_hdr
        res["rep_date"] = rep
        res["recs"] = recs
        res["log"] = log
    except Exception as e:  # noqa
        res["log"].append((fname, "error", repr(e)[:200]))
    return res


def main():
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 3
    files = sorted(p for p in RAW.iterdir() if p.suffix.lower() in (".pdf", ".xls", ".xlsx"))
    if "--only-xls" in args:
        files = [f for f in files if f.suffix.lower() != ".pdf"]
    if limit:
        files = files[:: max(1, len(files) // limit)]
    WORK.mkdir(parents=True, exist_ok=True)
    append = "--append" in args  # incremental: skip files already in the log (raw files are deleted after upload)
    if append and (WORK / "psp_parse_log.csv").exists():
        done = set(pd.read_csv(WORK / "psp_parse_log.csv").file)
        files = [f for f in files if f.name not in done]
    print("files to parse:", len(files), flush=True)
    mode = "a" if append else "w"
    with Pool(workers) as pool, \
            (WORK / "psp_parsed.csv").open(mode, newline="") as fo, \
            (WORK / "psp_ts_15min.csv").open(mode, newline="") as ft, \
            (WORK / "psp_parse_log.csv").open(mode, newline="") as fl:
        wo, wt, wl = csv.writer(fo), csv.writer(ft), csv.writer(fl)
        if not append:
            wo.writerow(["date", "report_date", "level", "entity", "region", "metric", "value", "unit", "file"])
            wt.writerow(["date", "time", "values", "header", "file"])
            wl.writerow(["file", "kind", "detail"])
        for n, res in enumerate(pool.imap(process, files, chunksize=4)):
            rep = res["rep_date"]
            if rep is None:
                wl.writerow([res["file"], "no_report_date", ""])
                # fall back on file-name date prefix (title date); flagged in log
                continue
            d = rep - dt.timedelta(days=1)
            for r in res["recs"]:
                region = r[5] if len(r) > 5 else (r[1] if r[0] == "region" else "")
                wo.writerow([d.isoformat(), rep.isoformat(), r[0], r[1], region, r[2], r[3], r[4], res["file"]])
            for tm, vals in res["ts"]:
                wt.writerow([d.isoformat(), tm, ";".join("" if v is None else repr(v) for v in vals),
                             res["ts_header"], res["file"]])
            for lg in res["log"]:
                wl.writerow(lg)
            wl.writerow([res["file"], "ok", f"recs={len(res['recs'])};ts={len(res['ts'])}"])
            if n % 200 == 0:
                print(n, res["file"], flush=True)


if __name__ == "__main__":
    main()
