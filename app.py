"""
IRCI Web Application
A user-friendly interface for running IRCI analysis on public companies.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
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
from irci.peers import find_peers_simple

# Page config
st.set_page_config(
    page_title="IRCI Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "IRCI Analysis Platform - Information Risk, Coverage, Trust, Liquidity & Valuation"
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

    # News file upload
    st.markdown("### News Data")
    st.info("📰 News articles are automatically fetched from FMP API for sentiment analysis")
    uploaded_news = st.file_uploader(
        "Or upload custom News CSV (optional override)",
        type=["csv"],
        help="CSV with columns: date, ticker, headline. If provided, this will override automatic fetching."
    )

    # Weights configuration
    with st.expander("⚙️ Advanced: Dial Weights"):
        st.markdown("Customize composite score weights:")
        weight_liquidity = st.slider("Liquidity", 0, 100, 35, 5)
        weight_valuation = st.slider("Valuation", 0, 100, 35, 5)
        weight_coverage = st.slider("Coverage", 0, 100, 15, 5)
        weight_trust = st.slider("Trust", 0, 100, 15, 5)

        total_weight = weight_liquidity + weight_valuation + weight_coverage + weight_trust
        if total_weight != 100:
            st.warning(f"⚠️ Weights sum to {total_weight}%. Will be normalized to 100%.")

    # Run button
    run_analysis = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    # Contact information
    st.markdown("""
    <div class="contact-info">
        <strong>Contact:</strong><br>
        Bonnie Rushing<br>
        <a href="mailto:brushing@uccs.edu">brushing@uccs.edu</a><br>
        <a href="https://www.thebonnierushing.com" target="_blank">www.thebonnierushing.com</a>
    </div>
    """, unsafe_allow_html=True)

# Main content area
if not run_analysis:
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
    st.info("👈 Configure your analysis in the sidebar and click **Run Analysis** to start")

    # Show example
    with st.expander("📖 How It Works"):
        st.markdown("""
        **IRCI** evaluates companies across four fundamental dimensions:

        1. **Coverage Dial** - How well does the company communicate?
           - 8-K filing frequency
           - 10-Q/10-K filing timeliness
           - Media visibility (automatically from FMP API)

        2. **Trust Dial** - How stable is the company?
           - Market sentiment from news headlines (automatically analyzed)
           - Event calmness (reactions to SEC filings)
           - Baseline volatility (Fama-French factor analysis)

        3. **Liquidity Dial** - How easily can you trade the stock?
           - Amihud illiquidity measure
           - Bid-ask spread estimates
           - Trading volume & turnover

        4. **Valuation Dial** - Is it fairly priced?
           - EV/EBITDA multiples
           - Peer comparison & ranking
           - Relative valuation gaps

        **Output:** A composite score (0-100%) ranking companies within your peer group.
        """)

else:
    # Run the analysis
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
            # Automatically fetch news for all tickers using API (FMP → Alpha Vantage fallback)
            status_text.text("Fetching news articles...")
            news_list = []
            q_start = pd.to_datetime(start_date, utc=True)
            q_end = pd.to_datetime(end_date, utc=True)
            news_source = None

            for ticker in tickers:
                try:
                    # Try FMP first
                    ticker_news = fmp_news_media_fetcher(ticker, q_start, q_end, s)
                    if not ticker_news.empty:
                        ticker_news['ticker'] = ticker
                        news_list.append(ticker_news)
                        news_source = "FMP API"
                except Exception:
                    pass  # Silently try fallback

                # If FMP failed or returned no results, try Alpha Vantage
                if not news_list or news_list[-1].empty if news_list else True:
                    try:
                        ticker_news = alpha_vantage_news_fetcher(ticker, q_start, q_end, s)
                        if not ticker_news.empty:
                            if ticker in [n.get('ticker', '') for n in news_list]:
                                # Remove empty FMP result
                                news_list = [n for n in news_list if n.get('ticker', '') != ticker]
                            ticker_news['ticker'] = ticker
                            news_list.append(ticker_news)
                            news_source = "Alpha Vantage API (free tier)"
                    except Exception as e:
                        pass  # Silent fallback failure

            if news_list:
                news_df = pd.concat(news_list, ignore_index=True)
                st.success(f"✓ Fetched {len(news_df)} news articles from {news_source} for {len(news_list)} ticker(s)")
            else:
                st.warning("⚠️ News API access unavailable (FMP requires paid plan, Alpha Vantage rate limited). Analysis will continue without news data.")

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
        st.session_state['run_time'] = datetime.now()

    except Exception as e:
        st.error(f"❌ Error running analysis: {str(e)}")
        st.exception(e)
        st.stop()

# Display results (if available)
if 'df_composite' in st.session_state:
    st.markdown("---")
    st.markdown("## 📊 Analysis Results")

    df_composite = st.session_state['df_composite']
    df_trust = st.session_state['df_trust']
    df_val = st.session_state['df_val']
    df_cov = st.session_state['df_cov']
    df_liq = st.session_state['df_liq']

    # Top metrics
    st.markdown(f"### Quarter: {selected_quarter} | Companies: {len(df_composite)} | Run: {st.session_state['run_time'].strftime('%Y-%m-%d %H:%M')}")

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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Composite Scores", "Dial Breakdown", "Detailed Metrics", "📊 Insights", "📅 Timeline"])

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

        try:
            dollar_value_df = compute_dollar_value_per_irci_point(df_composite, df_val)

            # Display key metric
            group_dollars_per_point = dollar_value_df['peer_group_$/irci_pt'].iloc[0]
            avg_company_dollars_per_point = dollar_value_df['company_$/irci_pt'].mean()
            r2_score = dollar_value_df['regression_r2'].iloc[0]

            col1, col2, col3, col4 = st.columns(4)
            col1.metric(
                "Peer Group $/IRCI Point",
                f"${group_dollars_per_point:,.0f}",
                help="Dollar value change per 1-point IRCI improvement across peer group (range-based)"
            )
            col2.metric(
                "Avg Company $/IRCI Point",
                f"${avg_company_dollars_per_point:,.0f}",
                help="Average company-specific dollar value per IRCI point (regression-based)"
            )
            col3.metric(
                "Regression R²",
                f"{r2_score:.2f}",
                help="How well EV correlates with IRCI scores (0-1 scale)"
            )
            col4.metric(
                "Max IRCI Gap",
                f"{dollar_value_df['irci_gap_to_top'].max():.1f} pts",
                help="Largest gap between a peer and the top performer"
            )

            # Per-Ticker $/IRCI Point Table (Most Important)
            st.markdown("**Per-Ticker Dollar Value per IRCI Point:**")
            st.dataframe(
                dollar_value_df[['ticker', 'irci_composite_pct', 'company_$/irci_pt', 'peer_group_$/irci_pt', 'irci_gap_to_top', 'market_cap_gap_regression']].rename(columns={
                    'ticker': 'Ticker',
                    'irci_composite_pct': 'IRCI Score %',
                    'company_$/irci_pt': '🎯 Company $/IRCI Point',
                    'peer_group_$/irci_pt': 'Peer Group $/IRCI Point',
                    'irci_gap_to_top': 'Gap to Top (pts)',
                    'market_cap_gap_regression': 'Potential $ Upside'
                }).style.format({
                    'IRCI Score %': '{:.1f}%',
                    '🎯 Company $/IRCI Point': '${:,.0f}',
                    'Peer Group $/IRCI Point': '${:,.0f}',
                    'Gap to Top (pts)': '{:.1f}',
                    'Potential $ Upside': '${:,.0f}'
                }),
                use_container_width=True,
                hide_index=True
            )
            st.caption("💡 **Company $/IRCI Point** shows how much each ticker's enterprise value could change per 1-point IRCI improvement based on peer group regression")

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
                sec_filings_df=sec_filings_df
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
            else:
                st.info("No events found for this period. Try uploading news data or check the date range.")

            # Detailed event timeline
            st.markdown("---")
            st.markdown("**🔍 Detailed Event Timeline**")

            if not timeline_df.empty:
                # Create a simpler display without complex styling that causes issues
                display_timeline = timeline_df[['date', 'event_type', 'description', 'irci_impact', 'dollar_impact', 'impact_confidence', 'affected_dials']].copy()

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
                    'impact_confidence': 'Confidence',
                    'affected_dials': 'Affected Dials'
                })

                # Format the dataframe
                st.dataframe(
                    display_timeline.style.format({
                        'IRCI Impact': '{:+.2f}',
                        '$ Impact': '${:+,.0f}',
                        'Confidence': '{:.0%}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                st.caption("💡 🟢 Positive news | 🔴 Negative news | 🔵 SEC filings | 📰 Neutral news | 💰 Valuation | 💧 Liquidity | 📊 Coverage | 💭 Trust")

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

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    IRCI Analysis Platform v0.1.0 | Powered by Streamlit |
    <a href='https://github.com/anthropics/claude-code' target='_blank'>Documentation</a>
</div>
""", unsafe_allow_html=True)
