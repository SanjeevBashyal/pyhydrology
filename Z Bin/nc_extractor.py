import os
import glob
import zipfile

# --- Configuration ---
# !!! IMPORTANT !!!
# Set this variable to the full path of the directory containing your compressed files.
# Example for Windows: base_path = r"C:\Users\YourUser\Documents\ERA5_Data"
# Example for Linux/macOS: base_path = "/home/youruser/data/era5"

base_path = "E:/0 Python/pyhydrology/1 Data/ERA to Extract"

# List of file patterns to search for.
# The script will find all files that match these patterns in the base_path.
file_patterns = [
    # "ERA5_Land_2m_temperature_*.nc",
    "ERA5_Land_total_precipitation_*.nc",
    # "ERA5_Land_2m_dewpoint_temperature_*.nc",
    # "ERA5_Land_surface_solar_radiation_downwards_*.nc",
    # Added underscore for consistency, will still work if missing
    "ERA5_Land_10m_u_component_of_wind_*.nc",
    # Added underscore for consistency, will still work if missing
    "ERA5_Land_10m_v_component_of_wind_*.nc"
]

# The name of the file to be extracted from within the zip archive.
# This is typically 'data_0.nc' for CDS downloads.
target_internal_file = "data_0.nc"


def process_compressed_files(directory, patterns, internal_file):
    """
    Finds, extracts, and renames ERA5 data files.

    Args:
        directory (str): The base directory to search for files.
        patterns (list): A list of glob patterns to match filenames.
        internal_file (str): The name of the file to extract from the zip archive.
    """
    print(f"Starting processing in directory: {directory}\n")

    total_processed = 0
    total_found = 0

    for pattern in patterns:
        # Construct the full search path using the base path and the current pattern
        search_path = os.path.join(directory, pattern)
        print(f"--- Searching for files matching: {pattern} ---")

        # Use glob to find all files matching the pattern
        found_files = glob.glob(search_path)

        if not found_files:
            print("No files found for this pattern.")
            continue

        total_found += len(found_files)

        for zip_file_path in found_files:
            # Get just the filename for cleaner log messages
            filename = os.path.basename(zip_file_path)
            print(f"Processing: {filename}")

            try:
                # First, check if the file is a valid zip archive
                if not zipfile.is_zipfile(zip_file_path):
                    print(
                        f"  [SKIPPING] '{filename}' is not a valid zip file.")
                    continue

                # Define all paths before opening the file
                output_dir = os.path.dirname(zip_file_path)
                extracted_file_path = os.path.join(output_dir, internal_file)
                final_nc_path = zip_file_path

                # Open the zip file in read mode
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    # Check if the target .nc file is inside the archive
                    if internal_file not in zip_ref.namelist():
                        print(
                            f"  [WARNING] '{internal_file}' not found inside '{filename}'. Skipping.")
                        continue

                    # Extract the target file to its parent directory
                    print(f"  Extracting '{internal_file}'...")
                    zip_ref.extract(internal_file, path=output_dir)

                # Use os.replace for an atomic rename/replace operation.
                # This is safer than deleting and then renaming.
                print(f"  Renaming and replacing with extracted content...")
                os.replace(extracted_file_path, final_nc_path)

                print(
                    f"  [SUCCESS] Created: {os.path.basename(final_nc_path)}")
                total_processed += 1

            except zipfile.BadZipFile:
                print(f"  [ERROR] Corrupted zip file: {filename}")
            except Exception as e:
                print(
                    f"  [ERROR] An unexpected error occurred with {filename}: {e}")

        print("-" * 40)

    print("\n--- Processing Summary ---")
    print(f"Total files found matching patterns: {total_found}")
    print(f"Total files successfully processed: {total_processed}")
    print("--------------------------")


# --- Main Execution ---
if __name__ == "__main__":
    # A simple check to ensure the user has changed the default base_path
    if base_path == "path/to/your/files" or not os.path.isdir(base_path):
        print("="*60)
        print("!!! CONFIGURATION NEEDED !!!")
        print("Please update the 'base_path' variable in the script to point")
        print("to the directory where your compressed ERA5 files are located.")
        print(f"Current invalid path: '{base_path}'")
        print("="*60)
    else:
        process_compressed_files(
            base_path, file_patterns, target_internal_file)
        print("\nScript finished.")
