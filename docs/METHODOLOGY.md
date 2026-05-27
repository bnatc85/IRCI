# IRCI Methodology & Calculations

A comprehensive reference of all mathematical formulas, scoring algorithms, and methodologies used in the IRCI (Investor Relations Contribution Index) system.

---

## Table of Contents

1. [Composite Score](#1-composite-score)
2. [Percentile Ranking](#2-percentile-ranking)
3. [Valuation Dial](#3-valuation-dial)
4. [Liquidity Dial](#4-liquidity-dial)
5. [Coverage Dial](#5-coverage-dial)
6. [Trust/Sentiment Dial](#6-trustsentiment-dial)
7. [Weight Optimization](#7-weight-optimization)
8. [Dollar Value Impact](#8-dollar-value-impact)
9. [Yahoo Finance Metrics](#9-yahoo-finance-metrics)
10. [Quick Reference Table](#10-quick-reference-table)

---

## 1. Composite Score

**Location:** `irci/composite.py`

The IRCI Composite Score is a weighted average of four dial percentiles:

```
IRCI = Σ(dial_pct × weight) / Σ(available_weights)
```

### Default Weights

| Dial | Weight | Rationale |
|------|--------|-----------|
| Valuation | 35% | Market perception of value |
| Liquidity | 35% | Trading accessibility |
| Coverage | 15% | Media visibility |
| Trust | 15% | Sentiment & credibility |

### Handling Missing Data

Row-by-row renormalization when dials are unavailable:

```python
mask = X.notna().astype(float).values
num = (X.fillna(0.0).values * W).sum(axis=1)
den = (mask * W).sum(axis=1)
result = np.where(den > 0, num / den, np.nan)
```

---

## 2. Percentile Ranking

**Location:** `irci/valuation.py`

### Median-Anchored Percentile Scaling

```python
if x <= median:
    pct = (x - min) / (median - min) × 50
else:
    pct = 50 + (x - median) / (max - median) × 50
```

### Peer Group Size Compression

To prevent extreme scores in small peer groups:

| Peer Count | Range Compression |
|------------|-------------------|
| 1 peer | Return 50% (neutral) |
| 2 peers | [0,100] → [30,70] |
| 3-5 peers | [0,100] → [15,85] |
| 6+ peers | Full [0,100] range |

### Directional Inversion

For metrics where lower is better (e.g., P/E ratio):
```python
return 100.0 - pct if lower_is_better else pct
```

---

## 3. Valuation Dial

**Location:** `irci/valuation.py`

### Components

#### EV/EBITDA Percentile (70% weight)
```
Enterprise Value = MarketCap + TotalDebt - Cash
EV/EBITDA = Enterprise Value / EBITDA
Percentile = median_anchored_pct(ratio, lower_is_better=True)
```

#### PEG Ratio Percentile (30% weight)
```
PEG = P/E Ratio / Earnings Growth Rate
Percentile = median_anchored_pct(ratio, lower_is_better=True)
```

#### Blended Score
```python
if PEG available:
    valuation_pct = 0.70 × ev_ebitda_pct + 0.30 × peg_pct
else:
    valuation_pct = ev_ebitda_pct
```

### Valuation Gap
```
valuation_gap_pct = (company_ev_to_ebitda - peer_mean) / peer_mean × 100
```

---

## 4. Liquidity Dial

**Location:** `irci/liquidity.py`

### Component Metrics

#### Amihud Illiquidity (35% weight)
```
Amihud = |daily_return| / dollar_volume
```
- Lower = more liquid (better)
- Normalized per $1M: `amihud_e6 = amihud × 1,000,000`

#### Roll Spread Proxy (25% weight)
```python
cov = log(price).diff().rolling(20).cov(shift(1))
spread = 2.0 × sqrt(max(-cov, 0))
```
- Only defined when covariance < 0
- Measured in basis points: `spread_bps = spread × 10,000`

#### Daily Turnover (25% weight)
```
turnover = dollar_volume / market_cap
```
- Higher = more liquid

#### Institutional Ownership Score (15% weight)
- From Yahoo Finance or SEC 13F filings
- Higher ownership = more institutional interest

### Quarterly Aggregation
```python
amihud_q = amihud_daily.resample("QE").median()
turnover_q = turnover_daily.resample("QE").mean()
spread_q = spread_daily.resample("QE").median()
```

### Percentile Calculation
```python
p_amihud = rank(ascending=False)  # lower → higher %
p_spread = rank(ascending=False)  # lower → higher %
p_turnover = rank(ascending=True) # higher → higher %

liquidity_pct = weighted_average([p_amihud, p_spread, p_turnover, p_inst],
                                  weights=[0.35, 0.25, 0.25, 0.15])
```

---

## 5. Coverage Dial

**Location:** `irci/coverage.py`

### Component Metrics

#### 8-K Filing Count
```
p_8k = percentile_rank(count, higher_is_better=True)
```
- More SEC event disclosures = better coverage

#### Filing Timeliness
```
p_timeliness = percentile_rank(days_to_10q, higher_is_better=False)
```
- Fewer days from quarter-end to filing = better

#### Media Visibility
```python
weighted_articles = Σ(domain_weight[article.domain] for each unique article)
p_media = percentile_rank(weighted_articles, higher_is_better=True)
```

Domain weights range from 0.25 to 1.0:
- WSJ, Bloomberg, Reuters: 1.0
- Seeking Alpha: 0.6
- PR Newswire: 0.4

#### Transcript Quality
```
p_transcript = percentile_rank(transcript_score, higher_is_better=True)
```
- Based on forward-looking statements, guidance, Q&A coverage

### Coverage Score Calculation

**With Media Data:**
```python
w_media = 0.40
w_transcript = 0.15
remainder = 1.0 - w_media - w_transcript  # 0.45

w_8k = 0.60 × remainder      # 0.27
w_timeliness = 0.40 × remainder  # 0.18

coverage_pct = (w_8k × p_8k +
                w_timeliness × p_timeliness +
                w_media × p_media +
                w_transcript × p_transcript)
```

---

## 6. Trust/Sentiment Dial

**Location:** `irci/trust.py`

### Component Metrics

#### Event Calmness (40% weight)
```python
# For each SEC filing event:
event_volatility = Σ|residual_returns| over ±3 trading days

event_calm_raw = -median(event_volatilities)
```
- Uses Fama-French 5-factor residuals (preferred)
- Falls back to CAPM residuals or raw returns

#### Baseline Calmness (15% weight)
```python
baseline_calm_raw = -std(quarterly_residual_returns)
```
- Lower quarterly volatility = calmer stock

#### Media Tone (30% weight)

**FinBERT Scoring:**
```python
scores = finbert_model(article_texts)  # Returns P(positive) - P(negative)
raw_tone = mean(scores)
media_tone_raw = clip(raw_tone × 0.6, -0.5, 0.5)
```

**Reliability Shrinkage:**
```python
k = 4.0  # shrinkage constant
shrink = n_articles / (n_articles + k)
media_tone_raw = media_tone_raw × shrink
```
- Shrinks toward neutral with fewer articles

#### Social Sentiment (15% weight)

**Reddit/WSB Sentiment:**
```python
if rank_change > 5:     score = 0.6
elif rank_change > 0:   score = 0.3
elif rank_change < -5:  score = -0.4
elif rank_change < 0:   score = -0.2
else:                   score = 0.0

# Activity multiplier
if activity > 200:  score *= 1.3
elif activity > 50: score *= 1.1
elif activity < 10: score *= 0.7
```

**StockTwits Sentiment:**
```python
sentiment = (bullish_count - bearish_count) / total_messages
```

### Trust Score Calculation
```python
p_event = median_anchored_pct(event_calm_raw)
p_baseline = median_anchored_pct(baseline_calm_raw)
p_tone = median_anchored_pct(media_tone_raw)
p_social = median_anchored_pct(social_sentiment_raw)

trust_pct = weighted_average([p_event, p_baseline, p_tone, p_social],
                              weights=[0.40, 0.15, 0.30, 0.15])
```

---

## 7. Weight Optimization

**Location:** `irci/dial_insights.py`, `out/comm/tune_weights_per_ticker.py`

### R² Score Calculation
```python
ss_res = Σ(y - ŷ)²
ss_tot = Σ(y - ȳ)²
R² = 1.0 - (ss_res / ss_tot)
```

### Ridge-Regularized NNLS (Non-Negative Least Squares)

**Objective:**
```
minimize: ||Xw - y||² + λ||w||²
subject to: w ≥ 0, Σw = 1
```

**Parameters:**
- λ (ridge penalty): 0.05
- Learning rate: 0.001
- Max iterations: 2,500

### Variance-Based Initial Weights
```python
variances = dial_scores.var()
availability = dial_scores.notna().mean()
discriminating_power = variances × availability

initial_weights = discriminating_power / sum(discriminating_power)
```

### Cross-Validation
```python
# 3-fold rolling cross-validation
for k in range(3):
    train = data[:fold_k]
    test = data[fold_k:fold_k+1]
    w = fit(train)
    R²_k = score(test, w)

R²_cv = mean(R²_k)
```

---

## 8. Dollar Value Impact

**Location:** `irci/dial_insights.py`

### Raw $/IRCI Point from Peer Spread
```python
irci_range = max(peer_irci) - min(peer_irci)
ev_range = max(peer_ev) - min(peer_ev)

dollars_per_point_raw = ev_range / irci_range
```

### R²-Adjusted $/IRCI Point
```python
r² = regression_r_squared(irci_pct, enterprise_value)
r²_floor = max(r², 0.10)  # 10% minimum

dollars_per_point = dollars_per_point_raw × r²_floor
```

### Company-Specific Calculation (Academic Research Basis)
```python
# Based on Bushee & Miller (2012): IR contributes 5-10% to firm value over long term
# Spread across ~50 IRCI points (typical leader-laggard gap)
# Per-point impact: 5% / 50 = 0.1%, conservatively halved = 0.05%
MAX_PERCENT_PER_POINT = 0.0005  # 0.05% of EV per IRCI point

company_dollars_per_point = enterprise_value × MAX_PERCENT_PER_POINT × r²_floor
```

### Dollar Upside Gap
```python
irci_gap = top_performer_irci - company_irci
uncapped_upside = irci_gap × company_dollars_per_point

MAX_TOTAL_UPSIDE = enterprise_value × 0.20  # 20% cap
market_cap_gap = min(uncapped_upside, MAX_TOTAL_UPSIDE)
```

---

## 9. Yahoo Finance Metrics

**Location:** `irci/yahoo_metrics.py`

### Analyst Coverage Score (0-100)
```python
if analyst_count == 0:
    score = 0
elif analyst_count <= 5:
    score = analyst_count × 6           # 0-30
elif analyst_count <= 15:
    score = 30 + (analyst_count - 5) × 3    # 30-60
elif analyst_count <= 30:
    score = 60 + (analyst_count - 15) × 1.67  # 60-85
else:
    score = min(100, 85 + (analyst_count - 30) × 0.5)  # 85-100
```

### Short Interest Score (0-100)
Lower short interest = higher trust score:

```python
if short_pct < 2:
    score = 90 + (2 - short_pct) × 5      # 90-100
elif short_pct < 5:
    score = 90 - (short_pct - 2) × 6.67   # 70-90
elif short_pct < 10:
    score = 70 - (short_pct - 5) × 4      # 50-70
elif short_pct < 20:
    score = 50 - (short_pct - 10) × 2     # 30-50
else:
    score = max(0, 30 - (short_pct - 20) × 1.5)  # 0-30
```

### Recommendation Score (0-100)
```python
# recommendation_mean: 1.0 = Strong Buy, 5.0 = Sell
score = (5 - recommendation_mean) / 4 × 100

# Converts: 1→100, 2→75, 3→50, 4→25, 5→0
```

### Price Target Upside
```python
upside_pct = (mean_target - current_price) / current_price × 100
```

---

## 10. Quick Reference Table

| Component | Formula | Range | Direction |
|-----------|---------|-------|-----------|
| **IRCI Composite** | Σ(dial×w)/Σ(w) | 0-100 | Higher=Better |
| **Valuation %** | 0.7×EV_pct + 0.3×PEG_pct | 0-100 | Higher=Better |
| **EV/EBITDA %** | median_anchored_pct(ratio) | 0-100 | Lower ratio=Higher % |
| **Liquidity %** | weighted_rank(amihud, spread, turnover) | 0-100 | Higher=Better |
| **Amihud** | \|return\|/volume | 0-∞ | Lower=Better |
| **Roll Spread** | 2√(max(-cov,0)) | 0-1 | Lower=Better |
| **Coverage %** | weighted(8K, timeliness, media, transcript) | 0-100 | Higher=Better |
| **Trust %** | weighted(calmness, tone, social) | 0-100 | Higher=Better |
| **Event Calmness** | -median(\|residuals\|) | -∞ to 0 | Less negative=Better |
| **Media Tone** | finbert_score × 0.6 × shrink | -0.5 to 0.5 | Positive=Better |
| **R²** | 1 - SSres/SStot | 0-1 | Higher=Better fit |
| **$/IRCI Point** | EV × 0.05% × r² | $ | — |
| **Analyst Score** | tiered(count) | 0-100 | More analysts=Higher |
| **Short Score** | inverse_tiered(short_pct) | 0-100 | Lower short%=Higher |

---

## Data Sources

| Data | Primary Source | Fallback |
|------|----------------|----------|
| Price/Volume | Yahoo Finance | — |
| Enterprise Value | FMP API | SEC filings |
| EBITDA | SEC XBRL | FMP API |
| Institutional Ownership | SEC 13F | Yahoo Finance |
| News/Media | WorldNews API | NewsAPI |
| SEC Filings | SEC EDGAR | — |
| Sentiment | FinBERT | VADER |
| Social | ApeWisdom | StockTwits |
| Analyst Coverage | Yahoo Finance | — |

---

## Notes

1. **Peer Group Context**: All percentile scores are relative to the selected peer group
2. **Missing Data**: System gracefully handles missing data through weight renormalization
3. **R² Scaling**: Dollar impacts are conservatively scaled by model fit quality
4. **Shrinkage**: Sentiment scores shrink toward neutral with small sample sizes
5. **Compression**: Small peer groups use compressed score ranges to avoid extremes

---

*Generated from IRCI codebase analysis - November 2024*
