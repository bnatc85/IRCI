#!/usr/bin/env python
import os, time, argparse, requests, numpy as np, pandas as pd
from datetime import timedelta

# ---------- Config ----------
SEC_UA = os.environ.get("SEC_USER_AGENT", "IRCI Research / missing-ua")

# ---------- Helpers ----------
def pct_rank(s: pd.Series, asc=True):
    if len(s) <= 1:
        return pd.Series([50.0]*len(s), index=s.index)
    r = s.rank(method="min", ascending=asc)
    return 100*(r-1)/(len(s)-1)

# ---------- Price loaders: Yahoo -> AV -> Stooq ----------
def yf_daily(symbol, period="5y"):
    try:
        import yfinance as yf
        df = yf.download(symbol, period=period, interval="1d",
                         auto_adjust=True, progress=False, threads=False, group_by="column")
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join([c for c in tup if c]) for tup in df.columns]
        df = df.rename(columns=lambda c: str(c).lower())
        if "close" not in df.columns:
            return pd.DataFrame()
        out = df[["close"]].copy()
        out.index = pd.to_datetime(out.index)
        out["ret"] = out["close"].pct_change()
        return out.dropna()
    except Exception:
        return pd.DataFrame()

def av_daily(symbol, key):
    if not key:
        return pd.DataFrame()
    base = "https://www.alphavantage.co/query"
    for fn in ("TIME_SERIES_DAILY_ADJUSTED","TIME_SERIES_DAILY"):
        params = {"function": fn, "symbol": symbol, "outputsize": "compact", "apikey": key}
        try:
            r = requests.get(base, params=params, timeout=30)
            r.raise_for_status()
            j = r.json()
        except Exception:
            continue
        ts = j.get("Time Series (Daily)") or j.get("Time Series (Daily Adjusted)")
        if not ts or "Note" in j or "Information" in j:
            continue  # throttled/limited
        raw = pd.DataFrame(ts).T
        raw.index = pd.to_datetime(raw.index, errors="coerce")
        close = raw.get("5. adjusted close", raw.get("4. close"))
        if close is None:
            continue
        out = pd.DataFrame({"close": pd.to_numeric(close, errors="coerce")})
        out = out.sort_index().dropna()
        out["ret"] = out["close"].pct_change()
        return out.dropna()
    return pd.DataFrame()

def stooq_daily(symbol):
    try:
        import pandas_datareader.data as pdr
        s = f"{symbol}.US"
        df = pdr.DataReader(s, "stooq")
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns=str.lower)
        if "close" not in df.columns:
            return pd.DataFrame()
        df = df[["close"]].copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df["ret"] = df["close"].pct_change()
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def load_ret(symbol, av_key):
    # Try Yahoo -> AV -> Stooq
    for loader in (
        lambda s: yf_daily(s, "5y"),
        lambda s: av_daily(s, av_key),
        lambda s: stooq_daily(s),
    ):
        df = loader(symbol)
        if not df.empty:
            return df
    return pd.DataFrame()

def market_proxy(av_key):
    # Try SPY -> XLC -> ^GSPC
    for sym in ("SPY", "XLC", "^GSPC"):
        m = load_ret(sym, av_key)
        if not m.empty:
            return m.rename(columns={"ret":"mkt"})[["mkt"]]
    raise SystemExit("No market proxy from Yahoo/AV/Stooq")

# ---------- SEC helpers ----------
def cik_map():
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers={"User-Agent": SEC_UA}, timeout=30)
    r.raise_for_status()
    j = r.json()
    return {row["ticker"].upper(): int(row["cik_str"]) for _, row in j.items()}

def sec_events(cik: int):
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    r = requests.get(url, headers={"User-Agent": SEC_UA}, timeout=30)
    r.raise_for_status()
    j = r.json()
    f = pd.DataFrame({
        "form": j.get("filings", {}).get("recent", {}).get("form", []),
        "filed": pd.to_datetime(
            j.get("filings", {}).get("recent", {}).get("filingDate", []),
            errors="coerce", utc=True
        )
    })
    if f.empty:
        return pd.DataFrame(columns=["form","filed"])
    f["filed"] = f["filed"].dt.tz_localize(None)
    f = f[f["form"].isin(["10-Q", "10-K", "8-K"])].dropna(subset=["filed"])
    return f

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    peers = pd.read_csv(args.peers)
    symcol = "ticker" if "ticker" in peers.columns else "symbol"
    syms = peers[symcol].astype(str).str.upper().tolist()

    av_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    mkt = market_proxy(av_key)                 # DataFrame with column 'mkt'
    ciks = cik_map()

    recs = []
    for i, sym in enumerate(syms, 1):
        try:
            print(f"[{i}/{len(syms)}] {sym}")
            px = load_ret(sym, av_key)        # DataFrame with 'close' and 'ret'
            if px.empty:
                print(f"[warn] {sym}: no prices from Yahoo/AV/Stooq")
                continue

            # Join to market; guard empties so we never touch undefined df
            df = px.join(mkt, how="inner")
            df = df.copy()
            df.index = pd.to_datetime(df.index)          # ensure DatetimeIndex
            df["ts"] = df.index                          # <- keep a stable datetime column
            df["quarter"] = df.index.to_period("Q").astype(str)
            if df.empty:
                print(f"[warn] {sym}: no overlap with market proxy")
                continue

            # Ensure DatetimeIndex before slicing
            df.index = pd.to_datetime(df.index)

            # Quarter tag
            df["quarter"] = df.index.to_period("Q").astype(str)

            # Simple CAPM beta per quarter
            betas = (df.groupby("quarter")[["mkt","ret"]]
                        .apply(lambda g: np.polyfit(g["mkt"].fillna(0), g["ret"].fillna(0), 1)[0])
                        .rename("beta").reset_index())

            df = df.merge(betas, on="quarter", how="left")
            df["resid"] = df["ret"] - df["beta"] * df["mkt"]

            base = df.groupby("quarter")["resid"].std().rename("base_std").reset_index()

            # SEC event calmness (median |resid| in ±3 days)
            ev_df = pd.DataFrame(columns=["quarter","event_medabs"])
            cik = ciks.get(sym)
            if cik:
                ev = sec_events(cik)
                if not ev.empty:
                    ev["quarter"] = ev["filed"].dt.to_period("Q").astype(str)
                    vals = {}
                    for q in ev["quarter"].unique():
                        med = []
                        for d in ev.loc[ev["quarter"] == q, "filed"].dt.normalize().tolist():
                            start = d - pd.Timedelta(days=3)
                            end   = d + pd.Timedelta(days=3)
                            mask  = df["ts"].between(start, end)         # <- use the datetime column
                            w     = df.loc[mask]
                            if not w.empty:
                                med.append(w["resid"].abs().median())
                        if med:
                            vals[q] = float(np.median(med))
                    if vals:
                        ev_df = pd.DataFrame({"quarter": list(vals.keys()), "event_medabs": list(vals.values())})

            # Assemble per-quarter features
            q = pd.DataFrame({"quarter": df["quarter"].unique()})
            q["ticker"] = sym
            q = q.merge(base, on="quarter", how="left").merge(ev_df, on="quarter", how="left")
            # Safe fills with medians if needed
            if q["event_medabs"].isna().all():
                q["event_medabs"] = 0.0
            else:
                q["event_medabs"] = q["event_medabs"].fillna(q["event_medabs"].median())
            if q["base_std"].isna().all():
                q["base_std"] = 0.0
            else:
                q["base_std"] = q["base_std"].fillna(q["base_std"].median())

            # Percentiles within quarter (lower = calmer = better)
            q["calm_evt_pct"]  = q.groupby("quarter")["event_medabs"].transform(lambda s: pct_rank(s, asc=False))
            q["calm_base_pct"] = q.groupby("quarter")["base_std"].transform(lambda s: pct_rank(s, asc=False))
            q["trust_pct"]     = (0.70*q["calm_evt_pct"] + 0.30*q["calm_base_pct"]).round(1)

            recs.append(q[["ticker","quarter","trust_pct"]])
            time.sleep(0.2)
        except Exception as e:
            print(f"[warn] {sym}: {e}")

    if not recs:
        raise SystemExit("No trust data built.")
    out = pd.concat(recs, ignore_index=True)
    out.to_csv(args.out, index=False)
    print(f"[ok] wrote {args.out} ({len(out)} rows)")

if __name__ == "__main__":
    main()
