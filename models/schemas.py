"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StockAnalysisRequest(BaseModel):
    """Request schema for stock analysis."""
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")


class PriceData(BaseModel):
    """Current price information."""
    current_price: float
    previous_close: float
    change_percent: float
    currency: str = "USD"


class CompanyProfile(BaseModel):
    """Company profile information."""
    name: str
    description: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: str = "US"
    employees: Optional[int] = None
    website: Optional[str] = None


class NewsItem(BaseModel):
    """News article information."""
    title: str
    summary: str
    published_at: datetime
    source: str
    url: Optional[str] = None


class FinancialMetrics(BaseModel):
    """Financial metrics information."""
    pe_ratio: Optional[float] = None
    market_cap: Optional[str] = None
    dividend_yield: Optional[float] = None
    eps: Optional[float] = None
    revenue: Optional[str] = None
    revenue_growth: Optional[float] = None


class RiskAssessment(BaseModel):
    """Risk assessment details."""
    risk_score: int = Field(..., ge=1, le=10, description="Risk score from 1 to 10")
    risk_factors: List[str]
    volatility_assessment: str


class StockAnalysisResponse(BaseModel):
    """Response schema for stock analysis."""
    ticker: str
    timestamp: datetime
    asset_type: Optional[str] = None  # "stock", "etf", "mutual_fund", etc.
    price_data: PriceData
    company_profile: CompanyProfile
    recent_news: List[NewsItem]
    financial_metrics: FinancialMetrics
    business_summary: str
    news_summary: str
    bull_case: str
    bear_case: str
    short_term_view: str
    long_term_view: str
    rating: str = Field(..., description="Buy / Hold / Avoid")
    risk_assessment: RiskAssessment
    disclaimer: str = "This is educational information, not financial advice. Always conduct your own research before making investment decisions."


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: Optional[str] = None
    ticker: Optional[str] = None
