"""Build data/processed/capacity_storage/re_capacity_statewise.csv (tidy long, MW).

Inputs (all read-only, untrusted data):
  MNRE monthly 'State-wise (Location based) installed capacity of Renewable Power' PDFs
    data/raw/capacity_storage/mnre/statewise/{202506131034278891,202602091660392380,
                                              20260402528287287,20260408192373680}.pdf
  MNRE 'Renewable Energy Statistics' 2023-24 (Tables 6.2/6.3, 31.03.2024) and 2024-25
    (Tables 8.2/8.3, 31.03.2025; top-5 state tables since 2014-15)
  PIB releases with state tables: 1911483 (solar 28.02.2023), 1985574 (solar 31.03.2020 and
    31.10.2023), 2287725 (wind 30.06.2026)
Each value is copied as printed; no state value is computed or filled.
"""
import csv
import io
import os
import re

import pandas as pd
import pdfplumber

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
SW = os.path.join(ROOT, "data", "raw", "capacity_storage", "mnre", "statewise")
WEB = os.path.join(ROOT, "data", "raw", "capacity_storage", "web")
OUT = os.path.join(ROOT, "data", "processed", "capacity_storage", "re_capacity_statewise.csv")

STATE_FIX = {
    "Pondicherry": "Puducherry",
    "Jammu & Kashmir": "Jammu and Kashmir",
    "Andaman & Nicobar": "Andaman and Nicobar Islands",
    "Andaman & Nicobar Islands": "Andaman and Nicobar Islands",
    "Dadar & Nagar Haveli/Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Dadra & Nagar Haveli and Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Dadra and Nagar Haveli and Daman and Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Total (MW)": "India",
    "Total": "India",
    "Others": "Others (MNRE 'Others' row)",
}


def clean_state(s):
    s = re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()
    s = re.sub(r"^\d+\s+", "", s)
    s = s.lstrip('"')
    if s.startswith("Andaman"):
        return "Andaman and Nicobar Islands"
    if s.startswith(("Dadra", "Dadar", "Haveli")):
        return "Dadra and Nagar Haveli and Daman and Diu"
    return STATE_FIX.get(s, s)


def classify(label):
    L = re.sub(r"\s+", " ", (label or "").replace("\n", " ")).lower()
    rules = [
        ("waste to energy (off-grid)", "wte_offgrid_capacity"),
        ("(off- grid)", "wte_offgrid_capacity"),
        ("non-bagasse", "biomass_cogen_non_bagasse_capacity"),
        ("non bagasse", "biomass_cogen_non_bagasse_capacity"),
        ("non baggasse", "biomass_cogen_non_bagasse_capacity"),
        ("bagasse", "biomass_bagasse_cogen_capacity"),
        ("waste to energy", "wte_capacity"),
        ("bio power total", "bio_power_capacity_total"),
        ("ground mounted", "solar_ground_mounted_capacity"),
        ("rts", "solar_rooftop_capacity"),
        ("rooftop", "solar_rooftop_capacity"),
        ("hybrid solar", "solar_hybrid_component_capacity"),
        ("off-grid solar", "solar_offgrid_kusum_capacity"),
        ("solar power total", "solar_capacity"),
        ("small hydro", "small_hydro_capacity"),
        ("wind", "wind_capacity"),
        ("re capacity sub-total", "re_capacity_excl_large_hydro"),
        ("large hydro", "large_hydro_capacity"),
        ("large", "large_hydro_capacity"),
        ("total capacity", "re_capacity_incl_large_hydro"),
        ("solar power", "solar_capacity"),
        ("solar", "solar_capacity"),
        ("bio", "bio_power_capacity_total"),
    ]
    for k, m in rules:
        if k in L:
            return m
    return None


def isnum(x):
    return x is not None and re.fullmatch(r"-?\d[\d,]*\.?\d*", str(x).strip()) is not None


def parse_table(tab, n_header, label_inherit=2):
    """tab: list of rows. Returns list of (state, metric, value)."""
    header = tab[:n_header]
    ncol = max(len(r) for r in tab)
    raw = []
    for i in range(ncol):
        parts = [str(r[i]) for r in header if i < len(r) and r[i] not in (None, "") and not str(r[i]).startswith("(MW")]
        raw.append(" ".join(parts))
    labels = []
    for i in range(ncol):
        lab = None
        for j in range(i, max(-1, i - label_inherit - 1), -1):
            if raw[j] and classify(raw[j]):
                lab = raw[j]
                break
        labels.append(lab)
    # where a column has its own label and a parent label, prefer the most specific (own)
    out = []
    for r in tab[n_header:]:
        cells = [c for c in r]
        st = None
        for c in cells[:4]:
            if c and not isnum(c) and len(str(c)) > 1:
                st = clean_state(c)
                break
        if not st or st.lower().startswith(("mw =", "national", "source")):
            continue
        seen = set()
        for i, c in enumerate(cells):
            if labels[i] is None or not isnum(c):
                continue
            m = classify(labels[i])
            if m in seen:
                continue
            seen.add(m)
            out.append((st, m, float(str(c).replace(",", ""))))
    return out


rows = []


def add(geo, date, metric, value, sid, note):
    rows.append({"geography": geo, "period_start": date, "period_end": date, "granularity": "snapshot",
                 "metric": metric, "value": value, "unit": "MW", "source_id": sid, "notes": note})


# ---- A) MNRE monthly state-wise PDFs
MONTHLY = {
    "202506131034278891.pdf": ("2025-05-31", "CAP-020"),
    # 202602091660392380.pdf (31.01.2026) skipped: PDF table columns are misaligned row-to-row
    "20260402528287287.pdf": ("2026-02-28", "CAP-022"),
    "20260408192373680.pdf": ("2026-03-31", "CAP-023"),
}
for fn, (date, sid) in MONTHLY.items():
    with pdfplumber.open(os.path.join(SW, fn)) as pdf:
        tabs = [t for pg in pdf.pages for t in pg.extract_tables() if len(t) > 20]
    for t in tabs:
        # header rows = rows before first row whose first cells contain a serial number '1'
        n_header = next(i for i, r in enumerate(t) if r and str(r[0]).strip() == "1")
        for st, m, v in parse_table(t, n_header, label_inherit=0):
            add(st, date, m, v, sid, f"MNRE state-wise (location based) installed capacity as on {date}; {fn}")

# ---- B) RE Statistics tables (positional layout with padding columns).
# Column indices were read off the extracted tables (value sits at the index below);
# they are checked against the printed 'Total' row (see notes/capacity_storage.md).
MAP_X2 = {4: "small_hydro_capacity", 7: "wind_capacity", 10: "bio_power_capacity_total",
          13: "solar_capacity", 16: "large_hydro_capacity", 19: "re_capacity_incl_large_hydro"}
MAP_83 = {4: "biomass_bagasse_cogen_capacity", 7: "biomass_cogen_non_bagasse_capacity", 10: "wte_capacity",
          13: "wte_offgrid_capacity", 16: "solar_ground_mounted_capacity", 19: "solar_rooftop_capacity",
          22: "solar_hybrid_component_capacity", 25: "solar_offgrid_kusum_capacity"}
MAP_63 = {4: "biomass_bagasse_cogen_capacity", 7: "biomass_cogen_non_bagasse_capacity", 10: "wte_capacity",
          13: "wte_offgrid_capacity", 16: "solar_ground_mounted_capacity", 19: "solar_rooftop_capacity",
          22: "solar_offgrid_kusum_capacity"}
BOOKS = [
    ("20251106791170361.pdf", 51, "2025-03-31", "CAP-011", "Table 8.2", MAP_X2),
    ("20251106791170361.pdf", 52, "2025-03-31", "CAP-011", "Table 8.3", MAP_83),
    ("20241029512325464.pdf", 42, "2024-03-31", "CAP-012", "Table 6.2", MAP_X2),
    ("20241029512325464.pdf", 43, "2024-03-31", "CAP-012", "Table 6.3", MAP_63),
]
for fn, page, date, sid, tname, cmap in BOOKS:
    with pdfplumber.open(os.path.join(SW, fn)) as pdf:
        tabs = [t for t in pdf.pages[page].extract_tables() if len(t) > 20]
    t = tabs[0]
    for r in t:
        name = next((c for c in r[:3] if c and not isnum(c) and len(str(c).strip()) > 1), None)
        if not name:
            continue
        st = clean_state(name)
        if st.lower().startswith(("states", "haveli", "nicobar")):
            continue
        for idx, m in cmap.items():
            if idx < len(r) and isnum(r[idx]):
                add(st, date, m, float(r[idx]), sid, f"MNRE Renewable Energy Statistics {tname} (as on {date}); {fn}")
            elif idx < len(r) and r[idx] in (None, "") and (idx - 1) not in cmap and isnum(r[idx - 1]):
                # a few rows (e.g. DNH&DD) are shifted one column left in the extracted table
                add(st, date, m, float(r[idx - 1]), sid, f"MNRE Renewable Energy Statistics {tname} (as on {date}); {fn}; value read from shifted cell")

# ---- C) top-5 state tables 'Installed Capacity under RES since 2014-15' (2024-25 book)
ref = {(r["geography"], r["metric"]): r["value"] for r in rows if r["period_start"] == "2025-03-31" and r["source_id"] == "CAP-011"}
with pdfplumber.open(os.path.join(SW, "20251106791170361.pdf")) as pdf:
    for i, pg in enumerate(pdf.pages):
        t = pg.extract_text() or ""
        mt = re.search(r"Table (1[1-5])\.2\.1", t)
        if not mt or i < 55:
            continue
        yrs = re.findall(r"\n(20\d\d-\d\d)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", t)
        if not yrs:
            continue
        last = [y for y in yrs if y[0] == "2024-25"]
        state = None
        if last:
            shp, wind, bio, solar = (float(x) for x in last[0][1:5])
            for (g, m), v in ref.items():
                if m == "solar_capacity" and abs(v - solar) < 0.6 and abs(ref.get((g, "wind_capacity"), -1) - wind) < 0.6:
                    state = g
        if not state:
            print("could not match state for table", mt.group(0))
            continue
        for y, shp, wind, bio, solar, tot in yrs:
            date = f"{int(y[:4]) + 1}-03-31"
            note = f"MNRE RE Statistics 2024-25 {mt.group(0)} (state identified by matching its 2024-25 row to Table 8.2); pdf page {i + 1}"
            for m, v in [("small_hydro_capacity", shp), ("wind_capacity", wind), ("bio_power_capacity_total", bio), ("solar_capacity", solar), ("re_capacity_excl_large_hydro", tot)]:
                add(state, date, m, float(v), "CAP-011", note)


# ---- D) PIB tables
def pib_tables(pid):
    h = open(os.path.join(WEB, f"pib_{pid}.html"), encoding="utf-8").read()
    return pd.read_html(io.StringIO(h))


t = pib_tables("1911483")[2]
for _, r in t.iloc[1:].iterrows():
    if isnum(r[2]):
        add(clean_state(str(r[1])), "2023-02-28", "solar_capacity", float(r[2]), "CAP-030", "PIB 28 Mar 2023 (MNRE, Lok Sabha): State-wise installed solar capacity as on 28.02.2023")
t = pib_tables("1985574")[0]
for _, r in t.iloc[2:].iterrows():
    if isnum(r[2]):
        add(clean_state(str(r[1])), "2020-03-31", "solar_capacity", float(r[2]), "CAP-031", "PIB 12 Dec 2023 (MNRE): State-wise solar capacity up to 31.03.2020")
    if isnum(r[3]):
        add(clean_state(str(r[1])), "2023-10-31", "solar_capacity", float(r[3]), "CAP-031", "PIB 12 Dec 2023 (MNRE): State-wise solar capacity up to 31.10.2023")
t = pib_tables("2287725")[2]
for _, r in t.iloc[1:].iterrows():
    if isnum(r[1]):
        add(clean_state(str(r[0])), "2026-06-30", "wind_capacity", float(r[1]), "CAP-032", "PIB 22 Jul 2026 (MNRE, Lok Sabha) Annexure: state-wise wind installed capacity as on 30.06.2026")

df = pd.DataFrame(rows)
df["geography"] = df["geography"].replace({"Total (MW)": "India"})
df = df.drop_duplicates(subset=["geography", "period_start", "metric", "source_id"])
df = df.sort_values(["period_start", "geography", "metric"])
df.to_csv(OUT, index=False)
print(len(df), "rows")
print(df.groupby(["period_start", "source_id"]).size())
