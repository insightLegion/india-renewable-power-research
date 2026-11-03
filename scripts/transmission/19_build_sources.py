"""Build sources/transmission_sources.csv from the download logs plus the hand-registered documents.
Only source_ids actually used in data/processed/transmission/*.csv are written (checked at the end)."""
import csv, glob, os, re, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission")
P = os.path.join(ROOT, "data/processed/transmission")
ACC = "2026-11-03"
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
S = {}
def reg(sid, org, title, url, pub, period, gran, units, ind, fmt, notes=""):
    S[sid] = dict(source_id=sid, organisation=org, title=title, url=url, publication_date=pub, accessed_date=ACC, data_period=period,
                  granularity=gran, units=units, indicators=ind, format=fmt, notes=notes)

# CEA monthly transmission reports
K = {"lines_growth": ("LG", "Growth Summary of Transmission Lines (220 kV & above)", "cumulative ckm by voltage/sector; inter-regional capacity (from Dec 2023 issues); ISTS vs intra-state FY additions (latest issue)", "ckm; MW"),
     "ss_growth": ("SG", "Growth Summary of Substations (220 kV & above)", "cumulative transformation capacity by voltage/sector", "MVA; MW (HVDC)"),
     "lines_exec": ("LE", "Executive Summary of Target and Achievement of Transmission Lines (220 kV & above)", "FY target (programme) and achievement", "ckm"),
     "ss_exec": ("SE", "Executive Summary of Target and Achievement of Substations / Transformation Capacity (220 kV & above)", "FY target and achievement", "MVA")}
for r in csv.reader(open(os.path.join(RAW, "cea/download_log.csv"))):
    k, p, url = r[0], r[1], r[2]
    code, title, ind, units = K[k]
    reg(f"TRN-CEA-{code}-{p}", "Central Electricity Authority (CEA), PSPM Division", f"{title}, {p}", url, p, f"up to end of {p}", "monthly", units, ind, "PDF",
        "CEA dashboard: https://cea.nic.in/reports/dashboardView?headingId=107&subHeadingId=1003&subSubHeadingId=10052 (lines) / 10051 (substations)")
for r in csv.reader(open(os.path.join(RAW, "cea_es/download_log.csv"))):
    p, url = r[0], r[1]
    reg(f"TRN-CEA-ES-{p}", "Central Electricity Authority (CEA)", f"Executive Summary on Power Sector, {p}", url, p, f"as of end {p}", "monthly", "MW; ckm; MVA",
        "inter-regional transmission capacity (growth of transmission sector table)", "PDF", "dashboard subSubHeadingId=10071")
# IEX
for mk, slug, start in (("DAM", "day-ahead-market", "2015-01"), ("RTM", "real-time-market", "2020-06")):
    reg(f"TRN-IEX-{mk}-SNAP", "Indian Energy Exchange (IEX)", f"{mk} Market Snapshot, 15-minute blocks (MCV, final scheduled volume, MCP, congestion flag)",
        f"https://www.iexindia.com/market-data/{slug}/market-snapshot?interval=ONE_FOURTH_HOUR&dp=SELECT_RANGE&fromDate=DD-MM-YYYY&toDate=DD-MM-YYYY",
        "", f"{start} to 2026-10", "15min", "MW; Rs/MWh", "MCV (unconstrained), FSV (after market splitting), congestion YES/NO", "Next.js RSC payload (header 'RSC: 1')",
        "monthly aggregates computed by scripts/transmission/11_parse_iex_congestion.py")
# CERC MMC
for f in sorted(glob.glob(os.path.join(RAW, "cerc/mmc/*.pdf"))):
    t = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True).stdout
    m = re.search(r"DETAILS OF CONGESTION IN POWER EXCHANGES,?\s*\(?([A-Z]+)[,'\s]*(\d{4})", t, re.I)
    if not m or m.group(1)[:3].lower() not in MON:
        continue
    y, mo = int(m.group(2)), MON[m.group(1)[:3].lower()]
    base = os.path.basename(f).split("__", 1)
    url = None
    for r in csv.reader(open(os.path.join(RAW, "cerc/download_log.csv"))):
        if os.path.basename(r[3]) == os.path.basename(f):
            url = r[2]
    reg(f"TRN-CERC-MMC-{y}-{mo:02d}", "Central Electricity Regulatory Commission (CERC), Market Monitoring Cell",
        f"Report on Short-term Power Market in India, {y}-{mo:02d}", url or "https://cercind.gov.in/report_MM.html", f"{y}-{mo:02d}", f"{y}-{mo:02d}", "monthly", "MU; %",
        "Details of congestion in power exchanges (unconstrained vs actual cleared volume, volume lost to congestion, % time congested)", "PDF")
# Grid-India
for r in csv.reader(open(os.path.join(RAW, "gridindia/download_log.csv"))):
    if r[0] == "qof":
        m = re.search(r"Feedback_([A-Za-z]+)_(\d{4})", os.path.basename(r[3]))
        y, mo = int(m.group(2)), MON[m.group(1)[:3].lower()]
        reg(f"TRN-GI-QOF-{y}-{mo:02d}", "Grid Controller of India (Grid-India) / NLDC (POSOCO before 2022)", f"Operational Feedback on Transmission Constraints ({r[1]})",
            r[2], f"{y}-{mo:02d}", "preceding quarter", "quarterly", "MW; text", "constrained lines/ICTs by region, RE evacuation issues", "PDF",
            "listing: https://grid-india.in/en/reports/quarterly-operational-feedback")
reg("TRN-GI-TGNA", "Grid Controller of India (Grid-India)", "Margin under T-GNA for the Evacuation of Renewable Generation from ISTS RE Complexes (59 issues)",
    "https://grid-india.in/en/operations/margin-under-tgna (files via webapi.grid-india.in file type F_PG00413; per-issue PDF URLs in data/raw/transmission/gridindia/download_log.csv)",
    "2025-11 to 2026-10", "2025-11-20 to 2026-10-25", "snapshot (irregular, ~weekly)", "MW", "connectivity/commissioned RE, GNA effective/not effective, permissible limit, T-GNA injection limit by time block, limiting constraints", "PDF")
reg("TRN-GI-ATC", "Grid Controller of India (Grid-India) / NLDC", "Monthly Total Transfer Capability (TTC/ATC) declarations, inter-regional corridors (last revision per month)",
    "https://grid-india.in/en/operations/monthly-atc-inter-regional (file type ATC_INTER_REGIONAL; per-file URLs in data/raw/transmission/gridindia/download_log.csv)",
    "2015-01 to 2026-11", "2015-01 to 2026-11", "monthly (time-block ranges)", "MW", "TTC, reliability margin, ATC by corridor/date range/time period", "PDF",
    "some months missing where file titles did not follow the 'ATC NLDC <Mon> <YY> Rev N' pattern or the download failed")
reg("TRN-CEA-500GW", "Central Electricity Authority (CEA)", "Transmission System for Integration of over 500 GW RE Capacity by 2030",
    "https://cea.nic.in/api/dashboardReports/view-pdf/en/6b8e86b5-4319-4e80-98df-0b5db8a49533", "2022-12", "to 2030", "snapshot", "MW; GW; ckm; MVA; Rs crore",
    "RE integration plan, ISTS line/substation additions, cost, IR capacity, GEC, GIB", "PDF")
reg("TRN-CEA-NEP-T", "Central Electricity Authority (CEA)", "National Electricity Plan (Volume II: Transmission) 2023-2032",
    "https://cea.nic.in/api/dashboardReports/view-pdf/en/d21db032-d7bd-4f09-8c3e-4c51ef0183e4", "2024-10", "2017-22 review; 2022-27; 2027-32", "FY / snapshot",
    "ckm; MVA; MW; Rs crore", "transmission plan targets, IR capacity by corridor, GEC-I/II status, delayed lines", "PDF")
reg("TRN-CEA-TBCB-2026-09", "Central Electricity Authority (CEA)", "Monthly Progress Report of Under Construction Transmission Projects awarded through TBCB, September 2026",
    "https://cea.nic.in/api/dashboardReports/download-pdf/en/ab1f6461-0843-4e03-a396-63924918c53f", "2026-09", "as of Sep 2026", "snapshot", "ckm; MVA; Rs crore; dates",
    "project-level original vs anticipated completion", "PDF")

# keep only used ids, and check none missing
used = set()
for f in glob.glob(os.path.join(P, "*.csv")):
    if os.path.basename(f).startswith("_"):
        continue
    for r in csv.DictReader(open(f)):
        if r.get("source_id"):
            used.add(r["source_id"])
missing = used - set(S)
print("used", len(used), "registered", len(S), "missing", sorted(missing))
os.makedirs(os.path.join(ROOT, "sources"), exist_ok=True)
with open(os.path.join(ROOT, "sources/transmission_sources.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(next(iter(S.values())).keys())); w.writeheader()
    for sid in sorted(used & set(S)):
        w.writerow(S[sid])
print("written", len(used & set(S)))
