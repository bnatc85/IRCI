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
        try:
            so = shares_outstanding_from_sec(symbol, as_of_ts, s=s).get("shares_outstanding")
        except ValueError as sec_e:
            # Foreign ADRs (e.g., HEINY) won't be in SEC mapping
            log.warning(f"SEC shares lookup failed for {symbol}: {sec_e}")
            so = None
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

# --- Institutional ownership integration -------------------------------------

def fetch_institutional_ownership_for_liquidity(symbols: list, settings=None) -> pd.DataFrame:
    """
    Fetch institutional ownership data for liquidity integration.
    Higher institutional ownership typically indicates better liquidity (larger block trades).
    """
    try:
        from .institutional_ownership import get_ownership_for_liquidity
        return get_ownership_for_liquidity(symbols, settings)
    except Exception as e:
        log.warning(f"Institutional ownership fetch failed: {e}")
        return pd.DataFrame(columns=["ticker", "institutional_pct", "holder_count", "inst_ownership_score"])


# --- Peer dial (0–100%) -----------------------------------------------------

def add_liquidity_percentile(
    df_q: pd.DataFrame,
    include_institutional: bool = True,
    institutional_weight: float = 0.15
) -> pd.DataFrame:
    """
    Compute a 0–100 liquidity dial per (quarter_end, ticker):
      - q_amihud: lower is better (35% weight)
      - q_roll_spread: lower is better (25% weight)
      - q_turnover: higher is better (25% weight)
      - inst_ownership_score: higher is better (15% weight, if available)
    """
    df_q = df_q.copy()

    # numeric hygiene
    for c in ["q_amihud", "q_turnover", "q_roll_spread"]:
        if c in df_q.columns:
            df_q[c] = pd.to_numeric(df_q[c], errors="coerce")

    # make sure left merge key is tz-aware UTC
    df_q["quarter_end"] = pd.to_datetime(df_q["quarter_end"], utc=True)

    # Fetch institutional ownership if requested
    if include_institutional and "inst_ownership_score" not in df_q.columns:
        symbols = df_q["ticker"].unique().tolist()
        try:
            inst_df = fetch_institutional_ownership_for_liquidity(symbols)
            if not inst_df.empty and "inst_ownership_score" in inst_df.columns:
                df_q = df_q.merge(
                    inst_df[["ticker", "institutional_pct", "holder_count", "inst_ownership_score"]],
                    on="ticker",
                    how="left"
                )
                log.info(f"Added institutional ownership data for {len(inst_df)} symbols")
        except Exception as e:
            log.warning(f"Could not add institutional ownership: {e}")

    has_institutional = include_institutional and "inst_ownership_score" in df_q.columns

    def per_quarter(x: pd.DataFrame) -> pd.DataFrame:
        # Percentiles; some components may be entirely/partially NaN
        p_amihud = x["q_amihud"].rank(pct=True, ascending=False)   # lower is better -> higher pct
        p_spread = x["q_roll_spread"].rank(pct=True, ascending=False)
        p_turn   = x["q_turnover"].rank(pct=True, ascending=True)  # higher is better

        if has_institutional:
            # inst_ownership_score is already 0-100, just rank it
            p_inst = x["inst_ownership_score"].rank(pct=True, ascending=True)  # higher is better
            # Weighted average: amihud 35%, spread 25%, turnover 25%, institutional 15%
            w_amihud = 0.35
            w_spread = 0.25
            w_turn = 0.25
            w_inst = institutional_weight

            # Normalize weights
            total_w = w_amihud + w_spread + w_turn + w_inst
            w_amihud /= total_w
            w_spread /= total_w
            w_turn /= total_w
            w_inst /= total_w

            # Handle NaN components by only using available ones
            comps = pd.DataFrame({
                'p_amihud': p_amihud,
                'p_spread': p_spread,
                'p_turn': p_turn,
                'p_inst': p_inst
            })
            weights = pd.DataFrame({
                'p_amihud': w_amihud,
                'p_spread': w_spread,
                'p_turn': w_turn,
                'p_inst': w_inst
            }, index=comps.index)

            # Weighted sum, normalized by available weights
            weighted_sum = (comps.fillna(0) * weights).sum(axis=1)
            weight_sum = (comps.notna().astype(float) * weights).sum(axis=1)
            dial = (weighted_sum / weight_sum.clip(lower=0.01)) * 100.0
        else:
            # Original logic without institutional data
            comps = pd.concat([p_amihud, p_spread, p_turn], axis=1)
            counts = comps.notna().sum(axis=1)
            sums = comps.fillna(0).sum(axis=1)
            dial = (sums / counts.clip(lower=1)) * 100.0

        out = x[["ticker"]].copy()
        if "quarter_end" in x.columns:
            out["quarter_end"] = x["quarter_end"]
        elif "quarter_end" in x.index.names:
            out["quarter_end"] = x.index.get_level_values("quarter_end")
        else:
            # include_groups=False path: the group key is on x.name
            out["quarter_end"] = x.name
        out["liquidity_pct"] = dial.round()
        return out

    res = (
        df_q.groupby("quarter_end", group_keys=False)
            .apply(per_quarter, include_groups=False)
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