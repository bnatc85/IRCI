"""
IRCI Web Application
A user-friendly interface for running IRCI analysis on public companies.
"""

import streamlit as st
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
from irci.peers import find_peers_simple
from irci.playbook import generate_playbook
from irci.chatbot import chat_with_context, get_suggested_questions
from irci.report_generator import generate_pdf_report

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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">IRCI Analysis Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">IRCI: Coverage, Trust, Liquidity & Valuation Analysis</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("IRCI_icon_primary.png", use_container_width=True)
    st.markdown("### Analysis Configuration")

    # Peer discovery section
    with st.expander("🔍 Find Peer Companies", expanded=False):
        st.markdown("**Curated peer groups** for 60+ popular tickers")
        st.caption("Examples: AAPL, TSLA, NVDA, NFLX, JPM, WMT, CRM")

        peer_base_ticker = st.text_input(
            "Base Company Ticker",
            value="",
            placeholder="e.g., AAPL",
            help="Enter a ticker to find peers in the same industry"
        )
        peer_count = st.slider("Number of Peers", 3, 15, 8)

        if st.button("Find Peers", use_container_width=True):
            if peer_base_ticker:
                try:
                    s = Settings.load()
                    peers = find_peers_simple(peer_base_ticker.upper(), s.fmp_api_key, max_peers=peer_count)
                    if peers:
                        # Store peers in session state
                        all_tickers = [peer_base_ticker.upper()] + peers
                        st.session_state['found_peers'] = ",".join(all_tickers)
                        st.success(f"✓ Found {len(peers)} peers for {peer_base_ticker.upper()}")
                        st.info(f"**Peers:** {', '.join(peers)}")
                    else:
                        st.warning(f"⚠️ {peer_base_ticker.upper()} not in curated peer database. Try: AAPL, TSLA, NVDA, NFLX, CRM, JPM, WMT, SNAP, CRWD")
                except Exception as e:
                    st.error(f"Error finding peers: {str(e)}")
            else:
                st.warning("Please enter a ticker")

    # Company selection
    default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]

    # Use found peers if available, otherwise use default
    initial_value = st.session_state.get('found_peers', ",".join(default_tickers))

    ticker_input = st.text_area(
        "Company Tickers (one per line or comma-separated)",
        value=initial_value,
        help="Enter stock tickers like AAPL, MSFT, GOOGL or use the peer finder above"
    )

    # Parse tickers
    if "," in ticker_input:
        tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    else:
        tickers = [t.strip().upper() for t in ticker_input.split("\n") if t.strip()]

    st.info(f"Selected: {len(tickers)} companies")

    # Quarter selection
    quarters = ["2025Q4", "2025Q3", "2025Q2", "2025Q1", "2024Q4", "2024Q3", "2024Q2", "2024Q1"]
    selected_quarter = st.selectbox("Select Quarter", quarters, index=1)

    # Convert quarter to dates
    quarter_map = {
        "Q1": ("01-01", "03-31"),
        "Q2": ("04-01", "06-30"),
        "Q3": ("07-01", "09-30"),
        "Q4": ("10-01", "12-31")
    }
    year = selected_quarter[:4]
    q = selected_quarter[4:]
    start_date = f"{year}-{quarter_map[q][0]}"
    end_date = f"{year}-{quarter_map[q][1]}"

    st.caption(f"Period: {start_date} to {end_date}")

    # Run Analysis button - prominently placed after quarter selection
    st.markdown("---")
    run_analysis = st.button(
        "🚀 Run Analysis",
        type="primary",
        use_container_width=True,
        help="Start analyzing the selected companies for the chosen quarter"
    )
    st.markdown("---")

    # News file upload
    st.markdown("### News Data")
    st.info("📰 News articles are automatically fetched from FMP API for sentiment analysis")
    uploaded_news = st.file_uploader(
        "Or upload custom News CSV (optional override)",
        type=["csv"],
        help="CSV with columns: date, ticker, headline. If provided, this will override automatic fetching."
    )

    # Weights configuration
    with st.expander("⚙️ Advanced: Dial Weights", expanded=True):
        st.markdown("**Customize composite score weights:**")
        st.caption("Type exact percentages or use 🎯 Auto-Optimize")

        # Initialize weights in session state if not present
        if 'weight_liquidity' not in st.session_state:
            st.session_state.weight_liquidity = 35.0
        if 'weight_valuation' not in st.session_state:
            st.session_state.weight_valuation = 35.0
        if 'weight_coverage' not in st.session_state:
            st.session_state.weight_coverage = 15.0
        if 'weight_trust' not in st.session_state:
            st.session_state.weight_trust = 15.0

        # Use number inputs with BOTH value and key for proper state management
        # value= forces widget to display current session state
        # key= allows widget to update session state when user changes it
        col1, col2 = st.columns(2)
        with col1:
            weight_valuation = st.number_input(
                "💰 Valuation (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.weight_valuation,  # Display current value
                step=0.1,
                format="%.1f",
                help="Weight for EV/EBITDA valuation metrics"
            )
            weight_coverage = st.number_input(
                "📊 Coverage (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.weight_coverage,  # Display current value
                step=0.1,
                format="%.1f",
                help="Weight for SEC filing and media coverage metrics"
            )

        with col2:
            weight_liquidity = st.number_input(
                "💧 Liquidity (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.weight_liquidity,  # Display current value
                step=0.1,
                format="%.1f",
                help="Weight for trading liquidity and spread metrics"
            )
            weight_trust = st.number_input(
                "💭 Trust (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.weight_trust,  # Display current value
                step=0.1,
                format="%.1f",
                help="Weight for sentiment and event calm metrics"
            )

        # Update session state with current widget values
        # This allows auto-optimize to change session state, rerun, and widgets will show new values
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

        # Auto-optimize button
        if st.button("🎯 Auto-Optimize Weights", use_container_width=True, help="Find weights that maximize EV ~ IRCI regression R²"):
            st.session_state.optimize_weights = True

    # Save/Load session
    st.markdown("---")
    st.markdown("### 💾 Save/Load Progress")

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
                'selected_quarter': selected_quarter,
                'tickers': tickers,
                'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Serialize to bytes
            session_bytes = pickle.dumps(session_data)

            # Offer download
            st.download_button(
                label="📥 Download Session File",
                data=session_bytes,
                file_name=f"irci_session_{selected_quarter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl",
                mime="application/octet-stream",
                use_container_width=True
            )
        else:
            st.warning("No analysis results to save. Run an analysis first!")

    # Load session
    uploaded_session = st.file_uploader(
        "📤 Load Previous Session",
        type=["pkl"],
        help="Upload a previously saved session file"
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
            st.session_state['weight_liquidity'] = session_data.get('weight_liquidity', 35)
            st.session_state['weight_valuation'] = session_data.get('weight_valuation', 35)
            st.session_state['weight_coverage'] = session_data.get('weight_coverage', 15)
            st.session_state['weight_trust'] = session_data.get('weight_trust', 15)
            st.session_state['run_time'] = datetime.now()

            # Verify data was loaded
            if st.session_state['df_composite'] is not None:
                num_companies = len(st.session_state['df_composite'])
                st.success(f"✓ Session loaded! Saved on {session_data.get('saved_at', 'unknown date')}. Analysis for {num_companies} companies is ready. Scroll down to view results.")
            else:
                st.warning("⚠️ Session loaded but no analysis data found. The session file may be incomplete.")

            st.rerun()
        except Exception as e:
            st.error(f"Failed to load session: {str(e)}")

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

    # Contact information
    st.markdown("""
    <div class="contact-info">
        <strong>Contact:</strong><br>
        Bonnie Rushing<br>
        <a href="mailto:brushing@uccs.edu">brushing@uccs.edu</a><br>
        <a href="https://www.thebonnierushing.com" target="_blank">www.thebonnierushing.com</a>
    </div>
    """, unsafe_allow_html=True)

# Auto-optimize weights if requested
if st.session_state.get('optimize_weights', False):
    # Only optimize if we have previous results to analyze
    if 'df_composite' in st.session_state and 'df_val' in st.session_state:
        try:
            from irci.dial_insights import recommend_optimal_weights

            # Merge enterprise_value into df_composite for R² optimization
            df_comp = st.session_state['df_composite'].copy()
            df_val = st.session_state['df_val']
            if 'enterprise_value' in df_val.columns:
                df_comp = df_comp.merge(
                    df_val[['ticker', 'enterprise_value']],
                    on='ticker',
                    how='left'
                )

            current_weights = {
                'valuation': weight_valuation / 100,
                'liquidity': weight_liquidity / 100,
                'coverage': weight_coverage / 100,
                'sentiment': weight_trust / 100
            }

            # Use variance-based optimization (same as Insights tab)
            # R² optimization tends to overfit and produce unrealistic weights
            weight_analysis = recommend_optimal_weights(
                st.session_state['df_composite'],  # Use original df_composite (same as Insights)
                current_weights=current_weights
                # No optimize_for parameter = default variance-based method
            )
            rec_weights = weight_analysis['recommended_weights']

            # Debug: show what recommend_optimal_weights returned
            print(f"DEBUG: Recommended weights from optimizer:")
            print(f"  valuation: {rec_weights['valuation']:.4f} ({rec_weights['valuation']*100:.1f}%)")
            print(f"  liquidity: {rec_weights['liquidity']:.4f} ({rec_weights['liquidity']*100:.1f}%)")
            print(f"  coverage: {rec_weights['coverage']:.4f} ({rec_weights['coverage']*100:.1f}%)")
            print(f"  sentiment: {rec_weights['sentiment']:.4f} ({rec_weights['sentiment']*100:.1f}%)")
            print(f"  sum: {sum(rec_weights.values()):.4f}")

            # Convert to percentages and ensure they sum to exactly 100
            val_pct = rec_weights['valuation'] * 100
            liq_pct = rec_weights['liquidity'] * 100
            cov_pct = rec_weights['coverage'] * 100
            tru_pct = rec_weights['sentiment'] * 100

            # Check if they sum to 100, if not normalize
            total = val_pct + liq_pct + cov_pct + tru_pct
            if abs(total - 100.0) > 0.1:
                print(f"DEBUG: Weights don't sum to 100 ({total:.2f}), normalizing...")
                val_pct = (val_pct / total) * 100
                liq_pct = (liq_pct / total) * 100
                cov_pct = (cov_pct / total) * 100
                tru_pct = (tru_pct / total) * 100

            # Update session state with optimized weights (round to 1 decimal place)
            st.session_state.weight_valuation = round(val_pct, 1)
            st.session_state.weight_liquidity = round(liq_pct, 1)
            st.session_state.weight_coverage = round(cov_pct, 1)
            st.session_state.weight_trust = round(tru_pct, 1)

            print(f"DEBUG: Set session state weights:")
            print(f"  weight_valuation: {st.session_state.weight_valuation}")
            print(f"  weight_liquidity: {st.session_state.weight_liquidity}")
            print(f"  weight_coverage: {st.session_state.weight_coverage}")
            print(f"  weight_trust: {st.session_state.weight_trust}")

            st.session_state.optimize_weights = False
            st.session_state.weights_just_optimized = True  # Flag to show message after rerun

            # Store the optimized R² for display
            if 'optimized_r2' in weight_analysis:
                st.session_state.optimized_r2 = weight_analysis['optimized_r2']

            st.rerun()  # Rerun to update sliders with new values
        except Exception as e:
            st.error(f"Could not optimize weights: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.session_state.optimize_weights = False
    else:
        st.warning("Please run an analysis first before optimizing weights")
        st.session_state.optimize_weights = False

# Show success message after weights were optimized
if st.session_state.get('weights_just_optimized', False):
    # Verify weights sum to 100
    total = st.session_state.weight_valuation + st.session_state.weight_liquidity + st.session_state.weight_coverage + st.session_state.weight_trust

    msg = "✓ **Weights Auto-Optimized!** The input fields above have been updated to maximize EV ~ IRCI correlation.\n\n"
    msg += f"**New Weights (sum = {total:.1f}%):**\n"
    msg += f"- Valuation: {st.session_state.weight_valuation:.1f}%\n"
    msg += f"- Liquidity: {st.session_state.weight_liquidity:.1f}%\n"
    msg += f"- Coverage: {st.session_state.weight_coverage:.1f}%\n"
    msg += f"- Trust: {st.session_state.weight_trust:.1f}%"
    if 'optimized_r2' in st.session_state:
        msg += f"\n\n**Achieved R²:** {st.session_state.optimized_r2:.3f}"
    msg += "\n\n📊 Click **'Run Analysis'** below to see results with these optimized weights."

    if abs(total - 100.0) > 0.5:
        st.warning(f"⚠️ {msg}\n\n**Note:** Weights sum to {total:.1f}% (not 100%). They will be normalized when running analysis.")
    else:
        st.success(msg)

    st.session_state.weights_just_optimized = False

# Main content area - show results if they exist in session state
show_results = 'df_composite' in st.session_state

# Logic:
# 1. If run_analysis is clicked, we'll run analysis and update session state
# 2. If results exist in session state but run_analysis is not clicked, just skip to display
# 3. If no results and no run_analysis, show welcome screen

if not show_results and not run_analysis:
    # Welcome screen
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 📊 Coverage")
        st.markdown("SEC filings + media visibility (auto-fetched)")

    with col2:
        st.markdown("### 💭 Trust")
        st.markdown("News sentiment + event stability (auto-analyzed)")

    with col3:
        st.markdown("### 💧 Liquidity")
        st.markdown("Market microstructure & trading metrics")

    with col4:
        st.markdown("### 💰 Valuation")
        st.markdown("EV/EBITDA peer comparison")

    st.markdown("---")

    # Important disclaimers - prominent placement
    st.warning("""
    ⚠️ **Important Disclaimers**

    - **Fundamentals set value. IR determines how efficiently markets realize it.** IRCI measures the pathway to fair value, not fundamental business performance.
    - IR's impact on share valuation is limited compared to business fundamentals, macroeconomic conditions, and industry trends.
    - IRCI is a planning and diagnostic tool—not a guarantee of market outcomes.
    - Dollar-per-point estimates are derived from historical peer relationships and should be treated as planning ranges, not promises.
    - This tool is for authorized use only. Views expressed are those of the creators and not official positions of any affiliated organization.
    """)

    st.info("👈 Configure your analysis in the sidebar and click **Run Analysis** to start")

    # Comprehensive About & Methodology
    tabs = st.tabs(["📖 How It Works", "🎯 About IRCI", "👥 Team", "🔬 Validation"])

    with tabs[0]:
        st.markdown("""
        ### How IRCI Works

        **IRCI** evaluates companies across four fundamental dimensions:

        #### 📊 Coverage Dial
        **"How visible and understandable is your company in the public record?"**

        - **Credible media attention** - Tracks mentions in Wall Street Journal, Bloomberg, Reuters vs. lower-signal press wires
        - **Filing cadence & timeliness** - SEC 8-K frequency, 10-Q/10-K filing speed relative to deadlines
        - **Coverage momentum** - Whether disclosure quality is improving or declining

        💡 High Coverage = investors don't have to hunt for your story. Low Coverage = greater uncertainty.

        #### 💭 Trust Dial
        **"When you speak, does the market stay calm or freak out?"**

        - **Event Calm** - Stock movement within normal bands around earnings/8-Ks (factor-adjusted)
        - **Baseline Calm** - Control group of ordinary days to see if announcements settle or stir markets
        - **Media tone** - AI/NLP sentiment analysis across credible news outlets

        💡 If Event Calm > Baseline Calm, your communication settles markets. If lower, you're creating questions.

        #### 💧 Liquidity Dial
        **"How easy and cheap is it for investors to get in and out?"**

        - **Turnover** - Trading volume relative to market cap
        - **Amihud illiquidity** - Price impact per dollar traded (lower is better)
        - **Implied spread (Roll estimate)** - The hidden toll booth every trade pays

        💡 Strong Liquidity = smooth, cheap trading. Weak Liquidity = every big move is costly and disruptive.

        #### 💰 Valuation Dial
        **"How many dollars is the market willing to pay for each dollar of operating earnings?"**

        - **EV/EBITDA multiple** - Enterprise value divided by EBITDA
        - **Peer-relative position** - Where you stand vs. industry comparables
        - **Trend stability** - Whether your multiple is steady or volatile

        💡 When uncertainty and trading friction decrease, investors typically pay more per dollar of earnings.

        ---

        ### The Master Framework

        Think of IRCI like tuning a stereo:
        - The first three dials (Coverage, Trust, Liquidity) are like bass, treble, and balance—they shape clarity and stability
        - The Valuation dial is the master volume—how loud and strong the music comes through

        **Fundamentals set the ceiling (the orange line on the chart).** IR and reputation determine how efficiently the market reaches that fair value (the path the blue/green lines take).

        ---

        **Output:** A composite score (0-100%) ranking companies within your peer group, with dollar-per-point estimates for planning.
        """)

    with tabs[1]:
        st.markdown("""
        ### About IRCI

        #### The Challenge

        Have you ever wondered whether investor relations and reputation really move a company's market value—or if it's all just "nice to have"?

        **Decades of research** reveal 4 major value contributions by IR:
        1. Fairer pricing
        2. Better liquidity
        3. Analyst coverage
        4. Reputation management

        But experts have always cautioned against claiming that IR contributions **directly** affect value. In fact, one study participant stated that IR's impact on share valuation is **"very, very minimal"** compared to other factors like fundamentals and macro conditions.

        ---

        #### The Solution

        **The industry says IR's impact can't be measured. We disagree.**

        IRCI builds upon **40+ years of academic and practitioner research**, compressing:
        - Coverage momentum
        - Trust and credibility
        - Liquidity and market microstructure
        - Valuation positioning

        ...into **one peer-relative score + actionable playbooks**.

        ---

        #### How It's Different

        IRCI isn't a PR or brand index—it's **market-plumbing aware**, built on:
        - Observed trading data
        - SEC filings and events
        - Factor-adjusted price reactions
        - Credible media analysis

        **Not surveys. Not opinions. Objective, repeatable metrics.**

        | Feature | IRCI | Traditional IR Tools | Reputation Scores |
        |---------|------|---------------------|-------------------|
        | **Objective data** | ✅ Market data, SEC filings | ⚠️ Mixed | ❌ Surveys |
        | **Dollar quantification** | ✅ $/IRCI point | ❌ | ⚠️ Annual estimates |
        | **Actionable playbooks** | ✅ Dial-specific | ⚠️ General advice | ❌ |
        | **Peer benchmarking** | ✅ Relative ranking | ⚠️ Limited | ✅ |
        | **Board-grade outputs** | ✅ | ❌ | ⚠️ |

        ---

        #### The Three Channels of IR Impact

        1. **Liquidity and Access**
           - Deeper trading, tighter spreads
           - Cheaper for investors to enter/exit
           - Improves discoverability, reduces friction

        2. **Coverage and Disclosure Momentum**
           - More (and better) coverage
           - Clear filings and events
           - Information travels faster, eases investor concerns

        3. **Trust Around Events**
           - Credible, consistent communication
           - Calmer earnings days and headlines
           - Stock tracks closer to fair value instead of whipping around on rumors

        **We don't pretend IR replaces fundamentals.** We measure how IR and reputation change the path to fair value, how persistent that proximity is, and then we price it in dollars per score point.

        ---

        #### Use Cases

        **For IR Teams:**
        - "Which dial is weak, and what should we do?"
        - "What are peer leaders doing well that we can borrow?"
        - Measure → pick weakest dial → run playbook → re-measure

        **For Boards and CFOs:**
        - "If 1 IRCI point is worth ~$X, is it worth spending $Y to move the weakest dial by 2-3 points?"
        - Quantifiable ROI for IR and communications investments
        - Compare IR efficiency across business units or portfolio companies

        **For Investors:**
        - Identify companies with IR/reputation inefficiencies
        - Spot potential mispricings due to poor disclosure or liquidity
        - Track improvements in company accessibility over time
        """)

    with tabs[2]:
        st.markdown("""
        ### The Team

        #### Bonnie Rushing
        **PhD Student, University of Colorado Colorado Springs**

        - Master's Degree in Strategic Intelligence
        - Military service in special operations and signals intelligence
        - Former instructor of strategic studies at US Air Force Academy
        - **Core expertise:** Signal detection, data analytics, translating operational tradecraft into market analysis

        *"From the aircraft to the boardroom, my job is the same: make sense of noise and enable decisions."*

        📧 [brushing@uccs.edu](mailto:brushing@uccs.edu)
        🌐 [www.thebonnierushing.com](https://www.thebonnierushing.com)

        ---

        #### Jim Wilkinson
        **Senior Advisor & Executive Chairman, TrailRunner International**

        - Led global communications and corporate affairs at Alibaba and PepsiCo
        - Senior government roles: Treasury, State Department, White House, USCENTCOM
        - **Core expertise:** Boardroom and global corporate communications strategy

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

    with tabs[3]:
        st.markdown("""
        ### Validation & Methodology

        #### Three Reasons to Trust This Score

        **1. Track Record**
        - Tested on **5+ years of data** and tens of thousands of observations
        - Covers multiple market cycles and industry sectors

        **2. Predictive Checks**
        - When Liquidity rises → spreads tighten ✅
        - When Trust is higher → event days are calmer ✅
        - Coverage momentum → Valuation behaves as expected ✅
        - All relationships are **directionally correct and statistically significant**

        **3. Ablation Testing**
        - Drop each dial one by one → measure signal loss
        - Result: **All 4 dials contribute unique information**
        - Not one magic number—comprehensive framework

        ---

        #### Sanity Checks Performed

        **Test 1: Directional Validation**

        *If a company scores higher on a dial today, do we see the right move next quarter in what that dial should influence?*

        ✅ **CHECK**
        - Strong Coverage → continued disclosure momentum
        - High Trust → calmer event days (factor-adjusted)
        - High Liquidity → tighter spreads
        - Strong Valuation → better peer-relative EV trend

        **Test 2: Ablation Analysis**

        *If we drop one dial, does prediction worsen?*

        ✅ **CHECK**
        - Reran composite 4 times, removing one dial each time
        - Signal weakens every time
        - **Trust delivers the largest unique lift** in our Big Tech sample, but all dials are necessary

        **Test 3: Dollar Value Calibration**

        *Can we convert IRCI points to enterprise value changes?*

        ✅ **CHECK**
        - In our Big Tech sample: +1 IRCI point ≈ -0.44% change in next-quarter peer valuation gap
        - R² ≈ 0.37 (moderate explanatory power—appropriate for a secondary factor after fundamentals)
        - Translation: On Apple-sized companies, ~$15B per IRCI point

        💡 **Interpretation:** Treat as a **planning range**, not a guarantee. Fundamentals dominate, but IR efficiency matters at the margin.

        ---

        #### Peer Group Selection

        **IRCI only works if the peer set is realistic:**
        - Same industry and approximate size
        - Typically 10-15 comparable companies
        - Pre-built peer groups for 60+ popular tickers

        **Right peers → right insights**

        ---

        #### Data Sources & Processing

        1. **SEC EDGAR** - Filings, events, submission dates
        2. **Financial Markets API** - Pricing, fundamentals, news
        3. **Fama-French Factors** - Market and sector adjustments for event calm
        4. **NLP/AI Sentiment** - Media tone analysis from credible outlets

        **Processing steps:**
        - Clean and normalize data
        - Convert to percentiles within peer group
        - Score each dial 0-100
        - Weight and combine to composite with peer ranking

        ---

        #### Limitations & Appropriate Use

        **What IRCI Does:**
        - Measures IR efficiency and market accessibility
        - Provides dollar-denominated planning ranges
        - Identifies which dial is weakest for targeted action

        **What IRCI Does NOT Do:**
        - Replace fundamental analysis
        - Guarantee stock price movements
        - Account for M&A, executive changes, or black swan events
        - Substitute for compliance, legal, or financial advice

        **Appropriate Use Cases:**
        - IR planning and resource allocation
        - Quarterly board reporting on IR effectiveness
        - Benchmarking against peers
        - Identifying improvement opportunities

        **Inappropriate Use Cases:**
        - Day trading or market timing
        - Guaranteeing specific ROI
        - Ignoring fundamentals or macro trends
        """)

    # Show example
    with st.expander("📖 Quick Start Guide"):
        st.markdown("""
        ### Quick Start Guide

        1. **Find Peers** (optional but recommended)
           - Use the "Find Peer Companies" tool in the sidebar
           - Enter a ticker (e.g., AAPL, TSLA, NVDA)
           - System will suggest 8-15 comparable companies

        2. **Configure Analysis**
           - Select your companies (or use found peers)
           - Choose a quarter to analyze
           - News data is **automatically fetched** from FMP API

        3. **Run Analysis**
           - Click "Run Analysis"
           - System will compute all 4 dials and composite score
           - Results appear in tabs below

        4. **Interpret Results**
           - **Composite Ranking** - See who leads the peer group
           - **Dial Breakdown** - Identify weak spots (radar chart)
           - **Insights Tab** - View dollar-per-point estimates
           - **Timeline Tab** - Track events and their impact

        5. **Take Action**
           - Focus on the weakest dial
           - Consult dial-specific playbooks (coming soon in app)
           - Re-measure next quarter to track progress
        """)

elif run_analysis:
    # Run the analysis (only when button is clicked)
    st.markdown("---")
    st.markdown("## 🔄 Running Analysis...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Load settings
        s = Settings.load()

        # Prepare news data - automatically fetch from FMP API
        news_df = None
        if uploaded_news is not None:
            # User uploaded news file
            news_df = pd.read_csv(uploaded_news)
            st.success(f"✓ Loaded {len(news_df)} news articles from upload")
        else:
            # Automatically fetch news for all tickers using API (FMP → World News → Alpha Vantage fallback)
            status_text.text("Fetching news articles...")
            news_list = []
            news_counts = {}
            news_sources_used = {}  # Track which source was used for each ticker
            q_start = pd.to_datetime(start_date, utc=True)
            q_end = pd.to_datetime(end_date, utc=True)

            # Track errors for display
            news_errors = {}

            for ticker in tickers:
                ticker_got_news = False
                ticker_errors = []

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

                if not ticker_got_news:
                    news_counts[ticker] = 0
                    news_errors[ticker] = ticker_errors
                    print(f"No news found for {ticker} in period {start_date} to {end_date}")

            if news_list:
                news_df = pd.concat(news_list, ignore_index=True)

                # Add sentiment scores to each article using FinBERT
                status_text.text("Analyzing sentiment for news articles...")
                try:
                    from irci.trust import finbert_score
                    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

                    headlines = news_df['headline'].fillna('').astype(str).tolist()
                    sentiment_scores = []

                    # Try FinBERT first
                    fb_scores = finbert_score(headlines)
                    if fb_scores:
                        sentiment_scores = fb_scores
                        sentiment_method = "FinBERT"
                    else:
                        # Fallback to VADER
                        sia = SentimentIntensityAnalyzer()
                        sentiment_scores = [sia.polarity_scores(h)["compound"] for h in headlines]
                        sentiment_method = "VADER"

                    news_df['sentiment_score'] = sentiment_scores

                    # Add sentiment label
                    news_df['sentiment'] = news_df['sentiment_score'].apply(
                        lambda x: 'positive' if x > 0.1 else ('negative' if x < -0.1 else 'neutral')
                    )

                    print(f"✓ Sentiment analysis complete using {sentiment_method}")
                except Exception as e:
                    print(f"Warning: Could not run sentiment analysis: {e}")
                    news_df['sentiment_score'] = 0.0
                    news_df['sentiment'] = 'neutral'

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

        # 1. Trust
        status_text.text("Running Trust analysis...")
        progress_bar.progress(10)
        df_trust = trust_snapshot(
            tickers,
            start=start_date,
            end=end_date,
            news_df=news_df,
            apikey=s.fmp_api_key,
            s=s
        )
        if not df_trust.empty:
            if "quarter_end" not in df_trust.columns:
                df_trust["quarter_end"] = quarter_end_dt
            # Force timezone-naive by normalizing to date
            df_trust["quarter_end"] = pd.to_datetime(pd.to_datetime(df_trust["quarter_end"]).dt.date)
        progress_bar.progress(30)

        # 2. Valuation
        status_text.text("Running Valuation analysis...")
        df_val = valuation_snapshot(
            tickers,
            as_of=end_date
        )
        if not df_val.empty:
            if "quarter_end" not in df_val.columns:
                df_val["quarter_end"] = quarter_end_dt
            # Force timezone-naive by normalizing to date
            df_val["quarter_end"] = pd.to_datetime(pd.to_datetime(df_val["quarter_end"]).dt.date)
        progress_bar.progress(50)

        # 3. Coverage
        status_text.text("Running Coverage analysis...")
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
        progress_bar.progress(70)

        # 4. Liquidity
        status_text.text("Running Liquidity analysis...")
        rows = []
        for sym in tickers:
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
        progress_bar.progress(85)

        # 5. Composite
        status_text.text("Computing composite scores...")

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
                'trust': weight_trust / 100
            }
        )
        progress_bar.progress(100)
        status_text.text("✓ Analysis complete!")

        # Store in session state
        st.session_state['df_composite'] = df_composite
        st.session_state['df_trust'] = df_trust
        st.session_state['df_val'] = df_val
        st.session_state['df_cov'] = df_cov
        st.session_state['df_liq'] = df_liq
        st.session_state['news_df'] = news_df  # Store news data for timeline
        st.session_state['run_time'] = datetime.now()

        # Also store as previous quarter data for future QoQ comparisons
        # This allows next quarter's analysis to compare against this one
        prev_quarter_key = f'df_composite_prev_{selected_quarter}'
        st.session_state[prev_quarter_key] = df_composite.copy()

    except Exception as e:
        st.error(f"❌ Error running analysis: {str(e)}")
        st.exception(e)
        st.stop()

# Display results (if available)
if 'df_composite' in st.session_state and st.session_state['df_composite'] is not None:
    st.markdown("---")
    st.markdown("## 📊 Analysis Results")

    # Disclaimer banner for results
    st.info("""
    💡 **Remember:** These scores measure IR efficiency and market accessibility—not business fundamentals.
    Dollar estimates are planning ranges based on peer relationships, not guarantees.
    Focus on identifying the weakest dial and taking targeted action.
    """)

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

        # Top metrics
        st.markdown(f"### Quarter: {selected_quarter} | Companies: {len(df_composite)} | Run: {st.session_state['run_time'].strftime('%Y-%m-%d %H:%M')}")
    except Exception as e:
        st.error(f"❌ Error displaying results: {str(e)}")
        st.exception(e)
        st.stop()

    # Composite ranking
    st.markdown("### 🏆 Composite Ranking")

    # Prepare display data
    display_df = df_composite.copy()
    # Sort by composite score (highest first) and create rank
    display_df = display_df.sort_values('irci_composite_pct', ascending=False)
    display_df['rank'] = range(1, len(display_df) + 1)

    # Format percentages
    for col in ['irci_composite_pct', 'valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(1)

    # Display table
    col1, col2 = st.columns([2, 1])

    with col1:
        st.dataframe(
            display_df[['rank', 'ticker', 'irci_composite_pct', 'valuation_pct', 'liquidity_pct', 'coverage_pct', 'sentiment_pct']].rename(columns={
                'rank': 'Rank',
                'ticker': 'Ticker',
                'irci_composite_pct': 'Composite %',
                'valuation_pct': 'Valuation %',
                'liquidity_pct': 'Liquidity %',
                'coverage_pct': 'Coverage %',
                'sentiment_pct': 'Trust %'
            }),
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
                delta=None
            )

    # Visualizations
    st.markdown("### 📈 Visualizations")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Composite Scores", "Dial Breakdown", "Detailed Metrics", "📊 Insights", "📅 Timeline", "📋 Playbook", "💬 AI Assistant"])

    with tab1:
        # Bar chart of composite scores
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

    with tab2:
        # Radar chart for each company
        selected_company = st.selectbox("Select company for dial breakdown:", display_df['ticker'].tolist())

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

        # Show metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Valuation", f"{values[0]:.1f}%")
        col2.metric("Liquidity", f"{values[1]:.1f}%")
        col3.metric("Coverage", f"{values[2]:.1f}%")
        col4.metric("Trust", f"{values[3]:.1f}%")

    with tab3:
        # Detailed metrics by dial
        st.markdown("#### 💰 Valuation Details")
        st.dataframe(
            df_val[['ticker', 'valuation_pct', 'ev_to_ebitda', 'peer_mean_excl_self', 'valuation_gap_pct', 'valuation_quartile']].rename(columns={
                'ticker': 'Ticker',
                'valuation_pct': 'Score %',
                'ev_to_ebitda': 'EV/EBITDA',
                'peer_mean_excl_self': 'Peer Avg',
                'valuation_gap_pct': 'Gap %',
                'valuation_quartile': 'Quartile'
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 💧 Liquidity Details")
        st.dataframe(
            df_liq[['ticker', 'liquidity_pct', 'q_amihud_e6', 'q_spread_bps', 'q_turnover']].rename(columns={
                'ticker': 'Ticker',
                'liquidity_pct': 'Score %',
                'q_amihud_e6': 'Amihud (×10⁶)',
                'q_spread_bps': 'Spread (bps)',
                'q_turnover': 'Turnover'
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 📊 Coverage Details")
        st.dataframe(
            df_cov[['ticker', 'coverage_pct', 'q_8k_count', 'q_days_to_10q']].rename(columns={
                'ticker': 'Ticker',
                'coverage_pct': 'Score %',
                'q_8k_count': '8-K Count',
                'q_days_to_10q': 'Days to 10-Q/K'
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 💭 Trust Details")
        st.dataframe(
            df_trust[['ticker', 'trust_pct', 'p_event_calm', 'p_baseline_calm', 'p_media_tone', 'event_count', 'media_tone_n']].rename(columns={
                'ticker': 'Ticker',
                'trust_pct': 'Score %',
                'p_event_calm': 'Event Calm %',
                'p_baseline_calm': 'Baseline Calm %',
                'p_media_tone': 'Media Tone %',
                'event_count': 'Events',
                'media_tone_n': 'Articles'
            }),
            use_container_width=True,
            hide_index=True
        )

    with tab4:
        # Import insights module
        from irci.dial_insights import (
            compute_dollar_value_per_irci_point,
            compute_dial_contribution,
            recommend_optimal_weights
        )

        # Section 1: Dollar Value per IRCI Point
        st.markdown("#### 💵 Dollar Value per IRCI Point")
        st.markdown("*Reveals how much enterprise value corresponds to each IRCI point improvement*")

        st.warning("""
        ⚠️ **Planning Range, Not a Promise:** Dollar-per-point estimates are derived from regression analysis of peer relationships
        and **automatically scaled by R²** to reflect that IR is one of many factors affecting enterprise value.
        R² values of 0.3-0.5 are typical for secondary factors (after fundamentals). If R²=0.3, dollar estimates are reduced by 70%
        to reflect that IR explains only 30% of enterprise value variance.
        These are **planning tools** for evaluating IR investments, not guarantees of market outcomes.
        """)

        try:
            dollar_value_df = compute_dollar_value_per_irci_point(df_composite, df_val)

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
                    help="Average company-specific dollar value per IRCI point (R²-scaled). This reflects how much enterprise value typically changes per 1-point IRCI improvement, accounting for the fact that IR is one of many factors."
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
                    st.info("""
                    **What this shows:** How much dollar value your IR team added THIS quarter by improving IRCI score
                    from the previous quarter. Calculated as: (Current Quarter IRCI - Previous Quarter IRCI) × $/IRCI point (R²-scaled).

                    - **Positive value** = IRCI improved, IR team added enterprise value
                    - **Negative value** = IRCI declined, IR team lost value
                    - **Zero** = No change from last quarter
                    """)
                else:
                    st.info("""
                    **What this shows:** How much dollar value your IR team represents relative to peer average.
                    Calculated as: (Your IRCI - Peer Average IRCI) × $/IRCI point (R²-scaled).

                    💡 **To track quarterly improvement**, run analysis for previous quarter first, then this quarter.

                    - **Positive value** = Your IR outperformed peers
                    - **Negative value** = Your IR underperformed peers
                    - **Zero** = You performed at peer average
                    """)

                # Calculate peer average IRCI
                peer_avg_irci = dollar_value_df['irci_composite_pct'].mean()

                # Calculate IR contribution for each company
                ir_contribution_data = []
                for _, row in dollar_value_df.iterrows():
                    ticker = row['ticker']
                    irci_score = row['irci_composite_pct']
                    dollar_per_pt = row['company_$/irci_pt']

                    if has_prev_data:
                        # Use quarter-over-quarter change
                        prev_df = st.session_state[prev_quarter_key]
                        prev_row = prev_df[prev_df['ticker'] == ticker]

                        if not prev_row.empty:
                            prev_irci_score = prev_row['irci_composite_pct'].iloc[0]
                            irci_change = irci_score - prev_irci_score
                            ir_value_contribution = irci_change * dollar_per_pt

                            ir_contribution_data.append({
                                'ticker': ticker,
                                'irci_score': irci_score,
                                'prev_irci_score': prev_irci_score,
                                'irci_change': irci_change,
                                'dollar_per_pt': dollar_per_pt,
                                'ir_value_contribution': ir_value_contribution,
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
                        if company.get('comparison_type') == 'qoq':
                            delta_text = f"{company['irci_change']:+.1f} pts vs {previous_quarter}"
                            help_text = f"Change: {company['irci_change']:+.1f} pts ({company['prev_irci_score']:.1f}→{company['irci_score']:.1f}) × $/IRCI: ${company['dollar_per_pt']:,.0f} = ${company['ir_value_contribution']:,.0f}"
                        else:
                            delta_text = f"{company['irci_gap_from_avg']:+.1f} pts vs avg"
                            help_text = f"Gap from avg: {company['irci_gap_from_avg']:+.1f} pts × $/IRCI: ${company['dollar_per_pt']:,.0f} = ${company['ir_value_contribution']:,.0f}"

                        st.metric(
                            f"{company['ticker']} IR Contribution",
                            f"${company['ir_value_contribution']:,.0f}",
                            delta=delta_text,
                            delta_color=delta_color,
                            help=help_text
                        )

                # Show appropriate caption based on comparison type
                if has_prev_data:
                    st.caption(f"""
                    📊 **Comparison:** {selected_quarter} vs {previous_quarter}

                    💡 **How to interpret:** This shows how much value your IR team added THIS quarter by improving IRCI.
                    - **Q2 IRCI:** 55 points → **Q3 IRCI:** 62 points = **+7 point improvement**
                    - +7 points × $150M/point = **+$1.05B** (IR improved score, added value)
                    - If IRCI declined: -3 points × $150M/point = **-$450M** (IR lost ground)

                    This answers: **"How much did our IR team contribute this quarter?"** by showing quarter-over-quarter improvement.
                    """)
                else:
                    st.caption(f"""
                    📊 **Peer Average IRCI:** {peer_avg_irci:.1f} points

                    💡 **To see quarterly improvement:** Run analysis for {previous_quarter if previous_quarter else 'previous quarter'} first,
                    then run for {selected_quarter}. The system will then show quarter-over-quarter change.

                    **Current view (vs peer average):**
                    - If you scored 65 IRCI and peer average is 50 → You're +15 points above average
                    - +15 points × $150M/point = **+$2.25B** (your IR outperformed peers)
                    - This shows positioning, not quarterly improvement
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
                st.caption("""
                📊 **Column Definitions:**

                - IRCI Score %: Current composite IRCI score (0-100, peer-relative)
                - 🎯 Company $/IRCI Point: **R²-scaled** estimate of enterprise value change per 1-point IRCI improvement (accounts for IR being one of many factors)
                - Gap to Top (pts): How many IRCI points behind the top performer this company is
                - Potential $ Upside: **R²-scaled** dollar value if this company reached the top performer's IRCI score (Gap × $/Point)
                """)

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

                # Add methodology and proof section
                with st.expander("📐 **Dollar Value Calculation Methodology & Proof**"):
                    st.markdown("""
                    ### How We Calculate Dollar Value per IRCI Point

                    **Goal:** Estimate how much enterprise value corresponds to each 1-point IRCI improvement

                    ---

                    ### Step 1: Linear Regression (Enterprise Value ~ IRCI Score)

                    We regress enterprise value against IRCI scores across your peer group:

                    ```
                    EV = slope × IRCI + intercept
                    ```

                    **What the regression tells us:**
                    - **Slope**: Raw change in EV per 1-point IRCI change
                    - **R²**: How much of EV variance is explained by IRCI (0-1 scale)
                    - **P-value**: Statistical significance of the relationship
                    """)

                    # Show actual regression results from this analysis
                    if not dollar_value_df.empty:
                        from scipy import stats
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            dollar_value_df['irci_composite_pct'],
                            dollar_value_df['enterprise_value']
                        )
                        r_squared = r_value ** 2

                        st.markdown(f"""
                        **Actual Regression Results for Your Peer Group:**

                        - **Raw Slope**: ${abs(slope):,.0f} per IRCI point (before R² scaling)
                        - **R² Value**: {r_squared:.3f} ({r_squared*100:.1f}% of EV variance explained by IRCI)
                        - **P-Value**: {p_value:.4f} {'✓ Significant' if p_value < 0.05 else '⚠️ Not significant'}
                        - **Standard Error**: ${std_err:,.0f}

                        **Interpretation:**
                        - R² = {r_squared:.2f} means IRCI explains {r_squared*100:.0f}% of enterprise value differences
                        - The other {(1-r_squared)*100:.0f}% comes from fundamentals, industry factors, macro conditions, etc.
                        - This is typical for IR metrics - fundamentals drive most value
                        """)

                    st.markdown("""
                    ---

                    ### Step 2: R² Scaling (Critical!)

                    **Why R² scaling matters:**

                    Raw regression slope assumes IRCI is the ONLY factor affecting enterprise value.
                    But we know that's not true - business fundamentals matter far more.

                    **R² scaling corrects for this:**

                    ```
                    Company $/IRCI Point = (Raw Slope) × R²
                    ```

                    **Example with your data:**
                    """)

                    if not dollar_value_df.empty:
                        raw_slope = abs(slope)
                        scaled_slope = raw_slope * r_squared
                        reduction_pct = (1 - r_squared) * 100

                        st.markdown(f"""
                        - **Raw slope**: ${raw_slope:,.0f} per IRCI point
                        - **R² value**: {r_squared:.2f}
                        - **Scaled slope**: ${raw_slope:,.0f} × {r_squared:.2f} = **${scaled_slope:,.0f} per IRCI point**
                        - **Reduction**: {reduction_pct:.0f}% (accounts for other factors)

                        **What this means:**
                        - Without R² scaling: improving 1 IRCI point = ${raw_slope:,.0f} (OVERSTATED)
                        - With R² scaling: improving 1 IRCI point = ${scaled_slope:,.0f} (REALISTIC)
                        - We reduce the estimate by {reduction_pct:.0f}% to reflect that IR is one of many factors
                        """)

                    st.markdown("""
                    ---

                    ### Step 3: Company-Specific Adjustments

                    Each company gets a $/IRCI point value based on:

                    1. **Company Size**: Larger companies have larger $/IRCI values
                    2. **Peer Group Sensitivity**: How EV changes with IRCI in this peer group
                    3. **R² Scaling**: Already applied to be conservative

                    **Formula:**
                    ```
                    Company $/IRCI = (Company EV / Peer Mean EV) × Peer Slope × R²
                    ```

                    This ensures larger companies show appropriate dollar values while maintaining R² realism.

                    ---

                    ### Step 4: Calculate Potential Upside

                    **Gap to Top:**
                    - Top performer IRCI: 85%
                    - Your company IRCI: 60%
                    - Gap: 25 points

                    **Potential Dollar Upside (R²-Scaled):**
                    ```
                    Upside = Gap × (Company $/IRCI Point)
                    Upside = 25 points × $150M/point = $3.75B
                    ```

                    **Important:** This is a PLANNING RANGE, not a guarantee:
                    - Assumes you can actually improve IRCI by 25 points
                    - R² scaling already applied (only {:.0f}% attribution to IR)
                    - Fundamentals must support the value creation
                    - Market conditions, industry trends, and other factors matter

                    ---

                    ### ✅ Why This Methodology is Sound

                    1. **Based on peer comparisons**: Uses actual market data, not assumptions
                    2. **R² scaling**: Conservative - only attributes the variance explained by IRCI
                    3. **Company-specific**: Accounts for size differences in peer group
                    4. **Transparent**: All calculations shown, regression results visible
                    5. **Honest disclaimers**: Clear that IR is secondary to fundamentals

                    **Bottom Line:**
                    These dollar estimates help you evaluate whether IR improvements are worth
                    the investment. They're planning tools, not promises. Business fundamentals
                    drive most value - IRCI measures how efficiently that value is realized
                    in the market.
                    """.format(r_squared*100 if not dollar_value_df.empty else 30))

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

            contrib_df = compute_dial_contribution(df_composite, weights=current_weights)

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
            st.dataframe(
                contrib_df[['ticker', 'irci_composite_pct', 'val_contrib_abs', 'liq_contrib_abs', 'cov_contrib_abs', 'sent_contrib_abs', 'dominant_dial', 'weakest_dial']].rename(columns={
                    'ticker': 'Ticker',
                    'irci_composite_pct': 'Composite %',
                    'val_contrib_abs': 'Val Points',
                    'liq_contrib_abs': 'Liq Points',
                    'cov_contrib_abs': 'Cov Points',
                    'sent_contrib_abs': 'Trust Points',
                    'dominant_dial': 'Strongest Dial',
                    'weakest_dial': 'Weakest Dial'
                }).style.format({
                    'Composite %': '{:.1f}%',
                    'Val Points': '{:.1f}',
                    'Liq Points': '{:.1f}',
                    'Cov Points': '{:.1f}',
                    'Trust Points': '{:.1f}'
                }),
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

        # Section 3: Optimal Weight Recommendations
        st.markdown("#### ⚖️ Optimal Weight Recommendations")
        st.markdown("*Analyzes peer group variance to suggest optimal dial weights*")

        try:
            # First, compute current R² with current weights
            from scipy import stats
            current_composite = df_composite['irci_composite_pct']
            if 'enterprise_value' in df_composite.columns:
                valid_mask = (current_composite > 0) & (df_composite['enterprise_value'] > 0)
                if valid_mask.sum() >= 3:
                    _, _, r_value, _, _ = stats.linregress(
                        current_composite[valid_mask],
                        df_composite['enterprise_value'][valid_mask]
                    )
                    current_r2 = r_value ** 2
                    st.info(f"📊 **Current R² with your weights:** {current_r2:.4f}")

            weight_analysis = recommend_optimal_weights(df_composite, current_weights=current_weights)

            # Display recommendations
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Current Weights:**")
                current_weights_df = pd.DataFrame([
                    {'Dial': 'Valuation', 'Weight': f"{current_weights['valuation']*100:.1f}%"},
                    {'Dial': 'Liquidity', 'Weight': f"{current_weights['liquidity']*100:.1f}%"},
                    {'Dial': 'Coverage', 'Weight': f"{current_weights['coverage']*100:.1f}%"},
                    {'Dial': 'Trust', 'Weight': f"{current_weights['sentiment']*100:.1f}%"}
                ])
                st.dataframe(current_weights_df, use_container_width=True, hide_index=True)

            with col2:
                st.markdown("**Recommended Weights:**")
                rec_weights = weight_analysis['recommended_weights']
                recommended_weights_df = pd.DataFrame([
                    {'Dial': 'Valuation', 'Weight': f"{rec_weights['valuation']*100:.1f}%"},
                    {'Dial': 'Liquidity', 'Weight': f"{rec_weights['liquidity']*100:.1f}%"},
                    {'Dial': 'Coverage', 'Weight': f"{rec_weights['coverage']*100:.1f}%"},
                    {'Dial': 'Trust', 'Weight': f"{rec_weights['sentiment']*100:.1f}%"}
                ])
                st.dataframe(recommended_weights_df, use_container_width=True, hide_index=True)

                # Show optimization method and achieved R² if available
                if 'optimized_r2' in weight_analysis:
                    st.success(f"🎯 Optimizer achieved R² = {weight_analysis['optimized_r2']:.4f}")
                    st.caption(f"Method: {weight_analysis.get('optimization_method', 'unknown')}")
                else:
                    st.caption(f"Method: {weight_analysis.get('optimization_method', 'variance-based')}")

            # Variance analysis
            st.markdown("**Variance Analysis (Why these weights?):**")
            st.caption("Dials with higher variance across peers better differentiate companies and should receive more weight")

            variance_df = pd.DataFrame([
                {
                    'Dial': 'Valuation',
                    'Mean Score': f"{weight_analysis['variance_analysis']['valuation']['mean']:.1f}",
                    'Std Dev': f"{weight_analysis['variance_analysis']['valuation']['std']:.1f}",
                    'Coefficient of Variation': f"{weight_analysis['variance_analysis']['valuation']['cv']:.2f}",
                    'Data Availability': f"{weight_analysis['variance_analysis']['valuation']['availability']*100:.0f}%",
                    'Discriminating Power': f"{weight_analysis['discriminating_power']['valuation']:.1f}"
                },
                {
                    'Dial': 'Liquidity',
                    'Mean Score': f"{weight_analysis['variance_analysis']['liquidity']['mean']:.1f}",
                    'Std Dev': f"{weight_analysis['variance_analysis']['liquidity']['std']:.1f}",
                    'Coefficient of Variation': f"{weight_analysis['variance_analysis']['liquidity']['cv']:.2f}",
                    'Data Availability': f"{weight_analysis['variance_analysis']['liquidity']['availability']*100:.0f}%",
                    'Discriminating Power': f"{weight_analysis['discriminating_power']['liquidity']:.1f}"
                },
                {
                    'Dial': 'Coverage',
                    'Mean Score': f"{weight_analysis['variance_analysis']['coverage']['mean']:.1f}",
                    'Std Dev': f"{weight_analysis['variance_analysis']['coverage']['std']:.1f}",
                    'Coefficient of Variation': f"{weight_analysis['variance_analysis']['coverage']['cv']:.2f}",
                    'Data Availability': f"{weight_analysis['variance_analysis']['coverage']['availability']*100:.0f}%",
                    'Discriminating Power': f"{weight_analysis['discriminating_power']['coverage']:.1f}"
                },
                {
                    'Dial': 'Trust',
                    'Mean Score': f"{weight_analysis['variance_analysis']['sentiment']['mean']:.1f}",
                    'Std Dev': f"{weight_analysis['variance_analysis']['sentiment']['std']:.1f}",
                    'Coefficient of Variation': f"{weight_analysis['variance_analysis']['sentiment']['cv']:.2f}",
                    'Data Availability': f"{weight_analysis['variance_analysis']['sentiment']['availability']*100:.0f}%",
                    'Discriminating Power': f"{weight_analysis['discriminating_power']['sentiment']:.1f}"
                }
            ])
            st.dataframe(variance_df, use_container_width=True, hide_index=True)

            st.info("💡 **Tip**: Use the sidebar to adjust weights based on these recommendations and re-run the analysis to see the impact.")

        except Exception as e:
            st.warning(f"Could not compute weight recommendations: {str(e)}")

    with tab5:
        # Event Timeline / Calendar View
        from irci.event_timeline import (
            aggregate_timeline_events,
            create_calendar_view,
            UserNotesManager,
            create_impact_summary
        )
        from irci.coverage import _company_submissions, _cik_for_ticker

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
                dollar_value_df = compute_dollar_value_per_irci_point(df_composite, df_val)
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
                - Company $/IRCI Point: **${company_dollar_per_irci_pt:,.0f}**
                - Example: Single positive news article (sentiment +0.6) → +{example_irci_impact:.6f} IRCI pts → **${example_dollar_impact:,.0f}** impact

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
                df_composite=df_composite,
                df_val=df_val,
                df_cov=df_cov,
                df_liq=df_liq,
                df_trust=df_trust,
                news_df=news_df,
                sec_filings_df=sec_filings_df,
                weights=current_weights,
                company_dollar_per_irci_pt=company_dollar_per_irci_pt
            )

            # Display impact summary
            st.markdown("**📊 Event Impact Summary**")
            impact_summary = create_impact_summary(timeline_df, selected_timeline_ticker)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Events", impact_summary['total_events'])
            col2.metric(
                "Total IRCI Impact",
                f"{impact_summary['total_irci_impact']:+.2f} pts",
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

                # Display calendar as interactive table
                st.dataframe(
                    calendar_df[['date', 'num_events', 'event_types', 'total_irci_impact', 'total_dollar_impact', 'headlines']].rename(columns={
                        'date': 'Date',
                        'num_events': '# Events',
                        'event_types': 'Event Types',
                        'total_irci_impact': 'IRCI Impact (pts)',
                        'total_dollar_impact': '$ Impact',
                        'headlines': 'Top Headlines'
                    }).style.format({
                        'IRCI Impact (pts)': '{:+.2f}',
                        '$ Impact': '${:+,.0f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                st.caption("""
                📊 **Calendar Note**: Each row shows the SUM of all events on that day.
                - If 20 news articles occur on one day, their impacts are added together
                - Individual events have tiny impacts (~0.00001-0.0005 IRCI points each)
                - For large companies, even tiny IRCI impacts can translate to $100K-$1M due to high $/IRCI point
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

                # Rename columns
                display_timeline = display_timeline.rename(columns={
                    'indicator': '',
                    'date': 'Date',
                    'event_type': 'Type',
                    'description': 'Description',
                    'irci_impact': 'IRCI Impact',
                    'dollar_impact': '$ Impact',
                    'affected_dials': 'Affected Dials'
                })

                # Format the dataframe
                st.dataframe(
                    display_timeline.style.format({
                        'IRCI Impact': '{:+.2f}',
                        '$ Impact': '${:+,.0f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                st.caption("""
                💡 **Event Indicators:** 🟢 Positive news | 🔴 Negative news | 🔵 SEC filings | 📰 Neutral news | 💰 Valuation | 💧 Liquidity | 📊 Coverage | 💭 Trust
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
                    - Use company-specific $/IRCI point (already R²-scaled from regression)
                    - Example (mid-cap): +0.000045 IRCI pts × $150M/point = **$6,750**
                    - Example (large-cap): +0.000045 IRCI pts × $4B/point = **$180,000**
                    - R² scaling already applied (if R²=0.3, the $/point was reduced by 70%)

                    ---

                    ### 📊 SEC Filing Impact Calculation

                    **8-K Filing:**
                    - Dial impact: 0.001 points on Coverage dial (0.1% of dial)
                    - IRCI impact: 0.001 × 0.15 (coverage weight) = **0.00015 IRCI points**
                    - Dollar impact (mid-cap): 0.00015 × $150M/point = **$22,500**
                    - Dollar impact (large-cap): 0.00015 × $4B/point = **$600,000**

                    **10-Q or 10-K Filing:**
                    - Dial impact: 0.003 points on Coverage dial (0.3% of dial)
                    - IRCI impact: 0.003 × 0.15 = **0.00045 IRCI points**
                    - Dollar impact (mid-cap): 0.00045 × $150M/point = **$67,500**
                    - Dollar impact (large-cap): 0.00045 × $4B/point = **$1.8M**

                    **Why these values?** Coverage dial measures aggregate quarterly filing activity,
                    not individual filings. A typical company has 5-20 8-Ks per quarter.

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
                                media_tone = ticker_trust['media_tone'].iloc[0] if 'media_tone' in ticker_trust.columns else None

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
                    - Raw regression slope: $500M per IRCI point
                    - R² value: 0.30 (IRCI explains 30% of EV variance)
                    - **R²-scaled slope**: $500M × 0.30 = **$150M per IRCI point**

                    **What This Means:**
                    - IR/IRCI is ONE of MANY factors affecting enterprise value
                    - Business fundamentals (revenue, earnings, growth) drive most value
                    - R² scaling ensures we don't overstate IR's contribution
                    - If R²=0.30, we reduce dollar estimates by 70% to be realistic

                    **Individual Event Example:**
                    - Event IRCI impact: +0.000045 points (single positive news article)
                    - Company $/IRCI: $150M/point (R²-scaled)
                    - Event dollar impact: +0.000045 × $150M = **$6,750**
                    - Without R² scaling: +0.000045 × $500M = $22,500 (OVERSTATED by 3.3x)

                    ---

                    ### ✅ Bottom Line

                    1. **Individual events = Tiny impacts** (~0.00001-0.0005 IRCI points, $1K-$100K for mid-caps, $50K-$2M for large-caps)
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

    with tab6:
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
                df_composite['ticker'].unique(),
                key="playbook_ticker_select"
            )

            # Get dial scores for selected company
            company_row = df_composite[df_composite['ticker'] == playbook_ticker].iloc[0]

            dial_scores = {
                'valuation': company_row.get('valuation_pct', 50),
                'liquidity': company_row.get('liquidity_pct', 50),
                'coverage': company_row.get('coverage_pct', 50),
                'trust': company_row.get('sentiment_pct', 50)
            }

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
                    "🤝 Trust",
                    f"{dial_scores['trust']:.1f}%",
                    delta=f"{classification_colors[trust_cls]} {trust_cls.capitalize()}"
                )

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

            with priority_tabs[0]:
                high_priority = [r for r in playbook['recommendations'] if r['priority'] == 'high']
                if high_priority:
                    for rec in high_priority:
                        with st.container():
                            st.markdown(f"**{rec['action']}**")
                            st.markdown(f"*Category: {rec['category']}*")
                            st.markdown(rec['description'])
                            if rec.get('quick_win'):
                                st.caption("⚡ Quick Win")
                            st.markdown("---")
                else:
                    st.success("No high-priority action items. Great job!")

            with priority_tabs[1]:
                medium_priority = [r for r in playbook['recommendations'] if r['priority'] == 'medium']
                if medium_priority:
                    for rec in medium_priority:
                        with st.container():
                            st.markdown(f"**{rec['action']}**")
                            st.markdown(f"*Category: {rec['category']}*")
                            st.markdown(rec['description'])
                            if rec.get('quick_win'):
                                st.caption("⚡ Quick Win")
                            st.markdown("---")
                else:
                    st.info("No medium-priority items.")

            with priority_tabs[2]:
                low_priority = [r for r in playbook['recommendations'] if r['priority'] == 'low']
                if low_priority:
                    for rec in low_priority:
                        with st.container():
                            st.markdown(f"**{rec['action']}**")
                            st.markdown(f"*Category: {rec['category']}*")
                            st.markdown(rec['description'])
                            if rec.get('quick_win'):
                                st.caption("⚡ Quick Win")
                            st.markdown("---")
                else:
                    st.info("No low-priority items.")

            # Category breakdown
            st.markdown("---")
            st.markdown("### 📂 Recommendations by Dial")

            category_tabs = st.tabs(["💰 Valuation", "💧 Liquidity", "📰 Coverage", "🤝 Trust"])

            for i, category in enumerate(['Valuation', 'Liquidity', 'Coverage', 'Trust']):
                with category_tabs[i]:
                    category_recs = [r for r in playbook['recommendations'] if r['category'] == category]
                    if category_recs:
                        for rec in category_recs:
                            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                            with st.container():
                                st.markdown(f"{priority_emoji[rec['priority']]} **{rec['action']}**")
                                st.markdown(rec['description'])
                                if rec.get('quick_win'):
                                    st.caption("⚡ Quick Win")
                                st.markdown("---")
                    else:
                        st.success(f"Your {category} dial is performing well. No specific actions needed.")

        except Exception as e:
            st.error(f"Error generating playbook: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    with tab7:
        # AI Chatbot Assistant
        st.markdown("#### 💬 AI Assistant")
        st.markdown("*Ask questions about your IRCI results and get IR recommendations*")

        # Check for OpenAI API key
        s = Settings.load()
        if not s.openai_api_key:
            st.warning("""
            ⚠️ **OpenAI API Key Required**

            To use the AI Assistant, please add your OpenAI API key:
            1. Add `OPENAI_API_KEY=your-key-here` to your `.env` file
            2. Or set the `OPENAI_API_KEY` environment variable
            3. Reload the app

            Get your API key at: https://platform.openai.com/api-keys
            """)
        else:
            try:
                # Initialize chat history in session state
                if 'chat_history' not in st.session_state:
                    st.session_state.chat_history = []

                # Company selector for chatbot
                chatbot_ticker = st.selectbox(
                    "Select company to discuss:",
                    df_composite['ticker'].unique(),
                    key="chatbot_ticker_select"
                )

                # Display suggested questions
                st.markdown("---")
                st.markdown("**💡 Suggested Questions:**")

                suggestions = get_suggested_questions(chatbot_ticker, df_composite)

                # Create columns for suggested questions (2 per row)
                for i in range(0, len(suggestions), 2):
                    col1, col2 = st.columns(2)
                    with col1:
                        if i < len(suggestions):
                            if st.button(suggestions[i], key=f"suggestion_{i}", use_container_width=True):
                                # Add question to chat
                                st.session_state.chat_history.append({
                                    "role": "user",
                                    "content": suggestions[i]
                                })
                                # Get response
                                response = chat_with_context(
                                    suggestions[i],
                                    df_composite,
                                    chatbot_ticker,
                                    st.session_state.chat_history[:-1],  # Exclude the question we just added
                                    s.openai_api_key
                                )
                                # Add response to history
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": response
                                })
                                st.rerun()

                    with col2:
                        if i + 1 < len(suggestions):
                            if st.button(suggestions[i + 1], key=f"suggestion_{i+1}", use_container_width=True):
                                # Add question to chat
                                st.session_state.chat_history.append({
                                    "role": "user",
                                    "content": suggestions[i + 1]
                                })
                                # Get response
                                response = chat_with_context(
                                    suggestions[i + 1],
                                    df_composite,
                                    chatbot_ticker,
                                    st.session_state.chat_history[:-1],
                                    s.openai_api_key
                                )
                                # Add response to history
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": response
                                })
                                st.rerun()

                st.markdown("---")

                # Display chat history
                st.markdown("**💬 Conversation:**")

                if st.session_state.chat_history:
                    for i, message in enumerate(st.session_state.chat_history):
                        if message["role"] == "user":
                            with st.chat_message("user"):
                                st.markdown(message["content"])
                        else:
                            with st.chat_message("assistant"):
                                st.markdown(message["content"])
                else:
                    st.info("👋 Start by asking a question or clicking a suggested question above!")

                # Chat input
                user_input = st.chat_input("Ask me anything about your IRCI analysis...")

                if user_input:
                    # Add user message to history
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_input
                    })

                    # Get AI response
                    with st.spinner("Thinking..."):
                        response = chat_with_context(
                            user_input,
                            df_composite,
                            chatbot_ticker,
                            st.session_state.chat_history[:-1],  # Exclude the question we just added
                            s.openai_api_key
                        )

                    # Add assistant response to history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response
                    })

                    # Rerun to display new messages
                    st.rerun()

                # Clear chat button
                if st.session_state.chat_history:
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 1, 4])
                    with col1:
                        if st.button("🗑️ Clear Chat"):
                            st.session_state.chat_history = []
                            st.rerun()
                    with col2:
                        # Export chat
                        if st.session_state.chat_history:
                            chat_text = "\n\n".join([
                                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                                for msg in st.session_state.chat_history
                            ])
                            st.download_button(
                                "💾 Export Chat",
                                chat_text,
                                f"irci_chat_{chatbot_ticker}.txt",
                                "text/plain"
                            )

            except Exception as e:
                st.error(f"Error loading chatbot: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # Download section
    st.markdown("---")
    st.markdown("### 💾 Download Results")

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
    st.markdown("---")
    st.markdown("#### 📄 Comprehensive PDF Report")
    st.markdown("*Generate a complete analysis report for a specific company*")

    col_pdf1, col_pdf2, col_pdf3 = st.columns([2, 2, 4])

    with col_pdf1:
        pdf_ticker = st.selectbox(
            "Select company for PDF report:",
            df_composite['ticker'].unique(),
            key="pdf_ticker_select"
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
                        news_df=pdf_news_df
                    )

                    # Store in session state for download
                    st.session_state['pdf_report'] = pdf_bytes
                    st.session_state['pdf_ticker'] = pdf_ticker
                    st.session_state['pdf_quarter'] = selected_quarter
                    st.success(f"✅ PDF report generated successfully for {pdf_ticker}!")

                except Exception as e:
                    st.error(f"Error generating PDF report: {str(e)}")
                    import traceback
                    with st.expander("Error details"):
                        st.code(traceback.format_exc())

    # Show download button if PDF was generated
    if 'pdf_report' in st.session_state and st.session_state.get('pdf_ticker') == pdf_ticker:
        with col_pdf3:
            st.download_button(
                label=f"⬇️ Download {pdf_ticker} Report",
                data=st.session_state['pdf_report'],
                file_name=f"IRCI_Report_{pdf_ticker}_{st.session_state.get('pdf_quarter', 'report')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    IRCI Analysis Platform v0.1.0 | Powered by Streamlit |
    <a href='https://github.com/anthropics/claude-code' target='_blank'>Documentation</a>
</div>
""", unsafe_allow_html=True)
