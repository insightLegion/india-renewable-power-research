"""Parse Grid-India NLDC daily REMC reports (PDF) into tidy CSVs.

Inputs : data/raw/curtailment_forecast/gridindia/remc_daily/*.pdf  (+ remc_daily_manifest.csv)
Outputs: data/processed/curtailment_forecast/remc_daily_curtailment.csv     (section 8 'VRE Curtailment Details'
                                                                             and section 9 'Emergency TRAS Down in VRE')
         data/processed/curtailment_forecast/remc_daily_profile.csv         (sections 2 and 4: REMC monitored regional / state
                                                                             profile: installed & available capacity, schedule,
                                                                             actual, deviation MU)
         data/processed/curtailment_forecast/remc_daily_parse_log.csv       (per-file QA: parsed totals vs report totals)
Run: .venv/bin/python -I scripts/curtailment_forecast/02_parse_remc_daily.py
"""
import csv
import glob
import os
import re
import sys
from datetime import datetime

import pdfplumber

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw", "curtailment_forecast", "gridindia", "remc_daily")
OUT = os.path.join(ROOT, "data", "processed", "curtailment_forecast")
os.makedirs(OUT, exist_ok=True)

REGIONS = {"NR": "Northern Region", "WR": "Western Region", "SR": "Southern Region", "ER": "Eastern Region",
           "NER": "North Eastern Region"}
STATE_FIX = {"UP": "Uttar Pradesh", "Kerela": "Kerala", "Telengana": "Telangana", "Chattisgarh": "Chhattisgarh",
             "Odhisa": "Odisha", "Jharkhnad": "Jharkhand", "HP": "Himachal Pradesh", "Tuticorn": "Tuticorin"}


def clean(c):
    return "" if c is None else " ".join(str(c).split())


def eng(c):
    """English part of a bilingual 'हिंदी / English' cell."""
    c = clean(c)
    if "/" in c:
        parts = [p.strip() for p in c.split("/")]
        latin = [p for p in parts if re.search(r"[A-Za-z]", p)]
        if latin:
            # pick the part with most latin chars
            c = max(latin, key=lambda p: len(re.findall(r"[A-Za-z]", p)))
    c = re.sub(r"[^\x00-\x7F]+", " ", c)
    c = " ".join(c.split())
    return STATE_FIX.get(c, c)


def num(c):
    c = clean(c).replace(",", "")
    if c in ("", "-", "--", "NA", "N/A"):
        return None
    try:
        return float(c)
    except ValueError:
        return None


def region_of(c):
    c = clean(c)
    m = re.search(r"/\s*(NER|NR|WR|SR|ER)\b", c)
    if m:
        return REGIONS[m.group(1)]
    return None


def report_date(path, manifest):
    base = os.path.basename(path)
    if base in manifest and manifest[base]:
        return manifest[base]
    m = re.match(r"(\d{1,2})[.\-](\d{1,2})[.\-](\d{4})", base)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", base)
    return m.group(0) if m else ""


def date_from_pdf(pdf):
    t = pdf.pages[0].extract_text() or ""
    m = re.search(r"Report for\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{2,4})", t)
    if m:
        for fmt in ("%d-%b-%y", "%d-%b-%Y"):
            try:
                return datetime.strptime(m.group(1), fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return ""


def parse_curtailment(pdf):
    """Return list of dict rows from sections 8 and 9, plus report totals."""
    rows, totals = [], {}
    section = None
    layout = None
    region = None
    category = None
    for pg in pdf.pages:
        txt = pg.extract_text() or ""
        if "Curtail" not in txt and "TRAS" not in txt and "Significant" not in txt:
            continue
        for tb in pg.extract_tables():
            for r in tb:
                cells = [clean(x) for x in r]
                joined = " ".join(cells)
                if re.search(r"VRE Curtailment Details", joined) and not any(num(x) is not None for x in cells[2:9]):
                    section, layout, region, category = "curtailment", None, None, None
                    continue
                if re.search(r"Emergency TRAS Down", joined) and not any(num(x) is not None for x in cells[2:9]):
                    section, layout, region, category = "emergency_tras_down", "B", None, None
                    continue
                if re.search(r"Significant information", joined):
                    if section:
                        sig = " ".join(c for c in cells[1:] if c)
                        totals["significant_info"] = sig
                    section = None
                    continue
                if section is None:
                    continue
                has_num = any(num(x) is not None for x in cells[2:9])
                if not has_num and ("Curtailment(MU)" in joined.replace(" ", "") or "VRECurtailment(MU)" in joined.replace(" ", "")):
                    layout = "A"; continue
                if not has_num and ("Wind Curtailment" in joined or "TRAS Down in Wind" in joined):
                    layout = "B"; continue
                if re.search(r"Max\s*MW|MUs|WIND\b|Time \(hh:mm\)", joined) and not any(num(c) is not None for c in cells):
                    continue
                if section == "curtailment" and layout is None:
                    layout = "B"
                # walk cells: region / category labels, then name, then values
                i = 0
                name = None
                while i < len(r):
                    c = cells[i]
                    if r[i] is None or c == "":
                        i += 1; continue
                    reg = region_of(c)
                    if reg and ("क्षेत्र" in c or "Region" in c or re.search(r"/\s*(NER|NR|WR|SR|ER)(\s+ISTS)?$", c)):
                        region = reg; i += 1; continue
                    if re.search(r"RE State", c):
                        category = "RE State"; i += 1; continue
                    if re.search(r"ISTS RE|ISTS\s*$", c) and not re.search(r"\d", c):
                        category = "ISTS RE Station"; i += 1; continue
                    name = c; i += 1
                    break
                if name is None:
                    continue
                raw_rest = list(r[i:])
                while raw_rest and raw_rest[0] is None:
                    raw_rest.pop(0)
                rest = [clean(x) for x in raw_rest]
                nvals = 6 if layout == "A" else 4
                vals = (rest + [""] * nvals)[:nvals]
                reason = next((x for x in rest[nvals:] if x), "")
                if layout == "A":
                    mu_w, mu_s, mw_w, t_w, mw_s, t_s = vals
                else:
                    mw_w, mu_w, mw_s, mu_s = vals
                    t_w = t_s = ""
                nm = eng(name)
                if re.match(r"^(Total Curtailment|SUM|Total)$", nm, re.I) or name.startswith("Total"):
                    totals[section] = {"wind_MU": num(mu_w), "solar_MU": num(mu_s), "wind_MW": num(mw_w), "solar_MW": num(mw_s)}
                    continue
                if section == "emergency_tras_down":
                    cat = "ISTS RE Station"
                else:
                    cat = category or ""
                rows.append({"section": section, "layout": layout, "region": region or "", "category": cat,
                             "entity": nm, "entity_raw": name, "wind_MU": num(mu_w), "solar_MU": num(mu_s),
                             "wind_max_MW": num(mw_w), "solar_max_MW": num(mw_s), "wind_max_time": t_w,
                             "solar_max_time": t_s, "reason": eng(reason) if reason not in ("-", "--") else ""})
    return rows, totals


def parse_profile(pdf):
    """Sections 2 (REMC Monitored Profile, regional) and 4 (REMC Monitored Intra State Profile)."""
    out = []
    section = None
    ent = None
    seen = set()
    for pg in pdf.pages[:2]:
        for tb in pg.extract_tables():
            for r in tb:
                cells = [clean(x) for x in r]
                joined = " ".join(cells)
                if re.search(r"^2\.", cells[0]) and "REMC Monitored Profile" in joined:
                    section = "REMC monitored regional"; ent = None; continue
                if re.search(r"^3\.", cells[0]):
                    section = None; continue
                if re.search(r"^4\.", cells[0]) and "Intra State" in joined:
                    section = "REMC monitored intra-state"; ent = None; continue
                if re.search(r"^[5-9]\.", cells[0]):
                    section = None; continue
                if section is None:
                    continue
                # find source cell
                src_idx = None
                for k, c in enumerate(cells):
                    if len(c) < 90 and not re.search(r"\d", c) and (
                            re.search(r"/\s*(Wind|Solar)\b", c) or "(Wind+Solar)" in c.replace(" ", "")):
                        src_idx = k; break
                if src_idx is None:
                    continue
                if src_idx > 0 and cells[src_idx - 1]:
                    cand = cells[src_idx - 1]
                    ent = region_of(cand) or eng(cand)
                src = "Wind" if "Wind" in cells[src_idx] and "Solar" not in cells[src_idx] else (
                    "Solar" if "Solar" in cells[src_idx] and "Wind" not in cells[src_idx] else "Wind+Solar")
                if ent == "Total" and section == "REMC monitored regional":
                    ent = "Total (all REMC monitored)"
                if (section, ent, src) in seen:
                    ent = "Total (all REMC monitored)" if section == "REMC monitored regional" else (ent or "") + " (unlabelled)"
                seen.add((section, ent, src))
                v = cells[src_idx + 1:]
                v = (v + [""] * 10)[:10]
                # installed, available, daymax MW, time, daymin MW, time, schedule MU, actual MU, deviation MU, CUF %
                out.append({"section": section, "entity": ent or "", "source": src,
                            "installed_MW": num(v[0]), "available_MW": num(v[1]), "day_max_MW": num(v[2]),
                            "schedule_MU": num(v[6]), "actual_MU": num(v[7]), "deviation_MU": num(v[8]), "CUF_pct": num(v[9])})
    return out


def parse_file(f):
    try:
        pdf = pdfplumber.open(f)
        d_pdf = date_from_pdf(pdf)
        rows, totals = parse_curtailment(pdf)
        prof = parse_profile(pdf)
        pdf.close()
        return d_pdf, rows, totals, prof
    except Exception as e:  # noqa
        return f"error {type(e).__name__}: {e}"


def main():
    manifest = {}
    mpath = os.path.join(ROOT, "data", "raw", "curtailment_forecast", "gridindia", "remc_daily_manifest.csv")
    if os.path.exists(mpath):
        for m in csv.DictReader(open(mpath)):
            manifest[os.path.basename(m["file_path"])] = m["title_date"]
    files = sorted(glob.glob(os.path.join(RAW, "*.pdf")))
    if len(sys.argv) > 1:
        files = [f for f in files if sys.argv[1] in os.path.basename(f)]
    crows, prows, log = [], [], []
    seen_dates = {}
    from multiprocessing import Pool
    with Pool(3) as pool:
        results = pool.map(parse_file, files, chunksize=4)
    for f, res in zip(files, results):
        base = os.path.basename(f)
        if isinstance(res, str):
            log.append({"file": base, "date": "", "status": res})
            continue
        d_pdf, rows, totals, prof = res
        d = d_pdf or report_date(f, manifest)
        if d in seen_dates:
            log.append({"file": base, "date": d, "status": f"duplicate of {seen_dates[d]}; skipped"})
            continue
        seen_dates[d] = base
        for r in rows:
            r.update({"date": d, "file": base})
        for r in prof:
            r.update({"date": d, "file": base})
        crows += rows
        prows += prof
        entry = {"file": base, "date": d, "date_from_pdf": d_pdf, "status": "ok", "n_curt_rows": len(rows),
                 "significant_info": totals.get("significant_info", "")[:300]}
        for sec in ("curtailment", "emergency_tras_down"):
            parsed_w = sum((r["wind_MU"] or 0) for r in rows if r["section"] == sec)
            parsed_s = sum((r["solar_MU"] or 0) for r in rows if r["section"] == sec)
            tot = totals.get(sec, {})
            entry[f"{sec}_parsed_wind_MU"] = round(parsed_w, 3)
            entry[f"{sec}_parsed_solar_MU"] = round(parsed_s, 3)
            entry[f"{sec}_reported_total_wind_MU"] = tot.get("wind_MU")
            entry[f"{sec}_reported_total_solar_MU"] = tot.get("solar_MU")
            entry[f"{sec}_section_present"] = int(any(r["section"] == sec for r in rows) or sec in totals)
        log.append(entry)
    cfields = ["date", "section", "region", "category", "entity", "wind_MU", "solar_MU", "wind_max_MW", "solar_max_MW",
               "wind_max_time", "solar_max_time", "reason", "layout", "entity_raw", "file"]
    with open(os.path.join(OUT, "remc_daily_curtailment.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cfields); w.writeheader()
        for r in sorted(crows, key=lambda x: (x["date"], x["section"])):
            w.writerow({k: r.get(k) for k in cfields})
    pfields = ["date", "section", "entity", "source", "installed_MW", "available_MW", "day_max_MW", "schedule_MU",
               "actual_MU", "deviation_MU", "CUF_pct", "file"]
    with open(os.path.join(OUT, "remc_daily_profile.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=pfields); w.writeheader()
        for r in sorted(prows, key=lambda x: x["date"]):
            w.writerow({k: r.get(k) for k in pfields})
    lf = sorted({k for e in log for k in e})
    with open(os.path.join(OUT, "remc_daily_parse_log.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=lf); w.writeheader(); w.writerows(sorted(log, key=lambda x: x.get("date", "")))
    print("files", len(files), "curt rows", len(crows), "profile rows", len(prows))


if __name__ == "__main__":
    main()
