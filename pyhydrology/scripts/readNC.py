import xarray as xr
import geopandas as gpd
import rioxarray  # IMPORTANT: This must be imported to enable the .rio accessor
import matplotlib.pyplot as plt
from shapely.geometry import box

from config import DATA_DIR, VECTOR_FILE, NC_FILE, OUTPUT_FILE


# --- 2. Read the GeoPackage and Get the Study Area's Geometry ---
print(f"Reading study area from: {VECTOR_FILE}")
study_area_gdf = gpd.read_file(VECTOR_FILE)

# --- CRITICAL STEP: Ensure the CRS matches the NetCDF file ---
# ERA5 data is in WGS84 (EPSG:4326). We must ensure our study area is too.
if study_area_gdf.crs.to_epsg() != 4326:
    print(f"Original CRS is {study_area_gdf.crs}. Reprojecting to WGS84 (EPSG:4326)...")
    study_area_gdf = study_area_gdf.to_crs(epsg=4326)
else:
    print("Study area CRS is already WGS84 (EPSG:4326).")

# Get the geometry object for clipping
study_area_geometry = study_area_gdf.geometry

"""
Derive extent from the study area geometry to pre-subset the NetCDF before clipping.
This speeds up processing and reduces memory usage.
"""

# --- 3. Read the NetCDF Data using xarray ---
print(f"\nReading NetCDF data from: {NC_FILE}")
# Using open_dataset is robust. rioxarray will add the geospatial magic.
ds = xr.open_dataset(NC_FILE, engine="netcdf4")

# Add CRS information to the xarray Dataset. rioxarray needs this to work.
# ERA5 uses a standard lat/lon grid, which is EPSG:4326.
# This line might not be necessary if the file has compliant metadata, but it's safe to add.
ds = ds.rio.write_crs("epsg:4326", inplace=True)

# Let's inspect the dataset to see its variables and coordinates
print("\nOriginal Dataset structure:")
print(ds)

# --- 3a. Subset by bounding box derived from shapefile ---
# Compute bbox in EPSG:4326
bounds = study_area_gdf.total_bounds  # [minx, miny, maxx, maxy]
minx, miny, maxx, maxy = bounds
print(f"Derived extent from vector (minx, miny, maxx, maxy): {bounds}")

# Detect coordinate names (lon/lat variants)
lon_candidates = ["lon", "longitude", "x"]
lat_candidates = ["lat", "latitude", "y"]
lon_name = next((n for n in lon_candidates if n in ds.coords), None)
lat_name = next((n for n in lat_candidates if n in ds.coords), None)
if lon_name is None or lat_name is None:
    raise KeyError("Could not find latitude/longitude coordinates in the NetCDF dataset.")

# Handle 0..360 longitude if present
lon_vals = ds[lon_name].values
if lon_vals.min() >= 0 and lon_vals.max() <= 360 and minx < 0:
    minx = minx + 360
    maxx = maxx + 360
    print("Adjusted bbox longitudes to 0..360 convention.")

# Subset using sel with slice and correct latitude direction
try:
    lat_vals = ds[lat_name].values
    lat_descending = lat_vals[0] > lat_vals[-1]
    lat_slice = slice(maxy, miny) if lat_descending else slice(miny, maxy)
    ds = ds.sel({lon_name: slice(minx, maxx), lat_name: lat_slice})
    print("Applied pre-subset using shapefile extent.")
except Exception as e:
    print(f"Warning: failed to subset by bbox, proceeding without subset. Reason: {e}")

# --- 4. Clip the NetCDF Data to the Study Area Extent ---
# This is the core step. rioxarray's clip() function does all the heavy lifting.
# It will select only the data that falls within the bounds of your geometries.
print("\nPreparing dataset spatial metadata for clipping...")

# Ensure rioxarray knows which dims are spatial
try:
    ds = ds.rio.set_spatial_dims(x_dim=lon_name, y_dim=lat_name, inplace=False)
except TypeError:
    # Older versions may not accept keyword args; try positional
    try:
        ds = ds.rio.set_spatial_dims(lon_name, lat_name, inplace=False)
    except Exception:
        # Fallback to inplace mutation
        ds.rio.set_spatial_dims(x_dim=lon_name, y_dim=lat_name, inplace=True)

print("Clipping data to the exact study area geometry...")

try:
    clipped_ds = ds.rio.clip(study_area_geometry, study_area_gdf.crs, drop=True, all_touched=True)
    # drop=True: Drops data outside of the bounding box of the clip geometry.
    # all_touched=True: Includes pixels that are touched by the geometry, not just those whose center is inside.
except Exception as e:
    print(f"An error occurred during clipping: {e}")
    print("This can happen if the study area extent does not overlap with the data extent.")
    # Add a check for longitude conventions (see "Important Considerations" below)
    if 'longitude' in ds.coords and ds.coords['longitude'].min() >= 0:
        print("Longitude in NetCDF seems to be 0-360. Your study area might be in -180 to 180.")
    exit()


print("\nClipped Dataset structure:")
print(clipped_ds)

# --- 5. Analyze and Visualize the Clipped Data ---
# Let's work with 't2m' (2m temperature) and 'tp' (total precipitation)
if 't2m' in clipped_ds and 'tp' in clipped_ds:
    print("\nAnalyzing and plotting results...")

    # Convert temperature from Kelvin to Celsius for easier interpretation
    temp_celsius = clipped_ds['t2m'] - 273.15
    
    # Calculate the mean temperature over the time dimension
    mean_temp_celsius = temp_celsius.mean(dim='time')

    # Convert precipitation from meters to millimeters
    precip_mm = clipped_ds['tp'] * 1000
    
    # Calculate the total precipitation over the time dimension
    total_precip_mm = precip_mm.sum(dim='time')

    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle('ERA5 Land Data for Study Area', fontsize=16)

    # Plot Mean Temperature
    mean_temp_celsius.plot(ax=ax1, cmap='viridis')
    study_area_gdf.plot(ax=ax1, facecolor='none', edgecolor='red', linewidth=1.5)
    ax1.set_title('Mean 2m Temperature (°C)')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.grid(True, linestyle='--', alpha=0.6)

    # Plot Total Precipitation
    total_precip_mm.plot(ax=ax2, cmap='Blues')
    study_area_gdf.plot(ax=ax2, facecolor='none', edgecolor='red', linewidth=1.5)
    ax2.set_title('Total Precipitation (mm)')
    ax2.set_xlabel('Longitude')
    ax2.set_ylabel('') # Hide y-axis label for cleaner look
    ax2.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

else:
    print("Variables 't2m' or 'tp' not found in the clipped dataset.")


# --- 6. Save the Clipped Data to CSV ---
csv_path = OUTPUT_FILE.with_suffix(".csv")
print(f"\nSaving clipped data to CSV: {csv_path}")
df = clipped_ds.to_dataframe().reset_index()
df.to_csv(csv_path, index=False)
print("CSV saved successfully.")