# Prices: IEX DAM / RTM / GDAM 15-minute prices, near-zero price frequency, market rules

Collector: `prices`. Access date for all sources: 2026-11-03. Source register: `sources/prices_sources.csv` (PRC-001..PRC-038).
Scripts: `scripts/prices/01..08_*.py` (run with `.venv/bin/python -I`). Raw files: `data/raw/prices/` (git-ignored).

## 1. Method

**IEX block data (PRC-001..005).** The IEX market-data pages (Next.js) are backed by a public JSON API found in the site's JS
bundle: `https://www.iexindia.com/api/v1/{dam,rtm,gdam}/{market-snapshot,area-price}?interval=ONE_FOURTH_HOUR&fromDate=DD-MM-YYYY&toDate=DD-MM-YYYY[&bidArea=A1,...,MKT]`.
A full calendar year per request works (35,136 rows for 2024). That is simpler and cleaner than the RSC payload
(`RSC: 1` header), which carries the same rows plus four summary rows per day (Total MWh / Max / Min / Avg). 15 yearly
requests per endpoint, sequential with 1.5 s pauses, no proxy needed. Raw JSON saved unchanged (`data/raw/prices/iex_api/`).

- **Earliest data**: the API serves DAM from **2012-04-01** (15-min blocks from the first day). Requests for 2008-2011 (hourly
  or daily) return no rows. So the DAM data starts in April 2012 rather than January 2015, and has no hourly-era data.
- **Volume units**: IEX publishes 15-min volumes as the **average MW over the block**. The CSVs keep them in MW
  (`*_mw` columns, not `*_mwh` as originally requested). Block energy (MWh) = MW x 0.25. This was checked two ways:
  IEX's own daily "Total (MWh)" = sum(block MW)/4, and the derived Oct 2025 DAM buy/sell bid totals (6,852.33 / 22,800.73 GWh)
  match CERC MMC's figures in MU exactly.
- **MCP** is IEX's unconstrained market clearing price in Rs/MWh. In the GDAM data the field is named `unconstrained_m_c_p`.
  Area (bid-area) clearing prices are in the separate `*_area_prices.csv` files.
- **No-trade blocks**: 232 RTM blocks (mostly June 2020 to 2021, a few later) show zero purchase bid, zero sell bid and zero volume,
  with MCP values of 0, 5000, 6000, 10000 and so on. These are flagged `no_trade=True` and excluded from all statistics. Without
  this flag, RTM would show false Rs 0 prices in 2020-21. Eleven blocks have zero bids reported but non-zero volume; they are kept and
  listed in `iex_block_validation.csv`.

**Derived tables (script 04). These are clearly DERIVED: every row's notes say so.** Rules:
- Statistics use traded blocks only. Days with fewer than 90 traded blocks are excluded (RTM 2020-06-06, 2021-12-31, 2026-04-15).
- **Solar hours** = blocks starting 09:00 to 16:45 IST (09:00-17:00). Non-solar = all other blocks.
- `avg_mcp` = simple mean of block MCPs. This matches how IEX's monthly releases report "average MCP". `vw_mcp` = mean weighted by MCV
  (cleared volume). It matches CERC MMC's "weighted average".
- Thresholds: `floor_0` = MCP exactly Rs 0/MWh (the CERC lower bid limit); `le_0.1`, `le_0.5`, `le_1`, `le_2` = MCP <= Rs 0.1, 0.5, 1 or 2/kWh.
  Equivalent hours = blocks / 4. "Longest run" = the longest run of consecutive blocks within one delivery day; the monthly and annual
  rows give the maximum over days and the first day it occurred.

**CERC MMC (script 05).** The monthly short-term market reports for Jan 2025 to Mar 2026 (15 PDFs) and the 2024-25 annual report
were fetched through the Indian proxy and converted to text with pdfplumber. From each report the script extracts the IEX columns of
the "Price of electricity transacted in DAM / GDAM / RTM" tables (minimum, maximum and weighted-average area clearing price) and the
IEX buy/sell bid volumes stated in the text.

## 2. Files (data/processed/prices/)

| file | rows | content |
|---|---|---|
| iex_dam_blocks.csv | 511,680 | wide format: date, block_no, block_start, block_end, purchase_bid_mw, sell_bid_mw, mcv_mw, scheduled_volume_mw, mcp_rs_mwh, congestion, no_trade, source_id. 2012-04-01 to 2026-11-04 (delivery date; 4 Nov already cleared on 3 Nov) |
| iex_rtm_blocks.csv | 225,308 | same columns, 2020-06-01 to 2026-11-03 (3 Nov has 94 of 96 blocks, because the last two were not yet traded at download) |
| iex_gdam_blocks.csv | 176,160 | purchase bid; sell bid, MCV and cleared volume by source (solar/non-solar/hydro until 2026-07-07; hydro/wind/other_re/dre from 2026-07-08; empty where not applicable); mcp_rs_mwh. 2021-10-27 to 2026-11-04 |
| iex_dam_area_prices.csv | 511,680 | wide format: area clearing price for A1, A2, E1, E2, N1, N2, N3, S1, S2, S3, W1, W2, W3 plus MCP (Rs/MWh); S3 is empty before 2017 |
| iex_gdam_area_prices.csv | 176,160 | same, for GDAM |
| iex_block_validation.csv | 81 | blocks per day, missing days and blocks, no-trade blocks, anomalies |
| prices_daily_summary.csv | 9,508 | wide format, one row per market and day: avg, vw, min and max MCP; solar and non-solar avg MCP; bid and cleared volumes (MWh); sell/buy ratio overall and in solar hours; near-zero block counts and longest runs per threshold |
| prices_monthly_summary.csv | 4,815 | long format (CONVENTIONS columns + `market`): monthly and annual avg/vw/min/max MCP, solar vs non-solar avg, sell/buy ratios, volumes (GWh), uncleared solar-hour sell bids |
| near_zero_price_stats_monthly.csv | 10,663 | long format: blocks, hours and share of blocks at or below each threshold; blocks in solar hours; days with any; longest daily run. Monthly and annual, per market |
| near_zero_by_hour.csv | 3,359 | long format: near-zero block counts by hour of day, per market, calendar year and threshold |
| near_zero_area_prices_monthly.csv | 18,459 | long format: per bid area and month, blocks with area price <= Rs 0.5, 1 or 2; blocks with area price <= Rs 1 while MCP > Rs 1 (near-zero caused by market splitting); min and avg area price; blocks with any area price different from MCP |
| market_rules_timeline.csv | 20 | price ceilings and floor, segment launches, block length, market coupling, GDAM category change; each row has a source and evidence type |
| cerc_mmc_monthly_iex_stats.csv | 315 | from CERC MMC monthly reports Jan 2025 to Mar 2026: IEX DAM/GDAM/RTM min, max and weighted-average ACP (Rs/kWh), buy, sell and traded volume (MU), sell/buy ratio (derived) |
| low_price_statements.csv | 21 | explicit statements and quotes on low or near-zero prices and surplus sell bids, each cross-checked against the block data |

**Coverage and validation.**
- DAM: 5,330 days. One day is missing, **2012-08-01** (the API returns nothing for it). Every other day has 96 blocks.
- RTM: 2,347 days. 2024-07-17 lacks blocks 95-96. 2026-11-03 was incomplete at download.
- GDAM: 1,835 days, all complete.
- No duplicate rows.
- Cross-checks against published figures all match:
  - IEX monthly releases (simple-average MCP): Oct 2025 DAM 2.67 / RTM 2.73; Jan 2026 3.86 / 3.72; Feb 2026 3.58 / 3.59; Apr 2026 DAM 5.26, RTM 4.82 (ours 4.81); May 2026 DAM 4.88.
  - CERC MMC (weighted averages): Oct 2025 DAM 2.86, GDAM 2.47, RTM 2.53.
  - Ember: 375 DAM blocks below Rs 1/kWh in 2024 and 514 in H1 2025 (ours: 375 and 514).

## 3. Key findings (all DERIVED from IEX block data unless a source is named)

1. **Price floor and minimum.**
   - Floor: CERC's bid range is Rs 0-10/kWh from 4 Apr 2023 (PRC-022). Before that it was Rs 0-12 (Apr 2022 to Apr 2023), and the observed
     maximum MCP was Rs 20/kWh in 2021-22. No negative-price provision was found.
   - **RTM cleared exactly at Rs 0/MWh in 21 traded blocks**: the first was on 2026-05-01 (10:30-11:00), then 2026-07-05 (10 blocks,
     15:00-17:30) and 2026-10-27 (9 blocks, 12:00-14:15). On 27 Oct 2026, 11,005 MW were bought against 36,878 MW of sell bids.
   - **The DAM MCP never reached Rs 0.** Its lowest was **Rs 20.81/MWh (Rs 0.021/kWh)** on 2026-05-31 at 13:30-14:00.
     Earlier lows: Rs 49.51/MWh (2025-10-02) and Rs 299.76/MWh (2024).
   - GDAM low: Rs 198.81/MWh (2025).
2. **Near-zero frequency, DAM (blocks with MCP <= Rs 1/kWh)**:

   | period | blocks | hours | share of blocks | days |
   |---|---|---|---|---|
   | 2022 | 19 | | | |
   | 2023 | 5 | | | |
   | 2024 | 375 | 93.75 | | 30 |
   | 2025 | 1,443 | 360.75 | 4.1% | 84 |
   | 2026, to 4 Nov | 1,055 | 263.75 | 3.6% | 65 |

   - At <= Rs 2/kWh: 551 blocks (1.6%) in 2023, 5,610 (16.0%) in 2025 and 5,180 (17.5%) in 2026 to date.
   - At <= Rs 0.5/kWh: 79 blocks in 2024, 865 in 2025 and 694 in 2026.
3. **RTM near-zero frequency (<= Rs 1/kWh)**:

   | year | blocks | share of blocks | days |
   |---|---|---|---|
   | 2023 | 198 | | |
   | 2024 | 643 | | |
   | 2025 | 1,595 | 4.6% | 160 |
   | 2026, to 3 Nov | 1,746 | 5.9% | 173 |

   - At <= Rs 0.1/kWh: 389 blocks in 2025 and 652 in 2026.
4. **Seasonality.** The peak months are April-June and August-November (monsoon and post-monsoon with weak demand). Examples:
   - Oct 2025 DAM: 313 blocks <= Rs 1 on 20 days; 33% of blocks <= Rs 2.
   - May 2026: DAM 292 blocks, RTM 290 blocks.
   - Dec-Feb: almost none.
5. **Hour of day.** In 2025-26 virtually all DAM near-zero blocks fall between 08:00 and 16:00, peaking at 13:00-14:00 (2025: 244
   blocks <= Rs 1). There were none between 19:00 and 07:00. This is the reverse of 2016-17, when the near-zero blocks (monsoon
   surplus) were mostly at night and before dawn (01:00-07:00).
6. **Solar-hour price collapse.**
   - DAM average MCP in 09:00-17:00 vs other hours:

     | year | solar hours (Rs/kWh) | other hours (Rs/kWh) |
     |---|---|---|
     | 2014 | 3.94 | 3.42 |
     | 2023 | 4.38 | 6.11 |
     | 2025 | **2.31** | **4.83** |
     | 2026, to date | **2.26** | **6.50** |

     Solar hours used to be the dearer part of the day; they are now the cheapest.
   - RTM: 2.56 vs 4.35 in 2025.
7. **Surplus sell bids.**
   - DAM sell/buy ratio in solar hours: 1.22 (2023), 2.81 (2025), 2.20 (2026 to date). Monthly peak: **6.0 in Oct 2025**.
   - Oct 2025 overall: 22,800.73 MU of sell bids vs 6,852.33 MU of buy bids (CERC MMC, PRC-015; ratio 3.33).
   - Uncleared DAM sell bids in solar hours were 9,937 GWh in Oct 2025.
   - GDAM is the exception: sell/buy is below 1 in every month, so GDAM is supply-short, yet its MCP still falls to Rs 0.2/kWh.
8. **Longest runs.** DAM held at or below Rs 1/kWh for up to 39 consecutive blocks (9.75 h) in a day: 2025-07-27 and 2025-09-28. In
   2026 the longest was 38 blocks (2026-05-03). RTM: 38 blocks (2025-05-25) and 37 (2026-07-05). The all-time DAM record of 66 blocks
   (2017-07-02) was an all-day monsoon event, not solar.
9. **Area (regional) prices.**
   - Market splitting in DAM has almost disappeared: blocks with any area price different from MCP fell from 32,842 (2015) to 580
     (2025) and 865 (2026). So the 2025-26 near-zero prices are **all-India uniform**, not regional.
   - Exceptions where congestion produced a regional low:
     - **N3 at Rs 0** for 39 midday blocks in July 2022 (e.g. 3 and 7 July, 12:00-16:00).
     - Northern areas (N1-N3) at or below Rs 1 while MCP was above Rs 1 in 41 blocks (N3) in 2024.
     - **15-18 April 2026: N1-N3 at Rs 0.20-0.95/kWh while the other areas were at Rs 1.40-2.42/kWh and MCP was above Rs 1** (53 blocks).
   - The RTM area-price endpoint returns no data.
10. **CERC MMC minimum ACP** (cerc_mmc_monthly_iex_stats.csv):
    - IEX RTM min Rs 0.0000/kWh in May and Jul 2025, 0.0005 in Oct 2025, 0.02 in Mar 2026.
    - IEX DAM min Rs 0.05/kWh in Aug, Sep and Oct 2025.
    - GDAM min Rs 0.2/kWh in Jun-Aug and Oct 2025.
11. **External analyses.**
    - Ember (PRC-035): mid-day DAM prices of Rs 0-0.30/kWh on 25-26 May and 1-2 Jun 2025; mid-day to evening spread of Rs 7.5/kWh in
      June 2025; solar capture rate down from 93% (2019) to 70% (2024).
    - IEX (via PRC-031): April 2026 "prices touching near-zero levels across multiple time blocks ... driven by surplus renewable
      energy during solar hours".
    - IIFL (PRC-034): "zero" spot prices on 25 May 2025. In the data, RTM min was Rs 0.52/MWh that day.

## 4. Caveats

- The market rules for 2011 (15-min blocks), 2020 (RTM), 2021 (GDAM), 2022 (Rs 12 cap) and 2025 (coupling order) come from secondary
  press summaries via WebSearch. The 2023 order (PRC-022), which recites the 2022 orders, was read in the original.
- The pre-April-2022 Rs 20/kWh upper limit is inferred from the observed maximum MCP, not from a document.
- **Market coupling status**: a draft PMR (Second Amendment) Regulations 2026 was published (comments to 5 Jun 2026), but no notified
  regulation appears on CERC's Current Regulations page. The coupling go-live is unconfirmed.
- **Area prices before 2016 contain whole-day zeros** (S2: 29 days in 2013 and 135 days in 2014; N3: 18 days in 2013). These are probably
  placeholders for an isolated or no-clearing area, not real prices, so treat pre-2016 regional zero counts as unreliable. Bid-area to
  state mapping was not verified, so only the region letter is reliable: N, S, E, W, and A = North-East.
- CERC reports ACP (area clearing price), which can differ slightly from IEX's unconstrained MCP. For example, RTM May 2025 min is
  0.0000 in CERC vs 0.0005 in our data.
- The Mint explainer's "zero on May 1 and May 15" claim (PRC-037, unverified) holds for 2026-05-01 in RTM only. 2026-05-15 did not
  go near zero (RTM min Rs 0.99/kWh).
- The 2026 figures are partial-year (to 3 or 4 Nov). Nov 2026 rows cover only 3-4 days.
- The DAM, RTM and area-price CSVs are large (18-70 MB). Consider git LFS or gzip before committing data/processed.

## 5. NOT AVAILABLE

- DAM data before 2012-04-01 (hourly era), because the IEX API returns nothing. 2012-08-01 DAM is also missing.
- RTM area (bid-area) prices: the endpoint exists but returns 0 rows for 2020-2026.
- IEX monthly press releases in the original: the IEX press-release page loads client-side, so the API for it was not found. Figures
  were taken from secondary reports (PRC-031..033).
- CERC MMC monthly reports for Apr-Oct 2026 are not yet published on cercind.gov.in. Monthly MMC reports before 2025 were not
  collected (the listing pages for 2008-2024 exist).
- Explicit "unmet / uncleared sell volume" statistics from CERC or IEX: none found. Our derived `uncleared_sell_bid_volume_solar_hours` =
  sell bids minus MCV, which overstates true unsold supply where bids are price-contingent.
- Bid-area to state mapping (not found in an official source within this task).
- PXIL and HPX block-level prices (not collected; IEX holds about 99% of DAM volume per CERC MMC).
- Final notified market-coupling regulations and a go-live date.
- The 2011 CERC ROP PDF (PRC-027): direct download failed with an SSL error via the proxy.
