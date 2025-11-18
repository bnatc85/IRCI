import pandas as pd
from types import SimpleNamespace
from irci.coverage import coverage_snapshot

def fake_settings():
    return SimpleNamespace(
        user_agent="IRCI/0.1 (+test)",
        domain_weights={"wsj.com": 1.0, "bloomberg.com": 1.0},
        data_root="."  # not used here
    )

def fake_media_fetcher(ticker, q_start, q_end, s):
    return pd.DataFrame([
        {"published_at":"2025-07-10","url":"https://www.wsj.com/x","domain":"wsj.com","lang":"en"},
        {"published_at":"2025-08-02","url":"https://www.bloomberg.com/y","domain":"bloomberg.com","lang":"en"},
    ])

def test_coverage_with_media(monkeypatch):
    # Avoid network: stub Settings.load and _company_submissions
    import irci.coverage as cov
    monkeypatch.setattr(cov.Settings, "load", staticmethod(fake_settings))
    subs = pd.DataFrame({
        "filingDate": pd.to_datetime(["2025-09-15","2025-10-20"], utc=True),
        "form": ["8-K","10-Q"]
    })
    monkeypatch.setattr(cov, "_company_submissions", lambda cik, s: subs)
    monkeypatch.setattr(cov, "_cik_for_ticker", lambda t, s: "0000320193")  # AAPL CIK

    df = coverage_snapshot(["AAPL"], as_of="2025-09-30", media_fetcher=fake_media_fetcher, media_weight=0.5)
    assert {"q_media_weighted","q_media_unique_articles","q_media_unique_domains"} <= set(df.columns)
    assert df.loc[0, "q_media_unique_articles"] == 2
