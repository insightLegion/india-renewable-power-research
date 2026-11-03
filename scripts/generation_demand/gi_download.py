"""Download Grid-India files listed by gi_list_files.py.

For DAILY_PSP_REPORT: one file per report date, preferring xls/xlsx over pdf.
Report date = date in title (DD.MM.YY or DD-MM-YY); the report covers the PREVIOUS day.
Writes manifest CSV next to the files.

Usage: myproxy run .venv/bin/python -I scripts/generation_demand/gi_download.py DAILY_PSP_REPORT [--all-formats]
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/generation_demand"
CDN = "https://webcdn.grid-india.in/"
H = {"User-Agent": "Mozilla/5.0"}


def title_date(t):
    m = re.match(r"^(\d{2})[.\-](\d{2})[.\-](\d{2,4})", t or "")
    if not m:
        return None
    d, mo, y = m.groups()
    y = int(y)
    y = y + 2000 if y < 100 else y
    return f"{y:04d}-{mo}-{d}"


def ext(r):
    p = r["FilePath"].lower()
    return p.rsplit(".", 1)[-1]


def main():
    ftype = sys.argv[1]
    allfmt = "--all-formats" in sys.argv
    recs = json.loads((RAW / "listings" / f"{ftype}.json").read_text())
    outdir = RAW / ftype.lower()
    outdir.mkdir(parents=True, exist_ok=True)
    bydate = {}
    for r in recs:
        d = title_date(r["Title_"])
        if not d:
            continue
        bydate.setdefault(d, []).append(r)
    chosen = []
    for d, rs in sorted(bydate.items()):
        if allfmt:
            chosen += [(d, r) for r in rs]
            continue
        xl = [r for r in rs if ext(r) in ("xls", "xlsx")]
        pdf = [r for r in rs if ext(r) == "pdf"]
        pick = xl or pdf
        if pick:
            chosen.append((d, max(pick, key=lambda r: r["Id"])))
    asc = "--asc" in sys.argv
    rng = None
    if "--range" in sys.argv:
        i = sys.argv.index("--range")
        rng = (sys.argv[i + 1], sys.argv[i + 2])
        chosen = [c for c in chosen if rng[0] <= c[0] <= rng[1]]
    if "--days" in sys.argv:  # sampling: only these days of month, e.g. --days 01,08,15,22
        days = set(sys.argv[sys.argv.index("--days") + 1].split(","))
        chosen = [c for c in chosen if c[0][8:10] in days]
    man_path = outdir / ("manifest_asc.csv" if asc else f"manifest_{rng[0]}.csv" if rng else "manifest.csv")
    done = {}
    if man_path.exists():
        for row in csv.DictReader(man_path.open()):
            done[row["file_path"]] = row
    up = outdir / "uploaded_to_bucket.txt"  # names of files confirmed in the bucket (written by the prune step)
    uploaded = set(up.read_text().split()) if up.exists() else set()
    n = 0
    for d, r in sorted(chosen, key=lambda x: x[0], reverse=not asc):
        fp = r["FilePath"]
        local = outdir / f"{d}_{Path(fp).name}"
        if local.name in uploaded:  # already in the B2 bucket (local copy pruned)
            continue
        if local.exists() and local.stat().st_size > 0:
            if fp not in done:
                done[fp] = {"report_date": d, "file_path": fp, "local": local.name, "status": "ok",
                            "id": r["Id"], "title": r["Title_"]}
            if asc and d > "2021-06-30":
                break
            continue
        ok = False
        for i in range(4):
            try:
                resp = requests.get(CDN + fp, headers=H, timeout=120)
                if resp.status_code == 200 and len(resp.content) > 500:
                    local.write_bytes(resp.content)
                    ok = True
                    break
                print("bad", resp.status_code, fp, flush=True)
                if resp.status_code == 404:
                    break
            except Exception as e:  # noqa
                print("err", fp, e, flush=True)
            time.sleep(5 * (i + 1))
        done[fp] = {"report_date": d, "file_path": fp, "local": local.name if ok else "",
                    "status": "ok" if ok else "failed", "id": r["Id"], "title": r["Title_"]}
        n += 1
        if n % 25 == 0:
            print(n, d, flush=True)
            with man_path.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["report_date", "file_path", "local", "status", "id", "title"])
                w.writeheader()
                w.writerows(done.values())
        time.sleep(1.0)
    with man_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["report_date", "file_path", "local", "status", "id", "title"])
        w.writeheader()
        w.writerows(done.values())
    print("done", len(done))


if __name__ == "__main__":
    main()
