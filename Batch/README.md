# Batch Processing Modules

This directory contains all market monitoring batch processing logic.

## Files

### Core Processing Modules

#### **MarketMonitorOrchestrator.py** (~109 lines)
Main orchestration logic for market monitoring workflow.
- Connects to database
- Gets stock list
- Coordinates the 3-step process
- Returns monitoring statistics

**Key Function:**
- `run_market_monitor(alert_threshold, alerts_enabled, frequency)` - Main entry point

---

#### **HistoryFetcher.py** (~236 lines)
Fetches and stores historical stock data efficiently.

**Key Methods:**
- `fetch_and_store_history(symbols, batch_size)` - Main entry point
- `_analyze_data_needs(symbols)` - Check DB for what each stock needs
- `_group_by_data_needs(data_needs)` - Group by freshness (recent/medium/old)
- `_fetch_grouped_data(groups)` - Batch download with optimal periods
- `_upsert_to_database(symbols, history_data)` - Bulk insert/update

**Features:**
- Smart grouping: <7d, 7-30d, >30d
- Variable batch sizes: 200/100/50
- Single DB query for all stock dates
- Efficient bulk upsert

---

#### **RealTimeUpdates.py** (~165 lines)
Creates stock models and updates current prices.

**Key Methods:**
- `fetch_and_update(symbols)` - Fetch data, create models, update DB
- `update_stock_models(symbols, history_data)` - Create StockDataModel instances
- `_create_stock_model(symbol, history)` - Build single model with indicators
- `update_database_prices(stock_models)` - Update Stock_Prices table

**Features:**
- Batch data fetching (200 stocks at a time)
- Technical indicator calculation (MA50, MA200)
- Price change percentage
- Progress bar for user feedback

---

#### **MonitorAlerts.py** (~159 lines)
Detects, filters, and sends stock alerts.

**Key Methods:**
- `process_alerts(stock_models, send_enabled)` - Main entry point
- `_collect_alerts(stock_models)` - Find all potential alerts
- `_filter_top_alerts(all_alerts, top_n)` - Sort by change %, take top N
- `_send_alerts(alerts, send_enabled)` - Send via Telegram and save to DB

**Features:**
- Detects Bullish Crossover alerts
- Detects Price Change alerts
- Filters to top 10 per type
- Sends via Telegram
- Saves to Alert_Log table

---

### Utility Scripts

#### **Stock_Universe_Refresh_Monthly.py** (~42 lines)
Monthly batch job to refresh the stock universe.

---

## Workflow

```
MarketWatcher.py (Cron Job)
    ↓
MarketMonitorOrchestrator.py
    ↓
    ├─→ 1. HistoryFetcher.py
    │      - Check what data is needed
    │      - Batch download historical data
    │      - Upsert to Stock_History table
    │
    ├─→ 2. RealTimeUpdates.py
    │      - Fetch recent data (7 days)
    │      - Create StockDataModel instances
    │      - Calculate technical indicators
    │      - Update Stock_Prices table
    │
    └─→ 3. MonitorAlerts.py
           - Detect alerts (Bullish Crossover, Price Change)
           - Filter to top 10 per type
           - Send Telegram notifications
           - Save to Alert_Log table
```

## Design Principles

1. **Separation of Concerns** - Each module has single responsibility
2. **Batch Processing** - Efficient bulk operations
3. **Smart Grouping** - Process stocks by data needs
4. **Rate Limiting** - Respect API limits with delays
5. **Progress Tracking** - User feedback via logging and progress bars
6. **Error Handling** - Graceful degradation, detailed logging

## Usage

Run from cron or manually:
```bash
python MarketWatcher.py
```

Or import and call:
```python
from MarketWatcher import Monitor_Market
results = Monitor_Market(Alert_Threshold=3.0, Alerts_Enabled=True, Frequency="Daily")
```
