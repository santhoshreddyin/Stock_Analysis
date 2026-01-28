#!/usr/bin/env python3
"""
Test script to demonstrate batch historical data fetching with yfinance.

This script shows the performance difference between:
1. Individual stock data fetching (one at a time)
2. Batch stock data fetching (all at once using yfinance.download)
"""

import time
from MCP_Servers.yfinance_MCP import get_historical_data, get_batch_historical_data
from StockDataModels import StockDataModel

# Test symbols - using a smaller set for testing
TEST_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']

print("=" * 80)
print("BATCH vs INDIVIDUAL HISTORICAL DATA FETCH COMPARISON")
print("=" * 80)
print(f"Testing with {len(TEST_SYMBOLS)} symbols: {', '.join(TEST_SYMBOLS)}")
print("NOTE: Using smaller sample to avoid rate limits. For production, use chunks of 250.")
print()

# Test 1: Individual fetching
print("-" * 80)
print("Test 1: INDIVIDUAL FETCHING (one stock at a time)")
print("-" * 80)
start_time = time.time()

individual_results = {}
for symbol in TEST_SYMBOLS:
    print(f"  Fetching {symbol}...", end=" ")
    try:
        data = get_historical_data(symbol, period="1mo", use_db=False)
        individual_results[symbol] = data
        print(f"✓ ({len(data)} records)")
    except Exception as e:
        print(f"✗ Error: {e}")
        individual_results[symbol] = []

individual_time = time.time() - start_time
print(f"\nIndividual Fetch Time: {individual_time:.2f} seconds")
print(f"Average per stock: {individual_time/len(TEST_SYMBOLS):.2f} seconds")

# Test 2: Batch fetching
print()
print("-" * 80)
print("Test 2: BATCH FETCHING (all stocks in parallel)")
print("-" * 80)
start_time = time.time()

batch_results = get_batch_historical_data(TEST_SYMBOLS, period="1mo")
batch_time = time.time() - start_time

print(f"Batch downloaded {len(batch_results)} stocks")
for symbol, data in batch_results.items():
    print(f"  {symbol}: {len(data)} records")

print(f"\nBatch Fetch Time: {batch_time:.2f} seconds")
print(f"Average per stock: {batch_time/len(TEST_SYMBOLS):.2f} seconds")

# Performance comparison
print()
print("=" * 80)
print("PERFORMANCE SUMMARY")
print("=" * 80)
print(f"Individual Method: {individual_time:.2f} seconds")
print(f"Batch Method:      {batch_time:.2f} seconds")
speedup = individual_time / batch_time if batch_time > 0 else 0
print(f"Speedup:           {speedup:.2f}x faster")
print(f"Time Saved:        {individual_time - batch_time:.2f} seconds")
print()

# Test 3: StockDataModel batch_create
print("-" * 80)
print("Test 3: StockDataModel.batch_create() (recommended approach)")
print("-" * 80)
start_time = time.time()

# Use shorter period for testing - only need recent data for most use cases
stock_models = StockDataModel.batch_create(TEST_SYMBOLS, period="1mo")
model_time = time.time() - start_time

print(f"\nCreated {len(stock_models)} StockDataModel instances")
successful = sum(1 for s in stock_models.values() if s.data_fetch_success)
print(f"Successful: {successful}/{len(stock_models)}")

for symbol, stock in stock_models.items():
    if stock.data_fetch_success:
        ma_50_str = f"{stock.ma_50:.2f}" if stock.ma_50 else "N/A"
        ma_200_str = f"{stock.ma_200:.2f}" if stock.ma_200 else "N/A"
        price_str = f"{stock.current_price:.2f}" if stock.current_price else "N/A"
        print(f"  {symbol}: ${price_str} | MA50: {ma_50_str} | MA200: {ma_200_str}")
    else:
        print(f"  {symbol}: Failed to fetch data")

print(f"\nStockDataModel.batch_create() Time: {model_time:.2f} seconds")

print()
print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("✓ Use StockDataModel.batch_create() for best performance when processing")
print("  multiple stocks at once (like in MarketWatcher)")
print()
print("✓ For large datasets (1000+ stocks):")
print("  - Process in chunks of 250 stocks at a time")
print("  - Add 2-second delay between chunks to avoid rate limits")
print("  - Use period='1mo' instead of '200d' when you only need recent data")
print("  - The get_historical_data() with use_db=True will cache results")
print()
print(f"✓ For {len(TEST_SYMBOLS)} stocks:")
print(f"  - Individual: {individual_time:.2f}s")
print(f"  - Batch:      {batch_time:.2f}s ({speedup:.1f}x faster)")
print("=" * 80)
