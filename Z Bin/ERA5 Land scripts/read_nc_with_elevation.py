from __future__ import annotations

from pathlib import Path

import pandas as pd
import xarray as xr

# Support running this file directly by ensuring the project root is on sys.path
try:
    from pyhydrology import NetCDFProcessor, DEMSampler
except ModuleNotFoundError:  # pragma: no cover - runtime convenience for direct runs
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from pyhydrology import NetCDFProcessor, DEMSampler


def _open_nc_folder(nc_folder: Path) -> xr.Dataset:
    files = sorted(Path(nc_folder).glob("*.nc"))
    if not files:
        raise FileNotFoundError(f"No .nc files found in {nc_folder}")
    # Use open_mfdataset to merge/concat along time
    ds = xr.open_mfdataset(files, combine="by_coords")
    return ds


def main(nc_folder: Path, vector_path: Path, dem_path: Path, output_dir: Path) -> None:
    # Open and merge multiple NetCDFs
    ds_merged = _open_nc_folder(nc_folder)
    proc = NetCDFProcessor(ds=ds_merged)
    proc.subset_to_vector_bounds(vector_path)
    # Pre-subset using bounds to avoid empty bounds issues, then clip
    proc.subset_to_vector_bounds(vector_path)
    clipped = proc.clip_to_vector(vector_path)

    # Convert clipped dataset to DataFrame with coordinates
    df = clipped.to_dataframe().reset_index()

    # Elevation sampling
    if {"lat", "latitude"} & set(df.columns):
        lat_col = "lat" if "lat" in df.columns else "latitude"
    else:
        raise KeyError("Latitude column not found in dataset after clipping.")
    if {"lon", "longitude"} & set(df.columns):
        lon_col = "lon" if "lon" in df.columns else "longitude"
    else:
        raise KeyError("Longitude column not found in dataset after clipping.")

    sampler = DEMSampler(str(dem_path))
    elevations = sampler.sample_many(
        df[lat_col].tolist(), df[lon_col].tolist())
    df["elevation_m"] = elevations

    # Determine the precipitation variable to use
    var_candidates = []
    for name, data_var in clipped.data_vars.items():
        dims = set(data_var.dims)
        if "time" in dims and lat_col in df.columns and lon_col in df.columns:
            var_candidates.append(name)
    var_name = "precipitation" if "precipitation" in clipped.data_vars else (
        var_candidates[0] if var_candidates else None)
    if var_name is None or var_name not in df.columns:
        raise KeyError(
            "Could not find a precipitation-like variable with time/lat/lon dims in the dataset.")

    # Prepare output directory
    out_dir = output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Normalize longitudes to -180..180 for station metadata readability
    if df[lon_col].max() > 180:
        df[lon_col] = df[lon_col].where(df[lon_col] <= 180, df[lon_col] - 360)

    # Group by station (unique lat/lon), write time series and build stations.cli entries
    records = []
    for station_id, ((lat, lon), group) in enumerate(df.groupby([lat_col, lon_col]), start=1):
        group_sorted = group.sort_values(by="time")
        # Format start date as YYYYMMDD
        start_date = pd.to_datetime(
            group_sorted["time"].iloc[0]).strftime("%Y%m%d")
        values = group_sorted[var_name].fillna(-99.0).tolist()

        station_name = f"station{station_id}"
        pcp_filename = f"{station_name}_pcp.txt"
        pcp_path = out_dir / pcp_filename

        # Write station precipitation file
        with pcp_path.open("w", newline="\n") as f:
            f.write(f"{start_date}\n")
            for v in values:
                f.write(f"{float(v):.3f}\n")

        elev = float(group_sorted["elevation_m"].iloc[0]) if pd.notna(
            group_sorted["elevation_m"].iloc[0]) else -99.0
        records.append({
            "id": station_id,
            "name": station_name,
            "lat": float(lat),
            "lon": float(lon),
            "elev": elev,
            "pcp": pcp_filename,
        })

    # Write stations.cli
    stations_cli = out_dir / "stations.cli"
    with stations_cli.open("w", newline="\n") as f:
        f.write("id\tname\tlat\tlon\telev\tpcp\n")
        for r in records:
            f.write(
                f"{r['id']}\t{r['name']}\t{r['lat']:.4f}\t{r['lon']:.4f}\t{r['elev']:.1f}\t{r['pcp']}\n")


if __name__ == "__main__":
    # Example usage; adapt paths as needed or wrap with argparse if desired
    from pyhydrology.config import VECTOR_FILE

    NC_FOLDER = Path("./1 Data/MSWEP")
    DEM_FILE = Path("./1 Data/Watershed/SRTM_WGS_84.tif")
    OUTPUT_DIR = Path("./outputs")
    main(NC_FOLDER, Path(VECTOR_FILE), DEM_FILE, OUTPUT_DIR)
