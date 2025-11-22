# irci/media_fetchers/worldnews_api.py
"""
World News API media fetcher - enterprise news API with broad coverage
https://worldnewsapi.com/
"""
from __future__ import annotations
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime


def worldnews_api_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Fetch news articles for a ticker from World News API.

    World News API provides comprehensive news coverage from thousands of sources.
    https://worldnewsapi.com/docs/#Search-News

    Args:
        ticker: Stock symbol
        q_start: Quarter start date (pd.Timestamp)
        q_end: Quarter end date (pd.Timestamp)
        settings: Settings object with worldnews_api_key

    Returns:
        DataFrame with columns: published_at, url, domain, lang, headline, source
    """
    # Check for World News API key
    api_key = getattr(settings, "worldnews_api_key", None) or ""

    if not api_key:
        print(f"Warning: No World News API key configured for {ticker}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

    # World News API endpoint
    url = "https://api.worldnewsapi.com/search-news"

    # Format dates for API (YYYY-MM-DD format)
    earliest_publish_date = q_start.strftime('%Y-%m-%d')
    latest_publish_date = q_end.strftime('%Y-%m-%d')

    # Search query - World News API uses text search
    # For better results, search by company name when possible
    # Common ticker to company name mappings
    ticker_to_company = {
        'AAPL': 'Apple',
        'MSFT': 'Microsoft',
        'GOOGL': 'Google',
        'GOOG': 'Google',
        'AMZN': 'Amazon',
        'META': 'Meta',
        'TSLA': 'Tesla',
        'NVDA': 'NVIDIA',
        'JPM': 'JPMorgan',
        'V': 'Visa',
        'WMT': 'Walmart',
        'JNJ': 'Johnson',
        'PG': 'Procter',
        'MA': 'Mastercard',
        'UNH': 'UnitedHealth',
        'HD': 'Home Depot',
        'BAC': 'Bank of America',
        'XOM': 'Exxon',
        'CVX': 'Chevron',
        'ABBV': 'AbbVie',
        'PFE': 'Pfizer',
        'KO': 'Coca-Cola',
        'PEP': 'Pepsi',
        'COST': 'Costco',
        'AVGO': 'Broadcom',
        'TMO': 'Thermo Fisher',
        'MRK': 'Merck',
        'ABT': 'Abbott',
        'CSCO': 'Cisco',
        'ACN': 'Accenture',
        'DHR': 'Danaher',
        'VZ': 'Verizon',
        'ADBE': 'Adobe',
        'CRM': 'Salesforce',
        'NKE': 'Nike',
        'NFLX': 'Netflix',
        'CMCSA': 'Comcast',
        'WFC': 'Wells Fargo',
        'DIS': 'Disney',
        'AMD': 'AMD',
        'INTC': 'Intel',
        'QCOM': 'Qualcomm',
        'TXN': 'Texas Instruments',
        'PM': 'Philip Morris',
        'UNP': 'Union Pacific',
        'HON': 'Honeywell',
        'UPS': 'UPS',
        'LOW': 'Lowes',
        'BA': 'Boeing',
        'CAT': 'Caterpillar',
        'GE': 'General Electric',
        'SBUX': 'Starbucks',
        'GILD': 'Gilead',
        'MDLZ': 'Mondelez',
        'BMY': 'Bristol-Myers',
        'AXP': 'American Express',
        'GS': 'Goldman Sachs',
        'BLK': 'BlackRock',
        'ISRG': 'Intuitive Surgical',
        'LMT': 'Lockheed Martin',
        'SPGI': 'S&P Global',
        'MMM': '3M',
        'CVS': 'CVS',
        'CI': 'Cigna',
        'SCHW': 'Charles Schwab',
        'CB': 'Chubb',
        'ADP': 'ADP',
        'MO': 'Altria',
        'USB': 'U.S. Bancorp',
        'TGT': 'Target',
        'SO': 'Southern Company',
        'DUK': 'Duke Energy',
    }

    # Use company name if available, otherwise use ticker
    search_query = ticker_to_company.get(ticker.upper(), ticker.upper())

    params = {
        "text": search_query,
        "earliest-publish-date": earliest_publish_date,
        "latest-publish-date": latest_publish_date,
        "language": "en",
        "sort": "publish-time",
        "sort-direction": "DESC",
        "number": 100,  # Max results per request
        "api-key": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "news" not in data or not isinstance(data["news"], list):
            print(f"Warning: No news found for {ticker} from World News API")
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        # Convert to DataFrame
        df = pd.DataFrame(data["news"])

        if df.empty:
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        # Normalize columns to match expected format
        # World News API returns: title, text, url, publish_date, author, language, source_country
        df["published_at"] = pd.to_datetime(df["publish_date"], utc=True, errors="coerce")
        df["headline"] = df["title"]

        # Extract source from URL or use author
        if "url" in df.columns:
            df["domain"] = df["url"].apply(lambda u: urlparse(str(u)).netloc.lower() if pd.notna(u) else "")
            df["source"] = df["domain"].apply(lambda d: d.replace("www.", "") if d else "Unknown")
        else:
            df["url"] = ""
            df["domain"] = ""
            df["source"] = "Unknown"

        # Use language from API
        if "language" in df.columns:
            df["lang"] = df["language"]
        else:
            df["lang"] = "en"

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
        print(f"Warning: Failed to fetch news for {ticker} from World News API: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
    except Exception as e:
        print(f"Warning: Error processing World News API data for {ticker}: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
