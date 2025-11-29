from __future__ import annotations
import pandas as pd
import numpy as np

def winsorize(df: pd.DataFrame, p: float = 0.01) -> pd.DataFrame:
    """Cap extremes column-wise at [p, 1-p] quantiles."""
    capped = df.copy()
    for c in capped.columns:
        lo, hi = capped[c].quantile([p, 1-p])
        capped[c] = capped[c].clip(lo, hi)
    return capped

def zscore(df: pd.DataFrame) -> pd.DataFrame:
    return (df - df.mean()) / df.std(ddof=0)

def irci_score(features: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.Series:
    """
    Combine standardized features into a single score.
    Defaults reflect 'higher risk/impact' when: lower return, higher vol, deeper drawdown, higher turnover.
    """
    if weights is None:
        weights = {"q_return": -0.35, "q_vol_gk": 0.25, "q_drawdown": 0.30, "q_volume_z": 0.10}
    # winsorize → zscore
    X = winsorize(features[weights.keys()].copy())
    Z = zscore(X).fillna(0.0)
    # linear composite
    s = sum(Z[k]*w for k, w in weights.items())
    return s.rename("irci_score")