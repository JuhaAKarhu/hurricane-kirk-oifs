#!/usr/bin/env python3
"""
Plot three-panel geopotential height difference anomalies (Ribberink Fig 6 style)
for Hurricane Kirk at different storm phases: hurricane, ETT start, and extratropical.

Uses control run (baserun) at:
  - 5 Oct 06 UTC (hurricane stage)
  - 6 Oct 06 UTC (ETT start)
  - 8 Oct 06 UTC (ET stage)

Includes white lines showing storm translation direction.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import xarray as xr
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/users/jfkarhu/Numlab/hurricane_kirk')

from scripts.oifs_adapter import OIFSRun
from scripts.run_track import load_kirk_best_track


def get_storm_velocity(track_ds, timestamp):
    """
    Get storm velocity (forward direction) at a given timestamp.
    Returns (latitude, longitude) of velocity vector.
    """
    # Find closest two timesteps around the given timestamp
    times = track_ds['time'].values
    idx = np.argmin(np.abs(times - np.datetime64(timestamp)))
    
    if idx == 0:
        idx = 1
    if idx >= len(times) - 1:
        idx = len(times) - 2
    
    t1 = times[idx - 1]
    t2 = times[idx + 1]
    lat1 = float(track_ds['lat'].isel(time=idx-1).values)
    lon1 = float(track_ds['lon'].isel(time=idx-1).values)
    lat2 = float(track_ds['lat'].isel(time=idx+1).values)
    lon2 = float(track_ds['lon'].isel(time=idx+1).values)
    
    # Velocity components (normalized)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    norm = np.sqrt(dlat**2 + dlon**2)
    if norm > 0:
        dlat /= norm
        dlon /= norm
    
    return dlat, dlon, lat1, lon1, lat2, lon2


def load_track_and_position(timestamp):
    """Load track and get storm center position at given timestamp."""
    track_file = '/users/jfkarhu/Numlab/hurricane_kirk/plots/tracks/track_baserun.nc'
    track_ds = xr.open_dataset(track_file)
    
    # Find closest timestep
    times = track_ds['time'].values
    idx = np.argmin(np.abs(times - np.datetime64(timestamp)))
    
    lat = float(track_ds['lat'].isel(time=idx).values)
    lon = float(track_ds['lon'].isel(time=idx).values)
    
    return lat, lon, track_ds


def compute_geopotential_anomaly(oifs_run, timestamp, lat_center, lon_center, level_hpa=500, radius_km=600, gridded_z_dir=None):
    """
    Compute geopotential height difference/anomaly in a storm-relative domain.
    Returns gridded data in storm-relative coordinates.
    """
    # Load geopotential at specified level
    z_data = oifs_run.get_geopotential_height(levels=(level_hpa,), gridded_z_dir=gridded_z_dir)
    
    # Select timestep closest to given timestamp
    z_ts = z_data.sel(time=timestamp, method='nearest')['zg']
    
    # Extract lat/lon coordinates
    lat = z_ts['lat'].values
    lon = z_ts['lon'].values
    
    # Get the actual geopotential values at the selected level
    # z_ts has dimensions (level, lat, lon) or just (lat, lon) if we selected a single level
    if 'level' in z_ts.dims:
        z_vals = z_ts.sel(level=level_hpa, method='nearest').values
    else:
        z_vals = z_ts.values
    
    # Convert to radians for distance calculation
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    lat_center_rad = np.radians(lat_center)
    lon_center_rad = np.radians(lon_center)
    
    # Create mesh
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    lon_grid_rad = np.radians(lon_grid)
    lat_grid_rad = np.radians(lat_grid)
    
    # Great-circle distance from storm center
    dlat = lat_grid_rad - lat_center_rad
    dlon = lon_grid_rad - lon_center_rad
    
    # Haversine distance
    a = np.sin(dlat/2)**2 + np.cos(lat_center_rad) * np.cos(lat_grid_rad) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    EARTH_RADIUS_KM = 6371
    distance = EARTH_RADIUS_KM * c
    
    # Mask data outside radius
    mask = distance <= radius_km
    z_masked = z_vals.copy()
    z_masked[~mask] = np.nan
    
    # Compute anomaly: difference from domain mean
    z_mean = np.nanmean(z_masked)
    z_anom = z_vals - z_mean
    z_anom[~mask] = np.nan
    
    return z_anom, lon, lat, distance, mask


def plot_geopotential_comparison():
    """Create three-panel geopotential anomaly figure."""
    
    # Initialize OIFS run handler for baserun
    run_dir = '/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/int_exp_1003'
    gridded_z_dir = '/scratch/project_2001271/jfkarhu/cps_z_gridded/baserun'
    oifs_run = OIFSRun(run_dir=run_dir)
    
    # Timestamps and labels for the three panels
    timestamps = [
        ('2024-10-05 06:00', 'Hurricane Stage'),
        ('2024-10-06 06:00', 'ETT Start'),
        ('2024-10-08 06:00', 'Extratropical Stage'),
    ]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('Geopotential Height Anomalies at 500 hPa (Ribberink Fig 6 Style)', fontsize=14, fontweight='bold')
    
    # Load track for entire run (for velocity calculation)
    _, _, track_ds = load_track_and_position(timestamps[0][0])
    
    for idx, (timestamp_str, label) in enumerate(timestamps):
        ax = axes[idx]
        
        # Get storm position
        lat_center, lon_center, _ = load_track_and_position(timestamp_str)
        
        # Compute anomaly
        z_anom, lon, lat, distance, mask = compute_geopotential_anomaly(
            oifs_run, timestamp_str, lat_center, lon_center, level_hpa=500, radius_km=600, gridded_z_dir=gridded_z_dir
        )
        
        # Plot anomaly field
        vmax = np.nanpercentile(np.abs(z_anom[mask]), 95)
        levels = np.linspace(-vmax, vmax, 21)
        cf = ax.contourf(lon, lat, z_anom, levels=levels, cmap='RdBu_r', extend='both')
        ax.contour(lon, lat, z_anom, levels=levels[::2], colors='k', linewidths=0.5, alpha=0.3)
        
        # Add circle showing analysis domain (600 km)
        from matplotlib.patches import Circle
        circle = Circle((lon_center, lat_center), 600/111, fill=False, edgecolor='grey', linewidth=1.5, linestyle='--', alpha=0.5)
        ax.add_patch(circle)
        
        # Get and plot storm translation direction
        dlat_vel, dlon_vel, lat_prev, lon_prev, lat_next, lon_next = get_storm_velocity(track_ds, timestamp_str)
        arrow_scale = 3.0  # Scale for visibility
        ax.arrow(lon_center, lat_center, dlon_vel * arrow_scale, dlat_vel * arrow_scale,
                head_width=0.4, head_length=0.3, fc='white', ec='white', linewidth=2.5, zorder=100)
        
        # Mark storm center
        ax.plot(lon_center, lat_center, 'w+', markersize=12, markeredgewidth=2.5, zorder=101)
        
        # Labels and formatting
        ax.set_xlabel('Longitude (°E)', fontsize=11)
        ax.set_ylabel('Latitude (°N)', fontsize=11)
        ax.set_title(f'{label}\n{timestamp_str[:10]} {timestamp_str[11:16]} UTC', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.2, linestyle='--')
        ax.set_aspect('equal')
        
        # Colorbar
        cbar = plt.colorbar(cf, ax=ax, orientation='horizontal', pad=0.1, shrink=0.8)
        cbar.set_label('Height anomaly (m)', fontsize=10)
    
    # Add legend for symbol meanings
    legend_elements = [
        mpatches.Patch(facecolor='none', edgecolor='white', linewidth=2.5, label='Storm motion direction'),
        plt.Line2D([0], [0], marker='+', color='w', linestyle='', markersize=12, markeredgewidth=2.5, label='Storm center'),
        mpatches.Patch(facecolor='none', edgecolor='grey', linewidth=1.5, linestyle='--', label='600 km analysis radius'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=3, fontsize=10, bbox_to_anchor=(0.5, -0.05))
    
    plt.tight_layout(rect=[0, 0.08, 1, 0.96])
    
    outfile = '/users/jfkarhu/Numlab/hurricane_kirk/plots/geopotential_anomalies_comparison.png'
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    print(f"Saved: {outfile}")
    plt.close()


if __name__ == '__main__':
    plot_geopotential_comparison()
