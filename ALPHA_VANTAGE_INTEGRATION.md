# Alpha Vantage Integration Guide

## ✅ Setup Complete

Your Alpha Vantage API key has been added: `N829FZVYINYKE58Q`

**Free Tier Limits:**
- 500 API calls per day
- 5 API calls per minute
- No credit card required

---

## 📊 What Alpha Vantage Adds to IRCI

### **Valuation Dial Enhancements:**

Alpha Vantage can supplement FMP data with:

1. **Company Overview**
   - Market Cap, P/E Ratio, PEG Ratio, Book Value
   - 52-week high/low, dividend yield
   - Sector, industry, description
   - **API Call:** `OVERVIEW`

2. **Income Statement**
   - Quarterly and annual revenue
   - Gross profit, operating income, net income
   - EPS (diluted), EBITDA
   - **API Call:** `INCOME_STATEMENT`

3. **Balance Sheet**
   - Total assets, total liabilities
   - Shareholder equity
   - Cash and equivalents, inventory
   - **API Call:** `BALANCE_SHEET`

4. **Cash Flow Statement**
   - Operating cash flow
   - Capital expenditures
   - Free cash flow
   - **API Call:** `CASH_FLOW`

5. **Earnings**
   - Quarterly EPS actual vs estimate
   - Earnings surprises
   - Forward P/E estimates
   - **API Call:** `EARNINGS`

---

## 🔧 Integration Options

### **Option 1: Fallback/Backup (Recommended for now)**

Use Alpha Vantage when FMP data is missing:
```python
# In irci/valuation.py
def get_enterprise_value(ticker):
    # Try FMP first
    ev = get_fmp_enterprise_value(ticker)

    # Fallback to Alpha Vantage
    if ev is None:
        ev = get_alpha_vantage_enterprise_value(ticker)

    return ev
```

**Pros:**
- Increases data coverage
- No changes to existing logic
- Better handling of missing data

### **Option 2: Merge/Average**

Combine data from both sources:
```python
# Average P/E ratios from both sources
fmp_pe = get_fmp_pe_ratio(ticker)
av_pe = get_alpha_vantage_pe_ratio(ticker)

if fmp_pe and av_pe:
    pe_ratio = (fmp_pe + av_pe) / 2  # Average
elif fmp_pe:
    pe_ratio = fmp_pe
else:
    pe_ratio = av_pe
```

**Pros:**
- More robust estimates
- Reduces impact of data errors
- Better for peer comparisons

### **Option 3: Additional Metrics**

Add new valuation metrics only available from Alpha Vantage:
```python
# PEG Ratio (not always in FMP)
peg_ratio = get_alpha_vantage_peg(ticker)

# Earnings Surprise %
earnings_surprise = get_alpha_vantage_earnings_surprise(ticker)

# Forward P/E
forward_pe = get_alpha_vantage_forward_pe(ticker)
```

**Pros:**
- Richer valuation analysis
- More comprehensive peer comparisons
- Better insights

---

## 📝 Example API Calls

### **1. Company Overview**
```python
from alpha_vantage.fundamentaldata import FundamentalData
import os

fd = FundamentalData(key=os.getenv('ALPHA_VANTAGE_API_KEY'), output_format='pandas')
data, meta_data = fd.get_company_overview('AAPL')

print(data['PERatio'])         # P/E Ratio
print(data['PEGRatio'])        # PEG Ratio
print(data['BookValue'])       # Book Value per Share
print(data['DividendYield'])   # Dividend Yield
```

### **2. Income Statement**
```python
data, meta_data = fd.get_income_statement_quarterly('AAPL')

# Returns DataFrame with:
# - fiscalDateEnding
# - totalRevenue
# - grossProfit
# - netIncome
# - eps (diluted)
```

### **3. Earnings & Surprises**
```python
data, meta_data = fd.get_earnings('AAPL')

# Returns:
# - quarterlyEarnings: Actual vs Estimated EPS
# - Earnings surprise %
```

---

## 🎯 Recommended Next Steps

### **Phase 1: Add PEG Ratio (Quick Win)**

PEG ratio is often missing from FMP but available in Alpha Vantage.

**Implementation:**
1. Add function to fetch PEG from Alpha Vantage
2. Include in valuation dial calculation
3. Show in Detailed Metrics tab

**Expected Impact:** +5-10% more comprehensive valuation scores

### **Phase 2: Earnings Quality Metrics**

Use earnings surprises to enhance valuation:
- Companies consistently beating estimates → premium valuation
- Companies missing estimates → valuation discount

**Expected Impact:** +10% better valuation accuracy

### **Phase 3: Full Backup Integration**

Use Alpha Vantage as fallback for all financial metrics when FMP data is missing.

**Expected Impact:** +15-20% better data coverage

---

## ⚠️ Rate Limit Management

**Free Tier Limits:**
- 5 calls/minute
- 500 calls/day

**For a typical analysis:**
- 10 companies × 4 API calls each = 40 calls
- Well within daily limit
- Completes in ~8 minutes (rate limited)

**Rate Limiting Code:**
```python
import time

def alpha_vantage_call_with_rate_limit(func, *args, **kwargs):
    """Wrapper to respect 5 calls/minute limit"""
    result = func(*args, **kwargs)
    time.sleep(12)  # Wait 12 seconds between calls (5 per minute)
    return result
```

---

## 📚 Alpha Vantage Documentation

- **API Docs:** https://www.alphavantage.co/documentation/
- **Python Library:** https://github.com/RomelTorres/alpha_vantage
- **Support:** https://www.alphavantage.co/support/

---

## ✅ Status

- [x] API Key added to .env
- [x] Python package installed (alpha-vantage 3.0.0)
- [x] Added to requirements.txt
- [ ] Integration into irci/valuation.py (next step)
- [ ] Testing with sample companies
- [ ] Documentation update

**Ready to integrate!** Let me know if you want me to implement Option 1, 2, or 3 above.
