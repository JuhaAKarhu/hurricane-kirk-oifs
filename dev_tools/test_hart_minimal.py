#!/usr/bin/env python3
"""Minimal hart() test with fake data to diagnose coordinate issues."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, 'ribberink_code'))

import numpy as np
import xarray as xr
import hurricane_functions as hf

print("=== Creating mock geopotential and track data ===")

# Create fake geopotential data with lat/lon coordinates
lat = np.linspace(-45, 45, 50)
lon = np.linspace(-180, 180, 100)
time = np.arange(5)
level = [300, 600]

# Create 2D grid
data_300 = np.random.rand(5, 50, 100) * 1000 + 9000  # geopotential-like values
data_600 = np.random.rand(5, 50, 100) * 1000 + 4000

zg_300 = xr.DataArray(
    data_300,
    coords={'time': time, 'lat': lat, 'lon': lon, 'level': 300},
    dims=['time', 'lat', 'lon'],
    name='zg'
)

zg_600 = xr.DataArray(
    data_600,
    coords={'time': time, 'lat': lat, 'lon': lon, 'level': 600},
    dims=['time', 'lat', 'lon'],
    name='zg'
)

# Create fake track
track_lat = np.array([20, 22, 24, 26, 28])
track_lon = np.array([-50, -48, -46, -44, -42])
track_ds = xr.Dataset({
    'lat': ('time', track_lat),
    'lon': ('time', track_lon),
}, coords={'time': time})

print(f"zg_300: {zg_300.shape}, coords: {list(zg_300.coords)}")
print(f"track: {track_ds.dims}, lat range: [{track_lat.min()}, {track_lat.max()}], lon range: [{track_lon.min()}, {track_lon.max()}]")

print("\n=== Calling hart() ===")
try:
    B, VT, B_c, VT_c, halves = hf.hart(
        zg_300, zg_600, track_ds, model='OPER', hemisphere='North', N=2
    )
    print(f"SUCCESS: B shape {B.shape}, non-zero: {np.count_nonzero(B)}, range: [{B.min():.1f}, {B.max():.1f}]")
    print(f"SUCCESS: VT shape {VT.shape}, range: [{np.nanmin(VT):.1f}, {np.nanmax(VT):.1f}]")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
