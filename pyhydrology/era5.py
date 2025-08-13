from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import cdsapi


def _build_payload(variable: str, year: str, month: str, area: List[float]):
    return {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": [variable],
        "year": [year],
        "month": [month],
        "day": [
            "01",
            "02",
            "03",
            "04",
            "05",
            "06",
            "07",
            "08",
            "09",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
            "20",
            "21",
            "22",
            "23",
            "24",
            "25",
            "26",
            "27",
            "28",
            "29",
            "30",
            "31",
        ],
        "time": [
            "00:00",
            "01:00",
            "02:00",
            "03:00",
            "04:00",
            "05:00",
            "06:00",
            "07:00",
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
            "17:00",
            "18:00",
            "19:00",
            "20:00",
            "21:00",
            "22:00",
            "23:00",
        ],
        "area": area,
    }


def _download_one(job, api_key: str, url: str):
    variable, year, month, area, dest_path = job
    target_name = os.path.basename(dest_path)
    client = cdsapi.Client(key=api_key, url=url)
    payload = _build_payload(variable, year, month, area)
    tmp_dir = tempfile.mkdtemp(prefix="era5_dl_")
    tmp_path = os.path.join(tmp_dir, target_name)

    try:
        client.retrieve("reanalysis-era5-land", payload, tmp_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.move(tmp_path, dest_path)
        return dest_path, True, "ok"
    except Exception as e:
        return dest_path, False, str(e)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        try:
            if os.path.isdir(tmp_dir):
                os.rmdir(tmp_dir)
        except Exception:
            pass


def download_era5_parallel(
    variables: List[str],
    years: List[str],
    months: List[str],
    area: List[float],
    destination_folder: str,
    api_key: str,
    url: str,
    max_workers: int = 4,
):
    os.makedirs(destination_folder, exist_ok=True)
    jobs = []
    for variable in variables:
        for year in years:
            for month in months:
                target_name = f"ERA5_Land_{variable}_{year}_{month}.nc"
                dest_path = os.path.join(destination_folder, target_name)
                if os.path.isfile(dest_path):
                    continue
                jobs.append((variable, year, month, area, dest_path))

    if not jobs:
        return []

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_download_one, job, api_key, url) for job in jobs]
        for fut in as_completed(futures):
            results.append(fut.result())
    return results


def cli():
    parser = argparse.ArgumentParser(description="Parallel ERA5-Land downloader")
    parser.add_argument("--variables", nargs="+", default=["2m_temperature", "total_precipitation"])
    parser.add_argument("--years", nargs="+", default=[str(i) for i in range(2016, 2024)])
    parser.add_argument("--months", nargs="+", default=[f"{i:02d}" for i in range(1, 13)])
    parser.add_argument("--area", nargs=4, type=float, default=[25.0, 79.0, 31.0, 89.0])
    parser.add_argument("--dest", type=str, required=True)
    parser.add_argument("--api-key", type=str, required=True)
    parser.add_argument("--url", type=str, default="https://cds.climate.copernicus.eu/api/")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    results = download_era5_parallel(
        variables=args.variables,
        years=args.years,
        months=args.months,
        area=args.area,
        destination_folder=args.dest,
        api_key=args.api_key,
        url=args.url,
        max_workers=args.workers,
    )
    successes = sum(1 for _, ok, _ in results if ok)
    fails = [(p, m) for p, ok, m in results if not ok]
    print(f"Success: {successes}, Failed: {len(fails)}")
    if fails:
        for p, m in fails:
            print(f" - {p}: {m}")


