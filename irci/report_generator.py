# irci/report_generator.py
"""
PDF Report Generator for IRCI Analysis
Creates comprehensive board-grade reports with all analysis results
"""
from fpdf import FPDF
from datetime import datetime, timedelta
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
    """Custom PDF class for IRCI reports - Board Grade"""

    def __init__(self, ticker: str, quarter: str, company_name: str = None):
        super().__init__()
        self.ticker = ticker
        self.quarter = quarter
        self.company_name = company_name or ticker
        # Set margins (left, top, right)
        self.set_margins(left=15, top=20, right=15)
        self.set_auto_page_break(auto=True, margin=20)
        self.is_cover_page = True

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
        """Page header - professional styling"""
        if self.is_cover_page:
            return  # No header on cover page

        # Header bar
        self.set_fill_color(20, 40, 80)  # Dark blue
        self.rect(0, 0, 210, 15, 'F')

        # Company name and report type
        self.set_font('Arial', 'B', 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(15, 4)
        self.cell(100, 6, f'{self.ticker} - IRCI Board Report', 0, 0, 'L')

        # Quarter and date
        self.set_font('Arial', '', 9)
        self.set_xy(115, 4)
        self.cell(80, 6, f'{self.quarter} | {datetime.now().strftime("%B %d, %Y")}', 0, 0, 'R')

        self.set_text_color(0, 0, 0)  # Reset to black
        self.set_y(20)

    def footer(self):
        """Page footer"""
        if self.is_cover_page:
            return
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'IRCI Board Report - {self.ticker} - Page {self.page_no()}', 0, 0, 'C')
        self.set_text_color(0, 0, 0)

    def add_cover_page(self, irci_score: float, peer_rank: int, total_peers: int,
                       dial_scores: Dict, dollar_per_point: float = None):
        """Add professional cover page - condensed to fit on one page"""
        self.add_page()
        self.is_cover_page = True

        # Compact dark header section
        self.set_fill_color(20, 40, 80)
        self.rect(0, 0, 210, 55, 'F')

        # IRCI Logo/Title
        self.set_font('Arial', 'B', 22)
        self.set_text_color(255, 255, 255)
        self.set_xy(15, 12)
        self.cell(0, 10, 'IRCI', 0, 1, 'L')

        self.set_font('Arial', '', 11)
        self.set_xy(15, 24)
        self.cell(0, 6, 'Investor Relations Composite Index', 0, 1, 'L')

        # Company and Quarter
        self.set_font('Arial', 'B', 16)
        self.set_xy(15, 36)
        self.cell(0, 8, f'{self.ticker} Board Report | {self.quarter}', 0, 1, 'L')

        self.set_text_color(0, 0, 0)

        # Score summary box - more compact
        self.set_y(62)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, 'EXECUTIVE SNAPSHOT', 0, 1, 'C')

        # Main score card - smaller
        self._draw_score_card(irci_score, peer_rank, total_peers, 60, 75)

        # Dial scores in a row - moved up
        self.set_y(125)
        self._draw_dial_summary(dial_scores)

        # Dollar value if available - more compact
        if dollar_per_point and dollar_per_point > 0:
            self.set_y(165)
            self.set_font('Arial', 'B', 10)
            self.cell(0, 6, 'VALUE PER IRCI POINT', 0, 1, 'C')
            self.set_font('Arial', 'B', 14)
            if dollar_per_point >= 1e9:
                value_str = f'${dollar_per_point/1e9:.2f}B'
            else:
                value_str = f'${dollar_per_point/1e6:.1f}M'
            self.cell(0, 8, value_str, 0, 1, 'C')
            self.set_font('Arial', 'I', 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, 'R-squared scaled estimate based on peer regression', 0, 1, 'C')
            self.set_text_color(0, 0, 0)

        # Footer - moved up
        self.set_y(250)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 4, f'Generated: {datetime.now().strftime("%B %d, %Y at %H:%M")}', 0, 1, 'C')
        self.cell(0, 4, 'Confidential - For Board Use Only', 0, 1, 'C')
        self.set_text_color(0, 0, 0)

        self.is_cover_page = False

    def _draw_score_card(self, score: float, rank: int, total: int, x: float, y: float):
        """Draw the main IRCI score card - compact version"""
        # Score circle background
        self.set_fill_color(*self._get_score_color(score))
        self.set_xy(x + 25, y)

        # Large score - smaller
        self.set_font('Arial', 'B', 36)
        self.set_text_color(0, 0, 0)
        self.cell(60, 22, f'{score:.0f}%', 0, 1, 'C')

        # Label
        self.set_font('Arial', 'B', 10)
        self.set_xy(x + 25, y + 24)
        self.cell(60, 6, 'IRCI COMPOSITE SCORE', 0, 1, 'C')

        # Rank and Classification on same line
        classification = self._classify_score_label(score)
        color = self._get_score_color(score)
        self.set_font('Arial', '', 9)
        self.set_xy(x + 25, y + 32)
        self.cell(60, 5, f'#{rank} of {total} peers', 0, 1, 'C')

        self.set_font('Arial', 'B', 11)
        self.set_text_color(*color)
        self.set_xy(x + 25, y + 38)
        self.cell(60, 6, classification.upper(), 0, 1, 'C')
        self.set_text_color(0, 0, 0)

    def _draw_dial_summary(self, dial_scores: Dict):
        """Draw the four dial scores in a row - compact version"""
        dials = [
            ('VALUATION', dial_scores.get('valuation', 0), '$'),
            ('LIQUIDITY', dial_scores.get('liquidity', 0), '~'),
            ('COVERAGE', dial_scores.get('coverage', 0), '#'),
            ('TRUST', dial_scores.get('trust', 0), '*')
        ]

        start_x = 20
        width = 42

        for i, (name, score, icon) in enumerate(dials):
            x = start_x + (i * width)

            # Box background - smaller height
            color = self._get_score_color(score)
            self.set_fill_color(*color)
            self.rect(x, self.get_y(), width - 2, 28, 'F')

            # Dial name
            self.set_font('Arial', 'B', 7)
            self.set_text_color(255, 255, 255)
            self.set_xy(x, self.get_y() + 2)
            self.cell(width - 2, 4, f'[{icon}] {name}', 0, 0, 'C')

            # Score - smaller
            self.set_font('Arial', 'B', 16)
            self.set_xy(x, self.get_y() + 7)
            self.cell(width - 2, 10, f'{score:.0f}%', 0, 0, 'C')

            # Classification
            self.set_font('Arial', '', 7)
            self.set_xy(x, self.get_y() + 18)
            self.cell(width - 2, 4, self._classify_score_label(score), 0, 0, 'C')

        self.set_text_color(0, 0, 0)

    def _get_score_color(self, score: float) -> tuple:
        """Get color based on score (RGB)"""
        if score >= 70:
            return (34, 139, 34)   # Forest green
        elif score >= 50:
            return (255, 193, 7)   # Amber/Gold
        elif score >= 35:
            return (255, 152, 0)   # Orange
        else:
            return (220, 53, 69)   # Red

    def _classify_score_label(self, score: float) -> str:
        """Get classification label for score"""
        if score >= 70:
            return "Strong"
        elif score >= 50:
            return "Good"
        elif score >= 35:
            return "Fair"
        else:
            return "Needs Attention"

    def chapter_title(self, title: str):
        """Add a chapter title with styling"""
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(20, 40, 80)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, strip_emojis(title), 0, 1, 'L', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def section_title(self, title: str):
        """Add a section title"""
        self.set_font('Arial', 'B', 11)
        self.set_text_color(20, 40, 80)
        self.cell(0, 8, strip_emojis(title), 0, 1, 'L')
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def body_text(self, text: str):
        """Add body text"""
        self.set_font('Arial', '', 10)
        self.safe_multi_cell(0, 5, text)
        self.ln(2)

    def add_score_indicator(self, label: str, score: float, x: float = None, width: float = 60):
        """Add a color-coded score indicator"""
        if x:
            self.set_x(x)

        color = self._get_score_color(score)
        classification = self._classify_score_label(score)

        # Label
        self.set_font('Arial', 'B', 9)
        self.cell(width * 0.4, 6, label, 0, 0, 'L')

        # Score with color background
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 9)
        self.cell(width * 0.25, 6, f'{score:.1f}%', 1, 0, 'C', fill=True)

        # Classification
        self.set_text_color(0, 0, 0)
        self.set_font('Arial', '', 8)
        self.cell(width * 0.35, 6, f' {classification}', 0, 1, 'L')

    def add_competitive_matrix(self, df_composite: pd.DataFrame, ticker: str, dial_scores: Dict,
                                df_valuation: pd.DataFrame = None, df_liquidity: pd.DataFrame = None,
                                df_coverage: pd.DataFrame = None, df_trust: pd.DataFrame = None):
        """Add competitive positioning matrix with dial breakdown"""
        self.chapter_title('COMPETITIVE POSITIONING & DIAL ANALYSIS')

        # Get top 3 peers plus the company
        df_sorted = df_composite.sort_values('irci_composite_pct', ascending=False)
        top_peers = df_sorted.head(5)['ticker'].tolist()

        if ticker not in top_peers:
            top_peers = top_peers[:4] + [ticker]

        # Table header
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(20, 40, 80)
        self.set_text_color(255, 255, 255)

        col_widths = [25, 25, 25, 25, 25, 30, 25]
        headers = ['Company', 'IRCI', 'Valuation', 'Liquidity', 'Coverage', 'Trust', 'Rank']

        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, 1, 0, 'C', fill=True)
        self.ln()

        self.set_text_color(0, 0, 0)

        # Table rows
        for rank, (_, row) in enumerate(df_sorted.iterrows(), 1):
            if row['ticker'] not in top_peers and rank > 5:
                continue

            is_target = row['ticker'] == ticker

            if is_target:
                self.set_font('Arial', 'B', 9)
                self.set_fill_color(230, 240, 255)
            else:
                self.set_font('Arial', '', 9)
                self.set_fill_color(255, 255, 255)

            # Company name
            self.cell(col_widths[0], 6, row['ticker'], 1, 0, 'C', fill=is_target)

            # Scores with color coding
            scores = [
                row['irci_composite_pct'],
                row['valuation_pct'],
                row['liquidity_pct'],
                row['coverage_pct'],
                row['sentiment_pct']
            ]

            for i, score in enumerate(scores):
                color = self._get_score_color(score)
                self.set_fill_color(*color)
                self.set_text_color(255, 255, 255)
                self.cell(col_widths[i + 1], 6, f'{score:.0f}%', 1, 0, 'C', fill=True)

            # Rank
            self.set_fill_color(255, 255, 255) if not is_target else self.set_fill_color(230, 240, 255)
            self.set_text_color(0, 0, 0)
            actual_rank = int(df_sorted['irci_composite_pct'].rank(ascending=False)[df_sorted['ticker'] == row['ticker']].iloc[0])
            self.cell(col_widths[6], 6, f'#{actual_rank}', 1, 0, 'C', fill=is_target)
            self.ln()

        self.set_text_color(0, 0, 0)
        self.ln(2)

        # Analysis text
        company_rank = int(df_sorted['irci_composite_pct'].rank(ascending=False)[df_sorted['ticker'] == ticker].iloc[0])
        leader = df_sorted.iloc[0]['ticker']
        leader_score = df_sorted.iloc[0]['irci_composite_pct']
        company_score = df_sorted[df_sorted['ticker'] == ticker]['irci_composite_pct'].iloc[0]
        gap = leader_score - company_score

        self.set_font('Arial', 'I', 9)
        if company_rank == 1:
            self.body_text(f"{ticker} leads this peer group. Focus on maintaining position.")
        else:
            self.body_text(f"{ticker} ranks #{company_rank}. Gap to leader ({leader}): {gap:.1f} pts.")

        # Dial breakdown section - integrated from detailed dial analysis
        self.ln(2)
        self.section_title(f'{ticker} Dial Breakdown vs Peer Averages')

        # Calculate peer averages
        avg_val = df_composite['valuation_pct'].mean()
        avg_liq = df_composite['liquidity_pct'].mean()
        avg_cov = df_composite['coverage_pct'].mean()
        avg_trust = df_composite['sentiment_pct'].mean()

        # Compact dial comparison table
        self.set_font('Arial', 'B', 8)
        self.set_fill_color(20, 40, 80)
        self.set_text_color(255, 255, 255)
        self.cell(45, 6, 'Dial', 1, 0, 'C', fill=True)
        self.cell(35, 6, f'{ticker}', 1, 0, 'C', fill=True)
        self.cell(35, 6, 'Peer Avg', 1, 0, 'C', fill=True)
        self.cell(35, 6, 'Gap', 1, 1, 'C', fill=True)
        self.set_text_color(0, 0, 0)

        dial_comparisons = [
            ('Valuation', dial_scores.get('valuation', 0), avg_val),
            ('Liquidity', dial_scores.get('liquidity', 0), avg_liq),
            ('Coverage', dial_scores.get('coverage', 0), avg_cov),
            ('Trust', dial_scores.get('trust', 0), avg_trust),
        ]

        self.set_font('Arial', '', 8)
        for dial_name, company_val, peer_avg in dial_comparisons:
            gap = company_val - peer_avg
            gap_str = f'+{gap:.1f}' if gap > 0 else f'{gap:.1f}'

            self.cell(45, 5, dial_name, 1, 0, 'L')

            # Company score with color
            color = self._get_score_color(company_val)
            self.set_fill_color(*color)
            self.set_text_color(255, 255, 255)
            self.cell(35, 5, f'{company_val:.1f}%', 1, 0, 'C', fill=True)

            # Peer avg
            self.set_fill_color(200, 200, 200)
            self.set_text_color(0, 0, 0)
            self.cell(35, 5, f'{peer_avg:.1f}%', 1, 0, 'C', fill=True)

            # Gap with color
            if gap >= 5:
                self.set_fill_color(34, 139, 34)
                self.set_text_color(255, 255, 255)
            elif gap <= -5:
                self.set_fill_color(220, 53, 69)
                self.set_text_color(255, 255, 255)
            else:
                self.set_fill_color(255, 255, 255)
                self.set_text_color(0, 0, 0)
            self.cell(35, 5, gap_str, 1, 1, 'C', fill=True)

        self.set_text_color(0, 0, 0)

    def add_90_day_action_plan(self, playbook: Dict, ticker: str, dial_scores: Dict,
                                dollar_per_point: float = None):
        """Add 90-day action plan section"""
        self.chapter_title('90-DAY ACTION PLAN')

        # Priority matrix
        self.section_title('Priority Matrix')

        # Identify weakest dial
        dial_order = sorted(dial_scores.items(), key=lambda x: x[1])
        weakest_dial = dial_order[0][0]
        weakest_score = dial_order[0][1]

        self.body_text(f"Primary Focus Area: {weakest_dial.upper()} ({weakest_score:.1f}%)")
        self.ln(2)

        # Timeline sections
        phases = [
            ("DAYS 1-30: QUICK WINS", "immediate", 30),
            ("DAYS 31-60: FOUNDATION", "foundation", 60),
            ("DAYS 61-90: STRATEGIC", "strategic", 90)
        ]

        high_priority = [r for r in playbook['recommendations'] if r['priority'] == 'high']
        medium_priority = [r for r in playbook['recommendations'] if r['priority'] == 'medium']
        quick_wins = playbook.get('quick_wins', [])

        # Days 1-30: Quick Wins
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(34, 139, 34)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, '  DAYS 1-30: QUICK WINS', 0, 1, 'L', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

        for i, rec in enumerate(quick_wins[:3], 1):
            self.set_font('Arial', 'B', 9)
            self.cell(8, 5, f'{i}.', 0, 0, 'L')
            self.safe_multi_cell(0, 5, rec['action'])
            self.set_font('Arial', '', 8)
            self.set_x(23)
            self.safe_multi_cell(0, 4, f"Owner: IR Team | Target: Week {i}")
            self.ln(1)

        if not quick_wins:
            self.body_text("No quick wins identified - focus on foundation building.")

        self.ln(3)

        # Days 31-60: Foundation
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(255, 193, 7)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, '  DAYS 31-60: FOUNDATION BUILDING', 0, 1, 'L', fill=True)
        self.ln(2)

        for i, rec in enumerate(high_priority[:3], 1):
            self.set_font('Arial', 'B', 9)
            self.cell(8, 5, f'{i}.', 0, 0, 'L')
            self.safe_multi_cell(0, 5, rec['action'])
            self.set_font('Arial', '', 8)
            self.set_x(23)
            self.safe_multi_cell(0, 4, f"Category: {rec['category']} | Priority: HIGH")
            self.ln(1)

        self.ln(3)

        # Days 61-90: Strategic
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(20, 40, 80)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, '  DAYS 61-90: STRATEGIC INITIATIVES', 0, 1, 'L', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

        remaining = high_priority[3:] + medium_priority[:3]
        for i, rec in enumerate(remaining[:3], 1):
            self.set_font('Arial', 'B', 9)
            self.cell(8, 5, f'{i}.', 0, 0, 'L')
            self.safe_multi_cell(0, 5, rec['action'])
            self.set_font('Arial', '', 8)
            self.set_x(23)
            self.safe_multi_cell(0, 4, f"Category: {rec['category']} | Priority: {rec['priority'].upper()}")
            self.ln(1)

        # Expected outcomes
        self.ln(5)
        self.section_title('Expected Outcomes')

        # Conservative improvement estimate
        if dollar_per_point and dollar_per_point > 0:
            min_improvement = 2
            max_improvement = 5
            min_value = min_improvement * dollar_per_point
            max_value = max_improvement * dollar_per_point

            if max_value >= 1e9:
                value_range = f"${min_value/1e9:.1f}B - ${max_value/1e9:.1f}B"
            else:
                value_range = f"${min_value/1e6:.0f}M - ${max_value/1e6:.0f}M"

            self.body_text(
                f"If this plan is executed successfully:\n"
                f"* Expected IRCI improvement: +{min_improvement} to +{max_improvement} points\n"
                f"* Estimated value creation: {value_range}\n"
                f"* Timeline to measurable results: 1-2 quarters"
            )
        else:
            self.body_text(
                f"If this plan is executed successfully:\n"
                f"* Expected IRCI improvement: +2 to +5 points\n"
                f"* Timeline to measurable results: 1-2 quarters"
            )

    def add_roi_section(self, ticker: str, dial_scores: Dict, dollar_per_point: float,
                        playbook: Dict):
        """Add ROI and investment recommendation section"""
        self.chapter_title('INVESTMENT & ROI ANALYSIS')

        if not dollar_per_point or dollar_per_point <= 0:
            self.body_text("Dollar value per IRCI point not available for this peer group.")
            return

        # Value per point
        self.section_title('Value Per IRCI Point')
        if dollar_per_point >= 1e9:
            value_str = f'${dollar_per_point/1e9:.2f} billion'
        else:
            value_str = f'${dollar_per_point/1e6:.1f} million'

        self.set_font('Arial', 'B', 14)
        self.cell(0, 8, value_str, 0, 1, 'L')
        self.set_font('Arial', 'I', 9)
        self.body_text("Based on peer group regression, R-squared scaled for conservatism.")
        self.ln(3)

        # Improvement scenarios
        self.section_title('Improvement Scenarios')

        scenarios = [
            ("Conservative", 2, "Basic IR improvements"),
            ("Moderate", 4, "Focused dial improvement program"),
            ("Aggressive", 7, "Comprehensive IR transformation")
        ]

        # Table header
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(20, 40, 80)
        self.set_text_color(255, 255, 255)

        self.cell(40, 7, 'Scenario', 1, 0, 'C', fill=True)
        self.cell(30, 7, 'IRCI Gain', 1, 0, 'C', fill=True)
        self.cell(50, 7, 'Est. Value Created', 1, 0, 'C', fill=True)
        self.cell(60, 7, 'Description', 1, 1, 'C', fill=True)

        self.set_text_color(0, 0, 0)
        self.set_font('Arial', '', 9)

        for scenario, points, desc in scenarios:
            value = points * dollar_per_point
            if value >= 1e9:
                value_str = f'${value/1e9:.2f}B'
            else:
                value_str = f'${value/1e6:.0f}M'

            self.cell(40, 6, scenario, 1, 0, 'L')
            self.cell(30, 6, f'+{points} pts', 1, 0, 'C')
            self.cell(50, 6, value_str, 1, 0, 'C')
            self.cell(60, 6, desc, 1, 1, 'L')

        self.ln(5)

        # Investment recommendation
        self.section_title('Investment Recommendation')

        # Identify primary dial to improve
        dial_order = sorted(dial_scores.items(), key=lambda x: x[1])
        weakest_dial = dial_order[0][0]
        weakest_score = dial_order[0][1]

        # Calculate break-even
        typical_ir_budget = 500000  # $500K typical IR program cost
        breakeven_points = typical_ir_budget / dollar_per_point if dollar_per_point > 0 else 0

        self.body_text(
            f"Primary Investment Focus: {weakest_dial.upper()} Dial (currently {weakest_score:.1f}%)\n\n"
            f"Investment Logic:\n"
            f"* Every 1-point IRCI improvement = ~{value_str} in enterprise value\n"
            f"* Typical IR program investment of $500K would break even at +{breakeven_points:.2f} IRCI points\n"
            f"* With focused effort on {weakest_dial}, a +3-5 point improvement is achievable\n"
            f"* Expected ROI: {(3 * dollar_per_point / typical_ir_budget - 1) * 100:.0f}% to {(5 * dollar_per_point / typical_ir_budget - 1) * 100:.0f}%"
        )

        self.ln(3)
        self.set_font('Arial', 'I', 8)
        self.body_text(
            "Note: Value estimates are R-squared scaled to reflect that IR is one of many factors "
            "affecting enterprise value. Actual results depend on execution and market conditions."
        )

    def add_risk_flags(self, dial_scores: Dict, ticker: str, df_composite: pd.DataFrame):
        """Add risk flags section"""
        self.section_title('RISK FLAGS')

        risks = []

        # Check for critical dials
        for dial, score in dial_scores.items():
            if score < 35:
                risks.append({
                    'severity': 'HIGH',
                    'dial': dial.upper(),
                    'issue': f'{dial.capitalize()} score is critically low ({score:.1f}%)',
                    'action': f'Immediate focus required on {dial} improvement'
                })
            elif score < 50:
                risks.append({
                    'severity': 'MEDIUM',
                    'dial': dial.upper(),
                    'issue': f'{dial.capitalize()} score below peer average ({score:.1f}%)',
                    'action': f'Include {dial} improvement in quarterly roadmap'
                })

        # Check peer ranking
        company_score = df_composite[df_composite['ticker'] == ticker]['irci_composite_pct'].iloc[0]
        rank = int(df_composite['irci_composite_pct'].rank(ascending=False)[df_composite['ticker'] == ticker].iloc[0])
        total = len(df_composite)

        if rank > total * 0.75:  # Bottom quartile
            risks.append({
                'severity': 'HIGH',
                'dial': 'OVERALL',
                'issue': f'Company ranks in bottom quartile (#{rank} of {total})',
                'action': 'Comprehensive IR review recommended'
            })

        if not risks:
            self.set_font('Arial', '', 10)
            self.set_text_color(34, 139, 34)
            self.body_text("No critical risk flags identified. All dials performing at acceptable levels.")
            self.set_text_color(0, 0, 0)
            return

        # Display risks
        for risk in risks:
            if risk['severity'] == 'HIGH':
                self.set_fill_color(220, 53, 69)
            else:
                self.set_fill_color(255, 193, 7)

            self.set_text_color(255, 255, 255)
            self.set_font('Arial', 'B', 9)
            self.cell(20, 6, risk['severity'], 0, 0, 'C', fill=True)

            self.set_text_color(0, 0, 0)
            self.set_font('Arial', 'B', 9)
            self.cell(25, 6, f" [{risk['dial']}]", 0, 0, 'L')

            self.set_font('Arial', '', 9)
            self.safe_multi_cell(0, 6, risk['issue'])

            self.set_font('Arial', 'I', 8)
            self.set_x(45)
            self.safe_multi_cell(0, 5, f"-> {risk['action']}")
            self.ln(2)

        self.set_text_color(0, 0, 0)


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
    Generate a comprehensive board-grade PDF report of IRCI analysis
    """
    pdf = IRCIReport(ticker, quarter)

    # Filter to the specific quarter if multi-quarter data is present
    if 'quarter' in df_composite.columns:
        df_composite_filtered = df_composite[df_composite['quarter'] == quarter].copy()
        df_valuation_filtered = df_valuation[df_valuation['quarter'] == quarter].copy() if 'quarter' in df_valuation.columns else df_valuation
        df_liquidity_filtered = df_liquidity[df_liquidity['quarter'] == quarter].copy() if 'quarter' in df_liquidity.columns else df_liquidity
        df_coverage_filtered = df_coverage[df_coverage['quarter'] == quarter].copy() if 'quarter' in df_coverage.columns else df_coverage
        df_trust_filtered = df_trust[df_trust['quarter'] == quarter].copy() if 'quarter' in df_trust.columns else df_trust
    else:
        df_composite_filtered = df_composite
        df_valuation_filtered = df_valuation
        df_liquidity_filtered = df_liquidity
        df_coverage_filtered = df_coverage
        df_trust_filtered = df_trust

    # Get company data
    company_data = df_composite_filtered[df_composite_filtered['ticker'] == ticker].iloc[0]

    # Calculate key metrics
    irci_score = company_data.get('irci_composite_pct', 0)
    peer_rank = int(df_composite_filtered['irci_composite_pct'].rank(ascending=False)[
        df_composite_filtered['ticker'] == ticker
    ].iloc[0])
    total_peers = len(df_composite_filtered)

    dial_scores = {
        'valuation': company_data.get('valuation_pct', 0),
        'liquidity': company_data.get('liquidity_pct', 0),
        'coverage': company_data.get('coverage_pct', 0),
        'trust': company_data.get('sentiment_pct', 0)
    }

    # Get dollar per point if available
    dollar_per_point = None
    if dollar_value_df is not None and not dollar_value_df.empty:
        company_dv = dollar_value_df[dollar_value_df['ticker'] == ticker]
        if not company_dv.empty:
            dollar_per_point = company_dv['company_$/irci_pt'].iloc[0]

    # === COVER PAGE ===
    pdf.add_cover_page(irci_score, peer_rank, total_peers, dial_scores, dollar_per_point)

    # === PAGE 2: COMPETITIVE POSITIONING & DIAL ANALYSIS ===
    pdf.add_page()
    pdf.add_competitive_matrix(df_composite_filtered, ticker, dial_scores)

    # Risk Flags (on same page as competitive positioning)
    pdf.ln(3)
    pdf.add_risk_flags(dial_scores, ticker, df_composite_filtered)

    # === PAGE 3: 90-DAY ACTION PLAN (includes playbook summary) ===
    pdf.add_page()
    pdf.add_90_day_action_plan(playbook, ticker, dial_scores, dollar_per_point)

    # === PAGE 4: ROI ANALYSIS (only if dollar value available) ===
    if dollar_per_point and dollar_per_point > 0:
        pdf.add_page()
        pdf.add_roi_section(ticker, dial_scores, dollar_per_point, playbook)

    # === MEDIA SENTIMENT (if available) ===
    if news_df is not None and not news_df.empty and 'sentiment_score' in news_df.columns:
        pdf.add_page()
        pdf.chapter_title('MEDIA SENTIMENT ANALYSIS')

        ticker_news = news_df[news_df['ticker'] == ticker].copy()

        if not ticker_news.empty:
            total_articles = len(ticker_news)
            avg_sentiment = ticker_news['sentiment_score'].mean()
            positive_count = len(ticker_news[ticker_news['sentiment_score'] > 0.1])
            negative_count = len(ticker_news[ticker_news['sentiment_score'] < -0.1])

            pdf.section_title('Sentiment Overview')
            pdf.body_text(
                f"Total Articles: {total_articles}\n"
                f"Average Sentiment: {avg_sentiment:+.3f}\n"
                f"Positive: {positive_count} ({positive_count/total_articles*100:.0f}%) | "
                f"Negative: {negative_count} ({negative_count/total_articles*100:.0f}%)"
            )

            # Top positive
            pdf.section_title('Most Positive Coverage')
            positive_news = ticker_news[ticker_news['sentiment_score'] > 0].sort_values(
                'sentiment_score', ascending=False
            ).head(3)

            for _, article in positive_news.iterrows():
                headline = article.get('headline', 'No headline')[:100]
                pdf.set_font('Arial', '', 9)
                pdf.safe_multi_cell(0, 5, f"+ {headline}")

            # Top negative
            pdf.ln(3)
            pdf.section_title('Most Negative Coverage')
            negative_news = ticker_news[ticker_news['sentiment_score'] < 0].sort_values(
                'sentiment_score', ascending=True
            ).head(3)

            for _, article in negative_news.iterrows():
                headline = article.get('headline', 'No headline')[:100]
                pdf.set_font('Arial', '', 9)
                pdf.safe_multi_cell(0, 5, f"- {headline}")

    # === FINAL PAGE: METHODOLOGY & DISCLAIMER ===
    pdf.add_page()
    pdf.chapter_title('METHODOLOGY & DISCLAIMER')

    # Condensed IRCI Framework
    pdf.section_title('IRCI Framework')
    pdf.body_text(
        "IRCI measures IR effectiveness across four dials: Valuation (market perception vs fundamentals), "
        "Liquidity (trading activity), Coverage (media attention), and Trust (sentiment). "
        "Each dial is scored 0-100% based on percentile ranking within the peer group."
    )

    # Condensed Dollar Value Methodology
    pdf.section_title('Dollar Value Methodology')
    pdf.body_text(
        "We regress Enterprise Value against IRCI scores across your peer group, then scale by R-squared "
        "to be conservative. Formula: Company $/IRCI = (Company EV / Peer Mean EV) x Slope x R-squared. "
        "R-squared scaling ensures we only attribute the portion of value explained by IRCI."
    )

    # Peer Group
    pdf.section_title('Peer Group')
    unique_tickers = df_composite_filtered['ticker'].unique().tolist()
    pdf.body_text(f"Analysis includes {len(unique_tickers)} companies: {', '.join(sorted(unique_tickers))}")

    pdf.ln(3)
    pdf.section_title('Legal Disclaimer')
    pdf.set_font('Arial', 'I', 8)
    pdf.body_text(
        "NOT FINANCIAL ADVICE: IRCI is for informational and educational purposes only. It does not "
        "constitute financial, investment, or trading advice.\n\n"
        "NO GUARANTEES: Past performance is not indicative of future results. IRCI scores may contain "
        "errors. No representation is made that any investment will achieve similar results.\n\n"
        "DO YOUR OWN RESEARCH: Conduct your own due diligence, consult a qualified financial advisor, "
        "and review official company filings before making investment decisions.\n\n"
        "LIMITATION OF LIABILITY: IRCI and its creators shall not be held liable for any losses or "
        "damages arising from use of this platform. Use is entirely at your own risk.\n\n"
        "DATA SOURCES: Analysis is based on publicly available information. We cannot guarantee "
        "completeness or timeliness of all data."
    )

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
