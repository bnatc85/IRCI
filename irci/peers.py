# irci/peers.py
"""
Peer company discovery - curated peer groups and quantum-optimized selection

Supports three modes:
1. Curated: Hand-picked peer groups for common tickers
2. Industry: API-based sector/market-cap matching
3. Quantum-Optimized: Multi-dimensional QUBO optimization (classical or D-Wave)
"""
import requests
import pandas as pd
from typing import List, Optional, Dict

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


def find_peers_optimized(
    ticker: str,
    api_key: str,
    num_peers: int = 10,
    weights: Optional[Dict[str, float]] = None,
    use_quantum: bool = False,
    method: str = 'auto'
) -> Dict:
    """
    Find optimal peers using quantum-ready multi-dimensional optimization.

    This uses QUBO (Quadratic Unconstrained Binary Optimization) to select
    peers that maximize analytical value across multiple dimensions:
    - Market cap similarity
    - Sector/industry match
    - Analyst coverage ratio
    - Liquidity profile
    - Trading volume patterns
    - Institutional ownership
    - Return correlation diversity

    Args:
        ticker: Target ticker symbol
        api_key: FMP API key for fetching candidates
        num_peers: Number of peers to select (default: 10)
        weights: Optional dict of dimension weights, e.g.:
            {
                'market_cap_log': 0.20,
                'sector_match': 0.25,
                'analyst_coverage_ratio': 0.10,
                'liquidity_score': 0.15,
                'trading_volume_pattern': 0.10,
                'geographic_exposure': 0.05,
                'institutional_ownership': 0.10,
                'correlation_penalty': 0.05
            }
        use_quantum: If True and D-Wave SDK available, use quantum solver
        method: 'auto', 'quantum', 'simulated_annealing', 'greedy', 'exhaustive'

    Returns:
        Dict with:
            - selected_peers: List of optimal peer tickers
            - peer_details: List of dicts with peer features and similarity scores
            - method: Optimization method used
            - weights: Dimension weights applied
            - quantum_available: Whether D-Wave SDK is installed
    """
    from .quantum_peers import find_optimal_peers, PeerSelectionWeights
    from .config import Settings

    settings = Settings.load()
    settings.fmp_api_key = api_key

    # Get initial candidates from industry
    candidates = find_peers_by_industry(ticker, api_key, max_peers=50)

    # Add curated peers if available (ensures known good peers are considered)
    ticker_upper = ticker.upper()
    if ticker_upper in PEER_GROUPS:
        curated = PEER_GROUPS[ticker_upper]
        candidates = list(set(candidates + curated))

    if not candidates:
        return {
            'target': ticker,
            'selected_peers': [],
            'error': 'No candidate peers found'
        }

    # Run quantum-ready optimization
    result = find_optimal_peers(
        ticker=ticker,
        candidates=candidates,
        num_peers=num_peers,
        weights=weights,
        settings=settings,
        use_quantum=use_quantum
    )

    return result


def find_peers(
    ticker: str,
    api_key: str,
    max_peers: int = 10,
    mode: str = 'curated',
    optimize_weights: Optional[Dict[str, float]] = None,
    use_quantum: bool = False
) -> List[str]:
    """
    Unified peer finder with multiple modes.

    Args:
        ticker: Target ticker symbol
        api_key: FMP API key
        max_peers: Number of peers to return
        mode: Selection mode:
            - 'curated': Use hand-picked peer groups (fast, reliable)
            - 'industry': Use sector/market-cap matching via API
            - 'optimized': Use quantum-ready multi-dimensional optimization
        optimize_weights: Dimension weights for 'optimized' mode
        use_quantum: Use D-Wave quantum solver (requires API access)

    Returns:
        List of peer ticker symbols
    """
    ticker_upper = ticker.upper()

    if mode == 'curated':
        return find_peers_simple(ticker, api_key, max_peers)

    elif mode == 'industry':
        return find_peers_by_industry(ticker, api_key, max_peers)

    elif mode == 'optimized':
        result = find_peers_optimized(
            ticker=ticker,
            api_key=api_key,
            num_peers=max_peers,
            weights=optimize_weights,
            use_quantum=use_quantum
        )
        return result.get('selected_peers', [])

    else:
        print(f"Unknown mode '{mode}', falling back to curated")
        return find_peers_simple(ticker, api_key, max_peers)
