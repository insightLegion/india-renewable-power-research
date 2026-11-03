"""Download IEX market data (15-min blocks) from the public JSON API used by
https://www.iexindia.com/market-data/... pages.

Endpoints (found in the site's Next.js client bundle; base https://www.iexindia.com/api/v1/):
  {dam,rtm,gdam}/market-snapshot?interval=ONE_FOURTH_HOUR&fromDate=DD-MM-YYYY&toDate=DD-MM-YYYY
  {dam,rtm,gdam}/area-price?interval=ONE_FOURTH_HOUR&fromDate=..&toDate=..&bidArea=A1,...,MKT
A full calendar year per request works (35,136 rows for 2024).

Raw JSON responses saved unchanged to data/raw/prices/iex_api/<market>_<endpoint>_<year>.json
Usage: .venv/bin/python -I scripts/prices/01_download_iex_api.py
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "raw" / "prices" / "iex_api"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://www.iexindia.com/api/v1"
AREAS = "A1,A2,E1,E2,N1,N2,N3,S1,S2,S3,W1,W2,W3,MKT"
HEAD = {"User-Agent": "Mozilla/5.0 (research data collection; contact via s1d-labs)"}

# market -> (first date, last date)
LAST = {"dam": date(2026, 11, 4), "rtm": date(2026, 11, 3), "gdam": date(2026, 11, 4)}
FIRST = {"dam": date(2012, 4, 1), "rtm": date(2020, 6, 1), "gdam": date(2021, 10, 27)}


def get(url, params, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEAD, timeout=300)
            r.raise_for_status()
            d = r.json()
            if d.get("statusCode") != 200:
                raise RuntimeError(d)
            return d
        except Exception as e:  # noqa: BLE001
            wait = 5 * 2 ** i
            print(f"  retry {i+1} after error {e!r}; sleep {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"failed {url} {params}")


def main():
    force = "--force" in sys.argv
    for mkt in ("dam", "rtm", "gdam"):
        for ep in ("market-snapshot", "area-price"):
            for y in range(FIRST[mkt].year, LAST[mkt].year + 1):
                f = OUT / f"{mkt}_{ep}_{y}.json"
                cur_year = y == LAST[mkt].year
                if f.exists() and not force and not cur_year:
                    continue
                start = max(date(y, 1, 1), FIRST[mkt])
                end = min(date(y, 12, 31), LAST[mkt])
                params = {"interval": "ONE_FOURTH_HOUR",
                          "fromDate": start.strftime("%d-%m-%Y"),
                          "toDate": end.strftime("%d-%m-%Y")}
                if ep == "area-price":
                    params["bidArea"] = AREAS
                d = get(f"{BASE}/{mkt}/{ep}", params)
                d["_request"] = {"url": f"{BASE}/{mkt}/{ep}", "params": params,
                                 "accessed": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
                f.write_text(json.dumps(d))
                print(mkt, ep, y, len(d.get("data") or []))
                time.sleep(1.5)


if __name__ == "__main__":
    main()
