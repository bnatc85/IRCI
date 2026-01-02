from __future__ import annotations
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
import requests
from requests import HTTPError
import os
import yfinance as yf

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

    Range compression based on peer group size:
    - 1 peer: return 50% (can't rank)
    - 2 peers: compress to 30-70% range
    - 3-5 peers: compress to 15-85% range (avoid extreme scores)
    - 6+ peers: full 0-100% range
    """
    s = s.astype(float)
    valid = s.dropna()
    n_valid = len(valid)

    # Handle edge cases with insufficient peer data
    if n_valid == 0:
        return pd.Series(index=s.index, dtype="float64")  # all NaN
    if n_valid == 1:
        # Single value - can't rank against peers, give neutral 50%
        pct = pd.Series(index=s.index, dtype="float64")
        pct.loc[valid.index] = 50.0
        return 100.0 - pct if lower_is_better else pct

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

    # Compress range based on peer group size to avoid overly extreme scores
    # With small peer groups, extreme 0%/100% values aren't statistically meaningful
    if n_valid == 2:
        # Compress from [0,100] to [30,70] centered at 50
        pct = 30.0 + (pct / 100.0) * 40.0
    elif n_valid <= 5:
        # Small peer group: compress from [0,100] to [15,85] centered at 50
        # This gives a 70pt spread instead of 100pt
        pct = 15.0 + (pct / 100.0) * 70.0

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

def get_peg_ratio(ticker: str, apikey: str = None) -> dict:
    """
    Fetch PEG ratio, trying Yahoo Finance first (most reliable).

    PEG = P/E divided by expected earnings growth rate.
    A PEG < 1 suggests undervaluation relative to growth; > 1 suggests overvaluation.

    Returns dict with peg_ratio and method.
    """
    # Try Yahoo Finance first (most reliable source)
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Yahoo has trailingPegRatio (TTM-based)
        peg = info.get('trailingPegRatio') or info.get('pegRatio')

        if peg is not None and peg > 0:
            peg = float(peg)
            # Filter out unreasonable PEG values (negative or extremely high)
            if peg < 0 or peg > 10:
                log.warning(f"PEG ratio {peg} for {ticker} outside reasonable range (0-10), excluding")
                return {"peg_ratio": np.nan, "method": "excluded_outlier"}

            log.info(f"Yahoo Finance PEG for {ticker}: {peg:.2f}")
            return {"peg_ratio": peg, "method": "yahoo_finance"}

    except Exception as e:
        log.warning(f"Yahoo Finance PEG fetch failed for {ticker}: {e}")

    # Fallback: Try FMP if Yahoo fails (requires premium API)
    if apikey:
        try:
            url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{ticker}?apikey={apikey}"
            log.info(f"GET FMP ratios-ttm for {ticker}")
            data = _get_json(url)

            if data and isinstance(data, list) and len(data) > 0:
                ratios = data[0]
                peg = ratios.get("pegRatioTTM")

                if peg is not None and peg > 0:
                    peg = float(peg)
                    if 0 < peg <= 10:
                        log.info(f"FMP PEG for {ticker}: {peg:.2f}")
                        return {"peg_ratio": peg, "method": "fmp_ratios_ttm"}

        except Exception as e:
            log.debug(f"FMP PEG fetch failed for {ticker}: {e}")

    log.warning(f"PEG ratio not available for {ticker}")
    return {"peg_ratio": np.nan, "method": "unavailable"}


def get_alpha_vantage_peg(ticker: str) -> float:
    """
    DEPRECATED: Use get_fmp_peg_ratio instead.
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

    try:
        so = shares_outstanding_from_sec(symbol, as_of_ts, s=s)
        shares = so.get("shares_outstanding")
    except ValueError as e:
        # Foreign ADRs (e.g., HEINY) won't be in SEC mapping
        log.warning(f"SEC shares lookup failed for {symbol}: {e}")
        shares = None
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
        try:
            sec_bs = debt_and_cash_from_sec(symbol, as_of_ts, s=s)
            debt = float(sec_bs["total_debt"])
            cash = float(sec_bs["cash_eq"])
            bs_date = sec_bs["as_of"] or as_of_ts
            bs_method = f"SEC facts ({sec_bs['method']})"
        except ValueError as sec_e:
            # Foreign ADRs (e.g., HEINY) won't be in SEC mapping
            log.warning(f"SEC debt/cash lookup also failed for {symbol}: {sec_e}; using 0 for debt/cash")
            debt = 0.0
            cash = 0.0
            bs_date = as_of_ts
            bs_method = "debt/cash unavailable"

    ev = mc_val + debt - cash
    as_of_used = max(mc_date, bs_date)
    log.info(f"EV components for {symbol}: MC={mc_val:,.0f} Debt={debt:,.0f} Cash={cash:,.0f} → EV={ev:,.0f} @ {as_of_used.date()} ({bs_method})")
    return as_of_used, ev

def ttm_ebitda_from_fmp(symbol: str, apikey: str, as_of: Optional[pd.Timestamp] = None) -> dict:
    """
    Backup EBITDA source from FMP income statement.
    Returns TTM EBITDA by summing last 4 quarters.
    """
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{symbol}?period=quarter&limit=16&apikey={apikey}"
    log.info(f"GET {url.replace(apikey, '***')}")
    try:
        js = _get_json(url)
        if not isinstance(js, list) or not js:
            raise ValueError(f"No income statement data for {symbol}")
        df = pd.DataFrame(js)
        if "date" not in df.columns:
            raise ValueError("Unexpected payload for income-statement")

        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date")

        # Filter to on-or-before as_of if specified
        if as_of is not None:
            as_of_naive = _naive_utc_ts(as_of)
            df.index = _naive_utc_index(df["date"])
            df = df[df.index <= as_of_naive]

        if len(df) < 4:
            return {"symbol": symbol, "as_of": as_of, "ttm_ebitda": np.nan, "method": "FMP (insufficient quarters)"}

        # Try to get EBITDA directly, or calculate from operating income + D&A
        if "ebitda" in df.columns:
            ttm_ebitda = df["ebitda"].tail(4).sum()
            method = "FMP EBITDA"
        elif "operatingIncome" in df.columns and "depreciationAndAmortization" in df.columns:
            df["calc_ebitda"] = df["operatingIncome"] + df["depreciationAndAmortization"].fillna(0)
            ttm_ebitda = df["calc_ebitda"].tail(4).sum()
            method = "FMP (OpInc + D&A)"
        elif "operatingIncome" in df.columns:
            ttm_ebitda = df["operatingIncome"].tail(4).sum()
            method = "FMP Operating Income (fallback)"
        else:
            return {"symbol": symbol, "as_of": as_of, "ttm_ebitda": np.nan, "method": "FMP unavailable"}

        latest_date = df["date"].iloc[-1]
        return {"symbol": symbol, "as_of": latest_date, "ttm_ebitda": float(ttm_ebitda), "method": method}

    except Exception as e:
        log.warning(f"FMP EBITDA fetch failed for {symbol}: {e}")
        return {"symbol": symbol, "as_of": as_of, "ttm_ebitda": np.nan, "method": f"FMP error: {str(e)[:50]}"}

def get_ev_ebitda_from_yahoo(symbol: str) -> dict:
    """
    Backup source: Get EV and EBITDA directly from Yahoo Finance.
    Yahoo often has pre-calculated values that can fill gaps.

    Returns dict with 'enterprise_value', 'ebitda', 'ev_to_ebitda', 'method'

    For financial companies (banks, etc.) that don't report EBITDA, falls back to P/E ratio
    as a comparable valuation metric (lower = cheaper, same as EV/EBITDA).
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Get EV and EBITDA from Yahoo's summary data
        ev = info.get('enterpriseValue')
        ebitda = info.get('ebitda')
        market_cap = info.get('marketCap')

        # Yahoo sometimes has the ratio pre-calculated
        ev_ebitda_ratio = info.get('enterpriseToEbitda')

        # If we have both EV and EBITDA, calculate ratio
        if ev and ebitda and ebitda != 0:
            calculated_ratio = ev / ebitda
            method = "Yahoo Finance (EV & EBITDA)"
        elif ev_ebitda_ratio:
            # Use pre-calculated ratio
            calculated_ratio = ev_ebitda_ratio
            method = "Yahoo Finance (ratio)"
            # Try to derive EBITDA if we have EV and ratio
            if ev and not ebitda:
                ebitda = ev / ev_ebitda_ratio
        else:
            # FALLBACK: For financials (banks, etc.) use P/E ratio instead of EV/EBITDA
            # Banks don't report EBITDA because interest is core to their business
            trailing_pe = info.get('trailingPE')
            forward_pe = info.get('forwardPE')
            pe_ratio = trailing_pe or forward_pe

            if pe_ratio and pe_ratio > 0:
                # Use P/E as valuation metric (lower = cheaper, same logic as EV/EBITDA)
                log.info(f"Using P/E ratio fallback for {symbol} (financial company): {pe_ratio:.2f}x")
                return {
                    "enterprise_value": float(ev or market_cap) if (ev or market_cap) else np.nan,
                    "ebitda": np.nan,  # Not applicable for financials
                    "ev_to_ebitda": float(pe_ratio),  # Use P/E as the valuation ratio
                    "method": "Yahoo Finance (P/E ratio - financial)"
                }

            return {
                "enterprise_value": ev if ev else np.nan,
                "ebitda": ebitda if ebitda else np.nan,
                "ev_to_ebitda": np.nan,
                "method": "Yahoo Finance (incomplete)"
            }

        log.info(f"Yahoo Finance provided EV/EBITDA for {symbol}: {calculated_ratio:.2f}x")
        return {
            "enterprise_value": float(ev) if ev else np.nan,
            "ebitda": float(ebitda) if ebitda else np.nan,
            "ev_to_ebitda": float(calculated_ratio) if calculated_ratio else np.nan,
            "method": method
        }

    except Exception as e:
        log.warning(f"Yahoo Finance fetch failed for {symbol}: {e}")
        return {
            "enterprise_value": np.nan,
            "ebitda": np.nan,
            "ev_to_ebitda": np.nan,
            "method": f"Yahoo error: {str(e)[:50]}"
        }

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

        # 2) EBITDA (SEC TTM first, then FMP backup, then Yahoo Finance) as of ev_date
        try:
            sec = ttm_ebitda_from_sec(sym, as_of=ev_date, s=s)
            ebitda = sec["ttm_ebitda"]
            ebitda_method = sec["method"]
        except ValueError as e:
            # Foreign ADRs (e.g., HEINY) won't be in SEC mapping - fall back to other sources
            log.info(f"SEC lookup failed for {sym}: {e}")
            ebitda = np.nan
            ebitda_method = "SEC unavailable"

        # If SEC EBITDA failed or returned NaN, try FMP as backup
        if pd.isna(ebitda) or ebitda == 0.0:
            log.info(f"SEC EBITDA unavailable for {sym}, trying FMP backup...")
            fmp_ebitda_result = ttm_ebitda_from_fmp(sym, s.fmp_api_key, as_of=ev_date)
            ebitda = fmp_ebitda_result["ttm_ebitda"]
            ebitda_method = fmp_ebitda_result["method"]

        # Calculate ratio
        ratio = np.nan if (pd.isna(ebitda) or ebitda == 0.0) else ev_val / ebitda

        # If we STILL don't have EV/EBITDA after all attempts, try Yahoo Finance as final backup
        if pd.isna(ratio) or pd.isna(ev_val) or pd.isna(ebitda):
            log.info(f"Primary sources failed for {sym}, trying Yahoo Finance as final backup...")
            yahoo_data = get_ev_ebitda_from_yahoo(sym)

            # Use Yahoo data if it's better than what we have
            if not pd.isna(yahoo_data["ev_to_ebitda"]):
                ratio = yahoo_data["ev_to_ebitda"]
                ebitda_method = yahoo_data["method"]

                # Also update EV and EBITDA if they're better
                if pd.isna(ev_val) and not pd.isna(yahoo_data["enterprise_value"]):
                    ev_val = yahoo_data["enterprise_value"]
                if pd.isna(ebitda) and not pd.isna(yahoo_data["ebitda"]):
                    ebitda = yahoo_data["ebitda"]

        # 3) PEG ratio (Yahoo Finance primary, FMP fallback)
        peg_result = get_peg_ratio(sym, s.fmp_api_key)
        peg_ratio = peg_result["peg_ratio"]
        peg_method = peg_result["method"]

        rows.append({
            "ticker": sym,
            "as_of": ev_date,
            "enterprise_value": ev_val,
            "ttm_ebitda": ebitda,
            "ev_to_ebitda": ratio,
            "ebitda_method": ebitda_method,
            "peg_ratio": peg_ratio,
            "peg_method": peg_method,
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

    # --- VALUATION SCORING ---
    # EV/EBITDA percentile: lower = cheaper = better (invert)
    out["ev_ebitda_pct"] = grp["ev_to_ebitda"].transform(lambda s: median_anchored_pct(s, lower_is_better=True))

    # PEG percentile: lower = cheaper relative to growth = better (invert)
    # PEG < 1 suggests undervaluation; PEG > 1 suggests overvaluation
    out["peg_pct"] = grp["peg_ratio"].transform(lambda s: median_anchored_pct(s, lower_is_better=True))

    # --- BLENDED VALUATION SCORE ---
    # Combine EV/EBITDA (70%) and PEG (30%) for growth-adjusted valuation
    # If PEG unavailable, use 100% EV/EBITDA
    # Rationale:
    #   - EV/EBITDA: Capital-structure neutral, compares value to operating earnings
    #   - PEG: Growth-adjusted, captures if you're paying appropriately for growth
    #   - Sources: CFA Institute (2025), Macabacus valuation multiples research
    def _blend_valuation(row):
        ev_pct = row["ev_ebitda_pct"]
        peg_pct = row["peg_pct"]

        if pd.isna(ev_pct):
            return np.nan
        if pd.isna(peg_pct):
            # No PEG available, use 100% EV/EBITDA
            return ev_pct
        # Blend: 70% EV/EBITDA + 30% PEG
        return 0.7 * ev_pct + 0.3 * peg_pct

    out["valuation_pct"] = out.apply(_blend_valuation, axis=1)

    # Track which method was used for transparency
    out["valuation_method"] = out.apply(
        lambda r: "blended_ev_peg" if not pd.isna(r["peg_pct"]) else "ev_ebitda_only",
        axis=1
    )

    # If a peer bucket has only one name, set neutral 50
    out["valuation_pct"] = np.where(out["peer_count"] == 1, 50.0, out["valuation_pct"])

    out["valuation_dial_pct"] = np.round(out["valuation_pct"], 1)

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
