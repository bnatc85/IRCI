# News Puller (GDELT, FMP, RSS)
Fetch news headlines for IRCI and save them to CSV/JSON/SQLite.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Examples
```bash
# GDELT
python news_pull.py gdelt --query "investor relations OR 10-K" --limit 50 --out out/gdelt.csv

# FMP (stock news)
export FMP_API_KEY=YOUR_KEY
python news_pull.py fmp --tickers AAPL,MSFT,AMZN,GOOGL --limit 100 --sqlite out/news.db

# RSS
python news_pull.py rss --feeds https://www.reuters.com/finance/archive/businessNews.rss,https://apnews.com/apf-topnews --limit 100 --json out/rss.json
```

**Schema (SQLite table `articles`):**
`source, ticker, title, url, published_at, source_name, language, raw, pulled_at` with `UNIQUE(url)`.
