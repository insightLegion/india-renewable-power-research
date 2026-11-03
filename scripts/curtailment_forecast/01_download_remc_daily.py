"""Download Grid-India NLDC daily REMC (VRE) reports listed on grid-india.in/en/reports/daily-vre-report.

Run via Indian proxy:  myproxy run .venv/bin/python -I scripts/curtailment_forecast/01_download_remc_daily.py
Listing API: POST https://webapi.grid-india.in/api/v1/file {"_source":"GRDW","_type":"DAILY_VRE_REPORT","_fileDate":FY,"_month":"00"}
Files saved to data/raw/curtailment_forecast/gridindia/remc_daily/<FilePath basename>; a manifest CSV is written.
"""
import csv
import json
import os
import re
import sys
import time

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw", "curtailment_forecast", "gridindia")
OUT = os.path.join(RAW, "remc_daily")
os.makedirs(OUT, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
FYS = ["2024-25", "2025-26", "2026-27"]

rows = []
for fy in FYS:
    r = requests.post("https://webapi.grid-india.in/api/v1/file", headers=H, timeout=120,
                      json={"_source": "GRDW", "_type": "DAILY_VRE_REPORT", "_fileDate": fy, "_month": "00"})
    r.raise_for_status()
    data = r.json()["retData"]
    with open(os.path.join(RAW, f"vre_files_{fy}.json"), "w") as f:
        json.dump(data, f)
    for d in data:
        m = re.match(r"\s*(\d{1,2})[.\-](\d{1,2})[.\-](\d{4})", d["Title_"])
        date = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""
        rows.append({"fy_listing": fy, "title": d["Title_"], "title_date": date, "file_path": d["FilePath"],
                     "size_kb": d["SizeInKb"], "created_on": d["CreatedOn"]})
    time.sleep(1)

n_ok = 0
for i, row in enumerate(rows):
    url = "https://webcdn.grid-india.in/" + row["file_path"]
    local = os.path.join(OUT, os.path.basename(row["file_path"]))
    row["local_file"] = os.path.relpath(local, ROOT)
    if os.path.exists(local) and os.path.getsize(local) > 10000:
        row["status"] = "ok"; n_ok += 1
        continue
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=180)
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                with open(local, "wb") as f:
                    f.write(r.content)
                row["status"] = "ok"; n_ok += 1
                break
            row["status"] = f"http_{r.status_code}"
        except Exception as e:  # noqa
            row["status"] = f"err_{type(e).__name__}"
        time.sleep(3)
    time.sleep(0.7)
    if i % 25 == 0:
        print(i, len(rows), n_ok, flush=True)

with open(os.path.join(RAW, "remc_daily_manifest.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("done", len(rows), n_ok)
