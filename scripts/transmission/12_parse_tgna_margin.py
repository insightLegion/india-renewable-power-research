"""Parse Grid-India 'Margin under T-GNA for the Evacuation of Renewable Generation from ISTS RE Complexes' PDFs.

Input: data/raw/transmission/gridindia/tgna/*.pdf (59 issues, Nov 2025 - Oct 2026)
Outputs:
  data/processed/transmission/re_complex_tgna_margin.csv  (tidy; one row per complex x issue x metric)
  data/processed/transmission/_tgna_constraints.csv       (intermediate; merged into grid_constraints.csv by 14_build_grid_constraints.py)
Metrics per RE complex (as printed, MW):
  connectivity_quantum (A), gna_effective (B), gna_not_effective (C=A-B), permissible_transmission_limit (incl. BESS),
  additional_re_via_bess_peak_solar, tgna_margin_min (minimum of column F over the day's time blocks; DERIVED: min taken here),
  tgna_margin_max (max of F; DERIVED)
"""
import csv, glob, os, re
import pdfplumber
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission/gridindia/tgna")
OUT = os.path.join(ROOT, "data/processed/transmission")
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

def num(s):
    s = (s or "").replace(",", "").strip()
    return int(float(s)) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None

def eff_date(text, fn):
    m = re.search(r"(?:Effective\s*from|Status\s*as\s*on)\s*:?\s*(\d{1,2})(?:st|nd|rd|th)?\s*([A-Za-z]+)\.?,?\s*(\d{4})", text)
    if m:
        return f"{m.group(3)}-{MON[m.group(2)[:3].lower()]:02d}-{int(m.group(1)):02d}", "effective date printed in report"
    m = re.search(r"_(\d{1,2})(?:st|nd|rd|th)?_([A-Za-z]+)_(\d{4})", fn)
    return f"{m.group(3)}-{MON[m.group(2)[:3].lower()]:02d}-{int(m.group(1)):02d}", "date from file title (issue date)"

rows, cons = [], []
for f in sorted(glob.glob(os.path.join(RAW, "*.pdf"))):
    fn = os.path.basename(f)
    title_date = re.search(r"_(\d{1,2})(?:st|nd|rd|th)?_([A-Za-z]+)_(\d{4})", fn)
    sid = "TRN-GI-TGNA"
    with pdfplumber.open(f) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        tables = [t for p in pdf.pages for t in p.extract_tables()]
    d, dnote = eff_date(text, fn)
    issue = f"{title_date.group(3)}-{MON[title_date.group(2)[:3].lower()]:02d}-{int(title_date.group(1)):02d}"
    cur = None
    complexes = []
    for t in tables:
        hdr = None
        for r in t:
            r = [(c or "").replace("\n", " ").strip() for c in r]
            if any("GNA is effective" in c for c in r):
                hdr = r; continue
            if hdr is None:
                continue
            col = {}
            for i, h in enumerate(hdr):
                hl = h.lower()
                if "connectivity quantum" in hl or hl.startswith("commissioned"): col["A"] = i
                elif "available t-gna margin" in hl: col["G"] = i
                elif "not effective" in hl: col["C"] = i
                elif "gna is effective" in hl: col["B"] = i
                elif "permissible" in hl: col["E"] = i
                elif "additional re" in hl: col["D"] = i
                elif "scheduling limit" in hl or "noc for t-gna" in hl or "allowed under t-gna" in hl: col["F"] = i
                elif "limiting" in hl: col["L"] = i
                elif hl.startswith("region"): col["R"] = i
                elif hl.startswith("area"): col["AR"] = i
                elif "pooling" in hl: col["P"] = i
            g = lambda k: r[col[k]] if k in col and col[k] < len(r) else ""
            if g("R"):
                cur = dict(region=g("R").rstrip("*").strip(), area=g("AR"), pooling=g("P"), A=num(g("A")), B=num(g("B")),
                           C=num(g("C")), E=num(g("E")), E_text=g("E"), D=num(g("D")), F=[], G=[], L=g("L"))
                complexes.append(cur)
            if cur is not None:
                fv = num(g("F"))
                if fv is not None:
                    cur["F"].append(fv)
                gv = num(g("G"))
                if gv is not None:
                    cur["G"].append(gv)
                if cur["E"] is None and num(g("E")) is not None: cur["E"] = num(g("E"))
                if cur["A"] is None and num(g("A")) is not None: cur["A"] = num(g("A"))
                if cur["B"] is None and num(g("B")) is not None: cur["B"] = num(g("B"))
                if cur["C"] is None and num(g("C")) is not None: cur["C"] = num(g("C"))
                if g("L") and g("L") not in cur["L"]: cur["L"] = (cur["L"] + " " + g("L")).strip()
    if not complexes:
        print("NO TABLE", fn); continue
    for c in complexes:
        geo = c["area"] or c["region"]
        note = f"{c['region']}; pooling stations: {c['pooling'][:200]}; period = issue date from file title; effective/status date printed: {d}"
        for metric, val in (("connectivity_quantum_commissioned", c["A"]), ("gna_effective", c["B"]), ("gna_not_effective", c["C"]),
                            ("permissible_transmission_limit_incl_bess", c["E"]), ("additional_re_injection_via_bess_peak_solar", c["D"]),
                            ("tgna_injection_limit_min_over_day", min(c["F"]) if c["F"] else None),
                            ("tgna_injection_limit_max_over_day", max(c["F"]) if c["F"] else None),
                            ("available_tgna_margin_min_over_day", min(c["G"]) if c["G"] else None),
                            ("available_tgna_margin_max_over_day", max(c["G"]) if c["G"] else None)):
            if val is None:
                continue
            rows.append(dict(geography=geo, period_start=issue, period_end=issue, granularity="snapshot", metric=metric, value=val,
                             unit="MW", source_id=sid, notes=note + ("; DERIVED (min/max over time blocks)" if "over_day" in metric else "")))
        if c["L"]:
            cons.append(dict(date=issue, issue=issue, region=c["region"], area=geo, pooling=c["pooling"], text=re.sub(r"\s+", " ", c["L"])))
    print(fn, d, [(c["area"], c["A"], c["B"], c["C"], min(c["F"]) if c["F"] else None) for c in complexes])

with open(os.path.join(OUT, "re_complex_tgna_margin.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(os.path.join(OUT, "_tgna_constraints.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(cons[0].keys())); w.writeheader(); w.writerows(cons)
print("rows", len(rows), "constraints", len(cons))
