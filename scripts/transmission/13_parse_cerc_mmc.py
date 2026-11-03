"""Parse 'Details of Congestion in Power Exchanges' tables from CERC MMC monthly short-term market reports.

Input: data/raw/transmission/cerc/mmc/*.pdf  (Jan 2015 - Mar 2026)
Output: data/processed/transmission/_cerc_congestion_rows.csv (merged into market_congestion_monthly.csv by 11_parse_iex_congestion.py)
Only IEX columns are extracted (PXIL/HPX volumes are tiny). Markets detected from table header: DAM, GDAM, HP-DAM, RTM.
The report's narrative paragraph on congestion (section 'Congestion on Inter-State Transmission Corridor') is kept,
truncated, in the notes of the share-of-time row (it names the congested corridors when congestion occurred).
"""
import csv, glob, os, re, subprocess, calendar
import pdfplumber
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission/cerc/mmc")
OUT = os.path.join(ROOT, "data/processed/transmission")
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
TOK = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%?(?![\w.])")

def month_of(text, fn):
    m = re.search(r"DETAILS OF CONGESTION IN POWER EXCHANGES,?\s*\(?([A-Z]+)[,'\s]*(\d{4})", text, re.I)
    if m and m.group(1)[:3].lower() in MON:
        return int(m.group(2)), MON[m.group(1)[:3].lower()]
    return None

rows = []
for f in sorted(glob.glob(os.path.join(RAW, "*.pdf"))):
    fn = os.path.basename(f)
    t = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True).stdout
    pages_txt = t.split("\f")
    ym = month_of(t, fn)
    i = [m.start() for m in re.finditer(r"DETAILS OF CONGESTION IN POWER EXCHANGES", t, re.I)]
    if not ym or not i:
        print("SKIP", fn); continue
    y, mo = ym
    blk = t[i[-1]:i[-1] + 6000]
    lines = blk.splitlines()
    # header: market label x positions and exchange token sequence
    hdr_end = next(k for k, l in enumerate(lines) if re.search(r"\bIEX\b", l))
    markets = []
    for l in lines[:hdr_end + 1]:
        for m in re.finditer(r"Green Day Ahead|High Price|Real Time|Day Ahead", l):
            name = {"Green Day Ahead": "gdam", "High Price": "hpdam", "Real Time": "rtm", "Day Ahead": "dam"}[m.group(0)]
            if name == "dam" and re.search(r"(Green|Price)\s*$", l[:m.start()]):
                continue
            markets.append((m.start(), name))
    seen, order = set(), []
    for x, n in sorted(markets):
        if n not in seen:
            seen.add(n); order.append(n)
    if not order:
        order = ["dam"]
    # values by x/y position (pdfplumber): numbers are assigned to the nearest exchange column and nearest row marker
    vals = {}
    with pdfplumber.open(f) as pdf:
        page = None
        for k in reversed(range(len(pages_txt))):   # locate the table page with pdftotext (fast), then read it with pdfplumber
            tx = pages_txt[k]
            if re.search(r"DETAILS OF CONGESTION IN POWER EXCHANGES", tx, re.I) and re.search(r"Unconstrained", tx, re.I) and k < len(pdf.pages):
                page = pdf.pages[k]; break
        if page is None:
            print("NO PAGE", fn); continue
        words = page.extract_words()
    ttl = [w for w in words if w["text"].upper().startswith("CONGESTION")]
    top0 = ttl[0]["top"] if ttl else 0
    cols = [w for w in words if w["text"] in ("IEX", "PXIL", "HPX") and w["top"] > top0]
    if not cols:
        print("NO COLS", fn); continue
    ytop = min(w["top"] for w in cols)
    cols = sorted([w for w in cols if abs(w["top"] - ytop) < 4], key=lambda w: w["x0"])
    if [w["text"] for w in cols].count("IEX") != len(order):
        print("MARKET MISMATCH", fn, order, [w["text"] for w in cols]); continue
    cx = [(w["x0"] + w["x1"]) / 2 for w in cols]
    marks = sorted([w for w in words if re.fullmatch(r"[A-G]|[1-7]", w["text"]) and w["top"] > ytop and w["x0"] < cols[0]["x0"] - 40],
                   key=lambda w: w["top"])
    if len(marks) < 5:
        print("NO MARKERS", fn); continue
    other = bool(re.search(r"other\s+than\s+congestion", blk, re.I))
    keys = (["unconstrained_cleared_volume", "actual_cleared_volume", "volume_curtailed_due_to_congestion"]
            + (["volume_not_cleared_other_reasons"] if other else [])
            + ["volume_curtailed_share_of_unconstrained", "share_of_time_congested", "_timeblocks"])
    ystop = marks[len(keys) - 1]["top"] if len(marks) >= len(keys) else 1e9
    cells = {}
    for w in words:
        if not re.fullmatch(r"-?\d+(?:\.\d+)?%?|-", w["text"]) or w["top"] < ytop + 3 or w["top"] >= ystop - 2:
            continue
        if w["x0"] < cols[0]["x0"] - 30:
            continue
        xc = (w["x0"] + w["x1"]) / 2
        ci = min(range(len(cx)), key=lambda k: abs(cx[k] - xc))
        mi = min(range(len(keys) - 1), key=lambda k: abs(marks[k]["top"] - w["top"]))
        cells.setdefault((mi, ci), w["text"])
    iex_cols = [k for k, w in enumerate(cols) if w["text"] == "IEX"]
    for mi, key in enumerate(keys[:-1]):
        v = [cells.get((mi, ci), "") for ci in range(len(cols))]
        vals[key] = v
    iex_idx = iex_cols
    # narrative
    nm = re.search(r"Congestion\d?\s+on\s+Inter-State\s+Transmission\s+Corridor.*?\n(.*?)(?:\n\s*\n\s*\n|Table-)", t[t.find("congestion did") - 3000 if "congestion did" in t else 0:], re.S)
    narr = ""
    k = re.search(r"In the month of [A-Za-z]+,? \d{4},? (?:the )?congestion.{0,600}", " ".join(t.split()), re.I)
    if k:
        narr = k.group(0)[:500]
    ps, pe = f"{y}-{mo:02d}-01", f"{y}-{mo:02d}-{calendar.monthrange(y, mo)[1]:02d}"
    sid = f"TRN-CERC-MMC-{y}-{mo:02d}"
    for key, v in vals.items():
        for mk, ix in zip(order, iex_idx):
            raw = v[ix]
            if not re.fullmatch(r"-?\d+(?:\.\d+)?%?", raw):
                continue
            unit = "%" if raw.endswith("%") or key.startswith("share") or "share_of" in key else "MU"
            val = float(raw.rstrip("%"))
            note = f"CERC MMC table 'Details of Congestion in Power Exchanges', IEX {mk.upper()} column"
            if key == "share_of_time_congested" and narr:
                note += "; report text: " + narr.replace(",", ";")
            rows.append(dict(geography="India", period_start=ps, period_end=pe, granularity="monthly",
                             metric=f"cerc_iex_{mk}_{key}", value=val, unit=unit, source_id=sid, notes=note))
    print(fn, y, mo, order, {k: v[iex_idx[0]] for k, v in vals.items()})

with open(os.path.join(OUT, "_cerc_congestion_rows.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["geography", "period_start", "period_end", "granularity", "metric", "value", "unit", "source_id", "notes"])
    w.writeheader(); w.writerows(rows)
print("rows", len(rows))
