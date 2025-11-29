#!/usr/bin/env python
# scripts/comm/tune_weights_per_ticker.py
import os, sys, numpy as np, pandas as pd
from collections import OrderedDict

PANEL  = "out/comm/irci_comm_quarterly.csv"       # has cov/trust/liq/val
TARGET = "out/comm/price_target_nextq.csv"        # has peer_gap_price_nextq
OUT1   = "out/comm/comm_weights_by_ticker.csv"
OUT2   = "out/comm/comm_weights_summary.csv"

DIALS = ["cov_pct","trust_pct","liq_pct","val_pct"]
YCOL  = "peer_gap_price_nextq"

def r2_score(y, yhat):
    if len(y) < 2: return np.nan
    ss_res = np.sum((y - yhat)**2)
    ss_tot = np.sum((y - y.mean())**2)
    return 1.0 - ss_res/ss_tot if ss_tot > 0 else np.nan

def nnls_sum1_ridge(X, y, lam=0.05, max_iter=2500, lr=1e-3, tol=1e-7):
    """
    Minimize ||Xw - y||^2 + lam * ||w||^2
    s.t. w >= 0, sum(w) = 1
    Projected gradient descent with ridge term:
      grad = 2 X^T (Xw - y) + 2*lam*w
      w <- w - lr * grad
      w <- max(w, 0)
      normalize to sum=1 (uniform if all-zero)
    """
    nfeat = X.shape[1]
    w = np.ones(nfeat)/nfeat
    Xt = X.T
    last = None
    for _ in range(max_iter):
        grad = 2.0 * (Xt @ (X @ w - y)) + 2.0 * lam * w
        w = w - lr * grad
        w = np.maximum(w, 0.0)
        s = w.sum()
        w = (np.ones_like(w)/nfeat) if s <= 1e-12 else (w / s)
        yhat = X @ w
        loss = np.mean((y - yhat)**2) + lam * np.sum(w*w)
        if last is not None and abs(last - loss) < tol:
            break
        last = loss
    return w

def rolling_cv_r2(X, y, splits=3):
    n = len(y)
    if n < 8: return np.nan
    splits = max(2, min(splits, n // 4))
    fold = n // (splits + 1)
    if fold < 2: return np.nan
    r2s = []
    for k in range(1, splits+1):
        tr_end = fold * k
        te_end = fold * (k+1) if k < splits else n
        Xtr, ytr = X[:tr_end], y[:tr_end]
        Xte, yte = X[tr_end:te_end], y[tr_end:te_end]
        if len(ytr) < 4 or len(yte) < 2: continue
        w = nnls_sum1_ridge(Xtr, ytr, lam=0.05)
        r2s.append(r2_score(yte, Xte @ w))
    return float(np.nanmean(r2s)) if r2s else np.nan

def main():
    panel = pd.read_csv(PANEL)
    need = {"ticker","quarter",*DIALS}
    miss = need - set(panel.columns)
    if miss:
        sys.exit(f"Base panel missing columns: {miss}")

    target = pd.read_csv(TARGET)  # ticker, quarter, peer_gap_price_nextq
    df = panel.merge(target, on=["ticker","quarter"], how="inner").dropna()
    if df.empty:
        sys.exit("No overlap between panel and target; rebuild price_target_nextq.csv.")

    rows = []
    for tkr, g in df.groupby("ticker", sort=True):
        g = g.sort_values("quarter")  # assume 'YYYYQn' strings
        if len(g) < 8:
            rows.append({"ticker": tkr, "n": len(g), "note": "too_few_quarters"})
            continue

        # --- Standardize dials per ticker (z-score) ---
        Xraw = g[DIALS].to_numpy(dtype=float)
        mu   = Xraw.mean(axis=0)
        sd   = Xraw.std(axis=0, ddof=0)
        sd[sd == 0] = 1.0
        X = (Xraw - mu) / sd

        y = g[YCOL].to_numpy(dtype=float)

        # --- Fit ridge-regularized NNLS with sum-to-one ---
        w_std = nnls_sum1_ridge(X, y, lam=0.05)
        # Map back to the original (unitless) dial weights for interpretability:
        # When X = (Xraw - mu)/sd, the prediction is proportional to (w_std/sd)·Xraw
        v = w_std / sd
        v = np.maximum(v, 0)
        s = v.sum()
        w = (np.ones_like(v)/len(v)) if s <= 1e-12 else (v / s)

        R2_in = r2_score(y, X @ w_std)
        R2_cv = rolling_cv_r2(X, y, splits=3 if len(g) >= 12 else 2)

        # Drop-one ablation
        base_R2 = R2_in
        ablate = OrderedDict()
        for i, dial in enumerate(DIALS):
            keep = [j for j in range(len(DIALS)) if j != i]
            Xi = X[:, keep]
            wi = nnls_sum1_ridge(Xi, y, lam=0.05)
            R2_i = r2_score(y, Xi @ wi)
            ablate[f"drop_{dial}_dR2"] = float(base_R2 - R2_i)

        rows.append({
            "ticker": tkr, "n": int(len(g)),
            "w_cov": float(w[0]), "w_trust": float(w[1]),
            "w_liq": float(w[2]), "w_val": float(w[3]),
            "R2_in": float(R2_in), "R2_cv": float(R2_cv), **ablate
        })

    res = pd.DataFrame(rows)
    res_cal = res[res["n"].ge(8) & res["w_cov"].notna()].copy().sort_values("ticker")
    os.makedirs(os.path.dirname(OUT1), exist_ok=True)
    res_cal.to_csv(OUT1, index=False)

    if not res_cal.empty:
        summary = pd.DataFrame({
            "metric": ["median","mean","iqr_low","iqr_high"],
            "w_cov":  [res_cal["w_cov"].median(),  res_cal["w_cov"].mean(),
                       res_cal["w_cov"].quantile(0.25), res_cal["w_cov"].quantile(0.75)],
            "w_trust":[res_cal["w_trust"].median(),res_cal["w_trust"].mean(),
                       res_cal["w_trust"].quantile(0.25), res_cal["w_trust"].quantile(0.75)],
            "w_liq":  [res_cal["w_liq"].median(),  res_cal["w_liq"].mean(),
                       res_cal["w_liq"].quantile(0.25), res_cal["w_liq"].quantile(0.75)],
            "w_val":  [res_cal["w_val"].median(),  res_cal["w_val"].mean(),
                       res_cal["w_val"].quantile(0.25), res_cal["w_val"].quantile(0.75)],
            "R2_in":  [res_cal["R2_in"].median(),  res_cal["R2_in"].mean(),
                       res_cal["R2_in"].quantile(0.25), res_cal["R2_in"].quantile(0.75)],
            "R2_cv":  [res_cal["R2_cv"].median(),  res_cal["R2_cv"].mean(),
                       res_cal["R2_cv"].quantile(0.25), res_cal["R2_cv"].quantile(0.75)],
        })
        summary.to_csv(OUT2, index=False)

    print(f"[ok] wrote:\n - {OUT1}\n - {OUT2} (if any rows)")
if __name__ == "__main__":
    main()
