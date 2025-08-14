from __future__ import annotations

import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Tuple

import cdsapi


class ERA5Downloader:
    """
    Downloader for ERA5-Land monthly data via CDS API.

    Encapsulates both single-threaded and parallel download logic.
    """

    def __init__(self, api_key: str, url: str, destination_folder: str, area: List[float]) -> None:
        self.api_key = api_key
        self.url = url
        self.destination_folder = destination_folder
        self.area = area
        os.makedirs(self.destination_folder, exist_ok=True)

    def _build_payload(self, variable: str, year: str, month: str) -> dict:
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
            "area": self.area,
        }

    def _target_path(self, variable: str, year: str, month: str) -> str:
        filename = f"ERA5_Land_{variable}_{year}_{month}.nc"
        return os.path.join(self.destination_folder, filename)

    def file_exists(self, variable: str, year: str, month: str) -> bool:
        return os.path.isfile(self._target_path(variable, year, month))

    def download_month(self, variable: str, year: str, month: str) -> Tuple[str, bool, str]:
        """Download a single monthly file, returning (dest_path, ok, message)."""
        dest_path = self._target_path(variable, year, month)
        if os.path.isfile(dest_path):
            return dest_path, True, "exists"

        client = cdsapi.Client(key=self.api_key, url=self.url)
        payload = self._build_payload(variable, year, month)

        tmp_dir = tempfile.mkdtemp(prefix="era5_dl_")
        tmp_path = os.path.join(tmp_dir, os.path.basename(dest_path))
        try:
            client.retrieve("reanalysis-era5-land", payload, tmp_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.move(tmp_path, dest_path)
            return dest_path, True, "ok"
        except Exception as exc:  # noqa: BLE001 broad is ok at boundary
            return dest_path, False, str(exc)
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

    def download_many(
        self,
        variables: Iterable[str],
        years: Iterable[str],
        months: Iterable[str],
        max_workers: int = 4,
    ) -> List[Tuple[str, bool, str]]:
        """Download multiple months potentially in parallel.

        Returns list of (dest_path, ok, message).
        """
        jobs = []
        for variable in variables:
            for year in years:
                for month in months:
                    if self.file_exists(variable, year, month):
                        continue
                    jobs.append((variable, year, month))

        if not jobs:
            return []

        results: List[Tuple[str, bool, str]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(self.download_month, v, y, m) for v, y, m in jobs]
            for fut in as_completed(futures):
                results.append(fut.result())
        return results


