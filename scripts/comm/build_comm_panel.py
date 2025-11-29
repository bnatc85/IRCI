# scripts/comm/build_comm_panel.py
import argparse, pandas as pd, numpy as np, re, sys

NEEDED = ["ticker","quarter","cov_pct","trust_pct","liq_pct","val_pct","ev_usd","val_metric"]

def normalize_headers(df):
    rename_map = {
        'symbol':'ticker', 'Symbol':'ticker',
        'Quarter':'quarter', 'quarter_end':'quarter',
        'coverage_pct':'cov_pct','coverage':'cov_pct',
        'trust':'trust_pct','liquidity_pct':'liq_pct','valuation_pct':'val_pct',
        'ev':'ev_usd','enterprise_value':'ev_usd','EV':'ev_usd',
        'ev_ebitda':'val_metric','valuation_metric':'val_metric'
    }
    for k,v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k:v})
    return df

def to_numeric(df, cols):
    for c in cols:
        df[c] = (df[c].astype(str).str.replace('%','',regex=False)
                             .str.replace(',','',regex=False))
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

def looks_common(sym):
    if '-' in sym: return False
    if sym.endswith(tuple([f'P{ch}' for ch in list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")])):
        return False
    return True

def make_composite(df, w):
    c,t,l,v = w
    return c*df['cov_pct'] + t*df['trust_pct'] + l*df['liq_pct'] + v*df['val_pct']

def zscore_by_quarter(df, col):
    return df.groupby('quarter')[col].transform(
        lambda x: (x - x.mean()) / (x.std(ddof=0) if x.std(ddof=0)!=0 else 1.0)
    )

def next_q_change(df, col):
    df = df.sort_values(['ticker','quarter'])
    return df.groupby('ticker')[col].shift(-1) - df[col]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dials", required=True, help="CSV with per-dial percentiles & valuation metric")
    ap.add_argument("--peers", required=True, help="CSV with column 'symbol'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", default="0.15,0.15,0.35,0.35", help="Weights C,T,L,V that sum to 1")
    args = ap.parse_args()

    df = pd.read_csv(args.in_dials)
    print(f"[info] read {args.in_dials}: {len(df)} rows, {len(df.columns)} cols")
    df = normalize_headers(df)
    missing = [c for c in NEEDED if c not in df.columns]
    if missing:
        print(f"[error] missing columns: {missing}")
        print("[hint] available:", list(df.columns)); sys.exit(1)

    # normalize strings
    df['ticker']  = df['ticker'].astype(str).str.strip().str.upper()
    df['quarter'] = df['quarter'].astype(str).str.strip()

    # coerce numerics
    num_cols = ["cov_pct","trust_pct","liq_pct","val_pct","ev_usd","val_metric"]
    df = to_numeric(df, num_cols)
    print("[info] NaNs per numeric col:", df[num_cols].isna().sum().to_dict())

    # peers
    peers = pd.read_csv(args.peers)['symbol'].astype(str).str.upper().tolist()
    peers_clean = [s for s in peers if looks_common(s)]
    print(f"[info] peers in file ({len(peers)}): {peers}")
    print(f"[info] peers after cleaning ({len(peers_clean)}): {peers_clean}")

    # restrict to overlap
    df0 = df.copy()
    df = df[df['ticker'].isin(peers_clean)]
    print(f"[info] rows after restricting to peers: {len(df)} (from {len(df0)})")
    print(f"[info] unique tickers after peer filter: {sorted(df['ticker'].unique().tolist())}")

    # drop quarters with <3 tickers for stable z-scores
    counts = df.groupby('quarter')['ticker'].nunique()
    good_quarters = counts[counts>=3].index
    df = df[df['quarter'].isin(good_quarters)]
    print(f"[info] quarters kept (>=3 tickers): {len(good_quarters)} / {counts.size}")

    # drop rows missing any numeric needed
    before = len(df)
    df = df.dropna(subset=num_cols)
    print(f"[info] rows after dropping NaNs in {num_cols}: {len(df)} (from {before})")

    # weights
    w = tuple(map(float, args.w.split(",")))
    if not np.isclose(sum(w), 1.0):
        print(f"[error] weights must sum to 1: {w} (sum={sum(w):.3f})"); sys.exit(1)

    # composite + targets
    if len(df)==0:
        print("[warn] no rows left; writing empty file so downstream errors are clear.")
        pd.DataFrame(columns=["ticker","quarter","irci_composite_pct","peer_gap_change_pp_nextq","ev_usd"]).to_csv(args.out, index=False)
        sys.exit(0)

    df['irci_composite_pct'] = make_composite(df, w)
    df['peer_gap_z'] = zscore_by_quarter(df, "val_metric")
    df['peer_gap_change_pp_nextq'] = next_q_change(df, "peer_gap_z")

    out = df[["ticker","quarter","irci_composite_pct","peer_gap_change_pp_nextq","ev_usd"]].dropna()
    out.to_csv(args.out, index=False)
    print(f"[ok] wrote {args.out}: {len(out)} rows, {out['ticker'].nunique()} tickers, {out['quarter'].nunique()} quarters")
