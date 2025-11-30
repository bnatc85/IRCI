# irci/transcripts.py
"""
Earnings Call Transcript Fetcher and Analyzer

Fetches earnings call transcripts from FMP API and analyzes them for:
- Management tone/sentiment
- Forward-looking statement density
- Key topic coverage (guidance, risks, opportunities)
- Q&A quality metrics
"""
from __future__ import annotations
import re
import requests
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime

from .config import Settings
from .logging import get_logger

log = get_logger("irci.transcripts")


def fetch_earnings_transcript(
    ticker: str,
    quarter: int,
    year: int,
    settings: Optional[Settings] = None
) -> Dict:
    """
    Fetch earnings call transcript from FMP API.

    Args:
        ticker: Stock symbol
        quarter: Quarter number (1-4)
        year: Year (e.g., 2024)
        settings: Settings object with API keys

    Returns:
        Dict with transcript content and metadata
    """
    s = settings or Settings.load()
    api_key = s.fmp_api_key

    if not api_key:
        log.warning("FMP API key not configured for transcript fetch")
        return {"content": "", "error": "No API key"}

    url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}"
    params = {
        "quarter": quarter,
        "year": year,
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            transcript = data[0]
            return {
                "ticker": ticker,
                "quarter": quarter,
                "year": year,
                "date": transcript.get("date", ""),
                "content": transcript.get("content", ""),
                "source": "fmp"
            }
        else:
            log.info(f"No transcript found for {ticker} Q{quarter} {year}")
            return {"content": "", "error": "No transcript available"}

    except requests.RequestException as e:
        log.warning(f"Error fetching transcript for {ticker}: {e}")
        return {"content": "", "error": str(e)}


def fetch_transcript_list(
    ticker: str,
    settings: Optional[Settings] = None,
    limit: int = 8
) -> List[Dict]:
    """
    Fetch list of available transcripts for a ticker.

    Returns list of available earnings calls with dates.
    """
    s = settings or Settings.load()
    api_key = s.fmp_api_key

    if not api_key:
        return []

    url = f"https://financialmodelingprep.com/api/v4/earning_call_transcript"
    params = {
        "symbol": ticker,
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            return data[:limit]
        return []

    except Exception as e:
        log.warning(f"Error fetching transcript list for {ticker}: {e}")
        return []


def analyze_transcript(content: str) -> Dict:
    """
    Analyze earnings call transcript for key metrics.

    Returns:
        Dict with analysis metrics:
        - word_count: Total words in transcript
        - forward_looking_density: % of sentences with forward-looking language
        - guidance_mentions: Count of guidance-related terms
        - risk_mentions: Count of risk-related terms
        - confidence_score: Overall management confidence (0-1)
        - q_and_a_ratio: Ratio of Q&A section to prepared remarks
        - key_topics: Dict of topic mentions
    """
    if not content or len(content) < 100:
        return {
            "word_count": 0,
            "forward_looking_density": 0,
            "guidance_mentions": 0,
            "risk_mentions": 0,
            "confidence_score": 0.5,
            "q_and_a_ratio": 0,
            "key_topics": {},
            "transcript_quality_score": 0
        }

    # Clean and tokenize
    words = content.split()
    word_count = len(words)
    sentences = re.split(r'[.!?]+', content)
    sentence_count = len([s for s in sentences if len(s.strip()) > 10])

    # Forward-looking language patterns
    forward_patterns = [
        r'\b(expect|anticipate|project|forecast|outlook|guidance|target)\w*\b',
        r'\b(will|would|should|could|may|might)\s+(be|have|see|achieve|reach)\b',
        r'\b(going forward|next quarter|next year|fiscal year|coming months)\b',
        r'\b(growth|expansion|opportunity|pipeline|roadmap)\b',
        r'\b(confident|optimistic|excited|pleased|strong position)\b'
    ]

    forward_count = 0
    for pattern in forward_patterns:
        forward_count += len(re.findall(pattern, content, re.IGNORECASE))

    forward_looking_density = min(1.0, forward_count / max(sentence_count, 1) * 0.2)

    # Guidance-related terms
    guidance_terms = [
        'guidance', 'outlook', 'forecast', 'expect', 'range',
        'revenue guidance', 'eps guidance', 'full year', 'quarter guidance'
    ]
    guidance_mentions = sum(
        len(re.findall(rf'\b{term}\b', content, re.IGNORECASE))
        for term in guidance_terms
    )

    # Risk-related terms
    risk_terms = [
        'risk', 'challenge', 'headwind', 'uncertain', 'volatile',
        'concern', 'difficult', 'pressure', 'decline', 'weakness'
    ]
    risk_mentions = sum(
        len(re.findall(rf'\b{term}\b', content, re.IGNORECASE))
        for term in risk_terms
    )

    # Confidence indicators
    confidence_positive = [
        'strong', 'robust', 'solid', 'excellent', 'outstanding',
        'exceeded', 'beat', 'record', 'momentum', 'confident'
    ]
    confidence_negative = [
        'miss', 'below', 'disappointed', 'challenging', 'weak',
        'declined', 'fell short', 'struggled', 'difficult'
    ]

    pos_count = sum(
        len(re.findall(rf'\b{term}\b', content, re.IGNORECASE))
        for term in confidence_positive
    )
    neg_count = sum(
        len(re.findall(rf'\b{term}\b', content, re.IGNORECASE))
        for term in confidence_negative
    )

    total_sentiment = pos_count + neg_count
    confidence_score = 0.5 + (pos_count - neg_count) / max(total_sentiment * 2, 1) * 0.5
    confidence_score = np.clip(confidence_score, 0, 1)

    # Q&A section detection
    qa_markers = ['question', 'operator', 'analyst', 'q&a', 'questions and answers']
    qa_start = -1
    content_lower = content.lower()
    for marker in qa_markers:
        idx = content_lower.find(marker)
        if idx > len(content) * 0.3:  # Q&A should be in latter part
            qa_start = idx
            break

    if qa_start > 0:
        prepared_remarks = len(content[:qa_start].split())
        qa_section = len(content[qa_start:].split())
        q_and_a_ratio = qa_section / max(prepared_remarks, 1)
    else:
        q_and_a_ratio = 0

    # Key topics
    key_topics = {
        'revenue': len(re.findall(r'\brevenue\b', content, re.IGNORECASE)),
        'margin': len(re.findall(r'\bmargin\b', content, re.IGNORECASE)),
        'growth': len(re.findall(r'\bgrowth\b', content, re.IGNORECASE)),
        'innovation': len(re.findall(r'\b(innovation|r&d|research)\b', content, re.IGNORECASE)),
        'customers': len(re.findall(r'\bcustomer\w*\b', content, re.IGNORECASE)),
        'competition': len(re.findall(r'\b(compet\w+|market share)\b', content, re.IGNORECASE)),
        'capital_allocation': len(re.findall(r'\b(buyback|dividend|capex|investment)\b', content, re.IGNORECASE)),
    }

    # Overall transcript quality score (0-100)
    # Based on: length, forward-looking content, balance of guidance/risk, Q&A presence
    quality_factors = [
        min(1.0, word_count / 5000),  # Adequate length
        forward_looking_density,  # Forward-looking statements
        min(1.0, guidance_mentions / 10),  # Guidance provided
        1.0 - min(1.0, risk_mentions / 20) * 0.3,  # Not overly risk-focused
        min(1.0, q_and_a_ratio / 0.5),  # Has Q&A section
        confidence_score  # Management confidence
    ]
    transcript_quality_score = np.mean(quality_factors) * 100

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "forward_looking_density": round(forward_looking_density, 3),
        "guidance_mentions": guidance_mentions,
        "risk_mentions": risk_mentions,
        "confidence_score": round(confidence_score, 3),
        "q_and_a_ratio": round(q_and_a_ratio, 2),
        "key_topics": key_topics,
        "transcript_quality_score": round(transcript_quality_score, 1)
    }


def get_transcript_coverage_metrics(
    ticker: str,
    q_start: pd.Timestamp,
    q_end: pd.Timestamp,
    settings: Optional[Settings] = None
) -> Dict:
    """
    Get transcript-based coverage metrics for a quarter.

    Returns metrics that can be integrated into the Coverage dial.
    """
    s = settings or Settings.load()

    # Determine quarter and year from dates
    quarter = (q_end.month - 1) // 3 + 1
    year = q_end.year

    # Also check previous quarter (earnings call for Q3 happens in Q4)
    prev_quarter = quarter - 1 if quarter > 1 else 4
    prev_year = year if quarter > 1 else year - 1

    # Try to fetch transcript for the reporting quarter
    transcript = fetch_earnings_transcript(ticker, prev_quarter, prev_year, s)

    if not transcript.get("content"):
        # Try current quarter (in case timing is different)
        transcript = fetch_earnings_transcript(ticker, quarter, year, s)

    if not transcript.get("content"):
        return {
            "has_transcript": False,
            "transcript_quality_score": 0,
            "transcript_metrics": None
        }

    # Analyze the transcript
    analysis = analyze_transcript(transcript["content"])

    return {
        "has_transcript": True,
        "transcript_date": transcript.get("date", ""),
        "transcript_quality_score": analysis["transcript_quality_score"],
        "transcript_metrics": analysis
    }


def transcript_sentiment_score(
    ticker: str,
    quarter: int,
    year: int,
    settings: Optional[Settings] = None
) -> Dict:
    """
    Get sentiment score from earnings call transcript using FinBERT.

    This provides management tone analysis separate from news sentiment.
    """
    s = settings or Settings.load()

    transcript = fetch_earnings_transcript(ticker, quarter, year, s)

    if not transcript.get("content"):
        return {"sentiment": np.nan, "error": "No transcript"}

    # Try to use FinBERT for sentiment analysis
    try:
        from .finbert_sentiment import finbert_score

        content = transcript["content"]

        # Split into manageable chunks (FinBERT has token limits)
        # Take key sections: intro, guidance, Q&A samples
        sections = []

        # Get first 1000 words (executive summary)
        words = content.split()
        if len(words) > 500:
            sections.append(" ".join(words[:500]))

        # Get middle section (often contains guidance)
        mid_start = len(words) // 3
        if len(words) > mid_start + 500:
            sections.append(" ".join(words[mid_start:mid_start + 500]))

        # Get final section (Q&A conclusion)
        if len(words) > 500:
            sections.append(" ".join(words[-500:]))

        if sections:
            scores = finbert_score(sections)
            if scores:
                avg_sentiment = float(np.mean(scores))
                return {
                    "sentiment": avg_sentiment,
                    "sections_analyzed": len(sections),
                    "source": "finbert"
                }
    except Exception as e:
        log.warning(f"FinBERT analysis failed for {ticker} transcript: {e}")

    # Fallback to simple analysis
    analysis = analyze_transcript(transcript["content"])

    # Convert confidence score to sentiment-like scale (-1 to 1)
    sentiment = (analysis["confidence_score"] - 0.5) * 2

    return {
        "sentiment": sentiment,
        "source": "rule_based",
        "confidence_score": analysis["confidence_score"]
    }
