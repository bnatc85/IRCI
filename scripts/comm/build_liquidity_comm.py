#!/usr/bin/env python
import os, argparse, time, numpy as np, pandas as pd, requests

def pct_rank(s, asc=True):
    if len(s) <= 1: return pd.Series([50.0]*len(s), index=s.index)
    r = s.rank(method="min", ascending=asc); return 100*(r-1)/(len(s)-1)

def cs_spread(df):
    if len(df) < 3: return pd.Series(index=df.index, dtype=float)
    H, L = df["high"].values, df["low"].values
    beta  = (np.log(H/L)**2); beta2 = pd.Series(beta, index=df.index).rolling(2).sum()
    gamma_vals = np.log(np.maximum(H[1:], H[:-1]) / np.minimum(L[1:], L[:-1]))**2
    gamma = pd.Series(np.r_[np.nan, gamma_vals], index=df.index)
    alpha = (beta2 - gamma).clip(lower=0); phi = np.sqrt(alpha)
    return 2*(np.exp(phi) - 1) / (1 + np.exp(phi))

def av_daily(symbol, key):
    base = "https://www.alphavantage.co/query"
    for fn in ("TIME_SERIES_DAILY_ADJUSTED","TIME_SERIES_DAILY"):
        params = {"function": fn, "symbol": symbol, "outputsize": "compact", "apikey": key}
        r = requests.get(base, params=params, timeout=30)
        try: r.raise_for_status()
        except: continue
        j = r.json()
        ts = j.get("Time Series (Daily)") or j.get("Time Series (Daily Adjusted)")
        if not ts or "Note" in j or "Information" in j:  # throttled/limited
            continue
        raw = pd.DataFrame(ts).T; raw.index = pd.to_datetime(raw.index, errors="coerce")
        cols = {}
        for k, dst in [("1. open","open"),("2. high","high"),("3. low","low"),
                       ("4. close","close"),("5. adjusted close","close")]:
            if k in raw.columns and dst not in cols:
                cols[dst] = pd.to_numeric(raw[k], errors="coerce")
        need = {"open","high","low","close"}
        if need <= set(cols):
            out = pd.DataFrame(cols).dropna().sort_index()
            return out
    return pd.DataFrame()

def yf_daily(symbol, period="3y"):
    try:
        import yfinance as yf
        df = yf.download(symbol, period=period, interval="1d", auto_adjust=False,
                         progress=False, threads=False, group_by="column")
        if df is None or df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join([c for c in tup if c]) for tup in df.columns]
        df = df.rename(columns=lambda c: str(c).lower())
        need = {"open","high","low","close"}
        if not need <= set(df.columns): return pd.DataFrame()
        out = df[list(need)].dropna().copy(); out.index = pd.to_datetime(out.index)
        return out.sort_index()
    except Exception:
        return pd.DataFrame()

def stooq_daily(symbol):
    try:
        import pandas_datareader.data as pdr
        sym = f"{symbol}.US"
        df = pdr.DataReader(sym, "stooq")  # no key, reliable
        if df is None or df.empty: return pd.DataFrame()
        df = df.rename(columns=str.lower)[["open","high","low","close"]]
        df.index = pd.to_datetime(df.index); df = df.sort_index()
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def load_bars(sym, av_key):
    for loader in (lambda s: yf_daily(s),
                   lambda s: av_daily(s, av_key) if av_key else pd.DataFrame(),
                   lambda s: stooq_daily(s)):
        d = loader(sym)
        if not d.empty: return d
    return pd.DataFrame()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    peers = pd.read_csv(args.peers)
    col = "ticker" if "ticker" in peers.columns else "symbol"
    syms = peers[col].astype(str).str.upper().tolist()
    av_key = os.environ.get("ALPHAVANTAGE_API_KEY")

    recs=[]
    for i, sym in enumerate(syms, 1):
        print(f"[{i}/{len(syms)}] {sym}")
        d = load_bars(sym, av_key)
        if d.empty:
            print(f"[warn] {sym}: no OHLC from Yahoo/AV/Stooq"); time.sleep(0.2); continue
        d["quarter"] = pd.to_datetime(d.index).to_period("Q").astype(str)
        d["cs"] = cs_spread(d)
        q = d.groupby("quarter")["cs"].mean().rename("cs_mean").reset_index()
        q["ticker"]=sym
        recs.append(q); time.sleep(0.2)

    if not recs: raise SystemExit("No liquidity data retrieved for any symbol.")
    df = pd.concat(recs, ignore_index=True)
    df["liq_pct"] = df.groupby("quarter")["cs_mean"].transform(lambda s: pct_rank(s, asc=False)).round(1)
    df[["ticker","quarter","liq_pct"]].to_csv(args.out, index=False)
    print(f"[ok] wrote {args.out} ({len(df)} rows)")

if __name__ == "__main__":
    main()
