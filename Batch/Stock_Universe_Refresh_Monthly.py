import os
import finnhub
import pandas as pd

api_key = os.getenv("FINNHUB_API_KEY")
if not api_key:
    raise RuntimeError("Missing FINNHUB_API_KEY environment variable")

finnhub_client = finnhub.Client(api_key=api_key)

# Get US stock symbols
symbols = finnhub_client.stock_symbols("US")
df = pd.DataFrame(symbols)
df.to_excel("Data/us_stock_symbols.xlsx", index=False)