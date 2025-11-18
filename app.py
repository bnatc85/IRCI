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

# Page config
st.set_page_config(
    page_title="IRCI Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stAlert {
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">IRCI Analysis Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">IRCI: Coverage, Trust, Liquidity & Valuation Analysis</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/1f77b4/ffffff?text=IRCI", use_container_width=True)
    st.markdown("### Analysis Configuration")

    # Company selection
    default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
    ticker_input = st.text_area(
        "Company Tickers (one per line or comma-separated)",
        value=",".join(default_tickers[:4]),
        help="Enter stock tickers like AAPL, MSFT, GOOGL"
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
    st.markdown("### Optional: News Data")
    uploaded_news = st.file_uploader(
        "Upload News CSV (optional)",
        type=["csv"],
        help="CSV with columns: date, ticker, headline"
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

# Main content area
if not run_analysis:
    # Welcome screen
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 📊 Coverage")
        st.markdown("SEC filing cadence & disclosure timeliness")

    with col2:
        st.markdown("### 💭 Trust")
        st.markdown("Sentiment & event stability analysis")

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
           - Media visibility (if news data provided)

        2. **Trust Dial** - How stable is the company?
           - Market sentiment from news headlines
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

        # Prepare news data
        news_df = None
        if uploaded_news is not None:
            news_df = pd.read_csv(uploaded_news)
            st.success(f"✓ Loaded {len(news_df)} news articles")

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
            # Ensure timezone-naive
            if hasattr(df_trust["quarter_end"], 'dt'):
                df_trust["quarter_end"] = pd.to_datetime(df_trust["quarter_end"]).dt.tz_localize(None)
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
            # Ensure timezone-naive
            if hasattr(df_val["quarter_end"], 'dt'):
                df_val["quarter_end"] = pd.to_datetime(df_val["quarter_end"]).dt.tz_localize(None)
        progress_bar.progress(50)

        # 3. Coverage
        status_text.text("Running Coverage analysis...")
        df_cov = coverage_snapshot(
            tickers,
            as_of=end_date
        )
        if not df_cov.empty:
            if "quarter_end" not in df_cov.columns:
                df_cov["quarter_end"] = quarter_end_dt
            # Ensure timezone-naive
            if hasattr(df_cov["quarter_end"], 'dt'):
                df_cov["quarter_end"] = pd.to_datetime(df_cov["quarter_end"]).dt.tz_localize(None)
        progress_bar.progress(70)

        # 4. Liquidity
        status_text.text("Running Liquidity analysis...")
        rows = []
        for sym in tickers:
            try:
                px = fetch_prices_fmp(sym, start_date, end_date, s.fmp_api_key)
                daily = daily_liquidity_bundle(sym, s, px, end_date)
                q = quarterly_liquidity(daily, freq="QE-DEC").reset_index()
                if "quarter_end" not in q.columns:
                    q = q.rename(columns={"Date": "quarter_end", "date": "quarter_end", "index": "quarter_end"})
                q["ticker"] = sym
                rows.append(q)
            except Exception as e:
                st.warning(f"⚠️ Liquidity data unavailable for {sym}: {str(e)}")
        df_liq = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        if not df_liq.empty:
            # Convert quarter_end to timezone-naive to match other dials
            if "quarter_end" in df_liq.columns:
                qe = pd.to_datetime(df_liq["quarter_end"])
                # Remove timezone if present
                if qe.dt.tz is not None:
                    df_liq["quarter_end"] = qe.dt.tz_localize(None)
                else:
                    df_liq["quarter_end"] = qe
            df_liq = add_liquidity_percentile(df_liq)
        progress_bar.progress(85)

        # 5. Composite
        status_text.text("Computing composite scores...")
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
    display_df = display_df.sort_values('rank_in_peer')
    display_df['rank'] = display_df['rank_in_peer'].astype(int)

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

    tab1, tab2, tab3 = st.tabs(["Composite Scores", "Dial Breakdown", "Detailed Metrics"])

    with tab1:
        # Bar chart of composite scores
        fig = px.bar(
            display_df,
            x='ticker',
            y='irci_composite_pct',
            title=f'IRCI Composite Scores - {selected_quarter}',
            labels={'irci_composite_pct': 'Composite Score (%)', 'ticker': 'Company'},
            color='irci_composite_pct',
            color_continuous_scale='RdYlGn',
            text='irci_composite_pct'
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(showlegend=False, height=400)
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
            name=selected_company
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            title=f'{selected_company} - Dial Breakdown',
            height=500
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
