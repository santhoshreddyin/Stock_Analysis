"""
Alert Types and Configuration for Stock Analysis Alert System

Defines alert types, priorities, and deduplication rules for the queue-based alert system.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import timedelta


class AlertPriority(Enum):
    """Alert priority levels - determines send order"""
    CRITICAL = 1  # Sent immediately (>10% price moves, crashes)
    HIGH = 2      # High priority (5-10% price moves, major news)
    MEDIUM = 3    # Medium priority (2-5% price moves, crossovers)
    LOW = 4       # Low priority (<2% price moves, routine updates)


class AlertStatus(Enum):
    """Alert processing status"""
    PENDING = "Pending"           # Queued, waiting to be sent
    PROCESSING = "Processing"     # Currently being sent
    SENT = "Sent"                 # Successfully delivered
    FAILED = "Failed"             # Failed, will retry
    DEAD_LETTER = "DeadLetter"    # Failed after max retries


class AlertType(Enum):
    """Alert types with specific handling rules"""
    PRICE_CHANGE = "price_change"
    BULLISH_CROSSOVER = "bullish_crossover"
    BEARISH_CROSSOVER = "bearish_crossover"
    RECOMMENDATION_CHANGE = "recommendation_change"
    VOLUME_SPIKE = "volume_spike"
    NEW_HIGH_52W = "new_high_52w"
    NEW_LOW_52W = "new_low_52w"
    EARNINGS_ANNOUNCEMENT = "earnings_announcement"
    DAILY_SUMMARY = "daily_summary"


@dataclass
class AlertTypeConfig:
    """Configuration for each alert type"""
    alert_type: AlertType
    priority: AlertPriority
    dedup_window_hours: int  # Hours to check for duplicate alerts
    batch_allowed: bool  # Can multiple alerts be batched together?
    max_per_batch: int  # Maximum alerts of this type per batch message
    
    def get_dedup_window(self) -> timedelta:
        """Get deduplication window as timedelta"""
        return timedelta(hours=self.dedup_window_hours)


# Alert Type Configurations
ALERT_CONFIGS = {
    AlertType.PRICE_CHANGE: AlertTypeConfig(
        alert_type=AlertType.PRICE_CHANGE,
        priority=AlertPriority.MEDIUM,  # Default, can be overridden based on % change
        dedup_window_hours=1,  # Don't spam same stock price alerts within 1 hour
        batch_allowed=True,
        max_per_batch=10
    ),
    
    AlertType.BULLISH_CROSSOVER: AlertTypeConfig(
        alert_type=AlertType.BULLISH_CROSSOVER,
        priority=AlertPriority.HIGH,
        dedup_window_hours=24,  # Only alert once per day for crossovers
        batch_allowed=True,
        max_per_batch=5
    ),
    
    AlertType.BEARISH_CROSSOVER: AlertTypeConfig(
        alert_type=AlertType.BEARISH_CROSSOVER,
        priority=AlertPriority.HIGH,
        dedup_window_hours=24,
        batch_allowed=True,
        max_per_batch=5
    ),
    
    AlertType.RECOMMENDATION_CHANGE: AlertTypeConfig(
        alert_type=AlertType.RECOMMENDATION_CHANGE,
        priority=AlertPriority.MEDIUM,
        dedup_window_hours=24,  # One recommendation change alert per day
        batch_allowed=True,
        max_per_batch=10
    ),
    
    AlertType.VOLUME_SPIKE: AlertTypeConfig(
        alert_type=AlertType.VOLUME_SPIKE,
        priority=AlertPriority.MEDIUM,
        dedup_window_hours=4,  # Alert every 4 hours max
        batch_allowed=True,
        max_per_batch=10
    ),
    
    AlertType.NEW_HIGH_52W: AlertTypeConfig(
        alert_type=AlertType.NEW_HIGH_52W,
        priority=AlertPriority.HIGH,
        dedup_window_hours=24,  # Once per day
        batch_allowed=True,
        max_per_batch=10
    ),
    
    AlertType.NEW_LOW_52W: AlertTypeConfig(
        alert_type=AlertType.NEW_LOW_52W,
        priority=AlertPriority.HIGH,
        dedup_window_hours=24,
        batch_allowed=True,
        max_per_batch=10
    ),
    
    AlertType.EARNINGS_ANNOUNCEMENT: AlertTypeConfig(
        alert_type=AlertType.EARNINGS_ANNOUNCEMENT,
        priority=AlertPriority.HIGH,
        dedup_window_hours=168,  # Once per week (7 days)
        batch_allowed=False,  # Send individually
        max_per_batch=1
    ),
      
    AlertType.DAILY_SUMMARY: AlertTypeConfig(
        alert_type=AlertType.DAILY_SUMMARY,
        priority=AlertPriority.LOW,
        dedup_window_hours=24,  # Once per day
        batch_allowed=False,
        max_per_batch=1
    ),
}


def get_alert_priority_from_price_change(price_change_pct: float) -> AlertPriority:
    """
    Determine alert priority based on price change percentage
    
    Args:
        price_change_pct: Percentage price change (absolute value)
        
    Returns:
        AlertPriority based on magnitude of change
    """
    abs_change = abs(price_change_pct)
    
    if abs_change >= 10.0:
        return AlertPriority.CRITICAL
    elif abs_change >= 5.0:
        return AlertPriority.HIGH
    elif abs_change >= 2.0:
        return AlertPriority.MEDIUM
    else:
        return AlertPriority.LOW


def get_dedup_hash(alert_type: AlertType, symbol: str, context: Optional[str] = None) -> str:
    """
    Generate deduplication hash for an alert
    
    Args:
        alert_type: Type of alert
        symbol: Stock symbol
        context: Additional context for deduplication (e.g., date, price range)
        
    Returns:
        Hash string for deduplication
    """
    import hashlib
    from datetime import date
    
    # Base components
    components = [
        alert_type.value,
        symbol.upper()
    ]
    
    # Add context-specific components
    if alert_type in [AlertType.PRICE_CHANGE]:
        # For price changes, include date to allow multiple alerts per day
        # but prevent duplicate alerts within the same hour
        components.append(context or "")  # Could be hour bucket like "2026-02-01-14"
    elif alert_type in [AlertType.BULLISH_CROSSOVER, AlertType.BEARISH_CROSSOVER]:
        # For crossovers, use date only (one per day)
        components.append(str(date.today()))
    elif alert_type == AlertType.RECOMMENDATION_CHANGE:
        # For recommendation changes, include the new recommendation
        components.append(context or "")  # e.g., "buy" or "sell"
    elif alert_type == AlertType.DAILY_SUMMARY:
        # For summaries, include date
        components.append(str(date.today()))
    else:
        # Default: use context as-is
        if context:
            components.append(context)
    
    # Generate hash
    hash_input = "|".join(components)
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def get_alert_config(alert_type: AlertType) -> AlertTypeConfig:
    """
    Get configuration for an alert type
    
    Args:
        alert_type: Type of alert
        
    Returns:
        AlertTypeConfig for the alert type
    """
    return ALERT_CONFIGS.get(alert_type, ALERT_CONFIGS[AlertType.PRICE_CHANGE])


def should_batch_alerts(alert_type: AlertType) -> bool:
    """
    Check if alerts of this type should be batched
    
    Args:
        alert_type: Type of alert
        
    Returns:
        True if batching is allowed
    """
    config = get_alert_config(alert_type)
    return config.batch_allowed


def get_max_batch_size(alert_type: AlertType) -> int:
    """
    Get maximum batch size for an alert type
    
    Args:
        alert_type: Type of alert
        
    Returns:
        Maximum number of alerts that can be batched
    """
    config = get_alert_config(alert_type)
    return config.max_per_batch
