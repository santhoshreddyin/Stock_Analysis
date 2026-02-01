"""
Monitor Alerts - Detect and send stock alerts
Handles: Alert detection, filtering top alerts, sending notifications
"""

import logging
from typing import Dict, List
import pandas as pd
from StockDataModels import StockDataModel
from Data_Loader import PostgreSQLConnection
from MCP_Servers.User_Notifications_MCP import send_telegram_message

logger = logging.getLogger(__name__)


class AlertMonitor:
    """Monitors stocks and generates alerts"""
    
    def __init__(self, db: PostgreSQLConnection, alert_threshold: float = 2.0):
        self.db = db
        self.alert_threshold = alert_threshold
    
    def process_alerts(self, stock_models: Dict[str, StockDataModel], 
                      send_enabled: bool = False) -> Dict[str, any]:
        """
        Process all stocks and generate alerts
        
        Args:
            stock_models: Dictionary of StockDataModel instances
            send_enabled: Whether to send Telegram alerts
            
        Returns:
            Dictionary with alert statistics
        """
        logger.info(f"Processing alerts for {len(stock_models)} stocks")
        
        # Collect all potential alerts
        all_alerts = self._collect_alerts(stock_models)
        
        # Filter to top 10 per type
        top_alerts = self._filter_top_alerts(all_alerts, top_n=10)
        
        # Send alerts
        alerts_sent = self._send_alerts(top_alerts, send_enabled)
        
        return {
            'total_alerts': len(all_alerts),
            'alerts_sent': alerts_sent,
            'stocks_processed': len([s for s in stock_models.values() if s.data_fetch_success]),
            'stocks_skipped': len([s for s in stock_models.values() if not s.data_fetch_success])
        }
    
    def _collect_alerts(self, stock_models: Dict[str, StockDataModel]) -> List[Dict]:
        """Collect all alerts from stock models"""
        all_alerts = []
        
        for symbol, stock in stock_models.items():
            if not stock.data_fetch_success or stock.history_df is None or stock.history_df.empty:
                continue
            
            # Check for Bullish Crossover
            if stock.has_technical_data() and stock.current_price is not None:
                if stock.has_bullish_crossover_signal():
                    message = (f"Bullish Crossover Alert!: {stock.symbol}\n"
                             f"Current Price: {stock.current_price}\n"
                             f"50-day MA: {stock.ma_50}\n"
                             f"200-day MA: {stock.ma_200}\n")
                    
                    change_pct = stock.price_change_percent if stock.price_change_percent else 0.0
                    all_alerts.append({
                        'symbol': stock.symbol,
                        'alert_type': 'Bullish Crossover',
                        'message': message,
                        'change_percent': abs(change_pct),
                        'current_price': stock.current_price
                    })
            
            # Check for Price Change
            if stock.has_significant_price_change(self.alert_threshold):
                message = (f"Price Change Alert!: {stock.symbol}\n"
                         f"Previous Close: {stock.previous_close:.1f}\n"
                         f"Current Price: {stock.current_price:.1f}\n"
                         f"Price Change: {stock.price_change_percent:.1f}%\n")
                
                all_alerts.append({
                    'symbol': stock.symbol,
                    'alert_type': 'Price Change',
                    'message': message,
                    'change_percent': abs(stock.price_change_percent),
                    'current_price': stock.current_price
                })
        
        logger.info(f"Collected {len(all_alerts)} total alerts")
        return all_alerts
    
    def _filter_top_alerts(self, all_alerts: List[Dict], top_n: int = 10) -> List[Dict]:
        """Filter to top N alerts per type, sorted by change percent"""
        if not all_alerts:
            logger.info("No alerts to filter")
            return []
        
        # Convert to DataFrame
        alerts_df = pd.DataFrame(all_alerts)
        
        # Get unique alert types
        alert_types = alerts_df['alert_type'].unique()
        
        top_alerts = []
        
        for alert_type in alert_types:
            # Filter by type
            type_alerts = alerts_df[alerts_df['alert_type'] == alert_type].copy()
            
            # Sort by change percent descending
            type_alerts = type_alerts.sort_values('change_percent', ascending=False)
            
            # Take top N
            top = type_alerts.head(top_n)
            
            logger.info(f"{alert_type}: Selected top {len(top)} of {len(type_alerts)} alerts")
            
            # Convert back to dict
            top_alerts.extend(top.to_dict('records'))
        
        return top_alerts
    
    def _send_alerts(self, alerts: List[Dict], send_enabled: bool) -> int:
        """Send alerts via Telegram and save to database"""
        if not alerts:
            logger.info("No alerts to send")
            return 0
        
        logger.info(f"Sending {len(alerts)} alerts (Telegram: {send_enabled})")
        
        sent_count = 0
        
        for alert in alerts:
            try:
                # Send via Telegram if enabled
                if send_enabled:
                    send_telegram_message(message=alert['message'])
                
                # Save to database
                self.db.add_alert(
                    symbol=alert['symbol'],
                    alert_type=alert['alert_type'],
                    message=alert['message'],
                    sent_status="Sent" if send_enabled else "Not Sent"
                )
                
                logger.info(f"Alert: {alert['symbol']} ({alert['alert_type']}) - "
                          f"Change: {alert['change_percent']:.1f}%")
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Error sending alert for {alert['symbol']}: {e}")
        
        return sent_count
