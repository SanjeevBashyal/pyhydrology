
import pandas as pd
import win32com.client
import os

# --- INTERFACE CONSTANTS ---
# WEAP Area Name
WEAP_AREA = "Ghunsa"
# Simulation period
START_YEAR = 2007
END_YEAR = 2010

# File Paths
# Use absolute paths or paths relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNEL_MAP_FILE = os.path.join(BASE_DIR, "channel_map.csv")
SWAT_OUTPUT_FILE = os.path.join(BASE_DIR, "channel_sd_mon.txt")
# Output directory for river files
CSV_OUTPUT_DIR = os.path.join(BASE_DIR, "Data", "Discharges")

def main():
    print("----------------------------------------------------------------")
    print("           SWAT+ to WEAP Linker Script                          ")
    print("----------------------------------------------------------------")

    # Ensure output directory exists
    if not os.path.exists(CSV_OUTPUT_DIR):
        try:
            os.makedirs(CSV_OUTPUT_DIR)
            print(f"Created output directory: {CSV_OUTPUT_DIR}")
        except Exception as e:
            print(f"Error creating output directory: {e}")
            return

    # 1. READ CHANNEL MAPPING
    print(f"Reading channel map from: {CHANNEL_MAP_FILE}")
    if not os.path.exists(CHANNEL_MAP_FILE):
        print(f"Error: Channel map file not found at {CHANNEL_MAP_FILE}")
        return

    try:
        # Expected columns: 'SWAT Channel', 'Weap Channel'
        # The file might be tab-separated or comma-separated
        df_map = pd.read_csv(CHANNEL_MAP_FILE, sep=None, engine='python')
        # Normalize column names to strip spaces
        df_map.columns = [c.strip() for c in df_map.columns]
        
        print(f"  - Detected columns: {df_map.columns.tolist()}")

        # Create a dictionary for mapping {SWAT_ID : WEAP_Name}
        # Assuming SWAT Channel is the ID (int) and Weap Channel is the name (str)
        swat_to_weap = dict(zip(df_map['SWAT Channel'], df_map['Weap Channel']))
        print(f"  - Loaded {len(swat_to_weap)} channel mappings.")
    except Exception as e:
        print(f"Error reading channel map: {e}")
        return

    # 2. READ SWAT+ OUTPUT DATA
    print(f"Reading SWAT+ output from: {SWAT_OUTPUT_FILE}")
    if not os.path.exists(SWAT_OUTPUT_FILE):
        print(f"Error: SWAT output file not found at {SWAT_OUTPUT_FILE}")
        return

    try:
        # Read the text file
        # Skip the first line (header info), assume 2nd line has column names
        # 'delim_whitespace=True' handles multiple spaces as delimiters
        df_swat = pd.read_csv(SWAT_OUTPUT_FILE, skiprows=1, delim_whitespace=True)
        
        # Clean column names
        df_swat.columns = [c.strip() for c in df_swat.columns]
        
        # Check requisite columns
        required_cols = ['yr', 'mon', 'gis_id', 'flo_out']
        for col in required_cols:
            if col not in df_swat.columns:
                print(f"Error: Column '{col}' not found in SWAT output.")
                print(f"Available columns: {df_swat.columns.tolist()}")
                return
        
        # Ensure data types are correct
        df_swat['yr'] = pd.to_numeric(df_swat['yr'], errors='coerce')
        df_swat['gis_id'] = pd.to_numeric(df_swat['gis_id'], errors='coerce')
        df_swat['flo_out'] = pd.to_numeric(df_swat['flo_out'], errors='coerce')
        
        # Drop any rows where yr is NaN (header repetition issues?)
        df_swat = df_swat.dropna(subset=['yr'])

        print(f"  - Loaded {len(df_swat)} rows of SWAT data.")

    except Exception as e:
        print(f"Error reading SWAT output: {e}")
        return

    # 3. FILTER AND PROCESS DATA
    print(f"Processing data for period {START_YEAR} - {END_YEAR}...")
    
    # Filter by year
    df_filtered = df_swat[(df_swat['yr'] >= START_YEAR) & (df_swat['yr'] <= END_YEAR)].copy()
    
    if df_filtered.empty:
        print("Warning: No data found for the specified period.")
        return

    # Filter only channels that are in our map
    df_filtered = df_filtered[df_filtered['gis_id'].isin(swat_to_weap.keys())]
    
    if df_filtered.empty:
        print("Warning: No data found for the mapped channels.")
        return

    # Map SWAT IDs to WEAP Names
    df_filtered['WEAP_Node'] = df_filtered['gis_id'].map(swat_to_weap)
    
    # Ensure Year and Month are integers
    df_filtered['yr'] = df_filtered['yr'].astype(int)
    df_filtered['mon'] = df_filtered['mon'].astype(int)

    # 4. GENERATE INDIVIDUAL FILES AND LINK TO WEAP
    print("Connecting to WEAP...")
    try:
        weap = win32com.client.Dispatch("WEAP.WEAPApplication")
        weap.Visible = True
        
        if weap.ActiveArea.Name != WEAP_AREA:
            print(f"Switching active area to '{WEAP_AREA}'...")
            weap.ActiveArea = WEAP_AREA
        
        print(f"Active Area: {weap.ActiveArea.Name}")

        # Set Simulation Period
        print(f"Setting simulation period to {START_YEAR} - {END_YEAR}...")
        weap.BaseYear = START_YEAR
        weap.EndYear = END_YEAR

        # Link Rivers
        print("Processing rivers and generating files...")
        
        # Determine unique WEAP nodes present in the data
        unique_nodes = df_filtered['WEAP_Node'].unique()
        
        count = 0
        for river_name in unique_nodes:
            # A. Prepare River Data
            # Extract data for this river
            df_river = df_filtered[df_filtered['WEAP_Node'] == river_name][['yr', 'mon', 'flo_out']]
            
            # Sort by Year and Month
            df_river = df_river.sort_values(by=['yr', 'mon'])
            
            # Define file path: e.g., current_dir/Data/Discharges/River_Name.csv
            river_filename = f"{river_name}.csv"
            river_file_path = os.path.join(CSV_OUTPUT_DIR, river_filename)
            
            print(f"  - Writing data for '{river_name}' to {river_file_path}...")
            # Write to CSV: No header, No index
            df_river.to_csv(river_file_path, index=False, header=False)
            
            # B. Update WEAP
            try:
                branch = weap.Branch(river_name)
                if branch.TypeId == 6: # River
                    # Expression: ReadFromFile("Absolute_Path")
                    # Since parsing "2010 1 val" or "2010,1,val" is standard for ReadFromFile
                    # CSV format default is comma, which works if extension is .csv
                    abs_path = os.path.abspath(river_file_path)
                    
                    # WEAP Expression
                    expression = f'ReadFromFile("{abs_path}")'
                    
                    branch.Variables("Headflow").Expression = expression
                    print(f"    -> Updated WEAP Headflow expression.")
                    count += 1
                else:
                    print(f"    -> Warning: Branch '{river_name}' is not a river object.")
            except Exception as e:
                print(f"    -> Warning: WEAP update failed for '{river_name}': {e}")

        print(f"\nSuccessfully processed and updated {count} rivers.")
        
    except Exception as e:
        print(f"Error connecting to or controlling WEAP: {e}")
        import traceback
        traceback.print_exc()

    print("Done.")

if __name__ == "__main__":
    main()
