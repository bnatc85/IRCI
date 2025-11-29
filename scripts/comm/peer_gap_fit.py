# scripts/comm/peer_gap_fit.py
import argparse, json
import pandas as pd
import statsmodels.api as sm

def run_fit(df):
    # OLS: next-q change in peer-gap (pp) ~ composite (%)
    X = sm.add_constant(df['irci_composite_pct'])
    y = df['peer_gap_change_pp_nextq']
    y = y.clip(y.quantile(0.01), y.quantile(0.99))
    model = sm.OLS(y, X, missing='drop').fit()
    m = sm.OLS(y, X, missing='drop').fit(cov_type='cluster', cov_kwds={'groups': df['ticker']})
    beta = float(model.params['irci_composite_pct'])   # pp change per 1 composite point
    r2 = float(model.rsquared)
    return beta, r2, model

def dollars_per_point(df, beta):
    # convert beta (pp per composite point) to $ sensitivity per point for each row
    # $/pt = EV * (|beta| / 100)
    out = df[['ticker','ev_usd']].copy()
    out = out.groupby('ticker', as_index=False)['ev_usd'].mean()
    out['usd_per_point'] = out['ev_usd'].abs() * (abs(beta) / 100.0)
    return out.sort_values('usd_per_point', ascending=False)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/comm/irci_comm_quarterly.csv")
    ap.add_argument("--filter-symbols", default="data/comm/peers_T.csv",
                    help="CSV with a 'symbol' column to filter the panel (T + peers).")
    ap.add_argument("--out-json", default="results/comm/peer_gap_fit_T.json")
    ap.add_argument("--out-csv",  default="results/comm/usd_per_point_T.csv")
    args = ap.parse_args()

    panel = pd.read_csv(args.input)
    # optional filter to cohort
    try:
        sym = pd.read_csv(args.filter_symbols)['symbol'].unique().tolist()
        panel = panel[panel['ticker'].isin(sym)]
    except Exception:
        pass

    # basic cleaning
    panel = panel.dropna(subset=['irci_composite_pct','peer_gap_change_pp_nextq','ev_usd'])
    beta, r2, model = run_fit(panel)

    usdpt = dollars_per_point(panel, beta)
    usdpt.to_csv(args.out_csv, index=False)

    out = {
        "beta_pp_per_point": beta,
        "r2": r2,
        "n_obs": int(model.nobs),
        "tickers": sorted(panel['ticker'].unique().tolist()),
        "usd_per_point_top": usdpt.head(10).to_dict(orient="records")
    }
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=2)

    print(json.dumps(out, indent=2))
    print(f"\nWrote: {args.out_json}\nWrote: {args.out_csv}")
