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
        'event_window_dollar': 0.0,  # CAR × current EV (literature-direct announcement effect)
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
        # Single-article CAR: Ke, Kelly & Xiu (2019, JFE) "Predicting Returns with Text" use
        # supervised topic models on Dow Jones Newswire to extract sentiment that predicts CARs
        # with materially better fit than Loughran-McDonald bag-of-words. Manela & Moreira
        # (2017, JFE) "NVIX" find news-implied volatility predicts equity excess returns.
        # We use a conservative ±30 bps CAR for a material article.
        if sentiment_score is not None:
            trust_weight = weights.get('sentiment', 0.15)
            dial_impact = sentiment_score * 0.0005  # ±0.05% to trust dial (persistent)
            impact['irci_impact'] = dial_impact * trust_weight
            impact['affected_dials'] = ['Trust']
            impact['confidence'] = 0.4
            # Short-window CAR: ±30 bps for sentiment_score=±1, scaled linearly
            impact['car_estimate'] = sentiment_score * 0.30  # Ke, Kelly & Xiu (2019, JFE)

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
        # CEO Turnover - Jenter & Kanaan (2015, JF) on 3,365 forced turnovers 1993-2009:
        # market reaction is CONDITIONAL on prior performance. Firing an underperformer
        # generates positive CARs; firing an outperformer generates negative CARs.
        # We assume the modal "forced" case is firing an underperformer (the common path).
        # Borokhovich, Parrino & Trapani (1996, JFQA) original on outside vs inside still holds.
        trust_weight = weights.get('sentiment', 0.15)

        succession_type = event_metadata.get('succession_type', 'unknown')
        forced = event_metadata.get('forced', False)

        if forced:
            # Forced turnover of underperformer - positive (governance correction)
            trust_dial_impact = 0.015  # +1.5% to trust
            impact['confidence'] = 0.6
            impact['car_estimate'] = 2.0  # Jenter & Kanaan (2015), conditional on underperformance
        elif succession_type == 'outside':
            # Outside successor - positive signal
            trust_dial_impact = 0.008  # +0.8% to trust
            impact['confidence'] = 0.5
            impact['car_estimate'] = 1.0  # Borokhovich, Parrino & Trapani (1996, JFQA)
        elif succession_type == 'planned_inside' and not forced:
            # Planned internal succession - near-zero, small positive
            trust_dial_impact = 0.005  # +0.5% to trust
            impact['confidence'] = 0.4
            impact['car_estimate'] = 0.5
        else:
            # Unknown type - neutral
            trust_dial_impact = 0.0
            impact['confidence'] = 0.2
            impact['car_estimate'] = 0.0

        impact['irci_impact'] = trust_dial_impact * trust_weight
        impact['affected_dials'] = ['Trust']

    elif event_type == 'cfo_change':
        # CFO Turnover - Zhang, Zhou & Wang (2025, Strategic Management Journal) on S&P 1500
        # CFO database 2000-2022 confirms pre-restatement forced turnovers generate significantly
        # negative CARs; voluntary departures near zero. Extends Mian (2001, JAE) and
        # Hennes, Leone & Miller (2008, AR) in modern data.
        trust_weight = weights.get('sentiment', 0.15)

        forced = event_metadata.get('forced', False)

        if forced:
            trust_dial_impact = -0.008  # -0.8% to trust (signals earnings-quality concerns)
            impact['car_estimate'] = -1.0  # Zhang et al. (2025, SMJ)
        else:
            trust_dial_impact = -0.003
            impact['car_estimate'] = -0.3

        impact['irci_impact'] = trust_dial_impact * trust_weight
        impact['affected_dials'] = ['Trust']
        impact['confidence'] = 0.3

    elif event_type == 'earnings_call':
        # Earnings surprise CARs - Meursault, Liu, Cohen, Tian, Hong et al. (2022, JFQA)
        # "PEAD.txt" show top-minus-bottom SUE decile hedge return ~5.1% over 3 months in
        # modern data, but PEAD magnitude has declined ~40% vs the original Bernard-Thomas
        # (1989/1990) finding. Short-window CAR around the announcement holds up better than
        # the post-announcement drift. Skinner & Sloan (2002, RAS) asymmetric punishment still
        # confirmed in modern samples.
        coverage_weight = weights.get('coverage', 0.15)
        trust_weight = weights.get('sentiment', 0.15)
        beat_pct = event_metadata.get('beat_pct', 0.0)

        if beat_pct >= 0.05:
            coverage_dial_impact = 0.005
            trust_dial_impact = 0.01
            impact['car_estimate'] = 3.5  # Meursault et al. (2022, JFQA); short-window CAR robust
            impact['confidence'] = 0.7
        elif beat_pct <= -0.05:
            coverage_dial_impact = -0.005
            trust_dial_impact = -0.01
            impact['car_estimate'] = -4.5  # Skinner-Sloan (2002); asymmetric punishment persists
            impact['confidence'] = 0.7
        else:
            coverage_dial_impact = 0.002
            trust_dial_impact = 0.0
            impact['car_estimate'] = 0.0
            impact['confidence'] = 0.2

        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Trust']

    elif event_type == 'strategic_announcement':
        # M&A, guidance, partnerships, restructuring - CARs vary widely by type.
        # Use announcement_type to pick a literature-grounded CAR.
        announcement_type = event_metadata.get('announcement_type', 'unknown')
        announcement_sentiment = event_metadata.get('sentiment', 0.0)  # -1 to +1

        trust_weight = weights.get('sentiment', 0.15)
        coverage_weight = weights.get('coverage', 0.15)

        # Type-specific CARs from event-study literature (2015+ where available)
        if announcement_type == 'guidance_raise':
            car = 2.5   # Anilowski, Feng & Skinner (2007, JAE); Call et al. (2024 WP)
            confidence = 0.6
        elif announcement_type == 'guidance_lower':
            car = -5.0  # Anilowski, Feng & Skinner (2007); Kasznik & Lev (1995, AR)
            confidence = 0.6
        elif announcement_type == 'ma_acquirer':
            # IMPORTANT: Alexandridis, Antypas & Travlos (2017, J. Corporate Finance) shows
            # the "acquirers lose" stylized fact from Moeller et al. (2004) reversed post-2009.
            # Modern acquirer CAR is small but positive (~+$62M avg per deal; +$325M improvement
            # vs 1990-2009 sample). Public/stock-for-stock deals no longer destroy value.
            car = 0.3   # Alexandridis, Antypas & Travlos (2017, JCF) - modern flip
            confidence = 0.5
        elif announcement_type == 'partnership':
            car = 1.2   # Chan, Kensinger, Keown & Martin (1997, JFE); recent alliance work confirms
            confidence = 0.5
        elif announcement_type == 'restructuring':
            car = -0.8  # John & Ofek (1995, JFE)
            confidence = 0.4
        else:
            car = announcement_sentiment * 2.0
            confidence = 0.3

        # Trust and coverage dial impacts (small relative to one-time CAR)
        trust_dial_impact = (car / 100.0) * 0.5  # half of CAR translates to persistent trust
        coverage_dial_impact = 0.005  # any announcement = small visibility bump

        impact['irci_impact'] = (trust_dial_impact * trust_weight) + (coverage_dial_impact * coverage_weight)
        impact['affected_dials'] = ['Trust', 'Coverage']
        impact['confidence'] = confidence
        impact['car_estimate'] = car

    elif event_type == 'dividend_announcement':
        # Dividend signaling: Michaely, Thaler & Womack (1995, JF) original. Modern replication
        # work confirms asymmetric punishment: cuts ≈ -3 to -5%; omissions ≈ -7%; initiations +3-4%.
        # Grullon, Michaely & Swaminathan (2002, JB) on dividend changes still holds in modern data.
        trust_weight = weights.get('sentiment', 0.15)

        dividend_change = event_metadata.get('dividend_change_pct', 0.0)
        is_initiation = event_metadata.get('is_initiation', False)

        if is_initiation:
            trust_dial_impact = 0.015
            impact['car_estimate'] = 3.4   # Michaely, Thaler & Womack (1995, JF)
            impact['confidence'] = 0.6
        elif dividend_change > 0:
            trust_dial_impact = 0.005
            impact['car_estimate'] = 1.0   # Grullon, Michaely & Swaminathan (2002, JB)
            impact['confidence'] = 0.5
        elif dividend_change < 0:
            trust_dial_impact = -0.012
            impact['car_estimate'] = -5.0  # Modern cuts ≈ -3-5%; this is a substantial cut
            impact['confidence'] = 0.6
        else:
            trust_dial_impact = 0.002
            impact['car_estimate'] = 0.0
            impact['confidence'] = 0.3

        impact['irci_impact'] = trust_dial_impact * trust_weight
        impact['affected_dials'] = ['Trust']

    elif event_type == 'buyback_announcement':
        # Manconi, Peyer & Vermaelen (2019, JFQA) 9,000+ announcements 31 countries:
        # short-window CAR ≈ +1.25-1.4% in U.S. open-market data. Tones down the original
        # Ikenberry-Lakonishok-Vermaelen (1995, JFE) +3.5% — magnitude shrinks in modern data
        # but the signal persists, especially for undervalued and well-governed firms.
        trust_weight = weights.get('sentiment', 0.15)

        trust_dial_impact = 0.005  # +0.5% (capital allocation confidence)
        impact['irci_impact'] = trust_dial_impact * trust_weight
        impact['affected_dials'] = ['Trust']
        impact['confidence'] = 0.6
        impact['car_estimate'] = 1.5  # Manconi, Peyer & Vermaelen (2019, JFQA)

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
        # Srinivasan & Hanssens (2024, J. Accounting Research) on US data 1977-2018: positive
        # year-of-spend abnormal return, but NEGATIVE drift in subsequent year concentrated in
        # competitive industries. Updates Joshi & Hanssens (2010, J. Marketing) — short-term
        # lift confirmed; long-horizon effect now appears competition-conditional, not uniform.
        liquidity_weight = weights.get('liquidity', 0.35)
        coverage_weight = weights.get('coverage', 0.15)

        liquidity_dial_impact = 0.008  # +0.8% to liquidity (breadth-of-ownership channel)
        coverage_dial_impact = 0.005   # +0.5% to coverage (investor awareness)
        impact['irci_impact'] = (liquidity_dial_impact * liquidity_weight) + (coverage_dial_impact * coverage_weight)
        impact['affected_dials'] = ['Liquidity', 'Coverage']
        impact['confidence'] = 0.4  # Competition-conditional per Srinivasan & Hanssens (2024)
        impact['car_estimate'] = 0.8  # Short-term lift; may reverse in competitive industries

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
        # Bushee, Jung & Miller (2011, JAR) original ~+1% conference CAR. Bushee, Taylor & Zhu
        # (2020) "The Dark Side of Investor Conferences" document an asymmetry: "hyping" firms
        # show +1.5% pre-conference CAR but -3.0% post-conference drift over 180 days.
        # Non-deal roadshow path uses Bradley, Jame & Williams (2022, JF) downstream.
        coverage_weight = weights.get('coverage', 0.15)
        trust_weight = weights.get('sentiment', 0.15)

        coverage_dial_impact = 0.008   # +0.8% to coverage (analyst/investor exposure)
        trust_dial_impact = 0.004      # +0.4% to trust (management credibility)
        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Trust']
        impact['confidence'] = 0.4  # Lower confidence due to post-conference drift asymmetry
        impact['car_estimate'] = 0.8  # Bushee, Jung & Miller (2011); short-window only

    elif event_type == 'analyst_coverage_initiation':
        # Li & You (2015, Review of Accounting Studies): 5-day CAR around coverage initiation
        # ≈ +82 bps. Extends Irvine (2003, JAE) which found +1.02% in earlier data.
        # Chowdhury et al. (2021, A&F) on abnormal coverage long-short generates ~1.36%/mo alpha.
        coverage_weight = weights.get('coverage', 0.15)
        liquidity_weight = weights.get('liquidity', 0.35)
        trust_weight = weights.get('sentiment', 0.15)

        coverage_dial_impact = 0.012   # +1.2% to coverage (new analyst following)
        liquidity_dial_impact = 0.008  # +0.8% to liquidity (institutional interest)
        trust_dial_impact = 0.005      # +0.5% to trust (third-party validation)
        impact['irci_impact'] = (coverage_dial_impact * coverage_weight) + \
                               (liquidity_dial_impact * liquidity_weight) + \
                               (trust_dial_impact * trust_weight)
        impact['affected_dials'] = ['Coverage', 'Liquidity', 'Trust']
        impact['confidence'] = 0.7
        impact['car_estimate'] = 0.8  # Li & You (2015, RAS) — modern 5-day CAR around initiation

    # Event-window dollar impact: literature-direct (CAR × current EV).
    # This is what published event-study research says happens in the days around the event,
    # independent of any IRCI dial-mediated quality lift.
    if current_ev > 0 and impact.get('car_estimate', 0.0) != 0.0:
        impact['event_window_dollar'] = (impact['car_estimate'] / 100.0) * current_ev

    # Persistent IRCI-mediated dollar impact: dial nudge × $/IRCI point.
    # This represents the slow-burn quality lift attributable to this IR action,
    # NOT the announcement-effect CAR (which goes in event_window_dollar above).
    if impact['irci_impact'] != 0:
        if company_dollar_per_irci_pt is not None and company_dollar_per_irci_pt > 0:
            impact['dollar_impact'] = impact['irci_impact'] * company_dollar_per_irci_pt
        elif current_ev > 0:
            # Fallback when $/IRCI point is unavailable: conservative 0.1% of EV per IRCI point
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
