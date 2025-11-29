#!/usr/bin/env python3
import argparse, numpy as np, pandas as pd, yfinance as yf

def pct_rank(s: pd.Series) -> pd.Series:
    r = s.rank(pct=True, method="average")
    return 100.0 * r

def daily_rets(sym: str, period: str = "10y") -> pd.DataFrame:
    """Yahoo daily returns for a symbol, with robust column handling."""
    df = yf.download(sym, period=period, auto_adjust=True, progress=False)
    if df is None or len(df) == 0:
        return pd.DataFrame()

    # yfinance can return a MultiIndex (e.g., OHLCV under level 0). Flatten to first level.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Normalize column names
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Require 'close'
    if "close" not in df.columns:
        return pd.DataFrame()

    px = df[["close"]].copy()
    px["ret"] = px["close"].pct_change()
    ret = px[["ret"]].dropna()

    # Make sure index is tz-naive DatetimeIndex
    ret.index = pd.to_datetime(ret.index)
    try:
        ret.index = ret.index.tz_localize(None)
    except Exception:
        # already tz-naive
        pass

    return ret

def per_quarter_beta_and_idio(df: pd.DataFrame) -> pd.DataFrame:
    """
    df has columns ['ret','mkt'] and DatetimeIndex.
    Returns DataFrame with columns ['quarter','beta','idio_vol'].
    """
    if df.empty:
        return pd.DataFrame(columns=["quarter","beta","idio_vol"])

    # Quarter labels
    q = df.copy()
    q["quarter"] = q.index.to_period("Q").astype(str)

    # Per-quarter beta via simple OLS slope of ret ~ mkt
    betas = (
        q.groupby("quarter", group_keys=False)[["mkt","ret"]]
         .apply(lambda g: np.polyfit(g["mkt"].fillna(0), g["ret"].fillna(0), 1)[0])
         .rename("beta")
    )

    # Per-quarter idiosyncratic volatility: std of residuals
    def resid_vol(g: pd.DataFrame) -> float:
        if len(g) < 20:
            return np.nan
        b = np.polyfit(g["mkt"].fillna(0), g["ret"].fillna(0), 1)[0]
        resid = g["ret"] - b * g["mkt"]
        return float(resid.std())

    idio = (
        q.groupby("quarter", group_keys=False)[["mkt","ret"]]
         .apply(resid_vol)
         .rename("idio_vol")
    )

    out = pd.concat([betas, idio], axis=1).reset_index()
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", required=True, help="CSV with a 'ticker' or 'symbol' column")
    ap.add_argument("--out",   required=True, help="Output CSV path")
    ap.add_argument("--period", default="10y")
    ap.add_argument("--market", default="^GSPC", help="Market proxy (e.g., ^GSPC, ^IXIC)")
    args = ap.parse_args()

    peers = pd.read_csv(args.peers)
    symcol = "symbol" if "symbol" in peers.columns else "ticker"
    if symcol not in peers.columns:
        raise SystemExit(f"Peers file must have 'symbol' or 'ticker' column. Found: {peers.columns.tolist()}")
    syms = peers[symcol].dropna().astype(str).str.upper().unique().tolist()

    # Market series
    mkt = daily_rets(args.market, period=args.period)
    if mkt.empty:
        # Try a fallback if ^GSPC is unavailable
        fallback = "^IXIC" if args.market != "^IXIC" else "^DJI"
        mkt = daily_rets(fallback, period=args.period)
        if mkt.empty:
            raise SystemExit("Failed to load a market proxy from Yahoo (tried ^GSPC, ^IXIC, ^DJI).")
    mkt = mkt.rename(columns={"ret": "mkt"})

    rows = []
    for s in syms:
        sr = daily_rets(s, period=args.period)
        if sr.empty:
            continue
        df = sr.join(mkt, how="inner")
        if df.empty:
            continue
        out = per_quarter_beta_and_idio(df)
        if out.empty:
            continue
        out["ticker"] = s
        rows.append(out)

    if not rows:
        raise SystemExit("No trust metrics built for any symbol — check ticker list or Yahoo reachability.")

    trust = pd.concat(rows, ignore_index=True)

    # Within-quarter percentiles → map to trust (lower beta & idio vol = higher trust)
    trust["beta_pctl"] = trust.groupby("quarter")["beta"].transform(pct_rank)
    trust["idio_pctl"] = trust.groupby("quarter")["idio_vol"].transform(pct_rank)
    trust["beta_trust"] = 100.0 - trust["beta_pctl"]
    trust["idio_trust"] = 100.0 - trust["idio_pctl"]

    # Blend (50/50 is a simple, stable default; tweak if you like)
    trust["trust_pct"] = 0.5 * trust["beta_trust"] + 0.5 * trust["idio_trust"]

    out = (
        trust[["ticker","quarter","trust_pct"]]
        .dropna()
        .sort_values(["quarter","ticker"])
        .reset_index(drop=True)
    )

    out.to_csv(args.out, index=False)
    print(f"[ok] wrote {args.out} ({len(out)} rows)")

if __name__ == "__main__":
    main()
