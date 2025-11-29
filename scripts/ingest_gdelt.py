#!/usr/bin/env python3
import argparse, sys, json
from datetime import datetime, timezone
from urllib.parse import urlparse, quote_plus
import requests
import pandas as pd

from irci.config import Settings
from irci.media_store import upsert_news_rows

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

def quarter_bounds(as_of: str):
    ts = pd.to_datetime(as_of, utc=True)
    p = ts.tz_convert("UTC").tz_localize(None).to_period("Q")
    start = p.start_time.tz_localize("UTC")
    end   = p.end_time.tz_localize("UTC")
    return start, end

def gdelt_list(query: str, start, end, maxrecords=75, user_agent="IRCI/0.1"):
    params = {
        "query": query,
        "mode": "ArtList",          # list of matching articles
        "format": "json",           # ask for JSON
        "maxrecords": str(maxrecords),
        "sort": "DateDesc",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    }
    headers = {"User-Agent": user_agent}
    r = requests.get(GDELT_URL, params=params, headers=headers, timeout=60)

    # If not 2xx, raise so we see the HTTP error
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        snippet = r.text[:200].replace("\n", " ")
        print(f"[GDELT] HTTP error {r.status_code}: {snippet}")
        raise

    # Some 200 responses are empty or plain text. Be defensive.
    ctype = r.headers.get("Content-Type", "").lower()
    text = (r.text or "").strip()

    if not text:
        # Empty body – just return no articles
        return []

    if "application/json" not in ctype and not text.startswith("{"):
        # Not JSON – log a snippet and return no articles
        print(f"[GDELT] Non-JSON response ({ctype}): {text[:200]!r}")
        return []

    try:
        js = r.json()
    except ValueError:
        # Body said JSON but wasn’t parseable – log and continue
        print(f"[GDELT] JSON parse error. First 200 chars: {text[:200]!r}")
        return []

    return js.get("articles", []) or []


def to_rows(arts, ticker):
    rows = []
    for a in arts:
        url = a.get("url") or ""
        if not url:
            continue
        dom = a.get("domain") or urlparse(url).netloc.lower()
        lang = a.get("language") or "en"
        # GDELT date fields vary; seendate is common and UTC
        dt = a.get("seendate") or a.get("date") or a.get("publishdate")
        # normalize to ISO 8601 if present
        try:
            if dt and isinstance(dt, str) and len(dt) >= 14 and dt.isdigit():
                # e.g., 20250710123000
                dt = datetime.strptime(dt[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
        rows.append({
            "published_at": dt,
            "url": url,
            "domain": dom.lower().removeprefix("www."),
            "lang": lang,
            "headline": a.get("title"),
            "source": "gdelt",
            "ticker": ticker,
        })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", required=True, help="Comma-separated, e.g. AAPL,MSFT")
    ap.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat(),
                    help="Quarter to fetch for (YYYY-MM-DD in that quarter)")
    ap.add_argument("--maxrecords", type=int, default=75)
    ap.add_argument("--queries", default="",
                    help='JSON map like {"AAPL": "Apple OR AAPL", "MSFT": "Microsoft OR MSFT"}; '
                         'defaults to ticker itself if omitted')
    args = ap.parse_args()

    s = Settings.load()
    qstart, qend = quarter_bounds(args["as_of"] if isinstance(args, dict) else args.as_of)

    queries = {}
    if args.queries:
        queries = json.loads(args.queries)

    for t in [x.strip().upper() for x in args.tickers.split(",") if x.strip()]:
        q = queries.get(t) or t  # start simple: search by ticker, or your custom query
        arts = gdelt_list(q, qstart, qend, maxrecords=args.maxrecords, user_agent=s.user_agent)
        rows = to_rows(arts, t)
        # keep only rows with a timestamp inside the quarter
        if rows:
            df = pd.DataFrame(rows)
            df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
            df = df[(df["published_at"] >= qstart) & (df["published_at"] <= qend)]
            rows = df.to_dict("records")
        upsert_news_rows(t, rows, s.data_root)
        print(f"{t}: saved {len(rows)} rows to {(s.data_root/'news').resolve()}")

if __name__ == "__main__":
    main()
