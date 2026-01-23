"""
MCP Tool for News Analyst to save news to the Vector and Graph Database
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Data_Loader import PostgreSQLConnection
from NewsProcessingService import get_news_service


def save_news_to_database(
    symbol: str,
    title: str,
    content: str,
    source: str,
    url: Optional[str] = None,
    author: Optional[str] = None,
    published_date: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str:
    """
    Save a news article to the database with vector embeddings and entity extraction.
    This tool should be used by the News_Analyst agent to store analyzed news.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        title: News article title
        content: Full article content or summary
        source: News source (e.g., 'Twitter', 'Bloomberg', 'Reuters')
        url: Optional URL to the article
        author: Optional author name
        published_date: Optional publication date (ISO format string)
        metadata: Optional additional metadata (as dict)
    
    Returns:
        str: Success or error message
    """
    try:
        # Create database connection
        db = PostgreSQLConnection.create_connection()
        session = db.get_session()
        
        if not session:
            return "❌ Error: Could not connect to database"
        
        # Parse published date
        pub_date = None
        if published_date:
            try:
                pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pub_date = datetime.utcnow()
        else:
            pub_date = datetime.utcnow()
        
        # Get news processing service
        news_service = get_news_service()
        
        # Store article
        article = news_service.store_news_article(
            session=session,
            symbol=symbol.upper(),
            title=title,
            content=content,
            source=source,
            url=url,
            author=author,
            published_date=pub_date,
            metadata=metadata or {}
        )
        
        if article:
            return f"✅ Successfully saved news article for {symbol} (ID: {article.article_id}). Sentiment: {article.sentiment_score:.2f}"
        else:
            return "❌ Error: Failed to save news article"
            
    except Exception as e:
        return f"❌ Error saving news: {str(e)}"
    finally:
        if session:
            session.close()
        if db:
            db.close()


def create_news_summary(
    symbol: str,
    summary_text: str,
    period: str = "daily",
    sentiment_trend: Optional[str] = None,
    key_events: Optional[list] = None
) -> str:
    """
    Create a summary of news analysis for a stock.
    This tool should be used by the News_Analyst agent to store aggregated summaries.
    
    Args:
        symbol: Stock ticker symbol
        summary_text: Summary text describing the news analysis
        period: Time period (daily, weekly, monthly)
        sentiment_trend: Overall sentiment (positive, negative, neutral, mixed)
        key_events: List of key events (as list of dicts)
    
    Returns:
        str: Success or error message
    """
    try:
        from NewsGraphModels import NewsSummary
        
        # Create database connection
        db = PostgreSQLConnection.create_connection()
        session = db.get_session()
        
        if not session:
            return "❌ Error: Could not connect to database"
        
        # Get recent articles for this symbol
        from NewsGraphModels import NewsArticle
        recent_articles = session.query(NewsArticle).filter(
            NewsArticle.symbol == symbol.upper()
        ).order_by(NewsArticle.published_date.desc()).limit(50).all()
        
        # Calculate average sentiment
        avg_sentiment = None
        if recent_articles:
            sentiments = [a.sentiment_score for a in recent_articles if a.sentiment_score is not None]
            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)
        
        # Create summary
        summary = NewsSummary(
            symbol=symbol.upper(),
            summary_date=datetime.utcnow(),
            period=period,
            summary_text=summary_text,
            key_events=key_events or [],
            sentiment_trend=sentiment_trend,
            overall_sentiment_score=avg_sentiment,
            article_ids=[a.article_id for a in recent_articles],
            article_count=len(recent_articles)
        )
        
        session.add(summary)
        session.commit()
        
        return f"✅ Successfully created news summary for {symbol} (Period: {period}, Articles: {len(recent_articles)})"
        
    except Exception as e:
        if session:
            session.rollback()
        return f"❌ Error creating summary: {str(e)}"
    finally:
        if session:
            session.close()
        if db:
            db.close()


# Test function
if __name__ == "__main__":
    # Test saving a news article
    result = save_news_to_database(
        symbol="AAPL",
        title="Apple Announces New Product Line",
        content="Apple Inc. announced today a revolutionary new product line that is expected to boost revenue significantly.",
        source="Test",
        published_date=datetime.utcnow().isoformat()
    )
    print(result)
    
    # Test creating a summary
    result = create_news_summary(
        symbol="AAPL",
        summary_text="Overall positive sentiment for Apple with new product announcements driving optimism.",
        period="daily",
        sentiment_trend="positive",
        key_events=[{"event": "New product announcement", "impact": "positive"}]
    )
    print(result)
