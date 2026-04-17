#!/usr/bin/env python3
"""
Plot three-panel 900-600 hPa geopotential height difference anomalies (Ribberink Fig 6 style).
Anomalies computed relative to full-run average over ±5° domain around storm track.
For Hurricane Kirk control run at three evolution stages.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle
import xarray as xr
import pandas as pd
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/users/jfkarhu/Numlab/hurricane_kirk')

from scripts.oifs_adapter import OIFSRun
from scripts.run_track import load_kirk_best_track


def get_storm_velocity(track_ds, timestamp):
    """
    Get storm velocity (forward direction) at a given timestamp.
    Returns normalized velocity vector components.
    """
    times = track_ds['time'].values
    idx = np.argmin(np.abs(times - np.datetime64(timestamp)))

    if idx == 0:
        idx = 1
    if idx >= len(times) - 1:
        idx = len(times) - 2

    lat1 = float(track_ds['lat'].isel(time=idx-1).values)
    lon1 = float(track_ds['lon'].isel(time=idx-1).values)
    lat2 = float(track_ds['lat'].isel(time=idx+1).values)
    lon2 = float(track_ds['lon'].isel(time=idx+1).values)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    norm = np.sqrt(dlat**2 + dlon**2)
    if norm > 0:
        dlat /= norm
        dlon /= norm

    return dlat, dlon


def load_track_and_position(timestamp):
    """Load track and get storm center position at given timestamp."""
    track_file = '/users/jfkarhu/Numlab/hurricane_kirk/plots/tracks/track_baserun.nc'
    track_ds = xr.open_dataset(track_file)

    times = track_ds['time'].values
    idx = np.argmin(np.abs(times - np.datetime64(timestamp)))

    lat = float(track_ds['lat'].isel(time=idx).values)
    lon = float(track_ds['lon'].isel(time=idx).values)

    return lat, lon, track_ds


def compute_thermal_asymmetry(timestamp, run_name='baserun'):
    """Get thermal asymmetry parameter B from precomputed ETT analysis."""
    try:
        safe_name = run_name.replace('+', 'p').replace('-', 'm')
        csv_file = f'/users/jfkarhu/Numlab/hurricane_kirk/plots/tracks/ett_B_timeseries_{safe_name}.csv'

        df = pd.read_csv(csv_file)
        df['time'] = pd.to_datetime(df['time'])
        target_time = pd.to_datetime(timestamp)

        idx = (df['time'] - target_time).abs().idxmin()
        B_value = df.loc[idx, 'B_smooth']

        return B_value
    except Exception as e:
        print(f"Warning: Could not load B: {e}")
        return None


def compute_geopotential_difference_anomaly(oifs_run, track_ds, timestamp, lat_center, lon_center, 
                                            domain_half_width=5.0, radius_km=500, gridded_z_dir=None):
    """
    Compute 900-600 hPa geopotential height difference anomaly.
    Anomaly = (inst 900-600) - (full-run mean 900-600 over ±5° domain)
    
    Returns anomaly and distance grid within the domain.
    """
    # Load both levels
    z_data = oifs_run.get_geopotential_height(levels=(300, 600, 900), gridded_z_dir=gridded_z_dir)
    
    # Get full lat/lon grid
    lat_full = z_data['lat'].values
    lon_full = z_data['lon'].values
    
    # Subset to ±5° domain around track's latitude range for baseline computation
    lat_min = np.min(track_ds['lat'].values) - domain_half_width
    lat_max = np.max(track_ds['lat'].values) + domain_half_width
    lat_idx_baseline = (lat_full >= lat_min) & (lat_full <= lat_max)
    
    # Compute full-run baseline: mean 900-600 difference over ±5° lat band
    z_900_all = z_data.sel(level=900, method='nearest')['zg'].isel(lat=lat_idx_baseline)
    z_600_all = z_data.sel(level=600, method='nearest')['zg'].isel(lat=lat_idx_baseline)
    z_diff_baseline = (z_900_all - z_600_all).mean(dim=['time', 'lat', 'lon']).values
    
    # Select current timestep for both levels
    z_ts_900 = z_data.sel(time=timestamp, method='nearest').sel(level=900, method='nearest')['zg']
    z_ts_600 = z_data.sel(time=timestamp, method='nearest').sel(level=600, method='nearest')['zg']
    
    # Compute difference at this timestep
    z_diff_ts = z_ts_900 - z_ts_600
    
    # Compute anomaly: instantaneous difference minus full-run baseline
    z_anom_full = z_diff_ts - z_diff_baseline
    
    # Now subset current timestep to ±5° domain around storm center for plotting
    lat_idx_ts = (lat_full >= lat_center - domain_half_width) & (lat_full <= lat_center + domain_half_width)
    lon_idx_ts = (lon_full >= lon_center - domain_half_width) & (lon_full <= lon_center + domain_half_width)
    
    z_anom_subset = z_anom_full.isel(lat=lat_idx_ts, lon=lon_idx_ts).values
    lat_subset = lat_full[lat_idx_ts]
    lon_subset = lon_full[lon_idx_ts]
    
    # Compute distance from storm center for all subset points
    lon_grid, lat_grid = np.meshgrid(lon_subset, lat_subset)
    lat_center_rad = np.radians(lat_center)
    lon_center_rad = np.radians(lon_center)
    lat_grid_rad = np.radians(lat_grid)
    lon_grid_rad = np.radians(lon_grid)
    
    dlat = lat_grid_rad - lat_center_rad
    dlon = lon_grid_rad - lon_center_rad
    a = np.sin(dlat/2)**2 + np.cos(lat_center_rad) * np.cos(lat_grid_rad) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    EARTH_RADIUS_KM = 6371
    distance_grid = EARTH_RADIUS_KM * c
    
    return z_anom_subset, lon_subset, lat_subset, distance_grid, lat_center, lon_center


def compute_thermal_asymmetry(timestamp, run_name='baserun'):
    """
    Get thermal asymmetry parameter B (lower layer, 600-900 hPa) from precomputed ETT analysis.
    Loads B values from existing ett_B_timeseries CSV files.
    """
    import pandas as pd
    from datetime import datetime

    try:
        # Map run names to safe filenames
        safe_name = run_name.replace('+', 'p').replace('-', 'm')
        csv_file = f'/users/jfkarhu/Numlab/hurricane_kirk/plots/tracks/ett_B_timeseries_{safe_name}.csv'

        # Read the B timeseries
        df = pd.read_csv(csv_file)
        df['time'] = pd.to_datetime(df['time'])

        # Parse the target timestamp
        target_time = pd.to_datetime(timestamp)

        # Find the closest timestamp
        idx = (df['time'] - target_time).abs().idxmin()
        B_value = df.loc[idx, 'B_smooth']  # Use smoothed B values

        return B_value
    except Exception as e:
        print(f"Warning: Could not load B from {csv_file}: {e}")
        return None


def plot_geopotential_comparison():
    """Create three-panel 900-600 hPa difference anomaly figure with unified coloring and B parameters."""
    
    run_dir = '/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/int_exp_1003'
    gridded_z_dir = '/scratch/project_2001271/jfkarhu/cps_z_gridded/baserun'
    oifs_run = OIFSRun(run_dir=run_dir)
    
    timestamps = [
        ('2024-10-05 06:00', 'Hurricane Stage'),
        ('2024-10-06 06:00', 'ETT Start'),
        ('2024-10-08 06:00', 'Extratropical Stage'),
    ]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    fig.suptitle('900-600 hPa Geopotential Height Difference Anomalies', fontsize=14, fontweight='bold')
    
    _, _, track_ds = load_track_and_position(timestamps[0][0])
    
    # Pre-compute all anomalies for unified color range
    all_anom_data = []
    all_params = []
    
    for timestamp_str, label in timestamps:
        lat_center, lon_center, _ = load_track_and_position(timestamp_str)
        
        z_anom, lon_subset, lat_subset, distance_grid, lat_c, lon_c = compute_geopotential_difference_anomaly(
            oifs_run, track_ds, timestamp_str, lat_center, lon_center, 
            domain_half_width=5.0, radius_km=500, gridded_z_dir=gridded_z_dir
        )
        
        B = compute_thermal_asymmetry(timestamp=timestamp_str, run_name='baserun')
        
        all_anom_data.append({
            'z_anom': z_anom,
            'lon_subset': lon_subset,
            'lat_subset': lat_subset,
            'distance_grid': distance_grid,
            'lat_center': lat_c,
            'lon_center': lon_c,
        })
        all_params.append({'B': B, 'label': label, 'timestamp': timestamp_str})
    
    # Unified color range
    all_anom_values = np.concatenate([np.abs(d['z_anom']).flatten() for d in all_anom_data])
    vmax_unified = np.nanpercentile(all_anom_values, 90)
    levels = np.linspace(-vmax_unified, vmax_unified, 21)
    
    # Plot each panel
    cf_list = []
    for idx, (data, params) in enumerate(zip(all_anom_data, all_params)):
        ax = axes[idx]
        z_anom = data['z_anom'].copy()
        lon_subset = data['lon_subset']
        lat_subset = data['lat_subset']
        distance_grid = data['distance_grid']
        lat_center = data['lat_center']
        lon_center = data['lon_center']
        
        # Create mesh
        lon_mesh, lat_mesh = np.meshgrid(lon_subset, lat_subset)
        
        # Mask area outside 500 km: set to NaN
        z_anom[distance_grid > 500] = np.nan
        
        # Plot
        cf = ax.contourf(lon_mesh, lat_mesh, z_anom, levels=levels, cmap='RdBu_r', extend='both')
        ax.contour(lon_mesh, lat_mesh, z_anom, levels=levels[::2], colors='k', linewidths=0.5, alpha=0.3)
        
        # Circle outline at 500 km
        circle_outline = Circle((lon_center, lat_center), 500/111.0, fill=False, 
                              edgecolor='black', linewidth=2, linestyle='--', alpha=0.7, zorder=50)
        ax.add_patch(circle_outline)
        
        # Storm translation direction - extend arrow to 500 km circle edge
        dlat_vel, dlon_vel = get_storm_velocity(track_ds, params['timestamp'])
        # Calculate arrow length to reach just at the inner edge of 500 km circle
        # Subtract arrow head length (0.25 deg) so tip lands at circle edge
        arrow_length_deg = (500.0 / 111.0) - 0.25
        ax.arrow(lon_center, lat_center, dlon_vel * arrow_length_deg, dlat_vel * arrow_length_deg,
                head_width=0.3, head_length=0.25, fc='white', ec='white', linewidth=2.5, zorder=100)
        
        # Perpendicular dashed line (left-right separation for B calculation)
        # Perpendicular to motion direction
        perp_dlon = dlat_vel
        perp_dlat = -dlon_vel
        perp_length_deg = 500.0 / 111.0
        ax.plot([lon_center - perp_dlon * perp_length_deg, lon_center + perp_dlon * perp_length_deg],
               [lat_center - perp_dlat * perp_length_deg, lat_center + perp_dlat * perp_length_deg],
               'w--', linewidth=2.5, alpha=0.8, zorder=99)
        
        # Storm center
        ax.plot(lon_center, lat_center, 'w+', markersize=14, markeredgewidth=3, zorder=101)
        
        # Domain extent
        ax.set_xlim(lon_center - 5.0, lon_center + 5.0)
        ax.set_ylim(lat_center - 5.0, lat_center + 5.0)
        ax.set_aspect('equal')
        
        ax.set_xlabel('Longitude (°E)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Latitude (°N)', fontsize=11, fontweight='bold')
        ax.set_title(f'{params["label"]}\n{params["timestamp"][:10]} {params["timestamp"][11:16]} UTC', 
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
        ax.tick_params(labelsize=10)
        
        # B parameter in top-right
        if params['B'] is not None:
            b_text = f'B = {params["B"]:.1f} m'
        else:
            b_text = 'B = N/A'
        ax.text(0.98, 0.98, b_text, transform=ax.transAxes, fontsize=11, fontweight='bold',
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='black'))
        
        cf_list.append(cf)
    
    # Single colorbar
    cbar_ax = fig.add_axes([0.88, 0.18, 0.015, 0.6])
    cbar = plt.colorbar(cf_list[0], cax=cbar_ax, orientation='vertical')
    cbar.set_label('Anomaly (m)', fontsize=11, fontweight='bold')
    
    # Legend
    legend_elements = [
        mpatches.Patch(facecolor='none', edgecolor='white', linewidth=2.5, 
                      label='Storm motion direction (white arrow)'),
        plt.Line2D([0], [0], marker='+', color='w', linestyle='', markersize=12, 
                  markeredgewidth=3, label='Storm center (white +)'),
        mpatches.Patch(facecolor='none', edgecolor='black', linewidth=2, linestyle='--', 
                      label='500 km radius (dashed circle)'),
        plt.Line2D([0], [0], color='white', linewidth=2.5, linestyle='--', 
                  label='Left-right separation (white dashed line)'),
        mpatches.Patch(facecolor='white', edgecolor='none', label='Area outside 500 km (white)'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=5, fontsize=9, 
              bbox_to_anchor=(0.5, -0.12))
    
    plt.subplots_adjust(wspace=0.15, hspace=0.3, left=0.06, right=0.87, bottom=0.18, top=0.93)
    
    outfile = '/users/jfkarhu/Numlab/hurricane_kirk/plots/geopotential_anomalies_comparison.png'
    plt.savefig(outfile, dpi=150)
    print(f"Saved: {outfile}")
    plt.close()


if __name__ == '__main__':
    plot_geopotential_comparison()
