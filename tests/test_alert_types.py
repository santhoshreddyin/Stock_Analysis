"""
Basic tests for Alert Queue system
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from AlertTypes import (
    AlertType, AlertPriority, AlertStatus,
    get_alert_priority_from_price_change,
    get_dedup_hash,
    should_batch_alerts
)


def test_alert_priority_from_price_change():
    """Test priority assignment based on price change"""
    assert get_alert_priority_from_price_change(15.0) == AlertPriority.CRITICAL
    assert get_alert_priority_from_price_change(-12.0) == AlertPriority.CRITICAL
    assert get_alert_priority_from_price_change(7.0) == AlertPriority.HIGH
    assert get_alert_priority_from_price_change(3.0) == AlertPriority.MEDIUM
    assert get_alert_priority_from_price_change(1.0) == AlertPriority.LOW


def test_dedup_hash_generation():
    """Test deduplication hash generation"""
    hash1 = get_dedup_hash(AlertType.PRICE_CHANGE, "AAPL", "2026-02-01-14")
    hash2 = get_dedup_hash(AlertType.PRICE_CHANGE, "AAPL", "2026-02-01-14")
    hash3 = get_dedup_hash(AlertType.PRICE_CHANGE, "AAPL", "2026-02-01-15")
    
    # Same context should produce same hash
    assert hash1 == hash2
    
    # Different context should produce different hash
    assert hash1 != hash3
    
    # Hash should be 16 characters
    assert len(hash1) == 16


def test_alert_batching_config():
    """Test alert batching configuration"""
    # Price changes can be batched
    assert should_batch_alerts(AlertType.PRICE_CHANGE) is True
    
    # System errors should not be batched
    assert should_batch_alerts(AlertType.SYSTEM_ERROR) is False
    
    # Daily summary should not be batched
    assert should_batch_alerts(AlertType.DAILY_SUMMARY) is False


def test_alert_type_enum():
    """Test alert type enum values"""
    assert AlertType.PRICE_CHANGE.value == "price_change"
    assert AlertType.BULLISH_CROSSOVER.value == "bullish_crossover"
    assert AlertType.RECOMMENDATION_CHANGE.value == "recommendation_change"


def test_alert_status_enum():
    """Test alert status enum values"""
    assert AlertStatus.PENDING.value == "Pending"
    assert AlertStatus.SENT.value == "Sent"
    assert AlertStatus.DEAD_LETTER.value == "DeadLetter"


if __name__ == "__main__":
    # Run tests manually
    test_alert_priority_from_price_change()
    test_dedup_hash_generation()
    test_alert_batching_config()
    test_alert_type_enum()
    test_alert_status_enum()
    
    print("✓ All tests passed!")
