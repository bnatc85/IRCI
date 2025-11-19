# irci/peers.py
"""
Peer company discovery using FMP API
"""
import requests
import pandas as pd
from typing import List, Optional


def find_peers_by_industry(
    ticker: str,
    api_key: str,
    max_peers: int = 10,
    market_cap_tolerance: float = 3.0
) -> List[str]:
    """
    Find peer companies by industry and similar market cap.

    Args:
        ticker: Base ticker symbol
        api_key: FMP API key
        max_peers: Maximum number of peers to return
        market_cap_tolerance: Market cap ratio tolerance (e.g., 3.0 = within 3x size)

    Returns:
        List of peer ticker symbols (excluding the input ticker)
    """
    try:
        # Get company profile
        profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api_key}"
        profile_response = requests.get(profile_url, timeout=10)
        profile_response.raise_for_status()
        profile_data = profile_response.json()

        if not profile_data or not isinstance(profile_data, list):
            print(f"Warning: No profile data for {ticker}")
            return []

        company = profile_data[0]
        industry = company.get('industry')
        sector = company.get('sector')
        market_cap = company.get('mktCap', 0)

        if not industry:
            print(f"Warning: No industry data for {ticker}")
            return []

        # Get stock screener data for the sector
        screener_url = f"https://financialmodelingprep.com/api/v3/stock-screener?sector={sector}&limit=500&apikey={api_key}"
        screener_response = requests.get(screener_url, timeout=10)
        screener_response.raise_for_status()
        screener_data = screener_response.json()

        if not screener_data:
            print(f"Warning: No screener data for sector {sector}")
            return []

        # Convert to DataFrame
        df = pd.DataFrame(screener_data)

        # Filter by industry
        if 'industry' in df.columns:
            df = df[df['industry'] == industry]

        # Remove the input ticker
        df = df[df['symbol'] != ticker.upper()]

        # Filter by market cap range if available
        if market_cap and 'marketCap' in df.columns:
            min_cap = market_cap / market_cap_tolerance
            max_cap = market_cap * market_cap_tolerance
            df = df[(df['marketCap'] >= min_cap) & (df['marketCap'] <= max_cap)]

            # Sort by market cap similarity
            df['cap_diff'] = (df['marketCap'] - market_cap).abs()
            df = df.sort_values('cap_diff')

        # Return top peers
        peers = df['symbol'].head(max_peers).tolist()
        return peers

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch peers for {ticker}: {e}")
        return []
    except Exception as e:
        print(f"Warning: Error finding peers for {ticker}: {e}")
        return []


def find_peers_simple(ticker: str, api_key: str, max_peers: int = 5) -> List[str]:
    """
    Simple peer finder using FMP's stock peers endpoint.

    Args:
        ticker: Base ticker symbol
        api_key: FMP API key
        max_peers: Maximum number of peers to return

    Returns:
        List of peer ticker symbols
    """
    try:
        # Try FMP's peers endpoint first (if available)
        url = f"https://financialmodelingprep.com/api/v4/stock_peers?symbol={ticker}&apikey={api_key}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                peers_data = data[0]
                if 'peersList' in peers_data:
                    return peers_data['peersList'][:max_peers]

        # Fallback to industry-based search
        return find_peers_by_industry(ticker, api_key, max_peers)

    except Exception as e:
        print(f"Warning: Simple peer lookup failed for {ticker}: {e}")
        return find_peers_by_industry(ticker, api_key, max_peers)
