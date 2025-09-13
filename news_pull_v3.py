#!/usr/bin/env python3
"""news_pull_v3.py
Pull news headlines from: GDELT, FMP (if plan allows), RSS, Alpha Vantage (NEWS_SENTIMENT).
Saves to CSV/JSON/SQLite with de-duplication.

Changes vs v2:
- GDELT: handles non-JSON responses gracefully (rate limits or HTML interstitials).
- UTC time generation updated (no deprecation warnings).
- FMP: clearer error for 403/plan restriction.
- Alpha Vantage: optional alternative to FMP (requires ALPHAVANTAGE_API_KEY).
"""
import argparse, csv, os, sys, json, sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

try:
    import requests
except Exception:
    print("Missing dependency: requests. Run: pip install -r requirements.txt", file=sys.stderr); raise

try:
    import feedparser  # optional (RSS mode)
except Exception:
    feedparser = None

Row = Dict[str, Any]

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_dir(path: str) -> None:
    d = path if os.path.isdir(path) else os.path.dirname(path) or "."
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

# ---------------------- Fetchers ----------------------
def fetch_gdelt(query: str, limit: int = 50) -> List[Row]:
    base = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": str(limit),
        "format": "json",
        "sort": "DateDesc",
    }
    r = requests.get(base, params=params, timeout=30)
    ct = r.headers.get("content-type", "")
    text_preview = (r.text or "")[:300]
    if r.status_code != 200:
        raise SystemExit(f"GDELT -> HTTP {r.status_code}: {text_preview}")
    try:
        data = r.json()
    except Exception:
        # GDELT sometimes returns HTML or empty body if throttled.
        print(f"[warn] GDELT returned non-JSON ({ct}). First bytes: {text_preview!r}", file=sys.stderr)
        return []
    arts = data.get("articles", []) or []
    rows: List[Row] = []
    for a in arts:
        rows.append({
            "source": "gdelt",
            "ticker": None,
            "title": a.get("title"),
            "url": a.get("url"),
            "published_at": a.get("seendate"),
            "source_name": a.get("domain"),
            "language": a.get("language"),
            "raw": a,
            "pulled_at": now_iso(),
        })
    return rows

def fetch_fmp(tickers, limit=50, api_key=None) -> List[Row]:
    api_key = api_key or os.getenv("FMP_API_KEY")
    if not api_key:
        raise SystemExit("FMP_API_KEY not set. Export it or pass --api-key.")
    base = "https://financialmodelingprep.com/api/v3/stock_news"
    params = {"tickers": ",".join(tickers), "limit": str(limit), "apikey": api_key}
    r = requests.get(base, params=params, timeout=30)
    if r.status_code == 403:
        raise SystemExit(
            "FMP -> HTTP 403 (plan restricted). This endpoint may require a paid plan."
            "Try: rss mode, gdelt mode, or the new 'alphavantage' subcommand (free key)."
        )
    if r.status_code != 200:
        raise SystemExit(f"FMP -> HTTP {r.status_code}: {r.text[:300]}")
    items = r.json() or []
    rows: List[Row] = []
    for it in items:
        rows.append({
            "source": "fmp",
            "ticker": it.get("symbol"),
            "title": it.get("title"),
            "url": it.get("url") or it.get("link"),
            "published_at": it.get("publishedDate") or it.get("date"),
            "source_name": it.get("site") or it.get("source"),
            "language": None,
            "raw": it,
            "pulled_at": now_iso(),
        })
    return rows

def fetch_alphavantage(tickers, limit=50, api_key=None) -> List[Row]:
    """Alpha Vantage NEWS_SENTIMENT (free with key, rate-limited).
    API: https://www.alphavantage.co/documentation/#news-and-sentiment
    Note: 'limit' is advisory; AV uses 'limit' param but enforces its own caps.
    """
    api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise SystemExit("ALPHAVANTAGE_API_KEY not set. Export it or pass --api-key.")
    base = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ",".join(tickers),
        "limit": str(limit),
        "apikey": api_key,
    }
    r = requests.get(base, params=params, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"AlphaVantage -> HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    feed = data.get("feed", []) or []
    rows: List[Row] = []
    for it in feed:
        rows.append({
            "source": "alphavantage",
            "ticker": ",".join(it.get("ticker_sentiment", []) and [t.get("ticker") for t in it["ticker_sentiment"]] or []),
            "title": it.get("title"),
            "url": it.get("url"),
            "published_at": it.get("time_published"),
            "source_name": it.get("source"),
            "language": it.get("language"),
            "raw": it,
            "pulled_at": now_iso(),
        })
    return rows

def fetch_rss(feed_urls, limit=100) -> List[Row]:
    if feedparser is None:
        raise SystemExit("RSS mode requires feedparser. Run: pip install feedparser")
    rows: List[Row] = []
    for url in feed_urls:
        parsed = feedparser.parse(url)
        for e in parsed.entries[:limit]:
            rows.append({
                "source": "rss",
                "ticker": None,
                "title": getattr(e, "title", None),
                "url": getattr(e, "link", None),
                "published_at": getattr(e, "published", None) or getattr(e, "updated", None),
                "source_name": getattr(parsed.feed, "title", None),
                "language": getattr(parsed.feed, "language", None),
                "raw": {k: getattr(e, k) for k in e.keys()},
                "pulled_at": now_iso(),
            })
    return rows

# ---------------------- Saving ----------------------
def dedupe(rows):
    seen = set(); out = []
    for r in rows:
        u = r.get("url")
        if u and u not in seen:
            seen.add(u); out.append(r)
    return out

def save_csv(rows, path):
    ensure_dir(path)
    if not rows:
        print("No rows to save (CSV)."); return
    fields = ["source","ticker","title","url","published_at","source_name","language","pulled_at","raw"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            r2 = r.copy(); r2["raw"] = json.dumps(r2["raw"], ensure_ascii=False)
            w.writerow(r2)
    print(f"CSV saved: {path} ({len(rows)} rows)")

def save_json(rows, path):
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON saved: {path} ({len(rows)} rows)")

def save_sqlite(rows, db_path):
    ensure_dir(db_path)
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    cur.execute("""    CREATE TABLE IF NOT EXISTS articles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT, ticker TEXT, title TEXT, url TEXT UNIQUE,
      published_at TEXT, source_name TEXT, language TEXT,
      raw TEXT, pulled_at TEXT
    );""")
    inserted = 0
    for r in rows:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO articles
                (source,ticker,title,url,published_at,source_name,language,raw,pulled_at)
                VALUES (?,?,?,?,?,?,?,?,?)""", (
                    r.get("source"), r.get("ticker"), r.get("title"), r.get("url"),
                    r.get("published_at"), r.get("source_name"), r.get("language"),
                    json.dumps(r.get("raw"), ensure_ascii=False), r.get("pulled_at"),
                )
            )
            inserted += cur.rowcount
        except Exception as e:
            print("SQLite error:", e, r.get("url"))
    conn.commit(); conn.close()
    print(f"SQLite saved: {db_path} (+{inserted} new, {len(rows)-inserted} dup/skipped)")

# ---------------------- CLI ----------------------
def main():
    ap = argparse.ArgumentParser(description="Pull news headlines and save to CSV/JSON/SQLite.")
    sub = ap.add_subparsers(dest="mode", required=True)

    # GDELT subcommand
    ap_gd = sub.add_parser("gdelt", help="Pull from GDELT Doc API")
    ap_gd.add_argument("--query", required=True)
    ap_gd.add_argument("--limit", type=int, default=50)
    ap_gd.add_argument("--out", help="CSV file path")
    ap_gd.add_argument("--json", dest="json_out", help="JSON file path")
    ap_gd.add_argument("--sqlite", dest="sqlite_db", help="SQLite DB path")

    # FMP subcommand
    ap_fmp = sub.add_parser("fmp", help="Pull from FMP /v3/stock_news (may require paid plan)")
    ap_fmp.add_argument("--tickers", required=True, help="Comma-separated tickers")
    ap_fmp.add_argument("--limit", type=int, default=50)
    ap_fmp.add_argument("--api-key", dest="api_key", default=None, help="FMP API key (or env FMP_API_KEY)")
    ap_fmp.add_argument("--out", help="CSV file path")
    ap_fmp.add_argument("--json", dest="json_out", help="JSON file path")
    ap_fmp.add_argument("--sqlite", dest="sqlite_db", help="SQLite DB path")

    # Alpha Vantage subcommand (alternative)
    ap_av = sub.add_parser("alphavantage", help="Pull from Alpha Vantage NEWS_SENTIMENT (requires ALPHAVANTAGE_API_KEY)")
    ap_av.add_argument("--tickers", required=True, help="Comma-separated tickers")
    ap_av.add_argument("--limit", type=int, default=50)
    ap_av.add_argument("--api-key", dest="api_key", default=None, help="Alpha Vantage API key (or env ALPHAVANTAGE_API_KEY)")
    ap_av.add_argument("--out", help="CSV file path")
    ap_av.add_argument("--json", dest="json_out", help="JSON file path")
    ap_av.add_argument("--sqlite", dest="sqlite_db", help="SQLite DB path")

    # RSS subcommand
    ap_rss = sub.add_parser("rss", help="Pull from RSS feeds (feedparser)")
    ap_rss.add_argument("--feeds", required=True, help="Comma-separated feed URLs")
    ap_rss.add_argument("--limit", type=int, default=100)
    ap_rss.add_argument("--out", help="CSV file path")
    ap_rss.add_argument("--json", dest="json_out", help="JSON file path")
    ap_rss.add_argument("--sqlite", dest="sqlite_db", help="SQLite DB path")

    args = ap.parse_args()

    if args.mode == "gdelt":
        rows = fetch_gdelt(args.query, args.limit)
    elif args.mode == "fmp":
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        rows = fetch_fmp(tickers, args.limit, api_key=args.api_key)
    elif args.mode == "alphavantage":
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        rows = fetch_alphavantage(tickers, args.limit, api_key=args.api_key)
    elif args.mode == "rss":
        feeds = [u.strip() for u in args.feeds.split(",") if u.strip()]
        rows = fetch_rss(feeds, args.limit)
    else:
        raise SystemExit(2)

    rows = dedupe(rows)

    # default if no output specified for that subcommand
    out = getattr(args, "out", None)
    jsn = getattr(args, "json_out", None)
    db  = getattr(args, "sqlite_db", None)
    if not any([out, jsn, db]):
        out = "out/news.csv"

    if out: save_csv(rows, out)
    if jsn: save_json(rows, jsn)
    if db:  save_sqlite(rows, db)

if __name__ == "__main__":
    main()
