from __future__ import annotations
from pathlib import Path
import pandas as pd

def _path_for(ticker: str, data_root: Path, ext: str = "parquet") -> Path:
    return Path(data_root) / "news" / f"{ticker.upper()}.{ext}"

def upsert_news_rows(ticker: str, rows: list[dict], data_root: Path) -> None:
    """Append rows and de-dupe by URL."""
    p = _path_for(ticker, data_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows)
    if "url" not in new.columns or new.empty:
        return
    if p.exists():
        old = pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)
        df = pd.concat([old, new], ignore_index=True)
    else:
        df = new
    df["url"] = df["url"].astype(str).str.strip()
    df = df.dropna(subset=["url"]).drop_duplicates(subset=["url"])
    if p.suffix == ".parquet":
        df.to_parquet(p, index=False)
    else:
        df.to_csv(p, index=False)

def _paths_for(ticker: str, data_root: Path):
    base = Path(data_root) / "news" / ticker.upper()
    return base.with_suffix(".parquet"), base.with_suffix(".csv")

def load_news(ticker: str, q_start, q_end, data_root: Path) -> pd.DataFrame:
    p_parq, p_csv = _paths_for(ticker, data_root)
    if p_parq.exists():
        df = pd.read_parquet(p_parq)
    elif p_csv.exists():
        df = pd.read_csv(p_csv)
    else:
        return pd.DataFrame(columns=["published_at","url","domain","lang","headline","source"])

    if "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df = df[(df["published_at"] >= q_start) & (df["published_at"] <= q_end)]
    return df