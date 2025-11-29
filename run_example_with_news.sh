#!/bin/bash
# IRCI Example: Generate Q3 2025 scores WITH sentiment analysis
# This script converts parquet news to CSV and runs the full pipeline

set -e  # Exit on error

echo "========================================="
echo "IRCI Q3 2025 with Sentiment Analysis"
echo "========================================="
echo ""

# Step 1: Convert parquet news files to combined CSV
echo "Step 1: Preparing news data..."
python -c "
import pandas as pd
import sys

dfs = []
for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN']:
    try:
        df = pd.read_parquet(f'data/news/{ticker}.parquet')
        # Ensure ticker column exists
        if 'ticker' not in df.columns or df['ticker'].isna().all():
            df['ticker'] = ticker
        dfs.append(df)
        print(f'  ✓ Loaded {len(df)} articles for {ticker}')
    except FileNotFoundError:
        print(f'  ⚠ No news file for {ticker}')

if dfs:
    combined = pd.concat(dfs, ignore_index=True)
    combined.to_csv('data/news_combined.csv', index=False)
    print(f'\n✓ Created data/news_combined.csv with {len(combined)} total articles')
else:
    print('\n❌ Error: No news data found in data/news/*.parquet')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Failed to prepare news data"
    exit 1
fi

echo ""

# Step 2: Test FinBERT (optional, can comment out for speed)
echo "Step 2: Testing FinBERT sentiment analysis..."
python -c "
from irci.trust import finbert_score

test_texts = [
    'Company reports record quarterly revenue and strong growth',
    'Stock faces regulatory challenges and analyst downgrades'
]

try:
    scores = finbert_score(test_texts)
    if scores:
        print('  ✓ FinBERT is working!')
        for text, score in zip(test_texts, scores):
            sentiment = 'positive' if score > 0 else 'negative'
            print(f'    {sentiment:>8} ({score:+.3f}): {text[:45]}...')
    else:
        print('  ⚠ FinBERT unavailable, will fall back to VADER')
except Exception as e:
    print(f'  ⚠ Sentiment analysis may not work: {e}')
" 2>&1

echo ""

# Step 3: Run IRCI pipeline with news
echo "Step 3: Running IRCI pipeline with sentiment analysis..."
echo "Companies: AAPL, MSFT, GOOGL, AMZN"
echo ""

irci run --symbols "AAPL,MSFT,GOOGL,AMZN" --quarter 2025Q3 \
  --news-csv data/news_combined.csv

echo ""
echo "========================================="
echo "✓ Pipeline Complete!"
echo "========================================="
echo ""
echo "Results saved to outputs/ directory:"
echo ""
echo "  📊 outputs/irci_composite_2025q3.csv  - Final composite scores & rankings"
echo "  📈 outputs/trust.csv                  - Trust scores WITH sentiment"
echo "  💰 outputs/valuation_2025q3.csv       - EV/EBITDA valuation metrics"
echo "  📋 outputs/coverage_2025q3.csv        - SEC filing coverage"
echo "  💧 outputs/liquidity.csv              - Market liquidity scores"
echo ""
echo "Check sentiment analysis results:"
echo "  cat outputs/trust.csv | column -t -s,"
echo ""
echo "Look for these columns in trust.csv:"
echo "  - p_media_tone: Should have values (not NaN)"
echo "  - media_tone_n: Number of articles analyzed"
echo "  - media_tone_src: Either 'ProsusAI/finbert' or 'vader'"
echo ""
