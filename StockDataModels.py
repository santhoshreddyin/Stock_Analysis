"""Data models for stock market analysis."""
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class StockInfo:
    """Stock information data structure."""
    symbol: str
    name: Optional[str] = None
    current_price: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    week52_high: Optional[float] = None
    week52_low: Optional[float] = None
    recommendation: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


@dataclass
class StockAnalysis:
    """Stock analysis metrics."""
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    average_volume: Optional[float] = None
    previous_close: Optional[float] = None
    price_change_percent: Optional[float] = None
    history_df: Optional[pd.DataFrame] = None
    
    @property
    def is_bullish_crossover(self) -> bool:
        """Check if 50-day MA is above 200-day MA."""
        if self.ma_50 is not None and self.ma_200 is not None:
            return self.ma_50 > self.ma_200
        return False
    
    def is_price_above_ma50(self, current_price: Optional[float]) -> bool:
        """Check if current price is above 50-day MA."""
        if current_price is not None and self.ma_50 is not None:
            return current_price > self.ma_50
        return False


@dataclass
class Stock:
    """Complete stock data with info and analysis."""
    info: StockInfo
    analysis: StockAnalysis
    
    def has_bullish_crossover_signal(self) -> bool:
        """Check for complete bullish crossover signal."""
        return (self.analysis.is_bullish_crossover and 
                self.analysis.is_price_above_ma50(self.info.current_price))
    
    def has_significant_price_change(self, threshold: float) -> bool:
        """Check if price change exceeds threshold."""
        if self.analysis.price_change_percent is not None:
            return abs(self.analysis.price_change_percent) >= threshold
        return False
