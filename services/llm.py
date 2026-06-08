"""LLM service using OpenRouter."""

import os
import json
import logging
from typing import Optional, Dict, Any
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


async def call_openrouter_api(messages: list, temperature: float = 0.7) -> str:
    """Call OpenRouter API directly with improved timeout handling."""
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set in environment")
        return ""
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)  # Increased to 2 minutes per request
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("choices") and len(data["choices"]) > 0:
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        logger.warning("No choices in API response")
                        return ""
                else:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                    return ""
    except asyncio.TimeoutError:
        logger.error("OpenRouter API request timed out after 120 seconds")
        return ""
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {e}")
        return ""


async def analyze_text(text: str, prompt: str) -> str:
    """Use LLM to analyze text with a given prompt."""
    try:
        messages = [
            {"role": "user", "content": prompt + "\n\nContext:\n" + text}
        ]
        return await call_openrouter_api(messages)
    except Exception as e:
        logger.error(f"Error analyzing text: {e}")
        return ""


async def generate_single_analysis(key: str, prompt: str, context_text: str) -> tuple[str, str]:
    """Generate a single analysis item in parallel."""
    try:
        full_prompt = f"{prompt}\n\nData:\n{context_text}"
        messages = [{"role": "user", "content": full_prompt}]
        response = await call_openrouter_api(messages)
        result = response if response else f"Unable to generate {key} at this time."
        return (key, result)
    except Exception as e:
        logger.error(f"Error generating {key}: {e}")
        return (key, f"Unable to generate {key} at this time.")


async def generate_analysis(context: Dict[str, Any]) -> Dict[str, str]:
    """Generate stock analysis using LLM with provided context (parallel calls)."""
    try:
        # Format context for analysis
        context_text = json.dumps(context, indent=2, default=str)
        
        analysis_prompts = {
            "business_summary": """Based on the provided company information and financial data, 
            provide a concise 2-3 sentence business summary. Be specific and factual.""",
            
            "news_summary": """Based on the recent news items provided, summarize the key themes 
            and recent developments in 2-3 sentences. Focus on material news.""",
            
            "bull_case": """Based on all provided data, write a compelling bull case (3-4 sentences) 
            for why an investor should consider this stock. Focus on strengths and opportunities.""",
            
            "bear_case": """Based on all provided data, write a realistic bear case (3-4 sentences) 
            for potential risks and reasons to avoid this stock. Be balanced and factual.""",
            
            "short_term_view": """Based on recent price action and news, what is the short-term 
            (1-3 months) price outlook? Provide 1-2 sentences with reasoning.""",
            
            "long_term_view": """Based on fundamentals and business prospects, what is the long-term 
            (1+ years) price outlook? Provide 1-2 sentences with reasoning.""",
        }
        
        # Run all LLM calls in parallel
        tasks = [generate_single_analysis(key, prompt, context_text) for key, prompt in analysis_prompts.items()]
        results_list = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Convert list of tuples to dict
        results = dict(results_list)
        
        return results
    except Exception as e:
        logger.error(f"Error in generate_analysis: {e}")
        return {
            "business_summary": "Unable to generate analysis at this time.",
            "news_summary": "Unable to generate analysis at this time.",
            "bull_case": "Unable to generate analysis at this time.",
            "bear_case": "Unable to generate analysis at this time.",
            "short_term_view": "Unable to generate analysis at this time.",
            "long_term_view": "Unable to generate analysis at this time.",
        }


def generate_rating(bull_score: float, bear_score: float, risk_score: int) -> str:
    """Generate buy/hold/avoid rating based on analysis scores."""
    # Simple logic: if bull is strong and risk is low, recommend buy
    # if bear is strong or risk is high, recommend avoid
    # otherwise hold
    
    risk_factor = (11 - risk_score) / 10  # Lower risk = higher factor
    combined_score = (bull_score - bear_score) * risk_factor
    
    if combined_score > 0.5:
        return "Buy"
    elif combined_score < -0.3:
        return "Avoid"
    else:
        return "Hold"
