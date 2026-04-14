#!/usr/bin/env python3
"""Quickly diagnose GRIB coordinate structure without full data load."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, 'scripts'))

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

import cfgrib
import numpy as np

# Check surface GRIB (Gaussian grid)
print("=== ICMGG (Surface, Gaussian Grid) ===")
path_gg = '/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/int_exp_1003/ICMGGac3u+000000'
try:
    ds_gg = cfgrib.open_dataset(path_gg, engine='cfgrib', backend_kwargs={'indexpath': ''})
    print(f"Variables: {list(ds_gg.data_vars)}")
    print(f"Dims: {dict(ds_gg.dims)}")
    print(f"Coords: {list(ds_gg.coords)}")
    print(f"Has latitude: {('latitude' in ds_gg.coords or 'lat' in ds_gg.coords)}")
    print(f"Has longitude: {('longitude' in ds_gg.coords or 'lon' in ds_gg.coords)}")
    if 'latitude' in ds_gg.coords:
        print(f"  latitude shape: {ds_gg.latitude.shape}")
except Exception as e:
    print(f"ERROR: {e}")

# Check pressure-level GRIB (Spectral)
print("\n=== ICMSH (Pressure Levels, Spectral) ===")
path_sh = '/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/int_exp_1003/ICMSHac3u+000000'
try:
    # Try to open as raw GRIB first
    ds_sh_list = cfgrib.open_datasets(path_sh, backend_kwargs={'indexpath': ''})
    print(f"Number of datasets: {len(ds_sh_list)}")
    for i, ds in enumerate(ds_sh_list):
        print(f"\nDataset {i}:")
        print(f"  Variables: {list(ds.data_vars)}")
        print(f"  Dims: {dict(ds.dims)}")
        print(f"  Coords: {list(ds.coords)}")
        has_lat = ('latitude' in ds.coords or 'lat' in ds.coords)
        has_lon = ('longitude' in ds.coords or 'lon' in ds.coords)
        has_vals = 'values' in ds.dims
        print(f"  Has lat/lon: {has_lat}/{has_lon}, Has 'values' dim: {has_vals}")
        if has_lat:
            print(f"    latitude shape: {ds.latitude.shape}")
        if 'z' in ds.data_vars:
            print(f"    z shape: {ds.z.shape}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Conclusion ===")
print("If ICMSH has 'values' dim but no lat/lon coords, it's spectral-only data.")
print("Hart CPS requires spatial grids, so we need to use gridded data source or transform spectral→grid.")
