# irci/media_fetchers/social_sentiment.py
"""
Social Sentiment Fetcher for Reddit (r/wallstreetbets) and StockTwits

Aggregates retail investor sentiment from social platforms:
- Reddit via ApeWisdom API (free, no auth required) - tracks WSB mentions
- StockTwits API (free tier available)
"""
from __future__ import annotations
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from ..logging import get_logger

log = get_logger("irci.social_sentiment")

# Cache for ApeWisdom data (refreshes every 5 minutes)
_apewisdom_cache = {"data": None, "timestamp": None}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_apewisdom_data() -> List[Dict]:
    """
    Fetch and cache ApeWisdom data for all stocks.
    Returns list of stock sentiment data from Reddit/WSB.
    """
    global _apewisdom_cache

    now = datetime.now()
    if (_apewisdom_cache["data"] is not None and
        _apewisdom_cache["timestamp"] is not None and
        (now - _apewisdom_cache["timestamp"]).total_seconds() < _CACHE_TTL_SECONDS):
        return _apewisdom_cache["data"]

    try:
        url = "https://apewisdom.io/api/v1.0/filter/all-stocks"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        _apewisdom_cache["data"] = results
        _apewisdom_cache["timestamp"] = now
        log.info(f"ApeWisdom: fetched {len(results)} stocks from Reddit sentiment")
        return results

    except Exception as e:
        log.warning(f"ApeWisdom API error: {e}")
        return _apewisdom_cache.get("data", []) or []


def fetch_reddit_sentiment(ticker: str) -> Dict:
    """
    Fetch Reddit/WSB sentiment from ApeWisdom API.

    Free API that tracks r/wallstreetbets and other investing subreddits.
    https://apewisdom.io/api/

    Returns:
        Dict with sentiment data including:
        - sentiment: 'Bullish', 'Bearish', or 'Neutral' (based on rank change)
        - sentiment_score: -1 to 1 scale
        - mentions: Number of mentions in past 24h
        - rank: Popularity rank on WSB
        - upvotes: Total upvotes
    """
    try:
        data = _get_apewisdom_data()

        if not data:
            return {"error": "No data available", "sentiment_score": np.nan}

        # Find our ticker in the results
        ticker_upper = ticker.upper()
        for item in data:
            item_ticker = item.get("ticker", "").upper()
            if item_ticker == ticker_upper:
                rank = item.get("rank", 0)
                mentions = item.get("mentions", 0)
                upvotes = item.get("upvotes", 0)
                rank_24h_ago = item.get("rank_24h_ago", rank)

                # Calculate sentiment based on rank change and activity
                # Rank improvement = bullish momentum, rank decline = bearish
                rank_change = (rank_24h_ago - rank) if rank_24h_ago else 0

                # Base sentiment on rank change
                if rank_change > 5:
                    sentiment = "Bullish"
                    sentiment_score = 0.6
                elif rank_change > 0:
                    sentiment = "Bullish"
                    sentiment_score = 0.3
                elif rank_change < -5:
                    sentiment = "Bearish"
                    sentiment_score = -0.4
                elif rank_change < 0:
                    sentiment = "Bearish"
                    sentiment_score = -0.2
                else:
                    sentiment = "Neutral"
                    sentiment_score = 0.0

                # Boost score based on activity level (mentions + upvotes)
                activity_score = mentions + (upvotes / 10)
                if activity_score > 200:
                    sentiment_score *= 1.3  # High activity = stronger signal
                elif activity_score > 50:
                    sentiment_score *= 1.1
                elif activity_score < 10:
                    sentiment_score *= 0.7  # Low activity = weaker signal

                sentiment_score = float(np.clip(sentiment_score, -1, 1))

                return {
                    "ticker": ticker_upper,
                    "sentiment": sentiment,
                    "sentiment_score": sentiment_score,
                    "mentions": mentions,
                    "upvotes": upvotes,
                    "rank": rank,
                    "rank_24h_ago": rank_24h_ago,
                    "rank_change": rank_change,
                    "source": "apewisdom_reddit"
                }

        # Ticker not found in WSB trending - return neutral
        return {
            "ticker": ticker_upper,
            "sentiment": "Neutral",
            "sentiment_score": 0.0,
            "mentions": 0,
            "rank": None,
            "source": "apewisdom_reddit",
            "note": "Not trending on Reddit"
        }

    except requests.RequestException as e:
        log.warning(f"Reddit sentiment API error for {ticker}: {e}")
        return {"error": str(e), "sentiment_score": np.nan}
    except Exception as e:
        log.warning(f"Error processing Reddit sentiment for {ticker}: {e}")
        return {"error": str(e), "sentiment_score": np.nan}


def fetch_stocktwits_sentiment(ticker: str) -> Dict:
    """
    Fetch StockTwits sentiment for a ticker.

    StockTwits API provides:
    - Message volume
    - Bullish/Bearish ratio from user-tagged messages
    - Trending status

    Returns:
        Dict with sentiment data
    """
    try:
        # StockTwits API - free tier
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        headers = {"User-Agent": "IRCI/1.0"}

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 404:
            return {
                "ticker": ticker.upper(),
                "sentiment_score": np.nan,
                "error": "Symbol not found on StockTwits"
            }

        response.raise_for_status()
        data = response.json()

        symbol_data = data.get("symbol", {})
        messages = data.get("messages", [])

        # Count bullish vs bearish sentiment from messages
        bullish_count = 0
        bearish_count = 0

        for msg in messages[:50]:  # Analyze last 50 messages
            sentiment = msg.get("entities", {}).get("sentiment", {})
            if sentiment:
                if sentiment.get("basic") == "Bullish":
                    bullish_count += 1
                elif sentiment.get("basic") == "Bearish":
                    bearish_count += 1

        total_sentiment = bullish_count + bearish_count

        if total_sentiment > 0:
            # Calculate sentiment score (-1 to 1)
            sentiment_score = (bullish_count - bearish_count) / total_sentiment
        else:
            sentiment_score = 0.0

        # Check if trending
        is_trending = symbol_data.get("is_following", False) or len(messages) > 20

        return {
            "ticker": ticker.upper(),
            "sentiment_score": sentiment_score,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "message_volume": len(messages),
            "is_trending": is_trending,
            "watchlist_count": symbol_data.get("watchlist_count", 0),
            "source": "stocktwits"
        }

    except requests.RequestException as e:
        log.warning(f"StockTwits API error for {ticker}: {e}")
        return {"error": str(e), "sentiment_score": np.nan}
    except Exception as e:
        log.warning(f"Error processing StockTwits for {ticker}: {e}")
        return {"error": str(e), "sentiment_score": np.nan}


def get_combined_social_sentiment(ticker: str) -> Dict:
    """
    Get combined social sentiment from Reddit and StockTwits.

    Combines multiple sources with weighting based on activity level.

    Returns:
        Dict with:
        - combined_score: Weighted average sentiment (-1 to 1)
        - reddit_data: Full Reddit sentiment data
        - stocktwits_data: Full StockTwits sentiment data
        - confidence: How much to weight this signal (0-1)
    """
    reddit_data = fetch_reddit_sentiment(ticker)
    stocktwits_data = fetch_stocktwits_sentiment(ticker)

    scores = []
    weights = []

    # Reddit sentiment
    reddit_score = reddit_data.get("sentiment_score", np.nan)
    if not np.isnan(reddit_score):
        reddit_mentions = reddit_data.get("mentions", 0)
        # Weight by activity level
        reddit_weight = min(1.0, reddit_mentions / 50) if reddit_mentions > 0 else 0.3
        scores.append(reddit_score)
        weights.append(reddit_weight)

    # StockTwits sentiment
    st_score = stocktwits_data.get("sentiment_score", np.nan)
    if not np.isnan(st_score):
        st_volume = stocktwits_data.get("message_volume", 0)
        # Weight by message volume
        st_weight = min(1.0, st_volume / 30) if st_volume > 0 else 0.3
        scores.append(st_score)
        weights.append(st_weight)

    # Calculate weighted average
    if scores and weights:
        total_weight = sum(weights)
        combined_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        confidence = min(1.0, total_weight / 1.5)  # Full confidence at 1.5 total weight
    else:
        combined_score = np.nan
        confidence = 0.0

    return {
        "ticker": ticker.upper(),
        "combined_score": combined_score,
        "confidence": confidence,
        "reddit": reddit_data,
        "stocktwits": stocktwits_data,
        "sources_available": len(scores)
    }


def social_sentiment_score_for_trust(
    ticker: str,
    news_sentiment: Optional[float] = None
) -> Dict:
    """
    Calculate social sentiment contribution to Trust dial.

    Social sentiment is weighted as a modifier to news sentiment:
    - Strong agreement between social and news = boost confidence
    - Divergence = potential contrarian signal

    Args:
        ticker: Stock symbol
        news_sentiment: Optional existing news sentiment score (-1 to 1)

    Returns:
        Dict with:
        - social_sentiment_raw: Raw combined score (-1 to 1)
        - social_sentiment_score: Normalized 0-100 for Trust dial
        - divergence: Difference from news sentiment
        - retail_activity: Level of retail interest
    """
    social_data = get_combined_social_sentiment(ticker)

    combined_score = social_data.get("combined_score", np.nan)
    confidence = social_data.get("confidence", 0)

    if np.isnan(combined_score):
        return {
            "social_sentiment_raw": np.nan,
            "social_sentiment_score": np.nan,
            "data_available": False
        }

    # Convert to 0-100 scale for Trust dial
    # -1 to 1 → 0 to 100
    social_sentiment_score = (combined_score + 1) / 2 * 100

    # Calculate divergence from news if available
    divergence = np.nan
    if news_sentiment is not None and not np.isnan(news_sentiment):
        divergence = combined_score - news_sentiment

    # Determine retail activity level
    reddit_mentions = social_data.get("reddit", {}).get("mentions", 0)
    st_volume = social_data.get("stocktwits", {}).get("message_volume", 0)
    total_activity = reddit_mentions + st_volume

    if total_activity > 100:
        activity_level = "high"
    elif total_activity > 20:
        activity_level = "moderate"
    elif total_activity > 0:
        activity_level = "low"
    else:
        activity_level = "minimal"

    return {
        "social_sentiment_raw": combined_score,
        "social_sentiment_score": round(social_sentiment_score, 1),
        "confidence": round(confidence, 2),
        "divergence_from_news": divergence,
        "retail_activity": activity_level,
        "reddit_mentions": reddit_mentions,
        "stocktwits_volume": st_volume,
        "data_available": True,
        "sources": social_data.get("sources_available", 0)
    }


def get_social_sentiment_batch(symbols: List[str]) -> pd.DataFrame:
    """
    Get social sentiment for multiple symbols.

    Returns DataFrame compatible with Trust dial integration.
    """
    rows = []

    for symbol in symbols:
        try:
            score_data = social_sentiment_score_for_trust(symbol)
            rows.append({
                "ticker": symbol,
                "social_sentiment_raw": score_data.get("social_sentiment_raw", np.nan),
                "social_sentiment_score": score_data.get("social_sentiment_score", np.nan),
                "retail_activity": score_data.get("retail_activity", "unknown"),
                "confidence": score_data.get("confidence", 0),
                "data_available": score_data.get("data_available", False)
            })
        except Exception as e:
            log.warning(f"Error getting social sentiment for {symbol}: {e}")
            rows.append({
                "ticker": symbol,
                "social_sentiment_raw": np.nan,
                "social_sentiment_score": np.nan,
                "retail_activity": "error",
                "confidence": 0,
                "data_available": False
            })

    return pd.DataFrame(rows)
