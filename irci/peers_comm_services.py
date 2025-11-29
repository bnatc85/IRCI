# peers_comm_services.py
import os, requests, pandas as pd
FMP = os.getenv("FMP_API_KEY")

def get_universe():
    url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={FMP}"
    df = pd.DataFrame(requests.get(url).json())
    return df

def get_profiles(symbols):
    out = []
    for chunk in [symbols[i:i+100] for i in range(0, len(symbols), 100)]:
        url = f"https://financialmodelingprep.com/api/v3/profile/{','.join(chunk)}?apikey={FMP}"
        out += requests.get(url).json()
    return pd.DataFrame(out)

u = get_universe()
# keep US common stocks; drop ETFs etc.
cand = u[(u['exchangeShortName'].isin(['NYSE','NASDAQ'])) & (u['type']=='stock') & (~u['symbol'].str.contains(r'\.'))]
prof = get_profiles(cand['symbol'].tolist())
comm = prof[prof['sector'].eq('Communication Services')].dropna(subset=['mktCap'])

# build peers for each target: 10–15 closest by market cap within sector
def peers_for(symbol, k=12):
    row = comm[comm['symbol']==symbol].iloc[0]
    df = comm[comm['symbol']!=symbol].assign(dist=(comm['mktCap']-row['mktCap']).abs())
    return df.nsmallest(k, 'dist')['symbol'].tolist()

# example
print(peers_for('T'))
