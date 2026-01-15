import pandas as pd
from pathlib import Path
combine_excels = []

for x in range(1,7):
        file_path = f"Data/Market_Monitor_Summary_Final_{x}.xlsx"
        if Path(file_path).exists():
            print(f"Reading {file_path}")
            df = pd.read_excel(file_path)
            combine_excels.append(df)
    
if combine_excels:
    final_df = pd.concat(combine_excels, ignore_index=True)
    final_df.to_excel("Data/Market_Monitor_Summary_Final.xlsx", index=False)    
    print("Market Monitoring Completed. Summary saved to Data/Market_Monitor_Summary_Final.xlsx")
else:
    print("No summary files found to combine.")