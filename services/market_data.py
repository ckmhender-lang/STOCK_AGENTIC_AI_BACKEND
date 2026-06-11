"""Market data service using Finnhub API."""

import aiohttp
import asyncio
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from models.schemas import (
    PriceData, CompanyProfile, NewsItem, FinancialMetrics
)
import logging

logger = logging.getLogger(__name__)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


async def validate_ticker(ticker: str) -> bool:
    """Validate if ticker exists in Finnhub."""
    logger.info(f"[VALIDATE_TICKER] Checking ticker: {ticker}")
    
    if not ticker or len(ticker) > 10:
        logger.warning(f"[VALIDATE_TICKER] Invalid ticker format: {ticker}")
        return False
    
    # Check if API key is configured
    if not FINNHUB_API_KEY or FINNHUB_API_KEY == "":
        logger.warning("[VALIDATE_TICKER] FINNHUB_API_KEY not configured - all tickers will be accepted")
        return True
    
    try:
        logger.info(f"[VALIDATE_TICKER] Querying Finnhub API for {ticker}")
        async with aiohttp.ClientSession() as session:
            url = f"{FINNHUB_BASE_URL}/quote"
            params = {"symbol": ticker.upper(), "token": FINNHUB_API_KEY}
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                logger.info(f"[VALIDATE_TICKER] Finnhub response status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"[VALIDATE_TICKER] Finnhub data received for {ticker}: {data.get('c') is not None}")
                    # Check if we got valid price data
                    # Handle case where API returns data but without price (c field)
                    if isinstance(data, dict):
                        current_price = data.get("c")
                        # Accept if we have a valid price, or if data exists (could be market closed)
                        return current_price is not None and isinstance(current_price, (int, float)) and current_price >= 0
                    return False
                elif resp.status == 429:
                    # Rate limited - assume ticker is valid
                    logger.warning(f"[VALIDATE_TICKER] Rate limited by Finnhub API for ticker {ticker}")
                    return True
                else:
                    logger.warning(f"[VALIDATE_TICKER] Finnhub returned status {resp.status} for {ticker}")
                    return False
    except asyncio.TimeoutError:
        logger.warning(f"[VALIDATE_TICKER] Timeout validating ticker {ticker} - assuming valid")
        return True
    except Exception as e:
        logger.error(f"[VALIDATE_TICKER] Error validating ticker {ticker}: {type(e).__name__}: {str(e)}", exc_info=True)
        return False


async def get_price_data(ticker: str) -> PriceData:
    """Fetch current stock price from Finnhub."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{FINNHUB_BASE_URL}/quote"
            params = {"symbol": ticker.upper(), "token": FINNHUB_API_KEY}
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Extract values, defaulting to 0 if None
                    current_price = data.get("c") or 0.0
                    previous_close = data.get("pc") or 0.0
                    
                    # Ensure they're numbers
                    if not isinstance(current_price, (int, float)):
                        current_price = 0.0
                    if not isinstance(previous_close, (int, float)):
                        previous_close = 0.0
                    
                    change_percent = 0.0
                    if previous_close and previous_close > 0:
                        change_percent = ((current_price - previous_close) / previous_close) * 100
                    
                    return PriceData(
                        current_price=float(current_price),
                        previous_close=float(previous_close),
                        change_percent=round(change_percent, 2),
                        currency="USD"
                    )
                else:
                    raise Exception(f"Finnhub API error: {resp.status}")
    except Exception as e:
        logger.error(f"Error fetching price data for {ticker}: {e}")
        raise


async def get_company_profile(ticker: str) -> CompanyProfile:
    """Fetch company profile from Finnhub."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{FINNHUB_BASE_URL}/company-profile2"
            params = {"symbol": ticker.upper(), "token": FINNHUB_API_KEY}
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Fallback to minimal profile if needed
                    return CompanyProfile(
                        name=data.get("name", ticker.upper()),
                        description=data.get("description", ""),
                        sector=data.get("finnhubIndustry", None),
                        industry=data.get("finnhubIndustry", None),
                        country=data.get("country", "US"),
                        employees=data.get("employees", None),
                        website=data.get("weburl", None)
                    )
                else:
                    # Return minimal profile if API fails
                    return CompanyProfile(
                        name=ticker.upper(),
                        description="",
                        sector=None,
                        industry=None,
                        country="US"
                    )
    except Exception as e:
        logger.error(f"Error fetching company profile for {ticker}: {e}")
        return CompanyProfile(
            name=ticker.upper(),
            description="",
            sector=None,
            industry=None,
            country="US"
        )


async def get_recent_news(ticker: str, limit: int = 5) -> List[NewsItem]:
    """Fetch recent news for a stock."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{FINNHUB_BASE_URL}/company-news"
            
            # Get news from last 30 days
            from datetime import datetime, timedelta
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            params = {
                "symbol": ticker.upper(),
                "from": from_date,
                "to": to_date,
                "token": FINNHUB_API_KEY
            }
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    news_items = []
                    
                    for item in data[:limit]:
                        try:
                            news_items.append(NewsItem(
                                title=item.get("headline", ""),
                                summary=item.get("summary", ""),
                                published_at=datetime.fromtimestamp(item.get("datetime", 0)),
                                source=item.get("source", "Unknown"),
                                url=item.get("url", None)
                            ))
                        except Exception as e:
                            logger.warning(f"Error parsing news item: {e}")
                            continue
                    
                    return news_items
                else:
                    return []
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return []


async def get_financial_metrics(ticker: str) -> FinancialMetrics:
    """Fetch financial metrics from Finnhub."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{FINNHUB_BASE_URL}/quote"
            params = {"symbol": ticker.upper(), "token": FINNHUB_API_KEY}
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Safely extract numeric values
                    pe_ratio = data.get("pe")
                    if pe_ratio is not None and not isinstance(pe_ratio, (int, float)):
                        pe_ratio = None
                    
                    eps = data.get("eps")
                    if eps is not None and not isinstance(eps, (int, float)):
                        eps = None
                    
                    # Get market cap if available
                    market_cap = None
                    try:
                        market_cap_val = data.get("marketCap")
                        if market_cap_val and isinstance(market_cap_val, (int, float)):
                            if market_cap_val >= 1_000_000_000:
                                market_cap = f"${market_cap_val / 1_000_000_000:.2f}B"
                            elif market_cap_val >= 1_000_000:
                                market_cap = f"${market_cap_val / 1_000_000:.2f}M"
                    except:
                        pass
                    
                    return FinancialMetrics(
                        pe_ratio=pe_ratio,
                        market_cap=market_cap,
                        dividend_yield=None,
                        eps=eps,
                        revenue=None,
                        revenue_growth=None
                    )
                else:
                    return FinancialMetrics()
    except Exception as e:
        logger.error(f"Error fetching financial metrics for {ticker}: {e}")
        return FinancialMetrics()


def detect_asset_type(ticker: str) -> str:
    """
    Detect asset type (stock, etf, or mutual_fund) based on ticker.
    
    Common patterns:
    - Mutual Funds: FSELX, FXAIX, FCNTX, VFIAX, VTSAX, etc. (typically 5 chars ending in X or capital letters)
    - ETFs: SPY, QQQ, IWM, AGG, GLD, XLE, etc. (typically 1-4 chars)
    - Stocks: AAPL, MSFT, NVDA, GOOGL, etc. (typically 1-5 chars)
    
    This is a heuristic-based detection. For more accurate results, 
    you would need to query a database or API that provides security type information.
    """
    ticker_upper = ticker.upper()
    ticker_len = len(ticker_upper)
    
    # Known mutual fund tickers
    mutual_funds = {
        'FSELX', 'FXAIX', 'FCNTX', 'VFIAX', 'VTSAX', 'VBTLX', 'FSKAX', 
        'JMVAX', 'PGAGX', 'DODGX', 'ADSSX', 'AIVSX', 'ANIMX', 'AQRIX',
        'ARMNX', 'ARMSX', 'ARTGX', 'ARTSX', 'ARTHX', 'ASMBX', 'ASGSX'
    }
    
    # Known ETF tickers
    etfs = {
        'SPY', 'QQQ', 'IWM', 'AGG', 'GLD', 'XLE', 'XLV', 'XLK', 'VTI', 'SCHD',
        'VOO', 'VUG', 'VTV', 'VGT', 'VHT', 'VFV', 'VGK', 'VXUS', 'BND', 'BSV',
        'VWITX', 'EMXC', 'EEM', 'IEMG', 'HYLD', 'HYD', 'XYLD', 'JEPI'
    }
    
    if ticker_upper in mutual_funds:
        return 'mutual_fund'
    elif ticker_upper in etfs:
        return 'etf'
    # Heuristic: if 5 characters and ends with X, likely a mutual fund
    elif ticker_len == 5 and ticker_upper.endswith('X'):
        return 'mutual_fund'
    # Otherwise, assume it's a stock (including unknown assets)
    else:
        return 'stock'
