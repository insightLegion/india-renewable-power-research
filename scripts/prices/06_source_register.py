"""Write sources/prices_sources.csv (source register for topic 'prices').
Usage: .venv/bin/python -I scripts/prices/06_source_register.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACC = "2026-11-03"
COLS = ["source_id", "organisation", "title", "url", "publication_date", "accessed_date", "data_period", "granularity",
        "units", "indicators", "format", "notes"]
API = "https://www.iexindia.com/api/v1"
rows = [
    ["PRC-001", "Indian Energy Exchange (IEX)", "Day-Ahead Market - Market Snapshot (15-min)",
     f"{API}/dam/market-snapshot?interval=ONE_FOURTH_HOUR&fromDate=DD-MM-YYYY&toDate=DD-MM-YYYY",
     "continuous", ACC, "2012-04-01..2026-11-04", "15min", "MW (block average), Rs/MWh",
     "purchase bid, sell bid, MCV, final scheduled volume, MCP, congestion flag", "JSON API",
     "JSON API behind https://www.iexindia.com/market-data/day-ahead-market/market-snapshot (found in site JS bundle). "
     "One calendar year per request. Raw: data/raw/prices/iex_api/dam_market-snapshot_YYYY.json. No data served before 2012-04-01."],
    ["PRC-002", "Indian Energy Exchange (IEX)", "Real-Time Market - Market Snapshot (15-min)",
     f"{API}/rtm/market-snapshot?interval=ONE_FOURTH_HOUR&fromDate=..&toDate=..", "continuous", ACC,
     "2020-06-01..2026-11-03", "15min", "MW, Rs/MWh", "purchase bid, sell bid, MCV, final scheduled volume, MCP, congestion",
     "JSON API", "Page: https://www.iexindia.com/market-data/real-time-market/market-snapshot. Raw: data/raw/prices/iex_api/rtm_market-snapshot_YYYY.json"],
    ["PRC-003", "Indian Energy Exchange (IEX)", "Green Day-Ahead Market - Market Snapshot (15-min)",
     f"{API}/gdam/market-snapshot?interval=ONE_FOURTH_HOUR&fromDate=..&toDate=..", "continuous", ACC,
     "2021-10-27..2026-11-04", "15min", "MW, Rs/MWh",
     "purchase bid, sell bids/MCV/cleared volume by source (solar/non-solar/hydro until 2026-07-07; hydro/wind/other RE/DRE from 2026-07-08), MCP (field 'unconstrained_m_c_p')",
     "JSON API", "Page: https://www.iexindia.com/market-data/green-day-ahead-market/market-snapshot"],
    ["PRC-004", "Indian Energy Exchange (IEX)", "Day-Ahead Market - Area clearing prices by bid area (15-min)",
     f"{API}/dam/area-price?interval=ONE_FOURTH_HOUR&fromDate=..&toDate=..&bidArea=A1,A2,E1,E2,N1,N2,N3,S1,S2,S3,W1,W2,W3,MKT",
     "continuous", ACC, "2012-04-01..2026-11-04", "15min", "Rs/MWh", "area clearing price for 13 bid areas + MCP", "JSON API",
     "Same API as the area-price chart on the DAM market snapshot page. S3 null before 2017."],
    ["PRC-005", "Indian Energy Exchange (IEX)", "Green Day-Ahead Market - Area clearing prices by bid area (15-min)",
     f"{API}/gdam/area-price?interval=ONE_FOURTH_HOUR&fromDate=..&toDate=..&bidArea=...", "continuous", ACC,
     "2021-10-27..2026-11-04", "15min", "Rs/MWh", "area clearing price for 13 bid areas + MCP", "JSON API",
     "rtm/area-price endpoint exists but returned no rows for any year (RTM area prices NOT AVAILABLE)."],
]
mmc = [
    ("PRC-006", "MMC_Report_on_Short_term_market_for_January_2025", "January 2025", "2025/market_monitoring/MMC Report on Short term market for January 2025.pdf"),
    ("PRC-007", "MMC_Report_on_Short_term_market_for_Februrary_2025", "February 2025", "2025/market_monitoring/MMC Report on Short term market for Februrary 2025.pdf"),
    ("PRC-008", "MMC_Report_on_Short_term_market_for_March_2025", "March 2025", "2025/market_monitoring/MMC Report on Short term market for March 2025.pdf"),
    ("PRC-009", "MMC_Report_on_Short_term_market_for_April_2025", "April 2025", "2025/market_monitoring/MMC Report on Short term market for April 2025.pdf"),
    ("PRC-010", "MMC_Report_on_Short_term_market_for_May2025", "May 2025", "2025/market_monitoring/MMC Report on Short term market for May2025.pdf"),
    ("PRC-011", "MMC_Report_on_Short_term_market_for_June_2025", "June 2025", "2025/market_monitoring/MMC Report on Short term market for June 2025.pdf"),
    ("PRC-012", "MMC_Report_on_Short_term_market_for_July_2025", "July 2025", "2025/market_monitoring/MMC Report on Short term market for July 2025.pdf"),
    ("PRC-013", "MMC_Report_short_term_market_Aug_2025", "August 2025", "2025/market_monitoring/MMC Report_short term market_Aug 2025.pdf"),
    ("PRC-014", "MMC_Report_short_term_market_Sep_2025", "September 2025", "2025/market_monitoring/MMC Report_short term market_Sep 2025.pdf"),
    ("PRC-015", "MMC_Report_short_term_market_Oct_2025", "October 2025", "2025/market_monitoring/MMC Report_short term market_Oct 2025.pdf"),
    ("PRC-016", "MMC_Report_short_term_market_Nov_2025", "November 2025", "2025/market_monitoring/MMC Report_short term market_Nov 2025.pdf"),
    ("PRC-017", "MMC_Report_short_term_market_Dec_2025", "December 2025", "2025/market_monitoring/MMC Report_short term market_Dec 2025.pdf"),
    ("PRC-018", "MMC_Report_on_Short_term_market_for_January_2026", "January 2026", "2026/market_monitoring/MMC Report on Short term market for January 2026.pdf"),
    ("PRC-019", "MMC_Report_on_Short_term_market_for_February_2026", "February 2026", "2026/market_monitoring/MMC Report on Short term market for February 2026.pdf"),
    ("PRC-020", "MMC_Report_on_Short_term_market_for_March_2026", "March 2026", "2026/market_monitoring/MMC Report on Short term market for March 2026.pdf"),
]
for sid, stem, per, path in mmc:
    rows.append([sid, "Central Electricity Regulatory Commission (CERC), Market Monitoring Cell",
                 f"Report on Short-term Power Market in India: {per}", "https://cercind.gov.in/" + path.replace(" ", "%20"),
                 "", ACC, per, "monthly", "MU, Rs/kWh", "min/max/weighted avg ACP by segment & exchange; buy/sell bid volumes",
                 "PDF", f"local:{stem}; fetched via Indian proxy; listing page https://cercind.gov.in/report_MM-{per[-4:]}.html. "
                        "April-October 2026 monthly reports not yet listed on CERC site at access date."])
rows += [
    ["PRC-021", "CERC, Market Monitoring Cell", "Report on Short-term Power Market in India, 2024-25 (annual)",
     "https://cercind.gov.in/2025/market_monitoring/Annual-Report-2024-25.pdf", "2025", ACC, "FY2024-25", "FY/monthly",
     "MU, Rs/kWh", "annual short-term market statistics, hourly price profiles", "PDF", "local:Annual-Report-2024-25"],
    ["PRC-022", "CERC", "Order in Petition No. 04/SM/2023 (Suo-Motu): Directions to Power Exchanges (price range Rs 0-10/kWh; HP-DAM Rs 0-20/kWh)",
     "https://cercind.gov.in/2023/orders/04-SM-2023.pdf", "2023-03-31", ACC, "from 2023-04-04", "snapshot", "Rs/kWh",
     "bid price range (floor/ceiling) by segment; history of 2022 orders", "PDF",
     "Primary. Also recites orders 05/SM/2022 (06.05.2022), 09/SM/2022, 13/SM/2022, 17/SM/2022 (28.12.2022) and HP-DAM order 16.02.2023."],
    ["PRC-023", "CERC", "Current Regulations page: Power Market Regulations, 2010 (Second Amendment) & IEGC 6th Amendment (27.12.2019) - 'Real Time Market to be implemented from 1st June 2020'; PMR 2021 effective 15.08.2021",
     "https://cercind.gov.in/Current_reg.html", "", ACC, "2019-2021", "snapshot", "", "RTM start; PMR 2021", "HTML",
     "No notified 2025/2026 amendment to PMR 2021 (market coupling) listed on this page at access date."],
    ["PRC-024", "CERC", "Draft CERC (Power Market) (Second Amendment) Regulations, 2026 - market coupling (public notice 19.04.2026; comments extended to 05.06.2026; hearing 23.05.2026)",
     "https://cercind.gov.in/2026/draft_reg/DN-PM-2ndAmd.pdf", "2026-04-19", ACC, "2026", "snapshot", "", "market coupling design",
     "PDF (listed on https://cercind.gov.in/Draft_reg.html)", "Draft PDF itself not downloaded; status taken from the Draft_reg listing page."],
    ["PRC-025", "SolarQuarter (reporting CERC order 23.07.2025, Petition 8/SM/2025)", "CERC directs phased implementation of market coupling in power exchanges starting January 2026",
     "https://solarquarter.com/2025/07/24/cerc-directs-phased-implementation-of-market-coupling-in-power-exchanges-starting-january-2026/",
     "2025-07-24", ACC, "2025", "snapshot", "", "market coupling timeline", "web article", "Secondary (via WebSearch summary)."],
    ["PRC-026", "Powerline / Business Standard (reporting CERC order 01.04.2022)", "CERC caps spot power price at Rs 12 per unit",
     "https://powerline.net.in/2022/04/05/cerc-caps-spot-power-price-at-rs-12-per-unit/", "2022-04-05", ACC, "2022", "snapshot",
     "Rs/kWh", "DAM/RTM bid price range Rs 0-12/kWh from April 2022", "web article", "Secondary (via WebSearch summary); the 06.05.2022 extension is confirmed in PRC-022."],
    ["PRC-027", "CERC", "Record of Proceedings, Petition No. 127/2011 (hearing 21.07.2011): bidding time block changed from one hour to 15 minutes by order dated 24.5.2011",
     "https://cercind.gov.in/2011/ROP/signed_ROP_in_Pet_No._127-2011_DOH_21-07-2011.pdf", "2011-07-21", ACC, "2011", "snapshot", "",
     "DAM block length", "PDF", "Content per WebSearch summary; direct download failed (SSL error via proxy). IEX API serves 15-min data from 2012-04-01."],
    ["PRC-028", "Mercom India / S&P Global", "CERC approves introduction of Green Day Ahead Contracts on energy exchanges (order 17.10.2021); GDAM launched late Oct 2021",
     "https://mercomindia.com/cerc-approves-green-day-ahead-contracts-on-energy-exchanges", "2021-10", ACC, "2021", "snapshot", "",
     "GDAM introduction", "web article", "Secondary; launch-date reports vary 25-27 Oct 2021; IEX data starts with delivery date 2021-10-27."],
    ["PRC-029", "Mercom India / SolarQuarter", "IEX launches real-time electricity market (1 June 2020; 48 half-hourly auctions)",
     "https://solarquarter.com/2020/06/01/cerc-approves-rtm-contracts-of-iex/", "2020-06-01", ACC, "2020", "snapshot", "",
     "RTM introduction", "web article", "Secondary (via WebSearch summary)."],
    ["PRC-030", "Mercom India", "IEX Green energy market July 2026 / GDAM category change (wind, hydro, DRE, other RE replacing solar/non-solar/hydro)",
     "https://www.mercomindia.com/iex-green-energy-market-rises-4-yoy-in-july", "2026-08", ACC, "2026", "snapshot", "",
     "GDAM seller categories", "web article", "Secondary (via WebSearch summary). IEX GDAM data switch to new categories observed from delivery date 2026-07-08 (PRC-003)."],
    ["PRC-031", "Electrical Mirror (reporting IEX Power Market Update April 2026)", "Indian Energy Exchange April 2026 monthly power market update",
     "https://electricalmirror.net/indian-energy-exchange-april-2026-monthly-power-market-update/", "2026-05-05", ACC, "April 2026",
     "monthly", "Rs/unit", "DAM/RTM/GDAM prices; near-zero prices statement", "web article", "Secondary; fetched with WebFetch."],
    ["PRC-032", "Mercom / Muthoot Securities (reporting IEX Power Market Update October 2025)", "IEX October 2025 market update: DAM Rs 2.67/unit (-32% YoY), RTM Rs 2.73/unit",
     "https://www.muthootsecurities.com/CorporateInfo/ComNews/Indian-Energy-Exchange-Ltd/24308010083", "2025-11", ACC, "October 2025",
     "monthly", "Rs/unit", "DAM/RTM/GDAM average prices", "web article", "Secondary (via WebSearch summary). Matches derived simple-average MCP (2.669 / 2.726)."],
    ["PRC-033", "Saur Energy (reporting IEX Power Market Update January 2026)", "IEX Jan '26 update: DAM Rs 3.86/unit (-12.9% YoY), RTM Rs 3.72/unit",
     "https://www.saurenergy.com/solar-energy-news/iex-jan-26-update-trades-rise-196-yoy-as-average-dam-price-falls-129-11073685",
     "2026-02", ACC, "January 2026", "monthly", "Rs/unit", "DAM/RTM average prices", "web article", "Secondary; matches derived 3.8645 / 3.7218."],
    ["PRC-034", "The Tribune (ANI, reporting IIFL Capital report)", "Spot power prices dropped to zero in India on May 25, reflecting risk of solar maximum",
     "https://www.tribuneindia.com/news/energy/spot-power-prices-dropped-to-zero-in-india-on-may-25-reflecting-risk-of-solar-maximum-report",
     "2025-05-28", ACC, "2025-05-25", "daily", "", "zero spot price event", "web article", "Fetched with WebFetch; market/hours not specified in article."],
    ["PRC-035", "Ember", "The age of storage: Batteries primed for India's power markets - Chapter 2 Understanding pain points",
     "https://ember-energy.org/latest-insights/the-age-of-storage-batteries-primed-for-indias-power-markets/chapter-2-understanding-pain-points",
     "2025-08-04", ACC, "2019-2025H1", "annual", "Rs/kWh, count of blocks", "mid-day vs evening spread, <Rs1/kWh block counts, solar capture rate",
     "web page", "Fetched with WebFetch."],
    ["PRC-036", "Ember (via pv magazine / Down To Earth)", "India curtails 2.3 TWh of solar between May and December 2025",
     "https://ember-energy.org/latest-insights/beyond-capacity-why-indias-power-system-must-get-flexible-to-harness-its-solar-potential/structural-and-operational-factors-of-renewable-en",
     "2026-01", ACC, "May-Dec 2025", "monthly", "TWh, GW", "solar curtailment via TRAS, mid-day demand", "web page",
     "Secondary (via WebSearch summary); curtailment topic owned by curtailment collector - recorded for context only."],
    ["PRC-037", "Mint (via pulse.bot summary)", "Mint Explainer: Why power prices on Indian exchanges are crashing to zero despite record demand",
     "https://www.pulse.bot/energy/news/mint-explainer-why-power-prices-on-indian-exchanges-are-crashing-to-zero-despite-record-demand-e7ffed1e-8bc0-4d76-8e3e-b6587c2e82e0/",
     "2026 (unconfirmed)", ACC, "May 2026?", "snapshot", "", "zero price events May 1 and May 15", "web article",
     "UNVERIFIED third-party summary; page fetch failed. IEX data confirm RTM MCP = Rs 0 on 2026-05-01 but NOT on 2026-05-15 (RTM min Rs 0.99/kWh)."],
    ["PRC-038", "IEEFA", "Clean energy key to addressing India's power demand peaks",
     "https://ieefa.org/articles/clean-energy-key-addressing-indias-power-demand-peaks", "2025-07", ACC, "2025", "snapshot", "",
     "peak timing, storage, ToD tariffs", "web article", "Secondary (via WebSearch summary); no price statistics."],
]
with open(ROOT / "sources" / "prices_sources.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(COLS)
    w.writerows(rows)
print(len(rows), "sources")
