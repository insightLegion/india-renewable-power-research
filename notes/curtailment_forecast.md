# Curtailment, forecast errors and oversupply — collector notes (topic: curtailment_forecast)

Collected 2026-11-03. Raw files: `data/raw/curtailment_forecast/` (untrusted downloads). Scripts: `scripts/curtailment_forecast/01..04`.
Source register: `sources/curtailment_forecast_sources.csv` (CUR-001 … CUR-030).

## Bottom line on data availability

- **There is an official, consistent daily curtailment series, but only from 1 Jan 2025.** Grid-India/NLDC's daily
  REMC report ("Daily VRE Report", CUR-001) carries Section 8 *VRE Curtailment Details* (state / ISTS pooling
  station, max MW, MU, free-text reason) since at least 1 Jan 2025, and Section 9 *Emergency TRAS Down in VRE*
  (ISTS pooling stations) since mid-2025. We downloaded all 627 reports listed (2025-01-01 … 2026-11-02) and
  parsed them. This is the only official consistent curtailment time series found.
- **No official national curtailment series exists before 2025.** For 2015–2024 there are only case-specific
  official numbers (e.g. POSOCO's report to APTEL on Tamil Nadu Mar–Jun 2017), regulatory filings, and
  industry/analyst claims. SLDCs did not publish curtailment data (Down To Earth 2020 notes data "is not publicly available").
- IEGC 2023 requires operational reports to include "Instances and quantum of curtailment of renewable energy"
  and SLDC/RLDC/NLDC to publish forecasting errors, which is presumably why the REMC sections exist.

## Files

Bucket copies (see "Storage" below); local paths relative to the repo:

| File | Rows | Content |
|---|---|---|
| `data/processed/curtailment_forecast/curtailment_events.csv` | 34 | Hand-read curtailment figures, events, rulings, T-GNA stranded capacity, with reason category, source type and quote |
| `data/processed/curtailment_forecast/curtailment_timeseries.csv` | 2,978 | Long format (conventions columns). Daily all-India MU by section (S8 / S9) × wind/solar; monthly MU by entity (state or ISTS pooling station) and all-India; monthly % share. All DERIVED from CUR-001 |
| `data/processed/curtailment_forecast/remc_daily_curtailment.csv` | 44,505 | Wide: one row per report date × section × entity (region, category, wind/solar MU, max MW, time, reason, layout, qa_flag, file) |
| `data/processed/curtailment_forecast/remc_daily_profile.csv` | 21,219 | Wide: report date × region/state × wind/solar/total: installed MW, available MW, day max MW, schedule MU, actual MU, deviation MU, CUF % |
| `data/processed/curtailment_forecast/remc_daily_parse_log.csv` | 628 | Per-file QA (parsed totals vs report totals, duplicates) |
| `data/processed/curtailment_forecast/remc_curtailment_reasons_summary.csv` | 278 | Free-text reasons with counts and MU |
| `data/processed/curtailment_forecast/forecast_errors.csv` | 2,500 | Monthly schedule-vs-actual metrics by region/state/technology (DERIVED from CUR-001) |
| `data/processed/curtailment_forecast/forecasting_rules_timeline.csv` | 10 | CERC/CEA/MoP/APTEL rules 2015–2026 on deviation bands, technical minimum, must-run, curtailment order |

## Method

1. `01_download_remc_daily.py` (run through `myproxy run`): lists `DAILY_VRE_REPORT` files for FY 2024-25,
   2025-26, 2026-27 via `POST https://webapi.grid-india.in/api/v1/file` and downloads PDFs from webcdn.grid-india.in.
   632 listed, 627 downloaded (5 Jan-2025 listings returned HTTP 404). Manifest: `data/raw/.../remc_daily_manifest.csv`.
2. `02_parse_remc_daily.py`: pdfplumber table extraction. Report date is read from the PDF ("Report for: dd-Mon-yy");
   duplicate dates are skipped. Two table layouts handled: layout A (early 2025: MU wind, MU solar, MW wind, time,
   MW solar, time, reason) and layout B (later: Max MW wind, MU wind, Max MW solar, MU solar, reason).
   QA: parsed station/state rows are summed and compared to the report's own "Total Curtailment"/"SUM" row
   (`remc_daily_parse_log.csv`). Result: on 592 unique report dates the parsed Section 8 sums match the report totals to within 0.01 MU (max 0.38 MU);
   Section 9 within 0.03 MU on average (max 2.1 MU, Apr–Oct 2026 rows with total rows rounded or stations missing).
   36 files were duplicates of another date (date in PDF differs from file title). 17 rows with >60 MU for a single entity in one day
   (Jan 28–30 2025, 19 May 2025, 8 Jul 2026 Neemuch 463.82 MU) are physically implausible (MW typed into the MU column) and are
   flagged `IMPLAUSIBLE` and excluded from aggregates; 62 milder MW/MU inconsistencies are flagged but kept.
   Layout A (Jan–May 2025) column use by operators is inconsistent, so early-2025 values are less reliable.
3. `03_tgna_margin.py`: downloads the 59 Grid-India "Margin under T-GNA" statements (Nov 2025 – Oct 2026).
   Automated parsing proved unreliable because the layout changes; values used in `curtailment_events.csv`
   were read by hand from the 20 Nov 2025, 31 May 2026 and 30 Oct 2026 statements.
4. `04_build_outputs.py`: writes the source register, hand-read events (with quotes), derived monthly
   aggregates, derived forecast-error metrics and the rules timeline.

## Key findings

All MU = GWh. "Derived" = our aggregation of the official daily reports (CUR-001).

1. **Official daily series (CUR-001, derived monthly sums, Section 8 + 9, wind + solar):** Jan–Apr 2025 ≈ 2–51 MU/month
   (Section 9 did not exist yet); May 2025 213; Jun 271; Jul 67; Aug 288; Sep 492; **Oct 2025 952 MU (peak; 5.1% of
   REMC-monitored wind+solar)**; Nov 419; Dec 1; Jan 2026 45; Feb 25; Mar 376; Apr 722; May 491; Jun 493; **Jul 2026 801**;
   Aug 720; Sep 490; Oct 246. FY2025-26 ≈ 3,201 MU; Apr–Oct 2026 ≈ 3,961 MU. Monthly share of REMC-monitored wind+solar
   generation peaks at 5.07% (Oct 2025), 3.35% (Apr 2026), 2.64% (Jul 2026).
2. **Emergency TRAS Down (grid security) dominates:** Section 9 solar May–Dec 2025 = 2,240 MU, matching Ember's 2.3 TWh
   security-led solar curtailment (CUR-016). Free-text reason "TRAS Down from NLDC" alone covers 2,543 MU of solar.
3. **Largest single days (derived):** 2 May 2026 140.8 MU; 15 Aug 2026 112.1; 26 Sep 2026 107.2; 12 Oct 2025 98.6 MU
   (Section 9 ISTS solar 93.26 MU, sum of station maxima 22,246 MW).
4. **Where:** FY2025-26 largest entities: Khavda ISTS 418 MU, Gujarat (intra-state) 360, Fatehgarh-2 334, Bikaner 302,
   Bhadla-2 284 MU. Sept 2026 Gujarat intra-state 197 MU. Northern Region (Rajasthan) ISTS pooling stations together ≈ 1,651 MU in FY2025-26.
5. **Reasons in the reports:** "TRAS Down from/by NLDC" (grid security, high frequency); "Due to high frequency and heavy
   underdrawal" / "To control underdrawal" (state SLDCs during low demand); "NOC has been revised due to transmission
   constraint", line overloading/outages (e.g. 400 kV Bhadla–Bikaner, 765 kV Bikaner–Moga tripping).
6. **T-GNA without transmission (CUR-004, read manually):** Rajasthan ISTS RE complex — 20 Nov 2025: 23,152 MW commissioned,
   14,590 MW with effective GNA, 8,562 MW without; T-GNA scheduling allowed only 3,795 MW 10:30–14:30. 31 May 2026: 26,982 /
   21,102 / 5,880 MW, T-GNA limit **383 MW** 10:45–15:00. 30 Oct 2026: 31,131 / 21,102 / 10,029 MW, limit 6,033 MW
   11:00–14:00. Khavda (Gujarat) 30 Oct 2026: 16,621 MW connectivity, 7,707 GNA, 8,914 without, T-GNA limit 1,843 MW
   09:00–17:30. These GW are stranded at peak hours and probably not counted as MU curtailment in the REMC tables.
7. **Historic official case:** POSOCO report to APTEL (CUR-002): TN solar Mar–Jun 2017, 16 developers (1,052 MW) lost
   ≈ 35.6 MU (derived sum); monthly solar curtailment 6%, 2%, 2%, 11% (avg 5%); wind 4% (solar hours), 2% (non-solar);
   only 60 of 1,140 curtailed blocks (5.26%) justified by grid security. APTEL (2 Aug 2021) ordered 75% of PPA tariff for
   1,080 blocks and full PPA tariff prospectively; CERC applied the same to Karnataka SLDC (Nov 2023).
8. **Analyst totals (not official):** Ember FY2025-26 2.1 TWh (1.3% of RE gen); Ember Q1 2026 470 GWh ISTS, ~300 GWh
   transmission; JMK Sep 2026 378.52 MU (our Grid-India-derived figure: 489.6 MU); CREA Jul–Aug 2026 1,835 MU (ours 1,520 MU).
9. **Oversupply / thermal:** Grid-India told a CEA committee (via news, CUR-022): peak RE curtailment 23 GW (May–Nov 2025),
   25 May 2025 thermal fleet backed down to ~58% and ~10 GW solar curtailed via TRAS yet frequency hit 50.48 Hz; frequency above
   IEGC band ~20% of time in May 2025; intra-state units unable to reach 55% technical minimum. Ember: April 2026 coal at
   minimum load in >50% of midday intervals; RE curtailment met 37% of down-regulation.
10. **Rules:** 2015 DSM amendment: ±15% error band on Available Capacity (first tier); DSM 2022: ±10% (5% at full rate);
   DSM 2024: solar 10%/15%, wind 15%/20% volume limits to 31.03.2026, then solar 5%/10%, wind 10%/15% with X-factor
   (100% FY26-27 → 0% by 2031); DSM 3rd Amendment 2026: new WS projects (bids from 1.1.2027 / COD from 1.1.2029) at par with
   general sellers. Technical minimum 55% (IEGC 2016, IEGC 2023), CEA 2023 flexibility regs 40%.
11. **Schedule-vs-actual (derived, CUR-001):** median monthly weighted absolute daily-energy deviation, India REMC-monitored:
   solar 5.0%, wind 12.2%; states: wind 11–39% (Tamil Nadu 39%, Rajasthan 35%, Maharashtra 28%), solar 9–20%
   (Maharashtra 20%, Madhya Pradesh 13%, Karnataka 12.5%). These are lower bounds of 15-min errors and include curtailment effects.

## Caveats

- Section 8 "VRE Curtailment Details" mixes state (intra-state RE, as reported by SLDCs) and ISTS pooling stations;
  Section 9 "Emergency TRAS Down" covers ISTS stations only. Section 8 and 9 are added as separate metrics; whether
  they overlap is not documented by Grid-India (we treat them as distinct categories, as JMK does).
- Max MW values are per-entity maxima; summing them across entities gives a non-coincident figure.
- Reasons are free text written by operators (e.g. "Due to High Frequency and heavy underdrwal", "TRAS Down from NLDC",
  transmission line overloading). `remc_curtailment_reasons_summary.csv` tabulates them; no official taxonomy exists
  (JMK: "Grid-India does not publish formal definitions").
- Curtailment of T-GNA capacity that is simply not scheduled (because the T-GNA injection limit is near zero at
  peak hours) probably does not appear in the REMC curtailment tables, because nothing is scheduled to curtail.
  The T-GNA margin statements (CUR-004) show the capacity stranded instead; MU totals for this are NOT AVAILABLE.
- Analyst totals disagree strongly (e.g. CREA 1,835 MU for Jul–Aug 2026 vs JMK 378.52 MU for Sep 2026 and our
  Grid-India-derived monthly sums), so definitions differ; do not mix them.
- Forecast "errors" derived here are schedule-vs-actual on **daily energy** at regional/state level from the REMC
  report. The schedule is the generators'/states' (revised) schedule, not an REMC forecast, and actual output is
  reduced by curtailment, so negative bias partly reflects curtailment. Daily netting understates 15-min errors.
- Months with few reports (Feb–Apr 2025) give partial monthly sums; the `notes` column states how many daily
  reports were available in each month.
- PDFs of NLDC Operational Feedback are large (~45–50 MB each, ~240 MB total in data/raw); consider moving them to the
  bucket (`mybucket put`) — left in place pending trideep's decision.

## NOT AVAILABLE (searched, not found or not retrievable)

- Official national/state curtailment time series for 2015–2024 (none published; only case reports).
- Official Grid-India/REMC **forecast-vs-actual** accuracy statistics (MAPE/NRMSE) for wind/solar, despite IEGC 2023
  Reg. requiring publication; Grid-India publishes demand-forecast error pages only. No REMC RE forecast dataset found
  on grid-india.in / webapi.
- SLDC forecasting performance statistics (Karnataka, Tamil Nadu, Gujarat, Rajasthan): not found.
- Academic/agency day-ahead error metrics: the MNRE/NREL/NIWE 2023 VRE-forecasting study (nrel.gov/docs/fy23osti/83949.pdf)
  could not be downloaded (host unresolvable); a 2018 POSOCO presentation ("~10% day-ahead wind error") was seen only
  as a search snippet and is NOT recorded.
- Official Tamil Nadu wind curtailment 2017–2019 figures (only industry claims; IWPA presentation on CEA's old site is gone).
- Grid-India's own 2025 report on Rajasthan/Western solar curtailment: not found as a standalone document; the CEA
  committee presentation (23 GW peak curtailment) is known only via news (CUR-022).
- CERC final orders on 2025 Rajasthan curtailment petitions (pending: 846/MP/2025 next hearing 25.11.2026; 26/MP/2026).
- MWh volumes of curtailment caused by T-GNA without transmission.
- Gazette texts of the MoP Must-Run Rules 2021 and CEA Flexible Operation Regulations 2023 (secondary summaries used).
- IEEFA, CEEW, CPI, Prayas, TERI quantified curtailment estimates: none found in searches (ieefa.org blocks scripted access).

## Storage

Per the project storage rule relayed by the coordinator, raw downloads, processed CSVs, the source register and these notes
are uploaded to the bucket under `from-box/india-renewable-power-research/` (`raw/curtailment_forecast/`,
`processed/curtailment_forecast/`, `sources/`, `notes/`). Local copies were NOT deleted: the box's CLAUDE.md says deleting the
box copy after upload is trideep's call and must be confirmed by trideep directly.
