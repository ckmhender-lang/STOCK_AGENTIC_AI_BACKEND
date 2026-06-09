"""LangGraph workflow for stock analysis."""

import logging
from typing import Callable, Any, Dict, Optional
from agents.state import StockAnalysisState
from agents.tools import (
    price_data_tool, company_profile_tool, news_tool, fundamentals_tool,
    technical_trend_tool, risk_scoring_tool, analysis_tool, rating_tool
)
from models.schemas import (
    PriceData, CompanyProfile, NewsItem, FinancialMetrics, RiskAssessment
)
import asyncio

logger = logging.getLogger(__name__)


async def price_data_agent(state: StockAnalysisState) -> StockAnalysisState:
    """Agent for fetching price data."""
    logger.info(f"Price Data Agent: Processing {state.ticker}")
    
    try:
        result = await price_data_tool(state.ticker)
        
        if result.get("success") and result.get("data"):
            data = result["data"]
            state.price_data = PriceData(**data)
        else:
            state.errors.append(f"Price Data Agent: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Price Data Agent exception: {e}")
        state.errors.append(f"Price Data Agent: {str(e)}")
    
    return state


async def company_agent(state: StockAnalysisState) -> StockAnalysisState:
    """Agent for fetching company profile."""
    logger.info(f"Company Agent: Processing {state.ticker}")
    
    try:
        result = await company_profile_tool(state.ticker)
        
        if result.get("success") and result.get("data"):
            data = result["data"]
            state.company_profile = CompanyProfile(**data)
        else:
            state.errors.append(f"Company Agent: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Company Agent exception: {e}")
        state.errors.append(f"Company Agent: {str(e)}")
    
    return state


async def news_agent(state: StockAnalysisState) -> StockAnalysisState:
    """Agent for fetching recent news."""
    logger.info(f"News Agent: Processing {state.ticker}")
    
    try:
        result = await news_tool(state.ticker, limit=5)
        
        if result.get("success") and result.get("data"):
            state.recent_news = [NewsItem(**item) for item in result["data"]]
        else:
            state.errors.append(f"News Agent: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"News Agent exception: {e}")
        state.errors.append(f"News Agent: {str(e)}")
    
    return state


async def fundamentals_agent(state: StockAnalysisState) -> StockAnalysisState:
    """Agent for fetching financial metrics."""
    logger.info(f"Fundamentals Agent: Processing {state.ticker}")
    
    try:
        result = await fundamentals_tool(state.ticker)
        
        if result.get("success") and result.get("data"):
            data = result["data"]
            state.financial_metrics = FinancialMetrics(**data)
        else:
            state.errors.append(f"Fundamentals Agent: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Fundamentals Agent exception: {e}")
        state.errors.append(f"Fundamentals Agent: {str(e)}")
    
    return state


async def analysis_agent(state: StockAnalysisState) -> StockAnalysisState:
    """Agent for generating LLM-based analysis."""
    logger.info(f"Analysis Agent: Processing {state.ticker}")
    
    try:
        # Prepare context for analysis
        context = {
            "ticker": state.ticker,
            "price_data": state.price_data.dict() if state.price_data else None,
            "company_profile": state.company_profile.dict() if state.company_profile else None,
            "recent_news": [item.dict() for item in state.recent_news],
            "financial_metrics": state.financial_metrics.dict() if state.financial_metrics else None,
        }
        
        result = await analysis_tool(context, state.ticker)
        
        if result.get("success") and result.get("analysis"):
            analysis = result["analysis"]
            state.business_summary = analysis.get("business_summary", "")
            state.news_summary = analysis.get("news_summary", "")
            state.bull_case = analysis.get("bull_case", "")
            state.bear_case = analysis.get("bear_case", "")
            state.short_term_view = analysis.get("short_term_view", "")
            state.long_term_view = analysis.get("long_term_view", "")
        else:
            state.errors.append(f"Analysis Agent: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Analysis Agent exception: {e}")
        state.errors.append(f"Analysis Agent: {str(e)}")
    
    return state


async def risk_agent(state: StockAnalysisState) -> StockAnalysisState:
    """Agent for assessing risk."""
    logger.info(f"Risk Agent: Processing {state.ticker}")
    
    try:
        result = await risk_scoring_tool(
            state.price_data.dict() if state.price_data else {},
            state.financial_metrics.dict() if state.financial_metrics else {},
            [item.dict() for item in state.recent_news],
            state.ticker
        )
        
        if result.get("success"):
            state.risk_assessment = RiskAssessment(
                risk_score=result.get("risk_score", 5),
                risk_factors=result.get("risk_factors", ["Data not available"]),
                volatility_assessment=result.get("volatility_assessment", "Unknown")
            )
        else:
            state.errors.append(f"Risk Agent: {result.get('error', 'Unknown error')}")
            # Provide default risk assessment
            state.risk_assessment = RiskAssessment(
                risk_score=5,
                risk_factors=["Unable to fully assess risk"],
                volatility_assessment="Unknown"
            )
    except Exception as e:
        logger.error(f"Risk Agent exception: {e}")
        state.errors.append(f"Risk Agent: {str(e)}")
        state.risk_assessment = RiskAssessment(
            risk_score=5,
            risk_factors=["Unable to assess risk"],
            volatility_assessment="Unknown"
        )
    
    return state


async def rating_agent(state: StockAnalysisState) -> StockAnalysisState:
    """Agent for generating final rating."""
    logger.info(f"Rating Agent: Processing {state.ticker}")
    
    try:
        result = rating_tool(
            state.bull_case or "",
            state.bear_case or "",
            state.risk_assessment.risk_score if state.risk_assessment else 5,
            state.ticker
        )
        
        if result.get("success"):
            state.rating = result.get("rating", "Hold")
        else:
            state.errors.append(f"Rating Agent: {result.get('error', 'Unknown error')}")
            state.rating = "Hold"
    except Exception as e:
        logger.error(f"Rating Agent exception: {e}")
        state.errors.append(f"Rating Agent: {str(e)}")
        state.rating = "Hold"
    
    return state


async def run_analysis_workflow(ticker: str) -> StockAnalysisState:
    """Run the complete stock analysis workflow."""
    logger.info(f"Starting analysis workflow for {ticker}")
    
    # Initialize state with default values
    state = StockAnalysisState(ticker=ticker)
    
    # Initialize default objects to prevent None validation errors
    state.price_data = PriceData(current_price=0.0, previous_close=0.0, change_percent=0.0, currency="USD")
    state.company_profile = CompanyProfile(name=ticker, description="", sector=None, industry=None, country="US")
    state.recent_news = []
    state.financial_metrics = FinancialMetrics()
    state.risk_assessment = RiskAssessment(risk_score=5, risk_factors=["Data not available"], volatility_assessment="Unknown")
    
    # Run agents sequentially for reliable state management
    try:
        state = await price_data_agent(state)
        state = await company_agent(state)
        state = await news_agent(state)
        state = await fundamentals_agent(state)
        
        # Analysis agents depend on collected data
        state = await analysis_agent(state)
        state = await risk_agent(state)
        state = await rating_agent(state)
        
        logger.info(f"Analysis workflow completed for {ticker}")
    except Exception as e:
        logger.error(f"Error in analysis workflow for {ticker}: {e}")
        state.errors.append(f"Workflow error: {str(e)}")
    
    return state
