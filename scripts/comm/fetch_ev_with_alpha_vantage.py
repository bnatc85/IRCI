#!/usr/bin/env python
import os, time, argparse, requests, pandas as pd, sys, csv, pathlib

BASE = "https://www.alphavantage.co/query"

def get_json(params, apikey, backoff=15):
    params["apikey"] = apikey
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    # AV free plan -> throttle messages under "Note" or "Information"
    if isinstance(j, dict) and ("Note" in j or "Information" in j):
        time.sleep(backoff)
        r = requests.get(BASE, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
    return j

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def append_rows_csv(path: pathlib.Path, rows: list[dict], header_order: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header_order)
        if write_header: w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in header_order})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", required=True, help="CSV with 'ticker' or 'symbol' column")
    ap.add_argument("--out-ev", required=True)
    ap.add_argument("--out-val", required=True)
    ap.add_argument("--quarters", type=int, default=2, help="how many recent quarters to pull (default 2)")
    ap.add_argument("--limit", type=int, default=6, help="limit number of peers (default 6)")
    ap.add_argument("--sleep", type=float, default=12.0, help="seconds between symbols to respect AV limits")
    args = ap.parse_args()

    AV = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not AV:
        print("ALPHAVANTAGE_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    peers = pd.read_csv(args.peers)
    symcol = "ticker" if "ticker" in peers.columns else ("symbol" if "symbol" in peers.columns else None)
    if not symcol:
        print("Expected a 'ticker' or 'symbol' column in peers CSV", file=sys.stderr); sys.exit(1)

    syms = peers[symcol].astype(str).str.upper().str.strip().tolist()
    if args.limit and args.limit < len(syms):
        syms = syms[:args.limit]

    ev_out  = pathlib.Path(args.out_ev)
    val_out = pathlib.Path(args.out_val)
    # start fresh each run
    if ev_out.exists(): ev_out.unlink()
    if val_out.exists(): val_out.unlink()

    ev_headers  = ["ticker","quarter","ev_usd"]
    val_headers = ["ticker","quarter","val_metric","val_pct"]

    for i, sym in enumerate(syms, 1):
        try:
            print(f"[{i}/{len(syms)}] {sym} ...", flush=True)

            # OVERVIEW for shares outstanding
            ov = get_json({"function":"OVERVIEW","symbol":sym}, AV)
            shares = safe_float(ov.get("SharesOutstanding"))

            # GLOBAL_QUOTE for price (spot proxy)
            gq = get_json({"function":"GLOBAL_QUOTE","symbol":sym}, AV)
            price = safe_float(gq.get("Global Quote", {}).get("05. price"))

            # BALANCE_SHEET for cash & debt (quarterly)
            bs = get_json({"function":"BALANCE_SHEET","symbol":sym}, AV)
            qtr = (bs.get("quarterlyReports") or [])[:args.quarters]

            ev_rows = []
            for q in qtr:
                fq   = q.get("fiscalDateEnding")
                cash = safe_float(q.get("cashAndShortTermInvestments"))
                debt = safe_float(q.get("shortLongTermDebtTotal"))
                mcap = shares * price if shares and price else 0.0
                ev   = mcap + debt - cash
                ev_rows.append({"ticker": sym, "quarter": fq, "ev_usd": ev})

            append_rows_csv(ev_out, ev_rows, ev_headers)

            # INCOME_STATEMENT for EBITDA (quarterly)
            isd = get_json({"function":"INCOME_STATEMENT","symbol":sym}, AV)
            iq = (isd.get("quarterlyReports") or [])[:args.quarters]
            eb_by_q = {r.get("fiscalDateEnding"): safe_float(r.get("ebitda")) for r in iq}

            # Join EV with EBITDA (per symbol, last N quarters)
            val_rows = []
            for r in ev_rows:
                ebitda = eb_by_q.get(r["quarter"], 0.0)
                val_metric = (r["ev_usd"] / ebitda) if ebitda else None
                val_rows.append({"ticker": sym, "quarter": r["quarter"], "val_metric": val_metric})

            # We’ll fill val_pct in a post-pass; write partial now
            append_rows_csv(val_out, val_rows, ["ticker","quarter","val_metric","val_pct"])

            time.sleep(args.sleep)  # be nice to AV
        except Exception as e:
            print(f"[warn] {sym}: {e}", file=sys.stderr)
            # keep going to next symbol

    # Post-pass: compute val_pct (0–100 per quarter across peers)
    try:
        val_df = pd.read_csv(val_out)
        if not val_df.empty:
            def pct_rank(s):
                return 100 * (s.rank(method="min") - 1) / (len(s) - 1) if len(s) > 1 else 50.0
            val_df["val_pct"] = (
                val_df.groupby("quarter")["val_metric"].transform(pct_rank).round(1)
            )
            val_df.to_csv(val_out, index=False)
    except Exception as e:
        print(f"[warn] post-pass val_pct: {e}", file=sys.stderr)

    print(f"[ok] wrote {ev_out} and {val_out}")

if __name__ == "__main__":
    main()
