"""Download IEX market snapshot (15-min blocks) month by month for DAM and RTM.

The IEX Next.js page returns its server data when requested with header 'RSC: 1'.
Each 15-min record has: date, period, purchase_bid, sell_bid, mcv, final_scheduled_volume, mcp, congestion (YES/NO).
Raw responses are stored gzipped in data/raw/transmission/iex/snapshot/<market>_<YYYY-MM>.rsc.gz
Direct access (no proxy needed).
"""
import calendar, gzip, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data/raw/transmission/iex/snapshot")
os.makedirs(OUT, exist_ok=True)
MARKETS = {"dam": ("day-ahead-market", (2015, 1)), "rtm": ("real-time-market", (2020, 6))}
END = (2026, 10)

def months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1

for mk, (slug, start) in MARKETS.items():
    for y, m in months(start, END):
        fn = os.path.join(OUT, f"{mk}_{y}-{m:02d}.rsc.gz")
        if os.path.exists(fn):
            continue
        last = calendar.monthrange(y, m)[1]
        url = (f"https://www.iexindia.com/market-data/{slug}/market-snapshot?interval=ONE_FOURTH_HOUR"
               f"&dp=SELECT_RANGE&fromDate=01-{m:02d}-{y}&toDate={last:02d}-{m:02d}-{y}")
        for attempt in range(3):
            p = subprocess.run(["curl", "-sL", "--max-time", "180", "-A", "Mozilla/5.0", "-H", "RSC: 1", url],
                               capture_output=True)
            n = p.stdout.count(b'"congestion":')
            if p.returncode == 0 and n > 0:
                break
            time.sleep(5)
        if n == 0:
            print("FAILED", mk, y, m, flush=True)
            continue
        with gzip.open(fn, "wb") as f:
            f.write(p.stdout)
        print(mk, y, m, n, flush=True)
        time.sleep(1.0)
