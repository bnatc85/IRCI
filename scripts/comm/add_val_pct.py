import argparse, pandas as pd
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()
df = pd.read_csv(args.inp)
assert {"ticker","quarter","val_metric"}.issubset(df.columns), "Need ticker, quarter, val_metric"
df["val_pct"] = df.groupby("quarter")["val_metric"].rank(pct=True) * 100.0
df.to_csv(args.out, index=False)
print(f"[ok] wrote {args.out} with val_pct computed per quarter")
