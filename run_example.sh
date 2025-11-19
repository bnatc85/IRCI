#!/bin/bash
# IRCI Example: Generate Q3 2025 scores for big tech companies
# Run this script to reproduce the results from the quickstart demo

set -e  # Exit on error

echo "========================================="
echo "IRCI Q3 2025 Big Tech Analysis"
echo "========================================="
echo ""

# 1. Check if irci is installed
if ! command -v irci &> /dev/null; then
    echo "❌ Error: irci command not found"
    echo "Please run: pip install -e ."
    exit 1
fi

echo "✓ IRCI CLI found"
echo ""

# 2. Create outputs directory if it doesn't exist
mkdir -p outputs

# 3. Run the full pipeline for Q3 2025
echo "Running IRCI pipeline for Q3 2025..."
echo "Companies: AAPL, MSFT, GOOGL, AMZN"
echo ""

irci run --symbols "AAPL,MSFT,GOOGL,AMZN" --quarter 2025Q3

echo ""
echo "========================================="
echo "✓ Pipeline Complete!"
echo "========================================="
echo ""
echo "Results saved to outputs/ directory:"
echo ""
echo "  📊 outputs/irci_composite_2025q3.csv  - Final composite scores & rankings"
echo "  📈 outputs/trust.csv                  - Sentiment & event stability"
echo "  💰 outputs/valuation_2025q3.csv       - EV/EBITDA valuation metrics"
echo "  📋 outputs/coverage_2025q3.csv        - SEC filing coverage"
echo "  💧 outputs/liquidity.csv              - Market liquidity scores"
echo ""
echo "View results:"
echo "  cat outputs/irci_composite_2025q3.csv"
echo ""
echo "Or use column to format nicely:"
echo "  cat outputs/irci_composite_2025q3.csv | column -t -s,"
echo ""
