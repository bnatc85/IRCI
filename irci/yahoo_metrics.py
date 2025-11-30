# irci/yahoo_metrics.py
"""
Additional Yahoo Finance metrics for Coverage and Trust dials.

Fetches:
- Analyst coverage (count, recommendations, price targets)
- Short interest data (short ratio, % of float)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Optional, Dict, List

from .logging import get_logger

log = get_logger("irci.yahoo_metrics")


def fetch_yahoo_metrics(ticker: str) -> Dict:
    """
    Fetch analyst coverage and short interest from Yahoo Finance.

    Returns:
        Dict with analyst and short interest data
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info

        # Analyst coverage metrics
        analyst_count = info.get('numberOfAnalystOpinions')
        target_high = info.get('targetHighPrice')
        target_low = info.get('targetLowPrice')
        target_mean = info.get('targetMeanPrice')
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        recommendation = info.get('recommendationKey', '')
        recommendation_mean = info.get('recommendationMean')  # 1=strong buy, 5=sell

        # Calculate upside/downside potential
        if target_mean and current_price and current_price > 0:
            price_target_upside = ((target_mean - current_price) / current_price) * 100
        else:
            price_target_upside = np.nan

        # Short interest metrics
        short_ratio = info.get('shortRatio')  # Days to cover
        short_pct_float = info.get('shortPercentOfFloat')
        shares_short = info.get('sharesShort')
        shares_short_prior = info.get('sharesShortPriorMonth')

        # Calculate short interest change
        if shares_short and shares_short_prior and shares_short_prior > 0:
            short_change_pct = ((shares_short - shares_short_prior) / shares_short_prior) * 100
        else:
            short_change_pct = np.nan

        # Convert short % to actual percentage (Yahoo returns as decimal)
        if short_pct_float is not None:
            short_pct_float = short_pct_float * 100

        return {
            "ticker": ticker,
            # Analyst coverage
            "analyst_count": analyst_count if analyst_count else 0,
            "target_high": target_high,
            "target_low": target_low,
            "target_mean": target_mean,
            "current_price": current_price,
            "price_target_upside_pct": price_target_upside,
            "recommendation": recommendation,
            "recommendation_mean": recommendation_mean,
            # Short interest
            "short_ratio": short_ratio,
            "short_pct_float": short_pct_float,
            "shares_short": shares_short,
            "short_change_pct": short_change_pct,
            "data_available": True
        }

    except Exception as e:
        log.warning(f"Yahoo metrics failed for {ticker}: {e}")
        return {
            "ticker": ticker,
            "analyst_count": 0,
            "short_pct_float": np.nan,
            "short_ratio": np.nan,
            "data_available": False,
            "error": str(e)
        }


def analyst_coverage_score(data: Dict) -> float:
    """
    Calculate analyst coverage score (0-100) for Coverage dial.

    More analysts = more coverage = higher score
    """
    analyst_count = data.get('analyst_count', 0) or 0

    if analyst_count == 0:
        return 0.0
    elif analyst_count <= 5:
        # Low coverage: 0-30
        return analyst_count * 6
    elif analyst_count <= 15:
        # Medium coverage: 30-60
        return 30 + (analyst_count - 5) * 3
    elif analyst_count <= 30:
        # Good coverage: 60-85
        return 60 + (analyst_count - 15) * 1.67
    else:
        # Excellent coverage: 85-100
        return min(100, 85 + (analyst_count - 30) * 0.5)


def short_interest_score(data: Dict) -> float:
    """
    Calculate short interest score (0-100) for Trust dial.

    Lower short interest = more trust = higher score
    High short interest = less trust = lower score
    """
    short_pct = data.get('short_pct_float')

    if short_pct is None or np.isnan(short_pct):
        return np.nan

    # Scoring: Low short interest = high trust
    # < 2% short = excellent (90-100)
    # 2-5% = good (70-90)
    # 5-10% = moderate (50-70)
    # 10-20% = concerning (30-50)
    # > 20% = high risk (0-30)

    if short_pct < 2:
        return 90 + (2 - short_pct) * 5  # 90-100
    elif short_pct < 5:
        return 90 - (short_pct - 2) * 6.67  # 70-90
    elif short_pct < 10:
        return 70 - (short_pct - 5) * 4  # 50-70
    elif short_pct < 20:
        return 50 - (short_pct - 10) * 2  # 30-50
    else:
        return max(0, 30 - (short_pct - 20) * 1.5)  # 0-30


def recommendation_score(data: Dict) -> float:
    """
    Calculate recommendation score (0-100) for Trust dial.

    recommendation_mean: 1.0 = Strong Buy, 5.0 = Sell
    """
    rec_mean = data.get('recommendation_mean')

    if rec_mean is None or np.isnan(rec_mean):
        return np.nan

    # Convert 1-5 scale to 0-100 (inverted)
    # 1.0 = 100, 5.0 = 0
    return max(0, min(100, (5 - rec_mean) / 4 * 100))


def get_yahoo_metrics_batch(symbols: List[str]) -> pd.DataFrame:
    """
    Fetch Yahoo metrics for multiple symbols.

    Returns DataFrame with analyst coverage and short interest.
    """
    rows = []

    for symbol in symbols:
        try:
            data = fetch_yahoo_metrics(symbol)

            # Calculate component scores
            coverage_score = analyst_coverage_score(data)
            short_score = short_interest_score(data)
            rec_score = recommendation_score(data)

            rows.append({
                "ticker": symbol,
                # Raw metrics
                "analyst_count": data.get("analyst_count", 0),
                "target_mean": data.get("target_mean"),
                "price_target_upside_pct": data.get("price_target_upside_pct"),
                "recommendation": data.get("recommendation", ""),
                "recommendation_mean": data.get("recommendation_mean"),
                "short_pct_float": data.get("short_pct_float"),
                "short_ratio": data.get("short_ratio"),
                "short_change_pct": data.get("short_change_pct"),
                # Scores
                "analyst_coverage_score": coverage_score,
                "short_interest_score": short_score,
                "recommendation_score": rec_score,
                "data_available": data.get("data_available", False)
            })

            log.info(f"{symbol}: {data.get('analyst_count', 0)} analysts, "
                    f"{data.get('short_pct_float', 'N/A')}% short")

        except Exception as e:
            log.warning(f"Error fetching Yahoo metrics for {symbol}: {e}")
            rows.append({
                "ticker": symbol,
                "analyst_count": 0,
                "analyst_coverage_score": 0,
                "short_interest_score": np.nan,
                "recommendation_score": np.nan,
                "data_available": False
            })

    return pd.DataFrame(rows)
