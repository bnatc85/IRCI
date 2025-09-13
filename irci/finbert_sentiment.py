
# irci/finbert_sentiment.py
from __future__ import annotations
from typing import List
import numpy as np

def _ensure_pipeline():
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    except Exception as e:
        raise RuntimeError("Transformers is required for FinBERT. pip install transformers torch") from e
    try:
        # Use widely adopted FinBERT tone model
        model_name = "yiyanghkust/finbert-tone"
        clf = pipeline("text-classification", model=model_name, tokenizer=model_name, return_all_scores=True, truncation=True)
        return clf
    except Exception as e:
        raise RuntimeError("Failed to load FinBERT model (yiyanghkust/finbert-tone).") from e

def finbert_tone_for_news(texts: List[str]) -> float:
    """
    Return a single tone score in [-1, 1] where higher = more positive.
    We compute mean( P(pos) - P(neg) ) across texts.
    """
    if not texts:
        return float("nan")
    clf = _ensure_pipeline()
    scores = []
    for t in texts:
        res = clf(t[:512])  # truncate long texts
        # res is list of dicts with label/prob
        lab2p = {d["label"].lower(): float(d["score"]) for d in res}
        pos = lab2p.get("positive", 0.0)
        neg = lab2p.get("negative", 0.0)
        scores.append(pos - neg)
    return float(np.nanmean(scores))
