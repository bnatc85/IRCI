# IRCI Web Application Guide

A user-friendly web interface for running IRCI analysis on public companies.

![IRCI Web App](https://via.placeholder.com/800x400/1f77b4/ffffff?text=IRCI+Web+Application)

---

## 🚀 Quick Start

### **Option 1: One-Command Launch**

```bash
./run_webapp.sh
```

Then open your browser to: **http://localhost:8501**

### **Option 2: Manual Launch**

```bash
# Install dependencies
pip install streamlit plotly

# Launch the app
streamlit run app.py
```

---

## 📋 Features

### **1. Interactive Dashboard**
- Select companies via ticker symbols
- Choose analysis quarter (Q1-Q4)
- Upload optional news data for sentiment analysis
- Customize composite score weights

### **2. Real-Time Analysis**
- Runs all 4 IRCI dials (Coverage, Trust, Liquidity, Valuation)
- Computes composite scores
- Generates peer rankings
- Shows progress indicator

### **3. Rich Visualizations**
- 📊 **Bar charts** - Composite score rankings
- 🕸️ **Radar charts** - Individual company dial breakdowns
- 📈 **Data tables** - Detailed metrics for each dial
- 💾 **Downloads** - Export all results to CSV

### **4. No Code Required**
- Point-and-click interface
- No command-line knowledge needed
- Perfect for analysts, investors, researchers

---

## 🎯 How to Use

### **Step 1: Configure Analysis**

In the **sidebar**:
1. Enter company tickers (comma or newline separated)
   ```
   AAPL, MSFT, GOOGL, AMZN
   ```
2. Select quarter (e.g., `2025Q3`)
3. *(Optional)* Upload news CSV for sentiment analysis
4. *(Optional)* Adjust dial weights in Advanced settings

### **Step 2: Run Analysis**

Click the **🚀 Run Analysis** button

The app will:
- Fetch SEC filings
- Pull market data
- Calculate 4 dials
- Compute composite scores
- Generate visualizations

### **Step 3: Review Results**

Explore the results through:
- **Composite Ranking** - See which companies rank best
- **Visualizations** - Interactive charts and graphs
- **Detailed Metrics** - Drill down into each dial
- **Downloads** - Export CSVs for further analysis

---

## 📊 Understanding the Output

### **Composite Ranking Table**

| Column | Description | Range |
|--------|-------------|-------|
| **Rank** | Position in peer group | 1 (best) to N (worst) |
| **Ticker** | Company stock symbol | - |
| **Composite %** | Overall IRCI score | 0-100% (higher is better) |
| **Valuation %** | Relative valuation score | 0-100% (higher = cheaper) |
| **Liquidity %** | Trading ease score | 0-100% (higher = more liquid) |
| **Coverage %** | Disclosure quality | 0-100% (higher = better disclosure) |
| **Trust %** | Stability & sentiment | 0-100% (higher = more stable) |

### **Default Weights**
- **Liquidity**: 35%
- **Valuation**: 35%
- **Coverage**: 15%
- **Trust**: 15%

You can customize these in Advanced settings.

---

## 📂 News Data Format

If you want to include sentiment analysis, upload a CSV with:

**Required Columns:**
- `date` or `published_at` - Article timestamp (YYYY-MM-DD or ISO format)
- `ticker` - Stock symbol (e.g., "AAPL")
- `headline` or `title` - Article headline text

**Optional Columns:**
- `url` - Article URL
- `domain` - Source domain (e.g., "bloomberg.com")
- `lang` - Language code (default: "en")

**Example:**
```csv
published_at,ticker,headline,url,domain
2025-07-15 09:30:00,AAPL,Apple announces new AI features,https://...,bloomberg.com
2025-07-20 14:00:00,MSFT,Microsoft beats earnings estimates,https://...,wsj.com
```

---

## 🌐 Deployment Options

### **Option 1: Local (Your Computer)**

```bash
streamlit run app.py
```

Access at: `http://localhost:8501`

**Best for:** Personal use, development, testing

---

### **Option 2: Streamlit Cloud (Free)**

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Deploy!

**Best for:** Sharing with team, lightweight use

**Free tier includes:**
- Unlimited public apps
- 1GB memory per app
- Community support

---

### **Option 3: Docker Container**

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements-webapp.txt .
RUN pip install --no-cache-dir -r requirements-webapp.txt

COPY . .
RUN pip install -e .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t irci-webapp .
docker run -p 8501:8501 irci-webapp
```

**Best for:** Production, scalability, IT-managed environments

---

### **Option 4: Cloud Platforms**

#### **Heroku**
```bash
# Add Procfile
echo "web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0" > Procfile

# Deploy
heroku create irci-app
git push heroku main
```

#### **AWS EC2 / Azure VM / GCP Compute**
```bash
# SSH into VM
ssh user@your-vm-ip

# Clone repo
git clone https://github.com/your-username/IRCI.git
cd IRCI

# Install dependencies
pip install -r requirements-webapp.txt
pip install -e .

# Run with nohup (keeps running after logout)
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

Access at: `http://your-vm-ip:8501`

**Best for:** Full control, custom infrastructure

---

### **Option 5: Streamlit in Production**

For production use with authentication:

```python
# Add to app.py
import streamlit_authenticator as stauth

# Password hashing
hashed_passwords = stauth.Hasher(['password123']).generate()

authenticator = stauth.Authenticate(
    {'usernames': {'admin': {'name': 'Admin User', 'password': hashed_passwords[0]}}},
    'cookie_name',
    'signature_key',
    cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status:
    # Show app
    st.write(f'Welcome {name}')
    # ... rest of app ...
elif authentication_status == False:
    st.error('Username/password is incorrect')
```

**Best for:** Multi-user environments, sensitive data

---

## ⚙️ Configuration

### **Streamlit Config**

Create `.streamlit/config.toml`:

```toml
[server]
port = 8501
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### **Environment Variables**

Create `.env`:
```bash
IRCI_FMP_API_KEY=your_api_key_here
IRCI_DATA_DIR=./data
IRCI_OUTPUT_DIR=./outputs
```

---

## 🔒 Security Considerations

### **For Public Deployment:**

1. **Add authentication** (see Option 5 above)
2. **Use HTTPS** (SSL/TLS certificates)
3. **Set rate limits** (prevent abuse)
4. **Sanitize inputs** (validate tickers)
5. **Hide API keys** (use environment variables)

### **Example: Rate Limiting**

```python
import streamlit as st
from datetime import datetime, timedelta

# Simple rate limiting
if 'last_run' not in st.session_state:
    st.session_state.last_run = datetime.min

if run_analysis:
    time_since_last = datetime.now() - st.session_state.last_run
    if time_since_last < timedelta(minutes=5):
        st.error("Please wait 5 minutes between analyses")
        st.stop()
    st.session_state.last_run = datetime.now()
```

---

## 📈 Performance Tips

### **For Large Datasets:**

1. **Cache results** (Streamlit built-in):
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(tickers, quarter):
    return irci_analysis(tickers, quarter)
```

2. **Async data loading**:
```python
import asyncio
async def fetch_all_data():
    tasks = [fetch_trust(), fetch_valuation(), ...]
    return await asyncio.gather(*tasks)
```

3. **Use lighter visualizations** for >20 companies

---

## 🐛 Troubleshooting

### **App won't start**
```bash
# Check if port is in use
lsof -i :8501

# Use different port
streamlit run app.py --server.port 8502
```

### **Module not found errors**
```bash
# Reinstall dependencies
pip install -r requirements-webapp.txt
pip install -e .
```

### **FMP API errors**
- Check your API key in `.env`
- Verify API rate limits
- App falls back to yfinance automatically

### **Out of memory**
- Reduce number of companies analyzed
- Clear Streamlit cache: `streamlit cache clear`
- Increase server memory allocation

---

## 🎨 Customization

### **Change Colors/Theme**

Edit `app.py`:
```python
st.set_page_config(
    page_title="My IRCI App",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

### **Add New Visualizations**

```python
# Example: Heatmap
import plotly.graph_objects as go

fig = go.Figure(data=go.Heatmap(
    z=correlation_matrix,
    x=dial_names,
    y=tickers,
    colorscale='RdYlGn'
))
st.plotly_chart(fig)
```

### **Add Download Reports**

```python
from io import BytesIO
import xlsxwriter

# Create Excel with multiple sheets
output = BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_composite.to_excel(writer, sheet_name='Composite')
    df_trust.to_excel(writer, sheet_name='Trust')

st.download_button(
    "📥 Download Excel Report",
    output.getvalue(),
    "irci_report.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
```

---

## 📞 Support

- **Documentation**: See `README.md`, `QUICKSTART.md`
- **Issues**: GitHub Issues page
- **Questions**: Email your team lead

---

## 🎓 Training Your Team

### **Quick Demo Script:**

1. Open app: `./run_webapp.sh`
2. Select companies: "AAPL, MSFT, GOOGL, AMZN"
3. Choose quarter: "2025Q3"
4. Click "Run Analysis"
5. Explore visualizations
6. Download results

**Time needed:** 5 minutes per analysis

### **Video Tutorial Ideas:**

1. "Getting Started with IRCI Web App" (3 min)
2. "Understanding the Four Dials" (5 min)
3. "Adding Sentiment Analysis with News Data" (4 min)
4. "Customizing Weights & Interpreting Results" (6 min)

---

## ✅ Checklist for Go-Live

- [ ] App runs locally without errors
- [ ] All 4 dials compute correctly
- [ ] Visualizations display properly
- [ ] Downloads work for all CSV exports
- [ ] News upload (optional) functions
- [ ] Error handling displays user-friendly messages
- [ ] Deployed to chosen platform
- [ ] Team members can access URL
- [ ] Documentation shared with team
- [ ] Support process established

---

**Congratulations!** You now have a production-ready web interface for IRCI analysis. 🎉

**Last Updated**: Nov 18, 2025
**IRCI Version**: 0.1.0
**App Version**: 1.0.0
