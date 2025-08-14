from pathlib import Path

# Input configuration
# Update these paths to your environment as needed

# Base directory for data
DATA_DIR = Path(".")

# Vector study area file (shapefile, GeoPackage, etc.)
# Example shapefile path: Path("1 Data/StudyArea/study_area.shp")
VECTOR_FILE = Path("./1 Data/Watershed/watershed.shp")

# NetCDF file to read
# Example ERA5 file: Path("1 Data/ERA5/ERA5_Land_2m_temperature_2016_02.nc")
NC_FILE = Path("./1 Data/2020001.nc")

# Output clipped NetCDF
OUTPUT_FILE = Path("era5_land_clipped.nc")


