"""Build data/processed/transmission/re_transmission_plans.csv.

Values below were transcribed from the source documents' text (see source_id) after reading them in this session;
the extracted texts were checked line by line (pdftotext of the PDFs in data/raw/transmission/plans and gridindia).
Also appends: under-construction ISTS TBCB projects (from _tbcb_projects.csv) and RE-complex GNA/T-GNA headline rows
(from re_complex_tgna_margin.csv: first and latest issue).
Columns: geography, period_start, period_end, granularity, scheme, metric, status, target, actual, unit, source_id, notes
"""
import csv, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, "data/processed/transmission")
R = []
def add(geo, ps, pe, gran, scheme, metric, status, target, actual, unit, sid, notes=""):
    R.append(dict(geography=geo, period_start=ps, period_end=pe, granularity=gran, scheme=scheme, metric=metric, status=status,
                  target="" if target is None else target, actual="" if actual is None else actual, unit=unit, source_id=sid, notes=notes))

# ---- CEA: Transmission System for Integration of over 500 GW RE Capacity by 2030 (Dec 2022)
S5 = "TRN-CEA-500GW"
d0, d1 = "2022-11-01", "2030-03-31"
add("India", d0, d1, "snapshot", "CEA 500 GW RE transmission plan", "re_capacity_planned_for_integration_total", "planned", 536924, None, "MW", S5, "Total (RE) incl. 165,943 MW commissioned as on 31.10.2022 and 16,673 MW additional hydro")
add("India", "2022-10-31", "2022-10-31", "snapshot", "CEA 500 GW RE transmission plan", "re_capacity_commissioned_incl_large_hydro", "actual", None, 165943, "MW", S5, "as on 31.10.2022")
add("India", d0, d1, "snapshot", "CEA 500 GW RE transmission plan", "re_capacity_to_integrate_ists_66.5GW_programme", "planned", 57639, None, "MW", S5, "66.5 GW programme; 8.861 GW already commissioned counted in commissioned capacity")
add("India", d0, d1, "snapshot", "CEA 500 GW RE transmission plan", "re_capacity_to_integrate_ists_additional", "planned", 236580, None, "MW", S5, "55.08 GW + 181.5 GW")
add("India", "2022-10-31", "2022-10-31", "snapshot", "CEA 500 GW RE transmission plan", "ists_substation_margin_available_for_re", "actual", None, 33658, "MW", S5, "margin in existing/under-construction ISTS sub-stations (NR 5250, WR 9628, SR 5630, ER 13150)")
for v, ckm, mva in (("±800 kV HVDC", 6200, 20000), ("±350 kV HVDC", 1920, 5000), ("765 kV", 25960, 274500), ("400 kV", 15758, 134075), ("220 kV cable (offshore)", 1052, 0), ("All voltages", 50890, 433575)):
    add("India", d0, d1, "snapshot", "CEA 500 GW RE transmission plan", f"additional_ists_line_length|{v}", "planned", ckm, None, "ckm", S5, "ISTS additions required for RE integration by 2030")
    add("India", d0, d1, "snapshot", "CEA 500 GW RE transmission plan", f"additional_ists_substation_capacity|{v}", "planned", mva, None, "MVA", S5, "ISTS additions required for RE integration by 2030")
add("India", d0, d1, "snapshot", "CEA 500 GW RE transmission plan", "estimated_cost_total", "planned", 244200, None, "Rs crore", S5, "onshore wind/solar 2,16,100 + offshore wind 28,100")
add("India", d0, d1, "snapshot", "CEA 500 GW RE transmission plan", "estimated_cost_offshore_wind_10GW", "planned", 28100, None, "Rs crore", S5)
add("India", d0, d1, "snapshot", "CEA 500 GW RE transmission plan", "bess_assumed", "planned", 51.5, None, "GW", S5, "BESS requirement with 537 GW RE by 2030")
add("India", "2022-11-01", "2022-11-01", "snapshot", "CEA 500 GW RE transmission plan", "inter_regional_capacity", "actual", None, 112250, "MW", S5, "'present' at report date")
add("India", d0, "2030-12-31", "snapshot", "CEA 500 GW RE transmission plan", "inter_regional_capacity", "planned", 150000, None, "MW", S5, "'likely to be about 1,50,000 MW in 2030'")
for st, gw in (("Commissioned", 12.9), ("Under construction (slated Dec 2022-Nov 2023)", 19.1), ("Under tendering", 8), ("To be taken up for bidding/implementation", 10.5),
               ("Other planned schemes", 9.5), ("Phase-I under implementation / Phase-II to be notified", 2.5), ("Planned under intra-state", 4)):
    add("India", "2022-11-01", "2022-11-01", "snapshot", "66.5 GW ISTS RE programme", "re_capacity_by_transmission_status", st, None, gw, "GW", S5, "RE capacity to be evacuated by transmission schemes in this status (total 66.5 GW)")
add("Rajasthan", d0, d1, "snapshot", "GIB constraint", "re_potential_zones_in_gib_area", "constraint", None, 45, "GW", S5, "of 75 GW identified RE potential zones in Rajasthan, 45 GW (30 GW solar, 15 GW wind) lie in GIB area (Barmer, Jaisalmer, Jodhpur)")
add("India", "2022-11-01", "2022-11-01", "snapshot", "GEC-I (intra-state)", "re_capacity_planned", "planned", 24, None, "GW", S5, "'about 24 GW'; 'about 7 GW of RE capacity is yet to be commissioned'; balance schemes likely by March 2023")
add("India", "2022-11-01", "2022-11-01", "snapshot", "GEC-II (intra-state)", "re_capacity_planned", "planned", 19431, None, "MW", S5, "HP 317, Rajasthan 4023, UP 4000, Gujarat 4000, Karnataka 2639, TN 4000, Kerala 452; cost Rs 12,031.33 cr, CFA 33% = Rs 3,970.34 cr")

# ---- CEA: National Electricity Plan Vol II Transmission (Oct 2024)
SN = "TRN-CEA-NEP-T"
for v, t, a, u in (("HVDC ±320/±800 kV", 3531, 3819, "ckm"), ("765 kV", 25670, 19783, "ckm"), ("400 kV", 36770, 36191, "ckm"), ("230/220 kV", 38429, 29072, "ckm"),
                   ("All voltages", 104400, 88865, "ckm")):
    add("India", "2017-04-01", "2022-03-31", "FY", "NEP 2017-22 review", f"transmission_line_addition|{v}", "target vs achievement", t, a, u, SN)
for v, t, a in (("765 kV", 116700, 89700), ("400 kV", 125535, 152306), ("230/220 kV", 85654, 107679), ("All voltages AC", 327889, 349685)):
    add("India", "2017-04-01", "2022-03-31", "FY", "NEP 2017-22 review", f"transformation_capacity_addition|{v}", "target vs achievement", t, a, "MVA", SN)
add("India", "2017-04-01", "2022-03-31", "FY", "NEP 2017-22 review", "hvdc_capacity_addition", "target vs achievement", 14000, 14000, "MW", SN)
for per, ps, pe, ckm, mva, hv, endckm, endmva, endhv, cost in (("2022-27", "2022-04-01", "2027-03-31", 114687, 776330, 1000, 571403, 1847280, 34500, 425222),
                                                                ("2027-32", "2027-04-01", "2032-03-31", 76787, 497855, 32250, 648190, 2345135, 66750, 490920)):
    add("India", ps, pe, "FY", f"NEP {per}", "transmission_line_addition|All voltages", "planned", ckm, None, "ckm", SN, "220 kV and above")
    add("India", ps, pe, "FY", f"NEP {per}", "transformation_capacity_addition|All voltages", "planned", mva, None, "MVA", SN, "220 kV and above")
    add("India", ps, pe, "FY", f"NEP {per}", "hvdc_bipole_capacity_addition", "planned", hv, None, "MW", SN)
    add("India", pe, pe, "snapshot", f"NEP {per}", "transmission_line_length_cumulative", "planned", endckm, None, "ckm", SN)
    add("India", pe, pe, "snapshot", f"NEP {per}", "transformation_capacity_cumulative", "planned", endmva, None, "MVA", SN)
    add("India", pe, pe, "snapshot", f"NEP {per}", "hvdc_capacity_cumulative", "planned", endhv, None, "MW", SN)
    add("India", ps, pe, "FY", f"NEP {per}", "estimated_cost", "planned", cost, None, "Rs crore", SN, "transmission lines, sub-stations, reactive compensation")
for c, a22, add27, e27, add32, e32 in (("West-North", 36720, 18400, 55120, 6000, 61120), ("North East-North", 3000, 0, 3000, 0, 3000), ("East-North", 22530, 0, 22530, 6000, 28530),
                                       ("East-West", 21190, 1600, 22790, 0, 22790), ("East-South", 7830, 0, 7830, 4200, 12030), ("West-South", 18120, 10000, 28120, 8400, 36520),
                                       ("East-North East", 2860, 690, 3550, 0, 3550), ("Total", 112250, 30690, 142940, 24600, 167540)):
    add("India", "2022-03-31", "2022-03-31", "snapshot", "NEP inter-regional", f"inter_regional_capacity|{c}", "actual", None, a22, "MW", SN)
    add("India", "2027-03-31", "2027-03-31", "snapshot", "NEP inter-regional", f"inter_regional_capacity|{c}", "planned", e27, None, "MW", SN, f"addition 2022-27: {add27} MW")
    add("India", "2032-03-31", "2032-03-31", "snapshot", "NEP inter-regional", f"inter_regional_capacity|{c}", "planned", e32, None, "MW", SN, f"addition 2027-32: {add32} MW (blank in source treated as 0 only where the end value equals the start value)")
for st, mw in (("commissioned 2022-24 (till 31.03.2024)", 6490), ("under construction", 7400), ("under bidding", 8400), ("to be taken up for bidding/construction in 2024-25", 8400)):
    add("India", "2024-03-31", "2024-03-31", "snapshot", "NEP inter-regional", "inter_regional_capacity_addition_2022-27_by_status", st, None, mw, "MW", SN)
add("India", "2024-03-31", "2024-03-31", "snapshot", "NEP inter-regional", "inter_regional_capacity", "actual", None, 118740, "MW", SN, "as on 31 March 2024")
add("India", "2024-04-01", "2025-03-31", "FY", "NEP annual target", "transmission_line_addition_target", "target", 16667, None, "ckm", SN, "target 2024-25 as stated in NEP; CEA exec summary Mar-2025 prints a programme of 15,253 ckm")
add("India", "2024-04-01", "2025-03-31", "FY", "NEP annual target", "transformation_capacity_addition_target", "target", 116490, None, "MVA", SN, "target 2024-25 as stated in NEP")
add("India", "2032-03-31", "2032-03-31", "snapshot", "NEP RE integration", "re_capacity_transmission_planned_for", "planned", 613, None, "GW", SN, "'Transmission system has been planned for evacuation of power from about 613 GW RE capacity by the year 2032'")
add("Rajasthan", "2032-03-31", "2032-03-31", "snapshot", "NEP RE integration", "re_capacity_planned_intra_state_other_than_gec", "planned", 10, None, "GW", SN)
add("Gujarat", "2032-03-31", "2032-03-31", "snapshot", "NEP RE integration", "re_capacity_planned_intra_state_other_than_gec", "planned", 37, None, "GW", SN)
# GEC-I state table, as on 30.06.2024
gec1 = [("Karnataka", 4.50, 3.92, 618, 618, 2702, 2702, "All projects completed (COD March 2023)"),
        ("Madhya Pradesh", 4.10, 4.13, 2773, 2773, 4748, 4748, "All projects completed (COD June 2022)"),
        ("Rajasthan", 2.41, 2.58, 1054, 984, 1915, 1915, "All projects completed (COD April 2021); some lines built on shorter route"),
        ("Tamil Nadu", 2.20, 1.77, 1068, 1068, 2250, 1910, "340 MVA cancelled; remaining completed (COD Oct 2022)"),
        ("Andhra Pradesh", 3.15, 1.90, 1073, 854, 2157, 1265, "RoW in one line; anticipated COD June 2024"),
        ("Gujarat", 4.00, 2.99, 1908, 1636, 7980, 7980, "RoW issues in four lines; one line stuck up due to GIB issue; anticipated COD June 2024"),
        ("Himachal Pradesh", 1.00, 0.50, 502, 498, 937, 793, "Approach roads damaged (July 2023 rain); anticipated COD June 2024"),
        ("Maharashtra", 1.86, 0.94, 771, 704, None, None, "RoW issue in one line; no substation sanctioned under GEC-I"),
        ("India", 23.22, 18.72, 9767, 9135, 22689, 21313, "Total of 8 states; states requested extension beyond June 2024")]
for st, ret, rea, lt, la, mt, ma, note in gec1:
    add(st, "2015-01-01", "2024-06-30", "snapshot", "GEC-I (intra-state)", "re_capacity", "target vs added (added as on 31.03.2024)", ret, rea, "GW", SN, note)
    add(st, "2015-01-01", "2024-06-30", "snapshot", "GEC-I (intra-state)", "transmission_lines", "target vs constructed (as on 30.06.2024)", lt, la, "ckm", SN, note)
    if mt is not None:
        add(st, "2015-01-01", "2024-06-30", "snapshot", "GEC-I (intra-state)", "substation_capacity", "target vs charged (as on 30.06.2024)", mt, ma, "MVA", SN, note)
gec2 = [("Gujarat", 5100, 2470, 7460, 3667.29), ("Himachal Pradesh", 317, 62, 761, 489.49), ("Karnataka", 2639, 938, 1225, 1036.25), ("Kerala", 452, 224, 620, 420.32),
        ("Rajasthan", 2478, 659, 2191, 907.61), ("Tamil Nadu", 4000, 624, 2200, 719.76), ("Uttar Pradesh", 4000, 2597, 15280, 4847.86), ("India", 18986, 7574, 29737, 12088.58)]
for st, re_mw, ckm, mva, cost in gec2:
    for metric, v, u in (("re_capacity", re_mw, "MW"), ("transmission_lines", ckm, "ckm"), ("substation_capacity", mva, "MVA"), ("estimated_cost", cost, "Rs crore")):
        add(st, "2021-04-01", "2026-03-31", "snapshot", "GEC-II (intra-state)", metric, "target (revised scheme); states issuing tenders", v, None, u, SN, "no progress figures in source")
add("Rajasthan", "2019-09-01", "2021-07-31", "snapshot", "ISTS delay (GIB)", "765 kV Fatehgarh PS - Bhadla (PG) D/C (operated at 400 kV), 292 ckm, Adani", "commissioned late",
    "2019-09", "2021-07", "YYYY-MM", SN, "Annex 6.2 lines slipped 2017-22: original schedule Sep'19, actual July'21; reason: re-routing on account of GIB area and height restrictions laid in Defence Aviation")

# ---- Grid-India QOF July 2026: Rajasthan REZ bottleneck
SQ = "TRN-GI-QOF-2026-07"
for metric, v in (("re_capacity_commissioned", 28645), ("gna_effective_complete_ATS_commissioned", 21102), ("gna_not_effective_ATS_not_commissioned", 7543),
                  ("noc_for_tgna_evacuation_peak_solar_11-14h", 1883)):
    add("Rajasthan", "2026-04-01", "2026-06-30", "snapshot", "Rajasthan REZ ISTS (Grid-India QOF)", metric, "actual", None, v, "MW", SQ, "Section 2.7.11 'Delay in commissioning of transmission system ... causing bottlenecking of RE power in Rajasthan REZ'")
for line, scod in (("Fatehgarh-III - Beawar 765 kV D/c + LILO Ajmer-Chittorgarh at Beawar (Rajasthan 20 GW Ph-III Part F)", "2025-03"),
                   ("Sikar-II - Narela 765 kV D/C and Sikar-II - Khetri 765 kV D/C (Rajasthan 20 GW Ph-III Part D)", "2025-08"),
                   ("Neemrana-II - Bareilly (PG) 765 kV D/c (Rajasthan REZ Ph-IV Part-1 Part D)", "2025-12"),
                   ("Bikaner-III - Neemrana-II 765 kV D/c (Rajasthan REZ Ph-IV Part-1 Part A)", "2025-12")):
    add("Rajasthan", "2026-04-01", "2026-06-30", "snapshot", "Rajasthan REZ ISTS (Grid-India QOF)", line, "not yet commissioned (as reported July 2026)", scod, None, "SCOD YYYY-MM", SQ)
add("Rajasthan", "2026-04-01", "2026-06-30", "snapshot", "Rajasthan REZ ISTS (Grid-India QOF)", "gna_not_effective_evacuated_on_tgna", "actual", None, 4.8, "GW", SQ, "Section 2.7.12: '~4.8 GW having GNA not-effective ... evacuated on T-GNA based on available margin' (text figure; differs from table figure above)")
add("Gujarat", "2026-04-01", "2026-06-30", "snapshot", "Khavda RE complex (Grid-India QOF)", "inverter_based_capacity_in_complex", "actual", None, 15.9, "GW", SQ, "14.8 GW RE + 1.1 GW BESS; grid event in the quarter: tripping of 765 kV KPS2-Lakadia D/C and KPS1-Bhuj D/C, all-India solar fell 69,224 -> 60,611 MW (loss ~8,613 MW)")

# ---- TBCB projects (CEA Sep 2026)
ST = "TRN-CEA-TBCB-2026-09"
tb = os.path.join(P, "_tbcb_projects.csv")
for r in csv.DictReader(open(tb)):
    if r["re_zone"] != "yes":
        continue
    geo = "Rajasthan" if "rajasthan" in r["project"].lower() or "bhadla" in r["project"].lower() or "fatehgarh" in r["project"].lower() else \
          "Gujarat" if any(k in r["project"].lower() for k in ("khavda", "gujarat", "kps", "lakadia", "banaskantha", "jam khambhaliya", "navinal")) else \
          "Karnataka" if any(k in r["project"].lower() for k in ("karnataka", "koppal", "gadag", "bidar", "tumkur", "davanagere", "bijapur", "bellary")) else \
          "Andhra Pradesh" if any(k in r["project"].lower() for k in ("kurnool", "ananthapur")) else \
          "Maharashtra" if any(k in r["project"].lower() for k in ("dhule", "kallam", "solapur", "maharashtra")) else \
          "Madhya Pradesh" if any(k in r["project"].lower() for k in ("madhya pradesh", "mandsaur", "morena", "rajgarh")) else \
          "Tamil Nadu" if "krishnagiri" in r["project"].lower() else "India"
    add(geo, "2026-09-30", "2026-09-30", "snapshot", "ISTS TBCB under construction (RE-related)", r["project"][:250], "under construction",
        r["completion_original"], r["completion_anticipated"], "completion month (Mon-YY)", ST,
        f"agency {r['agency']}; cost Rs {r['cost_rs_crore']} cr; SPV transfer {r['spv_transfer']}; DERIVED delay {r['delay_months']} months (anticipated minus original)")

# ---- T-GNA margin headline rows (first and latest issue)
tg = list(csv.DictReader(open(os.path.join(P, "re_complex_tgna_margin.csv"))))
dates = sorted(set(r["period_start"] for r in tg))
for d in (dates[0], dates[-1]):
    for r in tg:
        if r["period_start"] == d and r["metric"] in ("connectivity_quantum_commissioned", "gna_effective", "gna_not_effective", "tgna_injection_limit_min_over_day"):
            add(r["geography"], d, d, "snapshot", "ISTS RE complex GNA vs commissioned (Grid-India T-GNA margin)", r["metric"], "actual", None, r["value"], "MW", r["source_id"],
                "GNA effective = RE capacity whose associated transmission (ATS) is complete; not-effective = commissioned RE waiting for ATS. " + r["notes"][:200])

with open(os.path.join(P, "re_transmission_plans.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)
print("rows", len(R))
