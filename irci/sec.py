from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import requests

from .config import Settings
from .logging import get_logger

# --- timezone normalization helpers (force UTC-naive for all comparisons) ---
def _naive_utc_ts(ts):
    ts = pd.Timestamp(ts)
    if ts.tz is None:
        return ts.tz_localize("UTC").tz_localize(None)
    return ts.tz_convert("UTC").tz_localize(None)

def _naive_utc_index(idx) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(idx)
    if idx.tz is None:
        return idx.tz_localize("UTC").tz_localize(None)
    return idx.tz_convert("UTC").tz_localize(None)


log = get_logger("irci.sec")

_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

def _headers(s: Settings) -> Dict[str, str]:
    return {
        "User-Agent": s.user_agent or "IRCI/0.1 (contact@example.com)",
        "Accept": "application/json",
    }

def _get_json(url: str, s: Settings) -> Any:
    r = requests.get(url, headers=_headers(s), timeout=60)
    r.raise_for_status()
    return r.json()

def resolve_cik(symbol: str, s: Optional[Settings] = None) -> str:
    s = s or Settings.load()
    cache = s.data_dir / "sec_company_tickers.json"
    data = None
    if cache.exists():
        try:
            data = pd.read_json(cache)
        except Exception:
            data = None
    if data is None:
        log.info("Downloading SEC company_tickers.json …")
        js = _get_json(_COMPANY_TICKERS_URL, s)
        rows = list(js.values()) if isinstance(js, dict) else js
        data = pd.DataFrame(rows)
        cache.write_text(pd.Series(rows).to_json(orient="values"))
    sym = symbol.upper()
    row = data.loc[data["ticker"].str.upper() == sym]
    if row.empty:
        raise ValueError(f"Ticker not found in SEC mapping: {symbol}")
    cik = int(row.iloc[0]["cik_str"])
    return f"{cik:010d}"

def company_facts(cik_padded: str, s: Optional[Settings] = None) -> Dict[str, Any]:
    s = s or Settings.load()
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    return _get_json(url, s)

# ---------- Helpers for "duration" (quarterly) series (e.g., EBITDA) ----------

def _series_from_fact(facts: Dict[str, Any], tag: str, units: str = "USD") -> pd.Series:
    try:
        items = facts["facts"]["us-gaap"][tag]["units"][units]
    except KeyError:
        return pd.Series(dtype="float64")
    df = pd.DataFrame(items)
    if "end" not in df.columns or "val" not in df.columns:
        return pd.Series(dtype="float64")
    df["end"] = pd.to_datetime(df["end"], utc=True)
    df = df.dropna(subset=["end", "val"])
    df = df[df["form"].isin(["10-Q", "10-Q/A", "10-K", "10-K/A"])]
    df = df.sort_values(["end", "filed"]).drop_duplicates(subset=["end"], keep="last")
    s = pd.Series(df["val"].values, index=df["end"].values, dtype="float64").sort_index()
    s = s.sort_index()
    s.index = _naive_utc_index(s.index)
    return s

def _quarterly_series_from_possible_ytd(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    s = series.copy().astype(float)
    def _fix(group: pd.Series) -> pd.Series:
        if group.is_monotonic_increasing and len(group) <= 4:
            return group.diff().fillna(group.iloc[0])
        return group
    return s.groupby(s.index.year, group_keys=False).apply(_fix)

def ttm_ebitda_from_sec(symbol: str, as_of: Optional[pd.Timestamp] = None, s: Optional[Settings] = None) -> dict:
    s = s or Settings.load()
    cik = resolve_cik(symbol, s)
    facts = company_facts(cik, s)

    ebitda_q = _series_from_fact(facts, "EarningsBeforeInterestTaxesDepreciationAndAmortization")
    opinc_q = _series_from_fact(facts, "OperatingIncomeLoss")
    da_q = _series_from_fact(facts, "DepreciationAndAmortization")

    ebitda_q = _quarterly_series_from_possible_ytd(ebitda_q)
    opinc_q = _quarterly_series_from_possible_ytd(opinc_q)
    da_q = _quarterly_series_from_possible_ytd(da_q)

    method = None
    q_series = pd.Series(dtype="float64")
    if not ebitda_q.empty:
        q_series = ebitda_q
        method = "us-gaap:EBITDA"
    elif not opinc_q.empty and not da_q.empty:
        q_series = opinc_q.add(da_q, fill_value=0.0)
        method = "OperatingIncome + D&A"
    elif not opinc_q.empty:
        q_series = opinc_q
        method = "OperatingIncome (fallback)"
    else:
        return {"symbol": symbol.upper(), "as_of": as_of, "ttm_ebitda": np.nan, "method": "unavailable"}

    q_series = q_series.sort_index()
    if as_of is None:
        as_of = _naive_utc_ts(q_series.index.max())
    else:
        as_of = _naive_utc_ts(as_of)
    q_series.index = _naive_utc_index(q_series.index)
    q_series = q_series.loc[q_series.index <= as_of]

    ttm = q_series.rolling(4).sum().dropna()
    if ttm.empty:
        return {"symbol": symbol.upper(), "as_of": as_of, "ttm_ebitda": np.nan, "method": f"{method} (insufficient quarters)"}

    return {"symbol": symbol.upper(), "as_of": as_of, "ttm_ebitda": float(ttm.iloc[-1]), "method": method}

# ---------- Helpers for "instant" (point-in-time) series (e.g., debt, cash, shares) ----------

def _instant_series(facts: Dict[str, Any], tag: str, units: str) -> pd.Series:
    try:
        items = facts["facts"]["us-gaap"][tag]["units"][units]
    except KeyError:
        return pd.Series(dtype="float64")
    df = pd.DataFrame(items)
    if "end" not in df.columns or "val" not in df.columns:
        return pd.Series(dtype="float64")
    df["end"] = pd.to_datetime(df["end"], utc=True)
    df = df.dropna(subset=["end", "val"])
    df = df[df["form"].isin(["10-Q", "10-Q/A", "10-K", "10-K/A"])]
    df = df.sort_values(["end", "filed"]).drop_duplicates(subset=["end"], keep="last")
    s = pd.Series(df["val"].values, index=df["end"].values, dtype="float64").sort_index()
    s = s.sort_index()
    s.index = _naive_utc_index(s.index)
    return s

def _latest_value_on_or_before(series: pd.Series, as_of: pd.Timestamp):
    if series.empty:
        return None, None
    idx = _naive_utc_index(series.index)
    ts = _naive_utc_ts(as_of)
    pos = idx.searchsorted(ts, side="right") - 1
    if pos < 0:
        pos = 0
    return pd.Timestamp(idx[pos]).tz_localize("UTC"), float(series.iloc[pos])

def debt_and_cash_from_sec(symbol: str, as_of: pd.Timestamp, s: Optional[Settings] = None) -> dict:
    """
    Get total debt and cash equivalents from SEC companyfacts (instant values).
    Returns {'as_of': ts, 'total_debt': float, 'cash_eq': float, 'method': str}
    """
    s = s or Settings.load()
    cik = resolve_cik(symbol, s)
    facts = company_facts(cik, s)

    # Debt candidates (try total first, else build from components)
    debt_total = _instant_series(facts, "Debt", "USD")
    debt_current = _instant_series(facts, "DebtCurrent", "USD")
    ltd_current = _instant_series(facts, "LongTermDebtCurrent", "USD")
    ltd_noncurrent = _instant_series(facts, "LongTermDebtNoncurrent", "USD")
    stb = _instant_series(facts, "ShortTermBorrowings", "USD")
    ltd_cap_lease = _instant_series(facts, "LongTermDebtAndCapitalLeaseObligations", "USD")

    cash_eq = None
    for tag in ["CashAndCashEquivalentsAtCarryingValue",
                "CashCashEquivalentsAndShortTermInvestments",
                "CashAndShortTermInvestments",
                "CashAndCashEquivalents"]:
        s_cash = _instant_series(facts, tag, "USD")
        if not s_cash.empty:
            cash_eq = s_cash
            cash_tag = tag
            break
    if cash_eq is None:
        cash_eq = pd.Series(dtype="float64")
        cash_tag = "none"

    # pick dates/values
    as_of = pd.to_datetime(as_of, utc=True)
    # Debt
    d_date, d_val = _latest_value_on_or_before(debt_total, as_of)
    method = "us-gaap:Debt"
    if d_val is None:
        # sum components (only if present)
        comps = []
        for ser in [debt_current, ltd_current, ltd_noncurrent, stb, ltd_cap_lease]:
            date, val = _latest_value_on_or_before(ser, as_of)
            if val is not None:
                comps.append((date, val))
        if comps:
            d_val = float(sum(v for _, v in comps))
            d_date = max(dt for dt, _ in comps)
            method = "Debt components sum"
        else:
            d_val = 0.0
            d_date = None
            method = "Debt unavailable → 0.0"

    # Cash & equiv
    c_date, c_val = _latest_value_on_or_before(cash_eq, as_of)
    if c_val is None:
        c_val = 0.0
        c_date = None
        cash_tag = "none→0.0"

    # align date conservatively
    dates = [d for d in [d_date, c_date] if d is not None]
    as_of_used = max(dates) if dates else as_of
    return {"as_of": as_of_used, "total_debt": float(d_val), "cash_eq": float(c_val), "method": f"{method}; cash={cash_tag}"}

def shares_outstanding_from_sec(symbol: str, as_of: pd.Timestamp, s: Optional[Settings] = None) -> dict:
    """
    Shares outstanding (instant). Try 'EntityCommonStockSharesOutstanding' then 'CommonStockSharesOutstanding'.
    Returns {'as_of': ts, 'shares_outstanding': float|None, 'tag': str}
    """
    s = s or Settings.load()
    cik = resolve_cik(symbol, s)
    facts = company_facts(cik, s)

    for tag in ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"]:
        ser = _instant_series(facts, tag, "shares")
        date, val = _latest_value_on_or_before(ser, pd.to_datetime(as_of, utc=True))
        if val is not None:
            return {"as_of": date, "shares_outstanding": float(val), "tag": tag}
    return {"as_of": None, "shares_outstanding": None, "tag": "unavailable"}
