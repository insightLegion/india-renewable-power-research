# Transmission: capacity growth, RE evacuation, congestion (topic `transmission`)

Collected 2026-11-03. Scripts: `scripts/transmission/` (run with `.venv/bin/python -I`; CEA, Grid-India, CERC downloads via `myproxy run`).
Raw files: `data/raw/transmission/` (CEA ~200 PDFs, IEX 219 monthly RSC payloads, CERC 135 PDFs, Grid-India ~47 quarterly reports (≈1.8 GB) + 59 T-GNA + ~170 TTC/ATC PDFs, CEA plan documents).
Register: `sources/transmission_sources.csv` (352 source documents actually used).
Bucket copies (B2 `s1d-labs-trideep`): `from-box/india-renewable-power-research/raw/transmission/`, `.../processed/transmission/`, `.../sources/transmission_sources.csv`, `.../notes/transmission.md`.

## Files (data/processed/transmission/)

| file | content | format |
|---|---|---|
| `transmission_capacity.csv` | CEA cumulative line length (ckm, 220 kV+) by voltage x sector, monthly Jan-2015..Sep-2026; cumulative transformation capacity (MVA, HVDC in MW) at each March + Sep-2026; FY targets vs achievements (lines ckm, substations MVA); ISTS vs intra-state FY additions 2014-15..2026-27(H1) | tidy long |
| `inter_regional_capacity.csv` | Inter-regional transmission capacity (MW), total and 7 corridors: monthly Apr-2024..Sep-2026 (CEA growth summaries), plan-end values (2002, 2007, 2012, 2017, 2022), March totals 2015-2025 from CEA Executive Summaries | tidy long |
| `re_transmission_plans.csv` | CEA 500 GW RE transmission plan (2022), NEP Vol-II Transmission (Oct 2024) targets, IR corridor plan to 2027/2032, GEC-I state progress (30.06.2024), GEC-II state targets, Grid-India Rajasthan REZ bottleneck (Jul 2026), RE-related under-construction ISTS TBCB projects with original vs anticipated completion (CEA Sep 2026), ISTS RE complex GNA-effective vs commissioned (first/latest T-GNA issue) | long, with `scheme, metric, status, target, actual` columns (as requested) |
| `re_complex_tgna_margin.csv` | Grid-India 'Margin under T-GNA for evacuation of RE from ISTS RE complexes', 59 issues 20-Nov-2025..30-Oct-2026: per complex (Rajasthan ISTS RE, Gujarat-Khavda ISTS RE, Southern Region) connectivity/commissioned MW, GNA effective, GNA not effective, permissible limit, BESS add-on, min/max T-GNA injection limit over the day | tidy long |
| `market_congestion_monthly.csv` | (a) IEX DAM Jan-2015..Oct-2026 and RTM Jun-2020..Oct-2026, from 15-min snapshot: blocks, congested blocks, % of blocks congested, MCV and FSV totals (MU), volume curtailed by congestion (MU, % of MCV) — DERIVED; (b) CERC MMC 'Details of congestion in power exchanges' (IEX columns) Jan-2015..Mar-2026: unconstrained vs actual cleared volume, volume not cleared due to congestion, %, % of time congested, by market (DAM, GDAM, HP-DAM, RTM) — as printed | tidy long; metric prefix `dam_`/`rtm_` = IEX-derived, `cerc_iex_<mkt>_` = CERC |
| `iex_congestion_blocks_dam.csv.gz`, `..._rtm.csv.gz` | per-15-min block MCV, FSV, MCP, congestion flag (inputs to the derived monthly numbers) | wide |
| `grid_constraints.csv` | Constrained elements from NLDC/Grid-India quarterly 'Operational Feedback on Transmission Constraints' (Q4-2014 .. Q1 FY2026-27): transmission line/corridor and ICT constraint tables + RE-specific section headings; plus de-duplicated 'Limiting constraints' text for each ISTS RE complex from the T-GNA margin reports. Columns: period, quarter, region, state (keyword), element, constraint type, description, re_related (keyword flag), source_id | one row per item |
| `ttc_atc_monthly.csv` | NLDC monthly TTC / reliability margin / ATC by corridor, date range, time block (last revision of each month, 2015-2026; gaps where files missing) | wide rows |

Files starting with `_` are intermediates (merged into the above); `_*.log` are parse logs.

## Method notes
- CEA growth summaries: last cumulative row of the commissioned-lines (or substation) table parsed with pdftotext; a row is only written if Central+State+Private = Total for every voltage AND voltage totals sum to the grand total. Substation grand total is CEA's sum of AC MVA and HVDC MW.
- CEA executive summaries: FY programme (target) and cumulative achievement; programme rows written only if the sector totals add up. Newer format ("GRAND TOTAL" row) gives FY target and cumulative achievement directly.
- IEX: monthly figures are DERIVED from the 15-min snapshot. `share_of_blocks_congested` = blocks with IEX congestion flag YES / all blocks. `volume_curtailed_due_to_congestion` = sum over congested blocks of max(MCV − FSV, 0) × 0.25 h. MCV = unconstrained market clearing volume, FSV = final scheduled volume after market splitting. CERC's official figure (A−B for the month) is kept alongside for comparison; they agree closely (e.g. Jan-2015 IEX-derived 93.35% of blocks congested = CERC 93.35% of time; volume 192.6 vs CERC 197.35 MU).
- CERC MMC: numbers placed in cells by x/y position (pdfplumber) because table rows wrap; IEX column of each market is taken.
- T-GNA margin: complexes' first time-block row gives A, B, C, permissible limit, BESS; min/max of the T-GNA injection-limit column over the day are DERIVED. Period = issue date in the file title (the 30-Oct-2026 issue prints 'effective from 25 Oct 2026' and differs from the 25-Oct issue).
- Quarterly operational feedback: pdfplumber tables with 'Corridor'/'ICT' + 'Description' headers; continuation rows appended; region from the chapter. `re_related` is a keyword heuristic (RE, solar, wind, pooling, REZ, names of RE pooling stations, GIB...), not a Grid-India classification.
- TBCB: delay_months = anticipated − original completion month, DERIVED.

## Caveats
- CEA mislabelled uploads: `ss_exec_2026-03` (and the 'Executive Summary' link on the substations page for 2025-03/2026-09 in the old format) is the lines report; substation FY2025-26 target/achievement therefore not recorded. `lines_growth_2018-03` is a different report; `lines_growth_2017-11`, `2026-04`, `ss_growth_2024-03` unparseable (image/other layout) → those months missing.
- Inter-regional capacity at 31-Mar-2024: CEA Executive Summary says 1,12,340 MW; the later CEA growth summary and NEP say 1,18,740 MW. Both kept (different source_id).
- Monthly IR capacity before Apr-2024 is only available as March totals (exec summaries) and plan-end values; Oct-2023..Mar-2024 growth summaries had a different layout and were skipped.
- IEX congestion flag semantics are IEX's; CERC 'percentage of time congestion occurred' is hours-based. Both are in the file.
- grid_constraints: Western Region tables in recent reports are bilingual and partly missed by the table parser; older reports (2015-2017) have fewer table rows. Descriptions truncated at 1,500 characters.
- CERC MMC tables not parsed for Apr-2015, Oct-2017, Nov-2017 (layout) and Jun-2020 (no table found); Jul/Aug-2024 'Comparison of key statistics' files are not full reports. IEX-derived series covers those months.
- ttc_atc_monthly: 124 of 142 months; corridor labels keep NLDC footnote markers (*, ^, **) as printed; only the last revision per month; values with alternative figures (e.g. '17200 16250**') keep the first and show the cell text in `alt_values`.
- GEC numbers come from the NEP (status 30.06.2024) and the 500 GW report (Oct-2022). No official more recent GEC-I/GEC-II progress figures were retrieved (MNRE and MoP sites returned 404/SPA shells; Sansad PDF did not download).

## NOT AVAILABLE (searched, not obtained)
- IEX congested corridors by name per month (new IEX site has no congestion page); only the CERC narrative where congestion occurred.
- Grid-India 'Real-time TTC/ATC revisions' (240 files) not parsed; daily/weekly VDI-TTC-ATC reports not collected.
- GEC-II physical progress (ckm/MVA completed) and ISTS-GEC (PGCIL) completion figures from an official source.
- Stranded RE capacity before Nov-2025 (T-GNA margin reports start 20-Nov-2025; earlier only narrative in quarterly feedback).
- CEA 'Resource Adequacy Plan for Transmission System of Rajasthan / Gujarat up to 2034-35' downloaded (data/raw/transmission/plans) but not tabulated.
- Substation (MVA) cumulative values for months other than March and Sep-2026 (only March files downloaded).
- Area clearing prices / regional price divergence: deliberately left to the prices collector.
