#!/usr/bin/env python
import re, argparse, pandas as pd

BAD_PATTERNS = [
    r".*-P[A-Z]$",     # preferreds like T-PA
    r".*\.[A-Z]+$",    # dotted series
    r".*-[A-Z]+$",     # hyphen series like T-PC
    r".*[0-9]$",       # trailing digits (often notes/series)
]
BAD_EXACT = {"TBB", "TBC", "VZA", "T-PC", "T-PA"}

def is_common_equity(sym: str) -> bool:
    s = (sym or "").upper().strip()
    if s in BAD_EXACT: return False
    return not any(re.match(p, s) for p in BAD_PATTERNS)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.inp)
    # accept either 'ticker' or 'symbol'
    col = "ticker" if "ticker" in df.columns else ("symbol" if "symbol" in df.columns else None)
    if not col:
        raise SystemExit("Expected a 'ticker' or 'symbol' column")

    df[col] = df[col].astype(str).str.upper().str.strip()
    df = df[df[col].map(is_common_equity)].drop_duplicates(subset=[col])
    df.to_csv(args.out, index=False)
    print(f"[ok] Filtered peers -> {args.out} ({len(df)} rows)")

if __name__ == "__main__":
    main()
