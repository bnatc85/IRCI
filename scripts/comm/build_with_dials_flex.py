import argparse, pandas as pd

def load_map(path, tcol, qcol, vcol, keep):
    df = pd.read_csv(path)
    rename = {tcol: "ticker", qcol: "quarter", vcol: keep}
    missing = [c for c in [tcol, qcol, vcol] if c not in df.columns]
    if missing:
        raise SystemExit(f"{path}: missing required column(s): {missing}. Has {list(df.columns)}")
    out = df.rename(columns=rename)[["ticker","quarter",keep]]
    return out

def load_two(path, tcol, qcol, p1, p2, k1, k2):
    df = pd.read_csv(path)
    for c in [tcol, qcol, p1, p2]:
        if c not in df.columns:
            raise SystemExit(f"{path}: missing column {c}. Has {list(df.columns)}")
    return df.rename(columns={tcol:"ticker", qcol:"quarter", p1:k1, p2:k2})[["ticker","quarter",k1,k2]]

def normalize(df):
    df["ticker"]  = df["ticker"].astype(str).str.upper().str.strip()
    df["quarter"] = df["quarter"].astype(str).str.strip()
    # numeric coercion
    for c in ["cov_pct","trust_pct","liq_pct","val_pct","ev_usd","val_metric"]:
        if c in df.columns:
            df[c] = (df[c].astype(str).str.replace("%","",regex=False)
                               .str.replace(",","",regex=False))
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Merge real dial exports → canonical with_dials file")
    # Coverage
    ap.add_argument("--coverage-file", required=True)
    ap.add_argument("--coverage-ticker-col", required=True)
    ap.add_argument("--coverage-quarter-col", required=True)
    ap.add_argument("--coverage-value-col", required=True)   # maps → cov_pct
    # Trust
    ap.add_argument("--trust-file", required=True)
    ap.add_argument("--trust-ticker-col", required=True)
    ap.add_argument("--trust-quarter-col", required=True)
    ap.add_argument("--trust-value-col", required=True)      # maps → trust_pct
    # Liquidity
    ap.add_argument("--liquidity-file", required=True)
    ap.add_argument("--liquidity-ticker-col", required=True)
    ap.add_argument("--liquidity-quarter-col", required=True)
    ap.add_argument("--liquidity-value-col", required=True)  # maps → liq_pct
    # Valuation (percentile + metric)
    ap.add_argument("--valuation-file", required=True)
    ap.add_argument("--valuation-ticker-col", required=True)
    ap.add_argument("--valuation-quarter-col", required=True)
    ap.add_argument("--valuation-pct-col", required=True)    # maps → val_pct
    ap.add_argument("--valuation-metric-col", required=True) # maps → val_metric (e.g., ev_ebitda)
    # EV
    ap.add_argument("--ev-file", required=True)
    ap.add_argument("--ev-ticker-col", required=True)
    ap.add_argument("--ev-quarter-col", required=True)
    ap.add_argument("--ev-value-col", required=True)         # maps → ev_usd
    # peers + out
    ap.add_argument("--peers", required=True)
    ap.add_argument("--out", default="data/comm/irci_comm_quarterly_with_dials.csv")
    args = ap.parse_args()

    cov = load_map(args.coverage_file, args.coverage_ticker_col, args.coverage_quarter_col,
                   args.coverage_value_col, "cov_pct")
    tru = load_map(args.trust_file, args.trust_ticker_col, args.trust_quarter_col,
                   args.trust_value_col, "trust_pct")
    liq = load_map(args.liquidity_file, args.liquidity_ticker_col, args.liquidity_quarter_col,
                   args.liquidity_value_col, "liq_pct")
    val = load_two(args.valuation_file, args.valuation_ticker_col, args.valuation_quarter_col,
                   args.valuation_pct_col, args.valuation_metric_col, "val_pct", "val_metric")
    ev  = load_map(args.ev_file, args.ev_ticker_col, args.ev_quarter_col,
                   args.ev_value_col, "ev_usd")

    peers = pd.read_csv(args.peers)["symbol"].astype(str).str.upper().tolist()

    df = cov.merge(tru, on=["ticker","quarter"], how="outer") \
            .merge(liq, on=["ticker","quarter"], how="outer") \
            .merge(val, on=["ticker","quarter"], how="outer") \
            .merge(ev,  on=["ticker","quarter"], how="outer")

    df = normalize(df)
    df = df[df["ticker"].isin(peers)].copy()

    before = len(df)
    df = df.dropna(subset=["cov_pct","trust_pct","liq_pct","val_pct","ev_usd","val_metric"])
    print(f"[info] merged rows: {before} → {len(df)} after dropping NaNs")
    print("[info] names per quarter:\n", df.groupby("quarter")["ticker"].nunique())

    df.to_csv(args.out, index=False)
    print(f"[ok] wrote {args.out} with {len(df)} rows, {df['ticker'].nunique()} tickers, {df['quarter'].nunique()} quarters")
