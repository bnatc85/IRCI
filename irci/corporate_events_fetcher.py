"""
Corporate Events Fetcher Module

Fetches corporate events from multiple sources:
- FMP API (if premium subscription available)
- Yahoo Finance (free fallback for earnings, dividends)
- SEC EDGAR (for 8-K filings)

Event types:
- Earnings calendar (earnings calls)
- Dividends (historical and calendar)
- Stock splits
- Press releases (strategic announcements, investor days, etc.)
- SEC 8-K filings (CEO/CFO changes, strategic announcements)

These events are used to populate the Event Timeline automatically.
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from .config import Settings
from .sec_event_parser import parse_8k_filing, classify_leadership_change, classify_investor_event

# Try to import yfinance for fallback
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def fetch_earnings_calendar(
    ticker: str,
    start_date: str,
    end_date: str,
    api_key: str
) -> pd.DataFrame:
    """
    Fetch earnings calendar events for a ticker.

    Returns DataFrame with columns:
    - date: earnings date
    - event_type: 'earnings_call'
    - description: earnings description
    - ticker
    """
    events = []

    try:
        # FMP earnings calendar endpoint
        url = f"https://financialmodelingprep.com/api/v3/historical/earning_calendar/{ticker}?apikey={api_key}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()

            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            for item in data:
                event_date = pd.to_datetime(item.get('date'))

                # Filter to date range
                if start_dt <= event_date <= end_dt:
                    eps_actual = item.get('eps')
                    eps_estimate = item.get('epsEstimated')
                    revenue = item.get('revenue')
                    revenue_estimate = item.get('revenueEstimated')

                    # Calculate beat/miss
                    beat_miss = ""
                    if eps_actual is not None and eps_estimate is not None:
                        diff = eps_actual - eps_estimate
                        if diff > 0:
                            beat_miss = f"Beat by ${diff:.2f}"
                        elif diff < 0:
                            beat_miss = f"Missed by ${abs(diff):.2f}"
                        else:
                            beat_miss = "Met estimates"

                    description = f"Q{item.get('quarter', '?')} {item.get('year', '')} Earnings"
                    if beat_miss:
                        description += f" - {beat_miss}"

                    events.append({
                        'date': event_date,
                        'event_type': 'earnings_call',
                        'description': description,
                        'ticker': ticker,
                        'eps_actual': eps_actual,
                        'eps_estimate': eps_estimate,
                        'revenue': revenue,
                        'revenue_estimate': revenue_estimate
                    })
    except Exception as e:
        print(f"Warning: Failed to fetch earnings calendar from FMP for {ticker}: {e}")

    # Fallback to Yahoo Finance if FMP returned nothing
    if not events and YFINANCE_AVAILABLE:
        try:
            stock = yf.Ticker(ticker)
            # Get earnings dates from yfinance
            earnings_dates = stock.get_earnings_dates(limit=20)
            if earnings_dates is not None and not earnings_dates.empty:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)

                for idx, row in earnings_dates.iterrows():
                    event_date = pd.to_datetime(idx)
                    # Make timezone-naive for comparison
                    if event_date.tzinfo is not None:
                        event_date = event_date.tz_localize(None)

                    if start_dt <= event_date <= end_dt:
                        eps_actual = row.get('Reported EPS')
                        eps_estimate = row.get('EPS Estimate')

                        # Calculate beat/miss
                        beat_miss = ""
                        if pd.notna(eps_actual) and pd.notna(eps_estimate):
                            diff = eps_actual - eps_estimate
                            if diff > 0:
                                beat_miss = f"Beat by ${diff:.2f}"
                            elif diff < 0:
                                beat_miss = f"Missed by ${abs(diff):.2f}"
                            else:
                                beat_miss = "Met estimates"

                        # Try to determine quarter from date
                        quarter = (event_date.month - 1) // 3 + 1
                        year = event_date.year

                        description = f"Q{quarter} {year} Earnings"
                        if beat_miss:
                            description += f" - {beat_miss}"

                        events.append({
                            'date': event_date,
                            'event_type': 'earnings_call',
                            'description': description,
                            'ticker': ticker,
                            'eps_actual': eps_actual if pd.notna(eps_actual) else None,
                            'eps_estimate': eps_estimate if pd.notna(eps_estimate) else None,
                            'revenue': None,
                            'revenue_estimate': None,
                            'source': 'yahoo_finance'
                        })
                if events:
                    print(f"    - Found {len(events)} earnings events (Yahoo Finance fallback)")
        except Exception as e:
            print(f"Warning: Yahoo Finance earnings fallback failed for {ticker}: {e}")

    return pd.DataFrame(events) if events else pd.DataFrame()


def fetch_dividend_events(
    ticker: str,
    start_date: str,
    end_date: str,
    api_key: str
) -> pd.DataFrame:
    """
    Fetch dividend events for a ticker.

    Returns DataFrame with columns:
    - date: dividend date (declaration or ex-date)
    - event_type: 'dividend_announcement'
    - description: dividend details
    - ticker
    - dividend_change_pct: percentage change from previous dividend
    """
    events = []

    try:
        # FMP historical dividend endpoint
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/{ticker}?apikey={api_key}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            historical = data.get('historical', [])

            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            # Sort by date to calculate changes
            historical_sorted = sorted(historical, key=lambda x: x.get('date', ''))

            prev_dividend = None
            for item in historical_sorted:
                event_date = pd.to_datetime(item.get('date'))

                # Filter to date range
                if start_dt <= event_date <= end_dt:
                    dividend_amount = item.get('dividend', item.get('adjDividend', 0))

                    # Calculate change from previous dividend
                    dividend_change_pct = 0
                    if prev_dividend and prev_dividend > 0:
                        dividend_change_pct = ((dividend_amount - prev_dividend) / prev_dividend) * 100

                    # Determine event description
                    if dividend_change_pct > 5:
                        description = f"Dividend Increase: ${dividend_amount:.4f} (+{dividend_change_pct:.1f}%)"
                    elif dividend_change_pct < -5:
                        description = f"Dividend Cut: ${dividend_amount:.4f} ({dividend_change_pct:.1f}%)"
                    else:
                        description = f"Dividend: ${dividend_amount:.4f}"

                    events.append({
                        'date': event_date,
                        'event_type': 'dividend_announcement',
                        'description': description,
                        'ticker': ticker,
                        'dividend_amount': dividend_amount,
                        'dividend_change_pct': dividend_change_pct
                    })

                if item.get('dividend') or item.get('adjDividend'):
                    prev_dividend = item.get('dividend', item.get('adjDividend'))

    except Exception as e:
        print(f"Warning: Failed to fetch dividend events from FMP for {ticker}: {e}")

    # Fallback to Yahoo Finance if FMP returned nothing
    if not events and YFINANCE_AVAILABLE:
        try:
            stock = yf.Ticker(ticker)
            dividends = stock.dividends
            if dividends is not None and len(dividends) > 0:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)

                # Make timezone-naive for comparison
                div_index = dividends.index
                if div_index.tz is not None:
                    div_index = div_index.tz_localize(None)

                # Convert index to datetime and filter
                dividends_filtered = dividends[
                    (div_index >= start_dt) & (div_index <= end_dt)
                ]

                prev_dividend = None
                for date_idx, dividend_amount in dividends_filtered.items():
                    event_date = pd.to_datetime(date_idx)
                    if event_date.tzinfo is not None:
                        event_date = event_date.tz_localize(None)

                    # Calculate change from previous
                    dividend_change_pct = 0
                    if prev_dividend and prev_dividend > 0:
                        dividend_change_pct = ((dividend_amount - prev_dividend) / prev_dividend) * 100

                    if dividend_change_pct > 5:
                        description = f"Dividend Increase: ${dividend_amount:.4f} (+{dividend_change_pct:.1f}%)"
                    elif dividend_change_pct < -5:
                        description = f"Dividend Cut: ${dividend_amount:.4f} ({dividend_change_pct:.1f}%)"
                    else:
                        description = f"Dividend: ${dividend_amount:.4f}"

                    events.append({
                        'date': event_date,
                        'event_type': 'dividend_announcement',
                        'description': description,
                        'ticker': ticker,
                        'dividend_amount': dividend_amount,
                        'dividend_change_pct': dividend_change_pct,
                        'source': 'yahoo_finance'
                    })
                    prev_dividend = dividend_amount

                if events:
                    print(f"    - Found {len(events)} dividend events (Yahoo Finance fallback)")
        except Exception as e:
            print(f"Warning: Yahoo Finance dividend fallback failed for {ticker}: {e}")

    return pd.DataFrame(events) if events else pd.DataFrame()


def fetch_press_releases(
    ticker: str,
    start_date: str,
    end_date: str,
    api_key: str,
    limit: int = 100
) -> pd.DataFrame:
    """
    Fetch press releases for a ticker and classify them.

    Returns DataFrame with columns:
    - date: press release date
    - event_type: classified event type (investor_day, strategic_announcement, etc.)
    - description: press release title
    - ticker
    """
    events = []

    try:
        # FMP press releases endpoint
        url = f"https://financialmodelingprep.com/api/v3/press-releases/{ticker}?limit={limit}&apikey={api_key}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()

            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            for item in data:
                event_date = pd.to_datetime(item.get('date'))

                # Filter to date range
                if start_dt <= event_date <= end_dt:
                    title = item.get('title', '')
                    text = item.get('text', '')
                    title_lower = title.lower()

                    # Classify the press release
                    event_type = 'strategic_announcement'  # Default

                    # Investor Day / Analyst Day detection
                    if any(kw in title_lower for kw in ['investor day', 'capital markets day', 'analyst day']):
                        event_type = 'investor_day'
                    # Buyback detection
                    elif any(kw in title_lower for kw in ['buyback', 'repurchase', 'share repurchase']):
                        event_type = 'buyback_announcement'
                    # CEO/CFO change detection
                    elif any(kw in title_lower for kw in ['ceo', 'chief executive', 'cfo', 'chief financial']):
                        if any(kw in title_lower for kw in ['appoint', 'named', 'announces', 'promote']):
                            if 'cfo' in title_lower or 'chief financial' in title_lower:
                                event_type = 'cfo_change'
                            else:
                                event_type = 'ceo_change'
                    # Earnings call detection (supplement to earnings calendar)
                    elif any(kw in title_lower for kw in ['earnings', 'quarterly results', 'financial results']):
                        event_type = 'earnings_call'
                    # Conference presentation detection
                    elif any(kw in title_lower for kw in ['conference', 'presentation', 'summit']):
                        event_type = 'conference_presentation'

                    events.append({
                        'date': event_date,
                        'event_type': event_type,
                        'description': title[:200],  # Truncate long titles
                        'ticker': ticker,
                        'source': 'press_release'
                    })

    except Exception as e:
        print(f"Warning: Failed to fetch press releases for {ticker}: {e}")

    return pd.DataFrame(events) if events else pd.DataFrame()


def fetch_sec_8k_events(
    ticker: str,
    start_date: str,
    end_date: str,
    api_key: str
) -> pd.DataFrame:
    """
    Fetch SEC 8-K filings and parse them for corporate events.

    Returns DataFrame with columns:
    - date: filing date
    - event_type: classified event type (ceo_change, cfo_change, investor_day, etc.)
    - description: event description
    - ticker
    - event_metadata: dict with additional event details
    """
    events = []

    try:
        # FMP SEC filings endpoint
        url = f"https://financialmodelingprep.com/api/v3/sec_filings/{ticker}?type=8-K&apikey={api_key}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()

            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            for item in data:
                filing_date = pd.to_datetime(item.get('fillingDate', item.get('filingDate')))

                # Filter to date range
                if start_dt <= filing_date <= end_dt:
                    # Get filing text if available, otherwise use description
                    filing_text = item.get('description', '') or item.get('text', '')
                    filing_url = item.get('finalLink', item.get('link', ''))

                    # Parse the 8-K filing
                    parsed_events = parse_8k_filing(ticker, filing_date.strftime('%Y-%m-%d'), filing_text, filing_url)

                    for event in parsed_events:
                        events.append({
                            'date': filing_date,
                            'event_type': event['event_type'],
                            'description': event['description'],
                            'ticker': ticker,
                            'event_metadata': event.get('event_metadata', {}),
                            'filing_url': filing_url,
                            'source': 'sec_8k'
                        })

    except Exception as e:
        print(f"Warning: Failed to fetch SEC 8-K filings for {ticker}: {e}")

    return pd.DataFrame(events) if events else pd.DataFrame()


def fetch_all_corporate_events(
    ticker: str,
    start_date: str,
    end_date: str,
    settings: Optional[Settings] = None
) -> pd.DataFrame:
    """
    Fetch all corporate events from multiple sources.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        settings: Settings object with API keys

    Returns:
        Combined DataFrame with all corporate events
    """
    if settings is None:
        settings = Settings()

    api_key = settings.fmp_api_key
    if not api_key:
        print("Warning: FMP_API_KEY not set, cannot fetch corporate events")
        return pd.DataFrame()

    all_events = []

    # Fetch from each source
    print(f"  Fetching corporate events for {ticker}...")

    # 1. Earnings calendar
    earnings_df = fetch_earnings_calendar(ticker, start_date, end_date, api_key)
    if not earnings_df.empty:
        all_events.append(earnings_df)
        print(f"    - Found {len(earnings_df)} earnings events")

    # 2. Dividends
    dividend_df = fetch_dividend_events(ticker, start_date, end_date, api_key)
    if not dividend_df.empty:
        all_events.append(dividend_df)
        print(f"    - Found {len(dividend_df)} dividend events")

    # 3. Press releases (investor days, buybacks, strategic announcements)
    press_df = fetch_press_releases(ticker, start_date, end_date, api_key)
    if not press_df.empty:
        all_events.append(press_df)
        print(f"    - Found {len(press_df)} press releases")

    # 4. SEC 8-K filings (CEO/CFO changes, etc.)
    sec_df = fetch_sec_8k_events(ticker, start_date, end_date, api_key)
    if not sec_df.empty:
        all_events.append(sec_df)
        print(f"    - Found {len(sec_df)} SEC 8-K events")

    if not all_events:
        return pd.DataFrame()

    # Combine all events
    combined_df = pd.concat(all_events, ignore_index=True)

    # Remove duplicates (same date + event_type + ticker)
    combined_df = combined_df.drop_duplicates(subset=['date', 'event_type', 'ticker'], keep='first')

    # Sort by date
    combined_df = combined_df.sort_values('date')

    return combined_df


def fetch_corporate_events_for_peer_group(
    tickers: List[str],
    start_date: str,
    end_date: str,
    settings: Optional[Settings] = None
) -> pd.DataFrame:
    """
    Fetch corporate events for multiple tickers.

    Args:
        tickers: List of stock tickers
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        settings: Settings object with API keys

    Returns:
        Combined DataFrame with all corporate events for all tickers
    """
    all_events = []

    for ticker in tickers:
        ticker_events = fetch_all_corporate_events(ticker, start_date, end_date, settings)
        if not ticker_events.empty:
            all_events.append(ticker_events)

    if not all_events:
        return pd.DataFrame()

    combined_df = pd.concat(all_events, ignore_index=True)
    combined_df = combined_df.sort_values('date')

    return combined_df
