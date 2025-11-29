# irci/liquidity.py
from __future__ import annotations
import numpy as np
import pandas as pd
import yfinance as yf

from .config import Settings
from .logging import get_logger
from .sec import shares_outstanding_from_sec
from .valuation import fmp_market_cap  # re-use your existing helper

log = get_logger("irci.liquidity")

def _utc_index(idx) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(idx)
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")

def _safe_div(a, b):
    out = a / b
    return out.replace([np.inf, -np.inf], np.nan)

# --- Daily metrics -----------------------------------------------------------

def _winsorize(s: pd.Series, p: float = 0.01) -> pd.Series:
    if s.isna().all():
        return s
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lower=lo, upper=hi)

def daily_amihud(df: pd.DataFrame) -> pd.Series:
    """Amihud (2002): |return| / dollar volume (daily)."""
    px = df["adj_close"].astype(float)
    vol = df["volume"].astype(float)
    ret = px.pct_change().abs()
    dollar = (px * vol).replace(0, np.nan)
    illiq = _safe_div(ret, dollar)
    return illiq.rename("amihud")

def roll_spread_proxy(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Roll (1984) effective spread proxy from return autocovariance."""
    r = np.log(df["adj_close"]).diff()
    cov = r.rolling(window).cov(r.shift(1))
    spread = 2.0 * np.sqrt((-cov).clip(lower=0))  # only defined if cov < 0
    spread = spread.where(cov < 0)  # NaN otherwise
    return spread.rename("roll_spread")

def _market_cap_series(symbol: str, s: Settings, df_prices: pd.DataFrame, end: str | None) -> pd.Series:
    """Daily market cap series (FMP → SEC price×shares → Yahoo Finance)."""
    try:
        mc = fmp_market_cap(symbol, s.fmp_api_key, limit=400)  # has 'marketCap'
        mc = mc.sort_index()
        series = mc["marketCap"]
    except Exception as e:
        log.warning(f"market-cap lookup failed for {symbol}: {e}; fallback to price×shares via SEC")
        as_of_ts = pd.to_datetime(end, utc=True) if end else pd.Timestamp.utcnow(tz="UTC")
        so = shares_outstanding_from_sec(symbol, as_of_ts, s=s).get("shares_outstanding")
        if not so or so <= 0:
            log.warning(f"shares outstanding missing for {symbol}; trying Yahoo Finance as final backup")
            # Try Yahoo Finance as final backup
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                yahoo_mc = info.get('marketCap')

                if yahoo_mc and yahoo_mc > 0:
                    # Yahoo gives current market cap - use it as a constant for the period
                    log.info(f"Yahoo Finance provided market cap for {symbol}: ${yahoo_mc:,.0f}")
                    series = pd.Series(float(yahoo_mc), index=df_prices.index, name="marketCap")
                else:
                    log.warning(f"Yahoo Finance market cap unavailable for {symbol}; returning NaN series")
                    series = pd.Series(np.nan, index=df_prices.index, name="marketCap")
            except Exception as e_yahoo:
                log.warning(f"Yahoo Finance fetch failed for {symbol}: {e_yahoo}; returning NaN series")
                series = pd.Series(np.nan, index=df_prices.index, name="marketCap")
        else:
            series = (df_prices["adj_close"].astype(float) * float(so)).rename("marketCap")
    series.index = _utc_index(series.index)
    return series

def daily_turnover(symbol: str, s: Settings, df_prices: pd.DataFrame, end: str | None) -> pd.Series:
    """Dollar turnover: (price * shares traded) / market cap (daily)."""
    px = df_prices["adj_close"].astype(float)
    vol = df_prices["volume"].astype(float)
    dollar = (px * vol).replace(0, np.nan)
    mc = _market_cap_series(symbol, s, df_prices, end).reindex(df_prices.index).ffill()
    to = _safe_div(dollar, mc)
    return to.rename("turnover")

def daily_liquidity_bundle(symbol: str, s: Settings, df_prices: pd.DataFrame, end: str | None):
    """Return a daily DataFrame with amihud, turnover, roll_spread."""
    df = df_prices.copy()
    df.index = _utc_index(df.index) if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df.index, utc=True)
    out = pd.DataFrame(index=df.index)
    out["amihud"] = daily_amihud(df)
    out["turnover"] = daily_turnover(symbol, s, df, end)
    out["roll_spread"] = roll_spread_proxy(df)
    return out

# --- Quarterly aggregates ----------------------------------------------------

def quarterly_liquidity(daily_df: pd.DataFrame, freq: str = "QE-DEC") -> pd.DataFrame:
    """Aggregate daily liquidity metrics to quarter level (+ pretty display units)."""
    d = daily_df.copy()
    # optional de-noising
    d["amihud_w"] = _winsorize(d["amihud"])
    d["turnover_w"] = _winsorize(d["turnover"])
    d["roll_spread_w"] = _winsorize(d["roll_spread"])

    q = pd.DataFrame(index=d.resample(freq).last().index)
    # core signals used for the dial
    q["q_amihud"] = d["amihud_w"].resample(freq).median()
    q["q_turnover"] = d["turnover_w"].resample(freq).mean()
    q["q_roll_spread"] = d["roll_spread_w"].resample(freq).median()

    # human-friendly display columns (monotone transforms – do NOT affect ranks)
    q["q_amihud_e6"] = q["q_amihud"] * 1e6         # per $1M
    q["q_spread_bps"] = q["q_roll_spread"] * 1e4   # basis points
    return q

# --- Peer dial (0–100%) -----------------------------------------------------

def add_liquidity_percentile(df_q: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a 0–100 liquidity dial per (quarter_end, ticker):
      - q_amihud: lower is better
      - q_roll_spread: lower is better
      - q_turnover: higher is better
    """
    df_q = df_q.copy()

    # numeric hygiene
    for c in ["q_amihud", "q_turnover", "q_roll_spread"]:
        df_q[c] = pd.to_numeric(df_q[c], errors="coerce")

    # make sure left merge key is tz-aware UTC
    df_q["quarter_end"] = pd.to_datetime(df_q["quarter_end"], utc=True)

    def per_quarter(x: pd.DataFrame) -> pd.DataFrame:
        # Percentiles; some components may be entirely/partially NaN
        p_amihud = x["q_amihud"].rank(pct=True, ascending=False)   # lower is better -> higher pct
        p_spread = x["q_roll_spread"].rank(pct=True, ascending=False)
        p_turn   = x["q_turnover"].rank(pct=True, ascending=True)  # higher is better
        comps   = pd.concat([p_amihud, p_spread, p_turn], axis=1)
        counts  = comps.notna().sum(axis=1)        # how many components are present
        sums    = comps.fillna(0).sum(axis=1)      # sum only the present ones
        dial    = (sums / counts.clip(lower=1)) * 100.0

        out = x[["quarter_end", "ticker"]].copy()
        out["liquidity_pct"] = dial.round().astype("Int64")
        return out

    res = (
        df_q.groupby("quarter_end", group_keys=False)
            .apply(per_quarter)
            .reset_index(drop=True)
    )

    # make sure right merge key is also tz-aware UTC
    res["quarter_end"] = pd.to_datetime(res["quarter_end"], utc=True)

    # align back on (quarter_end, ticker)
    df_q = (
        df_q.drop(columns=["liquidity_pct"], errors="ignore")
            .merge(res, on=["quarter_end", "ticker"], how="left", validate="one_to_one")
    )
    return df_q