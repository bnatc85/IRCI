# irci/composite.py
from __future__ import annotations
from typing import Optional, Dict
import numpy as np
import pandas as pd
from .logging import get_logger

log = get_logger("irci.composite")

def _coerce_pct_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    if s.str.contains("%").any():
        s = s.str.replace("%", "", regex=False)
    out = pd.to_numeric(s, errors="coerce")
    if out.dropna().between(0, 1).all() and out.max() <= 1.0:
        out = out * 100.0
    return out


def _normalize_pct_column(df: pd.DataFrame, candidates: list[str], out_name: str) -> pd.Series:
    """
    Returns a 0..100 float percentage column from any of the candidate cols.
    Accepts either 0..1 or 0..100 inputs; auto-scales if needed.
    """
    for c in candidates:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            # If it looks like 0..1, promote to 0..100
            if s.dropna().between(0, 1).all() and s.max() <= 1.0:
                s = s * 100.0
            s.name = out_name
            return s
    raise KeyError(f"None of {candidates} found in DataFrame")


def _to_quarter_end_utc(series_dt: pd.Series) -> pd.Series:
    """
    Series -> quarter-end bucket in UTC (avoids timezone warning).
    """
    return (
        series_dt.dt.tz_convert("UTC")
        .dt.tz_localize(None)
        .dt.to_period("Q")
        .dt.end_time
        .dt.tz_localize("UTC")
    )


# ---------- loaders from your dial CSVs ----------
def prepare_valuation(path):
    df = pd.read_csv(path)
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    if "quarter_end" in df.columns:
        df["quarter_end"] = pd.to_datetime(df["quarter_end"], utc=True, errors="coerce")
    elif "as_of" in df.columns:
        df["as_of"] = pd.to_datetime(df["as_of"], utc=True, errors="coerce")
        df["quarter_end"] = df["as_of"]
    else:
        raise ValueError("valuation csv needs 'quarter_end' or 'as_of'")
    df["quarter_end"] = (
        pd.PeriodIndex(df["quarter_end"].dt.tz_localize(None), freq="Q-DEC")
          .end_time
          .tz_localize("UTC")
    )
    cand = next((c for c in ["valuation_pct","valuation_dial","valuation_score","valuation_pct_empirical","p_valuation"]
                 if c in df.columns), None)
    if not cand:
        raise ValueError("valuation csv missing valuation columns")
    df["valuation_pct"] = _coerce_pct_series(df[cand])
    return df[["ticker","quarter_end","valuation_pct"]]


def prepare_liquidity(path):
    df = pd.read_csv(path, parse_dates=["quarter_end"])
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["quarter_end"] = (
        pd.PeriodIndex(df["quarter_end"].dt.tz_localize(None), freq="Q-DEC")
          .end_time
          .tz_localize("UTC")
    )
    df["liquidity_pct"] = _normalize_pct_column(df, ["liquidity_pct"], "liquidity_pct")
    return df[["ticker","quarter_end","liquidity_pct"]]


def _ensure_quarter_end(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee a UTC quarter_end column, deriving from common alternatives."""
    if "quarter_end" in df.columns:
        df["quarter_end"] = pd.to_datetime(df["quarter_end"], utc=True, errors="coerce")
        return df
    # Try a date-like column
    for cand in ["date", "as_of", "period_end", "report_date", "timestamp"]:
        if cand in df.columns:
            dt = pd.to_datetime(df[cand], utc=True, errors="coerce")
            qe = pd.PeriodIndex(dt, freq="Q-DEC").end_time.tz_localize("UTC")
            df = df.assign(quarter_end=qe)
            return df
    # Try a quarter code like 2025Q2 or 2024-Q3
    if "quarter" in df.columns:
        qcodes = df["quarter"].astype(str).str.replace(" ", "").str.replace("-", "")
        qe = pd.PeriodIndex(qcodes, freq="Q-DEC").end_time.tz_localize("UTC")
        df = df.assign(quarter_end=qe)
        return df
    raise ValueError("Missing 'quarter_end' and no fallback date/quarter column found "
                     "(looked for: date, as_of, period_end, report_date, timestamp, quarter).")


def prepare_coverage(path):
    df = pd.read_csv(path)
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    if "quarter_end" in df.columns:
        df["quarter_end"] = pd.to_datetime(df["quarter_end"], utc=True, errors="coerce")
    elif "as_of" in df.columns:
        df["as_of"] = pd.to_datetime(df["as_of"], utc=True, errors="coerce")
        df["quarter_end"] = df["as_of"]
    else:
        raise ValueError("coverage csv needs 'quarter_end' or 'as_of'")
    df["quarter_end"] = (
        pd.PeriodIndex(df["quarter_end"].dt.tz_localize(None), freq="Q-DEC")
          .end_time
          .tz_localize("UTC")
    )
    cand = next((c for c in ["coverage_pct","coverage","coverage_score","coverage_percent","p_coverage","coverage_dial"]
                 if c in df.columns), None)
    if not cand:
        raise ValueError("coverage csv missing coverage columns")
    df["coverage_pct"] = _coerce_pct_series(df[cand])
    return df[["ticker","quarter_end","coverage_pct"]]


def prepare_sentiment(path):
    df = pd.read_csv(path, parse_dates=["quarter_end"])
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["quarter_end"] = (
        pd.PeriodIndex(df["quarter_end"].dt.tz_localize(None), freq="Q-DEC")
          .end_time
          .tz_localize("UTC")
    )
    df["sentiment_pct"] = _normalize_pct_column(df, ["sentiment_pct","trust_pct"], "sentiment_pct")
    return df[["ticker","quarter_end","sentiment_pct"]]


    # Prefer explicit sentiment_pct, else fallback to trust_pct
    col = "sentiment_pct" if "sentiment_pct" in df.columns else "trust_pct" if "trust_pct" in df.columns else None
    if col is None:
        raise KeyError("Neither 'sentiment_pct' nor 'trust_pct' found in sentiment CSV")

    s = pd.to_numeric(df[col], errors="coerce")
    if s.dropna().between(0, 1).all() and s.max() <= 1.0:
        s = s * 100.0
    df["sentiment_pct"] = s
    return df[["ticker", "quarter_end", "sentiment_pct"]]

# You can add similar loaders later:
# def prepare_coverage(path): -> returns ["ticker", "quarter_end", "coverage_pct"]
# def prepare_sentiment(path): -> returns ["ticker", "quarter_end", "sentiment_pct"]


# ---------- composite ----------
def irci_composite(
    valuation: Optional[pd.DataFrame] = None,
    liquidity: Optional[pd.DataFrame] = None,
    coverage: Optional[pd.DataFrame] = None,
    sentiment: Optional[pd.DataFrame] = None,
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Weighted average of dial percentiles (0..100). Missing dials are ignored
    and weights are re-normalized row-by-row.

    weights default: 0.35 valuation, 0.35 liquidity, 0.15 coverage, 0.15 sentiment
    """
    if weights is None:
        weights = {"valuation": 0.35, "liquidity": 0.35, "coverage": 0.15, "sentiment": 0.15}

    frames = []
    if valuation is not None:
        frames.append(valuation[["ticker", "quarter_end", "valuation_pct"]])
    if liquidity is not None:
        frames.append(liquidity[["ticker", "quarter_end", "liquidity_pct"]])
    if coverage is not None and "coverage_pct" in coverage:
        frames.append(coverage[["ticker", "quarter_end", "coverage_pct"]])
    if sentiment is not None and "sentiment_pct" in sentiment:
        frames.append(sentiment[["ticker", "quarter_end", "sentiment_pct"]])

    if not frames:
        raise ValueError("No dial dataframes provided")

    base = frames[0]
    for f in frames[1:]:
        base = base.merge(f, on=["ticker", "quarter_end"], how="outer")

    # Ensure expected columns exist (may be all-NA if not provided yet)
    for d in ["valuation", "liquidity", "coverage", "sentiment"]:
        col = f"{d}_pct"
        if col not in base.columns:
            base[col] = np.nan

    dial_cols = ["valuation_pct", "liquidity_pct", "coverage_pct", "sentiment_pct"]
    W = np.array([weights.get("valuation", 0.0), weights.get("liquidity", 0.0),
                  weights.get("coverage", 0.0), weights.get("sentiment", 0.0)], dtype=float)

    X = base[dial_cols].astype(float)
    mask = X.notna().astype(float).values
    num = (X.fillna(0.0).values * W).sum(axis=1)
    den = (mask * W).sum(axis=1)
    base["irci_composite_pct"] = np.where(den > 0, num / den, np.nan)

    base["dials_available"] = X.notna().sum(axis=1)
    base = base.sort_values(["quarter_end", "irci_composite_pct"], ascending=[True, False])
    return base
