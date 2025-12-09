
import pandas as pd
import win32com.client
import os
import re
import calendar

# --- CONFIGURATION ---
WEAP_AREA = "Ghunsa"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTLEMENTS_FILE = os.path.join(BASE_DIR, "settlements.csv")
TOURIST_FILE = os.path.join(BASE_DIR, "tourist.csv")

# Constants
DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] # 1-indexed for convenience
TOURIST_RATE_L_D = 100.0
CONSUMPTION_RATE = 50.0

def parse_header_rate(header):
    """Extracts the numeric rate from a header string like 'Houses (100L/d)' or 'Potato (4500 m3/ha)'."""
    # Look for number inside parentheses
    # Case 1: (100L/d) -> 100
    # Case 2: (4500 m3/ha) -> 4500
    match = re.search(r'\((\d+(\.\d+)?)\s*[L|m3]', header)
    if match:
        return float(match.group(1))
    return None

def get_crop_months(month_string):
    """Parses 'March,April,...' into a list of month indices (1-12)."""
    if pd.isna(month_string) or month_string.strip() == '-':
        return []
    
    month_map = {name: i for i, name in enumerate(calendar.month_name) if name}
    clean_str = str(month_string).replace('"', '').strip()
    months = []
    for m in clean_str.split(','):
        m = m.strip()
        if m in month_map:
            months.append(month_map[m])
    return months

def main():
    print("----------------------------------------------------------------")
    print("           WEAP Water Demand Input Script                       ")
    print("----------------------------------------------------------------")

    # 1. READ DATA
    if not os.path.exists(SETTLEMENTS_FILE) or not os.path.exists(TOURIST_FILE):
        print("Error: Input files not found.")
        return

    try:
        df_settlements = pd.read_csv(SETTLEMENTS_FILE, sep=None, engine='python', encoding='utf-8-sig')
        df_tourist = pd.read_csv(TOURIST_FILE, sep=None, engine='python', encoding='utf-8-sig')
        
        # Clean columns
        df_settlements.columns = [c.strip() for c in df_settlements.columns]
        df_tourist.columns = [c.strip() for c in df_tourist.columns]
        
        print(f"Settlements Columns: {df_settlements.columns.tolist()}")
        print(f"Tourist Columns: {df_tourist.columns.tolist()}")
        
        # Ensure 'Location' column exists
        if 'Location' not in df_settlements.columns:
            print("Error: 'Location' column missing in settlements.csv")
            return
        if 'Location' not in df_tourist.columns:
            print("Error: 'Location' column missing in Tourist.csv")
            return
        
        # Ensure Location is index or accessible
        # df_tourist should map Location -> Months
        # Assuming 'Location' column exists in both
        
        print(f"Loaded {len(df_settlements)} settlements.")

    except Exception as e:
        print(f"Error reading CSVs: {e}")
        return

    # 2. CONNECT TO WEAP
    print("Connecting to WEAP...")
    try:
        weap = win32com.client.Dispatch("WEAP.WEAPApplication")
        weap.Visible = True
        
        if weap.ActiveArea.Name != WEAP_AREA:
            weap.ActiveArea = WEAP_AREA
            
    except Exception as e:
        print(f"Error connecting to WEAP: {e}")
        return

    # 3. CALCULATE DEMANDS
    
    # Identify rate columns in settlements.csv
    # We distinguish between Daily L/d (Domestic/Livestock) and Seasonal m3/ha (Crops)
    # Heuristic: headers with 'L/d' vs 'm3/ha'
    
    domestic_livestock_cols = []
    crop_cols = []
    
    for col in df_settlements.columns:
        if 'L/d' in col:
            rate = parse_header_rate(col)
            if rate is not None:
                domestic_livestock_cols.append((col, rate))
        elif 'm3/ha' in col:
            rate = parse_header_rate(col)
            if rate is not None:
                crop_cols.append((col, rate))
                
    print(f"identified {len(domestic_livestock_cols)} domestic/livestock categories.")
    print(f"Identified {len(crop_cols)} crop categories.")
    
    # Crop seasonality pattern (percent of total seasonal demand)
    # Order: 1st month 30%, 2nd 25%, 3rd 20%, 4th 15%, 5th 10%
    crop_pattern = [0.30, 0.25, 0.20, 0.15, 0.10]

    count = 0
    
    for _, row in df_settlements.iterrows():
        location = row['Location']
        print(f"\nProcessing '{location}'...")
        
        # Initialize Monthly Demands (m3)
        monthly_demand_m3 = [0.0] * 13 # index 1-12
        
        # A. Domestic & Livestock (Daily Rate * Days)
        # Rate is L/d -> m3/month: Rate * Count * Days / 1000
        for col, rate_l_d in domestic_livestock_cols:
            count_val = row[col]
            if pd.isna(count_val): count_val = 0
            
            daily_vol_m3 = (count_val * rate_l_d) / 1000.0
            
            for m in range(1, 13):
                monthly_demand_m3[m] += daily_vol_m3 * DAYS_IN_MONTH[m]
                
        # B. Crops (Seasonal m3/ha)
        # Total Demand = Area * Rate
        # Distributed over growing months
        growing_months = get_crop_months(row.get("What time of the Year Crops are Grown?", ""))
        
        for col, rate_ha in crop_cols:
            area = row[col]
            if pd.isna(area): area = 0
            
            total_crop_water_m3 = area * rate_ha
            
            # Distribute
            # If we have growing months, apply pattern
            if growing_months and total_crop_water_m3 > 0:
                for i, m_idx in enumerate(growing_months):
                    if i < len(crop_pattern):
                        monthly_demand_m3[m_idx] += total_crop_water_m3 * crop_pattern[i]
            # If no growing months listed but crops exist, maybe ignore or warn? 
            # (Assuming csv has months if crops > 0)

        # C. Tourists (Daily Rate L/d * Days)
        # Look up location in tourist df
        tourist_row = df_tourist[df_tourist['Location'] == location]
        if not tourist_row.empty:
            # Month abbreviations in Tourist.csv: Jan, Feb...
            abbrs = list(calendar.month_abbr)[1:] # ['Jan', 'Feb', ...]
            
            for m_idx, abbr in enumerate(abbrs, 1): # 1-12
                # Check if column exists (strip just in case)
                # The file has 'Jan', 'Feb' etc.
                if abbr in df_tourist.columns:
                    t_count = tourist_row.iloc[0][abbr]
                    if pd.isna(t_count): t_count = 0
                    
                    # Demand = Count * 100 L/d * Days / 1000
                    month_vol_m3 = (t_count * TOURIST_RATE_L_D * DAYS_IN_MONTH[m_idx]) / 1000.0
                    monthly_demand_m3[m_idx] += month_vol_m3
        
        # 4. AGGREGATE AND UPDATE WEAP
        total_annual_m3 = sum(monthly_demand_m3[1:])
        
        if total_annual_m3 == 0:
            print("  Total demand is 0, skipping update.")
            continue
            
        # Monthly Variation %
        # MonthlyValues(Jan, Val, Feb, Val, ...)
        monthly_args = []
        current_sum = 0.0
        
        # Month abbreviations (Jan, Feb, ...)
        month_abbrs = list(calendar.month_abbr)[1:]
        
        # Calculate for Jan-Nov
        for m in range(1, 12):
            pct = (monthly_demand_m3[m] / total_annual_m3) * 100.0
            pct_rounded = round(pct, 2)
            current_sum += pct_rounded
            
            # Append MonthName, Value
            monthly_args.append(month_abbrs[m-1])
            monthly_args.append(f"{pct_rounded:.2f}")
            
        # Calculate Dec as remainder
        dec_pct = 100.0 - current_sum
        monthly_args.append(month_abbrs[11]) # Dec
        monthly_args.append(f"{dec_pct:.2f}")
            
        variation_expression = "MonthlyValues(" + ", ".join(monthly_args) + ")"
        
        print(f"  Annual Demand: {total_annual_m3:.2f} m3")
        # print("  Variation: " + variation_expression)

        try:
            # Find Demand Site
            # WEAP Demand sites might be named "Location" or similar
            branch = weap.Branch(location)
            # Ensure it's a Demand Site (TypeId 2)
            if branch.TypeId == 1:
                # Update Variables
                branch.Variables("Annual Water Use Rate").Expression = str(total_annual_m3)
                branch.Variables("Monthly Variation").Expression = variation_expression
                branch.Variables("Consumption").Expression = str(CONSUMPTION_RATE)
                print("  -> Updated WEAP variables.")
                count += 1
            else:
                print(f"  -> Branch '{location}' exists but is not a Demand Site (Type {branch.TypeId}).")
                
        except Exception as e:
            print(f"  -> Error updating '{location}': {e}")

    print(f"\nSuccessfully updated {count} demand sites.")
    print("Done.")

if __name__ == "__main__":
    main()
