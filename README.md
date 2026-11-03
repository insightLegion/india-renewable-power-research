# India: renewable expansion, curtailment and near-zero power prices — data pack

Compiled 3 Nov 2026. Everything lives in B2: `s3://s1d-labs-trideep/from-box/india-renewable-power-research/`

| Folder | Contents |
|---|---|
| `outputs/india_re_curtailment_data.xlsx` | 45 curated datasets (one sheet each) + `source_register` + `README` sheet (index) |
| `outputs/source_register.csv` | 470 sources: organisation, title, URL, publication date, accessed date, period, granularity, units |
| `outputs/dataset_index.csv` | every processed dataset: bucket key, rows, columns, sheet name |
| `outputs/graphs/` | graph1–3 as PNG and SVG |
| `processed/<topic>/` | all clean CSVs (block-level files >150k rows are CSV-only) |
| `raw/<topic>/` | original downloads (PDF/XLS/JSON): ~6,500 files, ~8 GB |
| `notes/<topic>.md` | method, caveats and NOT AVAILABLE list per topic |

## In this git repo

| Path | Contents |
|---|---|
| `data/processed/<topic>/` | all processed CSVs; files over 20 MB are gzipped (`.csv.gz`; pandas reads them directly) |
| `sources/`, `outputs/source_register.csv` | source registers (per topic / merged) |
| `notes/` | method, caveats, NOT AVAILABLE list per topic |
| `outputs/` | Excel workbook, dataset index, graphs (PNG/SVG) |
| `discovery.md` | investigative analysis: anomalies and links across the datasets |
| `scripts/` | collection, parsing, graphs, workbook, zip, analysis code |

Raw source documents (~8 GB PDFs/XLS) are too large for GitHub. They are in the bucket under `raw/` and in the
full zip under `zip/`.

Topics: `prices`, `capacity_storage`, `generation_demand`, `curtailment_forecast`, `transmission`.
Every data row carries a `source_id` that resolves in the register. Values computed by us are marked DERIVED in `notes`.
Code to rebuild: git repo `~/india-renewable-power-research/scripts/`.

## Coverage by indicator

| Indicator | Best series | Granularity / period | Source |
|---|---|---|---|
| Installed solar & wind (GW) | CEA installed capacity reports; MNRE state-wise | monthly 2017-01→2026-09 (March-only 2014–2016); state snapshots 2024–2026 (+ top-5 states 2015–2025) | CEA, MNRE, PIB, Ember |
| RE generation (MU) | Grid-India daily PSP; CEA monthly RE generation; Ember | daily 2013→2026-11 (2015–18 sampled 4 days/month); monthly 2018-08→2026-09; state-wise | Grid-India, CEA, Ember |
| Curtailment (MU) | Grid-India Daily VRE report Sections 8 & 9 | daily by state / pooling station, 2025-01→2026-11; reasons text | Grid-India; CERC/APTEL cases; Ember, JMK, CREA |
| DAM / RTM prices (₹/kWh) | IEX market snapshot API | 15-min: DAM 2012-04→2026-11, RTM 2020-06→, GDAM 2021-10→; DAM area prices | IEX; CERC MMC reports |
| Demand (MW) | Grid-India PSP 15-min SCADA sheet | 15-min 2024-11-04→2026-11-02; daily peak 2013→; FY 2015-16→ | Grid-India, CEA LGBR/NEP |
| Forecast errors | Grid-India VRE report schedule vs actual (derived) | daily, regional/state, 2025→ | Grid-India; CERC DSM regulations |
| Transmission & congestion | CEA transmission progress; Grid-India TTC/ATC, constraint reports, T-GNA margins; IEX/CERC congestion | monthly 2015→2026-09; T-GNA Nov 2025→Oct 2026 | CEA, Grid-India, IEX, CERC |
| Battery storage (MW/MWh) | CEA BESS status reports | monthly May→Sep 2026 + Mar 2025; pipeline by status | CEA, MNRE/PIB, Mercom, JMK |

## Key findings (each traceable in the datasets)

1. **Expansion.** Solar went from 2.6 GW (Mar 2014) to 171.1 GW (30 Sep 2026); wind from 21.0 to 59.2 GW (CEA). FY2025-26 added a record 44.6 GW of solar. Wind+solar were 14.4% of generation in 2025 and peaked at 21.8% in Jun–Jul 2026 (Ember).
2. **Generation kept pace with capacity.** Solar output per GW installed has held at about 19% a year since 2022 (derived). Monthly solar CF in mid-2025 and mid-2026 is the lowest since 2018; curtailment and under-metered rooftop solar both contribute.
3. **Midday surplus.** On 30 Oct 2026, net load (demand minus wind and solar) fell to 107.6 GW at 13:30. In an average October 2026 day the evening ramp is about 80 GW (Grid-India 15-min data, derived).
4. **Near-zero prices.** CERC's bid floor is ₹0/kWh and the cap ₹10/kWh. DAM blocks clearing at ≤ ₹1/kWh by year:
   - 2023: 5
   - 2024: 375
   - 2025: 1,443 (1,329 of them in 09:00–17:00)
   - 2026 to 4 Nov: 1,055
   RTM cleared at exactly ₹0 in 21 blocks on 1 May, 5 Jul and 27 Oct 2026. DAM's lowest was ₹0.021/kWh (31 May 2026). Low prices in 2015–17 also happened, but mostly at night. Solar-hour prices have been below other hours every year since 2021, and the gap widened from ₹0.85 to ₹4.24/kWh in 2026. In solar hours, DAM sell bids reached up to 6× buy bids (Oct 2025).
5. **Curtailment.** An official series exists only from Jan 2025. Derived monthly totals peak at 952 MU in Oct 2025 (5.1% of the wind+solar output the reports cover); the worst day was 140.8 MU on 2 May 2026. Most is "Emergency TRAS down" for grid security in solar hours. Analyst totals differ: Ember puts FY2025-26 at 2.1 TWh against our 3.2 TWh.
6. **Grid constraints.** Line additions fell from 28,114 ckm (FY16) to 8,830 ckm (FY25, 58% of target). Rajasthan's renewable-zone lines are 16–21 months late. At 30 Oct 2026, 10.0 GW in Rajasthan and 8.9 GW at Khavda were connected without firm access (GNA), with midday T-GNA headroom as low as 0–0.4 GW. Exchange congestion, by contrast, is low: 0.1–4% of DAM blocks since FY21.
7. **Storage is small but surging.** Operational BESS was 0.2 GWh (Mar 2025) and 14.5 GWh (Sep 2026, CEA); 79 GWh is under construction. 14.5 GWh is about 10% of the worst curtailment day. Pumped storage is 7.4 GW. NEP requires 82 GWh by 2026-27 and 411 GWh by 2031-32.

## Not available (searched, not found or not published)

- **Curtailment:** no official national or state series before Jan 2025; no MU figure for capacity held back under T-GNA limits; no official Tamil Nadu wind curtailment figures for 2017–19; no final CERC orders on the 2025–26 curtailment petitions.
- **Forecasting:** no official forecast-accuracy statistics (MAPE/NRMSE) from Grid-India or SLDCs, even though IEGC 2023 requires them. Only our derived schedule-vs-actual is available.
- **Demand:** no official 15-min or hourly all-India series before 4 Nov 2024. PSP solar data starts around Sep 2016.
- **Prices:** no DAM data before Apr 2012; no RTM area prices; no PXIL/HPX block data; no mapping of bid areas to states.
- **Capacity:** the MNRE "Physical Progress" page and its archive were not collected (the site requires a key embedded in its page code, and that access was refused by the permission check); CEA was used instead. Solar sub-category splits before 2024 and state-wise wind before Mar 2024 (except the top-5 states) are missing.
- **Storage:** no official BESS history before 2025 and no project/state list; trackers disagree (Mercom 9.3 GWh vs JMK ~1.8 GWh grid-scale).
- **Transmission:** no Green Energy Corridor I/II or ISTS progress after Jun 2024; IEX no longer names congested corridors.
- **Generation:** CEA monthly RE generation before Aug 2018 and FY 2016-17/2017-18 were not parsed (different PDF layout).
- **Ember data artifact:** Ember's 2019 solar generation (37.45 TWh) repeats its 2018 value, while CEA's FY2019-20 figure is 50.1 TWh.
