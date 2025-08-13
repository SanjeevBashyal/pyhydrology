from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
import xarray as xr


def _detect_lat_lon_names(dataset: xr.Dataset) -> Tuple[str, str]:
    lat_candidates = ["lat", "latitude", "y", "nav_lat"]
    lon_candidates = ["lon", "longitude", "x", "nav_lon"]

    def pick(candidates: List[str]) -> Optional[str]:
        for name in candidates:
            if name in dataset.coords or name in dataset.variables:
                return name
        return None

    lat_name = pick(lat_candidates)
    lon_name = pick(lon_candidates)
    if lat_name is None or lon_name is None:
        raise KeyError("Could not detect latitude/longitude variable names")
    return lat_name, lon_name


def _normalize_longitude(user_lon: float, dataset_lon: xr.DataArray) -> float:
    lon_min = float(np.nanmin(dataset_lon.values))
    lon_max = float(np.nanmax(dataset_lon.values))
    if lon_min >= 0.0 and lon_max <= 360.0 and user_lon < 0.0:
        return user_lon + 360.0
    if lon_min >= -180.0 and lon_max <= 180.0 and user_lon > 180.0:
        return user_lon - 360.0
    return user_lon


def extract_point_from_netcdf(
    lat: float,
    lon: float,
    file: Optional[str] = None,
    var: Optional[str] = None,
):
    nc_path = (
        Path(file).expanduser().resolve() if file else next(Path.cwd().glob("*.nc"))
    )
    ds = xr.open_dataset(nc_path)
    lat_name, lon_name = _detect_lat_lon_names(ds)
    lon_adj = _normalize_longitude(lon, ds[lon_name])
    selected = ds.sel({lat_name: lat, lon_name: lon_adj}, method="nearest")
    if var:
        if var not in selected:
            raise KeyError(f"Variable '{var}' not in dataset")
        return selected[var]
    return selected


def cli():
    parser = argparse.ArgumentParser(description="Extract NetCDF at given lat/lon")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--file", type=str, default=None)
    parser.add_argument("--var", type=str, default=None)
    args = parser.parse_args()
    da_or_ds = extract_point_from_netcdf(args.lat, args.lon, args.file, args.var)
    # Print a compact representation
    print(repr(da_or_ds))


