
# irci/trust.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict
import numpy as np
import pandas as pd
import requests
import json
from urllib.parse import urlencode

from .config import Settings
from .logging import get_logger
from .market import fetch_prices_fmp
from .valuation import median_anchored_pct

log = get_logger("irci.trust")

# --------------------------------------------------------------------------------------
# Kenneth French Daily Factors (via irci.ff)
# --------------------------------------------------------------------------------------
try:
    from .ff import load_ff_factors_daily
except Exception as e:
    load_ff_factors_daily = None
    log.warning("FF loader not available yet; install irci.ff. (%s)", e)

# --------------------------------------------------------------------------------------
# FinBERT tone (optional)
# --------------------------------------------------------------------------------------
try:
    from .finbert_sentiment import finbert_tone_for_news
except Exception as e:
    finbert_tone_for_news = None
    log.warning("FinBERT scorer not available yet; install irci.finbert_sentiment. (%s)", e)

# --------------------------------------------------------------------------------------
# SEC helpers w/ FMP fallback
# --------------------------------------------------------------------------------------
def _sec_headers(s: Settings) -> Dict[str, str]:
    return {"User-Agent": s.user_agent, "Accept-Encoding": "gzip, deflate", "Host": "data.sec.gov"}

_BUILTIN_CIK = {
    "AAPL": 320193,
    "MSFT": 789019,
    "AMZN": 1018724,
    "GOOGL": 1652044,
    "GOOG": 1652044,
}

def _ticker_map(s: Settings) -> pd.DataFrame:
    """Try SEC’s company_tickers.json; on failure, return a minimal built-in map."""
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        r = requests.get(url, headers=_sec_headers(s), timeout=60)
        r.raise_for_status()
        js = r.json()
        rows = [{"cik": int(v["cik_str"]), "ticker": v["ticker"].upper(), "name": v["title"]}
                for _, v in js.items()]
        return pd.DataFrame(rows).set_index("ticker")
    except Exception as e:
        log.warning("SEC ticker map unavailable (%s). Using built-in minimal map.", e)
        df = pd.DataFrame(
            [{"ticker": k, "cik": v, "name": k} for k, v in _BUILTIN_CIK.items()]
        ).set_index("ticker")
        return df

def _residuals_capm_yf(df_px: pd.DataFrame, q_start: pd.Timestamp, q_end: pd.Timestamp) -> pd.DataFrame:
    """
    Market-only residuals using SPY via yfinance as a fallback when FF is incomplete.
    y_t = stock return; x_t = SPY return; resid = y_t - (alpha + beta * x_t)
    """
    import yfinance as yf  # type: ignore[import-not-found]
    # fetch market series a bit before q_start to fit beta on sufficient history
    lo = (q_start - pd.Timedelta(days=400)).date().isoformat()
    hi = q_end.date().isoformat()
    mkt = yf.download("SPY", start=lo, end=hi, auto_adjust=True, progress=False)
    if mkt is None or mkt.empty:
        return pd.DataFrame(index=df_px.index, columns=["resid"]).assign(resid=np.nan)

    mkt = mkt.copy()
    mkt.index = pd.to_datetime(mkt.index, utc=True)
    mkt = mkt.sort_index()
    mkt["mret"] = mkt["Adj Close"].pct_change()

    d = df_px.copy().sort_index()
    d["ret"] = d["adj_close"].pct_change()

    joined = d.join(mkt[["mret"]], how="inner").dropna(subset=["ret", "mret"])
    if joined.empty:
        return pd.DataFrame(index=d.index, columns=["resid"]).assign(resid=np.nan)

    # OLS y ~ [1, mret]
    X = np.column_stack([np.ones(len(joined)), joined["mret"].values.astype(float)])
    y = joined["ret"].values.astype(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = beta[0] + beta[1] * joined["mret"].values
    resid = y - y_hat
    out = pd.DataFrame(index=joined.index)
    out["resid"] = resid
    return out


def _company_submissions(cik: str, s: Settings) -> pd.DataFrame:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url, headers=_sec_headers(s), timeout=60)
    r.raise_for_status()
    rec = r.json().get("filings", {}).get("recent", {})
    df = pd.DataFrame(rec)
    if df.empty:
        return df
    df["filingDate"] = pd.to_datetime(df["filingDate"], utc=True)
    df["reportDate"] = pd.to_datetime(df.get("reportDate"), utc=True, errors="coerce")
    df["form"] = df["form"].astype(str)
    return df[["filingDate", "reportDate", "form"]]

def _fmp_event_dates_for_quarter(symbol: str, q_start: pd.Timestamp, q_end: pd.Timestamp, apikey: str) -> List[pd.Timestamp]:
    """Fallback: use FMP's sec_filings endpoint to collect event dates for 8-K/10-Q/K."""
    base = "https://financialmodelingprep.com/api/v3/sec_filings"
    params = {
        "from": q_start.date().isoformat(),
        "to": q_end.date().isoformat(),
        "page": 0,
        "apikey": apikey,
    }
    url = f"{base}/{symbol}?{urlencode(params)}"
    log.info("GET %s", url.replace(apikey, "***"))
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json() or []
    forms = {"8-K", "8-K/A", "10-Q", "10-Q/A", "10-K", "10-K/A"}
    out = []
    for d in data:
        f = str(d.get("form", "")).strip()
        if f in forms:
            dt = d.get("fillingDate") or d.get("filingDate") or d.get("date")
            if dt:
                out.append(pd.to_datetime(dt, utc=True))
    return sorted(out)

def _sec_event_dates_for_quarter(ticker: str,
                                 q_start: pd.Timestamp,
                                 q_end: pd.Timestamp,
                                 s: Settings,
                                 apikey: Optional[str] = None) -> List[pd.Timestamp]:
    """Prefer SEC submissions; if that fails, fall back to FMP sec_filings."""
    try:
        tm = _ticker_map(s)
        t = ticker.upper()
        if t in tm.index:
            cik = f"{int(tm.loc[t, 'cik']):010d}"
            subs = _company_submissions(cik, s)
            if not subs.empty:
                mask = (subs["filingDate"] >= q_start) & (subs["filingDate"] <= q_end)
                forms = ["8-K", "8-K/A", "10-Q", "10-Q/A", "10-K", "10-K/A"]
                ev = subs.loc[mask & subs["form"].isin(forms), "filingDate"]
                ev = pd.to_datetime(ev, utc=True)
                if len(ev):
                    return sorted(ev.tolist())
        raise RuntimeError("SEC submissions not available or empty")
    except Exception as e:
        log.warning("SEC event fetch failed for %s (%s). Falling back to FMP.", ticker, e)
        if apikey:
            try:
                return _fmp_event_dates_for_quarter(ticker, q_start, q_end, apikey)
            except Exception as e2:
                log.warning("FMP fallback also failed for %s (%s). Returning empty.", ticker, e2)
        return []

# --------------------------------------------------------------------------------------
# Factor model residuals
# --------------------------------------------------------------------------------------
def _ols_beta(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    Xc = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    return beta  # [alpha, b_mkt, b_smb, ...]

def _factor_residuals(df_px: pd.DataFrame, ff: pd.DataFrame) -> pd.DataFrame:
    """
    Compute simple daily residuals from the Fama-French 5-factor model (with intercept).
    r_excess_t = r_t - RF_t;  y = r_excess;  X = [Mkt_RF, SMB, HML, RMW, CMA]
    """
    d = df_px.copy().sort_index()
    d["ret"] = d["adj_close"].pct_change()
    f = ff.copy().sort_index()
    joined = d.join(f, how="inner").dropna(subset=["ret", "Mkt_RF"])
    if joined.empty:
        return pd.DataFrame(index=d.index, columns=["resid"]).assign(resid=np.nan)
    y = (joined["ret"] - joined["RF"]).values.astype(float)
    X = joined[["Mkt_RF", "SMB", "HML", "RMW", "CMA"]].values.astype(float)
    beta = _ols_beta(X, y)
    y_hat = beta[0] + X @ beta[1:]
    resid = y - y_hat
    out = pd.DataFrame(index=joined.index)
    out["resid"] = resid
    return out

# --------------------------------------------------------------------------------------
# Event calmness helpers
# --------------------------------------------------------------------------------------
def _sum_abs_resid_window(resid: pd.Series, center_date: pd.Timestamp, window: int = 3) -> float:
    """Sum of |residuals| over a ±window trading-day window centered at center_date."""
    idx = resid.index
    anchor = center_date
    if center_date not in idx:
        pos = idx.searchsorted(center_date)
        if pos == 0:
            anchor = idx[0]
        else:
            anchor = idx[min(pos-1, len(idx)-1)]
    loc = idx.get_loc(anchor)
    if isinstance(loc, slice):  # unlikely, but be safe
        loc = loc.start
    lo = max(0, loc - window)
    hi = min(len(idx), loc + window + 1)
    return float(np.abs(resid.iloc[lo:hi]).sum())

@dataclass
class TrustWeights:
    w_event_calm: float = 0.50
    w_baseline_calm: float = 0.20
    w_media_tone: float = 0.30

def trust_quarter_for_symbol(
    symbol: str,
    q_start: pd.Timestamp,
    q_end: pd.Timestamp,
    ff: pd.DataFrame,
    news_df: Optional[pd.DataFrame],
    s: Optional[Settings] = None,
    weights: Optional[TrustWeights] = None,
    apikey: Optional[str] = None,
) -> Dict[str, float]:
    """
    Compute raw sub-signals for one symbol × quarter.
    Returns dict with keys: event_calm_raw, baseline_calm_raw, media_tone_raw, media_tone_src, event_count
    (higher raw is "better"; normalization to 0..100 happens across peers later).
    """
    s = s or Settings.load()
    W = weights or TrustWeights()
    apikey = apikey or s.fmp_api_key

    # 1) Prices and residuals
    df_px = fetch_prices_fmp(
        symbol,
        (q_start - pd.Timedelta(days=400)).date().isoformat(),
        q_end.date().isoformat(),
        apikey
    )
    df_px = df_px.sort_index()
    # Ensure tz-aware UTC (some backends are already UTC; this is idempotent)
    df_px.index = pd.to_datetime(df_px.index, utc=True)

    # Try FF residuals, but be robust if FF is empty
    resid_df = pd.DataFrame(index=df_px.index, columns=["resid"], data=np.nan)
    try:
        if ff is not None and not getattr(ff, "empty", True):
            resid_df = _factor_residuals(df_px, ff)
    except Exception as e:
        log.warning("FF residuals failed for %s: %s", symbol, e)

    # Quarter slice (ALWAYS build mask from resid_df.index)
    idx = resid_df.index
    resid_q = resid_df.loc[(idx >= q_start) & (idx <= q_end)].copy()

    # If no residuals in the quarter (e.g., FF stops at 2025-06-30), fall back to CAPM(SPY)
    if resid_q["resid"].dropna().empty:
        try:
            resid_df = _residuals_capm_yf(df_px, q_start, q_end)
            idx2 = resid_df.index
            resid_q = resid_df.loc[(idx2 >= q_start) & (idx2 <= q_end)].copy()
        except Exception as e:
            log.warning("CAPM fallback failed for %s: %s", symbol, e)
            idx_q = df_px.loc[(df_px.index >= q_start) & (df_px.index <= q_end)].index
            resid_q = pd.DataFrame(index=idx_q, columns=["resid"], data=np.nan)


    # Baseline calmness: negative of residual std (lower std => higher calmness)
    baseline_calm_raw = -float(resid_q["resid"].std(ddof=0)) if resid_q["resid"].notna().any() else np.nan
    if not np.isfinite(baseline_calm_raw):  # fallback to raw returns if residuals were still NaN
        ret_q = df_px.loc[(df_px.index >= q_start) & (df_px.index <= q_end), "adj_close"].pct_change()
        baseline_calm_raw = -float(ret_q.std(ddof=0)) if ret_q.notna().any() else np.nan


    # 2) Event calmness: 8-K / 10-Q/K windows (SEC with FMP fallback)
    ev_dates = _sec_event_dates_for_quarter(symbol, q_start, q_end, s, apikey=apikey)
    # try residuals first
    event_calm_raw = np.nan
    if ev_dates:
        sums = [_sum_abs_resid_window(resid_df["resid"], d, window=3) for d in ev_dates]
        if np.isfinite(np.nanmedian(sums)):
            event_calm_raw = -float(np.nanmedian(sums))

    # if residuals path failed, use raw returns as proxy for event windows
    if (not np.isfinite(event_calm_raw)) and ev_dates:
        ret_series = df_px["adj_close"].pct_change()
        sums = [_sum_abs_resid_window(ret_series, d, window=3) for d in ev_dates]
        if np.isfinite(np.nanmedian(sums)):
            event_calm_raw = -float(np.nanmedian(sums))

        # 2) Event calmness (8-K / 10-Q / 10-K + optional extras)
    event_calm_raw = np.nan
    event_count = 0
    ev_dates: list[pd.Timestamp] = []

    # SEC filing dates for this quarter
    try:
        ev_dates = _sec_event_dates_for_quarter(symbol, q_start, q_end, s)
    except Exception as e:
        log.warning("SEC event date fetch failed for %s: %s", symbol, e)
        ev_dates = []

    # (Optional) merge user-provided extra events from data/events_extra.csv
    try:
        import pathlib
        p = pathlib.Path("data/events_extra.csv")
        if p.exists():
            extra = pd.read_csv(p)
            extra["date"] = pd.to_datetime(extra["date"], utc=True, errors="coerce")
            m = (extra["date"] >= q_start) & (extra["date"] <= q_end)
            if "ticker" in extra.columns:
                m &= (extra["ticker"].astype(str).str.upper() == symbol.upper())
            ev_dates = sorted(set(ev_dates) | set(extra.loc[m, "date"].dropna().tolist()))
    except Exception as e:
        log.warning("Could not load extra events: %s", e)

    event_count = len(ev_dates)

    # Compute event calmness:
    # First try residuals around each event (±3d); if those are NaN, fallback to raw returns
    if event_count:
        sums = [_sum_abs_resid_window(resid_df["resid"], d, window=3) for d in ev_dates]
        med = np.nanmedian(sums)
        if np.isfinite(med):
            event_calm_raw = -float(med)
        else:
            # fallback: use raw returns magnitude around events
            ret_series = df_px["adj_close"].pct_change()
            sums = [_sum_abs_resid_window(ret_series, d, window=3) for d in ev_dates]
            med = np.nanmedian(sums)
            if np.isfinite(med):
                event_calm_raw = -float(med)


    # 3) Media tone: FinBERT with VADER fallback + shrink/clamp
    media_tone_raw = np.nan
    media_tone_src = None
    tone_n = 0  # <- define upfront so it's always in scope

    if news_df is not None:
        df_n = news_df.copy()
        if "date" in df_n.columns:
            df_n["date"] = pd.to_datetime(df_n["date"], utc=True, errors="coerce")
        else:
            raise ValueError("news_df must include a 'date' column")
        mask = (df_n["date"] >= q_start) & (df_n["date"] <= q_end)
        if "ticker" in df_n.columns:
            mask = mask & (df_n["ticker"].str.upper() == symbol.upper())

        texts = []
        if "text" in df_n.columns:
            texts = df_n.loc[mask, "text"].dropna().astype(str).tolist()
        elif "title" in df_n.columns:
            texts = df_n.loc[mask, "title"].dropna().astype(str).tolist()

        tone_n = len(texts)
        if tone_n:
            tone_val = float("nan")

        # Try FinBERT first
            if finbert_tone_for_news is not None:
                try:
                    tone_val = float(finbert_tone_for_news(texts))
                    media_tone_src = "finbert"
                except Exception as e:
                    log.warning("FinBERT tone failed (%s); falling back to VADER.", e)

        # VADER fallback
            if not (isinstance(tone_val, float) and tone_val == tone_val):  # NaN check
                try:
                    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                    a = SentimentIntensityAnalyzer()
                    vals = [a.polarity_scores(t[:500])["compound"]
                            for t in texts if isinstance(t, str) and t.strip()]
                    if vals:
                        tone_val = float(np.mean(vals))
                        media_tone_src = "vader"
                except Exception as e:
                    log.warning("VADER fallback not available (%s).", e)

        # Reliability shrink + clamp (only if we have a finite tone)
            if isinstance(tone_val, float) and tone_val == tone_val:
                k = 4.0
                shrink = tone_n / (tone_n + k)
                media_tone_raw = float(np.clip(tone_val * shrink, -0.6, 0.6))
    # --- Return a dict of raw metrics (higher is better) ---
    return {
        "event_calm_raw": event_calm_raw,
        "baseline_calm_raw": baseline_calm_raw,
        "media_tone_raw": media_tone_raw,
        "media_tone_src": media_tone_src,
        "media_tone_n": tone_n,   # number of articles used for tone
        "event_count": event_count,
    }


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------
def trust_snapshot(
    symbols: List[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    news_df: Optional[pd.DataFrame] = None,
    quarter_freq: str = "QE-DEC",
    weights: Optional[TrustWeights] = None,
    apikey: Optional[str] = None,
) -> pd.DataFrame:
    """
    Build per-quarter Trust dial (0..100) using:
      - Event Calmness (factor-adjusted residual quietness around SEC events)
      - Baseline Calmness (factor-adjusted residual volatility in quarter)
      - Media Tone (FinBERT→VADER fallback)

    Output columns:
      [ticker, quarter_end, trust_pct, sentiment_pct, p_event_calm, p_baseline_calm, p_media_tone,
       event_calm_raw, baseline_calm_raw, media_tone_raw, media_tone_src, event_count]
    """
    s = Settings.load()
    apikey = apikey or s.fmp_api_key
    if load_ff_factors_daily is None:
        raise RuntimeError("Fama-French loader is not available. Add irci/ff.py or install deps.")
    start = start or "2010-01-01"
    ff = load_ff_factors_daily(start=start, end=end)

    rows = []
    for sym in [t.strip().upper() for t in symbols if t.strip()]:
        px = fetch_prices_fmp(sym, start, end, apikey)
        q_ends = px.resample(quarter_freq).last().index
        for q_end in q_ends:
            prev_q_end = q_end - pd.offsets.QuarterEnd()
            q_start = (prev_q_end + pd.Timedelta(days=1)).tz_convert("UTC").normalize()
            res = trust_quarter_for_symbol(sym, q_start, q_end, ff, news_df, s=s, weights=weights, apikey=apikey)
            res.update({"ticker": sym, "quarter_end": pd.Timestamp(q_end.tz_convert("UTC"))})
            rows.append(res)

    df = pd.DataFrame(rows)

    # Percentile ranks within each quarter (median-anchored, higher better)
    df["p_event_calm"] = df.groupby("quarter_end", group_keys=False)["event_calm_raw"].apply(
        lambda s: median_anchored_pct(s, lower_is_better=False)
    )
    df["p_baseline_calm"] = df.groupby("quarter_end", group_keys=False)["baseline_calm_raw"].apply(
        lambda s: median_anchored_pct(s, lower_is_better=False)
    )
    df["p_media_tone"] = df.groupby("quarter_end", group_keys=False)["media_tone_raw"].apply(
        lambda s: median_anchored_pct(s, lower_is_better=False)
    )

    # Weighted mean over available sub-dials (renormalize if some are NaN)
    W = weights or TrustWeights()
    def _blend_trust_row(r):
        num = 0.0
        den = 0.0
        if pd.notna(r.get("p_event_calm")):
            num += W.w_event_calm * float(r["p_event_calm"]); den += W.w_event_calm
        if pd.notna(r.get("p_baseline_calm")):
            num += W.w_baseline_calm * float(r["p_baseline_calm"]); den += W.w_baseline_calm
        if pd.notna(r.get("p_media_tone")):
            num += W.w_media_tone * float(r["p_media_tone"]); den += W.w_media_tone
        return (num / den) if den > 0 else np.nan

    df["trust_pct"] = df.apply(_blend_trust_row, axis=1)
    df["sentiment_pct"] = df["trust_pct"]

    keep = ["ticker","quarter_end","trust_pct","sentiment_pct",
        "p_event_calm","p_baseline_calm","p_media_tone",
        "event_calm_raw","baseline_calm_raw","media_tone_raw",
        "media_tone_src","media_tone_n","event_count"]
    return df[keep].sort_values(["quarter_end", "ticker"]).reset_index(drop=True)
