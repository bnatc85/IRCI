from __future__ import annotations
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
import requests
from requests import HTTPError
import os
import time

from .config import Settings
from .logging import get_logger
from .sec import (
    ttm_ebitda_from_sec,
    debt_and_cash_from_sec,
    shares_outstanding_from_sec,
)
from .market import fetch_prices_fmp  # for price×shares market-cap fallback
# --- timezone normalization helpers (force UTC-naive for all comparisons) ---
def _naive_utc_ts(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tz is None:
        # treat naive as UTC
        return ts.tz_localize("UTC").tz_localize(None)
    return ts.tz_convert("UTC").tz_localize(None)

def _naive_utc_index(idx) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(idx)
    if idx.tz is None:
        # treat naive as UTC
        return idx.tz_localize("UTC").tz_localize(None)
    return idx.tz_convert("UTC").tz_localize(None)

def _filter_on_or_before(df: pd.DataFrame, as_of_ts: pd.Timestamp) -> pd.DataFrame:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("DataFrame index must be DatetimeIndex")
    idx = _naive_utc_index(df.index)
    ts = _naive_utc_ts(as_of_ts)
    return df.loc[idx <= ts]

def _last_on_or_before(df: pd.DataFrame, ts: pd.Timestamp) -> tuple[pd.Timestamp, pd.Series]:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("DataFrame index must be DatetimeIndex")
    idx = _naive_utc_index(df.index)
    tsn = _naive_utc_ts(ts)
    pos = idx.searchsorted(tsn, side="right") - 1
    if pos < 0:
        pos = 0
    return pd.Timestamp(idx[pos]).tz_localize("UTC"), df.iloc[pos]

log = get_logger("irci.valuation")

def median_anchored_pct(s: pd.Series, lower_is_better: bool = False) -> pd.Series:
    """
    Map values in s to a 0..100 scale with the peer median at 50.
    - For x <= median: linear from min..median -> 0..50
    - For x >= median: linear from median..max -> 50..100
    If all values equal, returns 50 for all.
    If lower_is_better=True, invert (so lower values -> higher %).
    """
    s = s.astype(float)
    med = s.median(skipna=True)

    lower = s[s <= med]
    upper = s[s >= med]
    lo_min = lower.min() if not lower.empty else med
    hi_max = upper.max() if not upper.empty else med

    pct = pd.Series(index=s.index, dtype="float64")

    # all equal (avoid 0-division)
    if med == lo_min == hi_max:
        pct[:] = 50.0
        return 100.0 - pct if lower_is_better else pct

    # lower half: min..median -> 0..50
    if med != lo_min:
        pct.loc[s <= med] = (s.loc[s <= med] - lo_min) / (med - lo_min) * 50.0
    else:
        pct.loc[s <= med] = 50.0  # everything at/above min is median → 50

    # upper half: median..max -> 50..100
    if hi_max != med:
        pct.loc[s > med] = 50.0 + (s.loc[s > med] - med) / (hi_max - med) * 50.0
    else:
        pct.loc[s > med] = 50.0

    return 100.0 - pct if lower_is_better else pct


# --- timezone helpers ---
def _utc_ts(ts):
    ts = pd.Timestamp(ts)
    return ts.tz_localize("UTC") if ts.tz is None else ts.tz_convert("UTC")

def _utc_index(idx) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(idx)
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")

def _get_json(url: str, timeout: int = 60) -> list | dict:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()

def get_alpha_vantage_peg(ticker: str) -> float:
    """
    Fetch PEG ratio from Alpha Vantage Company Overview endpoint.
    Returns np.nan if unavailable or on error.

    Rate limit: 5 calls/minute (free tier), so caller should manage timing.
    """
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        log.debug(f"ALPHA_VANTAGE_API_KEY not set; skipping PEG for {ticker}")
        return np.nan

    try:
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
        log.info(f"GET Alpha Vantage OVERVIEW for {ticker}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Alpha Vantage returns empty dict or error message if symbol not found
        if not data or 'PEGRatio' not in data:
            log.warning(f"PEG ratio not available from Alpha Vantage for {ticker}")
            return np.nan

        peg_str = data.get('PEGRatio', 'None')
        if peg_str in ('None', '', None):
            return np.nan

        peg_value = float(peg_str)
        log.info(f"Alpha Vantage PEG for {ticker}: {peg_value}")
        return peg_value

    except Exception as e:
        log.warning(f"Alpha Vantage PEG fetch failed for {ticker}: {e}")
        return np.nan

def fmp_enterprise_values(symbol: str, apikey: str, period: str = "quarter", limit: int = 40) -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/enterprise-values/{symbol}?period={period}&limit={limit}&apikey={apikey}"
    log.info(f"GET {url.replace(apikey, '***')}")
    js = _get_json(url)
    if not isinstance(js, list) or not js:
        raise ValueError(f"No enterprise values for {symbol}")
    df = pd.DataFrame(js)
    if "date" not in df.columns or "enterpriseValue" not in df.columns:
        raise ValueError("Unexpected payload for enterprise-values")
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").set_index("date")
    df.index = _utc_index(df.index)
    return df[["enterpriseValue"]].astype(float)

def fmp_market_cap(symbol: str, apikey: str, limit: int = 400) -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/market-capitalization/{symbol}?limit={limit}&apikey={apikey}"
    log.info(f"GET {url.replace(apikey, '***')}")
    js = _get_json(url)
    if not isinstance(js, list) or not js:
        raise ValueError(f"No market cap for {symbol}")
    df = pd.DataFrame(js)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").set_index("date")
    df.index = _utc_index(df.index)
    mc_col = "marketCap" if "marketCap" in df.columns else df.columns[-1]
    return df[[mc_col]].rename(columns={mc_col: "marketCap"}).astype(float)

def _last_on_or_before(df: pd.DataFrame, ts: pd.Timestamp) -> Tuple[pd.Timestamp, pd.Series]:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("DataFrame index must be DatetimeIndex")
    df = df.copy()
    df.index = _utc_index(df.index)
    ts = _utc_ts(ts)
    df2 = df.loc[df.index <= ts]
    if df2.empty:
        return df.index[-1], df.iloc[-1]
    return df2.index[-1], df2.iloc[-1]

def market_cap_from_price_and_shares(symbol: str, apikey: str, as_of_ts: pd.Timestamp, s: Settings) -> Tuple[pd.Timestamp, float]:
    # Fetch ~60 days of prices and use last close ≤ as_of
    as_of_ts = _utc_ts(as_of_ts)
    start = (as_of_ts - pd.Timedelta(days=60)).date().isoformat()
    end = as_of_ts.date().isoformat()
    px = fetch_prices_fmp(symbol, start, end, apikey).copy()
    if isinstance(px.index, pd.DatetimeIndex):
        px.index = _utc_index(px.index)
    px = _filter_on_or_before(px, as_of_ts)
    if px.empty:
        px = fetch_prices_fmp(symbol, "2010-01-01", end, apikey).copy()
        if isinstance(px.index, pd.DatetimeIndex):
            px.index = _utc_index(px.index)
    px_date = px.index[-1]
    price = float(px.loc[px_date, "adj_close"])

    so = shares_outstanding_from_sec(symbol, as_of_ts, s=s)
    shares = so.get("shares_outstanding")
    if shares is None or shares <= 0:
        log.warning(f"Shares outstanding unavailable for {symbol}; cannot compute price×shares market cap.")
        raise ValueError("shares outstanding unavailable")
    mc = price * shares
    log.warning(f"Market cap via price×shares (SEC {so['tag']} @ {px_date.date()}): {mc:,.0f}")
    return px_date, mc

def fmp_balance_sheet_q(symbol: str, apikey: str, limit: int = 16) -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{symbol}?period=quarter&limit={limit}&apikey={apikey}"
    log.info(f"GET {url.replace(apikey, '***')}")
    js = _get_json(url)
    if not isinstance(js, list) or not js:
        raise ValueError(f"No balance sheet for {symbol}")
    df = pd.DataFrame(js)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").set_index("date")
    

    # totalDebt & cash-equivalents (best-effort)
    if "totalDebt" in df.columns:
        total_debt = df["totalDebt"].astype(float)
    else:
        total_debt = df.get("shortTermDebt", 0).astype(float) + df.get("longTermDebt", 0).astype(float)

    cash = None
    for cand in ["cashAndCashEquivalents", "cashAndCashEquivalentsAtCarryingValue", "cashAndShortTermInvestments"]:
        if cand in df.columns:
            cash = df[cand].astype(float)
            break
    if cash is None:
        cash = pd.Series(0.0, index=df.index)

    return pd.DataFrame({"totalDebt": total_debt, "cashEq": cash})

def estimate_ev_from_components(symbol: str, apikey: str, as_of_ts: pd.Timestamp, s: Settings) -> Tuple[pd.Timestamp, float]:
    """
    EV ≈ MarketCap(as_of) + TotalDebt(qtr ≤ as_of) - CashEq(qtr ≤ as_of)
    Uses FMP where allowed; otherwise falls back to SEC for debt/cash and to price×shares for market cap.
    """
    # Market cap (FMP → fallback price×shares)
    try:
        mc = fmp_market_cap(symbol, apikey, limit=400)
        mc_date, mc_row = _last_on_or_before(mc, as_of_ts)
        mc_val = float(mc_row["marketCap"])
    except (HTTPError, ValueError) as e:
        log.warning(f"market-capitalization unavailable for {symbol}; fallback price×shares via SEC: {e}")
        mc_date, mc_val = market_cap_from_price_and_shares(symbol, apikey, as_of_ts, s)

    # Debt/Cash (FMP → fallback SEC)
    try:
        bs = fmp_balance_sheet_q(symbol, apikey, limit=16)
        bs_date, bs_row = _last_on_or_before(bs, as_of_ts)
        debt = float(bs_row["totalDebt"])
        cash = float(bs_row["cashEq"])
        bs_method = "FMP balance-sheet"
    except (HTTPError, ValueError) as e:
        log.warning(f"balance-sheet-statement unavailable for {symbol}; fallback to SEC facts: {e}")
        sec_bs = debt_and_cash_from_sec(symbol, as_of_ts, s=s)
        debt = float(sec_bs["total_debt"])
        cash = float(sec_bs["cash_eq"])
        bs_date = sec_bs["as_of"] or as_of_ts
        bs_method = f"SEC facts ({sec_bs['method']})"

    ev = mc_val + debt - cash
    as_of_used = max(mc_date, bs_date)
    log.info(f"EV components for {symbol}: MC={mc_val:,.0f} Debt={debt:,.0f} Cash={cash:,.0f} → EV={ev:,.0f} @ {as_of_used.date()} ({bs_method})")
    return as_of_used, ev

def valuation_snapshot(symbols: List[str], as_of: Optional[str] = None, source: str = "hybrid") -> pd.DataFrame:
    """
    EV (FMP enterprise-values if allowed, else components) + SEC TTM EBITDA → EV/EBITDA
    Also computes peer mean and valuation gap %.
    """
    s = Settings.load()
    if not s.fmp_api_key:
        raise RuntimeError("FMP_API_KEY not set; see .env.example")
    as_of_ts = pd.to_datetime(as_of, utc=True) if as_of else None
    as_of_ts = _utc_ts(as_of_ts) if as_of_ts is not None else None


    rows = []
    for sym in [t.strip().upper() for t in symbols if t.strip()]:
        # 1) EV (prefer enterprise-values; on 403/ValueError → components)
        try:
            ev_df = fmp_enterprise_values(sym, s.fmp_api_key, period="quarter", limit=40)
            if as_of_ts is None:
                ev_date = ev_df.index[-1]
                ev_val = float(ev_df.iloc[-1]["enterpriseValue"])
            else:
                # nearest-on-or-before as_of_ts
                ev_df2 = ev_df[ev_df.index <= as_of_ts]
                if ev_df2.empty:
                    raise ValueError("No enterprise values on/before as_of")
                ev_date = ev_df2.index[-1]
                ev_val  = float(ev_df2.iloc[-1]["enterpriseValue"])
        except Exception as e:
    # HTTP 403 or no data → estimate from components
            if isinstance(e, requests.HTTPError):
                try:
                    code = e.response.status_code
                except Exception:
                    code = "?"
                log.warning(f"enterprise-values HTTP {code} for {sym}; estimating EV from components")
            else:
                log.warning(f"enterprise-values unavailable for {sym}; estimating EV from components: {e}")

            asof = as_of_ts or pd.Timestamp.now(tz="UTC")
            try:
                # IMPORTANT: pass s=... here
                ev_date, ev_val = estimate_ev_from_components(sym, s.fmp_api_key, asof, s=s)
            except Exception as ee:
                log.error(f"EV estimation failed for {sym}: {ee}")
                # Guard against unbound locals later
                ev_date, ev_val = asof, np.nan

        # 2) EBITDA (SEC TTM) as of ev_date
        sec = ttm_ebitda_from_sec(sym, as_of=ev_date, s=s)
        ebitda = sec["ttm_ebitda"]
        ratio = np.nan if (pd.isna(ebitda) or ebitda == 0.0) else ev_val / ebitda

        # 3) PEG ratio from Alpha Vantage (with rate limiting)
        peg_ratio = get_alpha_vantage_peg(sym)
        # Rate limit: 5 calls/minute = 12 seconds between calls
        if not pd.isna(peg_ratio):
            time.sleep(12)

        rows.append({
            "ticker": sym,
            "as_of": ev_date,
            "enterprise_value": ev_val,
            "ttm_ebitda": ebitda,
            "ev_to_ebitda": ratio,
            "ebitda_method": sec.get("method"),
            "peg_ratio": peg_ratio,
        })

    out = pd.DataFrame(rows)
    out["as_of"] = pd.to_datetime(out["as_of"], utc=True)

    # Bucket peers by quarter-end so close dates compare together
    out["as_of_bucket"] = (
        out["as_of"].dt.tz_convert("UTC").dt.tz_localize(None)
          .dt.to_period("Q").dt.end_time.dt.tz_localize("UTC")
)

    # --- Peer metrics on the bucket (quarter) ---
    grp = out.groupby("as_of_bucket", group_keys=False)
    out["peer_count"] = grp["ev_to_ebitda"].transform("count")
    peer_sum = grp["ev_to_ebitda"].transform("sum")
    out["peer_mean_excl_self"] = ((peer_sum - out["ev_to_ebitda"]) / (out["peer_count"] - 1)).where(out["peer_count"] > 1)
    out["valuation_gap_pct"] = (out["ev_to_ebitda"] - out["peer_mean_excl_self"]) / out["peer_mean_excl_self"]

    # NEW: continuous dial 0–100% with median at 50 (invert because lower EV/EBITDA is better)
    out["valuation_pct"] = grp["ev_to_ebitda"].transform(lambda s: median_anchored_pct(s, lower_is_better=True))
            # --- Percentile dial: 0–100 where higher = cheaper ---
            # rank(pct=True) in ascending order => cheapest gets smallest pct
        # --- NEW: pure percentile-rank dial (lower EV/EBITDA is better) ---
    def _empirical_percentile_lower_is_better(s: pd.Series, stretch_to_full_range: bool = False) -> pd.Series:
        s = s.astype(float)
        r = s.rank(pct=True, method="average")       # in (1/n .. 1]
        if stretch_to_full_range:
            rmin, rmax = r.min(), r.max()
            if rmax == rmin:                         # all equal → flat 50
                return pd.Series(50.0, index=s.index, dtype="float64")
            r = (r - rmin) / (rmax - rmin)           # now in [0..1]
        # invert so cheaper (lower) → higher %
        pct = (1.0 - r) * 100.0
        pct[s.isna()] = np.nan
        return pct

    out["valuation_pct_empirical"] = grp["ev_to_ebitda"].transform(_empirical_percentile_lower_is_better)
    
    rank_pct = grp["ev_to_ebitda"].rank(method="average", pct=True, ascending=True)
    val_dial_pct = (1.0 - rank_pct) * 100.0            # invert so cheapest → 100

        # If a peer bucket has only one name, set neutral 50
    val_dial_pct = np.where(out["peer_count"] == 1, 50.0, val_dial_pct)

    out["valuation_dial_pct"] = np.round(val_dial_pct, 1)

    # Quartile label for quick interpretation
    def _bucket(p):
        if pd.isna(p): return "NA"
        if p >= 75:    return "strong"
        if p < 25:     return "attention"
        return "neutral"

    out["valuation_quartile"] = out["valuation_dial_pct"].map(_bucket)

    # Keep a clean sort for deterministic output
    out = out.sort_values(["as_of_bucket", "ev_to_ebitda"], ascending=[True, True])
    return out
