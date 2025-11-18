#!/usr/bin/env bash
set -euo pipefail
SYMS="${1:-AAPL,MSFT,AMZN,GOOGL}"
Q="${2:-2025Q2}"
START="${3:-2025-04-01}"
END="${4:-2025-06-30}"

irci trust     --symbols "$SYMS" --start "$START" --end "$END" --out-csv outputs/trust.csv
irci valuation --symbols "$SYMS" --as-of "$END" --out-csv outputs/valuation_${Q,,}.csv
irci coverage  --symbols "$SYMS" --as-of "$END" --out-csv outputs/coverage_${Q,,}.csv
irci liquidity --symbols "$SYMS" --start "$START" --end "$END" --out-csv outputs/liquidity_${Q,,}.csv
irci export-bridge --out-dir outputs --exports exports --quarter "$Q"
python tools/irci_bridge/irci_exporter.py --from-exports exports --excel artifacts/IRCI_lowcode_template.xlsx