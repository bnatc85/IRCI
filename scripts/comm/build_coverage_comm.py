#!/usr/bin/env python
import os, time, math, argparse, requests, pandas as pd, numpy as np
from pathlib import Path
# --- top of file ---
import os, time, argparse, requests, pandas as pd, numpy as np
SEC_UA = os.environ.get("SEC_USER_AGENT", "IRCI Research / missing-ua")
SEC_BASE = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def qtr_str(d):  # date -> 'YYYYQn'
    y, m = d.year, d.month
    return f"{y}Q{(m-1)//3+1}"

def quarter_end(yq):
    y, q = int(yq[:4]), int(yq[-1])
    m = q*3
    last = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
    return last.date()

def load_peers(p):
    df = pd.read_csv(p)
    col = "ticker" if "ticker" in df.columns else "symbol"
    return df[col].astype(str).str.upper().tolist()

# --- PATCH: safer SEC fetch + datetime parsing + guard rails ---
def latest_cik_map():
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers={"User-Agent": SEC_UA}, timeout=30)
    r.raise_for_status()
    j = r.json()
    return {row["ticker"].upper(): int(row["cik_str"]) for _, row in j.items()}

# --- SEC helpers (top of file) ---
SEC_BASE = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

def sec_submissions_df(cik: int, ua: str) -> pd.DataFrame:
    r = requests.get(SEC_BASE.format(cik=cik), headers={"User-Agent": ua}, timeout=30)
    r.raise_for_status()
    j = r.json()
    recent = j.get("filings", {}).get("recent", {})
    df = pd.DataFrame({"form": recent.get("form", []),
                       "filed": recent.get("filingDate", [])})
    if df.empty:
        return df
    # >>> key line: coerce BEFORE any .dt usage <<<
    df["filed"] = pd.to_datetime(df["filed"], errors="coerce", utc=True)
    df = df.dropna(subset=["filed"])
    df["filed"] = df["filed"].dt.tz_localize(None)
    df["quarter"] = df["filed"].dt.to_period("Q").astype(str)
    return df[["form","filed","quarter"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    peers = load_peers(args.peers)
    cikmap = latest_cik_map()

    recs = []
    # optional GDELT mentions file
    gd = None
    if Path("gdelt.csv").exists():
        gd = pd.read_csv("gdelt.csv", low_memory=False)
        # Expect columns: date, ticker or source; if none, this step is skipped
        for c in gd.columns:
            if "date" in c.lower():
                gd["date"] = pd.to_datetime(gd[c], errors="coerce")
                break

    for sym in peers:
        cik = cikmap.get(sym)
        if not cik: 
            continue
        try:
            forms = sec_submissions_df(cik, SEC_UA)   # <-- DataFrame already; do NOT re-index like JSON
            if forms.empty:
                print(f"[warn] {sym}: no recent filings"); continue
            if not np.issubdtype(forms["filed"].dtype, np.datetime64):
                print(f"[debug] {sym} filed dtype:", forms["filed"].dtype, forms["filed"].head().tolist()); continue

            # Map to quarters
            forms["quarter"] = forms["filed"].dt.to_period("Q").astype(str).str.replace("Q", "Q")
            # Counts of 8-K per quarter
            k8 = (forms.query("form == '8-K'")
                        .groupby("quarter").size().rename("k8_cnt"))
            # Timeliness: days from quarter end to 10-Q/10-K filing
            f10 = forms[forms["form"].isin(["10-Q","10-K"])].copy()
            if not f10.empty:
                f10["q_end"] = pd.PeriodIndex(f10["quarter"], freq="Q").to_timestamp(how="end")
                f10["days_to_10x"] = (f10["filed"] - f10["q_end"]).dt.days
                tim = f10.groupby("quarter")["days_to_10x"].min()
            else:
                tim = pd.Series(dtype=float)

            cov = pd.concat([k8, tim], axis=1).reset_index()
            cov["ticker"] = sym

            # Optional: GDELT mention count per quarter (fallback 0)
            if gd is not None and "date" in gd.columns:
                g = gd.copy()
                # If there is a ticker col, filter; else skip
                tcol = None
                for c in g.columns:
                    if c.lower() in ("ticker","symbol"):
                        tcol = c; break
                if tcol:
                    g = g[g[tcol].astype(str).str.upper()==sym]
                    g["quarter"] = g["date"].dt.to_period("Q").astype(str).str.replace("Q","Q")
                    ment = g.groupby("quarter").size().rename("mentions")
                    cov = cov.merge(ment, on="quarter", how="left")
            recs.append(cov)
            time.sleep(0.2)
        except Exception as e:
            print(f"[warn] {sym}: {e}")

    if not recs:
        raise SystemExit("No coverage records built.")
    df = pd.concat(recs, ignore_index=True).fillna({"k8_cnt":0,"days_to_10x":90,"mentions":0})

    # Build raw score: more 8-K, faster 10-Q/10-K, more mentions
    # Normalize: rank each component within-quarter to 0..100
    def pct_rank(s, asc=True):
        s = s.rank(method="min", ascending=asc)
        return 100*(s-1)/(len(s)-1) if len(s)>1 else 50.0

    df["k8_pct"]   = df.groupby("quarter")["k8_cnt"].transform(lambda s: pct_rank(s, asc=True))
    df["time_pct"] = df.groupby("quarter")["days_to_10x"].transform(lambda s: pct_rank(s, asc=False))  # fewer days -> higher pct
    if "mentions" in df.columns:
        df["men_pct"]  = df.groupby("quarter")["mentions"].transform(lambda s: pct_rank(s, asc=True))
    else:
        df["men_pct"] = 50.0

    # Blend (weights can be tweaked later)
    df["cov_pct"] = (0.5*df["k8_pct"] + 0.3*df["time_pct"] + 0.2*df["men_pct"]).round(1)
    out = df[["ticker","quarter","cov_pct"]].dropna().copy()
    out.to_csv(args.out, index=False)
    print(f"[ok] wrote {args.out} ({len(out)} rows)")
if __name__ == "__main__":
    main()
