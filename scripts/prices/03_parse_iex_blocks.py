"""Parse raw IEX API JSON (data/raw/prices/iex_api) into clean 15-min block CSVs.

Outputs (data/processed/prices/):
  iex_dam_blocks.csv, iex_rtm_blocks.csv, iex_gdam_blocks.csv   (wide; one row per delivery 15-min block)
  iex_dam_area_prices.csv, iex_gdam_area_prices.csv              (wide; one row per block, one column per bid area)
  iex_block_validation.csv                                       (blocks per day, per market; incomplete days)

Volume fields are as published by IEX for 15-minute intervals, i.e. average power in MW over the block
(IEX daily summary: "Total (MWh)" = sum(block MW) x 0.25 h; verified in validation). MCP in Rs/MWh.
Usage: .venv/bin/python -I scripts/prices/03_parse_iex_blocks.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "prices" / "iex_api"
OUT = ROOT / "data" / "processed" / "prices"
OUT.mkdir(parents=True, exist_ok=True)

SRC = {"dam": "PRC-001", "rtm": "PRC-002", "gdam": "PRC-003",
       "dam_area": "PRC-004", "gdam_area": "PRC-005"}


def load(mkt, ep):
    rows = []
    for f in sorted(RAW.glob(f"{mkt}_{ep}_*.json")):
        rows += json.loads(f.read_text())["data"] or []
    return pd.DataFrame(rows)


def norm_period(df, col):
    p = df[col].astype(str).str.replace(" ", "", regex=False)
    if p.str.contains("-").all():
        start = p.str.split("-").str[0]
        end = p.str.split("-").str[1]
    else:  # area-price: 'HH:MM' start only
        start = p
        end = None
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y").dt.strftime("%Y-%m-%d")
    hh = start.str[:2].astype(int)
    mm = start.str[3:5].astype(int)
    df["block_no"] = hh * 4 + mm // 15 + 1
    df["block_start"] = start
    df["block_end"] = end if end is not None else (
        ((hh * 60 + mm + 15) // 60).astype(str).str.zfill(2) + ":" + ((mm + 15) % 60).astype(str).str.zfill(2))
    return df


def snapshot(mkt):
    df = load(mkt, "market-snapshot")
    df = norm_period(df, "period")
    num = [c for c in df.columns if c not in ("date", "period", "congestion", "block_no", "block_start", "block_end")]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if mkt in ("dam", "rtm"):
        out = pd.DataFrame({
            "date": df["date"], "block_no": df["block_no"], "block_start": df["block_start"], "block_end": df["block_end"],
            "purchase_bid_mw": df["purchase_bid"], "sell_bid_mw": df["sell_bid"], "mcv_mw": df["mcv"],
            "scheduled_volume_mw": df["final_scheduled_volume"], "mcp_rs_mwh": df["mcp"],
            "congestion": df["congestion"]})
    else:  # gdam: keep every published field; MCP field is 'unconstrained_m_c_p'
        out = df[["date", "block_no", "block_start", "block_end"]].copy()
        out["purchase_bid_mw"] = df["purchase_bid"]
        for c in sorted(num):
            if c in ("purchase_bid", "unconstrained_m_c_p"):
                continue
            out[c + "_mw"] = df[c]
        out["mcp_rs_mwh"] = df["unconstrained_m_c_p"]
        out["congestion"] = df["congestion"]
    # Blocks where IEX reports zero purchase bid, zero sell bid and zero cleared volume: no trade took place
    # (session not held/cancelled); the MCP field is then not a price (0, 5000, 6000, 10000 ... observed).
    out["no_trade"] = (out["purchase_bid_mw"].fillna(0) == 0) & (out["mcp_rs_mwh"].notna()) & \
        (out.filter(like="sell_bid").fillna(0).sum(axis=1) == 0) & \
        (out[["mcv_mw" if "mcv_mw" in out.columns else "total_cleared_volume_mw"]].fillna(0).sum(axis=1) == 0)
    # Rows with zero bids but non-zero cleared volume are data anomalies (kept, flagged in validation file)
    anomaly = (out["purchase_bid_mw"].fillna(0) == 0) & ~out["no_trade"]
    out["source_id"] = SRC[mkt]
    dup = out.duplicated(["date", "block_no"]).sum()
    out = out.drop_duplicates(["date", "block_no"]).sort_values(["date", "block_no"])
    return out, dup, out[anomaly.reindex(out.index).fillna(False)]


def area(mkt):
    df = load(mkt, "area-price")
    df = norm_period(df, "timeperiod")
    areas = ["a1", "a2", "e1", "e2", "n1", "n2", "n3", "s1", "s2", "s3", "w1", "w2", "w3", "mkt"]
    out = df[["date", "block_no", "block_start", "block_end"]].copy()
    for a in areas:
        out[(a.upper() if a != "mkt" else "MCP") + "_rs_mwh"] = pd.to_numeric(df[a], errors="coerce")
    out["source_id"] = SRC[mkt + "_area"]
    return out.drop_duplicates(["date", "block_no"]).sort_values(["date", "block_no"])


def main():
    val = []
    for mkt in ("dam", "rtm", "gdam"):
        out, dup, anom = snapshot(mkt)
        for _, r in anom.iterrows():
            val.append({"market": mkt, "date": r["date"], "blocks": 1,
                        "issue": f"block {r['block_no']}: zero purchase bid reported but non-zero cleared volume (data anomaly, kept)"})
        out.to_csv(OUT / f"iex_{mkt}_blocks.csv", index=False)
        per_day = out.groupby("date").size()
        alldays = pd.date_range(per_day.index.min(), per_day.index.max()).strftime("%Y-%m-%d")
        missing = sorted(set(alldays) - set(per_day.index))
        bad = per_day[per_day != 96]
        print(mkt, len(out), "rows", per_day.index.min(), per_day.index.max(), "dups", dup,
              "missing days", missing[:20], "non-96 days", bad.to_dict())
        for d in missing:
            val.append({"market": mkt, "date": d, "blocks": 0, "issue": "day missing"})
        for d, n in bad.items():
            have = set(out.loc[out.date == d, "block_no"])
            miss = [b for b in range(1, 97) if b not in have]
            val.append({"market": mkt, "date": d, "blocks": n, "issue": f"missing blocks {miss}"})
        nt = out[out.no_trade]
        for d, n in nt.groupby("date").size().items():
            val.append({"market": mkt, "date": d, "blocks": n, "issue": "no-trade blocks (zero bids & volume)"})
        val.append({"market": mkt, "date": "ALL", "blocks": len(out),
                    "issue": f"{per_day.index.min()}..{per_day.index.max()}; {len(per_day)} days; dup rows dropped {dup}"})
    for mkt in ("dam", "gdam"):
        a = area(mkt)
        a.to_csv(OUT / f"iex_{mkt}_area_prices.csv", index=False)
        print(mkt, "area", len(a), a.date.min(), a.date.max())
    pd.DataFrame(val).to_csv(OUT / "iex_block_validation.csv", index=False)


if __name__ == "__main__":
    main()
