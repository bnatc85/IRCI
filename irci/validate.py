# irci/validate.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import pandas as pd

try:
    import statsmodels.api as sm  # optional
    HAS_SM = True
except Exception:
    HAS_SM = False

def _pick(path_default: str, pattern: str, quarter: Optional[str]) -> Path:
    """
    If quarter-specific file exists (pattern with {q}), use it; else default.
    """
    if quarter:
        q = quarter.lower()
        p = Path(pattern.format(q=q))
        if p.exists():
            return p
    return Path(path_default)

def _to_qend(series) -> pd.Series:
    s = pd.to_datetime(series, utc=True, errors="coerce")
    # PeriodIndex drops tz; add back normalized UTC
    qend = pd.PeriodIndex(s, freq="Q-DEC").end_time
    return qend.dt.tz_localize("UTC")

def _load_valuation(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # prefer existing 'quarter_end' if present; else bucket 'as_of'
    if "quarter_end" in df.columns:
        q = pd.to_datetime(df["quarter_end"], utc=True, errors="coerce")
    else:
        base = df["as_of"] if "as_of" in df.columns else df.iloc[:, 1]
        q = _to_qend(base)
    df["quarter_end"] = q
    # support multiple naming variants
    for c in ["valuation_pct", "valuation_dial", "valuation_dial_pct", "valuation_pct_empirical"]:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            if s.dropna().between(0, 1).all():
                s = s * 100.0
            df["valuation_pct"] = s
            break
    return df[["ticker", "quarter_end", "valuation_pct"]].dropna(subset=["ticker","quarter_end"])

def _load_liquidity(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    q = pd.to_datetime(df["quarter_end"], utc=True, errors="coerce")
    df["quarter_end"] = q
    s = pd.to_numeric(df["liquidity_pct"], errors="coerce")
    if s.dropna().between(0, 1).all():
        s = s * 100.0
    df["liquidity_pct"] = s
    return df[["ticker","quarter_end","liquidity_pct"]].dropna(subset=["ticker","quarter_end"])

def _load_coverage(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "quarter_end" in df.columns:
        q = pd.to_datetime(df["quarter_end"], utc=True, errors="coerce")
    else:
        base = df["as_of_bucket"] if "as_of_bucket" in df.columns else df.get("as_of")
        q = _to_qend(base)
    df["quarter_end"] = q
    s = pd.to_numeric(df["coverage_pct"], errors="coerce")
    if s.dropna().between(0, 1).all():
        s = s * 100.0
    df["coverage_pct"] = s
    return df[["ticker","quarter_end","coverage_pct"]].dropna(subset=["ticker","quarter_end"])

def _load_trust(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    q = pd.to_datetime(df["quarter_end"], utc=True, errors="coerce")
    df["quarter_end"] = q
    # allow 'trust_pct' as synonym
    col = "sentiment_pct" if "sentiment_pct" in df.columns else "trust_pct"
    s = pd.to_numeric(df[col], errors="coerce")
    if s.dropna().between(0, 1).all():
        s = s * 100.0
    df["sentiment_pct"] = s
    return df[["ticker","quarter_end","sentiment_pct"]].dropna(subset=["ticker","quarter_end"])

def _ic(x, y) -> float:
    a = pd.Series(x); b = pd.Series(y)
    m = a.notna() & b.notna()
    if m.sum() < 10:
        return np.nan
    return a[m].rank().corr(b[m].rank())

def _lead(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.sort_values(["ticker","quarter_end"])
    df[col + "_lead"] = df.groupby("ticker")[col].shift(-1)
    return df

def _panel_ols(df: pd.DataFrame, y: str, x: str) -> Optional[Tuple[float, float, float]]:
    if not HAS_SM:
        return None

    # Keep only the columns we need and drop rows with missing y/x/ticker/quarter_end
    dat = df[[y, x, "ticker", "quarter_end"]].dropna(subset=[y, x, "ticker", "quarter_end"]).copy()
    if dat.empty:
        return None

    # Make sure y and x are numeric
    dat[y] = pd.to_numeric(dat[y], errors="coerce")
    dat[x] = pd.to_numeric(dat[x], errors="coerce")
    dat = dat.dropna(subset=[y, x])
    if dat.empty:
        return None

    # Fixed effects (as floats, not bools)
    tick_fe = pd.get_dummies(dat["ticker"].astype("category"), drop_first=True, dtype=float)

    # Quarter FE: quarter_end may be tz-aware; convert to period strings, then dummies as float
    q = pd.to_datetime(dat["quarter_end"], utc=True, errors="coerce")
    t_per = q.dt.to_period("Q").astype(str)
    time_fe = pd.get_dummies(t_per, drop_first=True, dtype=float)

    # Design matrix: regressor + FE, all as float
    Z = pd.concat([dat[[x]].astype(float), tick_fe, time_fe], axis=1).astype(float)

    # Now it's safe to validate dtypes
    if not all(np.issubdtype(dt, np.number) for dt in Z.dtypes):
        bad = [c for c, dt in Z.dtypes.items() if not np.issubdtype(dt, np.number)]
        raise TypeError(f"Non-numeric columns in design matrix: {bad}")

    # Add constant and fit
    X = sm.add_constant(Z, has_constant="add")
    yv = dat[y].astype(float)

    # Guard against underdetermined systems
    if X.shape[0] <= X.shape[1]:
        return None

    try:
        model = sm.OLS(yv, X, missing="none").fit(cov_type="HC1")
        beta = float(model.params.get(x, np.nan))
        pval = float(model.pvalues.get(x, np.nan))
        r2 = float(model.rsquared)
        return beta, pval, r2
    except Exception:
        # Singular matrix or other numerical issues — skip gracefully
        return None


def run_validation(
    quarter: Optional[str] = None,
    out_txt: Path = Path("outputs/validation_report.txt"),
    out_csv: Path = Path("outputs/validation_panel.csv"),
    min_obs: int = 30,
) -> str:
    # choose input paths (quarter-specific if present)
    p_val = _pick("outputs/valuation.csv", "outputs/valuation_{q}.csv", quarter)
    p_liq = _pick("outputs/liquidity.csv", "outputs/liquidity_{q}.csv", quarter)
    p_cov = _pick("outputs/coverage.csv",  "outputs/coverage_{q}.csv",  quarter)
    p_tru = _pick("outputs/trust.csv",     "outputs/trust_{q}.csv",     quarter)

    frames = []
    if p_val.exists(): frames.append(_load_valuation(p_val))
    if p_liq.exists(): frames.append(_load_liquidity(p_liq))
    if p_cov.exists(): frames.append(_load_coverage(p_cov))
    if p_tru.exists(): frames.append(_load_trust(p_tru))
    if not frames:
        raise FileNotFoundError("No input CSVs found under outputs/. Generate dials first.")

    panel = frames[0]
    for f in frames[1:]:
        panel = panel.merge(f, on=["ticker","quarter_end"], how="outer")

    # Optional subselect by quarter (if user passed one)
    if quarter:
        pq = panel["quarter_end"].dt.to_period("Q").astype(str)
        panel = panel[pq == quarter]

    # Composite = simple mean of available dials (you can swap in your weighted calc if you prefer)
    dial_cols = [c for c in ["valuation_pct","liquidity_pct","coverage_pct","sentiment_pct"] if c in panel.columns]
    panel["irci_composite_pct"] = panel[dial_cols].mean(axis=1, skipna=True)

    # Build t -> t+1 leads
    for c in ["valuation_pct","liquidity_pct","coverage_pct","sentiment_pct","irci_composite_pct"]:
        if c in panel.columns:
            panel = _lead(panel, c)
            if c != "irci_composite_pct":
                panel[f"d_{c}"] = panel[f"{c}_lead"] - panel[c]

    # Minimum obs guard
    if len(panel) < min_obs:
        note = f"[validate] Only {len(panel)} rows after merge; increase history or lower --min-obs."
    else:
        note = f"[validate] Panel rows: {len(panel)}"

    # ICs
    lines = []
    def add(name, lhs, rhs):
        if lhs in panel.columns and rhs in panel.columns:
            lines.append((name, _ic(panel[lhs], panel[rhs])))
        else:
            lines.append((name, np.nan))

    add("Liquidity→ΔLiquidity", "liquidity_pct", "d_liquidity_pct")
    add("Coverage→ΔCoverage",   "coverage_pct",  "d_coverage_pct")
    add("Valuation→ΔValuation", "valuation_pct", "d_valuation_pct")
    add("Trust→ΔTrust",         "sentiment_pct", "d_sentiment_pct")

    # Δ average dial (next) vs IRCI now
    dcols = [c for c in ["d_valuation_pct","d_liquidity_pct","d_coverage_pct","d_sentiment_pct"] if c in panel.columns]
    panel["d_avg"] = panel[dcols].mean(axis=1) if dcols else np.nan
    if "irci_composite_pct" in panel.columns:
        lines.append(("IRCI→ΔAvgDial", _ic(panel["irci_composite_pct"], panel["d_avg"])))
    else:
        lines.append(("IRCI→ΔAvgDial", np.nan))

    # Panel OLS (optional if statsmodels present)
    regs = []
    if HAS_SM:
        for (y,x) in [
            ("d_liquidity_pct","liquidity_pct"),
            ("d_coverage_pct","coverage_pct"),
            ("d_valuation_pct","valuation_pct"),
            ("d_sentiment_pct","sentiment_pct"),
        ]:
            if y in panel.columns and x in panel.columns:
                out = _panel_ols(panel, y, x)
                if out:
                    beta, p, r2 = out
                    regs.append((f"{x} → {y}", beta, p, r2))
    else:
        regs.append(("statsmodels not installed", np.nan, np.nan, np.nan))

    # Ablation (IC of composite with one dial removed)
    abl = []
    if "irci_composite_pct" in panel.columns and not panel["d_avg"].isna().all():
        for drop in ["valuation_pct","liquidity_pct","coverage_pct","sentiment_pct"]:
            if drop in dial_cols:
                cols = [c for c in dial_cols if c != drop]
                panel[f"irci_no_{drop}"] = panel[cols].mean(axis=1, skipna=True)
                abl.append((f"Drop {drop}", _ic(panel[f"irci_no_{drop}"], panel["d_avg"])))

    # Write outputs
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_csv, index=False)

    header = f"== IRCI Validation {'('+quarter+')' if quarter else ''} ==\n{note}\n"
    txt = [header, "\n-- Information Coefficients (t → t+1) --\n"]
    for name, v in lines:
        txt.append(f"{name:24s}: {np.round(v,3) if pd.notna(v) else 'NA'}")
    txt.append("\n-- Panel OLS (FE via dummies) --")
    for name, beta, p, r2 in regs:
        if pd.notna(beta):
            txt.append(f"{name:30s}: beta={beta:0.3f}, p={p:0.3f}, R²={r2:0.3f}")
        else:
            txt.append(name)

    if abl:
        txt.append("\n-- Ablation (IC of IRCI-minus-one vs ΔAvgDial) --")
        for name, v in abl:
            txt.append(f"{name:30s}: IC={np.round(v,3) if pd.notna(v) else 'NA'}")

    report = "\n".join(txt) + "\n"
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(report, encoding="utf-8")
    return report
