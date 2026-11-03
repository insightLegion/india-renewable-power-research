"""Extract constrained elements from NLDC/Grid-India quarterly 'Operational Feedback on Transmission Constraints'.

Input: data/raw/transmission/gridindia/qof/*.pdf (quarterly, Jan 2015 - Jul 2026)
Output: data/processed/transmission/_qof_constraints.csv (merged into grid_constraints.csv by 15_build_grid_constraints.py)

Method
 - Pages are located with pdftotext; tables are read with pdfplumber.
 - A table is kept when its header has a 'Corridor'/'ICT'/'Element' column and a 'Description' column
   (the 'Transmission Line Constraints' and 'ICT Constraints' tables of each region chapter).
 - Continuation rows (no serial number) are appended to the previous element's description.
 - Region = the 'Transmission Constraints in <X> Region' chapter the page falls in.
 - Section headings from the table of contents that are RE-specific (keyword match) are also kept as items.
 - re_related = yes if element or description matches RE keywords (solar, wind, RE, renewable, pooling, known RE pooling
   station names). This flag is a keyword heuristic, not a Grid-India classification.
"""
import csv, glob, os, re, subprocess, sys
import pdfplumber
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission/gridindia/qof")
OUT = os.path.join(ROOT, "data/processed/transmission")
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
RE_KW = re.compile(r"\bRE\b|\bREZ\b|renewable|solar|wind|pooling|\bPS\b|Bhadla|Fatehgarh|Bikaner|Khavda|Pavagada|Tirunelveli|Kayathar|"
                   r"Bhuj|Lakadia|Jaisalmer|Barmer|Ramgarh|evacuat|NP ?Kunta|Anantapur|Ananthapuram|Kurnool|Koppal|Gadag|Rewa|VRE|"
                   r"Tuticorin|Pugalur|Hiriyur|Jamnagar|Dwarka|Jam Khambhaliya|Kutch|\bGIB\b|Bustard", re.I)
GENERIC = re.compile(r"^(Transmission Line Constraints|ICT Constraints|Nodes Experiencing|Lines opened|Lines / ICTs|Lines/ICTs|Delay in|"
                     r"Outage of|Oscillations|Transmission Tower|Transmission Elements|Important lines|Substations with|Section|Chapter|"
                     r"Grid Events|Frequency Response|SPS|System Protection|Table|Introduction|Demand met|Uncertainty|Action taken|Markets|"
                     r"Other issues|Congestion Observed|Congestion observed|Contents)", re.I)
REGIONS = [("Northern", "Northern Region"), ("Eastern", "Eastern Region"), ("Western", "Western Region"),
           ("Southern", "Southern Region"), ("North[ -]Eastern", "North-Eastern Region")]

def report_date(fn):
    m = re.search(r"Feedback_([A-Za-z]+)_(\d{4})", fn)
    return int(m.group(2)), MON[m.group(1)[:3].lower()]

def quarter_covered(y, m):
    # reports issued in Jan/Apr/Jul/Oct cover the preceding calendar quarter
    em = m - 1 if m > 1 else 12
    ey = y if m > 1 else y - 1
    sm = em - 2
    import calendar
    return f"{ey}-{sm:02d}-01", f"{ey}-{em:02d}-{calendar.monthrange(ey, em)[1]:02d}"

def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()

rows = []
files = sorted(glob.glob(os.path.join(RAW, "*.pdf")))
if len(sys.argv) > 1:
    files = [f for f in files if any(a in f for a in sys.argv[1:])]
for f in files:
    fn = os.path.basename(f)
    y, m = report_date(fn)
    ps, pe = quarter_covered(y, m)
    sid = f"TRN-GI-QOF-{y}-{m:02d}"
    pages = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True).stdout.split("\f")
    # TOC (first 12 pages): RE-specific section headings
    toc = "\n".join(pages[:12])
    region = "All India"
    for l in toc.splitlines():
        mm = re.search(r"Transmission Constraints in (.+?) Region", l)
        if mm:
            region = mm.group(1).strip() + " Region"
            continue
        hm = re.match(r"\s*(\d+(?:\.\d+){1,3})\.?\s+(.+?)\s*\.{4,}\s*\d+\s*$", l)
        if hm:
            title = clean(hm.group(2)).rstrip(":")
            if not GENERIC.match(title) and RE_KW.search(title):
                rows.append(dict(period_start=ps, period_end=pe, report=f"{y}-{m:02d}", region=region if hm.group(1)[0] != "1" else "All India",
                                 element=title[:200], constraint_type="section heading (RE-specific issue)", description=title,
                                 re_related="yes", source_id=sid))
    # locate region of each page (body), skipping TOC
    reg_of, cur = {}, "All India"
    for i, p in enumerate(pages):
        if i > 8:
            mm = re.search(r"Chapter\s*\d+\s*:?\s*Transmission Constraints in (.+?) Region", p)
            if mm:
                cur = mm.group(1).strip() + " Region"
        reg_of[i] = cur
    cand = [i for i, p in enumerate(pages) if i > 8 and re.search(r"Description", p, re.I) and re.search(r"Corridor|\bICTs?\b", p)
            and re.search(r"Season|Antecedent|constraint", p, re.I)]
    n0 = len(rows)
    with pdfplumber.open(f) as pdf:
        for i in cand:
            try:
                tables = pdf.pages[i].extract_tables()
            except Exception as e:
                print("ERR", fn, i, e); continue
            for tb in tables:
                if not tb:
                    continue
                hdr = [clean(c) for c in tb[0]]
                ec = next((k for k, h in enumerate(hdr) if re.search(r"Corridor|^ICT|ICTs|Element|Name of", h, re.I)), None)
                dc = next((k for k, h in enumerate(hdr) if re.search(r"Description", h, re.I)), None)
                if ec is None or dc is None:
                    continue
                ctype = "ICT constraint" if re.search(r"ICT", hdr[ec]) else "transmission line/corridor constraint"
                last = None
                for r in tb[1:]:
                    r = [clean(c) for c in r] + [""] * 8
                    if r[0] and re.match(r"^\d+[a-z]?\.?$", r[0]) and r[ec]:
                        last = dict(period_start=ps, period_end=pe, report=f"{y}-{m:02d}", region=reg_of[i], element=r[ec][:200],
                                    constraint_type=ctype, description=r[dc], re_related="", source_id=sid)
                        rows.append(last)
                    elif last is not None and r[dc] and not r[0]:
                        last["description"] = (last["description"] + " " + r[dc]).strip()
    for r in rows[n0:]:
        r["description"] = r["description"][:1500]
        r["re_related"] = "yes" if RE_KW.search(r["element"] + " " + r["description"]) else "no"
    print(fn, ps, pe, "table rows", len(rows) - n0, flush=True)

with open(os.path.join(OUT, "_qof_constraints.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("rows", len(rows))
