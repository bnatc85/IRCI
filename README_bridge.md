# IRCI Bridge (Keep your existing pipeline)

This scaffold lets you **keep all your current inputs/APIs/calculations** and simply **export** results
into a standard set of tables that your dashboard (Excel or Google Sheets) will read.

## How it works
1. Your pipeline generates its usual outputs (no code changes needed).
2. The **exporter** maps your DataFrames/CSVs to a canonical schema.
3. The exporter writes to:
   - **Excel**: `IRCI_lowcode_template.xlsx` (sheets: FILINGS, PRICES, FACTORS, EVENTS, NEWS, DIALS, COMPOSITE)
   - **or** Google Sheets (optional): one tab per table via `gspread`.

## Canonical tables (expected columns)
### FILINGS
FilingDate | Ticker | CIK | FormType | Accession | FilingURL | EventID

### PRICES (daily OHLCV)
Date | Ticker | Open | High | Low | Close | AdjClose | Volume

### FACTORS (daily Fama-French + RF)
Date | Mkt_RF | SMB | HML | RF

### EVENTS (±N-day windows and calmness)
EventID | Ticker | EventDate | WindowStart | WindowEnd | MedianAbsMove_FF | Calmness_Sign | CalmnessScore

### NEWS (one row per article/headline with sentiment)
Date | Ticker | Source | Title | URL | SentimentScore | Confidence | Language

### DIALS (quarterly by ticker)
Quarter | Ticker | Coverage_pct | Trust_pct | Liquidity_pct | Valuation_pct

### COMPOSITE (quarterly; weights included for transparency)
Quarter | Ticker | wCoverage | wTrust | wLiquidity | wValuation | CompositePct | RankInPeer

> Tip: If you already compute calmness/val/liq/coverage in your engine, you can **bypass** any sheet formulas and just write the final values.

## Using the exporter
- Put your CSVs into an `/exports` folder (or hand the exporter your in-memory DataFrames).
- Run: `python irci_exporter.py --excel /path/to/IRCI_lowcode_template.xlsx --from-exports /path/to/exports`
- Or set `--google-sheet` to the Sheet name (requires `gspread` and a service account).

## Versioning & audit
- The exporter writes a small `manifest.json` (inputs, timestamps, weights) into the Excel file's properties and next to the file for your audit trail.
