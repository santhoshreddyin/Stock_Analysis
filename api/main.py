"""
FastAPI Backend for Stock Analysis Data Presentation Layer
Provides REST APIs to read and present stock data from PostgreSQL database
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import sys
import os

# Add parent directory to path to import Data_Loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Data_Loader import PostgreSQLConnection, Stock_List, StockPrice, Stock_History
from api.models import StockListResponse, StockDetailResponse, KeyParametersResponse, StockHistoryResponse

# Initialize FastAPI app
app = FastAPI(
    title="Stock Analysis API",
    description="REST API for accessing stock analysis data and key parameters",
    version="1.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection (initialized on startup)
db: Optional[PostgreSQLConnection] = None


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    global db
    db = PostgreSQLConnection.create_connection()
    print("✓ Database connection established")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    global db
    if db:
        db.close()
        print("✓ Database connection closed")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Stock Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "stocks": "/api/stocks",
            "stock_detail": "/api/stocks/{symbol}",
            "key_parameters": "/api/key-parameters",
            "stock_history": "/api/stocks/{symbol}/history"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        session = db.get_session()
        if session:
            session.close()
            return {"status": "healthy", "database": "connected"}
        return {"status": "unhealthy", "database": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


@app.get("/api/stocks", response_model=List[StockListResponse])
async def get_stocks(
    limit: int = Query(100, ge=1, le=1000, description="Number of stocks to return"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    frequency: Optional[str] = Query(None, description="Filter by frequency (Daily, Weekly, Monthly)")
):
    """
    Get list of stocks with basic information
    """
    try:
        session = db.get_session()
        if not session:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        query = session.query(Stock_List)
        
        # Apply filters
        if sector:
            query = query.filter(Stock_List.sector == sector)
        if frequency:
            query = query.filter(Stock_List.Frequency == frequency)
        
        stocks = query.limit(limit).all()
        
        result = [
            StockListResponse(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                industry=stock.industry,
                frequency=stock.Frequency
            )
            for stock in stocks
        ]
        
        session.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stocks: {str(e)}")


@app.get("/api/stocks/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(symbol: str):
    """
    Get detailed information for a specific stock including current price data
    """
    try:
        session = db.get_session()
        if not session:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Get stock basic info
        stock = session.query(Stock_List).filter_by(symbol=symbol.upper()).first()
        if not stock:
            session.close()
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        # Get current price data
        price_data = session.query(StockPrice).filter_by(symbol=symbol.upper()).first()
        
        result = StockDetailResponse(
            symbol=stock.symbol,
            name=stock.name,
            sector=stock.sector,
            industry=stock.industry,
            description=stock.description,
            frequency=stock.Frequency,
            current_price=price_data.current_price if price_data else None,
            recommendation=price_data.Recommendation if price_data else None,
            target_low=price_data.Target_Low if price_data else None,
            target_high=price_data.Target_High if price_data else None,
            week52_low=price_data.Week52_Low if price_data else None,
            week52_high=price_data.Week52_High if price_data else None,
            average_volume=price_data.average_50d_volume if price_data else None,
            last_updated=price_data.Update_Timestamp if price_data else None
        )
        
        session.close()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stock details: {str(e)}")


@app.get("/api/key-parameters", response_model=KeyParametersResponse)
async def get_key_parameters():
    """
    Get key parameters and statistics across all stocks
    """
    try:
        session = db.get_session()
        if not session:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Count total stocks
        total_stocks = session.query(Stock_List).count()
        
        # Count stocks with price data
        stocks_with_prices = session.query(StockPrice).count()
        
        # Get stocks by recommendation
        buy_recommendations = session.query(StockPrice).filter(
            StockPrice.Recommendation.in_(['Buy', 'Strong Buy'])
        ).count()
        
        hold_recommendations = session.query(StockPrice).filter(
            StockPrice.Recommendation == 'Hold'
        ).count()
        
        sell_recommendations = session.query(StockPrice).filter(
            StockPrice.Recommendation.in_(['Sell', 'Strong Sell'])
        ).count()
        
        # Get sectors count
        sectors = session.query(Stock_List.sector).distinct().filter(
            Stock_List.sector.isnot(None)
        ).count()
        
        # Get top 5 stocks by current price (highest valued)
        top_stocks = session.query(StockPrice).filter(
            StockPrice.current_price.isnot(None)
        ).order_by(StockPrice.current_price.desc()).limit(5).all()
        
        top_stocks_list = [
            {"symbol": stock.symbol, "current_price": stock.current_price}
            for stock in top_stocks
        ]
        
        result = KeyParametersResponse(
            total_stocks=total_stocks,
            stocks_with_prices=stocks_with_prices,
            buy_recommendations=buy_recommendations,
            hold_recommendations=hold_recommendations,
            sell_recommendations=sell_recommendations,
            total_sectors=sectors,
            top_stocks_by_price=top_stocks_list,
            last_updated=datetime.utcnow()
        )
        
        session.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching key parameters: {str(e)}")


@app.get("/api/stocks/{symbol}/history", response_model=List[StockHistoryResponse])
async def get_stock_history(
    symbol: str,
    limit: int = Query(30, ge=1, le=365, description="Number of historical records to return")
):
    """
    Get historical price data for a specific stock
    """
    try:
        session = db.get_session()
        if not session:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Check if stock exists
        stock = session.query(Stock_List).filter_by(symbol=symbol.upper()).first()
        if not stock:
            session.close()
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        # Get historical data
        history = session.query(Stock_History).filter_by(
            symbol=symbol.upper()
        ).order_by(Stock_History.date.desc()).limit(limit).all()
        
        result = [
            StockHistoryResponse(
                date=record.date,
                open_price=record.open_price,
                close_price=record.close_price,
                high_price=record.high_price,
                low_price=record.low_price,
                volume=record.volume
            )
            for record in history
        ]
        
        session.close()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stock history: {str(e)}")


@app.get("/api/sectors")
async def get_sectors():
    """
    Get list of all unique sectors
    """
    try:
        session = db.get_session()
        if not session:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        sectors = session.query(Stock_List.sector).distinct().filter(
            Stock_List.sector.isnot(None)
        ).all()
        
        result = {"sectors": sorted([s[0] for s in sectors if s[0]])}
        
        session.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sectors: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
