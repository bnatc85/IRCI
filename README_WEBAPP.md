# 🌐 IRCI Web Application - Quick Start

## Launch in 10 Seconds

```bash
./run_webapp.sh
```

Then open: **http://localhost:8501**

---

## What You Get

### ✨ **User-Friendly Interface**
- No coding required
- Point-and-click analysis
- Real-time results
- Interactive visualizations

### 📊 **Features**
- Select companies via ticker symbols
- Choose analysis quarter
- Upload news for sentiment analysis
- Customize composite weights
- Download all results to CSV

### 🎨 **Visualizations**
- Bar charts (composite rankings)
- Radar charts (dial breakdowns)
- Data tables (detailed metrics)
- Export-ready reports

---

## Screenshot Preview

```
┌─────────────────────────────────────────────────────────┐
│  IRCI Analysis Platform                    [Settings ▼]│
│                                                         │
│  Information Risk, Coverage, Trust, Liquidity Analysis  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  COMPANIES:         QUARTER:                            │
│  AAPL,MSFT,GOOGL   [2025Q3 ▼]                          │
│  AMZN                                                   │
│                                                         │
│  NEWS DATA (optional):                                  │
│  [📎 Upload CSV...]                                     │
│                                                         │
│  [🚀 Run Analysis]                                      │
├─────────────────────────────────────────────────────────┤
│  📊 COMPOSITE RANKING                                   │
│  ┌───┬────────┬───────────┬──────────┬──────────┐      │
│  │ # │ Ticker │ Composite │ Valuation│ Liquidity│      │
│  ├───┼────────┼───────────┼──────────┼──────────┤      │
│  │ 1 │ AAPL   │   82.6%   │  100.0%  │   83%    │      │
│  │ 2 │ MSFT   │   54.3%   │   52.6%  │   50%    │      │
│  │ 3 │ AMZN   │   45.9%   │    0.0%  │   75%    │      │
│  │ 4 │ GOOGL  │   44.1%   │   49.6%  │   42%    │      │
│  └───┴────────┴───────────┴──────────┴──────────┘      │
│                                                         │
│  [📈 Composite Scores] [🕸️ Dial Breakdown] [📋 Details]│
│                                                         │
│  💾 Download: [Composite] [Valuation] [Liquidity] ...  │
└─────────────────────────────────────────────────────────┘
```

---

## For Your Team

### **Analysts**
- Run analyses without coding
- Explore interactive charts
- Export to Excel/CSV

### **Researchers**
- Compare multiple companies
- Test different weight configurations
- Download raw data

### **Executives**
- View high-level rankings
- Understand dial breakdowns
- Share results easily

---

## Deployment Options

| Option | Effort | Best For |
|--------|--------|----------|
| **Local** | ⚡ 10 seconds | Personal use |
| **Streamlit Cloud** | 🌥️ 5 minutes | Team sharing (free) |
| **Docker** | 🐳 15 minutes | IT-managed |
| **AWS/Azure/GCP** | ☁️ 30 minutes | Production |

See `WEB_APP_GUIDE.md` for detailed deployment instructions.

---

## Requirements

- Python 3.10+
- Streamlit 1.51+
- Plotly 6.5+
- IRCI package

All automatically installed by `./run_webapp.sh`

---

## Files Created

```
app.py                   # Main Streamlit application
run_webapp.sh           # Launch script (./run_webapp.sh)
requirements-webapp.txt # Web app dependencies
WEB_APP_GUIDE.md        # Full documentation
```

---

## Quick Test

```bash
# 1. Launch app
./run_webapp.sh

# 2. In your browser:
#    - Enter: AAPL, MSFT, GOOGL, AMZN
#    - Select: 2025Q3
#    - Click: Run Analysis

# 3. View results in ~30 seconds

# 4. Download CSVs for further analysis
```

---

## Next Steps

1. ✅ **Test locally**: `./run_webapp.sh`
2. 📚 **Read full guide**: `WEB_APP_GUIDE.md`
3. 🚀 **Deploy for team**: Choose deployment option
4. 👥 **Train users**: 5-minute demo session

---

**🎉 You now have a professional web interface for IRCI!**

For questions, see `WEB_APP_GUIDE.md` or contact your team lead.
