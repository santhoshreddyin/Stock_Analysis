"""
History Fetcher - Batch download and store historical stock data
Handles: Fetching historical data, upserting to database
"""

from datetime import datetime, timedelta
import logging
from typing import List, Dict
import time
from Data_Loader import PostgreSQLConnection, Stock_History
from MCP_Servers.yfinance_MCP import get_batch_historical_data
from sqlalchemy import func

logger = logging.getLogger(__name__)


class HistoryFetcher:
    """Fetches and stores historical stock data in batches"""
    
    def __init__(self, db: PostgreSQLConnection):
        self.db = db
    
    def fetch_and_store_history(self, symbols: List[str], batch_size: int = 500) -> Dict[str, any]:
        """
        Fetch historical data for stocks and store in database
        
        Args:
            symbols: List of stock symbols
            batch_size: Number of stocks to process per batch
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Fetching history for {len(symbols)} stocks in batches of {batch_size}")
        
        total_records = 0
        stocks_updated = 0
        
        for i in range(0, len(symbols), batch_size):
            chunk = symbols[i:i + batch_size]
            chunk_num = (i // batch_size) + 1
            total_chunks = (len(symbols) + batch_size - 1) // batch_size
            
            logger.info(f"Batch {chunk_num}/{total_chunks}: Processing {len(chunk)} stocks")
            
            try:
                # Analyze what data each stock needs
                data_needs = self._analyze_data_needs(chunk)
                
                # Group stocks by how much data they need
                groups = self._group_by_data_needs(data_needs)
                
                # Fetch data for each group
                history_data = self._fetch_grouped_data(groups)
                
                # Store in database
                records = self._upsert_to_database(chunk, history_data)
                
                total_records += records
                stocks_updated += len(chunk)
                
                logger.info(f"Batch {chunk_num}: Stored {records} records")
                
            except Exception as e:
                logger.error(f"Error processing batch {chunk_num}: {e}")
            
            # Rate limiting delay
            if i + batch_size < len(symbols):
                time.sleep(2)
        
        return {
            'stocks_updated': stocks_updated,
            'total_records': total_records
        }
    
    def _analyze_data_needs(self, symbols: List[str]) -> Dict[str, Dict]:
        """Check database to see what data each stock needs"""
        session = self.db.get_session()
        if not session:
            return {}
        
        try:
            today = datetime.now().date()
            
            # Get latest date for each stock in one query
            latest_records = session.query(
                Stock_History.symbol,
                func.max(Stock_History.date).label('latest_date')
            ).filter(
                Stock_History.symbol.in_(symbols)
            ).group_by(Stock_History.symbol).all()
            
            # Build needs dictionary
            latest_dates = {r.symbol: r.latest_date for r in latest_records}
            data_needs = {}
            
            for symbol in symbols:
                if symbol in latest_dates:
                    latest_date = latest_dates[symbol]
                    if hasattr(latest_date, 'date'):
                        latest_date = latest_date.date()
                    days_old = (today - latest_date).days
                    data_needs[symbol] = {'days': days_old, 'latest_date': latest_date}
                else:
                    # No history - need full year
                    data_needs[symbol] = {'days': 365, 'latest_date': None}
            
            logger.info(f"Analyzed data needs for {len(symbols)} stocks")
            return data_needs
            
        finally:
            session.close()
    
    def _group_by_data_needs(self, data_needs: Dict) -> Dict[str, List[str]]:
        """Group stocks by how much data they need"""
        groups = {
            'recent': [],   # <7 days - batch 200
            'medium': [],   # 7-30 days - batch 100
            'old': []       # >30 days - batch 50
        }
        
        for symbol, info in data_needs.items():
            days = info['days']
            if days < 7:
                groups['recent'].append(symbol)
            elif days <= 30:
                groups['medium'].append(symbol)
            else:
                groups['old'].append(symbol)
        
        logger.info(f"Groups: recent={len(groups['recent'])}, "
                   f"medium={len(groups['medium'])}, old={len(groups['old'])}")
        return groups
    
    def _fetch_grouped_data(self, groups: Dict[str, List[str]]) -> Dict[str, List]:
        """Fetch historical data for each group with appropriate period"""
        all_history = {}
        
        # Fetch recent stocks (7 days)
        if groups['recent']:
            logger.info(f"Fetching {len(groups['recent'])} recent stocks (7d)")
            for i in range(0, len(groups['recent']), 200):
                batch = groups['recent'][i:i + 200]
                history = get_batch_historical_data(batch, period='7d')
                all_history.update(history)
                if i + 200 < len(groups['recent']):
                    time.sleep(1)
        
        # Fetch medium stocks (1 month)
        if groups['medium']:
            logger.info(f"Fetching {len(groups['medium'])} medium stocks (1mo)")
            for i in range(0, len(groups['medium']), 100):
                batch = groups['medium'][i:i + 100]
                history = get_batch_historical_data(batch, period='1mo')
                all_history.update(history)
                if i + 100 < len(groups['medium']):
                    time.sleep(1)
        
        # Fetch old stocks (1 year)
        if groups['old']:
            logger.info(f"Fetching {len(groups['old'])} old stocks (1y)")
            for i in range(0, len(groups['old']), 50):
                batch = groups['old'][i:i + 50]
                history = get_batch_historical_data(batch, period='1y')
                all_history.update(history)
                if i + 50 < len(groups['old']):
                    time.sleep(2)
        
        logger.info(f"Fetched history for {len(all_history)} stocks")
        return all_history
    
    def _upsert_to_database(self, symbols: List[str], history_data: Dict) -> int:
        """Upsert historical data to database"""
        session = self.db.get_session()
        if not session:
            return 0
        
        try:
            # Prepare records
            records = []
            for symbol in symbols:
                history = history_data.get(symbol, [])
                for record in history:
                    try:
                        records.append({
                            'symbol': symbol,
                            'date': datetime.strptime(record['date'], '%Y-%m-%d').date(),
                            'open_price': record.get('open'),
                            'high_price': record.get('high'),
                            'low_price': record.get('low'),
                            'close_price': record.get('close'),
                            'volume': record.get('volume')
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing record for {symbol}: {e}")
            
            if not records:
                return 0
            
            logger.info(f"Upserting {len(records)} records")
            
            # Upsert in chunks
            chunk_size = 500
            total_upserted = 0
            
            for idx in range(0, len(records), chunk_size):
                chunk = records[idx:idx + chunk_size]
                
                for record in chunk:
                    existing = session.query(Stock_History).filter_by(
                        symbol=record['symbol'],
                        date=record['date']
                    ).first()
                    
                    if existing:
                        existing.open_price = record['open_price']
                        existing.high_price = record['high_price']
                        existing.low_price = record['low_price']
                        existing.close_price = record['close_price']
                        existing.volume = record['volume']
                    else:
                        session.add(Stock_History(**record))
                
                session.flush()
                total_upserted += len(chunk)
            
            session.commit()
            logger.info(f"Successfully upserted {total_upserted} records")
            return total_upserted
            
        except Exception as e:
            session.rollback()
            logger.error(f"Upsert failed: {e}")
            return 0
        finally:
            session.close()
