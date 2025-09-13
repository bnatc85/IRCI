from __future__ import annotations

import subprocess, shlex
from pathlib import Path
from typing import Optional, List, Dict

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
from .trust import trust_snapshot

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
    """
    Convert a datetime-like (scalar or Series) to the UTC quarter-end DATE at 00:00:00.
    Uses calendar-year quarters (Q-DEC). Normalized to midnight to ensure joins work.
    """
    dt = pd.to_datetime(s, utc=True, errors="coerce")

    # Series path
    if isinstance(dt, pd.Series):
        base = dt.dt.tz_convert("UTC").dt.tz_localize(None)
        # IMPORTANT: normalize() after end_time
        return (
            base.dt.to_period("Q-DEC")
                .dt.end_time
                .dt.tz_localize("UTC")
                .dt.normalize()
        )
    
    # Scalar Timestamp path
    base = dt.tz_convert("UTC").tz_localize(None)
    p = base.to_period("Q-DEC")
    return p.end_time.tz_localize("UTC").normalize()


    # Scalar Timestamp path
    base = dt.tz_convert("UTC").tz_localize(None)
    p = base.to_period("Q-DEC")
    return p.end_time.tz_localize("UTC")


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
            q = q.rename(columns={"date": "quarter_end", "index": "quarter_end"})
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
    df["rank_in_peer"] = df["irci_composite_pct"].rank(method="min", ascending=False)

    # Save & print
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cols = ["ticker", "quarter_end", "irci_composite_pct", "valuation_pct", "liquidity_pct", "coverage_pct", "sentiment_pct", "rank_in_peer"]
    df[cols].to_csv(out_csv, index=False)
    typer.secho(f"Wrote {out_csv} with {len(df)} rows", fg=typer.colors.GREEN)

    snap = df.sort_values("irci_composite_pct", ascending=False)
    typer.echo(f"\n== IRCI composite @ {pd.to_datetime(last_bucket).date()} ==")
    typer.echo(snap[["ticker", "irci_composite_pct", "valuation_pct", "liquidity_pct", "coverage_pct", "rank_in_peer"]]
               .to_string(index=False, float_format=lambda x: f"{x: .1f}"))


if __name__ == "__main__":
    app()
