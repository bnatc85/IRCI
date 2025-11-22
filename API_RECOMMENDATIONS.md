# API Recommendations for IRCI Enhancement

## Currently Using:
- ✅ **FMP (Financial Modeling Prep)** - Stock prices, enterprise value, financials
- ✅ **World News API** - News articles for coverage/sentiment
- ✅ **SEC EDGAR** - SEC filings (8-K, 10-Q, 10-K)
- ✅ **Yahoo Finance (yfinance)** - Market data, historical prices
- ✅ **OpenAI API** - AI chatbot

---

## 💰 VALUATION DIAL - Additional Data Sources

### Free/Affordable Options:

**1. Alpha Vantage** - https://www.alphavantage.co/
- **Cost:** Free tier (5 API calls/min, 500/day)
- **Data:** Income statements, balance sheets, cash flow, earnings
- **Enhancement:** More detailed financial ratios, quarterly earnings surprises
- **Setup:** `ALPHA_VANTAGE_API_KEY=your_key`

**2. IEX Cloud** - https://iexcloud.io/
- **Cost:** Free tier (500K messages/month)
- **Data:** Real-time financials, analyst estimates, P/E ratios
- **Enhancement:** Forward P/E, PEG ratio, analyst price targets
- **Setup:** `IEX_CLOUD_API_KEY=your_key`

**3. Polygon.io** - https://polygon.io/
- **Cost:** Free tier (5 API calls/min)
- **Data:** Stock fundamentals, financials, dividends
- **Enhancement:** More granular valuation metrics
- **Setup:** `POLYGON_API_KEY=your_key`

### Premium Options:

**4. Intrinio** - https://intrinio.com/
- **Cost:** ~$150-500/month
- **Data:** Professional-grade financials, standardized metrics
- **Enhancement:** High-quality standardized data, historical revisions

---

## 💧 LIQUIDITY DIAL - Trading & Market Microstructure

### Free/Affordable Options:

**1. Alpaca Markets API** - https://alpaca.markets/
- **Cost:** Free (for market data)
- **Data:** Real-time bid-ask spreads, tick data, NBBO (National Best Bid Offer)
- **Enhancement:** More accurate bid-ask spreads, intraday liquidity patterns
- **Setup:** `ALPACA_API_KEY=your_key` + `ALPACA_SECRET_KEY=your_secret`

**2. Polygon.io (Stocks)** - https://polygon.io/
- **Cost:** Free tier available
- **Data:** Trades and quotes (tick-by-tick)
- **Enhancement:** High-frequency liquidity metrics, more precise Amihud illiquidity
- **Setup:** `POLYGON_API_KEY=your_key`

**3. IEX Cloud** - https://iexcloud.io/
- **Cost:** Free tier
- **Data:** Real-time volume, intraday stats
- **Enhancement:** Intraday volume patterns, liquidity snapshots

### Premium Options:

**4. Nasdaq Data Link (Quandl)** - https://data.nasdaq.com/
- **Cost:** ~$50-200/month
- **Data:** High-quality market microstructure data
- **Enhancement:** Professional-grade liquidity metrics

---

## 📊 COVERAGE DIAL - Media & Analyst Coverage

### Free Options:

**1. NewsAPI.org** - https://newsapi.org/
- **Cost:** Free tier (100 requests/day)
- **Data:** 80,000+ news sources, headlines, articles
- **Enhancement:** Broader news coverage, more sources than World News API
- **Setup:** `NEWS_API_KEY=your_key`

**2. Google News RSS** - https://news.google.com/rss
- **Cost:** Free
- **Data:** Google News articles via RSS feeds
- **Enhancement:** Free alternative to paid news APIs
- **Setup:** No API key needed (use feedparser)

**3. Reddit API** - https://www.reddit.com/dev/api/
- **Cost:** Free
- **Data:** Reddit mentions, posts, comments (retail investor coverage)
- **Enhancement:** Track retail investor discussion on r/investing, r/stocks
- **Setup:** `REDDIT_CLIENT_ID=your_id` + `REDDIT_CLIENT_SECRET=your_secret`

**4. Hacker News API** - https://github.com/HackerNews/API
- **Cost:** Free
- **Data:** Tech company coverage on Hacker News
- **Enhancement:** Good for tech stocks, startup coverage
- **Setup:** No API key needed

### Affordable Options:

**5. Benzinga News API** - https://www.benzinga.com/apis/
- **Cost:** ~$25-100/month
- **Data:** Real-time financial news, analyst ratings
- **Enhancement:** Professional financial news feed
- **Setup:** `BENZINGA_API_KEY=your_key`

**6. Seeking Alpha API** - https://seekingalpha.com/
- **Cost:** Scraping (unofficial) or premium access
- **Data:** Analyst articles, earnings call transcripts
- **Enhancement:** Detailed analyst coverage, earnings call analysis

### Premium Options:

**7. Bloomberg Terminal API** - https://www.bloomberg.com/professional/
- **Cost:** ~$2,000/month (requires Bloomberg Terminal)
- **Data:** Comprehensive news, analyst coverage, terminal access
- **Enhancement:** Gold standard for financial news

**8. FactSet API** - https://www.factset.com/
- **Cost:** Custom pricing (thousands/month)
- **Data:** Analyst estimates, consensus ratings, transcripts
- **Enhancement:** Professional analyst coverage tracking

---

## 💭 TRUST DIAL - Sentiment & ESG

### Free Options:

**1. Stocktwits API** - https://api.stocktwits.com/developers
- **Cost:** Free
- **Data:** Social sentiment from retail investors
- **Enhancement:** Real-time retail investor sentiment
- **Setup:** `STOCKTWITS_API_KEY=your_key`

**2. Twitter/X API (Basic)** - https://developer.twitter.com/
- **Cost:** Free tier (limited)
- **Data:** Tweets, hashtags, mentions
- **Enhancement:** Social media sentiment, executive Twitter activity
- **Setup:** `TWITTER_BEARER_TOKEN=your_token`

**3. Glassdoor API** - https://www.glassdoor.com/developer/
- **Cost:** Unofficial/scraping
- **Data:** Employee reviews, CEO approval ratings
- **Enhancement:** Internal trust metric (employee sentiment)

### Affordable Options:

**4. LunarCrush API** - https://lunarcrush.com/
- **Cost:** Free tier (100 requests/day) + paid tiers
- **Data:** Social media sentiment aggregation
- **Enhancement:** Comprehensive social sentiment scores
- **Setup:** `LUNARCRUSH_API_KEY=your_key`

**5. Alternative.me** - https://alternative.me/
- **Cost:** Free
- **Data:** Market sentiment indices
- **Enhancement:** Broad market sentiment context

**6. CSRHub API** - https://www.csrhub.com/
- **Cost:** ~$100-500/month
- **Data:** ESG ratings, sustainability scores
- **Enhancement:** Environmental, Social, Governance metrics
- **Setup:** `CSRHUB_API_KEY=your_key`

### Premium Options:

**7. MSCI ESG Research** - https://www.msci.com/esg-ratings
- **Cost:** Custom pricing (expensive)
- **Data:** Professional ESG ratings
- **Enhancement:** Institutional-grade ESG scores

**8. Sustainalytics** - https://www.sustainalytics.com/
- **Cost:** Custom pricing
- **Data:** ESG risk ratings
- **Enhancement:** ESG risk assessment

**9. RepRisk** - https://www.reprisk.com/
- **Cost:** Custom pricing
- **Data:** ESG risk monitoring, controversies
- **Enhancement:** Real-time ESG risk events

---

## 🔧 CROSS-CUTTING / GENERAL

### Free/Affordable:

**1. Tiingo API** - https://www.tiingo.com/
- **Cost:** Free tier (1000 requests/day)
- **Data:** Stock prices, fundamentals, news
- **Enhancement:** Alternative to FMP for redundancy
- **Setup:** `TIINGO_API_KEY=your_key`

**2. Finnhub.io** - https://finnhub.io/
- **Cost:** Free tier (60 API calls/min)
- **Data:** Stock fundamentals, news, earnings, sentiment
- **Enhancement:** Good all-in-one alternative
- **Setup:** `FINNHUB_API_KEY=your_key`

**3. Marketstack** - https://marketstack.com/
- **Cost:** Free tier (100 requests/month)
- **Data:** Real-time and historical stock data
- **Enhancement:** Additional market data source

---

## 📋 RECOMMENDED PRIORITY

### **Immediate Value (Free/Low Cost):**

1. **NewsAPI.org** ($0, 100 req/day) → More coverage sources for Coverage dial
2. **Finnhub.io** ($0, 60 req/min) → Backup for FMP, additional sentiment
3. **Stocktwits API** ($0) → Retail investor sentiment for Trust dial
4. **Alpha Vantage** ($0, 500 req/day) → Additional financials for Valuation dial
5. **Google News RSS** ($0) → Free news coverage

### **High Value (Affordable):**

1. **IEX Cloud** ($0-$20/month) → Better liquidity metrics, real-time data
2. **LunarCrush** ($0-$50/month) → Comprehensive social sentiment
3. **Benzinga News** ($25-$100/month) → Professional news feed

### **Premium (If Budget Allows):**

1. **Polygon.io** ($200+/month) → Professional-grade tick data
2. **CSRHub** ($100-$500/month) → ESG ratings
3. **FactSet/Bloomberg** ($$$) → Institutional-grade everything

---

## 🎯 IMPLEMENTATION SUGGESTIONS

### Phase 1 (Free APIs - Quick Wins):
```bash
# Add to .env
NEWS_API_KEY=your_newsapi_key
FINNHUB_API_KEY=your_finnhub_key
STOCKTWITS_API_KEY=your_stocktwits_key
ALPHA_VANTAGE_API_KEY=your_alphavantage_key
```

### Phase 2 (Affordable Upgrades):
```bash
# Add to .env
IEX_CLOUD_API_KEY=your_iex_key
LUNARCRUSH_API_KEY=your_lunarcrush_key
BENZINGA_API_KEY=your_benzinga_key
```

### Phase 3 (Premium/Enterprise):
- Requires budget approval
- Consider institutional subscriptions (Bloomberg, FactSet, etc.)

---

## 📊 EXPECTED IMPACT BY DIAL

| Dial | Current Data | Priority APIs | Expected Improvement |
|------|-------------|---------------|---------------------|
| **Valuation** | FMP, yfinance | Alpha Vantage, IEX Cloud | +15% more comprehensive ratios |
| **Liquidity** | yfinance (spreads) | Alpaca, IEX Cloud, Polygon | +30% more accurate spreads |
| **Coverage** | World News, SEC | NewsAPI, Benzinga, Reddit | +50% more sources tracked |
| **Trust** | FinBERT on news | Stocktwits, Twitter, LunarCrush | +40% social sentiment added |

---

## 🔗 USEFUL AGGREGATORS

**API Aggregators (one key, multiple sources):**
- **RapidAPI** - https://rapidapi.com/ (aggregates 1000+ APIs)
- **API Layer** - https://apilayer.com/ (financial APIs collection)
- **AbstractAPI** - https://www.abstractapi.com/ (various data APIs)

These can simplify integration if you want multiple data sources.

---

## 💡 FREE TIER STRATEGY

**Maximum free data stack:**
1. FMP (existing) - 250 requests/day
2. Alpha Vantage - 500 requests/day
3. Finnhub - 60 requests/min
4. NewsAPI - 100 requests/day
5. IEX Cloud - 500K messages/month
6. World News API (existing)
7. Google News RSS - unlimited
8. Reddit API - 60 requests/min
9. Stocktwits - unlimited

**Total cost:** $0/month
**Coverage:** All 4 dials enhanced significantly

Let me know which ones you want to integrate first!
