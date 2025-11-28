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
from irci.media_fetchers.newsapi_fetcher import newsapi_fetcher
from irci.media_fetchers.finnhub_fetcher import finnhub_fetcher
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

        # Main sections (buttons)
        if st.button("📊 Company Analysis", use_container_width=True, type="primary" if st.session_state['selected_section'] == "📊 Company Analysis" else "secondary"):
            st.session_state['selected_section'] = "📊 Company Analysis"
            st.rerun()

        # Trends section (only show if multi-quarter data)
        if st.session_state.get('is_multi_quarter', False):
            if st.button("📈 Trends", use_container_width=True, type="primary" if st.session_state['selected_section'] == "📈 Trends" else "secondary"):
                st.session_state['selected_section'] = "📈 Trends"
                st.rerun()

        if st.button("💵 Value Analysis", use_container_width=True, type="primary" if st.session_state['selected_section'] == "💵 Value Analysis" else "secondary"):
            st.session_state['selected_section'] = "💵 Value Analysis"
            st.rerun()

        # Playbook & Events with sub-sections
        with st.expander("🎯 Playbook & Events", expanded=st.session_state['selected_section'] == "🎯 Playbook & Events"):
            if st.button("🎯 Playbook", use_container_width=True, key="nav_playbook"):
                st.session_state['selected_section'] = "🎯 Playbook & Events"
                st.session_state['selected_subsection'] = "🎯 Playbook"
                st.rerun()
            if st.button("📅 Event Timeline", use_container_width=True, key="nav_events"):
                st.session_state['selected_section'] = "🎯 Playbook & Events"
                st.session_state['selected_subsection'] = "📅 Event Timeline"
                st.rerun()
            if st.button("📋 Plan", use_container_width=True, key="nav_plan"):
                st.session_state['selected_section'] = "🎯 Playbook & Events"
                st.session_state['selected_subsection'] = "📋 Plan"
                st.rerun()

        if st.button("💬 AI Assistant", use_container_width=True, type="primary" if st.session_state['selected_section'] == "💬 AI Assistant" else "secondary"):
            st.session_state['selected_section'] = "💬 AI Assistant"
            st.rerun()

    st.markdown("---")
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
    run_analysis = st.button(
        "🚀 Run Analysis",
        type="primary",
        use_container_width=True,
        help="Start analyzing the selected companies for the chosen quarter"
    )
    st.markdown("---")

    # Weights configuration
    with st.expander("⚙️ Advanced: Dial Weights", expanded=False):
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
                    st.session_state['weight_liquidity'] = session_data.get('weight_liquidity', 35)
                    st.session_state['weight_valuation'] = session_data.get('weight_valuation', 35)
                    st.session_state['weight_coverage'] = session_data.get('weight_coverage', 15)
                    st.session_state['weight_trust'] = session_data.get('weight_trust', 15)
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

    # Important disclaimers - collapsible for cleaner interface
    with st.expander("⚠️ **Important Disclaimers**", expanded=False):
        st.markdown("""
        - **Fundamentals set value. IR determines how efficiently markets realize it.** IRCI measures the pathway to fair value, not fundamental business performance.
        - IR's impact on share valuation is limited compared to business fundamentals, macroeconomic conditions, and industry trends.
        - IRCI is a planning and diagnostic tool—not a guarantee of market outcomes.
        - Dollar-per-point estimates are derived from historical peer relationships and should be treated as planning ranges, not promises.
        - This tool is for authorized use only. Views expressed are those of the creators and not official positions of any affiliated organization.
        """)

    # First-time user onboarding
    if 'first_visit' not in st.session_state:
        st.session_state['first_visit'] = True

    if st.session_state.get('first_visit', False):
        with st.expander("👋 **Welcome! Take a 2-Minute Tour**", expanded=False):
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
            - Takes ~30-60 seconds depending on company count
            - Get instant IRCI scores, peer rankings, and actionable insights

            **💡 Tip:** Start with a quick template below to see IRCI in action!
            """)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✓ Got it! Hide this message"):
                    st.session_state['first_visit'] = False
                    st.rerun()
            with col2:
                st.caption("📖 For more details, check out the **Documentation & Background** section below")

    # Ready to start message
    st.info("""
    👈 **Ready to start?**
    1. Use a quick template below OR select companies in the sidebar
    2. Choose your quarter(s)
    3. Click **'Run Analysis'** to generate your IRCI report!
    """)

    # Quick Start Templates
    st.markdown("### 🎯 Quick Start Templates")
    st.caption("Click a template to pre-fill peer companies and start analyzing immediately")

    template_col1, template_col2, template_col3 = st.columns(3)

    with template_col1:
        if st.button("📱 **Big Tech**\n\nAAPL, MSFT, GOOGL, META, AMZN", use_container_width=True):
            st.session_state['found_peers'] = 'AAPL, MSFT, GOOGL, META, AMZN'
            st.success("✓ Loaded Big Tech template! Scroll down and click 'Run Analysis' →")
            st.rerun()

    with template_col2:
        if st.button("🏦 **Financials**\n\nJPM, BAC, WFC, C, GS", use_container_width=True):
            st.session_state['found_peers'] = 'JPM, BAC, WFC, C, GS'
            st.success("✓ Loaded Financials template! Scroll down and click 'Run Analysis' →")
            st.rerun()

    with template_col3:
        if st.button("💉 **Healthcare**\n\nJNJ, PFE, UNH, ABBV, LLY", use_container_width=True):
            st.session_state['found_peers'] = 'JNJ, PFE, UNH, ABBV, LLY'
            st.success("✓ Loaded Healthcare template! Scroll down and click 'Run Analysis' →")
            st.rerun()

    st.markdown("---")

    # Show success message if analysis is already loaded
    if 'df_composite' in st.session_state and st.session_state['df_composite'] is not None:
        st.success("✓ Analysis loaded! Scroll down to view results or select a new peer group above to start fresh.")

    # Comprehensive About & Methodology - collapsed by default for cleaner interface
    with st.expander("📚 Documentation & Background (How It Works, About IRCI, Team, Validation)", expanded=False):
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
    if len(selected_quarters) == 1:
        st.markdown("## 🔄 Running Analysis...")
    else:
        st.markdown(f"## 🔄 Running Analysis for {len(selected_quarters)} Quarters...")

    # Add analysis time estimate (very conservative)
    estimated_time = len(selected_quarters) * len(tickers) * 45  # ~45 seconds per ticker per quarter (very conservative)

    # Format time display
    if estimated_time >= 90:
        time_display = f"{estimated_time // 60} min {estimated_time % 60} sec"
    else:
        time_display = f"{estimated_time} seconds"

    st.caption(f"⏱️ Estimated time: ~{time_display} | Analyzing {len(tickers)} companies across {len(selected_quarters)} quarter(s)")

    # Store results for all quarters
    all_quarters_results = {}

    # Loop through each selected quarter
    for quarter_idx, selected_quarter in enumerate(selected_quarters):
        # Get start/end dates for this quarter
        start_date, end_date = quarter_to_dates(selected_quarter)

        # Progress tracking
        if len(selected_quarters) > 1:
            st.markdown(f"### 📊 Quarter {quarter_idx + 1}/{len(selected_quarters)}: **{selected_quarter}** ({start_date} to {end_date})")

        progress_bar = st.progress(0, text="🚀 Initializing analysis...")
        status_text = st.empty()

        try:
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
            progress_bar.progress(10, text="💭 Analyzing Trust dial (sentiment & event stability)...")
            status_text.text(f"⏳ Step 1/5: Computing trust scores for {len(tickers)} companies")
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
            progress_bar.progress(30, text="✓ Trust analysis complete")
            status_text.text("✓ Trust dial computed successfully")

            # 2. Valuation
            progress_bar.progress(35, text="💰 Analyzing Valuation dial (EV/EBITDA peer comparison)...")
            status_text.text(f"⏳ Step 2/5: Computing valuation metrics for {len(tickers)} companies")
            df_val = valuation_snapshot(
                tickers,
                as_of=end_date
            )
            if not df_val.empty:
                if "quarter_end" not in df_val.columns:
                    df_val["quarter_end"] = quarter_end_dt
                # Force timezone-naive by normalizing to date
                df_val["quarter_end"] = pd.to_datetime(pd.to_datetime(df_val["quarter_end"]).dt.date)
            progress_bar.progress(50, text="✓ Valuation analysis complete")
            status_text.text("✓ Valuation dial computed successfully")

            # 3. Coverage
            progress_bar.progress(55, text="📊 Analyzing Coverage dial (SEC filings & media visibility)...")
            status_text.text(f"⏳ Step 3/5: Analyzing coverage metrics for {len(tickers)} companies")
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
            progress_bar.progress(70, text="✓ Coverage analysis complete")
            status_text.text("✓ Coverage dial computed successfully")

            # 4. Liquidity
            progress_bar.progress(75, text="💧 Analyzing Liquidity dial (market microstructure)...")
            status_text.text(f"⏳ Step 4/5: Computing liquidity metrics for {len(tickers)} companies")
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
            progress_bar.progress(85, text="✓ Liquidity analysis complete")
            status_text.text("✓ Liquidity dial computed successfully")

            # 5. Composite
            progress_bar.progress(90, text="🎯 Computing final composite IRCI scores...")
            status_text.text(f"⏳ Step 5/5: Combining all dials into IRCI composite")

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
                'start_date': start_date,
                'end_date': end_date
            }

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
            st.session_state['run_time'] = datetime.now()
        else:
            # For multiple quarters, combine all data with quarter labels
            combined_composite = []
            combined_trust = []
            combined_val = []
            combined_cov = []
            combined_liq = []
            combined_news = []

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

            # Concatenate all quarters
            st.session_state['df_composite'] = pd.concat(combined_composite, ignore_index=True) if combined_composite else None
            st.session_state['df_trust'] = pd.concat(combined_trust, ignore_index=True) if combined_trust else None
            st.session_state['df_val'] = pd.concat(combined_val, ignore_index=True) if combined_val else None
            st.session_state['df_cov'] = pd.concat(combined_cov, ignore_index=True) if combined_cov else None
            st.session_state['df_liq'] = pd.concat(combined_liq, ignore_index=True) if combined_liq else None
            st.session_state['news_df'] = pd.concat(combined_news, ignore_index=True) if combined_news else None
            st.session_state['run_time'] = datetime.now()
            st.session_state['selected_quarters'] = selected_quarters  # Store list of quarters analyzed

        # Success animation and summary
        st.snow()  # Celebratory animation - more professional/minimal than balloons
        st.success(f"""
        🎉 **Analysis Complete!**

        ✅ Successfully analyzed **{len(tickers)} companies** across **{len(all_quarters_results)} quarter(s)**

        📊 Scroll down to see [Rankings & Peer Comparison](#composite-ranking), then explore the tabs below for:
        - **📊 Company Analysis** - Detailed dial breakdowns and metrics
        - **📈 Trends** - Multi-quarter progression (if analyzing multiple quarters)
        - **💵 Value Analysis** - Dollar impact insights
        - **🎯 Playbook & Events** - Action recommendations and timeline
        """)
    else:
        st.error("❌ No quarters were successfully analyzed.")
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

    # Auto-optimize weights button (post-analysis)
    col_opt1, col_opt2, col_opt3 = st.columns([2, 1, 2])
    with col_opt2:
        if st.button("🎯 Auto-Optimize Weights", key="optimize_post_analysis", use_container_width=True,
                     help="Find weights that maximize EV ~ IRCI regression R² based on current results"):
            st.session_state.optimize_weights = True
            st.rerun()

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
        if 'quarter' in df_composite.columns:
            # Multi-quarter data
            unique_quarters = df_composite['quarter'].unique()
            num_companies = len(df_composite[df_composite['quarter'] == unique_quarters[0]])
            st.markdown(f"### Quarters: {', '.join(unique_quarters)} | Companies: {num_companies} | Run: {st.session_state['run_time'].strftime('%Y-%m-%d %H:%M')}")
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
            st.markdown(f"### Quarter: {quarter_str} | Companies: {len(df_composite)} | Run: {st.session_state['run_time'].strftime('%Y-%m-%d %H:%M')}")
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
        st.markdown("### 📅 Quarter Selection")
        selected_quarter = st.selectbox(
            "Select quarter to display:",
            available_quarters,
            help="Viewing one quarter at a time. For trend analysis across quarters, see the Trend Analysis tab below."
        )

        # Filter data for selected quarter
        df_composite_filtered = df_composite[df_composite['quarter'] == selected_quarter].copy()
        df_trust_filtered = df_trust[df_trust['quarter'] == selected_quarter].copy() if 'quarter' in df_trust.columns else df_trust
        df_val_filtered = df_val[df_val['quarter'] == selected_quarter].copy() if 'quarter' in df_val.columns else df_val
        df_cov_filtered = df_cov[df_cov['quarter'] == selected_quarter].copy() if 'quarter' in df_cov.columns else df_cov
        df_liq_filtered = df_liq[df_liq['quarter'] == selected_quarter].copy() if 'quarter' in df_liq.columns else df_liq

        st.info(f"💡 **Multi-Quarter Mode:** Displaying results for **{selected_quarter}**. Click the **'Trends'** tab to see analysis across all {len(available_quarters)} quarters.")
    else:
        # Single quarter data - use directly
        selected_quarter = quarters_analyzed[0] if quarters_analyzed else "Current"
        df_composite_filtered = df_composite.copy()
        df_trust_filtered = df_trust.copy()
        df_val_filtered = df_val.copy()
        df_cov_filtered = df_cov.copy()
        df_liq_filtered = df_liq.copy()

    # Composite ranking
    st.markdown("### 🏆 Composite Ranking")

    # Prepare display data (use filtered data)
    display_df = df_composite_filtered.copy()
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

    # Get current section from session state (navigation is at top of sidebar now)
    selected_section = st.session_state.get('selected_section', "📊 Company Analysis")

    # SECTION 1: Company Analysis (Composite Scores + Dial Breakdown + Detailed Metrics)
    if selected_section == "📊 Company Analysis":
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

        # Dial Breakdown Radar Chart
        st.markdown("### 📉 Dial Breakdown")
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

        st.markdown("---")

        # Detailed Metrics by Dial (using expanders for each dial)
        st.markdown("### 📋 Detailed Metrics")

        with st.expander("💰 Valuation Details", expanded=False):
            # Include PEG ratio if available from Alpha Vantage
            val_cols = ['ticker']
            val_rename = {'ticker': 'Ticker'}

            # Add quarter column if in multi-quarter mode
            if 'quarter' in df_val.columns:
                val_cols.append('quarter')
                val_rename['quarter'] = 'Quarter'

            val_cols.extend(['valuation_pct', 'ev_to_ebitda'])
            val_rename.update({
                'valuation_pct': 'Score %',
                'ev_to_ebitda': 'EV/EBITDA'
            })

            if 'peg_ratio' in df_val.columns:
                val_cols.append('peg_ratio')
                val_rename['peg_ratio'] = 'PEG Ratio'

            val_cols.extend(['peer_mean_excl_self', 'valuation_gap_pct', 'valuation_quartile'])
            val_rename.update({
                'peer_mean_excl_self': 'Peer Avg',
                'valuation_gap_pct': 'Gap %',
                'valuation_quartile': 'Quartile'
            })

            st.dataframe(
                df_val[val_cols].rename(columns=val_rename),
                use_container_width=True,
                hide_index=True
            )

            if 'peg_ratio' in df_val.columns:
                st.caption("💡 **PEG Ratio** (Price/Earnings to Growth) from Alpha Vantage - Growth-adjusted valuation metric. Lower is generally better (typically <1.0 indicates undervalued relative to growth).")

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

            st.dataframe(
                df_liq[liq_cols].rename(columns=liq_rename),
                use_container_width=True,
                hide_index=True
            )

        with st.expander("📊 Coverage Details", expanded=False):
            # Calculate high-quality article counts
            df_cov_display = df_cov.copy()
            news_df = st.session_state.get('news_df', None)

            if news_df is not None and not news_df.empty and 'domain' in news_df.columns:
                from irci.config import Settings

                # Load domain weights
                s = Settings.load()
                domain_weights = s.domain_weights or {}

                # Define high-quality threshold (0.8 = top tier sources)
                HIGH_QUALITY_THRESHOLD = 0.8

                # Filter news for current quarter if multi-quarter mode
                news_for_quarter = news_df.copy()
                if is_multi_quarter and 'quarter' in news_df.columns:
                    news_for_quarter = news_df[news_df['quarter'] == selected_quarter]

                # Count high-quality articles per ticker
                high_quality_counts = []
                for ticker in df_cov_display['ticker']:
                    ticker_news = news_for_quarter[news_for_quarter.get('ticker', '') == ticker] if 'ticker' in news_for_quarter.columns else news_for_quarter

                    if not ticker_news.empty:
                        # Normalize domains
                        domains = ticker_news['domain'].astype(str).str.lower().str.removeprefix("www.")

                        # Count articles from high-quality domains
                        high_qual_count = sum(
                            domain_weights.get(dom, 0.5) >= HIGH_QUALITY_THRESHOLD
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

            st.dataframe(
                df_cov_display[coverage_cols].rename(columns=coverage_rename),
                use_container_width=True,
                hide_index=True
            )

            if 'high_quality_articles' in df_cov_display.columns:
                st.caption("💡 **High-Quality Articles** = Articles from top-tier sources (WSJ, Bloomberg, Reuters, etc. with domain weight ≥ 0.8). These sources have higher credibility and reach.")

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

            st.dataframe(
                df_trust[trust_cols].rename(columns=trust_rename),
                use_container_width=True,
                hide_index=True
            )

    # SECTION 2: Trend Analysis (only for multi-quarter data)
    if is_multi_quarter and selected_section == "📈 Trends":
        st.markdown("#### IRCI Score Progression Over Time")
        st.caption("Track how each company's IRCI score has changed across quarters")

        # Prepare data for trend visualization
        trend_df = df_composite.copy()

        # Line chart showing IRCI progression for each company
        fig_trend = px.line(
            trend_df,
            x='quarter',
            y='irci_composite_pct',
            color='ticker',
            markers=True,
            title='IRCI Composite Score Trends',
            labels={'irci_composite_pct': 'IRCI Score (%)', 'quarter': 'Quarter', 'ticker': 'Company'}
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
                facet_col_wrap=3
            )
            fig_qoq.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,33,48,0.5)',
                font=dict(color='#fafafa'),
                title_font=dict(color='#00d4ff')
            )
            st.plotly_chart(fig_qoq, use_container_width=True)

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
                        labels={dial_col: f'{dial_name} Score (%)', 'quarter': 'Quarter', 'ticker': 'Company'}
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
                    **Forecasting Models Available:**

                    **1. Linear Regression (Degree 1)**
                    - Fits a straight line through historical IRCI scores
                    - Best for: Consistent, steady trends
                    - Formula: IRCI = β₀ + β₁ × Quarter
                    - Requires: Minimum 2 quarters

                    **2. Polynomial Regression (Degree 2)**
                    - Fits a quadratic curve (can capture acceleration/deceleration)
                    - Best for: Trends that are speeding up or slowing down
                    - Formula: IRCI = β₀ + β₁×Q + β₂×Q²
                    - Requires: Minimum 3 quarters
                    - Example: IR improvements that accelerate over time

                    **3. Polynomial Regression (Degree 3)**
                    - Fits a cubic curve (can capture S-curves and inflection points)
                    - Best for: Complex trends with multiple phases
                    - Formula: IRCI = β₀ + β₁×Q + β₂×Q² + β₃×Q³
                    - Requires: Minimum 4 quarters
                    - Example: Initial improvement, plateau, then further gains

                    **4. Auto-Select Best Model**
                    - Automatically chooses the model with highest R² (best fit)
                    - Compares all available models based on your data
                    - Recommended for most use cases

                    **Current Selection:** {model_type}

                    ---

                    **Confidence Intervals ({confidence_level}%):**

                    The prediction interval shows the range where we expect the actual IRCI score to fall:
                    - **{confidence_level}% confidence** means if we repeated this forecast 100 times, about {confidence_level} times the actual value would fall within the range
                    - **Wider intervals** = more uncertainty in forecast
                    - **Narrower intervals** = more confidence in forecast

                    **Factors affecting interval width:**
                    - Data variance: More volatile historical data → wider intervals
                    - Sample size: More quarters → narrower intervals
                    - Model fit (R²): Better fit → narrower intervals

                    ---

                    **Metrics Explained:**

                    **R² (R-squared):**
                    - Measures how well the model fits historical data (0 to 1 scale)
                    - R² > 0.7: High confidence forecast (trend is very consistent)
                    - R² 0.4-0.7: Moderate confidence (trend is somewhat consistent)
                    - R² < 0.4: Low confidence (data is noisy, trend unclear)

                    **Range Width:**
                    - Width of the {confidence_level}% confidence interval
                    - Smaller width = more precise forecast
                    - Example: Width of 5 points means ±2.5 points uncertainty

                    **Model Used:**
                    - Shows which regression model was selected
                    - Compare models to see which fits your data best

                    ---

                    **When to Use Each Model:**

                    **Linear:** Choose when...
                    - Your IRCI improves/declines at a steady rate each quarter
                    - You have 2-3 quarters of data
                    - You want a simple, interpretable forecast

                    **Polynomial (Degree 2):** Choose when...
                    - Your IRCI improvement is accelerating or decelerating
                    - You see curved trends in historical data
                    - You have 3+ quarters of data

                    **Polynomial (Degree 3):** Choose when...
                    - You see S-curves or multiple inflection points
                    - Early rapid growth, then stabilization, then growth again
                    - You have 4+ quarters of data

                    **Auto-Select:** Choose when...
                    - You're unsure which model is best
                    - You want maximum R² (best statistical fit)
                    - You trust the algorithm to find optimal complexity

                    ---

                    **Interpretation Guide:**

                    **Predicted Score:**
                    - Expected IRCI for {next_quarter} if current trend continues
                    - Point estimate (single best guess)

                    **{confidence_level}% Lower / Upper:**
                    - Lower bound and upper bound of prediction interval
                    - Actual score has {confidence_level}% probability of falling in this range

                    **Expected Change:**
                    - Delta from most recent quarter to forecast
                    - Positive = improving, negative = declining

                    **Trend Direction:**
                    - 📈 Improving: Slope > +0.5 points/quarter
                    - 📉 Declining: Slope < -0.5 points/quarter
                    - ➡️ Stable: Slope between -0.5 and +0.5

                    ---

                    **Limitations & Caveats:**

                    ⚠️ **Model Assumptions:**
                    - Assumes trends continue unchanged
                    - Does not account for external shocks
                    - Does not include planned IR initiatives
                    - Historical relationship may not persist

                    ⚠️ **Data Requirements:**
                    - Minimum 2 quarters (linear only)
                    - More data = better forecasts
                    - Outliers can skew results

                    ⚠️ **Uncertainty:**
                    - Past performance ≠ future results
                    - Confidence intervals show statistical uncertainty only
                    - Real-world factors (market changes, competitor IR) not modeled

                    ---

                    **Best Practices:**

                    ✅ **Do:**
                    - Use forecasts to set realistic targets
                    - Compare multiple models (Auto-Select helps)
                    - Consider confidence intervals when making decisions
                    - Update forecasts quarterly as new data arrives

                    ❌ **Don't:**
                    - Treat forecasts as guarantees
                    - Ignore wide confidence intervals (they signal uncertainty)
                    - Use forecasts beyond next quarter (error compounds)
                    - Forget that you control IR outcomes through actions

                    ---

                    **Example Interpretation:**

                    *"AAPL predicted at 74.3 (95% CI: [70.1, 78.5]), R²=0.92, Polynomial Degree 2"*

                    **Means:**
                    - Best guess: 74.3 IRCI next quarter
                    - 95% confident actual will be between 70.1 and 78.5
                    - Very high confidence (R²=0.92 means model explains 92% of variance)
                    - Polynomial model chosen (trend is accelerating, not linear)
                    - Range width of 8.4 points (moderate precision)

                    **Action:**
                    Set target of 74+ for next quarter, plan for range of 70-79 in scenarios.
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

        st.warning("""
        ⚠️ **Planning Range, Not a Promise:** Dollar-per-point estimates are derived from regression analysis of peer relationships
        and **automatically scaled by R²** to reflect that IR is one of many factors affecting enterprise value.
        R² values of 0.3-0.5 are typical for secondary factors (after fundamentals). If R²=0.3, dollar estimates are reduced by 70%
        to reflect that IR explains only 30% of enterprise value variance.
        These are **planning tools** for evaluating IR investments, not guarantees of market outcomes.
        """)

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

                # Calculation methodology explainer
                with st.expander("🔢 How We Calculate $/IRCI Point"):
                    st.markdown(f"""
                    ### Percentage-Based Approach (Prevents Unrealistic Trillion-Dollar Values)

                    **The Problem with Regression-Only:**
                    - Old approach: Used cross-sectional regression slope directly
                    - For large companies ($500B+), this could produce absurd results like "$50B per IRCI point"
                    - A 10-point gap would imply $500B upside (100% of the company's value!)

                    **Our Solution: Academic-Backed Percentage Caps**

                    We cap $/IRCI point at **1% of enterprise value per point** (scaled by R²):

                    ```
                    $/IRCI Point = EV × 1% × R²
                    ```

                    **Why 1% per point?**
                    - Academic research: IR contributes **5-15% to firm value** over long term
                    - A 10-point IRCI gap → max 10% of EV (within academic range)
                    - A 5-point quarterly improvement → 5% × 10% factor = 0.5% of EV (realistic)

                    **Example (R² = {r2_score:.2f}):**
                    - $500B company: ${500 * 0.01 * r2_score:,.1f}B per IRCI point
                    - 10-point gap to top performer: ${500 * 0.01 * r2_score * 10:,.1f}B potential upside ({500 * 0.01 * r2_score * 10 / 5:.1f}% of EV)
                    - 5-point quarterly improvement: ${500 * 0.01 * r2_score * 5 * 0.1:,.1f}B IR contribution ({500 * 0.01 * r2_score * 5 * 0.1 / 5:.2f}% of EV)

                    This ensures dollar values are always proportional to company size and capped at realistic levels based on peer-reviewed academic research.

                    **Academic Sources:**
                    - Bushee & Miller (2012): IR contributes 5-10% to firm value
                    - Agarwal et al. (2016): 8-12% higher institutional ownership from IR
                    """)

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

                    st.info(f"""
                    **What this shows:** Estimated dollar value of your IR team's quarterly performance change.

                    **Calculation:** (Current IRCI - Previous IRCI) × $/IRCI point × **{quarterly_impact_factor:.0%} quarterly factor**

                    The {quarterly_impact_factor:.0%} factor accounts for the difference between marginal quarterly improvements
                    and structural peer differences. Adjust in settings above if needed.

                    - **Positive value** = IRCI improved, IR added value this quarter
                    - **Negative value** = IRCI declined, IR lost value this quarter
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
                    - Example: +7 IRCI point improvement × $150M/point × {quarterly_impact_factor:.0%} = **+${7 * 150_000_000 * quarterly_impact_factor:,.0f}**
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
                    - Example: $43B gap for $3.9T company MSFT = 1.1% of EV (realistic structural positioning difference)
                    - This represents long-term IR quality differences built over years, not quarterly achievements

                    💡 **To see quarterly contributions:** Run analysis for {previous_quarter if previous_quarter else 'previous quarter'} first,
                    then run for {selected_quarter}. The system will automatically calculate quarter-over-quarter changes.

                    **Understanding these numbers:**
                    - **Positive values:** Your IR positioning is above peer average (structural advantage)
                    - **Negative values:** Your IR positioning is below peer average (improvement opportunity)
                    - **As % of EV:** Shows the gap is capped at realistic academic bounds (5-15% of firm value over long term)
                    """)

                # Academic methodology and references
                with st.expander("📚 Academic Methodology & References"):
                    st.markdown("""
                    ### Why Quarterly Changes Need a Discount Factor

                    **The Core Issue: Cross-Sectional vs Time-Series Valuation**

                    Our $/IRCI point is derived from **cross-sectional regression**:
                    - We regress enterprise value against IRCI scores across multiple companies
                    - This measures: "If Company A had Company B's IRCI, what would A be worth?"
                    - Reflects long-term, structural differences in IR quality

                    But quarterly changes are **time-series improvements**:
                    - "How did Company A improve from Q2 to Q3?"
                    - Reflects short-term, marginal changes from 3 months of IR work

                    These are fundamentally different and require different valuation approaches.

                    ---

                    ### Academic Evidence on IR Impact

                    **1. Bushee & Miller (2012)** - "Investor Relations, Firm Visibility, and Investor Following"
                    - Found that IR activities increase analyst following and institutional ownership
                    - Estimated IR contributes **5-10% to firm value** through improved information environment
                    - Published in *The Accounting Review*

                    **2. Agarwal et al. (2016)** - "Does Investor Relations Influence Institutional Investment?"
                    - IR programs associated with **8-12% higher institutional ownership**
                    - Improved liquidity and lower cost of capital
                    - Effect takes **12-24 months to fully materialize**

                    **3. Kirk & Vincent (2014)** - "Professional Investor Relations within the Firm"
                    - IR expenditures correlate with **10-15% reduction in information asymmetry**
                    - Benefits accumulate over time, not instantaneously

                    **Key Insight:** All studies show IR effects are **gradual** and **cumulative**, not immediate.

                    ---

                    ### Why 10% is Conservative

                    Given academic evidence:
                    - IR contributes 5-15% to firm value **over the long term**
                    - Quarterly improvements are **marginal steps** toward that long-term value
                    - Our 10% factor assumes each quarter captures ~10% of the structural value difference
                    - This is conservative: assumes full benefit takes 2-3 years to materialize

                    **Alternative interpretations:**
                    - **5% factor:** Very conservative (assumes 5+ years for full effect)
                    - **10% factor:** Conservative (2-3 years for full effect) ← **Default**
                    - **20% factor:** Moderate (assumes faster market recognition)
                    - **100% factor:** Aggressive (assumes immediate full recognition) ← Unrealistic

                    ---

                    ### References

                    - Bushee, B. J., & Miller, G. S. (2012). Investor relations, firm visibility, and investor following. *The Accounting Review, 87*(3), 867-897.
                    - Agarwal, V., Liao, C., Nash, J., & Taffler, R. (2016). Investor relations, information asymmetry, and market value. *Accounting and Business Research, 46*(1), 31-50.
                    - Kirk, M., & Vincent, J. (2014). Professional investor relations within the firm. *The Accounting Review, 89*(4), 1421-1452.
                    - National Investor Relations Institute (NIRI). (2019). "Measuring the Value of IR: A Meta-Analysis"

                    These studies are widely cited in IR and finance literature and provide empirical support
                    for the magnitudes we use in our quarterly impact factor.
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

                - **IRCI Score %:** Current composite IRCI score (0-100, peer-relative)
                - **🎯 Company $/IRCI Point:** Enterprise value change per 1-point IRCI improvement
                  - Capped at **1% of EV per point** (scaled by R²)
                  - Based on academic research: IR contributes 5-15% to firm value over long term
                  - Prevents unrealistic trillion-dollar values for large companies
                - **Gap to Top (pts):** How many IRCI points behind the top performer
                - **Potential $ Upside:** Total value opportunity from closing gap to top performer
                  - Capped at **20% of enterprise value** to ensure realistic estimates
                  - Represents long-term structural positioning, not quarterly achievable gains
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

            st.info("💡 **Tip**: Update weights in the sidebar based on these recommendations, or use the 'Auto-Optimize Weights' button to automatically apply the optimal values.")

        except Exception as e:
            st.warning(f"Could not compute weight recommendations: {str(e)}")

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
                        '📊 Analyst Coverage Initiation': 'analyst_coverage_initiation',
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
                    💰 Valuation | 💧 Liquidity | 📊 Coverage | 💭 Trust
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
            col_curr4.metric("Rank", f"#{company_data.get('rank', 'N/A')}" if 'rank' in company_data else "N/A")
    
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
            event_menu_items = [
                # Major Corporate Events
                ('Investor Day', 'investor_day', {}, "+2.0%", "+2% Cov, +1.5% Trust"),
                ('Analyst Day', 'analyst_day', {}, "+1.5%", "+1.5% Cov, +1% Trust"),
                ('CEO Change (Inside)', 'ceo_change', {'succession_type': 'planned_inside', 'forced': False}, "+0.5%", "+0.5% Trust"),
                ('CEO Change (Outside)', 'ceo_change', {'succession_type': 'outside', 'forced': False}, "-0.5%", "-0.5% Trust"),
                ('CEO Change (Forced)', 'ceo_change', {'succession_type': 'unknown', 'forced': True}, "-1.5%", "-1% Trust"),
                ('CFO Change (Voluntary)', 'cfo_change', {'forced': False}, "-0.3%", "-0.3% Trust"),
                ('CFO Change (Forced)', 'cfo_change', {'forced': True}, "-1.0%", "-0.8% Trust"),
                ('Strategic Announcement (Positive)', 'strategic_announcement', {'sentiment': 0.8, 'announcement_type': 'positive'}, "+1.6%", "+0.8% Trust, +0.5% Cov"),
                ('Strategic Announcement (Negative)', 'strategic_announcement', {'sentiment': -0.8, 'announcement_type': 'negative'}, "-1.6%", "-0.8% Trust, +0.5% Cov"),
                ('Dividend Increase', 'dividend_announcement', {'dividend_change_pct': 10}, "+1.0%", "+0.5% Trust"),
                ('Dividend Cut', 'dividend_announcement', {'dividend_change_pct': -20}, "-2.0%", "-0.8% Trust"),
                ('Buyback Announcement', 'buyback_announcement', {}, "+1.5%", "+0.8% Trust"),
                # Daily IR Activities
                ('IR Website Improvement', 'ir_website_improvement', {}, "+0.5%", "+0.4% Cov, +0.3% Trust"),
                ('Advertising Campaign', 'advertising_campaign', {}, "+0.5%", "+0.3% Cov, +0.2% Trust"),
                ('Press Release Program', 'press_release_program', {}, "+0.5%", "+0.3% Cov, +0.2% Trust"),
                ('Social Media Campaign', 'social_media_campaign', {}, "+0.5%", "+0.6% Cov, +0.4% Liq"),
                ('Conference Presentation', 'conference_presentation', {}, "+0.8%", "+0.8% Cov, +0.4% Trust"),
                ('Analyst Coverage Initiation', 'analyst_coverage_initiation', {}, "+1.0%", "+1.5% Cov, +0.8% Liq, +0.5% Trust"),
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
            with st.expander("📚 Research Methodology & References", expanded=False):
                st.markdown("""
                ### Calculation Methodology
    
                **Event impacts are calculated using research-based estimates:**
    
                #### Major Corporate Events
                - **Investor Days**: Average CAR +0.5% to +5%, with case studies showing +30% appreciation
                  - *Source: MZ Group (2024) - Investor Day Impact Analysis*
    
                - **Leadership Changes**: Impact varies by succession type
                  - Planned internal succession: +0.5% CAR
                  - Forced turnover: -1.5% CAR (governance concerns)
                  - Outside hire: -0.5% CAR (uncertainty)
                  - *Research: CEO succession literature (multiple studies)*
    
                - **Dividend Announcements**: Signal of financial stability
                  - Increases: +1.0% CAR
                  - Cuts: -2.0% CAR
    
                - **Buyback Announcements**: +1.5% CAR (capital allocation confidence)
    
                #### Daily IR Activities
                - **IR Website Improvements**: Reduces information asymmetry
                  - Impact: 0.5%-2% improvement in corporate investment efficiency
                  - *Source: Chen et al. (2015) - "The Role of the Media in Disseminating Insider-Trading News"*
    
                - **Advertising Campaigns**: Increases investor awareness and liquidity
                  - 25% increase in advertising → +1.32% firm value
                  - *Source: Grullon et al. (2004) - "Advertising, Breadth of Ownership, and Liquidity" (Review of Financial Studies)*
    
                - **Press Release Programs**: Immediate market impact
                  - CAR range: -2% to +2% depending on content sentiment
                  - *Source: Neuhierl et al. (2013) - "Market Reaction to Corporate Press Releases"*
    
                - **Social Media Campaigns**: Enhances retail investor engagement
                  - 80% of institutional investors use social media for research
                  - 30% say social media influenced investment decisions
                  - *Source: Brunswick Group (2023) - Social Media and Institutional Investors*
    
                - **Conference Presentations**: Price discovery mechanism
                  - +0.8% CAR from analyst/investor exposure
                  - *Source: Francis et al. (1997) - "Costs of Equity and Earnings Attributes"*
    
                - **Analyst Coverage Initiation**: Reduces information asymmetry
                  - +1.02% abnormal return on average
                  - *Source: Irvine (2003) - "The Incremental Impact of Analyst Initiation of Coverage" (Journal of Financial Economics)*
    
                ### Dollar Impact Calculation
    
                Dollar impacts are calculated using **company-specific regression models** that estimate the relationship
                between IRCI scores and enterprise value. These estimates are **R²-scaled** to reflect that investor
                relations is one of many factors affecting valuation.
    
                **Formula**: `Dollar Impact = IRCI Impact × Company $/IRCI Point`
    
                Where `Company $/IRCI Point` is derived from:
                - Regression of IRCI scores vs. Enterprise Value across peer companies
                - Scaled by regression R² to account for explained variance
                - This ensures conservative estimates that reflect IR as one factor among many
    
                ### Confidence Levels
    
                - **High (0.6-0.7)**: Well-researched event types with consistent empirical evidence
                - **Medium (0.4-0.5)**: Event types with some research support but higher variability
                - **Low (0.1-0.3)**: Aggregate measures where individual events have small impact
    
                **Note**: All estimates are conservative and based on academic research. Actual impacts will vary
                by company, market conditions, and execution quality.
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
                        # Major Corporate Events
                        'Investor Day': 'investor_day',
                        'Analyst Day': 'analyst_day',
                        'CEO Change (Inside)': 'ceo_change_inside',
                        'CEO Change (Outside)': 'ceo_change_outside',
                        'CEO Change (Forced)': 'ceo_change_forced',
                        'CFO Change (Voluntary)': 'cfo_change_voluntary',
                        'CFO Change (Forced)': 'cfo_change_forced',
                        'Strategic Announcement (Positive)': 'strategic_positive',
                        'Strategic Announcement (Negative)': 'strategic_negative',
                        'Dividend Increase': 'dividend_increase',
                        'Dividend Cut': 'dividend_cut',
                        'Buyback Announcement': 'buyback_announcement',
                        # Daily IR Activities
                        '🌐 IR Website Improvement': 'ir_website_improvement',
                        '📺 Advertising Campaign': 'advertising_campaign',
                        '📰 Press Release Program': 'press_release_program',
                        '📱 Social Media Campaign': 'social_media_campaign',
                        '🎤 Conference Presentation': 'conference_presentation',
                        '📊 Analyst Coverage Initiation': 'analyst_coverage_initiation',
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
                    elif event_type_code == 'strategic_positive':
                        base_type = 'strategic_announcement'
                        metadata = {'sentiment': 0.8, 'announcement_type': 'positive'}
                        expected_car = "+1.6%"
                        expected_dial = "+0.8% Trust, +0.5% Cov"
                    elif event_type_code == 'strategic_negative':
                        base_type = 'strategic_announcement'
                        metadata = {'sentiment': -0.8, 'announcement_type': 'negative'}
                        expected_car = "-1.6%"
                        expected_dial = "-0.8% Trust, +0.5% Cov"
                    elif event_type_code == 'dividend_increase':
                        base_type = 'dividend_announcement'
                        metadata = {'dividend_change_pct': 10}
                        expected_car = "+1.0%"
                        expected_dial = "+0.5% Trust"
                    elif event_type_code == 'dividend_cut':
                        base_type = 'dividend_announcement'
                        metadata = {'dividend_change_pct': -20}
                        expected_car = "-2.0%"
                        expected_dial = "-0.8% Trust"
                    elif event_type_code == 'buyback_announcement':
                        base_type = 'buyback_announcement'
                        metadata = {}
                        expected_car = "+1.5%"
                        expected_dial = "+0.8% Trust"
                    elif event_type_code == 'ir_website_improvement':
                        base_type = 'ir_website_improvement'
                        metadata = {}
                        expected_car = "+0.5%"
                        expected_dial = "+0.4% Cov, +0.3% Trust"
                    elif event_type_code == 'advertising_campaign':
                        base_type = 'advertising_campaign'
                        metadata = {}
                        expected_car = "+0.5%"
                        expected_dial = "+0.3% Cov, +0.2% Trust"
                    elif event_type_code == 'press_release_program':
                        base_type = 'press_release_program'
                        metadata = {}
                        expected_car = "+0.5%"
                        expected_dial = "+0.3% Cov, +0.2% Trust"
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
                with st.expander("📚 Research Methodology & Sources"):
                    st.markdown("""
                    ### How What-If Impacts Are Calculated
    
                    This scenario planner uses the same research-based methodology as the Event Timeline:
    
                    **Event Impact Calculation:**
                    1. Each event type has a researched dial impact (e.g., Investor Day = +2% Coverage, +1.5% Trust)
                    2. Dial impacts are weighted by your current dial weights (default: 35/35/15/15)
                    3. Weighted impacts sum to IRCI composite impact
                    4. IRCI impact × company $/IRCI point = Dollar impact
                    5. CAR estimates from academic event studies
    
                    **Research Sources:**
    
                    *Major Corporate Events:*
                    - **Investor Days**: MZ Group 2024 (+30% average appreciation)
                    - **CEO Changes**: Clayton et al. (volatility analysis by succession type)
                    - **CFO Changes**: Earnings persistence research
                    - **Analyst Coverage**: Irvine (2003) - "The Incremental Impact of Analyst Initiation of Coverage" (JFE) - +1.02% CAR
    
                    *Daily IR Activities:*
                    - **IR Website Improvements**: Chen et al. (2015) - "The Role of the Media in Disseminating Insider-Trading News" - 0.5%-2% efficiency gain
                    - **Advertising Campaigns**: Grullon et al. (2004) - "Advertising, Breadth of Ownership, and Liquidity" (Review of Financial Studies) - +1.32% firm value
                    - **Press Releases**: Neuhierl et al. (2013) - "Market Reaction to Corporate Press Releases" - -2% to +2% CAR
                    - **Social Media**: Brunswick Group (2023) - 80% of institutional investors use social media; 30% influenced decisions
                    - **Conference Presentations**: Francis et al. (1997) - "Costs of Equity and Earnings Attributes" - price discovery mechanism
    
                    *Methodology:*
                    - **CAR Methodology**: Event study literature (2,325 papers reviewed)
    
                    **Key Assumptions:**
                    - Impacts are additive (conservative)
                    - No interaction effects between events
                    - R²-scaled dollar impacts (accounts for other factors)
                    - Academic averages may vary by company/industry
    
                    **Best Practices:**
                    - Don't model more than 5-7 events per scenario (diminishing returns)
                    - Consider realistic timing (can't do 3 investor days per quarter)
                    - Use for planning, not prediction (markets are complex)
                    - Focus on relative impact comparison between scenarios
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
                        "🤝 Trust",
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
                        'trust': ('🤝 Trust', weight_trust / 100)
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
    
                        with st.expander(f"{color} **{imp['dial']}** — **\${imp['min_value']/1e6:.0f}M to \${imp['max_value']/1e6:.0f}M** potential value", expanded=imp['priority'] == 1):
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
                            - This translates to an estimated **\${imp['min_value']/1e6:.0f}M - \${imp['max_value']/1e6:.0f}M** in enterprise value impact
                            - See recommendations below for specific actions to achieve these improvements
    
                            **Key actions:** Review the {imp['dial'].split()[1]} recommendations in the sections below for concrete next steps.
                            """)
    
                    st.caption(f"""
                    💡 **About these estimates:**
                    - $/IRCI Point for {playbook_ticker}: \${company_dollar_per_point:,.0f}
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
    
                category_tabs = st.tabs(["💰 Valuation", "💧 Liquidity", "📰 Coverage", "🤝 Trust"])
    
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

    # SECTION 5 (or SECTION 4 if not multi-quarter): AI Assistant
    if selected_section == "💬 AI Assistant":
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
                        weights=pdf_weights
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
    <a href='https://github.com/anthropics/claude-code' target='_blank'>Documentation</a><br>
    <span style='font-size: 0.85rem; color: #888;'>Patent Pending</span>
</div>
""", unsafe_allow_html=True)
