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


# Literature-anchored elasticity: ~0.12% of EV per IRCI percentile.
#
# Derivation:
#   Botosan (1997), Accounting Review: 1-unit higher disclosure-quality score reduces
#     cost of equity by ~28 bps for low-analyst-following firms.
#   Botosan & Plumlee (2002), JAR: annual disclosure → ~100 bps cost-of-equity reduction.
#   Gordon growth: P/D = 1/(r-g). A 28 bps drop in r at r=9%, g=3% implies ~4.7% EV uplift.
#   Healy, Hutton & Palepu (1999), CAR: firms expanding disclosure show ~7% abnormal
#     stock return in expansion year with persistent valuation gain.
#
# IRCI mapping: only the Coverage dial + half of Trust map cleanly to Botosan's
# "disclosure quality" construct (~50% of the composite). So:
#   1 IRCI percentile ≈ 0.5 × (5/100) = 0.025 Botosan disclosure units
#                     ≈ 0.025 × 28 bps = 0.7 bps cost-of-equity reduction
#                     ≈ 0.0007 / 0.06 ≈ 0.117% EV uplift via Gordon growth
EV_ELASTICITY_PER_IRCI_PT = 0.0012   # headline: 0.12% of EV per IRCI point
EV_ELASTICITY_LOW = 0.0005           # conservative band (only Coverage dial)
EV_ELASTICITY_HIGH = 0.0025          # aggressive band (full Botosan applies)

# Healy, Hutton & Palepu (1999) cap: IR-attributable EV uplift maxes around 20%
# even for firms making the largest disclosure-quality leaps.
MAX_TOTAL_UPSIDE_FRACTION = 0.20


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
    # First check if df_valuation has the required columns
    required_cols = ['ticker', 'enterprise_value']
    missing_cols = [col for col in required_cols if col not in df_valuation.columns]
    if missing_cols:
        print(f"Warning: df_valuation missing columns: {missing_cols}")
        # Return empty dataframe with expected columns
        return pd.DataFrame(columns=[
            'ticker', 'enterprise_value', 'irci_composite_pct',
            'company_$/irci_pt', 'company_$/irci_pt_low', 'company_$/irci_pt_high',
            'peer_group_$/irci_pt', 'irci_gap_to_top',
            'market_cap_gap_regression', 'market_cap_gap_group',
            'company_ev_efficiency', 'regression_r2',
            'regression_slope_diagnostic', 'regression_p_value',
        ])

    # Select columns that exist in df_valuation
    val_cols = ['ticker', 'enterprise_value']
    if 'as_of' in df_valuation.columns:
        val_cols.append('as_of')
    if 'ev_to_ebitda' in df_valuation.columns:
        val_cols.append('ev_to_ebitda')

    df = df_composite[['ticker', 'quarter_end', 'irci_composite_pct']].merge(
        df_valuation[val_cols],
        on='ticker',
        how='inner'
    )

    # Filter out rows with NaN enterprise_value BEFORE any calculations
    df = df.dropna(subset=['enterprise_value', 'irci_composite_pct'])

    if df.empty:
        print("Warning: No valid enterprise_value data after merge and dropna")
        return pd.DataFrame(columns=[
            'ticker', 'enterprise_value', 'irci_composite_pct',
            'company_$/irci_pt', 'company_$/irci_pt_low', 'company_$/irci_pt_high',
            'peer_group_$/irci_pt', 'irci_gap_to_top',
            'market_cap_gap_regression', 'market_cap_gap_group',
            'company_ev_efficiency', 'regression_r2',
            'regression_slope_diagnostic', 'regression_p_value',
        ])

    # Peer group statistics
    peer_max_irci = df['irci_composite_pct'].max()
    peer_mean_ev = df['enterprise_value'].mean()
    peer_std_ev = df['enterprise_value'].std()

    # === HEADLINE $/IRCI POINT: literature elasticity (Botosan 1997 + Healy-Hutton-Palepu 1999) ===
    # Each company's $/IRCI point is derived from THEIR enterprise value × the cost-of-equity
    # elasticity from the disclosure-quality literature. This is out-of-sample, robust to
    # peer group size, and doesn't collapse when the in-sample regression is noisy.
    df['company_$/irci_pt'] = df['enterprise_value'] * EV_ELASTICITY_PER_IRCI_PT
    df['company_$/irci_pt_low'] = df['enterprise_value'] * EV_ELASTICITY_LOW
    df['company_$/irci_pt_high'] = df['enterprise_value'] * EV_ELASTICITY_HIGH
    group_dollars_per_point = peer_mean_ev * EV_ELASTICITY_PER_IRCI_PT

    # === DIAGNOSTIC: in-sample peer regression (kept for transparency, NOT used for sizing) ===
    # With n~6 peers and EV dominated by size/business mix, R² is typically near zero.
    # We report it so users can see the empirical EV~IRCI relationship in their peer group,
    # but the headline $/IRCI point uses the literature elasticity above.
    irci_range = df['irci_composite_pct'].max() - df['irci_composite_pct'].min()
    if len(df) >= 3 and irci_range > 1.0:
        from scipy import stats
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            df['irci_composite_pct'],
            df['enterprise_value']
        )
        df['regression_r2'] = r_value ** 2
        df['regression_slope_diagnostic'] = abs(slope)  # raw $/pt from regression, unscaled
        df['regression_p_value'] = p_value
    else:
        df['regression_r2'] = np.nan
        df['regression_slope_diagnostic'] = np.nan
        df['regression_p_value'] = np.nan

    # === GAPS AND UPSIDE, CAPPED AT HEALY-HUTTON-PALEPU 20% IR-ATTRIBUTABLE EV ===
    df['irci_gap_to_top'] = peer_max_irci - df['irci_composite_pct']
    max_total_upside = df['enterprise_value'] * MAX_TOTAL_UPSIDE_FRACTION
    uncapped_upside = df['irci_gap_to_top'] * df['company_$/irci_pt']
    df['market_cap_gap_regression'] = np.minimum(uncapped_upside, max_total_upside)
    uncapped_group = df['irci_gap_to_top'] * group_dollars_per_point
    df['market_cap_gap_group'] = np.minimum(uncapped_group, max_total_upside)

    # Valuation efficiency: EV per IRCI point — high values = "underrated" relative to peers
    df['company_ev_efficiency'] = df['enterprise_value'] / (df['irci_composite_pct'] + 1)

    # Peer group summary statistics
    df['peer_group_ev_mean'] = peer_mean_ev
    df['peer_group_ev_std'] = peer_std_ev
    df['peer_group_$/irci_pt'] = group_dollars_per_point

    return df[[
        'ticker',
        'enterprise_value',
        'irci_composite_pct',
        'company_$/irci_pt',
        'company_$/irci_pt_low',
        'company_$/irci_pt_high',
        'peer_group_$/irci_pt',
        'irci_gap_to_top',
        'market_cap_gap_regression',
        'market_cap_gap_group',
        'company_ev_efficiency',
        'regression_r2',
        'regression_slope_diagnostic',
        'regression_p_value',
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
    current_weights: Optional[dict[str, float]] = None,
    optimize_for: str = 'r2'
) -> dict:
    """
    Analyze the peer group to recommend optimal dial weights.

    Strategy:
    - 'variance': Dials with higher variance across peers get more weight (better differentiation)
    - 'r2': Find weights that maximize R² of EV ~ IRCI regression (strongest relationship)

    Args:
        df_composite: Composite DataFrame with all dial scores and enterprise_value
        current_weights: Current weight allocation
        optimize_for: 'variance' or 'r2' (default: 'r2')

    Returns:
        Dictionary with:
        - recommended_weights: Suggested weight allocation
        - variance_analysis: Variance of each dial across peer group
        - optimization_method: Which method was used
        - regression_r2: R² achieved with recommended weights (if optimize_for='r2')
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
    variances = df_composite[dial_cols].var().fillna(0)

    # Also calculate coefficient of variation (CV = std / mean)
    # This normalizes for different mean values
    means = df_composite[dial_cols].mean().fillna(0)
    stds = df_composite[dial_cols].std().fillna(0)
    cv = (stds / (means + 1)).fillna(0)  # Add 1 to avoid division by zero

    # Calculate data availability (how many peers have data for each dial)
    availability = (df_composite[dial_cols].notna().sum() / len(df_composite)).fillna(0)

    # Optimization strategy selection
    if optimize_for == 'r2' and 'enterprise_value' in df_composite.columns:
        # Direct R² optimization: Find weights that maximize EV ~ IRCI regression R²
        from scipy.optimize import minimize
        from scipy import stats

        # Objective function: negative R² (we minimize, so we negate R² to maximize it)
        def objective(weights):
            # Ensure weights sum to 1
            w_val, w_liq, w_cov = weights
            w_sent = 1.0 - w_val - w_liq - w_cov

            if w_sent < 0 or any(w < 0 for w in weights):
                return 1.0  # Invalid weights, return high value

            # Compute composite score with these weights
            composite = (
                df_composite['valuation_pct'].fillna(0) * w_val +
                df_composite['liquidity_pct'].fillna(0) * w_liq +
                df_composite['coverage_pct'].fillna(0) * w_cov +
                df_composite['sentiment_pct'].fillna(0) * w_sent
            )

            # Regression EV ~ composite
            valid_mask = (composite > 0) & (df_composite['enterprise_value'] > 0)
            if valid_mask.sum() < 3:
                return 1.0  # Not enough data

            _, _, r_value, _, _ = stats.linregress(
                composite[valid_mask],
                df_composite['enterprise_value'][valid_mask]
            )
            r2 = r_value ** 2

            # Return negative R² (we minimize, so negate to maximize)
            return -r2

        # Initial guess: variance-based weights
        discriminating_power = variances * availability
        total_power = discriminating_power.sum()
        if total_power > 0:
            variance_weights = discriminating_power / total_power
            initial_guess = [
                float(variance_weights['valuation_pct']),
                float(variance_weights['liquidity_pct']),
                float(variance_weights['coverage_pct'])
            ]
        else:
            initial_guess = [0.33, 0.33, 0.33]

        # Bounds: each weight between 5% minimum and 60% maximum
        # This prevents any dial from being completely ignored or dominating
        MIN_WEIGHT = 0.05  # 5% floor ensures all dials contribute
        MAX_WEIGHT = 0.60  # 60% cap prevents over-reliance on one dial
        bounds = [(MIN_WEIGHT, MAX_WEIGHT), (MIN_WEIGHT, MAX_WEIGHT), (MIN_WEIGHT, MAX_WEIGHT)]

        # Constraint: first 3 weights must sum to at most 0.95 (leaving at least 5% for sentiment)
        constraints = {'type': 'ineq', 'fun': lambda w: (1.0 - MIN_WEIGHT) - sum(w)}

        # Optimize
        result = minimize(objective, initial_guess, method='SLSQP', bounds=bounds, constraints=constraints)

        if result.success:
            opt_weights = result.x
            sentiment_weight = max(MIN_WEIGHT, 1.0 - sum(opt_weights))  # Ensure sentiment also has minimum
            # Renormalize if needed to ensure sum = 1.0
            total = opt_weights[0] + opt_weights[1] + opt_weights[2] + sentiment_weight
            recommended_weights = {
                'valuation': float(opt_weights[0] / total),
                'liquidity': float(opt_weights[1] / total),
                'coverage': float(opt_weights[2] / total),
                'sentiment': float(sentiment_weight / total)
            }
            optimization_r2 = -result.fun  # Negate back to get positive R²

            # Verify the R² by recalculating with final weights
            verify_composite = (
                df_composite['valuation_pct'].fillna(0) * opt_weights[0] +
                df_composite['liquidity_pct'].fillna(0) * opt_weights[1] +
                df_composite['coverage_pct'].fillna(0) * opt_weights[2] +
                df_composite['sentiment_pct'].fillna(0) * (1.0 - sum(opt_weights))
            )
            valid_mask = (verify_composite > 0) & (df_composite['enterprise_value'] > 0)
            if valid_mask.sum() >= 3:
                from scipy import stats
                _, _, r_value, _, _ = stats.linregress(
                    verify_composite[valid_mask],
                    df_composite['enterprise_value'][valid_mask]
                )
                verified_r2 = r_value ** 2
                # Update with verified R² (should match optimization_r2)
                optimization_r2 = verified_r2
        else:
            # Fallback to variance-based if optimization fails
            recommended_raw = discriminating_power / (total_power + 1e-10)
            # Fill any NA values with equal weights before converting
            recommended_raw = recommended_raw.fillna(0.25)
            recommended_weights = {
                'valuation': float(recommended_raw['valuation_pct']),
                'liquidity': float(recommended_raw['liquidity_pct']),
                'coverage': float(recommended_raw['coverage_pct']),
                'sentiment': float(recommended_raw['sentiment_pct'])
            }
            optimization_r2 = None
    else:
        # Variance-based optimization (original method)
        # Recommended weights based on variance and availability
        # Higher variance + high availability = more discriminating = higher weight
        discriminating_power = variances * availability
        total_power = discriminating_power.sum()

        if total_power > 0:
            recommended_raw = discriminating_power / total_power
        else:
            recommended_raw = pd.Series([0.25, 0.25, 0.25, 0.25], index=dial_cols)

        # Fill any NA values with equal weights before converting
        recommended_raw = recommended_raw.fillna(0.25)

        # Convert to dictionary with friendly names
        recommended_weights = {
            'valuation': float(recommended_raw['valuation_pct']),
            'liquidity': float(recommended_raw['liquidity_pct']),
            'coverage': float(recommended_raw['coverage_pct']),
            'sentiment': float(recommended_raw['sentiment_pct'])
        }
        optimization_r2 = None

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

    result = {
        'recommended_weights': recommended_weights,
        'current_weights': current_weights,
        'variance_analysis': variance_analysis,
        'optimization_method': optimize_for,
        'discriminating_power': {
            'valuation': float(discriminating_power['valuation_pct']),
            'liquidity': float(discriminating_power['liquidity_pct']),
            'coverage': float(discriminating_power['coverage_pct']),
            'sentiment': float(discriminating_power['sentiment_pct'])
        }
    }

    # Add R² if we did R² optimization
    if optimization_r2 is not None:
        result['optimized_r2'] = optimization_r2

    return result
