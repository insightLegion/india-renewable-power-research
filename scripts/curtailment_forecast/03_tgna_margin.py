"""Download and parse Grid-India 'Margin under T-GNA for the Evacuation of Renewable Generation from ISTS RE Complexes'.

Page: https://grid-india.in/en/operations/margin-under-tgna (file type F_PG00413)
Run via Indian proxy: myproxy run .venv/bin/python -I scripts/curtailment_forecast/03_tgna_margin.py
Output: data/raw/curtailment_forecast/gridindia/tgna_margin/tgna_margin_autoparse_UNVERIFIED.csv (index only; NOT a clean dataset)
For each document and each RE complex block (rows grouped by the constant 'GNA not effective' value), records:
  connectivity_MW (A, if found), gna_effective_MW (B), gna_not_effective_MW (C), min T-GNA injection limit (F) and the
  time window when it applies, max F. Parsed from pdftotext -layout output; see notes for caveats.
"""
import csv
import json
import os
import re
import subprocess
import time

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw", "curtailment_forecast", "gridindia", "tgna_margin")
OUT = os.path.join(RAW, "tgna_margin_autoparse_UNVERIFIED.csv")  # layout varies by document; manually verified values are in curtailment_events.csv
os.makedirs(RAW, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}

r = requests.post("https://webapi.grid-india.in/api/v1/file", json={"_source": "GRDW", "_type": "F_PG00413"},
                  headers={**H, "Content-Type": "application/json"}, timeout=120)
files = r.json()["retData"]
json.dump(files, open(os.path.join(RAW, "listing.json"), "w"))

TIME = re.compile(r"(\d{2}:?\d{2})\s*-\s*(\d{2}:?\d{2})")
rows_out = []
for f in files:
    local = os.path.join(RAW, os.path.basename(f["FilePath"]).replace("%20", "_"))
    if not os.path.exists(local):
        resp = requests.get("https://webcdn.grid-india.in/" + f["FilePath"], headers=H, timeout=120)
        if resp.status_code != 200 or resp.content[:4] != b"%PDF":
            print("fail", f["Title_"]); continue
        open(local, "wb").write(resp.content)
        time.sleep(0.7)
    txt = subprocess.run(["pdftotext", "-layout", local, "-"], capture_output=True, text=True).stdout
    m = re.search(r"Effective from:?\s*([0-9]{1,2}\w*\s+\w+\.?\s+\d{4})", txt)
    eff = m.group(1) if m else ""
    groups = {}
    order = []
    cut = None
    for line in txt.splitlines():
        if "Limiting Constraints" in line:
            cut = line.index("Limiting Constraints") - 3
            break
    for line in txt.splitlines():
        tm = TIME.search(line)
        if not tm:
            continue
        seg = line[tm.end(): cut] if cut and cut > tm.end() else line[tm.end():]
        pre = re.match(r"^[\s\d]*", seg).group(0)  # numeric columns only: stop at first non-numeric text
        if len(pre) < len(seg) and pre and not pre[-1].isspace():
            pre = re.sub(r"\d+$", "", pre)  # drop a number glued to following text (e.g. '400kV')
        seg = pre
        nums = [int(x) for x in re.findall(r"(?<![\d:.])(\d{3,6})(?![\d:.])", seg)]
        if len(nums) < 3:
            continue
        if abs(nums[0] - nums[1] - nums[2]) <= 5:
            A, B, C, F = nums[0], nums[1], nums[2], nums[-1]
        else:
            A, B, C, F = None, nums[0], nums[1], nums[-1]
        key = (B, C)
        if key not in groups:
            groups[key] = {"A": None, "F": []}
            order.append(key)
        if A:
            groups[key]["A"] = A
        groups[key]["F"].append((F, tm.group(0)))
    labels = []
    for lab in ("Rajasthan", "Khavda", "Southern Region", "Karnataka", "Andhra", "Gujarat", "Madhya"):
        if lab in txt:
            labels.append(lab)
    for i, key in enumerate(order):
        g = groups[key]
        if len(g["F"]) < 1:
            continue
        fmin = min(x[0] for x in g["F"])
        win = [x[1] for x in g["F"] if x[0] == fmin]
        rows_out.append({"doc_title": f["Title_"], "effective_from": eff, "posted_on": f["CreatedOn"][:10],
                         "block_order": i + 1, "complex_labels_in_doc": ";".join(labels),
                         "connectivity_MW_A": g["A"], "gna_effective_MW_B": key[0], "gna_not_effective_MW_C": key[1],
                         "tgna_limit_min_MW": fmin, "tgna_limit_min_window": ";".join(win),
                         "tgna_limit_max_MW": max(x[0] for x in g["F"]), "n_time_rows": len(g["F"]),
                         "file": os.path.relpath(local, ROOT),
                         "url": "https://webcdn.grid-india.in/" + f["FilePath"]})
with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
    w.writeheader(); w.writerows(rows_out)
print(len(files), len(rows_out))
