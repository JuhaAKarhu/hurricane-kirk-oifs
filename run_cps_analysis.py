import sys, os
sys.path.insert(0, '../scripts')
sys.path.insert(0, '../ribberink_code')

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from oifs_adapter import RUNS, OIFSRun
import hurricane_functions as hf


def run_name_to_safe(run_name):
    """Encode run names for file paths (+3K -> p3K, -3K -> m3K)."""
    return run_name.replace('+', 'p').replace('-', 'm')

tracks = {}
for run_name in RUNS:
    safe_name = run_name_to_safe(run_name)
    path = f'../plots/tracks/track_{safe_name}.nc'
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
    zg_ds = oifs_run.get_geopotential_height(levels=(300, 600, 900))

    zg_300 = zg_ds.sel(level=300).drop_vars('level')
    zg_600 = zg_ds.sel(level=600).drop_vars('level')
    zg_900 = zg_ds.sel(level=900).drop_vars('level')

    # Ribberink hart() needs variable named after the level for OPER, or
    # we can pass renamed datasets. Here we pass geopotential height datasets
    # The Hart function computes halves based on storm direction and radius.
    # N=2 means 2-timestep (24h at 12h freq) convolution window.
    B_u, VT_u, B_c_u, VT_c_u, halves_u = hf.hart(
        zg_300, zg_600, track_ds, model='OPER', hemisphere='North', N=2
    )
    B_l, VT_l, B_c_l, VT_c_l, halves_l = hf.hart(
        zg_600, zg_900, track_ds, model='OPER', hemisphere='North', N=2
    )

    cps_results[run_name] = {
        'B': B_u, 'B_c': B_c_u,
        'VT_upper': VT_u, 'VT_upper_c': VT_c_u,
        'VT_lower': VT_l, 'VT_lower_c': VT_c_l,
        'times': track_ds.time.values[:-1]  # hart returns n-1 values
    }
    print(f'  B range: {B_u.min():.1f} to {B_u.max():.1f}')
    print(f'  V_T^U range: {VT_u.min():.1f} to {VT_u.max():.1f}')

colors = {'baserun': '#1f77b4', '+3K': '#d62728', '+6K': '#ff7f0e', '-3K': '#2ca02c'}

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for ax_idx, (ax, vt_key, title) in enumerate([
    (axes[0], 'VT_upper_c', 'Upper CPS (300–600 hPa)'),
    (axes[1], 'VT_lower_c', 'Lower CPS (600–900 hPa)'),
]):
    for run_name, res in cps_results.items():
        sc = ax.scatter(res['B_c'], res[vt_key],
                        c=colors.get(run_name, 'k'),
                        label=run_name, s=30, alpha=0.8, zorder=3)
        ax.plot(res['B_c'], res[vt_key],
                color=colors.get(run_name, 'k'), alpha=0.4, lw=1)

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
plt.savefig('../plots/kirk_cps.png', dpi=150)
plt.show()
print('Saved: ../plots/kirk_cps.png')
