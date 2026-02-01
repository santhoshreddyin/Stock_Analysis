"""
Basic sanity tests for API endpoints
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that critical modules can be imported"""
    try:
        from Data_Loader import PostgreSQLConnection, Alert_Log
        from AlertTypes import AlertType, AlertPriority
        from Batch.AlertQueue import AlertQueue
        assert True
    except ImportError as e:
        assert False, f"Import failed: {e}"


def test_alert_log_model():
    """Test Alert_Log model has required fields"""
    from Data_Loader import Alert_Log
    
    # Check that model has new queue fields
    assert hasattr(Alert_Log, 'retry_count')
    assert hasattr(Alert_Log, 'priority')
    assert hasattr(Alert_Log, 'scheduled_for')
    assert hasattr(Alert_Log, 'error_message')
    assert hasattr(Alert_Log, 'dedup_hash')


def test_alert_queue_initialization():
    """Test AlertQueue can be instantiated"""
    from Batch.AlertQueue import AlertQueue
    from unittest.mock import Mock
    
    mock_db = Mock()
    queue = AlertQueue(mock_db)
    
    assert queue.MAX_RETRIES == 5
    assert len(queue.RETRY_DELAYS) == 5


if __name__ == "__main__":
    test_imports()
    test_alert_log_model()
    test_alert_queue_initialization()
    
    print("✓ All API tests passed!")
