"""Build the curtailment_forecast deliverables.

Inputs : data/processed/curtailment_forecast/remc_daily_curtailment.csv, remc_daily_profile.csv, remc_daily_parse_log.csv
         (from 02_parse_remc_daily.py) + values hand-read from documents (listed below with quotes).
Outputs: sources/curtailment_forecast_sources.csv
         data/processed/curtailment_forecast/curtailment_events.csv
         data/processed/curtailment_forecast/curtailment_timeseries.csv      (derived from Grid-India daily REMC reports)
         data/processed/curtailment_forecast/forecast_errors.csv            (derived schedule-vs-actual metrics + documented values)
         data/processed/curtailment_forecast/forecasting_rules_timeline.csv
Run: .venv/bin/python -I scripts/curtailment_forecast/04_build_outputs.py
"""
import csv
import os

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "data", "processed", "curtailment_forecast")
ACCESSED = "2026-11-03"

# ---------------------------------------------------------------- source register
SOURCES = [
    ("CUR-001", "Grid Controller of India (Grid-India) / NLDC", "NLDC Renewable Energy Management Centre (REMC) daily report ('Daily VRE Report')",
     "https://grid-india.in/en/reports/daily-vre-report (files: https://webcdn.grid-india.in/files/grdw/YYYY/MM/DD.MM.YYYY_NLDC_REMC_REPORT_*.pdf; listing API POST https://webapi.grid-india.in/api/v1/file {_type: DAILY_VRE_REPORT})",
     "daily", "2025-01-01 to 2026-11-02 (as listed)", "daily", "MU, MW, %",
     "Section 2/4 REMC-monitored regional/state wind & solar installed & available capacity, schedule, actual, deviation (MU), CUF; Section 8 'VRE Curtailment Details' (state / ISTS pooling station, max MW, MU, reason); Section 9 'Emergency TRAS Down in VRE' (from ~mid-2025)",
     "PDF", "Based on SCADA operational data. Excludes rooftop/off-grid solar. Section 9 only exists in later reports. Parsed by scripts 01/02."),
    ("CUR-002", "POSOCO (now Grid-India) / NLDC", "Report on Renewable Energy Curtailment in Tamil Nadu (01.03.2017 to 30.06.2017) in compliance to APTEL order dated 26.08.2020 in Appeal No. 197/2019",
     "https://webcdn.grid-india.in/files/grdw/2025/04/Report-in-APTEL-by-POSOCO-in-Appeal-No-197-of-2019_R1_754.pdf",
     "2020 (posted on grid-india.in 2025-04-28)", "2017-03-01 to 2017-06-30", "monthly / 15-min blocks", "MU, %, blocks",
     "Estimated solar curtailment by developer and month; share of curtailed blocks justified by grid security; monthly average solar/wind curtailment %", "PDF",
     "Covers 16 of 56 solar generators (1052 MW) that submitted data."),
    ("CUR-003", "Appellate Tribunal for Electricity (APTEL)", "Judgment in Appeal No. 197 of 2019 & IA No. 1706 of 2019 (NSEFI v. TNERC, TANGEDCO & TNSLDC), dated 2 August 2021",
     "https://webcdn.grid-india.in/files/grdw/2025/04/APTEL-order-on-RE-curtailment_478.pdf", "2021-08-02", "2017-03-01 to 2017-06-30 + prospective", "event", "% of PPA tariff",
     "Compensation for curtailment for reasons other than grid security", "PDF", "Copy hosted on grid-india.in 'RE Curtailments' page."),
    ("CUR-004", "Grid-India / NLDC", "Margin under T-GNA for the Evacuation of Renewable Generation from ISTS RE Complexes (periodic statements)",
     "https://grid-india.in/en/operations/margin-under-tgna (59 PDFs, Nov 2025 - Oct 2026; e.g. https://webcdn.grid-india.in/files/grdw/2026/11/Margin_T-GNA_ISTS%20RE_30%20October%202026_688.pdf)",
     "2025-11-20 to 2026-11-02", "2025-11 to 2026-10", "snapshot by time-of-day", "MW",
     "Commissioned/connectivity capacity, capacity with effective GNA, capacity without effective GNA, T-GNA injection limit by time block, limiting constraints", "PDF",
     "Layout changes across documents; values in curtailment_events were read manually from three documents (20 Nov 2025, 31 May 2026, 30 Oct 2026). Automated index in data/raw (unverified)."),
    ("CUR-005", "Grid-India / NLDC", "NLDC Operational Feedback (quarterly) - Jul 2025, Oct 2025, Jan 2026, Apr 2026, Jul 2026",
     "https://grid-india.in/en/reports/quarterly-operational-feedback", "2025-08-05 to 2026-08-03", "2025-04 to 2026-07", "quarterly", "qualitative / MW",
     "Transmission constraints incl. Rajasthan RE complex; congestion during T-GNA processing", "PDF", "Large scanned/PDF files (~45-50 MB each)."),
    ("CUR-006", "Grid-India", "Communication: Low system strength at RE pooling station with grant of non-solar hour connectivity and necessary corrective measures (with SCR annexures)",
     "https://webcdn.grid-india.in/files/grdw/2026/05/GRID-INDIA%20Communication%20_Low%20system%20strength%20at%20RE%20pooling%20Station%20with%20grant%20of%20non-solar%20hour%20connectivity_778.pdf",
     "posted 2026-05-07", "n/a", "snapshot", "MW, SCR", "Short-circuit ratio at RE pooling stations", "PDF", "Letter body is a scan; only annexure tables machine-readable."),
    ("CUR-007", "CERC", "CERC (Deviation Settlement Mechanism and related matters) (Second Amendment) Regulations, 2015 - notification dated 7 Aug 2015 (copy on cbip.org)",
     "https://www.cbip.org/RegulationsData/CERC/CERC_3_Deviation/Amendment-II%20Deviation%20Settlement.pdf", "2015-08-07", "from 2015-11-01", "rule", "%",
     "Wind/solar regional-entity error definition and deviation charge tiers", "PDF", "Copy hosted by CBIP (not cercind.gov.in)."),
    ("CUR-008", "CERC", "CERC (Deviation Settlement Mechanism and Related Matters) Regulations, 2022 (No. L-1/260/2021/CERC dated 14 March 2022)",
     "https://cercind.gov.in/Regulations/168_reg.pdf", "2022-03-14", "commencement date notified separately", "rule", "%", "WS seller deviation bands and charges", "PDF", ""),
    ("CUR-009", "CERC", "CERC (Deviation Settlement Mechanism and Related Matters) Regulations, 2024 (dated 5 Aug 2024; Gazette 21.08.2024)",
     "https://cercind.gov.in/regulations/192-Noti.pdf", "2024-08-05", "from commencement; tightening from 2026-04-01", "rule", "%",
     "WS seller volume limits (VLwS), deviation formula with X factor from 1.4.2026", "PDF", "Amendments: 194 (17 Dec 2024), 199 (25 Jun 2025) - infirm power; not WS bands."),
    ("CUR-010", "CERC", "CERC (DSM and Related Matters) (Third Amendment) Regulations, 2026 (dated 25.08.2026; in force 31.08.2026)",
     "https://cercind.gov.in/regulations/208-notification.pdf", "2026-08-25", "from 2026-08-31", "rule", "", "WS sellers treated at par with general sellers for new projects", "PDF", ""),
    ("CUR-011", "CERC", "CERC (Indian Electricity Grid Code) Regulations, 2023 (No. L-1/265/2022/CERC dated 29.5.2023)",
     "https://cercind.gov.in/Regulations/180-Regulations.pdf", "2023-05-29", "from notified commencement", "rule", "%",
     "Minimum turndown 55% MCR; RE curtailment for minimum inertia; curtailment order under T-GNA/GNA; publication of forecasting errors; RE curtailment reporting", "PDF", ""),
    ("CUR-012", "CERC", "CERC (Indian Electricity Grid Code) (Fourth Amendment) Regulations, 2016 (6 April 2016)",
     "https://cercind.gov.in/2016/regulation/124_1.pdf", "2016-04-06", "", "rule", "% of MCR", "Technical minimum 55% for CGS/ISGS units", "PDF", "Reg. 6.3B in force from date notified by CERC."),
    ("CUR-013", "CERC", "Record of Proceedings, Petition No. 846/MP/2025 (Solaire Surya Urja Pvt Ltd v. RRVPNL & Ors) - hearings 12.5.2026, 30.7.2026, 17.9.2026",
     "https://cercind.gov.in/2026/ROP/846-MP-2025_170926.pdf", "2026-09-17", "", "event", "", "Compensation claim for curtailment by Rajasthan STU/SLDC due to inadequate transmission", "PDF", "No quantities in RoPs."),
    ("CUR-014", "CERC", "Record of Proceedings, Petition No. 26/MP/2026 (Serentica Renewables India-4 Pvt Ltd & Ors v. PGCIL & Ors), hearing 18.3.2026",
     "https://cercind.gov.in/2026/ROP/26-MP-2026_180326.pdf", "2026-03-18", "", "event", "%", "Curtailment under T-GNA due to non-availability of transmission (Bikaner)", "PDF", "Petitioner submission, not a finding."),
    ("CUR-015", "CERC", "Record of Proceedings, Petition No. 171/MP/2024 (NLC India v. Electricity Department Andaman), hearing 24.4.2026",
     "https://cercind.gov.in/2026/ROP/171-MP-2024_240426.pdf", "2026-04-24", "", "event", "", "Must-run breach compensation; Grid-India unable to assess curtailment for lack of data", "PDF", ""),
    ("CUR-016", "Ember", "Beyond capacity: why India's power system must get flexible to harness its solar potential (R. Shah, M. Ewen)",
     "https://ember-energy.org/latest-insights/beyond-capacity-why-indias-power-system-must-get-flexible-to-harness-its-solar-potential/",
     "2026-01-27", "2025-05 to 2025-12", "period", "TWh, %", "Security-led (emergency) solar curtailment", "web", "Analyst estimate based on Grid-India data (chapter cites NLDC REMC reports)."),
    ("CUR-017", "Ember", "Beyond capacity - chapter: Structural and operational factors of renewable energy curtailment in India in 2025",
     "https://ember-energy.org/chapter/structural-and-operational-factors-of-renewable-energy-curtailment-in-india-in-2025/", "2026-01-27", "2025", "daily events", "GWh, GW",
     "Emergency TRAS-down events; transmission-constraint curtailment", "web", "Cites NLDC REMC reports of 25.05.2025 and 12.10.2025."),
    ("CUR-018", "pv magazine (reporting Ember analysis)", "India curtailed 2.1 TWh of renewable electricity in fiscal year 2025-26",
     "https://www.pv-magazine.com/2026/06/17/india-needs-10-gwh-of-battery-storage-to-prevent-renewable-energy-curtailment/", "2026-06-17", "FY2025-26; Apr 2026", "FY / monthly", "TWh, %",
     "Total RE curtailment and share of RE generation", "web", "Secondary report of Ember analysis (analyst, not official)."),
    ("CUR-019", "Down To Earth (reporting Ember)", "India loses 300 GWh renewable energy in 2026 first quarter due to transmission delays (Ember report 'Transmission gaps are beginning to constrain India's rapid renewables integration')",
     "https://www.downtoearth.org.in/energy/india-loses-300-gwh-renewable-energy-in-2026-first-quarter-due-to-transmission-delays", "2026-05-19", "2026-01 to 2026-03", "quarter", "GWh, %",
     "Total ISTS RE curtailment and transmission-constraint share", "web", "Secondary report of analyst estimate."),
    ("CUR-020", "KNN India (reporting JMK Research)", "India curtails 378 MU of renewable energy in September amid grid constraints",
     "https://knnindia.co.in/news/newsdetails/sectors/india-curtails-378-mu-of-renewable-energy-in-september-amid-grid-constraints", "2026-10-22", "2026-09", "monthly", "MU, %",
     "Curtailment by technology, reason (real-time constraints vs Emergency TRAS down) and state", "web", "Analyst (JMK) figures; JMK categories match Grid-India REMC report sections."),
    ("CUR-021", "Business Today (reporting CREA)", "India wastes 4.2 percent of solar power in July-August due to inadequate infra: CREA",
     "https://www.businesstoday.in/india/story/india-wastes-4-2-percent-of-solar-power-in-july-august-due-to-inadequate-infra-crea-561055-2026-10-12", "2026-10-12", "2026-07 to 2026-08", "2 months", "MU, %",
     "RE curtailment total and solar share", "web", "Analyst (CREA Quarterly Energy Snapshot Q2 2026-27); method not stated in article."),
    ("CUR-022", "Construction World (reporting Grid-India presentation to a CEA committee)", "Renewable Curtailment Reaches 23 GW Amid Coal Flexibility Limits",
     "https://www.constructionworld.in/amp/energy-infrastructure/power-and-renewable-energy/renewable-curtailment-reaches-23-gw-amid-coal-flexibility-limits/87201", "2026-02-28", "2025-05 to 2025-11", "event", "GW, %, Hz",
     "Peak RE curtailment, thermal backing down, high frequency", "web", "News quoting an official (Grid-India) presentation; primary CEA committee document not retrieved."),
    ("CUR-023", "Down To Earth (interview with NSEFI)", "Rajasthan curtails 4 GW of solar capacity since March; industry incurs losses of up to Rs 250 crore",
     "https://www.downtoearth.org.in/energy/rajasthan-curtails-4-gw-of-solar-capacity-since-march-industry-incurs-losses-of-up-to-rs-250-crore", "2025-08-20", "2025-03 to 2025-08", "period", "GW, Rs crore, %",
     "Industry claims on Rajasthan curtailment", "web", "INDUSTRY CLAIM (NSEFI), not official."),
    ("CUR-024", "Down To Earth (P. Jhawar)", "Renewable energy: Curtailment is a bane",
     "https://www.downtoearth.org.in/energy/renewable-energy-curtailment-is-a-bane-68857", "2020-01-17", "2012-2019", "period", "%, MU",
     "Industry claims on TN/AP/Karnataka curtailment", "web", "INDUSTRY CLAIMS (NSEFI, TN Spinning Mills Assoc.); article notes curtailment data are not public."),
    ("CUR-025", "Energetica India (reporting CERC order)", "CERC notifies phased X factor reduction for wind and solar, tightens deviation bands from April 2026",
     "https://www.energetica-india.net/news/cerc-notifies-phased-x-factor-reduction-for-wind-and-solar-tightens-deviation-bands-from-april-2026", "2026-04-01", "FY2026-27 to 2031", "rule", "%",
     "X factor trajectory and deviation bands", "web", "Secondary; CERC order itself not retrieved."),
    ("CUR-026", "SolarQuarter (reporting CERC order)", "CERC ensures compensation for Karnataka solar power amid KSLDC curtailment",
     "https://solarquarter.com/2023/11/18/cerc-ensures-compensation-for-karnataka-solar-power-amid-ksldc-curtailment/", "2023-11-18", "pre/post 2 Aug 2021", "event", "% of PPA tariff",
     "Compensation for Karnataka SLDC curtailment (Wardha Solar, Parampujya Solar)", "web", "Secondary; petition number not in article."),
    ("CUR-027", "SCC Online blog", "Compensation rules for curtailing must-run renewable power notified vide Electricity (Promotion of Generation of Electricity from Must-Run Power Plant) Rules, 2021",
     "https://scconline.com/blog/post/2021/10/26/compensation-rules-for-curtailing-must-run-renewable-power-notified-vide-electricity-promotion-of-generation-of-electricity-from-must-run-power-plant-rules-2021",
     "2021-10-26", "from 2021-10-22", "rule", "", "Must-run status, compensation at PPA rate", "web", "Secondary summary; gazette text not retrieved."),
    ("CUR-028", "SCC Online blog / Powerline (secondary)", "CEA (Flexible Operation of Coal based Thermal Power Generating Units) Regulations, 2023 - notified 30.01.2023",
     "https://scconline.com/blog/?p=282841", "2023-01-30", "", "rule", "% of rated capacity", "Minimum power level 40% capability", "web",
     "Secondary (via web search results; regulation PDF on cea.nic.in not retrievable - site restructured)."),
    ("CUR-030", "JMK Research & Analytics", "96.9 GW of Solar and 21.7 GW of Wind Capacity affected by curtailment in September 2026",
     "https://jmkresearch.com/?p=142440", "2026-10", "2026-09", "monthly", "MU, %", "VRE curtailment by technology, reason and state", "web",
     "Analyst; 'Source: Grid-India, JMK Research & Analytics'; reason categories are JMK's interpretation as 'Grid-India does not publish formal definitions'."),
    ("CUR-029", "Mercom India", "CERC admits solar developers' plea for compensation due to power curtailment",
     "https://www.mercomindia.com/cerc-admits-solar-developers-plea-for-compensation-due-to-power-curtailment", "2025-10-06", "2025", "event", "", "Petitions on curtailment due to inadequate transmission", "web", "Paywalled; only headline/lede read."),
]
SRC_COLS = ["source_id", "organisation", "title", "url", "publication_date", "data_period", "granularity", "units", "indicators", "format", "notes"]


def write_sources():
    os.makedirs(os.path.join(ROOT, "sources"), exist_ok=True)
    with open(os.path.join(ROOT, "sources", "curtailment_forecast_sources.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "organisation", "title", "url", "publication_date", "accessed_date", "data_period",
                    "granularity", "units", "indicators", "format", "notes"])
        for s in SOURCES:
            d = dict(zip(["source_id", "organisation", "title", "url", "publication_date", "data_period", "granularity",
                          "units", "indicators", "format", "notes"], s))
            w.writerow([d["source_id"], d["organisation"], d["title"], d["url"], d["publication_date"], ACCESSED,
                        d["data_period"], d["granularity"], d["units"], d["indicators"], d["format"], d["notes"]])


# ---------------------------------------------------------------- curtailment events (hand-read values)
EV_COLS = ["geography", "period_start", "period_end", "granularity", "technology", "curtailed_energy_MU",
           "curtailed_capacity_MW", "curtailment_pct", "other_metric", "other_value", "other_unit", "reason",
           "reason_category", "source_id", "source_type", "notes"]
TN17_MU = {  # POSOCO Table 7a, total estimated curtailment (MU) per developer, Mar-Jun 2017
    "Sei Kathiravan": 0.537, "Welspun Kayathar 49MW": 0.860, "Kamuthi Solar Power": 4.550, "Ramnad Renewable": 1.444,
    "Swelect": 0.175, "Giriraj Enterprises": 1.040, "Adani Green Energy TN": 10.108, "Kamuthi Renewable": 3.418,
    "Ramnad Solar Power": 3.279, "Shapoorji Pallonji": 2.132, "Welspun Panchapatti 50MW": 2.656,
    "Welspun Iyyermalai 50MW": 3.020, "Sei Aditya Shakti": 0.567, "Greenko Kathiravan RTR": 0.242, "Sei Phoebus": 1.032,
    "Sei Adhavan": 0.560}


def ev(**k):
    return {c: k.get(c, "") for c in EV_COLS}


def build_events():
    E = []
    # --- Tamil Nadu 2017 (POSOCO report to APTEL) ---
    E.append(ev(geography="Tamil Nadu", period_start="2017-03-01", period_end="2017-06-30", granularity="period", technology="solar",
                curtailed_energy_MU=round(sum(TN17_MU.values()), 3),
                reason="Backing-down instructions by TNSLDC (oral); POSOCO found only 60 of 1140 curtailed blocks (5.26%) justified on grid-security grounds",
                reason_category="SLDC backing down (non-grid-security / commercial)", source_id="CUR-002", source_type="official (system operator report to APTEL)",
                notes="DERIVED: sum of Table 7a developer totals for the 16 developers (1052 MW) that submitted data; e.g. Adani Green Energy TN 10.108 MU. Not the whole state."))
    for m, s_pct, w_sol, w_non in [("2017-03", 6, 2, 1), ("2017-04", 2, 2, 2), ("2017-05", 2, 6, 3), ("2017-06", 11, 7, 2)]:
        end = {"03": "31", "04": "30", "05": "31", "06": "30"}[m[-2:]]
        E.append(ev(geography="Tamil Nadu", period_start=m + "-01", period_end=f"{m}-{end}", granularity="monthly", technology="solar",
                    curtailment_pct=s_pct, other_metric="wind curtailment % (solar period / non-solar period)", other_value=f"{w_sol} / {w_non}", other_unit="%",
                    reason="TNSLDC backing down", reason_category="SLDC backing down (non-grid-security / commercial)", source_id="CUR-002",
                    source_type="official (system operator report to APTEL)", notes="Table 15 'Month wise Average Solar & Wind Curtailment in %' (sample of reporting generators)."))
    E.append(ev(geography="Tamil Nadu", period_start="2017-03-01", period_end="2017-06-30", granularity="period", technology="solar & wind",
                curtailment_pct=5, other_metric="wind curtailment % (solar period / non-solar period)", other_value="4 / 2", other_unit="%",
                reason="TNSLDC backing down", reason_category="SLDC backing down (non-grid-security / commercial)", source_id="CUR-002",
                source_type="official (system operator report to APTEL)",
                notes="Quote: 'during the said period total average solar curtailment was 5% and wind curtailment is 4% and during non-solar period average wind curtailment was 2 %.'"))
    E.append(ev(geography="Tamil Nadu", period_start="2017-03-01", period_end="2017-06-30", granularity="period", technology="solar",
                other_metric="curtailed 15-min blocks analysed / blocks justified by grid security", other_value="1140 / 60", other_unit="blocks",
                reason="Grid security justified only in 5.26% of curtailed blocks", reason_category="SLDC backing down (non-grid-security / commercial)",
                source_id="CUR-002", source_type="official (system operator report to APTEL)",
                notes="Quote: 'only 5.26% (60 out of 1140 blocks) appears to be justified from grid security perspective'. Also: 'most of the solar generators with per unit cost of Rs 7.01 is curtailed more'."))
    E.append(ev(geography="Tamil Nadu", period_start="2017-03-01", period_end="2017-06-30", granularity="event", technology="solar",
                other_metric="compensation rate", other_value="75 (for 1080 blocks); 100 prospectively", other_unit="% of PPA tariff",
                reason="Curtailment for reasons other than grid security", reason_category="regulatory/compensation",
                source_id="CUR-003", source_type="judicial (APTEL)",
                notes="Quote: 'pay compensation for 1080 blocks considered by POSOCO ... other than grid security, at the rate of 75% of PPA tariff per unit'; '(ii) As a deterrent, the curtailment of Renewable Energy for the reasons other than grid security shall be compensated at PPA [tariff]'."))
    # --- industry claims (pre-2020) ---
    E.append(ev(geography="Tamil Nadu", period_start="2012-01-01", period_end="2015-12-31", granularity="period", technology="wind", curtailment_pct="30-35",
                reason="Wind not evacuated by state utility in peak season", reason_category="SLDC backing down (unspecified)", source_id="CUR-024",
                source_type="industry claim", notes="Anonymous TN Spinning Mills Association official: 'averaged around 30-35 per cent of generation in peak season during 2012-15'; 'it averages at 20-25 per cent currently' (2020)."))
    E.append(ev(geography="Andhra Pradesh", period_start="2019-07-01", period_end="2019-10-31", granularity="period", technology="solar", curtailment_pct="60-70",
                reason="Backing down by AP SLDC/discoms", reason_category="SLDC backing down (commercial, alleged)", source_id="CUR-024",
                source_type="industry claim", notes="NSEFI letter to MoP (Oct 2019): 'continuous curtailment to the order of 60-70 per cent since July 2019'."))
    E.append(ev(geography="Karnataka", period_start="2019-06-01", period_end="2019-06-30", granularity="monthly", technology="solar",
                other_metric="average curtailment hours per day", other_value=9, other_unit="hours/day",
                reason="SLDC curtailment", reason_category="SLDC backing down (unspecified)", source_id="CUR-024", source_type="industry claim",
                notes="NSEFI data for Nalwar project (Wardha Solar): 'average curtailment of nine hours daily'. CERC later ordered KSLDC to compensate (CUR-026)."))
    E.append(ev(geography="Karnataka", period_start="", period_end="2023-11-18", granularity="event", technology="solar",
                other_metric="compensation rate", other_value="75 (pre-2 Aug 2021) / 100 (post)", other_unit="% of PPA tariff",
                reason="CERC: curtailment by KSLDC 'was not solely due to grid security reasons' (Grid-India analysis)", reason_category="regulatory/compensation",
                source_id="CUR-026", source_type="regulatory (CERC order, via news)", notes="Petitioners Wardha Solar (Maharashtra) and Parampujya Solar; 9% interest; payable within 60 days."))
    E.append(ev(geography="India", period_start="2020-03-25", period_end="2020-05-31", granularity="period", technology="solar", curtailed_energy_MU=323,
                reason="Low demand during COVID-19 lockdown", reason_category="low demand / grid security", source_id="CUR-023", source_type="industry claim",
                notes="NSEFI CEO: 'Curtailment during the 2020 lockdown amounted to around 323 million units of solar power' (revised from an erroneous earlier figure; period boundaries approximate)."))
    # --- 2025 Rajasthan / national ---
    E.append(ev(geography="Rajasthan", period_start="2025-03-01", period_end="2025-08-19", granularity="period", technology="solar", curtailed_capacity_MW="3000-4000",
                curtailment_pct=48, other_metric="industry losses", other_value=250, other_unit="Rs crore",
                reason="Transmission delays; GNA 14,000 MW vs 22,500 MW commissioned/approved under GNA/T-GNA", reason_category="transmission / T-GNA without transmission",
                source_id="CUR-023", source_type="industry claim",
                notes="NSEFI: 'about 3-4 gigawatts (GW) of solar capacity has been curtailed in Rajasthan'; NSEFI letter to MNRE (24 Jul 2025): 'around 48 per cent curtailment during peak hours'."))
    E.append(ev(geography="India", period_start="2025-05-01", period_end="2025-12-31", granularity="period", technology="solar", curtailed_energy_MU=2300,
                reason="Grid security: low midday demand, coal fleet near 55% minimum thermal load; emergency TRAS down", reason_category="grid security / low demand / thermal must-run",
                source_id="CUR-016", source_type="analyst estimate (Ember, based on Grid-India data)",
                notes="'2.3 TWh' security-led solar curtailment May-Dec 2025; 'Highest daily solar curtailment due to grid-security measures in 2025' = 20%; compensation est. INR 5,750-6,900 million. Excludes transmission-constraint curtailment."))
    E.append(ev(geography="India (ISTS solar)", period_start="2025-05-25", period_end="2025-05-25", granularity="daily", technology="solar", curtailed_energy_MU=45,
                reason="Emergency TRAS down (grid security, high frequency)", reason_category="grid security / low demand / thermal must-run", source_id="CUR-017",
                source_type="analyst (Ember) citing NLDC REMC report", notes="'approximately 45 GWh of ISTS solar output, was curtailed' (Ember citing 25.05.2025 NLDC REMC report)."))
    E.append(ev(geography="India", period_start="2025-05-25", period_end="2025-05-25", granularity="daily", technology="solar", curtailed_capacity_MW="~10000",
                other_metric="max frequency / thermal fleet backed down to", other_value="50.48 Hz / ~58%", other_unit="Hz / %",
                reason="Surplus midday solar; thermal could not go lower", reason_category="grid security / low demand / thermal must-run", source_id="CUR-022",
                source_type="news quoting Grid-India presentation to CEA committee",
                notes="'despite backing down the national thermal fleet to about 58 per cent and curtailing nearly 10 GW of solar through TRAS emergency down dispatch, frequency still rose to 50.48 Hz'."))
    E.append(ev(geography="India", period_start="2025-05-01", period_end="2025-11-30", granularity="period", technology="wind & solar", curtailed_capacity_MW=23000,
                other_metric="May 2025 share of time frequency above IEGC band (49.90-50.05 Hz)", other_value="~20", other_unit="%",
                reason="Surplus midday solar; intra-state thermal units unable to run at 55% technical minimum; ~60 GW evening ramp", reason_category="grid security / low demand / thermal must-run",
                source_id="CUR-022", source_type="news quoting Grid-India presentation to CEA committee",
                notes="'peak renewable curtailment of 23 GW between May and November' (events 12 Oct, 9 Nov); >16 GW on 9 Nov; >13 GW on 28 Sep and 1 Jun; >11 GW on 31 May and 10 Aug; min 4.6 GW on 29 Jul (year 2025 implied)."))
    E.append(ev(geography="India (ISTS)", period_start="2025-10-12", period_end="2025-10-12", granularity="daily", technology="solar", curtailed_energy_MU=93.26,
                curtailed_capacity_MW=22246, other_metric="wind TRAS down (MU / max MW)", other_value="2.3 / 473", other_unit="MU / MW",
                reason="Emergency TRAS Down by NLDC (Section 9)", reason_category="grid security / low demand / thermal must-run", source_id="CUR-001",
                source_type="official (Grid-India daily REMC report)", notes="NLDC REMC report for 12-Oct-25, row 'SUM 473 2.3 22246 93.26' (max MW summed across stations, non-coincident). Ember (CUR-017) quotes 'about 93.3 GWh'."))
    E.append(ev(geography="Rajasthan", period_start="2025-10-12", period_end="2025-10-12", granularity="daily", technology="solar", curtailed_energy_MU=3.018,
                curtailed_capacity_MW=1207, reason="Due to High Frequency and heavy underdrawal", reason_category="grid security / low demand / thermal must-run",
                source_id="CUR-001", source_type="official (Grid-India daily REMC report)", notes="Section 8 'VRE Curtailment Details', state (intra-state) RE."))
    # --- FY2025-26 / 2026 analyst totals ---
    E.append(ev(geography="India", period_start="2025-04-01", period_end="2026-03-31", granularity="FY", technology="wind & solar", curtailed_energy_MU=2100, curtailment_pct=1.3,
                reason="All causes", reason_category="mixed", source_id="CUR-018", source_type="analyst estimate (Ember, via pv magazine)",
                notes="'about 2.1 TWh ... curtailed in fiscal year 2025-26' 'equivalent to 1.3% of total renewable generation'; ~10 GWh storage would have avoided it."))
    E.append(ev(geography="India", period_start="2026-04-01", period_end="2026-04-30", granularity="monthly", technology="wind & solar", curtailment_pct=4,
                other_metric="share of down-regulation met by RE curtailment", other_value=37, other_unit="%",
                reason="Coal at minimum technical load (~55%) in >half of midday intervals", reason_category="grid security / low demand / thermal must-run", source_id="CUR-018",
                source_type="analyst estimate (Ember, via pv magazine)", notes="'Peak-hour curtailment had returned to 4% of solar and wind generation by April 2026'; 'Renewable curtailment met 37% of down-regulation that month'."))
    E.append(ev(geography="India (ISTS)", period_start="2026-01-01", period_end="2026-03-31", granularity="quarter", technology="wind & solar", curtailed_energy_MU=470,
                other_metric="of which transmission constraints", other_value=300, other_unit="MU",
                reason="Transmission constraints ~two-thirds", reason_category="transmission / T-GNA without transmission", source_id="CUR-019",
                source_type="analyst estimate (Ember, via Down To Earth)", notes="Also: NR and WR lost ~1.5-2% of potential generation; 30 Mar 2026: ~34 GWh lost 'because of insufficient transmission margins'."))
    E.append(ev(geography="India", period_start="2026-07-01", period_end="2026-08-31", granularity="2 months", technology="wind & solar", curtailed_energy_MU=1835,
                other_metric="solar / wind MU; solar share curtailed", other_value="1462 / 373; 4.2%", other_unit="MU; %",
                reason="Inadequate transmission infrastructure; grid/operational constraints", reason_category="mixed", source_id="CUR-021",
                source_type="analyst (CREA, via Business Today)", notes="Article also: 'April-June: government data show 14% of solar output was held back' (source of 14% not identified). Conflicts with JMK/Grid-India-based monthly totals of a few hundred MU - definitions likely differ."))
    E.append(ev(geography="India", period_start="2026-09-01", period_end="2026-09-30", granularity="monthly", technology="wind & solar", curtailed_energy_MU=378.52, curtailment_pct=1.28,
                other_metric="solar / wind; real-time constraints / Emergency TRAS down", other_value="314 / 64.98; 146.73 / 231.79", other_unit="MU",
                reason="Real-time system constraints (39%) and Emergency TRAS Down (61%)", reason_category="mixed", source_id="CUR-030", source_type="analyst (JMK, from Grid-India data); also reported by KNN (CUR-020)",
                notes="By state: Gujarat 187.76 MU (49.6%), Rajasthan 110 MU (29.1%, all solar), Karnataka 21.07 MU, Tamil Nadu 12.93 MU. Down 43.31% m-o-m; 1.89% share in Aug 2026."))
    # --- T-GNA / connectivity without transmission (Grid-India margin statements, read manually) ---
    E.append(ev(geography="Rajasthan (ISTS RE complex)", period_start="2025-11-20", period_end="2025-11-20", granularity="snapshot", technology="solar & wind",
                curtailed_capacity_MW=4767, other_metric="commissioned / GNA effective / GNA not effective / T-GNA scheduling allowed 10:30-14:30", other_value="23152 / 14590 / 8562 / 3795", other_unit="MW",
                reason="De-rated 400 kV Bhadla line; voltage oscillations; angular stability risk; low voltage in STU network", reason_category="transmission / T-GNA without transmission",
                source_id="CUR-004", source_type="official (Grid-India T-GNA margin statement)",
                notes="DERIVED curtailed_capacity_MW = 8562 - 3795 (T-GNA capacity that cannot be scheduled at peak). 'Status as on: 20th Nov 2025'."))
    E.append(ev(geography="Rajasthan (ISTS RE complex)", period_start="2026-05-31", period_end="2026-05-31", granularity="snapshot", technology="solar & wind",
                curtailed_capacity_MW=5497, other_metric="connectivity / GNA effective / GNA not effective / T-GNA limit 10:45-15:00", other_value="26982 / 21102 / 5880 / 383", other_unit="MW",
                reason="Low SCR at pooling stations; voltage oscillations; N-1 of 765 kV Bikaner lines", reason_category="transmission / T-GNA without transmission",
                source_id="CUR-004", source_type="official (Grid-India T-GNA margin statement)", notes="DERIVED curtailed_capacity_MW = 5880 - 383. Pooling: Fatehgarh I-IV, Bhadla I-III, Bikaner I-II, Ramgarh."))
    E.append(ev(geography="Rajasthan (ISTS RE complex)", period_start="2026-10-25", period_end="2026-10-30", granularity="snapshot", technology="solar & wind",
                curtailed_capacity_MW=3996, other_metric="connectivity / GNA effective / GNA not effective / T-GNA limit 11:00-14:00", other_value="31131 / 21102 / 10029 / 6033", other_unit="MW",
                reason="N-1 non-compliance of ICTs at Bhadla-II; low SCR & voltage oscillations; angular instability risk (Bikaner-Moga); ICT loading at Bhiwani/Moga/Jhatikara", reason_category="transmission / T-GNA without transmission",
                source_id="CUR-004", source_type="official (Grid-India T-GNA margin statement)", notes="DERIVED curtailed_capacity_MW = 10029 - 6033. 'Effective from: 25th Oct 2026'; 338 MW additional injection via BESS."))
    E.append(ev(geography="Gujarat (Khavda ISTS RE complex)", period_start="2026-10-25", period_end="2026-10-30", granularity="snapshot", technology="solar & wind",
                curtailed_capacity_MW=7071, other_metric="connectivity / GNA effective / GNA not effective / T-GNA limit 09:00-17:30", other_value="16621 / 7707 / 8914 / 1843", other_unit="MW",
                reason="Low SCR at 400 kV KPS complex; N-1 of 765 kV Ahmedabad-Navsari; loading of Khavda-II-Lakadia", reason_category="transmission / T-GNA without transmission",
                source_id="CUR-004", source_type="official (Grid-India T-GNA margin statement)", notes="DERIVED curtailed_capacity_MW = 8914 - 1843. Permissible Khavda+Lakadiya limit 9550 MW w.e.f. 25.10.2026."))
    E.append(ev(geography="Southern Region (ISTS RE pooling stations)", period_start="2026-10-25", period_end="2026-10-30", granularity="snapshot", technology="solar & wind",
                other_metric="connectivity / GNA effective / GNA not effective / T-GNA limit (all hours)", other_value="13999 / 8547 / 5452 / 5452", other_unit="MW",
                reason="Injection limited by SR inter-regional export limit (Kudgi-Kolhapur angle, ICT N-1, HVDC Raigarh-Pugalur restrictions)", reason_category="transmission (inter-regional export)",
                source_id="CUR-004", source_type="official (Grid-India T-GNA margin statement)", notes="Koppal, Gadag, Pavagada, Kurnool, Tuticorin, Karur, Pugalur, NP Kunta, Ananthapur, Hiriyur PS."))
    E.append(ev(geography="Rajasthan (ISTS RE complex)", period_start="2025-07-01", period_end="2026-07-31", granularity="event", technology="solar & wind",
                reason="'In case of N-1 contingency of 765kV Bhadla II(PG)-Ajmer(PG) D/C line, RE curtailment would be required to ensure the voltage and angular stability'",
                reason_category="transmission / SPS / N-1 security", source_id="CUR-005", source_type="official (NLDC quarterly operational feedback)",
                notes="Recurring constraint in Operational Feedback Jul 2025 - Jul 2026; remedy: commissioning of planned RE evacuation Phase-II/III system."))
    E.append(ev(geography="Rajasthan (Bikaner, ISTS)", period_start="", period_end="2026-03-18", granularity="event", technology="solar", curtailment_pct=">95",
                reason="Evacuation only via T-GNA due to non-availability of transmission network; delayed connectivity operationalisation", reason_category="transmission / T-GNA without transmission",
                source_id="CUR-014", source_type="regulatory filing (petitioner submission to CERC)",
                notes="Serentica: 'has been subjected to more than 95% curtailment of power during peak solar hours'. Grid-India furnished remedial suggestions to PMO."))
    E.append(ev(geography="Rajasthan (intra-state)", period_start="", period_end="2026-09-17", granularity="event", technology="solar",
                reason="Curtailment/backing down by RRVPNL (STU) & Rajasthan SLDC 'on account of its inadequate transmission system for evacuation of power'",
                reason_category="transmission (intra-state)", source_id="CUR-013", source_type="regulatory filing (CERC petition 846/MP/2025)",
                notes="Pending; next hearing 25.11.2026. No quantities in RoP."))
    E.append(ev(geography="Andaman & Nicobar Islands", period_start="", period_end="2026-04-24", granularity="event", technology="solar+BESS",
                reason="Breach of must-run status (2x10 MW solar + 8 MWh BESS)", reason_category="must-run breach", source_id="CUR-015",
                source_type="regulatory filing (CERC petition 171/MP/2024)",
                notes="Grid-India report (20.4.2026) expressed 'constraint in carrying out a reliable and standard curtailment assessment' for lack of data."))
    df = pd.DataFrame(E, columns=EV_COLS)
    df.to_csv(os.path.join(P, "curtailment_events.csv"), index=False)
    return df


# ---------------------------------------------------------------- time series derived from Grid-India REMC daily reports
def build_timeseries():
    c = pd.read_csv(os.path.join(P, "remc_daily_curtailment.csv"))
    log = pd.read_csv(os.path.join(P, "remc_daily_parse_log.csv"))
    ok = log[log.status == "ok"].copy()
    # QA flags (written back to remc_daily_curtailment.csv)
    implaus = (c.wind_MU > 60) | (c.solar_MU > 60)
    soft = ((c.wind_MU > c.wind_max_MW.fillna(0) * 24 / 1000 + 0.05) | (c.solar_MU > c.solar_max_MW.fillna(0) * 24 / 1000 + 0.05))
    c["qa_flag"] = ""
    c.loc[soft, "qa_flag"] = "MU exceeds max MW x 24h (column misalignment in source; kept)"
    c.loc[implaus, "qa_flag"] = "IMPLAUSIBLE: >60 MU for one entity in a day (likely MW typed in MU column); EXCLUDED from aggregates"
    c.to_csv(os.path.join(P, "remc_daily_curtailment.csv"), index=False)
    c = c[~implaus].copy()
    rows = []
    # daily all-India totals: sum of parsed rows (QA: matches the report's own total row on all but a few days)
    present = {(r.date, sec): bool(r.get(f"{sec}_section_present", 0)) for _, r in ok.iterrows() for sec in ("curtailment", "emergency_tras_down")}
    g = c.groupby(["date", "section"])[["wind_MU", "solar_MU"]].sum()
    files = dict(zip(ok.date, ok.file))
    for (d, sec), r in g.iterrows():
        if not present.get((d, sec)):
            continue
        label = "VRE curtailment (Section 8: state & ISTS)" if sec == "curtailment" else "Emergency TRAS Down in VRE (Section 9: ISTS)"
        for tech in ("wind", "solar"):
            rows.append({"geography": "India", "period_start": d, "period_end": d, "granularity": "daily",
                         "metric": f"{label} - {tech}", "value": round(r[f"{tech}_MU"], 4), "unit": "MU", "source_id": "CUR-001",
                         "notes": f"DERIVED: sum of parsed entity rows (implausible rows excluded); file {files.get(d, '')}"})
    ts = pd.DataFrame(rows)
    # monthly aggregates by geography (state / ISTS station rolled up to state-or-region) - DERIVED
    c["month"] = c.date.str[:7]
    days = ok.groupby(ok.date.str[:7]).date.nunique()
    mrows = []
    for (sec, month), g in c.groupby(["section", "month"]):
        lab = "VRE curtailment (Section 8)" if sec == "curtailment" else "Emergency TRAS Down (Section 9)"
        nd = int(days.get(month, 0))
        y, m = map(int, month.split("-"))
        end = (pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
        for tech in ("wind", "solar"):
            tot = g[f"{tech}_MU"].sum()
            mrows.append({"geography": "India", "period_start": f"{month}-01", "period_end": end, "granularity": "monthly",
                          "metric": f"{lab} - {tech}", "value": round(tot, 3), "unit": "MU", "source_id": "CUR-001",
                          "notes": f"DERIVED: sum of daily parsed rows; {nd} daily reports available in month"})
            for (reg, cat, ent), gg in g.groupby(["region", "category", "entity"]):
                v = gg[f"{tech}_MU"].sum()
                if v and v > 0:
                    geo = ent if cat == "RE State" else f"{reg} ISTS pooling station: {ent}"
                    mrows.append({"geography": geo, "period_start": f"{month}-01", "period_end": end, "granularity": "monthly",
                                  "metric": f"{lab} - {tech}", "value": round(v, 3), "unit": "MU", "source_id": "CUR-001",
                                  "notes": f"DERIVED: sum of daily rows; {nd} daily reports in month; days with >0: {int((gg[f'{tech}_MU'] > 0).sum())}"})
    # DERIVED share: monthly curtailment (S8+S9, wind+solar) / (REMC-monitored actual wind+solar + curtailment)
    prof = pd.read_csv(os.path.join(P, "remc_daily_profile.csv"))
    tot = prof[(prof.entity == "Total (all REMC monitored)") & (prof.source == "Wind+Solar")].copy()
    tot["month"] = tot.date.str[:7]
    act = tot.groupby("month").actual_MU.sum()
    cm = c.groupby("month")[["wind_MU", "solar_MU"]].sum().sum(axis=1)
    for month, cur in cm.items():
        if month in act.index and act[month] > 0:
            y, m = map(int, month.split("-"))
            end = (pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
            mrows.append({"geography": "India", "period_start": f"{month}-01", "period_end": end, "granularity": "monthly",
                          "metric": "VRE curtailment (S8+S9) as % of REMC-monitored wind+solar actual + curtailed", "value": round(100 * cur / (act[month] + cur), 3),
                          "unit": "%", "source_id": "CUR-001",
                          "notes": f"DERIVED: curtailed {cur:.1f} MU / (actual {act[month]:.1f} MU + curtailed); REMC-monitored generation excludes non-REMC states, rooftop; same daily reports for both"})
    out = pd.concat([ts, pd.DataFrame(mrows)], ignore_index=True)
    out.to_csv(os.path.join(P, "curtailment_timeseries.csv"), index=False)
    # reason strings summary for notes
    rs = c[c.reason.notna() & ((c.wind_MU.fillna(0) + c.solar_MU.fillna(0)) > 0)]
    rs.groupby(["section", "reason"]).agg(n_rows=("date", "size"), solar_MU=("solar_MU", "sum"), wind_MU=("wind_MU", "sum")) \
        .sort_values("n_rows", ascending=False).to_csv(os.path.join(P, "remc_curtailment_reasons_summary.csv"))
    return out


# ---------------------------------------------------------------- forecast / schedule errors
def build_forecast_errors():
    p = pd.read_csv(os.path.join(P, "remc_daily_profile.csv"))
    p = p.dropna(subset=["schedule_MU", "actual_MU"])
    p = p[p.schedule_MU > 0]
    p["dev"] = p.actual_MU - p.schedule_MU
    p["month"] = p.date.str[:7]
    rows = []
    for (sec, ent, src, month), g in p.groupby(["section", "entity", "source", "month"]):
        y, m = map(int, month.split("-"))
        end = (pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
        geo = ent.replace("Total (all REMC monitored)", "India (REMC-monitored)")
        n = len(g)
        base = {"geography": geo, "period_start": f"{month}-01", "period_end": end, "granularity": "monthly",
                "technology": src, "horizon": "schedule (day-ahead + revisions) vs actual, daily energy",
                "source_id": "CUR-001"}
        rows.append({**base, "metric": "weighted abs daily energy deviation (sum|A-S|/sum S)",
                     "value": round(100 * g.dev.abs().sum() / g.schedule_MU.sum(), 2), "unit": "%",
                     "notes": f"DERIVED from {n} daily REMC reports ({sec}); daily netting hides intra-day 15-min errors, so this is a lower bound of block-wise error"})
        rows.append({**base, "metric": "net bias (sum(A-S)/sum S)", "value": round(100 * g.dev.sum() / g.schedule_MU.sum(), 2), "unit": "%",
                     "notes": f"DERIVED from {n} daily REMC reports ({sec}); negative = actual below schedule (may include curtailment and under-forecast of clouds)"})
        rows.append({**base, "metric": "mean abs daily deviation / available capacity x 24h", "value": round(
            100 * (g.dev.abs() / (g.available_MW * 24 / 1000)).mean(), 2) if g.available_MW.notna().all() and (g.available_MW > 0).all() else None,
                     "unit": "% of AvC-energy", "notes": f"DERIVED from {n} daily reports; comparable in spirit to CERC AvC-based error but daily, not 15-min"})
    fe = pd.DataFrame(rows)
    fe = fe[fe.value.notna()]
    fe.to_csv(os.path.join(P, "forecast_errors.csv"), index=False)
    return fe


# ---------------------------------------------------------------- rules timeline
RULES = [
    ("2015-08-07", "2015-11-01", "CERC", "DSM (Second Amendment) Regulations, 2015", "wind/solar regional entities",
     "Error % = 100 x (Actual - Scheduled)/Available Capacity per 15-min block; under-injection payable at PPA (fixed) rate for shortfall up to 15% error, +110% of rate for 15-25%, +120% for 25-35%, +130% beyond 35%; over-injection paid at fixed rate up to 15%, 90% for 15-25%, 80% for 25-35%, 70% beyond 35%",
     "+/-15% (first tier)", "CUR-007"),
    ("2016-04-06", "", "CERC", "IEGC (Fourth Amendment) Regulations, 2016 - Reg. 6.3B", "thermal CGS/ISGS",
     "'The technical minimum for operation in respect of a unit or units of a Central Generating Station of inter-State Generating Station shall be 55% of MCR loading' (with compensation for part-load operation)", "55% technical minimum", "CUR-012"),
    ("2021-08-02", "2021-08-02", "APTEL", "Judgment, Appeal 197 of 2019 (NSEFI v TNERC/TANGEDCO)", "RE curtailment compensation",
     "Curtailment for non-grid-security reasons compensated at 75% of PPA tariff for 2017 blocks; prospectively at full PPA tariff 'as a deterrent'", "", "CUR-003"),
    ("2021-10-22", "2021-10-22", "Ministry of Power", "Electricity (Promotion of Generation of Electricity from Must-Run Power Plant) Rules, 2021", "wind/solar/hydro must-run",
     "'A must-run power plant shall not be subjected to curtailment or regulation ... on account of merit order dispatch or any other commercial consideration'; compensation at PPA rate; procurer may let plant sell in power exchange with set-off", "", "CUR-027"),
    ("2022-03-14", "", "CERC", "DSM and Related Matters Regulations, 2022", "WS sellers (regional entities)",
     "Deviation-WS % = 100 x (Actual - Scheduled)/Available Capacity. Over-injection paid back at contract rate up to 5%, 90% of contract rate for 5-10%, nothing beyond 10%. Under-injection: pay back shortfall at contract rate; additional deviation charge zero up to 10%, 10% of normal rate beyond 10%",
     "+/-10% (5% full-rate)", "CUR-008"),
    ("2023-01-30", "2023-01-30", "CEA", "Flexible Operation of Coal based Thermal Power Generating Units Regulations, 2023", "coal units",
     "Flexible operation capability with minimum power level 40% (phased); ramp rates (secondary sources)", "40% minimum power level", "CUR-028"),
    ("2023-05-29", "", "CERC", "IEGC Regulations, 2023", "all",
     "Minimum turndown of regional-entity thermal units 55% of MCR or lower level per CEA flexible-operation regulations; NLDC may curtail wind/solar to maintain minimum inertia; curtailment for grid security: T-GNA transactions first, then GNA; within each, RE (wind/solar/hybrid/RoR) curtailed only after other sources; SLDC/RLDC/NLDC to compute and publish intra-day/day-ahead/weekly/monthly/yearly forecasting errors; RLDC forecasts RE of regional entities; operational reports to include 'Instances and quantum of curtailment of renewable energy'",
     "55% MCR", "CUR-011"),
    ("2024-08-05", "", "CERC", "DSM and Related Matters Regulations, 2024 (Gazette 21.08.2024)", "WS sellers",
     "To 31.03.2026: DWS % on Available Capacity; solar & hybrid VLwS(1) up to 10%, VLwS(2) 10-15%; wind VLwS(1) up to 15%, VLwS(2) 15-20%. Under-injection payable at contract rate within VLwS1, 110% within VLwS2, 200% beyond; over-injection received at contract rate, 90%, zero beyond. From 01.04.2026: denominator = X% of AvC + (100-X)% of schedule; solar/hybrid 5%/5-10%, wind 10%/10-15%",
     "solar 10% -> 5%; wind 15% -> 10% (from 2026-04-01)", "CUR-009"),
    ("2026-04-01", "2026-04-01", "CERC", "Order on 'X' factor under DSM 2024 (as reported)", "WS sellers",
     "X = 100% in FY2026-27, then solar/hybrid 90%, 75%, 55%, 30%, 0% (from 2031); wind 95%, 85%, 65%, 35%, 0%", "solar +/-5%, wind +/-10%", "CUR-025"),
    ("2026-08-25", "2026-08-31", "CERC", "DSM (Third Amendment) Regulations, 2026", "WS sellers",
     "Deviation charges for WS sellers at par with general sellers for bid-route projects with bid/tender dates on or after 01.01.2027 and other projects with COD on or after 01.01.2029", "general-seller bands", "CUR-010"),
]


def build_rules():
    df = pd.DataFrame(RULES, columns=["date_notified", "date_effective", "authority", "instrument", "applies_to", "provision",
                                      "band_or_threshold", "source_id"])
    df.to_csv(os.path.join(P, "forecasting_rules_timeline.csv"), index=False)
    return df


if __name__ == "__main__":
    write_sources()
    e = build_events()
    t = build_timeseries()
    f = build_forecast_errors()
    r = build_rules()
    ids = {s[0] for s in SOURCES}
    for name, d in (("events", e), ("timeseries", t), ("forecast", f), ("rules", r)):
        missing = set(d.source_id) - ids
        assert not missing, (name, missing)
        print(name, len(d))
