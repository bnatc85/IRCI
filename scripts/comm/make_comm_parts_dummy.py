import argparse, pandas as pd, numpy as np, hashlib, datetime as dt

def qlist(n=8, end_year=2025, end_q=2):
    qs=[]
    y, q = end_year, end_q
    for _ in range(n):
        qs.append(f"{y}Q{q}")
        q -= 1
        if q==0: q=4; y-=1
    return list(reversed(qs))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", default="data/comm/peers_T.csv")
    ap.add_argument("--outdir", default="data/comm")
    ap.add_argument("--quarters", default="", help="comma list like 2024Q3,2024Q4,2025Q1; blank=last 8")
    args = ap.parse_args()

    peers = pd.read_csv(args.peers)["symbol"].astype(str).str.upper().tolist()
    quarters = [q.strip() for q in args.quarters.split(",") if q.strip()] or qlist(8)

    # deterministic pseudo-randoms per (ticker,quarter)
    def seed(t,q): return int(hashlib.md5(f"{t}-{q}".encode()).hexdigest(),16) % (10**6)
    rows_cov, rows_tru, rows_liq, rows_val, rows_ev = [],[],[],[],[]

    for t in peers:
        for q in quarters:
            np.random.seed(seed(t,q))
            # percentiles 30-85 band with small jitter
            cov = 30 + np.random.rand()*55
            tru = 30 + np.random.rand()*55
            liq = 30 + np.random.rand()*55
            val = 30 + np.random.rand()*55
            # EV by rough size buckets
            base_ev = 1.4e11 if t in {"T","VZ","TMUS","CMCSA","DIS"} else 6e10
            ev = base_ev * (0.9 + 0.2*np.random.rand())
            # valuation metric (EV/EBITDA-like)
            val_metric = (7 + 8*np.random.rand()) if t in {"T","VZ","TMUS"} else (9 + 8*np.random.rand())
            rows_cov.append({"ticker":t,"quarter":q,"cov_pct":round(cov,2)})
            rows_tru.append({"ticker":t,"quarter":q,"trust_pct":round(tru,2)})
            rows_liq.append({"ticker":t,"quarter":q,"liq_pct":round(liq,2)})
            rows_val.append({"ticker":t,"quarter":q,"val_pct":round(val,2),"val_metric":round(val_metric,3)})
            rows_ev.append({"ticker":t,"quarter":q,"ev_usd":round(ev,2)})

    pd.DataFrame(rows_cov).to_csv(f"{args.outdir}/coverage_comm.csv", index=False)
    pd.DataFrame(rows_tru).to_csv(f"{args.outdir}/trust_comm.csv", index=False)
    pd.DataFrame(rows_liq).to_csv(f"{args.outdir}/liquidity_comm.csv", index=False)
    pd.DataFrame(rows_val).to_csv(f"{args.outdir}/valuation_comm.csv", index=False)
    pd.DataFrame(rows_ev).to_csv(f"{args.outdir}/ev_comm.csv", index=False)
    print("Wrote dummy parts in", args.outdir, "for quarters:", quarters)
