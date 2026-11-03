"""Download CERC Market Monitoring Cell monthly reports on the short-term power market (2015-2026).

Listing pages: https://cercind.gov.in/report_MM-<YEAR>.html ; PDFs relative to https://cercind.gov.in/
Run via Indian proxy: myproxy run .venv/bin/python -I scripts/transmission/04_download_cerc_mmc.py
"""
import os, re, subprocess, time, csv, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "data/raw/transmission/cerc")
os.makedirs(os.path.join(D, "mmc"), exist_ok=True)
BASE = "https://cercind.gov.in/"
log = csv.writer(open(os.path.join(D, "download_log.csv"), "a"))

def curl(url, out, t=180):
    for _ in range(3):
        subprocess.call(["curl", "-sL", "--max-time", str(t), "-A", "Mozilla/5.0", url, "-o", out])
        if os.path.exists(out) and os.path.getsize(out) > 500:
            return True
        time.sleep(5)
    return False

for y in range(2015, 2027):
    page = os.path.join(D, f"report_MM-{y}.html")
    if not os.path.exists(page):
        curl(BASE + f"report_MM-{y}.html", page)
    html = open(page, encoding="latin-1").read()
    hrefs = [h for h in re.findall(r'href="([^"]+\.pdf)"', html, re.I) if "market_monitoring" in h or "MMC" in h]
    for h in hrefs:
        out = os.path.join(D, "mmc", f"{y}__" + re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.basename(h)))
        if os.path.exists(out) and open(out, "rb").read(4) == b"%PDF":
            continue
        url = BASE + urllib.parse.quote(h)
        ok = curl(url, out) and open(out, "rb").read(4) == b"%PDF"
        log.writerow([y, h, url, out, ok]); print(y, h, ok, flush=True)
        time.sleep(1)
