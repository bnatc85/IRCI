# validation_comm.py
import pandas as pd
from scipy.stats import spearmanr

def rank_link(today_dial_rank, next_q_change):
    # negative is "good" when down = good (spreads/vol); Spearman robust for ranks
    rho, p = spearmanr(today_dial_rank, next_q_change)
    return rho, p

# Example: Liquidity vs next-q spread change
# df needs columns: 'ticker','qdate','liq_pct','delta_spread_nextq'
rho, p = rank_link(df['liq_pct'].rank(pct=True), df['delta_spread_nextq'])
print("Liquidity rank-link:", rho, p)
# Interpretation: negative rho means higher liquidity (higher rank) links to lower spreads (negative change)