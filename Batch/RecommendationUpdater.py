#!/usr/bin/env python3
"""
Recommendation Updater - Fetch and update analyst recommendations from yfinance

This script fetches recommendation data (recommendation, target prices, 52-week range)
from yfinance ticker.info API. Since ticker.info is rate-limited, this should be run
during non-market hours as a daily/weekly batch job.

Usage:
    python Batch/RecommendationUpdater.py
    
Data Updated:
    - recommendation (Buy, Hold, Sell, etc.)
    - target_low, target_high (analyst price targets)
    - week52_low, week52_high
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time

# Add parent directory for imports
parent = str(Path(__file__).resolve().parent.parent)
if parent not in sys.path:
    sys.path.insert(0, parent)

from tqdm import tqdm
import yfinance as yf
from typing import List, Dict, Optional
from Data_Loader import PostgreSQLConnection

# Suppress yfinance logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('peewee').setLevel(logging.WARNING)

# Setup logging
log_dir = Path(parent) / 'logs'
log_dir.mkdir(exist_ok=True)

file_handler = logging.FileHandler(log_dir / 'recommendation_updater.log')
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


class RecommendationUpdater:
    """
    Fetch and update analyst recommendations from yfinance.
    
    Uses ticker.info API which is rate-limited (~1 request/second).
    Designed to run during non-market hours as a batch job.
    """
    
    def __init__(self, db: PostgreSQLConnection):
        self.db = db
        self.updated_count = 0
        self.error_count = 0
        self.recommendation_changes = []
    
    def run(self, frequency: str = "Daily", delay: float = 0.5) -> Dict:
        """
        Main execution: Fetch recommendations and update database
        
        Args:
            frequency: Stock frequency to update ("Daily", "Weekly", "Monthly", "All")
            delay: Delay between API calls in seconds (to avoid rate limiting)
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        
        logger.info(f"{'='*15} RECOMMENDATION UPDATER - {frequency} Stocks {'='*15}")
        
        # Get stocks from database
        if frequency == "All":
            stocks = self.db.get_all_stocks()
        else:
            stocks = self.db.get_all_stocks(Frequency=frequency)
            
        if not stocks:
            logger.warning(f"No {frequency} stocks found")
            return {
                'updated': 0,
                'errors': 0,
                'recommendation_changes': 0,
                'elapsed_time': time.time() - start_time
            }
        
        symbols = [stock.symbol for stock in stocks]
        logger.info(f"Updating recommendations for {len(symbols)} stocks (delay: {delay}s)")
        
        # Fetch and update recommendations
        self._fetch_and_update(symbols, delay)
        
        # Results
        elapsed = time.time() - start_time
        result = {
            'updated': self.updated_count,
            'errors': self.error_count,
            'recommendation_changes': len(self.recommendation_changes),
            'total_stocks': len(symbols),
            'elapsed_time': elapsed
        }
        
        logger.info(f"{'='*50}")
        logger.info(f"Updated: {self.updated_count}/{len(symbols)} stocks")
        logger.info(f"Errors: {self.error_count}")
        logger.info(f"Recommendation Changes: {len(self.recommendation_changes)}")
        logger.info(f"Execution Time: {str(timedelta(seconds=int(elapsed)))} ({elapsed:.2f}s)")
        logger.info(f"{'='*50}")
        
        # Log recommendation changes
        if self.recommendation_changes:
            logger.info("Recommendation Changes:")
            for change in self.recommendation_changes:
                logger.info(f"  {change['symbol']}: {change['old']} → {change['new']}")
        
        return result
    
    def _fetch_and_update(self, symbols: List[str], delay: float):
        """
        Fetch recommendations from yfinance and update database
        
        Args:
            symbols: List of stock symbols
            delay: Delay between API calls
        """
        for symbol in tqdm(symbols, desc="Fetching recommendations", ncols=80, mininterval=0.5):
            try:
                # Get current recommendation from DB (for change detection)
                current_record = self.db.get_stock_price(symbol)
                old_recommendation = current_record.Recommendation if current_record else None
                
                # Fetch from yfinance
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if not info:
                    logger.debug(f"{symbol}: No info available")
                    self.error_count += 1
                    time.sleep(delay)
                    continue
                
                # Extract recommendation data
                recommendation = info.get('recommendationKey')  # buy, hold, sell, etc.
                target_low = info.get('targetLowPrice')
                target_high = info.get('targetHighPrice')
                week52_low = info.get('fiftyTwoWeekLow')
                week52_high = info.get('fiftyTwoWeekHigh')
                
                # Normalize recommendation
                if recommendation:
                    recommendation = recommendation.lower()
                
                # Normalize old recommendation for comparison
                old_normalized = old_recommendation.lower() if old_recommendation else None
                
                # Check for recommendation change (including null transitions)
                if old_normalized != recommendation:
                    self.recommendation_changes.append({
                        'symbol': symbol,
                        'old': old_recommendation or 'N/A',
                        'new': recommendation or 'N/A'
                    })
                
                # Update database
                self.db.update_stock_price(
                    symbol=symbol,
                    recommendation=recommendation,
                    target_low=target_low,
                    target_high=target_high,
                    week52_low=week52_low,
                    week52_high=week52_high
                )
                self.updated_count += 1
                
            except Exception as e:
                logger.debug(f"{symbol}: Error - {e}")
                self.error_count += 1
            
            # Rate limiting delay
            time.sleep(delay)
    
    def update_single(self, symbol: str) -> Optional[Dict]:
        """
        Update recommendation for a single stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with updated data or None on error
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return None
            
            recommendation = info.get('recommendationKey')
            target_low = info.get('targetLowPrice')
            target_high = info.get('targetHighPrice')
            week52_low = info.get('fiftyTwoWeekLow')
            week52_high = info.get('fiftyTwoWeekHigh')
            
            if recommendation:
                recommendation = recommendation.lower()
            
            self.db.update_stock_price(
                symbol=symbol,
                recommendation=recommendation,
                target_low=target_low,
                target_high=target_high,
                week52_low=week52_low,
                week52_high=week52_high
            )
            
            return {
                'symbol': symbol,
                'recommendation': recommendation,
                'target_low': target_low,
                'target_high': target_high,
                'week52_low': week52_low,
                'week52_high': week52_high
            }
            
        except Exception as e:
            logger.error(f"Error updating {symbol}: {e}")
            return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Update analyst recommendations from yfinance')
    parser.add_argument('--frequency', '-f', type=str, default='Daily',
                        choices=['Daily', 'Weekly', 'Monthly', 'All'],
                        help='Stock frequency to update (default: Daily)')
    parser.add_argument('--delay', '-d', type=float, default=0.5,
                        help='Delay between API calls in seconds (default: 0.5)')
    parser.add_argument('--symbol', '-s', type=str, default=None,
                        help='Update single symbol only')
    
    args = parser.parse_args()
    
    logger.info(f"{'='*50}")
    logger.info("RECOMMENDATION UPDATER")
    logger.info(f"{'='*50}")
    
    # Connect to database
    db = PostgreSQLConnection()
    if not db.connect():
        logger.error("Database connection failed")
        exit(1)
    
    try:
        updater = RecommendationUpdater(db)
        
        if args.symbol:
            # Update single symbol
            logger.info(f"Updating single symbol: {args.symbol}")
            result = updater.update_single(args.symbol)
            if result:
                logger.info(f"Updated {args.symbol}:")
                logger.info(f"  Recommendation: {result['recommendation']}")
                logger.info(f"  Target: ${result['target_low']:.2f} - ${result['target_high']:.2f}" if result['target_low'] else "  Target: N/A")
                logger.info(f"  52-Week: ${result['week52_low']:.2f} - ${result['week52_high']:.2f}" if result['week52_low'] else "  52-Week: N/A")
            else:
                logger.error(f"Failed to update {args.symbol}")
        else:
            # Update all stocks by frequency
            results = updater.run(frequency=args.frequency, delay=args.delay)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        exit(1)
    finally:
        db.close()
        logger.info("Database connection closed")
