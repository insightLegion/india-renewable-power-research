"""List files on Grid-India's webapi for a given FileType, per FY period and month.

Usage (via Indian proxy):
  myproxy run .venv/bin/python -I scripts/generation_demand/gi_list_files.py DAILY_PSP_REPORT [FY ...]
Writes data/raw/generation_demand/listings/<TYPE>.json (list of file records).
"""
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/raw/generation_demand/listings"
API = "https://webapi.grid-india.in/api/v1/"
H = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}


def post(ep, body):
    for i in range(4):
        try:
            r = requests.post(API + ep, json=body, headers=H, timeout=90)
            r.raise_for_status()
            return r.json().get("retData") or []
        except Exception as e:  # noqa
            print("retry", ep, body, e, file=sys.stderr)
            time.sleep(5 * (i + 1))
    return []


def main():
    ftype = sys.argv[1]
    only = set(sys.argv[2:])
    OUT.mkdir(parents=True, exist_ok=True)
    periods = [p["PeriodYear"] for p in post("file/get-period", {"_source": "GRDW", "_fileType": ftype})]
    print("periods", periods)
    out_path = OUT / f"{ftype}.json"
    allrecs = json.loads(out_path.read_text()) if out_path.exists() else []
    seen = {r["Id"] for r in allrecs}
    for fy in periods:
        if only and fy not in only:
            continue
        for m in ["00"] + [f"{i:02d}" for i in range(1, 13)]:
            recs = post("file", {"_source": "GRDW", "_type": ftype, "_fileDate": fy, "_month": m})
            new = [r for r in recs if r["Id"] not in seen]
            for r in new:
                seen.add(r["Id"])
            allrecs.extend(new)
            print(fy, m, len(recs), "new", len(new), flush=True)
            time.sleep(0.7)
            if m == "00" and recs and len(new) == len(recs) and len(recs) > 300:
                # month "00" may return the whole year; months add nothing new then
                pass
    out_path.write_text(json.dumps(allrecs, indent=0))
    print("total", len(allrecs))


if __name__ == "__main__":
    main()
