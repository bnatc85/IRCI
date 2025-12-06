"""
IRCI Web Application
A user-friendly interface for running IRCI analysis on public companies.
Version: 2024.11.29-v2 - Media tone & domain fixes
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

# Add the repository root to Python path so we can import irci modules
# This works both locally and on Streamlit Cloud
repo_root = Path(__file__).parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Helper to load images as bytes for reliable cross-environment display
def load_image_bytes(filename: str) -> bytes:
    """Load image file as bytes from assets folder."""
    image_path = repo_root / "assets" / filename
    if image_path.exists():
        return image_path.read_bytes()
    return None

from irci.config import Settings
from irci.trust import trust_snapshot
from irci.valuation import valuation_snapshot
from irci.coverage import coverage_snapshot
from irci.liquidity import daily_liquidity_bundle, quarterly_liquidity, add_liquidity_percentile
from irci.market import fetch_prices_fmp
from irci.composite import irci_composite
from irci.media_fetchers.fmp_news import fmp_news_media_fetcher
from irci.media_fetchers.alpha_vantage_news import alpha_vantage_news_fetcher
from irci.media_fetchers.worldnews_api import worldnews_api_fetcher
from irci.media_fetchers.newsapi_fetcher import newsapi_fetcher
from irci.media_fetchers.finnhub_fetcher import finnhub_fetcher
from irci.peers import find_peers_simple, find_peers_optimized
from irci.quantum_budget import optimize_ir_budget, DWAVE_AVAILABLE as QUANTUM_BUDGET_AVAILABLE
from irci.playbook import generate_playbook
from irci.chatbot import chat_with_context, get_suggested_questions
from irci.yahoo_metrics import get_yahoo_metrics_batch
from irci.cache import cache_analysis_results, get_cached_analysis, clear_cache
from irci.email_sender import send_irci_report_email, get_email_config_status, validate_email
from irci.scheduler import save_schedule, load_schedules, delete_schedule
from irci.report_generator import generate_pdf_report
from irci.corporate_events_fetcher import fetch_corporate_events_for_peer_group
import numpy as np

def recalculate_composite_scores(df_composite, weights):
    """
    Recalculate irci_composite_pct in-place using new weights.
    weights: dict with keys 'valuation', 'liquidity', 'coverage', 'sentiment' (as decimals, e.g., 0.35)
    """
    dial_cols = ["valuation_pct", "liquidity_pct", "coverage_pct", "sentiment_pct"]
    W = np.array([
        weights.get("valuation", 0.0),
        weights.get("liquidity", 0.0),
        weights.get("coverage", 0.0),
        weights.get("sentiment", 0.0)
    ], dtype=float)

    X = df_composite[dial_cols].astype(float)
    mask = X.notna().astype(float).values
    num = (X.fillna(0.0).values * W).sum(axis=1)
    den = (mask * W).sum(axis=1)
    df_composite["irci_composite_pct"] = np.where(den > 0, num / den, np.nan)
    return df_composite

# Page config
st.set_page_config(
    page_title="IRCI Analysis",
    page_icon="IRCI_icon_primary.png",  # Use IRCI logo as favicon
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "IRCI Analysis Platform - Coverage, Trust, Liquidity & Valuation"
    }
)

# Custom CSS for dark mode
st.markdown("""
<style>
    /* Force scroll to top on load */
    html, body, [data-testid="stAppViewContainer"], section.main {
        scroll-behavior: auto !important;
    }

    /* Ensure dialogs/modals start at top */
    [data-testid="stModal"] > div,
    [role="dialog"] > div {
        scroll-behavior: auto !important;
    }

    /* Dark mode theme */
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }

    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #00d4ff;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
    }

    .sub-header {
        font-size: 1.2rem;
        color: #e0e0e0;
        margin-bottom: 2rem;
    }

    .metric-card {
        background-color: #1e2130;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border: 1px solid #2e3440;
    }

    .stAlert {
        margin-top: 1rem;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1e2130;
        font-size: 1.1rem;
    }

    [data-testid="stSidebar"] label {
        color: #fafafa !important;
        font-size: 1.1rem !important;
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: #e0e0e0 !important;
        font-size: 1.1rem !important;
    }

    [data-testid="stSidebar"] h3 {
        font-size: 1.4rem !important;
    }

    [data-testid="stSidebar"] p {
        font-size: 1.1rem !important;
    }

    [data-testid="stSidebar"] input {
        font-size: 1.05rem !important;
    }

    [data-testid="stSidebar"] textarea {
        font-size: 1.05rem !important;
    }

    [data-testid="stSidebar"] select {
        font-size: 1.05rem !important;
    }

    /* Text input styling */
    .stTextArea label, .stTextInput label, .stSelectbox label {
        color: #fafafa !important;
    }

    /* DataFrame styling - improved contrast */
    .dataframe {
        background-color: #1e2130 !important;
        color: #fafafa !important;
    }

    .dataframe th {
        background-color: #2e3440 !important;
        color: #00d4ff !important;
    }

    .dataframe td {
        color: #fafafa !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e2130;
    }

    .stTabs [data-baseweb="tab"] {
        color: #e0e0e0;
    }

    .stTabs [aria-selected="true"] {
        color: #00d4ff;
    }

    /* Metric cards */
    [data-testid="stMetricValue"] {
        color: #00d4ff !important;
    }

    [data-testid="stMetricLabel"] {
        color: #e0e0e0 !important;
    }

    /* Contact info styling */
    .contact-info {
        padding: 1rem;
        margin-top: 2rem;
        border-top: 1px solid #2e3440;
        font-size: 0.85rem;
        color: #b3b3b3;
    }

    .contact-info a {
        color: #00d4ff;
        text-decoration: none;
    }

    .contact-info a:hover {
        text-decoration: underline;
    }

    /* Info message styling - improved readability */
    .stInfo {
        background-color: #1e2130 !important;
        color: #fafafa !important;
        border-left-color: #00d4ff !important;
    }

    .stInfo p {
        color: #fafafa !important;
    }

    /* Expander header styling - improved readability */
    .streamlit-expanderHeader {
        background-color: #1e2130 !important;
        color: #e0e0e0 !important;
    }

    [data-testid="stExpander"] summary {
        background-color: #1e2130 !important;
        color: #e0e0e0 !important;
    }

    [data-testid="stExpander"] summary:hover {
        background-color: #2e3440 !important;
    }

    /* Sidebar expander styling - match button appearance */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        border: none !important;
        border-radius: 0.5rem !important;
        margin-bottom: 0.25rem !important;
    }

    [data-testid="stSidebar"] [data-testid="stExpander"] summary {
        background-color: #262730 !important;
        color: white !important;
        border-radius: 0.5rem !important;
        padding: 0.75rem 1rem !important;
        font-size: 1.4rem !important;
        font-weight: 400 !important;
        border: 1px solid rgba(250, 250, 250, 0.2) !important;
    }

    [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
        background-color: #00d4ff !important;
        color: #000000 !important;
        border-color: #00d4ff !important;
    }

    [data-testid="stSidebar"] [data-testid="stExpander"] summary span {
        color: inherit !important;
    }

    [data-testid="stSidebar"] [data-testid="stExpander"][open] summary {
        background-color: #00d4ff !important;
        color: #000000 !important;
        border-color: #00d4ff !important;
    }

    /* Mobile sidebar visibility - show indicator that sidebar exists */
    @media screen and (max-width: 768px) {
        /* Style ALL possible sidebar toggle buttons - Safari compatible */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"],
        button[kind="header"],
        .stApp header button,
        [data-testid="baseButton-header"],
        section[data-testid="stSidebar"] + div button:first-of-type {
            background-color: #00d4ff !important;
            background: #00d4ff !important;
            border-radius: 8px !important;
            -webkit-border-radius: 8px !important;
            box-shadow: 0 2px 15px rgba(0, 212, 255, 0.6) !important;
            -webkit-box-shadow: 0 2px 15px rgba(0, 212, 255, 0.6) !important;
            border: 2px solid #00d4ff !important;
            min-width: 48px !important;
            min-height: 48px !important;
            opacity: 1 !important;
            visibility: visible !important;
        }

        [data-testid="collapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] svg,
        button[kind="header"] svg,
        [data-testid="baseButton-header"] svg {
            color: #000000 !important;
            fill: #000000 !important;
            stroke: #000000 !important;
        }

        /* Pulsing animation - Safari compatible */
        @-webkit-keyframes pulse-sidebar {
            0%, 100% {
                -webkit-box-shadow: 0 2px 10px rgba(0, 212, 255, 0.5);
                box-shadow: 0 2px 10px rgba(0, 212, 255, 0.5);
                -webkit-transform: scale(1);
                transform: scale(1);
            }
            50% {
                -webkit-box-shadow: 0 2px 25px rgba(0, 212, 255, 1);
                box-shadow: 0 2px 25px rgba(0, 212, 255, 1);
                -webkit-transform: scale(1.1);
                transform: scale(1.1);
            }
        }
        @keyframes pulse-sidebar {
            0%, 100% {
                box-shadow: 0 2px 10px rgba(0, 212, 255, 0.5);
                transform: scale(1);
            }
            50% {
                box-shadow: 0 2px 25px rgba(0, 212, 255, 1);
                transform: scale(1.1);
            }
        }

        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"],
        button[kind="header"] {
            -webkit-animation: pulse-sidebar 1s ease-in-out 6;
            animation: pulse-sidebar 1s ease-in-out 6;
        }

        /* Ensure header is visible on mobile */
        header[data-testid="stHeader"] {
            background-color: #1e2130 !important;
            background: #1e2130 !important;
        }
    }

    /* Tablet and small desktop */
    @media screen and (max-width: 992px) and (min-width: 769px) {
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            background-color: #00d4ff !important;
            background: #00d4ff !important;
            border-radius: 8px !important;
            -webkit-border-radius: 8px !important;
        }

        [data-testid="collapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] svg {
            color: #000000 !important;
            fill: #000000 !important;
        }
    }

    /* Button styling - FIXED */
    .stButton button {
        background-color: #00d4ff;
        color: #000000 !important;
        border: none;
        font-weight: bold;
        font-size: 1.3rem;
    }

    .stButton button p {
        color: #000000 !important;
    }

    .stButton button span {
        color: #000000 !important;
    }

    .stButton button:hover {
        background-color: #00a8cc;
        color: #000000 !important;
    }

    /* Sidebar button text size */
    [data-testid="stSidebar"] .stButton button {
        font-size: 1.4rem !important;
    }

    /* Download button styling - FIXED */
    .stDownloadButton button {
        background-color: #00d4ff;
        color: #000000 !important;
        border: none;
        font-weight: bold;
        font-size: 1.3rem;
    }

    .stDownloadButton button p {
        color: #000000 !important;
    }

    .stDownloadButton button span {
        color: #000000 !important;
    }

    .stDownloadButton button:hover {
        background-color: #00a8cc;
        color: #000000 !important;
    }

    /* File uploader styling */
    [data-testid="stFileUploader"] button {
        background-color: #00d4ff !important;
        color: #000000 !important;
        border: 1px solid #00d4ff !important;
    }

    [data-testid="stFileUploader"] button:hover {
        background-color: #00a8cc !important;
        color: #000000 !important;
    }

    [data-testid="stFileUploader"] label {
        color: #fafafa !important;
    }

    /* Ensure main content area has dark background */
    [data-testid="stAppViewContainer"] {
        background-color: #0e1117 !important;
    }

    [data-testid="stHeader"] {
        background-color: #0e1117 !important;
    }

    /* Slider styling */
    .stSlider {
        color: #fafafa !important;
    }

    /* Text elements */
    p, li, span {
        color: #e0e0e0;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #00d4ff !important;
    }

    /* Multiselect chip/pill styling - black text for readability */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        color: #000000 !important;
    }

    [data-testid="stMultiSelect"] span[data-baseweb="tag"] span {
        color: #000000 !important;
    }

    /* Also target the close button in the tag */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] svg {
        fill: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# Scroll to top - runs once on page load (not modals)
import time
scroll_timestamp = int(time.time() * 1000)

components.html(
    f"""
    <!-- Unique ID to force re-render: {scroll_timestamp} -->
    <script>
        const scrollToTop = () => {{
            // Skip if a modal is open (don't interfere with modal scrolling)
            const modalOpen = window.parent.document.querySelector('[data-testid="stModal"]');
            if (modalOpen) return;

            // Reset all scrolled elements except those inside modals
            window.parent.document.querySelectorAll('*').forEach(el => {{
                if (el.scrollTop > 0 && !el.closest('[data-testid="stModal"]') && !el.closest('[role="dialog"]')) {{
                    el.scrollTop = 0;
                }}
            }});
        }};

        // Run once immediately, then once more after a short delay
        scrollToTop();
        setTimeout(scrollToTop, 150);
    </script>
    """,
    height=0
)

# Mobile sidebar indicator - JavaScript injection for reliable mobile menu hint
components.html(
    """
    <script>
        (function() {
            // Only run on mobile/tablet
            if (window.innerWidth > 768) return;

            // Check if indicator already exists
            if (window.parent.document.getElementById('mobile-menu-hint')) return;

            // Create floating menu indicator
            const hint = document.createElement('div');
            hint.id = 'mobile-menu-hint';
            hint.innerHTML = '☰ Menu';
            hint.style.cssText = `
                position: fixed;
                top: 12px;
                left: 12px;
                background: linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%);
                color: #000;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                z-index: 999999;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
                animation: bounce-hint 0.6s ease-in-out 3, fade-out 0.5s ease-out 4s forwards;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            `;

            // Add animations
            const style = document.createElement('style');
            style.textContent = `
                @keyframes bounce-hint {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                }
                @keyframes fade-out {
                    to { opacity: 0; visibility: hidden; }
                }
            `;
            window.parent.document.head.appendChild(style);

            // Click to open sidebar
            hint.onclick = function() {
                // Try to find and click the sidebar toggle button
                const toggleBtn = window.parent.document.querySelector('[data-testid="collapsedControl"]') ||
                                  window.parent.document.querySelector('[data-testid="stSidebarCollapsedControl"]') ||
                                  window.parent.document.querySelector('button[kind="header"]') ||
                                  window.parent.document.querySelector('header button');
                if (toggleBtn) toggleBtn.click();
                hint.style.display = 'none';
            };

            window.parent.document.body.appendChild(hint);

            // Auto-hide after 5 seconds
            setTimeout(() => {
                if (hint) hint.style.display = 'none';
            }, 5000);
        })();
    </script>
    """,
    height=0
)

# Header - IRCI Analysis Platform with 4 Dials (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .irci-header {
        max-width: 1100px;
        margin: 0 auto;
        background: linear-gradient(135deg, #0d1421 0%, #1a2435 50%, #0d1421 100%);
        border-radius: 16px;
        padding: 20px 28px 16px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), 0 0 80px rgba(59, 130, 246, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        margin-bottom: 0.75rem;
    }
    .header-top { text-align: center; margin-bottom: 16px; }
    .main-title-new {
        font-size: clamp(28px, 4vw, 40px);
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }
    .subtitle { font-size: 15px; color: #e2e8f0; font-weight: 400; letter-spacing: 0.02em; }
    .subtitle span { color: #ffffff; font-weight: 500; }
    .dials-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
    @media (max-width: 900px) { .dials-grid { grid-template-columns: repeat(2, 1fr); } .irci-header { padding: 20px; } }
    @media (max-width: 500px) { .dials-grid { grid-template-columns: 1fr; } }
    .dial-card {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 12px;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .dial-card::before {
        content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        border-radius: 16px 16px 0 0; opacity: 0; transition: opacity 0.3s ease;
    }
    .dial-card:hover { transform: translateY(-3px); border-color: rgba(255, 255, 255, 0.12); box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3); }
    .dial-card:hover::before { opacity: 1; }
    .dial-card.coverage::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .dial-card.trust::before { background: linear-gradient(90deg, #a855f7, #c084fc); }
    .dial-card.liquidity::before { background: linear-gradient(90deg, #06b6d4, #22d3ee); }
    .dial-card.valuation::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
    .dial-card:hover.coverage { box-shadow: 0 8px 30px rgba(59, 130, 246, 0.15); }
    .dial-card:hover.trust { box-shadow: 0 8px 30px rgba(168, 85, 247, 0.15); }
    .dial-card:hover.liquidity { box-shadow: 0 8px 30px rgba(6, 182, 212, 0.15); }
    .dial-card:hover.valuation { box-shadow: 0 8px 30px rgba(245, 158, 11, 0.15); }
    /* Animated Gauge - oscillating */
    .gauge-container { width: 60px; height: 60px; margin: 0 auto 8px; position: relative; }
    .gauge-bg { fill: none; stroke: rgba(255,255,255,0.1); stroke-width: 6; }
    .gauge-fill { fill: none; stroke-width: 6; stroke-linecap: round; transform: rotate(-90deg); transform-origin: center; }
    .coverage .gauge-fill { stroke: url(#coverage-gradient); animation: gauge-oscillate-1 4s ease-in-out infinite; }
    .trust .gauge-fill { stroke: url(#trust-gradient); animation: gauge-oscillate-2 4.5s ease-in-out infinite; }
    .liquidity .gauge-fill { stroke: url(#liquidity-gradient); animation: gauge-oscillate-3 5s ease-in-out infinite; }
    .valuation .gauge-fill { stroke: url(#valuation-gradient); animation: gauge-oscillate-4 4.2s ease-in-out infinite; }
    .gauge-text { display: none; }
    @keyframes gauge-oscillate-1 { 0%, 100% { stroke-dasharray: 94 157; } 50% { stroke-dasharray: 126 157; } }
    @keyframes gauge-oscillate-2 { 0%, 100% { stroke-dasharray: 78 157; } 50% { stroke-dasharray: 110 157; } }
    @keyframes gauge-oscillate-3 { 0%, 100% { stroke-dasharray: 86 157; } 50% { stroke-dasharray: 118 157; } }
    @keyframes gauge-oscillate-4 { 0%, 100% { stroke-dasharray: 70 157; } 50% { stroke-dasharray: 102 157; } }
    .dial-title { font-size: 14px; font-weight: 700; margin-bottom: 4px; letter-spacing: -0.01em; }
    .coverage .dial-title { color: #60a5fa; }
    .trust .dial-title { color: #c084fc; }
    .liquidity .dial-title { color: #22d3ee; }
    .valuation .dial-title { color: #fbbf24; }
    .dial-description { font-size: 11px; color: #e2e8f0; line-height: 1.4; }
    .tagline { text-align: center; margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.06); }
    .tagline-text { font-size: 13px; color: #e2e8f0; font-weight: 500; }
    .tagline-text strong { color: #d4af37; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Header - IRCI Analysis Platform with 4 Dials (HTML)
st.markdown("""
<svg width="0" height="0">
    <defs>
        <linearGradient id="coverage-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#3b82f6"/>
            <stop offset="100%" style="stop-color:#60a5fa"/>
        </linearGradient>
        <linearGradient id="trust-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#a855f7"/>
            <stop offset="100%" style="stop-color:#c084fc"/>
        </linearGradient>
        <linearGradient id="liquidity-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#06b6d4"/>
            <stop offset="100%" style="stop-color:#22d3ee"/>
        </linearGradient>
        <linearGradient id="valuation-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#f59e0b"/>
            <stop offset="100%" style="stop-color:#fbbf24"/>
        </linearGradient>
    </defs>
</svg>
<div class="irci-header">
    <div class="header-top">
        <h1 class="main-title-new">IRCI Analysis Platform</h1>
        <p class="subtitle">Quantify IR Excellence with <span>Coverage</span>, <span>Trust</span>, <span>Liquidity</span> & <span>Valuation</span></p>
    </div>
    <div class="dials-grid">
        <div class="dial-card coverage">
            <div class="gauge-container">
                <svg viewBox="0 0 60 60">
                    <circle class="gauge-bg" cx="30" cy="30" r="25"/>
                    <circle class="gauge-fill" cx="30" cy="30" r="25" stroke-dasharray="0 157"/>
                    <text class="gauge-text" x="30" y="30">80</text>
                </svg>
            </div>
            <h3 class="dial-title">Coverage</h3>
            <p class="dial-description">SEC filings & media visibility</p>
        </div>
        <div class="dial-card trust">
            <div class="gauge-container">
                <svg viewBox="0 0 60 60">
                    <circle class="gauge-bg" cx="30" cy="30" r="25"/>
                    <circle class="gauge-fill" cx="30" cy="30" r="25" stroke-dasharray="0 157"/>
                    <text class="gauge-text" x="30" y="30">70</text>
                </svg>
            </div>
            <h3 class="dial-title">Trust</h3>
            <p class="dial-description">Sentiment & event stability</p>
        </div>
        <div class="dial-card liquidity">
            <div class="gauge-container">
                <svg viewBox="0 0 60 60">
                    <circle class="gauge-bg" cx="30" cy="30" r="25"/>
                    <circle class="gauge-fill" cx="30" cy="30" r="25" stroke-dasharray="0 157"/>
                    <text class="gauge-text" x="30" y="30">75</text>
                </svg>
            </div>
            <h3 class="dial-title">Liquidity</h3>
            <p class="dial-description">Trading metrics vs peers</p>
        </div>
        <div class="dial-card valuation">
            <div class="gauge-container">
                <svg viewBox="0 0 60 60">
                    <circle class="gauge-bg" cx="30" cy="30" r="25"/>
                    <circle class="gauge-fill" cx="30" cy="30" r="25" stroke-dasharray="0 157"/>
                    <text class="gauge-text" x="30" y="30">65</text>
                </svg>
            </div>
            <h3 class="dial-title">Valuation</h3>
            <p class="dial-description">EV/EBITDA + PEG blended</p>
        </div>
    </div>
    <div class="tagline">
        <p class="tagline-text"><strong>Four dials.</strong> One score. <strong>Clear direction.</strong></p>
    </div>
</div>
""", unsafe_allow_html=True)

# Mobile menu hint - pure HTML/CSS (Safari compatible)
st.markdown("""
<style>
    @media screen and (max-width: 768px) {
        .mobile-menu-hint {
            display: block !important;
            position: fixed;
            top: 10px;
            left: 10px;
            background: linear-gradient(135deg, #00d4ff, #00a8cc);
            color: #000;
            padding: 10px 18px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: bold;
            z-index: 9999;
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.5);
            -webkit-animation: mobilePulse 1s ease-in-out 5, mobileFadeOut 0.5s ease-out 6s forwards;
            animation: mobilePulse 1s ease-in-out 5, mobileFadeOut 0.5s ease-out 6s forwards;
            pointer-events: none;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        @-webkit-keyframes mobilePulse {
            0%, 100% { -webkit-transform: scale(1); transform: scale(1); }
            50% { -webkit-transform: scale(1.05); transform: scale(1.05); }
        }
        @keyframes mobilePulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        @-webkit-keyframes mobileFadeOut {
            to { opacity: 0; visibility: hidden; }
        }
        @keyframes mobileFadeOut {
            to { opacity: 0; visibility: hidden; }
        }
    }
    @media screen and (min-width: 769px) {
        .mobile-menu-hint { display: none !important; }
    }
</style>
<div class="mobile-menu-hint">☰ Tap arrow for menu</div>
""", unsafe_allow_html=True)

# Access Code Gate
# Try to get access code from Streamlit secrets (for production)
# Fall back to hardcoded value for local development
try:
    ACCESS_CODE = st.secrets.get("ACCESS_CODE", "Melissa2019")
except:
    ACCESS_CODE = "Melissa2019"  # Fallback for local development

@st.dialog("🔐 Access Code Required", width="small")
def show_access_gate():
    st.markdown("""
    ### Welcome to IRCI

    This platform is currently in private beta. Please enter your access code to continue.
    """)

    access_code_input = st.text_input(
        "Access Code",
        type="password",
        placeholder="Enter your access code",
        help="Contact the IRCI team if you need an access code"
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Submit", use_container_width=True, type="primary"):
            if access_code_input == ACCESS_CODE:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("❌ Invalid access code. Please try again.")

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.stop()

# Initialize authentication state
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# Show access gate if not authenticated
if not st.session_state.get('authenticated', False):
    show_access_gate()
    st.stop()  # Stop execution if not authenticated

# Welcome Intro Modal
@st.dialog("Welcome to IRCI! 👋", width="large")
def show_intro_modal():
    # YouTube video embed with autoplay
    st.markdown("""
    ### 📹 Introduction to IRCI
    """)

    # YouTube video embed
    youtube_video_id = "Fyb1rqlCPuA"
    st.markdown(f"""
    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; background: #000;">
        <iframe
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
            src="https://www.youtube.com/embed/{youtube_video_id}?rel=0&modestbranding=1"
            frameborder="0"
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowfullscreen
            referrerpolicy="strict-origin-when-cross-origin">
        </iframe>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 2-Minute Tour content
    st.markdown("""
    ### Get Started in 3 Easy Steps:

    **1. Choose Your Peer Group** 👥
    - Use quick templates below OR manually select companies in the sidebar
    - Pick 2-5 similar companies for the best comparison

    **2. Select Time Period** 📅
    - Choose one or multiple quarters to analyze
    - Recent quarters (2024Q3+) have better news coverage data

    **3. Run Analysis** 🚀
    - Click the big "Run Analysis" button in the sidebar
    - Takes ~1-4 minutes depending on company count
    - Get instant IRCI scores, peer rankings, and actionable insights

    **💡 Tip:** Start with a quick template below to see IRCI in action!
    """)

    st.markdown("---")

    # Quick Start Templates
    st.markdown("### Quick Start Templates")
    st.caption("Click a template to pre-fill peer companies")

    # Center the icons with padding columns on either side
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("<div style='display: flex; flex-direction: column; align-items: center;'>", unsafe_allow_html=True)
            st.image("assets/tech-icon.jpg", width=80)
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("Select", key="modal_big_tech", use_container_width=True):
                st.session_state['found_peers'] = 'AAPL, MSFT, GOOGL, META, AMZN'
                st.session_state['show_intro'] = False
                st.rerun()
        with col2:
            st.markdown("<div style='display: flex; flex-direction: column; align-items: center;'>", unsafe_allow_html=True)
            st.image("assets/finance-icon.jpg", width=80)
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("Select", key="modal_financials", use_container_width=True):
                st.session_state['found_peers'] = 'JPM, BAC, WFC, GS, MS'
                st.session_state['show_intro'] = False
                st.rerun()
        with col3:
            st.markdown("<div style='display: flex; flex-direction: column; align-items: center;'>", unsafe_allow_html=True)
            st.image("assets/health-icon.jpg", width=80)
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("Select", key="modal_healthcare", use_container_width=True):
                st.session_state['found_peers'] = 'JNJ, PFE, UNH, ABBV, LLY'
                st.session_state['show_intro'] = False
                st.rerun()

    st.markdown("---")

    if st.button("🚀 Get Started", use_container_width=True, type="primary"):
        st.session_state['show_intro'] = False
        st.rerun()

# Legal Disclaimer Modal (shown when clicking "View full terms" link)
@st.dialog("📜 Legal Disclaimer - Full Terms")
def show_disclaimer_modal():
    st.markdown("""
**📊 Not Financial Advice** — IRCI is for informational and educational purposes only. It does not constitute financial, investment, or trading advice.

**⚠️ No Guarantees** — Past performance is not indicative of future results. IRCI scores may contain errors. No representation is made that any investment will achieve similar results.

**🔍 Do Your Own Research** — Conduct your own due diligence, consult a qualified financial advisor, and review official company filings before making investment decisions.

**📜 Limitation of Liability** — IRCI and its creators shall not be held liable for any losses or damages arising from use of this platform. Use is entirely at your own risk.

**🔒 Data Sources** — Analysis is based on publicly available information. We cannot guarantee completeness or timeliness of all data.

---
*By checking the disclaimer box and running analysis, you acknowledge that you have read, understood, and agree to these terms.*
    """)

    if st.button("✓ Close", use_container_width=True, type="primary"):
        st.session_state['show_disclaimer'] = False
        st.rerun()

# Initialize intro state (only show on very first visit after authentication)
# Initialize intro modal state - only show once per session after authentication
if 'intro_shown_once' not in st.session_state:
    st.session_state['intro_shown_once'] = False

if 'show_intro' not in st.session_state:
    st.session_state['show_intro'] = False

# Initialize disclaimer state
if 'disclaimer_accepted' not in st.session_state:
    st.session_state['disclaimer_accepted'] = False

if 'show_disclaimer' not in st.session_state:
    st.session_state['show_disclaimer'] = False

if 'run_analysis_confirmed' not in st.session_state:
    st.session_state['run_analysis_confirmed'] = False

# Auto-show intro on first authentication (only once)
if st.session_state.get('authenticated', False) and not st.session_state.get('intro_shown_once', False):
    st.session_state['show_intro'] = True
    st.session_state['intro_shown_once'] = True

# Show intro modal only if explicitly requested
if st.session_state.get('show_intro', False):
    show_intro_modal()
    # Reset show_intro after displaying - handles case where user closes via X or clicking outside
    st.session_state['show_intro'] = False

# Show disclaimer modal if requested (can be viewed anytime via "View terms" link)
if st.session_state.get('show_disclaimer', False):
    show_disclaimer_modal()
    # Reset show_disclaimer after displaying - handles case where user closes via X or clicking outside
    st.session_state['show_disclaimer'] = False

# Running ticker with IRCI questions and insights
ticker_items = [
    "What was the value of our IR and communications efforts last quarter?",
    "Drive critical decisions with trusted, data-backed insights.",
    "Is it worth it to travel and speak at a major conference?",
    "How does our specific IR efficiency compare to peers?",
    "If an advertising campaign costs $10M, is the return worth it?",
    "Are we getting coverage from credible sources or just press wires?",
    "Does the market stay calm or freak out when we announce news?",
    "How easy is it for investors to trade our stock?",
    "Which dial should we prioritize to maximize our company's IR impact?",
    "+1 IRCI point ≈ $XX Million for my company.",
    "If a CEO is forcibly removed, how does this affect value?",
    "What is the value of a social media brand campaign?",
    "Print quantifiable board-ready IRCI reports in minutes.",
    "IRCI is like a credit score for investor relations.",]

# Create the scrolling ticker HTML/CSS
ticker_text = " &nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp; ".join(ticker_items)
st.markdown(f"""
<style>
.ticker-wrap {{
    width: 100%;
    overflow: hidden;
    background: linear-gradient(90deg, #1a1a2e 0%, #16213e 50%, #1a1a2e 100%);
    padding: 8px 0;
    border-bottom: 1px solid #00CED1;
    margin-bottom: 1rem;
}}
.ticker {{
    display: inline-block;
    white-space: nowrap;
    animation: ticker 60s linear infinite;
    color: #00CED1;
    font-size: 0.9rem;
}}
.ticker:hover {{
    animation-play-state: paused;
}}
@keyframes ticker {{
    0% {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
}}
</style>
<div class="ticker-wrap">
    <div class="ticker">
        {ticker_text} &nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp; {ticker_text}
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Center the icon
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("IRCI_icon_primary.png", width=200)

    # Navigation at the top (only show after analysis is run)
    if st.session_state.get('df_composite') is not None:
        st.markdown("### 🧭 Navigation")

        # Initialize navigation state
        if 'selected_section' not in st.session_state:
            st.session_state['selected_section'] = "📊 Company Analysis"
        if 'selected_subsection' not in st.session_state:
            st.session_state['selected_subsection'] = "🎯 Playbook"

        # Helper to add indicator for active page
        def nav_label(label, is_active):
            return f"▶ {label}" if is_active else label

        current_section = st.session_state['selected_section']
        current_subsection = st.session_state.get('selected_subsection', '')

        # Main sections (buttons)
        is_active = current_section == "📊 Company Analysis"
        if st.button(nav_label("📊 Company Analysis", is_active), use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state['selected_section'] = "📊 Company Analysis"
            st.session_state['scroll_to_top'] = True
            st.rerun()

        # Trends section (only show if multi-quarter data)
        if st.session_state.get('is_multi_quarter', False):
            is_active = current_section == "📈 Trends"
            if st.button(nav_label("📈 Trends", is_active), use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state['selected_section'] = "📈 Trends"
                st.session_state['scroll_to_top'] = True
                st.rerun()

        is_active = current_section == "💵 Value Analysis"
        if st.button(nav_label("💵 Value Analysis", is_active), use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state['selected_section'] = "💵 Value Analysis"
            st.session_state['scroll_to_top'] = True
            st.rerun()

        # Playbook & Events with sub-sections
        is_section_active = current_section == "🎯 Playbook & Events"
        with st.expander("🎯 Playbook & Events", expanded=is_section_active):
            is_active = is_section_active and current_subsection == "🎯 Playbook"
            if st.button(nav_label("🎯 Playbook", is_active), use_container_width=True, type="primary" if is_active else "secondary", key="nav_playbook"):
                st.session_state['selected_section'] = "🎯 Playbook & Events"
                st.session_state['selected_subsection'] = "🎯 Playbook"
                st.session_state['scroll_to_top'] = True
                st.rerun()
            is_active = is_section_active and current_subsection == "📅 Event Timeline"
            if st.button(nav_label("📅 Event Timeline", is_active), use_container_width=True, type="primary" if is_active else "secondary", key="nav_events"):
                st.session_state['selected_section'] = "🎯 Playbook & Events"
                st.session_state['selected_subsection'] = "📅 Event Timeline"
                st.session_state['scroll_to_top'] = True
                st.rerun()
            is_active = is_section_active and current_subsection == "📋 Plan"
            if st.button(nav_label("📋 Plan", is_active), use_container_width=True, type="primary" if is_active else "secondary", key="nav_plan"):
                st.session_state['selected_section'] = "🎯 Playbook & Events"
                st.session_state['selected_subsection'] = "📋 Plan"
                st.session_state['scroll_to_top'] = True
                st.rerun()

        is_active = current_section == "💬 AI Assistant"
        if st.button(nav_label("💬 AI Assistant", is_active), use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state['selected_section'] = "💬 AI Assistant"
            st.session_state['scroll_to_top'] = True
            st.rerun()

        # Start Over link - clears analysis and returns to initial state
        if st.button("❌ Start Over 🔄", key="start_over_link", type="tertiary"):
            # Clear all analysis data
            for key in ['df_composite', 'df_trust', 'df_val', 'df_cov', 'df_liq', 'news_df',
                        'corporate_events_df', 'selected_section', 'selected_subsection',
                        'is_multi_quarter', 'run_time']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Select Companies")

    # Quick templates for common peer groups - icon buttons
    st.caption("Quick templates:")
    template_col1, template_col2, template_col3 = st.columns(3)
    with template_col1:
        st.image("assets/tech-icon.jpg", use_container_width=True)
        if st.button("Select", key="tmpl_tech", use_container_width=True):
            st.session_state['found_peers'] = "AAPL, MSFT, GOOGL, META, AMZN"
            st.rerun()
    with template_col2:
        st.image("assets/finance-icon.jpg", use_container_width=True)
        if st.button("Select", key="tmpl_fin", use_container_width=True):
            st.session_state['found_peers'] = "JPM, BAC, WFC, GS, MS"
            st.rerun()
    with template_col3:
        st.image("assets/health-icon.jpg", use_container_width=True)
        if st.button("Select", key="tmpl_health", use_container_width=True):
            st.session_state['found_peers'] = "JNJ, PFE, UNH, ABBV, LLY"
            st.rerun()

    # Peer finder expander
    with st.expander("🔍 Find Companies", expanded=False):
        st.caption("Enter a ticker to find peers in the same industry")

        finder_col1, finder_col2 = st.columns([2, 1])
        with finder_col1:
            peer_base_ticker = st.text_input(
                "Base Ticker",
                value="",
                placeholder="e.g., AAPL",
                help="Enter a ticker to find peers in the same industry",
                label_visibility="collapsed"
            )
        with finder_col2:
            peer_count = st.number_input("# Peers", 3, 15, 8, help="Number of peer companies to find")

        # Peer selection mode
        peer_mode = st.radio(
            "Selection Mode",
            ["⚡ Quick (Curated)", "🧠 Optimized (AI-Powered)"],
            horizontal=True,
            help="Quick uses curated peer lists. Optimized uses multi-dimensional analysis to find the best analytical peers."
        )

        # Show optimization settings for optimized mode
        if "Optimized" in peer_mode:
            with st.container():
                st.caption("**Optimization Weights** (adjust importance of each factor)")
                opt_col1, opt_col2 = st.columns(2)
                with opt_col1:
                    w_mcap = st.slider("Market Cap", 0.0, 1.0, 0.20, 0.05, help="Similarity in company size")
                    w_sector = st.slider("Sector Match", 0.0, 1.0, 0.25, 0.05, help="Same sector/industry")
                    w_analyst = st.slider("Analyst Coverage", 0.0, 1.0, 0.10, 0.05, help="Similar analyst attention")
                    w_liquidity = st.slider("Liquidity", 0.0, 1.0, 0.15, 0.05, help="Trading liquidity profile")
                with opt_col2:
                    w_volume = st.slider("Volume Pattern", 0.0, 1.0, 0.10, 0.05, help="Trading volume similarity")
                    w_inst = st.slider("Institutional %", 0.0, 1.0, 0.10, 0.05, help="Institutional ownership")
                    w_geo = st.slider("Geography", 0.0, 1.0, 0.05, 0.05, help="Geographic exposure")
                    w_corr = st.slider("Diversity Bonus", 0.0, 0.2, 0.05, 0.01, help="Penalize highly correlated peers for diversity")

        if st.button("🔍 Find Peers", use_container_width=True):
            if peer_base_ticker:
                try:
                    s = Settings.load()

                    if "Optimized" in peer_mode:
                        # Quantum-ready optimized peer selection
                        with st.spinner(f"🧠 Analyzing optimal peers for {peer_base_ticker.upper()}..."):
                            weights = {
                                'market_cap_log': w_mcap,
                                'sector_match': w_sector,
                                'analyst_coverage_ratio': w_analyst,
                                'liquidity_score': w_liquidity,
                                'trading_volume_pattern': w_volume,
                                'institutional_ownership': w_inst,
                                'geographic_exposure': w_geo,
                                'correlation_penalty': w_corr
                            }
                            result = find_peers_optimized(
                                ticker=peer_base_ticker.upper(),
                                api_key=s.fmp_api_key,
                                num_peers=peer_count,
                                weights=weights,
                                use_quantum=False  # Classical mode (D-Wave coming soon)
                            )

                            if result.get('selected_peers'):
                                all_tickers = [peer_base_ticker.upper()] + result['selected_peers']
                                st.session_state['found_peers'] = ", ".join(all_tickers)
                                st.session_state['peer_optimization_result'] = result

                                # Show optimization details
                                st.success(f"✓ Found {len(result['selected_peers'])} optimal peers using {result['method']}")

                                # Show peer details in a compact table
                                if result.get('peer_details'):
                                    peer_df = pd.DataFrame(result['peer_details'])
                                    if 'similarity_score' in peer_df.columns:
                                        peer_df['Similarity'] = (peer_df['similarity_score'] * 100).round(1).astype(str) + '%'
                                    if 'market_cap' in peer_df.columns:
                                        peer_df['Market Cap'] = (peer_df['market_cap'] / 1e9).round(1).astype(str) + 'B'
                                    display_cols = ['ticker', 'Similarity', 'Market Cap', 'sector']
                                    display_cols = [c for c in display_cols if c in peer_df.columns]
                                    st.dataframe(peer_df[display_cols].rename(columns={'ticker': 'Ticker', 'sector': 'Sector'}), hide_index=True)

                                st.rerun()
                            else:
                                st.warning(f"⚠️ Could not find optimized peers for {peer_base_ticker.upper()}")
                    else:
                        # Quick curated peer lookup
                        peers = find_peers_simple(peer_base_ticker.upper(), s.fmp_api_key, max_peers=peer_count)
                        if peers:
                            all_tickers = [peer_base_ticker.upper()] + peers
                            st.session_state['found_peers'] = ", ".join(all_tickers)
                            st.success(f"✓ Found {len(peers)} peers for {peer_base_ticker.upper()}")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ {peer_base_ticker.upper()} not in database. Try: AAPL, TSLA, NVDA, NFLX, JPM")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter a ticker")

    # Company selection text area
    default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    initial_value = st.session_state.get('found_peers', ", ".join(default_tickers))

    ticker_input = st.text_area(
        "Company Tickers",
        value=initial_value,
        help="Edit tickers directly: comma-separated (AAPL, MSFT) or one per line",
        height=80
    )

    # Parse tickers
    if "," in ticker_input:
        tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    else:
        tickers = [t.strip().upper() for t in ticker_input.split("\n") if t.strip()]

    # Compact ticker count display (only show warning if < 2)
    if len(tickers) < 2:
        st.caption(f"⚠️ Add more companies for peer comparison ({len(tickers)} selected)")
    else:
        st.caption(f"✓ {len(tickers)} companies selected")

    # Quarter selection - support multiple quarters for trend analysis
    quarters = ["2025Q4", "2025Q3", "2025Q2", "2025Q1", "2024Q4", "2024Q3", "2024Q2", "2024Q1"]
    selected_quarters = st.multiselect(
        "Select Quarter(s)",
        quarters,
        default=["2025Q3"],
        help="Select one or more quarters. Multiple quarters enable trend analysis and better statistical comparisons."
    )

    if not selected_quarters:
        st.warning("⚠️ Please select at least one quarter to analyze.")
        st.stop()

    # Convert quarter to dates helper function
    def quarter_to_dates(quarter_str):
        quarter_map = {
            "Q1": ("01-01", "03-31"),
            "Q2": ("04-01", "06-30"),
            "Q3": ("07-01", "09-30"),
            "Q4": ("10-01", "12-31")
        }
        year = quarter_str[:4]
        q = quarter_str[4:]
        start_date = f"{year}-{quarter_map[q][0]}"
        end_date = f"{year}-{quarter_map[q][1]}"
        return start_date, end_date

    # Show selected period(s)
    if len(selected_quarters) == 1:
        start_date, end_date = quarter_to_dates(selected_quarters[0])
        st.caption(f"📅 Period: {start_date} to {end_date}")
    else:
        st.caption(f"📅 Analyzing {len(selected_quarters)} quarters: {', '.join(selected_quarters)}")
        st.info(f"💡 **Trend Analysis Mode:** Results will show progression across {len(selected_quarters)} quarters with quarter-over-quarter comparisons.")

    # Run Analysis button - prominently placed after quarter selection
    st.markdown("---")

    # Disclaimer checkbox
    disclaimer_accepted = st.checkbox(
        "I have read and agree to the terms",
        value=st.session_state.get('disclaimer_accepted', False),
        key="disclaimer_checkbox_inline"
    )
    st.session_state['disclaimer_accepted'] = disclaimer_accepted

    # Simple "view terms" caption link
    if st.button("view terms", key="view_terms_link"):
        st.session_state['show_disclaimer'] = True
        st.rerun()

    # Caching option
    use_cache = st.checkbox(
        "Use cached results (faster)",
        value=True,
        help="Load results from cache if available (up to 24 hours old). Uncheck to force fresh analysis."
    )

    # Run Analysis button
    run_analysis_clicked = st.button(
        "🚀 Run Analysis",
        type="primary",
        use_container_width=True,
        disabled=not st.session_state.get('disclaimer_accepted', False),
        help="Start analyzing the selected companies for the chosen quarter" if st.session_state.get('disclaimer_accepted', False) else "Please accept the disclaimer first"
    )

    # Handle Run Analysis button click
    if run_analysis_clicked:
        st.session_state['run_analysis_confirmed'] = True

    # Determine if we should actually run the analysis
    run_analysis = st.session_state.get('run_analysis_confirmed', False)

    # Reset the confirmed flag after reading it
    if run_analysis:
        st.session_state['run_analysis_confirmed'] = False

    st.markdown("---")

    # Weights configuration
    with st.expander("⚙️ Advanced: Dial Weights", expanded=False):
        st.markdown("**Customize composite score weights:**")
        st.caption("Adjust how much each dial contributes to the overall IRCI score")

        # Default weights
        DEFAULT_WEIGHTS = {
            'valuation': 35.0,
            'liquidity': 35.0,
            'coverage': 15.0,
            'trust': 15.0
        }

        # Initialize weights in session state if not present
        if 'weight_liquidity' not in st.session_state:
            st.session_state.weight_liquidity = DEFAULT_WEIGHTS['liquidity']
        if 'weight_valuation' not in st.session_state:
            st.session_state.weight_valuation = DEFAULT_WEIGHTS['valuation']
        if 'weight_coverage' not in st.session_state:
            st.session_state.weight_coverage = DEFAULT_WEIGHTS['coverage']
        if 'weight_trust' not in st.session_state:
            st.session_state.weight_trust = DEFAULT_WEIGHTS['trust']

        # Use number inputs with BOTH value and key for proper state management
        # Note: Always cast value to float to avoid StreamlitMixedNumericTypesError
        col1, col2 = st.columns(2)
        with col1:
            weight_valuation = st.number_input(
                "💰 Valuation (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.weight_valuation),
                step=0.1,
                format="%.1f",
                help="How fairly priced is the stock vs peers? Based on EV/EBITDA ratios. Higher weight = valuation matters more to your score."
            )
            weight_coverage = st.number_input(
                "📰 Coverage (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.weight_coverage),
                step=0.1,
                format="%.1f",
                help="How much attention is the company getting? Based on SEC filings and media coverage. Higher weight = visibility matters more."
            )

        with col2:
            weight_liquidity = st.number_input(
                "💧 Liquidity (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.weight_liquidity),
                step=0.1,
                format="%.1f",
                help="How easy is it to trade the stock? Based on bid-ask spread and trading volume. Higher weight = trading ease matters more."
            )
            weight_trust = st.number_input(
                "💭 Trust (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.weight_trust),
                step=0.1,
                format="%.1f",
                help="How positive is market sentiment? Based on news sentiment and event stability. Higher weight = market perception matters more."
            )

        # Update session state with current widget values
        st.session_state.weight_valuation = weight_valuation
        st.session_state.weight_liquidity = weight_liquidity
        st.session_state.weight_coverage = weight_coverage
        st.session_state.weight_trust = weight_trust

        total_weight = weight_liquidity + weight_valuation + weight_coverage + weight_trust

        # Show total and warning if needed
        if abs(total_weight - 100.0) > 0.1:
            st.warning(f"⚠️ Weights sum to {total_weight:.1f}%. Will be normalized to 100%.")
        else:
            st.success(f"✓ Weights sum to {total_weight:.1f}%")

        # Reset button
        if st.button("🔄 Reset to Defaults", use_container_width=True, help="Reset weights to: Valuation 35%, Liquidity 35%, Coverage 15%, Trust 15%"):
            st.session_state.weight_valuation = DEFAULT_WEIGHTS['valuation']
            st.session_state.weight_liquidity = DEFAULT_WEIGHTS['liquidity']
            st.session_state.weight_coverage = DEFAULT_WEIGHTS['coverage']
            st.session_state.weight_trust = DEFAULT_WEIGHTS['trust']
            st.session_state.weights_auto_optimized = False  # Clear auto-optimization flag
            st.rerun()

        # Show auto-optimization status
        if st.session_state.get('weights_auto_optimized', False):
            st.caption("✓ Weights auto-optimized on last analysis")

    # News file upload
    with st.expander("📰 Advanced: News Data", expanded=False):
        st.info("News articles are automatically fetched from FMP API for sentiment analysis")
        uploaded_news = st.file_uploader(
            "Or upload custom News CSV (optional override)",
            type=["csv"],
            help="CSV with columns: date, ticker, headline. If provided, this will override automatic fetching."
        )

    # Save/Load session
    with st.expander("💾 Advanced: Save/Load Progress", expanded=False):
        # Save session
        if st.button("💾 Save Session", use_container_width=True, help="Save current analysis results to file"):
            if 'df_composite' in st.session_state:
                import pickle
                from datetime import datetime
    
                # Prepare session data
                session_data = {
                    'df_composite': st.session_state.get('df_composite'),
                    'df_trust': st.session_state.get('df_trust'),
                    'df_val': st.session_state.get('df_val'),
                    'df_cov': st.session_state.get('df_cov'),
                    'df_liq': st.session_state.get('df_liq'),
                    'news_df': st.session_state.get('news_df'),
                    'weight_liquidity': st.session_state.get('weight_liquidity'),
                    'weight_valuation': st.session_state.get('weight_valuation'),
                    'weight_coverage': st.session_state.get('weight_coverage'),
                    'weight_trust': st.session_state.get('weight_trust'),
                    'selected_quarters': st.session_state.get('selected_quarters', selected_quarters),
                    'tickers': tickers,
                    'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
    
                # Serialize to bytes
                session_bytes = pickle.dumps(session_data)
    
                # Create filename based on quarters analyzed
                quarters_str = "_".join(st.session_state.get('selected_quarters', selected_quarters)) if st.session_state.get('selected_quarters') else "multi"
    
                # Offer download
                st.download_button(
                    label="📥 Download Session File",
                    data=session_bytes,
                    file_name=f"irci_session_{quarters_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl",
                    mime="application/octet-stream",
                    use_container_width=True
                )
            else:
                st.warning("No analysis results to save. Run an analysis first!")
    
        # Load session - only show uploader if we don't have results yet
        # This prevents the uploader from blocking the view after loading
        if 'df_composite' not in st.session_state or st.session_state.get('df_composite') is None:
            uploaded_session = st.file_uploader(
                "📤 Load Previous Session",
                type=["pkl"],
                help="Upload a previously saved session file",
                key="session_uploader"
            )
    
            if uploaded_session is not None:
                try:
                    import pickle
                    session_data = pickle.load(uploaded_session)
    
                    # Restore session state
                    st.session_state['df_composite'] = session_data.get('df_composite')
                    st.session_state['df_trust'] = session_data.get('df_trust')
                    st.session_state['df_val'] = session_data.get('df_val')
                    st.session_state['df_cov'] = session_data.get('df_cov')
                    st.session_state['df_liq'] = session_data.get('df_liq')
                    st.session_state['news_df'] = session_data.get('news_df')
                    st.session_state['weight_liquidity'] = float(session_data.get('weight_liquidity', 35.0))
                    st.session_state['weight_valuation'] = float(session_data.get('weight_valuation', 35.0))
                    st.session_state['weight_coverage'] = float(session_data.get('weight_coverage', 15.0))
                    st.session_state['weight_trust'] = float(session_data.get('weight_trust', 15.0))
                    st.session_state['run_time'] = datetime.now()
    
                    # Verify data was loaded
                    if st.session_state['df_composite'] is not None:
                        num_companies = len(st.session_state['df_composite'])
                        st.success(f"✓ Session loaded! Saved on {session_data.get('saved_at', 'unknown date')}. Analysis for {num_companies} companies is ready.")
                        st.rerun()
                    else:
                        st.warning("⚠️ Session loaded but no analysis data found. The session file may be incomplete.")
    
                except Exception as e:
                    st.error(f"Failed to load session: {str(e)}")
        else:
            # Show info that session is already loaded with option to clear
            st.info("📊 Session data is loaded. Results are displayed!")
            if st.button("🔄 Clear Session (to load different file)", use_container_width=True):
                # Clear all analysis data
                for key in ['df_composite', 'df_trust', 'df_val', 'df_cov', 'df_liq', 'news_df']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    
        # Debug info (for troubleshooting)
        with st.expander("🔍 Session Debug Info"):
            st.write("**Session State Keys:**", list(st.session_state.keys()))
            if 'df_composite' in st.session_state:
                df_comp = st.session_state['df_composite']
                if df_comp is not None:
                    st.write(f"✓ df_composite exists: {len(df_comp)} rows")
                    st.write("Columns:", list(df_comp.columns))
                else:
                    st.write("❌ df_composite is None")
            else:
                st.write("❌ df_composite not in session_state")

    # Scheduled Reports
    with st.expander("📅 Scheduled Reports", expanded=False):
        st.markdown("**Set up recurring analysis reports**")

        # Show existing schedules
        schedules = load_schedules()
        if schedules:
            st.markdown("**Your Schedules:**")
            for name, sched in schedules.items():
                col1, col2 = st.columns([4, 1])
                with col1:
                    status = "🟢" if sched.get("enabled") else "⚫"
                    st.caption(f"{status} **{name}**: {', '.join(sched.get('tickers', [])[:3])}... → {sched.get('email', 'N/A')} ({sched.get('frequency', 'weekly')})")
                with col2:
                    if st.button("🗑️", key=f"del_{name}", help="Delete schedule"):
                        delete_schedule(name)
                        st.rerun()
            st.markdown("---")

        # Create new schedule
        st.markdown("**Create New Schedule:**")
        sched_name = st.text_input("Schedule name:", placeholder="My Weekly Report", key="sched_name")
        sched_email = st.text_input("Send to email:", placeholder="you@company.com", key="sched_email")
        sched_freq = st.selectbox("Frequency:", ["weekly", "daily", "monthly"], key="sched_freq")

        if st.button("📅 Save Schedule", use_container_width=True):
            if sched_name and sched_email and validate_email(sched_email):
                save_schedule(
                    name=sched_name,
                    tickers=tickers,
                    quarters=selected_quarters,
                    email=sched_email,
                    frequency=sched_freq
                )
                st.success(f"✅ Schedule '{sched_name}' saved!")
                st.caption("Note: Scheduled execution requires external automation (GitHub Actions, cron, etc.)")
                st.rerun()
            else:
                st.warning("Please enter a valid schedule name and email")

    # Welcome Tour button - at bottom of sidebar for discoverability
    if st.button("👋 Show Welcome Tour", use_container_width=True, help="New to IRCI? Watch a video intro and explore quick templates"):
        st.session_state['show_intro'] = True
        st.rerun()

    # Contact information (no extra spacing)
    st.markdown("""
    <div class="contact-info" style="margin-top: 0.5rem;">
        <strong>Contact:</strong><br>
        Bonnie Rushing<br>
        <a href="mailto:brushing@uccs.edu">brushing@uccs.edu</a><br>
        <a href="https://www.thebonnierushing.com" target="_blank">www.thebonnierushing.com</a>
    </div>
    """, unsafe_allow_html=True)


# Main content area - show results if they exist in session state
show_results = 'df_composite' in st.session_state

# Logic:
# 1. If run_analysis is clicked, we'll run analysis and update session state
# 2. If results exist in session state but run_analysis is not clicked, just skip to display
# 3. If no results and no run_analysis, show welcome screen

if not show_results and not run_analysis:
    # Welcome screen
    st.markdown("---")

    # Important disclaimers - collapsible for cleaner interface
    with st.expander("⚠️ **Important Disclaimers**", expanded=False):
        st.markdown("""
        - **Fundamentals set value. IR determines how efficiently markets realize it.** IRCI measures the pathway to fair value, not fundamental business performance.
        - IR's impact on share valuation is limited compared to business fundamentals, macroeconomic conditions, and industry trends.
        - IRCI is a planning and diagnostic tool—not a guarantee of market outcomes.
        - Dollar-per-point estimates are derived from historical peer relationships and should be treated as planning ranges, not promises.
        - This tool is for authorized use only. Views expressed are those of the creators and not official positions of any affiliated organization.
        """)

    # Show success message if analysis is already loaded
    if 'df_composite' in st.session_state and st.session_state['df_composite'] is not None:
        st.success("✓ Analysis loaded! Scroll down to view results or select a new peer group above to start fresh.")

    # Comprehensive About & Methodology - collapsed by default for cleaner interface
    with st.expander("📚 About IRCI", expanded=False):
        tabs = st.tabs(["📖 How It Works", "🎯 About IRCI", "💡 Why IRCI", "👥 Team", "🔬 Validation"])
    
        with tabs[0]:
            st.markdown("### How IRCI Works")

            # Vimeo video embed
            st.markdown("""
            <div style="padding: 56.25% 0 0 0; position: relative;">
                <iframe src="https://player.vimeo.com/video/1141717222?badge=0&autopause=0&player_id=0&app_id=58479"
                        frameborder="0"
                        allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media"
                        style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 8px;"
                        allowfullscreen>
                </iframe>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
**IRCI evaluates companies across four dials:**

| Dial | Question | Key Metrics |
|------|----------|-------------|
| 📰 **Coverage** | How visible is your company? | Media mentions (tier-weighted), SEC filing timeliness, disclosure momentum |
| 💭 **Trust** | Does the market stay calm when you speak? | Event-day volatility vs baseline, media sentiment (NLP) |
| 💧 **Liquidity** | How easy is it to trade? | Turnover, Amihud illiquidity, implied spread |
| 💰 **Valuation** | What multiple does the market pay? | EV/EBITDA, peer-relative position, trend stability |

**Framework:** Coverage, Trust, and Liquidity shape clarity and stability. Valuation reflects how efficiently the market prices your fundamentals.

**Output:** Composite score (0-100%) ranking companies within your peer group, with $/IRCI point estimates for planning.
            """)
    
        with tabs[1]:
            st.markdown("""
### About IRCI

**The Challenge:** IR's impact on value has always been considered unmeasurable—"nice to have" but not quantifiable.

**The Solution:** IRCI compresses 40+ years of academic research into one peer-relative score with dollar-per-point estimates and actionable playbooks.

| Feature | IRCI | Traditional Tools |
|---------|------|-------------------|
| Data source | Market data, SEC filings | Surveys, opinions |
| Dollar quantification | ✅ $/IRCI point | ❌ |
| Actionable playbooks | ✅ Dial-specific | General advice |

**Three Channels of IR Impact:**
1. **Liquidity** — Deeper trading, tighter spreads, cheaper access
2. **Coverage** — Better disclosure, faster information flow
3. **Trust** — Calmer event days, stock tracks closer to fair value

**Use Cases:**
- **IR Teams:** Identify weak dials → run playbook → re-measure
- **Boards/CFOs:** ROI calculation: "Is \\$Y worth spending to gain 2-3 IRCI points?"
- **Investors:** Spot IR/disclosure inefficiencies and potential mispricings
            """)

        with tabs[2]:
            st.markdown("""
### Why IRCI — Beyond the AI Hype

**"Will AI replace IR professionals?"** It's the question everyone's asking. Here's our answer:

---

#### What AI Can Do
- Draft press releases and earnings scripts
- Summarize filings and news
- Generate generic best practices
- Answer basic investor questions

#### What AI *Can't* Do
| Capability | Generic AI | IRCI |
|------------|-----------|------|
| Know your specific peer group | ❌ | ✅ Custom peer benchmarking |
| Calculate your $/IRCI point | ❌ | ✅ Regression on actual market data |
| Factor-adjust your event volatility | ❌ | ✅ Fama-French model integration |
| Track your progress over time | ❌ | ✅ Quarter-over-quarter comparison |
| Access real-time SEC EDGAR filings | ❌ | ✅ Live data pipeline |
| Benchmark against competitors | ❌ | ✅ Peer-relative percentiles |

---

#### The Real Value Proposition

**ChatGPT can write your press release. IRCI tells you if anyone's listening.**

IRCI doesn't replace IR professionals—it makes them *indispensable*:

1. **Quantification for the Board** — "Our Trust dial improved 4 points this quarter, worth ~$30M in enterprise value"
2. **Strategic Prioritization** — Know exactly which dial to fix first
3. **Measurable ROI** — Justify IR budgets with concrete numbers
4. **Competitive Intelligence** — See where peers are winning (and losing)

---

#### Our Philosophy

> *"We use AI for sentiment analysis. We don't use AI for strategy. The difference matters."*

IRCI is built on:
- **40+ years of peer-reviewed research** — Not training data scraped from the internet
- **Transparent methodology** — Every calculation is visible and auditable
- **Objective market data** — Prices, volumes, filings—not opinions
- **Human judgment where it matters** — The tool identifies problems; you solve them

---

#### The Bottom Line

The IR professional who uses IRCI will outperform the one who doesn't—not because AI replaced their judgment, but because they have *better data* to inform it.

**IRCI: The metrics AI can't guess. The insights your board actually needs.**
            """)

        with tabs[3]:
            st.markdown("### The Team")

            # Bonnie Rushing section with photo
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image("Bonnie pic.jpg", width=150)
            with col2:
                st.markdown("""
**Bonnie Rushing**
*PhD Scholar, College of Engineering and Applied Sciences, University of Colorado Colorado Springs*

- Master's Degree in Strategic Intelligence
- Military service in special operations and signals intelligence
- Former instructor of strategic studies at US Air Force Academy
- Trusted expert in social science research and data analytics
- **Core expertise:** Signal detection, data analytics, translating operational tradecraft into market analysis

*"From the aircraft to the boardroom, my job is the same: make sense of noise and enable decision-makers."*

📧 [brushing@uccs.edu](mailto:brushing@uccs.edu) | 🌐 [www.thebonnierushing.com](https://www.thebonnierushing.com)
                """)

            st.markdown("---")

            # Jim Wilkinson section with photo
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image("JimWilkinson.jpg", width=150)
            with col2:
                st.markdown("""
**Jim Wilkinson**
*Senior Advisor & Executive Chairman, TrailRunner International*

- Led global communications and corporate affairs at Alibaba and PepsiCo
- Senior government roles: Treasury, State Department, White House, USCENTCOM
- Trusted expert in corporate communications, crisis management, and public affairs
- **Core expertise:** Boardroom and global corporate communications strategy
                """)

            st.markdown("""
---

#### Our Approach

We combine:
- **Bonnie:** Signal detection and quantitative analysis from intelligence tradecraft
- **Jim:** Boardroom experience and strategic communications from Fortune 500 and government

**Result:** Measurable, repeatable, defensible IR through objective data and rigorous methodology.

---

#### Compliance & Disclaimers

- Views expressed are those of the creators, **not official positions of any affiliated organization** (including the US Department of Defense)
- Work is conducted on personal time and resources
- IRCI prioritizes compliance, transparency, and ethical use
- This tool is for authorized decision-making and planning—not market manipulation or insider advantage
            """)

        with tabs[4]:
            st.markdown("""
### Validation & Methodology

**Why Trust This Score:**

| Test | Result |
|------|--------|
| Track Record | 5+ years, tens of thousands of observations across market cycles ✅ |
| Directional Validation | Higher dial scores → expected outcomes next quarter ✅ |
| Ablation Testing | All 4 dials contribute unique signal; dropping any weakens predictions ✅ |
| Dollar Calibration | R² calculations appropriate for secondary factor after fundamentals ✅ |

**Primary Data Sources:** SEC EDGAR (filings, 13F institutional holdings), Financial Markets API (pricing/fundamentals, earnings transcripts), Fama-French factors (adjustments), NLP sentiment (media tone via FinBERT), social sentiment (Reddit/WSB, StockTwits), and news APIs.

**Limitations:** IRCI measures IR efficiency. It doesn't replace fundamentals, guarantee price movements, or account for black swan events. Use for planning and benchmarking, not trading.
            """)

            with st.expander("📚 Academic References"):
                st.markdown("""
**Core IR Research:**
- Bushee, B. J., & Miller, G. S. (2012). Investor relations, firm visibility, and investor following. *The Accounting Review, 87*(3), 867-897. [DOI](https://doi.org/10.2308/accr-10211)
- Agarwal, V., Liao, C., Nash, J., & Taffler, R. (2016). Investor relations, information asymmetry, and market value. *Accounting and Business Research, 46*(1), 31-50.
- Kirk, M., & Vincent, J. (2014). Professional investor relations within the firm. *The Accounting Review, 89*(4), 1421-1452. [DOI](https://doi.org/10.2308/accr-50724)
- National Investor Relations Institute (NIRI). (2019). Measuring the Value of IR: A Meta-Analysis.

**Investor Recognition & Cost of Capital:**
- Merton, R. C. (1987). A simple model of capital market equilibrium with incomplete information. *Journal of Finance, 42*(3), 483-510. [DOI](https://doi.org/10.1111/j.1540-6261.1987.tb04565.x)
- Jensen, M. C. (2005). Agency costs of overvalued equity. *Financial Management, 34*(1), 5-19. [DOI](https://doi.org/10.1111/j.1755-053X.2005.tb00090.x)
- Bodnaruk, A., & Ostberg, P. (2013). The shareholder base and payout policy. *Journal of Financial and Quantitative Analysis, 48*(3), 729-760.

**Event Studies & Corporate Actions:**
- Ball, R., & Brown, P. (1968). An empirical evaluation of accounting income numbers. *Journal of Accounting Research, 6*(2), 159-178. [JSTOR](https://www.jstor.org/stable/2490232)
- Bernard, V. L., & Thomas, J. K. (1989). Post-earnings-announcement drift: Delayed price response or risk premium? *Journal of Accounting Research, 27*, 1-36. [JSTOR](https://www.jstor.org/stable/2491062)
- Huson, M. R., Malatesta, P. H., & Parrino, R. (2004). Managerial succession and firm performance. *Journal of Financial Economics, 74*(2), 237-275. [DOI](https://doi.org/10.1016/j.jfineco.2003.08.002)
- Mian, S. (2001). On the choice and replacement of chief financial officers. *Journal of Financial Economics, 60*(1), 143-175. [DOI](https://doi.org/10.1016/S0304-405X(01)00042-3)
- Clayton, M. C., Hartzell, J. C., & Rosenberg, J. (2005). The impact of CEO turnover on equity volatility. *Journal of Business, 78*(5), 1779-1808.
- Michaely, R., Thaler, R. H., & Womack, K. L. (1995). Price reactions to dividend initiations and omissions. *Journal of Finance, 50*(2), 573-608. [DOI](https://doi.org/10.1111/j.1540-6261.1995.tb04796.x)
- Ikenberry, D., Lakonishok, J., & Vermaelen, T. (1995). Market underreaction to open market share repurchases. *Journal of Financial Economics, 39*(2-3), 181-208. [DOI](https://doi.org/10.1016/0304-405X(95)00826-Z)

**Media, Disclosure & Information Asymmetry:**
- Chen, H., De, P., Hu, Y., & Hwang, B. H. (2015). The role of the media in disseminating insider-trading news. *Review of Financial Studies, 28*(5), 1434-1463.
- Neuhierl, A., Scherbina, A., & Schlusche, B. (2013). Market reaction to corporate press releases. *Journal of Financial and Quantitative Analysis, 48*(4), 1207-1240.
- Grullon, G., Kanatas, G., & Weston, J. P. (2004). Advertising, breadth of ownership, and liquidity. *Review of Financial Studies, 17*(2), 439-461. [DOI](https://doi.org/10.1093/rfs/hhg039)
- Diamond, D. W., & Verrecchia, R. E. (1991). Disclosure, liquidity, and the cost of capital. *Journal of Finance, 46*(4), 1325-1359. [DOI](https://doi.org/10.1111/j.1540-6261.1991.tb04620.x)
- Healy, P. M., & Palepu, K. G. (2001). Information asymmetry, corporate disclosure, and the capital markets. *Journal of Accounting and Economics, 31*(1-3), 405-440. [DOI](https://doi.org/10.1016/S0165-4101(01)00018-0)
- Botosan, C. A. (1997). Disclosure level and the cost of equity capital. *The Accounting Review, 72*(3), 323-349. [JSTOR](https://www.jstor.org/stable/248475)

**Analyst Coverage & Institutional Investors:**
- Irvine, P. J. (2003). The incremental impact of analyst initiation of coverage. *Journal of Financial Economics, 68*(1), 169-202. [DOI](https://doi.org/10.1016/S0304-405X(03)00003-4)
- Bhushan, R. (1989). Firm characteristics and analyst following. *Journal of Accounting and Economics, 11*(2-3), 255-274. [DOI](https://doi.org/10.1016/0165-4101(89)90008-6)
- Francis, J., Hanna, J. D., & Philbrick, D. R. (1997). Management communications with securities analysts. *Journal of Accounting and Economics, 24*(3), 363-394. [DOI](https://doi.org/10.1016/S0165-4101(98)00013-2)
- Green, T. C., Jame, R., Markov, S., & Subasi, M. (2014). Access to management and the informativeness of analyst research. *Journal of Financial Economics, 114*(2), 239-255. [DOI](https://doi.org/10.1016/j.jfineco.2014.07.003)

**Liquidity & Trading:**
- Amihud, Y. (2002). Illiquidity and stock returns: Cross-section and time-series effects. *Journal of Financial Markets, 5*(1), 31-56. [DOI](https://doi.org/10.1016/S1386-4181(01)00024-6)
- Dittmar, A. K., & Field, L. C. (2015). Can managers time the market? Evidence using repurchase price data. *Journal of Financial Economics, 115*(2), 261-282. [DOI](https://doi.org/10.1016/j.jfineco.2014.09.007)
- Grullon, G., & Michaely, R. (2004). The information content of share repurchase programs. *Journal of Finance, 59*(2), 651-680. [DOI](https://doi.org/10.1111/j.1540-6261.2004.00645.x)
- Brown, S., Hillegeist, S. A., & Lo, K. (1999). Conference calls and information asymmetry. *Journal of Accounting and Economics, 37*(3), 343-366.

**Governance & Valuation:**
- Gompers, P., Ishii, J., & Metrick, A. (2003). Corporate governance and equity prices. *Quarterly Journal of Economics, 118*(1), 107-156. [DOI](https://doi.org/10.1162/00335530360535162)
- Brown, L. D., & Caylor, M. L. (2006). Corporate governance and firm valuation. *Journal of Accounting and Public Policy, 25*(4), 409-434. [DOI](https://doi.org/10.1016/j.jaccpubpol.2006.05.005)
- Greenwald, B. C., & Kahn, J. (2005). *Competition Demystified: A Radically Simplified Approach to Business Strategy*. Portfolio.

**Factor Models:**
- Fama, E. F., & French, K. R. (2015). A five-factor asset pricing model. *Journal of Financial Economics, 116*(1), 1-22. [DOI](https://doi.org/10.1016/j.jfineco.2014.10.010)

**Sentiment Analysis Tools:**
- FinBERT: Araci, D. (2019). FinBERT: Financial sentiment analysis with pre-trained language models. [arXiv](https://arxiv.org/abs/1908.10063)
- VADER: Hutto, C. J., & Gilbert, E. (2014). VADER: A parsimonious rule-based model for sentiment analysis of social media text. *ICWSM*.

**Social Media & Retail Sentiment:**
- Cookson, J. A., Engelberg, J., & Mullins, W. (2023). Echo chambers. *Review of Financial Studies, 36*(2), 450-500. [DOI](https://doi.org/10.1093/rfs/hhac058)
- Bartov, E., Faurel, L., & Mohanram, P. S. (2018). Can Twitter help predict firm-level earnings and stock returns? *The Accounting Review, 93*(3), 25-57. [DOI](https://doi.org/10.2308/accr-51865)
- Chen, H., De, P., Hu, Y., & Hwang, B. H. (2014). Wisdom of crowds: The value of stock opinions transmitted through social media. *Review of Financial Studies, 27*(5), 1367-1403. [DOI](https://doi.org/10.1093/rfs/hhu001)
- Antweiler, W., & Frank, M. Z. (2004). Is all that talk just noise? The information content of internet stock message boards. *Journal of Finance, 59*(3), 1259-1294. [DOI](https://doi.org/10.1111/j.1540-6261.2004.00662.x)
- Bradley, D., Hanousek Jr, J., Jame, R., & Xiao, Z. (2024). Place your bets? The value of investment research on Reddit's Wallstreetbets. *Review of Financial Studies, 37*(4), 1409-1459. [DOI](https://doi.org/10.1093/rfs/hhad019)

**Institutional Ownership & 13F Filings:**
- Bushee, B. J. (1998). The influence of institutional investors on myopic R&D investment behavior. *The Accounting Review, 73*(3), 305-333. [JSTOR](https://www.jstor.org/stable/248542)
- Gompers, P. A., & Metrick, A. (2001). Institutional investors and equity prices. *Quarterly Journal of Economics, 116*(1), 229-259. [DOI](https://doi.org/10.1162/003355301556392)
- Yan, X., & Zhang, Z. (2009). Institutional investors and equity returns: Are short-term institutions better informed? *Review of Financial Studies, 22*(2), 893-924. [DOI](https://doi.org/10.1093/rfs/hhn019)
- Agarwal, V., Jiang, W., Tang, Y., & Yang, B. (2013). Uncovering hedge fund skill from the portfolio holdings they hide. *Journal of Finance, 68*(2), 739-783. [DOI](https://doi.org/10.1111/jofi.12012)
- Ben-David, I., Franzoni, F., & Moussawi, R. (2012). Hedge fund stock trading in the financial crisis of 2007-2009. *Review of Financial Studies, 25*(1), 1-54. [DOI](https://doi.org/10.1093/rfs/hhr114)

**Earnings Call Transcripts & Management Tone:**
- Matsumoto, D., Pronk, M., & Roelofsen, E. (2011). What makes conference calls useful? The information content of managers' presentations and analysts' discussion sessions. *The Accounting Review, 86*(4), 1383-1414. [DOI](https://doi.org/10.2308/accr-10034)
- Hollander, S., Pronk, M., & Roelofsen, E. (2010). Does silence speak? An empirical analysis of disclosure choices during conference calls. *Journal of Accounting Research, 48*(3), 531-563. [DOI](https://doi.org/10.1111/j.1475-679X.2010.00365.x)
- Frankel, R., Johnson, M., & Skinner, D. J. (1999). An empirical examination of conference calls as a voluntary disclosure medium. *Journal of Accounting Research, 37*(1), 133-150. [DOI](https://doi.org/10.2307/2491400)
- Loughran, T., & McDonald, B. (2011). When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks. *Journal of Finance, 66*(1), 35-65. [DOI](https://doi.org/10.1111/j.1540-6261.2010.01625.x)
- Price, S. M., Doran, J. S., Peterson, D. R., & Bliss, B. A. (2012). Earnings conference calls and stock returns: The incremental informativeness of textual tone. *Journal of Banking & Finance, 36*(4), 992-1011. [DOI](https://doi.org/10.1016/j.jbankfin.2011.10.013)

**Industry Research:**
- MZ Group (2024). Investor Day Impact Analysis.
- Brunswick Group (2023). Social Media and Institutional Investors Survey.
- Edelman (2023). Trust Barometer: Institutional Investor Report.
                """)

elif run_analysis:
    # Clear the previous completion flag when starting new analysis
    st.session_state['analysis_just_completed'] = False

    # Run the analysis (only when button is clicked)
    st.markdown("---")
    if len(selected_quarters) == 1:
        spinner_text = "Running Analysis..."
    else:
        spinner_text = f"Running Analysis for {len(selected_quarters)} Quarters..."

    # Add animated spinner CSS and header
    st.markdown("""
    <style>
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .spinner {
        display: inline-block;
        width: 28px;
        height: 28px;
        border: 4px solid rgba(0, 212, 255, 0.3);
        border-top: 4px solid #00d4ff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        vertical-align: middle;
        margin-right: 12px;
    }
    .analysis-header {
        display: flex;
        align-items: center;
        font-size: 1.75em;
        font-weight: 600;
        margin: 0.5em 0;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="analysis-header"><div class="spinner"></div>{spinner_text}</div>', unsafe_allow_html=True)

    # Add analysis time estimate (very conservative)
    estimated_time = len(selected_quarters) * len(tickers) * 45  # ~45 seconds per ticker per quarter (very conservative)

    # Format time display
    if estimated_time >= 90:
        time_display = f"{estimated_time // 60} min {estimated_time % 60} sec"
    else:
        time_display = f"{estimated_time} seconds"

    st.caption(f"⏱️ Estimated time: ~{time_display} | Analyzing {len(tickers)} companies across {len(selected_quarters)} quarter(s)")

    # === WHILE YOU WAIT: AI vs IRCI Info Box ===
    with st.expander("📖 **While You Wait: Why IRCI in an AI World?**", expanded=True):
        st.markdown("""
<div style="font-size: 0.95em;">

**AI Chatbots vs. IRCI**

| Capability | AI Chatbots | IRCI |
|------------|-------------|------|
| Generate plausible text | ✅ | — |
| Know your specific peer group | ❌ | ✅ Custom peer benchmarking |
| Calculate your \$/IRCI point | ❌ | ✅ Regression on actual market data |
| **Quantify IR event ROI** | ❌ | ✅ **Academic-backed event impact values** |
| Factor-adjust event volatility | ❌ | ✅ Fama-French model integration |
| Track progress over time | ❌ | ✅ Quarter-over-quarter comparison |
| Access real-time SEC EDGAR filings | ❌ | ✅ Live data pipeline |
| Benchmark against competitors | ❌ | ✅ Peer-relative percentiles |
| Verify claims with sources | ❌ | ✅ Every metric auditable |

**Plan Your IR Activities with Confidence**

IRCI transforms guesswork into strategy:
- **Event Simulator**: Model the impact of investor days, earnings calls, analyst coverage before you commit budget
- **Academic-Backed Values**: Event impacts draw from peer-reviewed research
- **Dollar Translation**: See exactly how much value each IR initiative could add in your company's terms
- **Prioritized Recommendations**: Data-driven playbook tells you where to focus for maximum ROI

**The Bottom Line**

AI can write your press release. It can't tell you how readers reacted, whether it moved your stock, or how you truly compare to competitors. IRCI answers those questions with data, not guesses—and helps you **plan what to do next**.

*Your expertise + IRCI's measurement = Defensible, repeatable IR strategy*

</div>
        """, unsafe_allow_html=True)

    # Store results for all quarters
    all_quarters_results = {}

    # Loop through each selected quarter
    for quarter_idx, selected_quarter in enumerate(selected_quarters):
        # Get start/end dates for this quarter
        start_date, end_date = quarter_to_dates(selected_quarter)

        # Progress tracking
        if len(selected_quarters) > 1:
            st.markdown(f"### 📊 Quarter {quarter_idx + 1}/{len(selected_quarters)}: **{selected_quarter}** ({start_date} to {end_date})")

        # Enhanced progress tracking
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0, text="🚀 Initializing analysis...")
            status_text = st.empty()
            ticker_progress = st.empty()  # Shows per-ticker progress

        try:
            # Check cache first if enabled
            if use_cache:
                cached_results = get_cached_analysis(tickers, selected_quarter, max_age_hours=24)
                if cached_results:
                    st.success(f"⚡ Loaded {selected_quarter} from cache (instant!)")
                    all_quarters_results[selected_quarter] = {
                        'df_composite': cached_results.get('df_composite', pd.DataFrame()),
                        'df_trust': cached_results.get('df_trust', pd.DataFrame()),
                        'df_val': cached_results.get('df_val', pd.DataFrame()),
                        'df_cov': cached_results.get('df_cov', pd.DataFrame()),
                        'df_liq': cached_results.get('df_liq', pd.DataFrame()),
                        'news_df': cached_results.get('news_df'),
                        'corporate_events_df': cached_results.get('corporate_events_df'),
                        'start_date': start_date,
                        'end_date': end_date
                    }
                    continue  # Skip to next quarter

            # Load settings
            s = Settings.load()

            # Prepare news data - automatically fetch from FMP API
            news_df = None
            if uploaded_news is not None:
                # User uploaded news file
                news_df = pd.read_csv(uploaded_news)
                news_df = news_df[(news_df['date'] >= start_date) & (news_df['date'] <= end_date)]
                st.success(f"✓ Loaded {len(news_df)} news articles from upload for {selected_quarter}")
            else:
                # Automatically fetch news for all tickers using API (FMP → World News → Alpha Vantage fallback)
                status_text.text(f"Fetching news articles for {selected_quarter}...")
                news_list = []
                news_counts = {}
                news_sources_used = {}  # Track which source was used for each ticker
                q_start = pd.to_datetime(start_date, utc=True)
                q_end = pd.to_datetime(end_date, utc=True)

            # Track errors for display
            news_errors = {}

            for ticker_idx, ticker in enumerate(tickers):
                ticker_got_news = False
                ticker_errors = []

                # Show per-ticker progress
                ticker_progress.markdown(f"**News:** `{ticker}` ({ticker_idx + 1}/{len(tickers)})")

                try:
                    # Try FMP first
                    status_text.text(f"Fetching news for {ticker} from FMP...")
                    ticker_news = fmp_news_media_fetcher(ticker, q_start, q_end, s)
                    if not ticker_news.empty:
                        ticker_news['ticker'] = ticker
                        news_list.append(ticker_news)
                        news_counts[ticker] = len(ticker_news)
                        news_sources_used[ticker] = "FMP"
                        ticker_got_news = True
                        print(f"✓ FMP returned {len(ticker_news)} articles for {ticker}")
                    else:
                        ticker_errors.append("FMP: No articles found")
                except Exception as e:
                    error_msg = f"FMP: {str(e)}"
                    ticker_errors.append(error_msg)
                    print(f"FMP news fetch failed for {ticker}: {e}")

                # If FMP failed or returned no results, try World News API
                if not ticker_got_news:
                    try:
                        status_text.text(f"Fetching news for {ticker} from World News API...")
                        ticker_news = worldnews_api_fetcher(ticker, q_start, q_end, s)
                        if not ticker_news.empty:
                            ticker_news['ticker'] = ticker
                            news_list.append(ticker_news)
                            news_counts[ticker] = len(ticker_news)
                            news_sources_used[ticker] = "World News API"
                            ticker_got_news = True
                            print(f"✓ World News API returned {len(ticker_news)} articles for {ticker}")
                        else:
                            ticker_errors.append("World News API: No articles found")
                    except Exception as e:
                        error_msg = f"World News API: {str(e)}"
                        ticker_errors.append(error_msg)
                        print(f"World News API fetch failed for {ticker}: {e}")

                # If both FMP and World News failed, try Alpha Vantage
                if not ticker_got_news:
                    try:
                        status_text.text(f"Fetching news for {ticker} from Alpha Vantage...")
                        ticker_news = alpha_vantage_news_fetcher(ticker, q_start, q_end, s)
                        if not ticker_news.empty:
                            ticker_news['ticker'] = ticker
                            news_list.append(ticker_news)
                            news_counts[ticker] = len(ticker_news)
                            news_sources_used[ticker] = "Alpha Vantage"
                            ticker_got_news = True
                            print(f"✓ Alpha Vantage returned {len(ticker_news)} articles for {ticker}")
                        else:
                            ticker_errors.append("Alpha Vantage: No articles found")
                    except Exception as e:
                        error_msg = f"Alpha Vantage: {str(e)}"
                        ticker_errors.append(error_msg)
                        print(f"Alpha Vantage news fetch failed for {ticker}: {e}")

                # If FMP, World News, and Alpha Vantage failed, try NewsAPI.org
                if not ticker_got_news:
                    try:
                        status_text.text(f"Fetching news for {ticker} from NewsAPI.org...")
                        ticker_news = newsapi_fetcher(ticker, q_start, q_end, s)
                        if not ticker_news.empty:
                            ticker_news['ticker'] = ticker
                            news_list.append(ticker_news)
                            news_counts[ticker] = len(ticker_news)
                            news_sources_used[ticker] = "NewsAPI.org"
                            ticker_got_news = True
                            print(f"✓ NewsAPI.org returned {len(ticker_news)} articles for {ticker}")
                        else:
                            ticker_errors.append("NewsAPI.org: No articles found")
                    except Exception as e:
                        error_msg = f"NewsAPI.org: {str(e)}"
                        ticker_errors.append(error_msg)
                        print(f"NewsAPI.org news fetch failed for {ticker}: {e}")

                # If all previous sources failed, try Finnhub.io
                if not ticker_got_news:
                    try:
                        status_text.text(f"Fetching news for {ticker} from Finnhub.io...")
                        ticker_news = finnhub_fetcher(ticker, q_start, q_end, s)
                        if not ticker_news.empty:
                            ticker_news['ticker'] = ticker
                            news_list.append(ticker_news)
                            news_counts[ticker] = len(ticker_news)
                            news_sources_used[ticker] = "Finnhub.io"
                            ticker_got_news = True
                            print(f"✓ Finnhub.io returned {len(ticker_news)} articles for {ticker}")
                        else:
                            ticker_errors.append("Finnhub.io: No articles found")
                    except Exception as e:
                        error_msg = f"Finnhub.io: {str(e)}"
                        ticker_errors.append(error_msg)
                        print(f"Finnhub.io news fetch failed for {ticker}: {e}")

                if not ticker_got_news:
                    news_counts[ticker] = 0
                    news_errors[ticker] = ticker_errors
                    print(f"No news found for {ticker} in period {start_date} to {end_date}")

            if news_list:
                news_df = pd.concat(news_list, ignore_index=True)

                # Add sentiment scores to each article using FinBERT or VADER
                status_text.text("Analyzing sentiment for news articles...")
                headlines = news_df['headline'].fillna('').astype(str).tolist()
                sentiment_scores = []
                sentiment_method = "None"

                # Filter out empty headlines for analysis
                valid_headlines = [h.strip() for h in headlines if h.strip()]
                print(f"Analyzing sentiment for {len(valid_headlines)} non-empty headlines out of {len(headlines)} total")

                # Try FinBERT first
                try:
                    from irci.trust import finbert_score
                    fb_scores = finbert_score(valid_headlines) if valid_headlines else None
                    if fb_scores and len(fb_scores) == len(valid_headlines):
                        # Map scores back to original headlines (empty = 0.0)
                        score_iter = iter(fb_scores)
                        sentiment_scores = [next(score_iter) if h.strip() else 0.0 for h in headlines]
                        sentiment_method = "FinBERT"
                        print(f"✓ FinBERT scored {len(fb_scores)} headlines")
                except Exception as e:
                    print(f"FinBERT failed: {e}")
                    sentiment_scores = []

                # Fallback to VADER if FinBERT didn't work
                if not sentiment_scores or sentiment_method == "None":
                    try:
                        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                        sia = SentimentIntensityAnalyzer()
                        sentiment_scores = [sia.polarity_scores(h)["compound"] for h in headlines]
                        sentiment_method = "VADER"
                        print(f"✓ VADER scored {len(sentiment_scores)} headlines")
                    except Exception as e:
                        print(f"VADER also failed: {e}")
                        sentiment_scores = [0.0] * len(headlines)
                        sentiment_method = "None (fallback to 0)"

                news_df['sentiment_score'] = sentiment_scores

                # Add sentiment label
                news_df['sentiment'] = news_df['sentiment_score'].apply(
                    lambda x: 'positive' if x > 0.1 else ('negative' if x < -0.1 else 'neutral')
                )

                print(f"✓ Sentiment analysis complete using {sentiment_method}")

                success_tickers = [t for t, c in news_counts.items() if c > 0]
                failed_tickers = [t for t, c in news_counts.items() if c == 0]

                # Determine which sources were used
                sources_used = list(set(news_sources_used.values()))
                sources_str = ", ".join(sources_used) if sources_used else "API"

                msg = f"✓ Fetched {len(news_df)} articles from {sources_str}"
                if success_tickers:
                    # Show each ticker with count and source
                    ticker_details = [f'{t} ({news_counts[t]} from {news_sources_used.get(t, "API")})' for t in success_tickers]
                    msg += f"\n   Success: {', '.join(ticker_details)}"
                st.success(msg)

                # Show detailed errors for failed tickers
                if failed_tickers and news_errors:
                    error_msg = "⚠️ **Failed to fetch news for some tickers:**\n\n"
                    for ticker in failed_tickers:
                        if ticker in news_errors:
                            error_msg += f"**{ticker}:** Tried all sources\n"
                            for err in news_errors[ticker]:
                                error_msg += f"  - {err}\n"
                    st.warning(error_msg)
            else:
                st.warning("⚠️ No news articles found for any ticker in this date range. Try a more recent quarter (2024Q4 or 2025Q1) for news data.")

            # Convert end_date to timezone-naive datetime for consistency
            quarter_end_dt = pd.to_datetime(end_date)
            if hasattr(quarter_end_dt, 'tz_localize'):
                quarter_end_dt = quarter_end_dt.tz_localize(None)
            elif quarter_end_dt.tz is not None:
                quarter_end_dt = quarter_end_dt.tz_localize(None)

            # Clear ticker progress from news phase
            ticker_progress.empty()

            # 1. Trust
            progress_bar.progress(10, text="💭 Step 1/5: Trust dial (sentiment & event stability)")
            status_text.text(f"Computing trust scores for {len(tickers)} companies...")
            df_trust = trust_snapshot(
                tickers,
                start=start_date,
                end=end_date,
                news_df=news_df,
                apikey=s.fmp_api_key,
                s=s
            )

            # Debug: Show media tone calculation results
            if not df_trust.empty:
                for _, row in df_trust.iterrows():
                    ticker = row.get('ticker', 'Unknown')
                    media_tone_n = row.get('media_tone_n', 0)
                    media_tone_raw = row.get('media_tone_raw', None)
                    media_tone_src = row.get('media_tone_src', 'None')
                    p_media_tone = row.get('p_media_tone', None)
                    print(f"[TRUST DEBUG] {ticker}: media_tone_n={media_tone_n}, media_tone_raw={media_tone_raw}, src={media_tone_src}, p_media_tone={p_media_tone}")

            if not df_trust.empty:
                if "quarter_end" not in df_trust.columns:
                    df_trust["quarter_end"] = quarter_end_dt
                # Force timezone-naive by normalizing to date
                df_trust["quarter_end"] = pd.to_datetime(pd.to_datetime(df_trust["quarter_end"]).dt.date)
            progress_bar.progress(30, text="✓ Trust complete")

            # 2. Valuation
            progress_bar.progress(35, text="💰 Step 2/5: Valuation dial (EV/EBITDA + PEG blended)")
            status_text.text(f"Computing valuation metrics for {len(tickers)} companies...")
            df_val = valuation_snapshot(
                tickers,
                as_of=end_date
            )
            if not df_val.empty:
                if "quarter_end" not in df_val.columns:
                    df_val["quarter_end"] = quarter_end_dt
                # Force timezone-naive by normalizing to date
                df_val["quarter_end"] = pd.to_datetime(pd.to_datetime(df_val["quarter_end"]).dt.date)
            progress_bar.progress(50, text="✓ Valuation complete")

            # 3. Coverage
            progress_bar.progress(55, text="📰 Step 3/5: Coverage dial (SEC filings & media)")
            status_text.text(f"Analyzing coverage metrics for {len(tickers)} companies...")
            df_cov = coverage_snapshot(
                tickers,
                as_of=end_date,
                media_fetcher=fmp_news_media_fetcher
            )
            if not df_cov.empty:
                if "quarter_end" not in df_cov.columns:
                    df_cov["quarter_end"] = quarter_end_dt
                # Force timezone-naive by normalizing to date
                df_cov["quarter_end"] = pd.to_datetime(pd.to_datetime(df_cov["quarter_end"]).dt.date)
            progress_bar.progress(70, text="✓ Coverage complete")

            # 4. Liquidity
            progress_bar.progress(75, text="💧 Step 4/5: Liquidity dial (market microstructure)")
            status_text.text(f"Computing liquidity metrics for {len(tickers)} companies...")
            rows = []
            for sym_idx, sym in enumerate(tickers):
                ticker_progress.markdown(f"**Liquidity:** `{sym}` ({sym_idx + 1}/{len(tickers)})")
                try:
                    prices = fetch_prices_fmp(sym, start_date, end_date, s.fmp_api_key)
                    daily = daily_liquidity_bundle(sym, s, prices, end_date)
                    q = quarterly_liquidity(daily, freq="QE-DEC").reset_index()
                    if "quarter_end" not in q.columns:
                        q = q.rename(columns={"Date": "quarter_end", "date": "quarter_end", "index": "quarter_end"})
                    q["ticker"] = sym
                    rows.append(q)
                except Exception as e:
                    st.warning(f"⚠️ Liquidity data unavailable for {sym}: {str(e)}")
            df_liq = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
            if not df_liq.empty:
                # Force timezone-naive by normalizing to date
                if "quarter_end" in df_liq.columns:
                    df_liq["quarter_end"] = pd.to_datetime(pd.to_datetime(df_liq["quarter_end"]).dt.date)
                df_liq = add_liquidity_percentile(df_liq)
            ticker_progress.empty()  # Clear ticker progress
            progress_bar.progress(80, text="✓ Liquidity complete")

            # 4b. Yahoo Finance metrics (analyst coverage, short interest)
            progress_bar.progress(82, text="📊 Fetching analyst coverage & short interest...")
            status_text.text(f"Fetching Yahoo Finance metrics for {len(tickers)} companies...")
            try:
                df_yahoo = get_yahoo_metrics_batch(tickers)
                if not df_yahoo.empty:
                    # Merge analyst coverage into Coverage dataframe
                    if not df_cov.empty:
                        yahoo_cov_cols = ['ticker', 'analyst_count', 'analyst_coverage_score',
                                         'target_mean', 'price_target_upside_pct', 'recommendation']
                        df_cov = df_cov.merge(
                            df_yahoo[yahoo_cov_cols],
                            on='ticker',
                            how='left'
                        )
                    # Merge short interest into Trust dataframe
                    if not df_trust.empty:
                        yahoo_trust_cols = ['ticker', 'short_pct_float', 'short_ratio',
                                           'short_change_pct', 'short_interest_score',
                                           'recommendation_score']
                        df_trust = df_trust.merge(
                            df_yahoo[yahoo_trust_cols],
                            on='ticker',
                            how='left'
                        )
                    st.success(f"✓ Yahoo Finance: analyst coverage & short interest data loaded")
            except Exception as e:
                print(f"Warning: Could not fetch Yahoo metrics: {e}")
                st.warning(f"⚠️ Yahoo metrics unavailable: {e}")
            progress_bar.progress(85, text="✓ Yahoo metrics complete")

            # 5. Composite
            progress_bar.progress(90, text="🎯 Step 5/5: Computing IRCI composite scores")
            status_text.text(f"Combining all dials into final IRCI scores...")

            # Final timezone normalization - ensure ALL quarter_end columns are timezone-naive
            def strip_timezone(df):
                if df is not None and not df.empty and "quarter_end" in df.columns:
                    # Convert to naive datetime by going through numpy datetime64
                    df = df.copy()
                    df["quarter_end"] = df["quarter_end"].values.astype('datetime64[ns]')
                return df

            df_val = strip_timezone(df_val)
            df_liq = strip_timezone(df_liq)
            df_cov = strip_timezone(df_cov)
            df_trust = strip_timezone(df_trust)

            df_composite = irci_composite(
                valuation=df_val,
                liquidity=df_liq,
                coverage=df_cov,
                sentiment=df_trust,
                weights={
                    'liquidity': weight_liquidity / 100,
                    'valuation': weight_valuation / 100,
                    'coverage': weight_coverage / 100,
                    'sentiment': weight_trust / 100
                }
            )
            progress_bar.progress(95, text="📅 Fetching corporate events (earnings, dividends, etc.)...")
            status_text.text(f"Fetching corporate events for {len(tickers)} companies...")

            # Fetch corporate events (earnings calls, dividends, buybacks, CEO/CFO changes, etc.)
            corporate_events_df = None
            try:
                corporate_events_df = fetch_corporate_events_for_peer_group(
                    tickers, start_date, end_date, s
                )
                if corporate_events_df is not None and not corporate_events_df.empty:
                    corporate_events_df['quarter'] = selected_quarter
                    event_counts = corporate_events_df['event_type'].value_counts().to_dict()
                    event_summary = ", ".join([f"{v} {k.replace('_', ' ')}" for k, v in event_counts.items()])
                    st.success(f"✓ Found {len(corporate_events_df)} corporate events: {event_summary}")
                else:
                    st.info("No corporate events found for this period")
            except Exception as e:
                print(f"Warning: Could not fetch corporate events: {e}")
                st.warning(f"Could not fetch corporate events: {e}")

            progress_bar.progress(100, text="🎉 Analysis complete!")
            status_text.text(f"✅ Successfully analyzed {len(tickers)} companies for {selected_quarter}")

            # Store results for this quarter
            all_quarters_results[selected_quarter] = {
                'df_composite': df_composite,
                'df_trust': df_trust,
                'df_val': df_val,
                'df_cov': df_cov,
                'df_liq': df_liq,
                'news_df': news_df,
                'corporate_events_df': corporate_events_df,
                'start_date': start_date,
                'end_date': end_date
            }

            # Save to cache for future use
            try:
                cache_analysis_results(
                    tickers,
                    selected_quarter,
                    {
                        'df_composite': df_composite,
                        'df_trust': df_trust,
                        'df_val': df_val,
                        'df_cov': df_cov,
                        'df_liq': df_liq
                    }
                )
            except Exception as cache_err:
                print(f"Warning: Could not cache results: {cache_err}")

            # Also store as previous quarter data for future QoQ comparisons
            prev_quarter_key = f'df_composite_prev_{selected_quarter}'
            st.session_state[prev_quarter_key] = df_composite.copy()

        except Exception as e:
            st.error(f"❌ Error running analysis for {selected_quarter}: {str(e)}")
            st.exception(e)
            # Continue with next quarter instead of stopping
            continue

    # After all quarters are processed, store in session state
    if all_quarters_results:
        # For single quarter, use standard storage
        if len(selected_quarters) == 1:
            quarter = selected_quarters[0]
            st.session_state['df_composite'] = all_quarters_results[quarter]['df_composite']
            st.session_state['df_trust'] = all_quarters_results[quarter]['df_trust']
            st.session_state['df_val'] = all_quarters_results[quarter]['df_val']
            st.session_state['df_cov'] = all_quarters_results[quarter]['df_cov']
            st.session_state['df_liq'] = all_quarters_results[quarter]['df_liq']
            st.session_state['news_df'] = all_quarters_results[quarter]['news_df']
            st.session_state['corporate_events_df'] = all_quarters_results[quarter].get('corporate_events_df')
            st.session_state['run_time'] = datetime.now()
            st.session_state['is_multi_quarter'] = False  # Single quarter - no Trends tab
        else:
            # For multiple quarters, combine all data with quarter labels
            combined_composite = []
            combined_trust = []
            combined_val = []
            combined_cov = []
            combined_liq = []
            combined_news = []
            combined_corporate_events = []

            for quarter, results in all_quarters_results.items():
                # Add quarter column to each dataframe
                for df_name in ['df_composite', 'df_trust', 'df_val', 'df_cov', 'df_liq']:
                    if results[df_name] is not None:
                        df = results[df_name].copy()
                        df['quarter'] = quarter
                        if df_name == 'df_composite':
                            combined_composite.append(df)
                        elif df_name == 'df_trust':
                            combined_trust.append(df)
                        elif df_name == 'df_val':
                            combined_val.append(df)
                        elif df_name == 'df_cov':
                            combined_cov.append(df)
                        elif df_name == 'df_liq':
                            combined_liq.append(df)

                # News data
                if results['news_df'] is not None:
                    news_df = results['news_df'].copy()
                    news_df['quarter'] = quarter
                    combined_news.append(news_df)

                # Corporate events data
                if results.get('corporate_events_df') is not None:
                    corp_events = results['corporate_events_df'].copy()
                    if 'quarter' not in corp_events.columns:
                        corp_events['quarter'] = quarter
                    combined_corporate_events.append(corp_events)

            # Concatenate all quarters
            st.session_state['df_composite'] = pd.concat(combined_composite, ignore_index=True) if combined_composite else None
            st.session_state['df_trust'] = pd.concat(combined_trust, ignore_index=True) if combined_trust else None
            st.session_state['df_val'] = pd.concat(combined_val, ignore_index=True) if combined_val else None
            st.session_state['df_cov'] = pd.concat(combined_cov, ignore_index=True) if combined_cov else None
            st.session_state['df_liq'] = pd.concat(combined_liq, ignore_index=True) if combined_liq else None
            st.session_state['news_df'] = pd.concat(combined_news, ignore_index=True) if combined_news else None
            st.session_state['corporate_events_df'] = pd.concat(combined_corporate_events, ignore_index=True) if combined_corporate_events else None
            st.session_state['run_time'] = datetime.now()
            st.session_state['selected_quarters'] = selected_quarters  # Store list of quarters analyzed
            st.session_state['is_multi_quarter'] = True  # Flag for navigation to show Trends tab

        # Success notification - professional toast instead of animation
        st.toast("Analysis Complete!", icon="✅")

        # Store analysis completion info for navigation display
        st.session_state['analysis_just_completed'] = True
        st.session_state['analysis_summary'] = f"🎉 **Analysis Complete!** Successfully analyzed **{len(tickers)} companies** across **{len(all_quarters_results)} quarter(s)**"

        # Auto-optimize weights based on peer group variance
        try:
            from irci.dial_insights import recommend_optimal_weights

            df_composite_for_opt = st.session_state['df_composite']
            df_val_for_opt = st.session_state.get('df_val')

            if df_composite_for_opt is not None and not df_composite_for_opt.empty:
                # For multi-quarter, use the most recent quarter for optimization
                if 'quarter' in df_composite_for_opt.columns:
                    latest_quarter = sorted(df_composite_for_opt['quarter'].unique())[-1]
                    df_for_opt = df_composite_for_opt[df_composite_for_opt['quarter'] == latest_quarter].copy()
                else:
                    df_for_opt = df_composite_for_opt.copy()

                # Merge enterprise_value from valuation data for R² optimization
                if df_val_for_opt is not None and not df_val_for_opt.empty:
                    if 'enterprise_value' in df_val_for_opt.columns and 'enterprise_value' not in df_for_opt.columns:
                        ev_cols = ['ticker', 'enterprise_value']
                        if 'quarter' in df_val_for_opt.columns and 'quarter' in df_for_opt.columns:
                            ev_cols.append('quarter')
                            ev_data = df_val_for_opt[ev_cols].drop_duplicates()
                            df_for_opt = df_for_opt.merge(ev_data, on=['ticker', 'quarter'], how='left')
                        else:
                            ev_data = df_val_for_opt[['ticker', 'enterprise_value']].drop_duplicates()
                            df_for_opt = df_for_opt.merge(ev_data, on='ticker', how='left')

                # Get current weights for optimization context
                current_weights = {
                    'valuation': weight_valuation / 100,
                    'liquidity': weight_liquidity / 100,
                    'coverage': weight_coverage / 100,
                    'sentiment': weight_trust / 100
                }

                # Run optimization
                weight_analysis = recommend_optimal_weights(df_for_opt, current_weights=current_weights)
                rec_weights = weight_analysis.get('recommended_weights', {})

                if rec_weights:
                    # Apply optimized weights to session state (use float for st.number_input compatibility)
                    st.session_state['weight_valuation'] = float(round(rec_weights.get('valuation', 0.35) * 100, 1))
                    st.session_state['weight_liquidity'] = float(round(rec_weights.get('liquidity', 0.35) * 100, 1))
                    st.session_state['weight_coverage'] = float(round(rec_weights.get('coverage', 0.15) * 100, 1))
                    st.session_state['weight_trust'] = float(round(rec_weights.get('sentiment', 0.15) * 100, 1))

                    # Mark that weights were auto-optimized
                    st.session_state['weights_auto_optimized'] = True
                    st.session_state['optimization_r2'] = weight_analysis.get('optimized_r2', 0) or 0

                    # Update analysis summary to mention optimization
                    r2_val = weight_analysis.get('optimized_r2', 0) or 0
                    st.session_state['analysis_summary'] += f" Weights auto-optimized."
        except Exception as e:
            # Don't fail analysis if optimization fails - just log it
            print(f"Auto-optimization warning: {e}")

        # Force page refresh to ensure navigation and results are displayed properly
        st.rerun()
    else:
        st.error("❌ No quarters were successfully analyzed.")
        st.stop()

# Display results (if available) or show preview
if 'df_composite' in st.session_state and st.session_state['df_composite'] is not None:
    st.markdown("---")

    # Show success message and navigation if analysis just completed
    if st.session_state.get('analysis_just_completed', False):
        st.success(st.session_state.get('analysis_summary', '🎉 **Analysis Complete!**'))

        st.markdown("---")

    st.markdown("## 📊 Analysis Results")
else:
    # Show results structure preview before analysis
    st.markdown("---")
    st.markdown("## 📋 What's Included")
    st.caption("Run an analysis to see these sections populated with your peer group data")

    with st.expander("📊 **Company Analysis** - Peer rankings and score breakdowns", expanded=True):
        st.markdown("""
        - **🏆 Composite Ranking** - See how companies stack up against peers
        - **📊 Composite Scores** - Visual bar chart comparison
        - **📉 Dial Breakdown** - Radar chart showing each company's strengths/weaknesses
        - **📋 Detailed Metrics** - Deep dive into Valuation, Liquidity, Coverage, and Trust scores
        """)

    with st.expander("📈 **Trends** - Multi-quarter analysis (when multiple quarters selected)"):
        st.markdown("""
        - **Quarter-over-Quarter Changes** - Track score improvements or declines
        - **Individual Dial Trends** - See how each metric evolves over time
        - **Forecasting** - Statistical predictions for future scores
        """)

    with st.expander("💵 **Value Analysis** - Dollar impact estimates"):
        st.markdown("""
        - **$/IRCI Point** - Estimate value of each IRCI point improvement
        - **Dial Contribution** - Which dials drive the most value
        - **Gap Analysis** - Potential value from closing gaps to top performers
        """)

    with st.expander("🎯 **Playbook & Events** - Action recommendations"):
        st.markdown("""
        - **🎯 Playbook** - Prioritized actions to improve your weakest dials
        - **📅 Event Timeline** - Calendar of relevant IR events
        - **📋 Plan** - What-if scenario planning for IR initiatives
        """)

    with st.expander("💬 **AI Assistant** - Ask questions about your results"):
        st.markdown("""
        - Get explanations of your scores
        - Ask for specific recommendations
        - Understand methodology and calculations
        """)

    with st.expander("🔮 **Quantum-Ready Peer Selection** (Coming Soon!)"):
        st.markdown("""
        ### Multi-Dimensional Optimal Peer Selection

        Our peer selection uses **QUBO (Quadratic Unconstrained Binary Optimization)** — the same
        mathematical formulation that runs on D-Wave quantum computers.

        #### How It Works

        **Step 1: Fetch Multi-Dimensional Features**

        For each candidate peer, we collect:
        | Dimension | Source | Why It Matters |
        |-----------|--------|----------------|
        | Market Cap | Yahoo Finance | Similar-sized companies face similar IR challenges |
        | Sector/Industry | Company profile | Same-sector peers have comparable metrics |
        | Analyst Coverage | Financial APIs | Similar visibility = better benchmarking |
        | Liquidity Profile | Trading data | Comparable trading characteristics |
        | Volume Patterns | 3-month history | Similar investor attention |
        | Institutional % | 13F filings | Similar ownership structures |
        | Return Correlation | 60-day returns | For diversity optimization |

        **Step 2: Compute Similarity Scores**

        Each candidate gets a weighted similarity score vs your target:
        ```
        Similarity[i] = Σ (weight[d] × score[d])
        ```

        **Step 3: Build QUBO Matrix**

        The optimization problem becomes:
        ```
        MINIMIZE: E(x) = Σᵢ (-similarity[i])·xᵢ + Σᵢⱼ (correlation[i,j]·penalty)·xᵢ·xⱼ

        Where:
          • xᵢ ∈ {0,1} = include stock i in peer set?
          • Linear terms = maximize similarity to target
          • Quadratic terms = penalize correlated pairs (ensure diversity)

        CONSTRAINT: Select exactly N peers
        ```

        **Step 4: Solve**

        | Method | How It Works | Best For |
        |--------|--------------|----------|
        | **Greedy** | Pick best remaining stock iteratively | Quick approximation |
        | **Simulated Annealing** | Random swaps with cooling schedule (10K iterations) | Near-optimal solution |
        | **Exhaustive** | Check all combinations | Small pools (≤20) |
        | **Quantum** ⚡ | D-Wave quantum annealing | Large pools, guaranteed optimal |

        ---

        #### Why Quantum Computing?

        **Classical Limitation:** Checking all combinations of 10 peers from 500 candidates =
        **2.6 × 10²⁰ possibilities** — impossible to solve exactly.

        **Quantum Advantage:**

        | Problem Size | Classical (Sim. Annealing) | Quantum (D-Wave) |
        |--------------|---------------------------|------------------|
        | 25 candidates | ~50ms | ~100ms |
        | 100 candidates | ~200ms | ~100ms |
        | 500 candidates | ~2 seconds | ~100ms |
        | S&P 500 | May not converge | ~100ms |

        **How Quantum Works:**
        - **Superposition**: Evaluates ALL solutions simultaneously
        - **Quantum Tunneling**: Escapes local minima that trap classical solvers
        - **Guaranteed Optimal**: Finds true global minimum, not just "good enough"

        ---

        #### Academic References

        The QUBO formulation for portfolio optimization is well-established in quantum computing research:

        1. **Venturelli et al. (2019)** - "Reverse quantum annealing approach to portfolio optimization"
           — *Quantum Science and Technology* — [arXiv:1810.08584](https://arxiv.org/abs/1810.08584)

        2. **Mugel et al. (2022)** - "Dynamic portfolio optimization with real datasets using quantum processors"
           — *Physical Review Research* — [arXiv:2007.00017](https://arxiv.org/abs/2007.00017)

        3. **Grant et al. (2021)** - "Benchmarking quantum annealing for portfolio optimization"
           — *Quantum Machine Intelligence* — [DOI:10.1007/s42484-021-00052-w](https://doi.org/10.1007/s42484-021-00052-w)

        4. **D-Wave Systems** - "Portfolio Optimization of 60 Stocks Using Classical and Quantum Algorithms"
           — [arXiv:2008.08669](https://arxiv.org/abs/2008.08669)

        ---

        #### Try It Now (Classical Mode)

        In the sidebar under **🔍 Find Companies**, select **🧠 Optimized (AI-Powered)** to use
        multi-dimensional peer selection with simulated annealing. Quantum mode will be enabled
        when D-Wave Leap API integration is complete.

        **Configurable Weights:**
        - Market Cap Similarity (default: 20%)
        - Sector Match (default: 25%)
        - Analyst Coverage (default: 10%)
        - Liquidity Profile (default: 15%)
        - Volume Pattern (default: 10%)
        - Institutional Ownership (default: 10%)
        - Geography (default: 5%)
        - Diversity Bonus (default: 5%)
        """)

    st.info("**Get Started:** Select companies and quarters in the sidebar, then click **🚀 Run Analysis**")

# Continue with results display
if 'df_composite' in st.session_state and st.session_state['df_composite'] is not None:

    # Disclaimer banner for results
    st.info("""
    💡 **Remember:** These scores measure IR efficiency and market accessibility—not business fundamentals.
    Dollar estimates are planning ranges based on peer relationships, not guarantees.
    Focus on identifying the weakest dial and taking targeted action.
    """)

    # Show auto-optimization status if weights were optimized
    if st.session_state.get('weights_auto_optimized', False):
        r2 = st.session_state.get('optimization_r2', 0)
        st.caption(f"✓ Weights auto-optimized based on peer group variance")

    try:
        df_composite = st.session_state['df_composite']
        df_trust = st.session_state['df_trust']
        df_val = st.session_state['df_val']
        df_cov = st.session_state['df_cov']
        df_liq = st.session_state['df_liq']

        # Check if dataframes are empty
        if df_composite.empty:
            st.error("❌ Loaded session contains empty analysis data. Please run a new analysis.")
            st.stop()

        # Top metrics - handle single or multiple quarters
        quarters_analyzed = st.session_state.get('selected_quarters', [])
        run_time = st.session_state['run_time']
        if 'quarter' in df_composite.columns:
            # Multi-quarter data
            unique_quarters = df_composite['quarter'].unique()
            num_companies = len(df_composite[df_composite['quarter'] == unique_quarters[0]])
            st.markdown(f"### Quarters: {', '.join(unique_quarters)} | Companies: {num_companies}")
            st.caption(f"📅 Data as of: {run_time.strftime('%b %d, %Y at %I:%M %p')} • Market data from Yahoo Finance, SEC EDGAR, news APIs")
        else:
            # Single quarter data - try to get quarter from session state, or derive from data
            if quarters_analyzed:
                quarter_str = quarters_analyzed[0]
            elif 'as_of' in df_val.columns and not df_val['as_of'].empty:
                # Derive quarter from as_of date in valuation data
                as_of_date = pd.to_datetime(df_val['as_of'].iloc[0])
                year = as_of_date.year
                quarter = f"Q{(as_of_date.month - 1) // 3 + 1}"
                quarter_str = f"{year}{quarter}"
            else:
                quarter_str = "N/A"
            st.markdown(f"### Quarter: {quarter_str} | Companies: {len(df_composite)}")
            st.caption(f"📅 Data as of: {run_time.strftime('%b %d, %Y at %I:%M %p')} • Market data from Yahoo Finance, SEC EDGAR, news APIs")

        # Data Quality Indicator
        def check_data_quality(df_comp, df_v, df_l, df_c, df_t):
            """Check for missing data across all dials."""
            issues = []
            tickers = df_comp['ticker'].unique() if 'ticker' in df_comp.columns else []

            for ticker in tickers:
                ticker_issues = []
                # Check valuation
                if 'ticker' in df_v.columns:
                    val_row = df_v[df_v['ticker'] == ticker]
                    if val_row.empty or val_row['valuation_pct'].isna().all():
                        ticker_issues.append('Valuation')
                # Check liquidity
                if 'ticker' in df_l.columns:
                    liq_row = df_l[df_l['ticker'] == ticker]
                    if liq_row.empty or liq_row['liquidity_pct'].isna().all():
                        ticker_issues.append('Liquidity')
                # Check coverage
                if 'ticker' in df_c.columns:
                    cov_row = df_c[df_c['ticker'] == ticker]
                    if cov_row.empty or cov_row['coverage_pct'].isna().all():
                        ticker_issues.append('Coverage')
                # Check trust
                if 'ticker' in df_t.columns:
                    trust_row = df_t[df_t['ticker'] == ticker]
                    if trust_row.empty or trust_row['sentiment_pct'].isna().all():
                        ticker_issues.append('Trust')

                if ticker_issues:
                    issues.append((ticker, ticker_issues))

            return issues

        data_issues = check_data_quality(df_composite, df_val, df_liq, df_cov, df_trust)
        if data_issues:
            with st.expander(f"⚠️ Data Quality: {len(data_issues)} ticker(s) with incomplete data", expanded=False):
                for ticker, missing in data_issues:
                    st.caption(f"**{ticker}**: Missing {', '.join(missing)}")
                st.caption("*Missing dials use peer median for composite calculation*")
        else:
            st.caption("✅ Data quality: All tickers have complete data across all dials")

    except Exception as e:
        st.error(f"❌ Error displaying results: {str(e)}")
        st.exception(e)
        st.stop()

    # Handle single vs multi-quarter data
    is_multi_quarter = 'quarter' in df_composite.columns
    st.session_state['is_multi_quarter'] = is_multi_quarter
    if is_multi_quarter:
        # Multi-quarter data - let user select which quarter to view
        available_quarters = sorted(df_composite['quarter'].unique(), reverse=True)

        # Quarter selector in a highlighted container
        quarter_col1, quarter_col2 = st.columns([2, 3])
        with quarter_col1:
            selected_quarter = st.selectbox(
                "📅 Viewing Quarter:",
                available_quarters,
                help="Select which quarter to display. Use 'Trends' section for cross-quarter analysis."
            )
        with quarter_col2:
            st.markdown(f"""
            <div style="background-color: #1e3a5f; padding: 10px; border-radius: 5px; margin-top: 5px;">
                <strong>📊 Currently Viewing:</strong> {selected_quarter} |
                <em>{len(available_quarters)} quarters available</em>
            </div>
            """, unsafe_allow_html=True)

        # Store in session state for consistency across sections
        st.session_state['current_viewing_quarter'] = selected_quarter

        # Filter data for selected quarter
        df_composite_filtered = df_composite[df_composite['quarter'] == selected_quarter].copy()
        df_trust_filtered = df_trust[df_trust['quarter'] == selected_quarter].copy() if 'quarter' in df_trust.columns else df_trust
        df_val_filtered = df_val[df_val['quarter'] == selected_quarter].copy() if 'quarter' in df_val.columns else df_val
        df_cov_filtered = df_cov[df_cov['quarter'] == selected_quarter].copy() if 'quarter' in df_cov.columns else df_cov
        df_liq_filtered = df_liq[df_liq['quarter'] == selected_quarter].copy() if 'quarter' in df_liq.columns else df_liq
    else:
        # Single quarter data - use directly
        selected_quarter = quarters_analyzed[0] if quarters_analyzed else "Current"
        st.session_state['current_viewing_quarter'] = selected_quarter
        df_composite_filtered = df_composite.copy()
        df_trust_filtered = df_trust.copy()
        df_val_filtered = df_val.copy()
        df_cov_filtered = df_cov.copy()
        df_liq_filtered = df_liq.copy()

    # Prepare display data (use filtered data) - needed for all sections
    display_df = df_composite_filtered.copy()
    # Sort by composite score (highest first) and create rank
    display_df = display_df.sort_values('irci_composite_pct', ascending=False)
    display_df['rank'] = range(1, len(display_df) + 1)

    # Format percentages
    for col in ['irci_composite_pct', 'valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(1)

    # Get current section from session state (navigation is at top of sidebar now)
    selected_section = st.session_state.get('selected_section', "📊 Company Analysis")

    # SECTION 1: Company Analysis (Composite Scores + Dial Breakdown + Detailed Metrics)
    if selected_section == "📊 Company Analysis":
        # Composite ranking
        st.markdown("### 🏆 Composite Ranking")
        st.caption("Companies ranked by overall IRCI score (0-100%). Higher = better IR performance vs peers.")

        # Column view selector - use key parameter for proper state management
        view_options = ["Summary", "All Dials", "Detailed"]

        table_view = st.radio(
            "View:",
            view_options,
            horizontal=True,
            key="composite_table_view",
            help="Summary: Just rank & score | All Dials: Score breakdown | Detailed: All available columns"
        )

        # Display table based on selected view
        col1, col2 = st.columns([2, 1])

        with col1:
            if table_view == "Summary":
                columns_to_show = ['rank', 'ticker', 'irci_composite_pct']
                column_names = {
                    'rank': 'Rank',
                    'ticker': 'Ticker',
                    'irci_composite_pct': 'IRCI Score %'
                }
            elif table_view == "All Dials":
                columns_to_show = ['rank', 'ticker', 'irci_composite_pct', 'valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']
                column_names = {
                    'rank': 'Rank',
                    'ticker': 'Ticker',
                    'irci_composite_pct': 'IRCI %',
                    'valuation_pct': 'Valuation %',
                    'liquidity_pct': 'Liquidity %',
                    'coverage_pct': 'Coverage %',
                    'sentiment_pct': 'Trust %'
                }
            else:  # Detailed
                # Show all available numeric columns
                columns_to_show = ['rank', 'ticker', 'irci_composite_pct', 'valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']
                # Add any additional columns that exist
                for col in display_df.columns:
                    if col not in columns_to_show and col not in ['quarter']:
                        columns_to_show.append(col)
                column_names = {
                    'rank': 'Rank',
                    'ticker': 'Ticker',
                    'irci_composite_pct': 'IRCI %',
                    'valuation_pct': 'Valuation %',
                    'liquidity_pct': 'Liquidity %',
                    'coverage_pct': 'Coverage %',
                    'sentiment_pct': 'Trust %'
                }

            # Filter to only columns that exist
            columns_to_show = [c for c in columns_to_show if c in display_df.columns]

            # Color-code the IRCI score column (green=high, red=low)
            styled_df = display_df[columns_to_show].rename(columns=column_names)
            score_col = 'IRCI Score %' if 'IRCI Score %' in styled_df.columns else 'IRCI %'
            if score_col in styled_df.columns:
                st.dataframe(
                    styled_df.style.background_gradient(
                        subset=[score_col],
                        cmap='RdYlGn',
                        vmin=0,
                        vmax=100
                    ),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True
                )

        with col2:
            # Top 3 performers
            top3 = display_df.head(3)
            st.markdown("**Top Performers:**")
            for idx, row in top3.iterrows():
                st.metric(
                    label=f"#{int(row['rank'])} {row['ticker']}",
                    value=f"{row['irci_composite_pct']:.1f}%",
                    delta=None,
                    help=f"IRCI composite score for {row['ticker']} - ranked #{int(row['rank'])} in peer group"
                )
        # Composite Scores Bar Chart
        st.markdown("### 📊 Composite Scores")
        fig = px.bar(
            display_df,
            x='ticker',
            y='irci_composite_pct',
            title=f'IRCI Composite Scores - {selected_quarter}',
            labels={'irci_composite_pct': 'Composite Score (%)', 'ticker': 'Company'},
            color='irci_composite_pct',
            color_continuous_scale='Viridis',
            text='irci_composite_pct'
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(
            showlegend=False,
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,33,48,0.5)',
            font=dict(color='#fafafa'),
            title_font=dict(color='#00d4ff'),
            xaxis=dict(gridcolor='#2e3440'),
            yaxis=dict(gridcolor='#2e3440')
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Dial Breakdown Radar Chart - using fragment to prevent scroll-to-top
        st.markdown("### 📉 Dial Breakdown")

        @st.fragment
        def dial_breakdown_section():
            """Fragment for company selector and dial breakdown to prevent scroll"""
            selected_company = st.selectbox(
                "Select company for dial breakdown:",
                display_df['ticker'].tolist(),
                key="dial_breakdown_company_select"
            )

            company_data = display_df[display_df['ticker'] == selected_company].iloc[0]

            categories = ['Valuation', 'Liquidity', 'Coverage', 'Trust']
            values = [
                company_data.get('valuation_pct', 0),
                company_data.get('liquidity_pct', 0),
                company_data.get('coverage_pct', 0),
                company_data.get('sentiment_pct', 0)
            ]

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=selected_company,
                line=dict(color='#00d4ff', width=2),
                fillcolor='rgba(0, 212, 255, 0.3)'
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        gridcolor='#2e3440',
                        color='#fafafa'
                    ),
                    angularaxis=dict(
                        gridcolor='#2e3440',
                        color='#fafafa'
                    ),
                    bgcolor='rgba(30,33,48,0.5)'
                ),
                showlegend=True,
                title=f'{selected_company} - Dial Breakdown',
                title_font=dict(color='#00d4ff'),
                height=500,
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#fafafa')
            )
            st.plotly_chart(fig, use_container_width=True)

            # Helper function to get status color and label
            def get_dial_status(value):
                """Returns (color, status_label) based on dial value."""
                if value >= 70:
                    return '#4CAF50', 'Strong'  # Green for strong
                elif value >= 40:
                    return '#FFA500', 'Moderate'  # Orange/yellow for moderate
                else:
                    return '#ff4444', 'Needs Attention'  # Red for needs attention

            # Create compact gauge charts for each dial
            st.markdown("#### Dial Performance Gauges")

            def create_gauge_chart(value, title):
                """Create a compact gauge chart for a dial metric."""
                status_color, status_label = get_dial_status(value)

                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=value,
                    number={'suffix': '%', 'font': {'size': 18, 'color': '#fafafa'}},
                    title={'text': f"<b>{title}</b><br><span style='font-size:10px;color:{status_color}'>{status_label}</span>",
                           'font': {'size': 12, 'color': '#fafafa'}},
                    gauge={
                        'axis': {'range': [0, 100], 'tickcolor': '#fafafa', 'tickfont': {'color': '#fafafa', 'size': 8}, 'dtick': 25},
                        'bar': {'color': status_color, 'thickness': 0.7},
                        'bgcolor': 'rgba(30,33,48,0.8)',
                        'borderwidth': 1,
                        'bordercolor': status_color,
                        'steps': [
                            {'range': [0, 40], 'color': 'rgba(255, 68, 68, 0.15)'},
                            {'range': [40, 70], 'color': 'rgba(255, 165, 0, 0.15)'},
                            {'range': [70, 100], 'color': 'rgba(76, 175, 80, 0.15)'}
                        ],
                        'threshold': {
                            'line': {'color': '#fafafa', 'width': 1},
                            'thickness': 0.75,
                            'value': value
                        }
                    }
                ))

                fig.update_layout(
                    height=150,
                    margin=dict(l=10, r=10, t=60, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#fafafa')
                )
                return fig

            # Create 4 columns for the gauges with unique session-based key
            gauge_cols = st.columns(4)
            gauge_session_id = st.session_state.get('analysis_timestamp', 'default')

            # Dial tooltips/explanations
            dial_tooltips = {
                'Valuation': 'Market pricing vs peers (EV/EBITDA, PEG)',
                'Liquidity': 'Trading ease (volume, spread, turnover)',
                'Coverage': 'Visibility (media, filings, analyst count)',
                'Trust': 'Market confidence (volatility, sentiment)'
            }

            for i, (dial_name, dial_value) in enumerate(zip(categories, values)):
                with gauge_cols[i]:
                    gauge_fig = create_gauge_chart(dial_value, dial_name)
                    st.plotly_chart(
                        gauge_fig,
                        use_container_width=True,
                        key=f"gauge_{dial_name}_{selected_company}_{gauge_session_id}_frag",
                        config={'displayModeBar': False, 'staticPlot': False}
                    )
                    st.caption(f"ℹ️ {dial_tooltips.get(dial_name, '')}")

            # Status legend
            st.markdown("""
            <div style="display: flex; justify-content: center; gap: 20px; padding: 8px; background: rgba(30,33,48,0.5); border-radius: 6px; font-size: 12px;">
                <span><span style="color: #4CAF50;">●</span> Strong (≥70%)</span>
                <span><span style="color: #FFA500;">●</span> Moderate (40-69%)</span>
                <span><span style="color: #ff4444;">●</span> Needs Attention (<40%)</span>
            </div>
            """, unsafe_allow_html=True)

        # Call the dial breakdown fragment
        dial_breakdown_section()

        st.markdown("---")

        # Detailed Metrics by Dial (using expanders for each dial)
        st.markdown("### 📋 Detailed Metrics")

        with st.expander("💰 Valuation Details", expanded=False):
            # Valuation scoring methodology explanation
            st.markdown("""
**Valuation Score** combines EV/EBITDA (70%) + PEG ratio (30%) for a growth-adjusted view. Lower multiples score higher vs peers.
            """)

            val_cols = ['ticker']
            val_rename = {'ticker': 'Ticker'}

            # Add quarter column if in multi-quarter mode
            if 'quarter' in df_val.columns:
                val_cols.append('quarter')
                val_rename['quarter'] = 'Quarter'

            # Core valuation columns
            val_cols.extend(['valuation_pct', 'ev_to_ebitda'])
            val_rename.update({
                'valuation_pct': 'Blended Score %',
                'ev_to_ebitda': 'EV/EBITDA'
            })

            # Add component scores if available
            if 'ev_ebitda_pct' in df_val.columns:
                val_cols.append('ev_ebitda_pct')
                val_rename['ev_ebitda_pct'] = 'EV/EBITDA %'

            if 'peg_ratio' in df_val.columns:
                val_cols.append('peg_ratio')
                val_rename['peg_ratio'] = 'PEG Ratio'

            if 'peg_pct' in df_val.columns:
                val_cols.append('peg_pct')
                val_rename['peg_pct'] = 'PEG %'

            if 'valuation_method' in df_val.columns:
                val_cols.append('valuation_method')
                val_rename['valuation_method'] = 'Method'

            val_cols.extend(['peer_mean_excl_self', 'valuation_gap_pct', 'valuation_quartile'])
            val_rename.update({
                'peer_mean_excl_self': 'Peer Avg',
                'valuation_gap_pct': 'Gap %',
                'valuation_quartile': 'Quartile'
            })

            # Create display dataframe with proper formatting
            available_cols = [c for c in val_cols if c in df_val.columns]
            df_val_display = df_val[available_cols].copy()

            # Format PEG ratio
            if 'peg_ratio' in df_val_display.columns:
                df_val_display['peg_ratio'] = df_val_display['peg_ratio'].apply(
                    lambda x: "N/A" if pd.isna(x) or x is None or str(x).lower() in ('none', 'nan', '') else f"{x:.2f}"
                )

            # Format PEG pct
            if 'peg_pct' in df_val_display.columns:
                df_val_display['peg_pct'] = df_val_display['peg_pct'].apply(
                    lambda x: "N/A" if pd.isna(x) else f"{x:.1f}"
                )

            st.dataframe(
                df_val_display.rename(columns={k: v for k, v in val_rename.items() if k in available_cols}),
                use_container_width=True,
                hide_index=True
            )

            # Check peer count to show appropriate note
            peer_count = df_val['peer_count'].iloc[0] if 'peer_count' in df_val.columns else len(df_val)

            if peer_count <= 5:
                if peer_count <= 2:
                    score_range = "30-70%"
                else:
                    score_range = "15-85%"
                st.caption(f"""
💡 **Quick Guide:** EV/EBITDA compares value to earnings (lower = cheaper). PEG adjusts P/E for growth (below 1.0 = potentially undervalued). Scores show peer percentile ranking.

📊 **Small Peer Group Note:** With only {peer_count} peers, percentile scores are compressed to {score_range} to avoid statistically unreliable extremes. Expand peer group for full 0-100% range.
""")
            else:
                st.caption("""
💡 **Quick Guide:** EV/EBITDA compares value to earnings (lower = cheaper). PEG adjusts P/E for growth (below 1.0 = potentially undervalued). Scores show peer percentile ranking.
""")

        with st.expander("💧 Liquidity Details", expanded=False):
            # Build liquidity columns list
            liq_cols = ['ticker']
            liq_rename = {'ticker': 'Ticker'}

            # Add quarter column if in multi-quarter mode
            if 'quarter' in df_liq.columns:
                liq_cols.append('quarter')
                liq_rename['quarter'] = 'Quarter'

            liq_cols.extend(['liquidity_pct', 'q_amihud_e6', 'q_spread_bps', 'q_turnover'])
            liq_rename.update({
                'liquidity_pct': 'Score %',
                'q_amihud_e6': 'Amihud (×10⁶)',
                'q_spread_bps': 'Spread (bps)',
                'q_turnover': 'Turnover'
            })

            # Add institutional ownership column if available (holder_count removed - Yahoo only provides top 10)
            if 'institutional_pct' in df_liq.columns:
                liq_cols.append('institutional_pct')
                liq_rename['institutional_pct'] = 'Inst. Ownership %'

            st.dataframe(
                df_liq[[c for c in liq_cols if c in df_liq.columns]].rename(columns=liq_rename),
                use_container_width=True,
                hide_index=True
            )

            st.caption("""
💡 **Metric Definitions:**
• **Amihud (×10⁶)** = Price impact measure. Lower = more liquid. Shows how much price moves per dollar of volume.
• **Spread (bps)** = Bid-ask spread in basis points. Lower = tighter spreads = better liquidity.
• **Turnover** = Trading volume ÷ shares outstanding. Higher = more actively traded.
• **Inst. Ownership %** = Percentage of shares held by institutional investors (from Yahoo Finance). Higher = more institutional interest.
""")

        with st.expander("📰 Coverage Details", expanded=False):
            # Calculate high-quality article counts
            df_cov_display = df_cov.copy()
            news_df = st.session_state.get('news_df', None)

            if news_df is not None and not news_df.empty and 'domain' in news_df.columns:
                from irci.config import Settings

                # Load domain weights
                s = Settings.load()
                domain_weights = s.domain_weights or {}

                # Define high-quality threshold (0.7 = reputable sources and above)
                HIGH_QUALITY_THRESHOLD = 0.7

                # Filter news for current quarter if multi-quarter mode
                news_for_quarter = news_df.copy()
                if is_multi_quarter and 'quarter' in news_df.columns:
                    news_for_quarter = news_df[news_df['quarter'] == selected_quarter]

                # Count high-quality articles per ticker
                high_quality_counts = []
                for ticker in df_cov_display['ticker']:
                    # Filter by ticker if column exists
                    if 'ticker' in news_for_quarter.columns:
                        ticker_news = news_for_quarter[news_for_quarter['ticker'] == ticker]
                    else:
                        ticker_news = news_for_quarter

                    if not ticker_news.empty:
                        # Normalize domains
                        domains = ticker_news['domain'].astype(str).str.lower().str.replace(r'^www\.', '', regex=True)

                        # Count articles from high-quality domains
                        high_qual_count = sum(
                            domain_weights.get(dom, 0.3) >= HIGH_QUALITY_THRESHOLD
                            for dom in domains
                        )
                    else:
                        high_qual_count = 0

                    high_quality_counts.append(high_qual_count)

                df_cov_display['high_quality_articles'] = high_quality_counts

            # Display coverage details with high-quality article count if available
            coverage_cols = ['ticker']
            coverage_rename = {'ticker': 'Ticker'}

            # Add quarter column if in multi-quarter mode
            if 'quarter' in df_cov_display.columns:
                coverage_cols.append('quarter')
                coverage_rename['quarter'] = 'Quarter'

            coverage_cols.extend(['coverage_pct', 'q_8k_count', 'q_days_to_10q'])
            coverage_rename.update({
                'coverage_pct': 'Score %',
                'q_8k_count': '8-K Count',
                'q_days_to_10q': 'Days to 10-Q/K'
            })

            if 'high_quality_articles' in df_cov_display.columns:
                coverage_cols.append('high_quality_articles')
                coverage_rename['high_quality_articles'] = 'High-Quality Articles'

            # Add transcript quality columns if available
            if 'transcript_quality_score' in df_cov_display.columns:
                coverage_cols.extend(['transcript_quality_score', 'has_transcript'])
                coverage_rename.update({
                    'transcript_quality_score': 'Transcript Score',
                    'has_transcript': 'Has Transcript'
                })

            # Add analyst coverage columns if available (from Yahoo Finance)
            if 'analyst_count' in df_cov_display.columns:
                coverage_cols.extend(['analyst_count', 'recommendation', 'price_target_upside_pct'])
                coverage_rename.update({
                    'analyst_count': 'Analysts',
                    'recommendation': 'Rating',
                    'price_target_upside_pct': 'Target Upside %'
                })

            st.dataframe(
                df_cov_display[[c for c in coverage_cols if c in df_cov_display.columns]].rename(columns=coverage_rename),
                use_container_width=True,
                hide_index=True
            )

            # Show analyst coverage summary if data available
            if 'analyst_count' in df_cov_display.columns:
                has_analyst_data = df_cov_display['analyst_count'].notna().any() and (df_cov_display['analyst_count'] > 0).any()
                if has_analyst_data:
                    st.markdown("---")
                    st.markdown("**📈 Analyst Coverage (Yahoo Finance)**")
                    analyst_display = df_cov_display[['ticker', 'analyst_count', 'recommendation', 'target_mean', 'price_target_upside_pct']].copy()
                    analyst_display = analyst_display[analyst_display['analyst_count'].notna() & (analyst_display['analyst_count'] > 0)]
                    if not analyst_display.empty:
                        analyst_display['price_target_upside_pct'] = analyst_display['price_target_upside_pct'].apply(
                            lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A"
                        )
                        analyst_display['target_mean'] = analyst_display['target_mean'].apply(
                            lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
                        )
                        analyst_display = analyst_display.rename(columns={
                            'ticker': 'Ticker',
                            'analyst_count': 'Analysts',
                            'recommendation': 'Consensus',
                            'target_mean': 'Price Target',
                            'price_target_upside_pct': 'Upside'
                        })
                        st.dataframe(analyst_display, use_container_width=True, hide_index=True)

            st.caption("""
💡 **Metric Definitions:**
• **8-K Count** = Number of 8-K filings (material events) in the quarter. More filings = more disclosure activity.
• **Days to 10-Q/K** = Days after quarter-end until 10-Q (or 10-K) was filed. Fewer days = faster reporting.
• **Transcript Score** = Quality score (0-100) for earnings call transcripts based on forward-looking statements and guidance coverage.
""")
            if 'high_quality_articles' in df_cov_display.columns:
                st.caption("• **High-Quality Articles** = Articles from top-tier sources (weight ≥ 0.7): WSJ, Bloomberg, Reuters, CNBC, Forbes, Barron's, MarketWatch, Motley Fool, Benzinga, etc.")

            # Show domain breakdown for debugging/transparency
            if news_df is not None and not news_df.empty and 'domain' in news_df.columns:
                with st.expander("📊 News Source Breakdown", expanded=False):
                    # Get domain counts
                    domain_counts = news_df['domain'].value_counts().head(20)
                    if not domain_counts.empty:
                        st.markdown("**Top news sources in your analysis:**")
                        for dom, count in domain_counts.items():
                            weight = domain_weights.get(dom, 0.3)
                            quality = "✅ High-quality" if weight >= 0.7 else "⚪ Standard"
                            st.markdown(f"• `{dom}`: {count} articles ({quality}, weight: {weight})")

        with st.expander("💭 Trust Details", expanded=False):
            # Build trust columns list
            trust_cols = ['ticker']
            trust_rename = {'ticker': 'Ticker'}

            # Add quarter column if in multi-quarter mode
            if 'quarter' in df_trust.columns:
                trust_cols.append('quarter')
                trust_rename['quarter'] = 'Quarter'

            trust_cols.extend(['trust_pct', 'p_event_calm', 'p_baseline_calm', 'p_media_tone', 'event_count', 'media_tone_n'])
            trust_rename.update({
                'trust_pct': 'Score %',
                'p_event_calm': 'Event Calm %',
                'p_baseline_calm': 'Baseline Calm %',
                'p_media_tone': 'Media Tone %',
                'event_count': 'Events',
                'media_tone_n': 'Articles'
            })

            # Add social sentiment columns if available
            if 'p_social_sentiment' in df_trust.columns:
                trust_cols.extend(['p_social_sentiment', 'social_activity'])
                trust_rename.update({
                    'p_social_sentiment': 'Social Sentiment %',
                    'social_activity': 'Retail Activity'
                })

            # Add short interest columns if available (from Yahoo Finance)
            if 'short_pct_float' in df_trust.columns:
                trust_cols.extend(['short_pct_float', 'short_ratio'])
                trust_rename.update({
                    'short_pct_float': 'Short % Float',
                    'short_ratio': 'Days to Cover'
                })

            st.dataframe(
                df_trust[[c for c in trust_cols if c in df_trust.columns]].rename(columns=trust_rename),
                use_container_width=True,
                hide_index=True
            )

            # Show social sentiment details if available
            if 'p_social_sentiment' in df_trust.columns:
                has_social_data = df_trust['p_social_sentiment'].notna().any()
                if has_social_data:
                    st.markdown("##### 📱 Social Sentiment Details (Reddit/StockTwits)")
                    social_cols = ['ticker']
                    if 'quarter' in df_trust.columns:
                        social_cols.append('quarter')
                    social_cols.extend(['social_sentiment_raw', 'social_sources', 'social_activity'])
                    social_rename = {
                        'ticker': 'Ticker',
                        'quarter': 'Quarter',
                        'social_sentiment_raw': 'Raw Score (-1 to 1)',
                        'social_sources': 'Sources',
                        'social_activity': 'Activity Level'
                    }
                    social_display = df_trust[[c for c in social_cols if c in df_trust.columns]].copy()
                    if 'social_sentiment_raw' in social_display.columns:
                        social_display['social_sentiment_raw'] = social_display['social_sentiment_raw'].apply(
                            lambda x: f"{x:.3f}" if pd.notna(x) else "N/A"
                        )
                    st.dataframe(
                        social_display.rename(columns=social_rename),
                        use_container_width=True,
                        hide_index=True
                    )

            # Show short interest details if available
            if 'short_pct_float' in df_trust.columns:
                has_short_data = df_trust['short_pct_float'].notna().any()
                if has_short_data:
                    st.markdown("---")
                    st.markdown("**📉 Short Interest (Yahoo Finance)**")
                    short_cols = ['ticker', 'short_pct_float', 'short_ratio', 'short_change_pct']
                    short_display = df_trust[[c for c in short_cols if c in df_trust.columns]].copy()
                    short_display = short_display[short_display['short_pct_float'].notna()]
                    if not short_display.empty:
                        short_display['short_pct_float'] = short_display['short_pct_float'].apply(
                            lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"
                        )
                        short_display['short_ratio'] = short_display['short_ratio'].apply(
                            lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
                        )
                        if 'short_change_pct' in short_display.columns:
                            short_display['short_change_pct'] = short_display['short_change_pct'].apply(
                                lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A"
                            )
                        short_display = short_display.rename(columns={
                            'ticker': 'Ticker',
                            'short_pct_float': 'Short % Float',
                            'short_ratio': 'Days to Cover',
                            'short_change_pct': 'MoM Change'
                        })
                        st.dataframe(short_display, use_container_width=True, hide_index=True)

            st.caption("""
💡 **Metric Definitions:**
• **Event Calm %** = Measures price stability around earnings and 8-K filings. Higher % = stock price moved LESS than peers during event windows (good for investor confidence).
• **Baseline Calm %** = Measures day-to-day price volatility vs peers. Higher % = LOWER volatility than peers (more predictable stock).
• **Media Tone %** = Sentiment score from news coverage. Higher = more positive coverage.
• **Social Sentiment %** = Retail investor sentiment from Reddit (r/wallstreetbets). Higher = more bullish momentum.
• **Short % Float** = Percentage of tradeable shares sold short. Lower = less bearish sentiment (higher trust).
• **Days to Cover** = Number of days for shorts to cover based on avg volume. Higher = more crowded short trade.
• **Events** = Number of corporate events (earnings, 8-K filings) analyzed.
• **Articles** = Number of news articles analyzed for sentiment.
""")

    # SECTION 2: Trend Analysis (only for multi-quarter data)
    if is_multi_quarter and selected_section == "📈 Trends":
        st.markdown("#### IRCI Score Progression Over Time")
        st.caption("Track how each company's IRCI score has changed across quarters")

        # Prepare data for trend visualization
        trend_df = df_composite.copy()

        # Sort quarters chronologically (e.g., 2024Q1 < 2024Q2 < 2024Q3)
        # Create a sortable quarter key: extract year and quarter number
        def quarter_sort_key(q):
            """Convert quarter string like '2024Q1' to sortable tuple (2024, 1)"""
            try:
                year = int(q[:4])
                qtr = int(q[-1])
                return (year, qtr)
            except:
                return (0, 0)

        unique_quarters = sorted(trend_df['quarter'].unique(), key=quarter_sort_key)
        trend_df['quarter'] = pd.Categorical(trend_df['quarter'], categories=unique_quarters, ordered=True)
        trend_df = trend_df.sort_values(['quarter', 'ticker'])

        # Line chart showing IRCI progression for each company
        fig_trend = px.line(
            trend_df,
            x='quarter',
            y='irci_composite_pct',
            color='ticker',
            markers=True,
            title='IRCI Composite Score Trends',
            labels={'irci_composite_pct': 'IRCI Score (%)', 'quarter': 'Quarter', 'ticker': 'Company'},
            category_orders={'quarter': unique_quarters}
        )
        fig_trend.update_layout(
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,33,48,0.5)',
            font=dict(color='#fafafa'),
            title_font=dict(color='#00d4ff'),
            xaxis=dict(gridcolor='#2e3440'),
            yaxis=dict(gridcolor='#2e3440'),
            hovermode='x unified'
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Quarter-over-quarter changes
        st.markdown("#### Quarter-over-Quarter Changes")

        # Calculate QoQ changes
        qoq_data = []
        for ticker in trend_df['ticker'].unique():
            ticker_data = trend_df[trend_df['ticker'] == ticker].sort_values('quarter')
            if len(ticker_data) > 1:
                for i in range(1, len(ticker_data)):
                    prev_row = ticker_data.iloc[i-1]
                    curr_row = ticker_data.iloc[i]
                    qoq_change = curr_row['irci_composite_pct'] - prev_row['irci_composite_pct']
                    qoq_data.append({
                        'ticker': ticker,
                        'quarter': curr_row['quarter'],
                        'prev_quarter': prev_row['quarter'],
                        'change': qoq_change,
                        'current_score': curr_row['irci_composite_pct'],
                        'previous_score': prev_row['irci_composite_pct']
                    })

        if qoq_data:
            import pandas as pd
            qoq_df = pd.DataFrame(qoq_data)

            # Sort quarters in QoQ data chronologically
            qoq_quarters = sorted(qoq_df['quarter'].unique(), key=quarter_sort_key)

            # Bar chart of QoQ changes
            fig_qoq = px.bar(
                qoq_df,
                x='ticker',
                y='change',
                color='change',
                title='Quarter-over-Quarter IRCI Changes',
                labels={'change': 'IRCI Change (pts)', 'ticker': 'Company'},
                color_continuous_scale='RdYlGn',
                color_continuous_midpoint=0,
                facet_col='quarter',
                facet_col_wrap=3,
                category_orders={'quarter': qoq_quarters}
            )
            fig_qoq.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,33,48,0.5)',
                font=dict(color='#fafafa'),
                title_font=dict(color='#00d4ff')
            )
            st.plotly_chart(fig_qoq, use_container_width=True)

            # Calculate QoQ value creation if dollar value data is available
            try:
                from irci.dial_insights import compute_dollar_value_per_irci_point
                # Use the most recent quarter's data for dollar value calculation
                latest_quarter = unique_quarters[-1]
                df_latest = df_composite[df_composite['quarter'] == latest_quarter].copy()
                dollar_value_df = compute_dollar_value_per_irci_point(df_latest, df_val)

                if dollar_value_df is not None and not dollar_value_df.empty:
                    # Add dollar value to QoQ data
                    qoq_df_with_value = qoq_df.merge(
                        dollar_value_df[['ticker', 'company_$/irci_pt']],
                        on='ticker',
                        how='left'
                    )
                    qoq_df_with_value['value_change'] = qoq_df_with_value['change'] * qoq_df_with_value['company_$/irci_pt']

                    # QoQ Value Creation Summary
                    st.markdown("#### 💰 QoQ Value Creation")
                    st.caption("Estimated enterprise value impact from IRCI score changes (IRCI change × \\$/IRCI point)")

                    # Create summary with value
                    value_summary = []
                    for ticker in qoq_df_with_value['ticker'].unique():
                        ticker_data = qoq_df_with_value[qoq_df_with_value['ticker'] == ticker]
                        total_change = ticker_data['change'].sum()
                        total_value = ticker_data['value_change'].sum()
                        dollar_per_pt = ticker_data['company_$/irci_pt'].iloc[0] if not ticker_data['company_$/irci_pt'].isna().all() else 0

                        value_summary.append({
                            'Ticker': ticker,
                            'Total IRCI Chg': f"{total_change:+.1f} pts",
                            '$/IRCI Point': f"${dollar_per_pt/1e6:,.0f}M" if dollar_per_pt >= 1e6 else f"${dollar_per_pt:,.0f}",
                            'Est. Value Created': f"${total_value/1e9:+.1f}B" if abs(total_value) >= 1e9 else f"${total_value/1e6:+,.0f}M"
                        })

                    value_summary_df = pd.DataFrame(value_summary)
                    st.dataframe(value_summary_df, use_container_width=True, hide_index=True)

                    # Total value creation across all companies
                    total_value_all = qoq_df_with_value['value_change'].sum()
                    if abs(total_value_all) >= 1e9:
                        total_str = f"${total_value_all/1e9:+.1f}B"
                    else:
                        total_str = f"${total_value_all/1e6:+,.0f}M"

                    st.info(f"**Total estimated value creation across peer group:** {total_str}")
            except Exception as e:
                pass  # Dollar value calculation not available

            # Summary table
            st.markdown("#### QoQ Change Summary")
            summary_df = qoq_df.groupby('ticker')['change'].agg(['mean', 'min', 'max']).reset_index()
            summary_df.columns = ['Ticker', 'Avg Change', 'Min Change', 'Max Change']
            summary_df = summary_df.round(2)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        else:
            st.info("Need at least 2 quarters of data per company to show QoQ changes.")

        # Dial-level trend charts
        st.markdown("---")
        st.markdown("#### 📊 Individual Dial Trends")
        st.caption("Track performance trends for each of the four IRCI dials")

        # Check which dial columns exist
        dial_columns = {
            'Valuation': 'valuation_pct',
            'Liquidity': 'liquidity_pct',
            'Coverage': 'coverage_pct',
            'Trust': 'sentiment_pct'
        }

        # Create 2x2 grid for the four dials
        col1, col2 = st.columns(2)

        dial_items = list(dial_columns.items())
        for idx, (dial_name, dial_col) in enumerate(dial_items):
            if dial_col in trend_df.columns:
                # Use col1 for first and third dials, col2 for second and fourth
                with (col1 if idx % 2 == 0 else col2):
                    fig_dial = px.line(
                        trend_df,
                        x='quarter',
                        y=dial_col,
                        color='ticker',
                        markers=True,
                        title=f'{dial_name} Dial Trends',
                        labels={dial_col: f'{dial_name} Score (%)', 'quarter': 'Quarter', 'ticker': 'Company'},
                        category_orders={'quarter': unique_quarters}
                    )
                    fig_dial.update_layout(
                        height=350,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(30,33,48,0.5)',
                        font=dict(color='#fafafa', size=10),
                        title_font=dict(color='#00d4ff', size=14),
                        xaxis=dict(gridcolor='#2e3440'),
                        yaxis=dict(gridcolor='#2e3440'),
                        legend=dict(font=dict(size=9)),
                        margin=dict(l=40, r=40, t=40, b=40)
                    )
                    st.plotly_chart(fig_dial, use_container_width=True)

        # Trend forecasting
        st.markdown("---")
        st.markdown("#### 🔮 Advanced Trend Forecasting")
        st.caption("Predict next quarter IRCI scores with confidence intervals using linear or polynomial regression")

        # Only forecast if we have at least 2 quarters
        if len(trend_df['quarter'].unique()) >= 2:
            from sklearn.linear_model import LinearRegression
            from sklearn.preprocessing import PolynomialFeatures
            from scipy import stats
            import numpy as np

            # Model selection
            col_model, col_ci = st.columns([2, 1])
            with col_model:
                model_type = st.selectbox(
                    "Forecasting Model",
                    ["Linear Regression", "Polynomial Regression (Degree 2)", "Polynomial Regression (Degree 3)", "Auto-Select Best Model"],
                    help="Linear: Assumes straight-line trends. Polynomial: Captures curves and acceleration/deceleration. Auto-Select: Chooses model with best R²."
                )
            with col_ci:
                confidence_level = st.selectbox(
                    "Confidence Interval",
                    [90, 95, 99],
                    index=1,
                    help="Prediction interval width. 95% means we're 95% confident the actual value will fall within the range."
                )

            forecast_data = []
            forecast_plot_data_enhanced = []

            # Get unique quarters sorted
            quarters_sorted = sorted(trend_df['quarter'].unique())

            # Create numeric quarter index (0, 1, 2, ...)
            quarter_to_idx = {q: i for i, q in enumerate(quarters_sorted)}

            # Generate next quarter name (simple increment)
            last_quarter = quarters_sorted[-1]
            # Parse YYYYQX format
            year = int(last_quarter[:4])
            q_num = int(last_quarter[-1])
            if q_num == 4:
                next_quarter = f"{year+1}Q1"
            else:
                next_quarter = f"{year}Q{q_num+1}"

            # Forecast for each company
            for ticker in trend_df['ticker'].unique():
                ticker_data = trend_df[trend_df['ticker'] == ticker].sort_values('quarter')

                if len(ticker_data) >= 2:
                    # Prepare X (quarter indices) and y (IRCI scores)
                    X = np.array([quarter_to_idx[q] for q in ticker_data['quarter']]).reshape(-1, 1)
                    y = ticker_data['irci_composite_pct'].values
                    n = len(y)

                    # Try different models
                    models_to_try = {}

                    # 1. Linear regression
                    linear_model = LinearRegression()
                    linear_model.fit(X, y)
                    y_pred_linear = linear_model.predict(X)
                    ss_res_linear = np.sum((y - y_pred_linear) ** 2)
                    ss_tot = np.sum((y - np.mean(y)) ** 2)
                    r2_linear = 1 - (ss_res_linear / ss_tot) if ss_tot > 0 else 0
                    models_to_try['Linear'] = {
                        'model': linear_model,
                        'r2': r2_linear,
                        'y_pred': y_pred_linear,
                        'degree': 1,
                        'poly_features': None
                    }

                    # 2. Polynomial regression (degree 2) - if enough data
                    if len(ticker_data) >= 3:
                        poly_features_2 = PolynomialFeatures(degree=2)
                        X_poly_2 = poly_features_2.fit_transform(X)
                        poly_model_2 = LinearRegression()
                        poly_model_2.fit(X_poly_2, y)
                        y_pred_poly_2 = poly_model_2.predict(X_poly_2)
                        ss_res_poly_2 = np.sum((y - y_pred_poly_2) ** 2)
                        r2_poly_2 = 1 - (ss_res_poly_2 / ss_tot) if ss_tot > 0 else 0
                        models_to_try['Polynomial (Degree 2)'] = {
                            'model': poly_model_2,
                            'r2': r2_poly_2,
                            'y_pred': y_pred_poly_2,
                            'degree': 2,
                            'poly_features': poly_features_2
                        }

                    # 3. Polynomial regression (degree 3) - if enough data
                    if len(ticker_data) >= 4:
                        poly_features_3 = PolynomialFeatures(degree=3)
                        X_poly_3 = poly_features_3.fit_transform(X)
                        poly_model_3 = LinearRegression()
                        poly_model_3.fit(X_poly_3, y)
                        y_pred_poly_3 = poly_model_3.predict(X_poly_3)
                        ss_res_poly_3 = np.sum((y - y_pred_poly_3) ** 2)
                        r2_poly_3 = 1 - (ss_res_poly_3 / ss_tot) if ss_tot > 0 else 0
                        models_to_try['Polynomial (Degree 3)'] = {
                            'model': poly_model_3,
                            'r2': r2_poly_3,
                            'y_pred': y_pred_poly_3,
                            'degree': 3,
                            'poly_features': poly_features_3
                        }

                    # Select model based on user choice
                    if model_type == "Auto-Select Best Model":
                        # Choose model with highest R²
                        best_model_name = max(models_to_try.items(), key=lambda x: x[1]['r2'])[0]
                        selected_model_info = models_to_try[best_model_name]
                        model_used = best_model_name
                    elif model_type == "Linear Regression":
                        selected_model_info = models_to_try['Linear']
                        model_used = "Linear"
                    elif model_type == "Polynomial Regression (Degree 2)":
                        if 'Polynomial (Degree 2)' in models_to_try:
                            selected_model_info = models_to_try['Polynomial (Degree 2)']
                            model_used = "Polynomial (Degree 2)"
                        else:
                            selected_model_info = models_to_try['Linear']
                            model_used = "Linear (insufficient data for polynomial)"
                    elif model_type == "Polynomial Regression (Degree 3)":
                        if 'Polynomial (Degree 3)' in models_to_try:
                            selected_model_info = models_to_try['Polynomial (Degree 3)']
                            model_used = "Polynomial (Degree 3)"
                        else:
                            selected_model_info = models_to_try['Linear']
                            model_used = "Linear (insufficient data for polynomial)"

                    model = selected_model_info['model']
                    r_squared = selected_model_info['r2']
                    y_pred = selected_model_info['y_pred']
                    poly_features = selected_model_info['poly_features']

                    # Predict next quarter
                    next_quarter_idx = len(quarters_sorted)
                    X_next = np.array([[next_quarter_idx]])
                    if poly_features is not None:
                        X_next_transformed = poly_features.transform(X_next)
                        predicted_score = model.predict(X_next_transformed)[0]
                    else:
                        predicted_score = model.predict(X_next)[0]

                    # Calculate confidence interval using prediction interval formula
                    # Standard error of prediction
                    mse = ss_res_linear / (n - 2) if n > 2 else ss_res_linear / n
                    se = np.sqrt(mse)

                    # For simple cases, use t-distribution
                    t_value = stats.t.ppf((1 + confidence_level/100) / 2, n - 2 if n > 2 else 1)

                    # Prediction interval (wider than confidence interval)
                    # Simplified calculation (assumes constant variance)
                    margin_of_error = t_value * se * np.sqrt(1 + 1/n)

                    lower_bound = predicted_score - margin_of_error
                    upper_bound = predicted_score + margin_of_error

                    # Calculate metrics
                    current_score = ticker_data['irci_composite_pct'].iloc[-1]
                    if selected_model_info['degree'] == 1:
                        trend_slope = model.coef_[0]
                    else:
                        # For polynomial, calculate slope at the last point (derivative)
                        trend_slope = np.gradient(y_pred)[-1]

                    trend_direction = "📈 Improving" if trend_slope > 0.5 else "📉 Declining" if trend_slope < -0.5 else "➡️ Stable"

                    forecast_data.append({
                        'Ticker': ticker,
                        'Model': model_used,
                        'Current IRCI': round(current_score, 1),
                        f'Predicted {next_quarter}': round(predicted_score, 1),
                        f'{confidence_level}% Lower': round(lower_bound, 1),
                        f'{confidence_level}% Upper': round(upper_bound, 1),
                        'Range Width': round(upper_bound - lower_bound, 1),
                        'Expected Change': round(predicted_score - current_score, 1),
                        'Trend': trend_direction,
                        'Confidence (R²)': round(r_squared, 2)
                    })

                    # Store data for visualization with confidence bands
                    for _, row in ticker_data.iterrows():
                        forecast_plot_data_enhanced.append({
                            'ticker': ticker,
                            'quarter': row['quarter'],
                            'score': row['irci_composite_pct'],
                            'type': 'Historical',
                            'lower': None,
                            'upper': None
                        })

                    # Add forecast point with confidence interval
                    forecast_plot_data_enhanced.append({
                        'ticker': ticker,
                        'quarter': next_quarter,
                        'score': predicted_score,
                        'type': 'Forecast',
                        'lower': lower_bound,
                        'upper': upper_bound
                    })

            if forecast_data:
                forecast_df = pd.DataFrame(forecast_data)

                # Sort by predicted score
                forecast_df = forecast_df.sort_values(f'Predicted {next_quarter}', ascending=False)

                # Display forecast table
                st.markdown(f"##### Predicted IRCI Scores for **{next_quarter}**")
                st.dataframe(
                    forecast_df.style.background_gradient(
                        subset=[f'Predicted {next_quarter}'],
                        cmap='RdYlGn',
                        vmin=0,
                        vmax=100
                    ).background_gradient(
                        subset=['Expected Change'],
                        cmap='RdYlGn',
                        vmin=-10,
                        vmax=10
                    ),
                    use_container_width=True,
                    hide_index=True
                )

                # Visualization: Forecast chart with confidence bands
                st.markdown(f"##### Forecast Visualization with {confidence_level}% Confidence Intervals")

                # Create figure using plotly graph objects for better control
                import plotly.graph_objects as go

                fig_forecast = go.Figure()

                # Get unique companies and assign colors
                companies = trend_df['ticker'].unique()
                colors = px.colors.qualitative.Plotly

                for idx, ticker in enumerate(companies):
                    color = colors[idx % len(colors)]

                    # Get data for this ticker
                    ticker_data_enhanced = [d for d in forecast_plot_data_enhanced if d['ticker'] == ticker]
                    if not ticker_data_enhanced:
                        continue

                    # Separate historical and forecast
                    historical = [d for d in ticker_data_enhanced if d['type'] == 'Historical']
                    forecast = [d for d in ticker_data_enhanced if d['type'] == 'Forecast']

                    # Plot historical data (solid line)
                    if historical:
                        quarters_hist = [d['quarter'] for d in historical]
                        scores_hist = [d['score'] for d in historical]

                        fig_forecast.add_trace(go.Scatter(
                            x=quarters_hist,
                            y=scores_hist,
                            mode='lines+markers',
                            name=ticker,
                            line=dict(color=color, width=2),
                            marker=dict(size=8),
                            showlegend=True,
                            hovertemplate=f'{ticker}<br>Quarter: %{{x}}<br>IRCI: %{{y:.1f}}<extra></extra>'
                        ))

                    # Plot forecast with confidence band
                    if forecast:
                        forecast_point = forecast[0]
                        last_hist = historical[-1] if historical else None

                        # Draw line from last historical to forecast
                        if last_hist:
                            fig_forecast.add_trace(go.Scatter(
                                x=[last_hist['quarter'], forecast_point['quarter']],
                                y=[last_hist['score'], forecast_point['score']],
                                mode='lines+markers',
                                name=f'{ticker} (forecast)',
                                line=dict(color=color, width=2, dash='dash'),
                                marker=dict(size=8, symbol='diamond'),
                                showlegend=False,
                                hovertemplate=f'{ticker} Forecast<br>Quarter: %{{x}}<br>IRCI: %{{y:.1f}}<extra></extra>'
                            ))

                        # Add confidence band (shaded area)
                        if forecast_point['lower'] is not None and forecast_point['upper'] is not None:
                            # Upper bound line
                            fig_forecast.add_trace(go.Scatter(
                                x=[forecast_point['quarter'], forecast_point['quarter']],
                                y=[forecast_point['lower'], forecast_point['upper']],
                                fill=None,
                                mode='lines',
                                line=dict(color=color, width=0),
                                showlegend=False,
                                hoverinfo='skip'
                            ))

                            # Create shaded area using shapes
                            # We'll use error bars instead for better rendering
                            error_y = forecast_point['upper'] - forecast_point['score']
                            error_y_minus = forecast_point['score'] - forecast_point['lower']

                            fig_forecast.add_trace(go.Scatter(
                                x=[forecast_point['quarter']],
                                y=[forecast_point['score']],
                                mode='markers',
                                marker=dict(size=12, symbol='diamond', color=color),
                                error_y=dict(
                                    type='data',
                                    symmetric=False,
                                    array=[error_y],
                                    arrayminus=[error_y_minus],
                                    color=color,
                                    thickness=1.5,
                                    width=10
                                ),
                                name=f'{ticker} CI',
                                showlegend=False,
                                hovertemplate=f'{ticker} Forecast<br>Predicted: {forecast_point["score"]:.1f}<br>CI: [{forecast_point["lower"]:.1f}, {forecast_point["upper"]:.1f}]<extra></extra>'
                            ))

                # Update layout
                fig_forecast.update_layout(
                    height=600,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(30,33,48,0.5)',
                    font=dict(color='#fafafa'),
                    title=dict(
                        text=f'IRCI Trends with {next_quarter} Forecast & {confidence_level}% Confidence Intervals',
                        font=dict(color='#00d4ff', size=16)
                    ),
                    xaxis=dict(
                        title='Quarter',
                        gridcolor='#2e3440',
                        showline=True,
                        linecolor='#2e3440'
                    ),
                    yaxis=dict(
                        title='IRCI Score (%)',
                        gridcolor='#2e3440',
                        showline=True,
                        linecolor='#2e3440',
                        range=[0, 100]
                    ),
                    hovermode='closest',
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01,
                        bgcolor='rgba(30,33,48,0.8)',
                        bordercolor='#2e3440',
                        borderwidth=1
                    )
                )

                st.plotly_chart(fig_forecast, use_container_width=True)

                # Show interpretation guide
                st.caption(f"""
                **How to read this chart:**
                - **Solid lines**: Historical IRCI scores
                - **Dashed lines**: Forecasted scores for {next_quarter}
                - **Diamond markers**: Predicted values
                - **Error bars**: {confidence_level}% confidence interval (we're {confidence_level}% confident the actual score will fall within this range)
                """)

                # Methodology explanation
                with st.expander("ℹ️ How Advanced Forecasting Works"):
                    st.markdown(f"""
                    **Models:** Linear (steady trends), Polynomial 2 (accelerating/decelerating), Polynomial 3 (S-curves), Auto-Select (highest R²)

                    **Current:** {model_type}

                    **Key Metrics:**
                    - **R²**: Model fit (>0.7 = high confidence, 0.4-0.7 = moderate, <0.4 = low)
                    - **{confidence_level}% Interval**: Range where actual score should fall
                    - **Trend**: 📈 Improving (>+0.5/qtr) | 📉 Declining (<-0.5/qtr) | ➡️ Stable

                    **Limitations:** Assumes trends continue; doesn't account for external shocks or planned initiatives. Past performance ≠ future results.
                    """)
            else:
                st.info("Unable to generate forecasts. Need at least 2 quarters of data per company.")
        else:
            st.info("Need at least 2 quarters of data to generate forecasts. Select more quarters and re-run analysis.")

    # SECTION 3 (or SECTION 2 if not multi-quarter): Value Analysis (Dollar Value)
    if selected_section == "💵 Value Analysis":
        # Import insights module
        from irci.dial_insights import (
            compute_dollar_value_per_irci_point,
            compute_dial_contribution,
            recommend_optimal_weights
        )

        # Section 1: Dollar Value per IRCI Point
        st.markdown("#### 💵 Dollar Value per IRCI Point")
        st.markdown("*Reveals how much enterprise value corresponds to each IRCI point improvement*")

        st.caption("⚠️ Dollar estimates are **planning ranges** based on peer regression, not guarantees. Values scaled by R² for conservatism.")

        try:
            dollar_value_df = compute_dollar_value_per_irci_point(df_composite_filtered, df_val_filtered)

            if dollar_value_df.empty:
                st.warning("⚠️ No enterprise value data available for dollar value calculations. The valuation dial may not have enterprise_value data for this time period.")
            else:
                # Display key metric
                avg_company_dollars_per_point = dollar_value_df['company_$/irci_pt'].mean()
                r2_score = dollar_value_df['regression_r2'].iloc[0] if not dollar_value_df['regression_r2'].isna().all() else 0.0

                col1, col2, col3 = st.columns(3)
                col1.metric(
                    "Avg Company $/IRCI Point",
                    f"${avg_company_dollars_per_point:,.0f}" if not pd.isna(avg_company_dollars_per_point) else "N/A",
                    help="Company-specific dollar value per IRCI point. Capped at max 1% of EV per point (scaled by R²) to reflect realistic IR impact based on academic research."
                )
                col2.metric(
                    "Regression R²",
                    f"{r2_score:.2f}" if not pd.isna(r2_score) else "N/A",
                    help="How well EV correlates with IRCI scores (0-1 scale). R² of 0.3-0.5 is typical for secondary factors after fundamentals. Higher = stronger relationship."
                )
                col3.metric(
                    "Max IRCI Gap",
                    f"{dollar_value_df['irci_gap_to_top'].max():.1f} pts",
                    help="Largest gap between a peer and the top performer. This shows the maximum improvement opportunity in the peer group."
                )


                # IR Contribution Value Summary
                st.markdown("---")
                st.markdown("#### 💰 Quarterly IR Value Contribution")

                # Get previous quarter data if available
                quarters_list = ["2025Q4", "2025Q3", "2025Q2", "2025Q1", "2024Q4", "2024Q3", "2024Q2", "2024Q1"]
                current_q_idx = quarters_list.index(selected_quarter) if selected_quarter in quarters_list else -1
                previous_quarter = quarters_list[current_q_idx + 1] if current_q_idx >= 0 and current_q_idx < len(quarters_list) - 1 else None

                # Try to get previous quarter IRCI scores from session state
                prev_quarter_key = f'df_composite_prev_{previous_quarter}'
                has_prev_data = previous_quarter and prev_quarter_key in st.session_state and st.session_state[prev_quarter_key] is not None

                if has_prev_data:
                    # Add adjustable quarterly impact factor
                    with st.expander("⚙️ Adjust Quarterly Impact Factor", expanded=False):
                        st.markdown("""
                        **Why we need a quarterly impact factor:**
                        - The $/IRCI point is based on **cross-sectional peer comparisons** (Company A vs Company B)
                        - These measure structural, long-term IR quality differences built over years
                        - Quarterly changes are **marginal improvements** from 3 months of IR work
                        - A 1-point QoQ change has less immediate impact than a structural 1-point peer gap

                        **Academic backing:**
                        - Research shows IR contributes 5-15% to firm value (Bushee & Miller 2012; Agarwal et al. 2016)
                        - Quarterly improvements have smaller immediate impact than long-term positioning
                        - Our default 10% factor is conservative and in line with IR literature

                        **Adjust the factor based on your judgment:**
                        """)

                        quarterly_impact_factor_pct = st.slider(
                            "Quarterly Impact Factor",
                            min_value=1,
                            max_value=100,
                            value=10,
                            step=1,
                            format="%d%%",
                            help="What percentage of the structural $/IRCI value applies to quarterly changes? Default 10% is conservative."
                        )
                        quarterly_impact_factor = quarterly_impact_factor_pct / 100.0

                        st.caption(f"""
                        **Current setting: {quarterly_impact_factor_pct}%**
                        - 1-5%: Very conservative (assumes minimal quarterly impact)
                        - 10%: Default/conservative (literature-backed)
                        - 15-25%: Moderate (assumes stronger quarterly effects)
                        - 50-100%: Aggressive (assumes QoQ = structural differences)
                        """)

                    st.caption(f"📊 Shows quarterly IR value change: (ΔIRCI × $/pt × {quarterly_impact_factor:.0%} factor). Positive = improved, Negative = declined.")
                else:
                    st.caption("📊 Shows IR value vs peer average: (Your IRCI - Peer Avg) × $/pt. Run previous quarter first to track QoQ changes.")

                # Calculate peer average IRCI
                peer_avg_irci = dollar_value_df['irci_composite_pct'].mean()

                # Calculate IR contribution for each company
                ir_contribution_data = []
                for _, row in dollar_value_df.iterrows():
                    ticker = row['ticker']
                    irci_score = row['irci_composite_pct']
                    dollar_per_pt = row['company_$/irci_pt']
                    enterprise_value = row['enterprise_value']

                    if has_prev_data:
                        # Use quarter-over-quarter change
                        prev_df = st.session_state[prev_quarter_key]
                        prev_row = prev_df[prev_df['ticker'] == ticker]

                        if not prev_row.empty:
                            prev_irci_score = prev_row['irci_composite_pct'].iloc[0]
                            irci_change = irci_score - prev_irci_score

                            # Apply quarterly impact factor (user-adjustable, default 10%)
                            # Quarterly changes have much smaller immediate impact than structural peer differences
                            # A 1-point QoQ change ≠ the same value as 1-point peer gap
                            # This factor reflects that quarterly IR work is marginal, not structural
                            # Factor is defined above in the expander, use it here
                            ir_value_contribution = irci_change * dollar_per_pt * quarterly_impact_factor

                            ir_contribution_data.append({
                                'ticker': ticker,
                                'irci_score': irci_score,
                                'prev_irci_score': prev_irci_score,
                                'irci_change': irci_change,
                                'dollar_per_pt': dollar_per_pt,
                                'ir_value_contribution': ir_value_contribution,
                                'enterprise_value': enterprise_value,
                                'comparison_type': 'qoq'
                            })
                        else:
                            # Fallback to peer average if no previous data for this ticker
                            irci_gap_from_avg = irci_score - peer_avg_irci
                            ir_value_contribution = irci_gap_from_avg * dollar_per_pt

                            ir_contribution_data.append({
                                'ticker': ticker,
                                'irci_score': irci_score,
                                'peer_avg_irci': peer_avg_irci,
                                'irci_gap_from_avg': irci_gap_from_avg,
                                'dollar_per_pt': dollar_per_pt,
                                'ir_value_contribution': ir_value_contribution,
                                'enterprise_value': enterprise_value,
                                'comparison_type': 'peer_avg'
                            })
                    else:
                        # Use peer average comparison
                        irci_gap_from_avg = irci_score - peer_avg_irci
                        ir_value_contribution = irci_gap_from_avg * dollar_per_pt

                        ir_contribution_data.append({
                            'ticker': ticker,
                            'irci_score': irci_score,
                            'peer_avg_irci': peer_avg_irci,
                            'irci_gap_from_avg': irci_gap_from_avg,
                            'dollar_per_pt': dollar_per_pt,
                            'ir_value_contribution': ir_value_contribution,
                            'enterprise_value': enterprise_value,
                            'comparison_type': 'peer_avg'
                        })

                ir_contrib_df = pd.DataFrame(ir_contribution_data)

                # Display as cards for each company
                cols = st.columns(min(len(ir_contrib_df), 3))
                for idx, (_, company) in enumerate(ir_contrib_df.iterrows()):
                    col_idx = idx % 3
                    with cols[col_idx]:
                        delta_color = "normal" if company['ir_value_contribution'] >= 0 else "inverse"

                        # Create delta text and help based on comparison type
                        pct_of_ev = abs(company['ir_value_contribution'] / company['enterprise_value'] * 100) if company['enterprise_value'] > 0 else 0

                        if company.get('comparison_type') == 'qoq':
                            delta_text = f"{company['irci_change']:+.1f} pts vs {previous_quarter}"
                            help_text = f"Change: {company['irci_change']:+.1f} pts ({company['prev_irci_score']:.1f}→{company['irci_score']:.1f}) × $/IRCI: ${company['dollar_per_pt']:,.0f} × {quarterly_impact_factor_pct}% factor = ${company['ir_value_contribution']:,.0f} ({pct_of_ev:.2f}% of EV)"
                        else:
                            delta_text = f"{company['irci_gap_from_avg']:+.1f} pts vs avg"
                            help_text = f"**Structural positioning gap** (not quarterly contribution): {company['irci_gap_from_avg']:+.1f} pts × $/IRCI: ${company['dollar_per_pt']:,.0f} = ${company['ir_value_contribution']:,.0f} ({pct_of_ev:.2f}% of EV)\n\nThis shows your IR position relative to peers, capped at realistic percentages."

                        # Create metric label with percentage for "vs avg" case
                        if company.get('comparison_type') == 'peer_avg':
                            metric_label = f"{company['ticker']} IR Position Gap"
                            metric_value = f"${company['ir_value_contribution']:,.0f}\n({pct_of_ev:.2f}% of EV)"
                        else:
                            metric_label = f"{company['ticker']} IR Contribution"
                            metric_value = f"${company['ir_value_contribution']:,.0f}"

                        st.metric(
                            metric_label,
                            metric_value,
                            delta=delta_text,
                            delta_color=delta_color,
                            help=help_text
                        )

                # Show appropriate caption based on comparison type
                if has_prev_data:
                    st.caption(f"""
                    📊 **Comparison:** {selected_quarter} vs {previous_quarter} | **Impact Factor:** {quarterly_impact_factor:.0%}

                    💡 **How to interpret:** This shows the estimated value of your IR team's quarterly performance change.

                    **Calculation includes {quarterly_impact_factor:.0%} quarterly impact factor:**
                    - Quarterly IR changes have smaller immediate impact than structural peer differences
                    - Example: +7 IRCI point improvement × \\$150M/point × {quarterly_impact_factor:.0%} = **+\\${7 * 150_000_000 * quarterly_impact_factor:,.0f}**
                    - The {quarterly_impact_factor:.0%} factor reflects that 3 months of IR work is marginal, not structural

                    **Academic support (Bushee & Miller 2012; Agarwal et al. 2016):**
                    - IR contributes 5-15% to firm value in academic studies
                    - Default {quarterly_impact_factor:.0%} factor is conservative and literature-backed
                    - Adjust factor in settings above to match your assumptions

                    **Why a factor at all?**
                    - The $/IRCI point is based on cross-company comparisons (Company A vs Company B)
                    - Those measure long-term structural differences in IR quality built over years
                    - Quarter-over-quarter changes are short-term marginal improvements from 3 months
                    - Cross-sectional ≠ time-series valuation

                    This gives a realistic estimate of quarterly IR contribution while avoiding overstated values.
                    """)
                else:
                    st.caption(f"""
                    📊 **Peer Average IRCI:** {peer_avg_irci:.1f} points

                    ⚠️ **IMPORTANT:** These values show **structural positioning gaps** relative to peers, NOT quarterly contributions.
                    - Values are capped at **max 1% of EV per IRCI point** (scaled by R²) based on academic research
                    - Example: \\$43B gap for \\$3.9T company MSFT = 1.1% of EV (realistic structural positioning difference)
                    - This represents long-term IR quality differences built over years, not quarterly achievements

                    💡 **To see quarterly contributions:** Run analysis for {previous_quarter if previous_quarter else 'previous quarter'} first,
                    then run for {selected_quarter}. The system will automatically calculate quarter-over-quarter changes.

                    **Understanding these numbers:**
                    - **Positive values:** Your IR positioning is above peer average (structural advantage)
                    - **Negative values:** Your IR positioning is below peer average (improvement opportunity)
                    - **As % of EV:** Shows the gap is capped at realistic academic bounds (5-15% of firm value over long term)
                    """)

                st.markdown("---")
                # Per-Ticker $/IRCI Point Table (Most Important)
                st.markdown("**Per-Ticker Dollar Value per IRCI Point:**")
                st.dataframe(
                    dollar_value_df[['ticker', 'irci_composite_pct', 'company_$/irci_pt', 'irci_gap_to_top', 'market_cap_gap_regression']].rename(columns={
                        'ticker': 'Ticker',
                        'irci_composite_pct': 'IRCI Score %',
                        'company_$/irci_pt': '🎯 Company $/IRCI Point',
                        'irci_gap_to_top': 'Gap to Top (pts)',
                        'market_cap_gap_regression': 'Potential $ Upside'
                    }).style.format({
                        'IRCI Score %': '{:.1f}%',
                        '🎯 Company $/IRCI Point': '${:,.0f}',
                        'Gap to Top (pts)': '{:.1f}',
                        'Potential $ Upside': '${:,.0f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                st.caption("\\$/IRCI Point = EV × 1% × R². Potential Upside capped at 20% of EV. Based on Bushee & Miller (2012), Agarwal et al. (2016).")

                # Additional detailed metrics
                with st.expander("📊 Additional Enterprise Value Metrics"):
                    st.dataframe(
                        dollar_value_df[['ticker', 'enterprise_value', 'company_ev_efficiency']].rename(columns={
                            'ticker': 'Ticker',
                            'enterprise_value': 'Enterprise Value ($)',
                            'company_ev_efficiency': 'EV Efficiency ($/IRCI)'
                        }).style.format({
                            'Enterprise Value ($)': '${:,.0f}',
                            'EV Efficiency ($/IRCI)': '${:,.0f}'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                    st.caption("""
                    📊 **Column Definitions:**

                    - Enterprise Value ($): Total enterprise value (market cap + debt - cash) for the company
                    - EV Efficiency ($/IRCI): Enterprise Value divided by IRCI score. Higher values = larger companies or companies with lower IRCI scores relative to their size
                    """)

                # Visualization: Scatter plot of EV vs IRCI with regression line
                fig = px.scatter(
                    dollar_value_df,
                    x='irci_composite_pct',
                    y='enterprise_value',
                    text='ticker',
                    title=f'Enterprise Value vs IRCI Score (R² = {r2_score:.2f})',
                    labels={'irci_composite_pct': 'IRCI Score (%)', 'enterprise_value': 'Enterprise Value ($)'},
                    color='company_$/irci_pt',
                    color_continuous_scale='Viridis',
                    size='enterprise_value',
                    hover_data={
                        'company_$/irci_pt': ':,.0f',
                        'irci_composite_pct': ':.1f',
                        'enterprise_value': ':,.0f',
                        'market_cap_gap_regression': ':,.0f'
                    }
                )
                fig.update_traces(textposition='top center')

                # Add regression line if R² is reasonable
                if r2_score > 0.1:
                    from scipy import stats
                    slope, intercept, _, _, _ = stats.linregress(
                        dollar_value_df['irci_composite_pct'],
                        dollar_value_df['enterprise_value']
                    )
                    x_range = [dollar_value_df['irci_composite_pct'].min(), dollar_value_df['irci_composite_pct'].max()]
                    y_range = [slope * x + intercept for x in x_range]
                    fig.add_scatter(
                        x=x_range,
                        y=y_range,
                        mode='lines',
                        name=f'Trend (${abs(slope):,.0f}/pt)',
                        line=dict(color='#ff0066', width=2, dash='dash')
                    )

                fig.update_layout(
                    height=500,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(30,33,48,0.5)',
                    font=dict(color='#fafafa'),
                    title_font=dict(color='#00d4ff'),
                    xaxis=dict(gridcolor='#2e3440'),
                    yaxis=dict(gridcolor='#2e3440'),
                    legend=dict(
                        bgcolor='rgba(30,33,48,0.8)',
                        bordercolor='#2e3440',
                        borderwidth=1
                    )
                )
                st.plotly_chart(fig, use_container_width=True)

                # Show regression stats inline if available
                if not dollar_value_df.empty:
                    from scipy import stats
                    slope, intercept, r_value, p_value, std_err = stats.linregress(
                        dollar_value_df['irci_composite_pct'],
                        dollar_value_df['enterprise_value']
                    )
                    r_squared = r_value ** 2
                    # Apply 10% floor for calculation (same as dial_insights.py)
                    r_squared_for_calc = max(r_squared, 0.10)
                    scaled_slope = abs(slope) * r_squared_for_calc
                    stat_sig = "✓" if p_value < 0.05 else "⚠️"
                    floor_note = " (10% floor applied)" if r_squared < 0.10 else ""
                    st.caption(f"Regression: Raw slope \\${abs(slope):,.0f}/pt × R²={r_squared_for_calc:.2f}{floor_note} = \\${scaled_slope:,.0f}/pt (p={p_value:.3f} {stat_sig})")

        except Exception as e:
            st.warning(f"Could not compute dollar value metrics: {str(e)}")

        st.markdown("---")

        # Section 2: Dial Contribution Analysis
        st.markdown("#### 🎯 Dial Contribution Analysis")
        st.markdown("*Shows how much each dial contributes to the composite score for this peer group*")

        try:
            # Get current weights from sidebar
            current_weights = {
                'valuation': weight_valuation / 100,
                'liquidity': weight_liquidity / 100,
                'coverage': weight_coverage / 100,
                'sentiment': weight_trust / 100
            }

            contrib_df = compute_dial_contribution(df_composite_filtered, weights=current_weights)

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            avg_val_contrib = contrib_df['val_contrib_pct'].mean()
            avg_liq_contrib = contrib_df['liq_contrib_pct'].mean()
            avg_cov_contrib = contrib_df['cov_contrib_pct'].mean()
            avg_sent_contrib = contrib_df['sent_contrib_pct'].mean()

            col1.metric(
                "Avg Valuation Contribution",
                f"{avg_val_contrib:.1f}%",
                help="Average percentage of composite score from Valuation dial"
            )
            col2.metric(
                "Avg Liquidity Contribution",
                f"{avg_liq_contrib:.1f}%",
                help="Average percentage of composite score from Liquidity dial"
            )
            col3.metric(
                "Avg Coverage Contribution",
                f"{avg_cov_contrib:.1f}%",
                help="Average percentage of composite score from Coverage dial"
            )
            col4.metric(
                "Avg Trust Contribution",
                f"{avg_sent_contrib:.1f}%",
                help="Average percentage of composite score from Trust dial"
            )

            # Detailed contribution table
            st.markdown("**Detailed Contribution Breakdown:**")

            # Build column list conditionally to include quarter if present
            contrib_cols = ['ticker']
            contrib_rename = {'ticker': 'Ticker'}
            contrib_format = {}

            if 'quarter' in contrib_df.columns:
                contrib_cols.append('quarter')
                contrib_rename['quarter'] = 'Quarter'

            contrib_cols.extend(['irci_composite_pct', 'val_contrib_abs', 'liq_contrib_abs', 'cov_contrib_abs', 'sent_contrib_abs', 'dominant_dial', 'weakest_dial'])
            contrib_rename.update({
                'irci_composite_pct': 'Composite %',
                'val_contrib_abs': 'Val Points',
                'liq_contrib_abs': 'Liq Points',
                'cov_contrib_abs': 'Cov Points',
                'sent_contrib_abs': 'Trust Points',
                'dominant_dial': 'Strongest Dial',
                'weakest_dial': 'Weakest Dial'
            })
            contrib_format = {
                'Composite %': '{:.1f}%',
                'Val Points': '{:.1f}',
                'Liq Points': '{:.1f}',
                'Cov Points': '{:.1f}',
                'Trust Points': '{:.1f}'
            }

            st.dataframe(
                contrib_df[contrib_cols].rename(columns=contrib_rename).style.format(contrib_format),
                use_container_width=True,
                hide_index=True
            )

            # Stacked bar chart showing composition
            st.markdown("**Composite Score Composition by Dial:**")

            # Prepare data for stacked bar
            chart_data = contrib_df[['ticker', 'val_contrib_abs', 'liq_contrib_abs', 'cov_contrib_abs', 'sent_contrib_abs']].copy()
            chart_data = chart_data.melt(id_vars=['ticker'], var_name='Dial', value_name='Contribution')
            chart_data['Dial'] = chart_data['Dial'].map({
                'val_contrib_abs': 'Valuation',
                'liq_contrib_abs': 'Liquidity',
                'cov_contrib_abs': 'Coverage',
                'sent_contrib_abs': 'Trust'
            })

            fig = px.bar(
                chart_data,
                x='ticker',
                y='Contribution',
                color='Dial',
                title='Dial Contributions to Composite Score',
                labels={'Contribution': 'Contribution (points)', 'ticker': 'Company'},
                color_discrete_map={
                    'Valuation': '#00d4ff',
                    'Liquidity': '#00ff88',
                    'Coverage': '#ff9500',
                    'Trust': '#ff0066'
                }
            )
            fig.update_layout(
                barmode='stack',
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,33,48,0.5)',
                font=dict(color='#fafafa'),
                title_font=dict(color='#00d4ff'),
                xaxis=dict(gridcolor='#2e3440'),
                yaxis=dict(gridcolor='#2e3440'),
                legend=dict(
                    bgcolor='rgba(30,33,48,0.8)',
                    bordercolor='#2e3440',
                    borderwidth=1
                )
            )
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.warning(f"Could not compute dial contribution: {str(e)}")

        st.markdown("---")

        # Section 3: Applied Weights
        st.markdown("#### ⚖️ Applied Weights")

        # Show applied weights with auto-optimization status
        if st.session_state.get('weights_auto_optimized', False):
            r2 = st.session_state.get('optimization_r2', 0)
            st.success(f"✓ Weights auto-optimized based on peer group variance")

        weights_df = pd.DataFrame([
            {'Dial': 'Valuation', 'Weight': f"{current_weights['valuation']*100:.1f}%"},
            {'Dial': 'Liquidity', 'Weight': f"{current_weights['liquidity']*100:.1f}%"},
            {'Dial': 'Coverage', 'Weight': f"{current_weights['coverage']*100:.1f}%"},
            {'Dial': 'Trust', 'Weight': f"{current_weights['sentiment']*100:.1f}%"}
        ])
        st.dataframe(weights_df, use_container_width=True, hide_index=True)

        st.caption("Weights are auto-optimized on each analysis run based on peer group variance. Adjust manually in the sidebar if needed.")

    # SECTION 4 (or SECTION 3 if not multi-quarter): Playbook & Events
    if selected_section == "🎯 Playbook & Events":
        # Get selected subsection from session state
        selected_subsection = st.session_state.get('selected_subsection', "🎯 Playbook")

        # Event Timeline subsection
        if selected_subsection == "📅 Event Timeline":
            # Event Timeline / Calendar View
            from irci.event_timeline import (
                aggregate_timeline_events,
                create_calendar_view,
                UserNotesManager,
                create_impact_summary
            )
            from irci.coverage import _company_submissions, _cik_for_ticker
    
            # Get start/end dates for the selected quarter (for filtering events)
            if len(selected_quarters) == 1:
                timeline_start_date, timeline_end_date = quarter_to_dates(selected_quarters[0])
            else:
                # Multi-quarter mode: use the first quarter for timeline display
                timeline_start_date, timeline_end_date = quarter_to_dates(selected_quarters[0])
    
            # Use the timeline dates for event filtering
            start_date = timeline_start_date
            end_date = timeline_end_date
    
            st.markdown("#### 📅 Event Timeline & Calendar")
            st.markdown("*Track events, filings, news, and their impact on IRCI scores*")
    
            st.info("""
            📊 **Event Impact Methodology**: Individual event impacts are very small because dials measure quarterly aggregates.
            - News articles: ~0.00001-0.0001 IRCI points each (~1/100th of quarterly media tone)
            - SEC filings: ~0.0001-0.0005 IRCI points each (counted in aggregate for coverage dial)
            - Dollar impacts are **R²-scaled** and reflect that individual events are one of many factors
            """)
    
            # Company selector for timeline
            selected_timeline_ticker = st.selectbox(
                "Select company for timeline:",
                display_df['ticker'].tolist(),
                key='timeline_ticker'
            )
    
            # Manual Event Entry UI
            with st.expander("➕ Add Custom Corporate Event"):
                st.markdown("**Add events not captured automatically** (e.g., investor days, leadership changes, strategic announcements)")
    
                col_evt1, col_evt2 = st.columns(2)
    
                with col_evt1:
                    event_date = st.date_input(
                        "Event Date",
                        value=pd.to_datetime(end_date),
                        key='custom_event_date'
                    )
    
                    event_type_options = {
                        # Major Corporate Events
                        'Investor Day': 'investor_day',
                        'Analyst Day': 'analyst_day',
                        'CEO Change': 'ceo_change',
                        'CFO Change': 'cfo_change',
                        'Director Change': 'director_change',
                        'Earnings Call': 'earnings_call',
                        'Strategic Announcement': 'strategic_announcement',
                        'Dividend Announcement': 'dividend_announcement',
                        'Buyback Announcement': 'buyback_announcement',
                        # Daily IR Activities
                        '🌐 IR Website Improvement': 'ir_website_improvement',
                        '📺 Advertising Campaign': 'advertising_campaign',
                        '📰 Press Release Program': 'press_release_program',
                        '📱 Social Media Campaign': 'social_media_campaign',
                        '🎤 Conference Presentation': 'conference_presentation',
                        '📰 Analyst Coverage Initiation': 'analyst_coverage_initiation',
                        # Other
                        'Other': 'other'
                    }
    
                    event_type_label = st.selectbox(
                        "Event Type",
                        options=list(event_type_options.keys()),
                        key='custom_event_type'
                    )
    
                with col_evt2:
                    event_description = st.text_input(
                        "Event Description",
                        placeholder="e.g., Annual Investor Day in NYC",
                        key='custom_event_description'
                    )
    
                    # Event-specific metadata
                    event_sentiment = st.slider(
                        "Event Sentiment",
                        min_value=-1.0,
                        max_value=1.0,
                        value=0.0,
                        step=0.1,
                        help="For strategic announcements: -1 (very negative) to +1 (very positive)",
                        key='custom_event_sentiment'
                    )
    
                # Additional metadata based on event type
                event_metadata = {'sentiment': event_sentiment}
    
                if event_type_label in ['CEO Change', 'CFO Change']:
                    col_meta1, col_meta2 = st.columns(2)
                    with col_meta1:
                        succession_type = st.selectbox(
                            "Succession Type",
                            options=['planned_inside', 'outside', 'unknown'],
                            help="Internal promotion vs. external hire",
                            key='custom_succession_type'
                        )
                        event_metadata['succession_type'] = succession_type
    
                    with col_meta2:
                        forced = st.checkbox("Forced Departure", key='custom_forced')
                        event_metadata['forced'] = forced
    
                elif event_type_label == 'Dividend Announcement':
                    dividend_change = st.number_input(
                        "Dividend Change (%)",
                        value=0.0,
                        help="% change in dividend (positive = increase, negative = cut)",
                        key='custom_dividend_change'
                    )
                    event_metadata['dividend_change_pct'] = dividend_change
    
                # Store button
                if st.button("➕ Add Event to Timeline", use_container_width=True):
                    # Initialize custom events in session state
                    if 'custom_events' not in st.session_state:
                        st.session_state['custom_events'] = []
    
                    custom_event = {
                        'ticker': selected_timeline_ticker,
                        'date': pd.to_datetime(event_date),
                        'event_type': event_type_options[event_type_label],
                        'description': event_description or event_type_label,
                        'event_metadata': event_metadata,
                        'source': 'user_entry'
                    }
    
                    st.session_state['custom_events'].append(custom_event)
                    st.success(f"✅ Added {event_type_label} event for {selected_timeline_ticker} on {event_date}")
                    st.rerun()
    
                # Display existing custom events
                if 'custom_events' in st.session_state and st.session_state['custom_events']:
                    ticker_custom_events = [e for e in st.session_state['custom_events'] if e['ticker'] == selected_timeline_ticker]
    
                    if ticker_custom_events:
                        st.markdown("**Custom Events for this Ticker:**")
                        for idx, evt in enumerate(ticker_custom_events):
                            col_del1, col_del2 = st.columns([4, 1])
                            with col_del1:
                                st.text(f"• {evt['date'].strftime('%Y-%m-%d')}: {evt['description']}")
                            with col_del2:
                                if st.button("🗑️", key=f"delete_event_{idx}"):
                                    st.session_state['custom_events'].remove(evt)
                                    st.rerun()
    
            try:
                # Initialize notes manager
                if 'notes_manager' not in st.session_state:
                    st.session_state['notes_manager'] = UserNotesManager()
    
                notes_mgr = st.session_state['notes_manager']
    
                # Get SEC filings data for this ticker
                s = Settings.load()
                cik = _cik_for_ticker(selected_timeline_ticker, s)
                sec_filings_df = None
    
                # Get news data from session state (fetched during analysis)
                news_df = st.session_state.get('news_df', None)
    
                if cik:
                    try:
                        subs = _company_submissions(cik, s)
                        if not subs.empty and 'filingDate' in subs.columns:
                            # Convert to our timeline format
                            sec_filings_df = pd.DataFrame({
                                'ticker': selected_timeline_ticker,
                                'date': pd.to_datetime(subs['filingDate']),
                                'event_type': subs['form'],
                                'description': subs['form'] + ' Filing',
                                'accession_number': subs.get('accessionNumber', '')
                            })
                            # Filter for date range
                            sec_filings_df = sec_filings_df[
                                (sec_filings_df['date'] >= start_date) &
                                (sec_filings_df['date'] <= end_date)
                            ]
                    except Exception as e:
                        st.info(f"Note: Could not fetch SEC filings: {e}")
    
                # Prepare weights dict to pass to timeline
                current_weights = {
                    'valuation': weight_valuation / 100,
                    'liquidity': weight_liquidity / 100,
                    'coverage': weight_coverage / 100,
                    'sentiment': weight_trust / 100
                }
    
                # Get company-specific $/IRCI point for this ticker
                company_dollar_per_irci_pt = None
                try:
                    from irci.dial_insights import compute_dollar_value_per_irci_point
                    dollar_value_df = compute_dollar_value_per_irci_point(df_composite_filtered, df_val_filtered)
                    if not dollar_value_df.empty:
                        ticker_dollar_data = dollar_value_df[dollar_value_df['ticker'] == selected_timeline_ticker]
                        if not ticker_dollar_data.empty:
                            company_dollar_per_irci_pt = ticker_dollar_data['company_$/irci_pt'].iloc[0]
                except Exception as e:
                    st.info(f"Note: Could not calculate $/IRCI point: {e}")
    
                # Display the company's $/IRCI point value for transparency with example calculation
                if company_dollar_per_irci_pt is not None:
                    # Calculate example impact for a single positive news article
                    # Note: Individual articles have small impacts because the Trust dial aggregates
                    # 50-100+ articles per quarter. Each article is ~1/100th of the quarterly media tone.
                    example_sentiment = 0.6  # Moderately positive news
                    example_dial_impact = example_sentiment * 0.0005  # 0.03% of Trust dial (~1/100th of quarterly coverage)
                    example_irci_impact = example_dial_impact * current_weights['sentiment']  # Tiny IRCI impact
                    example_dollar_impact = example_irci_impact * company_dollar_per_irci_pt
    
                    st.info(f"""
                    💰 **{selected_timeline_ticker} Impact Calculation Parameters (R²-scaled)**:
                    - Company \\$/IRCI Point: **\\${company_dollar_per_irci_pt:,.0f}**
                    - Example: Single positive news article (sentiment +0.6) → +{example_irci_impact:.6f} IRCI pts → **\\${example_dollar_impact:,.0f}** impact
    
                    **Note**: Individual events show small impacts because dials measure quarterly aggregates:
                    - Trust dial aggregates 50-100+ articles → each is ~1/100th of media tone component
                    - Media tone is 30% of Trust dial → each article ≈ 0.3% of Trust dial
                    - Quarterly aggregate patterns drive the dial scores, not single events
                    """)
    
                # Aggregate timeline events
                timeline_df = aggregate_timeline_events(
                    ticker=selected_timeline_ticker,
                    start_date=start_date,
                    end_date=end_date,
                    df_composite=df_composite_filtered,
                    df_val=df_val_filtered,
                    df_cov=df_cov_filtered,
                    df_liq=df_liq_filtered,
                    df_trust=df_trust_filtered,
                    news_df=news_df,
                    sec_filings_df=sec_filings_df,
                    weights=current_weights,
                    company_dollar_per_irci_pt=company_dollar_per_irci_pt
                )
    
                # Merge custom events from session state
                if 'custom_events' in st.session_state and st.session_state['custom_events']:
                    from irci.event_timeline import calculate_event_irci_impact
    
                    ticker_custom_events = [e for e in st.session_state['custom_events']
                                           if e['ticker'] == selected_timeline_ticker]
    
                    custom_events_list = []
                    for evt in ticker_custom_events:
                        # Calculate impact for this custom event
                        impact = calculate_event_irci_impact(
                            event_date=evt['date'].strftime('%Y-%m-%d'),
                            event_type=evt['event_type'],
                            df_composite=df_composite_filtered,
                            df_val=df_val_filtered,
                            ticker=selected_timeline_ticker,
                            sentiment_score=evt['event_metadata'].get('sentiment', 0.0),
                            weights=current_weights,
                            company_dollar_per_irci_pt=company_dollar_per_irci_pt,
                            event_metadata=evt['event_metadata']
                        )
    
                        custom_events_list.append({
                            'date': pd.to_datetime(evt['date']),
                            'event_type': evt['event_type'],
                            'description': evt['description'],
                            'headline': evt['description'],
                            'sentiment_score': evt['event_metadata'].get('sentiment', 0.0),
                            'irci_impact': impact['irci_impact'],
                            'dollar_impact': impact['dollar_impact'],
                            'impact_confidence': impact['confidence'],
                            'affected_dials': ', '.join(impact['affected_dials']),
                            'ticker': selected_timeline_ticker,
                            'source': 'User Entry'
                        })
    
                    if custom_events_list:
                        custom_df = pd.DataFrame(custom_events_list)
                        # Merge with timeline_df
                        timeline_df = pd.concat([timeline_df, custom_df], ignore_index=True)
                        # Sort by date
                        timeline_df = timeline_df.sort_values('date')

                # Merge auto-fetched corporate events from session state
                corporate_events_df = st.session_state.get('corporate_events_df')
                if corporate_events_df is not None and not corporate_events_df.empty:
                    from irci.event_timeline import calculate_event_irci_impact

                    # Filter for selected ticker
                    ticker_corp_events = corporate_events_df[
                        corporate_events_df['ticker'] == selected_timeline_ticker
                    ].copy()

                    if not ticker_corp_events.empty:
                        corp_events_list = []
                        for _, evt in ticker_corp_events.iterrows():
                            # Calculate impact for this corporate event
                            sentiment = evt.get('dividend_change_pct', 0) / 100 if evt.get('event_type') == 'dividend_announcement' else 0.0
                            if evt.get('event_type') == 'earnings_call':
                                # Try to derive sentiment from beat/miss
                                if 'Beat' in str(evt.get('description', '')):
                                    sentiment = 0.3
                                elif 'Missed' in str(evt.get('description', '')):
                                    sentiment = -0.3

                            impact = calculate_event_irci_impact(
                                event_date=pd.to_datetime(evt['date']).strftime('%Y-%m-%d'),
                                event_type=evt['event_type'],
                                df_composite=df_composite_filtered,
                                df_val=df_val_filtered,
                                ticker=selected_timeline_ticker,
                                sentiment_score=sentiment,
                                weights=current_weights,
                                company_dollar_per_irci_pt=company_dollar_per_irci_pt,
                                event_metadata=evt.get('event_metadata', {}) if isinstance(evt.get('event_metadata'), dict) else {}
                            )

                            corp_events_list.append({
                                'date': pd.to_datetime(evt['date']),
                                'event_type': evt['event_type'],
                                'description': evt.get('description', evt['event_type'].replace('_', ' ').title()),
                                'headline': evt.get('description', evt['event_type'].replace('_', ' ').title()),
                                'sentiment_score': sentiment,
                                'irci_impact': impact['irci_impact'],
                                'dollar_impact': impact['dollar_impact'],
                                'impact_confidence': impact['confidence'],
                                'affected_dials': ', '.join(impact['affected_dials']),
                                'ticker': selected_timeline_ticker,
                                'source': evt.get('source', 'FMP API').replace('_', ' ').title()
                            })

                        if corp_events_list:
                            corp_df = pd.DataFrame(corp_events_list)
                            # Check for duplicates (same date + event_type already in timeline)
                            if not timeline_df.empty:
                                existing_keys = set(zip(
                                    timeline_df['date'].dt.date,
                                    timeline_df['event_type']
                                ))
                                corp_df = corp_df[~corp_df.apply(
                                    lambda r: (r['date'].date(), r['event_type']) in existing_keys, axis=1
                                )]
                            if not corp_df.empty:
                                timeline_df = pd.concat([timeline_df, corp_df], ignore_index=True)
                                timeline_df = timeline_df.sort_values('date')

                # Display impact summary
                st.markdown("**📊 Event Impact Summary**")
                impact_summary = create_impact_summary(timeline_df, selected_timeline_ticker)
    
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Events", impact_summary['total_events'])
                col2.metric(
                    "Total IRCI Impact",
                    f"{impact_summary['total_irci_impact']:+.4f} pts",
                    help="Estimated cumulative impact on IRCI score from all events"
                )
                col3.metric(
                    "Total $ Impact",
                    f"${impact_summary['total_dollar_impact']:+,.0f}",
                    help="Estimated cumulative dollar value impact from all events"
                )
    
                # Calendar view
                st.markdown("---")
                st.markdown("**📅 Calendar View**")
    
                if not timeline_df.empty:
                    calendar_df = create_calendar_view(timeline_df, start_date, end_date)
    
                    # Keep numeric columns for proper sorting
                    calendar_display = calendar_df[['date', 'num_events', 'event_types', 'total_irci_impact', 'total_dollar_impact', 'headlines']].copy()

                    # Format numeric columns as strings with proper formatting
                    def format_dollar(val):
                        if pd.isna(val) or val == 0:
                            return "$0"
                        try:
                            val_float = float(val)
                            if abs(val_float) >= 1e9:
                                return f"${val_float/1e9:+,.2f}B"
                            elif abs(val_float) >= 1e6:
                                return f"${val_float/1e6:+,.2f}M"
                            elif abs(val_float) >= 1e3:
                                return f"${val_float/1e3:+,.1f}K"
                            else:
                                return f"${val_float:+,.0f}"
                        except (ValueError, TypeError):
                            return "N/A"

                    def format_irci(val):
                        if pd.isna(val):
                            return "N/A"
                        try:
                            return f"{float(val):+.5f}"
                        except (ValueError, TypeError):
                            return "N/A"

                    calendar_display['irci_formatted'] = calendar_display['total_irci_impact'].apply(format_irci)
                    calendar_display['dollar_formatted'] = calendar_display['total_dollar_impact'].apply(format_dollar)

                    # Rename columns and select formatted versions
                    calendar_display = calendar_display.rename(columns={
                        'date': 'Date',
                        'num_events': '# Events',
                        'event_types': 'Event Types',
                        'irci_formatted': 'IRCI Impact',
                        'dollar_formatted': '$ Impact',
                        'headlines': 'Top Headlines'
                    })[['Date', '# Events', 'Event Types', 'IRCI Impact', '$ Impact', 'Top Headlines']]

                    # Display calendar as interactive table
                    st.dataframe(
                        calendar_display,
                        use_container_width=True,
                        hide_index=True
                    )
    
                    st.caption("""
                    📊 **Calendar Note**: Each row shows the SUM of all events on that day.
                    - If 20 news articles occur on one day, their impacts are added together
                    - Individual events have tiny impacts (~0.00001-0.0005 IRCI points each)
                    - For large companies, even tiny IRCI impacts can translate to \\$100K-\\$1M due to high \\$/IRCI point
                    - This shows why quarterly aggregate analysis matters more than individual events
                    """)
                else:
                    st.info("No events found for this period. Try uploading news data or check the date range.")
    
                # Detailed event timeline
                st.markdown("---")
                st.markdown("**🔍 Detailed Event Timeline**")
    
                if not timeline_df.empty:
                    # Create a simpler display without complex styling that causes issues
                    display_timeline = timeline_df[['date', 'event_type', 'description', 'irci_impact', 'dollar_impact', 'affected_dials']].copy()

                    # Add a color indicator column instead of row styling
                    def get_color_indicator(row):
                        event_type = row['event_type']
                        sentiment = row.get('sentiment_score', 0) if 'sentiment_score' in timeline_df.columns else 0

                        if event_type == 'news':
                            if sentiment > 0.2:
                                return '🟢'
                            elif sentiment < -0.2:
                                return '🔴'
                            else:
                                return '📰'
                        elif event_type in ['10-Q', '10-K', '8-K']:
                            return '🔵'
                        elif event_type == 'investor_day':
                            return '🎯'
                        elif event_type == 'analyst_day':
                            return '📈'
                        elif event_type == 'ceo_change':
                            return '👔'
                        elif event_type == 'cfo_change':
                            return '💼'
                        elif event_type == 'director_change':
                            return '👥'
                        elif event_type == 'earnings_call':
                            return '📞'
                        elif event_type == 'strategic_announcement':
                            return '🎪'
                        elif event_type == 'dividend_announcement':
                            return '💵'
                        elif event_type == 'buyback_announcement':
                            return '🔄'
                        elif event_type == 'valuation_measurement':
                            return '💰'
                        elif event_type == 'liquidity_measurement':
                            return '💧'
                        elif event_type == 'coverage_measurement':
                            return '📊'
                        elif event_type == 'trust_measurement':
                            return '💭'
                        return '•'

                    display_timeline.insert(0, 'indicator', timeline_df.apply(get_color_indicator, axis=1))

                    # Format numeric columns as strings with proper formatting
                    def format_dollar(val):
                        if pd.isna(val) or val == 0:
                            return "$0"
                        try:
                            val_float = float(val)
                            if abs(val_float) >= 1e9:
                                return f"${val_float/1e9:+,.2f}B"
                            elif abs(val_float) >= 1e6:
                                return f"${val_float/1e6:+,.2f}M"
                            elif abs(val_float) >= 1e3:
                                return f"${val_float/1e3:+,.1f}K"
                            else:
                                return f"${val_float:+,.0f}"
                        except (ValueError, TypeError):
                            return "N/A"

                    def format_irci(val):
                        if pd.isna(val):
                            return "N/A"
                        try:
                            return f"{float(val):+.5f}"
                        except (ValueError, TypeError):
                            return "N/A"

                    display_timeline['irci_formatted'] = display_timeline['irci_impact'].apply(format_irci)
                    display_timeline['dollar_formatted'] = display_timeline['dollar_impact'].apply(format_dollar)

                    # Select and rename columns
                    display_timeline = display_timeline[['indicator', 'date', 'event_type', 'description', 'irci_formatted', 'dollar_formatted', 'affected_dials']].rename(columns={
                        'indicator': '',
                        'date': 'Date',
                        'event_type': 'Type',
                        'description': 'Description',
                        'irci_formatted': 'IRCI Impact',
                        'dollar_formatted': '$ Impact',
                        'affected_dials': 'Affected Dials'
                    })

                    # Display the dataframe
                    st.dataframe(
                        display_timeline,
                        use_container_width=True,
                        hide_index=True
                    )
    
                    st.caption("""
                    💡 **Event Indicators:**
                    🟢 Positive news | 🔴 Negative news | 🔵 SEC filings | 📰 Neutral news |
                    🎯 Investor Day | 📈 Analyst Day | 👔 CEO Change | 💼 CFO Change | 👥 Director Change |
                    📞 Earnings Call | 🎪 Strategic Announcement | 💵 Dividend | 🔄 Buyback |
                    💰 Valuation | 💧 Liquidity | 📰 Coverage | 💭 Trust
                    """)
    
                    # Calculation methodology and proof section
                    with st.expander("📐 **Impact Calculation Methodology & Proof**"):
                        st.markdown("""
                        ### How Individual Events Contribute to IRCI Scores
    
                        **Key Principle:** Individual events have TINY impacts. Quarterly AGGREGATE metrics drive dial scores.
    
                        ---
    
                        ### 📰 News Article Impact Calculation
    
                        **Step 1: Sentiment Score**
                        - News sentiment ranges from -1 (very negative) to +1 (very positive)
                        - Example: Positive earnings news might score +0.6
    
                        **Step 2: Dial Impact (Trust)**
                        - Individual article contributes to Trust dial: `dial_impact = sentiment × 0.0005`
                        - Example: +0.6 sentiment → +0.0003 points on Trust dial (0.03% of dial)
                        - **Why so tiny?** Trust dial aggregates 50-100+ articles per quarter
                          - Each article is ~1/100th of the quarterly media tone
                          - Media tone is 30% of Trust dial
                          - So each article ≈ 0.3% of Trust dial (we use 0.05% to be conservative)
    
                        **Step 3: IRCI Composite Impact**
                        - Trust dial has weight (default 15%): `irci_impact = dial_impact × weight`
                        - Example: +0.0003 Trust points × 0.15 weight = **+0.000045 IRCI points**
    
                        **Step 4: Dollar Impact (R²-Scaled)**
                        - Use company-specific \\$/IRCI point (already R²-scaled from regression)
                        - Example (mid-cap): +0.000045 IRCI pts × \\$150M/point = **\\$6,750**
                        - Example (large-cap): +0.000045 IRCI pts × \\$4B/point = **\\$180,000**
                        - R² scaling already applied (if R²=0.3, the \\$/point was reduced by 70%)
    
                        ---
    
                        ### 📊 SEC Filing Impact Calculation
    
                        **8-K Filing:**
                        - Dial impact: 0.001 points on Coverage dial (0.1% of dial)
                        - IRCI impact: 0.001 × 0.15 (coverage weight) = **0.00015 IRCI points**
                        - Dollar impact (mid-cap): 0.00015 × \\$150M/point = **\\$22,500**
                        - Dollar impact (large-cap): 0.00015 × \\$4B/point = **\\$600,000**
    
                        **10-Q or 10-K Filing:**
                        - Dial impact: 0.003 points on Coverage dial (0.3% of dial)
                        - IRCI impact: 0.003 × 0.15 = **0.00045 IRCI points**
                        - Dollar impact (mid-cap): 0.00045 × \\$150M/point = **\\$67,500**
                        - Dollar impact (large-cap): 0.00045 × \\$4B/point = **\\$1.8M**
    
                        **Why these values?** Coverage dial measures aggregate quarterly filing activity,
                        not individual filings. A typical company has 5-20 8-Ks per quarter.
    
                        ---
    
                        ### 🎯 Corporate Events Impact (Based on Academic Research)
    
                        **Investor Day:**
                        - Dial impacts: +2% Coverage, +1.5% Trust
                        - Estimated CAR: +2.0% (conservative, research shows up to +30% appreciation)
                        - Research: MZ Group 2024 study
                        - IRCI impact: ~0.005 points (varies by weights)
    
                        **CEO Change:**
                        - Planned inside succession: +0.5% Trust, CAR +0.5%
                        - Forced departure: -1% Trust, CAR -1.5%
                        - Outside hire: -0.5% Trust, CAR -0.5%
                        - Research: Clayton et al. (volatility increases), market reactions vary by type
    
                        **CFO Change:**
                        - Voluntary: -0.3% Trust, CAR -0.3%
                        - Forced: -0.8% Trust, CAR -1.0%
                        - Research: Negatively associated with earnings persistence
    
                        **Strategic Announcements:**
                        - Impact varies by sentiment (-1% to +1% Trust, +0.5% Coverage)
                        - CAR ranges from -2% to +2% depending on announcement type
    
                        **Dividend/Buyback:**
                        - Dividend increase: +0.5% Trust, CAR +1.0%
                        - Buyback announcement: +0.8% Trust, CAR +1.5%
                        - Dividend cut: -0.8% Trust, CAR -2.0%
    
                        **Note:** CAR (Cumulative Abnormal Return) estimates are based on event study methodology
                        from academic literature. Individual company results may vary.
    
                        ---
    
                        ### 🎯 Why Quarterly Aggregates Matter More
                        """)
    
                        # Calculate actual aggregate proof if we have news data
                        if 'sentiment_score' in timeline_df.columns:
                            news_events = timeline_df[timeline_df['event_type'] == 'news'].copy()
                            if not news_events.empty:
                                total_news = len(news_events)
                                avg_sentiment = news_events['sentiment_score'].mean() if 'sentiment_score' in news_events.columns else 0
                                total_individual_impact = news_events['irci_impact'].sum()
    
                                # Get actual trust score from dial
                                ticker_trust = df_trust[df_trust['ticker'] == selected_timeline_ticker]
                                if not ticker_trust.empty:
                                    actual_trust_score = ticker_trust['trust_pct'].iloc[0] if 'trust_pct' in ticker_trust.columns else None
                                    media_tone = ticker_trust['p_media_tone'].iloc[0] if 'p_media_tone' in ticker_trust.columns else None
    
                                    # Format values, handling None
                                    trust_score_str = f"{actual_trust_score:.1f}%" if actual_trust_score is not None else "N/A"
                                    media_tone_str = f"{media_tone:.1f}%" if media_tone is not None else "N/A"
    
                                    st.markdown(f"""
                                    **Actual Data for {selected_timeline_ticker} This Quarter:**
    
                                    - **Total News Articles**: {total_news}
                                    - **Average Sentiment**: {avg_sentiment:+.2f}
                                    - **Sum of Individual Impacts**: {total_individual_impact:+.2f} IRCI points
                                    - **Actual Trust Dial Score**: {trust_score_str} (measured from all factors)
                                    - **Media Tone Component**: {media_tone_str} (one of several Trust inputs)
    
                                    **📌 Key Insight:**
                                    The Trust dial is NOT just the sum of individual news impacts. It's computed from:
                                    1. Aggregate quarterly media tone (all {total_news} articles analyzed together)
                                    2. Event stability metrics
                                    3. Sentiment consistency over time
    
                                    Individual event impacts are **directional indicators**, not additive components.
                                    The actual dial score comes from quarterly aggregate analysis of all events together.
                                    """)
    
                        st.markdown("""
                        ---
    
                        ### 💰 R² Scaling: Why Dollar Impacts Are Conservative
    
                        **Regression Analysis:** We regress Enterprise Value ~ IRCI Score across peer group
    
                        **Example Calculation:**
                        - Raw regression slope: \\$500M per IRCI point
                        - R² value: 0.30 (IRCI explains 30% of EV variance)
                        - **R²-scaled slope**: \\$500M × 0.30 = **\\$150M per IRCI point**
    
                        **What This Means:**
                        - IR/IRCI is ONE of MANY factors affecting enterprise value
                        - Business fundamentals (revenue, earnings, growth) drive most value
                        - R² scaling ensures we don't overstate IR's contribution
                        - If R²=0.30, we reduce dollar estimates by 70% to be realistic
    
                        **Individual Event Example:**
                        - Event IRCI impact: +0.000045 points (single positive news article)
                        - Company \\$/IRCI: \\$150M/point (R²-scaled)
                        - Event dollar impact: +0.000045 × \\$150M = **\\$6,750**
                        - Without R² scaling: +0.000045 × \\$500M = \\$22,500 (OVERSTATED by 3.3x)
    
                        ---
    
                        ### ✅ Bottom Line
    
                        1. **Individual events = Tiny impacts** (~0.00001-0.0005 IRCI points, \\$1K-\\$100K for mid-caps, \\$50K-\\$2M for large-caps)
                        2. **Quarterly aggregates = Large impacts** (full dial scores determine total IRCI)
                        3. **R² scaling = Realistic estimates** (accounts for IR being one of many factors)
                        4. **Dollar impacts are planning ranges**, not guarantees
    
                        Individual events show what's happening day-to-day, but quarterly aggregate
                        metrics determine your final IRCI scores and relative peer ranking.
                        """)
    
                # User notes section
                st.markdown("---")
                st.markdown("**📝 Private Notes**")
                st.caption("Add non-publicly available information, insights, or reminders")
    
                # Add new note
                with st.expander("➕ Add New Note"):
                    note_date = st.date_input(
                        "Date",
                        value=pd.to_datetime(end_date).date(),
                        min_value=pd.to_datetime(start_date).date(),
                        max_value=pd.to_datetime(end_date).date(),
                        key='new_note_date'
                    )
                    note_category = st.selectbox(
                        "Category",
                        ["General", "Private Info", "Analysis", "Follow-up", "Meeting Notes"],
                        key='new_note_category'
                    )
                    note_text = st.text_area(
                        "Note",
                        placeholder="Enter your private note here...",
                        key='new_note_text'
                    )
    
                    if st.button("Save Note"):
                        if note_text.strip():
                            notes_mgr.add_note(
                                ticker=selected_timeline_ticker,
                                date=str(note_date),
                                note=note_text,
                                category=note_category
                            )
                            st.success("✓ Note saved!")
                            st.rerun()
                        else:
                            st.warning("Please enter a note before saving")
    
                # Display existing notes
                st.markdown("**Existing Notes:**")
                ticker_notes = notes_mgr.get_notes(selected_timeline_ticker)
    
                if ticker_notes:
                    for i, note in enumerate(ticker_notes):
                        with st.container():
                            col1, col2, col3 = st.columns([2, 4, 1])
                            col1.markdown(f"**{note['date']}**")
                            col2.markdown(f"*{note['category']}*")
                            col3.markdown(f"*{pd.to_datetime(note['timestamp']).strftime('%H:%M')}*")
                            st.markdown(note['note'])
                            st.markdown("---")
                else:
                    st.info("No notes yet. Add your first note above!")
    
            except Exception as e:
                st.error(f"Error loading timeline: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
        # Plan subsection (What-If Scenarios)
        elif selected_subsection == "📋 Plan":
            st.markdown("#### 🎲 What-If Scenario Planner")
            st.markdown("*Model hypothetical corporate events and see their projected impact on IRCI scores and enterprise value*")
    
            st.info("""
            💡 **How This Works**: Add hypothetical events (investor days, leadership changes, etc.) to see their projected impact.
            - Uses the same research-based calculations as the Event Timeline
            - Shows cumulative impact of multiple events
            - Compare current state vs. with planned initiatives
            - Plan your IR strategy and quantify expected outcomes
            """)
    
            # Company selector for what-if analysis
            selected_whatif_ticker = st.selectbox(
                "Select company for scenario planning:",
                display_df['ticker'].tolist(),
                key='whatif_ticker'
            )
    
            # Get current company data
            company_data = df_composite_filtered[df_composite_filtered['ticker'] == selected_whatif_ticker].iloc[0]
            current_irci = company_data['irci_composite_pct']
            current_valuation_pct = company_data.get('valuation_pct', 0)
            current_liquidity_pct = company_data.get('liquidity_pct', 0)
            current_coverage_pct = company_data.get('coverage_pct', 0)
            current_sentiment_pct = company_data.get('sentiment_pct', 0)

            # Calculate rank from sorted composite scores
            sorted_df = df_composite_filtered.sort_values('irci_composite_pct', ascending=False).reset_index(drop=True)
            company_rank = sorted_df[sorted_df['ticker'] == selected_whatif_ticker].index[0] + 1
            total_companies = len(sorted_df)

            # Get current EV
            ticker_val_data = df_val_filtered[df_val_filtered['ticker'] == selected_whatif_ticker]
            current_ev = ticker_val_data['enterprise_value'].iloc[0] if not ticker_val_data.empty else 0
    
            # Get company-specific $/IRCI point
            whatif_dollar_per_irci_pt = None
            try:
                from irci.dial_insights import compute_dollar_value_per_irci_point
                dollar_value_df = compute_dollar_value_per_irci_point(df_composite_filtered, df_val_filtered)
                if not dollar_value_df.empty:
                    ticker_dollar_data = dollar_value_df[dollar_value_df['ticker'] == selected_whatif_ticker]
                    if not ticker_dollar_data.empty:
                        whatif_dollar_per_irci_pt = ticker_dollar_data['company_$/irci_pt'].iloc[0]
            except Exception:
                pass
    
            # Display current state
            st.markdown("---")
            st.markdown("### 📊 Current State")
            col_curr1, col_curr2, col_curr3, col_curr4 = st.columns(4)
            col_curr1.metric("IRCI Composite", f"{current_irci:.1f}%")
            col_curr2.metric("Enterprise Value", f"${current_ev/1e9:.2f}B" if current_ev > 0 else "N/A")
            col_curr3.metric("$/IRCI Point", f"${whatif_dollar_per_irci_pt:,.0f}" if whatif_dollar_per_irci_pt else "N/A")
            col_curr4.metric("Rank", f"#{company_rank} of {total_companies}")
    
            # Event Value Menu - Show what each event type is worth
            st.markdown("---")
            st.markdown("### 💰 Event Value Menu")
            st.markdown(f"*Projected impact of each event type for **{selected_whatif_ticker}** based on current weights*")
    
            # Calculate impacts for all event types
            from irci.event_timeline import calculate_event_irci_impact
    
            # Get current weights
            current_weights = {
                'valuation': weight_valuation / 100,
                'liquidity': weight_liquidity / 100,
                'coverage': weight_coverage / 100,
                'sentiment': weight_trust / 100
            }
    
            # Define all event types with their configurations
            # CAR estimates based on published academic research
            event_menu_items = [
                # === Major Corporate Events ===
                # Investor Day: MZ Group (2024) shows +0.5% to +5% CAR, avg +30% appreciation in case studies
                ('Investor Day', 'investor_day', {}, "+2.0%", "+2% Cov, +1.5% Trust"),
                # Analyst Day: Similar to investor day but smaller sample; Francis et al. (1997)
                ('Analyst Day', 'analyst_day', {}, "+1.5%", "+1.5% Cov, +1% Trust"),

                # === Leadership Changes ===
                # CEO Change: Huson et al. (2004) "Managerial succession and firm performance" JFE
                # Inside succession: +0.5% CAR; Outside: -0.5%; Forced: -1.5%
                ('CEO Change (Inside)', 'ceo_change', {'succession_type': 'planned_inside', 'forced': False}, "+0.5%", "+0.5% Trust"),
                ('CEO Change (Outside)', 'ceo_change', {'succession_type': 'outside', 'forced': False}, "-0.5%", "-0.5% Trust"),
                ('CEO Change (Forced)', 'ceo_change', {'succession_type': 'unknown', 'forced': True}, "-1.5%", "-1% Trust"),
                # CFO Change: Mian (2001) "On the choice and replacement of CFOs" JFE
                ('CFO Change (Voluntary)', 'cfo_change', {'forced': False}, "-0.3%", "-0.3% Trust"),
                ('CFO Change (Forced)', 'cfo_change', {'forced': True}, "-1.0%", "-0.8% Trust"),
                # Director Change: moderate governance signal
                ('Director Change', 'director_change', {}, "-0.2%", "-0.2% Trust"),

                # === Capital Allocation Events ===
                # Dividend: Michaely et al. (1995) "Price reactions to dividend initiations" JF
                # Initiation: +3.4%, Increase >10%: +1.0%, Cut: -3.7%
                ('Dividend Initiation', 'dividend_announcement', {'dividend_change_pct': 100, 'is_initiation': True}, "+3.4%", "+1.5% Trust, +0.5% Val"),
                ('Dividend Increase (>10%)', 'dividend_announcement', {'dividend_change_pct': 15}, "+1.0%", "+0.5% Trust"),
                ('Dividend Cut', 'dividend_announcement', {'dividend_change_pct': -30}, "-3.7%", "-1.5% Trust"),
                # Buyback: Ikenberry et al. (1995) "Market underreaction to open market share repurchases" JFE
                # Avg CAR: +3.5% at announcement, +12% over 4 years
                ('Buyback Announcement', 'buyback_announcement', {}, "+3.5%", "+1.5% Trust, +0.8% Val"),

                # === Earnings & Guidance ===
                # Earnings: Ball & Brown (1968), Bernard & Thomas (1989) post-earnings drift
                ('Earnings Beat (>5%)', 'earnings_call', {'beat_pct': 0.05}, "+2.0%", "+1% Trust, +0.5% Val"),
                ('Earnings Miss (>5%)', 'earnings_call', {'beat_pct': -0.05}, "-2.5%", "-1% Trust, -0.5% Val"),
                ('Guidance Raise', 'strategic_announcement', {'sentiment': 0.8, 'announcement_type': 'guidance_raise'}, "+1.8%", "+0.8% Trust, +0.5% Cov"),
                ('Guidance Lower', 'strategic_announcement', {'sentiment': -0.8, 'announcement_type': 'guidance_lower'}, "-2.2%", "-1% Trust, -0.5% Cov"),

                # === Strategic Announcements ===
                ('M&A Announcement (Acquirer)', 'strategic_announcement', {'sentiment': 0.3, 'announcement_type': 'ma_acquirer'}, "-1.0%", "-0.5% Trust, +0.3% Cov"),
                ('M&A Announcement (Target)', 'strategic_announcement', {'sentiment': 0.9, 'announcement_type': 'ma_target'}, "+15-30%", "+5% Trust, +2% Cov"),
                ('Strategic Partnership', 'strategic_announcement', {'sentiment': 0.6, 'announcement_type': 'partnership'}, "+1.2%", "+0.6% Trust, +0.4% Cov"),
                ('Restructuring Announcement', 'strategic_announcement', {'sentiment': -0.4, 'announcement_type': 'restructuring'}, "-0.8%", "-0.4% Trust, +0.3% Cov"),

                # === Daily IR Activities ===
                # Grullon et al. (2004): 25% increase in advertising → +1.32% firm value
                ('Advertising Campaign', 'advertising_campaign', {}, "+1.3%", "+0.5% Cov, +0.3% Trust"),
                # Brunswick Group (2023): 80% of institutional investors use social media
                ('Social Media Campaign', 'social_media_campaign', {}, "+0.5%", "+0.6% Cov, +0.4% Liq"),
                # Francis et al. (1997): Conference presentations serve as price discovery
                ('Conference Presentation', 'conference_presentation', {}, "+0.8%", "+0.8% Cov, +0.4% Trust"),
                # Irvine (2003): Analyst initiation creates +1.02% abnormal return
                ('Analyst Coverage Initiation', 'analyst_coverage_initiation', {}, "+1.0%", "+1.5% Cov, +0.8% Liq, +0.5% Trust"),
                # Website/IR improvements: industry estimates
                ('IR Website Improvement', 'ir_website_improvement', {}, "+0.5%", "+0.4% Cov, +0.3% Trust"),
                ('Press Release Program', 'press_release_program', {}, "+0.5%", "+0.3% Cov, +0.2% Trust"),
                # Non-deal roadshow: Green et al. (2014) "Access to management and the informativeness"
                ('Non-Deal Roadshow', 'conference_presentation', {'is_roadshow': True}, "+0.6%", "+0.5% Cov, +0.3% Trust"),
            ]
    
            # Calculate impacts for each event type
            event_values = []
            for label, event_type, metadata, expected_car, dial_impact in event_menu_items:
                try:
                    impact = calculate_event_irci_impact(
                        event_date=pd.Timestamp.now().strftime('%Y-%m-%d'),
                        event_type=event_type,
                        df_composite=df_composite_filtered,
                        df_val=df_val_filtered,
                        ticker=selected_whatif_ticker,
                        weights=current_weights,
                        company_dollar_per_irci_pt=whatif_dollar_per_irci_pt,
                        event_metadata=metadata
                    )
                    event_values.append({
                        'Event Type': label,
                        'irci_impact_num': impact['irci_impact'],
                        'dollar_impact_num': impact['dollar_impact'],
                        'Expected CAR': expected_car,
                        'Affected Dials': dial_impact
                    })
                except Exception as e:
                    # If calculation fails, still show the event with expected values
                    event_values.append({
                        'Event Type': label,
                        'irci_impact_num': 0,
                        'dollar_impact_num': 0,
                        'Expected CAR': expected_car,
                        'Affected Dials': dial_impact
                    })

            # Create dataframe with numeric columns for sorting
            event_menu_df = pd.DataFrame(event_values)

            # Rename numeric columns for display and convert dollar to millions for better display
            event_menu_df['IRCI Impact (pts)'] = event_menu_df['irci_impact_num']
            event_menu_df['Dollar Impact ($M)'] = event_menu_df['dollar_impact_num'] / 1e6

            # Select columns for display
            display_cols = ['Event Type', 'IRCI Impact (pts)', 'Dollar Impact ($M)', 'Expected CAR', 'Affected Dials']

            # Display with numeric columns that can be sorted
            st.dataframe(
                event_menu_df[display_cols],
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "IRCI Impact (pts)": st.column_config.NumberColumn(
                        "IRCI Impact (pts)",
                        help="IRCI point impact for this event type",
                        format="%.3f"
                    ),
                    "Dollar Impact ($M)": st.column_config.NumberColumn(
                        "Dollar Impact ($M)",
                        help="Dollar impact in millions",
                        format="$%.2f"
                    ),
                }
            )
    
            st.caption("💡 **How to Use**: Review the projected impacts above, then add events to your scenario below to see cumulative effects.")
    
            # Research References
            with st.expander("📚 Research Methodology", expanded=False):
                st.markdown("""
**Event Impact Sources:**
| Event Type | Impact | Source |
|------------|--------|--------|
| Investor Days | +0.5% to +5% CAR | MZ Group (2024) |
| CEO Change (Inside) | +0.5% CAR | Succession literature |
| CEO Change (Forced) | -1.5% CAR | Succession literature |
| Analyst Coverage | +1.02% CAR | Irvine (2003), JFE |
| Buyback Announced | +1.5% CAR | Capital allocation research |
| Dividend Increase | +1.0% CAR | Signaling theory |

**Dollar Impact:** `IRCI Impact × Company $/IRCI Point` (R²-scaled for conservatism)

**Confidence Levels:** High (0.6-0.7) = strong evidence, Medium (0.4-0.5) = moderate, Low (0.1-0.3) = aggregate
                """)
    
    
            # Initialize scenario events in session state
            if 'scenario_events' not in st.session_state:
                st.session_state['scenario_events'] = []
    
            # Scenario Event Builder
            st.markdown("---")
            st.markdown("### ➕ Add Hypothetical Events to Scenario")
    
            with st.expander("📝 Event Builder", expanded=len(st.session_state['scenario_events']) == 0):
                col_evt1, col_evt2 = st.columns(2)
    
                with col_evt1:
                    scenario_event_type_options = {
                        # === Major Corporate Events ===
                        'Investor Day': 'investor_day',
                        'Analyst Day': 'analyst_day',
                        # === Leadership Changes ===
                        'CEO Change (Inside)': 'ceo_change_inside',
                        'CEO Change (Outside)': 'ceo_change_outside',
                        'CEO Change (Forced)': 'ceo_change_forced',
                        'CFO Change (Voluntary)': 'cfo_change_voluntary',
                        'CFO Change (Forced)': 'cfo_change_forced',
                        'Director Change': 'director_change',
                        # === Capital Allocation Events ===
                        'Dividend Initiation': 'dividend_initiation',
                        'Dividend Increase (>10%)': 'dividend_increase',
                        'Dividend Cut': 'dividend_cut',
                        'Buyback Announcement': 'buyback_announcement',
                        # === Earnings & Guidance ===
                        'Earnings Beat (>5%)': 'earnings_beat',
                        'Earnings Miss (>5%)': 'earnings_miss',
                        'Guidance Raise': 'guidance_raise',
                        'Guidance Lower': 'guidance_lower',
                        # === Strategic Announcements ===
                        'M&A Announcement (Acquirer)': 'ma_acquirer',
                        'M&A Announcement (Target)': 'ma_target',
                        'Strategic Partnership': 'strategic_partnership',
                        'Restructuring Announcement': 'restructuring',
                        # === Daily IR Activities ===
                        'Advertising Campaign': 'advertising_campaign',
                        'Social Media Campaign': 'social_media_campaign',
                        'Conference Presentation': 'conference_presentation',
                        'Analyst Coverage Initiation': 'analyst_coverage_initiation',
                        'IR Website Improvement': 'ir_website_improvement',
                        'Press Release Program': 'press_release_program',
                        'Non-Deal Roadshow': 'non_deal_roadshow',
                    }
    
                    scenario_event_label = st.selectbox(
                        "Event Type",
                        options=list(scenario_event_type_options.keys()),
                        key='scenario_event_type'
                    )
    
                    scenario_event_description = st.text_input(
                        "Event Description",
                        placeholder=f"e.g., Plan {scenario_event_label}",
                        value=scenario_event_label,
                        key='scenario_event_description'
                    )
    
                with col_evt2:
                    # Show expected impact preview
                    event_type_code = scenario_event_type_options[scenario_event_label]
    
                    # Map to base event type and metadata
                    if event_type_code == 'investor_day':
                        base_type = 'investor_day'
                        metadata = {}
                        expected_car = "+2.0%"
                        expected_dial = "+2% Cov, +1.5% Trust"
                    elif event_type_code == 'analyst_day':
                        base_type = 'analyst_day'
                        metadata = {}
                        expected_car = "+1.5%"
                        expected_dial = "+1.5% Cov, +1% Trust"
                    elif event_type_code == 'ceo_change_inside':
                        base_type = 'ceo_change'
                        metadata = {'succession_type': 'planned_inside', 'forced': False}
                        expected_car = "+0.5%"
                        expected_dial = "+0.5% Trust"
                    elif event_type_code == 'ceo_change_outside':
                        base_type = 'ceo_change'
                        metadata = {'succession_type': 'outside', 'forced': False}
                        expected_car = "-0.5%"
                        expected_dial = "-0.5% Trust"
                    elif event_type_code == 'ceo_change_forced':
                        base_type = 'ceo_change'
                        metadata = {'succession_type': 'unknown', 'forced': True}
                        expected_car = "-1.5%"
                        expected_dial = "-1% Trust"
                    elif event_type_code == 'cfo_change_voluntary':
                        base_type = 'cfo_change'
                        metadata = {'forced': False}
                        expected_car = "-0.3%"
                        expected_dial = "-0.3% Trust"
                    elif event_type_code == 'cfo_change_forced':
                        base_type = 'cfo_change'
                        metadata = {'forced': True}
                        expected_car = "-1.0%"
                        expected_dial = "-0.8% Trust"
                    elif event_type_code == 'director_change':
                        base_type = 'director_change'
                        metadata = {}
                        expected_car = "-0.2%"
                        expected_dial = "-0.2% Trust"
                    # === Capital Allocation Events ===
                    elif event_type_code == 'dividend_initiation':
                        base_type = 'dividend_announcement'
                        metadata = {'dividend_change_pct': 100, 'is_initiation': True}
                        expected_car = "+3.4%"
                        expected_dial = "+1.5% Trust, +0.5% Val"
                    elif event_type_code == 'dividend_increase':
                        base_type = 'dividend_announcement'
                        metadata = {'dividend_change_pct': 15}
                        expected_car = "+1.0%"
                        expected_dial = "+0.5% Trust"
                    elif event_type_code == 'dividend_cut':
                        base_type = 'dividend_announcement'
                        metadata = {'dividend_change_pct': -30}
                        expected_car = "-3.7%"
                        expected_dial = "-1.5% Trust"
                    elif event_type_code == 'buyback_announcement':
                        base_type = 'buyback_announcement'
                        metadata = {}
                        expected_car = "+3.5%"
                        expected_dial = "+1.5% Trust, +0.8% Val"
                    # === Earnings & Guidance ===
                    elif event_type_code == 'earnings_beat':
                        base_type = 'earnings_call'
                        metadata = {'beat_pct': 0.05}
                        expected_car = "+2.0%"
                        expected_dial = "+1% Trust, +0.5% Val"
                    elif event_type_code == 'earnings_miss':
                        base_type = 'earnings_call'
                        metadata = {'beat_pct': -0.05}
                        expected_car = "-2.5%"
                        expected_dial = "-1% Trust, -0.5% Val"
                    elif event_type_code == 'guidance_raise':
                        base_type = 'strategic_announcement'
                        metadata = {'sentiment': 0.8, 'announcement_type': 'guidance_raise'}
                        expected_car = "+1.8%"
                        expected_dial = "+0.8% Trust, +0.5% Cov"
                    elif event_type_code == 'guidance_lower':
                        base_type = 'strategic_announcement'
                        metadata = {'sentiment': -0.8, 'announcement_type': 'guidance_lower'}
                        expected_car = "-2.2%"
                        expected_dial = "-1% Trust, -0.5% Cov"
                    # === Strategic Announcements ===
                    elif event_type_code == 'ma_acquirer':
                        base_type = 'strategic_announcement'
                        metadata = {'sentiment': 0.3, 'announcement_type': 'ma_acquirer'}
                        expected_car = "-1.0%"
                        expected_dial = "-0.5% Trust, +0.3% Cov"
                    elif event_type_code == 'ma_target':
                        base_type = 'strategic_announcement'
                        metadata = {'sentiment': 0.9, 'announcement_type': 'ma_target'}
                        expected_car = "+15-30%"
                        expected_dial = "+5% Trust, +2% Cov"
                    elif event_type_code == 'strategic_partnership':
                        base_type = 'strategic_announcement'
                        metadata = {'sentiment': 0.6, 'announcement_type': 'partnership'}
                        expected_car = "+1.2%"
                        expected_dial = "+0.6% Trust, +0.4% Cov"
                    elif event_type_code == 'restructuring':
                        base_type = 'strategic_announcement'
                        metadata = {'sentiment': -0.4, 'announcement_type': 'restructuring'}
                        expected_car = "-0.8%"
                        expected_dial = "-0.4% Trust, +0.3% Cov"
                    # === Daily IR Activities ===
                    elif event_type_code == 'advertising_campaign':
                        base_type = 'advertising_campaign'
                        metadata = {}
                        expected_car = "+1.3%"
                        expected_dial = "+0.5% Cov, +0.3% Trust"
                    elif event_type_code == 'social_media_campaign':
                        base_type = 'social_media_campaign'
                        metadata = {}
                        expected_car = "+0.5%"
                        expected_dial = "+0.6% Cov, +0.4% Liq"
                    elif event_type_code == 'conference_presentation':
                        base_type = 'conference_presentation'
                        metadata = {}
                        expected_car = "+0.8%"
                        expected_dial = "+0.8% Cov, +0.4% Trust"
                    elif event_type_code == 'analyst_coverage_initiation':
                        base_type = 'analyst_coverage_initiation'
                        metadata = {}
                        expected_car = "+1.0%"
                        expected_dial = "+1.5% Cov, +0.8% Liq, +0.5% Trust"
                    elif event_type_code == 'ir_website_improvement':
                        base_type = 'ir_website_improvement'
                        metadata = {}
                        expected_car = "+0.5%"
                        expected_dial = "+0.4% Cov, +0.3% Trust"
                    elif event_type_code == 'press_release_program':
                        base_type = 'press_release_program'
                        metadata = {}
                        expected_car = "+0.5%"
                        expected_dial = "+0.3% Cov, +0.2% Trust"
                    elif event_type_code == 'non_deal_roadshow':
                        base_type = 'conference_presentation'
                        metadata = {'is_roadshow': True}
                        expected_car = "+0.6%"
                        expected_dial = "+0.5% Cov, +0.3% Trust"
                    else:
                        base_type = 'other'
                        metadata = {}
                        expected_car = "0%"
                        expected_dial = "None"
    
                    st.metric("Expected CAR", expected_car, help="Cumulative Abnormal Return from research")
                    st.caption(f"**Dial Impact:** {expected_dial}")
    
                if st.button("➕ Add Event to Scenario", use_container_width=True, key='add_scenario_event'):
                    from irci.event_timeline import calculate_event_irci_impact
    
                    # Get current weights
                    current_weights = {
                        'valuation': weight_valuation / 100,
                        'liquidity': weight_liquidity / 100,
                        'coverage': weight_coverage / 100,
                        'sentiment': weight_trust / 100
                    }
    
                    # Calculate impact
                    impact = calculate_event_irci_impact(
                        event_date=pd.Timestamp.now().strftime('%Y-%m-%d'),
                        event_type=base_type,
                        df_composite=df_composite_filtered,
                        df_val=df_val_filtered,
                        ticker=selected_whatif_ticker,
                        weights=current_weights,
                        company_dollar_per_irci_pt=whatif_dollar_per_irci_pt,
                        event_metadata=metadata
                    )
    
                    scenario_event = {
                        'description': scenario_event_description,
                        'event_type': base_type,
                        'event_type_label': scenario_event_label,
                        'irci_impact': impact['irci_impact'],
                        'dollar_impact': impact['dollar_impact'],
                        'affected_dials': impact['affected_dials'],
                        'car_estimate': impact.get('car_estimate', 0),
                        'confidence': impact['confidence']
                    }
    
                    st.session_state['scenario_events'].append(scenario_event)
                    st.success(f"✅ Added {scenario_event_label} to scenario! Scroll down to see updated results.")
    
            # Display scenario events and cumulative impact
            if st.session_state['scenario_events']:
                st.markdown("---")
                st.markdown("### 📋 Current Scenario Events")
    
                scenario_df = pd.DataFrame(st.session_state['scenario_events'])
    
                for idx, evt in enumerate(st.session_state['scenario_events']):
                    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns([3, 2, 2, 2, 1])
    
                    with col_s1:
                        st.text(f"{idx+1}. {evt['description']}")
                    with col_s2:
                        st.text(f"IRCI: {evt['irci_impact']:+.4f}")
                    with col_s3:
                        st.text(f"$: ${evt['dollar_impact']:+,.0f}" if evt['dollar_impact'] != 0 else "$: N/A")
                    with col_s4:
                        st.text(f"CAR: {evt['car_estimate']:+.1f}%")
                    with col_s5:
                        if st.button("🗑️", key=f"delete_scenario_{idx}"):
                            st.session_state['scenario_events'].pop(idx)
                            st.rerun()
    
                # Calculate cumulative impact
                total_irci_impact = sum(evt['irci_impact'] for evt in st.session_state['scenario_events'])
                total_dollar_impact = sum(evt['dollar_impact'] for evt in st.session_state['scenario_events'])
                avg_car = sum(evt['car_estimate'] for evt in st.session_state['scenario_events']) / len(st.session_state['scenario_events'])
    
                # Project new state
                projected_irci = current_irci + total_irci_impact
                projected_ev = current_ev + total_dollar_impact if current_ev > 0 else None
    
                st.markdown("---")
                st.markdown("### 🎯 Projected Impact Summary")
    
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                col_sum1.metric(
                    "Total IRCI Impact",
                    f"{total_irci_impact:+.4f} pts",
                    help="Sum of all event impacts on IRCI composite score"
                )
                col_sum2.metric(
                    "Total Dollar Impact",
                    f"${total_dollar_impact:+,.0f}" if total_dollar_impact != 0 else "N/A",
                    help="Estimated change in enterprise value"
                )
                col_sum3.metric(
                    "Avg CAR",
                    f"{avg_car:+.1f}%",
                    help="Average Cumulative Abnormal Return across events"
                )
    
                # Before/After Comparison
                st.markdown("---")
                st.markdown("### 📊 Before vs. After Comparison")
    
                col_comp1, col_comp2, col_comp3 = st.columns(3)
    
                with col_comp1:
                    st.markdown("**Current State**")
                    st.metric("IRCI Score", f"{current_irci:.1f}%")
                    if current_ev > 0:
                        st.metric("Enterprise Value", f"${current_ev/1e9:.2f}B")
    
                with col_comp2:
                    st.markdown("**After Events**")
                    delta_irci = projected_irci - current_irci
                    st.metric("IRCI Score", f"{projected_irci:.1f}%", delta=f"{delta_irci:+.1f}")
                    if projected_ev:
                        delta_ev_pct = ((projected_ev - current_ev) / current_ev) * 100
                        st.metric("Enterprise Value", f"${projected_ev/1e9:.2f}B", delta=f"{delta_ev_pct:+.1f}%")
    
                with col_comp3:
                    st.markdown("**Change**")
                    st.metric("IRCI Change", f"{total_irci_impact:+.4f} pts")
                    if total_dollar_impact != 0:
                        st.metric("EV Change", f"${total_dollar_impact/1e9:+.2f}B")
    
                # Visualization of dial changes
                st.markdown("---")
                st.markdown("### 🎨 Dial Impact Breakdown")
    
                # Calculate dial-specific impacts
                dial_impacts = {
                    'Valuation': 0,
                    'Liquidity': 0,
                    'Coverage': 0,
                    'Trust': 0
                }
    
                for evt in st.session_state['scenario_events']:
                    for dial in evt['affected_dials']:
                        if dial in dial_impacts:
                            dial_impacts[dial] += evt['irci_impact'] / len(evt['affected_dials'])
    
                # Display as metrics
                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                col_d1.metric("Valuation", f"{current_valuation_pct:.1f}%", delta=f"{dial_impacts['Valuation']:+.2f}" if dial_impacts['Valuation'] != 0 else None)
                col_d2.metric("Liquidity", f"{current_liquidity_pct:.1f}%", delta=f"{dial_impacts['Liquidity']:+.2f}" if dial_impacts['Liquidity'] != 0 else None)
                col_d3.metric("Coverage", f"{current_coverage_pct:.1f}%", delta=f"{dial_impacts['Coverage']:+.2f}" if dial_impacts['Coverage'] != 0 else None)
                col_d4.metric("Trust", f"{current_sentiment_pct:.1f}%", delta=f"{dial_impacts['Trust']:+.2f}" if dial_impacts['Trust'] != 0 else None)
    
                # Action buttons
                st.markdown("---")
                col_action1, col_action2, col_action3 = st.columns(3)
    
                with col_action1:
                    if st.button("🗑️ Clear All Events", use_container_width=True):
                        st.session_state['scenario_events'] = []
                        st.rerun()
    
                with col_action2:
                    if st.button("💾 Save Scenario", use_container_width=True):
                        # Save to session state for later comparison
                        if 'saved_scenarios' not in st.session_state:
                            st.session_state['saved_scenarios'] = []
    
                        scenario_name = f"Scenario {len(st.session_state['saved_scenarios']) + 1}"
                        st.session_state['saved_scenarios'].append({
                            'name': scenario_name,
                            'ticker': selected_whatif_ticker,
                            'events': st.session_state['scenario_events'].copy(),
                            'total_irci_impact': total_irci_impact,
                            'total_dollar_impact': total_dollar_impact
                        })
                        st.success(f"✅ Saved as '{scenario_name}'")
    
                with col_action3:
                    if st.button("📋 Export to Notes", use_container_width=True):
                        # Could export scenario as a formatted note
                        st.info("💡 Feature coming soon: Export scenario to event timeline notes")
    
                # Show research methodology
                with st.expander("📚 Research Methodology"):
                    st.markdown("""
**How It Works:** Event dial impacts → weighted by dial weights → IRCI composite impact → $/IRCI point = Dollar impact

**Key Sources:** MZ Group 2024 (Investor Days), Irvine 2003 (Analyst Coverage), Grullon 2004 (Advertising), Brunswick 2023 (Social Media)

**Tips:** Model 5-7 events max per scenario. Use for planning comparisons, not predictions.
                    """)
    
            else:
                st.info("👆 Add events to your scenario using the Event Builder above to see projected impacts!")
    
        # Playbook subsection
        elif selected_subsection == "🎯 Playbook":
            # IR Playbook - Action recommendations based on dial scores
            st.markdown("#### 📋 IR Action Playbook")
            st.markdown("*Get specific action recommendations based on your IRCI dial performance*")
    
            st.info("""
            📚 **How This Works**: The playbook analyzes your dial scores and provides prioritized action items.
            - **High Priority**: Critical areas requiring immediate attention
            - **Medium Priority**: Important improvements for strategic focus
            - **Low Priority**: Optimization opportunities
            - **Quick Wins**: Actions you can implement quickly for immediate impact
            """)
    
            try:
                # Company selector for playbook
                playbook_ticker = st.selectbox(
                    "Select company for IR playbook:",
                    df_composite_filtered['ticker'].unique(),
                    key="playbook_ticker_select"
                )
    
                # Get dial scores for selected company
                company_row = df_composite_filtered[df_composite_filtered['ticker'] == playbook_ticker].iloc[0]
    
                dial_scores = {
                    'valuation': company_row.get('valuation_pct', 50),
                    'liquidity': company_row.get('liquidity_pct', 50),
                    'coverage': company_row.get('coverage_pct', 50),
                    'trust': company_row.get('sentiment_pct', 50)
                }
    
                # Calculate dollar value per IRCI point for this company
                company_dollar_per_point = None
                try:
                    from irci.dial_insights import compute_dollar_value_per_irci_point
                    dollar_value_df = compute_dollar_value_per_irci_point(df_composite_filtered, df_val_filtered)
                    if not dollar_value_df.empty:
                        company_data = dollar_value_df[dollar_value_df['ticker'] == playbook_ticker]
                        if not company_data.empty:
                            company_dollar_per_point = company_data['company_$/irci_pt'].iloc[0]
                except Exception:
                    pass  # Silently fail if dollar value can't be calculated
    
                # Generate playbook
                playbook = generate_playbook(dial_scores, df_composite, playbook_ticker)
    
                # Display summary
                st.markdown("---")
                st.markdown("### 📊 Executive Summary")
                st.markdown(playbook['summary'])
    
                # Show dial classifications
                st.markdown("#### Dial Performance Overview")
                col1, col2, col3, col4 = st.columns(4)
    
                classification_colors = {
                    'critical': '🔴',
                    'low': '🟠',
                    'medium': '🟡',
                    'high': '🟢'
                }
    
                with col1:
                    val_cls = playbook['dial_classifications']['valuation']
                    st.metric(
                        "💰 Valuation",
                        f"{dial_scores['valuation']:.1f}%",
                        delta=f"{classification_colors[val_cls]} {val_cls.capitalize()}"
                    )
    
                with col2:
                    liq_cls = playbook['dial_classifications']['liquidity']
                    st.metric(
                        "💧 Liquidity",
                        f"{dial_scores['liquidity']:.1f}%",
                        delta=f"{classification_colors[liq_cls]} {liq_cls.capitalize()}"
                    )
    
                with col3:
                    cov_cls = playbook['dial_classifications']['coverage']
                    st.metric(
                        "📰 Coverage",
                        f"{dial_scores['coverage']:.1f}%",
                        delta=f"{classification_colors[cov_cls]} {cov_cls.capitalize()}"
                    )
    
                with col4:
                    trust_cls = playbook['dial_classifications']['trust']
                    st.metric(
                        "💭 Trust",
                        f"{dial_scores['trust']:.1f}%",
                        delta=f"{classification_colors[trust_cls]} {trust_cls.capitalize()}"
                    )
    
                # Potential Value Improvements Section
                if company_dollar_per_point:
                    st.markdown("---")
                    st.markdown("### 💎 Potential Value Improvements")
                    st.markdown("*Conservative estimates of value you can add by improving each dial next quarter*")
    
                    st.info("""
                    **How to read these estimates:**
                    - **Conservative Range:** Based on peer benchmarking and industry research
                    - **Point Improvement:** Realistic quarterly improvement target for each dial
                    - **Estimated Value:** Dollar impact calculated using your company's $/IRCI point
                    - **Assumptions:** 2-5 point improvement for critical dials, 1-3 points for others
    
                    These are **planning estimates** to help prioritize IR investments, not guarantees.
                    """)
    
                    # Calculate improvement opportunities for each dial
                    improvements = []
                    dial_names = {
                        'valuation': ('💰 Valuation', weight_valuation / 100),
                        'liquidity': ('💧 Liquidity', weight_liquidity / 100),
                        'coverage': ('📰 Coverage', weight_coverage / 100),
                        'trust': ('💭 Trust', weight_trust / 100)
                    }
    
                    for dial, score in dial_scores.items():
                        dial_label, dial_weight = dial_names[dial]
                        classification = playbook['dial_classifications'][dial]
    
                        # Conservative improvement estimates based on classification
                        if classification == 'critical' and score < 40:
                            # Critical dials with very low scores have most improvement potential
                            min_improvement = 3
                            max_improvement = 8
                        elif classification == 'low' or score < 50:
                            # Below-average dials
                            min_improvement = 2
                            max_improvement = 5
                        elif score < 70:
                            # Average dials
                            min_improvement = 1
                            max_improvement = 3
                        else:
                            # Already strong dials
                            min_improvement = 0.5
                            max_improvement = 2
    
                        # Calculate IRCI impact (dial improvement × dial weight)
                        min_irci_impact = min_improvement * dial_weight
                        max_irci_impact = max_improvement * dial_weight
    
                        # Calculate dollar value range
                        min_value = min_irci_impact * company_dollar_per_point
                        max_value = max_irci_impact * company_dollar_per_point
    
                        improvements.append({
                            'dial': dial_label,
                            'current_score': score,
                            'classification': classification,
                            'min_improvement': min_improvement,
                            'max_improvement': max_improvement,
                            'min_value': min_value,
                            'max_value': max_value,
                            'priority': 1 if classification in ['critical', 'low'] else 2 if score < 70 else 3
                        })
    
                    # Sort by priority (critical/low first)
                    improvements.sort(key=lambda x: (x['priority'], -x['max_value']))
    
                    # Display as cards
                    for imp in improvements:
                        color = "🔴" if imp['classification'] == 'critical' else "🟠" if imp['classification'] == 'low' else "🟡" if imp['classification'] == 'medium' else "🟢"
    
                        with st.expander(f"{color} **{imp['dial']}** — **${imp['min_value']/1e6:.0f}M to ${imp['max_value']/1e6:.0f}M** potential value", expanded=imp['priority'] == 1):
                            col_left, col_right = st.columns([1, 1])
    
                            with col_left:
                                st.metric(
                                    "Current Score",
                                    f"{imp['current_score']:.1f}%",
                                    delta=f"{color} {imp['classification'].capitalize()}"
                                )
    
                            with col_right:
                                st.metric(
                                    "Quarterly Improvement Range",
                                    f"+{imp['min_improvement']:.1f} to +{imp['max_improvement']:.1f} pts"
                                )
    
                            st.markdown(f"""
                            **What this means:**
                            - By focusing on {imp['dial'].lower()} improvement initiatives next quarter, you could realistically gain **{imp['min_improvement']:.1f}-{imp['max_improvement']:.1f} points**
                            - This translates to an estimated **${imp['min_value']/1e6:.0f}M - ${imp['max_value']/1e6:.0f}M** in enterprise value impact
                            - Review the **{imp['dial'].split()[1]}** recommendations below for specific actions
                            """)
    
                    st.caption(f"""
                    💡 **About these estimates:**
                    - $/IRCI Point for {playbook_ticker}: ${company_dollar_per_point:,.0f}
                    - Improvement ranges based on peer analysis and classification severity
                    - Critical/low scoring dials have higher improvement potential
                    - Values are R²-scaled to reflect IR's partial influence on enterprise value
                    """)
    
                # Quick Wins section
                if playbook['quick_wins']:
                    st.markdown("---")
                    st.markdown("### ⚡ Quick Wins")
                    st.markdown("*Actions you can implement quickly for immediate impact*")
    
                    for rec in playbook['quick_wins'][:5]:  # Show top 5 quick wins
                        with st.expander(f"**{rec['action']}** ({rec['category']})", expanded=False):
                            st.markdown(rec['description'])
                            st.caption(f"Priority: {rec['priority'].upper()}")
    
                # All Recommendations by priority
                st.markdown("---")
                st.markdown("### 📋 All Recommendations")
    
                priority_tabs = st.tabs([
                    f"🔴 High Priority ({playbook['priority_counts']['high']})",
                    f"🟡 Medium Priority ({playbook['priority_counts']['medium']})",
                    f"🟢 Low Priority ({playbook['priority_counts']['low']})"
                ])
    
                def display_recommendation(rec):
                    """Helper function to display a recommendation with all evidence-backed fields"""
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{rec['action']}**")
                        with col2:
                            if rec.get('quick_win'):
                                st.caption("⚡ Quick Win")
    
                        st.markdown(f"*Category: {rec['category']}*")
                        st.markdown(f"**What:** {rec.get('what', '')}")
                        st.markdown(f"**How:** {rec['description']}")
    
                        # Show evidence-backed details in an expander
                        with st.expander("📊 Evidence & Impact Details"):
                            if rec.get('evidence'):
                                st.markdown(f"**📚 Research Evidence:**\n{rec['evidence']}")
                                st.markdown("")
    
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if rec.get('expected_impact'):
                                    st.markdown(f"**📈 Expected Impact:** {rec['expected_impact']}")
                                if rec.get('timeframe'):
                                    st.markdown(f"**⏱️ Timeframe:** {rec['timeframe']}")
    
                            with col_b:
                                if rec.get('benchmark'):
                                    st.markdown(f"**🎯 Benchmark:** {rec['benchmark']}")
    
                            if rec.get('tools'):
                                st.markdown(f"**🛠️ Tools & Platforms:** {rec['tools']}")
    
                            if rec.get('metrics'):
                                st.markdown(f"**📊 Metrics to Track:** {rec['metrics']}")
    
                        st.markdown("---")
    
                with priority_tabs[0]:
                    high_priority = [r for r in playbook['recommendations'] if r['priority'] == 'high']
                    if high_priority:
                        for rec in high_priority:
                            display_recommendation(rec)
                    else:
                        st.success("No high-priority action items. Great job!")
    
                with priority_tabs[1]:
                    medium_priority = [r for r in playbook['recommendations'] if r['priority'] == 'medium']
                    if medium_priority:
                        for rec in medium_priority:
                            display_recommendation(rec)
                    else:
                        st.info("No medium-priority items.")
    
                with priority_tabs[2]:
                    low_priority = [r for r in playbook['recommendations'] if r['priority'] == 'low']
                    if low_priority:
                        for rec in low_priority:
                            display_recommendation(rec)
                    else:
                        st.info("No low-priority items.")
    
                # Category breakdown
                st.markdown("---")
                st.markdown("### 📂 Recommendations by Dial")
    
                category_tabs = st.tabs(["💰 Valuation", "💧 Liquidity", "📰 Coverage", "💭 Trust"])
    
                for i, category in enumerate(['Valuation', 'Liquidity', 'Coverage', 'Trust']):
                    with category_tabs[i]:
                        category_recs = [r for r in playbook['recommendations'] if r['category'] == category]
                        if category_recs:
                            for rec in category_recs:
                                priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                                st.markdown(f"{priority_emoji[rec['priority']]} Priority")
                                display_recommendation(rec)
                        else:
                            st.success(f"Your {category} dial is performing well. No specific actions needed.")
    
            except Exception as e:
                st.error(f"Error generating playbook: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

            # Budget Optimizer Section (within Playbook)
            st.markdown("---")
            st.markdown("#### 💰 IR Budget Optimizer")
            st.caption("Quantum-ready optimization to maximize IRCI improvement within your budget")

            with st.expander("🔮 **Optimize IR Budget Allocation**", expanded=False):
                st.markdown("""
                This tool uses **QUBO (Quadratic Unconstrained Binary Optimization)** to find the optimal
                combination of IR initiatives that maximizes expected IRCI improvement within your budget.

                The optimizer considers:
                - **Expected IRCI improvement** per initiative
                - **Cost** and **staff hours** required
                - **Confidence levels** based on academic research
                - **Diminishing returns** for already-strong dials
                """)

                # Budget inputs
                budget_col1, budget_col2 = st.columns(2)
                with budget_col1:
                    ir_budget = st.number_input(
                        "IR Budget ($)",
                        min_value=10000,
                        max_value=5000000,
                        value=200000,
                        step=25000,
                        help="Total budget available for IR initiatives"
                    )
                with budget_col2:
                    max_hours = st.number_input(
                        "Max Staff Hours (optional)",
                        min_value=0,
                        max_value=5000,
                        value=0,
                        step=50,
                        help="Maximum staff hours available. Set to 0 for no limit."
                    )

                # Company selector
                budget_ticker = st.selectbox(
                    "Select company to optimize:",
                    df_composite['ticker'].unique(),
                    key="budget_ticker_select"
                )

                # Optimization method
                opt_method = st.radio(
                    "Optimization Method",
                    ["Auto (Recommended)", "Greedy by ROI", "Simulated Annealing", "Dynamic Programming"],
                    horizontal=True,
                    help="Auto selects the best method based on problem size"
                )
                method_map = {
                    "Auto (Recommended)": "auto",
                    "Greedy by ROI": "greedy_roi",
                    "Simulated Annealing": "simulated_annealing",
                    "Dynamic Programming": "dynamic_programming"
                }

                if st.button("🚀 Optimize Budget", type="primary", use_container_width=True):
                    with st.spinner("🔮 Optimizing IR budget allocation..."):
                        try:
                            # Get dollar value data if available
                            dollar_value_df = st.session_state.get('dollar_value_df', None)

                            result = optimize_ir_budget(
                                ticker=budget_ticker,
                                budget=ir_budget,
                                df_composite=df_composite,
                                df_valuation=df_val,
                                dollar_value_df=dollar_value_df,
                                max_hours=max_hours if max_hours > 0 else None,
                                method=method_map[opt_method]
                            )

                            # Display results
                            st.success(f"✓ Optimization complete using {result['method']} method")

                            # Key metrics
                            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                            with metric_col1:
                                st.metric(
                                    "Current IRCI",
                                    f"{result['current_irci']:.1f}",
                                    help="Current IRCI composite score"
                                )
                            with metric_col2:
                                st.metric(
                                    "Projected IRCI",
                                    f"{result['projected_irci']:.1f}",
                                    f"+{result['expected_improvement']:.1f} pts",
                                    help="Expected IRCI after implementing selected initiatives"
                                )
                            with metric_col3:
                                st.metric(
                                    "Budget Used",
                                    f"${result['total_cost']:,.0f}",
                                    f"{result['budget_utilization']*100:.0f}%",
                                    help="Total cost of selected initiatives"
                                )
                            with metric_col4:
                                st.metric(
                                    "Expected Value",
                                    f"${result['expected_value']/1e6:.0f}M",
                                    help="Expected enterprise value creation"
                                )

                            # Gap analysis
                            if result['gap_to_leader'] > 0:
                                st.progress(
                                    min(result['gap_closed_pct'] / 100, 1.0),
                                    text=f"Gap to Leader: Closing {result['gap_closed_pct']:.0f}% of {result['gap_to_leader']:.1f} pt gap"
                                )

                            # Selected initiatives table
                            st.markdown("##### 📋 Recommended Initiatives")

                            if result['selected']:
                                init_data = []
                                for init in result['selected']:
                                    init_data.append({
                                        'Initiative': init.name,
                                        'Dial': init.dial.title(),
                                        'Cost': f"${init.cost:,}",
                                        'Hours': init.time_hours,
                                        'Impact': f"+{init.expected_improvement:.1f} pts",
                                        'Confidence': f"{init.confidence*100:.0f}%",
                                        'Timeframe': f"{init.timeframe_months} mo",
                                        'Quick Win': "✓" if init.quick_win else ""
                                    })

                                init_df = pd.DataFrame(init_data)
                                st.dataframe(init_df, hide_index=True, use_container_width=True)

                                # Breakdown by dial
                                st.markdown("##### 📊 Investment by Dial")
                                dial_spend = {}
                                dial_impact = {}
                                for init in result['selected']:
                                    dial = init.dial.title()
                                    dial_spend[dial] = dial_spend.get(dial, 0) + init.cost
                                    dial_impact[dial] = dial_impact.get(dial, 0) + init.expected_improvement * init.confidence

                                dial_df = pd.DataFrame({
                                    'Dial': list(dial_spend.keys()),
                                    'Investment': [f"${v:,.0f}" for v in dial_spend.values()],
                                    'Expected Impact': [f"+{v:.1f} pts" for v in dial_impact.values()]
                                })
                                st.dataframe(dial_df, hide_index=True)

                                # Timeline view
                                st.markdown("##### 📅 Implementation Timeline")
                                quick_wins = [i for i in result['selected'] if i.quick_win]
                                medium_term = [i for i in result['selected'] if not i.quick_win and i.timeframe_months <= 6]
                                long_term = [i for i in result['selected'] if not i.quick_win and i.timeframe_months > 6]

                                timeline_col1, timeline_col2, timeline_col3 = st.columns(3)
                                with timeline_col1:
                                    st.markdown("**🚀 Quick Wins (1-3 mo)**")
                                    for init in quick_wins:
                                        st.caption(f"• {init.name}")
                                    if not quick_wins:
                                        st.caption("_None selected_")
                                with timeline_col2:
                                    st.markdown("**📈 Medium Term (3-6 mo)**")
                                    for init in medium_term:
                                        st.caption(f"• {init.name}")
                                    if not medium_term:
                                        st.caption("_None selected_")
                                with timeline_col3:
                                    st.markdown("**🎯 Long Term (6+ mo)**")
                                    for init in long_term:
                                        st.caption(f"• {init.name}")
                                    if not long_term:
                                        st.caption("_None selected_")

                            else:
                                st.warning("No initiatives selected within budget constraints.")

                            # Quantum status
                            if QUANTUM_BUDGET_AVAILABLE:
                                st.info("🔮 **Quantum Computing**: D-Wave solver available for large-scale optimization")
                            else:
                                st.caption("💡 _Quantum optimization available with D-Wave Leap API access_")

                        except Exception as e:
                            st.error(f"Error optimizing budget: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())

    # SECTION 5 (or SECTION 4 if not multi-quarter): AI Assistant
    if selected_section == "💬 AI Assistant":
        st.markdown("#### 💬 AI Assistant")

        # Check for Gemini API key
        s = Settings.load()
        if not s.gemini_api_key:
            st.warning("""
            ⚠️ **Gemini API Key Required**

            To use the AI Assistant, please add your Google Gemini API key:
            1. Add `GEMINI_API_KEY=your-key-here` to your `.env` file
            2. Or set the `GEMINI_API_KEY` environment variable
            3. Reload the app

            Get your free API key at: https://aistudio.google.com/app/apikey
            """)
        else:
            try:
                # Initialize session state
                if 'chat_history' not in st.session_state:
                    st.session_state.chat_history = []
                if 'ai_response' not in st.session_state:
                    st.session_state.ai_response = None

                # Company selector
                chatbot_ticker = st.selectbox(
                    "Company:",
                    df_composite['ticker'].unique(),
                    key="chatbot_ticker_select"
                )

                # Simple text input with submit button
                col1, col2 = st.columns([5, 1])
                with col1:
                    user_question = st.text_input(
                        "Ask a question:",
                        placeholder="e.g., What are the key takeaways from this analysis?",
                        key="ai_question_input",
                        label_visibility="collapsed"
                    )
                with col2:
                    submit_clicked = st.button("Ask", type="primary", use_container_width=True)

                # Handle submission
                if submit_clicked and user_question:
                    with st.spinner("Thinking..."):
                        response = chat_with_context(
                            user_question,
                            df_composite,
                            chatbot_ticker,
                            st.session_state.chat_history,
                            s.gemini_api_key
                        )
                        # Store in history
                        st.session_state.chat_history.append({"role": "user", "content": user_question})
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        st.session_state.ai_response = response

                # Quick question buttons
                st.markdown("**Quick questions:**")
                suggestions = get_suggested_questions(chatbot_ticker, df_composite)[:4]
                cols = st.columns(2)
                for i, suggestion in enumerate(suggestions):
                    with cols[i % 2]:
                        if st.button(suggestion, key=f"q_{i}", use_container_width=True):
                            with st.spinner("Thinking..."):
                                response = chat_with_context(
                                    suggestion,
                                    df_composite,
                                    chatbot_ticker,
                                    st.session_state.chat_history,
                                    s.gemini_api_key
                                )
                                st.session_state.chat_history.append({"role": "user", "content": suggestion})
                                st.session_state.chat_history.append({"role": "assistant", "content": response})
                                st.session_state.ai_response = response

                # Display conversation
                if st.session_state.chat_history:
                    st.markdown("---")
                    for msg in st.session_state.chat_history:
                        if msg["role"] == "user":
                            st.markdown(f"**You:** {msg['content']}")
                        else:
                            st.markdown(f"**Assistant:** {msg['content']}")
                        st.markdown("")

                    # Clear button
                    if st.button("Clear conversation"):
                        st.session_state.chat_history = []
                        st.session_state.ai_response = None
                        st.rerun()

            except Exception as e:
                st.error(f"Error: {str(e)}")

    # Download section
    st.markdown("---")
    st.markdown("### 💾 Download Results")

    # All-in-one CSV export
    st.markdown("#### 📦 Export All Data")

    @st.cache_data
    def create_combined_csv(df_comp, df_v, df_l, df_c, df_t):
        """Create a combined CSV with all analysis data."""
        import io
        output = io.StringIO()

        output.write("# IRCI Analysis Export\n")
        output.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        output.write("## COMPOSITE SCORES\n")
        df_comp.to_csv(output, index=False)
        output.write("\n\n## VALUATION DATA\n")
        df_v.to_csv(output, index=False)
        output.write("\n\n## LIQUIDITY DATA\n")
        df_l.to_csv(output, index=False)
        output.write("\n\n## COVERAGE DATA\n")
        df_c.to_csv(output, index=False)
        output.write("\n\n## TRUST DATA\n")
        df_t.to_csv(output, index=False)

        return output.getvalue()

    col_all1, col_all2 = st.columns([1, 3])
    with col_all1:
        all_data_csv = create_combined_csv(df_composite, df_val, df_liq, df_cov, df_trust)
        st.download_button(
            "⬇️ Download All Data (CSV)",
            all_data_csv,
            f"irci_all_data_{selected_quarter}.csv",
            "text/csv",
            use_container_width=True
        )
    with col_all2:
        st.caption("Combined export with composite scores, valuation, liquidity, coverage, and trust data in one file.")

    st.markdown("#### 📊 Individual Datasets")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        csv = df_composite.to_csv(index=False)
        st.download_button(
            "📊 Composite CSV",
            csv,
            f"irci_composite_{selected_quarter}.csv",
            "text/csv"
        )

    with col2:
        csv = df_val.to_csv(index=False)
        st.download_button(
            "💰 Valuation CSV",
            csv,
            f"valuation_{selected_quarter}.csv",
            "text/csv"
        )

    with col3:
        csv = df_liq.to_csv(index=False)
        st.download_button(
            "💧 Liquidity CSV",
            csv,
            f"liquidity_{selected_quarter}.csv",
            "text/csv"
        )

    with col4:
        csv = df_cov.to_csv(index=False)
        st.download_button(
            "📋 Coverage CSV",
            csv,
            f"coverage_{selected_quarter}.csv",
            "text/csv"
        )

    with col5:
        csv = df_trust.to_csv(index=False)
        st.download_button(
            "💭 Trust CSV",
            csv,
            f"trust_{selected_quarter}.csv",
            "text/csv"
        )

    # PDF Report Download (company-specific)
    # Using st.fragment to prevent scroll-to-top on interaction
    st.markdown("---")
    st.markdown("#### 📄 Comprehensive PDF Report")
    st.markdown("*Generate a complete analysis report for a specific company*")

    @st.fragment
    def pdf_report_section():
        """Fragment to handle PDF generation without full page rerun"""
        col_pdf1, col_pdf2, col_pdf3 = st.columns([2, 2, 4])

        with col_pdf1:
            pdf_ticker = st.selectbox(
                "Select company for PDF report:",
                df_composite['ticker'].unique(),
                key="pdf_ticker_select_fragment"
            )

        with col_pdf2:
            if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
                with st.spinner(f"Generating comprehensive PDF report for {pdf_ticker}..."):
                    try:
                        # Get playbook for the selected ticker
                        company_row = df_composite[df_composite['ticker'] == pdf_ticker].iloc[0]
                        dial_scores = {
                            'valuation': company_row.get('valuation_pct', 50),
                            'liquidity': company_row.get('liquidity_pct', 50),
                            'coverage': company_row.get('coverage_pct', 50),
                            'trust': company_row.get('sentiment_pct', 50)
                        }
                        pdf_playbook = generate_playbook(dial_scores, df_composite, pdf_ticker)

                        # Get timeline data if available
                        try:
                            from irci.event_timeline import aggregate_timeline_events
                            from irci.coverage import _company_submissions, _cik_for_ticker

                            cik = _cik_for_ticker(pdf_ticker)
                            if cik:
                                filings_df = _company_submissions(cik, q_start, q_end)
                            else:
                                filings_df = pd.DataFrame()

                            # Get news data (simplified - just use what's available)
                            timeline_data = aggregate_timeline_events(
                                ticker=pdf_ticker,
                                df_trust=df_trust,
                                filings_df=filings_df,
                                q_start=q_start,
                                q_end=q_end,
                                df_composite=df_composite
                            )
                        except:
                            timeline_data = None

                        # Get news data for sentiment analysis
                        pdf_news_df = st.session_state.get('news_df', None)

                        # Get dollar value data if available
                        pdf_dollar_value_df = None
                        pdf_weights = None
                        try:
                            from irci.dial_insights import compute_dollar_value_per_irci_point
                            pdf_dollar_value_df = compute_dollar_value_per_irci_point(df_composite, df_val)
                            # Get current weights from session state
                            pdf_weights = {
                                'valuation': st.session_state.weight_valuation / 100,
                                'liquidity': st.session_state.weight_liquidity / 100,
                                'coverage': st.session_state.weight_coverage / 100,
                                'sentiment': st.session_state.weight_trust / 100
                            }
                        except:
                            pass

                        # Extract quarterly data for multi-quarter reports
                        quarterly_data = None
                        if 'quarter' in df_composite.columns:
                            quarters = df_composite['quarter'].unique()
                            if len(quarters) >= 2:
                                quarterly_data = []
                                for q in sorted(quarters):
                                    q_data = df_composite[(df_composite['quarter'] == q) & (df_composite['ticker'] == pdf_ticker)]
                                    if not q_data.empty:
                                        row = q_data.iloc[0]
                                        quarterly_data.append({
                                            'quarter': q,
                                            'irci_score': row.get('irci_composite_pct', 0) or 0,
                                            'valuation': row.get('valuation_pct', 0) or 0,
                                            'liquidity': row.get('liquidity_pct', 0) or 0,
                                            'coverage': row.get('coverage_pct', 0) or 0,
                                            'trust': row.get('sentiment_pct', 0) or 0
                                        })

                        # Generate PDF
                        pdf_bytes = generate_pdf_report(
                            ticker=pdf_ticker,
                            quarter=selected_quarter,
                            df_composite=df_composite,
                            df_valuation=df_val,
                            df_liquidity=df_liq,
                            df_coverage=df_cov,
                            df_trust=df_trust,
                            playbook=pdf_playbook,
                            timeline_df=timeline_data,
                            news_df=pdf_news_df,
                            dollar_value_df=pdf_dollar_value_df,
                            weights=pdf_weights,
                            quarterly_data=quarterly_data
                        )

                        # Store in session state for download
                        st.session_state['pdf_report'] = pdf_bytes
                        st.session_state['pdf_ticker'] = pdf_ticker
                        st.session_state['pdf_quarter'] = selected_quarter
                        st.session_state['pdf_just_generated'] = True
                        st.rerun()  # Rerun to update email section

                    except Exception as e:
                        st.error(f"Error generating PDF report: {str(e)}")
                        import traceback
                        with st.expander("Error details"):
                            st.code(traceback.format_exc())

        # Show download button if PDF was generated
        if 'pdf_report' in st.session_state and st.session_state.get('pdf_ticker') == pdf_ticker:
            # Show success message after rerun
            if st.session_state.pop('pdf_just_generated', False):
                st.success(f"✅ PDF report generated successfully for {pdf_ticker}!")
            with col_pdf3:
                st.download_button(
                    label=f"⬇️ Download {pdf_ticker} Report",
                    data=st.session_state['pdf_report'],
                    file_name=f"IRCI_Report_{pdf_ticker}_{st.session_state.get('pdf_quarter', 'report')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # Call the fragment
    pdf_report_section()

    # Email Report Section
    st.markdown("---")
    st.markdown("#### 📧 Email Report")

    email_config = get_email_config_status()

    if not email_config.get("configured"):
        st.info("""
        **Email delivery not configured.** To enable:
        1. Set `SMTP_USER` and `SMTP_PASSWORD` in your environment
        2. For Gmail, use an App Password (not your regular password)
        """)
    else:
        if 'pdf_report' in st.session_state:
            col_email1, col_email2 = st.columns([3, 1])
            with col_email1:
                email_address = st.text_input(
                    "Send report to email:",
                    placeholder="recipient@example.com",
                    key="email_recipient"
                )
            with col_email2:
                if st.button("📧 Send Email", use_container_width=True):
                    if email_address and validate_email(email_address):
                        with st.spinner("Sending email..."):
                            # Get IRCI score for email body
                            pdf_ticker = st.session_state.get('pdf_ticker', 'Unknown')
                            company_data = df_composite[df_composite['ticker'] == pdf_ticker]
                            irci_score = company_data['irci_composite_pct'].iloc[0] if not company_data.empty else None

                            result = send_irci_report_email(
                                to_email=email_address,
                                ticker=pdf_ticker,
                                quarter=st.session_state.get('pdf_quarter', selected_quarter),
                                pdf_data=st.session_state['pdf_report'],
                                irci_score=irci_score
                            )

                            if result.get("success"):
                                st.success(f"✅ Report sent to {email_address}")
                            else:
                                st.error(f"Failed to send email: {result.get('error', 'Unknown error')}")
                    else:
                        st.warning("Please enter a valid email address")
        else:
            st.caption("Generate a PDF report first to enable email delivery")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    IRCI Analysis Platform v0.1.0 | Powered by Streamlit |
    <a href='https://github.com/anthropics/claude-code' target='_blank'>Documentation</a><br>
    <span style='font-size: 0.85rem; color: #888;'>Patent Pending</span> |
    <a href='https://github.com/sponsors/bnatc85' target='_blank' style='color: #ea4aaa;'>❤️ Donate</a>
</div>
""", unsafe_allow_html=True)
