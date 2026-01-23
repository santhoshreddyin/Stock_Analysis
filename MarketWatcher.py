from MCP_Servers.User_Notifications_MCP import send_telegram_message
from Data_Loader import PostgreSQLConnection
from StockDataModels import StockDataModel
from typing import Any
import math
from datetime import datetime
import logging
from pathlib import Path

# Configure logging to both file and console
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Capture all levels

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
simple_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler - detailed logs (DEBUG level and above)
file_handler = logging.FileHandler(
    log_dir / f"market_watcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)

# Console handler - only warnings and errors (WARNING level and above)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(simple_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Prevent propagation to root logger
logger.propagate = False


def Monitor_Market(Alert_Threshold: float = 2.0, Alerts_Enabled: bool = False, Frequency: str = "Daily"):
    """
    Monitor stock market for alerts and updates.
    All data is stored in the database - no Excel files used.
    
    Args:
        Alert_Threshold: Price change threshold percentage for alerts
        Alerts_Enabled: Whether to send Telegram alerts
        Frequency: Stock selection frequency ("Daily", "Weekly", "Monthly")
    """
    # Initialize database connection
    db = PostgreSQLConnection()
    
    # Check if connection is successful
    if not db.connect():
        logger.error("Failed to connect to database")
        logger.error("Please check your database configuration and connection settings")
        return {
            "total_stocks": 0,
            "stocks_processed": 0,
            "stocks_skipped": 0,
            "alerts_generated": 0,
            "timestamp": datetime.now(),
            "error": "Database connection failed"
        }

    
    # Get stocks from database
    Stocks = db.get_all_stocks(Frequency=Frequency)
    
    if Stocks is None or len(Stocks) == 0:
        logger.warning(f"No stocks found with Frequency='{Frequency}'")
        logger.warning("Please check if stocks are loaded in the database")
        db.close()
        return {
            "total_stocks": 0,
            "stocks_processed": 0,
            "stocks_skipped": 0,
            "alerts_generated": 0,
            "timestamp": datetime.now(),
            "error": f"No stocks found with Frequency={Frequency}"
        }
    
    # Extract stock symbols from Stock_List objects
    stock_symbols = [stock.symbol for stock in Stocks]
    
    logger.info(f"Found {len(stock_symbols)} stocks to monitor")
    
    stocks_processed = 0
    stocks_skipped = 0
    alerts_generated = 0

    for stock_symbol in stock_symbols:
        logger.info(f"Processing {stock_symbol}...")
        
        # Create StockDataModel instance - automatically fetches all data
        stock = StockDataModel(symbol=stock_symbol)
        
        # Check if data fetch was successful
        if not stock.data_fetch_success or stock.history_df is None or stock.history_df.empty:
            logger.warning(f"Skipping {stock_symbol} - No data available")
            stocks_skipped += 1
            continue
        
        stocks_processed += 1
        Bullish_Alert = False

        # Check for Bullish Crossover Alert using StockDataModel methods
        if stock.has_technical_data() and stock.current_price is not None:
            if stock.has_bullish_crossover_signal():
                message = (f"Bullish Crossover Alert!: {stock.symbol}\n"
                           f"Current Price: {stock.current_price}\n"
                           f"50-day MA: {stock.ma_50}\n"
                           f"200-day MA: {stock.ma_200}\n")
                Bullish_Alert = True
                alerts_generated += 1
                if Alerts_Enabled:
                    logger.info("Sending Telegram Alert for Bullish Crossover")
                    send_telegram_message(message=message)
                # Save alert to database
                if db:
                    db.add_alert(stock.symbol, "Bullish Crossover", message, "Sent")
                logger.info(message)
            else:
                logger.debug(f"No alert for {stock.symbol}. Current Price: {stock.current_price}, 50-day MA: {stock.ma_50}, 200-day MA: {stock.ma_200}")

        # Check for significant price change using StockDataModel methods
        if stock.has_significant_price_change(Alert_Threshold):
            direction = "increased" if stock.price_change_percent > 0 else "decreased"
            message = (f"Price Change Alert!: {stock.symbol}\n"
                       f"Previous Close: {stock.previous_close:.1f}\n"
                       f"Current Price: {stock.current_price:.1f}\n"
                       f"Price Change: {stock.price_change_percent:.1f}%\n")
            alerts_generated += 1
            if Alerts_Enabled:
                logger.info("Sending Telegram Alert for Price Change")
                send_telegram_message(message=message)
            # Save alert to database
            db.add_alert(stock.symbol, "Price Change", message, "Sent")
            logger.info(message)
        else:
            if stock.price_change_percent is not None:
                logger.debug(f"No significant price change for {stock.symbol}. Change: {stock.price_change_percent:.1f}%")

        # Update database with stock price data
        db.update_stock_price(
            symbol=stock.symbol,
            current_price=stock.current_price,
            recommendation=stock.recommendation,
            target_low=stock.target_low,
            target_high=stock.target_high,
            week52_low=stock.week52_low,
            week52_high=stock.week52_high,
            avg_volume=int(stock.average_volume) if stock.average_volume is not None and not math.isnan(stock.average_volume) else None
        )

    # Close database connection
    db.close()
    
    # Return summary statistics
    return {
        "total_stocks": len(stock_symbols),
        "stocks_processed": stocks_processed,
        "stocks_skipped": stocks_skipped,
        "alerts_generated": alerts_generated,
        "timestamp": datetime.now()
    }


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("STOCK MARKET MONITOR - Database-Driven")
    logger.info("=" * 70)
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log file: logs/market_watcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Run market monitoring
    results = Monitor_Market(Alert_Threshold=3.0, Alerts_Enabled=False, Frequency="Daily")
    
    # Display results
    logger.info("=" * 70)
    logger.info("MONITORING RESULTS")
    logger.info("=" * 70)
    
    # Check for errors
    if "error" in results:
        logger.error(f"ERROR: {results['error']}")
        logger.error("Please ensure:")
        logger.error("  1. PostgreSQL database is running")
        logger.error("  2. Database credentials are correct")
        logger.error("  3. Stocks table is populated")
        logger.info("=" * 70)
        exit(1)
    logger.info("=" * 70)
    logger.info(f"Total Stocks in Universe: {results['total_stocks']}")
    logger.info(f"Successfully Processed:   {results['stocks_processed']}")
    logger.info(f"Skipped (No Data):        {results['stocks_skipped']}")
    logger.info(f"Alerts Generated:         {results['alerts_generated']}")
    logger.info(f"End Time:                 {results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)