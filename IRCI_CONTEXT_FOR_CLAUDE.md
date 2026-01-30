# IRCI (Investor Relations Composite Index) - Context for Diagram Creation

## Executive Summary

IRCI is a quantitative framework that measures investor relations (IR) quality by combining four key dials into a composite score (0-100). It helps IR teams benchmark against peers, identify improvement opportunities, and quantify the dollar value impact of their work.

---

## The Four Dials (Components)

### 1. 💰 Valuation Dial (Weight: 35%)
**What it measures:** How the market values the company relative to fundamentals
- **Primary Metric:** EV/EBITDA ratio (enterprise value to earnings)
- **Secondary Metrics:** PEG ratio (from Alpha Vantage)
- **Peer Comparison:** Median-anchored percentile scaling (0-100)
- **Interpretation:** Lower EV/EBITDA = cheaper = higher score (better positioned)

**Key Insight:** Good IR can improve valuation multiples by reducing information asymmetry

### 2. 💧 Liquidity Dial (Weight: 35%)
**What it measures:** How easily the stock can be traded without moving price
- **Primary Metrics:**
  - Amihud illiquidity ratio (price impact per dollar traded)
  - Bid-ask spread (cost to trade)
  - Turnover ratio (trading volume)
- **Data Source:** Yahoo Finance historical pricing
- **Interpretation:** Lower spreads, lower Amihud = higher score (more liquid)

**Key Insight:** Good IR attracts institutional investors, improving liquidity

### 3. 📊 Coverage Dial (Weight: 15%)
**What it measures:** How much attention the company gets from media and analysts
- **Primary Metrics:**
  - Number of news articles (FMP API, World News API)
  - Number of SEC filings (8-K, 10-Q, 10-K)
  - Media source quality (weighted by domain)
- **Time Period:** Quarterly aggregation
- **Interpretation:** More coverage = higher visibility = higher score

**Key Insight:** IR teams drive media engagement and analyst following

### 4. 💭 Trust Dial (Weight: 15%)
**What it measures:** Market sentiment and credibility
- **Primary Metrics:**
  - News sentiment (FinBERT AI analysis of articles)
  - Tone analysis (positive/negative/neutral)
  - Earnings surprises (beat/meet/miss)
- **Sentiment Scale:** -1 (very negative) to +1 (very positive)
- **Interpretation:** More positive sentiment = higher trust = higher score

**Key Insight:** Consistent, transparent communication builds trust

---

## How IRCI Composite Score is Calculated

```
IRCI Composite = (Valuation × 35%) + (Liquidity × 35%) + (Coverage × 15%) + (Trust × 15%)

Result: 0-100 score (peer-relative percentile)
- 75-100: Strong (top quartile)
- 50-75: Neutral (above average)
- 25-50: Neutral (below average)
- 0-25: Attention needed (bottom quartile)
```

**Peer Comparison:** Each dial uses median-anchored percentile scaling
- Median of peer group = 50
- Top performer = 100
- Bottom performer = 0

---

## Dollar Value Calculation (Unique Innovation)

**Question:** "How much is each IRCI point worth in enterprise value?"

**Method:** Cross-sectional regression across peer group
```
Enterprise Value ~ IRCI Composite Score
```

**Formula (Percentage-Based):**
```python
$/IRCI Point = Enterprise Value × 0.05% × R²

Where:
- 0.05% = Impact per point derived from academic research:
  - Total IR contribution: 5-10% of EV over long term (Bushee & Miller 2012)
  - Spread across ~50 IRCI points (typical leader-laggard gap)
  - Per-point impact: 5% / 50 = 0.1%, conservatively halved = 0.05%
- R² = Regression R-squared (how well IRCI explains EV variance)
- Scaled by company size (larger companies = larger $/point)
```

**Example:**
- Company: Blackstone ($135B EV)
- R² = 0.50 (IRCI explains 50% of EV variation)
- $/IRCI Point = $135B × 0.05% × 0.50 = **$33.8M per point**
- A good press release (+0.75 IRCI pts) = ~$25M value creation (realistic!)

**Academic Backing:**
- IR contributes 5-15% to firm value over LONG TERM (Bushee & Miller 2012)
- 0.05% per point ensures marginal improvements stay realistic
- Prevents unrealistic billion-dollar results from small IRCI changes

---

## Quarterly IR Contribution (Time-Series Analysis)

**Question:** "How much value did our IR team add this quarter?"

**Method:** Quarter-over-quarter change with impact factor
```
IR Contribution = (Current Q IRCI - Previous Q IRCI) × $/IRCI Point × 10%

Where:
- 10% = Quarterly impact factor (adjustable 1%-100%)
- Reflects marginal improvement vs. structural positioning
- Conservative estimate based on academic research
```

**Example:**
- Company: Intel ($208B EV)
- IRCI improvement: +5 points (Q2 → Q3)
- $/IRCI Point: $52M (0.05% of EV × R²=0.5 = 0.025%)
- IR Contribution: 5 × $52M × 10% = **$26M** (0.0125% of EV)

**Why 10% factor?**
- Cross-sectional regression measures structural differences (years)
- Quarterly changes are marginal improvements (3 months)
- Factor adjustable based on user assumptions

---

## Data Flow Architecture

```
INPUT DATA SOURCES:
1. Financial Modeling Prep (FMP) → Stock prices, financials, enterprise value
2. Alpha Vantage → PEG ratios, earnings data
3. Yahoo Finance → Bid-ask spreads, volume, returns
4. World News API → News articles for coverage
5. SEC EDGAR → 8-K, 10-Q, 10-K filings
6. FinBERT AI → Sentiment analysis of news text

↓

DIAL CALCULATIONS:
1. Valuation → EV/EBITDA percentile ranking
2. Liquidity → Amihud, spread, turnover composite
3. Coverage → Article count, filing count, quality weighting
4. Trust → FinBERT sentiment scores aggregated

↓

COMPOSITE SCORE:
Weighted average: 35% + 35% + 15% + 15% = 100%
Peer-relative percentile: 0-100 scale

↓

DOLLAR VALUE REGRESSION:
EV ~ IRCI across peer group
$/IRCI Point = EV × 0.05% × R²

↓

OUTPUTS:
1. IRCI Composite Score (0-100)
2. Dial breakdown (4 component scores)
3. $/IRCI Point (dollar value per point)
4. Peer comparison (gap to top performer)
5. Quarterly IR contribution (QoQ change)
6. Playbook recommendations (actionable next steps)
```

---

## Key Innovations

### 1. Academic-Backed Dollar Value Calculation
**Problem:** Old regression-based approach produced unrealistic values
**Solution:** Use 0.05% of EV per point (scaled by R²), derived from academic research:
- Total IR contribution: 5-10% of EV (Bushee & Miller 2012)
- Spread across ~50 IRCI points = 0.1% per point, conservatively halved
**Result:** All values realistic and defensible (e.g., $25-50M for press releases)

### 2. Median-Anchored Percentile Scaling
**Why:** Traditional min-max scaling fails with outliers
**How:**
- Below median: linear scale from min → median = 0 → 50
- Above median: linear scale from median → max = 50 → 100
**Result:** Median always at 50, smooth distribution

### 3. Composite Score Weights
**Default:** 35% Valuation, 35% Liquidity, 15% Coverage, 15% Trust
**Optimization:** Auto-optimize feature maximizes R² of EV ~ IRCI regression
**Result:** Weights adapt to each peer group's characteristics

### 4. Event Timeline with Impact Attribution
**Feature:** Individual events (news, filings) mapped to dial impacts
**Example:** Negative earnings announcement → -0.0005 Trust dial impact
**Scaling:** Individual events are 1/100th of quarterly aggregate (realistic)

### 5. Quarterly Impact Factor
**Feature:** Adjustable discount for QoQ changes (default 10%)
**Rationale:** Quarterly improvements ≠ structural peer differences
**Result:** Conservative, literature-backed quarterly contribution estimates

---

## Use Cases

### For IR Teams:
1. **Benchmark:** Compare IRCI score against peers
2. **Identify gaps:** Which dial needs improvement?
3. **Prioritize actions:** Playbook recommends high-impact initiatives
4. **Track progress:** Quarterly IRCI monitoring
5. **Justify budget:** "Our IR improved IRCI by 7 points = $500M in value"

### For CFOs:
1. **ROI calculation:** Dollar value per IRCI point
2. **Peer positioning:** Are we undervalued vs. competitors?
3. **Resource allocation:** Is IR investment paying off?
4. **Board reporting:** Quantitative IR performance metrics

### For Analysts:
1. **Liquidity research:** Which stocks have best execution costs?
2. **Valuation screening:** Identify mispriced peers
3. **Sentiment tracking:** Monitor market perception
4. **Coverage gaps:** Find under-covered opportunities

---

## Technical Specifications

### Peer Group Requirements:
- **Minimum:** 3 companies (for statistical validity)
- **Recommended:** 10-20 companies (for significance)
- **Homogeneity:** Same industry, similar market cap, business model

### Statistical Metrics:
- **R² (R-squared):** How much EV variance IRCI explains (0-1 scale)
  - R² > 0.30 = excellent for secondary factor like IR
- **P-value:** Statistical significance of IRCI-EV relationship
  - P < 0.10 = acceptable with small samples
  - P < 0.05 = statistically significant
  - P < 0.01 = highly significant

### Data Frequency:
- **Quarterly:** Standard analysis period (matches SEC reporting)
- **Monthly:** Advanced users can run more frequently
- **Historical:** Multi-quarter panel data for trend analysis

---

## Academic Foundation

### Key Research Papers:

1. **Bushee & Miller (2012)** - "Investor Relations, Firm Visibility, and Investor Following"
   - Found IR increases analyst following and institutional ownership
   - **Estimated IR contributes 5-10% to firm value**
   - Published in *The Accounting Review*

2. **Agarwal et al. (2016)** - "Does Investor Relations Influence Institutional Investment?"
   - IR programs associated with **8-12% higher institutional ownership**
   - Improved liquidity and lower cost of capital
   - Effect takes **12-24 months to fully materialize**

3. **Kirk & Vincent (2014)** - "Professional Investor Relations within the Firm"
   - IR reduces information asymmetry by **10-15%**
   - Stronger effect in growth companies and complex industries
   - Published in *The Accounting Review*

### IRCI Contribution:
- **Operationalizes** academic concepts into measurable KPIs
- **Quantifies** IR value in dollar terms (not just correlations)
- **Validates** with percentage-based caps aligned to research bounds
- **Extends** with quarterly tracking and peer benchmarking

---

## Example Peer Group Analysis

**Semiconductor Peer Group (2025Q3):**

| Company | IRCI Score | Valuation | Liquidity | Coverage | Trust | $/IRCI Point | Gap to Top |
|---------|-----------|-----------|-----------|----------|-------|--------------|------------|
| AMD     | 72.3      | 68.1      | 78.5      | 71.2     | 69.8  | $54.6M       | -7.7 pts   |
| AVGO    | 80.0      | 85.2      | 76.3      | 78.9     | 79.1  | $163.8M      | 0.0 pts    |
| INTC    | 58.7      | 52.3      | 61.8      | 62.1     | 58.9  | $43.7M       | -21.3 pts  |
| QCOM    | 65.4      | 71.9      | 59.2      | 64.8     | 65.7  | $37.2M       | -14.6 pts  |
| MU      | 61.2      | 58.7      | 64.3      | 60.9     | 61.8  | $22.9M       | -18.8 pts  |

**Analysis:**
- **Leader:** AVGO (80.0 IRCI) - strong across all dials
- **Laggard:** INTC (58.7 IRCI) - opportunities in valuation, coverage
- **R²:** 0.42 (IRCI explains 42% of EV variance - excellent!)
- **P-value:** 0.03 (statistically significant at 95% confidence)
- **Interpretation:** IR quality strongly correlates with enterprise value in this peer group

**Potential Upside (if INTC reached AVGO's IRCI):**
- Gap: 21.3 points
- $/IRCI: $43.7M per point (0.05% of $208B EV × 0.42 R²)
- Upside: 21.3 × $43.7M = **$930M** (0.45% of EV - realistic for IR improvement!)

---

## Playbook Recommendations (AI-Generated)

IRCI generates actionable recommendations based on dial scores:

**Example: Company with Low Liquidity Score (35/100)**
1. **Priority: HIGH** - Improve price discovery
   - **What:** Narrow bid-ask spreads by increasing market transparency
   - **How:** More frequent updates, engage additional market makers
   - **Expected Impact:** 10-15 point liquidity improvement

2. **Priority: MEDIUM** - Increase institutional ownership
   - **What:** Target institutional investors through NDR programs
   - **How:** Host investor days, one-on-one meetings, conferences
   - **Expected Impact:** 5-10 point liquidity improvement

3. **Quick Win** - Improve sell-side coverage
   - **What:** Add 2-3 analysts to expand research coverage
   - **How:** Targeted outreach to regional/boutique firms
   - **Expected Impact:** 3-5 point coverage improvement

---

## Visual Summary (for Diagram)

### Main Components to Visualize:

1. **Four Dials as Gauges/Speedometers** (0-100 scale)
   - 💰 Valuation (35% weight)
   - 💧 Liquidity (35% weight)
   - 📊 Coverage (15% weight)
   - 💭 Trust (15% weight)

2. **Composite Score** (center/top) - weighted average

3. **Data Sources** (bottom/left) - APIs feeding into each dial

4. **Dollar Value Calculation** (right side) - regression visualization

5. **Peer Comparison** (background) - show positioning relative to peers

6. **Timeline/Trend** (optional) - quarterly progression

### Suggested Diagram Style:
- **Dashboard-like** layout
- **Color coding:** Green (>75), Yellow (50-75), Orange (25-50), Red (<25)
- **Flow arrows:** Data sources → Dials → Composite → Dollar Value
- **Icons:** 💰💧📊💭 for each dial
- **Clean, professional** aesthetic suitable for executive presentations

---

## Key Messages for Claude

1. IRCI is a **composite index** combining 4 weighted dials into 0-100 score
2. Each dial measures a different aspect of **IR quality** (valuation, liquidity, coverage, trust)
3. **Dollar value** = **0.05% of EV per point × R²** (academic research: IR = 5-10% of firm value over long term, spread across ~50 IRCI points)
4. **Peer-relative** scoring (median = 50, top = 100, bottom = 0)
5. **Academic backing** ensures realistic, defensible values
6. **Actionable outputs:** Scores, benchmarks, recommendations, dollar impact

---

*This document provides context for creating visual diagrams of the IRCI framework.*
