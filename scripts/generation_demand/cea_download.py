"""Download CEA dashboard report files from cea_listing.csv.

Usage: myproxy run .venv/bin/python -I scripts/generation_demand/cea_download.py PAGE KIND [NAME_SUBSTR] [DATE_REGEX]
Saves to data/raw/generation_demand/cea/<PAGE>/<date>_<slug>.<ext>
"""
import csv
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CEA = ROOT / "data/raw/generation_demand/cea"
H = {"User-Agent": "Mozilla/5.0"}

page, kind = sys.argv[1], sys.argv[2]
name_sub = sys.argv[3] if len(sys.argv) > 3 else ""
date_re = re.compile(sys.argv[4]) if len(sys.argv) > 4 else None
out = CEA / page
out.mkdir(parents=True, exist_ok=True)
rows = [r for r in csv.DictReader((CEA / "cea_listing.csv").open())
        if r["page"] == page and r["kind"] == kind and name_sub.lower() in r["name"].lower()
        and (not date_re or date_re.search(r["date"]))]
print(len(rows), "files")
for r in rows:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", r["name"])[:40]
    stem = f"{r['date']}_{slug}_{r['report_id']}"
    if list(out.glob(stem + ".*")):
        continue
    for i in range(3):
        try:
            resp = requests.get(r["url"], headers=H, timeout=180)
            if resp.status_code == 200 and len(resp.content) > 200:
                ct = resp.headers.get("content-type", "")
                cd = resp.headers.get("content-disposition", "")
                m = re.search(r'filename="?([^";]+)', cd)
                ext = (m.group(1).rsplit(".", 1)[-1] if m and "." in m.group(1) else
                       "pdf" if "pdf" in ct else "xlsx" if "sheet" in ct else "xls" if "excel" in ct else "bin")
                ext = re.sub(r"[^a-z0-9].*$", "", ext.lower())
                (out / f"{stem}.{ext}").write_bytes(resp.content)
                print("ok", stem, ext, len(resp.content), flush=True)
                break
            print("bad", resp.status_code, r["url"], flush=True)
        except Exception as e:  # noqa
            print("err", e, flush=True)
        time.sleep(4 * (i + 1))
    time.sleep(1)
