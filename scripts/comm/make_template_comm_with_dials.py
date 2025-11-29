# scripts/comm/make_template_comm_with_dials.py
import argparse, pandas as pd, datetime as dt

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", default="data/comm/peers_T.csv", help="CSV with column 'symbol'")
    ap.add_argument("--out", default="data/comm/irci_comm_quarterly_with_dials.csv")
    ap.add_argument("--quarters", default="2024Q4,2025Q1,2025Q2")
    args = ap.parse_args()

    peers = pd.read_csv(args.peers)["symbol"].tolist()
    quarters = [q.strip() for q in args.quarters.split(",") if q.strip()]
    rows = []
    for s in peers:
        for q in quarters:
            rows.append({
                "ticker": s,
                "quarter": q,
                # TODO: fill these from your pipeline/exporter
                "cov_pct": "",
                "trust_pct": "",
                "liq_pct": "",
                "val_pct": "",
                "ev_usd": "",
                "val_metric": ""  # e.g., EV/EBITDA or P/S; must be comparable across peers
            })
    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"Wrote template with {len(df)} rows to {args.out}")
    print("Columns:", list(df.columns))
