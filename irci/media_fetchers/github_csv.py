# irci/media_fetchers/github_csv.py
from __future__ import annotations
import pandas as pd
from pathlib import Path
from urllib.parse import urlparse

def github_csv_media_fetcher(ticker: str, q_start, q_end, settings) -> pd.DataFrame:
    """
    Load repo-stored news for `ticker` from data/news/{TICKER}.csv.
    Required cols: published_at, url. Optional: domain, lang.
    """
    root = Path(getattr(settings, "data_root", "."))  # e.g., repo root
    fp = root / "data" / "news" / f"{ticker.upper()}.csv"
    if not fp.exists():
        return pd.DataFrame(columns=["published_at","url","domain","lang"])

    df = pd.read_csv(fp)
    # Normalize
    if "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]
    df["url"] = df["url"].astype(str).str.strip()
    if "domain" not in df.columns:
        df["domain"] = df["url"].map(lambda u: urlparse(u).netloc.lower())
    df["lang"] = df.get("lang", "en")
    return df
