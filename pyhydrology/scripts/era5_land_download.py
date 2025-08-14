import cdsapi
import os
import shutil

###################################################################################################

url = "https://cds.climate.copernicus.eu/api/"
api_key = "5fa3ac2c-dba0-4cd4-b2b0-3cd3937f9c0b"

###################################################################################################

years = [str(i) for i in range(2016,2025)]                    ## Time range
months = ['01','02','03','04','05','06','07','08','09','10','11','12']
extents = [25.0, 79.0, 31.0, 89.0]                        ## North, West, South, East. Default: global

destination_folder = 'E:/0 Python/pyhydrology/1 Data/ERA5'  # Update with your ERA5 data directory

variables = ['2m_temperature', 'total_precipitation']

###################################################################################################

# Initialize the CDS API client
c = cdsapi.Client(key=api_key, url=url)

###################################################################################################

for iv in variables:
    for iy in years:
        for iM in months:
            # check if file was already downloaded
            if not os.path.isfile(f'{destination_folder}/ERA5_Land_{iv}_{iy}_{iM}.nc'):
                c.retrieve(
                    'reanalysis-era5-land',
                    {
                        'product_type': 'reanalysis',
                        'format': 'netcdf',
                        'variable': [iv],
                        'year': [iy],
                        'month': [iM],
                        'day': [
                            '01','02','03',
                            '04','05','06',
                            '07','08','09',
                            '10','11','12',
                            '13','14','15',
                            '16','17','18',
                            '19','20','21',
                            '22','23','24',
                            '25','26','27',
                            '28','29','30',
                            '31'
                        ],
                        'time': [
                            '00:00','01:00','02:00',
                            '03:00','04:00','05:00',
                            '06:00','07:00','08:00',
                            '09:00','10:00','11:00',
                            '12:00','13:00','14:00',
                            '15:00','16:00','17:00',
                            '18:00','19:00','20:00',
                            '21:00','22:00','23:00'
                        ],
                        'area': extents,
                    },
                    f'ERA5_Land_{iv}_{iy}_{iM}.nc'
                )
                # Specify the source and destination paths
                source_path = f'./ERA5_Land_{iv}_{iy}_{iM}.nc'  # Update with the actual file path in /content

                # Copy the file to Google Drive
                shutil.move(source_path, destination_folder)
            else:
                print(f'ERA5_{iv}_{iy}_{iM}.nc is already downloaded')

