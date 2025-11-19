from __future__ import annotations
import subprocess, shlex
from pathlib import Path
from typing import Optional, List, Dict
from .validate import run_validation
import pandas as pd
import numpy as np
import typer
from .config import Settings
from .logging import get_logger
from .market import fetch_prices_fmp
from .liquidity import (
    daily_liquidity_bundle,
    quarterly_liquidity,
    add_liquidity_percentile,
)
from .coverage import coverage_snapshot

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib   # py310 fallback

app = typer.Typer(help="IRCI command-line interface")
log = get_logger("irci")


# ---------------------------
# small helpers
# ---------------------------
def _load_cfg() -> dict:
    for p in (Path("irci.toml"), Path.home() / ".irci.toml"):
        if p.exists():
            return tomllib.loads(p.read_text())
    return {}


def _quarter_bounds(qstr: str) -> tuple[str, str]:
    q = pd.Period(qstr, freq="Q-DEC")
    return q.start_time.date().isoformat(), q.end_time.date().isoformat()


def _sh(cmd: str):
    typer.secho(f"$ {cmd}", fg=typer.colors.BLUE)
    subprocess.run(cmd, shell=True, check=True)


def _pick_symbols(preset: str | None, symbols: str | None, cfg: dict) -> str:
    if symbols:
        return symbols
    if preset and "presets" in cfg and preset in cfg["presets"]:
        return cfg["presets"][preset].get("symbols", "")
    return cfg.get("defaults", {}).get("symbols", "")


def _to_bucket(s):
    dt = pd.to_datetime(s, utc=True, errors="coerce")
    if isinstance(dt, pd.Series):
        return dt.dt.to_period("Q-DEC").dt.end_time.dt.tz_localize("UTC").dt.normalize()
    return dt.to_period("Q-DEC").end_time.tz_localize("UTC").normalize()

# ---------------------------
# convenience runner
# ---------------------------
@app.command("run")
def run_cmd(
    preset: str = typer.Option(None, help="Preset from irci.toml (e.g., 'bigtech')"),
    symbols: str = typer.Option(None, help='Comma list e.g. "AAPL,MSFT,AMZN,GOOGL"'),
    quarter: str = typer.Option(None, help="Quarter like 2025Q2"),
    news_csv: Path | None = typer.Option(None, help="Optional news CSV"),
    out_dir: Path = typer.Option(Path("outputs"), help="Output directory"),
):
    cfg = _load_cfg()
    syms = _pick_symbols(preset, symbols, cfg)
    if not syms:
        raise typer.BadParameter("No symbols. Provide --symbols or set defaults/preset in irci.toml")

    q = quarter or (cfg.get("defaults", {}) or {}).get("quarter")
    if not q:
        raise typer.BadParameter("No quarter. Provide --quarter or set defaults.quarter in irci.toml")

    start, end = _quarter_bounds(q)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Trust
    trust_out = out_dir / "trust.csv"
    cmd = f'irci trust --symbols "{syms}" --start {start} --end {end} --out-csv {trust_out}'
    if news_csv:
        cmd += f" --news-csv {shlex.quote(str(news_csv))}"
    _sh(cmd)

    # 2) Valuation
    val_out = out_dir / f"valuation_{q.lower()}.csv"
    _sh(f'irci valuation --symbols "{syms}" --as-of {end} --out-csv {val_out}')

    # 3) Coverage
    cov_out = out_dir / f"coverage_{q.lower()}.csv"
    _sh(f'irci coverage --symbols "{syms}" --as-of {end} --out-csv {cov_out}')

    # 3.5) Liquidity  ← ADD THIS BLOCK
    liq_out = out_dir / "liquidity.csv"
    _sh(f'irci liquidity --symbols "{syms}" --start {start} --end {end} --out-csv {liq_out}')

    # 4) Composite
    comp_out = out_dir / f"irci_composite_{q.lower()}.csv"
    _sh(
        "irci composite "
        f"--valuation {val_out} "
        f"--liquidity {out_dir}/liquidity.csv "
        f"--coverage {cov_out} "
        f"--sentiment-csv {trust_out} "
        f"--quarter {q} "
        f"--out-csv {comp_out}"
    )

    typer.secho(f"Done. Composite: {comp_out}", fg=typer.colors.GREEN)


@app.command("wizard")
def wizard_cmd():
    syms = typer.prompt("Symbols (comma-separated)", default="AAPL,MSFT,AMZN,GOOGL")
    quarter = typer.prompt("Quarter (e.g., 2025Q2)", default="2025Q2")
    news = typer.prompt("News CSV (optional)", default="")
    args = f'--symbols "{syms}" --quarter {quarter}'
    if news.strip():
        args += f" --news-csv {news}"
    if typer.confirm(f"Run now with: irci run {args} ?", default=True):
        _sh(f"irci run {args}")


@app.command("init")
def init_cmd(
    path: Path = typer.Option(Path.home() / ".irci.toml", help="Where to write the config"),
):
    template = """# IRCI config
[defaults]
symbols = "AAPL,MSFT,AMZN,GOOGL"
quarter = "2025Q2"
news_csv = "data/news.csv"

[presets.bigtech]
symbols = "AAPL,MSFT,AMZN,GOOGL"

[presets.mag7]
symbols = "AAPL,MSFT,AMZN,GOOGL,NVDA,META,TSLA"
"""
    path.write_text(template)
    typer.secho(f"Wrote {path}", fg=typer.colors.GREEN)


# ---------------------------
# TRUST (sentiment dial)
# ---------------------------
@app.command("trust")
def trust_cmd(
    symbols: str = typer.Option(..., help='Comma-separated tickers, e.g. "AAPL,MSFT,GOOGL,AMZN"'),
    start: Optional[str] = typer.Option(None, help="Start date (YYYY-MM-DD)"),
    end: Optional[str] = typer.Option(None, help="End date (YYYY-MM-DD)"),
    news_csv: Optional[Path] = typer.Option(None, help="Optional CSV: date,ticker,title|text"),
    out_csv: Path = typer.Option(Path("./outputs/trust.csv"), help="Output CSV"),
):
    from .trust import trust_snapshot
    s = Settings.load()
    syms = [t.strip().upper() for t in symbols.split(",") if t.strip()]
    if not syms:
        typer.secho("No symbols provided.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    news_df = None
    if news_csv and news_csv.exists():
        news_df = pd.read_csv(news_csv)

    df = trust_snapshot(syms, start=start, end=end, news_df=news_df, apikey=s.fmp_api_key)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    typer.secho(f"Wrote {out_csv} with {len(df)} rows", fg=typer.colors.GREEN)

    last_q = df["quarter_end"].max()
    snap = df[df["quarter_end"] == last_q].copy().sort_values("trust_pct", ascending=False)
    cols = ["ticker", "trust_pct", "p_event_calm", "p_baseline_calm", "p_media_tone", "event_count"]
    typer.echo(f"\n== Trust snapshot @ {pd.to_datetime(last_q).date()} ==")
    typer.echo(snap[cols].to_string(index=False))


# ---------------------------
# COVERAGE (disclosure cadence dial)
# ---------------------------
@app.command("coverage")
def coverage_cmd(
    symbols: str = typer.Option(..., help='Comma-separated tickers, e.g. "AAPL,MSFT,GOOGL,AMZN"'),
    as_of: Optional[str] = typer.Option(None, help="Quarter to score (YYYY-MM-DD)"),
    out_csv: Path = typer.Option(Path("./outputs/coverage.csv"), help="Output CSV"),
):
    syms = [t.strip().upper() for t in symbols.split(",") if t.strip()]
    if not syms:
        typer.secho("No symbols provided.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    df = coverage_snapshot(syms, as_of=as_of or None)

    # Stamp quarter_end for downstream joins
    if as_of:
        as_of_ts = pd.to_datetime(as_of, utc=True, errors="coerce")
    else:
        as_of_ts = pd.Timestamp.utcnow().tz_localize("UTC")
    df["as_of"] = as_of_ts
    df["quarter_end"] = _to_bucket(df["as_of"])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    typer.secho(f"Wrote {out_csv} with {len(df)} rows", fg=typer.colors.GREEN)

    snap = df.sort_values("coverage_pct", ascending=False).copy()
    snap = snap.rename(columns={"q_8k_count": "8-Ks (quarter)", "q_days_to_10q": "days_to_10Q/10K"})
    cols = ["ticker", "coverage_pct", "8-Ks (quarter)", "days_to_10Q/10K"]
    typer.echo(f"\n== Coverage snapshot @ {pd.to_datetime(as_of_ts).date()} ==")
    typer.echo(snap[cols].to_string(index=False, float_format=lambda x: f"{x: .1f}"))


# ---------------------------
# LIQUIDITY (market microstructure dial)
# ---------------------------
@app.command("liquidity")
def liquidity_cmd(
    symbols: str = typer.Option(..., help='Comma-separated tickers, e.g. "AAPL,MSFT,GOOGL,AMZN"'),
    start: str = typer.Option("2022-01-01", help="YYYY-MM-DD"),
    end: str = typer.Option(None, help="YYYY-MM-DD (defaults to today)"),
    out_csv: Path = typer.Option(Path("./outputs/liquidity.csv"), help="Output CSV"),
    quarter_freq: str = typer.Option("QE-DEC", help="Quarter-end freq (e.g., QE-DEC, QE-JUN)"),
    autofetch: bool = typer.Option(True, help="Fetch prices if parquet missing"),
):
    s = Settings.load()
    syms: List[str] = [t.strip().upper() for t in symbols.split(",") if t.strip()]
    if not syms:
        typer.secho("No symbols provided.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    if end is None:
        end = pd.Timestamp.utcnow().date().isoformat()

    rows = []
    for sym in syms:
        pq = Path(f"./data/{sym}.parquet")
        if pq.exists() and not autofetch:
            px = pd.read_parquet(pq)
        else:
            px = fetch_prices_fmp(sym, start, end, s.fmp_api_key) if s.fmp_api_key else pd.read_parquet(pq)
            pq.parent.mkdir(parents=True, exist_ok=True)
            px.to_parquet(pq)

        daily = daily_liquidity_bundle(sym, s, px, end)
        q = quarterly_liquidity(daily, freq=quarter_freq).reset_index()
        if "quarter_end" not in q.columns:
            q = q.rename(columns={"Date": "quarter_end", "date": "quarter_end", "index": "quarter_end"})
            q = quarterly_liquidity(daily, freq=quarter_freq).reset_index()
            if "quarter_end" not in q.columns:
                q = q.rename(columns={"Date": "quarter_end", "date": "quarter_end", "index": "quarter_end"})
        q["quarter_end"] = pd.to_datetime(q["quarter_end"], utc=True)
        q["ticker"] = sym
        rows.append(q)

    out = pd.concat(rows, ignore_index=True)
    out = add_liquidity_percentile(out)  # adds liquidity_pct per quarter
    out = out.sort_values(["quarter_end", "liquidity_pct"], ascending=[True, False])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)
    typer.secho(f"Wrote {out_csv} with {len(out)} rows", fg=typer.colors.GREEN)

    last_q = out["quarter_end"].max()
    snap = out.loc[out["quarter_end"] == last_q].copy()
    disp = snap[["ticker", "liquidity_pct", "q_turnover", "q_amihud_e6", "q_spread_bps"]].copy()
    disp["turnover (%)"] = disp["q_turnover"] * 100.0
    disp["amihud (per $1M)"] = disp["q_amihud_e6"].map(lambda x: f"{x:.2e}")
    disp["roll_spread (bps)"] = disp["q_spread_bps"].map(lambda x: f"{x:,.2f}")
    disp = disp[["ticker", "liquidity_pct", "turnover (%)", "amihud (per $1M)", "roll_spread (bps)"]]
    typer.echo(f"\n== Liquidity snapshot @ {pd.to_datetime(last_q).date()} ==")
    typer.echo(disp.sort_values("liquidity_pct", ascending=False).to_string(index=False))


# ---------------------------
# VALUATION (fundamental dial)
# ---------------------------
@app.command("valuation")
def valuation_cmd(
    symbols: str = typer.Option(..., help='Comma-separated tickers, e.g. "AAPL,MSFT,GOOGL,AMZN"'),
    as_of: Optional[str] = typer.Option(None, help="Use EV as of this date (YYYY-MM-DD). Defaults to most recent."),
    out_csv: Path = typer.Option(Path("./outputs/valuation.csv"), help="Output CSV"),
    units: str = typer.Option("raw", "--units", help="Display units for EV/EBITDA: raw, B, or M"),
):
    try:
        from .valuation import valuation_snapshot
    except Exception as e:
        typer.secho(f"Import error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    syms = [t.strip().upper() for t in symbols.split(",") if t.strip()]
    if not syms:
        typer.secho("No symbols provided.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    df = valuation_snapshot(syms, as_of=as_of or None)

    # Stamp quarter_end for downstream consistency
    as_of_ts = pd.to_datetime(as_of, utc=True, errors="coerce") if as_of else pd.Timestamp.utcnow().tz_localize("UTC")
    df["as_of"] = as_of_ts
    df["quarter_end"] = _to_bucket(df["as_of"])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    typer.secho(f"Wrote {out_csv} with {len(df)} rows", fg=typer.colors.GREEN)

    # Pretty print (with units)
    unit = (units or "raw").upper()
    div, suffix = (1.0, "")
    if unit == "B":
        div, suffix = 1e9, " (B)"
    elif unit == "M":
        div, suffix = 1e6, " (M)"

    disp = df.copy()
    if div != 1.0:
        disp["enterprise_value"] = disp["enterprise_value"] / div
        disp["ttm_ebitda"] = disp["ttm_ebitda"] / div
        disp = disp.rename(columns={
            "enterprise_value": f"enterprise_value{suffix}",
            "ttm_ebitda": f"ttm_ebitda{suffix}",
        })

    ev_col = "enterprise_value" if div == 1.0 else f"enterprise_value{suffix}"
    ebitda_col = "ttm_ebitda" if div == 1.0 else f"ttm_ebitda{suffix}"

    # format percent columns
    if "valuation_gap_pct" in disp.columns:
        disp["valuation_gap_pct"] = disp["valuation_gap_pct"].map(lambda x: f"{x:.1%}" if pd.notna(x) else "NA")
    for c in ("valuation_pct", "valuation_pct_empirical"):
        if c in disp.columns:
            disp[c] = disp[c].map(lambda x: f"{x:.0f}%" if pd.notna(x) else "NA")

    cols = [
        "ticker",
        "valuation_pct",
        "valuation_pct_empirical",
        "ev_to_ebitda",
        "peer_mean_excl_self",
        "valuation_gap_pct",
        ev_col,
        ebitda_col,
        "ebitda_method",
    ]
    cols = [c for c in cols if c in disp.columns]
    typer.echo(disp[cols].sort_values("valuation_pct", ascending=False).to_string(index=False, float_format=lambda x: f"{x:,.3f}"))


# ---------------------------
# COMPOSITE (merge dials)
# ---------------------------
@app.command("composite")
def composite_cmd(
    valuation: Path = typer.Option(Path("./outputs/valuation.csv"), help="CSV from irci valuation"),
    liquidity: Path = typer.Option(Path("./outputs/liquidity.csv"), help="CSV from irci liquidity"),
    coverage: Optional[Path] = typer.Option(None, help="Optional CSV from irci coverage"),
    sentiment_csv: Optional[Path] = typer.Option(None, help="Optional trust CSV with sentiment_pct & quarter_end"),
    out_csv: Path = typer.Option(Path("./outputs/irci_composite.csv"), help="Output CSV"),
    quarter: Optional[str] = typer.Option(None, "--quarter", help="Force to a specific quarter like 2025Q2"),
    w_valuation: float = typer.Option(0.35, help="Weight for valuation dial"),
    w_liquidity: float = typer.Option(0.35, help="Weight for liquidity dial"),
    w_coverage: float = typer.Option(0.15, help="Weight for coverage dial"),
    w_sentiment: float = typer.Option(0.15, help="Weight for sentiment dial"),
    round_to: int = typer.Option(1, help="Rounding for composite percent"),
):
    # Load files
    if not valuation.exists():
        typer.secho(f"Valuation file not found: {valuation}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    if not liquidity.exists():
        typer.secho(f"Liquidity file not found: {liquidity}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    v = pd.read_csv(valuation, parse_dates=["as_of"])
    liq = pd.read_csv(liquidity)
    cov = pd.read_csv(coverage) if (coverage and coverage.exists()) else pd.DataFrame(columns=["ticker", "coverage_pct"])
    sent = pd.read_csv(sentiment_csv, parse_dates=["quarter_end"]) if (sentiment_csv and sentiment_csv.exists()) else None

    # Normalize buckets
    v["as_of_bucket"] = _to_bucket(v["as_of"])
    if "as_of" in liq.columns:
        liq["as_of"] = pd.to_datetime(liq["as_of"], utc=True, errors="coerce")
        liq["as_of_bucket"] = _to_bucket(liq["as_of"])
    if "quarter_end" in liq.columns and "as_of_bucket" not in liq.columns:
        liq["as_of_bucket"] = _to_bucket(liq["quarter_end"])
    if "as_of" in cov.columns:
        cov["as_of"] = pd.to_datetime(cov["as_of"], utc=True, errors="coerce")
        cov["as_of_bucket"] = _to_bucket(cov["as_of"])
    if sent is not None and "quarter_end" in sent.columns:
        sent["quarter_end"] = pd.to_datetime(sent["quarter_end"], utc=True, errors="coerce")
        sent["quarter_end"] = _to_bucket(sent["quarter_end"])
    if sent is not None and "sentiment_pct" not in sent.columns and "trust_pct" in sent.columns:
        sent = sent.rename(columns={"trust_pct": "sentiment_pct"})
    # Choose bucket
    if quarter:
        last_bucket = pd.Period(quarter, freq="Q-DEC").end_time.tz_localize("UTC").normalize()
    else:
        candidates = []
        if "as_of_bucket" in v.columns and pd.notna(v["as_of_bucket"].max()):
            candidates.append(v["as_of_bucket"].max())
        if "as_of_bucket" in liq.columns and pd.notna(liq["as_of_bucket"].max()):
            candidates.append(liq["as_of_bucket"].max())
        if "as_of_bucket" in cov.columns and pd.notna(cov["as_of_bucket"].max()):
            candidates.append(cov["as_of_bucket"].max())
        if not candidates:
            typer.secho("Could not determine a quarter bucket from inputs.", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        last_bucket = max(candidates)

    # Slice last bucket rows
    v_last = v.loc[v["as_of_bucket"] == last_bucket, ["ticker", "as_of_bucket", "valuation_pct"]].rename(columns={"as_of_bucket": "quarter_end"})
    liq_last = liq.loc[liq["as_of_bucket"] == last_bucket, ["ticker", "as_of_bucket", "liquidity_pct"]].rename(columns={"as_of_bucket": "quarter_end"})
    if "as_of_bucket" in cov.columns:
        cov_last = cov.loc[cov["as_of_bucket"] == last_bucket, ["ticker", "as_of_bucket", "coverage_pct"]].rename(columns={"as_of_bucket": "quarter_end"})
    else:
        cov_last = pd.DataFrame(columns=["ticker", "quarter_end", "coverage_pct"])
    if sent is not None:
        sent_last = sent.loc[sent["quarter_end"] == last_bucket, ["ticker", "quarter_end", "sentiment_pct"]]
    else:
        sent_last = pd.DataFrame(columns=["ticker", "quarter_end", "sentiment_pct"])

    # Merge
    df = v_last.merge(liq_last, on=["ticker", "quarter_end"], how="outer")
    df = df.merge(cov_last, on=["ticker", "quarter_end"], how="outer")
    df = df.merge(sent_last, on=["ticker", "quarter_end"], how="outer")

    # Row-wise composite with weight re-normalization
    def row_composite(row) -> float:
        vals, wts = [], []
        if pd.notna(row.get("valuation_pct")):
            vals.append(float(row["valuation_pct"])); wts.append(w_valuation)
        if pd.notna(row.get("liquidity_pct")):
            vals.append(float(row["liquidity_pct"])); wts.append(w_liquidity)
        if pd.notna(row.get("coverage_pct")):
            vals.append(float(row["coverage_pct"])); wts.append(w_coverage)
        if pd.notna(row.get("sentiment_pct")):
            vals.append(float(row["sentiment_pct"])); wts.append(w_sentiment)
        if not wts:
            return np.nan
        return float(np.dot(vals, wts) / sum(wts))

    df["irci_composite_pct"] = df.apply(row_composite, axis=1).round(round_to)
    df["rank_in_peer"] = df["irci_composite_pct"].rank(method="dense", ascending=False)

    # Save & print
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cols = ["ticker", "quarter_end", "irci_composite_pct", "valuation_pct", "liquidity_pct", "coverage_pct", "sentiment_pct", "rank_in_peer"]
    df[cols].to_csv(out_csv, index=False)
    typer.secho(f"Wrote {out_csv} with {len(df)} rows", fg=typer.colors.GREEN)

    snap = df.sort_values("irci_composite_pct", ascending=False)
    typer.echo(f"\n== IRCI composite @ {pd.to_datetime(last_bucket).date()} ==")
    typer.echo(snap[["ticker", "irci_composite_pct", "valuation_pct", "liquidity_pct", "coverage_pct", "rank_in_peer"]]
               .to_string(index=False, float_format=lambda x: f"{x: .1f}"))

import typer

@app.command("validate")
def validate_cmd(
    quarter: Optional[str] = typer.Option(None, "--quarter", help="Quarter like 2025Q2; if omitted, use all data"),
    out_txt: Path = typer.Option(Path("outputs/validation_report.txt"), "--out-txt", help="Report path"),
    out_csv: Path = typer.Option(Path("outputs/validation_panel.csv"), "--out-csv", help="Panel CSV path"),
    min_obs: int = typer.Option(30, "--min-obs", help="Min rows required to evaluate"),
):
    """
    Validate IRCI's proximal impact: ICs, panel OLS (if statsmodels installed), and ablation.
    Auto-picks quarter-specific files (e.g., valuation_2025q2.csv) if present.
    """
    rep = run_validation(quarter=quarter, out_txt=out_txt, out_csv=out_csv, min_obs=min_obs)
    typer.secho(rep, fg=typer.colors.GREEN)


@app.command("export-bridge")
def export_bridge_cmd(
    out_dir: Path = typer.Option(Path("./outputs"), help="Where your pipeline CSVs are written"),
    exports: Path = typer.Option(Path("./exports"), help="Where to write the canonical exports/*.csv"),
    quarter: Optional[str] = typer.Option(None, help="Force a quarter like 2025Q2; else use latest bucket"),
    w_valuation: float = typer.Option(0.35, help="Weight for valuation dial (for COMPOSITE.csv)"),
    w_liquidity: float = typer.Option(0.35, help="Weight for liquidity dial"),
    w_coverage: float = typer.Option(0.15, help="Weight for coverage dial"),
    w_trust: float = typer.Option(0.15, help="Weight for trust dial"),
    excel: Optional[Path] = typer.Option(None, help="(Optional) Excel file to write sheets to"),
):
    """
    Build low/no-code exports from existing outputs:
      - DIALS.csv   (quarter, ticker, Coverage/Trust/Liquidity/Valuation %)
      - COMPOSITE.csv (quarter, ticker, weights, CompositePct, RankInPeer)
      - COMPOSITE_WEIGHTED.csv (optional: simple weighted composite from DIALS)
    If present, will also pass through NEWS.csv (if you supplied --news-csv to trust).
    """
    exports.mkdir(parents=True, exist_ok=True)
    exp = exports
    def read_latest(glob_pat: str):
        paths = sorted(out_dir.glob(glob_pat))
        return pd.read_csv(paths[-1]) if paths else pd.DataFrame()

    # Load whatever exists
    trust = read_latest("trust*.csv")
    liq   = read_latest("liquidity*.csv")
    val   = read_latest("valuation*.csv")
    cov   = read_latest("coverage*.csv")
    comp  = read_latest("irci_composite*.csv")

    # Parse/standardize quarter_end columns
    def bucketize(s):
        dt = pd.to_datetime(s, utc=True, errors="coerce")
        return dt.dt.to_period("Q-DEC").dt.end_time.dt.tz_localize("UTC").dt.normalize()

    for df, col in (
        (trust, "quarter_end"),
        (liq, "quarter_end"),
        (val, "quarter_end"),
        (cov, "quarter_end"),
        (comp, "quarter_end"),
    ):
        if not df.empty and col in df.columns:
            df[col] = bucketize(df[col])
        elif not df.empty and "as_of" in df.columns:
            df["quarter_end"] = bucketize(df["as_of"])

    # Choose quarter bucket
    if quarter:
        last_bucket = pd.Period(quarter, freq="Q-DEC").end_time.tz_localize("UTC").normalize()
    else:
        candidates = []
        for df in (trust, liq, val, cov, comp):
            if not df.empty and "quarter_end" in df.columns:
                candidates.append(df["quarter_end"].max())
        if not candidates:
            typer.secho("No quarter_end found in outputs; run the dials first.", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        last_bucket = max(candidates)

    # Slice helpers
    def slice_cols(df, cols_map):
        if df.empty:
            return pd.DataFrame(columns=["ticker"] + list(cols_map.values()) + ["quarter_end"])
        df2 = df.loc[df["quarter_end"] == last_bucket].copy()
        df2 = df2.rename(columns=cols_map)
        keep = ["ticker", "quarter_end"] + list(cols_map.values())
        return df2[[c for c in keep if c in df2.columns]]

    trust_q = slice_cols(trust, {"trust_pct": "Trust_pct"})
    liq_q   = slice_cols(liq,   {"liquidity_pct": "Liquidity_pct"})
    val_q   = slice_cols(val,   {"valuation_pct": "Valuation_pct"})
    cov_q   = slice_cols(cov,   {"coverage_pct": "Coverage_pct"})
        # Build a per-ticker opportunity/risk export for the chosen quarter
    val_meta = slice_cols(val, {
        "valuation_gap_pct": "valuation_gap_pct",
        "enterprise_value":  "enterprise_value",
    })
    if not val_meta.empty:
        vm = val_meta.rename(columns={"ticker":"Ticker"}).copy()
        gap = pd.to_numeric(vm["valuation_gap_pct"], errors="coerce")
        EV  = pd.to_numeric(vm["enterprise_value"],  errors="coerce")
        target_closure = 0.50

        vm["ValuationOpportunity_$"] = EV * np.where(gap < 0, -gap * target_closure / 100.0, 0.0)
        vm["CompressionRisk_$"]      = EV * np.where(gap > 0,  gap * target_closure / 100.0, 0.0)
        vm["Opportunity_%EV"]        = 100.0 * vm["ValuationOpportunity_$"] / EV

        mask = vm["Opportunity_%EV"] < 1.0
        vm.loc[mask, ["ValuationOpportunity_$","Opportunity_%EV"]] = 0.0

        # Keep the quarter label consistent
        vm["Quarter"] = vm["quarter_end"].dt.to_period("Q-DEC").astype(str)
        vm_out = vm[["Quarter","Ticker","enterprise_value","valuation_gap_pct",
                    "ValuationOpportunity_$","CompressionRisk_$","Opportunity_%EV"]]
        vm_out.to_csv(exports / "VALUATION_OPPORTUNITY.csv", index=False)


    # Build DIALS
    from functools import reduce
    parts = [x for x in (trust_q, liq_q, val_q, cov_q) if not x.empty]
    if not parts:
        typer.secho("No dial inputs found in outputs/.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    dials = reduce(lambda a, b: pd.merge(a, b, on=["ticker", "quarter_end"], how="outer"), parts)
    p = dials["quarter_end"].dt.to_period("Q-DEC")
    dials["Quarter"] = p.astype(str)  # e.g., '2025Q2'
    dials = dials.rename(columns={"ticker": "Ticker"})
    dials_out = dials[["Quarter", "Ticker", "Coverage_pct", "Trust_pct", "Liquidity_pct", "Valuation_pct"]]
    dials_out.to_csv(exports / "DIALS.csv", index=False)

    # Build COMPOSITE (pipeline version if present; else weighted fallback)
    if not comp.empty and "irci_composite_pct" in comp.columns:
        comp_q = comp[comp["quarter_end"] == last_bucket].copy()

        out_comp = comp_q[["ticker", "quarter_end", "irci_composite_pct", "rank_in_peer"]].copy()
        p2 = out_comp["quarter_end"].dt.to_period("Q-DEC")
        out_comp["Quarter"] = p2.astype(str)
        out_comp = out_comp.rename(columns={
            "ticker": "Ticker",
            "irci_composite_pct": "CompositePct",
        })
        # Keep weights as metadata; tag provenance
        out_comp["wCoverage"]  = w_coverage
        out_comp["wTrust"]     = w_trust
        out_comp["wLiquidity"] = w_liquidity
        out_comp["wValuation"] = w_valuation
        out_comp["composite_source"] = "pipeline"

        out_comp = out_comp[
            ["Quarter", "Ticker", "wCoverage", "wTrust", "wLiquidity", "wValuation", "CompositePct", "rank_in_peer", "composite_source"]
        ]
        out_comp.to_csv(exports / "COMPOSITE.csv", index=False)

        # Also produce a simple weighted version from DIALS for comparison
        def _to_quarter(s):
            return s.dt.to_period("Q-DEC").astype(str)

        W = {"Coverage": w_coverage, "Trust": w_trust, "Liquidity": w_liquidity, "Valuation": w_valuation}
        WSUM = (W["Coverage"] + W["Trust"] + W["Liquidity"] + W["Valuation"]) or 1.0

        dials_q = dials.copy()
        dials_q["Quarter"] = _to_quarter(dials_q["quarter_end"])

        wc = dials_q.assign(
            wCoverage=W["Coverage"],
            wTrust=W["Trust"],
            wLiquidity=W["Liquidity"],
            wValuation=W["Valuation"],
        )

        for c in ["Coverage_pct", "Trust_pct", "Liquidity_pct", "Valuation_pct"]:
            wc[c] = pd.to_numeric(wc[c], errors="coerce")

        wc["CompositePct"] = (
            wc["Coverage_pct"] * wc["wCoverage"]
            + wc["Trust_pct"] * wc["wTrust"]
            + wc["Liquidity_pct"] * wc["wLiquidity"]
            + wc["Valuation_pct"] * wc["wValuation"]
        ) / WSUM

        wc["rank_in_peer"] = wc.groupby("Quarter")["CompositePct"].rank(ascending=False, method="dense")
        wc["composite_source"] = "weighted"

        wc_out = wc[[
            "Quarter", "Ticker", "wCoverage", "wTrust", "wLiquidity", "wValuation",
            "CompositePct", "rank_in_peer", "composite_source"
        ]]
        wc_out.to_csv(exports / "COMPOSITE_WEIGHTED.csv", index=False)

    else:
        # Fallback: compute weighted from DIALS only
        tmp = dials_out.copy()
        for c in ["Coverage_pct", "Trust_pct", "Liquidity_pct", "Valuation_pct"]:
            tmp[c] = pd.to_numeric(tmp[c], errors="coerce")
        wsum = w_coverage + w_trust + w_liquidity + w_valuation
        tmp["CompositePct"] = (
            (tmp["Coverage_pct"] * w_coverage) +
            (tmp["Trust_pct"] * w_trust) +
            (tmp["Liquidity_pct"] * w_liquidity) +
            (tmp["Valuation_pct"] * w_valuation)
        ) / (wsum or 1.0)
        tmp["CompositePct"] = tmp["CompositePct"].round(1)
        tmp["rank_in_peer"] = tmp.groupby("Quarter")["CompositePct"].rank(method="dense", ascending=False)
        comp_q = tmp.rename(columns={"Ticker": "Ticker"})
        comp_q["wCoverage"] = w_coverage
        comp_q["wTrust"] = w_trust
        comp_q["wLiquidity"] = w_liquidity
        comp_q["wValuation"] = w_valuation
        comp_q["composite_source"] = "weighted_fallback"
        comp_q = comp_q[["Quarter", "Ticker", "wCoverage", "wTrust", "wLiquidity", "wValuation", "CompositePct", "rank_in_peer", "composite_source"]]
        comp_q.to_csv(exports / "COMPOSITE.csv", index=False)

    # Optional: pass-through NEWS (adjust to your actual NEWS source if needed)
    # news_csv = out_dir / "trust.csv"

    msg = f"Wrote {exports/'DIALS.csv'} and {exports/'COMPOSITE.csv'}"
    if (exports / "COMPOSITE_WEIGHTED.csv").exists():
        msg += f" and {exports/'COMPOSITE_WEIGHTED.csv'}"
        msg += f" for {last_bucket.date()}"
    typer.secho(msg, fg=typer.colors.GREEN)

    if excel is not None:
        try:
            comp = pd.read_csv(exports / "COMPOSITE.csv")
            cmp_w_path = exports / "COMPOSITE_WEIGHTED.csv"
            comp_w = pd.read_csv(cmp_w_path) if cmp_w_path.exists() else None

            if excel.exists():
                # append sheets
                with pd.ExcelWriter(excel, engine="openpyxl", mode="a", if_sheet_exists="replace") as xls:
                    comp.to_excel(xls, sheet_name="COMPOSITE", index=False)
                    if comp_w is not None:
                        comp_w.to_excel(xls, sheet_name="COMPOSITE_WEIGHTED", index=False)
                        both = pd.concat(
                            [comp.assign(composite_source="pipeline"),
                                comp_w.assign(composite_source="weighted")],
                            ignore_index=True
                        )
                        both.to_excel(xls, sheet_name="COMPOSITE_ALL", index=False)
            else:
                # new file
                with pd.ExcelWriter(excel, engine="openpyxl", mode="w") as xls:
                    comp.to_excel(xls, sheet_name="COMPOSITE", index=False)
                    if comp_w is not None:
                        comp_w.to_excel(xls, sheet_name="COMPOSITE_WEIGHTED", index=False)
                        both = pd.concat(
                            [comp.assign(composite_source="pipeline"),
                                comp_w.assign(composite_source="weighted")],
                            ignore_index=True
                        )
                        both.to_excel(xls, sheet_name="COMPOSITE_ALL", index=False)
            typer.secho(f"Updated Excel: {excel}", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"[WARN] Excel write skipped: {e}", fg=typer.colors.YELLOW)