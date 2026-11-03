"""Download CEA transmission line / substation growth & executive summaries.

Reads data/raw/transmission/cea_reports_index.csv (built from the CEA dashboard pages)
and downloads:
  - lines growth summary: every month available (for monthly inter-regional capacity, cumulative ckm)
  - substation growth summary: every March + latest month
  - lines & substation executive summary (target vs achievement): every March + latest month
Run through the Indian proxy:  myproxy run .venv/bin/python -I scripts/transmission/01_download_cea.py
"""
import csv, os, sys, time, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission")
OUT = os.path.join(RAW, "cea")
BASE = "https://cea.nic.in"

KIND = {
    ("cea_dash_10052.html", "Transmission Growth Summary"): "lines_growth",
    ("cea_dash_10052.html", "Growth Summary"): "lines_growth",
    ("cea_dash_10052.html", "Transmissions Executive Summary"): "lines_exec",
    ("cea_dash_10052.html", "Executive Summary"): "lines_exec",
    ("cea_dash_10051.html", "Substations Growth Summary"): "ss_growth",
    ("cea_dash_10051.html", "Growth Summary"): "ss_growth",
    ("cea_dash_10051.html", "Substations Executive Summary"): "ss_exec",
    ("cea_dash_10051.html", "Executive Summary"): "ss_exec",
}

rows = {}
for r in csv.DictReader(open(os.path.join(RAW, "cea_reports_index.csv"))):
    k = KIND.get((r["page"], r["title"]))
    if k:
        rows.setdefault((k, r["period"]), r["href"])

latest = {k: max(p for kk, p in rows if kk == k) for k in set(k for k, _ in rows)}
todo = []
for (k, p), href in sorted(rows.items()):
    if k == "lines_growth" or p.endswith("-03") or p == latest[k]:
        todo.append((k, p, href))

os.makedirs(OUT, exist_ok=True)
log = csv.writer(open(os.path.join(OUT, "download_log.csv"), "a"))
for k, p, href in todo:
    fn = os.path.join(OUT, f"{k}_{p}.pdf")
    if os.path.exists(fn) and os.path.getsize(fn) > 5000:
        continue
    for attempt in range(3):
        rc = subprocess.call(["curl", "-sL", "--max-time", "120", "-A", "Mozilla/5.0", BASE + href, "-o", fn])
        if rc == 0 and os.path.exists(fn) and open(fn, "rb").read(4) == b"%PDF":
            break
        time.sleep(3)
    ok = os.path.exists(fn) and open(fn, "rb").read(4) == b"%PDF"
    log.writerow([k, p, BASE + href, fn, ok, time.strftime("%Y-%m-%d %H:%M")])
    print(k, p, ok, flush=True)
    time.sleep(0.7)
