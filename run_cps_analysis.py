import sys, os
# Resolve paths relative to this script's own directory
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'scripts'))
sys.path.insert(0, os.path.join(_HERE, 'ribberink_code'))

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from oifs_adapter import RUNS, OIFSRun, gridded_z_dir
import hurricane_functions as hf


def run_name_to_safe(run_name):
    """Encode run names for file paths (+3K -> p3K, -3K -> m3K)."""
    return run_name.replace('+', 'p').replace('-', 'm')

tracks = {}
for run_name in RUNS:
    safe_name = run_name_to_safe(run_name)
    path = os.path.join(_HERE, f'plots/tracks/track_{safe_name}.nc')
    if os.path.exists(path):
        tracks[run_name] = xr.open_dataset(path)
        print(f'Loaded track: {run_name} ({len(tracks[run_name].time)} timesteps)')
    else:
        print(f'⚠️  Track not found for {run_name}: run 02_track_analysis.ipynb first')

cps_results = {}

for run_name, run_dir in RUNS.items():
    if run_name not in tracks:
        print(f'Skipping {run_name}: no track')
        continue
    print(f'\nCPS for {run_name}...')

    oifs_run = OIFSRun(run_dir)
    track_ds = tracks[run_name]

    # Load geopotential height at 300, 600, 900 hPa (z/g, in metres)
    # Uses pre-converted gridded GRIB files (see scripts/convert_spectral_to_grid.sh)
    zg_ds = oifs_run.get_geopotential_height(
        levels=(300, 600, 900),
        gridded_z_dir=gridded_z_dir(run_name)
    )

    # hart() arithmetic (B/VT stored in numpy float arrays) requires DataArrays,
    # not Datasets. Extract the 'zg' DataArray per level, keeping the scalar
    # 'level' coordinate so that hart()'s OPER branch can read press_u/l.
    zg_300 = zg_ds['zg'].sel(level=300)
    zg_600 = zg_ds['zg'].sel(level=600)
    zg_900 = zg_ds['zg'].sel(level=900)

    # N=2 means 2-timestep convolution window.
    try:
        B_u, VT_u, B_c_u, VT_c_u, halves_u = hf.hart(
            zg_300, zg_600, track_ds, model='OPER', hemisphere='North', N=2
        )
        B_l, VT_l, B_c_l, VT_c_l, halves_l = hf.hart(
            zg_600, zg_900, track_ds, model='OPER', hemisphere='North', N=2
        )
    except Exception as e:
        print(f'  ERROR calling hart(): {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        print(f'  Skipping {run_name}')
        continue

    cps_results[run_name] = {
        'B': B_u, 'B_c': B_c_u,
        'VT_upper': VT_u, 'VT_upper_c': VT_c_u,
        'VT_lower': VT_l, 'VT_lower_c': VT_c_l,
        'times': track_ds.time.values[:-1]  # hart returns n-1 values
    }
    print(f'  B_u range: [{np.nanmin(B_u):.1f}, {np.nanmax(B_u):.1f}], NaN count: {np.isnan(B_u).sum()}/{len(B_u)}')
    print(f'  VT_u range: [{np.nanmin(VT_u):.1f}, {np.nanmax(VT_u):.1f}], NaN count: {np.isnan(VT_u).sum()}/{len(VT_u)}')

colors = {'baserun': '#1f77b4', '+3K': '#d62728', '+6K': '#ff7f0e', '-3K': '#2ca02c'}

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for ax_idx, (ax, vt_key, title) in enumerate([
    (axes[0], 'VT_upper_c', 'Upper CPS (300–600 hPa)'),
    (axes[1], 'VT_lower_c', 'Lower CPS (600–900 hPa)'),
]):
    plot_count = 0
    for run_name, res in cps_results.items():
        b_vals = res['B_c']
        vt_vals = res[vt_key]
        # Only plot non-NaN points
        valid_mask = ~(np.isnan(b_vals) | np.isnan(vt_vals))
        if valid_mask.sum() > 0:
            sc = ax.scatter(b_vals[valid_mask], vt_vals[valid_mask],
                            c=colors.get(run_name, 'k'),
                            label=run_name, s=30, alpha=0.8, zorder=3)
            ax.plot(b_vals[valid_mask], vt_vals[valid_mask],
                    color=colors.get(run_name, 'k'), alpha=0.4, lw=1)
            plot_count += valid_mask.sum()
        else:
            print(f'WARNING: No valid CPS points for {run_name} on {vt_key}')

    print(f'\nPlotted {plot_count} total points on {title}')

    ax.axhline(0, color='k', lw=0.8, ls='--')
    ax.axvline(0, color='k', lw=0.8, ls='--')
    ax.axhline(25, color='gray', lw=0.5, ls=':')
    ax.set_xlabel('B – Thermal Asymmetry (m)')
    ax.set_ylabel('−V_T (Thermal Wind, m)')
    ax.set_title(title)
    if ax_idx == 0:
        ax.legend()
    ax.grid(True, alpha=0.3)

    # Annotate quadrants
    ax.text(0.02, 0.98, 'Warm-core\n(tropical)', transform=ax.transAxes,
            ha='left', va='top', fontsize=8, color='red')
    ax.text(0.98, 0.98, 'Cold-core\n(extratropical)', transform=ax.transAxes,
            ha='right', va='top', fontsize=8, color='blue')

plt.suptitle('Hurricane Kirk 2024 – Cyclone Phase Space', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(_HERE, 'plots/kirk_cps.png'), dpi=150)
plt.show()
print('Saved: plots/kirk_cps.png')
