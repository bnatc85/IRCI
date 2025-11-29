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
      3) fallback to Yahoo Finance (yfinance) if FMP/HTTP error

    Returns DataFrame indexed by UTC datetimes with columns:
    ['open','high','low','close','adj_close','volume'].
    """
    s = Settings.load()
    cache_dir = s.data_dir / "prices"
    cache_dir.mkdir(parents=True, exist_ok=True)
    pq_path = cache_dir / f"{symbol.upper()}.parquet"
    csv_path = cache_dir / f"{symbol.upper()}.csv"

    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["open","high","low","close","adj_close","volume"])
        out = df.copy()
        out.index = pd.to_datetime(out.index, utc=True)
        out = out.sort_index()
        cols = ["open","high","low","close","adj_close","volume"]
        # keep only expected cols (fill if missing)
        for c in cols:
            if c not in out.columns:
                out[c] = np.nan
        return out[cols]

    def _read_cache() -> pd.DataFrame | None:
        try:
            if pq_path.exists():
                return _normalize(pd.read_parquet(pq_path))
        except Exception:
            pass
        if csv_path.exists():
            return _normalize(pd.read_csv(csv_path, index_col=0))
        return None

    def _write_cache(df: pd.DataFrame):
        try:
            df.to_parquet(pq_path)
        except Exception:
            df.to_csv(csv_path)

    # normalize date bounds
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC")

    # 0) cache first
    cached = _read_cache()
    if cached is not None and not cached.empty:
        if cached.index.min() <= lo and cached.index.max() >= hi:
            return cached.loc[(cached.index >= lo) & (cached.index <= hi)].copy()

    # 1) FMP
    try:
        url = _fmp_hist_url(symbol, lo.date().isoformat(), hi.date().isoformat(), apikey)
        log.info(f"GET {url.replace(apikey, '***')}")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        js = r.json()
        hist = js.get("historical") or []
        if not hist:
            raise RuntimeError(f"FMP returned no data for {symbol}")

        df = pd.DataFrame(hist)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date").sort_index()

        out = pd.DataFrame(index=df.index)
        out["open"]      = df["open"].astype(float)
        out["high"]      = df["high"].astype(float)
        out["low"]       = df["low"].astype(float)
        out["close"]     = df["close"].astype(float)
        out["adj_close"] = df.get("adjClose", df["close"]).astype(float)
        out["volume"]    = df["volume"].astype(float)

        merged_df = out if cached is None else pd.concat([cached, out])
        merged_df = merged_df.sort_index().groupby(level=0).last()
        _write_cache(merged_df)
        return merged_df.loc[(merged_df.index >= lo) & (merged_df.index <= hi)].copy()

    except Exception as e:
        log.warning("FMP fetch failed for %s (%s). Falling back to yfinance.", symbol, e)

        # 2) yfinance fallback
        try:
            import yfinance as yf
            yf_df = yf.download(symbol, start=lo.date().isoformat(), end=hi.date().isoformat(),
                                auto_adjust=False, progress=False)
            if yf_df is None or yf_df.empty:
                raise RuntimeError(f"yfinance returned no data for {symbol}")

            yf_df.index = pd.to_datetime(yf_df.index, utc=True)
            out = pd.DataFrame(index=yf_df.index)
            out["open"]      = yf_df["Open"].astype(float)
            out["high"]      = yf_df["High"].astype(float)
            out["low"]       = yf_df["Low"].astype(float)
            out["close"]     = yf_df["Close"].astype(float)
            out["adj_close"] = yf_df.get("Adj Close", yf_df["Close"]).astype(float)
            out["volume"]    = yf_df["Volume"].astype(float)

            merged_df = out if cached is None else pd.concat([cached, out])
            merged_df = merged_df.sort_index().groupby(level=0).last()
            _write_cache(merged_df)
            return merged_df.loc[(merged_df.index >= lo) & (merged_df.index <= hi)].copy()

        except Exception as e2:
            # If we still have cache, return the slice we have; else raise.
            if cached is not None and not cached.empty:
                log.warning("Both FMP and yfinance failed; serving cached data for %s.", symbol)
                return cached.loc[(cached.index >= lo) & (cached.index <= hi)].copy()
            raise RuntimeError(f"Both FMP and yfinance failed for {symbol}: {e2}") from e




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
