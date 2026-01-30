# irci/media_fetchers/google_news_rss.py
"""
Google News RSS fetcher - fetches news via Google News RSS feeds
Provides broader coverage than ticker-specific APIs
"""
from __future__ import annotations
import pandas as pd
import requests
from urllib.parse import urlparse, quote
from datetime import datetime
import xml.etree.ElementTree as ET
import re


# Map of ticker to company names for better search results
# This enables searching by company name which finds more articles than ticker-only searches
TICKER_TO_COMPANY = {
    # Private Equity / Asset Management
    "BX": "Blackstone",
    "KKR": "KKR",
    "APO": "Apollo Global Management",
    "CG": "Carlyle Group",
    "ARES": "Ares Management",
    "BLK": "BlackRock",
    "BAM": "Brookfield Asset Management",
    "OWL": "Blue Owl Capital",
    "TPG": "TPG Inc",
    # Tech Giants
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google Alphabet",
    "GOOG": "Google Alphabet",
    "AMZN": "Amazon",
    "META": "Meta Facebook",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "NFLX": "Netflix",
    "CRM": "Salesforce",
    "ORCL": "Oracle",
    "ADBE": "Adobe",
    "INTC": "Intel",
    "AMD": "AMD",
    # Financial Services
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "WFC": "Wells Fargo",
    "GS": "Goldman Sachs",
    "MS": "Morgan Stanley",
    "C": "Citigroup",
    "SCHW": "Charles Schwab",
    "BRK.A": "Berkshire Hathaway",
    "BRK.B": "Berkshire Hathaway",
    # Payments
    "V": "Visa",
    "MA": "Mastercard",
    "PYPL": "PayPal",
    "SQ": "Block Square",
    # Healthcare
    "UNH": "UnitedHealth",
    "JNJ": "Johnson Johnson",
    "PFE": "Pfizer",
    "ABBV": "AbbVie",
    "LLY": "Eli Lilly",
    "MRK": "Merck",
    "TMO": "Thermo Fisher",
    "ABT": "Abbott",
    # Energy
    "XOM": "ExxonMobil",
    "CVX": "Chevron",
    "COP": "ConocoPhillips",
    "SLB": "Schlumberger",
    # Consumer
    "WMT": "Walmart",
    "COST": "Costco",
    "HD": "Home Depot",
    "NKE": "Nike",
    "SBUX": "Starbucks",
    "MCD": "McDonald's",
    "DIS": "Disney",
    "PG": "Procter Gamble",
    "KO": "Coca-Cola",
    "PEP": "PepsiCo",
    # Industrial
    "BA": "Boeing",
    "CAT": "Caterpillar",
    "GE": "General Electric",
    "HON": "Honeywell",
    "UPS": "UPS",
    "FDX": "FedEx",
    # Telecom
    "T": "AT&T",
    "VZ": "Verizon",
    "TMUS": "T-Mobile",
}


def get_company_name(ticker: str) -> str:
    """Get company name for a ticker, or return ticker if not found."""
    return TICKER_TO_COMPANY.get(ticker.upper(), ticker.upper())


def google_news_rss_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Fetch news articles for a ticker/company from Google News RSS feed.

    Args:
        ticker: Stock symbol
        q_start: Quarter start date (pd.Timestamp)
        q_end: Quarter end date (pd.Timestamp)
        settings: Settings object (not used but kept for interface consistency)

    Returns:
        DataFrame with columns: published_at, url, domain, lang, headline, source
    """
    output_columns = ["published_at", "url", "domain", "lang", "headline", "source"]

    # Get company name for better search
    company_name = get_company_name(ticker)

    # URL encode the search query
    search_query = quote(f"{company_name} stock")

    # Google News RSS URL
    rss_url = f"https://news.google.com/rss/search?q={search_query}&hl=en-US&gl=US&ceid=US:en"

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
            source_elem = item.find("source")

            if title is None or link is None:
                continue

            headline = title.text or ""
            url = link.text or ""

            # Google News wraps URLs - extract actual URL if possible
            # The actual article URL is in the link text

            # Get source from source element or parse from headline
            source = ""
            if source_elem is not None and source_elem.text:
                source = source_elem.text
            else:
                # Google News format: "Headline - Source"
                if " - " in headline:
                    parts = headline.rsplit(" - ", 1)
                    if len(parts) == 2:
                        source = parts[1]
                        headline = parts[0]

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

            # Extract domain from URL
            domain = urlparse(url).netloc.lower() if url else "news.google.com"
            # Clean up Google News redirect domain
            if "news.google.com" in domain:
                domain = source.lower().replace(" ", "") + ".com" if source else "news.google.com"

            articles.append({
                "published_at": published_at,
                "url": url,
                "domain": domain,
                "lang": "en",
                "headline": headline,
                "source": source or "Google News"
            })

        if not articles:
            return pd.DataFrame(columns=output_columns)

        df = pd.DataFrame(articles)

        # Filter by date range
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]

        # Remove duplicates by headline
        df = df.drop_duplicates(subset=["headline"], keep="first")

        return df[output_columns]

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch Google News RSS for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
    except ET.ParseError as e:
        print(f"Warning: Failed to parse Google News RSS XML for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
    except Exception as e:
        print(f"Warning: Error processing Google News RSS for {ticker}: {e}")
        return pd.DataFrame(columns=output_columns)
