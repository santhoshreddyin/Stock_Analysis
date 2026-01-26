"""
FastAPI Backend for Stock Analysis Data Presentation Layer
Provides REST APIs to read and present stock data from PostgreSQL database
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import sys
import os

# Add parent directory to path to import Data_Loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Data_Loader import PostgreSQLConnection, Stock_List, StockPrice, Stock_History
from NewsGraphModels import NewsArticle, NewsSummary
from NewsProcessingService import get_news_service
from StockDataModels import StockNote
from api.models import (
    StockListResponse, StockDetailResponse, KeyParametersResponse, 
    StockHistoryResponse, NewsArticleResponse, GraphDataResponse,
    NewsSummaryResponse, NewsSearchRequest
)

# Database connection (initialized on startup)
db: Optional[PostgreSQLConnection] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    global db
    # Startup
    db = PostgreSQLConnection.create_connection()
    print("✓ Database connection established")
    
    # Create stock_notes table if it doesn't exist
    try:
        StockNote.create_table(db)
        print("✓ Stock notes table initialized")
    except Exception as e:
        print(f"Warning: Could not initialize stock_notes table: {e}")
    
    yield
    # Shutdown
    if db:
        db.close()
        print("✓ Database connection closed")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Stock Analysis API",
    description="REST API for accessing stock analysis data and key parameters",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            "stock_history": "/api/stocks/{symbol}/history",
            "news_articles": "/api/news",
            "news_search": "/api/news/search",
            "news_summary": "/api/news/summary/{symbol}",
            "graph_data": "/api/graph"
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
    industry: Optional[str] = Query(None, description="Filter by industry"),
    frequency: Optional[str] = Query(None, description="Filter by frequency (Daily, Weekly, Monthly)"),
    recommendation: Optional[str] = Query(None, description="Filter by recommendation"),
    min_price: Optional[float] = Query(None, description="Minimum current price"),
    max_price: Optional[float] = Query(None, description="Maximum current price")
):
    """
    Get list of stocks with basic information
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Join with StockPrice table to enable price and recommendation filtering
        query = session.query(Stock_List, StockPrice).outerjoin(
            StockPrice, Stock_List.symbol == StockPrice.symbol
        )
        
        # Apply filters
        if sector:
            query = query.filter(Stock_List.sector == sector)
        if industry:
            query = query.filter(Stock_List.industry == industry)
        if frequency:
            query = query.filter(Stock_List.Frequency == frequency)
        if recommendation:
            query = query.filter(StockPrice.Recommendation == recommendation)
        if min_price is not None:
            query = query.filter(StockPrice.current_price >= min_price)
        if max_price is not None:
            query = query.filter(StockPrice.current_price <= max_price)
        
        results = query.limit(limit).all()
        
        result = [
            StockListResponse(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                industry=stock.industry,
                frequency=stock.Frequency,
                current_price=price.current_price if price else None
            )
            for stock, price in results
        ]
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stocks: {str(e)}")
    finally:
        session.close()


@app.get("/api/stocks/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(symbol: str):
    """
    Get detailed information for a specific stock including current price data
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Get stock basic info
        stock = session.query(Stock_List).filter_by(symbol=symbol.upper()).first()
        if not stock:
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
        
        return result
    finally:
        session.close()


@app.get("/api/key-parameters", response_model=KeyParametersResponse)
async def get_key_parameters():
    """
    Get key parameters and statistics across all stocks
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
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
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching key parameters: {str(e)}")
    finally:
        session.close()


@app.get("/api/stocks/{symbol}/history", response_model=List[StockHistoryResponse])
async def get_stock_history(
    symbol: str,
    limit: int = Query(30, ge=1, le=2000, description="Number of historical records to return")
):
    """
    Get historical price data for a specific stock
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Check if stock exists
        stock = session.query(Stock_List).filter_by(symbol=symbol.upper()).first()
        if not stock:
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
        
        return result
    finally:
        session.close()


@app.get("/api/sectors")
async def get_sectors():
    """
    Get list of all unique sectors
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        sectors = session.query(Stock_List.sector).distinct().filter(
            Stock_List.sector.isnot(None)
        ).all()
        
        result = {"sectors": sorted([s[0] for s in sectors if s[0]])}
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sectors: {str(e)}")
    finally:
        session.close()


@app.get("/api/industries")
async def get_industries(sector: Optional[str] = Query(None, description="Filter industries by sector")):
    """
    Get list of all unique industries, optionally filtered by sector
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        query = session.query(Stock_List.industry).distinct().filter(
            Stock_List.industry.isnot(None)
        )
        
        if sector:
            query = query.filter(Stock_List.sector == sector)
        
        industries = query.all()
        
        result = {"industries": sorted([i[0] for i in industries if i[0]])}
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching industries: {str(e)}")
    finally:
        session.close()


# News and Graph API Endpoints

@app.get("/api/news", response_model=List[NewsArticleResponse])
async def get_news_articles(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles to return")
):
    """
    Get news articles with optional filters
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        query = session.query(NewsArticle)
        
        if symbol:
            query = query.filter(NewsArticle.symbol == symbol.upper())
        if source:
            query = query.filter(NewsArticle.source == source)
        
        articles = query.order_by(NewsArticle.published_date.desc()).limit(limit).all()
        
        return [
            NewsArticleResponse(
                id=article.id,
                article_id=article.article_id,
                symbol=article.symbol,
                title=article.title,
                content=article.content,
                source=article.source,
                url=article.url,
                author=article.author,
                published_date=article.published_date,
                collected_date=article.collected_date,
                sentiment_score=article.sentiment_score,
                relevance_score=article.relevance_score,
                metadata=article.metadata_
            )
            for article in articles
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news: {str(e)}")
    finally:
        session.close()


@app.post("/api/news/search", response_model=List[NewsArticleResponse])
async def search_news(request: NewsSearchRequest):
    """
    Semantic search for news articles using vector embeddings
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        news_service = get_news_service()
        articles = news_service.semantic_search(
            session=session,
            query=request.query,
            symbol=request.symbol,
            limit=request.limit
        )
        
        return [
            NewsArticleResponse(
                id=article.id,
                article_id=article.article_id,
                symbol=article.symbol,
                title=article.title,
                content=article.content,
                source=article.source,
                url=article.url,
                author=article.author,
                published_date=article.published_date,
                collected_date=article.collected_date,
                sentiment_score=article.sentiment_score,
                relevance_score=article.relevance_score,
                metadata=article.metadata_
            )
            for article in articles
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching news: {str(e)}")
    finally:
        session.close()


@app.get("/api/news/summary/{symbol}", response_model=List[NewsSummaryResponse])
async def get_news_summary(
    symbol: str,
    period: Optional[str] = Query("daily", description="Summary period (daily, weekly, monthly)"),
    limit: int = Query(5, ge=1, le=50, description="Number of summaries to return")
):
    """
    Get news summaries for a stock
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        query = session.query(NewsSummary).filter(
            NewsSummary.symbol == symbol.upper()
        )
        
        if period:
            query = query.filter(NewsSummary.period == period)
        
        summaries = query.order_by(NewsSummary.summary_date.desc()).limit(limit).all()
        
        return [
            NewsSummaryResponse(
                id=summary.id,
                symbol=summary.symbol,
                summary_date=summary.summary_date,
                period=summary.period,
                summary_text=summary.summary_text,
                key_events=summary.key_events,
                sentiment_trend=summary.sentiment_trend,
                overall_sentiment_score=summary.overall_sentiment_score,
                article_count=summary.article_count
            )
            for summary in summaries
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summaries: {str(e)}")
    finally:
        session.close()


@app.get("/api/graph", response_model=GraphDataResponse)
async def get_graph_data(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=500, description="Maximum entities to return")
):
    """
    Get graph data (nodes and edges) for visualization
    """
    session = db.get_session()
    if not session:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        news_service = get_news_service()
        graph_data = news_service.get_entity_graph(
            session=session,
            symbol=symbol,
            entity_type=entity_type,
            limit=limit
        )
        
        return GraphDataResponse(
            nodes=graph_data['nodes'],
            edges=graph_data['edges']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching graph data: {str(e)}")
    finally:
        session.close()


# ==================== Stock Notes Endpoints ====================

@app.get("/api/stocks/{symbol}/notes")
async def get_stock_notes(symbol: str):
    """Get all notes for a specific stock symbol"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        notes = StockNote.get_notes_by_symbol(db, symbol)
        return notes  # Already returns list of dicts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching notes: {str(e)}")


@app.post("/api/stocks/{symbol}/notes")
async def create_stock_note(symbol: str, request: dict):
    """Create a new note for a stock"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    content = request.get('content')
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Note content cannot be empty")
    
    try:
        note = StockNote.create_note(db, symbol, content)
        return note  # Already returns dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating note: {str(e)}")


@app.put("/api/notes/{note_id}")
async def update_stock_note(note_id: int, request: dict):
    """Update an existing note"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    content = request.get('content')
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Note content cannot be empty")
    
    try:
        note = StockNote.update_note(db, note_id, content)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note  # Already returns dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating note: {str(e)}")


@app.delete("/api/notes/{note_id}")
async def delete_stock_note(note_id: int):
    """Delete a note by ID"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        deleted = StockNote.delete_note(db, note_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"message": "Note deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting note: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
