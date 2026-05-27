# irci/quantum_peers.py
"""
Quantum-Ready Optimal Peer Selection using QUBO/CQM Formulation

This module implements multi-dimensional peer selection optimization that:
1. Works NOW with classical optimizers (scipy, simulated annealing)
2. Ready for D-Wave quantum annealing when API access is available

The optimization selects peers that maximize analytical value by balancing:
- Similarity (sector, market cap, business model)
- Data quality (liquidity, coverage availability)
- Diversity (minimize redundant correlations)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import warnings

from .config import Settings
from .logging import get_logger

log = get_logger("irci.quantum_peers")

# Try to import D-Wave SDK (optional)
DWAVE_AVAILABLE = False
try:
    from dimod import BinaryQuadraticModel, CQM, Binary
    from dwave.system import LeapHybridCQMSampler, LeapHybridBQMSampler
    DWAVE_AVAILABLE = True
    log.info("D-Wave Ocean SDK available - quantum optimization enabled")
except ImportError:
    log.info("D-Wave Ocean SDK not installed - using classical optimization")


@dataclass
class PeerSelectionWeights:
    """Weights for multi-dimensional peer similarity scoring."""
    market_cap_log: float = 0.20        # Log market cap similarity
    sector_match: float = 0.25          # Same sector/industry bonus
    analyst_coverage_ratio: float = 0.10  # Similar analyst coverage
    liquidity_score: float = 0.15       # IRCI liquidity dial similarity
    trading_volume_pattern: float = 0.10  # Volume profile similarity
    geographic_exposure: float = 0.05   # US vs international revenue
    institutional_ownership: float = 0.10  # Similar inst. ownership %
    correlation_penalty: float = 0.05   # Penalize highly correlated pairs

    def normalize(self) -> 'PeerSelectionWeights':
        """Normalize weights to sum to 1.0 (excluding penalty)."""
        total = (self.market_cap_log + self.sector_match +
                 self.analyst_coverage_ratio + self.liquidity_score +
                 self.trading_volume_pattern + self.geographic_exposure +
                 self.institutional_ownership)
        if total > 0:
            return PeerSelectionWeights(
                market_cap_log=self.market_cap_log / total,
                sector_match=self.sector_match / total,
                analyst_coverage_ratio=self.analyst_coverage_ratio / total,
                liquidity_score=self.liquidity_score / total,
                trading_volume_pattern=self.trading_volume_pattern / total,
                geographic_exposure=self.geographic_exposure / total,
                institutional_ownership=self.institutional_ownership / total,
                correlation_penalty=self.correlation_penalty
            )
        return self

    def to_dict(self) -> Dict[str, float]:
        return {
            'market_cap_log': self.market_cap_log,
            'sector_match': self.sector_match,
            'analyst_coverage_ratio': self.analyst_coverage_ratio,
            'liquidity_score': self.liquidity_score,
            'trading_volume_pattern': self.trading_volume_pattern,
            'geographic_exposure': self.geographic_exposure,
            'institutional_ownership': self.institutional_ownership,
            'correlation_penalty': self.correlation_penalty
        }


@dataclass
class CandidateStock:
    """Stock candidate with multi-dimensional features for peer selection."""
    ticker: str
    market_cap: float = np.nan
    sector: str = ""
    industry: str = ""
    analyst_count: int = 0
    liquidity_score: float = np.nan
    avg_volume: float = np.nan
    institutional_pct: float = np.nan
    us_revenue_pct: float = np.nan  # Domestic vs international
    returns_60d: Optional[np.ndarray] = None  # For correlation calc

    # Computed similarity scores (filled during optimization)
    similarity_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'market_cap': self.market_cap,
            'sector': self.sector,
            'industry': self.industry,
            'analyst_count': self.analyst_count,
            'liquidity_score': self.liquidity_score,
            'avg_volume': self.avg_volume,
            'institutional_pct': self.institutional_pct,
            'us_revenue_pct': self.us_revenue_pct,
            'similarity_score': self.similarity_score
        }


class QuantumPeerSelector:
    """
    Quantum-ready peer selection optimizer.

    Uses QUBO (Quadratic Unconstrained Binary Optimization) formulation
    that can run on:
    - Classical: scipy minimize, simulated annealing
    - Quantum: D-Wave hybrid solvers (when available)
    """

    def __init__(
        self,
        target_ticker: str,
        weights: Optional[PeerSelectionWeights] = None,
        settings: Optional[Settings] = None,
        use_quantum: bool = False
    ):
        self.target_ticker = target_ticker.upper()
        self.weights = (weights or PeerSelectionWeights()).normalize()
        self.settings = settings or Settings.load()
        self.use_quantum = use_quantum and DWAVE_AVAILABLE

        self.target_features: Optional[CandidateStock] = None
        self.candidates: List[CandidateStock] = []
        self.similarity_matrix: Optional[np.ndarray] = None
        self.correlation_matrix: Optional[np.ndarray] = None

    def fetch_candidate_features(
        self,
        candidates: List[str],
        include_target: bool = True
    ) -> List[CandidateStock]:
        """
        Fetch multi-dimensional features for candidate stocks.

        Args:
            candidates: List of ticker symbols to evaluate
            include_target: Whether to fetch target stock features too

        Returns:
            List of CandidateStock objects with features
        """
        import yfinance as yf
        from .institutional_ownership import get_institutional_ownership

        all_tickers = candidates.copy()
        if include_target and self.target_ticker not in all_tickers:
            all_tickers.insert(0, self.target_ticker)

        stocks = []
        log.info(f"Fetching features for {len(all_tickers)} candidates...")

        for ticker in all_tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                # Get historical data for volume and returns
                hist = stock.history(period="3mo")
                returns_60d = None
                avg_volume = np.nan

                if not hist.empty:
                    avg_volume = hist['Volume'].mean()
                    if len(hist) >= 20:
                        returns_60d = hist['Close'].pct_change().dropna().values[-60:]

                # Get institutional ownership
                inst_data = get_institutional_ownership(ticker, self.settings)
                inst_pct = inst_data.get('institutional_ownership_pct', np.nan)

                candidate = CandidateStock(
                    ticker=ticker,
                    market_cap=info.get('marketCap', np.nan),
                    sector=info.get('sector', ''),
                    industry=info.get('industry', ''),
                    analyst_count=info.get('numberOfAnalystOpinions', 0) or 0,
                    avg_volume=avg_volume,
                    institutional_pct=inst_pct if not np.isnan(inst_pct) else np.nan,
                    us_revenue_pct=100.0,  # Default, could fetch from financials
                    returns_60d=returns_60d
                )

                stocks.append(candidate)
                log.debug(f"  {ticker}: mcap={candidate.market_cap:.0f}, sector={candidate.sector}")

            except Exception as e:
                log.warning(f"Failed to fetch features for {ticker}: {e}")
                stocks.append(CandidateStock(ticker=ticker))

        # Separate target from candidates
        self.candidates = [s for s in stocks if s.ticker != self.target_ticker]
        target_matches = [s for s in stocks if s.ticker == self.target_ticker]
        if target_matches:
            self.target_features = target_matches[0]

        return stocks

    def compute_similarity_matrix(self) -> np.ndarray:
        """
        Compute pairwise similarity scores between target and all candidates.

        Returns:
            Array of similarity scores for each candidate (higher = more similar)
        """
        if self.target_features is None:
            raise ValueError("Must fetch candidate features first")

        n = len(self.candidates)
        similarities = np.zeros(n)
        w = self.weights

        target = self.target_features
        target_mcap_log = np.log10(target.market_cap) if target.market_cap > 0 else 0

        for i, cand in enumerate(self.candidates):
            score = 0.0

            # 1. Market cap similarity (log scale, normalized)
            if cand.market_cap > 0 and target.market_cap > 0:
                cand_mcap_log = np.log10(cand.market_cap)
                # Score: 1.0 if same size, decays with difference
                mcap_diff = abs(cand_mcap_log - target_mcap_log)
                mcap_sim = max(0, 1 - mcap_diff / 3)  # 3 orders of magnitude = 0
                score += w.market_cap_log * mcap_sim

            # 2. Sector/Industry match
            sector_sim = 0.0
            if cand.sector and target.sector:
                if cand.industry == target.industry:
                    sector_sim = 1.0
                elif cand.sector == target.sector:
                    sector_sim = 0.7
            score += w.sector_match * sector_sim

            # 3. Analyst coverage similarity
            if target.analyst_count > 0 and cand.analyst_count > 0:
                coverage_ratio = min(cand.analyst_count, target.analyst_count) / max(cand.analyst_count, target.analyst_count)
                score += w.analyst_coverage_ratio * coverage_ratio

            # 4. Liquidity score similarity (if available)
            if not np.isnan(cand.liquidity_score) and not np.isnan(target.liquidity_score):
                liq_diff = abs(cand.liquidity_score - target.liquidity_score) / 100
                liq_sim = max(0, 1 - liq_diff)
                score += w.liquidity_score * liq_sim

            # 5. Volume pattern similarity
            if not np.isnan(cand.avg_volume) and not np.isnan(target.avg_volume):
                vol_ratio = min(cand.avg_volume, target.avg_volume) / max(cand.avg_volume, target.avg_volume)
                score += w.trading_volume_pattern * vol_ratio

            # 6. Geographic exposure (placeholder - same region bonus)
            geo_sim = 0.5  # Default moderate similarity
            score += w.geographic_exposure * geo_sim

            # 7. Institutional ownership similarity
            if not np.isnan(cand.institutional_pct) and not np.isnan(target.institutional_pct):
                inst_diff = abs(cand.institutional_pct - target.institutional_pct) / 100
                inst_sim = max(0, 1 - inst_diff)
                score += w.institutional_ownership * inst_sim

            similarities[i] = score
            cand.similarity_score = score

        self.similarity_matrix = similarities
        return similarities

    def compute_correlation_matrix(self) -> np.ndarray:
        """
        Compute pairwise return correlations between candidates.

        High correlation between selected peers = redundant information.
        We want diverse peers, so we penalize selecting highly correlated pairs.

        Returns:
            n x n correlation matrix
        """
        n = len(self.candidates)
        corr = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                ret_i = self.candidates[i].returns_60d
                ret_j = self.candidates[j].returns_60d

                if ret_i is not None and ret_j is not None:
                    min_len = min(len(ret_i), len(ret_j))
                    if min_len >= 20:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            c = np.corrcoef(ret_i[-min_len:], ret_j[-min_len:])[0, 1]
                            if not np.isnan(c):
                                corr[i, j] = c
                                corr[j, i] = c

        self.correlation_matrix = corr
        return corr

    def build_qubo(self, num_peers: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build QUBO matrix for peer selection optimization.

        The QUBO formulation:
        - Linear terms: -similarity[i] (maximize similarity)
        - Quadratic terms: +correlation[i,j] * penalty (minimize redundancy)
        - Constraint: sum(x) == num_peers (select exactly N peers)

        Args:
            num_peers: Number of peers to select

        Returns:
            Tuple of (linear_coeffs, quadratic_coeffs) for QUBO
        """
        if self.similarity_matrix is None:
            self.compute_similarity_matrix()
        if self.correlation_matrix is None:
            self.compute_correlation_matrix()

        n = len(self.candidates)

        # Linear terms: negative similarity (we minimize, so negate to maximize)
        linear = -self.similarity_matrix.copy()

        # Quadratic terms: correlation penalty for selecting correlated pairs
        quadratic = self.correlation_matrix * self.weights.correlation_penalty

        return linear, quadratic

    def solve_classical(
        self,
        num_peers: int = 10,
        method: str = 'simulated_annealing'
    ) -> List[str]:
        """
        Solve peer selection using classical optimization.

        Args:
            num_peers: Number of peers to select
            method: 'simulated_annealing', 'greedy', or 'exhaustive' (small n only)

        Returns:
            List of selected peer tickers
        """
        linear, quadratic = self.build_qubo(num_peers)
        n = len(self.candidates)

        if method == 'greedy':
            return self._solve_greedy(linear, quadratic, num_peers)
        elif method == 'simulated_annealing':
            return self._solve_simulated_annealing(linear, quadratic, num_peers)
        elif method == 'exhaustive' and n <= 20:
            return self._solve_exhaustive(linear, quadratic, num_peers)
        else:
            log.warning(f"Method {method} not available, using greedy")
            return self._solve_greedy(linear, quadratic, num_peers)

    def _solve_greedy(
        self,
        linear: np.ndarray,
        quadratic: np.ndarray,
        num_peers: int
    ) -> List[str]:
        """Greedy selection: pick highest similarity, adjust for correlation."""
        selected_idx = []
        available = set(range(len(self.candidates)))

        for _ in range(num_peers):
            if not available:
                break

            best_idx = None
            best_score = float('inf')

            for i in available:
                # Score = linear term + quadratic penalty with already selected
                score = linear[i]
                for j in selected_idx:
                    score += quadratic[i, j]

                if score < best_score:
                    best_score = score
                    best_idx = i

            if best_idx is not None:
                selected_idx.append(best_idx)
                available.remove(best_idx)

        selected_tickers = [self.candidates[i].ticker for i in selected_idx]
        log.info(f"Greedy selection: {selected_tickers}")
        return selected_tickers

    def _solve_simulated_annealing(
        self,
        linear: np.ndarray,
        quadratic: np.ndarray,
        num_peers: int,
        max_iter: int = 10000,
        temp_start: float = 1.0,
        temp_end: float = 0.001
    ) -> List[str]:
        """Simulated annealing for QUBO optimization."""
        n = len(self.candidates)

        # Initialize with greedy solution
        greedy_solution = self._solve_greedy(linear, quadratic, num_peers)
        current = np.zeros(n, dtype=int)
        for ticker in greedy_solution:
            idx = next(i for i, c in enumerate(self.candidates) if c.ticker == ticker)
            current[idx] = 1

        def energy(x):
            """QUBO energy function."""
            e = np.dot(linear, x) + x @ quadratic @ x
            # Constraint penalty: must select exactly num_peers
            constraint_violation = abs(x.sum() - num_peers)
            e += 100 * constraint_violation  # Heavy penalty
            return e

        best = current.copy()
        best_energy = energy(best)
        current_energy = best_energy

        for iteration in range(max_iter):
            # Temperature schedule
            temp = temp_start * (temp_end / temp_start) ** (iteration / max_iter)

            # Propose swap: flip one 0->1 and one 1->0
            ones = np.where(current == 1)[0]
            zeros = np.where(current == 0)[0]

            if len(ones) == 0 or len(zeros) == 0:
                continue

            proposal = current.copy()
            flip_out = np.random.choice(ones)
            flip_in = np.random.choice(zeros)
            proposal[flip_out] = 0
            proposal[flip_in] = 1

            proposal_energy = energy(proposal)
            delta = proposal_energy - current_energy

            # Accept or reject
            if delta < 0 or np.random.random() < np.exp(-delta / temp):
                current = proposal
                current_energy = proposal_energy

                if current_energy < best_energy:
                    best = current.copy()
                    best_energy = current_energy

        selected_idx = np.where(best == 1)[0]
        selected_tickers = [self.candidates[i].ticker for i in selected_idx]
        log.info(f"Simulated annealing selection (energy={best_energy:.4f}): {selected_tickers}")
        return selected_tickers

    def _solve_exhaustive(
        self,
        linear: np.ndarray,
        quadratic: np.ndarray,
        num_peers: int
    ) -> List[str]:
        """Exhaustive search (only for small candidate pools)."""
        from itertools import combinations

        n = len(self.candidates)
        if n == 0:
            log.warning("No candidates available for exhaustive search")
            return []

        # Clamp num_peers to available candidates
        num_peers = min(num_peers, n)

        best_selection = None
        best_energy = float('inf')

        for combo in combinations(range(n), num_peers):
            x = np.zeros(n)
            x[list(combo)] = 1
            energy = np.dot(linear, x) + x @ quadratic @ x

            if energy < best_energy:
                best_energy = energy
                best_selection = combo

        if best_selection is None:
            log.warning("Exhaustive search found no valid selection")
            return []

        selected_tickers = [self.candidates[i].ticker for i in best_selection]
        log.info(f"Exhaustive selection (energy={best_energy:.4f}): {selected_tickers}")
        return selected_tickers

    def solve_quantum(self, num_peers: int = 10) -> List[str]:
        """
        Solve peer selection using D-Wave quantum annealer.

        Requires D-Wave Leap API access.

        Args:
            num_peers: Number of peers to select

        Returns:
            List of selected peer tickers
        """
        if not DWAVE_AVAILABLE:
            raise RuntimeError(
                "D-Wave Ocean SDK not installed. "
                "Install with: pip install dwave-ocean-sdk"
            )

        linear, quadratic = self.build_qubo(num_peers)
        n = len(self.candidates)

        # Build CQM (Constrained Quadratic Model)
        cqm = CQM()

        # Binary variables for each candidate
        x = {i: Binary(f'x_{self.candidates[i].ticker}') for i in range(n)}

        # Objective: minimize -similarity + correlation_penalty
        objective = sum(linear[i] * x[i] for i in range(n))
        for i in range(n):
            for j in range(i + 1, n):
                if quadratic[i, j] != 0:
                    objective += quadratic[i, j] * x[i] * x[j]

        cqm.set_objective(objective)

        # Constraint: select exactly num_peers
        cqm.add_constraint(
            sum(x.values()) == num_peers,
            label='peer_count'
        )

        # Solve on D-Wave
        log.info("Submitting to D-Wave quantum solver...")
        sampler = LeapHybridCQMSampler()
        result = sampler.sample_cqm(cqm, time_limit=10)

        # Get best feasible solution
        feasible = result.filter(lambda d: d.is_feasible)
        if len(feasible) == 0:
            log.warning("No feasible quantum solution, falling back to classical")
            return self.solve_classical(num_peers)

        best = feasible.first
        selected_idx = [i for i in range(n) if best.sample[f'x_{self.candidates[i].ticker}'] == 1]
        selected_tickers = [self.candidates[i].ticker for i in selected_idx]

        log.info(f"Quantum selection (energy={best.energy:.4f}): {selected_tickers}")
        return selected_tickers

    def select_optimal_peers(
        self,
        candidates: List[str],
        num_peers: int = 10,
        method: str = 'auto'
    ) -> Dict:
        """
        Main entry point: select optimal peers for the target stock.

        Args:
            candidates: List of candidate ticker symbols
            num_peers: Number of peers to select
            method: 'auto', 'quantum', 'simulated_annealing', 'greedy', 'exhaustive'

        Returns:
            Dict with selected peers and optimization metadata
        """
        # Fetch features
        self.fetch_candidate_features(candidates)

        if not self.candidates:
            log.warning(f"No valid candidates found for {self.target_ticker}")
            return {
                'target': self.target_ticker,
                'selected_peers': [],
                'num_requested': num_peers,
                'num_selected': 0,
                'method': method,
                'error': 'No valid candidate peers after data fetch'
            }

        # Compute similarity and correlation
        self.compute_similarity_matrix()
        self.compute_correlation_matrix()

        # Select solving method
        if method == 'auto':
            if self.use_quantum and DWAVE_AVAILABLE:
                method = 'quantum'
            elif len(candidates) <= 20:
                method = 'exhaustive'
            else:
                method = 'simulated_annealing'

        # Solve
        if method == 'quantum':
            selected = self.solve_quantum(num_peers)
        else:
            selected = self.solve_classical(num_peers, method)

        # Build result
        selected_details = []
        for ticker in selected:
            cand = next((c for c in self.candidates if c.ticker == ticker), None)
            if cand:
                selected_details.append(cand.to_dict())

        return {
            'target': self.target_ticker,
            'selected_peers': selected,
            'num_requested': num_peers,
            'num_selected': len(selected),
            'method': method,
            'weights': self.weights.to_dict(),
            'peer_details': selected_details,
            'quantum_available': DWAVE_AVAILABLE
        }


def find_optimal_peers(
    ticker: str,
    candidates: Optional[List[str]] = None,
    num_peers: int = 10,
    weights: Optional[Dict[str, float]] = None,
    settings: Optional[Settings] = None,
    use_quantum: bool = False
) -> Dict:
    """
    Convenience function to find optimal peers for a ticker.

    Args:
        ticker: Target stock ticker
        candidates: Optional list of candidates (if None, fetches from sector)
        num_peers: Number of peers to select
        weights: Optional dict of dimension weights
        settings: IRCI settings
        use_quantum: Whether to use D-Wave quantum solver

    Returns:
        Dict with selected peers and metadata
    """
    s = settings or Settings.load()

    # Build weights
    w = PeerSelectionWeights()
    if weights:
        for key, value in weights.items():
            if hasattr(w, key):
                setattr(w, key, value)

    # If no candidates provided, get sector peers
    if not candidates:
        from .peers import find_peers_by_industry
        candidates = find_peers_by_industry(ticker, s.fmp_api_key, max_peers=50)
        if not candidates:
            log.warning(f"No candidates found for {ticker}, using curated list")
            from .peers import PEER_GROUPS
            candidates = PEER_GROUPS.get(ticker.upper(), [])

    if not candidates:
        return {
            'target': ticker,
            'selected_peers': [],
            'error': 'No candidate peers found'
        }

    # Run optimization
    selector = QuantumPeerSelector(
        target_ticker=ticker,
        weights=w,
        settings=s,
        use_quantum=use_quantum
    )

    return selector.select_optimal_peers(
        candidates=candidates,
        num_peers=num_peers
    )
