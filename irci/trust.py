# irci/trust.py
from __future__ import annotations
from typing import Optional
FINBERT_MODEL = "ProsusAI/finbert"
from dataclasses import dataclass
from typing import List, Optional, Dict
import numpy as np
import pandas as pd
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests
import json
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlencode
from pandas.tseries.offsets import QuarterEnd
from .config import Settings
from .logging import get_logger
from .market import fetch_prices_fmp
from .valuation import median_anchored_pct
from .ff import load_ff_factors_daily

log = get_logger("irci.trust")
# --- HTTP session helper (SEC requires a UA; reuse across calls) ---
_requests_session_singleton = None

def _requests_session(s=None):
    """
    Return a singleton requests.Session with the proper User-Agent.
    """
    global _requests_session_singleton
    if _requests_session_singleton is None:
        import requests
        _requests_session_singleton = requests.Session()
        ua = (s.user_agent if s else Settings.load().user_agent)
        _requests_session_singleton.headers.update({"User-Agent": ua})
    return _requests_session_singleton

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

def _texts_for_quarter(news_df: Optional[pd.DataFrame],
                       symbol: str,
                       q_start: pd.Timestamp,
                       q_end: pd.Timestamp) -> list[str]:
    if news_df is None or getattr(news_df, "empty", True):
        return []
    df = news_df.copy()

    # Normalize date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    elif "published_at" in df.columns:
        df["date"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    else:
        return []

    # Filter by ticker + quarter
    m = (df["date"].between(q_start, q_end))
    if "ticker" in df.columns:
        m &= (df["ticker"].astype(str).str.upper() == symbol.upper())
    sub = df.loc[m]

    # Use whichever text columns exist
    text_cols = [c for c in ("headline","title","lede","summary") if c in sub.columns]
    if not text_cols:
        return []

    texts = (
        sub[text_cols]
        .astype(str)
        .apply(lambda r: " ".join([t for t in r if t and t != "nan"]), axis=1)
        .str.strip()
        .tolist()
    )
    return [t for t in texts if t]

def _get_finbert_pipeline() -> Optional["TextClassificationPipeline"]:
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, TextClassificationPipeline
        tok = AutoTokenizer.from_pretrained(FINBERT_MODEL)
        mdl = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL)
        return TextClassificationPipeline(model=mdl, tokenizer=tok, return_all_scores=True, device=-1)
    except Exception as e:
        print(f"[WARNING] FinBERT unavailable: {e} — skipping media tone.")
        return None

def finbert_score(texts):
    pipe = _get_finbert_pipeline()
    if pipe is None or not texts:
        return None  # caller sets NaNs
    # Batch for speed; truncate long pressers
    preds = pipe(texts, truncation=True, max_length=128, batch_size=32)
    # Convert to simple signed score: +1·pos -1·neg, ignore neutral
    out = []
    for p in preds:
        s = {d["label"].lower(): d["score"] for d in p}
        out.append( (s.get("positive",0) - s.get("negative",0)) )
    return out

def _ticker_map(s: Settings) -> pd.DataFrame:
    """Try SEC’s company_tickers.json; on failure, return a minimal built-in map."""
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        r = _requests_session(s).get(url, timeout=60)
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
    sess = _requests_session()
    r = sess.get(url, headers=_sec_headers(s), timeout=(5, 10))  # (connect, read)
    r.raise_for_status()
    rec = r.json().get("filings", {}).get("recent", {})
    df = pd.DataFrame(rec)
    if df.empty:
        return df
    df["filingDate"] = pd.to_datetime(df["filingDate"], utc=True)
    df["reportDate"] = pd.to_datetime(df.get("reportDate"), utc=True, errors="coerce")
    df["form"] = df["form"].astype(str)
    return df[["filingDate", "reportDate", "form"]]

def _events_from_fmp(symbol: str, start: pd.Timestamp, end: pd.Timestamp, apikey: str, s=None) -> list[pd.Timestamp]:
    events = []
    page = 0
    while True:
        url = (
            f"https://financialmodelingprep.com/api/v3/sec_filings/"
            f"{symbol}?from={start.date()}&to={end.date()}&page={page}&apikey={apikey}"
        )
        r = _requests_session(s).get(url, timeout=60)
        r.raise_for_status()
        js = r.json()
        if not js:
            break
        for it in js:
            ftype = (it.get("type") or "").upper()
            if ftype in {"10-Q", "10-K", "8-K"}:
                d = (it.get("acceptedDate")
                     or it.get("fillingDate")
                     or it.get("date"))
                dt = pd.to_datetime(d, utc=True, errors="coerce")
                if dt is not None and start <= dt <= end:
                    events.append(dt)
        page += 1
        if page > 8:  # hard stop to avoid infinite loops
            break
    return sorted(set(events))

def _events_between(symbol, start, end, apikey, s=None) -> list[pd.Timestamp]:
    # 1) Try SEC submissions JSON (fast, rich)
    try:
        cik = _get_cik_for_symbol(symbol, s=s)  # your existing helper
        url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
        r = _requests_session(s).get(url, timeout=60)
        r.raise_for_status()
        js = r.json()
        dates = pd.to_datetime(js["filings"]["recent"]["filingDate"], utc=True, errors="coerce")
        forms = js["filings"]["recent"]["form"]
        ev = [d for d, f in zip(dates, forms) if f in {"10-Q","10-K","8-K"} and (d is not None and start <= d <= end)]
        if ev:
            return ev
    except Exception as e:
        log.warning("SEC event fetch failed for %s (%s). Falling back to FMP.", symbol, e)

    # 2) Fallback: FMP
    try:
        return _events_from_fmp(symbol, start, end, apikey, s=s)
    except Exception as e:
        log.warning("FMP fallback failed for %s: %s", symbol, e)
        return []

_SEC_TICKER_MAP = None

def _sec_ticker_map(s=None) -> dict[str, int]:
    global _SEC_TICKER_MAP
    if _SEC_TICKER_MAP is not None:
        return _SEC_TICKER_MAP
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        r = _requests_session(s).get(url, timeout=60)
        r.raise_for_status()
        data = r.json()
        mp = {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}
        _SEC_TICKER_MAP = mp
        return mp
    except Exception as e:
        log.warning("SEC ticker map unavailable (%s). Using built-in minimal map.", e)
        _SEC_TICKER_MAP = _BUILTIN_CIK  # you already have this
        return _SEC_TICKER_MAP

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
    r = _requests_session(s).get(url, timeout=60)
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
    if os.getenv("IRCI_USE_SEC_EVENTS", "1") == "0":
        if apikey:
            try:
                return _fmp_event_dates_for_quarter(ticker, q_start, q_end, apikey)
            except Exception as e2:
                log.warning("FMP sec_filings failed for %s (%s); returning empty.", ticker, e2)
        return []
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

# --- keep your imports as-is above this line ---

from dataclasses import dataclass

@dataclass
class TrustWeights:
    w_event_calm: float = 0.50
    w_baseline_calm: float = 0.20
    w_media_tone: float = 0.30

def _coerce_weights(weights):
    if isinstance(weights, dict):
        return TrustWeights(
            w_event_calm=float(weights.get("w_event_calm", 0.50)),
            w_baseline_calm=float(weights.get("w_baseline_calm", 0.20)),
            w_media_tone=float(weights.get("w_media_tone", 0.30)),
        )
    return TrustWeights()

def trust_quarter_for_symbol(
    symbol: str,
    q_start,                 # pandas Timestamp (quarter start)
    q_end,                   # pandas Timestamp (quarter end)
    ff,                      # Fama-French daily factors DataFrame for [q_start, q_end]
    news_df=None,            # Optional preloaded news DataFrame
    apikey: str | None = None,
    s=None,                  # Settings (optional)
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Compute raw sub-signals for one symbol × quarter.
    Returns ONLY raw fields; percentiles & final trust_pct are computed in trust_snapshot.
    Keys returned:
      event_calm_raw, baseline_calm_raw, media_tone_raw, media_tone_src, media_tone_n, event_count
    """
    s = s or Settings.load()
    apikey = apikey or s.fmp_api_key

    # 1) Prices and residuals
    df_px = fetch_prices_fmp(
        symbol,
        (q_start - pd.Timedelta(days=400)).date().isoformat(),
        q_end.date().isoformat(),
        apikey
    ).sort_index()
    df_px.index = pd.to_datetime(df_px.index, utc=True)

    # Residuals: prefer FF5, fall back to CAPM(SPY), then raw returns
    resid_df = pd.DataFrame(index=df_px.index, columns=["resid"], data=np.nan)
    try:
        if ff is not None and not getattr(ff, "empty", True):
            resid_df = _factor_residuals(df_px, ff)
    except Exception as e:
        log.warning("FF residuals failed for %s: %s", symbol, e)

    mask = (resid_df.index >= q_start) & (resid_df.index <= q_end)
    resid_q = resid_df.loc[mask].copy()

    if resid_q["resid"].dropna().empty:
        try:
            resid_df = _residuals_capm_yf(df_px, q_start, q_end)
            resid_q = resid_df.loc[(resid_df.index >= q_start) & (resid_df.index <= q_end)].copy()
        except Exception as e:
            log.warning("CAPM fallback failed for %s: %s", symbol, e)
            resid_q = pd.DataFrame(index=df_px.loc[(df_px.index >= q_start) & (df_px.index <= q_end)].index,
                                   columns=["resid"], data=np.nan)

    # Baseline calmness (negative volatility = calmer = better)
    baseline_calm_raw = -float(resid_q["resid"].std(ddof=0)) if resid_q["resid"].notna().any() else np.nan
    if not np.isfinite(baseline_calm_raw):
        ret_q = df_px.loc[(df_px.index >= q_start) & (df_px.index <= q_end), "adj_close"].pct_change()
        baseline_calm_raw = -float(ret_q.std(ddof=0)) if ret_q.notna().any() else np.nan

    # 2) Event calmness from 8-K / 10-Q/K windows
    ev_dates = _sec_event_dates_for_quarter(symbol, q_start, q_end, s, apikey=apikey)
    # Optional extra events from data/events_extra.csv
    try:
        p = Path("data/events_extra.csv")
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
    event_calm_raw = np.nan
    if event_count:
        sums = [_sum_abs_resid_window(resid_df["resid"], d, window=3) for d in ev_dates]
        med = np.nanmedian(sums)
        if np.isfinite(med):
            event_calm_raw = -float(med)
        else:
            # fallback to raw returns in the window
            ret_series = df_px["adj_close"].pct_change()
            sums = [_sum_abs_resid_window(ret_series, d, window=3) for d in ev_dates]
            med = np.nanmedian(sums)
            if np.isfinite(med):
                event_calm_raw = -float(med)

    # 3) Media tone (FinBERT if available; VADER fallback; reliability shrink)
    media_tone_raw = np.nan
    media_tone_src = np.nan
    media_tone_n   = 0

    texts = []
    if news_df is not None and not getattr(news_df, "empty", True):
        nd = news_df.copy()
        if "date" in nd.columns:
            nd["date"] = pd.to_datetime(nd["date"], utc=True, errors="coerce")
        elif "published_at" in nd.columns:
            nd["date"] = pd.to_datetime(nd["published_at"], utc=True, errors="coerce")
        else:
            nd["date"] = pd.NaT
        if "headline" not in nd.columns and "title" in nd.columns:
            nd["headline"] = nd["title"].astype(str)
        m_ticker = nd["ticker"].astype(str).str.upper().eq(symbol.upper()) if "ticker" in nd.columns else True
        m_win = (nd["date"] >= q_start) & (nd["date"] <= q_end)
        raw_texts = nd.loc[m_ticker & m_win, "headline"].dropna().astype(str).tolist()
        # Filter out empty strings
        texts = [t.strip() for t in raw_texts if t.strip()]
        log.info("Trust media tone: %s has %d non-empty headlines (from %d total)", symbol, len(texts), len(raw_texts))

    if texts:
        scores = None
        # Try FinBERT first
        try:
            scores = finbert_score(texts)
            if scores:
                log.info("FinBERT scored %d headlines for %s", len(scores), symbol)
                print(f"[SENTIMENT] FinBERT scored {len(scores)} headlines for {symbol}")
        except Exception as e:
            log.warning("FinBERT failed for %s: %s", symbol, e)
            print(f"[SENTIMENT] FinBERT failed for {symbol}: {e}")
            scores = None

        if scores:
            raw = float(np.mean(scores))
            media_tone_raw = float(np.clip(raw * 0.6, -0.5, 0.5))
            media_tone_src = "ProsusAI/finbert"
            media_tone_n   = int(len(scores))
        else:
            # Fallback to VADER - this should always work
            print(f"[SENTIMENT] Trying VADER for {symbol} with {len(texts)} texts...")
            try:
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                sia = SentimentIntensityAnalyzer()
                vs = [sia.polarity_scores(t)["compound"] for t in texts]
                if vs:
                    raw = float(np.mean(vs))
                    media_tone_raw = float(np.clip(raw * 0.4, -0.3, 0.3))
                    media_tone_src = "vader"
                    media_tone_n   = int(len(vs))
                    log.info("VADER scored %d headlines for %s, mean=%.3f", len(vs), symbol, raw)
                    print(f"[SENTIMENT] VADER success for {symbol}: {len(vs)} headlines, mean={raw:.4f}, media_tone_raw={media_tone_raw:.4f}")
                else:
                    print(f"[SENTIMENT] VADER returned empty list for {symbol}")
            except Exception as e:
                log.warning("VADER also failed for %s: %s", symbol, e)
                print(f"[SENTIMENT] VADER failed for {symbol}: {e}")
    else:
        print(f"[SENTIMENT] No texts found for {symbol}")

    if np.isfinite(media_tone_raw):
        k = 4.0  # reliability shrink
        shrink = media_tone_n / (media_tone_n + k) if media_tone_n > 0 else 0.0
        media_tone_raw = float(np.clip(media_tone_raw * shrink, -0.6, 0.6))

    return {
        "event_calm_raw": event_calm_raw,
        "baseline_calm_raw": baseline_calm_raw,
        "media_tone_raw": media_tone_raw,
        "media_tone_src": media_tone_src,
        "media_tone_n": media_tone_n,
        "event_count": event_count,
    }

def trust_snapshot(
    symbols,
    start: str | None = None,
    end: str | None = None,
    news_df=None,
    as_of=None,  # unused here; kept for CLI symmetry
    apikey: str | None = None,
    s=None,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Build a per-ticker Trust snapshot for [start, end].
    Output columns:
      ticker, quarter_end, trust_pct(=sentiment_pct), p_event_calm, p_baseline_calm, p_media_tone, event_count
      + the raw diagnostics
    """
    if start is None or end is None:
        raise ValueError("trust_snapshot requires start and end (e.g., 2025-04-01 and 2025-06-30).")

    q_start = pd.to_datetime(start, utc=True)
    q_end   = pd.to_datetime(end, utc=True)

        # Robust FF import (prefer get_ff_factors_daily; fall back to load_ff_factors_daily)
    _ff_loader = None
    try:
        from .ff import get_ff_factors_daily as _ff_loader  # preferred
    except Exception:
        try:
            from .ff import load_ff_factors_daily as _ff_loader  # fallback
        except Exception:
            _ff_loader = None
    if _ff_loader is None:
        raise ImportError("Could not import Fama–French factor loader from irci.ff")

    # Some loaders expect (s, ...), others only keyword args. Try both.
    _s = s or Settings.load()
    try:
        ff = _ff_loader(_s, start=q_start, end=q_end, cache=True)
    except TypeError:
        ff = _ff_loader(start=q_start, end=q_end, cache=True)


    s = s or Settings.load()
    if isinstance(symbols, str):
        syms = [t.strip().upper() for t in symbols.split(",") if t.strip()]
    else:
        syms = [str(t).strip().upper() for t in symbols if str(t).strip()]
    if not syms:
        return pd.DataFrame(columns=["ticker","trust_pct","sentiment_pct",
                                     "p_event_calm","p_baseline_calm","p_media_tone",
                                     "event_count","quarter_end"])

    rows = []
    for sym in syms:
        rec = trust_quarter_for_symbol(sym, q_start, q_end, ff, news_df=news_df, apikey=apikey, s=s, weights=weights)
        rec["ticker"] = sym
        rows.append(rec)

    df = pd.DataFrame(rows)

    # Percentile ranks across peers (median-anchored 0..100, higher is better)
    df["p_event_calm"]    = median_anchored_pct(df["event_calm_raw"],   lower_is_better=False)
    df["p_baseline_calm"] = median_anchored_pct(df["baseline_calm_raw"], lower_is_better=False)
    df["p_media_tone"]    = median_anchored_pct(df["media_tone_raw"],    lower_is_better=False)
    # Weighted blend (renormalize if some sub-dials are NaN)
    W = _coerce_weights(weights)
    w_event, w_base, w_media = W.w_event_calm, W.w_baseline_calm, W.w_media_tone

    def _wavg_trust(row):
        vals, wts = [], []
        if pd.notna(row.get("p_event_calm")):
            vals.append(row["p_event_calm"]); wts.append(w_event)
        if pd.notna(row.get("p_baseline_calm")):
            vals.append(row["p_baseline_calm"]); wts.append(w_base)
        if pd.notna(row.get("p_media_tone")):
            vals.append(row["p_media_tone"]); wts.append(w_media)
        if not wts:
            return np.nan
        return float(np.average(vals, weights=wts))

    df["trust_pct"] = df.apply(_wavg_trust, axis=1)
    df["sentiment_pct"] = df["trust_pct"]
    df["quarter_end"] = q_end

    keep = ["ticker","quarter_end","trust_pct","sentiment_pct",
            "p_event_calm","p_baseline_calm","p_media_tone",
            "event_calm_raw","baseline_calm_raw","media_tone_raw",
            "media_tone_src","media_tone_n","event_count"]
    return df[keep].sort_values(["ticker"]).reset_index(drop=True)



# DISABLE_DEMO: # build one combined news_df for multiple tickers
# DISABLE_DEMO: news_list = []
# DISABLE_DEMO: for t in ["AAPL","MSFT"]:
# DISABLE_DEMO:     raw = load_news(t, q_start, q_end, s.data_root)  # columns: published_at, url, domain, lang, headline
# DISABLE_DEMO:     if raw is not None and not raw.empty:
# DISABLE_DEMO:         tmp = raw.rename(columns={"published_at":"date", "headline":"title"}).copy()
# DISABLE_DEMO:         tmp["ticker"] = t
# DISABLE_DEMO:         news_list.append(tmp)
# DISABLE_DEMO: news_df = pd.concat(news_list, ignore_index=True) if news_list else None
# DISABLE_DEMO: 
# DISABLE_DEMO: if __name__ == "__main__":
# DISABLE_DEMO:     from irci.media_store import load_news
# DISABLE_DEMO: 
# DISABLE_DEMO: 
# DISABLE_DEMO:     # Build combined news_df (published_at→date, headline→title)
# DISABLE_DEMO:     news_list = []
# DISABLE_DEMO:     for t in ["AAPL", "MSFT"]:
# DISABLE_DEMO:         raw = load_news(t, q_start, q_end, s.data_root)  # published_at, url, domain, lang, headline
# DISABLE_DEMO:         if raw is not None and not raw.empty:
# DISABLE_DEMO:             tmp = raw.rename(columns={"published_at": "date", "headline": "title"}).copy()
# DISABLE_DEMO:             tmp["ticker"] = t
# DISABLE_DEMO:             news_list.append(tmp)
# DISABLE_DEMO:     news_df = pd.concat(news_list, ignore_index=True) if news_list else None
# DISABLE_DEMO: 
# DISABLE_DEMO:     df_trust = trust_snapshot(["AAPL", "MSFT"], as_of=as_of, news_df=news_df)
# DISABLE_DEMO:     print(df_trust[[
# DISABLE_DEMO:         "ticker","quarter_end","trust_pct","p_event_calm","p_baseline_calm","p_media_tone",
# DISABLE_DEMO:         "event_calm_raw","baseline_calm_raw","media_tone_raw","media_tone_src","media_tone_n","event_count"
# DISABLE_DEMO:     ]].tail().to_string(index=False))
