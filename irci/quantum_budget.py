# irci/quantum_budget.py
"""
Quantum-Ready IR Budget Optimization using QUBO Formulation

Optimizes IR resource allocation to maximize IRCI improvement across:
- Multiple companies (portfolio optimization)
- Multiple dial initiatives (single company optimization)

Uses the same QUBO framework as quantum_peers.py, ready for D-Wave quantum annealing.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .config import Settings
from .logging import get_logger

log = get_logger("irci.quantum_budget")

# Try to import D-Wave SDK (optional)
DWAVE_AVAILABLE = False
try:
    from dimod import CQM, Binary, Integer
    from dwave.system import LeapHybridCQMSampler
    DWAVE_AVAILABLE = True
    log.info("D-Wave Ocean SDK available - quantum budget optimization enabled")
except ImportError:
    log.info("D-Wave Ocean SDK not installed - using classical optimization")


@dataclass
class IRInitiative:
    """An IR initiative that can improve a specific dial."""
    name: str
    dial: str  # 'valuation', 'liquidity', 'coverage', 'trust'
    cost: float  # Dollar cost
    time_hours: float  # Staff hours required
    expected_improvement: float  # Expected IRCI points improvement
    timeframe_months: int  # Time to see results
    confidence: float  # 0-1 confidence in estimate
    quick_win: bool  # Can be done quickly
    description: str = ""

    def roi(self, dollar_per_point: float) -> float:
        """Calculate ROI: (improvement * $/pt) / cost"""
        if self.cost <= 0:
            return float('inf')
        return (self.expected_improvement * dollar_per_point) / self.cost


@dataclass
class CompanyIRProfile:
    """IR profile for a company with current scores and improvement opportunities."""
    ticker: str
    current_irci: float
    dial_scores: Dict[str, float]  # valuation_pct, liquidity_pct, coverage_pct, sentiment_pct
    dollar_per_point: float
    enterprise_value: float
    gap_to_leader: float
    weakest_dial: str
    initiatives: List[IRInitiative]

    def potential_value(self) -> float:
        """Total potential value if all initiatives succeed."""
        total_improvement = sum(i.expected_improvement for i in self.initiatives)
        return total_improvement * self.dollar_per_point


# Standard IR initiatives with expected impacts (from academic research)
STANDARD_INITIATIVES = {
    'valuation': [
        IRInitiative(
            name="Earnings Call Enhancement",
            dial="valuation",
            cost=25000,
            time_hours=40,
            expected_improvement=6.5,  # 5-8 pts average
            timeframe_months=9,
            confidence=0.75,
            quick_win=False,
            description="Host deep-dive sessions to help analysts understand earnings quality"
        ),
        IRInitiative(
            name="Growth Narrative Clarification",
            dial="valuation",
            cost=50000,
            time_hours=80,
            expected_improvement=8.0,  # 6-10 pts
            timeframe_months=12,
            confidence=0.70,
            quick_win=False,
            description="Develop quantified growth story with TAM analysis"
        ),
        IRInitiative(
            name="Peer Set Optimization",
            dial="valuation",
            cost=15000,
            time_hours=20,
            expected_improvement=4.5,  # 3-6 pts
            timeframe_months=4,
            confidence=0.80,
            quick_win=True,
            description="Work with analysts to establish favorable peer comparisons"
        ),
        IRInitiative(
            name="SOTP Disclosure Enhancement",
            dial="valuation",
            cost=35000,
            time_hours=60,
            expected_improvement=5.5,  # 4-7 pts
            timeframe_months=6,
            confidence=0.72,
            quick_win=False,
            description="Provide segment-level metrics for sum-of-parts valuation"
        ),
    ],
    'liquidity': [
        IRInitiative(
            name="Market Maker Engagement",
            dial="liquidity",
            cost=20000,
            time_hours=30,
            expected_improvement=5.0,  # 4-6 pts
            timeframe_months=3,
            confidence=0.82,
            quick_win=True,
            description="Engage additional market makers to tighten spreads"
        ),
        IRInitiative(
            name="Retail Investor Outreach",
            dial="liquidity",
            cost=40000,
            time_hours=60,
            expected_improvement=6.0,  # 4-8 pts
            timeframe_months=6,
            confidence=0.68,
            quick_win=False,
            description="Social media engagement and retail investor days"
        ),
        IRInitiative(
            name="Index Inclusion Campaign",
            dial="liquidity",
            cost=30000,
            time_hours=50,
            expected_improvement=8.0,  # 6-10 pts
            timeframe_months=12,
            confidence=0.55,
            quick_win=False,
            description="Meet criteria and lobby for index inclusion"
        ),
        IRInitiative(
            name="ADR/Dual Listing",
            dial="liquidity",
            cost=100000,
            time_hours=200,
            expected_improvement=10.0,  # 8-12 pts
            timeframe_months=18,
            confidence=0.60,
            quick_win=False,
            description="Establish ADR program or secondary listing"
        ),
    ],
    'coverage': [
        IRInitiative(
            name="Analyst Day Event",
            dial="coverage",
            cost=75000,
            time_hours=120,
            expected_improvement=7.0,  # 5-9 pts
            timeframe_months=3,
            confidence=0.78,
            quick_win=False,
            description="Host comprehensive analyst/investor day"
        ),
        IRInitiative(
            name="Conference Circuit Expansion",
            dial="coverage",
            cost=50000,
            time_hours=80,
            expected_improvement=5.0,  # 4-6 pts
            timeframe_months=6,
            confidence=0.75,
            quick_win=False,
            description="Increase presence at industry conferences"
        ),
        IRInitiative(
            name="Press Release Optimization",
            dial="coverage",
            cost=10000,
            time_hours=15,
            expected_improvement=3.0,  # 2-4 pts
            timeframe_months=2,
            confidence=0.85,
            quick_win=True,
            description="Improve press release timing, format, and distribution"
        ),
        IRInitiative(
            name="Initiate Analyst Coverage",
            dial="coverage",
            cost=25000,
            time_hours=40,
            expected_improvement=6.0,  # 4-8 pts
            timeframe_months=6,
            confidence=0.65,
            quick_win=False,
            description="Proactively pitch to sell-side analysts for coverage initiation"
        ),
    ],
    'trust': [
        IRInitiative(
            name="ESG Disclosure Enhancement",
            dial="trust",
            cost=45000,
            time_hours=70,
            expected_improvement=5.5,  # 4-7 pts
            timeframe_months=6,
            confidence=0.72,
            quick_win=False,
            description="Improve sustainability reporting and ESG metrics"
        ),
        IRInitiative(
            name="Guidance Accuracy Program",
            dial="trust",
            cost=20000,
            time_hours=30,
            expected_improvement=6.0,  # 5-7 pts
            timeframe_months=4,
            confidence=0.80,
            quick_win=True,
            description="Implement processes to improve guidance accuracy"
        ),
        IRInitiative(
            name="Executive Visibility Campaign",
            dial="trust",
            cost=35000,
            time_hours=50,
            expected_improvement=4.5,  # 3-6 pts
            timeframe_months=6,
            confidence=0.70,
            quick_win=False,
            description="Increase CEO/CFO media presence and thought leadership"
        ),
        IRInitiative(
            name="Crisis Communication Prep",
            dial="trust",
            cost=30000,
            time_hours=40,
            expected_improvement=3.0,  # 2-4 pts (preventive)
            timeframe_months=3,
            confidence=0.75,
            quick_win=True,
            description="Develop crisis communication playbook and train spokespersons"
        ),
    ],
}


def get_initiatives_for_company(
    ticker: str,
    dial_scores: Dict[str, float],
    dollar_per_point: float,
    focus_dial: Optional[str] = None
) -> List[IRInitiative]:
    """
    Get relevant IR initiatives for a company based on their dial scores.

    Prioritizes initiatives for weaker dials and adjusts expected improvements
    based on current score (diminishing returns for high scores).
    """
    initiatives = []

    # Map dial names
    dial_map = {
        'valuation_pct': 'valuation',
        'liquidity_pct': 'liquidity',
        'coverage_pct': 'coverage',
        'sentiment_pct': 'trust'
    }

    for dial_col, dial_name in dial_map.items():
        if focus_dial and dial_name != focus_dial:
            continue

        score = dial_scores.get(dial_col, 50)

        # Get standard initiatives for this dial
        for base_initiative in STANDARD_INITIATIVES.get(dial_name, []):
            # Adjust improvement based on current score (diminishing returns)
            # Low scores have more room for improvement
            if score < 30:
                improvement_multiplier = 1.3  # More room to improve
            elif score < 50:
                improvement_multiplier = 1.0
            elif score < 70:
                improvement_multiplier = 0.8
            else:
                improvement_multiplier = 0.5  # Already high, harder to improve

            adjusted_improvement = base_initiative.expected_improvement * improvement_multiplier

            # Create adjusted initiative
            initiative = IRInitiative(
                name=f"{base_initiative.name}",
                dial=dial_name,
                cost=base_initiative.cost,
                time_hours=base_initiative.time_hours,
                expected_improvement=round(adjusted_improvement, 1),
                timeframe_months=base_initiative.timeframe_months,
                confidence=base_initiative.confidence,
                quick_win=base_initiative.quick_win,
                description=base_initiative.description
            )
            initiatives.append(initiative)

    return initiatives


class QuantumBudgetOptimizer:
    """
    Quantum-ready IR budget optimizer using QUBO formulation.

    Solves: Which IR initiatives should we fund to maximize IRCI improvement
    subject to budget and time constraints?
    """

    def __init__(
        self,
        budget: float,
        max_hours: Optional[float] = None,
        use_quantum: bool = False
    ):
        self.budget = budget
        self.max_hours = max_hours
        self.use_quantum = use_quantum and DWAVE_AVAILABLE

        self.initiatives: List[IRInitiative] = []
        self.dollar_per_point: float = 0
        self.company_profile: Optional[CompanyIRProfile] = None

    def load_from_irci_analysis(
        self,
        ticker: str,
        df_composite: pd.DataFrame,
        df_valuation: pd.DataFrame,
        dollar_value_df: Optional[pd.DataFrame] = None
    ) -> CompanyIRProfile:
        """
        Load company IR profile from existing IRCI analysis results.
        """
        # Get company data
        company_data = df_composite[df_composite['ticker'] == ticker]
        if company_data.empty:
            raise ValueError(f"Ticker {ticker} not found in analysis results")

        company_row = company_data.iloc[0]

        # Extract dial scores
        dial_scores = {
            'valuation_pct': company_row.get('valuation_pct', 50),
            'liquidity_pct': company_row.get('liquidity_pct', 50),
            'coverage_pct': company_row.get('coverage_pct', 50),
            'sentiment_pct': company_row.get('sentiment_pct', 50)
        }

        # Find weakest dial
        weakest_dial = min(dial_scores, key=dial_scores.get)
        weakest_dial_name = weakest_dial.replace('_pct', '')
        if weakest_dial_name == 'sentiment':
            weakest_dial_name = 'trust'

        # Get enterprise value
        val_data = df_valuation[df_valuation['ticker'] == ticker]
        if not val_data.empty:
            enterprise_value = val_data.iloc[0].get('enterprise_value', 0)
        else:
            enterprise_value = 0

        # Get dollar per point
        if dollar_value_df is not None and not dollar_value_df.empty:
            dv_data = dollar_value_df[dollar_value_df['ticker'] == ticker]
            if not dv_data.empty:
                self.dollar_per_point = dv_data.iloc[0].get('peer_group_$/irci_pt', 0)
            else:
                # Use peer group average
                self.dollar_per_point = dollar_value_df['peer_group_$/irci_pt'].mean()
        else:
            # Estimate: typically 0.5-1% of EV per point
            self.dollar_per_point = enterprise_value * 0.0075 if enterprise_value > 0 else 1000000

        # Calculate gap to leader
        leader_irci = df_composite['irci_composite_pct'].max()
        current_irci = company_row.get('irci_composite_pct', 50)
        gap_to_leader = leader_irci - current_irci

        # Get initiatives
        initiatives = get_initiatives_for_company(
            ticker=ticker,
            dial_scores=dial_scores,
            dollar_per_point=self.dollar_per_point
        )

        self.initiatives = initiatives

        self.company_profile = CompanyIRProfile(
            ticker=ticker,
            current_irci=current_irci,
            dial_scores=dial_scores,
            dollar_per_point=self.dollar_per_point,
            enterprise_value=enterprise_value,
            gap_to_leader=gap_to_leader,
            weakest_dial=weakest_dial_name,
            initiatives=initiatives
        )

        return self.company_profile

    def build_qubo(self) -> Tuple[np.ndarray, np.ndarray, List[IRInitiative]]:
        """
        Build QUBO matrix for initiative selection.

        Binary decision: x[i] = 1 if we fund initiative i, 0 otherwise

        MINIMIZE: -Σ (confidence[i] * improvement[i] * $/pt) * x[i]   (maximize value)
                  + λ₁ * (Σ cost[i]*x[i] - budget)²                   (budget penalty)
                  + λ₂ * (Σ hours[i]*x[i] - max_hours)²               (hours penalty)
        """
        n = len(self.initiatives)
        if n == 0:
            return np.array([]), np.array([[]]), []

        # Linear coefficients: negative expected value (we minimize)
        linear = np.zeros(n)
        for i, init in enumerate(self.initiatives):
            expected_value = init.confidence * init.expected_improvement * self.dollar_per_point
            linear[i] = -expected_value  # Negative because we minimize

        # Quadratic coefficients: constraint penalties
        quadratic = np.zeros((n, n))

        # Budget constraint penalty (quadratic expansion)
        # (Σ cost[i]*x[i] - budget)² = Σᵢ Σⱼ cost[i]*cost[j]*x[i]*x[j] - 2*budget*Σ cost[i]*x[i] + budget²
        # We encode this as quadratic terms
        lambda_budget = 0.001  # Penalty weight (scaled for dollar values)

        costs = np.array([init.cost for init in self.initiatives])

        # Add quadratic terms for budget constraint
        for i in range(n):
            for j in range(n):
                quadratic[i, j] += lambda_budget * costs[i] * costs[j]
            # Linear term from -2*budget*cost[i]
            linear[i] += lambda_budget * (-2 * self.budget * costs[i])

        # Hours constraint (if specified)
        if self.max_hours:
            lambda_hours = 0.1
            hours = np.array([init.time_hours for init in self.initiatives])
            for i in range(n):
                for j in range(n):
                    quadratic[i, j] += lambda_hours * hours[i] * hours[j]
                linear[i] += lambda_hours * (-2 * self.max_hours * hours[i])

        return linear, quadratic, self.initiatives

    def solve_classical(self, method: str = 'greedy_roi') -> Dict:
        """
        Solve using classical optimization.

        Methods:
        - 'greedy_roi': Select initiatives by ROI until budget exhausted
        - 'greedy_value': Select by expected value
        - 'simulated_annealing': QUBO-based optimization
        - 'dynamic_programming': Exact solution for small problems
        """
        if not self.initiatives:
            return {'selected': [], 'total_cost': 0, 'expected_improvement': 0}

        if method == 'greedy_roi':
            return self._solve_greedy_roi()
        elif method == 'greedy_value':
            return self._solve_greedy_value()
        elif method == 'simulated_annealing':
            return self._solve_simulated_annealing()
        elif method == 'dynamic_programming':
            return self._solve_dp()
        else:
            return self._solve_greedy_roi()

    def _solve_greedy_roi(self) -> Dict:
        """Greedy selection by ROI."""
        # Sort by ROI descending
        sorted_initiatives = sorted(
            enumerate(self.initiatives),
            key=lambda x: x[1].roi(self.dollar_per_point),
            reverse=True
        )

        selected = []
        selected_idx = []
        total_cost = 0
        total_hours = 0
        total_improvement = 0
        total_value = 0

        for idx, init in sorted_initiatives:
            # Check budget constraint
            if total_cost + init.cost > self.budget:
                continue

            # Check hours constraint
            if self.max_hours and total_hours + init.time_hours > self.max_hours:
                continue

            selected.append(init)
            selected_idx.append(idx)
            total_cost += init.cost
            total_hours += init.time_hours
            total_improvement += init.expected_improvement * init.confidence
            total_value += init.expected_improvement * init.confidence * self.dollar_per_point

        return {
            'selected': selected,
            'selected_indices': selected_idx,
            'total_cost': total_cost,
            'total_hours': total_hours,
            'expected_improvement': total_improvement,
            'expected_value': total_value,
            'method': 'greedy_roi',
            'budget_utilization': total_cost / self.budget if self.budget > 0 else 0
        }

    def _solve_greedy_value(self) -> Dict:
        """Greedy selection by expected value."""
        sorted_initiatives = sorted(
            enumerate(self.initiatives),
            key=lambda x: x[1].expected_improvement * x[1].confidence * self.dollar_per_point,
            reverse=True
        )

        selected = []
        selected_idx = []
        total_cost = 0
        total_hours = 0
        total_improvement = 0
        total_value = 0

        for idx, init in sorted_initiatives:
            if total_cost + init.cost > self.budget:
                continue
            if self.max_hours and total_hours + init.time_hours > self.max_hours:
                continue

            selected.append(init)
            selected_idx.append(idx)
            total_cost += init.cost
            total_hours += init.time_hours
            total_improvement += init.expected_improvement * init.confidence
            total_value += init.expected_improvement * init.confidence * self.dollar_per_point

        return {
            'selected': selected,
            'selected_indices': selected_idx,
            'total_cost': total_cost,
            'total_hours': total_hours,
            'expected_improvement': total_improvement,
            'expected_value': total_value,
            'method': 'greedy_value',
            'budget_utilization': total_cost / self.budget if self.budget > 0 else 0
        }

    def _solve_simulated_annealing(self, max_iter: int = 5000) -> Dict:
        """Simulated annealing for QUBO optimization."""
        linear, quadratic, initiatives = self.build_qubo()
        n = len(initiatives)

        if n == 0:
            return {'selected': [], 'total_cost': 0, 'expected_improvement': 0}

        # Initialize with greedy solution
        greedy_result = self._solve_greedy_roi()
        current = np.zeros(n)
        for idx in greedy_result['selected_indices']:
            current[idx] = 1

        def energy(x):
            return np.dot(linear, x) + x @ quadratic @ x

        def is_feasible(x):
            cost = sum(initiatives[i].cost for i in range(n) if x[i] == 1)
            if cost > self.budget * 1.01:  # 1% tolerance
                return False
            if self.max_hours:
                hours = sum(initiatives[i].time_hours for i in range(n) if x[i] == 1)
                if hours > self.max_hours * 1.01:
                    return False
            return True

        best = current.copy()
        best_energy = energy(best)
        current_energy = best_energy

        temp_start = abs(best_energy) * 0.1 if best_energy != 0 else 1000
        temp_end = temp_start * 0.001

        for iteration in range(max_iter):
            temp = temp_start * (temp_end / temp_start) ** (iteration / max_iter)

            # Flip a random bit
            proposal = current.copy()
            flip_idx = np.random.randint(n)
            proposal[flip_idx] = 1 - proposal[flip_idx]

            if not is_feasible(proposal):
                continue

            proposal_energy = energy(proposal)
            delta = proposal_energy - current_energy

            if delta < 0 or np.random.random() < np.exp(-delta / temp):
                current = proposal
                current_energy = proposal_energy

                if current_energy < best_energy:
                    best = current.copy()
                    best_energy = current_energy

        # Extract results
        selected = [initiatives[i] for i in range(n) if best[i] == 1]
        selected_idx = [i for i in range(n) if best[i] == 1]

        total_cost = sum(init.cost for init in selected)
        total_hours = sum(init.time_hours for init in selected)
        total_improvement = sum(init.expected_improvement * init.confidence for init in selected)
        total_value = total_improvement * self.dollar_per_point

        return {
            'selected': selected,
            'selected_indices': selected_idx,
            'total_cost': total_cost,
            'total_hours': total_hours,
            'expected_improvement': total_improvement,
            'expected_value': total_value,
            'method': 'simulated_annealing',
            'budget_utilization': total_cost / self.budget if self.budget > 0 else 0,
            'qubo_energy': best_energy
        }

    def _solve_dp(self) -> Dict:
        """Dynamic programming for exact solution (0-1 knapsack)."""
        n = len(self.initiatives)
        if n == 0:
            return {'selected': [], 'total_cost': 0, 'expected_improvement': 0}

        # Discretize budget into $1000 units (not cents!) to keep DP table manageable
        # For a $200K budget, this creates a table of ~200 columns instead of 20M
        scale = 1000  # $1000 units
        budget_units = int(self.budget / scale) + 1

        # Value = confidence * improvement * $/pt (scaled to reasonable integers)
        # Scale down to avoid integer overflow
        value_scale = max(1, self.dollar_per_point / 1e6)
        values = [int(init.confidence * init.expected_improvement * value_scale)
                  for init in self.initiatives]
        costs = [max(1, int(init.cost / scale)) for init in self.initiatives]  # At least 1 unit

        # DP table - space optimized to use 1D array
        dp = [0] * (budget_units + 1)
        # Track which items are selected at each capacity
        selected_at = [[] for _ in range(budget_units + 1)]

        for i in range(n):
            # Traverse backwards to avoid using same item twice
            for w in range(budget_units, costs[i] - 1, -1):
                new_value = dp[w - costs[i]] + values[i]
                if new_value > dp[w]:
                    dp[w] = new_value
                    selected_at[w] = selected_at[w - costs[i]] + [i]

        # Get selected items from best capacity
        selected_idx = selected_at[budget_units]

        selected = [self.initiatives[i] for i in selected_idx]
        total_cost = sum(init.cost for init in selected)
        total_hours = sum(init.time_hours for init in selected)
        total_improvement = sum(init.expected_improvement * init.confidence for init in selected)
        total_value = total_improvement * self.dollar_per_point

        return {
            'selected': selected,
            'selected_indices': selected_idx,
            'total_cost': total_cost,
            'total_hours': total_hours,
            'expected_improvement': total_improvement,
            'expected_value': total_value,
            'method': 'dynamic_programming',
            'budget_utilization': total_cost / self.budget if self.budget > 0 else 0
        }

    def solve_quantum(self) -> Dict:
        """Solve using D-Wave quantum annealer."""
        if not DWAVE_AVAILABLE:
            raise RuntimeError("D-Wave Ocean SDK not installed")

        n = len(self.initiatives)
        if n == 0:
            return {'selected': [], 'total_cost': 0, 'expected_improvement': 0}

        # Build CQM
        cqm = CQM()

        # Binary variables
        x = {i: Binary(f'x_{i}') for i in range(n)}

        # Objective: maximize expected value (negative for minimization)
        objective = sum(
            -self.initiatives[i].confidence *
             self.initiatives[i].expected_improvement *
             self.dollar_per_point * x[i]
            for i in range(n)
        )
        cqm.set_objective(objective)

        # Budget constraint
        cqm.add_constraint(
            sum(self.initiatives[i].cost * x[i] for i in range(n)) <= self.budget,
            label='budget'
        )

        # Hours constraint (if specified)
        if self.max_hours:
            cqm.add_constraint(
                sum(self.initiatives[i].time_hours * x[i] for i in range(n)) <= self.max_hours,
                label='hours'
            )

        # Solve
        sampler = LeapHybridCQMSampler()
        result = sampler.sample_cqm(cqm, time_limit=10)

        # Get best feasible solution
        feasible = result.filter(lambda d: d.is_feasible)
        if len(feasible) == 0:
            log.warning("No feasible quantum solution, falling back to classical")
            return self.solve_classical('simulated_annealing')

        best = feasible.first
        selected_idx = [i for i in range(n) if best.sample[f'x_{i}'] == 1]
        selected = [self.initiatives[i] for i in selected_idx]

        total_cost = sum(init.cost for init in selected)
        total_hours = sum(init.time_hours for init in selected)
        total_improvement = sum(init.expected_improvement * init.confidence for init in selected)
        total_value = total_improvement * self.dollar_per_point

        return {
            'selected': selected,
            'selected_indices': selected_idx,
            'total_cost': total_cost,
            'total_hours': total_hours,
            'expected_improvement': total_improvement,
            'expected_value': total_value,
            'method': 'quantum',
            'budget_utilization': total_cost / self.budget if self.budget > 0 else 0,
            'quantum_energy': best.energy
        }

    def optimize(self, method: str = 'auto') -> Dict:
        """
        Main entry point for budget optimization.

        Args:
            method: 'auto', 'quantum', 'simulated_annealing', 'greedy_roi',
                    'greedy_value', 'dynamic_programming'

        Returns:
            Dict with optimal allocation and expected outcomes
        """
        if method == 'auto':
            if self.use_quantum and DWAVE_AVAILABLE:
                method = 'quantum'
            elif len(self.initiatives) <= 20:
                method = 'dynamic_programming'  # Exact solution
            else:
                method = 'simulated_annealing'

        if method == 'quantum':
            result = self.solve_quantum()
        else:
            result = self.solve_classical(method)

        # Add company context
        if self.company_profile:
            result['ticker'] = self.company_profile.ticker
            result['current_irci'] = self.company_profile.current_irci
            result['projected_irci'] = self.company_profile.current_irci + result['expected_improvement']
            result['gap_to_leader'] = self.company_profile.gap_to_leader
            result['gap_closed_pct'] = (result['expected_improvement'] / self.company_profile.gap_to_leader * 100
                                        if self.company_profile.gap_to_leader > 0 else 0)
            result['weakest_dial'] = self.company_profile.weakest_dial
            result['dollar_per_point'] = self.dollar_per_point

        result['budget'] = self.budget
        result['quantum_available'] = DWAVE_AVAILABLE

        return result


def optimize_ir_budget(
    ticker: str,
    budget: float,
    df_composite: pd.DataFrame,
    df_valuation: pd.DataFrame,
    dollar_value_df: Optional[pd.DataFrame] = None,
    max_hours: Optional[float] = None,
    method: str = 'auto',
    use_quantum: bool = False
) -> Dict:
    """
    Convenience function to optimize IR budget for a company.

    Args:
        ticker: Company ticker symbol
        budget: Total IR budget in dollars
        df_composite: IRCI composite scores DataFrame
        df_valuation: Valuation data DataFrame
        dollar_value_df: Optional $/IRCI point DataFrame
        max_hours: Optional staff hours constraint
        method: Optimization method
        use_quantum: Use D-Wave quantum solver if available

    Returns:
        Dict with:
        - selected: List of recommended IR initiatives
        - total_cost: Total cost of selected initiatives
        - expected_improvement: Expected IRCI point improvement
        - expected_value: Expected dollar value creation
        - projected_irci: Projected IRCI score after initiatives
        - and more...
    """
    optimizer = QuantumBudgetOptimizer(
        budget=budget,
        max_hours=max_hours,
        use_quantum=use_quantum
    )

    optimizer.load_from_irci_analysis(
        ticker=ticker,
        df_composite=df_composite,
        df_valuation=df_valuation,
        dollar_value_df=dollar_value_df
    )

    return optimizer.optimize(method=method)
