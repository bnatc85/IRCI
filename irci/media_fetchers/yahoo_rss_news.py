# irci/media_fetchers/yahoo_rss_news.py
"""
Yahoo Finance RSS News fetcher - fetches news via Yahoo Finance RSS feeds
"""
from __future__ import annotations
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime
import xml.etree.ElementTree as ET
import re


def yahoo_rss_news_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Fetch news articles for a ticker from Yahoo Finance RSS feed.

    Args:
        ticker: Stock symbol
        q_start: Quarter start date (pd.Timestamp)
        q_end: Quarter end date (pd.Timestamp)
        settings: Settings object (not used but kept for interface consistency)

    Returns:
        DataFrame with columns: published_at, url, domain, lang, headline, source
    """
    output_columns = ["published_at", "url", "domain", "lang", "headline", "source"]

    # Yahoo Finance RSS URL for ticker news
    rss_url = f"https://finance.yahoo.com/rss/headline?s={ticker.upper()}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(rss_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse RSS XML
        root = ET.fromstring(response.content)

        articles = []
        for item in root.findall(".//item"):
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")
            description = item.find("description")

            if title is None or link is None:
                continue

            headline = title.text or ""
            url = link.text or ""

            # Parse publication date (format: "Thu, 30 Jan 2026 14:30:00 +0000")
            published_at = None
            if pub_date is not None and pub_date.text:
                try:
                    # Handle various date formats
                    date_str = pub_date.text
                    # Try RFC 2822 format
                    from email.utils import parsedate_to_datetime
                    published_at = parsedate_to_datetime(date_str)
                    published_at = pd.Timestamp(published_at, tz='UTC')
                except Exception:
                    try:
                        published_at = pd.to_datetime(date_str, utc=True)
                    except Exception:
                        published_at = pd.Timestamp.now(tz='UTC')

            if published_at is None:
                published_at = pd.Timestamp.now(tz='UTC')

            # Extract domain from URL
            domain = urlparse(url).netloc.lower() if url else "finance.yahoo.com"

            articles.append({
                "published_at": published_at,
                "url": url,
                "domain": domain,
                "lang": "en",
                "headline": headline,
                "source": "Yahoo Finance"
            })

        if not articles:
            return pd.DataFrame(columns=output_columns)

        df = pd.DataFrame(articles)

        # Filter by date range
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]

        return df[output_columns]

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch Yahoo RSS news for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
    except ET.ParseError as e:
        print(f"Warning: Failed to parse Yahoo RSS XML for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
    except Exception as e:
        print(f"Warning: Error processing Yahoo RSS news for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
