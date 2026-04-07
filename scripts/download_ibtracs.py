"""
download_ibtracs.py
===================
Downloads the IBTrACS North Atlantic best-track NetCDF file needed for
initialising the Ribberink storm-tracking algorithm.

Hurricane Kirk (2024) will be in IBTrACS.NA.v04r00.nc; the 2025 update
of the database should include the full 2024 season.
"""

import os
import urllib.request

IBTRACS_URL = (
    'https://www.ncei.noaa.gov/data/'
    'international-best-track-archive-for-climate-stewardship-ibtracs/'
    'v04r00/access/netcdf/IBTrACS.NA.v04r00.nc'
)

DEST_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DEST_FILE = os.path.join(DEST_DIR, 'IBTrACS.NA.v04r00.nc')


def download(force=False):
    os.makedirs(DEST_DIR, exist_ok=True)
    if os.path.exists(DEST_FILE) and not force:
        print(f'IBTrACS file already exists: {DEST_FILE}')
        return DEST_FILE

    print(f'Downloading IBTrACS NA basin from:\n  {IBTRACS_URL}')
    print('(This file is ~200 MB; may take a few minutes on Mahti.)')

    def _progress(block_num, block_size, total_size):
        pct = block_num * block_size / total_size * 100
        if block_num % 100 == 0:
            print(f'  {min(pct, 100):.0f}%', end='\r', flush=True)

    urllib.request.urlretrieve(IBTRACS_URL, DEST_FILE, _progress)
    print(f'\nSaved to {DEST_FILE}')
    return DEST_FILE


def verify_kirk(ibtracs_path=None):
    """Verify that Kirk 2024 is in the IBTrACS file."""
    import xarray as xr
    import numpy as np

    path = ibtracs_path or DEST_FILE
    ds = xr.open_dataset(path, engine='netcdf4')

    # season is per-storm; select storm indices for 2024
    season_vals = ds.season.values  # shape (storm,)
    idx_2024 = np.where(season_vals == 2024)[0]

    # name has shape (storm, char); decode each
    name_arr = ds.name.values  # bytes array
    def _decode(row):
        return b''.join(row).strip(b'\x00 ').decode('ascii', errors='ignore').upper()

    names = [_decode(name_arr[i]) for i in idx_2024]
    print(f'2024 NA storms in IBTrACS ({len(names)}): {names}')

    if 'KIRK' in names:
        print('✅ KIRK found in IBTrACS 2024 season')
    else:
        print('⚠️  KIRK not yet in this version of IBTrACS')
        print('   → Try updating with: python download_ibtracs.py --force')


if __name__ == '__main__':
    import sys

    force = '--force' in sys.argv
    path = download(force=force)
    verify_kirk(path)
