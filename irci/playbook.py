# irci/playbook.py
"""
IR Playbook Generator - Provides action recommendations based on IRCI dial scores
"""
from typing import Dict, List, Tuple
import pandas as pd


def classify_score(score: float) -> str:
    """Classify a dial score as low/medium/high"""
    if score < 35:
        return "critical"
    elif score < 50:
        return "low"
    elif score < 70:
        return "medium"
    else:
        return "high"


def get_valuation_recommendations(score: float, df_composite: pd.DataFrame) -> List[Dict]:
    """Generate recommendations for Valuation dial"""
    classification = classify_score(score)
    recommendations = []

    if classification in ["critical", "low"]:
        recommendations.append({
            "priority": "high",
            "category": "Valuation",
            "action": "Enhance earnings communication",
            "what": "Help analysts understand the quality and sustainability of your earnings through detailed financial education.",
            "description": "Your P/E ratio suggests the market may be undervaluing your earnings. Consider hosting an earnings call deep-dive session to help analysts better understand your business model and growth trajectory.",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Valuation",
            "action": "Clarify growth narrative",
            "what": "Articulate a clear, compelling story about how your company will grow revenue and expand market share.",
            "description": "If your P/S ratio is lagging peers, it may indicate unclear growth prospects. Develop a clear, quantified growth story with specific milestones and TAM analysis.",
            "quick_win": False
        })
        recommendations.append({
            "priority": "medium",
            "category": "Valuation",
            "action": "Increase analyst engagement",
            "what": "Build deeper relationships with sell-side analysts to improve their understanding and coverage of your company.",
            "description": "Low valuation may result from limited analyst coverage or understanding. Schedule 1-on-1 meetings with key analysts to deepen their sector knowledge.",
            "quick_win": True
        })

    if classification == "medium":
        recommendations.append({
            "priority": "medium",
            "category": "Valuation",
            "action": "Benchmark against peers",
            "what": "Systematically compare your valuation metrics to competitors to identify and address specific gaps.",
            "description": "Your valuation is moderate. Compare your P/E, P/S, and EV/EBITDA ratios to peers and identify specific gaps to address in investor communications.",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Valuation",
            "action": "Highlight competitive advantages",
            "what": "Emphasize your unique strengths that differentiate you from competitors and warrant higher valuation.",
            "description": "Emphasize unique value drivers (moats, market position, innovation) that justify premium valuation.",
            "quick_win": True
        })

    if classification == "high":
        recommendations.append({
            "priority": "low",
            "category": "Valuation",
            "action": "Maintain premium narrative",
            "what": "Continue reinforcing the key drivers that support your above-average valuation multiples.",
            "description": "Your valuation is strong. Continue reinforcing the factors that drive premium multiples through consistent messaging.",
            "quick_win": True
        })

    return recommendations


def get_liquidity_recommendations(score: float, df_composite: pd.DataFrame) -> List[Dict]:
    """Generate recommendations for Liquidity dial"""
    classification = classify_score(score)
    recommendations = []

    if classification in ["critical", "low"]:
        recommendations.append({
            "priority": "high",
            "category": "Liquidity",
            "action": "Launch liquidity enhancement program",
            "what": "Implement a comprehensive strategy to increase daily trading volume and reduce bid-ask spreads.",
            "description": "Low trading volume makes your stock less attractive to institutional investors. Consider: 1) Joining small/mid-cap conferences, 2) Engaging with market makers, 3) Exploring index inclusion opportunities.",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Liquidity",
            "action": "Expand investor base",
            "what": "Broaden and diversify your shareholder mix to create more consistent trading activity.",
            "description": "Diversify your shareholder base to increase natural trading activity. Target retail-focused platforms, attend non-deal roadshows, and increase visibility with ETF/index managers.",
            "quick_win": False
        })
        recommendations.append({
            "priority": "medium",
            "category": "Liquidity",
            "action": "Improve price discovery",
            "what": "Narrow bid-ask spreads by increasing market transparency and engagement with trading desks.",
            "description": "Wide bid-ask spreads indicate poor price discovery. Increase transparency through more frequent updates and consider engaging with additional sell-side firms.",
            "quick_win": True
        })

    if classification == "medium":
        recommendations.append({
            "priority": "medium",
            "category": "Liquidity",
            "action": "Monitor trading patterns",
            "what": "Analyze and optimize the timing of announcements to maximize market participation and volume.",
            "description": "Track daily volume trends and identify periods of illiquidity. Time major announcements to maximize trading participation.",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Liquidity",
            "action": "Engage with passive investors",
            "what": "Pursue index inclusion to benefit from automated buying by passive funds and ETFs.",
            "description": "Pursue inclusion in relevant indices to gain passive investor flows and improve baseline liquidity.",
            "quick_win": False
        })

    if classification == "high":
        recommendations.append({
            "priority": "low",
            "category": "Liquidity",
            "action": "Optimize liquidity events",
            "what": "Strategically time capital markets transactions to capitalize on strong liquidity conditions.",
            "description": "Your liquidity is strong. Ensure you're timing capital markets activities to take advantage of favorable trading conditions.",
            "quick_win": True
        })

    return recommendations


def get_coverage_recommendations(score: float, df_composite: pd.DataFrame) -> List[Dict]:
    """Generate recommendations for Coverage dial"""
    classification = classify_score(score)
    recommendations = []

    if classification in ["critical", "low"]:
        recommendations.append({
            "priority": "high",
            "category": "Coverage",
            "action": "Launch proactive media strategy",
            "what": "Build systematic relationships with top-tier financial journalists to increase quality media mentions.",
            "description": "Limited media coverage reduces investor awareness. Develop relationships with tier-1 business journalists (WSJ, Bloomberg, Reuters). Pitch newsworthy stories quarterly.",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Coverage",
            "action": "Create thought leadership content",
            "what": "Position your executives as industry experts through speaking engagements and published insights.",
            "description": "Position executives as industry experts. Secure speaking slots at major conferences, contribute to industry publications, and engage on LinkedIn with data-driven insights.",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Coverage",
            "action": "Leverage newsworthiness",
            "what": "Identify and proactively promote company milestones and achievements to generate media interest.",
            "description": "Identify and amplify newsworthy moments: product launches, partnerships, milestone achievements, industry trends you're leading.",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Coverage",
            "action": "Build journalist relationships",
            "what": "Cultivate ongoing relationships with key reporters who cover your industry and company.",
            "description": "Create a media contact database. Provide beat reporters with exclusive briefings and become their go-to source for industry commentary.",
            "quick_win": False
        })

    if classification == "medium":
        recommendations.append({
            "priority": "medium",
            "category": "Coverage",
            "action": "Upgrade media quality",
            "what": "Shift focus from quantity to quality by prioritizing placement in prestigious financial outlets.",
            "description": "You're getting coverage, but focus on tier-1 outlets. Prioritize WSJ, Bloomberg, Financial Times over press release distribution.",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Coverage",
            "action": "Track share of voice",
            "what": "Measure and benchmark your media presence relative to competitors in your sector.",
            "description": "Monitor how your media presence compares to competitors. Aim to increase your share of industry media mentions.",
            "quick_win": True
        })

    if classification == "high":
        recommendations.append({
            "priority": "low",
            "category": "Coverage",
            "action": "Maintain media momentum",
            "what": "Sustain your strong media presence through consistent engagement and story development.",
            "description": "Your media coverage is strong. Continue cultivating journalist relationships and maintain consistent story flow.",
            "quick_win": True
        })

    return recommendations


def get_trust_recommendations(score: float, df_composite: pd.DataFrame) -> List[Dict]:
    """Generate recommendations for Trust dial"""
    classification = classify_score(score)
    recommendations = []

    if classification in ["critical", "low"]:
        recommendations.append({
            "priority": "high",
            "category": "Trust",
            "action": "Address negative sentiment immediately",
            "what": "Identify and respond to negative media coverage and credibility concerns that are damaging investor confidence.",
            "description": "Low trust score indicates negative media tone or credibility concerns. Review recent negative articles and develop response strategy. Consider crisis communications support if needed.",
            "quick_win": True
        })
        recommendations.append({
            "priority": "high",
            "category": "Trust",
            "action": "Improve disclosure quality",
            "what": "Enhance transparency and clarity in financial reporting to build credibility with investors and analysts.",
            "description": "Enhance transparency through clearer MD&A, more detailed guidance, and proactive risk disclosure. Strong disclosure builds credibility.",
            "quick_win": False
        })
        recommendations.append({
            "priority": "high",
            "category": "Trust",
            "action": "Demonstrate accountability",
            "what": "Take ownership of past missteps and show concrete steps being taken to address issues and rebuild trust.",
            "description": "If you've missed guidance or faced controversies, acknowledge issues directly and outline corrective actions with measurable milestones.",
            "quick_win": True
        })
        recommendations.append({
            "priority": "medium",
            "category": "Trust",
            "action": "Build third-party validation",
            "what": "Leverage external endorsements and positive third-party voices to counter negative sentiment and build credibility.",
            "description": "Seek positive coverage from credible sources. Highlight customer testimonials, industry awards, and analyst endorsements.",
            "quick_win": False
        })

    if classification == "medium":
        recommendations.append({
            "priority": "medium",
            "category": "Trust",
            "action": "Monitor sentiment trends",
            "what": "Continuously track media tone and investor perception to catch and address emerging concerns early.",
            "description": "Track media sentiment weekly. Address emerging negative narratives before they spread.",
            "quick_win": True
        })
        recommendations.append({
            "priority": "low",
            "category": "Trust",
            "action": "Strengthen ESG narrative",
            "what": "Clearly communicate your environmental, social, and governance practices to meet growing investor expectations.",
            "description": "Growing investor focus on ESG. Ensure your governance, sustainability, and social impact stories are clearly communicated.",
            "quick_win": False
        })

    if classification == "high":
        recommendations.append({
            "priority": "low",
            "category": "Trust",
            "action": "Leverage positive sentiment",
            "what": "Build on strong investor confidence by amplifying positive coverage and maintaining consistent messaging.",
            "description": "Your trust is strong. Capitalize on positive momentum by amplifying favorable coverage and maintaining communication consistency.",
            "quick_win": True
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
