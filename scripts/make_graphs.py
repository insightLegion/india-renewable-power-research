"""Build the three deliverable graphs from processed data in the bucket.

Reads processed CSVs from the bucket into memory and uploads PNG + SVG to outputs/graphs/.
Optional argv[1]: a local preview directory (temporary, for eyeballing; delete afterwards).
Every number plotted is either read from a source CSV or computed here (marked "derived" on the chart).
Run:  eval "$(mybucket env --box)"; .venv/bin/python -I scripts/make_graphs.py [preview_dir]
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from bucket import read_csv, put_bytes

PREVIEW = Path(sys.argv[1]) if len(sys.argv) > 1 else None

# Reference palette (dataviz skill, light mode), fixed slot order
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
VIOLET, RED = "#6250d6", "#e34948"
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
WIND, SOLAR = BLUE, ORANGE  # slot 1, slot 2

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "axes.titlesize": 10.5, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "legend.frameon": False, "lines.linewidth": 2,
    "savefig.facecolor": SURFACE,
})


def save(fig, name):
    for ext in ("png", "svg"):
        buf = io.BytesIO()
        fig.savefig(buf, format=ext, dpi=200, bbox_inches="tight")
        put_bytes(f"outputs/graphs/{name}.{ext}", buf.getvalue())
        if PREVIEW and ext == "png":
            (PREVIEW / f"{name}.png").write_bytes(buf.getvalue())
    plt.close(fig)
    print("uploaded", name)


def footer(fig, text, y=0.005):
    fig.text(0.01, y, text, fontsize=7.3, color=MUTED, va="bottom", ha="left", wrap=True)


def pick(df, **eq):
    m = pd.Series(True, index=df.index)
    for k, v in eq.items():
        m &= df[k] == v
    return df[m]


# ---------------------------------------------------------------- Graph 1
def graph1():
    ecap = read_csv("processed/capacity_storage/ember_capacity_india_annual.csv")
    egen = read_csv("processed/generation_demand/gen_fy_india.csv")
    egen = egen[egen.source_id == "GEN-EMBER-YEARLY-GLOBAL"]
    cap_m = read_csv("processed/capacity_storage/re_capacity_india_monthly.csv")
    gen_m = read_csv("processed/generation_demand/gen_monthly_india.csv")

    yrs = range(2014, 2026)

    def annual(df, metric):
        s = pick(df, metric=metric, geography="India").copy()
        s["year"] = s.period_start.str[:4].astype(int)
        return s.groupby("year").value.first().reindex(yrs)

    cap = {t: annual(ecap, f"capacity_{t}") for t in ("solar", "wind")}
    gen = {t: annual(egen, f"gen_{t}") for t in ("solar", "wind")}
    years = np.arange(2015, 2026)

    # monthly (CEA): capacity MW at month end, generation MU in month
    def cea_cap(metric):
        s = pick(cap_m, metric=metric, source_id="CAP-001", geography="India").copy()
        s["v"] = np.where(s.unit == "GW", s.value * 1000, s.value)
        s["m"] = pd.to_datetime(s.period_start).dt.to_period("M")
        return s.groupby("m").v.last()

    def cea_gen(metric):
        s = pick(gen_m, metric=metric, source_id="GEN-CEA-RE-MONTHLY", geography="India").copy()
        s["m"] = pd.to_datetime(s.period_start).dt.to_period("M")
        return s.groupby("m").value.sum()

    fig = plt.figure(figsize=(12, 9.2))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.18, top=0.9, bottom=0.1)
    fig.suptitle("Graph 1 · India: solar & wind capacity expansion vs actual generation", x=0.01, ha="left",
                 fontsize=13.5, fontweight="bold", color=INK, y=0.985)
    fig.text(0.01, 0.94, "Solar capacity grew ~24× (5.7→136 GW, 2015→2025) and generation grew in step (7→195 TWh). Solar output per GW has "
             "held at ~19%/yr since 2022; monthly solar CF in mid-2025 and mid-2026 is the lowest since 2018.", fontsize=9.5, color=INK2)

    ax = fig.add_subplot(gs[0, 0])
    for t, c in (("wind", WIND), ("solar", SOLAR)):
        ax.plot(years, cap[t].loc[years], color=c, marker="o", ms=4.5)
        ax.annotate(f"{t.title()} {cap[t].loc[2025]:.0f} GW", (2025, cap[t].loc[2025]), xytext=(6, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=8.5)
    ax.set_title("A · Installed capacity, end of calendar year (GW)")
    ax.set_xlim(2014.6, 2026.6)
    ax.set_ylim(0)

    ax = fig.add_subplot(gs[0, 1])
    for t, c in (("wind", WIND), ("solar", SOLAR)):
        ax.plot(years, gen[t].loc[years], color=c, marker="o", ms=4.5)
        ax.annotate(f"{t.title()} {gen[t].loc[2025]:.0f} TWh", (2025, gen[t].loc[2025]), xytext=(6, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=8.5)
    ax.set_title("B · Actual generation, calendar year (TWh)")
    ax.set_xlim(2014.6, 2026.6)
    ax.set_ylim(0)

    ax = fig.add_subplot(gs[1, 0])
    for t, c in (("wind", WIND), ("solar", SOLAR)):
        avgcap = (cap[t] + cap[t].shift(1)) / 2  # mean of start/end-of-year capacity
        cf = gen[t] / (avgcap * 8.76) * 100
        ax.plot(years, cf.loc[years], color=c, marker="o", ms=4.5, label=t.title())
        ax.annotate(f"{cf.loc[2025]:.1f}%", (2025, cf.loc[2025]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=INK, fontsize=8.5)
    ax.annotate("2019: Ember repeats its 2018 solar\nvalue (37.45 TWh) — likely data\nartifact; CEA FY19-20 = 50.1 TWh",
                (2019, 13.6), xytext=(12, -32), textcoords="offset points", fontsize=7.5, color=INK2,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_title("C · Implied capacity factor, annual (%, derived)")
    ax.set_xlim(2014.6, 2026.6)
    ax.set_ylim(0, 30)
    ax.legend(loc="lower right", ncol=2)

    ax = fig.add_subplot(gs[1, 1])
    for t, c in (("wind", WIND), ("solar", SOLAR)):
        cp, gn = cea_cap(f"{t}_capacity"), cea_gen(f"gen_{t}")
        idx = gn.index.intersection(cp.index)
        prev = cp.shift(1).reindex(idx)
        avg = ((cp.reindex(idx) + prev) / 2).fillna(cp.reindex(idx))
        hours = np.array([p.days_in_month * 24 for p in idx])
        cf = gn.reindex(idx) / (avg * hours / 1000) * 100  # MU / (MW*h/1000) -> %
        ax.plot(idx.to_timestamp(), cf, color=c, lw=1.6, label=t.title())
    ax.axvspan(pd.Timestamp("2025-01-01"), pd.Timestamp("2026-10-01"), color=GRID, alpha=0.5, lw=0)
    ax.text(pd.Timestamp("2025-02-01"), 47, "official curtailment\ndata period", fontsize=7.5, color=INK2, va="top")
    ax.set_title("D · Implied capacity factor, monthly, CEA (%, derived)")
    ax.set_ylim(0, 50)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper left", ncol=2)

    footer(fig, "Sources: A–C Ember yearly electricity data (India; capacity at year end, generation by calendar year) — "
           "CAP-005 / GEN-EMBER-YEARLY-GLOBAL. D: CEA monthly installed capacity reports (CAP-001) and CEA monthly RE "
           "generation (GEN-CEA-RE-MONTHLY), Aug 2018–Sep 2026.\nDerived: capacity factor = generation ÷ (average of "
           "start- and end-of-period capacity × hours). Capacity factors use AC capacity as reported; behind-the-meter "
           "rooftop output is under-counted in grid generation, so solar CF is understated. Full links: source_register.csv.")
    save(fig, "graph1_capacity_vs_generation")


# ---------------------------------------------------------------- Graph 2
def graph2():
    pm = read_csv("processed/prices/prices_monthly_summary.csv")
    nz = read_csv("processed/prices/near_zero_price_stats_monthly.csv")
    gm = read_csv("processed/generation_demand/gen_monthly_india.csv")
    hr = read_csv("processed/generation_demand/hourly_india.csv",
                  usecols=["period_start", "demand_met_mw", "solar_mw", "wind_mw"])
    dam = read_csv("processed/prices/iex_dam_blocks.csv", usecols=["date", "block_start", "mcp_rs_mwh"])

    def mser(df, market, metric):
        s = df[(df.market == market) & (df.metric == metric) & (df.granularity == "monthly")].copy()
        s["m"] = pd.to_datetime(s.period_start)
        return s.set_index("m").value.sort_index()

    t0, t1 = pd.Timestamp("2015-01-01"), pd.Timestamp("2026-11-30")
    fig = plt.figure(figsize=(13, 10))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.55, 1], hspace=0.5, wspace=0.16, top=0.89, bottom=0.09)
    fig.suptitle("Graph 2 · India: wind & solar generation vs exchange electricity prices (IEX DAM / RTM)",
                 x=0.01, ha="left", fontsize=13.5, fontweight="bold", color=INK, y=0.995)
    fig.text(0.01, 0.935, "Since 2021 solar-hour prices sit below other hours, and the gap widened from ₹0.85 to ₹4.24/kWh (2026). Low "
             "prices are not new (2015–17, mostly at night), but since 2024 they recur at midday: 1,329 of 1,443 DAM\n"
             "blocks ≤ ₹1/kWh in 2025 were in solar hours. Higher wind+solar share ⇒ lower price (D). RTM cleared at ₹0 "
             "on three days in 2026.",
             fontsize=9.5, color=INK2)

    # A: wind+solar share of generation, Ember monthly
    ax = fig.add_subplot(gs[0, 0])
    sh = pick(gm, metric="share_wind_and_solar", geography="India").copy()
    if sh.empty:
        ws = pick(gm, metric="gen_wind_and_solar", geography="India").set_index("period_start").value
        tot = pick(gm, metric="gen_total_generation", geography="India").set_index("period_start").value
        sh = (ws / tot * 100).rename("value").reset_index()
    sh["m"] = pd.to_datetime(sh.period_start)
    sh = sh.set_index("m").value.sort_index()
    ax.fill_between(sh.index, sh.values, color=AQUA, alpha=0.18, lw=0)
    ax.plot(sh.index, sh.values, color=AQUA, lw=1.8)
    mx = sh.idxmax()
    ax.annotate(f"{sh.max():.1f}% ({mx:%b %Y})", (mx, sh.max()), xytext=(-110, 2), textcoords="offset points",
                fontsize=8, color=INK)
    ax.set_title("A · Wind + solar share of monthly generation (%, Ember, from 2019)")
    ax.set_xlim(t0, t1)
    ax.set_ylim(0, 25)

    # B: solar-hour vs non-solar-hour avg DAM MCP
    ax = fig.add_subplot(gs[1, 0], sharex=fig.axes[0])
    s_sol = mser(pm, "IEX DAM", "avg_mcp_solar_hours_0900_1700")
    s_non = mser(pm, "IEX DAM", "avg_mcp_non_solar_hours")
    unit = pm[pm.metric == "avg_mcp_solar_hours_0900_1700"].unit.iloc[0]
    k = 0.001 if "MWh" in unit else 1.0
    s_sol, s_non = s_sol[s_sol.index >= t0] * k, s_non[s_non.index >= t0] * k
    ax.plot(s_non.index, s_non.values, color=VIOLET, lw=1.6, label="Other hours (17:00–09:00)")
    ax.plot(s_sol.index, s_sol.values, color=YELLOW, lw=1.6, label="Solar hours (09:00–17:00)")
    ax.set_title("B · Average IEX day-ahead price by time of day (₹/kWh, monthly)")
    ax.set_ylim(0)
    ax.legend(loc="upper left", ncol=2)

    # C: near-zero blocks per month
    ax = fig.add_subplot(gs[2, 0], sharex=fig.axes[0])
    d = mser(nz, "IEX DAM", "blocks_le_1")
    r = mser(nz, "IEX RTM", "blocks_le_1")
    d, r = d[d.index >= t0], r[r.index >= t0]
    w = 13
    ax.bar(d.index - pd.Timedelta(days=7), d.values, width=w, color=BLUE, label="DAM", align="center")
    ax.bar(r.index + pd.Timedelta(days=7), r.values, width=w, color=ORANGE, label="RTM (from Jun 2020)", align="center")
    ax.set_title("C · 15-min blocks per month clearing at ≤ ₹1/kWh (derived)")
    ax.legend(loc="upper left", ncol=2)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for a in fig.axes[:2]:
        plt.setp(a.get_xticklabels(), visible=False)

    # D: 15-min scatter (density) of wind+solar share of demand vs DAM MCP
    ax = fig.add_subplot(gs[:, 1])
    hr["ts"] = pd.to_datetime(hr.period_start)
    hr["share"] = (hr.solar_mw + hr.wind_mw) / hr.demand_met_mw * 100
    dam["ts"] = pd.to_datetime(dam.date + "T" + dam.block_start)
    j = hr.merge(dam[["ts", "mcp_rs_mwh"]], on="ts").dropna(subset=["share", "mcp_rs_mwh"])
    j = j[(j.share >= 0) & (j.share <= 100)]
    j["p"] = j.mcp_rs_mwh / 1000
    hb = ax.hexbin(j.share, j.p, gridsize=45, mincnt=1, cmap=matplotlib.colors.ListedColormap(SEQ), bins="log",
                   linewidths=0.2, edgecolors=SURFACE)
    # median price per 5-pt share bin
    bins = np.arange(0, 50, 2.5)
    j["b"] = pd.cut(j.share, bins)
    med = j.groupby("b", observed=True).p.median()
    cnt = j.groupby("b", observed=True).p.size()
    mids = np.array([iv.mid for iv in med.index])
    keep = cnt.values >= 30
    ax.plot(mids[keep], med.values[keep], color=ORANGE, lw=2.2, marker="o", ms=4,
            label="Median price per 2.5-pt bin")
    ax.set_title(f"D · Each 15-min block, Nov 2024–Nov 2026 (n={len(j):,})")
    ax.set_xlabel("Wind + solar output as % of all-India demand met (Grid-India SCADA)")
    ax.set_ylabel("IEX DAM market clearing price (₹/kWh)")
    ax.set_ylim(-0.2, 10.4)
    ax.set_xlim(0, j.share.max() + 2)
    ax.legend(loc="center right")
    cb = fig.colorbar(hb, ax=ax, orientation="horizontal", pad=0.09, fraction=0.035, aspect=40)
    cb.set_label("blocks per cell (log scale)", color=INK2, fontsize=8)
    cb.outline.set_visible(False)

    footer(fig, "Sources: A Ember monthly electricity data (GEN-EMBER-MONTHLY-GLOBAL). B–C IEX market snapshot API, "
           "15-min DAM from 2015 and RTM from Jun 2020 (PRC-001/002; derived monthly stats). D Grid-India daily PSP "
           "time-series sheet, 15-min SCADA (GEN-GI-PSP-DAILY, from 4 Nov 2024) joined to IEX DAM 15-min MCP.\n"
           "₹1/kWh = ₹1,000/MWh. CERC bid range ₹0–10/kWh since Apr 2023 (ceiling visible as the top band). "
           "Excludes 232 RTM no-trade blocks. 2026 runs to 3–4 Nov. Full links: source_register.csv.", y=0.0)
    save(fig, "graph2_re_generation_vs_prices")


# ---------------------------------------------------------------- Graph 3
def graph3():
    cs = read_csv("processed/curtailment_forecast/curtailment_timeseries.csv")
    st = read_csv("processed/capacity_storage/storage_capacity.csv")
    tg = read_csv("processed/transmission/re_complex_tgna_margin.csv")

    ind = cs[cs.geography == "India"].copy()
    ind["m"] = pd.to_datetime(ind.period_start)
    mon = ind[ind.granularity == "monthly"]
    series = [("VRE curtailment (Section 8) - solar", "Solar · state & ISTS curtailment (S8)", ORANGE),
              ("VRE curtailment (Section 8) - wind", "Wind · state & ISTS curtailment (S8)", BLUE),
              ("Emergency TRAS Down (Section 9) - solar", "Solar · emergency TRAS-down, grid security (S9)", YELLOW),
              ("Emergency TRAS Down (Section 9) - wind", "Wind · emergency TRAS-down, grid security (S9)", AQUA)]
    months = pd.date_range("2025-01-01", mon.m.max(), freq="MS")
    tab = pd.DataFrame({lbl: mon[mon.metric == met].groupby("m").value.sum().reindex(months).fillna(0)
                        for met, lbl, _ in series})
    # coverage: report days per month (from notes "N daily reports available")
    cov = mon[mon.metric == series[0][0]].set_index("m").notes.str.extract(r"(\d+) daily reports")[0]
    cov = cov.astype(float).reindex(months)

    daily = ind[ind.granularity == "daily"].groupby("m").value.sum()  # all four sections summed per day
    dmax = daily.groupby(daily.index.to_period("M")).max()
    dmax.index = dmax.index.to_timestamp()

    fig = plt.figure(figsize=(12.5, 12))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.15, 1, 1], hspace=0.62, wspace=0.16, top=0.88, bottom=0.17)
    fig.suptitle("Graph 3 · India: renewable curtailment vs battery storage and grid absorption capacity",
                 x=0.01, ha="left", fontsize=13.5, fontweight="bold", color=INK, y=0.985)
    fig.text(0.01, 0.94, "Curtailment rose from mid-2025, mostly as emergency backing-down for grid security (S9). Operational batteries "
             "(14.5 GWh, Sep 2026) equal ~10% of the worst\ncurtailment day (140.8 GWh, 2 May 2026). In Rajasthan and "
             "Khavda ~19 GW of connected plants lack firm transmission access and inject only within T-GNA margins.", fontsize=9.5, color=INK2)

    ax = fig.add_subplot(gs[0, :])
    bottom = np.zeros(len(months))
    for _, lbl, c in series:
        ax.bar(months, tab[lbl].values, width=24, bottom=bottom, color=c, label=lbl, edgecolor=SURFACE, linewidth=1)
        bottom += tab[lbl].values
    for m, v, n in zip(months, bottom, cov.values):
        if v > 0:
            ax.text(m, v + 12, f"{v:,.0f}", ha="center", fontsize=7.3, color=INK)
        if not np.isnan(n) and n < 25:
            ax.text(m, -70, f"{int(n)}d", ha="center", fontsize=7, color=RED)
    ax.set_ylim(-95, bottom.max() * 1.18)
    ax.axhline(0, color=GRID, lw=0.8)
    ax.set_title("A · Curtailed wind & solar energy per month (MU = GWh), Grid-India daily VRE reports (derived sums)", pad=40)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.04), ncol=2, fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.text(1.0, -0.3, "red “Nd” = only N daily reports in that month (sum understated). "
            "Section 9 reported from May–Jun 2025.", transform=ax.transAxes, ha="right", fontsize=7.3, color=RED)

    # B: GWh comparison: worst curtailment day vs operational BESS energy
    ax = fig.add_subplot(gs[1, :], sharex=fig.axes[0])
    ax.bar(dmax.index, dmax.values, width=24, color="#f3b49b", label="Largest single-day curtailment in month (GWh/day)",
           edgecolor=SURFACE, linewidth=1)
    b = st[(st.geography == "India") & (st.status == "operational") & (st.source_id == "CAP-002")
           & (st.metric == "bess_energy_capacity")].copy()
    b["m"] = pd.to_datetime(b.period_start)
    b = b.sort_values("m")
    early, late = b[b.m < "2026-01-01"], b[b.m >= "2026-01-01"]  # no CEA data Apr 2025-Apr 2026: don't bridge
    ax.plot(late.m, late.value / 1000, color=VIOLET, marker="o", ms=6, lw=2,
            label="Operational battery storage, CEA (GWh energy capacity; no CEA data Apr 2025–Apr 2026)")
    ax.plot(early.m, early.value / 1000, color=VIOLET, marker="o", ms=6, lw=0)
    for m, v in zip(b.m, b.value / 1000):
        ax.annotate(f"{v:.1f}", (m, v), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7.8,
                    color=INK)
    ax.set_title("B · Same unit, GWh: biggest curtailment day vs installed battery energy capacity")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylim(0, max(dmax.max(), (b.value / 1000).max()) * 1.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))

    # C: grid absorption at the two big ISTS RE complexes (MW)
    for i, (geo, name) in enumerate((("Rajasthan ISTS RE", "C · Rajasthan ISTS RE complex"),
                                     ("Gujarat (Khavda) ISTS RE", "D · Khavda (Gujarat) ISTS RE complex"))):
        ax = fig.add_subplot(gs[2, i])
        t = tg[tg.geography.isin([geo, "(Khavda) ISTS RE"] if "Khavda" in geo else [geo])].copy()
        t["d"] = pd.to_datetime(t.period_start)

        def ser(metric):
            return t[t.metric == metric].groupby("d").value.max().sort_index() / 1000

        lines = [("connectivity_quantum_commissioned", "Commissioned & connected", INK2, "-"),
                 ("gna_effective", "With firm access (GNA effective)", BLUE, "-"),
                 ("tgna_injection_limit_max_over_day", "T-GNA injection limit for plants w/o firm access (max of day)", ORANGE, "-"),
                 ("tgna_injection_limit_min_over_day", "T-GNA injection limit (min of day, usually midday)", ORANGE, ":")]
        for met, lbl, c, ls in lines:
            s = ser(met)
            if len(s):
                ax.plot(s.index, s.values, color=c, ls=ls, lw=1.8 if ls == "-" else 1.6, label=lbl)
        com, gna = ser("connectivity_quantum_commissioned"), ser("gna_effective")
        if len(com) and len(gna):
            j = pd.concat([com, gna], axis=1).dropna()
            ax.fill_between(j.index, j.iloc[:, 1], j.iloc[:, 0], color=RED, alpha=0.08, lw=0)
            last = j.index[-1]
            ax.annotate(f"{(j.iloc[-1, 0] - j.iloc[-1, 1]):.1f} GW\nwithout firm access", (last, j.iloc[-1].mean()),
                        xytext=(-6, 0), textcoords="offset points", ha="right", va="center", fontsize=7.8, color=RED)
        ax.set_title(f"{name} (GW)")
        ax.set_ylim(0)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        if i == 0:
            ax.legend(loc="lower left", bbox_to_anchor=(0, -0.5), ncol=2, fontsize=7.4)
            ax.annotate("dips = issues listing\nfewer pooling stations", (pd.Timestamp("2026-03-12"), 20.4),
                        xytext=(-10, -38), textcoords="offset points", fontsize=7, color=INK2, ha="center",
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))

    footer(fig, "Sources: A–B Grid-India Daily VRE (REMC) report, Section 8 'VRE curtailment details' and Section 9 "
           "'Emergency TRAS down' (CUR-001; parsed daily, summed by month — derived; 17 rows where MW was typed into the "
           "MU column excluded). B battery: CEA monthly BESS status reports, projects ≥1 MWh (CAP-002).\nC–D Grid-India "
           "T-GNA margin statements for ISTS RE complexes, Nov 2025–Oct 2026 (TRN- sources in register). A battery "
           "absorbs at most ~its GWh rating per daily cycle and only where it is sited; no official curtailment series "
           "exists before Jan 2025.", y=0.0)
    save(fig, "graph3_curtailment_vs_storage_grid")


if __name__ == "__main__":
    which = set(sys.argv[2:]) or {"1", "2", "3"}
    if "1" in which:
        graph1()
    if "2" in which:
        graph2()
    if "3" in which:
        graph3()
