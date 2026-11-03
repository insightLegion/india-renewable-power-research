# capacity_storage: installed RE capacity, pipeline and energy storage (India)

Collector topic `capacity_storage`; collected 2026-11-03. Source register: `sources/capacity_storage_sources.csv` (CAP-001 to CAP-070).
Scripts: `scripts/capacity_storage/` (run order: `fetch_cea_dashboard.py` (via `myproxy run`), `fetch_text.py`,
`parse_cea_installed_capacity.py`, `parse_statewise.py`, `build_outputs.py`, `write_sources.py`).
Storage: per the project's storage rule, raw downloads, processed CSVs, the source register and these notes are kept in
bucket `s1d-labs-trideep` under `from-box/india-renewable-power-research/{raw,processed}/capacity_storage/`, `.../sources/` and `.../notes/`.
The local copies were deleted after upload. To re-run the scripts, first restore the raw folder:
`mybucket get -r from-box/india-renewable-power-research/raw/capacity_storage data/raw/capacity_storage`.

## Files (data/processed/capacity_storage/)
All files use the tidy long format (geography, period_start, period_end, granularity, metric, value, unit, source_id, notes)
unless noted otherwise.

| file | rows | content |
|---|---|---|
| re_capacity_india_monthly.csv | 1765 | CEA monthly All-India installed capacity, 2014-03 to 2026-09 (only the March reports before 2017; 2017-11 missing). Also a few MNRE/PIB national points (2024-11, 2025-11, 2026-01, 2026-06, 2026-07). |
| re_capacity_india_fy.csv | 523 | FY-end stocks (CEA 31-Mar, MNRE RE Statistics Table 1.1/2.1 2014-15 to 2024-25, MNRE FY2025-26), FY additions (MNRE/PIB), MNRE solar sub-categories, and DERIVED CEA net additions and shares |
| re_capacity_statewise.csv | 2160 | State-wise snapshots (MW): 31.03.2015-31.03.2025 for the top-5 RE states (from MNRE state tables); all states on 31.03.2020 (solar), 28.02.2023 (solar), 31.10.2023 (solar), 31.03.2024, 31.03.2025, 31.05.2025, 28.02.2026, 31.03.2026, plus wind on 30.06.2026 |
| re_pipeline_targets.csv | 195 | MNRE under-implementation/tendered by sector, CEA under-construction RE by state (Mar & Sep 2026), REIA LoA/PPA backlog, NEP 2026-27/2031-32 projected mix, 500 GW target, bidding trajectory |
| storage_capacity.csv | 245 | BESS and PSP by status (operational, under_construction, awarded, tendered, pipeline, planned, required, potential, commissioned_in_period). It has extra columns `technology` and `status`. |
| storage_policy_timeline.csv | 32 | Storage policy events (VGF 1 & 2, ESO trajectory, ISTS waivers, NEP, advisories). Columns: date, date_precision, instrument, issuer, description, parameter, value, unit, source_id, notes |
| ember_capacity_india_annual.csv | 156 | Ember yearly capacity (GW) for India, 2014-2025, by source |
| capacity_crosscheck_ember_vs_cea.csv | 39 | DERIVED: Ember vs CEA 31-Dec values for solar, wind, bio and nuclear |
| _cea_ic_parse_log.csv, _cea_installed_capacity_monthly.csv | - | Intermediate parser outputs (diagnostics and the CEA-only series) |

## Method
- **CEA Installed Capacity (CAP-001):** all 120 monthly PDFs listed on the new CEA dashboard were downloaded through the Indian proxy and parsed
  with pdfplumber. Two items were read from each PDF:
  1. The "ALL INDIA … Total" row: coal, lignite, gas, diesel, nuclear, hydro, RES(MNRE), renewable total and grand total. Reports before 2018-11 have
     no lignite column, so those rows are recorded as `coal_capacity_incl_lignite`.
  2. The footnote "Break up of RES all India as on <date>": small hydro, wind, BM power/cogen, waste-to-energy and solar. The break-up sums were
     checked against its stated total.

  The RES break-up date can lag the report date (common in 2017-2019). Rows are dated by the RES date, and when several reports repeat the
  same RES date only one row is kept. The newest reports (2026-09) also carry a page-1 summary, which was used where the table/footnote lacked a value.
- **MNRE:** the MNRE website is a JavaScript application, and its content API could not be used. Its data was taken instead from:
  - MNRE files on the government CDN (cdnbbsr.s3waas.gov.in): the RE Statistics 2023-24 and 2024-25 books and the monthly state-wise PDFs;
  - PIB releases (fetched through the Indian proxy).

  State tables were read with pdfplumber `extract_tables`, using explicit column maps for the RE-Statistics layout. The parser checks that state
  rows sum to the India "Total" row; only small residuals remain (see caveats). The top-5 state history tables (Tables 11-15.2.1) were assigned
  to a state only when their 2024-25 row matched that state's Table 8.2 solar and wind exactly. The book's chapter headings and text are inconsistent
  about which chapter covers which state, which is why this matching was used.
- **Storage:** values come from these sources:
  - CEA's monthly "Status of BESS" (May-Sep 2026; data attributed to IESA), parsed with regex;
  - CEA PSP status reports (March of 2017-2026, except 2023, plus Sep 2026), transcribed from their summary/total lines;
  - PIB, Mercom, JMK/IEEFA and the VGF progress reply, transcribed by hand in `build_outputs.py` with source text in the notes column.
- **DERIVED rows** (only in `re_capacity_india_fy.csv` and `capacity_crosscheck_ember_vs_cea.csv`, marked "DERIVED" in notes):
  - year-on-year differences of CEA 31-March stocks (net additions, net of retirements/revisions);
  - shares of RES / RE incl. large hydro / solar+wind in CEA total capacity;
  - Ember minus CEA differences.

  The inputs to every derived row are in the same file.

## Key numbers (all read from the sources; GW unless stated)
- CEA solar: 2.63 (31.03.2014), 6.76 (2016), 21.65 (2018), 34.63 (2020), 54.00 (2022), 81.81 (2024), 105.65 (2025), 150.26 (31.03.2026), 171.05 (30.09.2026).
  CEA wind: 21.04 (2014), 34.05 (2018), 40.36 (2022), 50.04 (2025), 56.09 (2026-03), 59.20 (2026-09).
- CEA total installed capacity (utilities): 248.55 (Mar-2014), 475.21 (Mar-2025), 532.74 (Mar-2026), 558.90 (Sep-2026).
  RES(MNRE) = 223.27 GW at Mar-2026 and 247.18 GW at Sep-2026.
- DERIVED shares of CEA total capacity: RES 14.2% (Mar-2015) → 41.9% (Mar-2026); RE incl. large hydro 29.2% → 51.6%; solar+wind 9.9% → 38.7%.
- FY additions: solar 15.03 (FY24), 23.83 (FY25), 44.61 (FY26); wind 3,253 / 4,151 / 6,057 MW; non-fossil 55.29 GW in FY26 (MNRE/PIB).
  The CEA-derived net additions match: FY26 solar +44,614 MW, wind +6,057 MW.
- MNRE solar sub-categories on 31.03.2026 (MW): ground-mounted 114,873; rooftop (incl. PM Surya Ghar) 25,728; hybrid solar component 3,862;
  off-grid/KUSUM-B 5,798. On 31.03.2025 they were 81,012 / 17,017 / 2,875 / 4,743.
- State, 31.03.2026: Rajasthan solar 41,013 MW (wind 5,349); Gujarat solar 29,303 MW (wind 15,642). On 30.06.2026 Gujarat wind was 16,086 MW
  and Tamil Nadu wind 12,273 MW.
- Pipeline: on 30.11.2025, 184.24 GW of RE was under implementation and 48.74 GW tendered (solar 69.12 / 35.46; hybrid/RTC/FDRE 59.24 / 11.48).
  CEA counted 140.5 GW under construction on 30.09.2026, of which Rajasthan had 52.1 GW and Gujarat 37.4 GW.
  REIAs held about 69 GW of LoAs on 31.12.2025 but only about 24.3 GW of PPAs. On 30.09.2025, 43.9 GW of LoAs had unsigned PSAs.
- BESS (CEA, ≥1 MWh), operational: 2,721 MW / 7,499 MWh (31.05.2026) → 5,318 MW / 14,543 MWh (30.09.2026). On 30.09.2026 a further
  27,730 MW / 78,964 MWh was under construction, 9,697 MW / 28,914 MWh awarded and 20,380 MW / 76,021 MWh in tender, for 63.1 GW / 198.4 GWh across all stages.
  CEA's FY profile shows 84.5 MW / 215.6 MWh commissioned up to March 2025.
- BESS according to Mercom: 1,082 MWh (end-2025), 5.9 GWh (Mar-2026), 9.3 GWh (Jun-2026); 8.2 GWh were added in 1H 2026.
  JMK/IEEFA counts only about 1.8 GWh of grid-scale BESS at Mar-2026, and 10.4 GW of standalone BESS allocated in 2025.
- PSP (CEA): operational capacity was 4,786 MW from 2017 to 2021 (several units then not working in pumping mode), then 4,746 MW,
  7,176 MW (Mar-2026) and 7,426 MW (Sep-2026). Under construction: 1,080 MW (2017) → 15,870 MW (Sep-2026). CEA's pathway reaches
  105.6 GW cumulative by 2035-36.
- Requirements:
  - NEP 2023: 16.13 GW / 82.37 GWh by 2026-27 (BESS 8.68 / 34.72) and 73.93 GW / 411.4 GWh by 2031-32 (BESS 47.24 / 236.22; PSP 26.69 / 175.18).
  - CEA Optimal Generation Mix 2030: 60.63 GW (BESS 41.65, PSP 18.98) by 2029-30, and about 336 GWh.
- VGF: scheme 1 (Sep 2023) was 4,000 MWh, raised to 13,220 MWh. Scheme 2 (9 Jun 2025) is 30 GWh at Rs 18 lakh/MWh. By July 2026, LoAs
  under both schemes totalled 35.1 GWh, financial closure 11.5 GWh, and only 0.5 GWh had been commissioned.
- ESO trajectory (MoP order 22.07.2022, as reproduced by MERC): 1.5% (FY25), rising 0.5 pp a year to 4.0% (FY30).

## Caveats / discrepancies
- **AC vs DC and coverage:** MNRE and CEA solar figures are AC/installed-capacity numbers. MNRE solar includes rooftop and off-grid/KUSUM,
  and CEA has included off-grid RES since July 2021.
  - MNRE Table 2.1 gives solar of 3.99 GW at FY2014-15 against CEA's 3.74 GW at 31.03.2015. Early MNRE series appear to include off-grid.
  - The MNRE RE-Statistics 2014-15 total capacity (275.99 GW) differs from CEA's 274.90 GW.
- **Ember vs CEA:** wind and nuclear match to within 0.01-0.15 GW. Solar differs by up to +2.3 GW (2018, 2020); 2023 and 2025 are slightly below CEA.
  Bioenergy is about 0.2 GW higher in Ember from 2019, which is roughly CEA's waste-to-energy (excluded from CEA `bio_power_capacity`); before 2019 the gap is 0.86-0.91 GW.
  Ember "Hydro" (49.12 GW in 2025) does not equal CEA large hydro incl. PSP (50.91) and appears to use a different hydro/PSP/small-hydro boundary.
  Ember's capacity is calendar-year end and is not explicitly AC/DC-labelled in the file.
- **CEA:**
  - Grand total fell from 475.2 GW (Mar-2025) to 472.5 GW (Apr-2025): coal dropped 2.5 GW, presumably a reclassification. The value is recorded as printed.
  - Large hydro includes PSP.
  - State tables in the CEA reports are ownership/allocation based, not location based, and were not used for state RE.
- **BESS definitions differ a lot.** CEA/IESA "operational" counts projects ≥1 MWh including merchant ones (14.5 GWh at Sep-2026). Mercom counts all
  installations (9.3 GWh at Jun-2026). JMK counts grid-scale only (1.8 GWh at Mar-2026). JMK's "9.6 GWh … FY2027 YTD" wording is ambiguous.
  CEA's FY2025-26 commissioned figure changed between reports: 445.35 MW / 1,082.6 MWh (May report) vs 193.35 MW / 574.6 MWh (Jun-Sep reports). Both are kept.
- **Mercom inconsistencies:** Q4-2025 additions of 442.7 MWh sit oddly with 547 MWh for the whole of 2025 (H1-2025 was 98.4 MWh).
- **State parse residuals** (sum of states minus India total):
  - bagasse cogeneration +46 to +57 MW in the Feb/Mar-2026 MNRE tables;
  - A&N Islands small hydro (5.25 MW) on 31.03.2026 not captured;
  - PIB wind on 30.06.2026 −4 MW (the 4.3 MW 'Others' row was not captured).

  The 31.01.2026 MNRE state table was skipped because its rows are misaligned; only its India solar sub-category totals are used.
- **CEA under-construction report:** the Sep-2026 Karnataka hybrid value extracted as "36055.885" does not fit the row total, so it was not recorded (value left empty, with a note).
- **NEP 2031-32 total capacity** appears as 900,422 MW in the 2023 PIB release and as 873,736 MW in an April 2026 MoP reply. Both are recorded.
- **VGF scheme-1 size** is 13,200 MWh (Apr 2025), 13,220 MWh (Feb/Dec 2025) or 13.8 GWh (Jul 2026 reply). The VGF rate is Rs 27 lakh/MWh per PIB Feb 2026
  vs "Rs 46 lakh/MWh or 30%" per PIB Apr 2025. The PLI ACC approval is dated May 2021 vs June 2021 in different PIB releases.

## NOT AVAILABLE (not found or not obtainable in this pass)
- MNRE "Physical Progress" page and its monthly archive: the site is a JavaScript application, and its data API needs a key embedded in the page
  (use was refused). MNRE monthly physical-progress PDFs were therefore not collected; national monthly breakdowns come from CEA instead.
- A monthly series of solar sub-categories (ground-mounted / rooftop / hybrid / off-grid) before 2024. Only these points were found: 31.03.2024
  (no hybrid split), 31.03.2025, 31.01.2026, 28.02.2026 and 31.03.2026.
- State-wise wind before 31.03.2024, except the top-5 RE states (2014-15 onward). Historical all-state wind snapshots and state-wise solar for
  31.03.2015-2019 and 2021-2022 (other than the top-5 states) were not found. The RE Statistics Table 8.1 (state RE totals 2017-18 to 2024-25) was not parsed (PDF text glitches).
- CEA monthly installed capacity for 2017-11 (not listed), and monthly reports between Apr-2014 and Dec-2016 (only the March reports are listed).
- BESS operational capacity before 2025 from an official source (CEA's BESS reports start May 2026, apart from the "up to March 2025" profile row),
  and a BESS state/project-wise list (the CEA report gives only totals).
- SECI / NTPC / NHPC / NVVN agency-wise BESS tender and award volumes. Only market-tracker aggregates (Mercom, JMK/IEEFA) and the Aug-2026
  awards (SECI, WBSEDCL, GUVNL) were collected.
- VGF tranche-2 state-wise MWh allocation. Secondary sources conflict (Karnataka and Andhra Pradesh at 2,000 vs 1,500 MWh) and the MoP letter was not obtained.
- The ESO value for FY2023-24 from the primary MoP order (the MoP PDF itself was not retrieved).
- The full CEA "Optimal Generation Mix 2030" report (only the PIB summary was used). CEA PSP report for 2023-03 not downloaded.
- AC/DC labelling of capacities from CEA/MNRE (not stated in the sources).
