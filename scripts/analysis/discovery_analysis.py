"""Cross-dataset investigation for discovery.md.

Reads processed CSVs from the repo (data/processed), prints findings, and writes the derived tables it relies on
to data/processed/analysis/. Every figure here is DERIVED from the cited processed datasets.
Run from repo root:  .venv/bin/python -I scripts/analysis/discovery_analysis.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "processed"
OUT = P / "analysis"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)


def rd(rel, **kw):
    f = P / rel
    if not f.exists() and (P / (rel + ".gz")).exists():
        f = P / (rel + ".gz")
    return pd.read_csv(f, low_memory=False, **kw)


def h(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


# ------------------------------------------------------------------ load
cs = rd("curtailment_forecast/curtailment_timeseries.csv")
cd = cs[(cs.geography == "India") & (cs.granularity == "daily")]
curt = cd.pivot_table(index="period_start", columns="metric", values="value", aggfunc="sum")
curt.index = pd.to_datetime(curt.index)
curt.columns = ["s9_solar", "s9_wind", "s8_solar", "s8_wind"] if list(curt.columns) == sorted(curt.columns) else curt.columns
curt = curt.rename(columns=lambda c: c)
cols = {c: ("s9_" if "Section 9" in c else "s8_") + ("solar" if "solar" in c else "wind") for c in curt.columns
        if isinstance(c, str) and "Section" in c}
curt = curt.rename(columns=cols).fillna(0)
curt["total"] = curt.sum(axis=1)
report_days = curt.index  # days with a parsed report

pdly = rd("prices/prices_daily_summary.csv")
pdly["date"] = pd.to_datetime(pdly.date)
dam = pdly[pdly.market == "IEX DAM"].set_index("date")
rtm = pdly[pdly.market == "IEX RTM"].set_index("date")
gdam = pdly[pdly.market == "IEX GDAM"].set_index("date")

hr = rd("generation_demand/hourly_india.csv")
hr["ts"] = pd.to_datetime(hr.period_start)
hr["date"] = hr.ts.dt.normalize()
hr["hhmm"] = hr.ts.dt.strftime("%H:%M")
hr["vre"] = hr.solar_mw + hr.wind_mw
hr["net_load"] = hr.demand_met_mw - hr.vre

# ------------------------------------------------------------------ I1: curtailment vs prices (daily)
h("I1  Daily curtailment vs IEX prices (days with a parsed Grid-India VRE report)")
j = curt.join(dam[["avg_mcp_solar_0900_1700_rs_mwh", "min_mcp_rs_mwh", "max_mcp_rs_mwh", "n_blocks_le_1",
                   "sell_buy_ratio_solar"]], how="left")
j = j.join(rtm[["min_mcp_rs_mwh", "n_blocks_le_1"]].add_prefix("rtm_"), how="left")
j["dam_solar_rs_kwh"] = j.avg_mcp_solar_0900_1700_rs_mwh / 1000
print("days:", len(j), " with curtailment >= 10 MU:", (j.total >= 10).sum())
print("Spearman corr total curtailment vs DAM solar-hour price:",
      round(j[["total", "dam_solar_rs_kwh"]].corr(method="spearman").iloc[0, 1], 3))
print("Spearman corr total curtailment vs DAM sell/buy ratio (solar):",
      round(j[["total", "sell_buy_ratio_solar"]].corr(method="spearman").iloc[0, 1], 3))
bins = pd.cut(j.total, [-0.01, 1, 10, 30, 60, 1000], labels=["<1", "1-10", "10-30", "30-60", ">60"])
g = j.groupby(bins, observed=True).agg(days=("total", "size"), dam_solar_price=("dam_solar_rs_kwh", "median"),
                                       dam_blocks_le1=("n_blocks_le_1", "median"),
                                       share_days_any_le1=("n_blocks_le_1", lambda s: (s > 0).mean() * 100),
                                       sell_buy=("sell_buy_ratio_solar", "median"))
print(g.round(2).to_string())
top = j.sort_values("total", ascending=False).head(25)
print("\nTop-25 curtailment days:")
print(top[["total", "s8_solar", "s9_solar", "s8_wind", "s9_wind", "dam_solar_rs_kwh", "n_blocks_le_1",
           "rtm_n_blocks_le_1", "sell_buy_ratio_solar"]].round(2).to_string())
hi_price = j[(j.total >= 30) & (j.dam_solar_rs_kwh >= 3)]
print(f"\nDays with >=30 MU curtailed while DAM solar-hour avg >= Rs3/kWh: {len(hi_price)}")
print(hi_price[["total", "s8_solar", "s9_solar", "dam_solar_rs_kwh"]].round(2).to_string())
nz_no = j[(j.n_blocks_le_1 >= 8) & (j.total < 1)]
print(f"\nDays with >=8 DAM blocks <= Rs1/kWh but <1 MU curtailment: {len(nz_no)}")
j.to_csv(OUT / "daily_curtailment_vs_prices.csv")

# ------------------------------------------------------------------ I2: thermal flexibility during curtailment
h("I2  Was thermal backed down at midday on curtailment days? (Grid-India 15-min SCADA)")
day = hr.groupby("date").agg(thermal_max=("thermal_mw", "max"), thermal_min=("thermal_mw", "min"),
                             freq_max=("frequency_hz", "max"), vre_max=("vre", "max"),
                             demand_max=("demand_met_mw", "max"), net_min=("net_load", "min"))
mid = hr[hr.hhmm.between("12:00", "14:45")].groupby("date").agg(thermal_mid=("thermal_mw", "mean"),
                                                                 freq_mid=("frequency_hz", "mean"),
                                                                 hydro_mid=("hydro_mw", "mean"))
eve = hr[hr.hhmm.between("19:00", "21:45")].groupby("date").agg(thermal_eve=("thermal_mw", "mean"),
                                                                hydro_eve=("hydro_mw", "mean"))
day = day.join(mid).join(eve)
day["thermal_mid_to_max"] = day.thermal_mid / day.thermal_max * 100
day["thermal_swing_gw"] = (day.thermal_eve - day.thermal_mid) / 1000
dj = day.join(curt[["total"]], how="inner")
b2 = pd.cut(dj.total, [-0.01, 1, 10, 30, 60, 1000], labels=["<1", "1-10", "10-30", "30-60", ">60"])
print(dj.groupby(b2, observed=True).agg(days=("total", "size"), thermal_mid_gw=("thermal_mid", lambda s: s.median() / 1000),
                                       thermal_eve_gw=("thermal_eve", lambda s: s.median() / 1000),
                                       mid_as_pct_of_day_max=("thermal_mid_to_max", "median"),
                                       freq_mid=("freq_mid", "median"), freq_max=("freq_max", "median"),
                                       hydro_mid_gw=("hydro_mid", lambda s: s.median() / 1000)).round(2).to_string())
print("\nThermal midday as % of that day's max, on days with >=30 MU curtailed: min/median/max",
      dj[dj.total >= 30].thermal_mid_to_max.describe()[["min", "50%", "max"]].round(1).to_dict())
print("Lowest midday thermal on any day in the 15-min record (GW):", round(day.thermal_mid.min() / 1000, 1),
      "on", day.thermal_mid.idxmin().date())
print("Days with frequency max >= 50.20 Hz:", (day.freq_max >= 50.2).sum(), "of", len(day),
      "| on >=30 MU curtailment days:", (dj[dj.total >= 30].freq_max >= 50.2).mean().round(2))
print("Corr curtailment vs midday mean frequency (spearman):",
      round(dj[["total", "freq_mid"]].corr(method="spearman").iloc[0, 1], 3))
day.to_csv(OUT / "daily_system_profile_15min_derived.csv")

# storage columns in SCADA
sc = hr[["storage_demand_mw", "storage_gen_mw"]].notna().sum()
print("\nSCADA storage columns non-null rows:", sc.to_dict())
if sc.max() > 0:
    s = hr.dropna(subset=["storage_demand_mw"])
    print("storage data from", s.ts.min(), "to", s.ts.max())
    print(s.groupby(s.ts.dt.hour)[["storage_demand_mw", "storage_gen_mw"]].mean().round(0).T.to_string())
    print("max storage_demand_mw (charging):", s.storage_demand_mw.max(), "max storage_gen_mw:", s.storage_gen_mw.max())

# ------------------------------------------------------------------ I3: the three RTM ₹0 days
h("I3  The RTM Rs 0 days")
rb = rd("prices/iex_rtm_blocks.csv")
z = rb[(rb.mcp_rs_mwh == 0) & (~rb.no_trade.astype(bool))]
for d0 in sorted(z.date.unique()):
    d = pd.Timestamp(d0)
    blocks = z[z.date == d0].block_start.tolist()
    row = {"date": d0, "rtm_zero_blocks": f"{len(blocks)} ({blocks[0]}-{blocks[-1]})"}
    if d in curt.index:
        row.update(curtail_MU=round(curt.loc[d, "total"], 1), s9_MU=round(curt.loc[d, ["s9_solar", "s9_wind"]].sum(), 1))
    if d in day.index:
        x = day.loc[d]
        row.update(freq_max=x.freq_max, net_min_gw=round(x.net_min / 1000, 1), vre_max_gw=round(x.vre_max / 1000, 1),
                   thermal_mid_gw=round(x.thermal_mid / 1000, 1), thermal_eve_gw=round(x.thermal_eve / 1000, 1))
    if d in dam.index:
        row.update(dam_min=dam.loc[d, "min_mcp_rs_mwh"] / 1000, dam_max=dam.loc[d, "max_mcp_rs_mwh"] / 1000)
    dow = d.day_name()
    row["weekday"] = dow
    print(row)
    # holiday/weekend context + demand vs same weekday previous week
    if d in day.index and (d - pd.Timedelta(days=7)) in day.index:
        print("   demand max vs 7 days earlier: %.1f vs %.1f GW" % (day.loc[d, "demand_max"] / 1000,
                                                                 day.loc[d - pd.Timedelta(days=7), "demand_max"] / 1000))

# ------------------------------------------------------------------ I4: floor-to-cap days (duck curve spread)
h("I4  Same-day price spread: midday near-zero AND evening at the Rs10 cap (IEX DAM)")
dam_y = dam.copy()
dam_y["year"] = dam_y.index.year
dam_y["spread"] = (dam_y.max_mcp_rs_mwh - dam_y.min_mcp_rs_mwh) / 1000
dam_y["floor_cap"] = (dam_y.min_mcp_rs_mwh <= 1000) & (dam_y.max_mcp_rs_mwh >= 9999)
print(dam_y.groupby("year").agg(days=("spread", "size"), median_spread=("spread", "median"),
                                days_spread_ge8=("spread", lambda s: (s >= 8).sum()),
                                days_min_le1_and_max_at_cap=("floor_cap", "sum")).round(2).to_string())

# ------------------------------------------------------------------ I5: demand slowdown vs RE additions
h("I5  Demand growth vs supply growth")
pi = rd("generation_demand/psp_daily_india.csv")
em = pi[pi.metric == "energy_met"].copy()
em["d"] = pd.to_datetime(em.period_start)
em = pd.to_numeric(em.set_index("d").value, errors="coerce")
mon = em.resample("MS").agg(["sum", "count"])
mon = mon[mon["count"] >= 28]
mon["yoy_%"] = mon["sum"].pct_change(12) * 100
print(mon.loc["2023-01-01":].round(1).to_string())
fy = rd("generation_demand/demand_fy.csv")
print(fy[fy.metric.str.contains("peak|requirement", case=False, na=False) & (fy.source_id.str.contains("LGBR", na=False))]
      [["period_start", "metric", "value", "unit"]].tail(16).to_string())

# ------------------------------------------------------------------ I6: reasons & geography
h("I6  Curtailment reasons and entities")
rc = rd("curtailment_forecast/remc_daily_curtailment.csv")
rc = rc[rc.qa_flag.isna()] if "qa_flag" in rc else rc
rc["MU"] = rc.wind_MU.fillna(0) + rc.solar_MU.fillna(0)
r = rc.reason.fillna("").str.lower()
cat = np.select([r.str.contains("tras"), r.str.contains("transmission|evacuat|line|ict|outage|constraint|n-1|sps"),
                 r.str.contains("frequenc|underdraw|ud\\b|under draw|low demand|surplus|grid secur|voltage"),
                 r.str.contains("no curtailment") | (r == "0") | (r == "")],
                ["TRAS down (NLDC, grid security reserve)", "Transmission / evacuation constraint",
                 "High frequency / under-drawal / low demand", "none/blank"], "other")
rc["reason_cat"] = cat
print(rc.groupby(["section", "reason_cat"]).MU.sum().round(1).sort_values(ascending=False).to_string())
print("\nTop entities by curtailed MU (all sections, 2025-01 -> latest):")
print(rc.groupby(["section", "entity"]).MU.sum().sort_values(ascending=False).head(20).round(1).to_string())
oth = rc[(rc.reason_cat == "other") & (rc.MU > 0)].reason.value_counts().head(15)
print("\nUnclassified reasons with MU>0:\n", oth.to_string())
rc.groupby(["reason_cat"]).MU.sum().to_csv(OUT / "curtailment_by_reason_category.csv")

# ------------------------------------------------------------------ I7: GDAM vs DAM paradox
h("I7  GDAM vs DAM in solar hours")
gd = gdam[["avg_mcp_solar_0900_1700_rs_mwh", "sell_buy_ratio_solar"]].join(
    dam[["avg_mcp_solar_0900_1700_rs_mwh", "sell_buy_ratio_solar"]], lsuffix="_gdam", rsuffix="_dam", how="inner")
gd = gd.resample("YS").mean() / [1000, 1, 1000, 1]
print(gd.round(2).to_string())

# ------------------------------------------------------------------ I8: wind in curtailment (monsoon)
h("I8  Wind share of curtailment by month")
m = curt.resample("MS").sum()
m["wind_share_%"] = (m.s8_wind + m.s9_wind) / m.total * 100
print(m[["total", "s8_solar", "s9_solar", "s8_wind", "s9_wind", "wind_share_%"]].round(1).to_string())

# ------------------------------------------------------------------ I9: invisible curtailment (T-GNA)
h("I9  Capacity without firm access vs midday T-GNA headroom (MW)")
tg = rd("transmission/re_complex_tgna_margin.csv")
tg["d"] = pd.to_datetime(tg.period_start)
pv = tg[tg.metric.isin(["connectivity_quantum_commissioned", "gna_effective", "gna_not_effective",
                        "tgna_injection_limit_min_over_day", "tgna_injection_limit_max_over_day"])] \
    .pivot_table(index=["geography", "d"], columns="metric", values="value", aggfunc="max")
pv["blocked_at_min_MW"] = (pv.gna_not_effective - pv.tgna_injection_limit_min_over_day).clip(lower=0)
print(pv.groupby(level=0).agg(issues=("gna_not_effective", "size"),
                              median_without_gna=("gna_not_effective", "median"),
                              median_tgna_min=("tgna_injection_limit_min_over_day", "median"),
                              median_blocked_at_min=("blocked_at_min_MW", "median"),
                              max_blocked_at_min=("blocked_at_min_MW", "max")).round(0).to_string())
pv.to_csv(OUT / "tgna_blocked_capacity_derived.csv")

# ------------------------------------------------------------------ I10: PPA backlog & storage economics context
h("I10 Pipeline / storage context rows")
pp = rd("capacity_storage/re_pipeline_targets.csv")
print(pp[pp.metric.str.contains("ppa|psa|unsigned|awarded", case=False, na=False)]
      [["period_start", "metric", "value", "unit", "source_id"]].to_string())
st = rd("capacity_storage/storage_capacity.csv")
print(st[st.metric.str.contains("tariff", case=False, na=False)][["period_start", "metric", "value", "unit", "source_id"]]
      .to_string())

# ------------------------------------------------------------------ I11: anomalies catalogue checks
h("I11 Data anomaly checks")
warn = pi[pi.notes.fillna("").str.contains("WARN|inconsistent|contradict", case=False)]
print("PSP rows with warning notes:", len(warn), "| distinct days:", warn.period_start.nunique())
print(warn[["period_start", "metric", "value"]].head(15).to_string())
qa = rd("curtailment_forecast/remc_daily_curtailment.csv")
qa = qa[qa.qa_flag.notna()]
print("\nREMC rows with qa_flag:", len(qa))
print(qa[["date", "section", "entity", "wind_MU", "solar_MU", "qa_flag"]].head(20).to_string())
irc = rd("transmission/inter_regional_capacity.csv")
print("\nInter-regional total around Mar-2024:")
print(irc[irc.period_start.str.startswith(("2024-03", "2024-04")) & irc.metric.str.contains("total", case=False)]
      [["period_start", "metric", "value", "source_id"]].to_string())
bess = st[(st.technology == "BESS") & st.metric.str.contains("energy", case=False) & (st.geography == "India")]
print("\nBESS energy figures by source around 2026:")
print(bess[bess.period_start >= "2025-12"][["period_start", "metric", "status", "value", "unit", "source_id"]].to_string())

# ------------------------------------------------------------------ I12: money value of curtailment
h("I12 Rough value of curtailed energy, at IEX solar-hour price (derived, lower bound)")
val = j.copy()
val["value_lost_cr"] = val.total * 1000 * val.dam_solar_rs_kwh * 1000 / 1e7  # MU->MWh (*1000); Rs/kWh->Rs/MWh (*1000); /1e7 = crore
val["year"] = val.index.year
print(val.groupby("year").value_lost_cr.sum().round(0).to_string())
print("Total (Jan 2025 - latest), Rs crore:", round(val.value_lost_cr.sum(), 0),
      "| at exchange price. PPA tariffs are typically lower than DAM solar-hour price in low-price periods,")
print("so compensation at PPA rates (where owed) could differ materially; this is a floor, not an estimate of compensation due.")

# ------------------------------------------------------------------ I13: weekday effect
h("I13 Day-of-week effect on curtailment and prices")
j["dow"] = j.index.day_name()
order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
print("Median curtailment (MU) by weekday, all days with a report:")
print(j.groupby("dow").total.median().reindex(order).round(1).to_string())
d26 = dam[dam.index.year == 2026].copy()
d26["dow"] = d26.index.day_name()
print("\n2026 median DAM solar-hour price (Rs/kWh) by weekday:")
print((d26.groupby("dow").avg_mcp_solar_0900_1700_rs_mwh.median() / 1000).reindex(order).round(2).to_string())
print("\n2026 median DAM blocks <= Rs1/kWh by weekday:")
print(d26.groupby("dow").n_blocks_le_1.median().reindex(order).to_string())

# ------------------------------------------------------------------ I14: the second curtailment front (south)
h("I14 Curtailment entities outside Rajasthan/Gujarat (Karnataka, Tamil Nadu wind; Andhra solar)")
south = rc[rc.entity.isin(["Pugalur", "Karur", "Tuticorin GIS", "GADAG", "HIRIYUR", "KOPPAL", "Kurnool", "NPKunta"])]
print(south.groupby("entity")[["wind_MU", "solar_MU"]].sum().round(1)
      .assign(total=lambda d: d.sum(axis=1)).sort_values("total", ascending=False).to_string())
print("\n(Pugalur/Karur/Tuticorin = Tamil Nadu wind corridor; GADAG/HIRIYUR/KOPPAL = Karnataka wind; "
      "Kurnool/NPKunta = Andhra Pradesh solar parks)")

# ------------------------------------------------------------------ I15: the pipeline concentration risk
h("I15 Where the next wave of capacity is being built (CEA under-construction, state-wise)")
uc = pp[(pp.metric == "re_under_construction_total") & (pp.period_start == "2026-09-30")].sort_values("value", ascending=False)
nat_uc = uc[uc.geography == "India"].value.iloc[0]
print(uc[uc.geography != "India"][["geography", "value", "unit"]].head(8).to_string())
top2 = uc[uc.geography.isin(["Rajasthan", "Gujarat"])].value.sum()
print(f"\nNational under-construction RE total (30 Sep 2026): {nat_uc:,.0f} MW")
print(f"Rajasthan + Gujarat share: {top2:,.0f} MW = {top2/nat_uc*100:.0f}% of national under-construction capacity")
print("\nRajasthan under-construction over time:")
print(pp[(pp.geography == "Rajasthan") & (pp.metric == "re_under_construction_total")]
      [["period_start", "value"]].to_string())

# ------------------------------------------------------------------ I16: does the T-GNA report cover all state capacity?
h("I16 T-GNA complex coverage vs total state installed capacity (Rajasthan)")
raj_state = rd("capacity_storage/re_capacity_statewise.csv")
raj_state = raj_state[raj_state.geography == "Rajasthan"]
re_total = raj_state[(raj_state.metric == "re_capacity_incl_large_hydro") & (raj_state.period_start == "2026-03-31")]
print("Rajasthan total installed RE (CEA/MNRE statewise, 31 Mar 2026):", re_total.value.values, re_total.unit.values)
tgna_mar = pv.loc["Rajasthan ISTS RE"].reset_index()
tgna_near = tgna_mar[tgna_mar.d.between("2026-02-15", "2026-03-15")]
print("\nT-GNA 'connectivity_quantum_commissioned' for Rajasthan ISTS RE complex, issues near 1 Mar 2026:")
print(tgna_near[["d", "connectivity_quantum_commissioned"]].to_string())
print("\nGap: state-wide installed RE capacity substantially exceeds the T-GNA complex's 'commissioned' figure for the "
      "same period. The T-GNA report names specific ISTS pooling stations (Fatehgarh/Bhadla/Bikaner), not all RE in "
      "the state, so the complex-level stranded-capacity figures in Lead 3 are a subset of Rajasthan, not the whole "
      "state's exposure. Cause of the gap (other access arrangements vs. untracked stations) is not established.")
