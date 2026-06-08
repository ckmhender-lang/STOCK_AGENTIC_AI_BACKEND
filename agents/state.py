"""LangGraph state definition for stock analysis workflow."""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from models.schemas import (
    PriceData, CompanyProfile, NewsItem, FinancialMetrics, RiskAssessment
)


@dataclass
class StockAnalysisState:
    """State object passed through LangGraph agents."""
    
    # Input
    ticker: str
    
    # Data from various agents
    price_data: Optional[PriceData] = None
    company_profile: Optional[CompanyProfile] = None
    recent_news: List[NewsItem] = field(default_factory=list)
    financial_metrics: Optional[FinancialMetrics] = None
    
    # Analysis outputs
    business_summary: Optional[str] = None
    news_summary: Optional[str] = None
    bull_case: Optional[str] = None
    bear_case: Optional[str] = None
    short_term_view: Optional[str] = None
    long_term_view: Optional[str] = None
    risk_assessment: Optional[RiskAssessment] = None
    
    # Final result
    rating: Optional[str] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "price_data": self.price_data.dict() if self.price_data else None,
            "company_profile": self.company_profile.dict() if self.company_profile else None,
            "recent_news": [item.dict() for item in self.recent_news],
            "financial_metrics": self.financial_metrics.dict() if self.financial_metrics else None,
            "business_summary": self.business_summary,
            "news_summary": self.news_summary,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "short_term_view": self.short_term_view,
            "long_term_view": self.long_term_view,
            "risk_assessment": self.risk_assessment.dict() if self.risk_assessment else None,
            "rating": self.rating,
            "timestamp": self.timestamp.isoformat(),
            "errors": self.errors,
        }
