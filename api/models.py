"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class StockListResponse(BaseModel):
    """Response model for stock list"""
    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    sector: Optional[str] = Field(None, description="Industry sector")
    industry: Optional[str] = Field(None, description="Industry type")
    frequency: Optional[str] = Field(None, description="Data update frequency")
    current_price: Optional[float] = Field(None, description="Current stock price")

    class Config:
        from_attributes = True


class StockDetailResponse(BaseModel):
    """Response model for detailed stock information"""
    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    sector: Optional[str] = Field(None, description="Industry sector")
    industry: Optional[str] = Field(None, description="Industry type")
    description: Optional[str] = Field(None, description="Company description")
    frequency: Optional[str] = Field(None, description="Data update frequency")
    current_price: Optional[float] = Field(None, description="Current stock price")
    recommendation: Optional[str] = Field(None, description="Analyst recommendation")
    target_low: Optional[float] = Field(None, description="Target price low")
    target_high: Optional[float] = Field(None, description="Target price high")
    week52_low: Optional[float] = Field(None, description="52-week low price")
    week52_high: Optional[float] = Field(None, description="52-week high price")
    average_volume: Optional[int] = Field(None, description="Average 50-day volume")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class TopStockInfo(BaseModel):
    """Information about top performing stocks"""
    symbol: str
    current_price: float


class KeyParametersResponse(BaseModel):
    """Response model for key parameters and statistics"""
    total_stocks: int = Field(..., description="Total number of stocks in database")
    stocks_with_prices: int = Field(..., description="Number of stocks with current price data")
    buy_recommendations: int = Field(..., description="Number of buy recommendations")
    hold_recommendations: int = Field(..., description="Number of hold recommendations")
    sell_recommendations: int = Field(..., description="Number of sell recommendations")
    total_sectors: int = Field(..., description="Number of unique sectors")
    top_stocks_by_price: List[TopStockInfo] = Field(..., description="Top 5 highest priced stocks")
    last_updated: datetime = Field(..., description="Timestamp of this report")

    class Config:
        from_attributes = True


class StockHistoryResponse(BaseModel):
    """Response model for historical stock data"""
    date: datetime = Field(..., description="Date of the record")
    open_price: Optional[float] = Field(None, description="Opening price")
    close_price: Optional[float] = Field(None, description="Closing price")
    high_price: Optional[float] = Field(None, description="Day's high price")
    low_price: Optional[float] = Field(None, description="Day's low price")
    volume: Optional[int] = Field(None, description="Trading volume")

    class Config:
        from_attributes = True


# News and Graph models

class NewsArticleResponse(BaseModel):
    """Response model for news article"""
    id: int
    article_id: str
    symbol: str
    title: str
    content: str
    source: str
    url: Optional[str] = None
    author: Optional[str] = None
    published_date: datetime
    collected_date: datetime
    sentiment_score: Optional[float] = None
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class GraphNodeResponse(BaseModel):
    """Response model for graph node"""
    id: str
    label: str
    type: str
    symbol: Optional[str] = None
    mentionCount: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None


class GraphEdgeResponse(BaseModel):
    """Response model for graph edge"""
    source: str
    target: str
    type: str
    weight: float
    context: Optional[str] = None


class GraphDataResponse(BaseModel):
    """Response model for graph visualization data"""
    nodes: List[GraphNodeResponse]
    edges: List[GraphEdgeResponse]


class NewsSummaryResponse(BaseModel):
    """Response model for news summary"""
    id: int
    symbol: str
    summary_date: datetime
    period: str
    summary_text: str
    key_events: Optional[List[Dict[str, Any]]] = None
    sentiment_trend: Optional[str] = None
    overall_sentiment_score: Optional[float] = None
    article_count: int

    class Config:
        from_attributes = True


class NewsSearchRequest(BaseModel):
    """Request model for semantic news search"""
    query: str = Field(..., description="Search query")
    symbol: Optional[str] = Field(None, description="Filter by stock symbol")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")

