# irci/coverage.py
from __future__ import annotations

from typing import List, Tuple, Optional, Callable, Dict
import numpy as np
import pandas as pd
import requests
from urllib.parse import urlparse

from .config import Settings
from .logging import get_logger

log = get_logger("irci.coverage")

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def _headers(s: Settings) -> dict:
    return {"User-Agent": s.user_agent, "Accept-Encoding": "gzip"}

def _to_quarter_bucket(dt_series: pd.Series) -> pd.Series:
    """
    Convert datetimes to quarter-end buckets (UTC midnight) without tz warnings.
    """
    dt = pd.to_datetime(dt_series, utc=True)
    return (
        dt.dt.tz_convert("UTC").dt.tz_localize(None)
          .dt.to_period("Q").dt.end_time
          .dt.tz_localize("UTC").dt.normalize()
    )

# In-memory cache for the SEC ticker map during a single run
_TICKER_MAP_DF: Optional[pd.DataFrame] = None

def _ticker_map(s: Settings) -> pd.DataFrame:
    """
    SEC master map Ticker -> CIK. Cached for the process lifetime.
    """
    global _TICKER_MAP_DF
    if _TICKER_MAP_DF is not None:
        return _TICKER_MAP_DF

    url = "https://www.sec.gov/files/company_tickers.json"
    log.info(f"GET {url}")
    r = requests.get(url, headers=_headers(s), timeout=60)
    r.raise_for_status()
    js = r.json()
    rows = [
        {"cik": int(v["cik_str"]), "ticker": v["ticker"].upper(), "name": v["title"]}
        for _, v in js.items()
    ]
    df = pd.DataFrame(rows).set_index("ticker")
    _TICKER_MAP_DF = df
    return df

def _cik_for_ticker(ticker: str, s: Settings) -> str:
    m = _ticker_map(s)
    t = ticker.upper()
    if t not in m.index:
        raise ValueError(f"SEC could not find CIK for {ticker}")
    return f"{int(m.loc[t, 'cik']):010d}"

def _company_submissions(cik: str, s: Settings) -> pd.DataFrame:
    """
    Pull the company's 'recent filings' table from the submissions JSON.
    Uses filingDate (tz-aware) and form; reportDate used only as auxiliary.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    log.info(f"GET {url}")
    r = requests.get(url, headers=_headers(s), timeout=60)
    r.raise_for_status()
    js = r.json()
    rec = js.get("filings", {}).get("recent", {})
    df = pd.DataFrame(rec)
    if df.empty:
        return df

    # Normalize types
    if "filingDate" in df.columns:
        df["filingDate"] = pd.to_datetime(df["filingDate"], utc=True, errors="coerce")
    if "reportDate" in df.columns:
        df["reportDate"] = pd.to_datetime(df["reportDate"], utc=True, errors="coerce")
    if "form" in df.columns:
        df["form"] = df["form"].astype(str)
    return df

def _quarter_window(as_of) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Given a reference date, return the UTC start/end of that quarter.
    """
    ts = pd.to_datetime(as_of, utc=True)
    p = ts.to_period("Q")
    start = p.start_time.tz_localize("UTC")
    end = p.end_time.tz_localize("UTC")
    return start, end

def _pct_rank(series: pd.Series, *, higher_is_better: bool, neutral: float = 50.0) -> pd.Series:
    """
    Percentile rank in [0,100]. NaNs map to `neutral`. If the entire series is NaN, return all neutral.
    """
    s = series.copy()
    mask = s.notna()
    if mask.sum() == 0:
        return pd.Series(neutral, index=s.index)
    out = pd.Series(np.nan, index=s.index)
    out.loc[mask] = s.loc[mask].rank(pct=True, ascending=not higher_is_better, method="average") * 100.0
    return out.fillna(neutral)

# ---------- Media visibility helpers (optional input to Coverage) ----------

def _domain_weights(s: Settings) -> Dict[str, float]:
    """
    Map of domain -> credibility/reach weight in [0.25, 1.0].
    Prefer Settings.domain_weights if present; else default midpoint 0.5.
    """
    try:
        dw = getattr(s, "domain_weights", None)
        if isinstance(dw, dict):
            # Normalize to [0.25, 1.0]
            return {k.lower(): float(max(0.25, min(1.0, v))) for k, v in dw.items()}
    except Exception:
        pass
    return {}

def _media_visibility(
    ticker: str,
    q_start: pd.Timestamp,
    q_end: pd.Timestamp,
    s: Settings,
    media_fetcher: Optional[Callable[[str, pd.Timestamp, pd.Timestamp, Settings], pd.DataFrame]] = None,
) -> dict:
    """
    Compute media visibility metrics for the quarter.
    Expects media_fetcher to return columns: published_at, url, [domain], [lang].
    Sentiment/tone is explicitly excluded (belongs to Trust).
    """
    if media_fetcher is None:
        return {"q_media_weighted": np.nan, "q_media_unique_articles": np.nan, "q_media_unique_domains": np.nan}

    df = media_fetcher(ticker, q_start, q_end, s)
    if df is None or len(df) == 0:
        return {"q_media_weighted": np.nan, "q_media_unique_articles": 0, "q_media_unique_domains": 0}

    df = df.copy()
    if "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]

    if "url" not in df.columns:
        return {"q_media_weighted": np.nan, "q_media_unique_articles": 0, "q_media_unique_domains": 0}

    df["url"] = df["url"].astype(str).str.strip()
    df = df.dropna(subset=["url"]).drop_duplicates(subset=["url"])

    if "domain" not in df.columns:
        df["domain"] = df["url"].map(lambda u: urlparse(u).netloc.lower() if isinstance(u, str) else None)

    df["domain"] = df["domain"].astype(str).str.lower().str.removeprefix("www.")

    # Optional language filter
    if "lang" in df.columns:
        df = df[df["lang"].fillna("en").str.startswith("en")]

    if df.empty:
        return {"q_media_weighted": np.nan, "q_media_unique_articles": 0, "q_media_unique_domains": 0}

    weights = _domain_weights(s)

    def w(dom: str) -> float:
        return float(weights.get(dom, 0.5))  # default mid-weight for unknown but not spammy domains

    q_media_weighted = float((df["domain"].map(w)).sum())
    q_media_unique_articles = int(df["url"].nunique())
    q_media_unique_domains = int(df["domain"].nunique())

    return {
        "q_media_weighted": q_media_weighted,
        "q_media_unique_articles": q_media_unique_articles,
        "q_media_unique_domains": q_media_unique_domains,
    }

# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------

def coverage_snapshot(
    symbols: List[str],
    as_of: str | None = None,
    lookahead_days: int = 90,
    media_fetcher: Optional[Callable[[str, pd.Timestamp, pd.Timestamp, Settings], pd.DataFrame]] = None,
    media_weight: float = 0.50,
) -> pd.DataFrame:
    """
    Coverage/Visibility dial (per quarter end = as_of bucket):
      - SEC cadence & timeliness (always)
      - Media visibility (optional): weighted unique reputable articles/domains
        NOTE: sentiment/tone is excluded (belongs to Trust)

    SEC metrics:
      - q_8k_count: # of 8-Ks filed during the quarter (cadence/visibility)
      - q_days_to_10q: days from quarter-end to first 10-Q (or 10-K in Q4) filing (timeliness; lower is better)

    Scoring:
      If media is provided:
        coverage_pct = w_media * p_media + w_8k * p_8k + w_time * p_timely
        default weights: w_media=0.50, w_8k=0.30, w_time=0.20
      Else:
        coverage_pct = 0.60 * p_8k + 0.40 * p_timely

    Returns columns:
      ticker, as_of, as_of_bucket, coverage_pct, q_8k_count, q_days_to_10q
      and if media present: q_media_weighted, q_media_unique_articles, q_media_unique_domains
    """
    s = Settings.load()
    as_of_ts = pd.to_datetime(as_of, utc=True) if as_of is not None else pd.Timestamp.utcnow(tz="UTC")
    q_start, q_end = _quarter_window(as_of_ts)

    rows = []
    for sym in [t.strip().upper() for t in symbols if t.strip()]:
        try:
            cik = _cik_for_ticker(sym, s)
            subs = _company_submissions(cik, s)
        except Exception as e:
            log.warning(f"SEC submissions unavailable for {sym}: {e}")
            row = {"ticker": sym, "as_of": q_end, "q_8k_count": np.nan, "q_days_to_10q": np.nan}
            row.update(_media_visibility(sym, q_start, q_end, s, media_fetcher=None))
            rows.append(row)
            continue

        if subs.empty or "filingDate" not in subs.columns or "form" not in subs.columns:
            row = {"ticker": sym, "as_of": q_end, "q_8k_count": np.nan, "q_days_to_10q": np.nan}
            row.update(_media_visibility(sym, q_start, q_end, s, media_fetcher=None))
            rows.append(row)
            continue

        # 8-K count within the current quarter
        in_q = (subs["filingDate"] >= q_start) & (subs["filingDate"] <= q_end)
        q_8k_count = int((subs.loc[in_q, "form"].isin(["8-K", "8-K/A"])).sum())

        # Timeliness: days from quarter-end to first 10-Q (or 10-K in Q4), within the lookahead window
        ten_x_forms = ["10-Q", "10-Q/A"]
        if q_end.to_period("Q").quarter == 4:
            ten_x_forms = ["10-K", "10-K/A"]

        post = (subs["filingDate"] > q_end) & (subs["filingDate"] <= q_end + pd.Timedelta(days=lookahead_days))
        f10 = subs.loc[post & subs["form"].isin(ten_x_forms)].sort_values("filingDate")
        q_days_to_10q = (f10.iloc[0]["filingDate"] - q_end).days if not f10.empty else np.nan

        media_metrics = _media_visibility(sym, q_start, q_end, s, media_fetcher=media_fetcher)

        row = {
            "ticker": sym,
            "as_of": q_end,               # use quarter end as the as_of for this dial
            "q_8k_count": q_8k_count,
            "q_days_to_10q": q_days_to_10q,
            **media_metrics,
        }
        rows.append(row)

    # --- assemble dataframe ---
    cov = pd.DataFrame(rows)

    # quarter bucket (UTC midnight) without tz warnings
    cov["as_of_bucket"] = _to_quarter_bucket(cov["as_of"])

    # percentile ranks within the cohort for this run
    cov["p_8k"] = _pct_rank(cov["q_8k_count"], higher_is_better=True)          # more 8-Ks -> better
    cov["p_timely"] = _pct_rank(cov["q_days_to_10q"], higher_is_better=False)  # fewer days -> better

    has_media = "q_media_weighted" in cov.columns and cov["q_media_weighted"].notna().any()
    if has_media:
        cov["p_media"] = _pct_rank(cov["q_media_weighted"], higher_is_better=True)

    # Blend weights
    if has_media and media_fetcher is not None:
        w_media = float(media_weight)
        w_8k = 0.30
        w_time = 0.20
        # If user sets media_weight != 0.50, scale the others proportionally (0.30 : 0.20)
        remainder = max(0.0, 1.0 - w_media)
        scale = remainder / (0.30 + 0.20) if (0.30 + 0.20) > 0 else 0.0
        w_8k *= scale
        w_time *= scale
        cov["coverage_pct"] = (w_8k * cov["p_8k"] + w_time * cov["p_timely"] + w_media * cov["p_media"]).round(1)
    else:
        cov["coverage_pct"] = (0.6 * cov["p_8k"] + 0.4 * cov["p_timely"]).round(1)

    # Order & return
    base_cols = ["ticker", "as_of", "as_of_bucket", "coverage_pct", "q_8k_count", "q_days_to_10q"]
    media_cols = ["q_media_weighted", "q_media_unique_articles", "q_media_unique_domains"] if has_media else []
    cov = cov[base_cols + media_cols].sort_values(["as_of_bucket", "ticker"]).reset_index(drop=True)
    return cov
