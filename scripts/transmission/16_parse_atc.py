"""Parse NLDC monthly TTC/ATC declarations (inter-regional corridors and regional import/export).

Input: data/raw/transmission/gridindia/atc/atc_<YYYY-MM>_rev<N>.pdf (one file per month: the highest revision on the
       Grid-India site, i.e. the last declaration for that month)
Output: data/processed/transmission/ttc_atc_monthly.csv
  columns: month, corridor, date_text, time_period, ttc_MW, reliability_margin_MW, atc_MW, alt_values, revision, source_id
  - corridor/date are forward-filled within a table (the PDFs use merged cells)
  - when a cell holds two values (e.g. '17200 16250**'), the first is taken and the full cell text is kept in alt_values
"""
import csv, glob, os, re
import pdfplumber
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission/gridindia/atc")
OUT = os.path.join(ROOT, "data/processed/transmission")

def first_num(s):
    m = re.search(r"-?\d[\d,]*", s or "")
    return int(m.group(0).replace(",", "")) if m else None

def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()

out = []
for f in sorted(glob.glob(os.path.join(RAW, "atc_*.pdf"))):
    ym, rev = re.search(r"atc_(\d{4}-\d{2})_rev(\d+)", f).groups()
    sid = f"TRN-GI-ATC"
    n0 = len(out)
    try:
        pdf = pdfplumber.open(f)
    except Exception as e:
        print("ERR", f, e); continue
    with pdf:
        for page in pdf.pages:
            for tb in page.extract_tables():
                hdr_i = next((i for i, r in enumerate(tb) if any("Corridor" in (c or "") for c in r)), None)
                if hdr_i is None:
                    continue
                hdr = [clean(c) for c in tb[hdr_i]]
                def col(rx):
                    return next((k for k, h in enumerate(hdr) if re.search(rx, h, re.I)), None)
                cc, dc, tc = col(r"^Corridor"), col(r"^Date"), col(r"Time")
                ttc, rm, atc = col(r"Total Transfer"), col(r"Reliability"), col(r"Available Transfer")
                if None in (cc, ttc, atc):
                    continue
                corr = date = ""
                for r in tb[hdr_i + 1:]:
                    r = [clean(c) for c in r] + [""] * 12
                    if r[cc]:
                        corr = r[cc]
                    if dc is not None and r[dc]:
                        date = r[dc]
                    tv = first_num(r[ttc]); av = first_num(r[atc])
                    if not corr or (tv is None and av is None):
                        if corr and re.search(r"No limit|not specified|NA", r[ttc] + r[atc], re.I):
                            out.append(dict(month=ym, corridor=corr, date_text=date, time_period=r[tc] if tc is not None else "",
                                            ttc_MW="", reliability_margin_MW="", atc_MW="", alt_values=(r[ttc] or r[atc])[:80],
                                            revision=rev, source_id=sid))
                        continue
                    alt = " | ".join(x for x in (r[ttc], r[atc]) if re.search(r"\d+\D+\d+", x))
                    out.append(dict(month=ym, corridor=corr, date_text=date, time_period=r[tc] if tc is not None else "",
                                    ttc_MW=tv if tv is not None else "", reliability_margin_MW=first_num(r[rm]) if rm is not None and first_num(r[rm]) is not None else "",
                                    atc_MW=av if av is not None else "", alt_values=alt[:120], revision=rev, source_id=sid))
    print(ym, rev, len(out) - n0, flush=True)

with open(os.path.join(OUT, "ttc_atc_monthly.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print("rows", len(out))
