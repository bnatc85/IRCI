"""
SEC Event Parser Module

Parses SEC 8-K filings to extract corporate events:
- Item 5.02: Departure/appointment of directors or officers (CEO/CFO changes)
- Item 7.01: Regulation FD Disclosure (investor days, conference presentations)
- Item 8.01: Other Events (strategic announcements)
- Item 2.03: Creation of direct financial obligation (debt issuance)
- Item 1.01: Entry into material definitive agreement (M&A)

Based on SEC 8-K Item taxonomy:
https://www.sec.gov/files/form8-k.pdf
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


# 8-K Item codes mapped to event types
ITEM_TO_EVENT_TYPE = {
    # Leadership changes
    '5.02': 'leadership_change',  # Departure/appointment of directors or officers
    '5.03': 'leadership_change',  # Amendments to articles of incorporation/bylaws (sometimes officer-related)

    # Investor Relations events
    '7.01': 'investor_event',     # Regulation FD Disclosure (presentations, investor days)
    '9.01': 'investor_event',     # Financial statements and exhibits

    # Strategic/Corporate actions
    '1.01': 'strategic_announcement',  # Material definitive agreement
    '1.02': 'strategic_announcement',  # Termination of material definitive agreement
    '2.01': 'strategic_announcement',  # Completion of acquisition/disposition
    '2.03': 'debt_issuance',           # Creation of direct financial obligation
    '2.04': 'debt_issuance',           # Triggering events that accelerate obligations
    '8.01': 'strategic_announcement',  # Other Events

    # Earnings/Financial
    '2.02': 'earnings_release',   # Results of operations and financial condition

    # Dividends/Buybacks
    '5.05': 'compensation_change',  # Amendments to registrant's code of ethics
}

# Keywords to identify specific event subtypes
CEO_KEYWORDS = ['chief executive officer', 'ceo', 'president and ceo', 'acting ceo']
CFO_KEYWORDS = ['chief financial officer', 'cfo', 'treasurer', 'acting cfo']
DEPARTURE_KEYWORDS = ['resign', 'departure', 'step down', 'stepping down', 'retire', 'retirement',
                     'terminate', 'termination', 'ceased', 'no longer', 'will leave']
APPOINTMENT_KEYWORDS = ['appoint', 'appointed', 'named', 'promote', 'promoted', 'effective',
                       'assume', 'will serve', 'has joined']
INVESTOR_DAY_KEYWORDS = ['investor day', 'investor event', 'analyst day', 'investor presentation',
                        'investor conference', 'capital markets day']


def parse_8k_item_numbers(filing_text: str) -> List[str]:
    """
    Extract Item numbers from 8-K filing text.

    Args:
        filing_text: Raw text from 8-K filing

    Returns:
        List of item numbers (e.g., ['5.02', '9.01'])
    """
    # Pattern to match "Item X.XX" format
    pattern = r'Item\s+(\d+\.\d+)'
    matches = re.findall(pattern, filing_text, re.IGNORECASE)

    return list(set(matches))  # Remove duplicates


def classify_leadership_change(filing_text: str) -> Dict[str, any]:
    """
    Classify leadership change events from 8-K text.

    Returns:
        Dict with keys:
        - event_type: 'ceo_change' or 'cfo_change' or 'director_change'
        - role: specific role title
        - change_type: 'departure', 'appointment', or 'both'
        - forced: True if forced departure indicators present
        - succession_type: 'planned_inside', 'outside', or 'unknown'
    """
    text_lower = filing_text.lower()

    # Determine role
    is_ceo = any(kw in text_lower for kw in CEO_KEYWORDS)
    is_cfo = any(kw in text_lower for kw in CFO_KEYWORDS)

    if is_ceo:
        event_type = 'ceo_change'
    elif is_cfo:
        event_type = 'cfo_change'
    else:
        event_type = 'director_change'

    # Determine change type
    has_departure = any(kw in text_lower for kw in DEPARTURE_KEYWORDS)
    has_appointment = any(kw in text_lower for kw in APPOINTMENT_KEYWORDS)

    if has_departure and has_appointment:
        change_type = 'both'
    elif has_departure:
        change_type = 'departure'
    elif has_appointment:
        change_type = 'appointment'
    else:
        change_type = 'unknown'

    # Detect forced departure indicators
    forced_indicators = ['terminate', 'termination', 'dismissed', 'removed', 'effective immediately']
    forced = any(ind in text_lower for ind in forced_indicators)

    # Detect succession type
    inside_indicators = ['promoted', 'current', 'has served', 'interim', 'acting']
    outside_indicators = ['join', 'joining', 'hired', 'appointed from']

    has_inside = any(ind in text_lower for ind in inside_indicators)
    has_outside = any(ind in text_lower for ind in outside_indicators)

    if has_inside and not has_outside:
        succession_type = 'planned_inside'
    elif has_outside:
        succession_type = 'outside'
    else:
        succession_type = 'unknown'

    return {
        'event_type': event_type,
        'change_type': change_type,
        'forced': forced,
        'succession_type': succession_type,
        'confidence': 0.7 if (is_ceo or is_cfo) else 0.4
    }


def classify_investor_event(filing_text: str) -> Dict[str, any]:
    """
    Classify investor/IR events from 8-K text.

    Returns:
        Dict with keys:
        - event_type: 'investor_day', 'analyst_day', or 'conference_presentation'
        - description: extracted description
    """
    text_lower = filing_text.lower()

    if 'investor day' in text_lower or 'capital markets day' in text_lower:
        event_type = 'investor_day'
    elif 'analyst day' in text_lower:
        event_type = 'analyst_day'
    elif 'investor presentation' in text_lower or 'investor conference' in text_lower:
        event_type = 'conference_presentation'
    else:
        event_type = 'investor_event'

    # Try to extract event description
    description = "IR Event"  # Default

    return {
        'event_type': event_type,
        'description': description,
        'confidence': 0.6
    }


def parse_8k_filing(
    ticker: str,
    filing_date: str,
    filing_text: str,
    filing_url: Optional[str] = None
) -> List[Dict]:
    """
    Parse a single 8-K filing and extract corporate events.

    Args:
        ticker: Company ticker
        filing_date: Date of filing (YYYY-MM-DD)
        filing_text: Full text of 8-K filing
        filing_url: Optional URL to filing

    Returns:
        List of event dictionaries with keys:
        - ticker
        - date
        - event_type
        - description
        - event_metadata
        - filing_url
    """
    events = []

    # Extract Item numbers
    items = parse_8k_item_numbers(filing_text)

    # Process each item
    for item in items:
        base_event_type = ITEM_TO_EVENT_TYPE.get(item, 'other_8k')

        event = {
            'ticker': ticker,
            'date': filing_date,
            'event_type': base_event_type,
            'description': f"8-K Item {item}",
            'event_metadata': {},
            'filing_url': filing_url,
            'item_number': item
        }

        # Classify specific event types
        if base_event_type == 'leadership_change':
            metadata = classify_leadership_change(filing_text)
            event['event_type'] = metadata['event_type']
            event['description'] = f"{metadata['event_type'].replace('_', ' ').title()} - {metadata['change_type'].title()}"
            event['event_metadata'] = {
                'succession_type': metadata.get('succession_type'),
                'forced': metadata.get('forced', False),
                'change_type': metadata.get('change_type')
            }

        elif base_event_type == 'investor_event':
            metadata = classify_investor_event(filing_text)
            event['event_type'] = metadata['event_type']
            event['description'] = metadata.get('description', event['event_type'].replace('_', ' ').title())

        elif base_event_type == 'strategic_announcement':
            event['description'] = f"Strategic Announcement (Item {item})"
            event['event_metadata'] = {
                'announcement_type': 'strategic',
                'sentiment': 0.0  # Neutral default, could be enhanced with NLP
            }

        events.append(event)

    return events


def extract_events_from_filings(
    df_filings: pd.DataFrame,
    ticker_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Extract corporate events from a DataFrame of SEC filings.

    Args:
        df_filings: DataFrame with columns ['ticker', 'form', 'filed', 'text' or 'url']
        ticker_filter: Optional ticker to filter to
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        DataFrame with columns:
        - ticker
        - date
        - event_type
        - description
        - event_metadata (dict)
        - filing_url
    """
    # Filter to 8-K filings only
    filings_8k = df_filings[df_filings['form'].str.contains('8-K', case=False, na=False)].copy()

    if ticker_filter:
        filings_8k = filings_8k[filings_8k['ticker'] == ticker_filter]

    if start_date:
        filings_8k = filings_8k[filings_8k['filed'] >= start_date]

    if end_date:
        filings_8k = filings_8k[filings_8k['filed'] <= end_date]

    all_events = []

    for _, row in filings_8k.iterrows():
        ticker = row['ticker']
        filing_date = row['filed']
        filing_text = row.get('text', '')
        filing_url = row.get('url', None)

        # Skip if no text available
        if not filing_text and 'url' in row:
            # In production, you might fetch the filing text from the URL here
            continue

        # Parse this filing
        events = parse_8k_filing(ticker, filing_date, filing_text, filing_url)
        all_events.extend(events)

    if not all_events:
        return pd.DataFrame(columns=['ticker', 'date', 'event_type', 'description', 'event_metadata', 'filing_url'])

    return pd.DataFrame(all_events)


def get_corporate_events_summary(events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize extracted corporate events by type.

    Args:
        events_df: DataFrame from extract_events_from_filings()

    Returns:
        Summary DataFrame with event counts by type
    """
    if events_df.empty:
        return pd.DataFrame(columns=['event_type', 'count', 'tickers'])

    summary = events_df.groupby('event_type').agg({
        'event_type': 'count',
        'ticker': lambda x: ', '.join(sorted(set(x)))
    }).rename(columns={'event_type': 'count', 'ticker': 'tickers'})

    summary = summary.reset_index()
    summary = summary.sort_values('count', ascending=False)

    return summary


# Example usage:
if __name__ == '__main__':
    # Example 8-K text snippets
    example_ceo_change = """
    Item 5.02 Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers

    On January 15, 2024, John Smith resigned as Chief Executive Officer of Example Corp.
    The Board of Directors has appointed Jane Doe, currently serving as Chief Operating Officer,
    to succeed Mr. Smith as CEO effective January 22, 2024.
    """

    example_investor_day = """
    Item 7.01 Regulation FD Disclosure

    Example Corp. will host its annual Investor Day on March 1, 2024, at its headquarters in New York.
    The company will provide updates on strategic initiatives and long-term financial targets.
    """

    # Test parsing
    events1 = parse_8k_filing('EXMP', '2024-01-15', example_ceo_change)
    events2 = parse_8k_filing('EXMP', '2024-02-20', example_investor_day)

    print("CEO Change Event:")
    print(events1)
    print("\nInvestor Day Event:")
    print(events2)
