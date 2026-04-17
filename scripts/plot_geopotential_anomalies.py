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


def compute_geopotential_anomaly(oifs_run, timestamp, lat_center, lon_center, level_hpa=500, domain_half_width=5.0, gridded_z_dir=None):
    """
    Compute geopotential height difference/anomaly in a storm-relative square domain.
    
    Parameters
    ----------
    domain_half_width : float
        Half-width of the square domain in degrees (default 5.0 gives ±5°).
    gridded_z_dir : str
        Directory with pre-converted gridded geopotential files.
    
    Returns
    -------
    tuple: (z_anom, lon_subset, lat_subset, distance_full, lat_full, lon_full, domain_bounds)
    """
    # Load geopotential at specified level
    z_data = oifs_run.get_geopotential_height(levels=(level_hpa,), gridded_z_dir=gridded_z_dir)
    
    # Select timestep closest to given timestamp
    z_ts = z_data.sel(time=timestamp, method='nearest')['zg']
    
    # Extract full lat/lon coordinates
    lat_full = z_ts['lat'].values
    lon_full = z_ts['lon'].values
    
    # Get the actual geopotential values at the selected level
    if 'level' in z_ts.dims:
        z_vals_full = z_ts.sel(level=level_hpa, method='nearest').values
    else:
        z_vals_full = z_ts.values
    
    # Create full mesh for distance calculation
    lon_grid_full, lat_grid_full = np.meshgrid(lon_full, lat_full)
    
    # Calculate great-circle distance from storm center
    lat_center_rad = np.radians(lat_center)
    lon_center_rad = np.radians(lon_center)
    lat_grid_rad = np.radians(lat_grid_full)
    lon_grid_rad = np.radians(lon_grid_full)
    
    dlat = lat_grid_rad - lat_center_rad
    dlon = lon_grid_rad - lon_center_rad
    a = np.sin(dlat/2)**2 + np.cos(lat_center_rad) * np.cos(lat_grid_rad) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    EARTH_RADIUS_KM = 6371
    distance_full = EARTH_RADIUS_KM * c
    
    # Extract data within the square domain (±domain_half_width degrees)
    lat_min = lat_center - domain_half_width
    lat_max = lat_center + domain_half_width
    lon_min = lon_center - domain_half_width
    lon_max = lon_center + domain_half_width
    
    # Subset to domain
    lat_idx = (lat_full >= lat_min) & (lat_full <= lat_max)
    lon_idx = (lon_full >= lon_min) & (lon_full <= lon_max)
    
    lat_subset = lat_full[lat_idx]
    lon_subset = lon_full[lon_idx]
    
    # Subset the geopotential data
    z_subset = z_vals_full[np.ix_(lat_idx, lon_idx)]
    
    # Compute anomaly: difference from domain mean
    z_mean = np.nanmean(z_subset)
    z_anom = z_subset - z_mean
    
    domain_bounds = (lat_min, lat_max, lon_min, lon_max)
    
    return z_anom, lon_subset, lat_subset, distance_full, lat_full, lon_full, domain_bounds


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
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Geopotential Height Anomalies at 500 hPa (±5° domain)', fontsize=14, fontweight='bold')
    
    # Load track for entire run (for velocity calculation)
    _, _, track_ds = load_track_and_position(timestamps[0][0])
    
    for idx, (timestamp_str, label) in enumerate(timestamps):
        ax = axes[idx]
        
        # Get storm position
        lat_center, lon_center, _ = load_track_and_position(timestamp_str)
        
        # Compute anomaly (using ±5° square domain)
        z_anom, lon_subset, lat_subset, distance_full, lat_full, lon_full, domain_bounds = compute_geopotential_anomaly(
            oifs_run, timestamp_str, lat_center, lon_center, level_hpa=500, domain_half_width=5.0, gridded_z_dir=gridded_z_dir
        )
        
        # Create mesh for the subset domain
        lon_mesh, lat_mesh = np.meshgrid(lon_subset, lat_subset)
        
        # Plot anomaly field with contours
        vmax = np.nanpercentile(np.abs(z_anom), 90)
        levels = np.linspace(-vmax, vmax, 21)
        cf = ax.contourf(lon_mesh, lat_mesh, z_anom, levels=levels, cmap='RdBu_r', extend='both')
        ax.contour(lon_mesh, lat_mesh, z_anom, levels=levels[::2], colors='k', linewidths=0.5, alpha=0.3)
        
        # Add circle showing 600 km analysis radius
        from matplotlib.patches import Circle
        # Convert 600 km to approximate degrees (~5.4°)
        radius_deg = 600 / 111.0
        circle = Circle((lon_center, lat_center), radius_deg, fill=False, edgecolor='white', linewidth=2, linestyle='--', alpha=0.7, zorder=50)
        ax.add_patch(circle)
        
        # Get and plot storm translation direction
        dlat_vel, dlon_vel, lat_prev, lon_prev, lat_next, lon_next = get_storm_velocity(track_ds, timestamp_str)
        arrow_scale = 2.5  # Scale for visibility
        ax.arrow(lon_center, lat_center, dlon_vel * arrow_scale, dlat_vel * arrow_scale,
                head_width=0.3, head_length=0.25, fc='white', ec='white', linewidth=2.5, zorder=100)
        
        # Mark storm center
        ax.plot(lon_center, lat_center, 'w+', markersize=14, markeredgewidth=3, zorder=101)
        
        # Set square domain extent (±5°)
        ax.set_xlim(lon_center - 5.0, lon_center + 5.0)
        ax.set_ylim(lat_center - 5.0, lat_center + 5.0)
        ax.set_aspect('equal')
        
        # Labels and formatting with proper axes
        ax.set_xlabel('Longitude (°E)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Latitude (°N)', fontsize=11, fontweight='bold')
        ax.set_title(f'{label}\n{timestamp_str[:10]} {timestamp_str[11:16]} UTC', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
        
        # Add tick labels
        ax.tick_params(labelsize=10)
        
        # Colorbar
        cbar = plt.colorbar(cf, ax=ax, orientation='horizontal', pad=0.12, shrink=0.9)
        cbar.set_label('Height anomaly (m)', fontsize=10)
    
    # Add legend for symbol meanings
    legend_elements = [
        mpatches.Patch(facecolor='none', edgecolor='white', linewidth=2.5, label='Storm motion direction (white arrow)'),
        plt.Line2D([0], [0], marker='+', color='w', linestyle='', markersize=12, markeredgewidth=3, label='Storm center (white +)'),
        mpatches.Patch(facecolor='none', edgecolor='white', linewidth=2, linestyle='--', label='600 km analysis radius (dashed circle)'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=3, fontsize=10, bbox_to_anchor=(0.5, -0.1))
    
    plt.tight_layout(rect=[0, 0.1, 1, 0.96])
    
    outfile = '/users/jfkarhu/Numlab/hurricane_kirk/plots/geopotential_anomalies_comparison.png'
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    print(f"Saved: {outfile}")
    plt.close()


if __name__ == '__main__':
    plot_geopotential_comparison()
