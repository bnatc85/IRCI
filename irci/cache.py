# irci/cache.py
"""
Caching utilities for IRCI analysis.

Uses Streamlit's caching for web app and file-based caching for CLI.
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd

from .logging import get_logger

log = get_logger("irci.cache")

# Cache directory
CACHE_DIR = Path(os.getenv("IRCI_CACHE_DIR", ".cache/irci"))


def get_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def get_cached_result(cache_key: str, max_age_hours: int = 24) -> Optional[Dict]:
    """
    Retrieve cached result if it exists and is not expired.

    Args:
        cache_key: Unique identifier for the cached data
        max_age_hours: Maximum age in hours before cache expires

    Returns:
        Cached data dict or None if not found/expired
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)

        # Check expiration
        cached_time = datetime.fromisoformat(cached.get('timestamp', '2000-01-01'))
        if datetime.now() - cached_time > timedelta(hours=max_age_hours):
            log.debug(f"Cache expired for {cache_key}")
            return None

        log.info(f"Cache hit for {cache_key}")
        return cached.get('data')

    except Exception as e:
        log.warning(f"Cache read error for {cache_key}: {e}")
        return None


def set_cached_result(cache_key: str, data: Dict) -> None:
    """
    Store result in cache.

    Args:
        cache_key: Unique identifier for the cached data
        data: Data to cache (must be JSON-serializable)
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"

    try:
        cached = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_file, 'w') as f:
            json.dump(cached, f)
        log.debug(f"Cached result for {cache_key}")
    except Exception as e:
        log.warning(f"Cache write error for {cache_key}: {e}")


def clear_cache(max_age_hours: int = 0) -> int:
    """
    Clear cached files older than max_age_hours.

    Args:
        max_age_hours: Delete files older than this. 0 = delete all.

    Returns:
        Number of files deleted
    """
    if not CACHE_DIR.exists():
        return 0

    deleted = 0
    cutoff = datetime.now() - timedelta(hours=max_age_hours)

    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            if max_age_hours == 0:
                cache_file.unlink()
                deleted += 1
            else:
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if mtime < cutoff:
                    cache_file.unlink()
                    deleted += 1
        except Exception as e:
            log.warning(f"Could not delete cache file {cache_file}: {e}")

    log.info(f"Cleared {deleted} cache files")
    return deleted


def cache_analysis_results(
    tickers: List[str],
    quarter: str,
    results: Dict[str, pd.DataFrame]
) -> None:
    """
    Cache complete analysis results for a peer group and quarter.

    Args:
        tickers: List of ticker symbols
        quarter: Quarter string (e.g., '2024Q3')
        results: Dict of dataframes to cache
    """
    cache_key = get_cache_key(sorted(tickers), quarter)

    # Convert DataFrames to dicts for JSON serialization
    data = {}
    for key, df in results.items():
        if isinstance(df, pd.DataFrame):
            data[key] = df.to_dict(orient='records')
        else:
            data[key] = df

    set_cached_result(f"analysis_{cache_key}", data)


def get_cached_analysis(
    tickers: List[str],
    quarter: str,
    max_age_hours: int = 24
) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Retrieve cached analysis results.

    Args:
        tickers: List of ticker symbols
        quarter: Quarter string (e.g., '2024Q3')
        max_age_hours: Maximum age before cache expires

    Returns:
        Dict of dataframes or None if not cached
    """
    cache_key = get_cache_key(sorted(tickers), quarter)
    cached = get_cached_result(f"analysis_{cache_key}", max_age_hours)

    if cached is None:
        return None

    # Convert dicts back to DataFrames
    results = {}
    for key, data in cached.items():
        if isinstance(data, list):
            results[key] = pd.DataFrame(data)
        else:
            results[key] = data

    return results
