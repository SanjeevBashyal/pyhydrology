from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr


# -------- User-configurable inputs --------
NC_FILE = Path("./1 Data/ERA5/ERA5_Land_total_precipitation_1995_01.nc")
TARGET_LAT = 31.0
TARGET_LON = 88.0
NUM_STEPS = 48  # number of time steps to output (e.g., hours)
OUT_TXT = Path("./outputs/point_timeseries_pcp.txt")


def _detect_lat_lon_names(ds: xr.Dataset) -> Tuple[str, str]:
    lat_candidates = ["lat", "latitude", "y"]
    lon_candidates = ["lon", "longitude", "x"]
    lat = next((n for n in lat_candidates if n in ds.coords), None)
    lon = next((n for n in lon_candidates if n in ds.coords), None)
    if lat is None or lon is None:
        raise KeyError("Could not find latitude/longitude coordinates in the dataset.")
    return lat, lon


def _normalize_lon(user_lon: float, ds_lon: xr.DataArray) -> float:
    lon_min = float(np.nanmin(ds_lon.values))
    lon_max = float(np.nanmax(ds_lon.values))
    if lon_min >= 0.0 and lon_max <= 360.0 and user_lon < 0.0:
        return user_lon + 360.0
    if lon_min >= -180.0 and lon_max <= 180.0 and user_lon > 180.0:
        return user_lon - 360.0
    return user_lon


def _find_precip_var(ds: xr.Dataset) -> str:
    # Prefer ERA5 'tp', else common alternatives
    if "tp" in ds.data_vars:
        return "tp"
    for name in ("precipitation", "total_precipitation"):
        if name in ds.data_vars:
            return name
    raise KeyError("Precipitation variable not found (looked for 'tp', 'precipitation', 'total_precipitation').")


def extract_point_timeseries(
    nc_path: Path,
    lat: float,
    lon: float,
    num_steps: Optional[int] = None,
) -> pd.Series:
    ds = xr.open_dataset(nc_path, engine="netcdf4")
    lat_name, lon_name = _detect_lat_lon_names(ds)
    lon_adj = _normalize_lon(lon, ds[lon_name])
    var_name = _find_precip_var(ds)

    # Select nearest grid point
    sel = ds.sel({lat_name: lat, lon_name: lon_adj}, method="nearest")[var_name]
    # Ensure time is sorted
    sel = sel.sortby("time")

    # Convert to millimeters if in meters
    units = sel.attrs.get("units", "")
    data = sel
    if units.lower().startswith("m"):
        data = sel * 1000.0

    series = data.to_series()
    if num_steps is not None:
        series = series.iloc[: num_steps]
    return series


def write_series_as_text(series: pd.Series, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # First line: start datetime in YYYYMMDDHH format (hourly ERA5)
    if len(series.index) == 0:
        out_path.write_text("")
        return
    start_str = pd.to_datetime(series.index[0]).strftime("%Y%m%d%H")
    with out_path.open("w", newline="\n") as f:
        f.write(f"{start_str}\n")
        for v in series.fillna(-99.0).tolist():
            f.write(f"{float(v):.3f}\n")


def main() -> None:
    series_mm = extract_point_timeseries(NC_FILE, TARGET_LAT, TARGET_LON, NUM_STEPS)
    write_series_as_text(series_mm, OUT_TXT)
    # Also print nearest gridpoint info
    ds = xr.open_dataset(NC_FILE, engine="netcdf4")
    lat_name, lon_name = _detect_lat_lon_names(ds)
    lon_adj = _normalize_lon(TARGET_LON, ds[lon_name])
    nearest = ds.sel({lat_name: TARGET_LAT, lon_name: lon_adj}, method="nearest")
    grid_lat = float(nearest[lat_name].values)
    grid_lon = float(nearest[lon_name].values)
    if grid_lon > 180:
        grid_lon -= 360
    print(f"Wrote {len(series_mm)} values to {OUT_TXT}")
    print(f"Nearest grid cell: lat={grid_lat:.4f}, lon={grid_lon:.4f}")


if __name__ == "__main__":
    main()


