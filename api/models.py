"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StockListResponse(BaseModel):
    """Response model for stock list"""
    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    sector: Optional[str] = Field(None, description="Industry sector")
    industry: Optional[str] = Field(None, description="Industry type")
    frequency: Optional[str] = Field(None, description="Data update frequency")

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
