#!/usr/bin/env python3
"""
Alert Queue Service - PostgreSQL-based queue for stock alerts

Provides queue operations for enqueueing, dequeueing, and managing alerts
with deduplication, priority handling, and retry logic.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional, Tuple

# Add parent directory for imports
parent = str(Path(__file__).resolve().parent.parent)
if parent not in sys.path:
    sys.path.insert(0, parent)

from sqlalchemy import and_, or_
from Data_Loader import PostgreSQLConnection, Alert_Log
from AlertTypes import (
    AlertType, AlertPriority, AlertStatus,
    get_alert_config, get_dedup_hash, get_alert_priority_from_price_change
)

logger = logging.getLogger(__name__)


class AlertQueue:
    """
    PostgreSQL-based alert queue with deduplication and retry logic
    """
    
    MAX_RETRIES = 5
    RETRY_DELAYS = [60, 300, 900, 3600, 14400]  # 1min, 5min, 15min, 1hr, 4hr
    
    def __init__(self, db: PostgreSQLConnection):
        self.db = db
    
    def enqueue_alert(
        self,
        symbol: str,
        alert_type: AlertType,
        message: str,
        priority: Optional[AlertPriority] = None,
        context: Optional[str] = None,
        scheduled_for: Optional[datetime] = None
    ) -> Optional[int]:
        """
        Enqueue an alert with deduplication
        
        Args:
            symbol: Stock ticker symbol
            alert_type: Type of alert (from AlertType enum)
            message: Alert message to send
            priority: Alert priority (auto-determined if None)
            context: Additional context for deduplication
            scheduled_for: When to send the alert (default: now)
            
        Returns:
            Alert ID if enqueued, None if duplicate or error
        """
        session = self.db.get_session()
        if not session:
            logger.error("Database session unavailable")
            return None
        
        try:
            # Get alert configuration
            config = get_alert_config(alert_type)
            
            # Determine priority
            if priority is None:
                priority = config.priority
            
            # Generate deduplication hash
            dedup_hash = get_dedup_hash(alert_type, symbol, context)
            
            # Check for duplicate within deduplication window
            if self._is_duplicate(session, dedup_hash, config.get_dedup_window()):
                logger.debug(f"Duplicate alert skipped: {symbol} - {alert_type.value}")
                return None
            
            # Create alert
            alert = Alert_Log(
                symbol=symbol,
                alert_type=alert_type.value,
                message=message,
                sent_status=AlertStatus.PENDING.value,
                priority=priority.value,
                dedup_hash=dedup_hash,
                scheduled_for=scheduled_for or datetime.utcnow(),
                alert_timestamp=datetime.utcnow(),
                retry_count=0,
                error_message=None
            )
            
            session.add(alert)
            session.commit()
            
            logger.info(f"Alert enqueued: ID={alert.id}, {symbol}, {alert_type.value}, priority={priority.value}")
            return alert.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error enqueueing alert for {symbol}: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def enqueue_price_alert(
        self,
        symbol: str,
        current_price: float,
        previous_price: float,
        change_percent: float
    ) -> Optional[int]:
        """
        Enqueue a price change alert with auto-priority based on change magnitude
        
        Args:
            symbol: Stock ticker symbol
            current_price: Current stock price
            previous_price: Previous close price
            change_percent: Percentage change
            
        Returns:
            Alert ID if enqueued
        """
        # Determine priority based on change magnitude
        priority = get_alert_priority_from_price_change(change_percent)
        
        # Format message
        direction = "📈" if change_percent > 0 else "📉"
        message = (
            f"{direction} *{symbol}*: ${current_price:.2f} "
            f"({change_percent:+.2f}% from ${previous_price:.2f})"
        )
        
        # Context for deduplication: hour bucket to allow multiple alerts per day
        # but prevent spam within same hour
        context = datetime.utcnow().strftime("%Y-%m-%d-%H")
        
        return self.enqueue_alert(
            symbol=symbol,
            alert_type=AlertType.PRICE_CHANGE,
            message=message,
            priority=priority,
            context=context
        )
    
    def enqueue_batch(self, alerts: List[Dict]) -> Tuple[int, int]:
        """
        Enqueue multiple alerts in a batch
        
        Args:
            alerts: List of alert dictionaries with keys:
                   - symbol, alert_type, message, priority (optional), context (optional)
        
        Returns:
            Tuple of (enqueued_count, skipped_count)
        """
        enqueued = 0
        skipped = 0
        
        for alert_data in alerts:
            alert_id = self.enqueue_alert(
                symbol=alert_data['symbol'],
                alert_type=alert_data['alert_type'],
                message=alert_data['message'],
                priority=alert_data.get('priority'),
                context=alert_data.get('context')
            )
            
            if alert_id:
                enqueued += 1
            else:
                skipped += 1
        
        logger.info(f"Batch enqueue: {enqueued} added, {skipped} skipped (duplicates)")
        return enqueued, skipped
    
    def dequeue_alerts(self, batch_size: int = 10) -> List[Alert_Log]:
        """
        Dequeue alerts ready to be sent
        
        Fetches pending alerts ordered by priority and scheduled time.
        Marks them as 'Processing' to prevent double-processing.
        
        Args:
            batch_size: Maximum number of alerts to dequeue
            
        Returns:
            List of Alert_Log objects ready to send
        """
        session = self.db.get_session()
        if not session:
            logger.error("Database session unavailable")
            return []
        
        try:
            now = datetime.utcnow()
            
            # Query pending alerts ready to send
            alerts = session.query(Alert_Log).filter(
                and_(
                    Alert_Log.sent_status == AlertStatus.PENDING.value,
                    Alert_Log.scheduled_for <= now
                )
            ).order_by(
                Alert_Log.priority.asc(),  # Lower number = higher priority
                Alert_Log.scheduled_for.asc()
            ).limit(batch_size).all()
            
            # Mark as processing
            for alert in alerts:
                alert.sent_status = AlertStatus.PROCESSING.value
            
            session.commit()
            
            logger.debug(f"Dequeued {len(alerts)} alerts for processing")
            return alerts
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error dequeueing alerts: {e}", exc_info=True)
            return []
        finally:
            session.close()
    
    def mark_sent(self, alert_id: int) -> bool:
        """
        Mark an alert as successfully sent
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if updated successfully
        """
        session = self.db.get_session()
        if not session:
            return False
        
        try:
            alert = session.query(Alert_Log).filter_by(id=alert_id).first()
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return False
            
            alert.sent_status = AlertStatus.SENT.value
            alert.error_message = None
            session.commit()
            
            logger.debug(f"Alert {alert_id} marked as sent")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking alert {alert_id} as sent: {e}")
            return False
        finally:
            session.close()
    
    def mark_failed(self, alert_id: int, error_message: str) -> bool:
        """
        Mark an alert as failed and schedule retry or move to dead letter
        
        Args:
            alert_id: Alert ID
            error_message: Error description
            
        Returns:
            True if updated successfully
        """
        session = self.db.get_session()
        if not session:
            return False
        
        try:
            alert = session.query(Alert_Log).filter_by(id=alert_id).first()
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return False
            
            alert.retry_count += 1
            alert.error_message = error_message[:1000]  # Truncate to fit column
            
            if alert.retry_count >= self.MAX_RETRIES:
                # Move to dead letter queue
                alert.sent_status = AlertStatus.DEAD_LETTER.value
                logger.warning(f"Alert {alert_id} moved to dead letter after {alert.retry_count} retries")
            else:
                # Schedule retry with exponential backoff
                delay_seconds = self.RETRY_DELAYS[min(alert.retry_count - 1, len(self.RETRY_DELAYS) - 1)]
                alert.scheduled_for = datetime.utcnow() + timedelta(seconds=delay_seconds)
                alert.sent_status = AlertStatus.PENDING.value
                logger.info(f"Alert {alert_id} retry #{alert.retry_count} scheduled in {delay_seconds}s")
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking alert {alert_id} as failed: {e}")
            return False
        finally:
            session.close()
    
    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get statistics about the alert queue
        
        Returns:
            Dictionary with queue metrics
        """
        session = self.db.get_session()
        if not session:
            return {}
        
        try:
            stats = {
                'pending': session.query(Alert_Log).filter_by(
                    sent_status=AlertStatus.PENDING.value
                ).count(),
                'processing': session.query(Alert_Log).filter_by(
                    sent_status=AlertStatus.PROCESSING.value
                ).count(),
                'sent_today': session.query(Alert_Log).filter(
                    and_(
                        Alert_Log.sent_status == AlertStatus.SENT.value,
                        Alert_Log.alert_timestamp >= datetime.utcnow().date()
                    )
                ).count(),
                'failed': session.query(Alert_Log).filter_by(
                    sent_status=AlertStatus.FAILED.value
                ).count(),
                'dead_letter': session.query(Alert_Log).filter_by(
                    sent_status=AlertStatus.DEAD_LETTER.value
                ).count()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {}
        finally:
            session.close()
    
    def _is_duplicate(self, session, dedup_hash: str, window: timedelta) -> bool:
        """
        Check if alert is duplicate within time window
        
        Args:
            session: SQLAlchemy session
            dedup_hash: Deduplication hash
            window: Time window to check
            
        Returns:
            True if duplicate exists
        """
        cutoff = datetime.utcnow() - window
        
        existing = session.query(Alert_Log).filter(
            and_(
                Alert_Log.dedup_hash == dedup_hash,
                Alert_Log.alert_timestamp >= cutoff,
                or_(
                    Alert_Log.sent_status == AlertStatus.SENT.value,
                    Alert_Log.sent_status == AlertStatus.PENDING.value,
                    Alert_Log.sent_status == AlertStatus.PROCESSING.value
                )
            )
        ).first()
        
        return existing is not None


if __name__ == "__main__":
    # Test the queue
    logging.basicConfig(level=logging.INFO)
    
    db = PostgreSQLConnection()
    if not db.connect():
        print("Database connection failed")
        exit(1)
    
    queue = AlertQueue(db)
    
    # Test enqueue
    alert_id = queue.enqueue_price_alert(
        symbol="AAPL",
        current_price=150.50,
        previous_price=145.00,
        change_percent=3.79
    )
    
    if alert_id:
        print(f"✓ Alert enqueued: ID={alert_id}")
    
    # Get stats
    stats = queue.get_queue_stats()
    print(f"Queue stats: {stats}")
    
    db.close()
