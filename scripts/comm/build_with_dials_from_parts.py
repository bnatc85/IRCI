import argparse, pandas as pd

def read_csv(path, cols, rename=None):
    df = pd.read_csv(path)
    if rename: df = df.rename(columns=rename)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise SystemExit(f"{path}: missing columns {missing}. Has {list(df.columns)}")
    return df[cols]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", required=True, help="CSV with ticker,quarter,cov_pct")
    ap.add_argument("--trust",    required=True, help="CSV with ticker,quarter,trust_pct")
    ap.add_argument("--liquidity",required=True, help="CSV with ticker,quarter,liq_pct")
    ap.add_argument("--valuation",required=True, help="CSV with ticker,quarter,val_pct,val_metric")
    ap.add_argument("--ev",       required=True, help="CSV with ticker,quarter,ev_usd")
    ap.add_argument("--peers",    required=True, help="CSV with 'symbol' column (commons only)")
    ap.add_argument("--out",      default="data/comm/irci_comm_quarterly_with_dials.csv")
    args = ap.parse_args()

    cov = read_csv(args.coverage, ["ticker","quarter","cov_pct"])
    tru = read_csv(args.trust,    ["ticker","quarter","trust_pct"])
    liq = read_csv(args.liquidity,["ticker","quarter","liq_pct"])
    val = read_csv(args.valuation,["ticker","quarter","val_pct","val_metric"])
    ev  = read_csv(args.ev,       ["ticker","quarter","ev_usd"])

    peers = pd.read_csv(args.peers)["symbol"].astype(str).str.upper().tolist()

    df = cov.merge(tru, on=["ticker","quarter"], how="outer") \
            .merge(liq, on=["ticker","quarter"], how="outer") \
            .merge(val, on=["ticker","quarter"], how="outer") \
            .merge(ev,  on=["ticker","quarter"], how="outer")

    # keep only peers we care about, normalize types
    df["ticker"]  = df["ticker"].astype(str).str.upper()
    df["quarter"] = df["quarter"].astype(str).str.strip()
    df = df[df["ticker"].isin(peers)].copy()

    # coerce numerics, drop rows missing any required numeric
    for c in ["cov_pct","trust_pct","liq_pct","val_pct","ev_usd","val_metric"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["cov_pct","trust_pct","liq_pct","val_pct","ev_usd","val_metric"])
    print(f"[info] merged rows: {before} -> {len(df)} after dropping NaNs")

    # sanity: at least 3 names per quarter
    sizes = df.groupby("quarter")["ticker"].nunique()
    print("[info] names per quarter:\n", sizes)

    df.to_csv(args.out, index=False)
    print(f"[ok] wrote {args.out} with {len(df)} rows, {df['ticker'].nunique()} tickers, {df['quarter'].nunique()} quarters")
