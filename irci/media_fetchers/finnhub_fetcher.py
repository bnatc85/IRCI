# irci/media_fetchers/finnhub_fetcher.py
"""
Finnhub.io media fetcher - comprehensive financial news and market data
https://finnhub.io/
"""
from __future__ import annotations
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime


def finnhub_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Fetch news articles for a ticker from Finnhub.io.

    Finnhub.io provides comprehensive financial news, market data, and analysis.
    Free tier: 60 API calls/minute, company news endpoint included
    https://finnhub.io/docs/api/company-news

    Args:
        ticker: Stock symbol
        q_start: Quarter start date (pd.Timestamp)
        q_end: Quarter end date (pd.Timestamp)
        settings: Settings object with finnhub_api_key

    Returns:
        DataFrame with columns: published_at, url, domain, lang, headline, source
    """
    # Check for Finnhub key
    api_key = getattr(settings, "finnhub_api_key", None) or ""

    if not api_key:
        print(f"Warning: No Finnhub.io API key configured for {ticker}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

    # Finnhub.io company news endpoint
    url = "https://finnhub.io/api/v1/company-news"

    # Format dates for API (YYYY-MM-DD format)
    from_date = q_start.strftime('%Y-%m-%d')
    to_date = q_end.strftime('%Y-%m-%d')

    params = {
        "symbol": ticker.upper(),
        "from": from_date,
        "to": to_date,
        "token": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Finnhub returns a list of articles directly
        if not isinstance(data, list):
            print(f"Warning: Unexpected Finnhub.io response format for {ticker}")
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        if not data:
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Normalize columns to match our standard format
        # Finnhub fields: category, datetime, headline, id, image, related, source, summary, url

        # Convert datetime (Unix timestamp) to pandas timestamp
        if 'datetime' in df.columns:
            df['published_at'] = pd.to_datetime(df['datetime'], unit='s', utc=True)
        else:
            df['published_at'] = pd.NaT

        # Rename headline field
        if 'headline' in df.columns:
            df['headline'] = df['headline']
        else:
            df['headline'] = ""

        # Extract source - Finnhub provides source name directly
        if 'source' in df.columns:
            df['source'] = df['source'].fillna("Finnhub")
        else:
            df['source'] = "Finnhub"

        # For domain, use the source name converted to domain format
        # Finnhub URLs are proxied (finnhub.io/api/news?id=...), so we derive domain from source
        # Common mappings: "SeekingAlpha" -> "seekingalpha.com", "Yahoo" -> "yahoo.com", etc.
        source_to_domain = {
            'seekingalpha': 'seekingalpha.com',
            'yahoo': 'yahoo.com',
            'reuters': 'reuters.com',
            'bloomberg': 'bloomberg.com',
            'cnbc': 'cnbc.com',
            'marketwatch': 'marketwatch.com',
            'benzinga': 'benzinga.com',
            'thestreet': 'thestreet.com',
            'investorplace': 'investorplace.com',
            'fool': 'fool.com',
            'motleyfool': 'fool.com',
            'barrons': 'barrons.com',
            'wsj': 'wsj.com',
            'ft': 'ft.com',
            'forbes': 'forbes.com',
            'businessinsider': 'businessinsider.com',
            'techcrunch': 'techcrunch.com',
            'zacks': 'zacks.com',
            'investopedia': 'investopedia.com',
            'thefly': 'thefly.com',
            'accesswire': 'accesswire.com',
            'prnewswire': 'prnewswire.com',
            'businesswire': 'businesswire.com',
            'globenewswire': 'globenewswire.com',
        }

        def source_to_domain_name(source):
            if pd.isna(source) or not source:
                return ""
            s = str(source).lower().replace(" ", "").replace(".", "")
            # Check mapping first
            if s in source_to_domain:
                return source_to_domain[s]
            # Otherwise, try to create domain from source name
            return f"{s}.com"

        df['domain'] = df['source'].apply(source_to_domain_name)

        # Finnhub news is primarily English
        df['lang'] = "en"

        # Filter by date range (extra safety check)
        df = df[(df['published_at'] >= q_start) & (df['published_at'] <= q_end)]

        # Select required columns
        output_columns = ["published_at", "url", "domain", "lang", "headline", "source"]
        for col in output_columns:
            if col not in df.columns:
                df[col] = ""

        result = df[output_columns].copy()

        # Add ticker column for trust analysis
        result['ticker'] = ticker.upper()

        print(f"✓ Fetched {len(result)} articles from Finnhub.io for {ticker}")
        return result

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch news for {ticker} from Finnhub.io: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
    except Exception as e:
        print(f"Warning: Error processing Finnhub.io news for {ticker}: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
