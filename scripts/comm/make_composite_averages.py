#!/usr/bin/env python
import argparse
import pandas as pd
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="out/comm/irci_comm_quarterly_with_dials.csv")
    ap.add_argument("--outdir", default="out/comm")
    args = ap.parse_args()

    src = Path(args.inp)
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src)
    if "ticker" not in df.columns or "irci_composite_pct" not in df.columns:
        raise SystemExit(f"Expected columns 'ticker' and 'irci_composite_pct' in {src}")

    # Per-ticker stats across all quarters
    by_ticker = (
        df.groupby("ticker", as_index=False)
          .agg(
              quarters=("quarter","nunique"),
              mean_composite_pct=("irci_composite_pct","mean"),
              median_composite_pct=("irci_composite_pct","median"),
              min_composite_pct=("irci_composite_pct","min"),
              max_composite_pct=("irci_composite_pct","max"),
          )
    )
    for c in ["mean_composite_pct","median_composite_pct","min_composite_pct","max_composite_pct"]:
        by_ticker[c] = by_ticker[c].round(2)
    by_ticker = by_ticker.sort_values("mean_composite_pct", ascending=False).reset_index(drop=True)

    # Overall (portfolio-level)
    overall = pd.DataFrame({
        "metric": ["mean_composite_pct","median_composite_pct"],
        "value": [
            round(df["irci_composite_pct"].mean(), 2),
            round(df["irci_composite_pct"].median(), 2),
        ]
    })

    # Latest quarter snapshot (nice for a sidebar in the slide)
    latest_q = str(sorted(df["quarter"].astype(str).unique())[-1])
    latest = (df[df["quarter"].astype(str)==latest_q]
              .groupby("ticker", as_index=False)["irci_composite_pct"].mean()
              .rename(columns={"irci_composite_pct":"latest_composite_pct"}))
    latest["latest_composite_pct"] = latest["latest_composite_pct"].round(2)

    # Save
    p1 = outdir / "irci_comm_composite_averages_by_ticker.csv"
    p2 = outdir / "irci_comm_composite_overall.csv"
    p3 = outdir / "irci_comm_latest_quarter.csv"
    by_ticker.to_csv(p1, index=False)
    overall.to_csv(p2, index=False)
    latest.to_csv(p3, index=False)
    print(f"[ok] wrote:\n  {p1}\n  {p2}\n  {p3}")

if __name__ == "__main__":
    main()
