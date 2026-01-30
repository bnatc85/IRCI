# irci/media_fetchers/seeking_alpha_rss.py
"""
Seeking Alpha RSS fetcher - fetches news and analysis from Seeking Alpha RSS feeds
"""
from __future__ import annotations
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime
import xml.etree.ElementTree as ET


def seeking_alpha_rss_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Fetch news articles for a ticker from Seeking Alpha RSS feed.

    Args:
        ticker: Stock symbol
        q_start: Quarter start date (pd.Timestamp)
        q_end: Quarter end date (pd.Timestamp)
        settings: Settings object (not used but kept for interface consistency)

    Returns:
        DataFrame with columns: published_at, url, domain, lang, headline, source
    """
    output_columns = ["published_at", "url", "domain", "lang", "headline", "source"]

    # Seeking Alpha RSS URL for ticker
    rss_url = f"https://seekingalpha.com/api/sa/combined/{ticker.upper()}.xml"

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

            if title is None or link is None:
                continue

            headline = title.text or ""
            url = link.text or ""

            # Parse publication date
            published_at = None
            if pub_date is not None and pub_date.text:
                try:
                    from email.utils import parsedate_to_datetime
                    published_at = parsedate_to_datetime(pub_date.text)
                    published_at = pd.Timestamp(published_at, tz='UTC')
                except Exception:
                    try:
                        published_at = pd.to_datetime(pub_date.text, utc=True)
                    except Exception:
                        published_at = pd.Timestamp.now(tz='UTC')

            if published_at is None:
                published_at = pd.Timestamp.now(tz='UTC')

            articles.append({
                "published_at": published_at,
                "url": url,
                "domain": "seekingalpha.com",
                "lang": "en",
                "headline": headline,
                "source": "Seeking Alpha"
            })

        if not articles:
            return pd.DataFrame(columns=output_columns)

        df = pd.DataFrame(articles)

        # Filter by date range
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]

        return df[output_columns]

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch Seeking Alpha RSS for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
    except ET.ParseError as e:
        print(f"Warning: Failed to parse Seeking Alpha RSS XML for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
    except Exception as e:
        print(f"Warning: Error processing Seeking Alpha RSS for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
