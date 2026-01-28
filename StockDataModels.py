"""Data models for stock market analysis."""
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd
import logging
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Date, Index
from sqlalchemy.sql import func
from MCP_Servers.yfinance_MCP import get_stock_price, get_historical_data, get_batch_historical_data
from HelperFunctions import to_float

# Configure logger for this module
logger = logging.getLogger(__name__)


class StockDataModel:
    """
    A comprehensive stock data model class for stock market analysis.
    
    This class encapsulates stock information, technical analysis metrics,
    and provides various methods for stock analysis and evaluation.
    All data is automatically fetched and calculated during initialization.
    """
    
    # Class variables (shared across all instances)
    DEFAULT_MA_50_PERIOD = 50
    DEFAULT_MA_200_PERIOD = 200
    DEFAULT_PRICE_CHANGE_THRESHOLD = 5.0  # 5% change threshold
    
    def __init__(self, symbol: str, fetch_data: bool = True):
        """
        Initialize StockDataModel with automatic data fetching from yfinance.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
            fetch_data: If True, automatically fetch all data from yfinance (default: True)
        """
        # Basic stock information
        self.symbol = symbol
        self.name: Optional[str] = None
        self.current_price: Optional[float] = None
        self.sector: Optional[str] = None
        self.industry: Optional[str] = None
        
        # Price targets and ranges
        self.target_high: Optional[float] = None
        self.target_low: Optional[float] = None
        self.week52_high: Optional[float] = None
        self.week52_low: Optional[float] = None
        
        # Analysis and recommendations
        self.recommendation: Optional[str] = None
        self.description: Optional[str] = None
        
        # Technical analysis metrics
        self.ma_50: Optional[float] = None
        self.ma_200: Optional[float] = None
        self.average_volume: Optional[float] = None
        self.previous_close: Optional[float] = None
        self.price_change_percent: Optional[float] = None
        
        # Historical data
        self.history_df: Optional[pd.DataFrame] = None
        
        # Metadata
        self.last_updated: Optional[datetime] = None
        self.data_fetch_success: bool = False
        
        # Automatically fetch all data if requested
        if fetch_data:
            self._fetch_all_data()
    
    def _fetch_all_data(self) -> None:
        """
        Internal method to fetch all stock data from yfinance and calculate technical indicators.
        This is automatically called during initialization.
        """
        try:
            # Fetch basic stock information
            info = get_stock_price(self.symbol)
            
            # Set basic information
            self.name = info.get("Name")
            self.current_price = to_float(info.get("Current Price"))
            self.sector = info.get("sector")
            self.industry = info.get("industry")
            
            # Set price targets and ranges
            self.target_high = to_float(info.get("Target High"))
            self.target_low = to_float(info.get("Target Low"))
            self.week52_high = to_float(info.get("52 Week High"))
            self.week52_low = to_float(info.get("52 Week Low"))
            
            # Set recommendations
            self.recommendation = info.get("Recommendation")
            self.description = info.get("Description")
            
            # Fetch and process historical data (use DB cache, only fetch what's needed)
            history = get_historical_data(self.symbol, period="200d", use_db=True)
            self.history_df = pd.DataFrame(history)
            
            if not self.history_df.empty:
                # Calculate technical indicators
                self.history_df['close'] = pd.to_numeric(self.history_df['close'], errors='coerce')
                self.history_df['volume'] = pd.to_numeric(self.history_df['volume'], errors='coerce')
                
                # Calculate moving averages
                self.history_df['50_MA'] = self.history_df['close'].rolling(window=self.DEFAULT_MA_50_PERIOD).mean()
                self.history_df['200_MA'] = self.history_df['close'].rolling(window=self.DEFAULT_MA_200_PERIOD).mean()
                
                # Set technical indicators
                self.ma_50 = self.history_df['50_MA'].iloc[-1] if len(self.history_df) >= self.DEFAULT_MA_50_PERIOD else None
                self.ma_200 = self.history_df['200_MA'].iloc[-1] if len(self.history_df) >= self.DEFAULT_MA_200_PERIOD else None
                self.average_volume = self.history_df['volume'].rolling(window=50).mean().iloc[-1]
                
                # Calculate price change
                if len(self.history_df) >= 2:
                    self.previous_close = to_float(self.history_df['close'].iloc[-2])
                    if self.previous_close is not None and self.current_price is not None:
                        self.price_change_percent = ((self.current_price - self.previous_close) / self.previous_close) * 100
                
                self.last_updated = datetime.now()
                self.data_fetch_success = True
            else:
                logger.warning(f"No historical data available for {self.symbol}")
                self.data_fetch_success = False
                
        except Exception as e:
            logger.error(f"Error fetching data for {self.symbol}: {str(e)}")
            self.data_fetch_success = False
    
    @classmethod
    def batch_create(cls, symbols: List[str], period: str = "200d") -> Dict[str, 'StockDataModel']:
        """
        Create multiple StockDataModel instances efficiently using batch download.
        
        This is much faster than creating instances one by one because yfinance
        downloads all stock data in parallel.
        
        Args:
            symbols: List of stock ticker symbols
            period: Historical data period (default: "200d" for MA calculations)
        
        Returns:
            Dictionary mapping symbol to StockDataModel instance
        
        Example:
            stocks = StockDataModel.batch_create(['AAPL', 'MSFT', 'GOOGL'])
            for symbol, stock in stocks.items():
                if stock.data_fetch_success:
                    print(f"{symbol}: ${stock.current_price}")
        
        Note:
            For large numbers of stocks, call this in chunks of 250 or less to avoid rate limits.
        """
        logger.info(f"Batch creating StockDataModel for {len(symbols)} symbols")
        
        # Create instances without fetching data
        stock_models = {symbol: cls(symbol, fetch_data=False) for symbol in symbols}
        
        # Batch download historical data (use_db is not supported in batch, so we skip DB cache here)
        # The batch download is fast enough and we only fetch the requested period
        batch_history = get_batch_historical_data(symbols, period=period)
        
        # Process each stock
        for symbol in symbols:
            stock = stock_models[symbol]
            
            try:
                # Fetch basic stock information (this is quick, no historical data)
                info = get_stock_price(symbol)
                
                # Set basic information
                stock.name = info.get("Name")
                stock.current_price = to_float(info.get("Current Price"))
                stock.sector = info.get("sector")
                stock.industry = info.get("industry")
                
                # Set price targets and ranges
                stock.target_high = to_float(info.get("Target High"))
                stock.target_low = to_float(info.get("Target Low"))
                stock.week52_high = to_float(info.get("52 Week High"))
                stock.week52_low = to_float(info.get("52 Week Low"))
                
                # Set recommendations
                stock.recommendation = info.get("Recommendation")
                stock.description = info.get("Description")
                
                # Process historical data from batch download
                history_data = batch_history.get(symbol, [])
                if history_data:
                    stock.history_df = pd.DataFrame(history_data)
                    
                    # Calculate technical indicators
                    stock.history_df['close'] = pd.to_numeric(stock.history_df['close'], errors='coerce')
                    stock.history_df['volume'] = pd.to_numeric(stock.history_df['volume'], errors='coerce')
                    
                    # Calculate moving averages
                    stock.history_df['50_MA'] = stock.history_df['close'].rolling(window=cls.DEFAULT_MA_50_PERIOD).mean()
                    stock.history_df['200_MA'] = stock.history_df['close'].rolling(window=cls.DEFAULT_MA_200_PERIOD).mean()
                    
                    # Set technical indicators
                    stock.ma_50 = stock.history_df['50_MA'].iloc[-1] if len(stock.history_df) >= cls.DEFAULT_MA_50_PERIOD else None
                    stock.ma_200 = stock.history_df['200_MA'].iloc[-1] if len(stock.history_df) >= cls.DEFAULT_MA_200_PERIOD else None
                    stock.average_volume = stock.history_df['volume'].rolling(window=50).mean().iloc[-1]
                    
                    # Calculate price change
                    if len(stock.history_df) >= 2:
                        stock.previous_close = to_float(stock.history_df['close'].iloc[-2])
                        if stock.previous_close is not None and stock.current_price is not None:
                            stock.price_change_percent = ((stock.current_price - stock.previous_close) / stock.previous_close) * 100
                    
                    stock.last_updated = datetime.now()
                    stock.data_fetch_success = True
                else:
                    logger.warning(f"No historical data available for {symbol}")
                    stock.data_fetch_success = False
                    
            except Exception as e:
                logger.error(f"Error processing batch data for {symbol}: {str(e)}")
                stock.data_fetch_success = False
        
        logger.info(f"Batch creation completed. Successful: {sum(1 for s in stock_models.values() if s.data_fetch_success)}/{len(symbols)}")
        return stock_models
        
    # ==================== Setter Methods ====================
    
    
    def set_technical_indicators(
        self,
        ma_50: Optional[float] = None,
        ma_200: Optional[float] = None,
        average_volume: Optional[float] = None
    ) -> None:
        """Set technical analysis indicators."""
        if ma_50 is not None:
            self.ma_50 = ma_50
        if ma_200 is not None:
            self.ma_200 = ma_200
        if average_volume is not None:
            self.average_volume = average_volume
    
    def set_price_data(self, current_price: float, previous_close: Optional[float] = None) -> None:
        """
        Set current price and calculate price change.
        
        Args:
            current_price: Current stock price
            previous_close: Previous closing price
        """
        self.current_price = current_price
        if previous_close is not None:
            self.previous_close = previous_close
            self.price_change_percent = ((current_price - previous_close) / previous_close) * 100
    
    def set_historical_data(self, history_df: pd.DataFrame) -> None:
        """Set historical price data."""
        self.history_df = history_df
        self.last_updated = datetime.now()
    
    # ==================== Getter Methods ====================
    
    def get_symbol(self) -> str:
        """Get stock symbol."""
        return self.symbol
    
    def get_current_price(self) -> Optional[float]:
        """Get current stock price."""
        return self.current_price
    
    def get_price_change(self) -> Optional[float]:
        """Get price change percentage."""
        return self.price_change_percent
    
    def get_moving_averages(self) -> Dict[str, Optional[float]]:
        """Get all moving averages."""
        return {
            'ma_50': self.ma_50,
            'ma_200': self.ma_200
        }
    
    def get_52week_range(self) -> Dict[str, Optional[float]]:
        """Get 52-week price range."""
        return {
            'high': self.week52_high,
            'low': self.week52_low
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all stock data."""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'current_price': self.current_price,
            'price_change_percent': self.price_change_percent,
            'sector': self.sector,
            'industry': self.industry,
            'recommendation': self.recommendation,
            'ma_50': self.ma_50,
            'ma_200': self.ma_200,
            'week52_high': self.week52_high,
            'week52_low': self.week52_low,
            'target_high': self.target_high,
            'target_low': self.target_low,
            'average_volume': self.average_volume
        }
    
    # ==================== Analysis Methods ====================
    
    def is_bullish_crossover(self) -> bool:
        """
        Check if 50-day MA is above 200-day MA (Golden Cross).
        
        Returns:
            True if bullish crossover exists, False otherwise
        """
        if self.ma_50 is not None and self.ma_200 is not None:
            return self.ma_50 > self.ma_200
        return False
    
    def is_bearish_crossover(self) -> bool:
        """
        Check if 50-day MA is below 200-day MA (Death Cross).
        
        Returns:
            True if bearish crossover exists, False otherwise
        """
        if self.ma_50 is not None and self.ma_200 is not None:
            return self.ma_50 < self.ma_200
        return False
    
    def is_price_above_ma50(self) -> bool:
        """Check if current price is above 50-day MA."""
        if self.current_price is not None and self.ma_50 is not None:
            return self.current_price > self.ma_50
        return False
    
    def is_price_above_ma200(self) -> bool:
        """Check if current price is above 200-day MA."""
        if self.current_price is not None and self.ma_200 is not None:
            return self.current_price > self.ma_200
        return False
    
    def has_bullish_crossover_signal(self) -> bool:
        """
        Check for complete bullish crossover signal.
        Requires: Golden Cross + Price above 50-day MA
        """
        return self.is_bullish_crossover() and self.is_price_above_ma50()
    
    def has_significant_price_change(self, threshold: Optional[float] = None) -> bool:
        """
        Check if price change exceeds threshold.
        
        Args:
            threshold: Price change threshold percentage (default: 5.0%)
        
        Returns:
            True if price change exceeds threshold
        """
        if threshold is None:
            threshold = self.DEFAULT_PRICE_CHANGE_THRESHOLD
        
        if self.price_change_percent is not None:
            return abs(self.price_change_percent) >= threshold
        return False
    
    def is_near_52week_high(self, tolerance_percent: float = 5.0) -> bool:
        """
        Check if current price is near 52-week high.
        
        Args:
            tolerance_percent: Percentage tolerance from 52-week high
        
        Returns:
            True if price is within tolerance of 52-week high
        """
        if self.current_price is not None and self.week52_high is not None:
            threshold = self.week52_high * (1 - tolerance_percent / 100)
            return self.current_price >= threshold
        return False
    
    def is_near_52week_low(self, tolerance_percent: float = 5.0) -> bool:
        """
        Check if current price is near 52-week low.
        
        Args:
            tolerance_percent: Percentage tolerance from 52-week low
        
        Returns:
            True if price is within tolerance of 52-week low
        """
        if self.current_price is not None and self.week52_low is not None:
            threshold = self.week52_low * (1 + tolerance_percent / 100)
            return self.current_price <= threshold
        return False
    
    def get_upside_potential(self) -> Optional[float]:
        """
        Calculate upside potential to target high.
        
        Returns:
            Percentage upside potential or None if data unavailable
        """
        if self.current_price is not None and self.target_high is not None:
            return ((self.target_high - self.current_price) / self.current_price) * 100
        return None
    
    def get_downside_risk(self) -> Optional[float]:
        """
        Calculate downside risk to target low.
        
        Returns:
            Percentage downside risk or None if data unavailable
        """
        if self.current_price is not None and self.target_low is not None:
            return ((self.current_price - self.target_low) / self.current_price) * 100
        return None
    
    def get_risk_reward_ratio(self) -> Optional[float]:
        """
        Calculate risk-reward ratio.
        
        Returns:
            Risk-reward ratio or None if data unavailable
        """
        upside = self.get_upside_potential()
        downside = self.get_downside_risk()
        
        if upside is not None and downside is not None and downside != 0:
            return upside / downside
        return None
    
    # ==================== Validation Methods ====================
    
    def is_valid(self) -> bool:
        """Check if stock has minimum required data."""
        return self.symbol is not None and self.current_price is not None
    
    def has_technical_data(self) -> bool:
        """Check if technical analysis data is available."""
        return self.ma_50 is not None and self.ma_200 is not None
    
    def has_historical_data(self) -> bool:
        """Check if historical data is available."""
        return self.history_df is not None and not self.history_df.empty
    
    # ==================== String Representation ====================
    
    def __str__(self) -> str:
        """String representation of the stock."""
        price_str = f"${self.current_price:.2f}" if self.current_price else "N/A"
        change_str = f"{self.price_change_percent:+.2f}%" if self.price_change_percent else "N/A"
        return f"{self.symbol} ({self.name}): {price_str} ({change_str})"
    
    def __repr__(self) -> str:
        """Detailed representation of the stock."""
        return (f"StockDataModel(symbol='{self.symbol}', name='{self.name}', "
                f"current_price={self.current_price}, sector='{self.sector}')")


# Import Base from Data_Loader for ORM
from Data_Loader import Base


class StockNote(Base):
    """
    SQLAlchemy ORM model for storing user notes about stocks.
    Provides CRUD operations for stock notes stored in PostgreSQL.
    """
    __tablename__ = "stock_notes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_stock_notes_symbol', 'symbol'),
    )
    
    @classmethod
    def create_table(cls, db_connection):
        """
        Create the stock_notes table if it doesn't exist.
        
        Args:
            db_connection: PostgreSQLConnection instance
        """
        try:
            if db_connection.engine:
                Base.metadata.create_all(db_connection.engine, tables=[cls.__table__])
                logger.info(f"Table {cls.__tablename__} created or already exists")
        except Exception as e:
            logger.error(f"Error creating {cls.__tablename__} table: {e}")
            raise
    
    @classmethod
    def create_note(cls, db_connection, symbol, content):
        """
        Create a new note for a stock.
        
        Args:
            db_connection: PostgreSQLConnection instance
            symbol: Stock symbol
            content: Note content
            
        Returns:
            dict: The created note as dictionary
        """
        session = db_connection.get_session()
        try:
            note = cls(symbol=symbol.upper(), content=content)
            session.add(note)
            session.commit()
            session.refresh(note)
            return note.to_dict()
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating note: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def get_notes_by_symbol(cls, db_connection, symbol):
        """
        Get all notes for a specific stock symbol.
        
        Args:
            db_connection: PostgreSQLConnection instance
            symbol: Stock symbol
            
        Returns:
            list: List of note dictionaries
        """
        session = db_connection.get_session()
        try:
            notes = session.query(cls).filter(cls.symbol == symbol.upper()).order_by(cls.created_at.desc()).all()
            return [note.to_dict() for note in notes]
        except Exception as e:
            logger.error(f"Error fetching notes: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def get_note_by_id(cls, db_connection, note_id):
        """
        Get a specific note by ID.
        
        Args:
            db_connection: PostgreSQLConnection instance
            note_id: Note ID
            
        Returns:
            dict or None: The note as dictionary or None if not found
        """
        session = db_connection.get_session()
        try:
            note = session.query(cls).filter(cls.id == note_id).first()
            return note.to_dict() if note else None
        except Exception as e:
            logger.error(f"Error fetching note: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def update_note(cls, db_connection, note_id, content):
        """
        Update a note's content.
        
        Args:
            db_connection: PostgreSQLConnection instance
            note_id: Note ID
            content: New content
            
        Returns:
            dict or None: Updated note as dictionary or None if not found
        """
        session = db_connection.get_session()
        try:
            note = session.query(cls).filter(cls.id == note_id).first()
            if note:
                note.content = content
                note.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(note)
                return note.to_dict()
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating note: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def delete_note(cls, db_connection, note_id):
        """
        Delete a note by ID.
        
        Args:
            db_connection: PostgreSQLConnection instance
            note_id: Note ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        session = db_connection.get_session()
        try:
            note = session.query(cls).filter(cls.id == note_id).first()
            if note:
                session.delete(note)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting note: {e}")
            raise
        finally:
            session.close()
    
    def to_dict(self):
        """Convert note to dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        """String representation of the note."""
        return f"StockNote(id={self.id}, symbol='{self.symbol}', created_at='{self.created_at}')"


class WatchList(Base):
    """
    SQLAlchemy ORM model for storing user watchlist of stocks.
    Provides CRUD operations for watchlist stored in PostgreSQL.
    """
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    added_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_watchlist_symbol', 'symbol'),
    )
    
    @classmethod
    def create_table(cls, db_connection):
        """
        Create the watchlist table if it doesn't exist.
        
        Args:
            db_connection: PostgreSQLConnection instance
        """
        try:
            if db_connection.engine:
                Base.metadata.create_all(db_connection.engine, tables=[cls.__table__])
                logger.info(f"Table {cls.__tablename__} created or already exists")
        except Exception as e:
            logger.error(f"Error creating {cls.__tablename__} table: {e}")
            raise
    
    @classmethod
    def add_to_watchlist(cls, db_connection, symbol):
        """
        Add a stock to the watchlist.
        
        Args:
            db_connection: PostgreSQLConnection instance
            symbol: Stock symbol
            
        Returns:
            dict: The created watchlist item as dictionary
        """
        session = db_connection.get_session()
        try:
            # Check if already exists
            existing = session.query(cls).filter_by(symbol=symbol.upper()).first()
            if existing:
                return existing.to_dict()
            
            watchlist_item = cls(symbol=symbol.upper())
            session.add(watchlist_item)
            session.commit()
            session.refresh(watchlist_item)
            return watchlist_item.to_dict()
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding to watchlist: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def get_all_watchlist(cls, db_connection):
        """
        Get all stocks in the watchlist.
        
        Args:
            db_connection: PostgreSQLConnection instance
            
        Returns:
            list: List of watchlist items as dictionaries
        """
        session = db_connection.get_session()
        try:
            items = session.query(cls).order_by(cls.added_at.desc()).all()
            return [item.to_dict() for item in items]
        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def is_in_watchlist(cls, db_connection, symbol):
        """
        Check if a stock is in the watchlist.
        
        Args:
            db_connection: PostgreSQLConnection instance
            symbol: Stock symbol
            
        Returns:
            bool: True if in watchlist, False otherwise
        """
        session = db_connection.get_session()
        try:
            item = session.query(cls).filter_by(symbol=symbol.upper()).first()
            return item is not None
        except Exception as e:
            logger.error(f"Error checking watchlist: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def remove_from_watchlist(cls, db_connection, symbol):
        """
        Remove a stock from the watchlist.
        
        Args:
            db_connection: PostgreSQLConnection instance
            symbol: Stock symbol
            
        Returns:
            bool: True if removed, False if not found
        """
        session = db_connection.get_session()
        try:
            item = session.query(cls).filter_by(symbol=symbol.upper()).first()
            if item:
                session.delete(item)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error removing from watchlist: {e}")
            raise
        finally:
            session.close()
    
    def to_dict(self):
        """Convert watchlist item to dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }
    
    def __repr__(self):
        """String representation of the watchlist item."""
        return f"WatchList(id={self.id}, symbol='{self.symbol}', added_at='{self.added_at}')"


class Portfolio(Base):
    """
    SQLAlchemy ORM model for storing user portfolio of stocks.
    Provides CRUD operations for portfolio stored in PostgreSQL.
    """
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    shares = Column(Float, nullable=False)
    purchase_price = Column(Float, nullable=False)
    purchase_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_portfolio_symbol', 'symbol'),
    )
    
    @classmethod
    def create_table(cls, db_connection):
        """
        Create the portfolio table if it doesn't exist.
        
        Args:
            db_connection: PostgreSQLConnection instance
        """
        try:
            if db_connection.engine:
                Base.metadata.create_all(db_connection.engine, tables=[cls.__table__])
                logger.info(f"Table {cls.__tablename__} created or already exists")
        except Exception as e:
            logger.error(f"Error creating {cls.__tablename__} table: {e}")
            raise
    
    @classmethod
    def add_to_portfolio(cls, db_connection, symbol, shares, purchase_price, purchase_date):
        """
        Add a stock to the portfolio.
        
        Args:
            db_connection: PostgreSQLConnection instance
            symbol: Stock symbol
            shares: Number of shares
            purchase_price: Purchase price per share
            purchase_date: Date of purchase
            
        Returns:
            dict: The created portfolio item as dictionary
        """
        session = db_connection.get_session()
        try:
            portfolio_item = cls(
                symbol=symbol.upper(),
                shares=shares,
                purchase_price=purchase_price,
                purchase_date=purchase_date
            )
            session.add(portfolio_item)
            session.commit()
            session.refresh(portfolio_item)
            return portfolio_item.to_dict()
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding to portfolio: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def get_all_portfolio(cls, db_connection):
        """
        Get all stocks in the portfolio.
        
        Args:
            db_connection: PostgreSQLConnection instance
            
        Returns:
            list: List of portfolio items as dictionaries
        """
        session = db_connection.get_session()
        try:
            items = session.query(cls).order_by(cls.purchase_date.desc()).all()
            return [item.to_dict() for item in items]
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def get_portfolio_by_id(cls, db_connection, portfolio_id):
        """
        Get a specific portfolio item by ID.
        
        Args:
            db_connection: PostgreSQLConnection instance
            portfolio_id: Portfolio item ID
            
        Returns:
            dict or None: The portfolio item as dictionary or None if not found
        """
        session = db_connection.get_session()
        try:
            item = session.query(cls).filter(cls.id == portfolio_id).first()
            return item.to_dict() if item else None
        except Exception as e:
            logger.error(f"Error fetching portfolio item: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def update_portfolio(cls, db_connection, portfolio_id, shares=None, purchase_price=None, purchase_date=None):
        """
        Update a portfolio item.
        
        Args:
            db_connection: PostgreSQLConnection instance
            portfolio_id: Portfolio item ID
            shares: New number of shares (optional)
            purchase_price: New purchase price (optional)
            purchase_date: New purchase date (optional)
            
        Returns:
            dict or None: Updated portfolio item as dictionary or None if not found
        """
        session = db_connection.get_session()
        try:
            item = session.query(cls).filter(cls.id == portfolio_id).first()
            if item:
                if shares is not None:
                    item.shares = shares
                if purchase_price is not None:
                    item.purchase_price = purchase_price
                if purchase_date is not None:
                    item.purchase_date = purchase_date
                item.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(item)
                return item.to_dict()
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating portfolio: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def remove_from_portfolio(cls, db_connection, portfolio_id):
        """
        Remove a stock from the portfolio.
        
        Args:
            db_connection: PostgreSQLConnection instance
            portfolio_id: Portfolio item ID
            
        Returns:
            bool: True if removed, False if not found
        """
        session = db_connection.get_session()
        try:
            item = session.query(cls).filter(cls.id == portfolio_id).first()
            if item:
                session.delete(item)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error removing from portfolio: {e}")
            raise
        finally:
            session.close()
    
    def to_dict(self):
        """Convert portfolio item to dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'shares': self.shares,
            'purchase_price': self.purchase_price,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        """String representation of the portfolio item."""
        return f"Portfolio(id={self.id}, symbol='{self.symbol}', shares={self.shares}, purchase_price={self.purchase_price})"
