import pandas as pd
import numpy as np
import requests
from pathlib import Path
from .config import Settings

from .logging import get_logger

log = get_logger("irci.market")


def _fmp_hist_url(symbol: str, start: str, end: str, apikey: str) -> str:
    base = "https://financialmodelingprep.com/api/v3/historical-price-full"
    return f"{base}/{symbol}?from={start}&to={end}&apikey={apikey}"


def fetch_prices_fmp(symbol: str, start: str, end: str, apikey: str) -> pd.DataFrame:
    """
    Daily OHLCV loader with:
      1) local cache under data/prices/{symbol}.parquet (or .csv fallback)
      2) FMP API fetch
      3) fallback to Yahoo Finance (yfinance) if FMP 429/HTTP error
    Returns DataFrame with columns: open, high, low, close, adj_close, volume
    indexed by UTC datetimes ascending.
    """
    s = Settings.load()
    cache_dir = s.data_dir / "prices"
    cache_dir.mkdir(parents=True, exist_ok=True)
    pq_path = cache_dir / f"{symbol.upper()}.parquet"
    csv_path = cache_dir / f"{symbol.upper()}.csv"

    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.index = pd.to_datetime(df.index, utc=True)
        df = df.sort_index()
        cols = ["open", "high", "low", "close", "adj_close", "volume"]
        return df[cols]

    def _read_cache() -> pd.DataFrame | None:
        try:
            if pq_path.exists():
                df = pd.read_parquet(pq_path)
                return _normalize(df)
        except Exception:
            pass
        if csv_path.exists():
            df = pd.read_csv(csv_path, index_col=0)
            return _normalize(df)
        return None

    def _write_cache(df: pd.DataFrame):
        try:
            df.to_parquet(pq_path)
        except Exception:
            df.to_csv(csv_path)

    # 0) Try cache first
    cached = _read_cache()
    if cached is not None:
        lo = pd.Timestamp(start, tz="UTC")
        hi = pd.Timestamp(end, tz="UTC")
        have_range = (cached.index.min() <= lo) and (cached.index.max() >= hi)
        if have_range:
            return cached.loc[(cached.index >= lo) & (cached.index <= hi)].copy()

    # 1) Try FMP
    try:
        url = _fmp_hist_url(symbol, start, end, apikey)
        log.info(f"GET {url.replace(apikey, '***')}")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        js = r.json()
        hist = js.get("historical") or []
        if not hist:
            raise RuntimeError(f"FMP returned no data for {symbol}")
        df = pd.DataFrame(hist)
        # normalize
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date").sort_index()
        out = pd.DataFrame(index=df.index)
        out["open"] = df["open"].astype(float)
        out["high"] = df["high"].astype(float)
        out["low"] = df["low"].astype(float)
        out["close"] = df["close"].astype(float)
        # prefer adjClose if present, else close
        out["adj_close"] = df.get("adjClose", df["close"]).astype(float)
        out["volume"] = df["volume"].astype(float)
        # merge into cache
        merged = out if cached is None else pd.concat([cached, out]).drop_duplicates  # noqa: E999
    except Exception as e:
        # If this was a 429 or any HTTP error, fall back to yfinance
        try:
            status = getattr(e, "response", None).status_code if hasattr(e, "response") else None
        except Exception:
            status = None
        log.warning("FMP fetch failed for %s (%s). Falling back to yfinance.", symbol, e)
        try:
            import yfinance as yf
            yf_df = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
            if yf_df is None or yf_df.empty:
                raise RuntimeError(f"yfinance returned no data for {symbol}")
            yf_df.index = pd.to_datetime(yf_df.index, utc=True)
            out = pd.DataFrame(index=yf_df.index)
            out["open"] = yf_df["Open"].astype(float)
            out["high"] = yf_df["High"].astype(float)
            out["low"] = yf_df["Low"].astype(float)
            out["close"] = yf_df["Close"].astype(float)
            # Adj Close may be missing for some assets; fallback to close
            out["adj_close"] = yf_df.get("Adj Close", yf_df["Close"]).astype(float)
            out["volume"] = yf_df["Volume"].astype(float)
            merged = out if cached is None else pd.concat([cached, out]).sort_index().groupby(level=0).last()
            _write_cache(merged)
            lo = pd.Timestamp(start, tz="UTC"); hi = pd.Timestamp(end, tz="UTC")
            return merged.loc[(merged.index >= lo) & (merged.index <= hi)].copy()
        except Exception as e2:
            raise RuntimeError(f"Both FMP and yfinance failed for {symbol}: {e2}") from e

    # Save/return merged (FMP success path)
    merged = merged.sort_index().groupby(level=0).last()
    _write_cache(merged)
    lo = pd.Timestamp(start, tz="UTC"); hi = pd.Timestamp(end, tz="UTC")
    return merged.loc[(merged.index >= lo) & (merged.index <= hi)].copy()



def garman_klass_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    log_returns = (
        np.log(df["high"] / df["low"]) ** 2 / 2
        - (2 * np.log(2) - 1) * (np.log(df["close"] / df["open"]) ** 2)
    )
    return log_returns.rolling(window).mean().apply(np.sqrt)


def max_drawdown(series: pd.Series) -> pd.Series:
    """Rolling peak-to-trough drawdown since inception."""
    cummax = series.cummax()
    dd = (series / cummax) - 1.0
    return dd


def quarterly_features(df: pd.DataFrame, freq: str = "QE-DEC") -> pd.DataFrame:
    """Aggregate to quarter-end (default calendar year: QE-DEC)."""
    out = pd.DataFrame(index=df.resample(freq).last().index)

    q = df["adj_close"].resample(freq)
    out["q_return"] = q.last().pct_change()
    out["q_vol_gk"] = garman_klass_vol(df, 20).resample(freq).mean()
    out["q_drawdown"] = max_drawdown(df["adj_close"]).resample(freq).last()

    # Volume z-score within series
    vol_mean = df["volume"].resample(freq).mean()
    out["q_volume_z"] = (vol_mean - vol_mean.mean()) / vol_mean.std(ddof=0)
    
    out.index.name = "quarter_end"
    return out
