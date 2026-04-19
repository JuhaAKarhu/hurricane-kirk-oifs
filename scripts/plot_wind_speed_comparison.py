#!/usr/bin/env python3
"""
plot_wind_speed_comparison.py
==============================
Generate a max sustained surface (10 m) wind speed comparison plot for
Hurricane Kirk across all OIFS SST-sensitivity runs.

Loads 10m wind components from OIFS output at each storm centre location,
computes wind speed magnitude, and plots time series for all runs.

Output: plots/kirk_wind_speed_comparison.png
"""

import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from oifs_adapter import RUNS, OIFSRun
from run_track import load_kirk_best_track, run_name_to_safe
import hurricane_functions as hf


def compute_max_wind_speed_within_radius(oifs_run, track_ds, radius_km=500):
    """
    Compute max sustained 10m wind speed within a given radius of the storm centre.

    The wind maximum in a tropical cyclone occurs at the radius of maximum wind
    (RMW), not at the pressure minimum. Searching within 500 km ensures the RMW
    is captured without contamination from remote weather systems.

    Uses hf.magnitude (xr.apply_ufunc) for full-grid wind speed, then constrains
    to a bounding box and filters by haversine distance. Handles OIFS reduced
    Gaussian grids (flattened 'values' dimension) by restructuring to 2D.

    Args:
        oifs_run   : OIFSRun instance with OIFS forecast data
        track_ds   : xarray Dataset with storm track (lat, lon, time coordinates)
        radius_km  : search radius in km (default 500)

    Returns:
        np.array: Max wind speed (m/s) within radius at each timestep
    """
    # Load 10m wind components and compute wind speed magnitude on full grid
    wind_ds = oifs_run.get_10m_wind()
    ws = hf.magnitude(wind_ds['u10m'], wind_ds['v10m'])

    # Initialize output array
    wind_speed = np.zeros(len(track_ds.time))

    for t_idx in range(len(track_ds.time)):
        lat_c = float(track_ds.lat.isel(time=t_idx))
        lon_c = float(track_ds.lon.isel(time=t_idx))

        try:
            ws_t = ws.isel(time=t_idx)

            # Handle OIFS reduced Gaussian grid (flattened 'values' dimension)
            if 'values' in ws_t.dims and 'lat' in ws_t.coords and 'lon' in ws_t.coords:
                ws_t = (
                    ws_t.to_dataset(name='ws')
                    .set_index(values=['lat', 'lon'])
                    .unstack('values')['ws']
                    .sortby('lat')
                    .sortby('lon')
                )

            # Match storm longitude convention to grid (0..360 vs -180..180)
            lon_vals = ws_t.lon.values
            grid_is_360 = float(np.nanmax(lon_vals)) > 180.0
            if grid_is_360 and lon_c < 0:
                lon_target = lon_c + 360.0
            elif (not grid_is_360) and lon_c > 180:
                lon_target = lon_c - 360.0
            else:
                lon_target = lon_c

            # Bounding box pre-filter (degrees); ~1° ≈ 111 km
            deg_pad = radius_km / 111.0 + 1.0
            ws_box = ws_t.where(
                (ws_t.lat >= lat_c - deg_pad) & (ws_t.lat <= lat_c + deg_pad) &
                (ws_t.lon >= lon_target - deg_pad) & (ws_t.lon <= lon_target + deg_pad),
                drop=True
            )

            # Exact haversine distance filter (use original lon_c for haversine)
            distances = hf.haversine(lon_c, lat_c, ws_box.lon - (360.0 if grid_is_360 and lon_c < 0 else 0.0), ws_box.lat)
            ws_within = ws_box.where(distances <= radius_km)

            wind_speed[t_idx] = float(ws_within.max(skipna=True))
        except Exception as e:
            print(f"  WARNING: t={t_idx}: {e}")
            wind_speed[t_idx] = np.nan

    return wind_speed


def main():
    """Generate wind speed comparison plot."""

    # Explicit run order (consistent with multi_run_comparison)
    run_order = ['-3K', 'baserun', '+3K', '+6K']
    # Use consistent color scheme across all project plots
    colors = {'-3K': '#1f77b4', 'baserun': '#2ca02c', '+3K': '#ff7f0e', '+6K': '#d62728'}

    # Load tracks
    tracks = {}
    for run_name in run_order:
        safe_name = run_name_to_safe(run_name)
        path = os.path.join(_ROOT, f'plots/tracks/track_{safe_name}.nc')
        if os.path.exists(path):
            tracks[run_name] = xr.open_dataset(path)
            print(f'✓ Track loaded: {run_name} ({len(tracks[run_name].time)} steps)')
        else:
            print(f'⚠ Track missing: {run_name}')

    # Load IBTrACS best track if available
    obs_track = None
    try:
        obs_track = load_kirk_best_track().to_dataframe().reset_index()
        print(f'✓ IBTrACS Kirk loaded: {len(obs_track)} records')
    except Exception as exc:
        print(f'⚠ IBTrACS load failed: {exc}')

    # Compute max wind speed for each run
    wind_data = {}
    for run_name in run_order:
        if run_name not in tracks:
            print(f'Skipping {run_name}: no track')
            continue

        print(f'\nComputing wind speed for {run_name}...')
        run_dir = RUNS.get(run_name)
        if not run_dir or not os.path.isdir(run_dir):
            print(f'  Run directory not found: {run_dir}')
            continue

        try:
            oifs_run = OIFSRun(run_dir)
            track_ds = tracks[run_name]
            wind_speed = compute_max_wind_speed_within_radius(oifs_run, track_ds, radius_km=500)
            wind_data[run_name] = wind_speed
            print(f'  ✓ Wind speed computed: min={np.nanmin(wind_speed):.1f}, max={np.nanmax(wind_speed):.1f} m/s')
        except Exception as e:
            print(f'  ERROR: {type(e).__name__}: {e}')
            import traceback
            traceback.print_exc()

    # Load ETT start times
    ett_summary_path = os.path.join(_ROOT, 'plots/tracks/ett_start_summary.csv')
    ett_start_times = {}
    if os.path.exists(ett_summary_path):
        ett_df = pd.read_csv(ett_summary_path)
        for _, row in ett_df.iterrows():
            run_name = str(row.get('run', ''))
            et_start = row.get('et_start_time_utc', '')
            if run_name and isinstance(et_start, str) and et_start.strip():
                ett_start_times[run_name] = np.datetime64(et_start)

    # Create plot
    fig, ax = plt.subplots(figsize=(11, 5))

    for run_name, track in tracks.items():
        if run_name not in wind_data:
            continue

        t_vals = np.array(track.time.values)
        wind_vals = wind_data[run_name]
        c = colors.get(run_name, 'k')

        ax.plot(t_vals, wind_vals, '.-', color=c, label=run_name, linewidth=2, markersize=6)

        # Larger marker for ETT start time
        et_t = ett_start_times.get(run_name)
        if et_t is not None and len(t_vals) > 0:
            idx_et = int(np.abs(t_vals.astype('datetime64[ns]') - et_t.astype('datetime64[ns]')).argmin())
            if not np.isnan(wind_vals[idx_et]):
                ax.plot(t_vals[idx_et], wind_vals[idx_et], 'o', ms=12, color=c,
                        markeredgecolor='k', markeredgewidth=0.8, zorder=6)

    # Add IBTrACS wind speed if available
    if obs_track is not None and 'wind' in obs_track.columns:
        try:
            obs_wind = obs_track['wind'].astype(float) * 0.51444  # Convert knots to m/s
            ax.plot(obs_track['datetime'], obs_wind, 'k--', label='IBTrACS (obs)', linewidth=2)
        except Exception as e:
            print(f'⚠ Could not plot IBTrACS wind: {e}')

    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel('Wind Speed (m s⁻¹)', fontsize=11)
    ax.set_title('Hurricane Kirk 2024 – Peak 10 m Wind Speed Within 500 km Radius', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30)
    plt.tight_layout()

    out_path = os.path.join(_ROOT, 'plots/kirk_wind_speed_comparison.png')
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f'\n✓ Saved: {out_path}')


if __name__ == '__main__':
    main()
