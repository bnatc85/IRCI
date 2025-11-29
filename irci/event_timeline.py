"""
IRCI Event Timeline Module

Creates comprehensive event calendars showing:
- News headlines and media coverage
- SEC filings (8-K, 10-Q, 10-K)
- Major EV/liquidity changes
- IRCI score impact analysis
- User-editable notes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import json
from pathlib import Path


def extract_sec_filing_events(
    df_coverage: pd.DataFrame,
    ticker: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Extract SEC filing events from coverage data.

    Returns DataFrame with columns:
    - date: filing date
    - event_type: '8-K', '10-Q', '10-K'
    - description: filing description
    - ticker
    """
    # This would need access to the underlying SEC filings data
    # For now, we'll create a placeholder that estimates from coverage data
    events = []

    # In the actual implementation, we'd parse the SEC filings from coverage module
    # Placeholder for demonstration
    return pd.DataFrame(events, columns=['date', 'event_type', 'description', 'ticker'])


def extract_news_events(
    df_trust: pd.DataFrame,
    ticker: str,
    start_date: str,
    end_date: str,
    news_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Extract news and media events.

    Args:
        df_trust: Trust data with media tone information
        ticker: Company ticker
        start_date: Start of period
        end_date: End of period
        news_df: Optional raw news DataFrame if available

    Returns DataFrame with:
    - date
    - event_type: 'news'
    - headline
    - sentiment: positive/negative/neutral
    - sentiment_score
    - ticker
    """
    events = []

    if news_df is not None and not news_df.empty:
        # Filter news for this ticker and date range
        # Handle both 'ticker' column (if present) and 'published_at' date column
        date_col = 'published_at' if 'published_at' in news_df.columns else 'date'

        # Filter by ticker if column exists
        if 'ticker' in news_df.columns:
            ticker_news = news_df[news_df['ticker'] == ticker].copy()
        else:
            ticker_news = news_df.copy()

        # Filter by date range
        if date_col in ticker_news.columns:
            ticker_news[date_col] = pd.to_datetime(ticker_news[date_col])

            # Make start/end dates timezone-aware if needed
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            # If news dates are timezone-aware, make comparison dates timezone-aware too
            if ticker_news[date_col].dt.tz is not None:
                if start_dt.tz is None:
                    start_dt = start_dt.tz_localize('UTC')
                if end_dt.tz is None:
                    end_dt = end_dt.tz_localize('UTC')
            else:
                # If news dates are timezone-naive, make sure comparison dates are too
                if start_dt.tz is not None:
                    start_dt = start_dt.tz_localize(None)
                if end_dt.tz is not None:
                    end_dt = end_dt.tz_localize(None)

            ticker_news = ticker_news[
                (ticker_news[date_col] >= start_dt) &
                (ticker_news[date_col] <= end_dt)
            ]

        for _, row in ticker_news.iterrows():
            events.append({
                'date': row.get(date_col, pd.Timestamp.now()),
                'event_type': 'news',
                'headline': row.get('headline', row.get('title', 'News Article')),
                'sentiment': row.get('sentiment', 'neutral'),
                'sentiment_score': row.get('sentiment_score', 0.0),
                'ticker': ticker,
                'source': row.get('source', 'Unknown')
            })

    return pd.DataFrame(events)


def extract_liquidity_events(
    df_liquidity: pd.DataFrame,
    ticker: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Extract liquidity measurement events.

    Returns DataFrame with:
    - date
    - event_type: 'liquidity_measurement'
    - description
    - liquidity_score
    """
    events = []

    ticker_liq = df_liquidity[df_liquidity['ticker'] == ticker]

    for _, row in ticker_liq.iterrows():
        if pd.notna(row.get('liquidity_pct')):
            # Create description based on available metrics
            desc_parts = [f"Liquidity Score: {row['liquidity_pct']:.1f}%"]
            if pd.notna(row.get('q_turnover')):
                desc_parts.append(f"Turnover: {row['q_turnover']:.4f}")
            if pd.notna(row.get('q_amihud_e6')):
                desc_parts.append(f"Amihud: {row['q_amihud_e6']:.2f}×10⁶")

            events.append({
                'date': row['quarter_end'],
                'event_type': 'liquidity_measurement',
                'description': ', '.join(desc_parts),
                'liquidity_pct': row['liquidity_pct'],
                'ticker': ticker
            })

    return pd.DataFrame(events)


def extract_valuation_events(
    df_valuation: pd.DataFrame,
    ticker: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Extract valuation measurement events.

    Returns DataFrame with:
    - date
    - event_type: 'valuation_measurement'
    - description
    - valuation_score
    """
    events = []

    ticker_val = df_valuation[df_valuation['ticker'] == ticker]

    for _, row in ticker_val.iterrows():
        if pd.notna(row.get('enterprise_value')):
            desc_parts = [f"Valuation Score: {row['valuation_pct']:.1f}%"]
            if pd.notna(row.get('enterprise_value')):
                desc_parts.append(f"EV: ${row['enterprise_value']/1e9:.1f}B")
            if pd.notna(row.get('ev_to_ebitda')):
                desc_parts.append(f"EV/EBITDA: {row['ev_to_ebitda']:.1f}x")

            events.append({
                'date': row['as_of'],
                'event_type': 'valuation_measurement',
                'description': ', '.join(desc_parts),
                'enterprise_value': row['enterprise_value'],
                'valuation_pct': row.get('valuation_pct', np.nan),
                'ticker': ticker
            })

    return pd.DataFrame(events)


def extract_trust_events(
    df_trust: pd.DataFrame,
    ticker: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Extract trust/sentiment measurement events.

    Returns DataFrame with:
    - date
    - event_type: 'trust_measurement'
    - description
    - trust_score
    """
    events = []

    ticker_trust = df_trust[df_trust['ticker'] == ticker]

    for _, row in ticker_trust.iterrows():
        if pd.notna(row.get('trust_pct')):
            desc_parts = [f"Trust Score: {row['trust_pct']:.1f}%"]
            if pd.notna(row.get('media_tone_n')) and row.get('media_tone_n', 0) > 0:
                desc_parts.append(f"{int(row['media_tone_n'])} articles analyzed")
            if pd.notna(row.get('event_count')) and row.get('event_count', 0) > 0:
                desc_parts.append(f"{int(row['event_count'])} events")

            events.append({
                'date': row['quarter_end'],
                'event_type': 'trust_measurement',
                'description': ', '.join(desc_parts),
                'trust_pct': row['trust_pct'],
                'ticker': ticker
            })

    return pd.DataFrame(events)


def extract_coverage_events(
    df_coverage: pd.DataFrame,
    ticker: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Extract coverage measurement events.

    Returns DataFrame with:
    - date
    - event_type: 'coverage_measurement'
    - description
    - coverage_score
    """
    events = []

    ticker_cov = df_coverage[df_coverage['ticker'] == ticker]

    for _, row in ticker_cov.iterrows():
        if pd.notna(row.get('coverage_pct')):
            desc_parts = [f"Coverage Score: {row['coverage_pct']:.1f}%"]
            if pd.notna(row.get('q_8k_count')):
                desc_parts.append(f"{int(row['q_8k_count'])} 8-K filings")
            if pd.notna(row.get('q_days_to_10q')):
                desc_parts.append(f"10-Q filed in {int(row['q_days_to_10q'])} days")

            events.append({
                'date': row['as_of'],
                'event_type': 'coverage_measurement',
                'description': ', '.join(desc_parts),
                'coverage_pct': row['coverage_pct'],
                'ticker': ticker
            })

    return pd.DataFrame(events)


def calculate_event_irci_impact(
    event_date: str,
    event_type: str,
    df_composite: pd.DataFrame,
    df_val: pd.DataFrame,
    ticker: str,
    sentiment_score: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
    company_dollar_per_irci_pt: Optional[float] = None,
    event_metadata: Optional[Dict] = None
) -> Dict[str, float]:
    """
    Estimate the impact of an event on IRCI score and dollar value.

    Strategy:
    - For news: use sentiment score to estimate impact on trust dial
    - For filings: positive impact on coverage dial
    - For EV changes: direct impact on valuation dial
    - For investor days: major positive impact on coverage and trust (CAR +0.5% to +5%)
    - For leadership changes: impact on trust/governance based on succession type
    - For strategic announcements: varies by type

    Args:
        event_date: Date of the event
        event_type: Type of event ('news', '8-K', '10-Q', '10-K', 'investor_day', 'ceo_change', etc.)
        df_composite: Composite scores DataFrame
        df_val: Valuation DataFrame
        ticker: Stock ticker
        sentiment_score: Sentiment score for news (-1 to 1)
        weights: Dial weights dict with keys: valuation, liquidity, coverage, sentiment
        company_dollar_per_irci_pt: Company-specific $/IRCI point from regression
        event_metadata: Additional event metadata (succession_type, announcement_type, etc.)

    Returns:
    - irci_impact: estimated change in IRCI composite score
    - dollar_impact: estimated change in enterprise value
    - confidence: 0-1 scale confidence in the estimate
    - affected_dials: list of dials affected
    - car_estimate: Cumulative Abnormal Return estimate (%)
    """
    # Default weights if not provided
    if weights is None:
        weights = {
            'valuation': 0.35,
            'liquidity': 0.35,
            'coverage': 0.15,
            'sentiment': 0.15
        }

    # Initialize event metadata if not provided
    if event_metadata is None:
        event_metadata = {}

    impact = {
        'irci_impact': 0.0,
        'dollar_impact': 0.0,
        'confidence': 0.0,
        'affected_dials': [],
        'car_estimate': 0.0  # Cumulative Abnormal Return estimate (%)
    }

    # Get current IRCI score and EV
    ticker_composite = df_composite[df_composite['ticker'] == ticker]
    ticker_val = df_val[df_val['ticker'] == ticker]

    if ticker_composite.empty or ticker_val.empty:
        return impact

    current_irci = ticker_composite['irci_composite_pct'].iloc[0]
    current_ev = ticker_val['enterprise_value'].iloc[0] if 'enterprise_value' in ticker_val.columns else 0

    # Estimate impact based on event type
    if event_type == 'news':
        # News impacts trust dial (sentiment_pct)
        # Individual articles have VERY small impact - aggregate quarterly sentiment matters more
        # A single article might contribute 0.01-0.1% to the trust dial (not 0.5%)
        # The trust dial aggregates 50-100+ articles per quarter, so each article is ~1-2% of the total
        if sentiment_score is not None:
            trust_weight = weights.get('sentiment', 0.15)  # Use configured trust/sentiment weight
            # VERY Conservative: single article contributes ~0.05% max to trust dial
            # sentiment_score ranges -1 to +1, scale to 0.0005 dial points (0.05%)
            # This reflects that a single article is ~1/100th of quarterly coverage
            dial_impact = sentiment_score * 0.0005  # -0.0005 to +0.0005 points on trust dial
            impact['irci_impact'] = dial_impact * trust_weight
            impact['affected_dials'] = ['Trust']
            impact['confidence'] = 0.05  # Very low confidence - individual news is weak signal

    elif event_type in ['8-K', '10-Q', '10-K']:
        # Filings positively impact coverage dial
        # Individual filings contribute to quarterly coverage metrics
        # A single filing might contribute 0.01-0.1% to coverage dial
        # Coverage is measured by aggregate filing activity, not individual filings
        coverage_weight = weights.get('coverage', 0.15)  # Use configured coverage weight
        if event_type == '8-K':
            dial_impact = 0.001  # Small positive contribution (0.1%)
        else:  # 10-Q or 10-K
            dial_impact = 0.003  # Larger contribution for major filings (0.3%)
        impact['irci_impact'] = dial_impact * coverage_weight
        impact['affected_dials'] = ['Coverage']
        impact['confidence'] = 0.1  # Low confidence - filings are measured in aggregate

    elif event_type == 'ev_change':
        # Direct impact on valuation
        impact['confidence'] = 0.7  # Higher confidence for direct measurements
        impact['affected_dials'] = ['Valuation']
        # This would need time-series EV data to calculate actual change

    elif event_type == 'investor_day':
        # Investor Days - Major IR engagement event
        # Research: Average CAR +0.5% to +5%, average +30% appreciation in case studies (MZ Group 2024)
        # Impacts: Coverage (IR engagement) and Trust (transparency/confidence)
        coverage_weight = weights.get('coverage', 0.15)
        trust_weight = weights.get('sentiment', 0.15)

        # Conservative estimate: +2% to coverage dial, +1.5% to trust dial
        coverage_dial_impact = 0.02  # 2% improvement
        trust_dial_impact = 0.015    # 1.5% improvement

        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Trust']
        impact['confidence'] = 0.6  # Medium-high confidence (well-researched event type)
        impact['car_estimate'] = 2.0  # Conservative 2% CAR estimate

    elif event_type == 'analyst_day':
        # Similar to investor_day but slightly lower impact
        coverage_weight = weights.get('coverage', 0.15)
        trust_weight = weights.get('sentiment', 0.15)

        coverage_dial_impact = 0.015  # 1.5% improvement
        trust_dial_impact = 0.01      # 1% improvement

        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Trust']
        impact['confidence'] = 0.5
        impact['car_estimate'] = 1.5

    elif event_type == 'ceo_change':
        # CEO Turnover - Impact varies significantly by succession type
        # Research: Forced = negative returns, Voluntary inside = small positive, Outside = higher volatility
        trust_weight = weights.get('sentiment', 0.15)

        succession_type = event_metadata.get('succession_type', 'unknown')
        forced = event_metadata.get('forced', False)

        if succession_type == 'planned_inside' and not forced:
            # Planned internal succession - small positive signal
            trust_dial_impact = 0.005  # +0.5% to trust
            impact['confidence'] = 0.4
            impact['car_estimate'] = 0.5  # Small positive CAR
        elif forced:
            # Forced turnover - negative signal (governance concerns)
            trust_dial_impact = -0.01  # -1% to trust
            impact['confidence'] = 0.5
            impact['car_estimate'] = -1.5  # Negative CAR
        elif succession_type == 'outside':
            # Outside succession - uncertainty/volatility
            trust_dial_impact = -0.005  # -0.5% to trust
            impact['confidence'] = 0.4
            impact['car_estimate'] = -0.5
        else:
            # Unknown type - assume neutral to slightly negative
            trust_dial_impact = -0.003
            impact['confidence'] = 0.3
            impact['car_estimate'] = 0.0

        impact['irci_impact'] = trust_dial_impact * trust_weight
        impact['affected_dials'] = ['Trust']

    elif event_type == 'cfo_change':
        # CFO Turnover - Generally negative for earnings quality perception
        # Research: Negatively associated with earnings persistence, increases accrual management concerns
        trust_weight = weights.get('sentiment', 0.15)

        forced = event_metadata.get('forced', False)

        if forced:
            trust_dial_impact = -0.008  # -0.8% to trust (earnings quality concern)
            impact['car_estimate'] = -1.0
        else:
            trust_dial_impact = -0.003  # -0.3% to trust (mild concern)
            impact['car_estimate'] = -0.3

        impact['irci_impact'] = trust_dial_impact * trust_weight
        impact['affected_dials'] = ['Trust']
        impact['confidence'] = 0.3

    elif event_type == 'earnings_call':
        # Earnings calls - positive coverage signal (already partially captured via 10-Q/10-K)
        coverage_weight = weights.get('coverage', 0.15)

        dial_impact = 0.002  # Small positive (0.2%)
        impact['irci_impact'] = dial_impact * coverage_weight
        impact['affected_dials'] = ['Coverage']
        impact['confidence'] = 0.2
        impact['car_estimate'] = 0.0  # Neutral (depends on actual results)

    elif event_type == 'strategic_announcement':
        # M&A, restructuring, major initiatives
        # Impact highly variable - use metadata sentiment if available
        announcement_type = event_metadata.get('announcement_type', 'unknown')
        announcement_sentiment = event_metadata.get('sentiment', 0.0)  # -1 to +1

        trust_weight = weights.get('sentiment', 0.15)
        coverage_weight = weights.get('coverage', 0.15)

        # Strategic announcements impact both trust and coverage
        trust_dial_impact = announcement_sentiment * 0.01  # -1% to +1%
        coverage_dial_impact = 0.005  # +0.5% (any announcement increases visibility)

        impact['irci_impact'] = (trust_dial_impact * trust_weight) + (coverage_dial_impact * coverage_weight)
        impact['affected_dials'] = ['Trust', 'Coverage']
        impact['confidence'] = 0.4
        impact['car_estimate'] = announcement_sentiment * 2.0  # -2% to +2% CAR

    elif event_type == 'dividend_announcement':
        # Dividend announcements - generally positive for trust/stability
        trust_weight = weights.get('sentiment', 0.15)

        dividend_change = event_metadata.get('dividend_change_pct', 0.0)

        if dividend_change > 0:
            trust_dial_impact = 0.005  # +0.5% for increase
            impact['car_estimate'] = 1.0
        elif dividend_change < 0:
            trust_dial_impact = -0.008  # -0.8% for decrease/cut
            impact['car_estimate'] = -2.0
        else:
            trust_dial_impact = 0.002  # +0.2% for maintaining
            impact['car_estimate'] = 0.0

        impact['irci_impact'] = trust_dial_impact * trust_weight
        impact['affected_dials'] = ['Trust']
        impact['confidence'] = 0.4

    elif event_type == 'buyback_announcement':
        # Share buyback announcements - positive signal
        trust_weight = weights.get('sentiment', 0.15)

        trust_dial_impact = 0.008  # +0.8% (capital allocation confidence)
        impact['irci_impact'] = trust_dial_impact * trust_weight
        impact['affected_dials'] = ['Trust']
        impact['confidence'] = 0.5
        impact['car_estimate'] = 1.5  # Positive CAR

    # === Daily IR Activities ===
    # Research-backed impacts for ongoing investor relations programs

    elif event_type == 'ir_website_improvement':
        # Research: IR website visits improve corporate investment efficiency by 0.5%-2%
        # Source: Chen et al. (2015) - "The Role of the Media in Disseminating Insider-Trading News"
        # Improved disclosure quality reduces information asymmetry
        coverage_weight = weights.get('coverage', 0.15)
        trust_weight = weights.get('sentiment', 0.15)

        coverage_dial_impact = 0.01   # +1% to coverage (better information access)
        trust_dial_impact = 0.005     # +0.5% to trust (transparency signal)
        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Trust']
        impact['confidence'] = 0.5
        impact['car_estimate'] = 1.0  # Conservative 1% CAR estimate

    elif event_type == 'advertising_campaign':
        # Research: 25% increase in advertising → +1.32% firm value (Grullon et al. 2004)
        # Mechanism: Increased investor awareness → higher liquidity → lower cost of capital
        # Source: "Advertising, Breadth of Ownership, and Liquidity" (Review of Financial Studies)
        liquidity_weight = weights.get('liquidity', 0.35)
        coverage_weight = weights.get('coverage', 0.15)

        liquidity_dial_impact = 0.012  # +1.2% to liquidity (breadth of ownership)
        coverage_dial_impact = 0.008   # +0.8% to coverage (investor awareness)
        impact['irci_impact'] = (liquidity_dial_impact * liquidity_weight) + (coverage_dial_impact * coverage_weight)
        impact['affected_dials'] = ['Liquidity', 'Coverage']
        impact['confidence'] = 0.6
        impact['car_estimate'] = 1.3  # Based on Grullon et al. findings

    elif event_type == 'press_release_program':
        # Research: Press releases affect immediate stock prices and trading volumes
        # Source: Neuhierl et al. (2013) - "Market Reaction to Corporate Press Releases"
        # Impact varies by content sentiment (-2% to +2%)
        sentiment = event_metadata.get('sentiment', 0.0)  # -1 to +1 scale
        coverage_weight = weights.get('coverage', 0.15)
        trust_weight = weights.get('sentiment', 0.15)

        coverage_dial_impact = 0.003   # +0.3% base coverage improvement
        trust_dial_impact = sentiment * 0.005  # ±0.5% based on sentiment
        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Trust']
        impact['confidence'] = 0.4
        impact['car_estimate'] = sentiment * 2.0  # -2% to +2% CAR range

    elif event_type == 'social_media_campaign':
        # Research: 80% of institutional investors use social media for research
        # 30% say social media influenced investment decisions (Brunswick Group 2023)
        # Enhances retail investor engagement and brand awareness
        coverage_weight = weights.get('coverage', 0.15)
        liquidity_weight = weights.get('liquidity', 0.35)

        coverage_dial_impact = 0.006   # +0.6% to coverage (broader reach)
        liquidity_dial_impact = 0.004  # +0.4% to liquidity (retail engagement)
        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + (liquidity_dial_impact * liquidity_weight)
        impact['affected_dials'] = ['Coverage', 'Liquidity']
        impact['confidence'] = 0.4
        impact['car_estimate'] = 0.5  # Modest positive impact

    elif event_type == 'conference_presentation':
        # Research: Conference presentations serve as price discovery mechanism
        # Source: Francis et al. (1997) - "Costs of Equity and Earnings Attributes"
        # Non-deal roadshows help control narrative and engage investors
        coverage_weight = weights.get('coverage', 0.15)
        trust_weight = weights.get('sentiment', 0.15)

        coverage_dial_impact = 0.008   # +0.8% to coverage (analyst/investor exposure)
        trust_dial_impact = 0.004      # +0.4% to trust (management credibility)
        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Trust']
        impact['confidence'] = 0.5
        impact['car_estimate'] = 0.8  # Positive information effect

    elif event_type == 'analyst_coverage_initiation':
        # Research: Analyst coverage initiation creates +1.02% abnormal return (Irvine 2003)
        # Source: "The Incremental Impact of Analyst Initiation of Coverage" (JFE)
        # Reduces information asymmetry and increases institutional ownership
        coverage_weight = weights.get('coverage', 0.15)
        liquidity_weight = weights.get('liquidity', 0.35)
        trust_weight = weights.get('sentiment', 0.15)

        coverage_dial_impact = 0.015   # +1.5% to coverage (new analyst following)
        liquidity_dial_impact = 0.008  # +0.8% to liquidity (institutional interest)
        trust_dial_impact = 0.005      # +0.5% to trust (third-party validation)
        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + \
                               (liquidity_dial_impact * liquidity_weight) + \
                               (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Liquidity', 'Trust']
        impact['confidence'] = 0.7
        impact['car_estimate'] = 1.0  # Conservative vs. Irvine's 1.02%

    # Calculate dollar impact using company-specific $/IRCI point from regression
    # NOTE: company_dollar_per_irci_pt should already be R²-scaled from dial_insights.py
    # This ensures dollar estimates reflect that IR is only one factor affecting enterprise value
    if impact['irci_impact'] != 0:
        if company_dollar_per_irci_pt is not None and company_dollar_per_irci_pt > 0:
            # Use the regression-based estimate (more accurate and R²-scaled)
            impact['dollar_impact'] = impact['irci_impact'] * company_dollar_per_irci_pt
        elif current_ev > 0:
            # Fallback: rough estimate using current EV (no R² scaling available)
            # Apply conservative 10% scaling to account for IR being one of many factors
            ev_per_irci_point = current_ev / (current_irci + 1)
            impact['dollar_impact'] = impact['irci_impact'] * ev_per_irci_point * 0.1

    return impact


def aggregate_timeline_events(
    ticker: str,
    start_date: str,
    end_date: str,
    df_composite: pd.DataFrame,
    df_val: pd.DataFrame,
    df_cov: pd.DataFrame,
    df_liq: pd.DataFrame,
    df_trust: pd.DataFrame,
    news_df: Optional[pd.DataFrame] = None,
    sec_filings_df: Optional[pd.DataFrame] = None,
    weights: Optional[Dict[str, float]] = None,
    company_dollar_per_irci_pt: Optional[float] = None
) -> pd.DataFrame:
    """
    Aggregate all events for a ticker into a single timeline.

    Returns DataFrame with all events sorted by date, including:
    - date
    - event_type
    - description
    - headline (for news)
    - sentiment_score (for news)
    - irci_impact
    - dollar_impact
    - impact_confidence
    - affected_dials
    """
    all_events = []

    # Extract SEC filings from coverage data
    if sec_filings_df is not None:
        filing_events = sec_filings_df[
            (sec_filings_df['ticker'] == ticker) &
            (sec_filings_df['date'] >= start_date) &
            (sec_filings_df['date'] <= end_date)
        ].copy()

        for _, row in filing_events.iterrows():
            impact = calculate_event_irci_impact(
                row['date'],
                row['event_type'],
                df_composite,
                df_val,
                ticker,
                weights=weights,
                company_dollar_per_irci_pt=company_dollar_per_irci_pt
            )

            all_events.append({
                'date': pd.to_datetime(row['date']),
                'event_type': row['event_type'],
                'description': row.get('description', f"{row['event_type']} Filing"),
                'headline': row.get('description', ''),
                'sentiment_score': None,
                'irci_impact': impact['irci_impact'],
                'dollar_impact': impact['dollar_impact'],
                'impact_confidence': impact['confidence'],
                'affected_dials': ', '.join(impact['affected_dials']),
                'ticker': ticker
            })

    # Extract news events
    news_events = extract_news_events(df_trust, ticker, start_date, end_date, news_df)
    for _, row in news_events.iterrows():
        impact = calculate_event_irci_impact(
            row['date'],
            'news',
            df_composite,
            df_val,
            ticker,
            sentiment_score=row.get('sentiment_score', 0.0),
            weights=weights,
            company_dollar_per_irci_pt=company_dollar_per_irci_pt
        )

        all_events.append({
            'date': pd.to_datetime(row['date']),
            'event_type': 'news',
            'description': row.get('headline', 'News Article'),
            'headline': row.get('headline', ''),
            'sentiment_score': row.get('sentiment_score', 0.0),
            'irci_impact': impact['irci_impact'],
            'dollar_impact': impact['dollar_impact'],
            'impact_confidence': impact['confidence'],
            'affected_dials': ', '.join(impact['affected_dials']),
            'ticker': ticker,
            'source': row.get('source', 'Unknown')
        })

    # Extract liquidity events
    liquidity_events = extract_liquidity_events(df_liq, ticker, start_date, end_date)
    for _, row in liquidity_events.iterrows():
        all_events.append({
            'date': pd.to_datetime(row['date']),
            'event_type': 'liquidity_measurement',
            'description': row['description'],
            'headline': '',
            'sentiment_score': None,
            'irci_impact': 0.0,  # These are measurements, not events with impact
            'dollar_impact': 0.0,
            'impact_confidence': 0.0,
            'affected_dials': 'Liquidity',
            'ticker': ticker
        })

    # Extract valuation events
    valuation_events = extract_valuation_events(df_val, ticker, start_date, end_date)
    for _, row in valuation_events.iterrows():
        all_events.append({
            'date': pd.to_datetime(row['date']),
            'event_type': 'valuation_measurement',
            'description': row['description'],
            'headline': '',
            'sentiment_score': None,
            'irci_impact': 0.0,
            'dollar_impact': 0.0,
            'impact_confidence': 0.0,
            'affected_dials': 'Valuation',
            'ticker': ticker
        })

    # Extract trust events
    trust_events = extract_trust_events(df_trust, ticker, start_date, end_date)
    for _, row in trust_events.iterrows():
        all_events.append({
            'date': pd.to_datetime(row['date']),
            'event_type': 'trust_measurement',
            'description': row['description'],
            'headline': '',
            'sentiment_score': None,
            'irci_impact': 0.0,
            'dollar_impact': 0.0,
            'impact_confidence': 0.0,
            'affected_dials': 'Trust',
            'ticker': ticker
        })

    # Extract coverage events
    coverage_events = extract_coverage_events(df_cov, ticker, start_date, end_date)
    for _, row in coverage_events.iterrows():
        all_events.append({
            'date': pd.to_datetime(row['date']),
            'event_type': 'coverage_measurement',
            'description': row['description'],
            'headline': '',
            'sentiment_score': None,
            'irci_impact': 0.0,
            'dollar_impact': 0.0,
            'impact_confidence': 0.0,
            'affected_dials': 'Coverage',
            'ticker': ticker
        })

    # Create DataFrame and sort by date
    if all_events:
        timeline_df = pd.DataFrame(all_events)
        # Normalize all dates to timezone-naive to avoid comparison errors
        # Convert to UTC first (handles both tz-aware and tz-naive), then remove tz
        timeline_df['date'] = pd.to_datetime(timeline_df['date'], utc=True).dt.tz_localize(None)
        timeline_df = timeline_df.sort_values('date')
        return timeline_df
    else:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(columns=[
            'date', 'event_type', 'description', 'headline', 'sentiment_score',
            'irci_impact', 'dollar_impact', 'impact_confidence', 'affected_dials', 'ticker'
        ])


def create_calendar_view(
    timeline_df: pd.DataFrame,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Create a calendar-style view of events organized by date.

    Groups events by day and provides summary statistics.

    Returns DataFrame with:
    - date
    - num_events
    - event_types (comma-separated)
    - total_irci_impact
    - total_dollar_impact
    - headlines (top 3)
    """
    if timeline_df.empty:
        return pd.DataFrame(columns=[
            'date', 'num_events', 'event_types', 'total_irci_impact',
            'total_dollar_impact', 'headlines'
        ])

    # Group by date
    calendar = timeline_df.groupby(timeline_df['date'].dt.date).agg({
        'event_type': lambda x: ', '.join(set(x)),
        'irci_impact': 'sum',
        'dollar_impact': 'sum',
        'headline': lambda x: ' | '.join([h for h in x if h][:3]),  # Top 3 headlines
    }).reset_index()

    calendar.columns = ['date', 'event_types', 'total_irci_impact', 'total_dollar_impact', 'headlines']
    calendar['num_events'] = timeline_df.groupby(timeline_df['date'].dt.date).size().values

    return calendar


class UserNotesManager:
    """
    Manages user-entered notes for events and dates.

    Stores notes in a JSON file per session or workspace.
    """

    def __init__(self, notes_file: str = "irci_user_notes.json"):
        self.notes_file = Path(notes_file)
        self.notes = self._load_notes()

    def _load_notes(self) -> Dict:
        """Load notes from JSON file."""
        if self.notes_file.exists():
            try:
                with open(self.notes_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_notes(self):
        """Save notes to JSON file."""
        try:
            with open(self.notes_file, 'w') as f:
                json.dump(self.notes, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save notes: {e}")

    def add_note(self, ticker: str, date: str, note: str, category: str = "general"):
        """
        Add a user note for a specific ticker and date.

        Args:
            ticker: Company ticker
            date: Date (YYYY-MM-DD format)
            note: User's note text
            category: Note category (general, private, analysis, etc.)
        """
        key = f"{ticker}_{date}"

        if key not in self.notes:
            self.notes[key] = []

        self.notes[key].append({
            'note': note,
            'category': category,
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'date': date
        })

        self._save_notes()

    def get_notes(self, ticker: str, date: Optional[str] = None) -> List[Dict]:
        """
        Get notes for a ticker, optionally filtered by date.

        Args:
            ticker: Company ticker
            date: Optional date to filter by

        Returns:
            List of note dictionaries
        """
        if date:
            key = f"{ticker}_{date}"
            return self.notes.get(key, [])
        else:
            # Return all notes for ticker
            all_notes = []
            for key, notes in self.notes.items():
                if key.startswith(f"{ticker}_"):
                    all_notes.extend(notes)
            return sorted(all_notes, key=lambda x: x['timestamp'], reverse=True)

    def delete_note(self, ticker: str, date: str, note_index: int):
        """Delete a specific note."""
        key = f"{ticker}_{date}"
        if key in self.notes and note_index < len(self.notes[key]):
            del self.notes[key][note_index]
            if not self.notes[key]:  # Remove key if no notes left
                del self.notes[key]
            self._save_notes()

    def get_all_notes(self) -> Dict:
        """Get all notes."""
        return self.notes


def create_impact_summary(
    timeline_df: pd.DataFrame,
    ticker: str
) -> Dict[str, any]:
    """
    Create a summary of event impacts over the period.

    Returns:
    - total_events: number of events
    - total_irci_impact: sum of IRCI impacts
    - total_dollar_impact: sum of dollar impacts
    - top_positive_events: top 5 positive impact events
    - top_negative_events: top 5 negative impact events
    - impact_by_type: breakdown by event type
    """
    if timeline_df.empty:
        return {
            'total_events': 0,
            'total_irci_impact': 0.0,
            'total_dollar_impact': 0.0,
            'top_positive_events': pd.DataFrame(),
            'top_negative_events': pd.DataFrame(),
            'impact_by_type': pd.DataFrame()
        }

    summary = {
        'total_events': len(timeline_df),
        'total_irci_impact': timeline_df['irci_impact'].sum(),
        'total_dollar_impact': timeline_df['dollar_impact'].sum(),
        'top_positive_events': timeline_df.nlargest(5, 'irci_impact')[
            ['date', 'event_type', 'description', 'irci_impact', 'dollar_impact']
        ],
        'top_negative_events': timeline_df.nsmallest(5, 'irci_impact')[
            ['date', 'event_type', 'description', 'irci_impact', 'dollar_impact']
        ],
        'impact_by_type': timeline_df.groupby('event_type').agg({
            'irci_impact': 'sum',
            'dollar_impact': 'sum',
            'event_type': 'count'
        }).rename(columns={'event_type': 'count'})
    }

    return summary
