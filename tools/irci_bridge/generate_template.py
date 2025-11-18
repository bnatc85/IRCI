import pandas as pd
from pathlib import Path

out = Path("artifacts/IRCI_lowcode_template.xlsx")

settings = pd.DataFrame({
    "Key": [
        "Tickers (comma-separated)","Peer Group (comma-separated)",
        "Weights: Coverage","Weights: Trust","Weights: Liquidity","Weights: Valuation",
        "Event Window Days (+/-)","Liquidity Estimator","Sentiment Source"
    ],
    "Value": [
        "AAPL,MSFT,AMZN,GOOGL","AAPL,MSFT,AMZN,GOOGL",
        "0.20","0.30","0.20","0.30","3",
        "Amihud & Corwin-Schultz (daily)","Azure Language or MonkeyLearn"
    ],
    "Notes": [
        "Tickers to track","Peer set for percentile ranks",
        "Composite weight","Composite weight","Composite weight","Composite weight",
        "Trading days (e.g., 3 for ±3)","Uses OHLCV only","Low-code option"
    ]
})

filings = pd.DataFrame(columns=["FilingDate","Ticker","CIK","FormType","Accession","FilingURL","EventID"])
prices  = pd.DataFrame(columns=["Date","Ticker","Open","High","Low","Close","AdjClose","Volume"])
factors = pd.DataFrame(columns=["Date","Mkt_RF","SMB","HML","RF"])
events  = pd.DataFrame(columns=["EventID","Ticker","EventDate","WindowStart","WindowEnd","MedianAbsMove_FF","Calmness_Sign","CalmnessScore"])
news    = pd.DataFrame(columns=["Date","Ticker","Source","Title","URL","SentimentScore","Confidence","Language"])
dials   = pd.DataFrame(columns=["Quarter","Ticker","Coverage_pct","Trust_pct","Liquidity_pct","Valuation_pct"])
comp    = pd.DataFrame(columns=["Quarter","Ticker","wCoverage","wTrust","wLiquidity","wValuation","CompositePct","RankInPeer"])
readme  = pd.DataFrame({
    "Where": ["PRICES","FACTORS","EVENTS","NEWS","DIALS","COMPOSITE"],
    "What to do": [
        "Fetch OHLCV into PRICES (Alpha Vantage/FMP, etc.)",
        "Paste daily Mkt_RF, SMB, HML, RF (Fama-French) here",
        "Compute ±N-day window bounds then calmness per event",
        "Compute sentiment per headline; shrink/clamp as needed",
        "Compute each dial & convert to 0–100 peer percentiles",
        "Weighted composite = SUMPRODUCT(weights, dials); rank"
    ]
})

out.parent.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(out, engine="xlsxwriter") as w:
    settings.to_excel(w, sheet_name="SETTINGS", index=False)
    filings.to_excel(w,  sheet_name="FILINGS",  index=False)
    prices.to_excel(w,   sheet_name="PRICES",   index=False)
    factors.to_excel(w,  sheet_name="FACTORS",  index=False)
    events.to_excel(w,   sheet_name="EVENTS",   index=False)
    news.to_excel(w,     sheet_name="NEWS",     index=False)
    dials.to_excel(w,    sheet_name="DIALS",    index=False)
    comp.to_excel(w,     sheet_name="COMPOSITE",index=False)
    readme.to_excel(w,   sheet_name="READ ME",  index=False)

print(f"Wrote {out}")
