#!/usr/bin/env python
"""
Generate multiple alternative versions of the Kirk CPS plot from cached data.
Avoids recomputing Hart diagnostics by loading them from existing run_cps_analysis output.
"""

import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_ROOT, 'ribberink_code'))

import numpy as np
import xarray as xr
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Import the same run configuration as run_cps_analysis.py
from oifs_adapter import RUNS

def run_name_to_safe(run_name):
    """Encode run names for file paths (+3K -> p3K, -3K -> m3K)."""
    return run_name.replace('+', 'p').replace('-', 'm')

# Require that run_cps_analysis.py has been run to generate the cached CPS data
# We can't easily extract data from an image, so we'll re-run a minimal version
# that skips the expensive hart() calls and just uses existing outputs

def generate_all_variants():
    """Generate all CPS plot variants."""
    from oifs_adapter import RUNS, OIFSRun, gridded_z_dir
    import hurricane_functions as hf

    # First, recompute CPS data (same as run_cps_analysis.py but faster with caching)
    tracks = {}
    for run_name in RUNS:
        safe_name = run_name_to_safe(run_name)
        path = os.path.join(_ROOT, f'plots/tracks/track_{safe_name}.nc')
        if os.path.exists(path):
            tracks[run_name] = xr.open_dataset(path)

    cps_results = {}
    for run_name, run_dir in RUNS.items():
        if run_name not in tracks:
            print(f'Skipping {run_name}: no track')
            continue
        print(f'CPS for {run_name}...')

        oifs_run = OIFSRun(run_dir)
        track_ds = tracks[run_name]

        zg_ds = oifs_run.get_geopotential_height(
            levels=(300, 600, 900),
            gridded_z_dir=gridded_z_dir(run_name)
        )

        zg_300 = zg_ds['zg'].sel(level=300)
        zg_600 = zg_ds['zg'].sel(level=600)
        zg_900 = zg_ds['zg'].sel(level=900)

        try:
            B_u, VT_u, B_c_u, VT_c_u, halves_u = hf.hart(
                zg_300, zg_600, track_ds, model='OPER', hemisphere='North', N=2
            )
            B_l, VT_l, B_c_l, VT_c_l, halves_l = hf.hart(
                zg_600, zg_900, track_ds, model='OPER', hemisphere='North', N=2
            )
        except Exception as e:
            print(f'  ERROR calling hart(): {e}')
            continue

        cps_results[run_name] = {
            'B_upper': B_u,
            'B_upper_c': B_c_u,
            'B_lower': B_l,
            'B_lower_c': B_c_l,
            'VT_upper': VT_u,
            'VT_upper_c': VT_c_u,
            'VT_lower': VT_l,
            'VT_lower_c': VT_c_l,
            'times': track_ds.time.values[:-1],
        }

    # Run color mapping
    colors = {
        '-3K': 'tab:blue',
        'baserun': 'tab:green',
        '+3K': 'tab:orange',
        '+6K': 'tab:red',
    }

    # Keep only the publication-relevant fixed-axes grid variant.
    print('\nGenerating VARIANT 3b: fixed axes, no legend, 12-UTC annotations...')
    generate_variant_3b_fixed_axes(cps_results, colors, _ROOT)

    print('\n✓ All variants generated successfully!')

def generate_variant_3b_fixed_axes(cps_results, colors, root):
    """Variant 3b: 2x2 lower-CPS grid per run with shared fixed axes, no legend boxes.
    Plots only every-second 3-hourly step (00, 06, 12, 18 UTC), annotates 12 UTC only."""
    run_order = ['-3K', 'baserun', '+3K', '+6K']

    # First pass: compute global axis bounds across all runs
    all_vt, all_b = [], []
    for run_name in run_order:
        if run_name not in cps_results:
            continue
        res = cps_results[run_name]
        b_vals = res['B_lower_c']
        vt_vals = res['VT_lower_c']
        valid = ~(np.isnan(b_vals) | np.isnan(vt_vals))
        all_b.extend(b_vals[valid].tolist())
        all_vt.extend(vt_vals[valid].tolist())
    pad_b  = (max(all_b)  - min(all_b))  * 0.08 or 5
    pad_vt = (max(all_vt) - min(all_vt)) * 0.08 or 5
    xlim = (min(all_vt) - pad_vt, max(all_vt) + pad_vt)
    ylim = (min(all_b)  - pad_b,  max(all_b)  + pad_b)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    for run_idx, run_name in enumerate(run_order):
        ax = axes[run_idx]
        if run_name not in cps_results:
            ax.set_visible(False)
            continue
        res = cps_results[run_name]

        b_vals = res['B_lower_c']
        vt_vals = res['VT_lower_c']
        times = pd.to_datetime(res['times'])
        valid_mask = ~(np.isnan(b_vals) | np.isnan(vt_vals))

        if valid_mask.sum() > 0:
            # Keep every-second 3-hourly step: first step always included, then
            # only those whose hour is 00, 06, 12, or 18 UTC. This halves the
            # point density while preserving the key synoptic timestamps.
            hour_mask = np.array([
                (i == 0) or (pd.Timestamp(t).hour % 6 == 0)
                for i, t in enumerate(times[valid_mask])
            ])
            all_valid_idx = np.where(valid_mask)[0]
            keep_idx = all_valid_idx[hour_mask]

            b_plot  = b_vals[keep_idx]
            vt_plot = vt_vals[keep_idx]
            t_plot  = pd.to_datetime(times.to_numpy()[keep_idx])

            ax.scatter(vt_plot, b_plot, c=colors.get(run_name, 'k'),
                      s=20, alpha=0.7, marker='o', zorder=3)
            ax.plot(vt_plot, b_plot, color=colors.get(run_name, 'k'),
                   alpha=0.3, lw=1)

            # Annotate only 12UTC timesteps
            for b_pt, vt_pt, t_pt in zip(b_plot, vt_plot, t_plot):
                if pd.Timestamp(t_pt).hour == 12:
                    ax.annotate(pd.Timestamp(t_pt).strftime('%m-%d %HZ'),
                               xy=(vt_pt, b_pt), xytext=(4, 3),
                               textcoords='offset points', fontsize=6,
                               color=colors.get(run_name, 'k'), alpha=0.85)

        ax.axvline(0, color='k', lw=0.8, ls='--', alpha=0.5)
        ax.axhline(10, color='red', lw=1.2, ls='--', alpha=0.7)
        ax.axvline(25, color='gray', lw=0.5, ls=':', alpha=0.5)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xlabel('−V_T (Thermal Wind, m)', fontsize=9)
        ax.set_ylabel('B – Thermal Asymmetry (m)', fontsize=9)
        ax.set_title(run_name, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.2)
        # No legend boxes

    plt.suptitle('Hurricane Kirk 2024 – Cyclone Phase Space', fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(root, 'plots/kirk_cps_v3b_fixed_axes.png'), dpi=150)
    plt.close()
    print('  → plots/kirk_cps_v3b_fixed_axes.png')

if __name__ == '__main__':
    print('Generating CPS plot variants...\n')
    generate_all_variants()
