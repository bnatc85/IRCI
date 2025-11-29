# scripts/comm/peers_comm.py
import os, sys, json, math, time, argparse
import requests
import pandas as pd

FMP = os.getenv("FMP_API_KEY")
if not FMP:
    raise SystemExit("FMP_API_KEY not set. Run: export FMP_API_KEY=YOUR_KEY")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "irci-peer-builder/1.0"})

def _get(url, expect_list=True, sleep=0.0):
    r = SESSION.get(url, timeout=30)
    if sleep: time.sleep(sleep)
    try:
        data = r.json()
    except Exception:
        raise SystemExit(f"Non-JSON response ({r.status_code}): {r.text[:200]}")
    if expect_list and not isinstance(data, list):
        # Likely an error dict from FMP
        raise SystemExit(f"Expected a list from FMP but got: {json.dumps(data)[:200]}\nURL: {url}")
    return data

def get_universe():
    # Large list endpoint; returns a list on success
    url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={FMP}"
    return pd.DataFrame(_get(url, expect_list=True))

def screener_comm_services():
    # Fallback: screener for US Communication Services, large cap-ish
    url = (
        "https://financialmodelingprep.com/api/v3/stock-screener"
        f"?sector=Communication%20Services&country=US&exchange=NYSE,NASDAQ&limit=500&apikey={FMP}"
    )
    return pd.DataFrame(_get(url, expect_list=True))

def get_profiles(symbols):
    out = []
    for i in range(0, len(symbols), 100):
        chunk = symbols[i:i+100]
        url = f"https://financialmodelingprep.com/api/v3/profile/{','.join(chunk)}?apikey={FMP}"
        out += _get(url, expect_list=True, sleep=0.2)
    return pd.DataFrame(out)

def comm_services_universe():
    try:
        u = get_universe()
        # keep US common stocks; drop ETFs/spvs/foreign suffixes
        u = u[(u['exchangeShortName'].isin(['NYSE','NASDAQ'])) & (u['type']=='stock') & (~u['symbol'].str.contains(r'\.'))]
        prof = get_profiles(u['symbol'].tolist())
    except SystemExit as e:
        print(f"[WARN] stock/list failed, using screener fallback: {e}", file=sys.stderr)
        prof = screener_comm_services()

    # Standardize expected columns
    cols = set(prof.columns)
    if 'sector' not in cols and 'sector' in prof.columns: pass
    prof = prof.rename(columns={"companyName":"companyName", "marketCap":"mktCap"})
    if 'mktCap' not in prof.columns and 'marketCap' in prof.columns:
        prof['mktCap'] = prof['marketCap']

    comm = prof[prof['sector'].eq('Communication Services')].dropna(subset=['mktCap'])
    # Keep core fields only if present
    keep = [c for c in ['symbol','companyName','mktCap','sector','industry'] if c in comm.columns]
    return comm[keep].drop_duplicates(subset=['symbol'])

def peers_for(symbol, comm_df, k=12):
    row = comm_df[comm_df['symbol']==symbol]
    if row.empty:
        raise SystemExit(f"{symbol} not found in Communication Services universe.")
    row = row.iloc[0]
    df = comm_df[comm_df['symbol']!=symbol].copy()
    df['dist'] = (df['mktCap'].astype(float) - float(row['mktCap'])).abs()
    return [symbol] + df.nsmallest(k, 'dist')['symbol'].tolist()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="T")
    ap.add_argument("--k", type=int, default=12, help="# of peers (in addition to target)")
    ap.add_argument("--out", default="data/comm/peers_T.csv")
    args = ap.parse_args()
    # near the end, before writing .csv:
    from peer_filters import is_common_equity

    symbols = [s for s in symbols if is_common_equity(s)]
    symbols = list(dict.fromkeys(symbols))  # dedupe, keep order
    
    comm = comm_services_universe()
    cohort = peers_for(args.symbol, comm, k=args.k)
    pd.DataFrame({"symbol": cohort}).to_csv(args.out, index=False)
    print(f"Wrote {args.out} with {len(cohort)} symbols: {cohort}")
