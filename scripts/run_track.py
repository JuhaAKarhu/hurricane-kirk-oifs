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


def _angular_lon_distance(lon_vals, lon0):
    """Return shortest signed distance (deg) between lon_vals and lon0."""
    return ((lon_vals - lon0 + 180.0) % 360.0) - 180.0


def local_storm_tracker(msl_ds, best_track, s_size=4.0):
    """Track storm center by minimum MSL in a moving search box.

    This mirrors the Ribberink logic but avoids xarray compatibility
    issues in the original helper functions.
    """
    da = msl_ds.msl
    use_360 = float(da.lon.max()) > 180.0

    bt_time = pd.to_datetime(best_track.time.values)
    bt_lat = best_track.lat.values.astype(float)
    bt_lon = best_track.lon.values.astype(float)
    if use_360:
        bt_lon = bt_lon % 360.0

    times = pd.to_datetime(da.time.values)
    enter = max(times[0], bt_time[0])
    idx_enter = int(np.searchsorted(times, enter))

    recs = []
    guess_lat = float(bt_lat[int(np.searchsorted(bt_time, enter))])
    guess_lon = float(bt_lon[int(np.searchsorted(bt_time, enter))])

    for ti in range(idx_enter, len(times)):
        frame = da.isel(time=ti)
        lat = frame.lat
        lon = frame.lon

        lat_mask = np.abs(lat - guess_lat) <= s_size
        if use_360:
            lon_mask = np.abs(_angular_lon_distance(lon, guess_lon)) <= s_size
        else:
            lon_mask = np.abs(lon - guess_lon) <= s_size

        box = frame.where(lat_mask & lon_mask, drop=True)
        if box.size == 0:
            # Fallback: expand search box once, then use domain-wide minimum.
            lat_mask2 = np.abs(lat - guess_lat) <= (2.0 * s_size)
            if use_360:
                lon_mask2 = np.abs(_angular_lon_distance(lon, guess_lon)) <= (2.0 * s_size)
            else:
                lon_mask2 = np.abs(lon - guess_lon) <= (2.0 * s_size)
            box = frame.where(lat_mask2 & lon_mask2, drop=True)
            if box.size == 0:
                box = frame

        df = box.to_dataframe(name='msl').dropna().reset_index()
        if df.empty:
            continue

        msl_min = df['msl'].min()
        cand = df[df['msl'] == msl_min].copy()
        if use_360:
            dlon = _angular_lon_distance(cand['lon'].to_numpy(), guess_lon)
        else:
            dlon = cand['lon'].to_numpy() - guess_lon
        d = (cand['lat'].to_numpy() - guess_lat) ** 2 + dlon ** 2
        k = int(np.argmin(d))
        row = cand.iloc[k]

        guess_lat = float(row['lat'])
        guess_lon = float(row['lon'])
        out_lon = ((guess_lon + 180.0) % 360.0) - 180.0 if use_360 else guess_lon

        recs.append({
            'time': pd.to_datetime(row['time']),
            'lat': guess_lat,
            'lon': out_lon,
            'msl': float(row['msl']),
        })

    if not recs:
        raise RuntimeError('Local tracker produced no points')
    return pd.DataFrame(recs)


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

    track_df = local_storm_tracker(msl_ds, bt, s_size=4)
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
