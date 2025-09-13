
# irci/ff.py
from __future__ import annotations
from pathlib import Path
import io, zipfile, requests
import pandas as pd
from .config import Settings
from .logging import get_logger

log = get_logger("irci.ff")

_FF_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"

def _download_ff_daily() -> pd.DataFrame:
    log.info("Downloading daily Fama-French 5 factors...")
    r = requests.get(_FF_URL, timeout=90)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    raw_lines = z.read(name).decode("utf-8", errors="ignore").splitlines()

    # locate header line; handle variants
    hdr_idx = None
    for i, line in enumerate(raw_lines):
        s = line.strip()
        if not s:
            continue
        if ("Mkt-RF" in s or "Mkt_RF" in s) and ("RF" in s):
            hdr_idx = i
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 6 and (parts[0] == "" or parts[0].lower() != "date"):
                parts = ["Date"] + parts[1:]
                raw_lines[i] = ",".join(parts)
            break
    if hdr_idx is None:
        raise RuntimeError("Could not locate header in FF daily CSV")

    df = pd.read_csv(io.StringIO("\n".join(raw_lines[hdr_idx:])))
    df = df.rename(columns={c: c.strip() for c in df.columns})
    if "Date" not in df.columns:
        if "date" in df.columns:
            df = df.rename(columns={"date": "Date"})
        else:
            raise RuntimeError("FF CSV missing Date column after normalization")

    mask_date = df["Date"].astype(str).str.fullmatch(r"\d{8}")
    df = df.loc[mask_date].copy()

    df = df.rename(columns={"Date": "date", "Mkt-RF": "Mkt_RF"})
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", utc=True)
    df = df.set_index("date").sort_index()

    for c in ["Mkt_RF", "SMB", "HML", "RMW", "CMA", "RF"]:
        if c in df.columns:
            df[c] = df[c].astype(float) / 100.0

    return df[["Mkt_RF", "SMB", "HML", "RMW", "CMA", "RF"]]

def load_ff_factors_daily(start: str | None = None, end: str | None = None, cache: bool = True) -> pd.DataFrame:
    """Load daily Fama-French 5 factors; caches under data/ff_5f_daily.parquet."""
    s = Settings.load()
    path = s.data_dir / "ff_5f_daily.parquet"
    if cache and path.exists():
        df = pd.read_parquet(path)
    else:
        df = _download_ff_daily()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path)
        except Exception as e:
            log.warning("Could not cache FF factors: %s", e)
    if start:
        df = df[df.index >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df.index <= pd.Timestamp(end, tz="UTC")]
    return df
