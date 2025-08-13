# pyhydrology

Tools for hydrology: ERA5 downloader and NetCDF point extractor.

## Install

```bash
pip install pyhydrology
```

## CLI

- Extract NetCDF near a lat/lon from current directory `.nc`:
```bash
pyhydrology-readnc --lat 27.7 --lon 85.3 --file 2020001.nc --var 2m_temperature
```

- Parallel ERA5-Land monthly downloader:
```bash
pyhydrology-era5-download \
  --variables 2m_temperature total_precipitation \
  --years 2016 2017 \
  --months 01 02 03 \
  --area 25.0 79.0 31.0 89.0 \
  --dest "E:/0 Python/pyhydrology/1 Data/ERA5" \
  --api-key YOUR_CDS_API_KEY
```

## Links

- Source: https://github.com/SanjeevBashyal/pyhydrology

## License

MIT
