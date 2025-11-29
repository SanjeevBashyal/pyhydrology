import csv
import re
import sys
from datetime import datetime

def is_valid_date(year, month, day):
    try:
        datetime(year, month, day)
        return True
    except ValueError:
        return False

def main():
    input_file = 'Discharge.txt'
    output_file = 'Discharge.csv'
    
    try:
        with open(input_file, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    # Split by whitespace to handle newlines and spaces uniformly
    tokens = content.split()
    
    data_rows = []
    
    i = 0
    n = len(tokens)
    
    while i < n:
        token = tokens[i]
        
        # Look for Table start
        if token == 'Table':
            # Extract Year
            # We expect "in <Year>" somewhere in the header
            # Let's scan forward until we find a 4-digit year
            current_year = None
            while i < n:
                if re.match(r'^\d{4}$', tokens[i]):
                    current_year = int(tokens[i])
                    # Check if it's a reasonable year (e.g. 19xx or 20xx)
                    if 1900 <= current_year <= 2100:
                        break
                i += 1
            
            if current_year is None:
                # Could not find a year for this table, skip or break
                # If we reached end of file, break
                if i >= n: break
                continue
            
            # Now skip until we pass "Dec"
            # The header is "Day Jan ... Dec"
            while i < n and tokens[i] != 'Dec':
                i += 1
            i += 1 # Skip 'Dec'
            
            # Now we expect 31 rows of data
            for day in range(1, 32):
                if i >= n: break
                
                # The first token should be the day number
                day_token = tokens[i]
                
                # Sanity check: if we hit 'Table', we probably finished the year (shouldn't happen if 31 rows are always present)
                # or the file structure is slightly different.
                if day_token == 'Table':
                    # Backtrack one token so the main loop catches 'Table'
                    i -= 1 # This is safe because we incremented i at start of loop or previous iteration
                    break 
                
                # If it's not the day number we expect, it might be a misalignment or missing day.
                # But based on file inspection, it seems consistent.
                # Let's just consume it.
                i += 1 
                
                # Now read 12 values (Jan to Dec)
                for month in range(1, 13):
                    if i >= n: break
                    val = tokens[i]
                    i += 1
                    
                    if is_valid_date(current_year, month, day):
                        # If valid date, we record it
                        # Handle '-'
                        if val == '-':
                            # Missing value for a valid date
                            # We can leave it empty or keep '-' depending on preference.
                            # User asked for "formats ... into a csv", usually implies usable data.
                            # Let's keep it empty for better compatibility with analysis tools, 
                            # or keep '-' if user wants raw data.
                            # Given "time series order", missing data is often represented as empty or NaN.
                            # I'll use empty string.
                            clean_val = '' 
                        else:
                            clean_val = val
                        
                        date_str = f"{current_year}-{month:02d}-{day:02d}"
                        data_rows.append([date_str, clean_val])
                    else:
                        # Invalid date (e.g. Feb 30), ignore value
                        pass
        else:
            i += 1
            
    # Sort by date just in case, though it should be in order
    data_rows.sort(key=lambda x: x[0])
    
    # Write to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Discharge'])
        writer.writerows(data_rows)
        
    print(f"Successfully wrote {len(data_rows)} rows to {output_file}")

if __name__ == '__main__':
    main()
