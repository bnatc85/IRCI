# irci/report_generator.py
"""
PDF Report Generator for IRCI Analysis
Creates comprehensive reports with all analysis results
"""
from fpdf import FPDF
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import io
import re


def strip_emojis(text: str) -> str:
    """Remove emojis and other non-ASCII characters from text for PDF compatibility"""
    # Remove emojis and other Unicode characters
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    # Also remove other common Unicode characters that might cause issues
    text = text.replace('✅', '[OK]')
    text = text.replace('⚠️', '[WARNING]')
    text = text.replace('❌', '[X]')
    text = text.replace('✓', '[CHECK]')
    text = text.replace('→', '->')
    text = text.replace('•', '*')
    return text.strip()


class IRCIReport(FPDF):
    """Custom PDF class for IRCI reports"""

    def __init__(self, ticker: str, quarter: str):
        super().__init__()
        self.ticker = ticker
        self.quarter = quarter
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Page header"""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, f'IRCI Analysis Report - {self.ticker}', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Quarter: {self.quarter} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        """Page footer"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title: str):
        """Add a chapter title"""
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(0, 212, 255)
        self.cell(0, 10, strip_emojis(title), 0, 1, 'L', 0)
        self.ln(2)

    def section_title(self, title: str):
        """Add a section title"""
        self.set_font('Arial', 'B', 11)
        self.cell(0, 8, strip_emojis(title), 0, 1, 'L')
        self.ln(1)

    def body_text(self, text: str):
        """Add body text"""
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, strip_emojis(text))
        self.ln(2)


def generate_pdf_report(
    ticker: str,
    quarter: str,
    df_composite: pd.DataFrame,
    df_valuation: pd.DataFrame,
    df_liquidity: pd.DataFrame,
    df_coverage: pd.DataFrame,
    df_trust: pd.DataFrame,
    playbook: Dict,
    timeline_df: Optional[pd.DataFrame] = None
) -> bytes:
    """
    Generate a comprehensive PDF report of IRCI analysis

    Args:
        ticker: Company ticker symbol
        quarter: Quarter being analyzed
        df_composite: Composite scores dataframe
        df_valuation: Valuation dial dataframe
        df_liquidity: Liquidity dial dataframe
        df_coverage: Coverage dial dataframe
        df_trust: Trust dial dataframe
        playbook: Playbook recommendations dictionary
        timeline_df: Optional timeline events dataframe

    Returns:
        PDF file as bytes
    """
    pdf = IRCIReport(ticker, quarter)
    pdf.add_page()

    # Get company data
    company_data = df_composite[df_composite['ticker'] == ticker].iloc[0]

    # 1. EXECUTIVE SUMMARY
    pdf.chapter_title('1. Executive Summary')

    irci_score = company_data.get('irci_composite_pct', 0)
    peer_avg = df_composite['irci_composite_pct'].mean()
    peer_rank = int(df_composite['irci_composite_pct'].rank(ascending=False)[
        df_composite['ticker'] == ticker
    ].iloc[0])
    total_peers = len(df_composite)

    pdf.section_title('Overall Performance')
    pdf.body_text(
        f"IRCI Composite Score: {irci_score:.1f}%\n"
        f"Peer Group Rank: #{peer_rank} out of {total_peers} companies\n"
        f"Peer Group Average: {peer_avg:.1f}%\n"
        f"Performance vs Peers: {irci_score - peer_avg:+.1f} percentage points"
    )

    # Dial scores summary
    pdf.section_title('Dial Performance')
    valuation_score = company_data.get('valuation_pct', 0)
    liquidity_score = company_data.get('liquidity_pct', 0)
    coverage_score = company_data.get('coverage_pct', 0)
    trust_score = company_data.get('sentiment_pct', 0)

    pdf.body_text(
        f"Valuation:  {valuation_score:.1f}% ({classify_score(valuation_score)})\n"
        f"Liquidity:  {liquidity_score:.1f}% ({classify_score(liquidity_score)})\n"
        f"Coverage:   {coverage_score:.1f}% ({classify_score(coverage_score)})\n"
        f"Trust:      {trust_score:.1f}% ({classify_score(trust_score)})"
    )

    # Playbook summary
    pdf.section_title('Key Recommendations')
    pdf.body_text(playbook['summary'])

    high_priority_count = playbook['priority_counts']['high']
    if high_priority_count > 0:
        pdf.body_text(f"\n{high_priority_count} high-priority action items identified (see Playbook section)")

    pdf.add_page()

    # 2. DETAILED DIAL ANALYSIS
    pdf.chapter_title('2. Detailed Dial Analysis')

    # Valuation
    pdf.section_title('Valuation Dial ({:.1f}%)'.format(valuation_score))
    val_data = df_valuation[df_valuation['ticker'] == ticker].iloc[0]

    ev_ebitda = val_data['ev_to_ebitda'] if 'ev_to_ebitda' in val_data.index and pd.notna(val_data['ev_to_ebitda']) else None
    enterprise_value = val_data['enterprise_value'] if 'enterprise_value' in val_data.index and pd.notna(val_data['enterprise_value']) else None
    ttm_ebitda = val_data['ttm_ebitda'] if 'ttm_ebitda' in val_data.index and pd.notna(val_data['ttm_ebitda']) else None

    pdf.body_text(
        f"Valuation Percentile: {valuation_score:.1f}% (within peer group)\n"
        f"EV/EBITDA Ratio: {ev_ebitda:.2f}" if ev_ebitda else "EV/EBITDA Ratio: N/A"
    )
    if enterprise_value:
        pdf.body_text(f"Enterprise Value: ${enterprise_value/1e9:.2f}B")
    if ttm_ebitda:
        pdf.body_text(f"TTM EBITDA: ${ttm_ebitda/1e9:.2f}B")

    # Liquidity
    pdf.section_title('Liquidity Dial ({:.1f}%)'.format(liquidity_score))
    liq_data = df_liquidity[df_liquidity['ticker'] == ticker].iloc[0]

    avg_volume = liq_data['avg_volume'] if 'avg_volume' in liq_data.index and pd.notna(liq_data['avg_volume']) else None
    avg_spread = liq_data['avg_spread_pct'] if 'avg_spread_pct' in liq_data.index and pd.notna(liq_data['avg_spread_pct']) else None
    avg_volatility = liq_data['avg_volatility'] if 'avg_volatility' in liq_data.index and pd.notna(liq_data['avg_volatility']) else None

    pdf.body_text(
        f"Liquidity Percentile: {liquidity_score:.1f}% (within peer group)"
    )
    if avg_volume:
        pdf.body_text(f"Average Daily Volume: {avg_volume:,.0f} shares")
    if avg_spread:
        pdf.body_text(f"Average Bid-Ask Spread: {avg_spread:.3f}%")
    if avg_volatility:
        pdf.body_text(f"Average Volatility: {avg_volatility:.2f}%")

    # Coverage
    pdf.section_title('Coverage Dial ({:.1f}%)'.format(coverage_score))
    cov_data = df_coverage[df_coverage['ticker'] == ticker].iloc[0]

    total_weighted = cov_data['total_weighted_articles'] if 'total_weighted_articles' in cov_data.index and pd.notna(cov_data['total_weighted_articles']) else None
    total_filings = cov_data['total_filings'] if 'total_filings' in cov_data.index and pd.notna(cov_data['total_filings']) else None
    media_score = cov_data['media_score'] if 'media_score' in cov_data.index and pd.notna(cov_data['media_score']) else None

    pdf.body_text(
        f"Coverage Percentile: {coverage_score:.1f}% (within peer group)"
    )
    if total_weighted:
        pdf.body_text(f"Weighted Media Coverage: {total_weighted:.1f} articles")
    if total_filings:
        pdf.body_text(f"SEC Filings This Quarter: {int(total_filings)}")
    if media_score:
        pdf.body_text(f"Media Score: {media_score:.1f}")

    # Trust
    pdf.section_title('Trust Dial ({:.1f}%)'.format(trust_score))
    trust_data = df_trust[df_trust['ticker'] == ticker].iloc[0]

    media_tone = trust_data['media_tone'] if 'media_tone' in trust_data.index and pd.notna(trust_data['media_tone']) else None
    sentiment_label = "N/A"
    if media_tone is not None:
        if media_tone > 60:
            sentiment_label = "Positive"
        elif media_tone > 40:
            sentiment_label = "Neutral"
        else:
            sentiment_label = "Negative"

    pdf.body_text(
        f"Trust Percentile: {trust_score:.1f}% (within peer group)"
    )
    if media_tone is not None:
        pdf.body_text(f"Media Tone Score: {media_tone:.1f}%\nSentiment: {sentiment_label}")

    pdf.add_page()

    # 3. PEER COMPARISON
    pdf.chapter_title('3. Peer Group Comparison')

    pdf.section_title('IRCI Composite Scores')

    # Sort peers by IRCI score
    peer_comparison = df_composite[['ticker', 'irci_composite_pct']].sort_values(
        'irci_composite_pct', ascending=False
    )

    for idx, row in peer_comparison.iterrows():
        peer_ticker = row['ticker']
        peer_score = row['irci_composite_pct']

        if peer_ticker == ticker:
            pdf.set_font('Arial', 'B', 10)
            marker = '>>> '
        else:
            pdf.set_font('Arial', '', 10)
            marker = '    '

        pdf.cell(0, 5, f"{marker}{peer_ticker}: {peer_score:.1f}%", 0, 1)

    pdf.ln(5)

    # Dial comparison
    pdf.section_title('Dial Score Comparison')

    avg_valuation = df_composite['valuation_pct'].mean()
    avg_liquidity = df_composite['liquidity_pct'].mean()
    avg_coverage = df_composite['coverage_pct'].mean()
    avg_trust = df_composite['sentiment_pct'].mean()

    pdf.body_text(
        f"Valuation:  {ticker} {valuation_score:.1f}% vs Peer Avg {avg_valuation:.1f}% ({valuation_score - avg_valuation:+.1f})\n"
        f"Liquidity:  {ticker} {liquidity_score:.1f}% vs Peer Avg {avg_liquidity:.1f}% ({liquidity_score - avg_liquidity:+.1f})\n"
        f"Coverage:   {ticker} {coverage_score:.1f}% vs Peer Avg {avg_coverage:.1f}% ({coverage_score - avg_coverage:+.1f})\n"
        f"Trust:      {ticker} {trust_score:.1f}% vs Peer Avg {avg_trust:.1f}% ({trust_score - avg_trust:+.1f})"
    )

    pdf.add_page()

    # 4. IR PLAYBOOK
    pdf.chapter_title('4. IR Action Playbook')

    pdf.body_text(playbook['summary'])
    pdf.ln(3)

    # High priority recommendations
    high_priority = [r for r in playbook['recommendations'] if r['priority'] == 'high']
    if high_priority:
        pdf.section_title('High Priority Actions')
        for i, rec in enumerate(high_priority, 1):
            pdf.set_font('Arial', 'B', 10)
            # Use multi_cell for wrapping long titles
            pdf.multi_cell(0, 6, strip_emojis(f"{i}. {rec['action']} ({rec['category']})"))
            pdf.set_font('Arial', '', 9)
            pdf.multi_cell(0, 5, strip_emojis(rec['description']))
            if rec.get('quick_win'):
                pdf.set_font('Arial', 'I', 8)
                pdf.cell(0, 4, '   Quick Win', 0, 1)
            pdf.ln(2)

    # Medium priority recommendations
    medium_priority = [r for r in playbook['recommendations'] if r['priority'] == 'medium']
    if medium_priority:
        pdf.add_page()
        pdf.section_title('Medium Priority Actions')
        for i, rec in enumerate(medium_priority, 1):
            pdf.set_font('Arial', 'B', 10)
            # Use multi_cell for wrapping long titles
            pdf.multi_cell(0, 6, strip_emojis(f"{i}. {rec['action']} ({rec['category']})"))
            pdf.set_font('Arial', '', 9)
            pdf.multi_cell(0, 5, strip_emojis(rec['description']))
            if rec.get('quick_win'):
                pdf.set_font('Arial', 'I', 8)
                pdf.cell(0, 4, '   Quick Win', 0, 1)
            pdf.ln(2)

    # Quick Wins summary
    if playbook['quick_wins']:
        pdf.add_page()
        pdf.section_title('Quick Wins Summary')
        pdf.body_text(f"Identified {len(playbook['quick_wins'])} quick win opportunities:")
        pdf.ln(2)

        for i, rec in enumerate(playbook['quick_wins'][:10], 1):  # Top 10 quick wins
            pdf.set_font('Arial', 'B', 9)
            # Use multi_cell for wrapping
            pdf.multi_cell(0, 5, strip_emojis(f"{i}. {rec['action']}"))

    # 5. TIMELINE HIGHLIGHTS
    if timeline_df is not None and not timeline_df.empty:
        pdf.add_page()
        pdf.chapter_title('5. Recent Events & Timeline')

        # Show most impactful events
        timeline_sorted = timeline_df.sort_values('irci_impact', ascending=False, key=abs)

        pdf.section_title('Most Impactful Events')

        for idx, event in timeline_sorted.head(10).iterrows():
            event_type = event.get('event_type', 'unknown')
            date = event.get('date', '')
            description = event.get('description', 'No description')[:200]  # Increased from 100 to 200
            irci_impact = event.get('irci_impact', 0)

            pdf.set_font('Arial', 'B', 9)
            # Use multi_cell for date/type to handle wrapping
            pdf.multi_cell(0, 5, strip_emojis(f"{date} - {event_type.upper()}"))
            pdf.set_font('Arial', '', 9)
            pdf.multi_cell(0, 4, strip_emojis(description))
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 4, f"IRCI Impact: {irci_impact:+.3f} points", 0, 1)
            pdf.ln(2)

    # 6. METHODOLOGY
    pdf.add_page()
    pdf.chapter_title('6. Methodology & Calculations')

    pdf.section_title('IRCI Framework')
    pdf.body_text(
        "The IRCI (Investor Relations Composite Index) measures IR effectiveness across four dimensions:\n\n"
        "1. Valuation - Market perception relative to fundamentals (P/E, P/S, EV/EBITDA)\n"
        "2. Liquidity - Trading activity (volume, spreads, volatility)\n"
        "3. Coverage - Media attention quality and quantity\n"
        "4. Trust - Sentiment and credibility (media tone, disclosure quality)\n\n"
        "Each dial is scored 0-100% based on percentile ranking within the peer group."
    )

    pdf.section_title('Composite Score Calculation')
    pdf.body_text(
        "The IRCI Composite Score is a weighted average of the four dials.\n"
        "Weights are optimized to maximize explanatory power of enterprise value variance.\n\n"
        "R-squared scaling is applied to dollar impact estimates to reflect that IR is one of many "
        "factors affecting enterprise value."
    )

    pdf.section_title('Peer Group')
    peer_list = ', '.join(df_composite['ticker'].tolist())
    pdf.body_text(f"Analysis includes {len(df_composite)} companies: {peer_list}")

    # Output PDF
    return bytes(pdf.output())


def classify_score(score: float) -> str:
    """Classify a score as Strong/Good/Fair/Weak"""
    if score >= 75:
        return "Strong"
    elif score >= 50:
        return "Good"
    elif score >= 25:
        return "Fair"
    else:
        return "Weak"
