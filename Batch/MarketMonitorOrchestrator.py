"""
Market Monitor Orchestrator - Coordinates all batch processing
Handles: Full workflow from DB connection to alert generation
"""

import logging
import time
from datetime import datetime
from Data_Loader import PostgreSQLConnection
from Batch.HistoryFetcher import HistoryFetcher
from Batch.RealTimeUpdates import RealTimeUpdater
from Batch.MonitorAlerts import AlertMonitor

logger = logging.getLogger(__name__)


def run_market_monitor(alert_threshold: float = 2.0, alerts_enabled: bool = False, frequency: str = "Daily"):
    """
    Main orchestration function for market monitoring
    
    Args:
        alert_threshold: Price change threshold percentage for alerts
        alerts_enabled: Whether to send Telegram alerts
        frequency: Stock selection frequency ("Daily", "Weekly", "Monthly")
    
    Returns:
        Dictionary with monitoring statistics
    """
    start_time = time.time()
    
    # Initialize database
    db = PostgreSQLConnection()
    if not db.connect():
        logger.error("Database connection failed")
        return _error_result("Database connection failed", time.time() - start_time)
    
    # Get stocks to monitor
    stocks = db.get_all_stocks(Frequency=frequency)
    if not stocks or len(stocks) == 0:
        logger.warning(f"No stocks found with Frequency='{frequency}'")
        db.close()
        return _error_result(f"No stocks found with Frequency={frequency}", time.time() - start_time)
    
    symbols = [stock.symbol for stock in stocks]
    logger.info(f"Monitoring {len(symbols)} stocks")
    
    # STEP 1: Fetch and store historical data
    logger.info("=" * 70)
    logger.info("STEP 1: FETCHING HISTORICAL DATA")
    logger.info("=" * 70)
    
    fetcher = HistoryFetcher(db)
    fetch_results = fetcher.fetch_and_store_history(symbols, batch_size=500)
    
    logger.info(f"Fetched history for {fetch_results['stocks_updated']} stocks")
    logger.info(f"Stored {fetch_results['total_records']} records")
    
    # STEP 2: Create real-time stock models and update prices
    logger.info("=" * 70)
    logger.info("STEP 2: UPDATING REAL-TIME DATA")
    logger.info("=" * 70)
    
    updater = RealTimeUpdater(db)
    update_results = updater.fetch_and_update(symbols)
    
    logger.info(f"Updated {update_results['stocks_updated']} stock prices")
    
    # STEP 3: Process alerts
    logger.info("=" * 70)
    logger.info("STEP 3: PROCESSING ALERTS")
    logger.info("=" * 70)
    
    monitor = AlertMonitor(db, alert_threshold=alert_threshold)
    alert_results = monitor.process_alerts(update_results['stock_models'], send_enabled=alerts_enabled)
    
    logger.info(f"Processed {alert_results['stocks_processed']} stocks")
    logger.info(f"Generated {alert_results['total_alerts']} total alerts")
    logger.info(f"Sent top {alert_results['alerts_sent']} alerts")
    
    # Close database
    db.close()
    
    # Calculate stats
    elapsed_time = time.time() - start_time
    
    return {
        "total_stocks": len(symbols),
        "stocks_processed": alert_results['stocks_processed'],
        "stocks_skipped": alert_results['stocks_skipped'],
        "alerts_generated": alert_results['alerts_sent'],
        "total_alerts": alert_results['total_alerts'],
        "records_stored": fetch_results['total_records'],
        "timestamp": datetime.now(),
        "elapsed_time": elapsed_time,
        "avg_time_per_stock": elapsed_time / len(symbols) if len(symbols) > 0 else 0
    }


def _error_result(error_msg: str, elapsed_time: float) -> dict:
    """Create error result dictionary"""
    return {
        "total_stocks": 0,
        "stocks_processed": 0,
        "stocks_skipped": 0,
        "alerts_generated": 0,
        "timestamp": datetime.now(),
        "elapsed_time": elapsed_time,
        "error": error_msg
    }
