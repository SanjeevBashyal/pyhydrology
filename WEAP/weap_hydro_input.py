
import pandas as pd
import win32com.client
import os

# --- CONFIGURATION ---
WEAP_AREA = "Ghunsa"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HYDRO_CSV_FILE = os.path.join(BASE_DIR, "hydropower.csv")

def main():
    print("----------------------------------------------------------------")
    print("           WEAP Hydropower Parameter Input Script               ")
    print("----------------------------------------------------------------")

    # 1. READ CSV DATA
    print(f"Reading hydropower data from: {HYDRO_CSV_FILE}")
    if not os.path.exists(HYDRO_CSV_FILE):
        print(f"Error: File not found: {HYDRO_CSV_FILE}")
        return

    try:
        # Use python engine to auto-detect separators (likely tab or comma)
        df_hydro = pd.read_csv(HYDRO_CSV_FILE, sep=None, engine='python')
        # Clean column names
        df_hydro.columns = [c.strip() for c in df_hydro.columns]
        
        print(f"  - Detected columns: {df_hydro.columns.tolist()}")
        
        if 'ROR Hydropower Name' not in df_hydro.columns:
            print("Error: Required column 'ROR Hydropower Name' not found.")
            return
            
        print(f"  - Loaded {len(df_hydro)} rows.")

    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # 2. CONNECT TO WEAP
    print("Connecting to WEAP...")
    try:
        weap = win32com.client.Dispatch("WEAP.WEAPApplication")
        weap.Visible = True
        
        if weap.ActiveArea.Name != WEAP_AREA:
            print(f"Switching active area to '{WEAP_AREA}'...")
            weap.ActiveArea = WEAP_AREA
            
        print(f"Active Area: {weap.ActiveArea.Name}")
        
        # 3. UPDATE HYDROPOWER OBJECTS
        # Define Mapping: CSV Column -> WEAP Variable Name
        var_mapping = {
            'Discharge(m3/s)': 'Max Turbine Flow',
            'Efficiency(%)': 'Generating Efficiency',
            'Gross Head(m)': 'Fixed Head',
            'Priority': 'Hydropower Priority',
            'Energy Demand(GJ)': 'Energy Demand'
        }
        
        count = 0
        for index, row in df_hydro.iterrows():
            hydro_name = row['ROR Hydropower Name']
            
            print(f"Processing '{hydro_name}'...")
            try:
                # Find the branch
                branch = weap.Branch(hydro_name)
                
                # Check required columns exist
                missing_cols = [col for col in var_mapping.keys() if col not in df_hydro.columns]
                if missing_cols:
                    print(f"  -> Error: Missing columns in CSV: {missing_cols}")
                    continue

                updates_made = 0
                for csv_col, weap_var_name in var_mapping.items():
                    val = row[csv_col]
                    expression = str(val)
                    
                    try:
                        if branch.Variables(weap_var_name):
                            branch.Variables(weap_var_name).Expression = expression
                            print(f"    -> Set '{weap_var_name}' to {expression}")
                            updates_made += 1
                        else:
                            print(f"    -> Warning: Variable '{weap_var_name}' not found for '{hydro_name}'.")
                    except Exception as e:
                         print(f"    -> Error setting '{weap_var_name}': {e}")
                
                if updates_made > 0:
                    count += 1
                    
            except Exception as e:
                # If branch lookup fails or variable issues
                print(f"  -> Error updating '{hydro_name}': {e}")
                
        print(f"\nSuccessfully updated {count} hydropower objects.")

    except Exception as e:
        print(f"Error connecting to or controlling WEAP: {e}")

    print("Done.")

if __name__ == "__main__":
    main()
