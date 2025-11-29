import argparse, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--ticker-col", default="ticker")
ap.add_argument("--date-col", default="quarter")  # accepts 'quarter', 'quarter_end', 'as_of', or a date column
args = ap.parse_args()

df = pd.read_csv(args.inp)

def to_quarter(s):
    s = str(s)
    if "Q" in s:           # already like '2024Q3'
        return s.strip()
    d = pd.to_datetime(s, errors="coerce")
    if pd.isna(d):
        return None
    q = (d.month - 1)//3 + 1
    return f"{d.year}Q{q}"

src = args.date_col
if src not in df.columns:
    for cand in ["quarter", "quarter_end", "as_of", "date"]:
        if cand in df.columns:
            src = cand
            break
    else:
        raise SystemExit(f"No quarter-like column in {args.inp}. Columns: {list(df.columns)}")

df["quarter"] = df[src].apply(to_quarter)
df["ticker"]  = df[args.ticker_col].astype(str).str.upper().str.strip()

df.to_csv(args.out, index=False)
print(f"[ok] wrote {args.out} with normalized 'quarter'")
