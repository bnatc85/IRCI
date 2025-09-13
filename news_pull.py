#!/usr/bin/env python3
"""news_pull.py
Pull real news headlines from multiple sources and save them to CSV/JSON/SQLite.
Sources: GDELT Doc API, FMP stock_news, and generic RSS feeds.
"""
import argparse, csv, os, sys, json, sqlite3, datetime as dt
from typing import List, Dict, Any, Optional

try:
    import requests
except Exception as e:
    print("Missing dependency: requests. Try 'pip install -r requirements.txt'", file=sys.stderr)
    raise

# RSS mode is optional
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None

Row = Dict[str, Any]

def now_iso() -> str:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()

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
    r.raise_for_status()
    data = r.json()
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

def fetch_fmp(tickers: List[str], limit: int = 50, api_key: Optional[str] = None) -> List[Row]:
    api_key = api_key or os.getenv("FMP_API_KEY")
    if not api_key:
        raise RuntimeError("FMP_API_KEY not set. Export your key or pass --api-key.")
    base = "https://financialmodelingprep.com/api/v3/stock_news"
    params = {"tickers": ",".join(tickers), "limit": str(limit), "apikey": api_key}
    r = requests.get(base, params=params, timeout=30)
    r.raise_for_status()
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

def fetch_rss(feed_urls: List[str], limit: int = 100) -> List[Row]:
    if feedparser is None:
        raise RuntimeError("RSS mode requires feedparser. Run: pip install feedparser")
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
def dedupe(rows: List[Row]) -> List[Row]:
    seen = set(); out = []
    for r in rows:
        u = r.get("url")
        if u and u not in seen:
            seen.add(u)
            out.append(r)
    return out

def save_csv(rows: List[Row], path: str) -> None:
    ensure_dir(path)
    if not rows:
        print("No rows to save (CSV).")
        return
    fieldnames = ["source","ticker","title","url","published_at","source_name","language","pulled_at","raw"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            r2 = r.copy()
            r2["raw"] = json.dumps(r2["raw"], ensure_ascii=False)
            w.writerow(r2)
    print(f"CSV saved: {path} ({len(rows)} rows)")

def save_json(rows: List[Row], path: str) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON saved: {path} ({len(rows)} rows)")

def save_sqlite(rows: List[Row], db_path: str) -> None:
    ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""        CREATE TABLE IF NOT EXISTS articles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT,
      ticker TEXT,
      title TEXT,
      url TEXT UNIQUE,
      published_at TEXT,
      source_name TEXT,
      language TEXT,
      raw TEXT,
      pulled_at TEXT
    );
    """)
    inserted = 0
    for r in rows:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO articles
                (source,ticker,title,url,published_at,source_name,language,raw,pulled_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    r.get("source"),
                    r.get("ticker"),
                    r.get("title"),
                    r.get("url"),
                    r.get("published_at"),
                    r.get("source_name"),
                    r.get("language"),
                    json.dumps(r.get("raw"), ensure_ascii=False),
                    r.get("pulled_at"),
                ),
            )
            inserted += cur.rowcount
        except sqlite3.Error as e:
            print("SQLite error:", e, r.get("url"))
    conn.commit()
    conn.close()
    print(f"SQLite saved: {db_path} (+{inserted} new, {len(rows)-inserted} dup/skipped)")

# ---------------------- CLI ----------------------
def main():
    import argparse
    ap = argparse.ArgumentParser(description="Pull news headlines and save to CSV/JSON/SQLite.")
    sub = ap.add_subparsers(dest="mode", required=True)

    ap_gd = sub.add_parser("gdelt", help="Pull from GDELT Doc API")
    ap_gd.add_argument("--query", required=True, help="Search query, e.g., 'AAPL OR Apple Inc'")
    ap_gd.add_argument("--limit", type=int, default=50)

    ap_fmp = sub.add_parser("fmp", help="Pull from Financial Modeling Prep /v3/stock_news")
    ap_fmp.add_argument("--tickers", required=True, help="Comma-separated tickers, e.g., AAPL,MSFT")
    ap_fmp.add_argument("--limit", type=int, default=50)
    ap_fmp.add_argument("--api-key", dest="api_key", default=None, help="FMP API key (or set FMP_API_KEY env var)")

    ap_rss = sub.add_parser("rss", help="Pull from RSS feeds (feedparser)")
    ap_rss.add_argument("--feeds", required=True, help="Comma-separated feed URLs")
    ap_rss.add_argument("--limit", type=int, default=100)

    # Outputs
    ap.add_argument("--out", help="CSV file path to save")
    ap.add_argument("--json", dest="json_out", help="JSON file path to save")
    ap.add_argument("--sqlite", dest="sqlite_db", help="SQLite DB path to upsert into (creates if missing)")

    args = ap.parse_args()

    if args.mode == "gdelt":
        rows = fetch_gdelt(args.query, args.limit)
    elif args.mode == "fmp":
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        rows = fetch_fmp(tickers, args.limit, api_key=args.api_key)
    elif args.mode == "rss":
        if feedparser is None:
            raise RuntimeError("RSS mode requires feedparser. Try: pip install feedparser")
        feeds = [u.strip() for u in args.feeds.split(",") if u.strip()]
        rows = fetch_rss(feeds, args.limit)
    else:
        raise SystemExit(2)

    rows = dedupe(rows)
    if not any([args.out, args.json_out, args.sqlite_db]):
        args.out = "out/news.csv"  # default

    if args.out:
        save_csv(rows, args.out)
    if args.json_out:
        save_json(rows, args.json_out)
    if args.sqlite_db:
        save_sqlite(rows, args.sqlite_db)

if __name__ == "__main__":
    main()
