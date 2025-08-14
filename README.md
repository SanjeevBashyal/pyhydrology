# pyhydrology

Tools for hydrology: ERA5/Land downloader, NetCDF processing (subset/clip/point extract), station file export, and DEM-based elevation sampling.

## Install

Using pip (recommended if pre-built wheels are available for your platform):
```bash
pip install pyhydrology
```

For development (from this repository):
```bash
pip install -r requirements.txt
pip install -e .
```

If you encounter issues installing geospatial dependencies (`geopandas`, `rasterio`, `rioxarray`), consider using conda/mamba:
```bash
conda install -c conda-forge geopandas rasterio rioxarray shapely
```

## Key features

- Parallel ERA5-Land monthly downloader
- Merge multiple NetCDF files by coordinates (e.g., time) and clip to a polygon AOI
- Generate station metadata (`stations.cli`) and per-station precipitation series files (`stationN_pcp.txt`)
- Elevation sampling from a DEM for every station/grid point
- Helper utilities to subset by AOI bounds and extract values at a given lat/lon

## Quick start: Create stations + per-station precipitation with elevation

1) Prepare inputs:
   - A folder with NetCDF files (e.g., ERA5/MSWEP) sharing dimensions/coordinates
   - A polygon AOI vector file (e.g., shapefile) in any CRS (auto reprojected to EPSG:4326)
   - A DEM GeoTIFF for elevation (same CRS not required; it will be projected internally)

2) Run the script (from repo root):
```bash
python -m pyhydrology.scripts.read_nc_with_elevation
```
Defaults are set at the bottom of `pyhydrology/scripts/read_nc_with_elevation.py`. To customize, edit:
```python
NC_FOLDER = Path("./1 Data/ERA5")            # folder with .nc files
VECTOR_FILE = Path("./1 Data/Watershed/watershed.shp")
DEM_FILE = Path("./1 Data/Watershed/SRTM_WGS_84.tif")
OUTPUT_DIR = Path("./outputs")
```

Outputs written to `OUTPUT_DIR`:
- `stations.cli` (tab-separated):
  - Columns: `id`, `name`, `lat`, `lon`, `elev`, `pcp`
  - Example:
    ```
    id	name	lat	lon	elev	pcp
    1	station1	30.5678	-96.7890	150.0	station1_pcp.txt
    2	station2	30.8123	-96.5432	165.0	station2_pcp.txt
    ```
- `stationN_pcp.txt` per station:
  - First line: start date in YYYYMMDD
  - Following lines: one precipitation value per line; missing values as `-99.0`
  - Example:
    ```
    20100101
    0.0
    5.2
    12.7
    0.0
    ```
- `era5_with_elevation.csv` (QA) with full data and an `elevation_m` column

Notes:
- AOI is reprojected to EPSG:4326; longitudes in [0, 360] are normalized when needed
- Pre-subsetting by AOI bounds reduces memory before exact geometry clip

## Programmatic usage

### Merge, clip, and export
```python
from pathlib import Path
import xarray as xr
from pyhydrology import NetCDFProcessor, DEMSampler

files = sorted(Path("./1 Data/ERA5").glob("*.nc"))
ds = xr.open_mfdataset(files, combine="by_coords")
proc = NetCDFProcessor(ds=ds)
proc.subset_to_vector_bounds(Path("./1 Data/Watershed/watershed.shp"))
clipped = proc.clip_to_vector(Path("./1 Data/Watershed/watershed.shp"))
df = clipped.to_dataframe().reset_index()
elev = DEMSampler("./1 Data/Watershed/SRTM_WGS_84.tif")
df["elevation_m"] = elev.sample_many(df["lat"], df["lon"])  # column names may be 'latitude'/'longitude'
```

### Parallel ERA5 downloads
```python
from pyhydrology import ERA5Downloader

dl = ERA5Downloader(
    api_key="YOUR_CDS_API_KEY",
    url="https://cds.climate.copernicus.eu/api/",
    destination_folder="E:/0 Python/pyhydrology/1 Data/ERA5",
    area=[25.0, 79.0, 31.0, 89.0],  # North, West, South, East
)

results = dl.download_many(
    variables=["2m_temperature", "total_precipitation"],
    years=[str(y) for y in range(2016, 2024)],
    months=[f"{m:02d}" for m in range(1, 13)],
    max_workers=4,
)
```

## What's new in 0.2.0

- Merge multiple NetCDFs by coordinates and clip to AOI polygons
- Generate `stations.cli` and per-station precipitation series from gridded data
- DEM-based elevation sampling for each station
- Public classes: `ERA5Downloader`, `NetCDFProcessor`, `DEMSampler`

## Links

- Source: https://github.com/SanjeevBashyal/pyhydrology

## License

MIT
