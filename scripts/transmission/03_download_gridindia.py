"""Download Grid-India (NLDC) files relevant to transmission constraints.

Uses the public webapi (POST https://webapi.grid-india.in/api/v1/file {_source:GRDW,_type:<FileType>})
which the grid-india.in SPA itself calls. File types found from the page metadata API:
  QUARTERLY_OPERATIONAL_FEEDBACK  -> /en/reports/quarterly-operational-feedback
  F_PG00413                       -> /en/operations/margin-under-tgna  (Margin under T-GNA for RE evacuation from ISTS RE complexes)
  ATC_INTER_REGIONAL              -> /en/operations/monthly-atc-inter-regional  (monthly TTC/ATC, many revisions)
Run via Indian proxy: myproxy run .venv/bin/python -I scripts/transmission/03_download_gridindia.py [qof|tgna|atc]
"""
import json, os, re, subprocess, sys, time, csv
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission/gridindia")
CDN = "https://webcdn.grid-india.in/"
API = "https://webapi.grid-india.in/api/v1/file"

def listing(ftype):
    fn = os.path.join(RAW, f"files_{ftype}.json")
    if not os.path.exists(fn):
        subprocess.run(["curl", "-s", "--max-time", "90", "-A", "Mozilla/5.0", "-H", "Content-Type: application/json",
                        "-X", "POST", "-d", json.dumps({"_source": "GRDW", "_type": ftype}), API, "-o", fn], check=True)
    return json.load(open(fn))["retData"]

def get(path, out):
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return True
    for _ in range(3):
        subprocess.call(["curl", "-s", "--max-time", "600", "-A", "Mozilla/5.0", CDN + path, "-o", out])
        if os.path.exists(out) and open(out, "rb").read(4) == b"%PDF":
            return True
        time.sleep(5)
    return False

MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

def safe(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:120]

what = sys.argv[1:] or ["tgna", "qof", "atc"]
log = csv.writer(open(os.path.join(RAW, "download_log.csv"), "a"))

if "tgna" in what:
    d = os.path.join(RAW, "tgna"); os.makedirs(d, exist_ok=True)
    for r in listing("F_PG00413"):
        out = os.path.join(d, safe(r["Title_"]) + ".pdf")
        ok = get(r["FilePath"], out); log.writerow(["tgna", r["Title_"], CDN + r["FilePath"], out, ok]); print("tgna", r["Title_"], ok, flush=True)
        time.sleep(0.5)

if "qof" in what:
    d = os.path.join(RAW, "qof"); os.makedirs(d, exist_ok=True)
    for r in listing("QUARTERLY_OPERATIONAL_FEEDBACK"):
        t = r["Title_"]
        m = re.search(r"Operational[ _]Feedback_([A-Za-z]+)[ _]?(\d{4})", t)
        if not m or "Addendum" in t:
            continue
        if int(m.group(2)) < 2015:
            continue
        out = os.path.join(d, safe(t) + ".pdf")
        ok = get(r["FilePath"], out); log.writerow(["qof", t, CDN + r["FilePath"], out, ok]); print("qof", t, ok, flush=True)
        time.sleep(1)

if "atc" in what:
    # one file per month: the highest revision number published for that month
    d = os.path.join(RAW, "atc"); os.makedirs(d, exist_ok=True)
    best = {}
    for r in listing("ATC_INTER_REGIONAL"):
        t = r["Title_"]
        m = re.search(r"ATC[\s_]+NLDC[\s_]+([A-Za-z]+)[\s_]*'?(\d{2,4})[\s_]+Rev[\s_]*(\d+)", t, re.I)
        if not m:
            continue
        mon = MON.get(m.group(1)[:3].lower())
        yr = int(m.group(2)); yr = yr + 2000 if yr < 100 else yr
        if not mon or yr < 2015 or (yr, mon) > (2026, 11):
            continue
        rev = int(m.group(3))
        k = (yr, mon)
        if k not in best or rev > best[k][0]:
            best[k] = (rev, r)
    for (yr, mon), (rev, r) in sorted(best.items()):
        out = os.path.join(d, f"atc_{yr}-{mon:02d}_rev{rev}.pdf")
        ok = get(r["FilePath"], out); log.writerow(["atc", r["Title_"], CDN + r["FilePath"], out, ok]); print("atc", yr, mon, rev, ok, flush=True)
        time.sleep(0.5)
