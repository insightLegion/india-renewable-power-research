# Discovery: what the data says about India's surplus solar, curtailment and ₹0 power

*Investigative notes, 3 Nov 2026. Every number below is either read from a dataset in this repo or derived from it by
[`scripts/analysis/discovery_analysis.py`](scripts/analysis/discovery_analysis.py) (derived tables in
`data/processed/analysis/`). Source IDs resolve in [`outputs/source_register.csv`](outputs/source_register.csv).
"Derived" means our calculation, not an official statistic.*

---

## The short version

India now regularly produces more electricity at midday than it can use or move, and it shows in three places at once:

- **Prices:** the exchange price collapses to near zero.
- **Curtailment:** Grid-India orders solar and wind plants to back down.
- **The evening:** a few hours later the same market hits its ₹10/kWh ceiling.

Coal plants keep running at about two-thirds of their evening output through all of this. The storage that would move midday power into the evening exists, but at roughly a tenth of the scale the worst days need.

Two things make the problem look smaller than it is:

1. **The reason given for curtailment.** Official reports attribute about 3% of curtailment to transmission. Yet the curtailment is concentrated in exactly the Rajasthan and Khavda complexes that Grid-India's own access reports show to be short of transmission.
2. **Capacity that never appears in the curtailment tables.** Up to 6.7 GW in Rajasthan and 8.9 GW at Khavda is connected but not allowed to inject at midday.

---

## Lead 1: Curtailment and near-zero prices are the same event

When Grid-India curtails the most, the day-ahead market is also flooded with unsold solar.

| Curtailment that day (all India) | Days | Median DAM price, 09:00–17:00 | Days with any DAM block ≤ ₹1/kWh | Median sell/buy bid ratio, solar hours |
|---|---|---|---|---|
| < 1 MU | 264 | ₹2.62/kWh | 4% | 1.9× |
| 10–30 MU | 91 | ₹1.79 | 37% | 3.8× |
| 30–60 MU | 57 | ₹1.34 | 67% | 4.9× |
| > 60 MU | 26 | **₹0.81** | **88%** | **5.5×** |

*592 report days, Jan 2025–Nov 2026; Spearman ρ = −0.64 between curtailment and solar-hour price. Source:
`analysis/daily_curtailment_vs_prices.csv`, derived from CUR-001 and PRC-001.*

Only 2 of the 83 days with ≥ 30 MU curtailed had a solar-hour price above ₹3/kWh (24 Sep and 11 Oct 2026).

**Why it matters:** this is a system-wide surplus, not just isolated local bottlenecks. On the heaviest days the market had more than five times as much solar-hour supply as demand. Plants were still being curtailed while buyers paid ₹0.2–0.8/kWh.

**Open question:** on those days, were the curtailed plants merchant or PPA-backed? Under the Must-Run Rules 2021, RE may be curtailed only for grid security or technical constraints; otherwise compensation is due.

## Lead 2: Coal kept running while solar was switched off

These figures come from Grid-India's 15-minute SCADA data, 4 Nov 2024–2 Nov 2026 (GEN-GI-PSP-DAILY).

On days with more than 60 MU curtailed:

- **Thermal output at midday** (12:00–14:45) was a median of **110 GW**, against **159 GW** in the evening (19:00–21:45). That is 67% of the day's maximum.
- Across every heavy-curtailment day (≥ 30 MU), midday thermal never fell below **63%** of that day's peak.
- The lowest midday thermal in two years of 15-minute data was 88.3 GW, on 2 Nov 2025.
- **Hydro** was also running harder at midday on curtailment days: a median of 18.5 GW against 7.3 GW on no-curtailment days. Monsoon run-of-river and wind arrive together.

The dispatch notes inside Grid-India's daily reports show the operators know this. Gujarat SLDC entries read *"All ISGS & SGS schedule to MTDL, Gujarat system heavy under drwal"* [sic] (MTDL is the minimum technical load of thermal units), and *"system freq 50.31 Hz … instructed to Curtail 15% of wind and 15% of solar"* (30 May 2025). Grid frequency peaked at 50.20 Hz or more on 60% of heavy-curtailment days, against 33% of all days.

**Why it matters:**

- India's thermal minimum is 55% of each unit's rating (Grid Code); the CEA's 2023 flexibility rules aim for 40%. The data suggests the midday floor is set by how many coal units must stay synchronised to meet the evening peak, not by the minimum of any one unit.
- Each GW of coal kept on bars at noon for the 19:00 peak displaces solar.
- The evening ramp on heavy-curtailment days is about 45–50 GW of thermal (derived).

**Ask:** Grid-India / CEA for unit-level on-bar data on these days. How many units were held at minimum load, and how much of that was a "must-run" decision?

## Lead 3: The reason column hides the transmission problem

Grid-India's daily report gives a reason for every curtailment entry. We grouped about 7.1 TWh of entries from Jan 2025 to Nov 2026 by keyword (derived; `analysis/curtailment_by_reason_category.csv`):

| Reason category | MU | Share |
|---|---|---|
| Emergency "TRAS down" ordered by NLDC (Section 9) | 3,429 | 48% |
| Section 9, no reason given | 1,786 | 25% |
| High frequency / state under-drawal / low demand | 1,472 | 21% |
| **Transmission or evacuation constraint named** | **205** | **3%** |
| Other | 189 | 3% |

Where it happens is a different story. The ten biggest curtailed entities are almost all ISTS solar pooling stations in Rajasthan and Gujarat:

- Khavda: 872 MU
- Fatehgarh-2: 579 MU
- Bikaner: 521 MU
- Bhadla-2: 502 MU
- Bhadla: 451 MU
- Bikaner-2: 278 MU
- Fatehgarh-1: 242 MU
- Fatehgarh-3: 207 MU

Gujarat's intra-state curtailment (1,238 MU) is the single largest state line.

These are the same complexes that Grid-India's own T-GNA margin statements (Nov 2025–Oct 2026) show to be short of transmission (TRN sources, `re_complex_tgna_margin.csv`):

| Complex | Connected without firm access (median) | Midday T-GNA headroom (median) | Blocked at the tightest block (median / max) |
|---|---|---|---|
| Rajasthan ISTS RE | 4.7 GW | 0.23 GW | 4.1 GW / **6.7 GW** |
| Khavda ISTS RE | 8.3 GW | 2.8 GW | 4.9 GW / **8.9 GW** |

*Derived: `analysis/tgna_blocked_capacity_derived.csv`.*

Meanwhile the CEA reports the Rajasthan RE-zone ISTS lines running 16–21 months late. Congestion on the power exchange is near zero (0.1–4% of DAM blocks since FY21), so the bottleneck is inside and around the RE complexes, not between regions.

**Why it matters:**

- **Compensation:** the reason label decides who pays. Grid-security curtailment is generally not compensated; curtailment for other reasons is. Labelling stranded-transmission curtailment as "TRAS down / grid security" shifts the cost onto developers. This is the subject of pending CERC petitions 846/MP/2025 (Rajasthan, next hearing 25 Nov 2026) and 26/MP/2026 (Serentica, which claims more than 95% curtailment in peak solar hours under T-GNA).
- **Invisible curtailment:** capacity held back by T-GNA limits is a planned injection limit, not a real-time instruction. It does not appear to be counted as curtailment at all. Official curtailment totals are therefore probably a floor.

## Lead 4: The ₹0 days

The RTM cleared at exactly ₹0/MWh in 21 blocks on three days, all in 2026 (PRC-002; 232 "no-trade" dummy blocks excluded):

| Day | ₹0 blocks | Context (Grid-India 15-min data, derived) |
|---|---|---|
| Fri 1 May 2026 (May Day / Maharashtra Day) | 2 (10:30–10:45) | Demand peak 218.7 GW, against 251.8 GW a week earlier (**−33 GW**); frequency up to 50.35 Hz; the same day's DAM touched the ₹10 cap |
| Sun 5 Jul 2026 | 10 (15:00–17:15) | Demand −25 GW against the previous Sunday; **102 MU curtailed** (85 MU emergency TRAS down); wind in full monsoon |
| Tue 27 Oct 2026 | 9 (12:00–14:00) | Wind + solar peaked at 89.6 GW; frequency up to 50.25 Hz; DAM evening at the ₹10 cap |

The official curtailment report is missing for two of the three days. See Anomaly A1: Grid-India's archive serves the wrong file for 1 May, and has no file for 27 Oct.

**Pattern:** ₹0 needs a demand dip (holiday or Sunday) on top of a high wind+solar day. As capacity keeps growing, ordinary weekdays are starting to qualify (27 Oct was a Tuesday with normal demand).

## Lead 5: The floor-to-cap day is new, and it is the storage business case

These are days when the DAM cleared at ≤ ₹1/kWh at midday and hit the ₹10/kWh cap in the evening (derived from PRC-001):

| Year | Floor-to-cap days | Days with a same-day spread ≥ ₹8/kWh | Median daily spread |
|---|---|---|---|
| 2021 | 0 | 73 | ₹4.34 |
| 2023 | 0 | 73 | ₹7.02 |
| 2024 | 14 | 136 | ₹7.75 |
| 2025 | 45 | 177 | ₹7.97 |
| 2026 (to 4 Nov) | 44 | 227 | ₹8.41 |

Solar-hour prices have been below other hours every year since 2021. The gap widened from ₹0.85 (2021) to ₹4.24/kWh (2026). Discovered BESS costs have fallen from ~₹10.18/kWh (2022-23 bids) to about ₹2.1/kWh (MoP, Dec 2025; CAP-054).

**Storage is arriving, but behind the curve:**

- **What the grid data shows.** Grid-India's 15-minute data began reporting storage in June 2026. Average charging peaks at about 5.2 GW at 12:00 and average discharge at about 3.9 GW at 22:00, with a maximum charge of 7.35 GW. This covers BESS and pumped storage together.
- **Operational BESS (CEA):** 14.5 GWh on 30 Sep 2026. That is about 10% of the worst curtailment day (140.8 GWh, 2 May 2026) and 42% of the NEP BESS requirement for 2026-27 (34.7 GWh; 82.4 GWh including pumped storage, PIB 31 May 2023).
- **VGF subsidy schemes:** 35.1 GWh awarded but **0.5 GWh commissioned** (Jul 2026).

**Ask:** why VGF projects are lagging, and whether ISTS-waiver deadlines (co-located storage commissioned by June 2028; standalone waiver tapering 25% a year since June 2025) are shaping the timing.

## Lead 6: 2025's crisis started with weak demand; 2026's didn't need it

Monthly energy met, year on year (derived from Grid-India PSP):

- **2025 was weak:** May −4.9%, Jun −1.5%, **Oct −6.0%**. FY2025-26 peak demand *fell* 1.8% (245.4 GW against 249.9 GW, CEA LGBR) while FY2025-26 added a record 44.6 GW of solar.
- **October 2025** combined the weakest demand with the record curtailment month (952 MU), the most DAM blocks ≤ ₹1/kWh (313) and a DAM sell/buy ratio of about 6×.
- **2026 demand rebounded** (+11% to +21% YoY from May), with a record 270.8 GW on 21 May 2026. Curtailment stayed high anyway: 722 MU in April, 801 MU in July and 720 MU in August.
- **Wind's share of curtailment** rose from about 5% in 2025 to **31% in July 2026**: monsoon wind is now being curtailed alongside solar.

**Reading:** 2025 could be blamed on a cool, wet year. 2026 shows the surplus is structural. Midday supply growth (wind, solar and monsoon hydro together) is outrunning both demand growth and evacuation capacity.

## Lead 7: Contracts are lagging the build-out

- **Contracts:** renewable implementing agencies (REIAs) held **43.9 GW** of awarded projects (LoAs) without signed power-sale agreements (Sep 2025). Against about 69 GW awarded, only **24.3 GW** of PPAs were signed (Dec 2025) (CAP-047/048).
- **Connections:** more plants are connecting under temporary access (T-GNA) than firm transmission is being built (Lead 3).
- **The green market is short of sellers:** the GDAM sell/buy ratio in solar hours has been below 1 every year since 2022 (0.50 in 2026), while the DAM's is 2.7×. GDAM solar-hour prices sit ₹0.03–0.81/kWh above DAM, depending on the year.

**Open question:** why is surplus green power not flowing into the green market?

---

## Anomalies in the official data

| # | Anomaly | Evidence | Effect |
|---|---|---|---|
| A1 | **Grid-India's VRE report archive serves the wrong files.** The links for 01.05.2026, 02.05.2026 and 03.05.2026 all open the report for 02-May-26. The 30.04.2026 link opens the 24-May-26 report. No report is listed for 26 or 27 Oct 2026. | PDFs in `raw/curtailment_forecast/gridindia/remc_daily/` (page 1: "Report for : 02-May-26"); `remc_daily_parse_log.csv` | The official curtailment record is unobtainable for two of the three RTM ₹0 days (1 May, 27 Oct). Monthly sums for those months are understated. |
| A2 | **Values in MW typed into the MU column, repeated across days.** For example, Bhadla-2 shows "407 MU" and Bikaner-2 "503 MU" of wind curtailment, identically on 28, 29 and 30 Jan 2025. | 79 rows with a `qa_flag` in `remc_daily_curtailment.csv` (17 excluded as impossible) | Points to copy-paste templating in the report. Anyone summing the raw tables overstates January 2025 by more than 1 TWh. |
| A3 | **Analysts disagree on how much is curtailed.** | Ember 2.1 TWh against our 3.2 TWh (FY26); JMK 379 against 490 MU (Sep 2026); CREA 1,835 against 1,520 MU (Jul–Aug 2026) | Totals depend on whether Section 9 is counted and on how missing days are handled. No official annual total is published. |
| A4 | **Battery trackers disagree by up to 5×.** | CEA 9.08 GWh (Jul–Aug 2026); Mercom 9.3 GWh (Jun 2026); JMK/IEEFA about 1.8 GWh "grid-scale" against Mercom 5.9 GWh (both Mar 2026); CEA reported 0.2 GWh in Mar 2025 against 7.5 GWh in May 2026 | Definitions (behind-the-meter vs grid; commissioned vs energised) are not harmonised, and CEA published no series between them. |
| A5 | **The CEA contradicts itself on inter-regional capacity for Mar 2024.** | 112,340 MW (CEA executive summary, Mar-24) against 118,740 MW (CEA, Apr-24) | A 6.4 GW gap within one month. |
| A6 | **Ember repeats its 2018 solar generation for 2019.** | 37.45 TWh in both years; CEA FY2019-20 = 50.1 TWh | 2019 solar capacity factor looks like 13.6% in Ember-based analyses. Flagged on Graph 1. |
| A7 | **The PSP report's printed RE share contradicts its own figures.** | 96.8% on 12 Mar 2024; 8.0% on 3 Sep 2023; 3.1% on 18 Dec 2024 | Printed share fields can't be used without recomputing them. |
| A8 | **Grid-India's T-GNA statements change which pooling stations they cover between issues.** | Rajasthan "commissioned" drops from 24.3 to 20.4 GW in March 2026 when Bikaner-II and Bhadla-III disappear from the list, then returns | Any trend line must be checked against station coverage. Labelled on Graph 3. |
| A9 | **IEX returns placeholder prices for RTM "no-trade" blocks.** | 232 RTM blocks with zero bids show prices of ₹0 or ₹10,000/MWh (mostly 2020-21) | Without filtering, RTM appears to hit ₹0 in 2020-21. It didn't; the first real ₹0 was 1 May 2026. |
| A10 | **Grid-India publishes duplicate PSP reports.** | 50 of 124 missing PSP days since 2019 are files on the site that duplicate the previous or next day | Gaps in the daily series. |
| A11 | **CEA halves its own figure for BESS commissioned in FY2025-26.** | 1,082.6 MWh / 445.35 MW (CEA BESS report as on 31 May 2026) against 574.6 MWh / 193.35 MW (as on 30 Sep 2026) | No explanation is published. Treat historical BESS additions as provisional. |

---

## What we could not establish

- **Curtailment before 2025:** no official national or state series exists, only case files such as the 2017 Tamil Nadu solar case. There, POSOCO found only 5% of curtailed blocks were justified by grid security, and APTEL ordered compensation in 2021.
- **Energy lost under T-GNA limits:** not reported anywhere. Lead 3 gives MW, not MWh.
- **Forecast accuracy:** no official MAPE or NRMSE is published, although IEGC 2023 requires it. Our schedule-vs-actual deviation figure (solar 5.0%, wind 12.2%) is derived from daily energy and includes curtailment.
- **Which plants were curtailed, and who holds their PPAs:** reports list pooling stations, not projects. Linking them to developers needs CERC petition records or RLDC schedules.

## Method notes

- Daily curtailment comes from Grid-India Daily VRE reports, Sections 8 and 9, 592 report days. Prices are IEX 15-minute MCP. System data is Grid-India's 15-minute PSP SCADA sheet (instantaneous values).
- "Solar hours" means 09:00–17:00. The thermal comparisons use 12:00–14:45 for midday and 19:00–21:45 for evening.
- Correlations are Spearman, at daily level.
- The reason categories are a keyword classification (`scripts/analysis/discovery_analysis.py`, section I6), not Grid-India's own taxonomy.
