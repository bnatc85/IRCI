from __future__ import annotations
import os, time
from typing import List
import requests, pandas as pd
from urllib.parse import urlencode
API_STOCK_NEWS="https://financialmodelingprep.com/api/v3/stock_news"
API_PRESS_REL="https://financialmodelingprep.com/api/v3/press-releases/{symbol}"
def _get(url, **kw): r=requests.get(url,timeout=60,**kw); r.raise_for_status(); return r.json()
def fetch_stock_news(symbols: List[str], start: str, end: str, apikey: str, per_page: int=200, max_pages: int=10):
    rows=[]; syms=",".join([s.upper() for s in symbols])
    for page in range(max_pages):
        params={"tickers":syms,"limit":per_page,"from":start,"to":end,"page":page,"apikey":apikey}
        js=_get(f"{API_STOCK_NEWS}?{urlencode(params)}"); 
        if not js: break
        for d in js:
            rows.append({"date":d.get("publishedDate") or d.get("date"),
                         "ticker":(d.get("symbol") or "").upper(),
                         "title":d.get("title"),
                         "text":d.get("text") or d.get("content"),
                         "source":d.get("site"),"url":d.get("url")})
        time.sleep(0.3)
    return rows
def fetch_press_releases(symbol: str, start: str, end: str, apikey: str, per_page: int=200, max_pages: int=10):
    rows=[]
    for page in range(max_pages):
        params={"from":start,"to":end,"page":page,"apikey":apikey}
        js=_get(API_PRESS_REL.format(symbol=symbol.upper())+"?"+urlencode(params))
        if not js: break
        for d in js:
            rows.append({"date":d.get("date") or d.get("publishedDate"),
                         "ticker":symbol.upper(),"title":d.get("title"),
                         "text":d.get("text"),"source":"press-release","url":d.get("url")})
        time.sleep(0.3)
    return rows
def main(argv=None):
    import argparse, pathlib
    ap=argparse.ArgumentParser()
    ap.add_argument("--symbols",required=True); ap.add_argument("--start",required=True); ap.add_argument("--end",required=True)
    ap.add_argument("--apikey",default=os.getenv("FMP_API_KEY")); ap.add_argument("--out",default="data/news.csv")
    ap.add_argument("--skip-pr",action="store_true"); ap.add_argument("--skip-news",action="store_true")
    a=ap.parse_args(argv)
    if not a.apikey: ap.error("Provide --apikey or set FMP_API_KEY")
    syms=[s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    rows=[]
    if not a.skip_news: rows+=fetch_stock_news(syms,a.start,a.end,a.apikey)
    if not a.skip_pr:
        for s in syms: rows+=fetch_press_releases(s,a.start,a.end,a.apikey)
    if not rows: print("[WARN] No rows fetched."); return 0
    df=pd.DataFrame(rows); df["date"]=pd.to_datetime(df["date"],errors="coerce",utc=True)
    df=df.dropna(subset=["date","ticker","title"]); df["ticker"]=df["ticker"].str.upper(); df=df.sort_values("date")
    p=pathlib.Path(a.out); p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False)
    print(f"[OK] Wrote {p} with {len(df)} rows"); return 0
if __name__=="__main__": import sys; sys.exit(main())
