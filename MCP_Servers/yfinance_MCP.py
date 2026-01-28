"""yfinance MCP server (FastMCP style).
- Each function is synchronous and importable for local scripts.
- The same functions are exposed as MCP tools via `@mcp.tool()`.
- Running this file starts an stdio MCP server.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional

import yfinance as yf
import pandas as pd
from mcp.server.fastmcp import FastMCP


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yfinance-mcp-server")

# Ensure this module emits logs even when imported into an app that already configured logging.
# Also prefer stdout (some apps redirect/hide stderr).
if not logger.handlers:
    _handler = logging.StreamHandler(stream=sys.stdout)
    _handler.setLevel(logging.INFO)
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)

logger.setLevel(logging.INFO)
logger.propagate = False  # don't rely on/root logger handlers & levels

#Helper Functions

def get_stock_info_payload(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info
    if not isinstance(info, dict):
        raise RuntimeError("yfinance returned a non-dict info payload")
    return info

def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    """json.dumps that won't fail on non-serializable yfinance values."""
    return json.dumps(obj, default=str, **kwargs)

mcp = FastMCP("yfinance-mcp-server")


@mcp.tool()
def fetch_stock_info(symbol: str) -> dict[str, Any]:
    """Fetch the full Stock Information Payload from yfinance."""
    info = get_stock_info_payload(symbol)
    return info



@mcp.tool()
def get_stock_price(symbol: str) -> float:
    """Returns the Stock Current Price, Currency, and Target Prices, 52 Week High/Low, Stock Recommendation & Prev Close in Json Format."""
    info = get_stock_info_payload(symbol)
    data = {
           "Name":info.get("shortName") or info.get("longName"),
           "Current Price": info.get("currentPrice"),
            "Currency": info.get("financialCurrency"),
            "Target High": info.get("targetHighPrice"),
            "Target Low": info.get("targetLowPrice"),
            "52 Week High": info.get("fiftyTwoWeekHigh"),
            "52 Week Low": info.get("fiftyTwoWeekLow"),
            "Recommendation": info.get("recommendationKey"),
            "Description": info.get("longBusinessSummary"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
    }    
    return data


@mcp.tool()
def get_historical_data(symbol: str, period: str = "1mo", use_db: bool = True) -> list[dict[str, Any]]:
    """Get historical OHLCV data for `symbol`.
    
    If use_db=True, checks database first and only fetches new data from yfinance if needed.
    Returns a list of dicts with keys: date, open, high, low, close, volume.
    
    Args:
        symbol: Stock ticker symbol
        period: Period to return (e.g., "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
        use_db: Whether to use database caching (default: True)
    """
    
    def parse_period_to_days(period: str) -> int:
        """Convert period string to approximate number of days."""
        period_map = {
            "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
            "1y": 365, "2y": 730, "5y": 1825, "10y": 3650,
            "ytd": 365, "max": 10000  # Use a large number for max
        }
        return period_map.get(period.lower(), 30)  # Default to 30 days
    
    try:
        if use_db:
            # Import here to avoid circular dependency
            from Data_Loader import PostgreSQLConnection, Stock_History
            from sqlalchemy import func, desc
            from datetime import datetime, timedelta
            
            requested_days = parse_period_to_days(period)
            
            db = PostgreSQLConnection()
            if db.connect():
                session = db.get_session()
                if session:
                    try:
                        # Get the last recorded date for this symbol
                        last_record = session.query(Stock_History).filter_by(
                            symbol=symbol
                        ).order_by(desc(Stock_History.date)).first()
                        
                        today = datetime.now().date()
                        
                        if last_record:
                            last_date = last_record.date.date() if hasattr(last_record.date, 'date') else last_record.date
                            
                            # If last record is today or recent, return DB data limited to requested period
                            if last_date >= today:
                                logger.info(f"Using cached data for {symbol} (up to date)")
                                cutoff_date = today - timedelta(days=requested_days)
                                
                                all_history = session.query(Stock_History).filter(
                                    Stock_History.symbol == symbol,
                                    Stock_History.date >= cutoff_date
                                ).order_by(Stock_History.date).all()
                                
                                data = []
                                for record in all_history:
                                    data.append({
                                        "date": record.date.strftime("%Y-%m-%d"),
                                        "open": float(record.open_price) if record.open_price else None,
                                        "high": float(record.high_price) if record.high_price else None,
                                        "low": float(record.low_price) if record.low_price else None,
                                        "close": float(record.close_price) if record.close_price else None,
                                        "volume": int(record.volume) if record.volume else None,
                                    })
                                session.close()
                                db.close()
                                return data
                            
                            # Fetch from (last_date - 1) to today
                            start_date = last_date - timedelta(days=1)
                            logger.info(f"Fetching new data for {symbol} from {start_date} to {today}")
                            
                            stock = yf.Ticker(symbol)
                            # Use start/end instead of period for incremental fetch
                            history = stock.history(start=start_date, end=today + timedelta(days=1))
                            
                            if not history.empty:
                                # Save new data to database
                                for date, row in history.iterrows():
                                    record_date = date.date() if hasattr(date, 'date') else date
                                    
                                    # Check if this date already exists
                                    existing = session.query(Stock_History).filter_by(
                                        symbol=symbol,
                                        date=date
                                    ).first()
                                    
                                    if existing:
                                        # Update existing record
                                        existing.open_price = float(row["Open"]) if row.get("Open") is not None else None
                                        existing.high_price = float(row["High"]) if row.get("High") is not None else None
                                        existing.low_price = float(row["Low"]) if row.get("Low") is not None else None
                                        existing.close_price = float(row["Close"]) if row.get("Close") is not None else None
                                        existing.volume = int(row["Volume"]) if row.get("Volume") is not None else None
                                    else:
                                        # Insert new record
                                        new_history = Stock_History(
                                            symbol=symbol,
                                            date=date,
                                            open_price=float(row["Open"]) if row.get("Open") is not None else None,
                                            close_price=float(row["Close"]) if row.get("Close") is not None else None,
                                            high_price=float(row["High"]) if row.get("High") is not None else None,
                                            low_price=float(row["Low"]) if row.get("Low") is not None else None,
                                            volume=int(row["Volume"]) if row.get("Volume") is not None else None
                                        )
                                        session.add(new_history)
                                
                                session.commit()
                                logger.info(f"Updated {len(history)} records for {symbol}")
                            
                            # Return data from database limited to requested period
                            cutoff_date = today - timedelta(days=requested_days)
                            all_history = session.query(Stock_History).filter(
                                Stock_History.symbol == symbol,
                                Stock_History.date >= cutoff_date
                            ).order_by(Stock_History.date).all()
                            
                            data = []
                            for record in all_history:
                                data.append({
                                    "date": record.date.strftime("%Y-%m-%d"),
                                    "open": float(record.open_price) if record.open_price else None,
                                    "high": float(record.high_price) if record.high_price else None,
                                    "low": float(record.low_price) if record.low_price else None,
                                    "close": float(record.close_price) if record.close_price else None,
                                    "volume": int(record.volume) if record.volume else None,
                                })
                            session.close()
                            db.close()
                            return data
                        
                        else:
                            # No records exist, fetch maximum available data from yfinance
                            logger.info(f"No historical data in DB for {symbol}, fetching maximum available data from yfinance")
                            stock = yf.Ticker(symbol)
                            history = stock.history(period="max")  # Fetch all available history
                            
                            if not history.empty:
                                # Save to database in batches to avoid parameter limit
                                batch_size = 100  # Insert 100 records at a time
                                records_to_insert = []
                                
                                for date, row in history.iterrows():
                                    records_to_insert.append({
                                        'symbol': symbol,
                                        'date': date,
                                        'open_price': float(row["Open"]) if row.get("Open") is not None else None,
                                        'close_price': float(row["Close"]) if row.get("Close") is not None else None,
                                        'high_price': float(row["High"]) if row.get("High") is not None else None,
                                        'low_price': float(row["Low"]) if row.get("Low") is not None else None,
                                        'volume': int(row["Volume"]) if row.get("Volume") is not None else None
                                    })
                                    
                                    # Insert in batches
                                    if len(records_to_insert) >= batch_size:
                                        try:
                                            session.bulk_insert_mappings(Stock_History, records_to_insert)
                                            session.commit()
                                            records_to_insert = []
                                        except Exception as batch_error:
                                            session.rollback()
                                            logger.warning(f"Batch insert failed for {symbol}, trying individual inserts: {str(batch_error)}")
                                            # Try inserting individually with conflict handling
                                            for record in records_to_insert:
                                                try:
                                                    existing = session.query(Stock_History).filter_by(
                                                        symbol=record['symbol'],
                                                        date=record['date']
                                                    ).first()
                                                    if not existing:
                                                        new_history = Stock_History(**record)
                                                        session.add(new_history)
                                                        session.commit()
                                                except Exception as e:
                                                    session.rollback()
                                                    continue
                                            records_to_insert = []
                                
                                # Insert remaining records
                                if records_to_insert:
                                    try:
                                        session.bulk_insert_mappings(Stock_History, records_to_insert)
                                        session.commit()
                                    except Exception as batch_error:
                                        session.rollback()
                                        logger.warning(f"Final batch insert failed for {symbol}, trying individual inserts: {str(batch_error)}")
                                        for record in records_to_insert:
                                            try:
                                                existing = session.query(Stock_History).filter_by(
                                                    symbol=record['symbol'],
                                                    date=record['date']
                                                ).first()
                                                if not existing:
                                                    new_history = Stock_History(**record)
                                                    session.add(new_history)
                                                    session.commit()
                                            except Exception as e:
                                                session.rollback()
                                                continue
                                
                                logger.info(f"Saved {len(history)} records for {symbol}")
                                
                                # Return only the requested period from the fetched data
                                today = datetime.now().date()
                                cutoff_date = today - timedelta(days=requested_days)
                                data = []
                                for date, row in history.iterrows():
                                    record_date = date.date() if hasattr(date, 'date') else date
                                    if record_date >= cutoff_date:
                                        data.append({
                                            "date": date.strftime("%Y-%m-%d"),
                                            "open": float(row["Open"]) if row.get("Open") is not None else None,
                                            "high": float(row["High"]) if row.get("High") is not None else None,
                                            "low": float(row["Low"]) if row.get("Low") is not None else None,
                                            "close": float(row["Close"]) if row.get("Close") is not None else None,
                                            "volume": int(row["Volume"]) if row.get("Volume") is not None else None,
                                        })
                                session.close()
                                db.close()
                                return data
                            
                            session.close()
                            db.close()
                            return []
                    
                    except Exception as e:
                        session.rollback()
                        session.close()
                        db.close()
                        logger.error(f"Database error for {symbol}, falling back to direct yfinance: {str(e)}")
                        # Fall through to direct yfinance fetch
        
        # Direct fetch from yfinance (when use_db=False or database error)
        stock = yf.Ticker(symbol)
        history = stock.history(period=period)
        if history.empty:
            return []

        data: list[dict[str, Any]] = []
        for date, row in history.iterrows():
            data.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]) if row.get("Open") is not None else None,
                    "high": float(row["High"]) if row.get("High") is not None else None,
                    "low": float(row["Low"]) if row.get("Low") is not None else None,
                    "close": float(row["Close"]) if row.get("Close") is not None else None,
                    "volume": int(row["Volume"]) if row.get("Volume") is not None else None,
                }
            )
        return data
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        raise RuntimeError(f"Failed to fetch historical data: {str(e)}")

def get_batch_historical_data(symbols: list[str], period: str = "1mo") -> dict[str, list[dict[str, Any]]]:
    """Get historical data for multiple symbols at once using yfinance batch download.
    
    This is much faster than calling get_historical_data() multiple times individually.
    yfinance will download all symbols in parallel.
    
    Args:
        symbols: List of stock ticker symbols
        period: Period to return (e.g., "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
    
    Returns:
        Dictionary mapping each symbol to its historical data list
    """
    try:
        if not symbols:
            return {}
        
        logger.info(f"Batch downloading historical data for {len(symbols)} symbols")
        
        # Use yfinance download function for batch downloading
        # This downloads all symbols in parallel
        data = yf.download(
            tickers=" ".join(symbols),
            period=period,
            group_by='ticker',
            threads=True,  # Enable multi-threading
            progress=False  # Disable progress bar for cleaner output
        )
        
        results = {}
        
        # Handle single symbol case
        if len(symbols) == 1:
            symbol = symbols[0]
            if not data.empty:
                history_list = []
                for date, row in data.iterrows():
                    history_list.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "open": float(row["Open"]) if row.get("Open") is not None and not pd.isna(row.get("Open")) else None,
                        "high": float(row["High"]) if row.get("High") is not None and not pd.isna(row.get("High")) else None,
                        "low": float(row["Low"]) if row.get("Low") is not None and not pd.isna(row.get("Low")) else None,
                        "close": float(row["Close"]) if row.get("Close") is not None and not pd.isna(row.get("Close")) else None,
                        "volume": int(row["Volume"]) if row.get("Volume") is not None and not pd.isna(row.get("Volume")) else None,
                    })
                results[symbol] = history_list
            else:
                results[symbol] = []
        else:
            # Multiple symbols - data is grouped by ticker
            for symbol in symbols:
                try:
                    if symbol in data.columns.levels[0]:
                        symbol_data = data[symbol]
                        history_list = []
                        for date, row in symbol_data.iterrows():
                            history_list.append({
                                "date": date.strftime("%Y-%m-%d"),
                                "open": float(row["Open"]) if row.get("Open") is not None and not pd.isna(row.get("Open")) else None,
                                "high": float(row["High"]) if row.get("High") is not None and not pd.isna(row.get("High")) else None,
                                "low": float(row["Low"]) if row.get("Low") is not None and not pd.isna(row.get("Low")) else None,
                                "close": float(row["Close"]) if row.get("Close") is not None and not pd.isna(row.get("Close")) else None,
                                "volume": int(row["Volume"]) if row.get("Volume") is not None and not pd.isna(row.get("Volume")) else None,
                            })
                        results[symbol] = history_list
                    else:
                        logger.warning(f"No data returned for {symbol}")
                        results[symbol] = []
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    results[symbol] = []
        
        logger.info(f"Batch download completed for {len(results)} symbols")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch historical data download: {str(e)}")
        # Return empty dict for all symbols on error
        return {symbol: [] for symbol in symbols}


@mcp.tool()
def search_stocks(query: str, limit: int = 5) -> dict[str, Any]:
    """Search for stocks by company name or keyword."""
    try:
        from yfinance.search import Search

        search_results = Search(query=query, max_results=limit)
        results: dict[str, Any] = {}

        if search_results.quotes:
            results["quotes"] = []
            for quote in search_results.quotes[:limit]:
                if not isinstance(quote, dict):
                    continue
                results["quotes"].append(
                    {
                        "symbol": quote.get("symbol"),
                        "name": quote.get("shortname", quote.get("longname")),
                        "exchange": quote.get("exchange"),
                        "price": quote.get("regularMarketPrice"),
                    }
                )

        if search_results.news:
            results["news"] = []
            for news in search_results.news[:limit]:
                if not isinstance(news, dict):
                    continue
                results["news"].append(
                    {
                        "title": news.get("title"),
                        "publisher": news.get("publisher"),
                        "link": news.get("link"),
                    }
                )

        return results
    except Exception as e:
        logger.error(f"Error searching stocks for query '{query}': {str(e)}")
        raise RuntimeError(f"Failed to search stocks: {str(e)}")


@mcp.tool()
def get_news(symbol: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get normalized news items for a symbol."""
    try:
        limit_int = max(0, int(limit))
    except Exception:
        limit_int = 10

    try:
        stock = yf.Ticker(symbol)
        news_items = getattr(stock, "news", None) or []
        if not isinstance(news_items, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in news_items[:limit_int]:
            if not isinstance(item, dict):
                continue

            content = item.get("content") if isinstance(item.get("content"), dict) else {}

            title = item.get("title") or content.get("title")
            provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
            publisher = item.get("publisher") or provider.get("displayName")

            canonical = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
            click = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
            link = item.get("link") or click.get("url") or canonical.get("url")

            published_ts = item.get("providerPublishTime") or content.get("pubDate")
            published_at: Optional[str] = None
            if isinstance(published_ts, (int, float)):
                try:
                    published_at = datetime.utcfromtimestamp(float(published_ts)).strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    published_at = None
            elif isinstance(published_ts, str) and published_ts:
                published_at = published_ts

            row = {"title": title, "publisher": publisher, "link": link, "published_at": published_at}
            if any(v is not None for v in row.values()):
                normalized.append(row)

        return normalized
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {str(e)}")
        raise RuntimeError(f"Failed to fetch news: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport="stdio")