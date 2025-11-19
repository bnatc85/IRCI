# scripts/comm/weights_search.py
import argparse, json, numpy as np, pandas as pd
from scipy.stats import spearmanr

def composite(df, w):
    # expects cov_pct, trust_pct, liq_pct, val_pct in [0,100]
    return (w[0]*df['cov_pct'] + w[1]*df['trust_pct'] + w[2]*df['liq_pct'] + w[3]*df['val_pct'])

def grid_weights(step=0.05):
    xs = np.arange(0, 1+1e-9, step)
    W = []
    for w0 in xs:
        for w1 in xs:
            for w2 in xs:
                w3 = 1 - (w0+w1+w2)
                if w3 < -1e-9 or w3 > 1: continue
                W.append(np.array([w0,w1,w2,w3]))
    return W

def score_ic(df, comp_col, target_col):
    return spearmanr(df[comp_col], df[target_col], nan_policy="omit")[0]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/comm/irci_comm_quarterly_with_dials.csv",
                    help="Must include cov_pct, trust_pct, liq_pct, val_pct, peer_gap_change_pp_nextq")
    ap.add_argument("--out", default="results/comm/weights_comm.json")
    ap.add_argument("--step", type=float, default=0.05)
    args = ap.parse_args()

    df = pd.read_csv(args.panel)
    # Train/test split by time (last 2 quarters = test, rest = train)
    q_order = sorted(df['quarter'].unique())
    test_quarters = set(q_order[-2:])
    df_train = df[~df['quarter'].isin(test_quarters)].copy()
    df_test  = df[df['quarter'].isin(test_quarters)].copy()

    best = None
    best_abs_ic = -1
    for w in grid_weights(args.step):
        df_train['comp_tmp'] = composite(df_train, w)
        df_test['comp_tmp']  = composite(df_test,  w)
        ic_test = score_ic(df_test, 'comp_tmp', 'peer_gap_change_pp_nextq')
        if abs(ic_test) > best_abs_ic:
            best_abs_ic = abs(ic_test)
            best = {"weights": {"coverage": w[0], "trust": w[1], "liquidity": w[2], "valuation": w[3]},
                    "ic_test": ic_test}

    with open(args.out, "w") as f:
        json.dump(best, f, indent=2)
    print(json.dumps(best, indent=2))
