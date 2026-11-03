"""Write data/processed/prices/market_rules_timeline.csv (market design & price limit history, with sources).
Data-observation rows are computed from the IEX block files; documentary rows cite the source register.
Usage: .venv/bin/python -I scripts/prices/07_market_rules_timeline.py
"""
import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "processed" / "prices"
COLS = ["event_date", "end_date", "market_segment", "rule_type", "description", "price_min_rs_kwh", "price_max_rs_kwh",
        "source_id", "evidence_type", "notes"]

dam = pd.read_csv(P / "iex_dam_blocks.csv", usecols=["date", "block_start", "mcp_rs_mwh", "no_trade"])
rtm = pd.read_csv(P / "iex_rtm_blocks.csv", usecols=["date", "block_start", "mcp_rs_mwh", "no_trade"])
gdam = pd.read_csv(P / "iex_gdam_blocks.csv", usecols=["date", "block_start", "mcp_rs_mwh", "no_trade"])
dam, rtm, gdam = dam[~dam.no_trade], rtm[~rtm.no_trade], gdam[~gdam.no_trade]


def max_by_period(d, a, b):
    x = d[(d.date >= a) & (d.date <= b)]
    return x.mcp_rs_mwh.max() / 1000, x.mcp_rs_mwh.min() / 1000


r0 = rtm[rtm.mcp_rs_mwh == 0].sort_values(["date", "block_start"])
first0 = r0.iloc[0]
dmin = dam.loc[dam.mcp_rs_mwh.idxmin()]
mx_pre = max_by_period(dam, "2021-01-01", "2022-03-31")
mx_12 = max_by_period(dam, "2022-04-02", "2023-04-03")
mx_10 = max_by_period(dam, "2023-04-04", "2026-11-04")
rx_10 = max_by_period(rtm, "2023-04-04", "2026-11-03")
gx_10 = max_by_period(gdam, "2023-04-04", "2026-11-04")

rows = [
    ["2011-05-24", "", "IEX DAM", "block length", "CERC order (Suo Motu Petition 127/2011) changed DAM bidding time block from one hour to 15 minutes",
     "", "", "PRC-027", "secondary (ROP via search summary)", "Implementation date not confirmed from primary source."],
    ["2012-04-01", "", "IEX DAM", "block length (data)", "Earliest date served by the IEX market-snapshot API; all days from here have 96 x 15-min blocks",
     "", "", "PRC-001", "data observation", "No hourly pre-2012 data served by the API (2008-2012 requests return empty)."],
    ["2019-12-27", "", "RTM", "market introduction", "CERC notified Power Market Regulations 2010 (Second Amendment) & IEGC amendments: 'Real Time Market to be implemented from 1st June 2020'",
     "", "", "PRC-023", "primary (CERC regulations page)", ""],
    ["2020-06-01", "", "IEX RTM", "market introduction", "IEX Real-Time Market launched: 48 half-hourly auction sessions per day, each for two 15-min delivery blocks",
     "", "", "PRC-029;PRC-002", "secondary + data observation", "IEX RTM data start 2020-06-01; several early blocks show zero bids/volume (no trade)."],
    ["2021-08-15", "", "all PX segments", "regulation", "CERC (Power Market) Regulations, 2021 effective", "", "", "PRC-023", "primary", ""],
    ["2021-10-17", "", "IEX GDAM", "market introduction", "CERC approved Green Day-Ahead Contracts on IEX (restricted manner); first GDAM delivery date in IEX data 2021-10-27",
     "", "", "PRC-028;PRC-003", "secondary + data observation", "Launch dates reported 25-27 Oct 2021."],
    ["2021-01-01", "2022-03-31", "IEX DAM", "price ceiling (observed)", "Highest DAM MCP observed before the April 2022 cap",
     round(mx_pre[1], 4), round(mx_pre[0], 4), "PRC-001", "data observation",
     "Observed max = Rs 20/kWh; the exchange's pre-2022 technical bid limit itself NOT verified from a primary document."],
    ["2022-04-01", "2022-05-05", "DAM; RTM", "price range", "CERC directed exchanges to allow bids only between Rs 0/kWh and Rs 12/kWh in DAM and RTM",
     0, 12, "PRC-026", "secondary", ""],
    ["2022-05-06", "2022-06-30", "DAM incl. GDAM; RTM; Intra-day; DAC; TAM incl. GTAM", "price range",
     "CERC Order 05/SM/2022: price range Rs 0-12/kWh extended to all segments", 0, 12, "PRC-022", "primary (recital)", ""],
    ["2022-07-01", "2022-12-31", "all segments above", "price range", "Rs 0-12/kWh extended (09/SM/2022 to 30.09.2022; 13/SM/2022 to 31.12.2022)",
     0, 12, "PRC-022", "primary (recital)", ""],
    ["2022-12-28", "2023-04-03", "all segments above", "price range", "Rs 0-12/kWh extended until further orders (17/SM/2022)", 0, 12, "PRC-022",
     "primary (recital)", f"Observed DAM max MCP 2022-04-02..2023-04-03 = Rs {mx_12[0]:.2f}/kWh"],
    ["2023-02-16", "2023-04-03", "HP-DAM (IEX)", "price range", "CERC approved High-Price DAM with price ceiling Rs 50/kWh", 0, 50, "PRC-022", "primary (recital)", ""],
    ["2023-04-04", "", "DAM incl. GDAM; RTM; Intra-day; DAC; TAM incl. GTAM", "price range",
     "CERC Order 04/SM/2023 (dated 31.03.2023): bids in range Rs 0/kWh to Rs 10/kWh, 'from 04.04.2023 until further orders'",
     0, 10, "PRC-022", "primary",
     f"Observed max MCP 2023-04-04..2026-11-04: DAM Rs {mx_10[0]:.2f}, RTM Rs {rx_10[0]:.2f}, GDAM Rs {gx_10[0]:.2f}/kWh - consistent with the Rs 10 ceiling still applying at access date."],
    ["2023-04-04", "", "HP-DAM", "price range", "CERC Order 04/SM/2023: HP-DAM range Rs 0-20/kWh (from Rs 50)", 0, 20, "PRC-022", "primary", ""],
    ["2023-04-04", "", "DAM; RTM; GDAM", "price floor", "Lower bid limit Rs 0/kWh (no negative prices allowed under the CERC price range)",
     0, "", "PRC-022", "primary", "No CERC provision for negative bids found (searches 2026-11-03)."],
    [first0["date"], "", "IEX RTM", "floor reached (observed)",
     f"First 15-min RTM block with trade clearing exactly at Rs 0/MWh: {first0['date']} {first0['block_start']} IST; {len(r0)} such traded blocks up to 2026-11-02 on {r0.date.nunique()} days ({', '.join(sorted(r0.date.unique()))})",
     0, "", "PRC-002", "data observation", "Earlier RTM blocks with MCP 0 had zero bids and zero volume (no-trade) and are excluded."],
    [dmin["date"], "", "IEX DAM", "lowest MCP (observed)", f"Lowest DAM MCP since 2012-04-01: Rs {dmin['mcp_rs_mwh']:.2f}/MWh at {dmin['block_start']} IST",
     round(dmin["mcp_rs_mwh"] / 1000, 5), "", "PRC-001", "data observation", "DAM unconstrained MCP never reached exactly Rs 0 in the period."],
    ["2025-07-23", "", "DAM (then RTM/TAM)", "market coupling", "CERC order (Petition 8/SM/2025): phased market coupling, starting with DAM coupling by January 2026; exchanges rotate as Market Coupling Operator, Grid-India backup",
     "", "", "PRC-025", "secondary", "IEX challenged at APTEL (per press)."],
    ["2026-04-19", "", "DAM; RTM; other segments", "market coupling (draft)", "Draft CERC (Power Market) (Second Amendment) Regulations, 2026 published (uniform clearing price; Grid-India proposed as Market Coupling Operator); comments extended to 05.06.2026",
     "", "", "PRC-024", "primary (CERC draft regulations listing)", "Not listed as notified on CERC Current Regulations page at 2026-11-03 (PRC-023): market coupling NOT confirmed operational."],
    ["2026-07-08", "", "IEX GDAM", "product design", "GDAM seller categories reported as Hydro / Wind / Other RE / DRE (previously Solar / Non-solar / Hydro)",
     "", "", "PRC-003;PRC-030", "data observation + secondary", "Field change visible in IEX GDAM API data from delivery date 2026-07-08."],
]
with open(P / "market_rules_timeline.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(COLS)
    w.writerows(rows)
print(len(rows))
