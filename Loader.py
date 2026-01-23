#!/usr/bin/env python3
"""
Stock Universe Loader
Loads stock data from Excel files into PostgreSQL Stock_List table
"""

import os
import sys
from datetime import datetime
import pandas as pd
from typing import Optional, Dict
from Data_Loader import PostgreSQLConnection


def load_excel_data() -> pd.DataFrame:
    """
    Load and merge stock data from Excel files
    
    Returns:
        DataFrame: Merged stock data with all required columns
    """
    try:
        # Read Market_Monitor_Summary_Final.xlsx for main stock universe
        market_monitor_df = pd.read_excel(
            "Data/Market_Monitor_Summary_Final.xlsx", 
            sheet_name="Sheet1"
        )
        print(f"✓ Loaded {len(market_monitor_df)} stocks from Market_Monitor_Summary_Final.xlsx")
        
        # Read us_stock_symbols_Universe.xlsx for additional details
        stock_symbols_df = pd.read_excel(
            "Data/us_stock_symbols_Universe.xlsx", 
            sheet_name="Sheet1"
        )
        print(f"✓ Loaded {len(stock_symbols_df)} stock symbols from us_stock_symbols_Universe.xlsx")
        
        # Merge the dataframes on stock symbol
        # Note: Market_Monitor uses 'Stock' column, us_stock_symbols uses 'symbol' column
        merged_df = market_monitor_df.merge(
            stock_symbols_df,
            left_on='Stock',
            right_on='symbol',
            how='left'
        )
        
        print(f"✓ Merged dataframe has {len(merged_df)} records")
        return merged_df
    
    except FileNotFoundError as e:
        print(f"✗ Excel file not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading Excel files: {e}")
        sys.exit(1)


def prepare_stock_data(row: pd.Series) -> Dict:
    """
    Prepare stock data for database insertion
    
    Args:
        row: DataFrame row containing stock data
        
    Returns:
        Dictionary with stock data for insertion
    """
    return {
        'symbol': str(row['Stock']).strip() if pd.notna(row['Stock']) else None,
        'name': str(row.get('description', '')).strip() if pd.notna(row.get('description')) else '',
        'frequency': str(row.get('Frequency', '')).strip() if pd.notna(row.get('Frequency')) else None,
        'sector': str(row.get('Sector', '')).strip() if pd.notna(row.get('Sector')) else None,
        'industry': str(row.get('Industry', '')).strip() if pd.notna(row.get('Industry')) else None,
        'description': str(row.get('Description', '')).strip() if pd.notna(row.get('Description')) else None
    }


def main():
    """Main loader function"""
    
    print("\n" + "="*60)
    print("STOCK UNIVERSE LOADER")
    print("="*60 + "\n")
    
    # Initialize database connection
    print("Connecting to PostgreSQL database...")
    db = PostgreSQLConnection(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )
    
    if not db.connect():
        print("\n✗ Failed to connect to database")
        sys.exit(1)
    
    # Create tables if they don't exist
    print("\nEnsuring database tables exist...")
    db.create_tables()
    
    # Load Excel data
    print("\nLoading stock data from Excel files...")
    merged_df = load_excel_data()
    
    # Insert stocks into database
    print(f"\nInserting {len(merged_df)} stocks into Stock_List table...")
    successful_inserts = 0
    failed_inserts = 0
    
    for idx, row in merged_df.iterrows():
        try:
            stock_data = prepare_stock_data(row)
            
            # Skip if symbol is missing
            if not stock_data['symbol']:
                failed_inserts += 1
                continue
            
            # Add stock to database
            if db.add_stock(
                symbol=stock_data['symbol'],
                name=stock_data['name'],
                frequency=stock_data['frequency'],
                sector=stock_data['sector'],
                industry=stock_data['industry'],
                description=stock_data['description']
            ):
                successful_inserts += 1
            else:
                failed_inserts += 1
        
        except Exception as e:
            print(f"  ⚠ Error processing row {idx}: {e}")
            failed_inserts += 1
        
        # Print progress every 500 records
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(merged_df)} records...")
    
    # Print summary
    print("\n" + "="*60)
    print("LOAD SUMMARY")
    print("="*60)
    print(f"Total records processed: {len(merged_df)}")
    print(f"✓ Successful inserts: {successful_inserts}")
    print(f"✗ Failed inserts: {failed_inserts}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Close database connection
    db.close()
    
    # Exit with appropriate code
    if failed_inserts > 0:
        print(f"⚠ Loader completed with {failed_inserts} errors")
        sys.exit(1)
    else:
        print("✓ Loader completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()    