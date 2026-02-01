"""
Market Watcher - Simple Cron Job Entry Point
Delegates all logic to batch processing modules
"""

from datetime import datetime, timedelta
import logging
from pathlib import Path

# Configure logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(f"logs/market_watcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logging.getLogger().handlers[1].setLevel(logging.INFO)
logger = logging.getLogger(__name__)


def Monitor_Market(Alert_Threshold: float = 2.0, Alerts_Enabled: bool = False, Frequency: str = "Daily"):
    """
    Simple cron job - orchestrates stock monitoring
    All logic is delegated to batch processing modules
    """
    from Batch.MarketMonitorOrchestrator import run_market_monitor
    return run_market_monitor(Alert_Threshold, Alerts_Enabled, Frequency)


if __name__ == "__main__":
    logger.info(f"{'='*70}\nSTOCK MARKET MONITOR\n{'='*70}")
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run monitoring
    results = Monitor_Market(Alert_Threshold=3.0, Alerts_Enabled=True, Frequency="Daily")
    
    # Display results
    logger.info(f"{'='*70}\nMONITORING RESULTS\n{'='*70}")
    
    if "error" in results:
        logger.error(f"ERROR: {results['error']}")
        exit(1)
    
    logger.info(f"Total Stocks:            {results['total_stocks']}")
    logger.info(f"Successfully Processed:  {results['stocks_processed']}")
    logger.info(f"Skipped (No Data):       {results['stocks_skipped']}")
    logger.info(f"Records Stored:          {results.get('records_stored', 0)}")
    logger.info(f"Total Alerts Found:      {results.get('total_alerts', 0)}")
    logger.info(f"Top Alerts Sent:         {results['alerts_generated']}")
    logger.info(f"End Time:                {results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    elapsed = results['elapsed_time']
    logger.info(f"Execution Time:          {str(timedelta(seconds=int(elapsed)))} ({elapsed:.2f}s)")
    logger.info(f"Avg Time/Stock:          {results['avg_time_per_stock']:.2f}s")
    
    logger.info("=" * 70)
