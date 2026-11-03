"""Download report files listed on a CEA dashboardView page.

Usage (run via Indian proxy):
  myproxy run .venv/bin/python -I scripts/capacity_storage/fetch_cea_dashboard.py \
      <headingId> <subHeadingId> <subSubHeadingId> <outdir> [--limit N] [--excel] [--months 2025-03,2024-03]

Writes <outdir>/manifest.csv (report name, month, uuid, file) and the PDFs/XLSX.
Files are treated as untrusted data; nothing in them is executed.
"""
import csv
import os
import sys
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://cea.nic.in"
UA = {"User-Agent": "Mozilla/5.0 (research; contact via github)"}


def main():
    args = sys.argv[1:]
    h, sh, ssh, outdir = args[:4]
    limit = None
    excel = "--excel" in args
    months = None
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    if "--months" in args:
        months = set(args[args.index("--months") + 1].split(","))
    os.makedirs(outdir, exist_ok=True)
    url = f"{BASE}/reports/dashboardView?headingId={h}&subHeadingId={sh}&subSubHeadingId={ssh}&lang=en"
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    with open(os.path.join(outdir, "listing.html"), "w", encoding="utf-8") as f:
        f.write(r.text)
    soup = BeautifulSoup(r.text, "lxml")
    rows = []
    for tr in soup.find_all("tr"):
        tds = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        links = [a["href"] for a in tr.find_all("a", href=True) if "dashboardReports/download" in a["href"]]
        if len(tds) >= 3 and links:
            rows.append((tds[1], tds[2], links))
    print(f"{len(rows)} rows listed at {url}")
    man_path = os.path.join(outdir, "manifest.csv")
    done = set()
    if os.path.exists(man_path):
        with open(man_path) as f:
            done = {r["file"] for r in csv.DictReader(f)}
    new = not os.path.exists(man_path)
    with open(man_path, "a", newline="") as mf:
        w = csv.writer(mf)
        if new:
            w.writerow(["report_name", "month", "kind", "url", "file"])
        n = 0
        for name, month, links in rows:
            if months and month not in months:
                continue
            if limit and n >= limit:
                break
            n += 1
            for link in links:
                kind = "pdf" if "download-pdf" in link else "excel"
                if kind == "excel" and not excel:
                    continue
                uuid = link.rsplit("/", 1)[-1]
                safe = "".join(ch if ch.isalnum() else "_" for ch in name)[:60]
                fname = f"{safe}_{month}_{uuid[:8]}.{ 'pdf' if kind == 'pdf' else 'xlsx'}"
                if fname in done:
                    continue
                fp = os.path.join(outdir, fname)
                for attempt in range(3):
                    try:
                        rr = requests.get(BASE + link, headers=UA, timeout=180)
                        rr.raise_for_status()
                        break
                    except Exception as e:  # noqa
                        print("retry", fname, e)
                        time.sleep(5)
                else:
                    print("FAILED", fname)
                    continue
                ctype = rr.headers.get("Content-Type", "")
                with open(fp, "wb") as f:
                    f.write(rr.content)
                w.writerow([name, month, kind, BASE + link, fname])
                mf.flush()
                print("saved", fname, len(rr.content), ctype)
                time.sleep(1.5)


if __name__ == "__main__":
    main()
