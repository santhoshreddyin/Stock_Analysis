from MCP_Servers.User_Notifications_MCP import send_telegram_message
from Data_Loader import PostgreSQLConnection, Stock_History
from StockDataModels import StockDataModel
from typing import Any
import math
from datetime import datetime, timedelta
import logging
from pathlib import Path
import time
from tqdm import tqdm
from sqlalchemy import func, text
from MCP_Servers.yfinance_MCP import get_batch_historical_data
import pandas as pd

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
console_handler.setLevel(logging.INFO)  # Changed to INFO to see progress
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
    # Start timing
    start_time = time.time()
    
    # Initialize database connection
    db = PostgreSQLConnection()
    
    # Check if connection is successful
    if not db.connect():
        logger.error("Failed to connect to database")
        logger.error("Please check your database configuration and connection settings")
        elapsed_time = time.time() - start_time
        return {
            "total_stocks": 0,
            "stocks_processed": 0,
            "stocks_skipped": 0,
            "alerts_generated": 0,
            "timestamp": datetime.now(),
            "elapsed_time": elapsed_time,
            "error": "Database connection failed"
        }

    
    # Get stocks from database
    Stocks = db.get_all_stocks(Frequency=Frequency)
    
    if Stocks is None or len(Stocks) == 0:
        logger.warning(f"No stocks found with Frequency='{Frequency}'")
        logger.warning("Please check if stocks are loaded in the database")
        db.close()
        elapsed_time = time.time() - start_time
        return {
            "total_stocks": 0,
            "stocks_processed": 0,
            "stocks_skipped": 0,
            "alerts_generated": 0,
            "timestamp": datetime.now(),
            "elapsed_time": elapsed_time,
            "error": f"No stocks found with Frequency={Frequency}"
        }
    
    # Extract stock symbols from Stock_List objects
    stock_symbols = [stock.symbol for stock in Stocks]
    
    logger.info(f"Found {len(stock_symbols)} stocks to monitor")
    
    # Process stocks in chunks to avoid rate limits
    BATCH_SIZE = 500
    stock_models = {}
    
    logger.info(f"Processing stocks in batches of {BATCH_SIZE}...")
    for i in range(0, len(stock_symbols), BATCH_SIZE):
        chunk = stock_symbols[i:i+BATCH_SIZE]
        chunk_num = (i // BATCH_SIZE) + 1
        total_chunks = (len(stock_symbols) + BATCH_SIZE - 1) // BATCH_SIZE
        
        logger.info(f"Batch {chunk_num}/{total_chunks}: Processing {len(chunk)} stocks...")
        
        # Check Stock_History for latest date for ALL stocks in the chunk first
        session = db.get_session()
        if not session:
            logger.error("Failed to get database session")
            continue
        
        try:
            # Get the latest history date for ALL stocks in the chunk with a SINGLE query
            today = datetime.now().date()
            stock_data_needs = {}
            
            logger.info(f"  Querying database for latest history dates (single query for all {len(chunk)} stocks)...")
            
            # Use a single optimized query with GROUP BY to get latest dates
            from sqlalchemy import and_
            
            # Get all latest records for stocks in this chunk in ONE query
            latest_records = session.query(
                Stock_History.symbol,
                func.max(Stock_History.date).label('latest_date')
            ).filter(
                Stock_History.symbol.in_(chunk)
            ).group_by(Stock_History.symbol).all()
            
            # Create a dict of latest dates
            latest_dates_dict = {record.symbol: record.latest_date for record in latest_records}
            
            logger.info(f"  Found history for {len(latest_dates_dict)}/{len(chunk)} stocks")
            
            # Now process all stocks
            for symbol in chunk:
                if symbol in latest_dates_dict:
                    latest_date = latest_dates_dict[symbol]
                    latest_date = latest_date.date() if hasattr(latest_date, 'date') else latest_date
                    days_since_update = (today - latest_date).days
                    stock_data_needs[symbol] = {'days': days_since_update, 'latest_date': latest_date}
                else:
                    # No history exists
                    stock_data_needs[symbol] = {'days': 365, 'latest_date': None}
            
            # Organize stocks into groups based on days needed
            groups = {
                'recent': [],      # <7 days - can batch 200 at a time
                'medium': [],      # 7-30 days - batch 100 at a time
                'old': []          # >30 days or no history - batch 50 at a time
            }
            
            for symbol, info in stock_data_needs.items():
                days = info['days']
                if days < 7:
                    groups['recent'].append(symbol)
                elif days <= 30:
                    groups['medium'].append(symbol)
                else:
                    groups['old'].append(symbol)
            
            logger.info(f"  Stock groups: recent(<7d)={len(groups['recent'])}, medium(7-30d)={len(groups['medium'])}, old(>30d)={len(groups['old'])}")
            
            # Process each group with appropriate batch size
            all_batch_history = {}
            
            # Process recent stocks (large batches)
            if groups['recent']:
                recent_batch_size = 200
                logger.info(f"  Processing {len(groups['recent'])} recent stocks in batches of {recent_batch_size}...")
                for idx in range(0, len(groups['recent']), recent_batch_size):
                    sub_batch = groups['recent'][idx:idx + recent_batch_size]
                    logger.info(f"    Downloading {len(sub_batch)} recent stocks (7d period)...")
                    group_history = get_batch_historical_data(sub_batch, period='7d')
                    all_batch_history.update(group_history)
                    if idx + recent_batch_size < len(groups['recent']):
                        time.sleep(1)  # Short delay between sub-batches
            
            # Process medium stocks (medium batches)
            if groups['medium']:
                medium_batch_size = 100
                logger.info(f"  Processing {len(groups['medium'])} medium stocks in batches of {medium_batch_size}...")
                for idx in range(0, len(groups['medium']), medium_batch_size):
                    sub_batch = groups['medium'][idx:idx + medium_batch_size]
                    logger.info(f"    Downloading {len(sub_batch)} medium stocks (1mo period)...")
                    group_history = get_batch_historical_data(sub_batch, period='1mo')
                    all_batch_history.update(group_history)
                    if idx + medium_batch_size < len(groups['medium']):
                        time.sleep(1)
            
            # Process old stocks (small batches)
            if groups['old']:
                old_batch_size = 50
                logger.info(f"  Processing {len(groups['old'])} old stocks in batches of {old_batch_size}...")
                for idx in range(0, len(groups['old']), old_batch_size):
                    sub_batch = groups['old'][idx:idx + old_batch_size]
                    logger.info(f"    Downloading {len(sub_batch)} old stocks (1y period)...")
                    group_history = get_batch_historical_data(sub_batch, period='1y')
                    all_batch_history.update(group_history)
                    if idx + old_batch_size < len(groups['old']):
                        time.sleep(2)  # Longer delay for old stocks
            
            batch_history = all_batch_history
            logger.info(f"  Collected history for {len(batch_history)} stocks")
            
            # Upsert data into Stock_History table using bulk operations
            logger.info(f"  Upserting historical data to database...")
            
            # Prepare all records for bulk upsert
            logger.info(f"  Preparing records for {len(chunk)} stocks...")
            records_to_upsert = []
            for symbol in chunk:
                history_data = batch_history.get(symbol, [])
                
                if not history_data:
                    logger.debug(f"  {symbol}: No data received")
                    continue
                
                for record in history_data:
                    try:
                        record_date = datetime.strptime(record['date'], '%Y-%m-%d').date()
                        records_to_upsert.append({
                            'symbol': symbol,
                            'date': record_date,
                            'open_price': record.get('open'),
                            'high_price': record.get('high'),
                            'low_price': record.get('low'),
                            'close_price': record.get('close'),
                            'volume': record.get('volume')
                        })
                    except Exception as e:
                        logger.error(f"  Error parsing {symbol} for {record.get('date')}: {str(e)}")
                        continue
            
            # Bulk upsert using session.merge for simplicity
            logger.info(f"  Prepared {len(records_to_upsert)} total records for upsert")
            if records_to_upsert:
                try:
                    # Process records in chunks for better performance
                    chunk_size = 500
                    total_upserted = 0
                    
                    for idx in range(0, len(records_to_upsert), chunk_size):
                        record_chunk = records_to_upsert[idx:idx + chunk_size]
                        logger.info(f"    Upserting chunk {idx//chunk_size + 1}/{(len(records_to_upsert) + chunk_size - 1)//chunk_size} ({len(record_chunk)} records)...")
                        
                        # Use bulk insert with ON CONFLICT DO NOTHING for speed
                        # Then update existing records separately
                        for record in record_chunk:
                            # Try to find existing record
                            existing = session.query(Stock_History).filter_by(
                                symbol=record['symbol'],
                                date=record['date']
                            ).first()
                            
                            if existing:
                                # Update existing
                                existing.open_price = record['open_price']
                                existing.high_price = record['high_price']
                                existing.low_price = record['low_price']
                                existing.close_price = record['close_price']
                                existing.volume = record['volume']
                            else:
                                # Insert new
                                new_record = Stock_History(**record)
                                session.add(new_record)
                        
                        session.flush()  # Flush this chunk
                        total_upserted += len(record_chunk)
                    
                    session.commit()
                    logger.info(f"  Batch {chunk_num}: Upserted {total_upserted} records")
                    
                except Exception as e:
                    logger.error(f"  Bulk upsert failed: {str(e)}")
                    session.rollback()
                    raise
            
            # Create StockDataModel instances from the already-downloaded batch_history data
            # No need to fetch from yfinance again!
            logger.info(f"  Creating StockDataModel instances from cached data for {len(chunk)} stocks...")
            
            for symbol in chunk:
                try:
                    # Create instance without auto-fetching
                    stock = StockDataModel(symbol, fetch_data=False)
                    
                    # Use the already-downloaded historical data from batch_history
                    history_data = batch_history.get(symbol, [])
                    if history_data:
                        stock.history_df = pd.DataFrame(history_data)
                        
                        # Calculate technical indicators
                        stock.history_df['close'] = pd.to_numeric(stock.history_df['close'], errors='coerce')
                        stock.history_df['volume'] = pd.to_numeric(stock.history_df['volume'], errors='coerce')
                        
                        # Set current price from latest close
                        if len(stock.history_df) > 0:
                            stock.current_price = float(stock.history_df['close'].iloc[-1])
                        
                        # Calculate moving averages
                        stock.history_df['50_MA'] = stock.history_df['close'].rolling(window=50).mean()
                        stock.history_df['200_MA'] = stock.history_df['close'].rolling(window=200).mean()
                        
                        # Set technical indicators
                        if len(stock.history_df) >= 50:
                            stock.ma_50 = stock.history_df['50_MA'].iloc[-1]
                        if len(stock.history_df) >= 200:
                            stock.ma_200 = stock.history_df['200_MA'].iloc[-1]
                        
                        stock.average_volume = stock.history_df['volume'].rolling(window=50).mean().iloc[-1]
                        
                        # Calculate price change
                        if len(stock.history_df) >= 2:
                            stock.previous_close = float(stock.history_df['close'].iloc[-2])
                            if stock.previous_close and stock.current_price:
                                stock.price_change_percent = ((stock.current_price - stock.previous_close) / stock.previous_close) * 100
                        
                        stock.last_updated = datetime.now()
                        stock.data_fetch_success = True
                    else:
                        stock.data_fetch_success = False
                    
                    stock_models[symbol] = stock
                    
                except Exception as e:
                    logger.error(f"  Error creating StockDataModel for {symbol}: {str(e)}")
                    # Create a failed instance
                    stock = StockDataModel(symbol, fetch_data=False)
                    stock.data_fetch_success = False
                    stock_models[symbol] = stock
            
            logger.info(f"  Batch {chunk_num}: Created {len(chunk)} StockDataModel instances")
            
        except Exception as e:
            logger.error(f"Error processing batch {chunk_num}: {str(e)}")
            session.rollback()
        finally:
            session.close()
        
        # Small delay between batches to avoid rate limiting
        if i + BATCH_SIZE < len(stock_symbols):
            time.sleep(2)
    
    logger.info(f"Completed batch downloading for all {len(stock_symbols)} stocks")
    
    stocks_processed = 0
    stocks_skipped = 0
    alerts_generated = 0

    # Process stocks with progress bar
    for stock_symbol in tqdm(stock_symbols, desc="Processing stocks", unit="stock"):
        logger.info(f"Processing {stock_symbol}...")
        
        # Get pre-fetched StockDataModel instance
        stock = stock_models.get(stock_symbol)
        
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
    
    # Calculate timing statistics
    elapsed_time = time.time() - start_time
    avg_time_per_stock = elapsed_time / len(stock_symbols) if len(stock_symbols) > 0 else 0
    
    # Return summary statistics
    return {
        "total_stocks": len(stock_symbols),
        "stocks_processed": stocks_processed,
        "stocks_skipped": stocks_skipped,
        "alerts_generated": alerts_generated,
        "timestamp": datetime.now(),
        "elapsed_time": elapsed_time,
        "avg_time_per_stock": avg_time_per_stock
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
    
    # Display timing information
    if 'elapsed_time' in results:
        elapsed = results['elapsed_time']
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        logger.info(f"Total Execution Time:     {elapsed_str} ({elapsed:.2f} seconds)")
        
        if 'avg_time_per_stock' in results:
            avg_time = results['avg_time_per_stock']
            logger.info(f"Avg Time per Stock:       {avg_time:.2f} seconds")
    
    logger.info("=" * 70)