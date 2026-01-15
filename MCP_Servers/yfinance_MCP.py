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
def get_historical_data(symbol: str, period: str = "1mo") -> list[dict[str, Any]]:
    """Get historical OHLCV data for `symbol`.

    Returns a list of dicts with keys: date, open, high, low, close, volume.
    """
    try:
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