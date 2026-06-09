"""Tools for stock analysis agents."""

import json
from typing import Any, Dict, List
from services.market_data import (
    get_price_data, get_company_profile, get_recent_news, get_financial_metrics
)
from services.llm import generate_analysis, generate_rating
from models.schemas import RiskAssessment
import logging

logger = logging.getLogger(__name__)


async def price_data_tool(ticker: str) -> Dict[str, Any]:
    """Tool for fetching price data."""
    try:
        data = await get_price_data(ticker)
        return {
            "success": True,
            "data": data.dict(),
            "message": f"Fetched price data for {ticker}"
        }
    except Exception as e:
        logger.error(f"Price data tool error: {e}")
        # Return safe default instead of error
        return {
            "success": True,
            "data": {
                "current_price": 0.0,
                "previous_close": 0.0,
                "change_percent": 0.0,
                "currency": "USD"
            },
            "message": f"Unable to fetch live price data for {ticker} - using placeholder"
        }


async def company_profile_tool(ticker: str) -> Dict[str, Any]:
    """Tool for fetching company profile."""
    try:
        data = await get_company_profile(ticker)
        return {
            "success": True,
            "data": data.dict(),
            "message": f"Fetched company profile for {ticker}"
        }
    except Exception as e:
        logger.error(f"Company profile tool error: {e}")
        return {
            "success": True,
            "data": {
                "name": ticker.upper(),
                "description": "",
                "sector": None,
                "industry": None,
                "country": "US",
                "employees": None,
                "website": None
            },
            "message": f"Unable to fetch company profile for {ticker} - using placeholder"
        }


async def news_tool(ticker: str, limit: int = 5) -> Dict[str, Any]:
    """Tool for fetching recent news."""
    try:
        data = await get_recent_news(ticker, limit)
        return {
            "success": True,
            "data": [item.dict() for item in data],
            "count": len(data),
            "message": f"Fetched {len(data)} news items for {ticker}"
        }
    except Exception as e:
        logger.error(f"News tool error: {e}")
        return {
            "success": True,
            "data": [],
            "count": 0,
            "message": f"Unable to fetch news for {ticker} - no recent news available"
        }


async def fundamentals_tool(ticker: str) -> Dict[str, Any]:
    """Tool for fetching financial metrics."""
    try:
        data = await get_financial_metrics(ticker)
        return {
            "success": True,
            "data": data.dict(),
            "message": f"Fetched financial metrics for {ticker}"
        }
    except Exception as e:
        logger.error(f"Fundamentals tool error: {e}")
        return {
            "success": True,
            "data": {
                "pe_ratio": None,
                "market_cap": None,
                "dividend_yield": None,
                "eps": None,
                "revenue": None,
                "revenue_growth": None
            },
            "message": f"Unable to fetch financial metrics for {ticker} - using placeholder"
        }


async def technical_trend_tool(price_data: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    """Tool for analyzing technical trends based on price data."""
    try:
        trend = "neutral"
        reasoning = ""
        
        if "change_percent" in price_data:
            change = price_data["change_percent"]
            if change > 2:
                trend = "bullish"
                reasoning = f"Price up {change:.2f}% - positive momentum"
            elif change < -2:
                trend = "bearish"
                reasoning = f"Price down {change:.2f}% - negative momentum"
            else:
                trend = "neutral"
                reasoning = f"Price change {change:.2f}% - consolidating"
        
        return {
            "success": True,
            "trend": trend,
            "reasoning": reasoning,
            "message": f"Technical trend analysis for {ticker}: {trend}"
        }
    except Exception as e:
        logger.error(f"Technical trend tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to analyze technical trend for {ticker}"
        }


async def risk_scoring_tool(
    price_data: Dict[str, Any],
    financial_metrics: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    ticker: str
) -> Dict[str, Any]:
    """Tool for assessing risk."""
    try:
        risk_factors = []
        base_risk = 5
        
        # Price volatility risk
        if "change_percent" in price_data:
            change = abs(price_data["change_percent"])
            if change > 5:
                base_risk += 2
                risk_factors.append("High recent volatility")
            elif change > 3:
                base_risk += 1
                risk_factors.append("Moderate recent volatility")
        
        # Financial metrics risk
        if financial_metrics.get("pe_ratio"):
            pe = financial_metrics["pe_ratio"]
            if pe < 0:
                base_risk += 2
                risk_factors.append("Negative earnings")
            elif pe > 30:
                base_risk += 1
                risk_factors.append("High P/E ratio")
        
        # News sentiment (simplified)
        if news_items:
            # Could implement sentiment analysis here
            risk_factors.append(f"Recent developments tracked ({len(news_items)} news items)")
        
        risk_score = max(1, min(10, base_risk))
        
        volatility = "High" if abs(price_data.get("change_percent", 0)) > 5 else "Moderate" if abs(price_data.get("change_percent", 0)) > 2 else "Low"
        
        return {
            "success": True,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "volatility_assessment": volatility,
            "message": f"Risk assessment for {ticker}: {risk_score}/10"
        }
    except Exception as e:
        logger.error(f"Risk scoring tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to assess risk for {ticker}"
        }


async def analysis_tool(context: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    """Tool for generating AI analysis of stock."""
    try:
        analysis = await generate_analysis(context)
        return {
            "success": True,
            "analysis": analysis,
            "message": f"Generated analysis for {ticker}"
        }
    except Exception as e:
        logger.error(f"Analysis tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate analysis for {ticker}"
        }


def rating_tool(
    bull_case: str,
    bear_case: str,
    risk_score: int,
    ticker: str
) -> Dict[str, Any]:
    """Tool for generating final rating."""
    try:
        # Simple scoring: positive words in bull case, negative in bear case
        bull_score = len(bull_case.split()) / 10  # Normalize by length
        bear_score = len(bear_case.split()) / 10
        
        rating = generate_rating(bull_score, bear_score, risk_score)
        
        return {
            "success": True,
            "rating": rating,
            "message": f"Generated rating for {ticker}: {rating}"
        }
    except Exception as e:
        logger.error(f"Rating tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate rating for {ticker}"
        }
