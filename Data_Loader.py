from sqlalchemy import create_engine, inspect, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os
from typing import List, Optional, Type
from datetime import datetime
import logging

Base = declarative_base()
logger = logging.getLogger(__name__)


class Stock_List(Base):
    """Stock table model"""
    __tablename__ = 'Stock_List'

    symbol = Column(String(15), primary_key=True, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    Frequency = Column(String(50)) # e.g., Daily, Weekly, Monthly
    sector = Column(String(100))
    industry = Column(String(100))
    description = Column(String(10000))

class StockPrice(Base):
    """Stock price history table model"""
    __tablename__ = 'Stock_Prices'
    
    symbol = Column(String(15), primary_key=True, unique=True, nullable=False)
    Update_Timestamp = Column(DateTime, nullable=False)
    current_price = Column(Float)
    Recommendation = Column(String(50)) #Buy, Hold, Sell
    Target_Low = Column(Float)
    Target_High = Column(Float)
    Week52_Low = Column(Float)
    Week52_High = Column(Float)

class Stock_History(Base):
    """Stock historical data table model"""
    __tablename__ = 'Stock_History'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(15), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    open_price = Column(Float)
    close_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    volume = Column(Integer)
    
    # Create unique constraint on symbol + date combination
    __table_args__ = (
        {'schema': None},
    )

class Alert_Log(Base):
    """
    Alert log table model with queue support
    
    Extended schema for queue-based alert processing:
    - retry_count: Number of send attempts
    - priority: Alert priority (1=Critical, 2=High, 3=Medium, 4=Low)
    - scheduled_for: When to attempt sending (for delayed/retry)
    - error_message: Last error if failed
    - dedup_hash: Hash for deduplication within time window
    - sent_status: Pending, Processing, Sent, Failed, DeadLetter
    """
    __tablename__ = 'Alert_Log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(15), nullable=False)
    alert_type = Column(String(100), nullable=False)  # e.g., price_change, bullish_crossover
    alert_timestamp = Column(DateTime, default=datetime.utcnow)
    message = Column(String(2000))
    sent_status = Column(String(50), default='Pending')  # Pending, Processing, Sent, Failed, DeadLetter
    
    # Queue-specific fields
    retry_count = Column(Integer, default=0)
    priority = Column(Integer, default=3)  # 1=Critical, 2=High, 3=Medium, 4=Low
    scheduled_for = Column(DateTime, default=datetime.utcnow)  # When to send
    error_message = Column(String(1000), nullable=True)
    dedup_hash = Column(String(16), nullable=True, index=True)  # For deduplication
    
    # Indexes for queue operations
    __table_args__ = (
        Index('idx_alert_queue', 'sent_status', 'scheduled_for', 'priority'),
        Index('idx_dedup', 'dedup_hash', 'alert_timestamp'),
        {'schema': None},
    )


class PostgreSQLConnection:
    """SQLAlchemy-based PostgreSQL database connection handler"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        user: str = "postgres",
        password: str = "postgres"
    ):
        """
        Initialize PostgreSQL connection using SQLAlchemy
        
        Args:
            host: Database host (default: localhost)
            port: Database port (default: 5432)
            database: Database name (default: postgres)
            user: Database user (default: postgres)
            password: Database password (default: postgres)
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.engine = None
        self.SessionLocal = None
    
    @classmethod
    def create_connection(cls):
        """
        Create a PostgreSQL connection using environment variables
        
        Returns:
            PostgreSQLConnection: Initialized and connected database instance
        """
        db = cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres")
        )
        db.connect()
        db.create_tables()
        return db
    
    def connect(self) -> bool:
        """
        Establish connection to PostgreSQL database
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Create database URL
            database_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            
            # Create engine
            self.engine = create_engine(database_url, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            # Test connection
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            
            print(f"✓ Successfully connected to PostgreSQL database: {self.database}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to PostgreSQL: {e}")
            return False
    
    def get_session(self) -> Optional[Session]:
        """
        Get a new database session
        
        Returns:
            SQLAlchemy Session object or None if not connected
        """
        if not self.SessionLocal:
            print("✗ No active database connection")
            return None
        return self.SessionLocal()
    
    def get_tables(self) -> Optional[List[str]]:
        """
        Get list of all tables in the database
        
        Returns:
            List of table names, or None if error occurred
        """
        if not self.engine:
            print("✗ No active database connection")
            return None
        
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            return sorted(tables)
        except Exception as e:
            print(f"✗ Error fetching tables: {e}")
            return None
    
    def create_tables(self):
        """Create all ORM model tables in the database"""
        if not self.engine:
            print("✗ No active database connection")
            return False
        
        try:
            # Enable pgvector extension for vector operations
            with self.engine.connect() as connection:
                try:
                    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    connection.commit()
                    logger.info("✓ pgvector extension enabled")
                except Exception as e:
                    logger.warning(f"Could not enable pgvector extension: {e}")
            
            Base.metadata.create_all(self.engine)
            print("✓ Database tables created successfully")
            return True
        except Exception as e:
            print(f"✗ Error creating tables: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            print("✓ Database connection closed")
    
    def add_stock(self, symbol: str, name: str, frequency: str = None, sector: str = None, 
                  industry: str = None, description: str = None) -> bool:
        """
        Add a new stock to Stock_List table
        
        Args:
            symbol: Stock ticker symbol
            name: Company name
            frequency: Data frequency (Daily, Weekly, Monthly)
            sector: Industry sector
            industry: Industry type
            description: Stock description
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.upsert_stock(symbol, name, frequency, sector, industry, description)

    def upsert_stock(self, symbol: str, name: str, frequency: str = None, sector: str = None, 
                  industry: str = None, description: str = None) -> bool:
        """
        Add or Update a stock in Stock_List table
        
        Args:
            symbol: Stock ticker symbol
            name: Company name
            frequency: Data frequency (Daily, Weekly, Monthly)
            sector: Industry sector
            industry: Industry type
            description: Stock description
            
        Returns:
            bool: True if successful, False otherwise
        """
        session = self.get_session()
        if not session:
            return False
        
        try:
            stock = session.query(Stock_List).filter_by(symbol=symbol).first()
            if stock:
                # Update existing
                if name: stock.name = name
                if frequency: stock.Frequency = frequency
                if sector: stock.sector = sector
                if industry: stock.industry = industry
                if description: stock.description = description
                print(f"✓ Updated stock details: {symbol}")
            else:
                # Insert new
                stock = Stock_List(
                    symbol=symbol,
                    name=name,
                    Frequency=frequency,
                    sector=sector,
                    industry=industry,
                    description=description
                )
                session.add(stock)
                print(f"✓ Added stock: {symbol}")

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"✗ Error upserting stock {symbol}: {e}")
            return False
        finally:
            session.close()

    def get_all_tickers(self) -> list[str]:
        """
        Get list of all stock symbols
        
        Returns:
            List of stock symbols
        """
        session = self.get_session()
        if not session:
            return []
        
        try:
            stocks = session.query(Stock_List.symbol).all()
            return [stock.symbol for stock in stocks]
        except Exception as e:
            print(f"✗ Error fetching tickers: {e}")
            return []
        finally:
            session.close()
    
    def update_stock_price(self, symbol: str, current_price: float = None, 
                          recommendation: str = None, target_low: float = None,
                          target_high: float = None, week52_low: float = None,
                          week52_high: float = None) -> bool:
        """
        Update or insert stock price data. Only updates fields that are explicitly provided.
        
        Args:
            symbol: Stock ticker symbol
            current_price: Current stock price (optional)
            recommendation: Buy, Hold, or Sell (optional)
            target_low: Target price low (optional)
            target_high: Target price high (optional)
            week52_low: 52-week low (optional)
            week52_high: 52-week high (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        session = self.get_session()
        if not session:
            return False
        
        try:
            stock_price = session.query(StockPrice).filter_by(symbol=symbol).first()
            
            if stock_price:
                # Only update fields that are explicitly provided (not None)
                if current_price is not None:
                    stock_price.current_price = current_price
                if recommendation is not None:
                    stock_price.Recommendation = recommendation
                if target_low is not None:
                    stock_price.Target_Low = target_low
                if target_high is not None:
                    stock_price.Target_High = target_high
                if week52_low is not None:
                    stock_price.Week52_Low = week52_low
                if week52_high is not None:
                    stock_price.Week52_High = week52_high
                stock_price.Update_Timestamp = datetime.utcnow()
            else:
                stock_price = StockPrice(
                    symbol=symbol,
                    current_price=current_price,
                    Update_Timestamp=datetime.utcnow(),
                    Recommendation=recommendation,
                    Target_Low=target_low,
                    Target_High=target_high,
                    Week52_Low=week52_low,
                    Week52_High=week52_high
                )
                session.add(stock_price)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"✗ Error updating stock price for {symbol}: {e}")
            return False
        finally:
            session.close()
    
    def add_price_history(self, symbol: str, date: datetime, open_price: float,
                         close_price: float, high_price: float, low_price: float,
                         volume: int) -> bool:
        """
        Add historical price data for a stock
        
        Args:
            symbol: Stock ticker symbol
            date: Date of the price data
            open_price: Opening price
            close_price: Closing price
            high_price: Day's high price
            low_price: Day's low price
            volume: Trading volume
            
        Returns:
            bool: True if successful, False otherwise
        """
        session = self.get_session()
        if not session:
            return False
        
        try:
            history = Stock_History(
                symbol=symbol,
                date=date,
                open_price=open_price,
                close_price=close_price,
                high_price=high_price,
                low_price=low_price,
                volume=volume
            )
            session.add(history)
            session.commit()
            print(f"✓ Added history for {symbol} on {date.date()}")
            return True
        except Exception as e:
            session.rollback()
            print(f"✗ Error adding history for {symbol}: {e}")
            return False
        finally:
            session.close()
    
    def add_alert(self, symbol: str, alert_type: str, message: str, 
                 sent_status: str = "Pending") -> bool:
        """
        Log an alert in the Alert_Log table
        
        Args:
            symbol: Stock ticker symbol
            alert_type: Type of alert (e.g., Bullish Crossover, Price Change)
            message: Alert message
            sent_status: Status of alert (Pending, Sent, Failed)
            
        Returns:
            bool: True if successful, False otherwise
        """
        session = self.get_session()
        if not session:
            return False
        
        try:
            alert = Alert_Log(
                symbol=symbol,
                alert_type=alert_type,
                alert_timestamp=datetime.utcnow(),
                message=message,
                sent_status=sent_status
            )
            session.add(alert)
            session.commit()
            print(f"✓ Alert logged for {symbol}: {alert_type}")
            return True
        except Exception as e:
            session.rollback()
            print(f"✗ Error logging alert for {symbol}: {e}")
            return False
        finally:
            session.close()
    
    def get_stock(self, symbol: str) -> Optional[Stock_List]:
        """Get stock details by symbol"""
        session = self.get_session()
        if not session:
            return None
        
        try:
            stock = session.query(Stock_List).filter_by(symbol=symbol).first()
            return stock
        except Exception as e:
            print(f"✗ Error fetching stock {symbol}: {e}")
            return None
        finally:
            session.close()
    
    def get_stock_price(self, symbol: str) -> Optional[StockPrice]:
        """Get current stock price data by symbol"""
        session = self.get_session()
        if not session:
            return None
        
        try:
            price = session.query(StockPrice).filter_by(symbol=symbol).first()
            return price
        except Exception as e:
            print(f"✗ Error fetching price for {symbol}: {e}")
            return None
        finally:
            session.close()
    
    def get_all_stocks(self, Frequency: str) -> Optional[List[Stock_List]]:
        """Get all stocks from Stock_List table"""
        session = self.get_session()
        if not session:
            return None
        
        try:
            stocks = session.query(Stock_List).filter_by(Frequency=Frequency).all()
            return stocks
        except Exception as e:
            print(f"✗ Error fetching stocks: {e}")
            return None
        finally:
            session.close()


def main():
    """Main function to demonstrate SQLAlchemy ORM connection and operations"""
    
    # Create connection instance
    db = PostgreSQLConnection(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )
    
    # Connect to database
    if db.connect():
        # Create tables from ORM models
        db.create_tables()
        
        # Get list of tables
        tables = db.get_tables()
        
        if tables is not None:
            print(f"\n📊 Found {len(tables)} table(s):")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
        else:
            print("No tables found or error occurred")
        
        # Close connection
        db.close()
    else:
        print("Could not establish database connection")


if __name__ == "__main__":
    main()

