# irci/media_fetchers/newsapi_fetcher.py
"""
NewsAPI.org media fetcher - comprehensive news coverage from 150,000+ sources
https://newsapi.org/
"""
from __future__ import annotations
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime


def newsapi_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Fetch news articles for a ticker from NewsAPI.org.

    NewsAPI.org provides comprehensive news coverage from 150,000+ sources worldwide.
    Free tier: 100 requests/day, 1 month of historical data
    https://newsapi.org/docs/endpoints/everything

    Args:
        ticker: Stock symbol
        q_start: Quarter start date (pd.Timestamp)
        q_end: Quarter end date (pd.Timestamp)
        settings: Settings object with newsapi_api_key

    Returns:
        DataFrame with columns: published_at, url, domain, lang, headline, source
    """
    # Check for NewsAPI key
    api_key = getattr(settings, "newsapi_api_key", None) or ""

    if not api_key:
        print(f"Warning: No NewsAPI.org API key configured for {ticker}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

    # NewsAPI.org endpoint
    url = "https://newsapi.org/v2/everything"

    # Format dates for API (YYYY-MM-DD format)
    from_date = q_start.strftime('%Y-%m-%d')
    to_date = q_end.strftime('%Y-%m-%d')

    # Company name mapping for better search results
    ticker_to_company = {
        'AAPL': 'Apple',
        'MSFT': 'Microsoft',
        'GOOGL': 'Google OR Alphabet',
        'GOOG': 'Google OR Alphabet',
        'AMZN': 'Amazon',
        'META': 'Meta OR Facebook',
        'TSLA': 'Tesla',
        'NVDA': 'NVIDIA',
        'AMD': 'AMD OR "Advanced Micro Devices"',
        'INTC': 'Intel',
        'QCOM': 'Qualcomm',
        'AVGO': 'Broadcom',
        'MU': 'Micron',
        'NFLX': 'Netflix',
        'DIS': 'Disney',
        'V': 'Visa',
        'MA': 'Mastercard',
        'JPM': 'JPMorgan OR "JP Morgan"',
        'BAC': '"Bank of America"',
        'WFC': '"Wells Fargo"',
        'C': 'Citigroup',
        'GS': '"Goldman Sachs"',
        'MS': '"Morgan Stanley"',
    }

    # Use company name if available, otherwise ticker
    query = ticker_to_company.get(ticker.upper(), ticker.upper())

    params = {
        "q": query,
        "from": from_date,
        "to": to_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 100,  # Max per request
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Check for API errors
        if data.get("status") != "ok":
            error_msg = data.get("message", "Unknown error")
            print(f"Warning: NewsAPI.org error for {ticker}: {error_msg}")
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        if "articles" not in data or not isinstance(data["articles"], list):
            print(f"Warning: No articles found for {ticker} from NewsAPI.org")
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        # Convert to DataFrame
        articles = data["articles"]
        if not articles:
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        df = pd.DataFrame(articles)

        # Normalize columns
        df["published_at"] = pd.to_datetime(df["publishedAt"], utc=True, errors="coerce")
        df["headline"] = df["title"]

        # Extract source name (NewsAPI returns source as dict)
        if "source" in df.columns:
            df["source"] = df["source"].apply(lambda s: s.get("name", "") if isinstance(s, dict) else str(s))
        else:
            df["source"] = ""

        # Extract domain from URL
        if "url" in df.columns:
            df["domain"] = df["url"].apply(lambda u: urlparse(str(u)).netloc.lower() if pd.notna(u) else "")
        else:
            df["url"] = ""
            df["domain"] = ""

        df["lang"] = "en"  # We filtered for English

        # Filter by date range (extra safety check)
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]

        # Select required columns
        output_columns = ["published_at", "url", "domain", "lang", "headline", "source"]
        for col in output_columns:
            if col not in df.columns:
                df[col] = ""

        result = df[output_columns].copy()

        # Add ticker column for trust analysis
        result["ticker"] = ticker.upper()

        print(f"✓ Fetched {len(result)} articles from NewsAPI.org for {ticker}")
        return result

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch news for {ticker} from NewsAPI.org: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
    except Exception as e:
        print(f"Warning: Error processing NewsAPI.org news for {ticker}: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
