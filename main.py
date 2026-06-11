"""FastAPI main application."""

import os
from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
load_dotenv()

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio

from models.schemas import StockAnalysisRequest, StockAnalysisResponse, ErrorResponse
from agents.graph import run_analysis_workflow
from services.market_data import validate_ticker, detect_asset_type
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Stock Analysis Agent",
    description="AI-powered stock analysis API",
    version="1.0.0"
)

# Configure CORS - Accept both local development and production URLs
frontend_urls = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "http://localhost:3005",
    "https://stockagent.netlify.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_urls,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.post("/analyze", response_model=StockAnalysisResponse)
async def analyze_stock(request: StockAnalysisRequest):
    """
    Analyze a stock and return comprehensive analysis.
    
    Request body:
    {
        "ticker": "MU"
    }
    """
    
    ticker = request.ticker.upper().strip()
    
    # Validate ticker input
    if not ticker or len(ticker) > 10:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker. Ticker must be 1-10 characters."
        )
    
    logger.info(f"Received analysis request for ticker: {ticker}")
    
    # Validate ticker exists
    try:
        logger.info(f"[VALIDATE] Starting ticker validation for {ticker}")
        is_valid = await validate_ticker(ticker)
        logger.info(f"[VALIDATE] Ticker {ticker} validation result: {is_valid}")
        if not is_valid:
            logger.warning(f"[VALIDATE] Ticker {ticker} not found in Finnhub")
            raise HTTPException(
                status_code=404,
                detail=f"Ticker '{ticker}' not found. Please check the symbol and try again."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VALIDATE] ERROR validating ticker {ticker}: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error validating ticker. Please try again."
        )
    
    try:
        # Run analysis workflow
        logger.info(f"[WORKFLOW] Starting analysis workflow for {ticker}")
        state = await run_analysis_workflow(ticker)
        logger.info(f"[WORKFLOW] Analysis workflow completed for {ticker}")
        
        # Check for errors
        if state.errors:
            logger.warning(f"[WORKFLOW] Analysis completed with errors for {ticker}: {state.errors}")
        
        # Build response
        logger.info(f"[RESPONSE] Building response for {ticker}")
        response = StockAnalysisResponse(
            ticker=ticker,
            timestamp=state.timestamp,
            asset_type=detect_asset_type(ticker),
            price_data=state.price_data,
            company_profile=state.company_profile,
            recent_news=state.recent_news,
            financial_metrics=state.financial_metrics,
            business_summary=state.business_summary or "Unable to generate summary.",
            news_summary=state.news_summary or "Unable to generate news summary.",
            bull_case=state.bull_case or "Unable to generate bull case.",
            bear_case=state.bear_case or "Unable to generate bear case.",
            short_term_view=state.short_term_view or "Unable to assess short-term view.",
            long_term_view=state.long_term_view or "Unable to assess long-term view.",
            rating=state.rating or "Hold",
            risk_assessment=state.risk_assessment,
            disclaimer="This is educational information, not financial advice. Always conduct your own research and consult with a financial advisor before making investment decisions."
        )
        
        logger.info(f"Analysis completed successfully for {ticker}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing stock {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while analyzing the stock. Please try again."
        )


@app.post("/chat")
async def chat_with_ai(request: dict):
    """
    Chat endpoint for conversational stock analysis.
    
    Request body:
    {
        "message": "I have $25,000. Should I buy NVDA, MU, AVGO, SCHD, or FTEC?",
        "conversation_history": []
    }
    """
    
    message = request.get("message", "").strip()
    conversation_history = request.get("conversation_history", [])
    
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    logger.info(f"Chat request: {message}")
    
    try:
        from services.llm import call_openrouter_api
        
        # Create enhanced prompt for portfolio recommendations
        system_prompt = """You are an expert AI stock research assistant. Help users with:
1. Stock analysis and comparisons
2. Portfolio recommendations with allocation percentages
3. Investment strategies based on their budget and goals
4. Market insights and trends

When recommending portfolios, always provide:
- Specific ticker allocations (e.g., "NVDA (20%): $5,000")
- Rationale for each position
- Total allocation matches their budget
- Risk assessment and diversification notes

Be concise, data-driven, and practical."""
        
        # Build messages list in OpenAI format
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 4 messages for context)
        for msg in conversation_history[-4:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Call LLM for response
        response_text = await call_openrouter_api(messages)
        
        return {
            "response": response_text,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your message. Please try again."
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed",
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AI Stock Analysis Agent",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "False") == "True"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
