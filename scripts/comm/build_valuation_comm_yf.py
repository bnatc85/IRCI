#!/usr/bin/env python
# scripts/comm/build_valuation_comm_yf.py
import argparse, sys, math
from pathlib import Path
import numpy as np
import pandas as pd

# --- helpers -------------------------------------------------
def to_quarter_idx(dt):
    """Return 'YYYYQ#' from a pandas Timestamp."""
    p = pd.Period(dt, freq="Q")
    return f"{p.year}Q{p.quarter}"

def quarter_ends(dates):
    """Map a DatetimeIndex to quarter-end timestamps (last valid date in that Q)."""
    q = dates.to_series().groupby(pd.Grouper(freq="Q")).last()
    return q.index

def yf_prices(symbol, period="8y"):
    import yfinance as yf
    df = yf.download(
        symbol, period=period, interval="1d",
        auto_adjust=True, progress=False, threads=False, group_by="ticker"
    )
    if df is None or df.empty:
        return pd.DataFrame()
    # If MultiIndex (yfinance sometimes does this), flatten and find *close*-like column.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(c) for c in tup if c]) for tup in df.columns]
    # Normalize to lowercase
    df.columns = [str(c).lower() for c in df.columns]
    # Prefer 'close'; otherwise take the first column that contains 'close'
    candidates = [c for c in df.columns if "close" in c]
    if not candidates:
        return pd.DataFrame()
    col = "close" if "close" in df.columns else candidates[0]
    out = df[[col]].rename(columns={col: "close"}).dropna()
    out.index = pd.to_datetime(out.index)
    return out


def yf_shares_out(symbol):
    import yfinance as yf, numpy as np, pandas as pd
    t = yf.Ticker(symbol)
    so_hist = None
    try:
        # available in yfinance ≥ 0.2.x
        so_hist = t.get_shares_full()  # Series indexed by date
    except Exception:
        pass
    if so_hist is not None and hasattr(so_hist, "dropna") and not so_hist.dropna().empty:
        so_hist.index = pd.to_datetime(so_hist.index)
        return so_hist.sort_index()
    # fallback to latest
    so = getattr(t, "info", {}).get("sharesOutstanding")
    if so is None or not np.isfinite(so):
        return None
    return float(so)


def yf_quarterly(symbol):
    """Quarterly financials & balance sheet from Yahoo (yfinance)."""
    import yfinance as yf
    t = yf.Ticker(symbol)

    # Financials (income statement) – contains EBITDA in many cases
    q_is = t.quarterly_financials
    if q_is is None or q_is.empty:
        q_is = pd.DataFrame()

    # Balance sheet – contains Cash and Debt
    q_bs = t.quarterly_balance_sheet
    if q_bs is None or q_bs.empty:
        q_bs = pd.DataFrame()

    # Normalize to long tidy frames: index=LineItem, columns=dates
    def tidy(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=["date","item","value"])
        df = df.copy()
        df.columns = pd.to_datetime(df.columns)
        df.index = df.index.astype(str)
        out = (
            df.stack().reset_index()
              .rename(columns={"level_0":"item","level_1":"date",0:"value"})
              .dropna(subset=["value"])
        )
        return out

    return tidy(q_is), tidy(q_bs)

def _pick_first(df, item_names):
    """From a tidy quarterly DF (date,item,value), pick first matching item name."""
    mask = df["item"].str.lower().isin([n.lower() for n in item_names])
    sub = df.loc[mask].copy()
    if sub.empty:
        return pd.Series(dtype=float)
    s = sub.pivot(index="date", columns="item", values="value")
    # choose first column (first matched alias), keeping the series indexed by date
    return s.iloc[:, 0].astype(float)

def pct_rank_series(x, higher_is_better=True):
    """Percentile rank within each quarter (0..100)."""
    if not higher_is_better:
        x = -x  # so lower raw value -> higher rank
    return 100.0 * x.rank(pct=True, method="average")

# --- main ----------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peers", required=True, help="CSV with 'symbol' or 'ticker' column")
    ap.add_argument("--out-ev", required=True, help="Output CSV for EV: ticker,quarter,ev_usd")
    ap.add_argument("--out-val", required=True, help="Output CSV for Valuation: ticker,quarter,val_metric,val_pct")
    ap.add_argument("--period", default="8y")
    args = ap.parse_args()

    peers = pd.read_csv(args.peers)
    col = "ticker" if "ticker" in peers.columns else "symbol"
    peers = peers[[col]].rename(columns={col:"ticker"}).dropna().drop_duplicates()
    syms = peers["ticker"].tolist()

    ev_rows = []
    val_rows = []

    for i, sym in enumerate(syms, 1):
        print(f"[{i}/{len(syms)}] {sym}")

        # 1) Prices & quarter ends
        px = yf_prices(sym, period=args.period)
        if px.empty:
            print(f"[warn] {sym}: no prices")
            continue
            # quarter close via period grouping (handles weekends/holidays cleanly)
        q = px[["close"]].copy()
        q["quarter"] = q.index.to_period("Q")  # quarter labels
        q_close = (
            q.groupby("quarter")["close"].last()  # last trading day in the quarter
            .rename_axis(None)
        )
        q_close.index = [f"{p.year}Q{p.quarter}" for p in q_close.index]  # 'YYYYQ#'

        # 2) Shares outstanding (approx constant over sample)
        so_obj = yf_shares_out(sym)
        if isinstance(so_obj, pd.Series):
            # so_obj indexed by date; convert to quarter then align
            so_df = so_obj.to_frame("so").copy()
            so_df["quarter"] = so_df.index.to_period("Q")
            so_q = so_df.groupby("quarter")["so"].last()
            so_q.index = [f"{p.year}Q{p.quarter}" for p in so_q.index]
            so_series = so_q.reindex(q_close.index, method="ffill")
            mc = q_close * so_series
            so_ok = True
        elif so_obj:
            mc = q_close * float(so_obj)
            so_ok = True
        else:
            mc = pd.Series(index=q_close.index, dtype=float)
            so_ok = False

        # 3) Fundamentals
        q_is, q_bs = yf_quarterly(sym)
        # Cash and Total Debt
        # Cash (pick the largest reasonable cash-like item)
        cash = _pick_first(q_bs, [
            "CashAndCashEquivalents", "Cash And Cash Equivalents",
            "Cash", "Cash And Short Term Investments"
        ])

        # Debt (prefer total; else sum short+long)
        total_debt = _pick_first(q_bs, ["TotalDebt", "Total Debt"])
        lt_debt    = _pick_first(q_bs, ["Long Term Debt"])
        st_debt    = _pick_first(q_bs, ["Short Long Term Debt", "Short/Current Long Term Debt"])
        if not total_debt.empty:
            debt = total_debt
        else:
            # combine pieces if present
            debt = (lt_debt.reindex(lt_debt.index).fillna(0.0) if not lt_debt.empty else 0.0)
            if isinstance(debt, pd.Series) and not st_debt.empty:
                debt = (debt + st_debt.reindex(debt.index).fillna(0.0))
            elif not st_debt.empty:
                debt = st_debt
            if isinstance(debt, (int, float)):
                debt = pd.Series(dtype=float)  # nothing reliable found


        # Map BS dates (quarter end) to our 'YYYYQ#'
        if not cash.empty:
            cash.index = [to_quarter_idx(d) for d in cash.index]
        if not debt.empty:
            debt.index = [to_quarter_idx(d) for d in debt.index]

        # EBITDA & Revenue from IS
        ebitda = _pick_first(q_is, ["EBITDA", "Ebitda"])
        revenue = _pick_first(q_is, ["TotalRevenue", "Total Revenue", "Revenue"])
        if not ebitda.empty:
            ebitda.index = [to_quarter_idx(d) for d in ebitda.index]
        if not revenue.empty:
            revenue.index = [to_quarter_idx(d) for d in revenue.index]

        # 4) EV by quarter: MarketCap + Debt - Cash
        ev = pd.Series(index=q_close.index, dtype=float)
        if so_ok:
            ev = mc.copy()
            if not debt.empty:
                ev = ev.add(debt.reindex(ev.index), fill_value=0.0)
            if not cash.empty:
                ev = ev.sub(cash.reindex(ev.index), fill_value=0.0)


        # 5) EV/EBITDA metric
        # Use trailing quarterly EBITDA (Yahoo is quarterly) – guard small/neg values.
        ev_ebitda = pd.Series(index=ev.index, dtype=float)
        if not ebitda.empty and not ev.empty:
            e = ebitda.reindex(ev.index)
            ev_ebitda = ev / e.replace(0, np.nan)
            # guard extremes
            ev_ebitda = ev_ebitda.replace([np.inf, -np.inf], np.nan)

        # 6) Build rows for EV csv
        if not ev.empty:
            ev_df = pd.DataFrame({"ticker": sym, "quarter": ev.index, "ev_usd": ev.values})
            ev_rows.append(ev_df)

        # 7) Build rows for valuation csv:
        #    - val_metric: EV/EBITDA if available else Price/Sales proxy
        #    - val_pct: within-quarter percentile rank (lower metric => better => higher pct)
        m = ev_ebitda.copy()
        # fallback proxy if EBITDA missing: Price/Sales ~ (Price / (Revenue/share))
        if m.isna().all():
            if not revenue.empty and so_ok:
                revps = (revenue / so_series if isinstance(so_obj, pd.Series) else revenue / float(so_obj))
                revps = revps.reindex(q_close.index)
                m = (q_close / revps).replace([np.inf, -np.inf], np.nan)

        # only keep quarters where we have a metric
        m = m.dropna()
        if not m.empty:
            val_df = pd.DataFrame({"ticker": sym, "quarter": m.index, "val_metric": m.values})
            val_rows.append(val_df)
        else:
            print(f"[warn] {sym}: no valuation metric this period")

    # Concatenate & compute percentile ranks within quarter (lower metric is better)
    if ev_rows:
        ev_all = pd.concat(ev_rows, ignore_index=True)
    else:
        ev_all = pd.DataFrame(columns=["ticker","quarter","ev_usd"])

    if val_rows:
        val_all = pd.concat(val_rows, ignore_index=True)
        # percentile rank by quarter (lower metric => higher pct)
        val_all["val_pct"] = (
            val_all.groupby("quarter")["val_metric"]
                   .transform(lambda s: pct_rank_series(s, higher_is_better=False))
        )
    else:
        val_all = pd.DataFrame(columns=["ticker","quarter","val_metric","val_pct"])

    # Write outputs
    Path(args.out_ev).parent.mkdir(parents=True, exist_ok=True)
    ev_all.to_csv(args.out_ev, index=False)
    val_all.to_csv(args.out_val, index=False)
    print(f"[ok] wrote {args.out_ev} ({len(ev_all)} rows)")
    print(f"[ok] wrote {args.out_val} ({len(val_all)} rows)")

if __name__ == "__main__":
    main()