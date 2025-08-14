import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import cdsapi


###################################################################################################

url = "https://cds.climate.copernicus.eu/api/"
api_key = "5fa3ac2c-dba0-4cd4-b2b0-3cd3937f9c0b"

# Concurrency settings
max_workers = 4  # Adjust based on your network and CDS limits

###################################################################################################

years = [str(i) for i in range(2016, 2024)]  # Time range
months = [
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
]
extents = [25.0, 79.0, 31.0, 89.0]  # North, West, South, East. Default: global

destination_folder = "E:/0 Python/pyhydrology/1 Data/ERA5"  # Update with your ERA5 data directory

variables = ["2m_temperature", "total_precipitation"]

###################################################################################################


def build_request_payload(variable: str, year: str, month: str):
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
        "area": extents,
    }


def make_job_list() -> List[Tuple[str, str, str, str]]:
    jobs: List[Tuple[str, str, str, str]] = []
    os.makedirs(destination_folder, exist_ok=True)
    for variable in variables:
        for year in years:
            for month in months:
                target_name = f"ERA5_Land_{variable}_{year}_{month}.nc"
                dest_path = os.path.join(destination_folder, target_name)
                if os.path.isfile(dest_path):
                    print(f"Already exists, skipping: {dest_path}")
                    continue
                jobs.append((variable, year, month, dest_path))
    return jobs


def download_one(job: Tuple[str, str, str, str]) -> Tuple[str, bool, str]:
    variable, year, month, dest_path = job
    target_name = os.path.basename(dest_path)

    # Per-thread client to avoid shared-state issues
    client = cdsapi.Client(key=api_key, url=url)

    payload = build_request_payload(variable, year, month)

    # Unique temp directory for the job
    tmp_dir = tempfile.mkdtemp(prefix="era5_dl_")
    tmp_path = os.path.join(tmp_dir, target_name)

    try:
        client.retrieve("reanalysis-era5-land", payload, tmp_path)
        # Move to destination atomically
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.move(tmp_path, dest_path)
        return dest_path, True, "ok"
    except Exception as e:
        return dest_path, False, str(e)
    finally:
        # Best-effort cleanup of temp directory
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


def main() -> None:
    jobs = make_job_list()
    if not jobs:
        print("All requested files are already present. Nothing to do.")
        return

    print(f"Submitting {len(jobs)} requests with max_workers={max_workers}...")

    successes = 0
    failures: List[Tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures_map = {executor.submit(download_one, job): job for job in jobs}
        for fut in as_completed(futures_map):
            dest_path, ok, message = fut.result()
            if ok:
                successes += 1
                print(f"DONE: {dest_path}")
            else:
                failures.append((dest_path, message))
                print(f"FAILED: {dest_path} -> {message}")

    print(f"Completed. Success: {successes}, Failed: {len(failures)}")
    if failures:
        print("Failures summary:")
        for path, msg in failures:
            print(f" - {path}: {msg}")


if __name__ == "__main__":
    main()


