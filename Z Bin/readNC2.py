#!/usr/bin/env python3

"""
Read a NetCDF (.nc) file and extract data for a given latitude/longitude.

Usage examples:
  python readNC2.py --lat 27.7 --lon 85.3
  python readNC2.py --lat 27.7 --lon 85.3 --file 2020001.nc
  python readNC2.py --lat 27.7 --lon 85.3 --var precipitation --out precip_at_point.csv

This script:
  - Auto-detects the .nc file in the current directory if --file is not provided
  - Auto-detects latitude/longitude coordinate names (lat/lon, latitude/longitude, y/x)
  - Selects the nearest grid cell to the provided latitude/longitude
  - Prints values for the requested variable or for all variables that have lat/lon dims
  - Optionally writes the result to CSV

Requires: xarray (and a compatible NetCDF engine such as netCDF4 or h5netcdf)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np

try:
    import xarray as xr
except Exception as import_error:  # pragma: no cover
    sys.stderr.write(
        "Error: This script requires the 'xarray' package. Install it via:\n"
        "  pip install xarray netCDF4\n"
    )
    raise import_error


def find_netcdf_file(user_path: Optional[str]) -> Path:
    if user_path:
        candidate = Path(user_path).expanduser().resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"NetCDF file not found: {candidate}")
        return candidate

    cwd = Path.cwd()
    nc_files = sorted([p for p in cwd.glob("*.nc")])
    if not nc_files:
        raise FileNotFoundError("No .nc files found in the current directory.")
    return nc_files[0]


def detect_lat_lon_names(dataset: xr.Dataset) -> Tuple[str, str]:
    lat_candidates = ["lat", "latitude", "y", "nav_lat"]
    lon_candidates = ["lon", "longitude", "x", "nav_lon"]

    def pick_name(candidates: List[str]) -> Optional[str]:
        for name in candidates:
            if name in dataset.coords or name in dataset.variables:
                return name
        return None

    lat_name = pick_name(lat_candidates)
    lon_name = pick_name(lon_candidates)

    if lat_name is None or lon_name is None:
        dataset_coords = ", ".join(list(dataset.coords))
        dataset_vars = ", ".join(list(dataset.variables))
        raise KeyError(
            "Could not detect latitude/longitude coordinate names.\n"
            f"Available coords: {dataset_coords}\n"
            f"Available variables: {dataset_vars}\n"
            "Tried: lat/latitude/y/nav_lat and lon/longitude/x/nav_lon"
        )

    return lat_name, lon_name


def normalize_longitude(user_lon: float, dataset_lon: xr.DataArray) -> float:
    lon_min = float(np.nanmin(dataset_lon.values))
    lon_max = float(np.nanmax(dataset_lon.values))

    if lon_min >= 0.0 and lon_max <= 360.0 and user_lon < 0.0:
        return user_lon + 360.0
    if lon_min >= -180.0 and lon_max <= 180.0 and user_lon > 180.0:
        return user_lon - 360.0
    return user_lon


def select_at_point(dataset: xr.Dataset, lat: float, lon: float, lat_name: str, lon_name: str) -> xr.Dataset:
    ds_lon = dataset[lon_name]
    lon_adj = normalize_longitude(lon, ds_lon)

    try:
        selected = dataset.sel({lat_name: lat, lon_name: lon_adj}, method="nearest")
    except Exception as select_error:
        raise ValueError(
            f"Failed to select nearest grid cell using {lat_name} and {lon_name}: {select_error}"
        )

    return selected


def variables_with_lat_lon(dataset: xr.Dataset, lat_name: str, lon_name: str) -> List[str]:
    candidates: List[str] = []
    for var_name, data_var in dataset.data_vars.items():
        dims = list(data_var.dims)
        if lat_name in dims and lon_name in dims:
            candidates.append(var_name)
    return candidates


def print_or_save_result(
    selected: xr.Dataset,
    var_name: Optional[str],
    lat_name: str,
    lon_name: str,
    outfile: Optional[str],
) -> None:
    if var_name is not None:
        if var_name not in selected:
            available = ", ".join(list(selected.data_vars))
            raise KeyError(f"Variable '{var_name}' not found. Available: {available}")
        data = selected[var_name]
        if outfile:
            df = data.to_dataframe(name=var_name).reset_index()
            Path(outfile).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(outfile, index=False)
            print(f"Saved '{var_name}' at nearest point to CSV: {outfile}")
        else:
            print(f"Variable: {var_name}")
            print(repr(data))
        return

    vars_at_point = variables_with_lat_lon(selected, lat_name, lon_name)
    if not vars_at_point:
        available = ", ".join(list(selected.data_vars))
        raise ValueError(
            "No data variables with both latitude and longitude dimensions were found.\n"
            f"Available variables: {available}"
        )

    if outfile:
        combined = []
        for name in vars_at_point:
            df = selected[name].to_dataframe(name=name).reset_index()
            combined.append(df)
        # Outer-merge on shared indexes to retain all dims without duplication
        from functools import reduce
        import pandas as pd

        merged = reduce(lambda left, right: pd.merge(left, right, how="outer"), combined)
        Path(outfile).parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(outfile, index=False)
        print(f"Saved variables at nearest point to CSV: {outfile}")
        return

    for name in vars_at_point:
        print(f"Variable: {name}")
        print(repr(selected[name]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract data from NetCDF at given lat/lon")
    parser.add_argument("--lat", type=float, required=True, help="Latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="Longitude in degrees")
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to NetCDF file (.nc). If omitted, the first .nc in the current directory is used.",
    )
    parser.add_argument(
        "--var",
        type=str,
        default=None,
        help="Specific variable name to extract. If omitted, all variables with lat/lon are printed/saved.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional CSV path to save the extracted values (e.g., output.csv)",
    )

    args = parser.parse_args()

    nc_path = find_netcdf_file(args.file)
    try:
        dataset = xr.open_dataset(nc_path)
    except Exception as open_error:
        raise RuntimeError(f"Failed to open NetCDF file '{nc_path}': {open_error}")

    try:
        lat_name, lon_name = detect_lat_lon_names(dataset)
    except Exception as detect_error:
        dataset.close()
        raise detect_error

    selected = select_at_point(dataset, args.lat, args.lon, lat_name, lon_name)
    try:
        print_or_save_result(selected, args.var, lat_name, lon_name, args.out)
    finally:
        dataset.close()


if __name__ == "__main__":
    main()


