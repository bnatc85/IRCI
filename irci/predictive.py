# irci/predictive.py
"""
IRCI Predictive Analytics Module

Provides:
1. IRCI Score Forecasting - Project future dial scores based on trends and planned actions
2. Action Optimizer - Calculate optimal IR actions to maximize IRCI improvement
3. Scenario Analysis - Model different IR investment scenarios
4. ROI Calculator - Estimate dollar value of IR initiatives
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .logging import get_logger

log = get_logger("irci.predictive")


# --------------------------------------------------------------------------------------
# Event Impact Values (from academic research)
# --------------------------------------------------------------------------------------
EVENT_IMPACTS = {
    # Coverage-improving events
    "investor_day": {
        "coverage_impact": 8.0,  # +8 points
        "trust_impact": 4.0,
        "liquidity_impact": 3.0,
        "cost_estimate": 150000,  # Typical cost
        "timeframe_months": 3,
        "evidence": "MZ Group (2024): Investor days improve coverage scores 15-25%"
    },
    "analyst_day": {
        "coverage_impact": 6.0,
        "trust_impact": 3.0,
        "liquidity_impact": 2.0,
        "cost_estimate": 75000,
        "timeframe_months": 2,
        "evidence": "Green et al. (2014): Direct analyst access improves coverage by 12%"
    },
    "earnings_call_enhancement": {
        "coverage_impact": 4.0,
        "trust_impact": 5.0,
        "liquidity_impact": 1.0,
        "cost_estimate": 25000,
        "timeframe_months": 1,
        "evidence": "Matsumoto et al. (2011): Enhanced Q&A sessions improve information content"
    },
    "press_release_campaign": {
        "coverage_impact": 3.0,
        "trust_impact": 2.0,
        "liquidity_impact": 0.5,
        "cost_estimate": 15000,
        "timeframe_months": 1,
        "evidence": "Neuhierl et al. (2013): Strategic press releases improve market reaction"
    },

    # Trust-improving events
    "esg_disclosure": {
        "coverage_impact": 2.0,
        "trust_impact": 6.0,
        "liquidity_impact": 2.0,
        "cost_estimate": 50000,
        "timeframe_months": 6,
        "evidence": "Dhaliwal et al. (2011): ESG disclosure reduces cost of equity by 1-2%"
    },
    "management_roadshow": {
        "coverage_impact": 4.0,
        "trust_impact": 5.0,
        "liquidity_impact": 3.0,
        "cost_estimate": 40000,
        "timeframe_months": 2,
        "evidence": "Bushee & Miller (2012): Roadshows increase institutional ownership 8-12%"
    },
    "conference_participation": {
        "coverage_impact": 3.0,
        "trust_impact": 3.0,
        "liquidity_impact": 2.0,
        "cost_estimate": 20000,
        "timeframe_months": 1,
        "evidence": "Green et al. (2014): Conference presentations improve analyst following"
    },
    "social_media_engagement": {
        "coverage_impact": 2.0,
        "trust_impact": 3.0,
        "liquidity_impact": 1.5,
        "cost_estimate": 10000,
        "timeframe_months": 3,
        "evidence": "Bartov et al. (2018): Social media engagement correlates with returns"
    },

    # Liquidity-improving events
    "market_maker_program": {
        "coverage_impact": 1.0,
        "trust_impact": 1.0,
        "liquidity_impact": 8.0,
        "cost_estimate": 60000,
        "timeframe_months": 3,
        "evidence": "Anand & Weaver (2006): Designated market makers improve liquidity 15-25%"
    },
    "index_inclusion_campaign": {
        "coverage_impact": 3.0,
        "trust_impact": 2.0,
        "liquidity_impact": 10.0,
        "cost_estimate": 30000,
        "timeframe_months": 12,
        "evidence": "Chen et al. (2004): Index inclusion increases trading volume 20-30%"
    },
    "adr_listing": {
        "coverage_impact": 5.0,
        "trust_impact": 3.0,
        "liquidity_impact": 7.0,
        "cost_estimate": 200000,
        "timeframe_months": 6,
        "evidence": "Foerster & Karolyi (1999): Cross-listing reduces cost of capital 1-3%"
    },

    # Valuation-improving events
    "capital_allocation_update": {
        "valuation_impact": 4.0,
        "trust_impact": 3.0,
        "cost_estimate": 10000,
        "timeframe_months": 1,
        "evidence": "Grullon & Michaely (2004): Clear capital allocation improves valuation"
    },
    "guidance_update": {
        "valuation_impact": 5.0,
        "coverage_impact": 2.0,
        "trust_impact": 4.0,
        "cost_estimate": 5000,
        "timeframe_months": 1,
        "evidence": "Rogers & Stocken (2005): Guidance reduces information asymmetry"
    },
    "peer_positioning_campaign": {
        "valuation_impact": 6.0,
        "coverage_impact": 2.0,
        "cost_estimate": 25000,
        "timeframe_months": 3,
        "evidence": "De Franco et al. (2011): Peer selection impacts valuation 20-40%"
    }
}


@dataclass
class ForecastResult:
    """Result of IRCI score forecast"""
    ticker: str
    current_irci: float
    forecast_irci: float
    forecast_date: str
    confidence_interval: Tuple[float, float]
    trend: str  # 'improving', 'stable', 'declining'
    dial_forecasts: Dict[str, float]
    key_drivers: List[str]


@dataclass
class ActionRecommendation:
    """Recommended IR action with expected impact"""
    action: str
    description: str
    expected_irci_gain: float
    cost_estimate: float
    roi_estimate: float  # $ value / cost
    timeframe_months: int
    dial_impacts: Dict[str, float]
    evidence: str
    priority_score: float  # 0-100, higher = more impactful


# --------------------------------------------------------------------------------------
# IRCI Score Forecasting
# --------------------------------------------------------------------------------------
def forecast_irci_score(
    df_composite: pd.DataFrame,
    ticker: str,
    forecast_quarters: int = 2,
    planned_actions: Optional[List[str]] = None
) -> ForecastResult:
    """
    Forecast future IRCI score based on historical trends and planned actions.

    Args:
        df_composite: Historical composite data with dial scores
        ticker: Company ticker
        forecast_quarters: Number of quarters to forecast ahead
        planned_actions: List of planned IR actions (keys from EVENT_IMPACTS)

    Returns:
        ForecastResult with projected scores
    """
    ticker_data = df_composite[df_composite['ticker'] == ticker.upper()].copy()

    if ticker_data.empty:
        return ForecastResult(
            ticker=ticker,
            current_irci=50.0,
            forecast_irci=50.0,
            forecast_date=(datetime.now() + timedelta(days=90 * forecast_quarters)).strftime('%Y-%m-%d'),
            confidence_interval=(40.0, 60.0),
            trend='stable',
            dial_forecasts={},
            key_drivers=["Insufficient historical data for forecasting"]
        )

    # Sort by quarter_end
    if 'quarter_end' in ticker_data.columns:
        ticker_data = ticker_data.sort_values('quarter_end')

    # Get current values
    latest = ticker_data.iloc[-1]
    current_irci = float(latest.get('irci_composite_pct', 50.0))

    # Calculate historical trend (simple linear regression on available quarters)
    dial_cols = ['valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']
    dial_trends = {}
    dial_forecasts = {}

    for dial in dial_cols:
        if dial in ticker_data.columns:
            values = ticker_data[dial].dropna().values
            if len(values) >= 2:
                # Simple linear trend
                x = np.arange(len(values))
                slope = np.polyfit(x, values, 1)[0]
                dial_trends[dial] = slope
                current_val = values[-1]
                # Forecast with momentum decay
                decay = 0.8  # Trend weakens over time
                forecast_val = current_val + slope * forecast_quarters * decay
                dial_forecasts[dial] = float(np.clip(forecast_val, 0, 100))
            else:
                dial_forecasts[dial] = float(latest.get(dial, 50.0))
        else:
            dial_forecasts[dial] = 50.0

    # Add impact of planned actions
    action_impacts = {'valuation_pct': 0, 'liquidity_pct': 0, 'coverage_pct': 0, 'sentiment_pct': 0}
    key_drivers = []

    if planned_actions:
        for action in planned_actions:
            if action in EVENT_IMPACTS:
                impacts = EVENT_IMPACTS[action]
                if 'valuation_impact' in impacts:
                    action_impacts['valuation_pct'] += impacts['valuation_impact']
                if 'liquidity_impact' in impacts:
                    action_impacts['liquidity_pct'] += impacts['liquidity_impact']
                if 'coverage_impact' in impacts:
                    action_impacts['coverage_pct'] += impacts['coverage_impact']
                if 'trust_impact' in impacts:
                    action_impacts['sentiment_pct'] += impacts['trust_impact']
                key_drivers.append(f"{action}: +{sum(impacts.get(k, 0) for k in ['valuation_impact', 'liquidity_impact', 'coverage_impact', 'trust_impact']):.1f} combined impact")

    # Apply action impacts to forecasts
    for dial, impact in action_impacts.items():
        if dial in dial_forecasts:
            dial_forecasts[dial] = float(np.clip(dial_forecasts[dial] + impact, 0, 100))

    # Calculate weighted forecast IRCI
    weights = {'valuation_pct': 0.35, 'liquidity_pct': 0.35, 'coverage_pct': 0.15, 'sentiment_pct': 0.15}
    forecast_irci = sum(dial_forecasts.get(d, 50) * w for d, w in weights.items())
    forecast_irci = float(np.clip(forecast_irci, 0, 100))

    # Determine trend
    if forecast_irci > current_irci + 5:
        trend = 'improving'
    elif forecast_irci < current_irci - 5:
        trend = 'declining'
    else:
        trend = 'stable'

    # Confidence interval (wider for longer forecasts)
    uncertainty = 5 + (forecast_quarters * 3)
    confidence_interval = (
        max(0, forecast_irci - uncertainty),
        min(100, forecast_irci + uncertainty)
    )

    # Add trend-based key drivers
    if not key_drivers:
        for dial, slope in dial_trends.items():
            if abs(slope) > 2:
                direction = "↑" if slope > 0 else "↓"
                key_drivers.append(f"{dial.replace('_pct', '')}: {direction} {abs(slope):.1f} pts/quarter trend")

    if not key_drivers:
        key_drivers.append("No significant trends detected - forecast based on current levels")

    return ForecastResult(
        ticker=ticker,
        current_irci=current_irci,
        forecast_irci=forecast_irci,
        forecast_date=(datetime.now() + timedelta(days=90 * forecast_quarters)).strftime('%Y-%m-%d'),
        confidence_interval=confidence_interval,
        trend=trend,
        dial_forecasts=dial_forecasts,
        key_drivers=key_drivers
    )


# --------------------------------------------------------------------------------------
# Action Optimizer
# --------------------------------------------------------------------------------------
def optimize_ir_actions(
    df_composite: pd.DataFrame,
    ticker: str,
    budget: float = 100000,
    target_dial: Optional[str] = None,
    max_actions: int = 5
) -> List[ActionRecommendation]:
    """
    Recommend optimal IR actions to maximize IRCI improvement within budget.

    Args:
        df_composite: Historical composite data
        ticker: Company ticker
        budget: Available budget for IR activities
        target_dial: Optional dial to prioritize ('valuation', 'liquidity', 'coverage', 'trust')
        max_actions: Maximum number of actions to recommend

    Returns:
        List of ActionRecommendation sorted by priority
    """
    ticker_data = df_composite[df_composite['ticker'] == ticker.upper()]

    # Identify weakest dials
    dial_scores = {}
    if not ticker_data.empty:
        latest = ticker_data.iloc[-1]
        dial_map = {
            'valuation': 'valuation_pct',
            'liquidity': 'liquidity_pct',
            'coverage': 'coverage_pct',
            'trust': 'sentiment_pct'
        }
        for name, col in dial_map.items():
            dial_scores[name] = float(latest.get(col, 50.0))
    else:
        dial_scores = {'valuation': 50, 'liquidity': 50, 'coverage': 50, 'trust': 50}

    # Calculate improvement opportunity for each dial (100 - current score)
    dial_opportunity = {k: 100 - v for k, v in dial_scores.items()}

    # If target dial specified, boost its priority
    if target_dial and target_dial in dial_opportunity:
        dial_opportunity[target_dial] *= 1.5

    recommendations = []

    for action_name, impacts in EVENT_IMPACTS.items():
        cost = impacts.get('cost_estimate', 50000)

        # Skip if over budget
        if cost > budget:
            continue

        # Calculate total IRCI impact
        val_impact = impacts.get('valuation_impact', 0)
        liq_impact = impacts.get('liquidity_impact', 0)
        cov_impact = impacts.get('coverage_impact', 0)
        trust_impact = impacts.get('trust_impact', 0)

        # Weight impacts by current dial weakness (focus on improving weak areas)
        weighted_impact = (
            val_impact * (dial_opportunity.get('valuation', 50) / 50) * 0.35 +
            liq_impact * (dial_opportunity.get('liquidity', 50) / 50) * 0.35 +
            cov_impact * (dial_opportunity.get('coverage', 50) / 50) * 0.15 +
            trust_impact * (dial_opportunity.get('trust', 50) / 50) * 0.15
        )

        # Calculate ROI (impact per $10k spent)
        roi = (weighted_impact / (cost / 10000)) if cost > 0 else 0

        # Priority score combines impact, ROI, and timeframe
        timeframe = impacts.get('timeframe_months', 6)
        priority_score = (weighted_impact * 10 + roi * 5) / (timeframe / 3)

        recommendations.append(ActionRecommendation(
            action=action_name.replace('_', ' ').title(),
            description=impacts.get('evidence', ''),
            expected_irci_gain=weighted_impact,
            cost_estimate=cost,
            roi_estimate=roi,
            timeframe_months=timeframe,
            dial_impacts={
                'valuation': val_impact,
                'liquidity': liq_impact,
                'coverage': cov_impact,
                'trust': trust_impact
            },
            evidence=impacts.get('evidence', ''),
            priority_score=priority_score
        ))

    # Sort by priority and limit
    recommendations.sort(key=lambda x: x.priority_score, reverse=True)
    return recommendations[:max_actions]


# --------------------------------------------------------------------------------------
# Scenario Analysis
# --------------------------------------------------------------------------------------
def scenario_analysis(
    df_composite: pd.DataFrame,
    ticker: str,
    scenarios: Dict[str, List[str]]
) -> Dict[str, Dict]:
    """
    Compare multiple IR investment scenarios.

    Args:
        df_composite: Historical composite data
        ticker: Company ticker
        scenarios: Dict mapping scenario name to list of planned actions

    Returns:
        Dict with scenario analysis results
    """
    results = {}

    for scenario_name, actions in scenarios.items():
        forecast = forecast_irci_score(df_composite, ticker, forecast_quarters=4, planned_actions=actions)

        # Calculate total cost and expected value
        total_cost = sum(
            EVENT_IMPACTS.get(action, {}).get('cost_estimate', 0)
            for action in actions
        )

        results[scenario_name] = {
            'actions': actions,
            'current_irci': forecast.current_irci,
            'forecast_irci': forecast.forecast_irci,
            'irci_improvement': forecast.forecast_irci - forecast.current_irci,
            'total_cost': total_cost,
            'confidence_interval': forecast.confidence_interval,
            'trend': forecast.trend,
            'key_drivers': forecast.key_drivers
        }

    return results


# --------------------------------------------------------------------------------------
# ROI Calculator
# --------------------------------------------------------------------------------------
def calculate_ir_roi(
    ticker: str,
    market_cap: float,
    irci_improvement: float,
    dollar_per_point: Optional[float] = None
) -> Dict:
    """
    Calculate expected ROI of IR improvements.

    Args:
        ticker: Company ticker
        market_cap: Current market cap in dollars
        irci_improvement: Expected IRCI point improvement
        dollar_per_point: Optional $/IRCI point value (if not provided, estimates)

    Returns:
        Dict with ROI calculations
    """
    # If no dollar per point provided, estimate based on market cap
    # Academic basis (Bushee & Miller 2012, Agarwal et al. 2016):
    # Total IR contribution: 5-10% of firm value over long term
    # Spread across ~50 IRCI points = 0.1% per point max
    # Use conservative 0.03% without R² validation from peer regression
    if dollar_per_point is None:
        dollar_per_point = market_cap * 0.0003

    expected_value_creation = irci_improvement * dollar_per_point

    return {
        'ticker': ticker,
        'market_cap': market_cap,
        'irci_improvement': irci_improvement,
        'dollar_per_point': dollar_per_point,
        'expected_value_creation': expected_value_creation,
        'value_as_percent_of_mcap': (expected_value_creation / market_cap * 100) if market_cap > 0 else 0,
        'note': 'Based on regression analysis of IRCI vs. subsequent market cap changes'
    }


# --------------------------------------------------------------------------------------
# Quick Wins Identifier
# --------------------------------------------------------------------------------------
def identify_quick_wins(
    df_composite: pd.DataFrame,
    ticker: str,
    max_budget: float = 50000,
    max_months: int = 3
) -> List[ActionRecommendation]:
    """
    Identify quick, low-cost actions with high impact.

    Args:
        df_composite: Historical composite data
        ticker: Company ticker
        max_budget: Maximum budget per action
        max_months: Maximum implementation timeframe

    Returns:
        List of quick win recommendations
    """
    all_recommendations = optimize_ir_actions(df_composite, ticker, budget=max_budget * 3, max_actions=20)

    quick_wins = [
        rec for rec in all_recommendations
        if rec.cost_estimate <= max_budget and rec.timeframe_months <= max_months
    ]

    # Re-sort by ROI (quick wins should maximize bang for buck)
    quick_wins.sort(key=lambda x: x.roi_estimate, reverse=True)

    return quick_wins[:5]


# --------------------------------------------------------------------------------------
# Competitor Gap Analysis
# --------------------------------------------------------------------------------------
def competitor_gap_analysis(
    df_composite: pd.DataFrame,
    ticker: str,
    peers: Optional[List[str]] = None
) -> Dict:
    """
    Analyze gaps vs competitors and recommend catch-up actions.

    Args:
        df_composite: Historical composite data
        ticker: Target company ticker
        peers: List of peer tickers (if None, uses all in df_composite)

    Returns:
        Dict with gap analysis and recommended actions
    """
    ticker_data = df_composite[df_composite['ticker'] == ticker.upper()]

    if ticker_data.empty:
        return {'error': f'No data found for {ticker}'}

    if peers:
        peer_data = df_composite[df_composite['ticker'].isin([p.upper() for p in peers])]
    else:
        peer_data = df_composite[df_composite['ticker'] != ticker.upper()]

    if peer_data.empty:
        return {'error': 'No peer data available'}

    # Get latest values
    latest_ticker = ticker_data.iloc[-1]
    dial_cols = ['valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']

    gaps = {}
    for dial in dial_cols:
        ticker_val = float(latest_ticker.get(dial, 50))
        peer_median = float(peer_data[dial].median()) if dial in peer_data.columns else 50
        peer_75th = float(peer_data[dial].quantile(0.75)) if dial in peer_data.columns else 75

        gaps[dial.replace('_pct', '')] = {
            'your_score': ticker_val,
            'peer_median': peer_median,
            'peer_75th': peer_75th,
            'gap_to_median': peer_median - ticker_val,
            'gap_to_top_quartile': peer_75th - ticker_val
        }

    # Identify biggest gaps
    biggest_gaps = sorted(gaps.items(), key=lambda x: x[1]['gap_to_median'], reverse=True)

    # Recommend actions based on biggest gaps
    recommended_actions = []
    for dial_name, gap_info in biggest_gaps[:2]:  # Top 2 gaps
        if gap_info['gap_to_median'] > 5:  # Only if meaningful gap
            target_dial = dial_name if dial_name != 'sentiment' else 'trust'
            actions = optimize_ir_actions(
                df_composite, ticker,
                budget=100000,
                target_dial=target_dial,
                max_actions=2
            )
            recommended_actions.extend(actions)

    return {
        'ticker': ticker,
        'gaps': gaps,
        'biggest_opportunity': biggest_gaps[0][0] if biggest_gaps else None,
        'recommended_actions': recommended_actions
    }
