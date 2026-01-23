import os
import sys
import finnhub

# Add parent directory to path to allow importing Data_Loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Data_Loader import PostgreSQLConnection

api_key = os.getenv("FINNHUB_API_KEY")
if not api_key:
    raise RuntimeError("Missing FINNHUB_API_KEY environment variable")

def refresh_stock_universe():
    finnhub_client = finnhub.Client(api_key=api_key)

    print("Fetching US stock symbols from Finnhub...")
    # Get US stock symbols
    symbols = finnhub_client.stock_symbols("US")
    
    # Initialize DB connection
    db = PostgreSQLConnection.create_connection()

    print(f"Processing {len(symbols)} symbols...")
    count = 0
    for stock in symbols:
        # Filter for Common Stock only to reduce noise
        if stock.get('type') != 'Common Stock':
            continue
            
        success = db.upsert_stock(
            symbol=stock['symbol'],
            name=stock['description'],
            # We don't get sector/industry from this endpoint
            description=f"Exchange: {stock.get('mic')}, Type: {stock.get('type')}" 
        )
        if success:
            count += 1
            
    print(f"Successfully refreshed {count} stocks in database.")
    db.close()

if __name__ == "__main__":
    refresh_stock_universe()