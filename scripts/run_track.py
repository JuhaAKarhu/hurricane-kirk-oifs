"""
run_track.py
============
Computes the Hurricane Kirk storm track for each OIFS SST-perturbation run
using Ribberink's storm_tracker function (hurricane_functions.py, model='OPER').

Outputs one NetCDF file per run: plots/tracks/track_<runname>.nc

Usage:
    cd /users/jfkarhu/Numlab/hurricane_kirk
    python scripts/run_track.py
"""

import os
import sys
import pickle
import traceback
import numpy as np
import pandas as pd
import xarray as xr

# Make ribberink_code importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ribberink_code'))
sys.path.insert(0, os.path.dirname(__file__))

from oifs_adapter import RUNS, OIFSRun, INIT_DATETIME
import hurricane_functions as hf


def _dist_broadcast_safe(a, b):
    """xarray-safe magnitude helper used by Ribberink storm_tracker."""
    aa, bb = xr.broadcast(a, b)
    return np.sqrt(aa**2 + bb**2)


# Patch Ribberink helper for compatibility with newer xarray versions.
hf.dist = _dist_broadcast_safe

# Path to IBTrACS file
IBTRACS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'IBTrACS.NA.v04r00.nc'
)
BEST_TRACK_PICKLE = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'kirk_best_track.pickle'
)

# Output directory for tracks
TRACK_DIR = os.path.join(os.path.dirname(__file__), '..', 'plots', 'tracks')


def load_kirk_best_track():
    """Load Kirk 2024 best track (pickle first, IBTrACS fallback)."""
    if os.path.exists(BEST_TRACK_PICKLE):
        with open(BEST_TRACK_PICKLE, 'rb') as f:
            bt = pickle.load(f)
        bt_df = pd.DataFrame({
            'time': pd.to_datetime(bt['time']),
            'lat': bt['lat'],
            'lon': bt['lon'],
            'min_pres': bt['pres'],
        })
        best_track = xr.Dataset.from_dataframe(bt_df).set_index(index='time').rename(index='time')
        print(
            f'Best track loaded from pickle: {best_track.sizes["time"]} timesteps, '
            f'{pd.to_datetime(best_track.time.values[0])} -> {pd.to_datetime(best_track.time.values[-1])}'
        )
        return best_track

    if not os.path.exists(IBTRACS_PATH):
        raise FileNotFoundError(
            f'Best-track file not found: {BEST_TRACK_PICKLE} and {IBTRACS_PATH}\n'
            'Run: python scripts/download_ibtracs.py'
        )

    orig_dir = os.getcwd()
    os.chdir(os.path.dirname(IBTRACS_PATH))
    try:
        best_track = hf.import_ibtracs(hurr_year=2024, storm_name=b'KIRK')
    finally:
        os.chdir(orig_dir)
    print(
        f'Best track loaded from IBTrACS: {len(best_track.time)} timesteps, '
        f'{best_track.time.values[0]} -> {best_track.time.values[-1]}'
    )
    return best_track


def compute_track(run_name, oifs_run, best_track):
    """
    Run storm_tracker on a single OIFSRun and return track DataFrame.

    Ribberink's storm_tracker signature:
        storm_tracker(data, best_track, model, s_size)
    where data must have:
        - .msl variable (Pa) with dims (time, lat, lon)
        - .time coordinate (datetime64)
    Using model='OPER' since OIFS MSLP is named 'msl' (same as ECMWF operational).
    """
    print(f'\nTracking: {run_name}')
    msl_ds = oifs_run.get_msl()

    # Align best-track longitudes with model grid convention.
    # OIFS often uses 0..360, while best-track uses -180..180.
    bt = best_track.copy()
    if float(msl_ds.lon.max()) > 180 and float(bt.lon.min()) < 0:
        bt['lon'] = (bt.lon % 360)

    track_df = hf.storm_tracker(msl_ds, bt, model='OPER', s_size=4)
    print(f'  Track computed: {len(track_df)} timesteps')
    return track_df


def track_df_to_xarray(track_df, run_name):
    """Convert storm_tracker DataFrame output to an xarray Dataset."""
    ds = xr.Dataset.from_dataframe(
        track_df.set_index('time') if 'time' in track_df.columns
        else track_df.set_index('datetime')
    )
    ds.attrs['run'] = run_name
    ds.attrs['description'] = (
        f'Hurricane Kirk storm track from OIFS {run_name} run. '
        'Produced by run_track.py using Ribberink storm_tracker.'
    )
    return ds


def save_track(ds, run_name):
    """Save track to NetCDF."""
    os.makedirs(TRACK_DIR, exist_ok=True)
    out_path = os.path.join(TRACK_DIR, f'track_{run_name.replace("+", "p")}.nc')
    ds.to_netcdf(out_path)
    print(f'  Saved: {out_path}')
    return out_path


def main():
    best_track = load_kirk_best_track()
    tracks = {}

    for run_name, run_dir in RUNS.items():
        if not os.path.isdir(run_dir):
            print(f'Skipping {run_name}: directory not found ({run_dir})')
            continue
        try:
            oifs_run = OIFSRun(run_dir)
            track_df = compute_track(run_name, oifs_run, best_track)
            track_ds = track_df_to_xarray(track_df, run_name)
            save_track(track_ds, run_name)
            tracks[run_name] = track_ds
        except Exception as e:
            print(f'ERROR for {run_name}: {repr(e)}')
            traceback.print_exc()
            continue

    print(f'\nDone. Computed tracks for: {list(tracks.keys())}')
    return tracks


if __name__ == '__main__':
    main()
