"""
IRCI Dial Insights Module

Provides advanced analysis functions for understanding:
1. Dollar value implications of IRCI scores
2. Dial contribution breakdown
3. Optimal weight recommendations
"""

import pandas as pd
import numpy as np
from typing import Optional


def compute_dollar_value_per_irci_point(
    df_composite: pd.DataFrame,
    df_valuation: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate dollar value per IRCI point for the peer group.

    This metric reveals: "How much enterprise value change corresponds to
    a 1-point improvement in IRCI composite score?"

    Args:
        df_composite: Composite scores with irci_composite_pct
        df_valuation: Valuation data with enterprise_value, ev_to_ebitda

    Returns:
        DataFrame with columns:
        - ticker
        - enterprise_value
        - irci_composite_pct
        - ev_per_irci_point: Dollar value per 1% IRCI improvement
        - irci_gap_to_top: Points below top performer
        - market_cap_gap: Estimated $ gap to reach top performer's IRCI
    """
    # Merge composite and valuation data
    df = df_composite[['ticker', 'quarter_end', 'irci_composite_pct']].merge(
        df_valuation[['ticker', 'as_of', 'enterprise_value', 'ev_to_ebitda']],
        left_on=['ticker'],
        right_on=['ticker'],
        how='inner'
    )

    # Calculate peer group statistics
    peer_max_irci = df['irci_composite_pct'].max()
    peer_mean_ev = df['enterprise_value'].mean()
    peer_std_ev = df['enterprise_value'].std()

    # Dollar value per IRCI point
    # Method 1: Group-level metric using spread of EV vs IRCI across peers
    # If IRCI ranges 40-80 (40 points) and EV ranges $10B-$50B ($40B)
    # Then ~$1B per IRCI point

    irci_range = df['irci_composite_pct'].max() - df['irci_composite_pct'].min()
    ev_range = df['enterprise_value'].max() - df['enterprise_value'].min()

    if irci_range > 1.0:  # Avoid division by very small numbers
        group_dollars_per_point = ev_range / irci_range
    else:
        group_dollars_per_point = 0.0

    # Method 2: Company-specific $/IRCI point
    # Each company gets a unique value based on their EV and position

    # Simple linear regression: EV ~ IRCI for the peer group
    from scipy import stats
    if len(df) >= 3 and irci_range > 1.0:
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            df['irci_composite_pct'],
            df['enterprise_value']
        )
        # The peer group regression slope (used for reference)
        peer_regression_slope = abs(slope)
        df['regression_r2'] = r_value ** 2

        # Company-specific $/IRCI point calculation
        # Approach: Scale the regression slope by company's EV relative to predicted EV
        # This accounts for company size and position relative to trend
        df['predicted_ev'] = slope * df['irci_composite_pct'] + intercept
        df['ev_to_predicted_ratio'] = df['enterprise_value'] / (df['predicted_ev'] + 1e9)

        # Company-specific $/IRCI is the regression slope scaled by company size
        # Companies with higher EV should have higher $/IRCI point
        # Use the company's actual EV as the baseline, scaled by peer group sensitivity
        irci_std = df['irci_composite_pct'].std()
        if irci_std > 0:
            # Sensitivity: how much EV changes per IRCI point for this company
            # Based on company's EV and the peer group's IRCI volatility
            df['company_$/irci_pt'] = df['enterprise_value'] * (peer_regression_slope / peer_mean_ev)
        else:
            df['company_$/irci_pt'] = peer_regression_slope

    else:
        # Fallback: proportional to company EV
        df['regression_r2'] = 0.0
        # Each company's $/IRCI point proportional to their EV
        if peer_mean_ev > 0:
            df['company_$/irci_pt'] = df['enterprise_value'] * (group_dollars_per_point / peer_mean_ev)
        else:
            df['company_$/irci_pt'] = group_dollars_per_point

    # Per-company gap metrics
    df['irci_gap_to_top'] = peer_max_irci - df['irci_composite_pct']
    df['market_cap_gap_regression'] = df['irci_gap_to_top'] * df['company_$/irci_pt']
    df['market_cap_gap_group'] = df['irci_gap_to_top'] * group_dollars_per_point

    # Valuation efficiency: How much EV per IRCI point for this specific company?
    # Companies with low EV but high IRCI are "efficient"
    df['company_ev_efficiency'] = df['enterprise_value'] / (df['irci_composite_pct'] + 1)

    # Add peer group summary statistics
    df['peer_group_ev_mean'] = peer_mean_ev
    df['peer_group_ev_std'] = peer_std_ev
    df['peer_group_$/irci_pt'] = group_dollars_per_point

    return df[[
        'ticker',
        'enterprise_value',
        'irci_composite_pct',
        'company_$/irci_pt',
        'peer_group_$/irci_pt',
        'irci_gap_to_top',
        'market_cap_gap_regression',
        'market_cap_gap_group',
        'company_ev_efficiency',
        'regression_r2'
    ]]


def compute_dial_contribution(
    df_composite: pd.DataFrame,
    weights: Optional[dict[str, float]] = None
) -> pd.DataFrame:
    """
    Break down composite score into absolute contribution of each dial.

    This reveals which dials are driving the composite score and identifies
    the optimal weight allocation based on actual peer group characteristics.

    Args:
        df_composite: From irci_composite() with columns:
          valuation_pct, liquidity_pct, coverage_pct, sentiment_pct, irci_composite_pct
        weights: e.g., {'valuation': 0.35, 'liquidity': 0.35, 'coverage': 0.15, 'sentiment': 0.15}

    Returns:
        DataFrame with original columns plus:
          - val_contrib_abs, liq_contrib_abs, cov_contrib_abs, sent_contrib_abs
            (absolute contribution in 0-100 scale)
          - val_contrib_pct, liq_contrib_pct, cov_contrib_pct, sent_contrib_pct
            (% of total composite)
          - dominant_dial (which dial contributes most)
          - weakest_dial (which dial is lowest)
          - weakest_dial_score
    """
    if weights is None:
        weights = {
            'valuation': 0.35,
            'liquidity': 0.35,
            'coverage': 0.15,
            'sentiment': 0.15
        }

    df = df_composite.copy()

    # Absolute contributions (weighted scores)
    df['val_contrib_abs'] = df['valuation_pct'].fillna(0) * weights['valuation']
    df['liq_contrib_abs'] = df['liquidity_pct'].fillna(0) * weights['liquidity']
    df['cov_contrib_abs'] = df['coverage_pct'].fillna(0) * weights['coverage']
    df['sent_contrib_abs'] = df['sentiment_pct'].fillna(0) * weights['sentiment']

    # Total weighted (should equal composite, but recompute for safety)
    contrib_cols = ['val_contrib_abs', 'liq_contrib_abs', 'cov_contrib_abs', 'sent_contrib_abs']
    total_contrib = df[contrib_cols].sum(axis=1)

    # Percentage of composite (what % of final score came from each dial)
    df['val_contrib_pct'] = (df['val_contrib_abs'] / (total_contrib + 0.001)) * 100.0
    df['liq_contrib_pct'] = (df['liq_contrib_abs'] / (total_contrib + 0.001)) * 100.0
    df['cov_contrib_pct'] = (df['cov_contrib_abs'] / (total_contrib + 0.001)) * 100.0
    df['sent_contrib_pct'] = (df['sent_contrib_abs'] / (total_contrib + 0.001)) * 100.0

    # Identify which dial is "dominant" (contributes most absolute points)
    dial_labels = ['Valuation', 'Liquidity', 'Coverage', 'Trust']
    df['dominant_dial'] = df[contrib_cols].idxmax(axis=1).map(
        dict(zip(contrib_cols, dial_labels))
    )

    # Weakness analysis: which dial is pulling down the score?
    weakness_cols = ['valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']
    df['weakest_dial'] = df[weakness_cols].idxmin(axis=1).map(
        dict(zip(weakness_cols, dial_labels))
    )
    df['weakest_dial_score'] = df[weakness_cols].min(axis=1)

    # Calculate improvement potential per dial
    # If we improved the weakest dial to match the strongest, how much would composite increase?
    df['strongest_dial_score'] = df[weakness_cols].max(axis=1)
    df['improvement_potential'] = (df['strongest_dial_score'] - df['weakest_dial_score']) * min(weights.values())

    return df


def recommend_optimal_weights(
    df_composite: pd.DataFrame,
    current_weights: Optional[dict[str, float]] = None
) -> dict:
    """
    Analyze the peer group to recommend optimal dial weights.

    Strategy: Dials with higher variance across peers should get more weight,
    as they better differentiate between companies.

    Args:
        df_composite: Composite DataFrame with all dial scores
        current_weights: Current weight allocation

    Returns:
        Dictionary with:
        - recommended_weights: Suggested weight allocation
        - variance_analysis: Variance of each dial across peer group
        - current_vs_recommended: Comparison
    """
    if current_weights is None:
        current_weights = {
            'valuation': 0.35,
            'liquidity': 0.35,
            'coverage': 0.15,
            'sentiment': 0.15
        }

    dial_cols = ['valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']

    # Calculate variance (spread) of each dial across peers
    variances = df_composite[dial_cols].var()

    # Also calculate coefficient of variation (CV = std / mean)
    # This normalizes for different mean values
    means = df_composite[dial_cols].mean()
    stds = df_composite[dial_cols].std()
    cv = stds / (means + 1)  # Add 1 to avoid division by zero

    # Calculate data availability (how many peers have data for each dial)
    availability = df_composite[dial_cols].notna().sum() / len(df_composite)

    # Recommended weights based on variance and availability
    # Higher variance + high availability = more discriminating = higher weight
    discriminating_power = variances * availability
    total_power = discriminating_power.sum()

    if total_power > 0:
        recommended_raw = discriminating_power / total_power
    else:
        recommended_raw = pd.Series([0.25, 0.25, 0.25, 0.25], index=dial_cols)

    # Convert to dictionary with friendly names
    recommended_weights = {
        'valuation': float(recommended_raw['valuation_pct']),
        'liquidity': float(recommended_raw['liquidity_pct']),
        'coverage': float(recommended_raw['coverage_pct']),
        'sentiment': float(recommended_raw['sentiment_pct'])
    }

    # Variance analysis for reporting
    variance_analysis = {
        'valuation': {
            'variance': float(variances['valuation_pct']),
            'std': float(stds['valuation_pct']),
            'mean': float(means['valuation_pct']),
            'cv': float(cv['valuation_pct']),
            'availability': float(availability['valuation_pct'])
        },
        'liquidity': {
            'variance': float(variances['liquidity_pct']),
            'std': float(stds['liquidity_pct']),
            'mean': float(means['liquidity_pct']),
            'cv': float(cv['liquidity_pct']),
            'availability': float(availability['liquidity_pct'])
        },
        'coverage': {
            'variance': float(variances['coverage_pct']),
            'std': float(stds['coverage_pct']),
            'mean': float(means['coverage_pct']),
            'cv': float(cv['coverage_pct']),
            'availability': float(availability['coverage_pct'])
        },
        'sentiment': {
            'variance': float(variances['sentiment_pct']),
            'std': float(stds['sentiment_pct']),
            'mean': float(means['sentiment_pct']),
            'cv': float(cv['sentiment_pct']),
            'availability': float(availability['sentiment_pct'])
        }
    }

    return {
        'recommended_weights': recommended_weights,
        'current_weights': current_weights,
        'variance_analysis': variance_analysis,
        'discriminating_power': {
            'valuation': float(discriminating_power['valuation_pct']),
            'liquidity': float(discriminating_power['liquidity_pct']),
            'coverage': float(discriminating_power['coverage_pct']),
            'sentiment': float(discriminating_power['sentiment_pct'])
        }
    }
