# irci/media_fetchers/github_repo.py
from __future__ import annotations
import pandas as pd
from urllib.parse import urlparse
from irci.media_store import load_news   # <-- fix: absolute import from irci.media_store

def github_repo_media_fetcher(ticker, q_start, q_end, s) -> pd.DataFrame:
    df = load_news(ticker, q_start, q_end, getattr(s, "data_root", "."))
    if df.empty:
        return df
    if "domain" not in df.columns:
        df["domain"] = df["url"].map(lambda u: urlparse(u).netloc.lower())
    if "lang" not in df.columns:
        df["lang"] = "en"
    return df
