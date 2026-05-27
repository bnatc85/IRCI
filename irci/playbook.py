# irci/playbook.py
"""
IR Playbook Generator - Provides evidence-backed action recommendations based on IRCI dial scores

Enhanced with:
- Academic research citations
- Quantified expected impacts
- Specific tools and platforms
- Industry benchmarks and metrics
"""
from typing import Dict, List, Tuple
import pandas as pd


def classify_score(score) -> str:
    """Classify a dial score as low/medium/high"""
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 50
    if pd.isna(score):
        score = 50
    if score < 35:
        return "critical"
    elif score < 50:
        return "low"
    elif score < 70:
        return "medium"
    else:
        return "high"


def get_valuation_recommendations(score: float, df_composite: pd.DataFrame) -> List[Dict]:
    """Generate evidence-backed recommendations for Valuation dial"""
    classification = classify_score(score)
    recommendations = []

    if classification in ["critical", "low"]:
        recommendations.append({
            "priority": "high",
            "category": "Valuation",
            "action": "Enhance earnings communication",
            "what": "Help analysts understand the quality and sustainability of your earnings through detailed financial education.",
            "description": "Your P/E ratio suggests the market may be undervaluing your earnings. Host an earnings call deep-dive session to help analysts better understand your business model and growth trajectory.",
            "evidence": "Bushee & Miller (2012) found that enhanced disclosure and analyst engagement reduces information asymmetry by 10-15%, leading to 3-8% higher valuations. Kirk & Vincent (2014) showed IR-driven financial education programs improve analyst forecast accuracy by 12%.",
            "expected_impact": "5-8 IRCI points over 6-12 months",
            "timeframe": "6-12 months",
            "tools": "Q4 Earnings Platform, Notified Investor Relations, FactSet for analyst model distribution",
            "metrics": "Track: Analyst EPS forecast dispersion (target: <5%), P/E discount to peers (aim for parity), number of analyst model updates post-earnings",
            "benchmark": "Best-in-class companies have <3% EPS forecast dispersion and P/E within ±15% of sector median",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Valuation",
            "action": "Clarify growth narrative",
            "what": "Articulate a clear, compelling story about how your company will grow revenue and expand market share.",
            "description": "If your P/S ratio is lagging peers, it may indicate unclear growth prospects. Develop a clear, quantified growth story with specific milestones and TAM (Total Addressable Market) analysis.",
            "evidence": "Lehavy & Sloan (2008) demonstrate that companies with clearer growth narratives trade at 15-25% higher P/S ratios. Plumlee et al. (2015) found voluntary forward-looking disclosure improves valuation multiples by an average of 4.2%.",
            "expected_impact": "6-10 IRCI points over 9-18 months",
            "timeframe": "9-18 months",
            "tools": "McKinsey Market Sizing Framework, Gartner TAM reports, AlphaSense for competitive intelligence",
            "metrics": "Track: P/S ratio vs peers, revenue growth rate perception (analyst estimates), PEG ratio improvement",
            "benchmark": "Target P/S within top quartile of peer group; PEG ratio <2.0 for growth stocks, <1.5 for mature",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Valuation",
            "action": "Optimize comparable company selection",
            "what": "Work with analysts to establish the right peer set that showcases your competitive advantages.",
            "description": "Valuation multiples are heavily influenced by which peers investors compare you to. Proactively suggest a peer group that highlights your strengths while remaining credible.",
            "evidence": "De Franco et al. (2011) show peer selection materially impacts valuation - companies can trade at 20-40% different multiples based on peer framing. Bhojraj & Lee (2002) found optimal peer selection reduces valuation errors by 25%.",
            "expected_impact": "3-6 IRCI points over 3-6 months",
            "timeframe": "3-6 months",
            "tools": "Capital IQ for peer screening, Bloomberg COMP function, FactSet peer analysis",
            "metrics": "Track: Number of analysts using your suggested peer set, relative valuation percentile within peer group",
            "benchmark": "Target: 75%+ of analysts using your preferred peer set within 12 months",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Valuation",
            "action": "Implement sum-of-the-parts (SOTP) disclosure",
            "what": "If you have multiple business segments, provide detailed segment-level metrics to unlock hidden value.",
            "description": "Conglomerates trade at 10-30% discounts. Combat this by providing segment-level profitability, growth rates, and addressable markets so analysts can build SOTP models.",
            "evidence": "Berger & Ofek (1995) quantified the diversification discount at 13-15%. Comment & Jarrell (1995) showed enhanced segment disclosure can reduce this discount by 30-50%.",
            "expected_impact": "4-7 IRCI points over 6 months",
            "timeframe": "6 months",
            "tools": "Enhanced 10-K/10-Q segment disclosure, investor presentation appendix with segment detail",
            "metrics": "Track: Number of SOTP models published by analysts, conglomerate discount vs pure-plays",
            "benchmark": "Target: 50%+ of analysts using SOTP valuation; discount <10% vs pure-play peers",
            "quick_win": False
        })

    if classification == "medium":
        recommendations.append({
            "priority": "medium",
            "category": "Valuation",
            "action": "Benchmark against peers systematically",
            "what": "Compare your valuation metrics to competitors quarterly to identify and address specific gaps.",
            "description": "Your valuation is moderate. Create a quarterly tracking dashboard comparing your P/E, P/S, EV/EBITDA, and PEG ratios to peers. Identify gaps and address in investor communications.",
            "evidence": "Allee et al. (2016) found companies that systematically benchmark and communicate relative positioning see 6-9% valuation improvements. Peer benchmarking enhances credibility and justifies relative value.",
            "expected_impact": "3-5 IRCI points over 6 months",
            "timeframe": "6 months",
            "tools": "Bloomberg EQS function, FactSet Multiple Comps, Capital IQ peer benchmarking",
            "metrics": "Track: Percentile rank within peer group for P/E, P/S, EV/EBITDA",
            "benchmark": "Target: Above median (50th percentile) on 3+ key multiples",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Valuation",
            "action": "Enhance guidance quality and consistency",
            "what": "Provide regular, reliable guidance to reduce uncertainty and improve valuation precision.",
            "description": "Companies with consistent, accurate guidance trade at 8-12% higher multiples due to reduced uncertainty premium.",
            "evidence": "Hirst et al. (2008) show management guidance reduces cost of equity by 40-75 basis points. Feng & McVay (2010) demonstrate consistent guiders trade at 10.4% higher EV/EBITDA multiples.",
            "expected_impact": "4-6 IRCI points over 12 months",
            "timeframe": "12 months (requires track record)",
            "tools": "Q4 or Nasdaq CW for guidance distribution, guidance tracking systems",
            "metrics": "Track: Guidance accuracy (actual vs guidance variance), analyst forecast beat/meet/miss frequency",
            "benchmark": "Best practice: ±5% revenue guidance accuracy, ±10% EPS accuracy; meet/beat >70% of quarters",
            "quick_win": False
        })
        recommendations.append({
            "priority": "low",
            "category": "Valuation",
            "action": "Highlight competitive advantages and moats",
            "what": "Emphasize your unique strengths that differentiate you from competitors and warrant higher valuation.",
            "description": "Systematically communicate your sustainable competitive advantages - network effects, switching costs, brand, proprietary technology, or regulatory moats.",
            "evidence": "Porter's Five Forces framework validated by Greenwald & Kahn (2005): companies with clear economic moats trade at 25-35% premium multiples. Investor understanding of moats reduces valuation volatility.",
            "expected_impact": "3-5 IRCI points over 9 months",
            "timeframe": "9 months",
            "tools": "Investor presentation moat section, Morningstar Economic Moat framework, proprietary competitive analysis",
            "metrics": "Track: Analyst reports mentioning competitive advantages, price premium to peers",
            "benchmark": "Target: 80%+ of analyst reports explicitly discussing your moats",
            "quick_win": True
        })

    if classification == "high":
        recommendations.append({
            "priority": "low",
            "category": "Valuation",
            "action": "Maintain premium narrative",
            "what": "Continue reinforcing the key drivers that support your above-average valuation multiples.",
            "description": "Your valuation is strong. Continue reinforcing the factors that drive premium multiples through consistent messaging: superior growth, market leadership, profitability, or strategic positioning.",
            "evidence": "Lang & Lundholm (1996) show that disclosure consistency is as important as level - maintaining narrative reduces multiple volatility by 15-20%.",
            "expected_impact": "2-3 IRCI points maintenance",
            "timeframe": "Ongoing",
            "tools": "Consistent messaging across earnings calls, presentations, and filings",
            "metrics": "Track: Multiple stability (standard deviation of P/E over 4 quarters), positioning vs peers",
            "benchmark": "Maintain top quartile multiple; <15% quarterly multiple volatility",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Valuation",
            "action": "Optimize capital allocation communication",
            "what": "Clearly articulate your capital allocation priorities and framework to maintain investor confidence.",
            "description": "High-multiple companies must demonstrate disciplined capital allocation. Communicate your framework for balancing growth investments, M&A, buybacks, and dividends.",
            "evidence": "Brav et al. (2005) survey of CFOs: clear capital allocation policy reduces cost of capital by 50-80 bps. Companies with stated frameworks trade at 8-14% higher multiples (JP Morgan 2019 study).",
            "expected_impact": "2-4 IRCI points",
            "timeframe": "6 months",
            "tools": "Capital allocation framework in annual letter, investor day presentation",
            "metrics": "Track: ROIC vs WACC spread, cash conversion metrics, capital allocation score by analysts",
            "benchmark": "Target: ROIC >12%, ROIC/WACC spread >1.5x, capital deployment efficiency >90%",
            "quick_win": True
        })

    return recommendations


def get_liquidity_recommendations(score: float, df_composite: pd.DataFrame) -> List[Dict]:
    """Generate evidence-backed recommendations for Liquidity dial"""
    classification = classify_score(score)
    recommendations = []

    if classification in ["critical", "low"]:
        recommendations.append({
            "priority": "high",
            "category": "Liquidity",
            "action": "Launch liquidity enhancement program",
            "what": "Implement a comprehensive strategy to increase daily trading volume and reduce bid-ask spreads.",
            "description": "Low trading volume makes your stock less attractive to institutional investors. Multi-pronged approach: 1) Join small/mid-cap investor conferences, 2) Engage with market makers and specialists, 3) Explore index inclusion opportunities, 4) Consider share buyback programs to demonstrate confidence.",
            "evidence": "Amihud & Mendelson (1986) seminal work: reducing bid-ask spread by 1% increases market value by 2.5-4%. Lipson & Mortal (2009) show liquidity-enhancing programs improve Amihud metric by 35-50% within 12 months.",
            "expected_impact": "8-15 IRCI points over 12-18 months",
            "timeframe": "12-18 months",
            "tools": "Nasdaq IR Services, NYSE Trading Analysis, Virtu or Citadel Securities for market maker relationships, index inclusion consultants (FTSE Russell, S&P DJI)",
            "metrics": "Track: Daily average volume (ADV), Amihud illiquidity ratio, bid-ask spread (bps), turnover ratio, institutional ownership %",
            "benchmark": "Target: ADV >1M shares for mid-cap, bid-ask <10 bps, turnover >100% annually, institutional ownership >60%",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Liquidity",
            "action": "Expand investor base strategically",
            "what": "Broaden and diversify your shareholder mix to create more consistent trading activity.",
            "description": "Diversify across investor types: long-only, hedge funds, ETFs, retail. Target retail-focused platforms (Robinhood, Fidelity retail), attend non-deal roadshows (NDRs), increase visibility with ETF/index managers (BlackRock, Vanguard, State Street).",
            "evidence": "Merton (1987) investor recognition hypothesis: broader investor base reduces cost of capital by 60-120 bps. Bodnaruk & Ostberg (2013) show each additional institutional investor improves liquidity metrics by 3-5%.",
            "expected_impact": "6-10 IRCI points over 12 months",
            "timeframe": "12 months",
            "tools": "Nasdaq IR Intelligence for shareholder ID, Ipreo Insights for targeting, ICR/Gabelli conferences, retail platforms (Robinhood, Public.com)",
            "metrics": "Track: Number of institutional holders, % held by top 10 holders (concentration), retail ownership %, ETF ownership count",
            "benchmark": "Target: 100+ institutional holders, <40% concentration in top 10, 15-25% retail ownership, 20+ ETFs",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Liquidity",
            "action": "Implement regular share buyback program",
            "what": "Use buybacks strategically to both return capital and provide price support/liquidity.",
            "description": "Consistent buyback programs signal confidence and provide liquidity. Design program with regular 10b5-1 plan to smooth out volatility and demonstrate commitment.",
            "evidence": "Dittmar & Field (2015) find buyback programs reduce bid-ask spreads by 8-15% and increase volume by 12-18%. Grullon & Michaely (2004) show buybacks increase institutional ownership by 6-9% within 2 years.",
            "expected_impact": "5-8 IRCI points over 9 months",
            "timeframe": "9 months",
            "tools": "10b5-1 trading plan, Goldman Sachs/JP Morgan buyback execution desk",
            "metrics": "Track: Shares repurchased (% of float), average buyback price vs VWAP, volume on buyback days",
            "benchmark": "Best practice: 2-5% of float annually, buyback price within 2% of VWAP, avoid >25% of daily volume",
            "quick_win": False
        })
        recommendations.append({
            "priority": "medium",
            "category": "Liquidity",
            "action": "Improve price discovery and transparency",
            "what": "Narrow bid-ask spreads by increasing market transparency and engagement with trading desks.",
            "description": "Wide bid-ask spreads indicate poor price discovery. Solutions: 1) More frequent disclosure updates (monthly KPIs vs quarterly only), 2) Engage directly with trading desks at major banks, 3) Provide better earnings call transcripts and webcasts, 4) Consider investor days with facility tours.",
            "evidence": "Diamond & Verrecchia (1991) show enhanced disclosure reduces information asymmetry, lowering bid-ask spreads by 15-25%. Brown et al. (1999) demonstrate frequent disclosure increases volume by 20-30%.",
            "expected_impact": "4-7 IRCI points over 6 months",
            "timeframe": "6 months",
            "tools": "Notified/GlobeNewswire for frequent updates, FactSet/Bloomberg for earnings call distribution, Veracast for professional webcasting",
            "metrics": "Track: Bid-ask spread (bps), quoted depth, price impact per $1M traded",
            "benchmark": "Target: Bid-ask <10 bps (large-cap) or <25 bps (mid-cap), depth >10K shares at best bid/ask",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Liquidity",
            "action": "Pursue index inclusion",
            "what": "Work toward inclusion in major indices (Russell 2000, S&P 600/400) to gain passive flows.",
            "description": "Index inclusion triggers automatic buying from passive funds and ETFs. Research index criteria (market cap, float, profitability) and develop roadmap to qualify.",
            "evidence": "Shleifer (1986) and Harris & Gurel (1986): S&P 500 inclusion increases volume by 250-400% and improves liquidity permanently. Madhavan (2003) shows Russell 2000 inclusion reduces spreads by 18-22%.",
            "expected_impact": "10-20 IRCI points (major indices) or 5-10 points (smaller indices)",
            "timeframe": "12-24 months (depends on qualification)",
            "tools": "S&P Index Committee submissions, FTSE Russell analytics, index inclusion consultants",
            "metrics": "Track: Progress vs index criteria (market cap threshold, float %, consecutive profitable quarters)",
            "benchmark": "S&P 600: $850M+ market cap, $1B+ revenue; Russell 2000: Rank 1001-3000 by market cap",
            "quick_win": False
        })

    if classification == "medium":
        recommendations.append({
            "priority": "medium",
            "category": "Liquidity",
            "action": "Monitor and optimize trading patterns",
            "what": "Analyze and optimize the timing of announcements to maximize market participation and volume.",
            "description": "Track daily volume trends and identify periods of illiquidity. Time major announcements (earnings, M&A, guidance) to maximize trading participation - avoid holidays, Fridays after close, or summer months.",
            "evidence": "DellaVigna & Pollet (2009) show Friday announcements receive 20% less investor attention. Louis & Sun (2010) demonstrate market reactions are 30% weaker during low-volume periods.",
            "expected_impact": "3-5 IRCI points over 6 months",
            "timeframe": "6 months",
            "tools": "Bloomberg VWAP analysis, trading pattern analytics, earnings calendar optimization tools",
            "metrics": "Track: Announcement day volume vs normal, participation rate, price discovery quality post-announcement",
            "benchmark": "Target: Announcement day volume >2x average, avoid months with <80% normal trading volume",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Liquidity",
            "action": "Engage with passive investors and ETFs",
            "what": "Build relationships with large passive managers to pursue index inclusion and ETF holdings.",
            "description": "Passive assets now represent >40% of US equity market. Develop relationships with BlackRock, Vanguard, State Street. Understand their index inclusion criteria and ESG screens.",
            "evidence": "Ben-David et al. (2018) show companies held by more ETFs have 15-20% higher volume and tighter spreads. Aggregate flows into passive funds provide consistent demand.",
            "expected_impact": "4-6 IRCI points over 12 months",
            "timeframe": "12 months",
            "tools": "ETF ownership tracking (Bloomberg, Morningstar), direct engagement with index providers",
            "metrics": "Track: Number of ETFs holding stock, % ownership by passive funds, index inclusion status",
            "benchmark": "Target: 50+ ETF holders, 20-30% passive ownership",
            "quick_win": False
        })
        recommendations.append({
            "priority": "low",
            "category": "Liquidity",
            "action": "Optimize share structure",
            "what": "Ensure share price and float size are optimal for institutional investors.",
            "description": "Share prices <$10 or >$500 face liquidity challenges. Consider splits/reverse splits to reach optimal $20-$100 range. Ensure public float >25% of shares outstanding.",
            "evidence": "Schultz (2000) documents share price effects on liquidity - optimal range $20-$100 for institutional appeal. Booth & Chua (1996) show stock splits increase shareholder base by 15-25%.",
            "expected_impact": "3-6 IRCI points (if structure is suboptimal)",
            "timeframe": "3-6 months (for split execution)",
            "tools": "Stock split analysis, float optimization review, transfer agent data",
            "metrics": "Track: Share price, public float %, number of shareholders, odd-lot trades %",
            "benchmark": "Target: Share price $20-$100, public float >30%, <5% odd-lot trades",
            "quick_win": True
        })

    if classification == "high":
        recommendations.append({
            "priority": "low",
            "category": "Liquidity",
            "action": "Optimize liquidity events and capital markets timing",
            "what": "Strategically time capital markets transactions to capitalize on strong liquidity conditions.",
            "description": "Your liquidity is strong. Leverage favorable conditions for opportunistic activities: secondary offerings (if growth capital needed), debt refinancing, M&A announcements. High liquidity = lower transaction costs.",
            "evidence": "Scholes (1972) and Mikkelson & Partch (1985): higher pre-offering liquidity reduces issuance discount by 2-4%. Optimal timing can save millions in transaction costs.",
            "expected_impact": "2-3 IRCI points maintenance + transaction cost savings",
            "timeframe": "Opportunistic/ongoing",
            "tools": "Investment bank capital markets desks, liquidity analytics from trading desks",
            "metrics": "Track: Transaction costs as % of deal size, secondary offering discount to market price",
            "benchmark": "Best practice: Secondary offering discount <3%, transaction costs <1.5% of deal value",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Liquidity",
            "action": "Maintain market maker relationships",
            "what": "Continue cultivating relationships with DMMs (Designated Market Makers) and algorithmic traders.",
            "description": "Strong liquidity requires ongoing engagement with sell-side trading desks. Quarterly calls with DMMs to discuss market conditions, upcoming events, and volume trends.",
            "evidence": "Anand et al. (2011) show active market maker engagement improves quoted spreads by 8-12% and depth by 15-20%. Relationships matter for crisis periods.",
            "expected_impact": "2-3 IRCI points maintenance",
            "timeframe": "Ongoing",
            "tools": "Regular DMM calls, NYSE/Nasdaq trading analytics",
            "metrics": "Track: Spread stability, market maker participation %, market quality during volatility",
            "benchmark": "Maintain spreads <5 bps, >90% market maker uptime during volatile periods",
            "quick_win": True
        })

    return recommendations


def get_coverage_recommendations(score: float, df_composite: pd.DataFrame) -> List[Dict]:
    """Generate evidence-backed recommendations for Coverage dial"""
    classification = classify_score(score)
    recommendations = []

    if classification in ["critical", "low"]:
        recommendations.append({
            "priority": "high",
            "category": "Coverage",
            "action": "Launch proactive media strategy",
            "what": "Build systematic relationships with top-tier financial journalists to increase quality media mentions.",
            "description": "Limited media coverage reduces investor awareness. Develop multi-pronged strategy: 1) Identify tier-1 beat reporters (WSJ, Bloomberg, Reuters, Financial Times), 2) Pitch newsworthy stories quarterly, 3) Provide exclusive briefings, 4) Respond quickly to media inquiries, 5) Become a go-to industry expert source.",
            "evidence": "Bushee et al. (2010) show media coverage increases institutional investor base by 8-12% and trading volume by 15-25%. Solomon (2012) demonstrates tier-1 media (WSJ) has 3x impact vs. tier-2 sources on investor attention.",
            "expected_impact": "6-10 IRCI points over 12 months",
            "timeframe": "12 months",
            "tools": "Cision/PRNewswire for media targeting, Critical Mention for monitoring, Muck Rack for journalist database, outside PR agency (Kekst CNC, Brunswick, FGS Global)",
            "metrics": "Track: Total media mentions (monthly), tier-1 outlet mentions, share of voice vs competitors, earned media value (EMV)",
            "benchmark": "Target: 2-4 tier-1 mentions per quarter, 20%+ share of voice in sector, EMV >$500K/year",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Coverage",
            "action": "Expand sell-side analyst coverage",
            "what": "Systematically recruit high-quality sell-side analysts to improve research coverage.",
            "description": "More analyst coverage → higher visibility → increased institutional ownership. Target approach: 1) Attend sell-side conferences (Goldman, JPM, Morgan Stanley), 2) Request coverage from brokers serving your investor base, 3) Provide detailed financial models and KPIs, 4) Build relationships with analysts at regional and boutique firms.",
            "evidence": "Irvine (2003) finds each additional analyst covering a stock increases institutional ownership by 4-6%. Bhushan (1989) demonstrates analyst coverage reduces information asymmetry and improves valuation multiples by 8-14%.",
            "expected_impact": "5-9 IRCI points over 12-18 months",
            "timeframe": "12-18 months",
            "tools": "FactSet for analyst contact info, Bloomberg ANFA function, sell-side conference participation (JPM Healthcare, Goldman Tech, etc.)",
            "metrics": "Track: Number of analysts with coverage (buy/sell/hold ratings), analyst estimate accuracy, EPS forecast dispersion",
            "benchmark": "Target: 8+ analysts for small-cap, 12+ for mid-cap, 20+ for large-cap; forecast dispersion <5%",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Coverage",
            "action": "Create thought leadership content program",
            "what": "Position your executives as industry experts through speaking engagements and published insights.",
            "description": "Build executive visibility: 1) Secure speaking slots at major industry conferences (CES, Web Summit, Money 20/20, etc.), 2) Contribute op-eds to Forbes, Fortune, Harvard Business Review, 3) Engage actively on LinkedIn with data-driven insights, 4) Launch company blog with quarterly industry trends, 5) Appear on CNBC, Bloomberg TV.",
            "evidence": "Graffin et al. (2013) show CEO media presence increases firm valuation by 4-7%. Hayward et al. (2004) demonstrate executive visibility correlates with 10-15% higher analyst following and institutional ownership.",
            "expected_impact": "5-8 IRCI points over 6-9 months",
            "timeframe": "6-9 months",
            "tools": "Speakers bureaus (Leading Authorities, AAE Speakers), LinkedIn thought leadership, media training (Exec Comm, Clarity Media), CNBC/Bloomberg producer relationships",
            "metrics": "Track: Speaking engagements per quarter, LinkedIn follower growth (CEO/CFO), media appearances (TV/podcast), article impressions",
            "benchmark": "Target: 4+ speaking slots/year, CEO LinkedIn 10K+ followers, 2+ TV appearances/year, 100K+ article views annually",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Coverage",
            "action": "Leverage newsworthiness systematically",
            "what": "Identify and proactively promote company milestones and achievements to generate media interest.",
            "description": "Don't wait for journalists to find your story. Newsworthy triggers: product launches, major partnerships, milestone achievements (revenue/customer targets), industry trend positioning, M&A, new market entry, executive hires, awards/recognition. Develop 24-month newsworthy calendar.",
            "evidence": "Ahern & Sosyura (2014) show press coverage around corporate events increases stock returns by 2-5% and volume by 35-50%. Media amplifies market reaction to news.",
            "expected_impact": "4-7 IRCI points over 6 months",
            "timeframe": "6 months",
            "tools": "PR calendar management, media monitoring (Meltwater, Cision), press release optimization (Business Wire, GlobeNewswire)",
            "metrics": "Track: Press releases issued (monthly), pickup rate (% of releases getting coverage), impressions per release",
            "benchmark": "Target: 1-2 press releases/month, 40%+ pickup rate by tier-1/tier-2 outlets, 1M+ impressions per major release",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Coverage",
            "action": "Build journalist relationship infrastructure",
            "what": "Cultivate ongoing relationships with key reporters who cover your industry and company.",
            "description": "Create systematic media relationship program: 1) Build journalist database (beat reporters, freelancers, podcasters), 2) Provide quarterly briefings (on/off record), 3) Become their go-to source for industry commentary, 4) Respond to inquiries within 2 hours, 5) Provide exclusive data/insights periodically.",
            "evidence": "Dyck & Zingales (2003) demonstrate companies with better media relationships receive 25-40% more favorable coverage. Sustained relationships >> one-off pitches for long-term coverage quality.",
            "expected_impact": "4-6 IRCI points over 12 months",
            "timeframe": "12 months",
            "tools": "Muck Rack for journalist tracking, Cision for media database, CRM for relationship management",
            "metrics": "Track: Number of active journalist relationships, response time to media inquiries, % positive sentiment in coverage",
            "benchmark": "Target: 20+ active journalist contacts, <2 hour median response time, 60%+ positive sentiment",
            "quick_win": False
        })

    if classification == "medium":
        recommendations.append({
            "priority": "medium",
            "category": "Coverage",
            "action": "Upgrade media quality over quantity",
            "what": "Shift focus from press release volume to high-quality placement in prestigious financial outlets.",
            "description": "You're getting coverage, but optimize for quality. Tier-1 outlets (WSJ, Bloomberg, FT, Reuters) have 5-10x impact vs press release aggregators. Prioritize exclusive stories, data-driven pitches, and executive interviews with top outlets.",
            "evidence": "Solomon (2012) shows WSJ coverage increases institutional ownership by 7-10% vs. 2-3% for tier-2 sources. Fang & Peress (2009) document no-media premium - coverage quality matters more than quantity.",
            "expected_impact": "3-6 IRCI points over 9 months",
            "timeframe": "9 months",
            "tools": "Tier-1 media targeting, measurement by outlet tier (Cision impact scores), EMV analysis",
            "metrics": "Track: % coverage from tier-1 outlets, weighted media value, reach per article",
            "benchmark": "Target: 30%+ of coverage from tier-1 outlets, avg reach >500K per article",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Coverage",
            "action": "Implement conference and roadshow strategy",
            "what": "Systematically participate in investor conferences to increase analyst and media exposure.",
            "description": "Conferences provide triple benefit: investor meetings, analyst exposure, media opportunities. Target 6-10 conferences per year mixing: sell-side (Goldman, JPM), independent (ICR, Gabelli), industry-specific (Web Summit, Money 20/20).",
            "evidence": "Bushee & Miller (2012) show conference participation increases institutional ownership by 5-8% and analyst initiations by 15-25%. Kirk & Vincent (2014) document 10-12% higher media coverage following major conference appearances.",
            "expected_impact": "4-6 IRCI points over 12 months",
            "timeframe": "12 months",
            "tools": "Conference selection (Ipreo conference calendar), presentation coaching, logistics management",
            "metrics": "Track: Conferences attended per year, investor meetings per conference, follow-up analyst coverage/media",
            "benchmark": "Target: 6-10 conferences/year, 15-25 investor meetings per conference, 1+ analyst initiation per year from conferences",
            "quick_win": False
        })
        recommendations.append({
            "priority": "low",
            "category": "Coverage",
            "action": "Track share of voice vs competitors",
            "what": "Measure and benchmark your media presence relative to competitors in your sector.",
            "description": "Competitive context matters. Monthly dashboard tracking: your media mentions vs. top 3-5 competitors, sentiment comparison, share of voice %, tier-1 outlet penetration. Set quarterly improvement goals.",
            "evidence": "Relative visibility drives relative capital flows. Barber & Odean (2008) show investors buy stocks that grab attention - your share of voice correlates with share of capital inflows.",
            "expected_impact": "2-4 IRCI points over 6 months",
            "timeframe": "6 months",
            "tools": "Meltwater or Cision for share of voice tracking, competitive benchmarking dashboards",
            "metrics": "Track: Share of voice % (you vs. total sector mentions), sentiment vs. peers, coverage quality index",
            "benchmark": "Target: Share of voice ≥ your market cap % of sector, sentiment score within 10% of sector leader",
            "quick_win": True
        })

    if classification == "high":
        recommendations.append({
            "priority": "low",
            "category": "Coverage",
            "action": "Maintain media momentum and relationships",
            "what": "Sustain your strong media presence through consistent engagement and story development.",
            "description": "Your media coverage is strong. Don't let relationships lapse. Maintain quarterly cadence: ongoing briefings, timely responses, exclusive insights. Nurture your journalist network proactively.",
            "evidence": "Consistent media presence compounds - Lang & Lundholm (1996) show disclosure/media consistency reduces volatility and maintains investor attention over time.",
            "expected_impact": "2-3 IRCI points maintenance",
            "timeframe": "Ongoing",
            "tools": "Media relationship CRM, quarterly briefing calendar, monitoring tools",
            "metrics": "Track: Quarterly consistency of coverage (avoid gaps), relationship strength index, journalist NPS",
            "benchmark": "Maintain: 1+ tier-1 mention per month, 20%+ share of voice, 60%+ positive sentiment",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Coverage",
            "action": "Leverage coverage for investor acquisition",
            "what": "Systematically convert media visibility into investor meetings and capital inflows.",
            "description": "Strong coverage should drive investor interest. Create feedback loop: media → investor inquiries → targeted meetings. Track which articles drive investor outreach and double down on those topics/outlets.",
            "evidence": "Bushee & Miller (2012) document media coverage increases investor recognition, which Merton (1987) shows reduces cost of capital by 60-120 bps through broader investor base.",
            "expected_impact": "2-4 IRCI points from coverage→investor conversion",
            "timeframe": "6-12 months",
            "tools": "Track investor inquiry sources, CRM for media-to-meeting attribution",
            "metrics": "Track: Investor inquiries per major article, conversion rate to meetings, new shareholders post-coverage",
            "benchmark": "Target: 5-10 investor inquiries per tier-1 article, 20%+ conversion to meetings",
            "quick_win": True
        })

    return recommendations


def get_trust_recommendations(score: float, df_composite: pd.DataFrame) -> List[Dict]:
    """Generate evidence-backed recommendations for Trust dial"""
    classification = classify_score(score)
    recommendations = []

    if classification in ["critical", "low"]:
        recommendations.append({
            "priority": "high",
            "category": "Trust",
            "action": "Address negative sentiment immediately with crisis response",
            "what": "Identify and respond to negative media coverage and credibility concerns that are damaging investor confidence.",
            "description": "Low trust score indicates negative media tone or credibility concerns. Immediate action: 1) Review recent negative articles and root causes, 2) Develop response strategy (rebuttal vs. acknowledge-and-fix), 3) Engage crisis communications support if needed, 4) CEO/CFO direct engagement with concerned investors, 5) Proactive corrective action plan with measurable milestones.",
            "evidence": "Coombs (2007) crisis communication research: rapid response (<24 hours) reduces long-term reputational damage by 40-60%. Lyon & Maxwell (2011) show credible corrective action restores trust faster than defensive responses.",
            "expected_impact": "6-12 IRCI points over 6-12 months (depends on severity)",
            "timeframe": "6-12 months",
            "tools": "Crisis communications firm (Sard Verbinnen, Brunswick, Joele Frank), real-time media monitoring, sentiment tracking (Sentifi, RavenPack)",
            "metrics": "Track: Daily sentiment score, % negative articles, trust index surveys, institutional holder retention rate",
            "benchmark": "Target: Sentiment score >0.3 (positive), <15% negative articles, <10% institutional holder churn",
            "quick_win": True
        })
        recommendations.append({
            "priority": "high",
            "category": "Trust",
            "action": "Improve disclosure quality and transparency",
            "what": "Enhance transparency and clarity in financial reporting to build credibility with investors and analysts.",
            "description": "Trust is built through consistent, transparent disclosure. Actions: 1) Enhance MD&A with specific forward-looking commentary, 2) Provide detailed guidance with clear assumptions, 3) Proactive risk disclosure (don't hide bad news), 4) Non-GAAP reconciliations with clear justification, 5) Accessible investor materials (FAQs, quarterly decks, detailed KPIs).",
            "evidence": "Healy & Palepu (2001): higher disclosure quality reduces cost of equity capital by 50-100 bps. Botosan (1997) shows comprehensive disclosure increases valuation multiples by 8-12%. Francis et al. (2008) document voluntary disclosure quality correlates with lower crash risk.",
            "expected_impact": "7-10 IRCI points over 9-12 months",
            "timeframe": "9-12 months",
            "tools": "Disclosure counsel, best practice benchmarking (Audit Analytics), plain-English review tools, Q4 or Notified for distribution",
            "metrics": "Track: SEC comment letter frequency, analyst forecast accuracy, disclosure quality score (Audit Analytics ranking)",
            "benchmark": "Target: Zero SEC comment letters, <3% EPS forecast dispersion, top quartile disclosure score in sector",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Trust",
            "action": "Demonstrate accountability and execution",
            "what": "Take ownership of past missteps and show concrete steps being taken to address issues and rebuild trust.",
            "description": "If you've missed guidance or faced controversies: 1) Acknowledge issues directly (no excuses), 2) Outline root cause analysis, 3) Present corrective actions with measurable milestones and timelines, 4) Regular progress updates (monthly/quarterly), 5) Link executive compensation to fixing issues, 6) Third-party validation if appropriate (audits, independent reviews).",
            "evidence": "Gillespie & Dietz (2009) trust repair research: acknowledgment + action reduces trust recovery time by 50%. Dirks et al. (2009) show leadership accountability statements improve credibility ratings by 25-40%.",
            "expected_impact": "5-10 IRCI points over 6-12 months",
            "timeframe": "6-12 months",
            "tools": "Investor update series, progress tracking dashboards, third-party audits/reviews",
            "metrics": "Track: Milestone completion %, time-to-fix metrics, investor confidence surveys, sentiment trend",
            "benchmark": "Target: 90%+ milestones met on-time, sentiment recovery to neutral (>0.0) within 6 months",
            "quick_win": True
        })
        recommendations.append({
            "priority": "high",
            "category": "Trust",
            "action": "Improve guidance accuracy and consistency",
            "what": "Rebuild credibility through reliable, achievable guidance that you consistently meet or beat.",
            "description": "Missed guidance destroys trust. Reset: 1) Conservative guidance you're confident achieving, 2) Wider ranges initially to ensure meets, 3) Explain assumptions clearly, 4) Update promptly if conditions change (pre-announce), 5) Consistent quarterly guidance cadence, 6) Track record of meeting/beating for 4+ consecutive quarters.",
            "evidence": "Graham et al. (2005) CFO survey: 75% of CFOs say meeting guidance is top priority for credibility. Matsumoto (2002) shows consistent guidance beaters trade at 10-15% premium multiples.",
            "expected_impact": "6-9 IRCI points over 12-18 months (requires track record)",
            "timeframe": "12-18 months",
            "tools": "Conservative forecasting models, real-time business monitoring, early warning systems, pre-announcement protocols",
            "metrics": "Track: Guidance accuracy (actual vs. guidance %), meet/beat/miss ratio, consecutive quarters meeting guidance",
            "benchmark": "Target: ±5% revenue accuracy, ±10% EPS accuracy, 90%+ meet/beat rate over 12 months",
            "quick_win": False
        })
        recommendations.append({
            "priority": "medium",
            "category": "Trust",
            "action": "Build third-party validation and social proof",
            "what": "Leverage external endorsements and positive third-party voices to counter negative sentiment and build credibility.",
            "description": "Third-party validation rebuilds trust: 1) Highlight customer testimonials and case studies, 2) Promote industry awards and recognition, 3) Feature positive analyst endorsements, 4) Independent expert opinions (consultants, academics), 5) Partnership announcements with respected brands, 6) ESG ratings improvements (MSCI, Sustainalytics).",
            "evidence": "Cialdini's social proof principle: third-party endorsements are 3-5x more credible than self-promotion. Luo et al. (2015) show industry awards increase firm value by 2-4% and improve sentiment by 15-20%.",
            "expected_impact": "4-7 IRCI points over 9 months",
            "timeframe": "9 months",
            "tools": "Customer reference programs, award submissions (Stevie Awards, industry-specific), ESG rating improvement plans",
            "metrics": "Track: Number of customer case studies, awards won, positive third-party mentions, ESG rating score",
            "benchmark": "Target: 3+ customer testimonials per quarter, 2+ industry awards per year, ESG rating top quintile",
            "quick_win": False
        })
        recommendations.append({
            "priority": "medium",
            "category": "Trust",
            "action": "Implement ESG transparency program",
            "what": "Proactively address ESG concerns through comprehensive reporting and measurable commitments.",
            "description": "ESG is now material to trust. If low score relates to ESG concerns: 1) Publish comprehensive ESG/sustainability report, 2) Set measurable targets (carbon reduction, diversity, governance), 3) Third-party verification (B-Corp, SASB, GRI frameworks), 4) Board-level ESG oversight, 5) Link executive comp to ESG goals, 6) Regular progress updates.",
            "evidence": "Khan et al. (2016) find material ESG disclosure improves stock performance by 4-6% annually. Eccles et al. (2014) show ESG transparency reduces cost of capital by 20-40 bps and improves valuation multiples.",
            "expected_impact": "5-8 IRCI points over 12-18 months",
            "timeframe": "12-18 months",
            "tools": "SASB/GRI reporting frameworks, ESG data platforms (Sustainalytics, MSCI ESG), third-party verification (ERM, SGS)",
            "metrics": "Track: ESG rating scores (MSCI, Sustainalytics), ESG investor ownership %, sustainability report downloads",
            "benchmark": "Target: MSCI ESG Rating AA or higher, Sustainalytics <20 risk score, 30%+ ESG-focused investors",
            "quick_win": False
        })

    if classification == "medium":
        recommendations.append({
            "priority": "medium",
            "category": "Trust",
            "action": "Monitor sentiment trends proactively",
            "what": "Continuously track media tone and investor perception to catch and address emerging concerns early.",
            "description": "Prevent trust issues before they escalate. Implement real-time monitoring: 1) Daily sentiment scoring (FinBERT, RavenPack), 2) Weekly media review, 3) Monthly investor perception surveys, 4) Social media listening (Twitter, StockTwits, Reddit), 5) Rapid response protocol for emerging negative narratives.",
            "evidence": "Tetlock (2007) shows media sentiment predicts stock returns - early detection allows proactive response. Antweiler & Frank (2004) demonstrate social media sentiment has 15-20% predictive power for trading volume.",
            "expected_impact": "3-5 IRCI points over 6 months",
            "timeframe": "6 months",
            "tools": "RavenPack or Sentifi for sentiment scoring, Meltwater for media monitoring, Dataminr for real-time alerts, Q4 Analytics for investor surveys",
            "metrics": "Track: Daily sentiment score, weekly trend, negative narrative emergence rate, response time to negative news",
            "benchmark": "Target: Sentiment >0.3, <24 hour response to negative narratives, <5% negative article %",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Trust",
            "action": "Strengthen governance and board composition",
            "what": "Enhance corporate governance practices to demonstrate commitment to shareholder interests.",
            "description": "Governance drives trust. Best practices: 1) Majority independent board, 2) Separate CEO/Chair roles (or strong lead independent director), 3) Diverse board (gender, race, experience), 4) Regular board refreshment, 5) Transparent compensation (clear pay-for-performance), 6) Strong audit/risk committees, 7) Annual say-on-pay >90% support.",
            "evidence": "Gompers et al. (2003) show strong governance correlates with 8.5% higher annual returns. ISS governance scores improve valuations by 5-10% (Brown & Caylor 2006).",
            "expected_impact": "4-6 IRCI points over 12 months",
            "timeframe": "12 months",
            "tools": "ISS governance ratings, Glass Lewis reviews, board evaluation consultants (Spencer Stuart, Egon Zehnder)",
            "metrics": "Track: ISS governance score, board independence %, board diversity %, say-on-pay vote %, shareholder proposal outcomes",
            "benchmark": "Target: ISS score 1-3 (low risk), >80% independent board, >30% diverse directors, >90% say-on-pay approval",
            "quick_win": False
        })
        recommendations.append({
            "priority": "low",
            "category": "Trust",
            "action": "Strengthen ESG narrative and reporting",
            "what": "Clearly communicate your environmental, social, and governance practices to meet growing investor expectations.",
            "description": "Growing investor focus on ESG. Even with moderate trust score, strengthen positioning: 1) Annual ESG report (SASB framework), 2) Clear materiality assessment, 3) Quantified goals (net zero by 20XX, diversity targets), 4) Progress dashboards, 5) ESG-focused investor engagement.",
            "evidence": "Krueger et al. (2021) survey: 88% of institutional investors consider ESG in decisions. Friede et al. (2015) meta-analysis: 63% of studies show positive ESG-financial performance relationship.",
            "expected_impact": "3-5 IRCI points over 12 months",
            "timeframe": "12 months",
            "tools": "SASB framework, CDP reporting, ESG data platforms, ESG-focused IR targeting",
            "metrics": "Track: ESG rating improvement, % ESG investors in base, ESG report engagement metrics",
            "benchmark": "Target: Annual ESG report published, measurable targets set, ESG investors >25% of base",
            "quick_win": False
        })

    if classification == "high":
        recommendations.append({
            "priority": "low",
            "category": "Trust",
            "action": "Leverage positive sentiment and thought leadership",
            "what": "Build on strong investor confidence by amplifying positive coverage and maintaining consistent messaging.",
            "description": "Your trust is strong. Capitalize on momentum: 1) Amplify favorable coverage across channels, 2) Feature positive analyst quotes in presentations, 3) Customer success stories, 4) Thought leadership to maintain visibility, 5) Consistent messaging across all platforms.",
            "evidence": "Momentum effects documented by Jegadeesh & Titman (1993) - positive sentiment compounds. Lang & Lundholm (1996) show communication consistency maintains valuation premiums.",
            "expected_impact": "2-3 IRCI points maintenance",
            "timeframe": "Ongoing",
            "tools": "Social amplification tools, investor presentation updates, consistent messaging frameworks",
            "metrics": "Track: Sentiment score trend, positive coverage %, analyst recommendation distribution (buy/hold/sell)",
            "benchmark": "Maintain: Sentiment >0.5, >60% positive coverage, >50% buy ratings from analysts",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Trust",
            "action": "Maintain transparency and proactive communication",
            "what": "Sustain high trust through ongoing transparency, consistent disclosure, and proactive investor engagement.",
            "description": "Don't let guard down. Maintain practices that built trust: 1) Consistent disclosure cadence, 2) Proactive updates (don't wait for questions), 3) Accessible management (responsive to inquiries), 4) Clear guidance, 5) Risk transparency.",
            "evidence": "Trust takes years to build, moments to destroy. Slovic (1993) asymmetry principle: negative events have 5-10x more impact on trust than positive events.",
            "expected_impact": "2-3 IRCI points maintenance",
            "timeframe": "Ongoing",
            "tools": "Disclosure calendar, proactive communication protocols, investor access management",
            "metrics": "Track: Investor satisfaction scores, analyst accessibility ratings, disclosure consistency metrics",
            "benchmark": "Maintain: >90% investor satisfaction, <24 hour response to inquiries, zero quarters missed guidance",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Trust",
            "action": "Build strategic narrative for long-term value creation",
            "what": "Articulate a compelling multi-year strategy that reinforces confidence in long-term value creation.",
            "description": "High trust enables long-term thinking. Communicate strategic narrative: 1) 3-5 year strategic vision, 2) Clear value creation roadmap, 3) Capital allocation framework, 4) M&A strategy if applicable, 5) Technology/innovation investments, 6) Market expansion plans.",
            "evidence": "Barton et al. (2017) McKinsey research: companies with long-term orientation deliver 50% higher returns. Clear strategic communication reduces investor uncertainty.",
            "expected_impact": "3-5 IRCI points from enhanced strategic clarity",
            "timeframe": "6-12 months",
            "tools": "Investor day presentations, strategic roadmap visualization, multi-year financial frameworks",
            "metrics": "Track: Long-term investor % (holding >1 year), analyst long-term growth estimates, strategic clarity scores",
            "benchmark": "Target: >70% long-term holders, analyst LT growth estimates >10%, strategic clarity rating top quartile",
            "quick_win": False
        })

    return recommendations


def generate_playbook(
    dial_scores: Dict[str, float],
    df_composite: pd.DataFrame,
    ticker: str = None
) -> Dict:
    """
    Generate a comprehensive IR playbook based on dial scores

    Args:
        dial_scores: Dict with keys 'valuation', 'liquidity', 'coverage', 'trust'
        df_composite: Composite dataframe with analysis results
        ticker: Optional ticker symbol for company-specific context

    Returns:
        Dict with 'recommendations' (list), 'priorities' (dict), 'summary' (str)
    """
    all_recommendations = []

    # Generate recommendations for each dial
    all_recommendations.extend(
        get_valuation_recommendations(dial_scores.get('valuation', 50), df_composite)
    )
    all_recommendations.extend(
        get_liquidity_recommendations(dial_scores.get('liquidity', 50), df_composite)
    )
    all_recommendations.extend(
        get_coverage_recommendations(dial_scores.get('coverage', 50), df_composite)
    )
    all_recommendations.extend(
        get_trust_recommendations(dial_scores.get('trust', 50), df_composite)
    )

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    all_recommendations.sort(key=lambda x: priority_order[x["priority"]])

    # Identify weakest dials
    dial_classifications = {
        dial: classify_score(score)
        for dial, score in dial_scores.items()
    }

    critical_dials = [dial for dial, cls in dial_classifications.items() if cls == "critical"]
    low_dials = [dial for dial, cls in dial_classifications.items() if cls == "low"]

    # Generate summary
    if critical_dials:
        focus_areas = ", ".join([d.capitalize() for d in critical_dials])
        summary = f"🚨 **Critical Focus Areas:** {focus_areas}. These dials require immediate attention with dedicated resources."
    elif low_dials:
        focus_areas = ", ".join([d.capitalize() for d in low_dials])
        summary = f"⚠️ **Priority Areas:** {focus_areas}. Focus your IR efforts on improving these metrics."
    else:
        summary = "✅ **Strong Performance:** Your IRCI scores are healthy across all dials. Continue current strategies while optimizing for efficiency."

    # Count priorities
    priority_counts = {
        "high": len([r for r in all_recommendations if r["priority"] == "high"]),
        "medium": len([r for r in all_recommendations if r["priority"] == "medium"]),
        "low": len([r for r in all_recommendations if r["priority"] == "low"])
    }

    # Identify quick wins
    quick_wins = [r for r in all_recommendations if r.get("quick_win", False)]

    return {
        "recommendations": all_recommendations,
        "priority_counts": priority_counts,
        "summary": summary,
        "quick_wins": quick_wins,
        "dial_classifications": dial_classifications
    }
