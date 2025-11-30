# irci/media_fetchers/fmp_news.py
"""
FMP Stock News API media fetcher - automatically fetches news for any public ticker
"""
from __future__ import annotations
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime


def fmp_news_media_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Fetch news articles for a ticker from FMP Stock News API.

    Args:
        ticker: Stock symbol
        q_start: Quarter start date (pd.Timestamp)
        q_end: Quarter end date (pd.Timestamp)
        settings: Settings object with fmp_api_key

    Returns:
        DataFrame with columns: published_at, url, domain, lang, headline, source
    """
    api_key = getattr(settings, "fmp_api_key", "")
    if not api_key:
        # Return empty DataFrame if no API key
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

    # Format dates for FMP API (YYYY-MM-DD)
    from_date = q_start.strftime("%Y-%m-%d")
    to_date = q_end.strftime("%Y-%m-%d")

    # FMP Stock News API endpoint (new stable endpoint)
    url = f"https://financialmodelingprep.com/stable/news/stock"
    params = {
        "symbols": ticker.upper(),
        "apikey": api_key
    }

    try:
        # Fetch multiple pages to get sufficient news coverage
        all_articles = []
        max_pages = 3  # Reduced from 10 - fetch up to 3 pages to avoid timeouts

        for page in range(max_pages):
            params_with_page = params.copy()
            params_with_page["page"] = page

            response = requests.get(url, params=params_with_page, timeout=10)  # Reduced from 30s
            response.raise_for_status()
            data = response.json()

            if not data or not isinstance(data, list):
                break  # No more data

            all_articles.extend(data)

            # Stop if we got fewer than 20 articles (last page)
            if len(data) < 20:
                break

        if not all_articles:
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        # Convert to DataFrame
        df = pd.DataFrame(all_articles)

        # Normalize columns to match expected format
        column_mapping = {
            "publishedDate": "published_at",
            "title": "headline",
            "site": "source"
        }
        df = df.rename(columns=column_mapping)

        # Ensure required columns exist
        if "published_at" not in df.columns or "url" not in df.columns:
            return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])

        # Parse published_at as UTC datetime
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")

        # Filter by date range (in case API returns extra)
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]

        # Extract domain from site field or URL
        if "domain" not in df.columns:
            # FMP's new API provides "site" field directly (e.g., "fool.com")
            if "source" in df.columns and df["source"].notna().any():
                df["domain"] = df["source"].str.lower()
            else:
                df["domain"] = df["url"].apply(lambda u: urlparse(str(u)).netloc.lower() if pd.notna(u) else "")

        # Default language to English
        if "lang" not in df.columns:
            df["lang"] = "en"

        # Add headline if missing
        if "headline" not in df.columns:
            df["headline"] = df.get("title", "")

        # Add source if missing (use site field from FMP)
        if "source" not in df.columns:
            df["source"] = df.get("site", df.get("domain", ""))

        # Select and order columns
        output_columns = ["published_at", "url", "domain", "lang", "headline", "source"]
        df = df[[col for col in output_columns if col in df.columns]]

        # Ensure all expected columns exist
        for col in output_columns:
            if col not in df.columns:
                df[col] = ""

        return df[output_columns]

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch news for {ticker} from FMP API: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
    except Exception as e:
        print(f"Warning: Error processing FMP news for {ticker}: {e}")
        return pd.DataFrame(columns=["published_at", "url", "domain", "lang", "headline", "source"])
