from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd
import xarray as xr

# Import as a package or directly for script execution
try:
    from pyhydrology import NetCDFProcessor, DEMSampler
except ModuleNotFoundError:  # pragma: no cover
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from pyhydrology import NetCDFProcessor, DEMSampler


def _open_era_nc_folder(folder: Path, pattern: str) -> xr.Dataset:
    files = sorted(Path(folder).glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching '{pattern}' found in {folder}")

    def try_open_one(path: Path) -> xr.Dataset | None:
        for eng in ("netcdf4", "scipy", "h5netcdf"):
            try:
                return xr.open_dataset(str(path), engine=eng)
            except Exception:
                continue
        return None

    opened = []
    for p in files:
        ds = try_open_one(p)
        if ds is not None:
            opened.append(ds)

    if not opened:
        raise RuntimeError(
            f"Failed to open any files for pattern '{pattern}'. Ensure they are valid NetCDF."
        )

    try:
        merged = xr.combine_by_coords(opened, combine_attrs="override")
    except Exception:
        # Fallback to mfdataset if combine fails
        paths = [str(p) for p in files]
        merged = xr.open_mfdataset(paths, combine="by_coords")
    return merged


def _detect_lat_lon_columns(df: pd.DataFrame) -> Tuple[str, str]:
    if "lat" in df.columns:
        lat_col = "lat"
    elif "latitude" in df.columns:
        lat_col = "latitude"
    else:
        raise KeyError("Latitude column not found in dataframe")

    if "lon" in df.columns:
        lon_col = "lon"
    elif "longitude" in df.columns:
        lon_col = "longitude"
    else:
        raise KeyError("Longitude column not found in dataframe")
    return lat_col, lon_col


def main(nc_folder: Path, vector_path: Path, dem_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Open precipitation and temperature datasets separately
    ds_pcp = _open_era_nc_folder(nc_folder, "ERA5_Land_total_precipitation_*.nc")
    ds_tmp = _open_era_nc_folder(nc_folder, "ERA5_Land_2m_temperature_*.nc")

    # Clip both datasets to AOI
    proc_pcp = NetCDFProcessor(ds=ds_pcp)
    proc_pcp.subset_to_vector_bounds(vector_path)
    ds_pcp_clip = proc_pcp.clip_to_vector(vector_path)

    proc_tmp = NetCDFProcessor(ds=ds_tmp)
    proc_tmp.subset_to_vector_bounds(vector_path)
    ds_tmp_clip = proc_tmp.clip_to_vector(vector_path)

    # Aggregate to daily
    # Precipitation: hourly to daily sum (m/day)
    if "tp" not in ds_pcp_clip.data_vars:
        raise KeyError("Variable 'tp' not found in precipitation dataset")
    # Convert meters to millimeters for station output
    pcp_daily = (ds_pcp_clip["tp"].resample(time="1D").max()) * 1000.0

    # Temperature: hourly to daily max/min; convert to Celsius from Kelvin
    if "t2m" not in ds_tmp_clip.data_vars:
        raise KeyError("Variable 't2m' not found in temperature dataset")
    tmax_daily_k = ds_tmp_clip["t2m"].resample(time="1D").max()
    tmin_daily_k = ds_tmp_clip["t2m"].resample(time="1D").min()
    tmax_daily_c = tmax_daily_k - 273.15
    tmin_daily_c = tmin_daily_k - 273.15

    # Convert to DataFrames
    df_pcp = pcp_daily.to_dataframe(name="pcp").reset_index()
    df_tmax = tmax_daily_c.to_dataframe(name="tmax").reset_index()
    df_tmin = tmin_daily_c.to_dataframe(name="tmin").reset_index()

    # Detect lat/lon column names
    lat_col, lon_col = _detect_lat_lon_columns(df_pcp)

    # Merge temp max/min and then with precip on lat/lon/time (inner join to align dates)
    df_tmp = pd.merge(df_tmax, df_tmin, on=["time", lat_col, lon_col], how="inner")
    df = pd.merge(df_pcp, df_tmp, on=["time", lat_col, lon_col], how="inner")

    # Normalize longitudes to -180..180 for readability
    if df[lon_col].max() > 180:
        df[lon_col] = df[lon_col].where(df[lon_col] <= 180, df[lon_col] - 360)

    # Elevation sampling
    sampler = DEMSampler(str(dem_path))
    # Compute elevation per unique station to avoid repeated sampling
    station_coords = df[[lat_col, lon_col]].drop_duplicates().reset_index(drop=True)
    station_coords["elevation_m"] = sampler.sample_many(
        station_coords[lat_col].tolist(), station_coords[lon_col].tolist()
    )
    df = df.merge(station_coords, on=[lat_col, lon_col], how="left")

    # Generate station files
    station_records = []
    for station_id, ((lat, lon), group) in enumerate(df.groupby([lat_col, lon_col]), start=1):
        group_sorted = group.sort_values(by="time")
        start_date = pd.to_datetime(group_sorted["time"].iloc[0]).strftime("%Y%m%d")

        # File names
        station_name = f"station{station_id}"
        pcp_filename = f"{station_name}_pcp.txt"
        tmp_filename = f"{station_name}_tmp.txt"

        # Write precipitation file
        with (output_dir / pcp_filename).open("w", newline="\n") as f:
            f.write(f"{start_date}\n")
            for v in group_sorted["pcp"].fillna(-99.0).tolist():
                f.write(f"{float(v):.3f}\n")

        # Write temperature file (max,min per day in Celsius)
        with (output_dir / tmp_filename).open("w", newline="\n") as f:
            f.write(f"{start_date}\n")
            for tmax, tmin in zip(
                group_sorted["tmax"].fillna(-99.0).tolist(),
                group_sorted["tmin"].fillna(-99.0).tolist(),
            ):
                # Comma-separated pair
                f.write(f"{float(tmax):.1f},{float(tmin):.1f}\n")

        elev_val = group_sorted["elevation_m"].iloc[0]
        elev = float(elev_val) if pd.notna(elev_val) else -99.0
        station_records.append(
            {
                "id": station_id,
                "name": station_name,
                "lat": float(lat),
                "lon": float(lon),
                "elev": elev,
                "pcp": pcp_filename,
                "tmp": tmp_filename,
            }
        )

    # Write stations.cli with pcp and tmp columns
    stations_cli = output_dir / "stations.cli"
    with stations_cli.open("w", newline="\n") as f:
        f.write("id\tname\tlat\tlon\telev\tpcp\ttmp\n")
        for r in station_records:
            f.write(
                f"{r['id']}\t{r['name']}\t{r['lat']:.4f}\t{r['lon']:.4f}\t{r['elev']:.1f}\t{r['pcp']}\t{r['tmp']}\n"
            )


if __name__ == "__main__":
    # Defaults for direct execution
    NC_FOLDER = Path("./1 Data/ERA5")
    VECTOR_FILE = Path("./1 Data/Watershed/watershed.shp")
    DEM_FILE = Path("./1 Data/Watershed/SRTM_WGS_84.tif")
    OUTPUT_DIR = Path("./outputs")
    main(NC_FOLDER, VECTOR_FILE, DEM_FILE, OUTPUT_DIR)


