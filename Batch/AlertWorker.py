#!/usr/bin/env python3
"""
Alert Worker - Background service for processing alert queue

Continuously polls the alert queue, sends alerts via Telegram with rate limiting,
and handles retries with exponential backoff.

Usage:
    python Batch/AlertWorker.py
    
    # With custom poll interval
    python Batch/AlertWorker.py --poll-interval 10
    
    # Dry run mode (don't actually send)
    python Batch/AlertWorker.py --dry-run
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time
import signal
from typing import List

# Add parent directory for imports
parent = str(Path(__file__).resolve().parent.parent)
if parent not in sys.path:
    sys.path.insert(0, parent)

from Data_Loader import PostgreSQLConnection, Alert_Log
from Batch.AlertQueue import AlertQueue
from MCP_Servers.User_Notifications_MCP import send_telegram_message
from AlertTypes import AlertStatus

# Setup logging
log_dir = Path(parent) / 'logs'
log_dir.mkdir(exist_ok=True)

file_handler = logging.FileHandler(log_dir / 'alert_worker.log')
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

# Suppress noisy logs from other modules
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)


class AlertWorker:
    """
    Background worker that processes alerts from the queue
    """
    
    def __init__(
        self,
        db: PostgreSQLConnection,
        poll_interval: int = 5,
        batch_size: int = 10,
        rate_limit_delay: float = 0.1,  # 100ms between sends = 10 msg/sec
        dry_run: bool = False
    ):
        """
        Initialize Alert Worker
        
        Args:
            db: Database connection
            poll_interval: Seconds between queue polls
            batch_size: Maximum alerts to process per batch
            rate_limit_delay: Delay in seconds between alert sends (rate limiting)
            dry_run: If True, don't actually send alerts (for testing)
        """
        self.db = db
        self.queue = AlertQueue(db)
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay
        self.dry_run = dry_run
        self.running = False
        
        # Statistics
        self.stats = {
            'sent': 0,
            'failed': 0,
            'batches_processed': 0,
            'start_time': None
        }
    
    def start(self):
        """Start the worker loop"""
        self.running = True
        self.stats['start_time'] = datetime.utcnow()
        
        logger.info(f"{'='*60}")
        logger.info(f"Alert Worker Started")
        logger.info(f"  Poll Interval: {self.poll_interval}s")
        logger.info(f"  Batch Size: {self.batch_size}")
        logger.info(f"  Rate Limit: {1/self.rate_limit_delay:.1f} msg/sec")
        logger.info(f"  Dry Run: {self.dry_run}")
        logger.info(f"{'='*60}")
        
        try:
            while self.running:
                self._process_batch()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the worker and show statistics"""
        self.running = False
        
        elapsed = datetime.utcnow() - self.stats['start_time']
        
        logger.info(f"{'='*60}")
        logger.info(f"Alert Worker Stopped")
        logger.info(f"  Runtime: {elapsed}")
        logger.info(f"  Batches Processed: {self.stats['batches_processed']}")
        logger.info(f"  Alerts Sent: {self.stats['sent']}")
        logger.info(f"  Alerts Failed: {self.stats['failed']}")
        logger.info(f"{'='*60}")
    
    def _process_batch(self):
        """Process one batch of alerts from the queue"""
        try:
            # Get queue stats
            queue_stats = self.queue.get_queue_stats()
            pending_count = queue_stats.get('pending', 0)
            
            if pending_count == 0:
                logger.debug("Queue empty, waiting...")
                return
            
            logger.info(f"Queue status: {pending_count} pending, processing batch...")
            
            # Dequeue alerts
            alerts = self.queue.dequeue_alerts(batch_size=self.batch_size)
            
            if not alerts:
                logger.debug("No alerts ready to send")
                return
            
            # Process each alert
            for alert in alerts:
                self._process_alert(alert)
                
                # Rate limiting delay
                if self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)
            
            self.stats['batches_processed'] += 1
            
            # Log batch completion
            logger.info(
                f"Batch complete: {len(alerts)} processed "
                f"(sent: {self.stats['sent']}, failed: {self.stats['failed']})"
            )
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}", exc_info=True)
    
    def _process_alert(self, alert: Alert_Log):
        """
        Process a single alert
        
        Args:
            alert: Alert_Log object to process
        """
        try:
            logger.info(
                f"Processing alert #{alert.id}: {alert.symbol} - {alert.alert_type} "
                f"(priority={alert.priority}, retry={alert.retry_count})"
            )
            
            if self.dry_run:
                # Dry run mode - simulate success
                logger.info(f"[DRY RUN] Would send: {alert.message}")
                self.queue.mark_sent(alert.id)
                self.stats['sent'] += 1
                return
            
            # Send alert via Telegram
            try:
                result = send_telegram_message(
                    message=alert.message,
                    parse_mode="Markdown"
                )
                
                # Mark as sent
                self.queue.mark_sent(alert.id)
                self.stats['sent'] += 1
                logger.info(f"✓ Alert #{alert.id} sent successfully")
                
            except Exception as send_error:
                # Send failed - mark for retry
                error_msg = str(send_error)[:500]
                logger.warning(
                    f"✗ Alert #{alert.id} send failed (retry #{alert.retry_count + 1}): {error_msg}"
                )
                
                self.queue.mark_failed(alert.id, error_msg)
                self.stats['failed'] += 1
                
        except Exception as e:
            logger.error(f"Error processing alert #{alert.id}: {e}", exc_info=True)
            # Try to mark as failed
            try:
                self.queue.mark_failed(alert.id, str(e)[:500])
            except:
                pass


def setup_signal_handlers(worker: AlertWorker):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        worker.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Alert Worker - Process alert queue')
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Seconds between queue polls (default: 5)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Maximum alerts per batch (default: 10)'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.1,
        help='Delay in seconds between sends (default: 0.1 = 10 msg/sec)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate sending without actually sending alerts'
    )
    
    args = parser.parse_args()
    
    # Connect to database
    db = PostgreSQLConnection()
    if not db.connect():
        logger.error("Database connection failed")
        exit(1)
    
    # Create and start worker
    worker = AlertWorker(
        db=db,
        poll_interval=args.poll_interval,
        batch_size=args.batch_size,
        rate_limit_delay=args.rate_limit,
        dry_run=args.dry_run
    )
    
    # Setup signal handlers
    setup_signal_handlers(worker)
    
    try:
        worker.start()
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        exit(1)
    finally:
        db.close()
        logger.info("Database connection closed")
