
import sys
from pathlib import Path
import logging
import pandas as pd
import matplotlib.pyplot as plt

# Add project root to sys.path to import pySWATPlus
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from pySWATPlus import TxtinoutReader
except ImportError as e:
    print(f"Error importing pySWATPlus: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_swat_and_plot():
    # --- Configuration ---
    SWAT_PROJECT_DIR = Path(r"E:\5 Nexus\3 SWATplus\Ghnusa_SWATplus")
    TXTINOUT_DIR = SWAT_PROJECT_DIR / "Scenarios" / "Default" / "TxtInOut"
    OBSERVED_DATA_FILE = r"E:\5 Nexus\3 SWATplus\2 Calibration\1 Observation Files\discharge_2005_2010.csv"
    OUTPUT_PLOT = SWAT_PROJECT_DIR / "sim_vs_obs.png"
    
    print(f"Target TxtInOut Directory: {TXTINOUT_DIR}")
    
    if not TXTINOUT_DIR.exists():
        print(f"Error: Directory not found: {TXTINOUT_DIR}")
        return

    try:
        # Initialize Reader
        reader = TxtinoutReader(tio_dir=TXTINOUT_DIR)
        
        # Configure Output: Disable all, then enable channel_sd daily
        print("Configuring outputs...")
        reader.disable_csv_print()
        reader.enable_object_in_print_prt(
            obj='channel_sd',
            daily=True,
            monthly=False,
            yearly=False,
            avann=False
        )
        
        print("Starting SWAT+ simulation...")
        # Run Simulation
        run_path = reader.run_swat()
        print(f"Simulation completed successfully in: {run_path}")
        
        # --- Process Results ---
        print("Processing results...")
        
        # 1. Read Simulated Data
        sim_file = Path(run_path) / "channel_sd_day.txt"
        # Skip the second row (units)
        df_sim = pd.read_csv(sim_file, skiprows=[1], delim_whitespace=True)
        
        # Filter for Channel 1
        df_sim = df_sim[df_sim['gis_id'] == 1].copy()
        
        # Create Date Column from year and day
        # Assuming 'yr' and 'day' columns exist. 
        # Note: 'day' in SWAT+ output is usually day of year (1-366)
        # We need to construct a date.
        # Let's check columns first. Usually: jday, mon, day, yr.
        # If 'day' is day of year, we can use origin.
        
        # Let's try to parse date from yr, mon, day if available, or yr, jday.
        # Based on standard output, it usually has 'yr', 'mon', 'day'.
        df_sim['date'] = pd.to_datetime(df_sim[['yr', 'mon', 'day']].rename(columns={'yr': 'year', 'mon': 'month', 'day': 'day'}))
        
        # Select relevant columns
        df_sim = df_sim[['date', 'flo_out']]
        df_sim.rename(columns={'flo_out': 'simulated'}, inplace=True)
        
        # 2. Read Observed Data
        print("Reading observed data...")
        df_obs = pd.read_csv(OBSERVED_DATA_FILE)
        df_obs.rename(columns={'Date': 'date', 'Flow': 'observed'}, inplace=True)
        # Parse dates with the format identified in run_sensitivity.py
        df_obs['date'] = pd.to_datetime(df_obs['date'], format='%d/%m/%Y')
        
        # 3. Merge Data
        df_merge = pd.merge(df_sim, df_obs, on='date', how='inner')
        
        if df_merge.empty:
            print("Warning: No overlapping dates found between simulated and observed data.")
            print("Simulated range:", df_sim['date'].min(), "to", df_sim['date'].max())
            print("Observed range:", df_obs['date'].min(), "to", df_obs['date'].max())
            return

        # 4. Plot
        print(f"Plotting comparison ({len(df_merge)} points)...")
        plt.figure(figsize=(12, 6))
        plt.plot(df_merge['date'], df_merge['observed'], label='Observed', alpha=0.7)
        plt.plot(df_merge['date'], df_merge['simulated'], label='Simulated', alpha=0.7)
        plt.xlabel('Date')
        plt.ylabel('Discharge (m³/s)')
        plt.title('Daily Discharge: Simulated vs Observed (Channel 1)')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(OUTPUT_PLOT)
        print(f"Plot saved to: {OUTPUT_PLOT}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_swat_and_plot()
