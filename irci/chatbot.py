# irci/chatbot.py
"""
IRCI Chatbot - AI assistant to help interpret results and provide IR guidance
Supports multiple AI backends: Google Gemini 3.1 Pro (default) and OpenAI GPT-5
Updated March 2026
"""
from typing import List, Dict, Optional, Literal
import pandas as pd
import os

# Supported AI providers and models
AI_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "model": "gemini-3.1-pro",
        "env_key": "GEMINI_API_KEY"
    },
    "openai": {
        "name": "OpenAI GPT-5",
        "model": "gpt-5",
        "env_key": "OPENAI_API_KEY"
    }
}

DEFAULT_PROVIDER = "gemini"


def build_context_prompt(
    df_composite: pd.DataFrame,
    ticker: str,
    conversation_history: List[Dict[str, str]] = None
) -> str:
    """
    Build a context-rich system prompt for the chatbot based on analysis results

    Args:
        df_composite: Composite dataframe with all analysis results
        ticker: Current ticker being analyzed
        conversation_history: Previous messages in the conversation

    Returns:
        System prompt with full context
    """
    # Get company-specific data
    company_data = df_composite[df_composite['ticker'] == ticker].iloc[0] if ticker else None

    if company_data is not None:
        # Extract key metrics
        irci_score = company_data.get('irci_composite_pct', 0)
        valuation_score = company_data.get('valuation_pct', 0)
        liquidity_score = company_data.get('liquidity_pct', 0)
        coverage_score = company_data.get('coverage_pct', 0)
        trust_score = company_data.get('sentiment_pct', 0)

        # Get peer context
        peer_group = df_composite['ticker'].tolist()
        avg_irci = df_composite['irci_composite_pct'].mean()
        ticker_rank = df_composite['irci_composite_pct'].rank(ascending=False)[
            df_composite['ticker'] == ticker
        ].iloc[0] if ticker else None

        context = f"""You are an expert Investor Relations (IR) advisor with deep knowledge of the IRCI framework.

CURRENT ANALYSIS CONTEXT:
Company: {ticker}
IRCI Composite Score: {irci_score:.1f}%
Peer Group Rank: #{int(ticker_rank)} out of {len(peer_group)} companies
Peer Group Average IRCI: {avg_irci:.1f}%

DIAL SCORES:
- 💰 Valuation: {valuation_score:.1f}%
- 💧 Liquidity: {liquidity_score:.1f}%
- 📰 Coverage: {coverage_score:.1f}%
- 🤝 Trust: {trust_score:.1f}%

PEER GROUP: {', '.join(peer_group)}

ABOUT IRCI:
IRCI (Investor Relations Composite Index) measures IR effectiveness across four key dimensions:

1. **Valuation (Market Perception)**
   - Measures: P/E ratio, P/S ratio, EV/EBITDA vs peer group
   - What it means: How the market values the company relative to fundamentals
   - Lower scores indicate potential undervaluation or unclear value narrative

2. **Liquidity (Trading Activity)**
   - Measures: Trading volume, bid-ask spread, volatility
   - What it means: How easily investors can trade the stock
   - Lower scores indicate poor liquidity, wide spreads, or volatile trading

3. **Coverage (Media Attention)**
   - Measures: Media mentions, source credibility (WSJ, Bloomberg > PR wires)
   - What it means: Level and quality of media attention
   - Lower scores indicate limited visibility or low-quality coverage

4. **Trust (Sentiment & Credibility)**
   - Measures: Media sentiment, disclosure quality, consistency
   - What it means: Market perception of management credibility
   - Lower scores indicate negative sentiment or trust concerns

SCORING METHODOLOGY:
- Scores are percentile-ranked within peer group (0-100%)
- 75%+ = Strong performance (top quartile)
- 50-75% = Above average
- 25-50% = Below average
- <25% = Weak performance (bottom quartile)

R² SCALING:
- Dollar impact estimates are R²-scaled
- R² represents how much of enterprise value variance is explained by IRCI
- Typical R²: 0.30-0.50 (IRCI explains 30-50% of value differences)
- This ensures we don't overstate IR's impact on total enterprise value

YOUR ROLE:
- Answer questions about {ticker}'s IRCI results clearly and concisely
- Provide specific, actionable IR recommendations
- Explain methodology when asked
- Compare to peer group performance
- Be direct and practical - IR professionals need actionable insights
- Use the actual scores and data provided above in your responses
- If asked about dollar impacts, explain R² scaling

RESPONSE STYLE:
- Professional but conversational
- Use bullet points for clarity
- Prioritize actionable insights
- Reference specific scores when relevant
- Keep responses concise (3-5 paragraphs max unless asked for detail)
"""
    else:
        # General context when no specific company is selected
        context = f"""You are an expert Investor Relations (IR) advisor with deep knowledge of the IRCI framework.

CURRENT ANALYSIS:
Analyzing {len(df_composite)} companies in peer group: {', '.join(df_composite['ticker'].tolist())}
Average IRCI Score: {df_composite['irci_composite_pct'].mean():.1f}%

ABOUT IRCI:
IRCI (Investor Relations Composite Index) measures IR effectiveness across four dimensions:
1. **Valuation** - Market perception relative to fundamentals (P/E, P/S, EV/EBITDA)
2. **Liquidity** - Trading activity (volume, spreads, volatility)
3. **Coverage** - Media attention quality and quantity
4. **Trust** - Sentiment and credibility (media tone, disclosure quality)

YOUR ROLE:
- Answer questions about IRCI methodology and results
- Provide IR best practices and recommendations
- Help interpret scores and comparisons
- Explain calculations and methodology

Keep responses professional, concise, and actionable.
"""

    return context


def _chat_with_gemini(
    user_message: str,
    system_prompt: str,
    conversation_history: List[Dict[str, str]],
    api_key: str
) -> str:
    """Generate response using Google Gemini 3.1 Pro"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    except ImportError:
        return "⚠️ Google Generative AI library not installed. Run: pip install google-generativeai"
    except Exception as e:
        return f"⚠️ Error initializing Gemini client: {str(e)}"

    # Build conversation history for Gemini
    history = []
    if conversation_history:
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

    try:
        # Initialize Gemini 3.1 Pro model (March 2026)
        model = genai.GenerativeModel(
            model_name="gemini-3.1-pro",
            system_instruction=system_prompt
        )

        # Start chat with history
        chat = model.start_chat(history=history)

        # Generate response
        response = chat.send_message(user_message)

        return response.text

    except Exception as e:
        return f"⚠️ Error generating Gemini response: {str(e)}"


def _chat_with_openai(
    user_message: str,
    system_prompt: str,
    conversation_history: List[Dict[str, str]],
    api_key: str
) -> str:
    """Generate response using OpenAI GPT-5"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except ImportError:
        return "⚠️ OpenAI library not installed. Run: pip install openai"
    except Exception as e:
        return f"⚠️ Error initializing OpenAI client: {str(e)}"

    # Build messages list for OpenAI
    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    messages.append({"role": "user", "content": user_message})

    try:
        # Use GPT-5 model (March 2026)
        response = client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ Error generating OpenAI response: {str(e)}"


def chat_with_context(
    user_message: str,
    df_composite: pd.DataFrame,
    ticker: str = None,
    conversation_history: List[Dict[str, str]] = None,
    api_key: str = None,
    provider: Literal["gemini", "openai"] = "gemini"
) -> str:
    """
    Generate chatbot response using specified AI provider with IRCI context

    Args:
        user_message: User's question or message
        df_composite: Composite dataframe with analysis results
        ticker: Optional ticker for company-specific context
        conversation_history: Previous conversation messages
        api_key: API key for the selected provider
        provider: AI provider to use ("gemini" or "openai")

    Returns:
        Assistant's response
    """
    provider_info = AI_PROVIDERS.get(provider, AI_PROVIDERS[DEFAULT_PROVIDER])

    if not api_key:
        return f"⚠️ {provider_info['name']} API key not configured. Please add {provider_info['env_key']} to your .env file or Streamlit secrets."

    # Build context
    system_prompt = build_context_prompt(df_composite, ticker, conversation_history)

    # Route to appropriate provider
    if provider == "openai":
        return _chat_with_openai(user_message, system_prompt, conversation_history or [], api_key)
    else:
        return _chat_with_gemini(user_message, system_prompt, conversation_history or [], api_key)


def get_available_providers() -> Dict[str, Dict]:
    """
    Get list of available AI providers with their configuration status

    Returns:
        Dictionary of providers with their availability status
    """
    providers = {}
    for key, info in AI_PROVIDERS.items():
        api_key = os.getenv(info["env_key"], "")
        providers[key] = {
            "name": info["name"],
            "model": info["model"],
            "available": bool(api_key),
            "env_key": info["env_key"]
        }
    return providers


def get_suggested_questions(ticker: str, df_composite: pd.DataFrame) -> List[str]:
    """
    Generate suggested questions based on company's dial scores

    Args:
        ticker: Company ticker
        df_composite: Composite dataframe

    Returns:
        List of suggested question strings
    """
    suggestions = [
        f"What are the key takeaways from {ticker}'s IRCI analysis?",
        f"How does {ticker} compare to its peers?",
        "Explain how the IRCI composite score is calculated",
        "What actions should I prioritize to improve my IRCI score?",
    ]

    # Add specific suggestions based on scores
    company_data = df_composite[df_composite['ticker'] == ticker].iloc[0]

    # Find weakest dial
    scores = {
        'Valuation': company_data.get('valuation_pct', 50),
        'Liquidity': company_data.get('liquidity_pct', 50),
        'Coverage': company_data.get('coverage_pct', 50),
        'Trust': company_data.get('sentiment_pct', 50)
    }

    weakest_dial = min(scores.items(), key=lambda x: x[1])

    if weakest_dial[1] < 50:
        suggestions.insert(1, f"Why is my {weakest_dial[0]} score low and how can I improve it?")

    # Add peer comparison if not top performer
    avg_irci = df_composite['irci_composite_pct'].mean()
    ticker_irci = company_data.get('irci_composite_pct', 50)

    if ticker_irci < avg_irci:
        suggestions.append(f"What are the top-performing companies doing differently?")

    return suggestions[:6]  # Return top 6 suggestions
