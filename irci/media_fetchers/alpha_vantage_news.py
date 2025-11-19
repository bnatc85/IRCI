# irci/media_fetchers/alpha_vantage_news.py
"""
Alpha Vantage News API media fetcher - free tier includes news with sentiment
"""
from __future__ import annotations
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime


def alpha_vantage_news_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Fetch news articles for a ticker from Alpha Vantage News & Sentiment API.

    Free tier: 25 requests per day
    https://www.alphavantage.co/documentation/#news-sentiment

    Args:
        ticker: Stock symbol
        q_start: Quarter start date (pd.Timestamp)
        q_end: Quarter end date (pd.Timestamp)
        settings: Settings object (alpha_vantage_api_key optional)

    Returns:
        DataFrame with columns: published_at, url, domain, lang, headline, source
    """
    # Check for Alpha Vantage API key (can add to settings if needed)
    api_key = getattr(settings, "alpha_vantage_api_key", None) or "demo"

    # Alpha Vantage News API endpoint
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker.upper(),
        "limit": 1000,  # Max results
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "feed" not in data or not isinstance(data["feed"], list):
            print(f"Warning: No news feed found for {ticker} from Alpha Vantage")
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        # Convert to DataFrame
        df = pd.DataFrame(data["feed"])

        if df.empty:
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        # Normalize columns
        df["published_at"] = pd.to_datetime(df["time_published"], format="%Y%m%dT%H%M%S", utc=True, errors="coerce")
        df["headline"] = df["title"]
        df["source"] = df["source"]

        # Extract domain from URL
        if "url" in df.columns:
            df["domain"] = df["url"].apply(lambda u: urlparse(str(u)).netloc.lower() if pd.notna(u) else "")
        else:
            df["url"] = ""
            df["domain"] = ""

        df["lang"] = "en"  # Alpha Vantage news is English

        # Filter by date range
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]

        # Select required columns
        output_columns = ["published_at", "url", "domain", "lang", "headline", "source"]
        for col in output_columns:
            if col not in df.columns:
                df[col] = ""

        result = df[output_columns].copy()

        # Add ticker column for trust analysis
        result["ticker"] = ticker.upper()

        return result

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch news for {ticker} from Alpha Vantage API: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
    except Exception as e:
        print(f"Warning: Error processing Alpha Vantage news for {ticker}: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
