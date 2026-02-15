"""
Real-Time Updates - Monitor stock prices and send alerts on changes
Independently executable batch job for real-time price monitoring
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import logging
import time
from typing import Dict, List, Tuple
from tqdm import tqdm
import pandas as pd
import yfinance as yf
from Data_Loader import PostgreSQLConnection, Stock_History
from Batch.AlertQueue import AlertQueue
from AlertTypes import AlertType
from StockDataModels import StockDataModel
from datetime import datetime, timedelta

# Suppress yfinance logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# Configure logging
Path("logs").mkdir(exist_ok=True)
file_handler = logging.FileHandler(f"logs/realtime_updates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)


class RealTimeUpdater:
    """
    Monitor real-time stock prices and send alerts on changes.
    
    Note: This module only tracks PRICE changes. Recommendation monitoring
    is not available in real-time mode because yf.download() only provides
    OHLCV data. Recommendation monitoring should be done in History Fetcher
    which uses ticker.info (rate-limited, suitable for daily batch jobs).
    """
    
    def __init__(self, db: PostgreSQLConnection):
        self.db = db
        self.alert_queue = AlertQueue(db)
        self.price_alerts = []
    
    def run(self, frequency: str = "Daily", batch_size: int = 200, alert_threshold: float = 2.0) -> Dict:
        """
        Main execution: Monitor stocks and send alerts
        
        Args:
            frequency: Stock frequency to monitor ("Daily", "Weekly", "Monthly")
            batch_size: Number of stocks to process per batch
            alert_threshold: Minimum price change % to trigger alert
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        
        logger.info(f"{'='*15}\nREAL-TIME MONITORING - {frequency} Stocks\n{'='*15}")
        
        # Get stocks from database
        stocks = self.db.get_all_stocks(Frequency=frequency)
        if not stocks:
            logger.warning(f"No {frequency} stocks found")
            return {'stocks_updated': 0, 'price_alerts': 0, 'elapsed_time': time.time() - start_time}
        
        symbols = [stock.symbol for stock in stocks]
        logger.info(f"Monitoring {len(symbols)} {frequency} stocks (Alert threshold: {alert_threshold}%)")
        
        # Get latest history records from DB
        latest_history = self._get_latest_history(symbols)
        
        # Fetch current prices from yfinance
        current_prices = self._fetch_current_prices(symbols, batch_size)
        
        # Compare and generate alerts
        updates = self._compare_and_alert(latest_history, current_prices, alert_threshold)
        
        # Update database
        updated_count = self._update_database(updates)
        
        # Send alerts
        self._send_alerts()
        
        # Results
        result = {
            'stocks_updated': updated_count,
            'price_alerts': len(self.price_alerts),
            'elapsed_time': time.time() - start_time,
            'total_stocks': len(symbols)
        }
        
        logger.info(f"{'='*15}")
        logger.info(f"Updated: {updated_count}/{len(symbols)} stocks")
        logger.info(f"Price Alerts: {len(self.price_alerts)}")
        logger.info(f"Execution Time: {str(timedelta(seconds=int(result['elapsed_time'])))} ({result['elapsed_time']:.2f}s)")
        logger.info(f"{'='*15}")
        
        return result

    def fetch_and_update(self, symbols: List[str], batch_size: int = 200, alert_threshold: float = 2.0) -> Dict:
        """
        Fetch current prices, update DB, enqueue alerts, and build StockDataModel instances.

        Args:
            symbols: List of stock symbols
            batch_size: Number of stocks to process per batch
            alert_threshold: Minimum price change % to trigger alert

        Returns:
            Dictionary with update stats and stock models for alert processing
        """
        # Get latest history records from DB
        latest_history = self._get_latest_history(symbols)

        # Fetch current prices from yfinance
        current_prices = self._fetch_current_prices(symbols, batch_size)

        # Compare and generate alerts
        updates = self._compare_and_alert(latest_history, current_prices, alert_threshold)

        # Update database
        updated_count = self._update_database(updates)

        # Send alerts
        self._send_alerts()

        # Build StockDataModel instances for alert processing
        stock_models = self._build_stock_models(symbols, current_prices)

        return {
            'stocks_updated': updated_count,
            'price_alerts': len(self.price_alerts),
            'stock_models': stock_models,
            'total_stocks': len(symbols)
        }
    
    def _get_latest_history(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get latest price record for each stock from database
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbol to latest price record
        """
        logger.info("Fetching current prices from database...")
        
        latest_records = {}
        
        for symbol in tqdm(symbols, desc="Getting DB prices", ncols=80, mininterval=0.5):
            try:
                price_record = self.db.get_stock_price(symbol)
                
                if price_record and price_record.current_price:
                    latest_records[symbol] = {
                        'close': float(price_record.current_price),
                        'recommendation': price_record.Recommendation,
                        'date': price_record.Update_Timestamp
                    }
                else:
                    latest_records[symbol] = None
                    
            except Exception as e:
                logger.error(f"Error fetching history for {symbol}: {e}")
                latest_records[symbol] = None
        
        found = len([v for v in latest_records.values() if v is not None])
        logger.info(f"Found history for {found}/{len(symbols)} stocks")
        return latest_records
    
    def _fetch_current_prices(self, symbols: List[str], batch_size: int) -> Dict[str, Dict]:
        """
        Fetch current prices from yfinance using yf.download batch mode
        
        Args:
            symbols: List of stock symbols
            batch_size: Number of symbols per batch
            
        Returns:
            Dictionary mapping symbol to current price data
        """
        logger.info(f"Fetching current prices from yfinance (batch download, {batch_size} per batch)...")
        
        all_prices = {}
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        
        print()  # New line before progress bar
        pbar = tqdm(total=len(symbols), desc="Fetching prices", ncols=80)
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            try:
                # Use yf.download for true batch downloading (parallel)
                data = yf.download(
                    tickers=" ".join(batch),
                    period="2d",  # Get 2 days for previous close comparison
                    progress=False,
                    threads=True
                )
                
                if not data.empty:
                    # Handle single symbol case
                    if len(batch) == 1:
                        symbol = batch[0]
                        if len(data) >= 1:
                            latest = data.iloc[-1]
                            prev = data.iloc[-2] if len(data) >= 2 else latest
                            all_prices[symbol] = {
                                'current_price': float(latest['Close']) if not pd.isna(latest['Close']) else None,
                                'previous_close': float(prev['Close']) if not pd.isna(prev['Close']) else None,
                                'recommendation': None,
                                'target_low': None,
                                'target_high': None,
                                'week52_low': None,
                                'week52_high': None
                            }
                    else:
                        # Multiple symbols - data has multi-level columns
                        for symbol in batch:
                            try:
                                if symbol in data['Close'].columns:
                                    closes = data['Close'][symbol]
                                    if len(closes) >= 1:
                                        latest_close = closes.iloc[-1]
                                        prev_close = closes.iloc[-2] if len(closes) >= 2 else latest_close
                                        if not pd.isna(latest_close):
                                            all_prices[symbol] = {
                                                'current_price': float(latest_close),
                                                'previous_close': float(prev_close) if not pd.isna(prev_close) else None,
                                                'recommendation': None,
                                                'target_low': None,
                                                'target_high': None,
                                                'week52_low': None,
                                                'week52_high': None
                                            }
                            except Exception:
                                pass
                                
            except Exception as e:
                logger.debug(f"Error in batch {i//batch_size + 1}: {e}")
            
            pbar.update(len(batch))
            
            # Rate limit between batches
            if i + batch_size < len(symbols):
                time.sleep(2)
        
        pbar.close()
        print()  # New line after progress bar
        
        logger.info(f"Fetched prices for {len(all_prices)}/{len(symbols)} stocks")
        return all_prices
    
    def _compare_and_alert(self, latest_history: Dict, current_prices: Dict, threshold: float) -> List[Dict]:
        """
        Compare current prices with history and generate alerts
        
        Note: Recommendation change detection not available in real-time mode.
        yf.download() only provides OHLCV data. Recommendation data requires
        ticker.info calls which are rate-limited. Recommendation monitoring
        should be done in History Fetcher job.
        
        Args:
            latest_history: Latest history records from DB
            current_prices: Current prices from yfinance
            threshold: Minimum price change % for alert
            
        Returns:
            List of update records for database
        """
        logger.info("Comparing prices and generating alerts...")
        
        updates = []
        
        for symbol in tqdm(latest_history.keys(), desc="Comparing"):
            history = latest_history.get(symbol)
            current = current_prices.get(symbol)
            
            if not history or not current:
                continue
            
            try:
                previous_close = history['close']
                current_price = current.get('current_price')
                
                if not current_price:
                    continue
                
                # Calculate price change
                price_change_pct = ((current_price - previous_close) / previous_close) * 100
                
                # Check for significant price change
                if abs(price_change_pct) >= threshold:
                    self.price_alerts.append({
                        'symbol': symbol,
                        'previous_close': previous_close,
                        'current_price': current_price,
                        'change_percent': price_change_pct
                    })
                
                # Note: Recommendation change detection disabled in real-time mode
                # yf.download() only provides OHLCV - recommendation requires ticker.info
                # which is rate-limited. Use History Fetcher for recommendation monitoring.
                
                # Prepare update record (only current_price is updated in DB)
                updates.append({
                    'symbol': symbol,
                    'current_price': current_price
                })
                
            except Exception as e:
                logger.error(f"Error comparing {symbol}: {e}")
        
        logger.info(f"Generated {len(self.price_alerts)} price alerts")
        return updates
    
    def _update_database(self, updates: List[Dict]) -> int:
        """
        Upsert stock prices to database
        Only updates current_price - recommendation/targets come from History Fetcher
        
        Args:
            updates: List of update records
            
        Returns:
            Number of stocks updated
        """
        logger.info(f"Updating database with {len(updates)} records...")
        
        updated = 0
        
        for record in tqdm(updates, desc="Updating DB"):
            try:
                # Only update current_price - yf.download() doesn't provide recommendation/targets
                # Those fields are updated by History Fetcher which uses ticker.info
                self.db.update_stock_price(
                    symbol=record['symbol'],
                    current_price=record['current_price']
                )
                updated += 1
            except Exception as e:
                logger.error(f"Error updating {record['symbol']}: {e}")
        
        logger.info(f"Updated {updated} records in database")
        return updated
    
    def _send_alerts(self):
        """Enqueue price alerts to queue for async delivery"""
        if not self.price_alerts:
            logger.info("No alerts to enqueue")
            return
        
        logger.info(f"Enqueueing {len(self.price_alerts)} price alerts...")
        
        enqueued = 0
        skipped = 0
        
        # Enqueue each alert individually (top 10 by magnitude)
        sorted_alerts = sorted(self.price_alerts, key=lambda x: abs(x['change_percent']), reverse=True)
        
        for alert in sorted_alerts[:10]:  # Top 10
            alert_id = self.alert_queue.enqueue_price_alert(
                symbol=alert['symbol'],
                current_price=alert['current_price'],
                previous_price=alert['previous_close'],
                change_percent=alert['change_percent']
            )
            
            if alert_id:
                enqueued += 1
            else:
                skipped += 1
        
        logger.info(f"Alert queue: {enqueued} enqueued, {skipped} skipped (duplicates)")

    def _build_stock_models(self, symbols: List[str], current_prices: Dict[str, Dict], period: str = "200d") -> Dict[str, StockDataModel]:
        """Build StockDataModel instances using DB-cached history and current prices."""
        stock_models: Dict[str, StockDataModel] = {}

        def _period_to_days(value: str) -> int:
            if value.endswith("d"):
                return int(value[:-1])
            if value.endswith("mo"):
                return int(value[:-2]) * 30
            if value.endswith("y"):
                return int(value[:-1]) * 365
            return 200

        cutoff_date = datetime.now().date() - timedelta(days=_period_to_days(period))

        session = self.db.get_session()
        if not session:
            logger.error("No active database session")
            return {symbol: StockDataModel(symbol, fetch_data=False) for symbol in symbols}

        try:
            history_by_symbol: Dict[str, List[Dict]] = {symbol: [] for symbol in symbols}

            chunk_size = 500
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i + chunk_size]
                records = (
                    session.query(Stock_History)
                    .filter(Stock_History.symbol.in_(chunk))
                    .filter(Stock_History.date >= cutoff_date)
                    .order_by(Stock_History.symbol, Stock_History.date)
                    .all()
                )

                for record in records:
                    history_by_symbol[record.symbol].append({
                        'date': record.date.strftime("%Y-%m-%d"),
                        'close': float(record.close_price) if record.close_price is not None else None,
                        'volume': int(record.volume) if record.volume is not None else None
                    })

            for symbol in tqdm(symbols, desc="Building models"):
                stock = StockDataModel(symbol, fetch_data=False)
                try:
                    history = history_by_symbol.get(symbol, [])
                    history_df = pd.DataFrame(history) if history else pd.DataFrame()

                    if not history_df.empty:
                        history_df['close'] = pd.to_numeric(history_df.get('close'), errors='coerce')
                        history_df['volume'] = pd.to_numeric(history_df.get('volume'), errors='coerce')

                        history_df['50_MA'] = history_df['close'].rolling(window=50).mean()
                        history_df['200_MA'] = history_df['close'].rolling(window=200).mean()

                        stock.history_df = history_df
                        stock.ma_50 = history_df['50_MA'].iloc[-1] if len(history_df) >= 50 else None
                        stock.ma_200 = history_df['200_MA'].iloc[-1] if len(history_df) >= 200 else None
                        stock.average_volume = history_df['volume'].rolling(window=50).mean().iloc[-1]

                        current_price = current_prices.get(symbol, {}).get('current_price')
                        if current_price is None and len(history_df) > 0:
                            current_price = history_df['close'].iloc[-1]

                        stock.current_price = float(current_price) if current_price is not None else None

                        if len(history_df) >= 2:
                            stock.previous_close = float(history_df['close'].iloc[-2]) if history_df['close'].iloc[-2] is not None else None
                            if stock.previous_close and stock.current_price is not None:
                                stock.price_change_percent = ((stock.current_price - stock.previous_close) / stock.previous_close) * 100

                        stock.last_updated = datetime.now()
                        stock.data_fetch_success = True
                    else:
                        stock.data_fetch_success = False

                except Exception as e:
                    logger.error(f"Error building model for {symbol}: {e}")
                    stock.data_fetch_success = False

                stock_models[symbol] = stock

        finally:
            session.close()

        return stock_models


if __name__ == "__main__":
    logger.info(f"{'='*15}\\nREAL-TIME STOCK MONITORING\\n{'='*15}")
    
    # Connect to database
    db = PostgreSQLConnection()
    if not db.connect():
        logger.error("Database connection failed")
        exit(1)
    
    try:
        # Run real-time monitoring for Daily stocks
        # batch_size=500 - yf.download handles 500 symbols efficiently per batch
        updater = RealTimeUpdater(db)
        results = updater.run(frequency="Daily", batch_size=500, alert_threshold=5.0)
        
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        exit(1)
    finally:
        db.close()
        logger.info("Database connection closed")
