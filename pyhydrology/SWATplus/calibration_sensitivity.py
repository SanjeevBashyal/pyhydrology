
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# Add project root to sys.path to import pySWATPlus
# Assuming this script is in pyhydrology/pyhydrology/SWATplus/
# and pySWATPlus is in pyhydrology/
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from pySWATPlus import Calibration, SensitivityAnalyzer
except ImportError as e:
    print(f"Error importing pySWATPlus: {e}")
    print(f"Checked path: {project_root}")
    sys.exit(1)

# --- Configuration ---

# Paths
SWAT_PROJECT_DIR = Path(r"E:\5 Nexus\3 SWATplus\Ghnusa_SWATplus")
TXTINOUT_DIR = SWAT_PROJECT_DIR / "Scenarios" / "Default" / "TxtInOut" # Adjust if different
CALSIM_DIR = SWAT_PROJECT_DIR / "calibration_sims"
SENSIM_DIR = SWAT_PROJECT_DIR / "sensitivity_sims"
OBSERVED_DATA_FILE = r"E:\5 Nexus\3 SWATplus\2 Calibration\1 Observation Files\discharge_2005_2010.csv"

# Ensure directories exist (and are empty if required by pySWATPlus, though we might need to handle that carefully)
# pySWATPlus requires empty directories for calsim_dir and sensim_dir
# We will handle creation/cleaning in the main execution block

# Parameters
# Format based on pySWATPlus docstring
PARAMETERS = [
    {
        'name': 'cn2',
        'change_type': 'pctchg',
        'lower_bound': -10.0,
        'upper_bound': 10.0,
    },
    {
        'name': 'esco',
        'change_type': 'absval',
        'lower_bound': 0.0,
        'upper_bound': 1.0,
    },
    {
        'name': 'perco',
        'change_type': 'absval',
        'lower_bound': 0.0,
        'upper_bound': 1.0,
    },
    # Add more parameters as needed
]

# Observed Data Configuration
OBSERVE_DATA = {
    'channel_sd_day.txt': {
        'obs_file': OBSERVED_DATA_FILE,
        'date_format': '%Y-%m-%d' # Adjust format to match your CSV
    }
}

# Objective Configuration
OBJECTIVE_CONFIG = {
    'channel_sd_day.txt': {
        'sim_col': 'flo_out',
        'obs_col': 'discharge', # Adjust to match column name in CSV
        'indicator': 'NSE'
    }
}

# Extract Data Configuration
EXTRACT_DATA = {
    'channel_sd_day.txt': {
        'has_units': True,
        # 'begin_date': '01-Jan-2005', # Optional
        # 'end_date': '31-Dec-2010',   # Optional
    }
}

# --- Execution Functions ---

def run_sensitivity_analysis(sample_number=4, max_workers=4):
    """
    Run sensitivity analysis using pySWATPlus.SensitivityAnalyzer.
    """
    print("\n--- Starting Sensitivity Analysis ---")
    
    # Clean/Create directory
    if SENSIM_DIR.exists():
        import shutil
        shutil.rmtree(SENSIM_DIR)
    SENSIM_DIR.mkdir(parents=True)

    analyzer = SensitivityAnalyzer()
    
    # 1. Run Simulations
    print("Running simulations...")
    sensim_output = analyzer.simulation_by_sample_parameters(
        parameters=PARAMETERS,
        sample_number=sample_number,
        sensim_dir=SENSIM_DIR,
        txtinout_dir=TXTINOUT_DIR,
        extract_data=EXTRACT_DATA,
        max_workers=max_workers,
        save_output=True,
        clean_setup=True
    )
    
    # 2. Calculate Indices
    print("Calculating sensitivity indices...")
    # Note: parameter_sensitivity_indices reads from the generated JSON
    indices = analyzer.parameter_sensitivity_indices(
        sensim_file=SENSIM_DIR / 'sensitivity_simulation.json',
        df_name='channel_sd_day_df', # Based on file name + _df
        sim_col='flo_out',
        obs_file=OBSERVED_DATA_FILE,
        date_format='%Y-%m-%d',
        obs_col='discharge',
        indicators=['NSE'],
        json_file=SENSIM_DIR / 'sensitivity_indices.json'
    )
    
    print("Sensitivity Analysis Complete.")
    print("Indices:", indices['sensitivity_indices'])
    
    # Plotting (Optional - basic bar chart)
    try:
        S1 = indices['sensitivity_indices']['NSE']['S1']
        names = indices['problem']['names']
        plt.figure(figsize=(10, 6))
        plt.bar(names, S1)
        plt.title("First-Order Sensitivity Indices (NSE)")
        plt.ylabel("S1")
        plt.xlabel("Parameters")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(SENSIM_DIR / "sensitivity_plot.png")
        print(f"Plot saved to {SENSIM_DIR / 'sensitivity_plot.png'}")
    except Exception as e:
        print(f"Plotting failed: {e}")

def run_calibration(n_gen=10, pop_size=20, max_workers=4):
    """
    Run calibration using pySWATPlus.Calibration.
    """
    print("\n--- Starting Calibration ---")
    
    # Clean/Create directory
    if CALSIM_DIR.exists():
        import shutil
        shutil.rmtree(CALSIM_DIR)
    CALSIM_DIR.mkdir(parents=True)

    # Initialize Calibration Problem
    try:
        cal_problem = Calibration(
            parameters=PARAMETERS,
            calsim_dir=CALSIM_DIR,
            txtinout_dir=TXTINOUT_DIR,
            extract_data=EXTRACT_DATA,
            observe_data=OBSERVE_DATA,
            objective_config=OBJECTIVE_CONFIG,
            algorithm='NSGA2',
            n_gen=n_gen,
            pop_size=pop_size,
            max_workers=max_workers
        )
    except Exception:
        import traceback
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)
        raise
    
    # Run Optimization
    print("Running optimization...")
    results = cal_problem.parameter_optimization()
    
    print("\nCalibration Complete!")
    print("Best Variables:", results['variables'])
    print("Best Objectives:", results['objectives'])

def main():
    print("Initializing SWAT+ Calibration and Sensitivity Analysis Script")
    print(f"Project Root: {project_root}")
    print(f"SWAT+ Project: {SWAT_PROJECT_DIR}")
    
    if not TXTINOUT_DIR.exists():
        print(f"Error: TxtInOut directory not found at {TXTINOUT_DIR}")
        return

    # Uncomment to run steps
    # run_sensitivity_analysis(sample_number=2, max_workers=4) # sample_number=2 -> 12 samples
    run_calibration(n_gen=2, pop_size=4, max_workers=4) # Small run for testing

if __name__ == "__main__":
    main()
