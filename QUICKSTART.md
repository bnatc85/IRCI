# IRCI Quickstart Guide

This guide shows you how to run the IRCI pipeline to generate dials and composite scores for public companies.

## Prerequisites

- Python 3.10+ (this codespace has Python 3.12.1)
- Git (for cloning the repo)

## Setup Instructions

### 1. Clone and Navigate to Repository

```bash
cd /workspaces/IRCI  # Or wherever you cloned the repo
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install the Package in Editable Mode

```bash
pip install -e .
```

This installs the `irci` package and makes the CLI command available.

### 4. Verify Installation

```bash
irci --help
```

You should see the IRCI CLI help menu with commands like `run`, `trust`, `coverage`, `liquidity`, `valuation`, etc.

---

## Running the Full Pipeline

### Basic Usage: Single Command

To generate all 4 dials + composite score for a set of companies in a specific quarter:

```bash
irci run --symbols "AAPL,MSFT,GOOGL,AMZN" --quarter 2025Q3
```

**What this does:**
1. Runs the **Trust** dial (sentiment & event stability)
2. Runs the **Valuation** dial (EV/EBITDA vs peers)
3. Runs the **Coverage** dial (SEC filing cadence & timeliness)
4. Runs the **Liquidity** dial (market microstructure metrics)
5. Combines all 4 into a **Composite** score with peer ranking

### Output Files

All results are saved to `outputs/` directory:

```
outputs/
├── trust.csv                    # Trust/sentiment scores
├── valuation_2025q3.csv         # Valuation metrics
├── coverage_2025q3.csv          # SEC disclosure scores
├── liquidity.csv                # Liquidity scores
└── irci_composite_2025q3.csv    # Final composite ranking
```

---

## Example: Q3 2025 Big Tech Analysis

### Command

```bash
irci run --symbols "AAPL,MSFT,GOOGL,AMZN" --quarter 2025Q3
```

### Expected Results

**Composite Scores (outputs/irci_composite_2025q3.csv):**

| Rank | Ticker | Composite | Valuation | Liquidity | Coverage | Trust |
|------|--------|-----------|-----------|-----------|----------|-------|
| 1    | AAPL   | 82.6%     | 100.0%    | 83%       | 72.5%    | 51.2% |
| 2    | MSFT   | 52.7%     | 52.6%     | 50%       | 47.5%    | 64.3% |
| 3    | AMZN   | 45.9%     | 0.0%      | 75%       | 95.0%    | 35.7% |
| 4    | GOOGL  | 44.1%     | 49.6%     | 42%       | 35.0%    | 45.6% |

---

## Running Individual Dials

You can also run each dial independently:

### Trust (Sentiment & Event Stability)

```bash
irci trust --symbols "AAPL,MSFT,GOOGL,AMZN" \
  --start 2025-07-01 \
  --end 2025-09-30 \
  --out-csv outputs/trust.csv
```

### Valuation (EV/EBITDA)

```bash
irci valuation --symbols "AAPL,MSFT,GOOGL,AMZN" \
  --as-of 2025-09-30 \
  --out-csv outputs/valuation_2025q3.csv
```

### Coverage (SEC Filings)

```bash
irci coverage --symbols "AAPL,MSFT,GOOGL,AMZN" \
  --as-of 2025-09-30 \
  --out-csv outputs/coverage_2025q3.csv
```

### Liquidity (Market Microstructure)

```bash
irci liquidity --symbols "AAPL,MSFT,GOOGL,AMZN" \
  --start 2025-07-01 \
  --end 2025-09-30 \
  --out-csv outputs/liquidity.csv
```

### Composite (Combine All Dials)

```bash
irci composite \
  --valuation outputs/valuation_2025q3.csv \
  --liquidity outputs/liquidity.csv \
  --coverage outputs/coverage_2025q3.csv \
  --sentiment-csv outputs/trust.csv \
  --quarter 2025Q3 \
  --out-csv outputs/irci_composite_2025q3.csv
```

---

## Understanding the Outputs

### Trust Dial (`trust.csv`)
- **trust_pct**: Overall trust score (0-100%)
- **p_event_calm**: Event calmness percentile
- **p_baseline_calm**: Baseline market calmness percentile
- **event_count**: Number of events analyzed

### Valuation Dial (`valuation_2025q3.csv`)
- **valuation_pct**: Valuation score (0-100%, higher = cheaper/better)
- **ev_to_ebitda**: Enterprise Value / EBITDA multiple
- **peer_mean_excl_self**: Average peer multiple
- **valuation_gap_pct**: % difference from peer average
- **valuation_quartile**: strong/neutral/attention

### Coverage Dial (`coverage_2025q3.csv`)
- **coverage_pct**: Coverage score (0-100%)
- **q_8k_count**: Number of 8-K filings in quarter
- **q_days_to_10q**: Days to file 10-Q/10-K

### Liquidity Dial (`liquidity.csv`)
- **liquidity_pct**: Liquidity score (0-100%)
- **q_amihud**: Amihud illiquidity measure (lower is better)
- **q_turnover**: Average daily turnover
- **q_spread_bps**: Roll spread estimate in basis points

### Composite (`irci_composite_2025q3.csv`)
- **irci_composite_pct**: Weighted composite score (0-100%)
- **rank_in_peer**: Ranking within peer group
- Individual dial scores for reference

**Default Weights:**
- Liquidity: 35%
- Valuation: 35%
- Coverage: 15%
- Trust: 15%

---

## Advanced Options

### Using Presets

If you have a preset defined in your config:

```bash
irci run --preset bigtech --quarter 2025Q3
```

### Adding News Data

To include media sentiment (FinBERT):

```bash
irci run --symbols "AAPL,MSFT" --quarter 2025Q3 --news-csv data/news.csv
```

### Custom Output Directory

```bash
irci run --symbols "AAPL,MSFT" --quarter 2025Q3 --out-dir my_results
```

---

## Troubleshooting

### FMP API 403 Errors

The Financial Modeling Prep (FMP) API may return 403 errors due to rate limits or API key issues. The system automatically falls back to:
- **yfinance** for price data
- **SEC EDGAR** for financial data

This is expected behavior and results will still be generated successfully.

### Missing Dependencies

If you see import errors, install missing packages:

```bash
pip install -e .
```

Or install optional dependencies:

```bash
pip install yfinance transformers
```

### Command Not Found

If `irci` command is not found, make sure:
1. Virtual environment is activated: `source .venv/bin/activate`
2. Package is installed: `pip install -e .`
3. Check installation: `which irci`

---

## Data Sources

The IRCI pipeline pulls data from:
- **SEC EDGAR**: Company filings (8-K, 10-Q, 10-K)
- **Financial Modeling Prep (FMP)**: Market data, financials
- **Yahoo Finance**: Fallback price data
- **Kenneth French Data Library**: Fama-French factors
- **News CSV** (optional): For sentiment analysis

---

## Next Steps

1. **Explore other quarters**: Change `--quarter` to 2025Q2, 2025Q1, etc.
2. **Add more companies**: Expand the `--symbols` list
3. **Customize weights**: Use `irci composite` with custom weight parameters
4. **Validate results**: Run `irci validate` to check correlations and IC
5. **Export to Excel**: Use `irci export-bridge` to create dashboard-ready files

---

## Support

- CLI Help: `irci --help` or `irci <command> --help`
- Issues: Check the GitHub issues page
- Documentation: See README.md and README_bridge.md

---

## Quick Reference

| Task | Command |
|------|---------|
| Full pipeline | `irci run --symbols "AAPL,MSFT" --quarter 2025Q3` |
| Trust only | `irci trust --symbols "AAPL" --start 2025-07-01 --end 2025-09-30` |
| Valuation only | `irci valuation --symbols "AAPL" --as-of 2025-09-30` |
| Coverage only | `irci coverage --symbols "AAPL" --as-of 2025-09-30` |
| Liquidity only | `irci liquidity --symbols "AAPL" --start 2025-07-01 --end 2025-09-30` |
| List all commands | `irci --help` |
| Command help | `irci run --help` |

---

**Last Updated**: Nov 18, 2025
**IRCI Version**: 0.1.0
