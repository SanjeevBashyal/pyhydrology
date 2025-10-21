import geopandas as gpd
import rasterio
from shapely.geometry import Point

def get_elevation_local(lat, lon, dem_path):
    """
    Gets elevation for a single lat/lon coordinate from a local or cloud-hosted DEM file.
    
    Args:
        lat (float): Latitude of the point.
        lon (float): Longitude of the point.
        dem_path (str): Path to the DEM file (can be a local path or a URL to a cloud object).
        
    Returns:
        float: Elevation in the units of the DEM file (usually meters), or None on error.
    """
    try:
        # Create a GeoDataFrame for the input point.
        # The CRS is set to WGS84 (EPSG:4326), which is the standard for lat/lon.
        point_gdf = gpd.GeoDataFrame(
            geometry=[Point(lon, lat)],
            crs="EPSG:4326"
        )
        
        # Open the DEM file
        with rasterio.open(dem_path) as src:
            # Ensure the point's CRS matches the raster's CRS
            point_proj = point_gdf.to_crs(src.crs)
            
            # Get the coordinates of the re-projected point
            coords = [(p.x, p.y) for p in point_proj.geometry]
            
            # Sample the raster at the given coordinates
            # The result is a generator, so we convert it to a list and get the first item
            elevation_values = list(src.sample(coords))
            
            # The value is inside a numpy array, get the first (and only) value
            elevation = elevation_values[0][0]
            
            return float(elevation)
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# --- Example Usage ---

# We'll use a public Cloud-Optimized GeoTIFF (COG) of the Grand Canyon area from AWS.
# This file is part of the Amazon Terrain Tiles dataset.
# Rasterio can read this URL directly if boto3 is installed.
dem_url = "./1 Data/Watershed/SRTM_WGS_84.tif"

# Coordinates for a point within the Grand Canyon
lat, lon = 27.8, 88.3 

# Get the elevation from the DEM
elevation = get_elevation_local(lat, lon, dem_url)

if elevation is not None:
    # Note: If the elevation is a very large negative number (e.g., -32767),
    # it might be a 'nodata' value, meaning there's no data for that specific point.
    if elevation < -30000:
        print(f"No data available for the point ({lat}, {lon}).")
    else:
        print(f"The elevation at ({lat}, {lon}) is approximately {elevation:.2f} meters.")