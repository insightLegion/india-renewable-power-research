"""Parse CEA monthly 'Installed Capacity' PDFs into a tidy long CSV.

Input : data/raw/capacity_storage/cea/installed_capacity/*.pdf (+ manifest.csv)
Output: data/processed/capacity_storage/_cea_installed_capacity_monthly.csv (intermediate, tidy long)
        data/processed/capacity_storage/_cea_ic_parse_log.csv (per-file diagnostics)

Extracted per report (all MW, utilities, All India):
 - from the 'ALL INDIA ... Total' row of the mode-wise table: coal, lignite, gas, diesel,
   thermal_total, nuclear, hydro (large hydro incl. PSP), res_mnre, [renewable_total], grand_total
 - from the '*Break up of RES all India as on <date>' footnote (older format) or the
   page-1 summary (newer format): small hydro, wind, bio-power (BM power/cogen), waste-to-energy,
   solar, RES total. The RES 'as on' date is recorded in notes (it can lag the report date).
Nothing is estimated: if a value is not found it is simply absent.
"""
import csv
import glob
import os
import re
import sys

import pdfplumber

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RAW = os.path.join(ROOT, "data", "raw", "capacity_storage", "cea", "installed_capacity")
OUT = os.path.join(ROOT, "data", "processed", "capacity_storage")
SRC = "CAP-001"

NUM = r"-?[\d,]+\.?\d*"


def num(s):
    return float(s.replace(",", ""))


def parse_date(d):
    d = d.strip().rstrip(".")
    m = re.match(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", d)
    if not m:
        return None
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"


def parse_file(path):
    with pdfplumber.open(path) as pdf:
        texts = [(p.extract_text() or "") for p in pdf.pages]
    full = "\n".join(texts)
    rec = {"file": os.path.basename(path)}
    m = re.search(r"\(As on\s*([\d.\-/]+)\s*\)", full) or re.search(r"as on\s*([\d.\-/]{8,10})", full, re.I)
    rec["asof"] = parse_date(m.group(1)) if m else None

    # ---- ALL INDIA total row of mode-wise table
    i = full.find("ALL INDIA")
    while i != -1:
        seg = full[i:i + 1500]
        mt = re.search(r"(?:^|\n)\s*(?:ALL INDIA\s+)?Total\s+((?:" + NUM + r"\s+){7,9}" + NUM + r")", seg)
        if mt:
            vals = [num(x) for x in mt.group(1).split()]
            if len(vals) == 10:
                keys = ["coal", "lignite", "gas", "diesel", "thermal_total", "nuclear", "hydro", "res_mnre", "renewable_total", "grand_total"]
            elif len(vals) == 9:
                keys = ["coal", "lignite", "gas", "diesel", "thermal_total", "nuclear", "hydro", "res_mnre", "grand_total"]
            else:  # pre-2018 layout: no separate lignite column (coal incl. lignite)
                keys = ["coal_incl_lignite", "gas", "diesel", "thermal_total", "nuclear", "hydro", "res_mnre", "grand_total"]
            rec.update(dict(zip(keys, vals)))
            rec["table_found"] = True
            break
        i = full.find("ALL INDIA", i + 9)

    # ---- RES breakup footnote (older format)
    mb = re.search(r"Break\s*up of RES all India as on\s*([\d.\-/]+)", full, re.I)
    if mb:
        rec["res_asof"] = parse_date(mb.group(1))
        seg = full[mb.end(): mb.end() + 600]
        nums = re.findall(r"(?<![\w/])" + NUM + r"(?![\w/])", seg)
        nums = [num(x) for x in nums if re.match(r"^[\d,]+\.\d+$|^[\d,]{3,}$", x)]
        # expect 6 numbers: SHP, Wind, BM, WtE, Solar, Total (newer years)
        # older layouts may have 5 (no WtE split) -> SHP, Wind, Bio, Solar, Total
        if len(nums) >= 6 and abs(sum(nums[:5]) - nums[5]) < 2:
            rec.update(dict(zip(["small_hydro", "wind", "bio_power", "waste_to_energy", "solar", "res_total"], nums[:6])))
        elif len(nums) >= 5 and abs(sum(nums[:4]) - nums[4]) < 2:
            rec.update(dict(zip(["small_hydro", "wind", "bio_power_incl_wte", "solar", "res_total"], nums[:5])))
        else:
            rec["res_breakup_unparsed"] = " ".join(str(x) for x in nums[:8])

    # ---- newer summary page (page 1 'Category Installed Capacity (MW) % Share')
    if "Category Installed Capacity" in texts[0]:
        t = texts[0]
        pats = {
            "s_coal": r"\nCoal\s+(" + NUM + ")",
            "s_lignite": r"\nLignite\s+(" + NUM + ")",
            "s_gas": r"\nGas\s+(" + NUM + ")",
            "s_diesel": r"\nDiesel\s+(" + NUM + ")",
            "s_fossil_total": r"Total Fossil Fuel\s+(" + NUM + ")",
            "s_res_incl_hydro": r"RES \(including Hydro\)\s+(" + NUM + ")",
            "s_hydro_incl_psp": r"Hydro \(including PSPs?\)\s+(" + NUM + ")",
            "s_wind_solar_other": r"Wind, Solar & Other RE\s+(" + NUM + ")",
            "s_wind": r"\nWind\s+(" + NUM + ")",
            "s_solar": r"\nSolar\s+(" + NUM + ")",
            "s_bm_power": r"BM Power(?:/Cogen\.?)?\s+(" + NUM + ")",
            "s_wte": r"Waste to Energy\s+(" + NUM + ")",
            "s_small_hydro": r"Small Hydro(?: Power)?\s+(" + NUM + ")",
            "s_nuclear": r"\nNuclear\s+(" + NUM + ")",
            "s_nonfossil_total": r"Total Non-Fossil Fuel\s+(" + NUM + ")",
            "s_total": r"Total Installed Capacity\s+(" + NUM + ")",
        }
        for k, p in pats.items():
            mm = re.search(p, t)
            if mm:
                rec[k] = num(mm.group(1))
    rec["offgrid_note"] = "Off-grid RES Capacity has been included from July-2021" in full
    return rec


METRICS = [
    # key, metric name, note
    ("coal", "coal_capacity", ""),
    ("coal_incl_lignite", "coal_capacity_incl_lignite", "older CEA layout: Coal column includes lignite"),
    ("lignite", "lignite_capacity", ""),
    ("gas", "gas_capacity", ""),
    ("diesel", "diesel_capacity", ""),
    ("thermal_total", "thermal_capacity_total", "coal+lignite+gas+diesel"),
    ("nuclear", "nuclear_capacity", ""),
    ("hydro", "large_hydro_capacity", "CEA 'Hydro' column (>25 MW, includes pumped storage)"),
    ("res_mnre", "res_mnre_capacity", "CEA 'RES (MNRE)' column: small hydro+wind+bio+WtE+solar"),
    ("renewable_total", "renewable_capacity_incl_large_hydro", "CEA 'Renewable Total' column = hydro + RES(MNRE)"),
    ("grand_total", "total_installed_capacity", "All-India utilities grand total"),
    ("small_hydro", "small_hydro_capacity", "RES break-up footnote"),
    ("wind", "wind_capacity", "RES break-up footnote"),
    ("bio_power", "bio_power_capacity", "RES break-up footnote: BM power/cogen"),
    ("bio_power_incl_wte", "bio_power_capacity_incl_wte", "RES break-up footnote: bio-power incl. waste-to-energy"),
    ("waste_to_energy", "waste_to_energy_capacity", "RES break-up footnote"),
    ("solar", "solar_capacity", "RES break-up footnote"),
    ("res_total", "res_mnre_capacity_breakup_total", "RES break-up footnote total"),
    ("s_wind", "wind_capacity", "page-1 summary"),
    ("s_solar", "solar_capacity", "page-1 summary"),
    ("s_bm_power", "bio_power_capacity", "page-1 summary"),
    ("s_wte", "waste_to_energy_capacity", "page-1 summary"),
    ("s_small_hydro", "small_hydro_capacity", "page-1 summary"),
    ("s_hydro_incl_psp", "large_hydro_capacity", "page-1 summary: Hydro (including PSPs)"),
    ("s_wind_solar_other", "res_mnre_capacity", "page-1 summary: Wind, Solar & Other RE"),
    ("s_res_incl_hydro", "renewable_capacity_incl_large_hydro", "page-1 summary: RES (including Hydro)"),
    ("s_nonfossil_total", "non_fossil_capacity_total", "page-1 summary"),
    ("s_fossil_total", "fossil_capacity_total", "page-1 summary"),
    ("s_total", "total_installed_capacity", "page-1 summary"),
]


def main():
    man = {}
    mp = os.path.join(RAW, "manifest.csv")
    with open(mp) as f:
        for r in csv.DictReader(f):
            man[r["file"]] = r
    files = sorted(glob.glob(os.path.join(RAW, "*.pdf")))
    rows, log = [], []
    for fp in files:
        try:
            rec = parse_file(fp)
        except Exception as e:  # noqa
            log.append({"file": os.path.basename(fp), "error": repr(e)})
            continue
        listed_month = man.get(rec["file"], {}).get("month")
        log.append({k: rec.get(k) for k in ["file", "asof", "res_asof", "table_found", "grand_total", "res_mnre", "solar", "wind", "s_solar", "res_breakup_unparsed"]} | {"listed_month": listed_month})
        asof = rec.get("asof")
        if not asof:
            continue
        seen = set()
        for key, metric, note in METRICS:
            if key not in rec or rec[key] is None:
                continue
            # footnote break-up refers to res_asof date
            period = asof
            n = note
            if key in ("small_hydro", "wind", "bio_power", "bio_power_incl_wte", "waste_to_energy", "solar", "res_total"):
                ra = rec.get("res_asof")
                if ra and ra != asof:
                    n += f"; RES break-up 'as on' {ra} (report dated {asof}) - period set to RES date"
                    period = ra
            if (metric, period) in seen:
                continue  # summary duplicates table; keep first (table/footnote)
            seen.add((metric, period))
            if rec.get("offgrid_note") and metric in ("solar_capacity", "res_mnre_capacity", "res_mnre_capacity_breakup_total"):
                n += "; CEA note: off-grid RES included from July-2021 onwards"
            rows.append({
                "geography": "India",
                "period_start": period,
                "period_end": period,
                "granularity": "monthly",
                "metric": metric,
                "value": rec[key],
                "unit": "MW",
                "source_id": SRC,
                "notes": f"CEA Installed Capacity report as on {asof} (listed month {listed_month}); {n}; file {rec['file']}".replace("; ;", ";"),
                "_report_asof": asof,
            })
    # The RES break-up footnote can lag the report date, so several reports may carry the
    # same RES-date values. Keep one row per (metric, period): prefer the report whose own
    # date equals the period, else the latest report (most recent revision). Values that
    # differ between reports for the same period are logged.
    best, conflicts = {}, []
    for r in rows:
        k = (r["metric"], r["period_start"])
        cur = best.get(k)
        if cur is None:
            best[k] = r
            continue
        if cur["value"] != r["value"]:
            conflicts.append((k, cur["value"], cur["_report_asof"], r["value"], r["_report_asof"]))
        def score(x):
            return (x["_report_asof"] == x["period_start"], x["_report_asof"])
        if score(r) > score(cur):
            best[k] = r
    rows = list(best.values())
    for r in rows:
        r.pop("_report_asof")
    if conflicts:
        print("value conflicts between reports for same period (kept preferred):")
        for c in conflicts:
            print("  ", c)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "_cea_installed_capacity_monthly.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["period_start"], r["metric"])))
    keys = sorted({k for r in log for k in r})
    with open(os.path.join(OUT, "_cea_ic_parse_log.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(log)
    print(len(rows), "rows from", len(files), "files")


if __name__ == "__main__":
    main()
