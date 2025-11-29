
import sys
import shutil
from pathlib import Path
import logging

# Add project root to sys.path to import pySWATPlus
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    import pySWATPlus
except ImportError as e:
    print(f"Error importing pySWATPlus: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_sensitivity():
    # --- Configuration ---
    
    # Paths
    SWAT_PROJECT_DIR = Path(r"E:\5 Nexus\3 SWATplus\Ghnusa_SWATplus")
    TXTINOUT_DIR = SWAT_PROJECT_DIR / "Scenarios" / "Default" / "TxtInOut"
    WORK_DIR = SWAT_PROJECT_DIR / "sensitivity_work" # Intermediate dir for setup
    SENSIM_DIR = SWAT_PROJECT_DIR / "sensitivity_sims" # Dir for actual simulations
    OBSERVED_DATA_FILE = r"E:\5 Nexus\3 SWATplus\2 Calibration\1 Observation Files\discharge_2005_2010.csv"
    
    # Clean directories if they exist
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True)
    
    if SENSIM_DIR.exists():
        shutil.rmtree(SENSIM_DIR)
    SENSIM_DIR.mkdir(parents=True)

    print(f"Source TxtInOut: {TXTINOUT_DIR}")
    print(f"Work Directory: {WORK_DIR}")
    print(f"Simulation Directory: {SENSIM_DIR}")

    # --- Step 1: Prepare Simulation Directory ---
    print("\nPreparing simulation directory...")
    
    # Initialize Reader for Source
    source_reader = pySWATPlus.TxtinoutReader(tio_dir=TXTINOUT_DIR)
    
    # Copy required files to WORK_DIR
    source_reader.copy_required_files(sim_dir=WORK_DIR)
    
    # Initialize Reader for Work Dir
    work_reader = pySWATPlus.TxtinoutReader(tio_dir=WORK_DIR)
    
    # Optimize settings for speed
    work_reader.disable_csv_print()
    
    # Set Simulation Period
    work_reader.set_simulation_period(
        begin_date='01-Jan-2005',
        end_date='31-Dec-2010'
    )
    work_reader.set_warmup_year(warmup=1)

    # Ensure channel_sd is printed (daily)
    work_reader.enable_object_in_print_prt(
        obj='channel_sd',
        daily=True,
        monthly=False,
        yearly=False,
        avann=False
    )

    # --- Step 2: Define Sensitivity Parameters ---
    parameters = [
        {'name': 'cn2', 'change_type': 'absval', 'lower_bound': 40, 'upper_bound': 90},
        {'name': 'surlag', 'change_type': 'absval', 'lower_bound': 4, 'upper_bound': 12},
        {'name': 'ovn', 'change_type': 'absval', 'lower_bound': 2, 'upper_bound': 12},
        {'name': 'slope_len', 'change_type': 'absval', 'lower_bound': 10, 'upper_bound': 50},
        {'name': 'alb', 'change_type': 'absval', 'lower_bound': 0, 'upper_bound': 0.15},
        {'name': 'revap_min', 'change_type': 'absval', 'lower_bound': 0, 'upper_bound': 20},
        {'name': 'revap_co', 'change_type': 'absval', 'lower_bound': 0.03, 'upper_bound': 0.15},
        {'name': 'snomelt_lag', 'change_type': 'absval', 'lower_bound': 0.05, 'upper_bound': 0.8},
        {'name': 'chn', 'change_type': 'absval', 'lower_bound': 0.05, 'upper_bound': 0.3},
        {'name': 'chl', 'change_type': 'absval', 'lower_bound': 0.005, 'upper_bound': 450},
        {'name': 'alpha', 'change_type': 'absval', 'lower_bound': 0.05, 'upper_bound': 0.9},
        {'name': 'bf_max', 'change_type': 'absval', 'lower_bound': 0.2, 'upper_bound': 1.5},
        {'name': 'esco', 'change_type': 'absval', 'lower_bound': 0.05, 'upper_bound': 0.9},
        {'name': 'lat_len', 'change_type': 'absval', 'lower_bound': 2, 'upper_bound': 130},
        {'name': 'canmx', 'change_type': 'absval', 'lower_bound': 0.2, 'upper_bound': 80},
        {'name': 'k', 'change_type': 'absval', 'lower_bound': 0.05, 'upper_bound': 1500},
        {'name': 'awc', 'change_type': 'absval', 'lower_bound': 0.05, 'upper_bound': 0.9},
        {'name': 'cbn', 'change_type': 'absval', 'lower_bound': 0.1, 'upper_bound': 9},
        {'name': 'chk', 'change_type': 'absval', 'lower_bound': 0.5, 'upper_bound': 400},
        {'name': 'chs', 'change_type': 'absval', 'lower_bound': 0.05, 'upper_bound': 9},
        {'name': 'chw', 'change_type': 'absval', 'lower_bound': 0.5, 'upper_bound': 500},
        {'name': 'snow_lte', 'change_type': 'absval', 'lower_bound': 0.5, 'upper_bound': 900},
        {'name': 'snomelt_tmp', 'change_type': 'absval', 'lower_bound': -4, 'upper_bound': 4},
        {'name': 'snomelt_max', 'change_type': 'absval', 'lower_bound': 0.1, 'upper_bound': 9},
        {'name': 'snomelt_min', 'change_type': 'absval', 'lower_bound': 0.5, 'upper_bound': 9},
        {'name': 'flo_init_mm', 'change_type': 'absval', 'lower_bound': 0.5, 'upper_bound': 4},
        {'name': 'deep_seep', 'change_type': 'absval', 'lower_bound': 0.01, 'upper_bound': 0.35}
    ]

    # --- Step 3: Configure Data Extraction & Observation ---
    
    # Pre-process observed data to match pySWATPlus requirements (date column, specific format)
    import pandas as pd
    temp_obs_file = WORK_DIR / "observed_processed.csv"
    df_obs = pd.read_csv(OBSERVED_DATA_FILE)
    df_obs.rename(columns={'Date': 'date', 'Flow': 'discharge'}, inplace=True)
    df_obs['date'] = pd.to_datetime(df_obs['date'], format='%d/%m/%Y')
    df_obs['date'] = df_obs['date'].dt.strftime('%d/%m/%Y')
    df_obs.to_csv(temp_obs_file, index=False)
    print(f"Processed observed data saved to: {temp_obs_file}")

    extract_data = {
        'channel_sd_day.txt': {
            'has_units': True,
            'apply_filter': {
                'gis_id': [1]
            }
        }
    }
    
    observe_data = {
        'channel_sd_day.txt': {
            'obs_file': str(temp_obs_file),
            'date_format': '%d/%m/%Y'
        }
    }
    
    metric_config = {
        'channel_sd_day.txt': {
            'sim_col': 'flo_out',
            'obs_col': 'discharge',
            'indicator': 'NSE'
        }
    }

    # --- Step 4: Run Sensitivity Analysis ---
    print("\nStarting Sensitivity Analysis...")
    
    analyzer = pySWATPlus.SensitivityAnalyzer()
    
    # Using simulation_and_indices for integrated workflow
    results = analyzer.simulation_and_indices(
        parameters=parameters,
        sample_number=1, # Total samples = sample_number * (2 * n_params + 2)
        sensim_dir=SENSIM_DIR,
        txtinout_dir=WORK_DIR, # Use the prepared work dir
        extract_data=extract_data,
        observe_data=observe_data,
        metric_config=metric_config,
        max_workers=1
    )
    
    print("\nSensitivity Analysis Results:")
    import json
    print(json.dumps(results, indent=4))

if __name__ == "__main__":
    try:
        run_sensitivity()
    except Exception:
        import traceback
        traceback.print_exc()
