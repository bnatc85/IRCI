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
    if not text:
        return ""

    # Convert to string if not already
    text = str(text)

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

    # Break very long words that might not fit (URLs, long strings without spaces)
    words = text.split()
    max_word_length = 80  # Maximum characters for a single word
    processed_words = []
    for word in words:
        if len(word) > max_word_length:
            # Insert spaces every max_word_length characters
            chunks = [word[i:i+max_word_length] for i in range(0, len(word), max_word_length)]
            processed_words.append(' '.join(chunks))
        else:
            processed_words.append(word)

    return ' '.join(processed_words).strip()


class IRCIReport(FPDF):
    """Custom PDF class for IRCI reports"""

    def __init__(self, ticker: str, quarter: str):
        super().__init__()
        self.ticker = ticker
        self.quarter = quarter
        # Set margins (left, top, right)
        self.set_margins(left=15, top=15, right=15)
        self.set_auto_page_break(auto=True, margin=15)

    def safe_multi_cell(self, w, h, txt, border=0, align='L', fill=False):
        """Safely render multi_cell with error handling"""
        try:
            cleaned_txt = strip_emojis(txt) if txt else ""
            if cleaned_txt:
                self.multi_cell(w, h, cleaned_txt, border=border, align=align, fill=fill)
        except Exception as e:
            # If rendering fails, truncate and try again
            print(f"Warning: PDF rendering issue, truncating text: {str(e)}")
            cleaned_txt = strip_emojis(txt)[:300] if txt else ""
            try:
                self.multi_cell(w, h, cleaned_txt + "...", border=border, align=align, fill=fill)
            except:
                # Last resort - just skip this text
                pass

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
        self.safe_multi_cell(0, 5, text)
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
    timeline_df: Optional[pd.DataFrame] = None,
    news_df: Optional[pd.DataFrame] = None,
    dollar_value_df: Optional[pd.DataFrame] = None,
    weights: Optional[Dict] = None
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

    # Calculate averages for comparison
    avg_valuation = df_composite['valuation_pct'].mean()
    avg_liquidity = df_composite['liquidity_pct'].mean()
    avg_coverage = df_composite['coverage_pct'].mean()
    avg_trust = df_composite['sentiment_pct'].mean()

    pdf.body_text(
        f"Valuation:  {valuation_score:.1f}% ({classify_score(valuation_score)}) - Peer Avg: {avg_valuation:.1f}% ({valuation_score - avg_valuation:+.1f})\n"
        f"Liquidity:  {liquidity_score:.1f}% ({classify_score(liquidity_score)}) - Peer Avg: {avg_liquidity:.1f}% ({liquidity_score - avg_liquidity:+.1f})\n"
        f"Coverage:   {coverage_score:.1f}% ({classify_score(coverage_score)}) - Peer Avg: {avg_coverage:.1f}% ({coverage_score - avg_coverage:+.1f})\n"
        f"Trust:      {trust_score:.1f}% ({classify_score(trust_score)}) - Peer Avg: {avg_trust:.1f}% ({trust_score - avg_trust:+.1f})"
    )

    # Identify strengths and weaknesses
    pdf.section_title('Key Strengths and Weaknesses')
    dials = {
        'Valuation': (valuation_score, avg_valuation),
        'Liquidity': (liquidity_score, avg_liquidity),
        'Coverage': (coverage_score, avg_coverage),
        'Trust': (trust_score, avg_trust)
    }

    strengths = [(name, score, avg) for name, (score, avg) in dials.items() if score > avg + 10]
    weaknesses = [(name, score, avg) for name, (score, avg) in dials.items() if score < avg - 10]

    if strengths:
        strength_text = "Strengths:\n" + "\n".join([f"* {name}: {score:.1f}% (vs peer avg {avg:.1f}%)" for name, score, avg in strengths])
        pdf.body_text(strength_text)

    if weaknesses:
        weakness_text = "Weaknesses:\n" + "\n".join([f"* {name}: {score:.1f}% (vs peer avg {avg:.1f}%)" for name, score, avg in weaknesses])
        pdf.body_text(weakness_text)

    if not strengths and not weaknesses:
        pdf.body_text("Performance is balanced across all dials, closely aligned with peer averages.")

    # Playbook summary
    pdf.section_title('Key Recommendations')
    pdf.body_text(playbook['summary'])

    high_priority_count = playbook['priority_counts']['high']
    if high_priority_count > 0:
        pdf.body_text(f"\n{high_priority_count} high-priority action items identified (see Playbook section)")

    # Add Potential Value Improvements if we have dollar value data
    if dollar_value_df is not None and not dollar_value_df.empty and weights is not None:
        company_data_dv = dollar_value_df[dollar_value_df['ticker'] == ticker]
        if not company_data_dv.empty:
            company_dollar_per_point = company_data_dv['company_$/irci_pt'].iloc[0]

            pdf.section_title('Potential Value Improvements')
            pdf.body_text(
                "Conservative estimates of value you can add by improving each dial next quarter:"
            )
            pdf.ln(2)

            # Get dial scores
            dial_scores = {
                'valuation': company_data.get('valuation_pct', 0),
                'liquidity': company_data.get('liquidity_pct', 0),
                'coverage': company_data.get('coverage_pct', 0),
                'trust': company_data.get('sentiment_pct', 0)
            }

            # Calculate improvements for each dial
            improvements = []
            dial_names = {
                'valuation': ('Valuation', weights.get('valuation', 0.25)),
                'liquidity': ('Liquidity', weights.get('liquidity', 0.25)),
                'coverage': ('Coverage', weights.get('coverage', 0.25)),
                'trust': ('Trust', weights.get('sentiment', 0.25))
            }

            for dial, score in dial_scores.items():
                dial_label, dial_weight = dial_names[dial]
                classification = playbook['dial_classifications'][dial]

                # Conservative improvement estimates based on classification
                if classification == 'critical' and score < 40:
                    min_improvement = 3
                    max_improvement = 8
                elif classification == 'low' or score < 50:
                    min_improvement = 2
                    max_improvement = 5
                elif score < 70:
                    min_improvement = 1
                    max_improvement = 3
                else:
                    min_improvement = 0.5
                    max_improvement = 2

                # Calculate IRCI impact (dial improvement x dial weight)
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

            # Sort by priority
            improvements.sort(key=lambda x: (x['priority'], -x['max_value']))

            # Display improvements
            for imp in improvements:
                classification_marker = {
                    'critical': '[CRITICAL]',
                    'low': '[LOW]',
                    'medium': '[MEDIUM]',
                    'strong': '[STRONG]'
                }.get(imp['classification'], '')

                pdf.set_font('Arial', 'B', 10)
                pdf.safe_multi_cell(
                    0, 6,
                    f"{imp['dial']} {classification_marker} - ${imp['min_value']/1e6:.0f}M to ${imp['max_value']/1e6:.0f}M"
                )
                pdf.set_font('Arial', '', 9)
                pdf.safe_multi_cell(
                    0, 5,
                    f"Current Score: {imp['current_score']:.1f}% | "
                    f"Improvement Range: +{imp['min_improvement']:.1f} to +{imp['max_improvement']:.1f} points"
                )
                pdf.ln(2)

            pdf.set_font('Arial', 'I', 8)
            pdf.safe_multi_cell(
                0, 4,
                f"$/IRCI Point for {ticker}: ${company_dollar_per_point:,.0f}. "
                f"Improvement ranges based on peer analysis and classification severity. "
                f"Values are R-squared scaled to reflect IR's partial influence on enterprise value."
            )

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

    pdf.body_text("\nLiquidity Dial Components:")
    if avg_volume:
        pdf.body_text(f"* Average Daily Volume: {avg_volume:,.0f} shares\n  (Higher volume = easier to trade large blocks)")
    if avg_spread:
        pdf.body_text(f"* Average Bid-Ask Spread: {avg_spread:.3f}%\n  (Narrower spreads = lower transaction costs)")
    if avg_volatility:
        pdf.body_text(f"* Average Volatility: {avg_volatility:.2f}%\n  (Lower volatility = more predictable pricing)")

    pdf.body_text("\nThese metrics are combined and percentile-ranked against peers to create the Liquidity dial score.")

    # Coverage
    pdf.section_title('Coverage Dial ({:.1f}%)'.format(coverage_score))
    cov_data = df_coverage[df_coverage['ticker'] == ticker].iloc[0]

    total_weighted = cov_data['total_weighted_articles'] if 'total_weighted_articles' in cov_data.index and pd.notna(cov_data['total_weighted_articles']) else None
    total_filings = cov_data['total_filings'] if 'total_filings' in cov_data.index and pd.notna(cov_data['total_filings']) else None
    media_score = cov_data['media_score'] if 'media_score' in cov_data.index and pd.notna(cov_data['media_score']) else None

    pdf.body_text(
        f"Coverage Percentile: {coverage_score:.1f}% (within peer group)"
    )

    pdf.body_text("\nCoverage Dial Components:")
    if total_weighted:
        pdf.body_text(f"* Weighted Media Coverage: {total_weighted:.1f} articles\n  (Quality sources like WSJ/Bloomberg weighted higher)")
    if total_filings:
        pdf.body_text(f"* SEC Filings This Quarter: {int(total_filings)}\n  (8-Ks, 10-Qs, 10-Ks demonstrate transparency)")
    if media_score:
        pdf.body_text(f"* Media Score: {media_score:.1f}\n  (Combined metric of article count and source quality)")

    pdf.body_text("\nThe Coverage dial rewards both quantity and quality of media attention, plus regulatory disclosure frequency.")

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

    pdf.body_text("\nTrust Dial Components:")
    if media_tone is not None:
        pdf.body_text(
            f"* Media Tone Score: {media_tone:.1f}%\n"
            f"  Sentiment Classification: {sentiment_label}\n"
            f"  (Aggregate sentiment from all news articles using FinBERT AI)"
        )

    pdf.body_text(
        f"* Sentiment Consistency: Measures volatility in media tone over time\n"
        f"* Source Credibility: Weighted by reputation of news outlets\n"
        f"* Disclosure Quality: Timeliness and clarity of SEC filings"
    )

    pdf.body_text("\nThe Trust dial reflects market perception of management credibility and transparency based on media sentiment and disclosure patterns.")

    # MEDIA SENTIMENT ANALYSIS (NEW SECTION)
    if news_df is not None and not news_df.empty and 'sentiment_score' in news_df.columns:
        pdf.add_page()
        pdf.chapter_title('2a. Media Sentiment Analysis')

        # Filter news for this ticker
        ticker_news = news_df[news_df['ticker'] == ticker].copy()

        if not ticker_news.empty and 'sentiment_score' in ticker_news.columns:
            # Overall sentiment stats
            pdf.section_title('Sentiment Overview')
            total_articles = len(ticker_news)
            avg_sentiment = ticker_news['sentiment_score'].mean()
            positive_count = len(ticker_news[ticker_news['sentiment_score'] > 0.1])
            negative_count = len(ticker_news[ticker_news['sentiment_score'] < -0.1])
            neutral_count = total_articles - positive_count - negative_count

            pdf.body_text(
                f"Total News Articles Analyzed: {total_articles}\n"
                f"Average Sentiment Score: {avg_sentiment:+.3f}\n"
                f"Positive Articles: {positive_count} ({positive_count/total_articles*100:.1f}%)\n"
                f"Neutral Articles: {neutral_count} ({neutral_count/total_articles*100:.1f}%)\n"
                f"Negative Articles: {negative_count} ({negative_count/total_articles*100:.1f}%)"
            )

            # Most Positive News
            pdf.section_title('Most Positive News (Top 5)')
            positive_news = ticker_news[ticker_news['sentiment_score'] > 0].sort_values(
                'sentiment_score', ascending=False
            ).head(5)

            if not positive_news.empty:
                for idx, article in positive_news.iterrows():
                    headline = article.get('headline', 'No headline')[:150]
                    sentiment = article.get('sentiment_score', 0)
                    date = article.get('published_at', '')
                    source = article.get('source', 'Unknown')

                    # Format date if it's a timestamp
                    if isinstance(date, pd.Timestamp):
                        date_str = date.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date)[:10] if date else 'N/A'

                    pdf.set_font('Arial', 'B', 9)
                    pdf.safe_multi_cell(0, 5, f"[{date_str}] {headline}")
                    pdf.set_font('Arial', 'I', 8)
                    pdf.safe_multi_cell(0, 4, f"Source: {source}")
                    pdf.safe_multi_cell(0, 4, f"Sentiment: +{sentiment:.3f}")
                    pdf.ln(2)
            else:
                pdf.body_text("No strongly positive news articles found in this period.")

            # Most Negative News
            pdf.section_title('Most Negative News (Top 5)')
            negative_news = ticker_news[ticker_news['sentiment_score'] < 0].sort_values(
                'sentiment_score', ascending=True
            ).head(5)

            if not negative_news.empty:
                for idx, article in negative_news.iterrows():
                    headline = article.get('headline', 'No headline')[:150]
                    sentiment = article.get('sentiment_score', 0)
                    date = article.get('published_at', '')
                    source = article.get('source', 'Unknown')

                    # Format date if it's a timestamp
                    if isinstance(date, pd.Timestamp):
                        date_str = date.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date)[:10] if date else 'N/A'

                    pdf.set_font('Arial', 'B', 9)
                    pdf.safe_multi_cell(0, 5, f"[{date_str}] {headline}")
                    pdf.set_font('Arial', 'I', 8)
                    pdf.safe_multi_cell(0, 4, f"Source: {source}")
                    pdf.safe_multi_cell(0, 4, f"Sentiment: {sentiment:.3f}")
                    pdf.ln(2)
            else:
                pdf.body_text("No strongly negative news articles found in this period.")

            # Sentiment by Source
            if 'source' in ticker_news.columns:
                pdf.section_title('Sentiment by News Source')
                source_sentiment = ticker_news.groupby('source')['sentiment_score'].agg(['count', 'mean']).sort_values('count', ascending=False).head(10)

                if not source_sentiment.empty:
                    for source, row in source_sentiment.iterrows():
                        count = int(row['count'])
                        avg_sent = row['mean']
                        pdf.set_font('Arial', '', 9)
                        pdf.safe_multi_cell(0, 5, f"{source}: {count} articles, avg sentiment {avg_sent:+.3f}")

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
        pdf.body_text(
            "HIGH PRIORITY actions address critical weaknesses or opportunities with significant impact. "
            "These should be actioned immediately with dedicated resources and executive sponsorship. "
            "Expect to see measurable improvements within 1-2 quarters."
        )
        pdf.ln(2)

        for i, rec in enumerate(high_priority, 1):
            pdf.set_font('Arial', 'B', 10)
            # Use safe_multi_cell for wrapping long titles
            pdf.safe_multi_cell(0, 6, f"{i}. {rec['action']} ({rec['category']})")
            # Add "what" field if present
            if rec.get('what'):
                pdf.set_font('Arial', 'I', 9)
                pdf.safe_multi_cell(0, 5, f"What: {rec['what']}")
            pdf.set_font('Arial', '', 9)
            pdf.safe_multi_cell(0, 5, rec['description'])
            if rec.get('quick_win'):
                pdf.set_font('Arial', 'I', 8)
                pdf.safe_multi_cell(0, 4, '[Quick Win]')
            pdf.ln(2)

    # Medium priority recommendations
    medium_priority = [r for r in playbook['recommendations'] if r['priority'] == 'medium']
    if medium_priority:
        pdf.add_page()
        pdf.section_title('Medium Priority Actions')
        pdf.body_text(
            "MEDIUM PRIORITY actions improve performance in areas where you're meeting baseline standards "
            "but have room for optimization. These should be planned into your quarterly IR roadmap. "
            "Focus here after addressing high-priority items."
        )
        pdf.ln(2)

        for i, rec in enumerate(medium_priority, 1):
            pdf.set_font('Arial', 'B', 10)
            # Use safe_multi_cell for wrapping long titles
            pdf.safe_multi_cell(0, 6, f"{i}. {rec['action']} ({rec['category']})")
            # Add "what" field if present
            if rec.get('what'):
                pdf.set_font('Arial', 'I', 9)
                pdf.safe_multi_cell(0, 5, f"What: {rec['what']}")
            pdf.set_font('Arial', '', 9)
            pdf.safe_multi_cell(0, 5, rec['description'])
            if rec.get('quick_win'):
                pdf.set_font('Arial', 'I', 8)
                pdf.safe_multi_cell(0, 4, '[Quick Win]')
            pdf.ln(2)

    # Quick Wins summary
    if playbook['quick_wins']:
        pdf.add_page()
        pdf.section_title('Quick Wins Summary')
        pdf.body_text(
            f"QUICK WINS are actions that can be implemented quickly (within 1-2 weeks) with minimal resources "
            f"but deliver immediate visible impact. These are ideal for building momentum and demonstrating progress "
            f"while longer-term initiatives are underway."
        )
        pdf.ln(2)

        pdf.body_text(f"Identified {len(playbook['quick_wins'])} quick win opportunities:")
        pdf.ln(2)

        for i, rec in enumerate(playbook['quick_wins'][:10], 1):  # Top 10 quick wins
            pdf.set_font('Arial', 'B', 9)
            # Use safe_multi_cell for wrapping
            pdf.safe_multi_cell(0, 5, f"{i}. {rec['action']}")

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
            # Use safe_multi_cell for date/type to handle wrapping
            pdf.safe_multi_cell(0, 5, f"{date} - {event_type.upper()}")
            pdf.set_font('Arial', '', 9)
            pdf.safe_multi_cell(0, 4, description)
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 4, f"IRCI Impact: {irci_impact:+.3f} points", 0, 1)
            pdf.ln(2)

    # 6. DETAILED METRICS BREAKDOWN
    pdf.add_page()
    pdf.chapter_title('6. Detailed Metrics & Statistics')

    # Enterprise Value and Financial Metrics
    pdf.section_title('Financial Metrics')
    if 'enterprise_value' in company_data.index and pd.notna(company_data['enterprise_value']):
        ev = company_data['enterprise_value']
        pdf.body_text(f"Enterprise Value: ${ev/1e9:.2f} billion")

        # Show percentile within peer group
        ev_percentile = (df_composite['enterprise_value'] < ev).sum() / len(df_composite) * 100
        pdf.body_text(f"EV Percentile: {ev_percentile:.1f}% (larger than {ev_percentile:.0f}% of peers)")

    # Company vs Peer Averages - Detailed
    pdf.section_title('Peer Group Positioning')

    peer_metrics = []
    peer_metrics.append(f"IRCI Composite: {ticker} {irci_score:.1f}% vs Avg {peer_avg:.1f}%")
    peer_metrics.append(f"Valuation Dial: {ticker} {valuation_score:.1f}% vs Avg {avg_valuation:.1f}%")
    peer_metrics.append(f"Liquidity Dial: {ticker} {liquidity_score:.1f}% vs Avg {avg_liquidity:.1f}%")
    peer_metrics.append(f"Coverage Dial: {ticker} {coverage_score:.1f}% vs Avg {avg_coverage:.1f}%")
    peer_metrics.append(f"Trust Dial: {ticker} {trust_score:.1f}% vs Avg {avg_trust:.1f}%")

    pdf.body_text("\n".join(peer_metrics))

    # Dial Score Distribution
    pdf.section_title('Score Distribution Analysis')

    dial_stats = []
    for dial_name, dial_col in [
        ('Valuation', 'valuation_pct'),
        ('Liquidity', 'liquidity_pct'),
        ('Coverage', 'coverage_pct'),
        ('Trust', 'sentiment_pct')
    ]:
        if dial_col in df_composite.columns:
            dial_data = df_composite[dial_col]
            dial_min = dial_data.min()
            dial_max = dial_data.max()
            dial_median = dial_data.median()
            company_score = company_data.get(dial_col, 0)

            dial_stats.append(
                f"{dial_name}: Range {dial_min:.1f}%-{dial_max:.1f}%, "
                f"Median {dial_median:.1f}%, "
                f"{ticker} {company_score:.1f}%"
            )

    pdf.body_text("\n".join(dial_stats))

    # Recommendations Priority Matrix
    if playbook['recommendations']:
        pdf.section_title('Action Items Priority Matrix')

        total_recs = len(playbook['recommendations'])
        high_pct = playbook['priority_counts']['high'] / total_recs * 100
        med_pct = playbook['priority_counts']['medium'] / total_recs * 100
        low_pct = playbook['priority_counts']['low'] / total_recs * 100

        pdf.body_text(
            f"Total Recommendations: {total_recs}\n"
            f"High Priority: {playbook['priority_counts']['high']} ({high_pct:.0f}%)\n"
            f"Medium Priority: {playbook['priority_counts']['medium']} ({med_pct:.0f}%)\n"
            f"Low Priority: {playbook['priority_counts']['low']} ({low_pct:.0f}%)\n"
            f"Quick Wins Available: {len(playbook['quick_wins'])}"
        )

        # Recommendations by category
        category_counts = {}
        for rec in playbook['recommendations']:
            cat = rec['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        if category_counts:
            pdf.body_text("\nRecommendations by Focus Area:")
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                pdf.body_text(f"  {cat}: {count} action items")

    # 7. METHODOLOGY
    pdf.add_page()
    pdf.chapter_title('7. Methodology & Calculations')

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
