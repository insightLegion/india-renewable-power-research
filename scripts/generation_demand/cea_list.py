"""Parse CEA dashboardView report listings (already saved HTML) into a CSV of downloadable files.

Usage: .venv/bin/python -I scripts/generation_demand/cea_list.py data/raw/generation_demand/cea/dv_10068.html ...
Prints CSV rows: page_id, report_id, date, name, kind, url
"""
import csv
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

w = csv.writer(sys.stdout)
w.writerow(["page", "report_id", "date", "name", "kind", "url"])
for fn in sys.argv[1:]:
    page = re.search(r"dv_(\d+)", fn).group(1)
    soup = BeautifulSoup(Path(fn).read_text(errors="ignore"), "lxml")
    for tr in soup.select("tr.report-item"):
        name = tr.select_one(".report-name-cell")
        name = name.get_text(" ", strip=True) if name else ""
        for a in tr.select("a[href]"):
            h = re.sub(r";jsessionid=[A-F0-9]+", "", a["href"])
            m = re.search(r"/api/dashboardReports/download-(pdf|excel)/", h)
            if m:
                w.writerow([page, tr.get("data-report-id"), tr.get("data-date"), name, m.group(1),
                            "https://cea.nic.in" + h])
