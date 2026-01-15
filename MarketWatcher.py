from MCP_Servers.User_Notifications_MCP import send_telegram_message
from MCP_Servers.yfinance_MCP import get_stock_price,get_historical_data
from typing import Any, Optional
import math
import pandas as pd
from pathlib import Path

#Stock_Universe = Stocks_US 

def to_float(value: Any) -> Optional[float]:
    """Coerce numpy/pandas scalars/strings into a real Python float."""
    if value is None:
        return None
    try:
        # numpy/pandas scalar -> python scalar
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except Exception:
        return None

def Monitor_Market(Stock_Universe: list[str],Alert_Threshold: float = 2.0,Alerts_Enabled: bool = False,OutputFile: str ="Data/Market_Monitor_Summary.xlsx"):
    summary_rows: list[dict[str, Any]] = []
    summary_columns = ["Stock", "Current Price", "Volume","50-day MA ", "200-day MA","Target Low","Target High","52 Week Low","52 Week High","Bullish Alert","Recommendation","Sector","Industry","Description"]

    for stock in Stock_Universe:
        Info = get_stock_price(stock)

        Current_Price = to_float(Info.get("Current Price"))
        Target_High = to_float(Info.get("Target High"))
        Target_Low = to_float(Info.get("Target Low"))
        Week52_High = to_float(Info.get("52 Week High"))
        Week52_Low = to_float(Info.get("52 Week Low"))
        Recommendation = Info.get("Recommendation")
        Description = Info.get("Description")
        histoy = get_historical_data(stock, period="200d")
        sector = Info.get("sector")
        industry = Info.get("industry")
        # Load history to pandas DataFrame for easier manipulation
        
        history_df = pd.DataFrame(histoy)
        if history_df.empty:
            print(f"No historical data for {stock}")
            continue

        # Calculate 50-day and 200-day moving averages
        history_df['close'] = pd.to_numeric(history_df['close'], errors='coerce')
        history_df['50_MA'] = history_df['close'].rolling(window=50).mean()
        history_df['200_MA'] = history_df['close'].rolling(window=200).mean()
        latest_50_MA = history_df['50_MA'].iloc[-1]
        latest_200_MA = history_df['200_MA'].iloc[-1]
        #get average Volume
        average_volume = history_df['volume'].rolling(window=50).mean().iloc[-1]
        Bullish_Alert = " "

        # Check the Alert Conditions
        # Bullish Crossover: 50-day MA crosses above 200-day MA and Current Price is above 50-day MA
        if pd.notna(latest_50_MA) and pd.notna(latest_200_MA) and Current_Price is not None:
            if latest_50_MA > latest_200_MA and Current_Price > latest_50_MA:
                message = (f"Bullish Crossover Alert!: {stock}\n"
                           f"Current Price: {Current_Price}\n"
                           f"50-day MA: {latest_50_MA}\n"
                           f"200-day MA: {latest_200_MA}\n")
                Bullish_Alert = "Yes"
                if Alerts_Enabled:
                    print("Sending Telegram Alert for Bullish Crossover")
                    send_telegram_message(message=message)
                print(message)
            else:
                print(f"No alert for {stock}. Current Price: {Current_Price}, 50-day MA: {latest_50_MA}, 200-day MA: {latest_200_MA}")

        # Greater than threshold Change in Previous Close Price
        Previous_Close = to_float(history_df['close'].iloc[-2]) if len(history_df) >= 2 else None
        if Previous_Close is not None and Current_Price is not None:
            price_change = ((Current_Price - Previous_Close) / Previous_Close) * 100
            if abs(price_change) >= Alert_Threshold:
                direction = "increased" if price_change > 0 else "decreased"
                message = (f"Price Change Alert!: {stock}\n"
                           f"Previous Close: {Previous_Close:.1f}\n"
                           f"Current Price: {Current_Price:.1f}\n"
                           f"Price Change: {price_change:.1f}%\n")
                if Alerts_Enabled:
                    print("Sending Telegram Alert for Price Change")
                    send_telegram_message(message=message)
                print(message)
            else:
                print(f"No significant price change for {stock}. Change: {price_change:.1f}%")

        # Append to Summary (no DataFrame.append)
        summary_rows.append({
            "Stock": stock,
            "Current Price": Current_Price,
            "Volume": int(average_volume) if average_volume is not None and not math.isnan(average_volume) else None,
            "50-day MA ": latest_50_MA,
            "200-day MA": latest_200_MA,
            "Target Low": Target_Low,
            "Target High": Target_High,
            "52 Week Low": Week52_Low,
            "52 Week High": Week52_High,
            "Bullish Alert": Bullish_Alert,
            "Recommendation": Recommendation,
            "Sector": sector,
            "Industry": industry,
            "Description": Description
        })

    # Write to Excel File
    Path("Data").mkdir(parents=True, exist_ok=True)
    df_summary = pd.DataFrame(summary_rows, columns=summary_columns)
    df_summary.to_excel(OutputFile, index=False)


if __name__ == "__main__":
    # Read Stock Lists from Data Folder
    #Stocks_US = ["AAPL", "MSFT", "GOOG", "AMZN", "META"]
    Stocks_US = pd.read_excel("Data/us_stock_symbols.xlsx")["symbol"].tolist() 
    #Stocks_US = Stocks_US[:200]  # For testing, process only a subset
    print(f"Total Stocks to Monitor: {len(Stocks_US)}")
    increment = 25
    x = 1
    #Combine all the excel files into one
    for i in range(0, len(Stocks_US), increment):
        Monitor_Market(Stocks_US[i:i+increment],Alert_Threshold=3.0,Alerts_Enabled=False,OutputFile=f"Data/Market_Monitor_Summary_{x}.xlsx")
        x = x + 1

    combine_excels = []
    x = 1
    for i in range(0, len(Stocks_US), increment):
        file_path = f"Data/Market_Monitor_Summary_{x}.xlsx"
        x = x + 1
        if Path(file_path).exists():
            df = pd.read_excel(file_path)
            combine_excels.append(df)
    
    if combine_excels:
        final_df = pd.concat(combine_excels, ignore_index=True)
        final_df.to_excel("Data/Market_Monitor_Summary_Final.xlsx", index=False)    
        print("Market Monitoring Completed. Summary saved to Data/Market_Monitor_Summary_Final.xlsx")
    else:
        print("No summary files found to combine.")
