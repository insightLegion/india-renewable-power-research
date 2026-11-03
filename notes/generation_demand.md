# generation_demand — notes

Collector: generation_demand. Collected 2026-11-03. Source register: `sources/generation_demand_sources.csv`.
Scripts: `scripts/generation_demand/` (run order at the end). Raw downloads: bucket `from-box/india-renewable-power-research/raw/generation_demand/` (local copies deleted after verified upload; scripts read local paths, so restore with `mybucket get -r` before re-running).

## Outputs (data/processed/generation_demand/)

Stored in the B2 bucket (s3 bucket s1d-labs-trideep, prefix from-box/india-renewable-power-research/processed/generation_demand/); local copies deleted after upload per the project storage rule.

| file | rows | coverage |
|---|---|---|
| psp_daily_india.csv | 64,395 | 3,887 days, 2013-03-31 → 2026-11-02 (see gaps below) |
| psp_daily_regions.csv | 275,777 | NR/WR/SR/ER/NER, same days |
| psp_daily_states.csv | 502,383 | ~36-44 states/entities per day, same days |
| hourly_india.csv | 69,371 | **15-min**, 2024-11-04 → 2026-11-02 (724 days); wide format |
| profile_by_month_derived.csv | 2,400 | DERIVED: mean 15-min profile per month 2024-11 → 2026-11 |
| vre_extremes_derived.csv | 125 | DERIVED: top-25 blocks (VRE share, min net load, solar) + monthly extremes |
| gen_monthly_india.csv | 3,845 | CEA RE by source 2018-08 → 2026-09 (gaps 2018-11, 2026-04); Ember all sources 2019-01 → 2026-09 |
| gen_fy_india.csv | 560 | CEA RE FY 2018-19 → 2025-26; Ember calendar years 2010-2025 |
| gen_statewise.csv | 126,065 | CEA state x RE source monthly 2019-09 → 2026-09 (gaps as above + 2026-01..05, 07); Ember states monthly 2019-01 → 2025-11, yearly 2019-2024 |
| demand_cea_psp_monthly.csv | 51,703 | CEA energy 2013-01 → 2026-08, peak 2015-01 → 2026-08, state/region/India |
| demand_fy.csv | 4,473 | FY 2012-13 → 2025-26 (CEA March reports) + LGBR FY 2015-16 → 2025-26 |
| demand_projections.csv | 118 | LGBR 2026-27 anticipated; NEP/20th EPS 2026-27 & 2031-32 |
| all_time_highs_snapshot.csv | 34 | Grid-India records as of 30-Sep-2026 |

PSP day coverage by year (energy_met present): 2013 265, 2014 364, 2015 217, 2016 47, 2017 207, 2018 48 (2015-18
sampled: days 1/8/15/22 + whatever had already downloaded), 2019 310, 2020 312, 2021 358, 2022 359, 2023 365,
2024 364, 2025 365, 2026 306 (to 2-Nov). Of 124 missing days since 2019, the archive lists a file for each, but 50
are byte-for-byte duplicates of a neighbouring day's report (same printed date, same numbers) and a few are 404s;
54 duplicate-date reports were dropped (list in `_work/psp_duplicate_reports_dropped.csv`).

All files use the CONVENTIONS long format (`geography, period_start, period_end, granularity, metric, value, unit,
source_id, notes`) except `hourly_india.csv` (wide, see below) and the two `*_derived.csv` files.

## Method

### 1. Grid-India Daily PSP reports (GEN-GI-PSP-DAILY)
* File list obtained from the site's own API (`POST https://webapi.grid-india.in/api/v1/file`, `_type=DAILY_PSP_REPORT`,
  per FY, `_month=00` returns the whole FY); files fetched from `https://webcdn.grid-india.in/<FilePath>` via the
  Indian proxy, 1 s delay, one file per report date (xls preferred over pdf; latest upload if duplicated).
* Reports are xls from late 2022 (2022-23 reports were back-filled as xls in 2026) and PDF only before.
  PDFs parsed with `pdftotext -layout`; xls with pandas. Same line-oriented parser for both (`psp_parse.py`).
* **Data date = "Date of Reporting" printed inside the report minus one day** ("Report for previous day").
  The file title date is sometimes the data date (2026) and sometimes the reporting date (2016-2019), so the
  printed reporting date is used, not the file name.
* Section A (regional/all-India): evening-peak demand met & shortage, energy met, hydro/wind/solar gen, energy
  shortage, max demand met of the day (+ time). Section G: source-wise generation (coal, lignite [from ~2018;
  2017 reports give "Thermal (Coal & Lignite)"], hydro, nuclear, gas/naphtha/diesel, RES, total) and RES /
  non-fossil shares. Section I (from ~2023): all-India max demand met in solar vs non-solar hours, with time and
  shortage. Section C: state max demand met, shortage at max demand, energy met, energy shortage.
* Format history seen: 2013-16 reports have only demand/energy/hydro/wind (no solar line, no section G); solar line
  and section G appear by 2017; the "time of max demand" line by 2019; section I (solar / non-solar hour peak) in
  2023+; 15-min time series sheet/page from 2024-11-04.
* **RE curtailment: no curtailment field exists in any Daily PSP format seen (checked 2013-2026 xls/pdf text for
  "curtail").** The separate Grid-India "Daily VRE report" (NLDC REMC report, FileType DAILY_VRE_REPORT, 632
  files 2024-11 → 2026-11) gives VRE forecast vs actual and max wind/solar penetration by region; not parsed here
  (left to the curtailment collector).

### 2. Hourly / 15-min all-India series
* Best official source found: the **"TimeSeries" sheet of the Daily PSP xls** (and last page of the PDF): "15 Min
  (INSTANTANEOUS) ALL INDIA GRID FREQUENCY, GENERATION & DEMAND MET (SCADA DATA)": demand met, storage demand
  (PSP+BESS), nuclear, wind, solar, hydro, gas, thermal, storage generation, others, net demand met (= demand − wind
  − solar, as printed), total generation, net transnational exchange, frequency. 96 values/day.
* It **first appears on 2024-11-04** (checked: 2022-23 and earlier xls/pdf have no such sheet/page). So the official
  15-min series covers 2024-11-04 → 2026-11-02 only. `hourly_india.csv` keeps the native 15-min instantaneous values
  (granularity `15min`) rather than inventing hourly averages.
* Columns: geography, period_start, period_end, granularity, demand_met_mw, net_demand_met_mw, solar_mw, wind_mw,
  hydro_mw, thermal_mw, gas_mw, nuclear_mw, storage_demand_mw, storage_gen_mw, others_mw, total_generation_mw,
  net_transnational_mw, frequency_hz, source_id, notes.
* DERIVED (by me): `profile_by_month_derived.csv` = mean over the month's days of each 15-min slot (demand, solar,
  wind, net load = demand − solar − wind, VRE share, thermal, hydro); `vre_extremes_derived.csv` = rankings.

### 3. Monthly / FY / state RE generation
* CEA "Monthly Report of Renewable Generation" (GEN-CEA-RE-MONTHLY): 64 Excel reports (2020-09 → 2026-09, gaps
  2020-10, 2022-01 [Hindi file], 2023-02, 2026-01..05, 2026-07) parsed for (a) the all-India overview (month,
  same month last year, April-to-date for current and previous FY) and (b) the "Source Wise" state sheet (state x
  source, current month and same month previous year). PDFs used for the all-India overview only, where no Excel
  exists and the PDF is in the 7-category layout (2019-08 → 2020-07, 2023-02, 2026-01..03, 2026-05, 2026-07);
  current/previous column order is resolved by the printed % column. 2016-04 → 2019-07 PDFs are in other layouts
  and were **not** parsed.
  - Monthly value rule: the value printed for the report's own month is used; if no report for that month was
    parsed, the "same month previous year" column of the report 12 months later is used (flagged in notes).
  - FY totals = April-March cumulative column of March reports (or previous-FY column of the next March report).
  - "Total" before 2023-07 = RE excl. large hydro; from 2023-07 CEA includes large hydro (labelled
    `gen_re_total_incl_large_hydro` vs `_excl_`). Large hydro excludes imports from Bhutan.
  - Anomaly: the 2023-10 report's state sheet shows Large Hydro = 0 for every state although its overview gives
    11,240 MU; those state rows were dropped and the 2024-10 report's previous-year column is used instead.
* Ember (GEN-EMBER-*): India monthly (2019-01 → 2026-09) and yearly (calendar 2010-2025) from Ember's global
  releases (TWh, shares incl. coal, gas, nuclear, hydro, bioenergy, solar, wind, net imports, total generation,
  demand); Ember India state dataset (monthly 2019-01 → 2025-11, yearly 2019-2024; GWh and % shares by fuel; GWh
  recorded as MU). Ember values are recorded exactly as published (TWh not converted).

### 4. Demand history and projections
* CEA monthly Power Supply Position reports, Energy (2013-01 → 2026-08) and Peak (2013-01 → 2026-08;
  parsed rows from 2015 for peak), state/region/All-India, month and April-to-date. FY values = March reports'
  cumulative columns (`demand_fy.csv`; peak = FY maximum). Pre-2016-17 reports use "Availability" and
  "Surplus/Deficit(-)" (kept as `energy_availability`, `energy_surplus_deficit`); FY 2016-17 reports print "energy
  not supplied" with a negative sign (kept as printed, flagged in notes).
* CEA LGBR 2026-27: all-India energy requirement & peak demand FY 2015-16 → 2025-26 (actual) and 2026-27
  (anticipated) from the executive-summary charts, plus the anticipated 2026-27 regional table.
* CEA NEP 2022-32 Vol I (May 2023): 20th EPS projections (Table 4.2: regions & All India, 2021-22 / 2026-27 /
  2031-32) and likely source-wise gross generation 2026-27 & 2031-32 (Tables 5.11-5.12).
* Grid-India monthly operational report Sep-2026: "All Time Highest" demand/energy/hydro/wind/solar records by region.

## Key findings
1. Record demand: all-India max demand met **270,820 MW on 2026-05-21** (solar hours; Grid-India record table and PSP);
   non-solar-hour record 253,294 MW on 2026-05-22. CEA monthly peak May-2026 270,832 MW.
2. FY peak demand (CEA LGBR 2026-27): 153,366 MW (2015-16) → 243,271 (2023-24) → 249,856 (2024-25) → **245,444 MW in
   2025-26 (only y/y decline in the 2015-16→2025-26 series, −1.8%)**; 2026-27 anticipated 271,643 MW (already reached in May 2026).
3. FY energy requirement: 1,114,408 MU (2015-16) → 1,693,959 (2024-25) → 1,707,493 MU (2025-26, +0.8%); 2026-27
   anticipated 1,886,625 MU. Energy not supplied fell from 2.1% deficit (2015-16) to 508 MU in 2025-26 (printed 0.0%; ≈0.03% derived).
4. NEP/20th EPS projected 277,201 MW and 1,907,835 MU for 2026-27, 366,393 MW and 2,473,776 MU for 2031-32.
5. CEA RE generation FY 2025-26: solar **174,757 MU** (2019-20: 50,131; ×3.5), wind 106,700 MU (+28% y/y),
   RE excl. large hydro 310,585 MU, incl. large hydro 477,789 MU.
6. Ember (calendar): wind+solar share 3.0% (2015) → 11.0% (2024) → **14.4% (2025)**; solar 194.6 TWh = 9.4% in 2025;
   coal 70.9% (2025; lowest since 2011's 67.9%). Monthly W+S peak 21.8% (Jun/Jul 2026).
7. PSP daily: solar gen record **737.7 MU on 2026-10-03**; wind record 784.3 MU on 2026-07-12; energy met record
   6,002 MU on 2026-07-16. Highest printed daily RES share in total generation 23.6% (2026-07-12).
8. 15-min (derived): highest solar+wind share of demand **42.8% at 12:00 on 2026-10-10** (solar 93,695 MW, wind
   9,917 MW, demand 241,914 MW); highest solar 93,912 MW (2026-10-10 11:45).
9. Lowest net load (demand − solar − wind) **107,555 MW at 13:30 on 2025-10-30** (demand 165,362 MW); minima cluster
   at 13:00-14:15 in Oct-Nov and Mar-Apr (derived ranking).
10. Typical-day shape (derived means): Oct-2026 net load bottoms ~139,700 MW at 13:15 and peaks ~219,400 MW at 18:45
    (≈80 GW evening ramp); May-2026 bottom 142,400 MW (11:15) vs 216,900 MW (22:45).
11. Wind is strongly seasonal: CEA wind 17.8-18.5 TWh/month in Jul-Aug 2026 vs ~5.5 TWh in Mar 2026; solar peaks
    Mar-May (21.6 TWh May 2026).
12. State RE (CEA, FY 2025-26 Apr-Dec): Rajasthan solar 43.9 TWh (largest); Gujarat leads wind 26.6 TWh, Tamil Nadu
    21.7 TWh.
13. No RE curtailment field in Daily PSP reports (any year).

## Caveats
* PSP "Solar Gen" = RLDC (ISTS) + SLDC (embedded) data; footnote says visibility of embedded/rooftop solar is limited,
  so PSP solar (and the 15-min solar series) understate total solar incl. rooftop. CEA RE reports and Ember differ
  from PSP for the same reason (CEA counts SLDC/utility data; Ember includes estimates).
* PSP energy met / demand met are grid (utility) figures; captive generation is not included.
* Evening-peak hour changed over time (20:00 in 2017 reports, 19:00 later) — see `notes` for each value's report.
* PSP time-of-day values (`time_*`) are text HH:MM in the `value` column (unit "HH:MM (IST)").
* State names: PSP abbreviations mapped to full names; non-state entities kept as named (DVC, Essar Steel / AM-NS
  India, ISTS bulk consumers, Railways). J&K reported as "J&K(UT) & Ladakh(UT)" from 2019-11 → mapped to
  "Jammu and Kashmir and Ladakh". DNH and DD merged (DNHDDPDCL) from 2020-21.
* CEA RE state values flagged `*` in source are provisional (carried from an earlier report).
* Ember calendar-year vs CEA/Grid-India fiscal-year (Apr-Mar) — not directly comparable.
* Derived files (`*_derived.csv`) are computed by me (means / rankings), not published numbers.

## NOT AVAILABLE
* Hourly/15-min all-India demand & generation **before 2024-11-04** from an official public source: not found (PSP
  TimeSeries begins then; Vidyut PRAVAH/MERIT show only live/short windows; Grid-India monthly reports carry one
  max-demand day's 15-min curve per month — not collected).
* RE curtailment in Daily PSP: no such field (curtailment left to the curtailment collector; DAILY_VRE_REPORT exists).
* Max demand during solar vs non-solar hours before 2023 (section I not present in earlier reports).
* PSP solar generation before ~Sept 2016; source-wise generation (section G) before 2017; time of max demand before 2019.
* Full daily PSP for 2015-2018 (sampled only, by instruction to prioritise 2019+); 2016 and 2018 thinly covered.
* CEA monthly RE by source before 2018-08 (2016-04 → 2019-07 PDFs downloaded but in other layouts, not parsed);
  CEA FY RE totals for 2016-17 and 2017-18; CEA state-wise RE for months without Excel (2016-2020-08, 2026-01..05, 07).
* CEA conventional (coal/gas/nuclear) generation monthly — not collected from CEA; use Ember (all sources) or PSP
  section G (daily gross generation by source, 2017+).
* 20th EPS report itself (only NEP's reproduction of its projections); state-wise EPS (NEP Annex 4.1/4.2 not parsed).
* Grid-India daily PSP on 2024-12-30 (xls 404) and ~6 other dates (missing upload.pdf links).

## Re-running
```
myproxy run .venv/bin/python -I scripts/generation_demand/gi_list_files.py DAILY_PSP_REPORT
myproxy run .venv/bin/python -I scripts/generation_demand/gi_download.py DAILY_PSP_REPORT [--range A B] [--days 01,08]
.venv/bin/python -I scripts/generation_demand/psp_parse.py --workers 3
.venv/bin/python -I scripts/generation_demand/build_psp.py
.venv/bin/python -I scripts/generation_demand/build_hourly.py
.venv/bin/python -I scripts/generation_demand/cea_list.py data/raw/generation_demand/cea/dv_*.html > data/raw/generation_demand/cea/cea_listing.csv
myproxy run .venv/bin/python -I scripts/generation_demand/cea_download.py 10068|10010|10011|10003 pdf|excel
.venv/bin/python -I scripts/generation_demand/cea_re_parse.py
.venv/bin/python -I scripts/generation_demand/cea_re_pdf_parse.py
.venv/bin/python -I scripts/generation_demand/cea_psp_parse.py
.venv/bin/python -I scripts/generation_demand/demand_docs_parse.py
.venv/bin/python -I scripts/generation_demand/build_gen.py
```
(Ember CSVs: plain `curl` from files.ember-energy.org — URLs in the source register.)
