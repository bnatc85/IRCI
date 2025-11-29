# Sentiment Analysis & Media Pulling - Current Status

## Summary

**Short answer:** The sentiment analysis and media pulling code is **well-implemented but not currently being used** in your pipeline runs. Here's what's happening:

## What the Code Does (Architecture)

### ✅ **Correctly Implemented Components**

#### 1. **Media Fetcher (github_csv.py)**
- Loads news from `data/news/{TICKER}.csv` files
- Supports fields: `published_at`, `url`, `domain`, `lang`, `headline`, `title`
- Filters by ticker and date range
- **Status:** ✅ Code is correct

#### 2. **Sentiment Analysis (trust.py + finbert_sentiment.py)**
The code has **two sentiment engines** with fallback:

**Primary: FinBERT** (`ProsusAI/finbert`)
- Financial news sentiment model
- Returns scores from -1 (negative) to +1 (positive)
- Uses Hugging Face transformers
- Clips scores to ±0.5 with 60% shrinkage for reliability

**Fallback: VADER Sentiment**
- General-purpose sentiment analyzer
- Used if FinBERT is unavailable
- Clips scores to ±0.3 with 40% shrinkage

**Status:** ✅ Code is correct and robust

#### 3. **Trust Dial Composition**
Trust score = weighted average of:
- **Event Calmness** (50%): How calm markets are around SEC filings
- **Baseline Calmness** (50%): Overall volatility using Fama-French factors
- **Media Tone** (0%): Sentiment from news headlines

**Status:** ✅ Code is correct

---

## ❌ What's Missing in Your Runs

### Issue 1: News Data Not Being Loaded

**Current output shows:**
```
ticker  trust_pct  p_event_calm  p_baseline_calm  p_media_tone  event_count
  AAPL  51.2%      50.0          54.3             NaN           4
```

Notice `p_media_tone` is **NaN** and `media_tone_n=0` (zero articles processed).

**Why?**
1. The `irci run` command does **NOT** pass a `--news-csv` parameter
2. Without `--news-csv`, the trust module receives `news_df=None`
3. The sentiment analysis code is skipped entirely

### Issue 2: News Files Are in Wrong Format

Your news data exists but in the wrong location/format:
```
data/news/AAPL.parquet   ← Current (77 articles)
data/news/MSFT.parquet   ← Current
```

The code expects:
```
data/news/AAPL.csv       ← Expected by github_csv_media_fetcher
```

Or a single consolidated CSV passed via `--news-csv`.

### Issue 3: CLI Doesn't Auto-Load News

The `irci run` command in `cli.py:87-90` shows:
```python
cmd = f'irci trust --symbols "{syms}" --start {start} --end {end} --out-csv {trust_out}'
if news_csv:
    cmd += f" --news-csv {shlex.quote(str(news_csv))}"
_sh(cmd)
```

It only passes `--news-csv` if you provide it to `irci run --news-csv ...`.

---

## 🔧 How to Fix & Enable Sentiment Analysis

### Option 1: Convert Parquet to CSV (Quick Fix)

```bash
python -c "
import pandas as pd
for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN']:
    try:
        df = pd.read_parquet(f'data/news/{ticker}.parquet')
        df.to_csv(f'data/news/{ticker}.csv', index=False)
        print(f'✓ Converted {ticker}.parquet to CSV')
    except FileNotFoundError:
        print(f'⚠ No news data for {ticker}')
"
```

### Option 2: Create Consolidated News CSV

```bash
python -c "
import pandas as pd
dfs = []
for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN']:
    try:
        df = pd.read_parquet(f'data/news/{ticker}.parquet')
        df['ticker'] = ticker
        dfs.append(df)
    except FileNotFoundError:
        pass

if dfs:
    combined = pd.concat(dfs, ignore_index=True)
    combined.to_csv('data/news_combined.csv', index=False)
    print(f'✓ Created news_combined.csv with {len(combined)} articles')
"
```

### Option 3: Run with News CSV

After creating the CSV (Option 1 or 2), run:

```bash
# If using combined CSV:
irci run --symbols "AAPL,MSFT,GOOGL,AMZN" --quarter 2025Q3 \
  --news-csv data/news_combined.csv

# Or for trust dial only:
irci trust --symbols "AAPL,MSFT,GOOGL,AMZN" \
  --start 2025-07-01 --end 2025-09-30 \
  --news-csv data/news_combined.csv \
  --out-csv outputs/trust_with_sentiment.csv
```

---

## 📊 Expected Results After Fix

Once news is properly loaded, you should see:

```
ticker  trust_pct  p_event_calm  p_baseline_calm  p_media_tone  media_tone_n
  AAPL  XX.X%      50.0          54.3             XX.X          77
  MSFT  XX.X%      50.0          100.0            XX.X          XX
```

Where:
- `p_media_tone` will have actual percentile scores (0-100%)
- `media_tone_n` will show number of articles analyzed
- `trust_pct` will be a weighted average including sentiment

---

## 🔍 Verify News Data

Check your current news data:

```bash
python -c "
import pandas as pd
df = pd.read_parquet('data/news/AAPL.parquet')
print(f'AAPL news: {len(df)} articles')
print(f'Date range: {df.published_at.min()} to {df.published_at.max()}')
print(f'Columns: {df.columns.tolist()}')
print(f'\nSample headlines:')
print(df[['published_at', 'headline']].head(3))
"
```

---

## 🧪 Test Sentiment Analysis

Test if FinBERT is working:

```bash
python -c "
from irci.trust import finbert_score

test_texts = [
    'Apple reports record quarterly revenue',
    'Microsoft faces regulatory challenges',
    'Amazon stock plummets on earnings miss'
]

scores = finbert_score(test_texts)
if scores:
    print('✅ FinBERT is working!')
    for text, score in zip(test_texts, scores):
        sentiment = 'positive' if score > 0 else 'negative'
        print(f'{sentiment:>8} ({score:+.3f}): {text[:50]}')
else:
    print('❌ FinBERT is not available')
"
```

---

## 📝 Implementation Details

### News CSV Requirements

Your CSV must have these columns:

**Required:**
- `date` or `published_at`: Timestamp of article
- `ticker`: Stock symbol (e.g., "AAPL")
- `headline` or `title`: Article headline text

**Optional:**
- `url`: Article URL
- `domain`: Source domain (e.g., "wsj.com")
- `lang`: Language code (e.g., "en")

**Example:**
```csv
published_at,ticker,headline,url,domain
2025-07-15 09:30:00+00:00,AAPL,Apple announces new AI features,https://...,bloomberg.com
2025-07-20 14:00:00+00:00,MSFT,Microsoft beats earnings estimates,https://...,wsj.com
```

---

## 🚀 Recommended Next Steps

1. **Convert your parquet files to CSV** (Option 1 above)
2. **Test sentiment analysis** (run the FinBERT test)
3. **Re-run the pipeline with news:**
   ```bash
   ./run_example_with_news.sh  # (see below)
   ```
4. **Compare results** - Trust scores should change when media sentiment is included

---

## 📜 Script: Run with Sentiment

Create `run_example_with_news.sh`:

```bash
#!/bin/bash
set -e

echo "Converting parquet to CSV..."
python -c "
import pandas as pd
dfs = []
for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN']:
    try:
        df = pd.read_parquet(f'data/news/{ticker}.parquet')
        df['ticker'] = ticker
        dfs.append(df)
        print(f'✓ Loaded {len(df)} articles for {ticker}')
    except FileNotFoundError:
        print(f'⚠ No news for {ticker}')

if dfs:
    combined = pd.concat(dfs, ignore_index=True)
    combined.to_csv('data/news_combined.csv', index=False)
    print(f'\n✓ Created news_combined.csv with {len(combined)} articles')
else:
    print('\n❌ No news data found')
    exit(1)
"

echo ""
echo "Running IRCI with sentiment analysis..."
irci run --symbols "AAPL,MSFT,GOOGL,AMZN" --quarter 2025Q3 \
  --news-csv data/news_combined.csv

echo ""
echo "✅ Complete! Check outputs/trust.csv for p_media_tone values"
```

---

## 🔬 Technical Details: How Sentiment Is Used

1. **Headlines are extracted** from news_df for each ticker/quarter
2. **FinBERT scores each headline** from -1 (negative) to +1 (positive)
3. **Raw score = mean(scores)** across all headlines
4. **Adjusted score = clip(raw * 0.6, -0.5, 0.5)** (shrinkage for reliability)
5. **Percentile ranked** across peer group (0-100%)
6. **Blended into Trust** with event calmness & baseline volatility

**Default Weights:**
- Event Calmness: 50%
- Baseline Calmness: 50%
- Media Tone: 0% (only used if provided)

When media tone is available, weights can be adjusted.

---

## ✅ Summary Checklist

- [ ] Convert `.parquet` news to `.csv` format
- [ ] Verify transformers package is installed (`pip list | grep transformers`)
- [ ] Test FinBERT with sample headlines
- [ ] Run pipeline with `--news-csv` parameter
- [ ] Verify `p_media_tone` is no longer NaN
- [ ] Compare Trust scores with/without sentiment

---

**Bottom Line:** Your sentiment analysis code is production-ready and well-designed. It just needs news data in the right format and the `--news-csv` flag to activate it.

**Last Updated:** Nov 18, 2025
