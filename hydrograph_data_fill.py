import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import os

# --- (Optional) Helper to create the sample CSV if it doesn't exist ---
def create_sample_csv(filename='hydrology_data_scattered.csv'):
    if not os.path.exists(filename):
        raise RuntimeError("Sample CSV file does not exist and cannot be created automatically.")
    else:
        print(f"Using existing file: '{filename}'")

basefolder = 'E:/0 Python/pyhydrology/1 Data/Hydrology'

# Define input and output filenames
input_csv = f'{basefolder}/hydrology_data_scattered.csv'
output_csv = f'{basefolder}/hydrology_data_filled.csv'

# Create the sample file if needed
create_sample_csv(input_csv)

# 1. Load and Prepare Data from CSV
print(f"\nReading data from '{input_csv}'...")
try:
    df_scattered = pd.read_csv(input_csv)
except FileNotFoundError:
    print(f"Error: The file '{input_csv}' was not found. Please create it or run the script again.")
    exit()

# Convert the 'Date' column to datetime objects
df_scattered['Date'] = pd.to_datetime(df_scattered['Date'], format='%d-%b-%y')

# Map all dates to their 'day of the year' (1-366) to align data on a single yearly axis
df_scattered['DayOfYear'] = df_scattered['Date'].dt.dayofyear

# Sort the data for proper fitting and plotting
df_scattered = df_scattered.sort_values('DayOfYear').reset_index(drop=True)

# Prepare data for the fitting function
x_data = df_scattered['DayOfYear']
y_data = df_scattered['Discharge']

# 2. Generate Best-Fit Curve using LOWESS
print("Generating best-fit curve...")
lowess = sm.nonparametric.lowess
# frac=0.5 provides a good balance of smoothness and trend-following
smooth_curve = lowess(y_data, x_data, frac=0.5)
x_smooth = smooth_curve[:, 0]
y_smooth = smooth_curve[:, 1]

# 3. Generate Daily Data for a Full Year by Interpolating the Curve
print("Interpolating to generate daily discharge data...")
# Create an array representing every day of a standard year
full_year_days = np.arange(1, 366) 

# Use numpy's interpolation function to find the discharge value for each day
# based on the smoothed LOWESS curve.
daily_discharge_interpolated = np.interp(full_year_days, x_smooth, y_smooth)

# 4. Create and Save Output CSV
print(f"Saving daily data to '{output_csv}'...")
# Create a date range for a non-leap year (e.g., 2023) for readability
# This makes the output CSV much more user-friendly
dates_for_output = pd.to_datetime(pd.Series(full_year_days - 1, name='DayOfYear'), unit='D', origin='2023-01-01')

# Create the final DataFrame for export
df_filled = pd.DataFrame({
    'Date': dates_for_output.dt.strftime('%Y-%m-%d'),
    'DayOfYear': full_year_days,
    'EstimatedDischarge': np.round(daily_discharge_interpolated, 2) # Round to 2 decimal places
})

# Save the DataFrame to a new CSV file without the index column
df_filled.to_csv(output_csv, index=False)
print("Process complete.")

# 5. Plot the Results for Verification
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(12, 7))

# Plot the original scattered data points
ax.scatter(x_data, y_data, label='Observed Scattered Data', color='royalblue', zorder=10)

# Plot the final, interpolated daily curve
ax.plot(df_filled['DayOfYear'], df_filled['EstimatedDischarge'], color='red', linewidth=3, label='Generated Daily Discharge Curve')

# Enhancing the Plot
ax.set_title('Annual Discharge Pattern from Scattered Data', fontsize=16, fontweight='bold')
ax.set_xlabel('Month', fontsize=12)
ax.set_ylabel('Discharge', fontsize=12)
ax.legend(fontsize=11)

# Customize the x-axis to show month names
month_starts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
ax.set_xticks(month_starts)
ax.set_xticklabels(month_names)
ax.set_xlim(0, 366)
ax.set_ylim(bottom=0)

plt.tight_layout()
plt.show()