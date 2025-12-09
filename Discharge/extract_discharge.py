
import pandas as pd
import os

# Configuration
START_DATE = "2005-01-01"
END_DATE = "2015-12-31"
INPUT_FILE = "Discharge.csv"
OUTPUT_FILE = "Filtered_Discharge.csv"

def main():
    print("----------------------------------------------------------------")
    print("           Discharge Data Extractor                             ")
    print("----------------------------------------------------------------")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, INPUT_FILE)
    output_path = os.path.join(base_dir, OUTPUT_FILE)

    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        return

    print(f"Reading {INPUT_FILE}...")
    try:
        # Read CSV with fallback encoding
        df = pd.read_csv(input_path, encoding='ISO-8859-1')
        
        # Ensure Date column is datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        else:
            print("Error: 'Date' column not found.")
            return

        # Filter by Date Range
        print(f"Filtering data from {START_DATE} to {END_DATE}...")
        mask = (df['Date'] >= START_DATE) & (df['Date'] <= END_DATE)
        df_filtered = df.loc[mask].copy()

        if df_filtered.empty:
            print("Warning: No data found in the specified range.")
        else:
            print(f"Found {len(df_filtered)} rows.")

            # Format Date: d/m/yyyy (No leading zeros)
            # Row example: 1/1/2005
            df_filtered['NewDate'] = df_filtered['Date'].apply(lambda x: f"{x.month}/{x.day}/{x.year}")
            
            # The user requested format: 
            # 1/1/2005, 2/1/2005... 
            # If input is daily 2005-01-01, 2005-01-02 -> 1/1/2005, 2/1/2005? (Day/Month)
            # OR 1/1/2005, 1/2/2005? (Month/Day)
            # The example 1/1/2005, 2/1/2005, 3/1/2005... could be Day/Month (1st Jan, 2nd Jan...)
            # Let's check the provided example values:
            # 1/1/2005 -> 11.145
            # 2/1/2005 -> 11.145
            # ...
            # 12/1/2005 -> 10.848
            
            # I will assume M/D/YYYY simply because it is extremely common in US/Software, 
            # BUT the user showed 1/1, 2/1, 3/1... up to 12/1.
            # If it's valid daily data, 12/1 is Dec 1st (M/D) or Jan 12th (D/M).
            # Given that it stops at 12/1 in the short 12-line example, it looks like monthly data (Jan 1, Feb 1...).
            # However, the source file is DAILY.
            # If I stick to the SOURCE being daily, then 1/1, 2/1, 3/1 is likely Month/Day if it jumps months, 
            # OR Day/Month if it is sequential days.
            # 1/1 -> Jan 1
            # 2/1 -> Jan 2 (if D/M) or Feb 1 (if M/D)
            # 3/1 -> Jan 3 (if D/M) or Mar 1 (if M/D)
            
            # Note: The user said "extract data... from Discharge.csv".
            # The Source csv has 1965-01-01, 1965-01-02.
            # If I output 1/1, 2/1, 3/1... effectively Jan 1, Jan 2, Jan 3.
            # That corresponds to Day/Month/Year.
            # Python standard for 1/1, 2/1 is usually M/D in US.
            # I'll stick to M/D/YYYY as it's safer for "1/1, 2/1, 3/1.." usually implies Month changes in summary tables, 
            # BUT if it's raw extraction of daily data, it's Day/Month.
            # WAIT. If I implement Day/Month/Year:
            # 1/1/2005 -> Jan 1
            # 2/1/2005 -> Jan 2
            
            # Let's look at the example values again.
            # 1/1, 2/1, 3/1 have same value 11.145.
            # 4/1 has 10.947.
            # If the source data changes slowly (e.g. monthly constants), then Jan 1, Jan 2, Jan 3 might have same value.
            # If Jan 1, Feb 1, Mar 1 have same value, that's also possible.
            # However, 1/1, 2/1, 3/1, 4/1, 5/1... 12/1. 12 steps. 
            # If it was daily data (Jan 1 to Jan 12), it would be 12 days.
            # If it was monthly data (Jan 1 to Dec 1), it would be 12 months.
            # The example shows 12 lines.
            
            # I will use `Month/Day/Year` format because 1/1, 2/1... 12/1 looks like months. 
            # (Jan 1, Feb 1..). 
            # AND the user said "extract data". The source data is DAILY.
            # So I will output DAILY rows, but I will format as M/D/YYYY.
            # Result: Jan 2 will be 1/2/2005.
            
            # NO, the example is SPECIFIC:
            # 1/1/2005
            # 2/1/2005
            # 3/1/2005
            # This increments the FIRST number.
            # In US format (M/D/Y), this is Jan 1, Feb 1, Mar 1.
            # In Intl format (D/M/Y), this is Jan 1, Jan 2, Jan 3.
            # Since the source is daily, Jan 1, Jan 2, Jan 3 is the most logical extraction of consecutive rows.
            # So the format is D/M/YYYY.
            
            df_filtered['NewDate'] = df_filtered['Date'].apply(lambda x: f"{x.day}/{x.month}/{x.year}")
            
            # Select and Rename Columns
            df_output = df_filtered[['NewDate', 'Discharge']].copy()
            df_output.columns = ['Date', 'Flow']
            
            # Write to CSV
            df_output.to_csv(output_path, index=False)
            print(f"Data saved to {OUTPUT_FILE}")
            
            # Preview
            print("\nPreview:")
            print(df_output.head())

    except Exception as e:
        print(f"Error processing data: {e}")

if __name__ == "__main__":
    main()
