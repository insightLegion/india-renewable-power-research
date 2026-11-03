"""DERIVED statistics from the IEX 15-min block files (inputs kept in data/processed/prices/iex_*_blocks.csv).

Outputs (data/processed/prices/):
  prices_daily_summary.csv          wide: one row per market x delivery date
  prices_monthly_summary.csv        long (CONVENTIONS columns): monthly + annual metrics per market
  near_zero_price_stats_monthly.csv long: near-zero block counts/hours/share + longest daily run, monthly + annual
  near_zero_by_hour.csv             long: count of near-zero blocks by hour of day, per market x calendar year
  near_zero_area_prices_monthly.csv long: DAM/GDAM area (bid-area) near-zero block counts per month

Rules:
  * Blocks flagged no_trade (zero bids and zero volume) are excluded from all price statistics.
  * Incomplete days with fewer than 90 traded blocks are excluded from daily/monthly stats (RTM 2026-11-03 is
    an in-progress day at download time). Other days with 94-95 traded blocks are kept (n_blocks reported).
  * Solar hours = blocks starting 09:00..16:45 IST (09:00-17:00); non-solar = all other blocks.
  * Thresholds on MCP: floor (MCP == Rs 0/MWh, the CERC lower bid limit), <= Rs 0.1/kWh, <= 0.5, <= 1, <= 2.
  * avg_mcp = simple mean of block MCPs; vw_mcp = MCV-weighted mean. Volumes are MW per block; energy MWh = MW x 0.25.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "processed" / "prices"
SRC = {"dam": "PRC-001", "rtm": "PRC-002", "gdam": "PRC-003"}
MKT_NAME = {"dam": "IEX DAM", "rtm": "IEX RTM", "gdam": "IEX GDAM"}
THR = {"floor_0": 0.0, "le_0.1": 100.0, "le_0.5": 500.0, "le_1": 1000.0, "le_2": 2000.0}
THR_LABEL = {"floor_0": "MCP = Rs 0/kWh (floor)", "le_0.1": "MCP <= Rs 0.1/kWh", "le_0.5": "MCP <= Rs 0.5/kWh",
             "le_1": "MCP <= Rs 1/kWh", "le_2": "MCP <= Rs 2/kWh"}
DERIVED = "DERIVED from IEX 15-min block data (scripts/prices/04_derive_price_stats.py)"


def longest_run(mask: np.ndarray) -> int:
    best = cur = 0
    for v in mask:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def load(mkt):
    d = pd.read_csv(P / f"iex_{mkt}_blocks.csv")
    d = d[~d["no_trade"]].copy()
    n = d.groupby("date")["block_no"].transform("size")
    d = d[n >= 90].copy()
    sell_col = "sell_bid_mw" if "sell_bid_mw" in d.columns else "total_sell_bid_mw"
    mcv_col = "mcv_mw" if "mcv_mw" in d.columns else "total_cleared_volume_mw"
    d["sell"] = d[sell_col]
    d["mcv"] = d[mcv_col]
    d["buy"] = d["purchase_bid_mw"]
    d["solar"] = (d["block_no"] >= 37) & (d["block_no"] <= 68)  # 09:00 .. 16:45 start
    d["month"] = d["date"].str[:7]
    d["year"] = d["date"].str[:4]
    d["hour"] = (d["block_no"] - 1) // 4
    for k, v in THR.items():
        d[k] = d["mcp_rs_mwh"] <= v if k != "floor_0" else d["mcp_rs_mwh"] == 0.0
    return d


def daily(d, mkt):
    g = d.groupby("date")
    out = pd.DataFrame({
        "n_blocks": g.size(),
        "avg_mcp_rs_mwh": g["mcp_rs_mwh"].mean(),
        "vw_mcp_rs_mwh": g.apply(lambda x: np.average(x["mcp_rs_mwh"], weights=x["mcv"]) if x["mcv"].sum() > 0 else np.nan,
                                 include_groups=False),
        "min_mcp_rs_mwh": g["mcp_rs_mwh"].min(),
        "max_mcp_rs_mwh": g["mcp_rs_mwh"].max(),
        "avg_mcp_solar_0900_1700_rs_mwh": d[d.solar].groupby("date")["mcp_rs_mwh"].mean(),
        "avg_mcp_nonsolar_rs_mwh": d[~d.solar].groupby("date")["mcp_rs_mwh"].mean(),
        "purchase_bid_mwh": g["buy"].sum() * 0.25,
        "sell_bid_mwh": g["sell"].sum() * 0.25,
        "cleared_volume_mwh": g["mcv"].sum() * 0.25,
        "sell_buy_ratio": g["sell"].sum() / g["buy"].sum(),
        "sell_buy_ratio_solar": d[d.solar].groupby("date")["sell"].sum() / d[d.solar].groupby("date")["buy"].sum(),
    })
    for k in THR:
        out[f"n_blocks_{k}"] = g[k].sum()
        out[f"longest_run_blocks_{k}"] = g[k].apply(lambda s: longest_run(s.to_numpy()))
    out["source_id"] = SRC[mkt]
    out = out.reset_index()
    out.insert(0, "market", MKT_NAME[mkt])
    return out


def long_rows(rows, mkt, period_start, period_end, gran, metric, value, unit, notes=""):
    rows.append({"geography": "India", "market": MKT_NAME[mkt], "period_start": period_start, "period_end": period_end,
                 "granularity": gran, "metric": metric, "value": value, "unit": unit,
                 "source_id": SRC[mkt], "notes": (DERIVED + ("; " + notes if notes else ""))})


def period_bounds(key, gran, dates):
    return dates.min(), dates.max()


def monthly(d, dd, mkt, rows_sum, rows_nz):
    for gran, col in (("monthly", "month"), ("annual", "year")):
        for key, x in d.groupby(col):
            xd = dd[dd["date"].str.startswith(key)]
            ps, pe = x["date"].min(), x["date"].max()
            ndays = x["date"].nunique()
            note = f"{ndays} days, {len(x)} traded blocks; covers {ps}..{pe}"
            m = lambda metric, v, unit: long_rows(rows_sum, mkt, ps, pe, gran, metric, round(float(v), 4) if pd.notna(v) else None, unit, note)
            m("avg_mcp", x["mcp_rs_mwh"].mean() / 1000, "Rs/kWh")
            m("vw_mcp", np.average(x["mcp_rs_mwh"], weights=x["mcv"]) / 1000 if x["mcv"].sum() > 0 else np.nan, "Rs/kWh")
            m("min_mcp", x["mcp_rs_mwh"].min() / 1000, "Rs/kWh")
            m("max_mcp", x["mcp_rs_mwh"].max() / 1000, "Rs/kWh")
            m("avg_mcp_solar_hours_0900_1700", x.loc[x.solar, "mcp_rs_mwh"].mean() / 1000, "Rs/kWh")
            m("avg_mcp_non_solar_hours", x.loc[~x.solar, "mcp_rs_mwh"].mean() / 1000, "Rs/kWh")
            m("avg_daily_min_mcp", xd["min_mcp_rs_mwh"].mean() / 1000, "Rs/kWh")
            m("sell_buy_bid_ratio", x["sell"].sum() / x["buy"].sum(), "ratio")
            m("sell_buy_bid_ratio_solar_hours", x.loc[x.solar, "sell"].sum() / x.loc[x.solar, "buy"].sum(), "ratio")
            m("sell_buy_bid_ratio_non_solar_hours", x.loc[~x.solar, "sell"].sum() / x.loc[~x.solar, "buy"].sum(), "ratio")
            m("purchase_bid_volume", x["buy"].sum() * 0.25 / 1000, "GWh")
            m("sell_bid_volume", x["sell"].sum() * 0.25 / 1000, "GWh")
            m("cleared_volume", x["mcv"].sum() * 0.25 / 1000, "GWh")
            m("uncleared_sell_bid_volume_solar_hours", (x.loc[x.solar, "sell"] - x.loc[x.solar, "mcv"]).sum() * 0.25 / 1000, "GWh")
            for k, lab in THR_LABEL.items():
                n = int(x[k].sum())
                ns = int(x.loc[x.solar, k].sum())
                long_rows(rows_nz, mkt, ps, pe, gran, f"blocks_{k}", n, "15-min blocks", f"{lab}; {note}")
                long_rows(rows_nz, mkt, ps, pe, gran, f"hours_{k}", n / 4, "hours", f"{lab}; equivalent hours = blocks/4; {note}")
                long_rows(rows_nz, mkt, ps, pe, gran, f"share_blocks_{k}", round(100 * n / len(x), 3), "%", f"{lab}; share of traded blocks; {note}")
                long_rows(rows_nz, mkt, ps, pe, gran, f"blocks_{k}_in_solar_hours", ns, "15-min blocks", f"{lab}; blocks starting 09:00-16:45; {note}")
                long_rows(rows_nz, mkt, ps, pe, gran, f"days_with_any_{k}", int((xd[f'n_blocks_{k}'] > 0).sum()), "days", f"{lab}; {note}")
                lr = xd[f"longest_run_blocks_{k}"]
                if lr.max() > 0:
                    day = xd.loc[lr.idxmax(), "date"]
                    long_rows(rows_nz, mkt, ps, pe, gran, f"longest_daily_run_blocks_{k}", int(lr.max()), "15-min blocks",
                              f"{lab}; longest consecutive run within one delivery day, first occurring on {day}; {note}")
                else:
                    long_rows(rows_nz, mkt, ps, pe, gran, f"longest_daily_run_blocks_{k}", 0, "15-min blocks", f"{lab}; {note}")
            long_rows(rows_nz, mkt, ps, pe, gran, "traded_blocks", len(x), "15-min blocks", note)


def by_hour(d, mkt, rows):
    for (yr, hr), x in d.groupby(["year", "hour"]):
        ps, pe = x["date"].min(), x["date"].max()
        for k, lab in THR_LABEL.items():
            rows.append({"geography": "India", "market": MKT_NAME[mkt], "period_start": ps, "period_end": pe,
                         "granularity": "annual", "hour_of_day": f"{hr:02d}:00-{hr + 1:02d}:00", "threshold": lab,
                         "metric": f"blocks_{k}", "value": int(x[k].sum()), "unit": "15-min blocks",
                         "traded_blocks_in_hour": len(x), "source_id": SRC[mkt], "notes": DERIVED})


def area_stats(mkt, rows):
    a = pd.read_csv(P / f"iex_{mkt}_area_prices.csv")
    b = pd.read_csv(P / f"iex_{mkt}_blocks.csv", usecols=["date", "block_no", "no_trade"])
    a = a.merge(b, on=["date", "block_no"], how="left")
    a = a[~a["no_trade"].fillna(False)]
    a["month"] = a["date"].str[:7]
    areas = [c for c in a.columns if c.endswith("_rs_mwh") and c != "MCP_rs_mwh"]
    src = {"dam": "PRC-004", "gdam": "PRC-005"}[mkt]
    for mo, x in a.groupby("month"):
        ps, pe = x["date"].min(), x["date"].max()
        split = (x[areas].sub(x["MCP_rs_mwh"], axis=0).abs() > 0.5).any(axis=1)
        rows.append({"geography": "India", "bid_area": "ALL", "market": MKT_NAME[mkt], "period_start": ps, "period_end": pe,
                     "granularity": "monthly", "metric": "blocks_with_any_area_price_differing_from_MCP", "value": int(split.sum()),
                     "unit": "15-min blocks", "source_id": src, "notes": DERIVED + "; |area price - MCP| > Rs 0.5/MWh"})
        for c in areas:
            ar = c.replace("_rs_mwh", "")
            v = x[c]
            if v.notna().sum() == 0:
                continue
            for k, thr in (("le_0.5", 500), ("le_1", 1000), ("le_2", 2000)):
                rows.append({"geography": "India", "bid_area": ar, "market": MKT_NAME[mkt], "period_start": ps, "period_end": pe,
                             "granularity": "monthly", "metric": f"blocks_area_price_{k}", "value": int((v <= thr).sum()),
                             "unit": "15-min blocks", "source_id": src, "notes": DERIVED + f"; area clearing price <= Rs {thr / 1000}/kWh"})
            rows.append({"geography": "India", "bid_area": ar, "market": MKT_NAME[mkt], "period_start": ps, "period_end": pe,
                         "granularity": "monthly", "metric": "blocks_area_price_le_1_while_MCP_gt_1",
                         "value": int(((v <= 1000) & (x["MCP_rs_mwh"] > 1000)).sum()), "unit": "15-min blocks", "source_id": src,
                         "notes": DERIVED + "; regional near-zero caused by market splitting (area price <= Rs 1/kWh while unconstrained MCP > Rs 1/kWh)"})
            rows.append({"geography": "India", "bid_area": ar, "market": MKT_NAME[mkt], "period_start": ps, "period_end": pe,
                         "granularity": "monthly", "metric": "min_area_price", "value": round(v.min() / 1000, 4),
                         "unit": "Rs/kWh", "source_id": src, "notes": DERIVED})
            rows.append({"geography": "India", "bid_area": ar, "market": MKT_NAME[mkt], "period_start": ps, "period_end": pe,
                         "granularity": "monthly", "metric": "avg_area_price", "value": round(v.mean() / 1000, 4),
                         "unit": "Rs/kWh", "source_id": src, "notes": DERIVED})


def main():
    dailies, rows_sum, rows_nz, rows_hr, rows_area = [], [], [], [], []
    for mkt in ("dam", "rtm", "gdam"):
        d = load(mkt)
        dd = daily(d, mkt)
        dailies.append(dd)
        monthly(d, dd, mkt, rows_sum, rows_nz)
        by_hour(d, mkt, rows_hr)
        print(mkt, "done", len(d))
    pd.concat(dailies).round(4).to_csv(P / "prices_daily_summary.csv", index=False)
    pd.DataFrame(rows_sum).to_csv(P / "prices_monthly_summary.csv", index=False)
    pd.DataFrame(rows_nz).to_csv(P / "near_zero_price_stats_monthly.csv", index=False)
    pd.DataFrame(rows_hr).to_csv(P / "near_zero_by_hour.csv", index=False)
    for mkt in ("dam", "gdam"):
        area_stats(mkt, rows_area)
    pd.DataFrame(rows_area).to_csv(P / "near_zero_area_prices_monthly.csv", index=False)


if __name__ == "__main__":
    main()
