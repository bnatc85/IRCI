import os, time, argparse, pandas as pd, requests
KEY = os.getenv("FMP_API_KEY")
BASE = "https://financialmodelingprep.com/api/v3"

def get_json(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def q_from_date(s):  # 'YYYY-MM-DD' -> 'YYYYQx'
    y, m = s[:4], s[5:7]
    return f"{y}Q{(int(m)-1)//3 + 1}" if m and m.isdigit() else None

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", required=True, help="CSV with column 'symbol'")
    ap.add_argument("--out-ev", default="data/exports/ev.csv")
    ap.add_argument("--out-val", default="data/exports/valuation.csv")
    args = ap.parse_args()
    assert KEY, "Set FMP_API_KEY first: export FMP_API_KEY=WuMAUXOpUqV3J69icFs1FwuRJhi9LRoG"

    syms = pd.read_csv(args.peers)["symbol"].astype(str).tolist()
    rows_ev, rows_is = [], []

    for s in syms:
        # Enterprise value (quarterly)
        try:
            evq = get_json(f"{BASE}/enterprise-values/{s}?period=quarter&limit=12&apikey={KEY}")
            for r in evq:
                q = q_from_date(r.get("date",""))
                ev = r.get("enterpriseValue")
                if q and ev is not None:
                    rows_ev.append({"ticker":s, "quarter":q, "ev_usd": ev})
        except Exception as e:
            print("[warn] EV fetch failed for", s, e)
        # EBITDA (quarterly)
        try:
            inc = get_json(f"{BASE}/income-statement/{s}?period=quarter&limit=12&apikey={KEY}")
            for r in inc:
                q = q_from_date(r.get("date",""))
                ebitda = r.get("ebitda")
                if q and ebitda not in (None, 0):
                    rows_is.append({"ticker":s, "quarter":q, "ebitda": ebitda})
        except Exception as e:
            print("[warn] IS fetch failed for", s, e)
        time.sleep(0.2)

    ev_df = pd.DataFrame(rows_ev)
    is_df = pd.DataFrame(rows_is)
    val = ev_df.merge(is_df, on=["ticker","quarter"], how="inner")
    val["val_metric"] = val["ev_usd"] / val["ebitda"]
    # We’re writing a valuation file with just the metric; you’ll still supply val_pct from your pipeline
    out_val = val[["ticker","quarter","val_metric"]].copy()
    # placeholder column for percentiles; your pipeline should replace this
    out_val["val_pct"] = None

    ev_df.to_csv(args.out_ev, index=False)
    out_val.to_csv(args.out_val, index=False)
    print(f"[ok] wrote {args.out_ev} and {args.out_val}")
