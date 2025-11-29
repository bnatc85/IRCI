# irci/peers.py
"""
Peer company discovery - curated peer groups for common tickers
"""
import requests
import pandas as pd
from typing import List, Optional

# Curated peer groups by industry/sector
PEER_GROUPS = {
    # Mega-cap Tech
    "AAPL": ["MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX", "ADBE"],
    "MSFT": ["AAPL", "GOOGL", "AMZN", "META", "ORCL", "ADBE", "CRM", "NVDA"],
    "GOOGL": ["META", "AAPL", "MSFT", "AMZN", "NFLX", "DIS", "SNAP", "PINS"],
    "META": ["GOOGL", "SNAP", "PINS", "TWTR", "AAPL", "MSFT", "NFLX"],
    "AMZN": ["WMT", "TGT", "COST", "EBAY", "SHOP", "AAPL", "MSFT", "GOOGL"],

    # Cloud/Enterprise Software
    "CRM": ["MSFT", "ORCL", "NOW", "WDAY", "ADBE", "SAP", "TEAM", "ZM"],
    "NOW": ["CRM", "WDAY", "SNOW", "DDOG", "MSFT", "ORCL"],
    "SNOW": ["DDOG", "MDB", "NET", "CRWD", "NOW", "PLTR"],

    # Semiconductors
    "NVDA": ["AMD", "INTC", "TSM", "QCOM", "AVGO", "MU", "ASML"],
    "AMD": ["NVDA", "INTC", "QCOM", "MU", "AVGO", "MRVL"],
    "INTC": ["AMD", "NVDA", "QCOM", "TXN", "AVGO", "MU"],

    # Auto/EV (US SEC filers with available data only)
    "TSLA": ["GM", "RIVN", "LCID"],
    "RIVN": ["TSLA", "LCID", "GM"],
    "LCID": ["RIVN", "TSLA", "GM"],
    "GM": ["TSLA", "RIVN", "LCID"],

    # Streaming/Entertainment
    "NFLX": ["DIS", "PSKY", "WBD", "CMCSA", "GOOGL", "AAPL"],
    "DIS": ["NFLX", "PSKY", "WBD", "CMCSA", "LYV"],

    # E-commerce
    "SHOP": ["AMZN", "EBAY", "ETSY", "WMT", "MELI"],
    "ETSY": ["SHOP", "EBAY", "AMZN", "PINS"],

    # Fintech/Payments
    "SQ": ["PYPL", "V", "MA", "ADYEN", "AFRM", "COIN"],
    "PYPL": ["SQ", "V", "MA", "ADYEN", "AFRM"],
    "V": ["MA", "PYPL", "AXP", "SQ"],
    "MA": ["V", "PYPL", "AXP", "SQ"],

    # Social Media
    "SNAP": ["PINS", "META", "GOOGL", "TWTR"],
    "PINS": ["SNAP", "ETSY", "META", "GOOGL"],

    # Cybersecurity
    "CRWD": ["PANW", "ZS", "FTNT", "S", "OKTA"],
    "PANW": ["CRWD", "FTNT", "ZS", "CHKP"],
    "ZS": ["CRWD", "PANW", "NET", "OKTA"],

    # Cloud Infrastructure
    "DDOG": ["SNOW", "NET", "ESTC", "SPLK", "MDB"],
    "NET": ["DDOG", "FSLY", "AKAMAI", "CRWD"],

    # Retail
    "WMT": ["TGT", "COST", "KR", "DG", "AMZN"],
    "TGT": ["WMT", "COST", "DG", "BBY"],
    "COST": ["WMT", "TGT", "BJ", "AMZN"],

    # Airlines
    "DAL": ["UAL", "AAL", "LUV", "JBLU", "SAVE"],
    "UAL": ["DAL", "AAL", "LUV", "JBLU"],
    "AAL": ["DAL", "UAL", "LUV", "JBLU"],

    # Banks
    "JPM": ["BAC", "WFC", "C", "GS", "MS"],
    "BAC": ["JPM", "WFC", "C", "USB", "PNC"],
    "WFC": ["JPM", "BAC", "C", "USB"],
}


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
    Simple peer finder using curated peer groups.

    Args:
        ticker: Base ticker symbol
        api_key: FMP API key (not used with curated approach)
        max_peers: Maximum number of peers to return

    Returns:
        List of peer ticker symbols
    """
    ticker_upper = ticker.upper()

    # Check curated peer groups first
    if ticker_upper in PEER_GROUPS:
        peers = PEER_GROUPS[ticker_upper][:max_peers]
        print(f"Found {len(peers)} curated peers for {ticker_upper}")
        return peers

    # If not in curated list, inform user
    print(f"No curated peers for {ticker_upper}. Add to PEER_GROUPS in irci/peers.py for this ticker.")
    return []
