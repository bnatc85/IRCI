# irci/institutional_ownership.py
"""
Institutional Ownership Data from SEC 13F Filings

Fetches and analyzes institutional ownership metrics:
- Total institutional ownership %
- Number of institutional holders
- Top 10 holders concentration
- Quarter-over-quarter changes in ownership
- Smart money indicators (hedge funds vs mutual funds)
"""
from __future__ import annotations
import requests
import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from .config import Settings
from .logging import get_logger

log = get_logger("irci.institutional")


def fetch_institutional_holders_fmp(
    ticker: str,
    settings: Optional[Settings] = None
) -> Dict:
    """
    Fetch institutional holders from FMP API.

    Returns:
        Dict with institutional ownership data
    """
    s = settings or Settings.load()
    api_key = s.fmp_api_key

    if not api_key:
        log.warning("FMP API key not configured for institutional ownership")
        return {"error": "No API key"}

    url = f"https://financialmodelingprep.com/api/v3/institutional-holder/{ticker}"
    params = {"apikey": api_key}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            return {
                "ticker": ticker,
                "holders": data,
                "holder_count": len(data),
                "source": "fmp"
            }
        else:
            log.info(f"No institutional holders found for {ticker}")
            return {"holders": [], "holder_count": 0}

    except requests.RequestException as e:
        log.warning(f"Error fetching institutional holders for {ticker}: {e}")
        return {"error": str(e)}


def fetch_institutional_ownership_fmp(
    ticker: str,
    settings: Optional[Settings] = None
) -> Dict:
    """
    Fetch institutional ownership percentage from FMP.

    Returns ownership % and other aggregate metrics.
    """
    s = settings or Settings.load()
    api_key = s.fmp_api_key

    if not api_key:
        return {"institutional_ownership_pct": np.nan, "error": "No API key"}

    # Try the stock ownership endpoint
    url = f"https://financialmodelingprep.com/api/v4/institutional-ownership/symbol-ownership"
    params = {
        "symbol": ticker,
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            latest = data[0]
            return {
                "ticker": ticker,
                "institutional_ownership_pct": latest.get("ownershipPercent", np.nan),
                "investor_count": latest.get("investorsHolding", 0),
                "date": latest.get("date", ""),
                "source": "fmp"
            }
    except Exception as e:
        log.debug(f"FMP ownership endpoint failed for {ticker}: {e}")

    # Fallback: Calculate from holders list
    holders_data = fetch_institutional_holders_fmp(ticker, s)

    if holders_data.get("holders"):
        holders = holders_data["holders"]
        total_shares = sum(h.get("shares", 0) for h in holders)
        holder_count = len(holders)

        return {
            "ticker": ticker,
            "total_institutional_shares": total_shares,
            "holder_count": holder_count,
            "institutional_ownership_pct": np.nan,  # Need shares outstanding to calculate
            "source": "fmp_calculated"
        }

    return {"institutional_ownership_pct": np.nan, "holder_count": 0}


def fetch_institutional_ownership_yahoo(ticker: str) -> Dict:
    """
    Fetch institutional ownership from Yahoo Finance as fallback.
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info

        inst_pct = info.get("heldPercentInstitutions", np.nan)
        if inst_pct is not None and not np.isnan(inst_pct):
            inst_pct = float(inst_pct) * 100  # Convert to percentage

        return {
            "ticker": ticker,
            "institutional_ownership_pct": inst_pct,
            "insider_pct": info.get("heldPercentInsiders", np.nan),
            "float_shares": info.get("floatShares", np.nan),
            "shares_outstanding": info.get("sharesOutstanding", np.nan),
            "source": "yahoo"
        }
    except Exception as e:
        log.warning(f"Yahoo institutional data failed for {ticker}: {e}")
        return {"institutional_ownership_pct": np.nan, "error": str(e)}


def get_institutional_ownership(
    ticker: str,
    settings: Optional[Settings] = None
) -> Dict:
    """
    Get institutional ownership with fallback sources.

    Returns:
        Dict with:
        - institutional_ownership_pct: % held by institutions (0-100)
        - holder_count: Number of institutional holders
        - top_holders: List of top 10 holders
        - concentration: % held by top 10
    """
    s = settings or Settings.load()

    # Try FMP first
    fmp_data = fetch_institutional_ownership_fmp(ticker, s)

    if fmp_data.get("institutional_ownership_pct") and not np.isnan(fmp_data.get("institutional_ownership_pct", np.nan)):
        ownership_pct = fmp_data["institutional_ownership_pct"]
    else:
        # Fallback to Yahoo
        yahoo_data = fetch_institutional_ownership_yahoo(ticker)
        ownership_pct = yahoo_data.get("institutional_ownership_pct", np.nan)

    # Get holder details
    holders_data = fetch_institutional_holders_fmp(ticker, s)
    holders = holders_data.get("holders", [])

    # Calculate top 10 concentration
    top_10 = sorted(holders, key=lambda x: x.get("shares", 0), reverse=True)[:10]
    top_10_shares = sum(h.get("shares", 0) for h in top_10)
    total_shares = sum(h.get("shares", 0) for h in holders)

    if total_shares > 0:
        top_10_concentration = (top_10_shares / total_shares) * 100
    else:
        top_10_concentration = np.nan

    # Classify holder types (hedge funds, mutual funds, etc.)
    hedge_fund_keywords = ['hedge', 'capital', 'partners', 'management', 'advisors']
    mutual_fund_keywords = ['fund', 'trust', 'etf', 'index', 'vanguard', 'blackrock', 'fidelity']

    hedge_fund_shares = 0
    mutual_fund_shares = 0

    for h in holders:
        name = h.get("holder", "").lower()
        shares = h.get("shares", 0)

        if any(kw in name for kw in hedge_fund_keywords):
            hedge_fund_shares += shares
        if any(kw in name for kw in mutual_fund_keywords):
            mutual_fund_shares += shares

    return {
        "ticker": ticker,
        "institutional_ownership_pct": ownership_pct,
        "holder_count": len(holders),
        "top_10_concentration": top_10_concentration,
        "top_10_holders": [
            {
                "name": h.get("holder", ""),
                "shares": h.get("shares", 0),
                "change": h.get("change", 0)
            }
            for h in top_10
        ],
        "hedge_fund_pct": (hedge_fund_shares / total_shares * 100) if total_shares > 0 else np.nan,
        "mutual_fund_pct": (mutual_fund_shares / total_shares * 100) if total_shares > 0 else np.nan,
        "total_institutional_shares": total_shares
    }


def institutional_ownership_score(
    ticker: str,
    settings: Optional[Settings] = None
) -> Dict:
    """
    Calculate institutional ownership contribution to Liquidity dial.

    Higher institutional ownership = more liquidity (larger block trades)
    But too concentrated = less liquidity (illiquid blocks)

    Returns:
        Dict with:
        - raw_ownership_pct: Raw institutional ownership %
        - ownership_score: 0-100 score for liquidity contribution
        - quality_factors: Dict of quality adjustments
    """
    data = get_institutional_ownership(ticker, settings)

    ownership_pct = data.get("institutional_ownership_pct", np.nan)
    holder_count = data.get("holder_count", 0)
    concentration = data.get("top_10_concentration", np.nan)

    if np.isnan(ownership_pct):
        return {
            "raw_ownership_pct": np.nan,
            "ownership_score": np.nan,
            "data_available": False
        }

    # Score based on ownership % (optimal range is 40-80%)
    # Too low = no institutional interest
    # Too high = float concerns
    if ownership_pct < 20:
        ownership_factor = ownership_pct / 20 * 0.5  # 0-0.5 for <20%
    elif ownership_pct <= 80:
        ownership_factor = 0.5 + (ownership_pct - 20) / 60 * 0.5  # 0.5-1.0 for 20-80%
    else:
        ownership_factor = 1.0 - (ownership_pct - 80) / 20 * 0.3  # Slight penalty for >80%

    # Holder count factor (more holders = more liquidity sources)
    if holder_count < 50:
        holder_factor = holder_count / 50 * 0.5
    elif holder_count <= 500:
        holder_factor = 0.5 + (holder_count - 50) / 450 * 0.5
    else:
        holder_factor = 1.0

    # Concentration penalty (too concentrated = less liquid)
    if not np.isnan(concentration):
        if concentration > 70:
            concentration_penalty = (concentration - 70) / 30 * 0.2
        else:
            concentration_penalty = 0
    else:
        concentration_penalty = 0

    # Combined score (0-100)
    ownership_score = (
        ownership_factor * 0.5 +
        holder_factor * 0.3 +
        (1 - concentration_penalty) * 0.2
    ) * 100

    return {
        "raw_ownership_pct": ownership_pct,
        "holder_count": holder_count,
        "top_10_concentration": concentration,
        "ownership_score": round(ownership_score, 1),
        "data_available": True,
        "quality_factors": {
            "ownership_factor": round(ownership_factor, 3),
            "holder_factor": round(holder_factor, 3),
            "concentration_penalty": round(concentration_penalty, 3)
        }
    }


def get_ownership_for_liquidity(
    symbols: List[str],
    settings: Optional[Settings] = None
) -> pd.DataFrame:
    """
    Get institutional ownership data for multiple symbols.

    Returns DataFrame compatible with liquidity dial integration.
    """
    s = settings or Settings.load()

    rows = []
    for symbol in symbols:
        try:
            score_data = institutional_ownership_score(symbol, s)
            rows.append({
                "ticker": symbol,
                "institutional_pct": score_data.get("raw_ownership_pct", np.nan),
                "holder_count": score_data.get("holder_count", 0),
                "inst_ownership_score": score_data.get("ownership_score", np.nan),
                "data_available": score_data.get("data_available", False)
            })
        except Exception as e:
            log.warning(f"Error getting ownership for {symbol}: {e}")
            rows.append({
                "ticker": symbol,
                "institutional_pct": np.nan,
                "holder_count": 0,
                "inst_ownership_score": np.nan,
                "data_available": False
            })

    return pd.DataFrame(rows)
