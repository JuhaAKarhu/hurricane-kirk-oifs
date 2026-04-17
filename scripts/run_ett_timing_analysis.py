import os
import sys
import numpy as np
import pandas as pd
import xarray as xr

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Resolve paths relative to this script's directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_ROOT, 'ribberink_code'))

from oifs_adapter import RUNS, OIFSRun, gridded_z_dir
import hurricane_functions as hf


def run_name_to_safe(run_name):
    """Encode run names for file paths (+3K -> p3K, -3K -> m3K)."""
    return run_name.replace('+', 'p').replace('-', 'm')


def load_track_for_run(run_name):
    safe_name = run_name_to_safe(run_name)
    path = os.path.join(_ROOT, f'plots/tracks/track_{safe_name}.nc')
    if not os.path.exists(path):
        return None
    return xr.open_dataset(path)


def first_crossing_time(times, values, threshold=10.0):
    """Return first timestamp where values > threshold (Ribberink criterion)."""
    vals = np.asarray(values, dtype=float)
    idx = np.where(np.isfinite(vals) & (vals > threshold))[0]
    if idx.size == 0:
        return pd.NaT
    return pd.Timestamp(times[int(idx[0])])


def compute_lower_b_timeseries(track_ds, run_dir, run_name, smooth_n=2):
    """Compute lower-layer CPS asymmetry B (600-900 hPa) for one run."""
    oifs_run = OIFSRun(run_dir)
    zg_ds = oifs_run.get_geopotential_height(
        levels=(600, 900),
        gridded_z_dir=gridded_z_dir(run_name),
    )

    zg_600 = zg_ds['zg'].sel(level=600)
    zg_900 = zg_ds['zg'].sel(level=900)

    # hart() returns arrays with length n_time - 1.
    B_raw, _, B_smooth, _, _ = hf.hart(
        zg_600,
        zg_900,
        track_ds,
        model='OPER',
        hemisphere='North',
        N=smooth_n,
    )

    times = pd.to_datetime(track_ds.time.values[:-1])
    return times, np.asarray(B_raw, dtype=float), np.asarray(B_smooth, dtype=float)


def main():
    threshold = 10.0
    smooth_n = 2

    colors = {
        '-3K': 'tab:blue',
        'baserun': 'tab:green',
        '+3K': 'tab:orange',
        '+6K': 'tab:red',
    }

    run_data = {}
    summary_rows = []

    for run_name, run_dir in RUNS.items():
        track_ds = load_track_for_run(run_name)
        if track_ds is None:
            print(f'Skipping {run_name}: track file not found in plots/tracks')
            continue

        print(f'Computing ETT timing for {run_name}...')
        try:
            times, b_raw, b_smooth = compute_lower_b_timeseries(
                track_ds=track_ds,
                run_dir=run_dir,
                run_name=run_name,
                smooth_n=smooth_n,
            )
        except Exception as exc:
            print(f'  ERROR for {run_name}: {type(exc).__name__}: {exc}')
            continue

        et_start = first_crossing_time(times, b_smooth, threshold=threshold)

        run_data[run_name] = {
            'times': times,
            'b_raw': b_raw,
            'b_smooth': b_smooth,
            'et_start': et_start,
        }

        summary_rows.append({
            'run': run_name,
            'et_start_time_utc': et_start.isoformat() if pd.notna(et_start) else '',
            'crossing_threshold_m': threshold,
            'smooth_window_n': smooth_n,
        })

        if pd.notna(et_start):
            print(f'  ET start ({run_name}): {et_start} (first B > {threshold:.0f})')
        else:
            print(f'  ET start ({run_name}): not reached (B never exceeded {threshold:.0f})')

    if not run_data:
        raise RuntimeError('No runs were processed successfully. Ensure tracks and gridded z files are available.')

    # Save ET-start summary table.
    summary_df = pd.DataFrame(summary_rows)
    summary_csv = os.path.join(_ROOT, 'plots/tracks/ett_start_summary.csv')
    summary_df.to_csv(summary_csv, index=False)
    print(f'Saved: {summary_csv}')

    # Save per-run B time series for traceability.
    for run_name, data in run_data.items():
        safe = run_name_to_safe(run_name)
        df = pd.DataFrame({
            'time': data['times'],
            'B_raw': data['b_raw'],
            'B_smooth': data['b_smooth'],
        })
        out_csv = os.path.join(_ROOT, f'plots/tracks/ett_B_timeseries_{safe}.csv')
        df.to_csv(out_csv, index=False)

    # Build Fig.-5-style two-panel timing figure.
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)

    all_valid_starts = [d['et_start'] for d in run_data.values() if pd.notna(d['et_start'])]
    if all_valid_starts:
        zoom_start = min(all_valid_starts) - pd.Timedelta(hours=12)
        zoom_end = max(all_valid_starts) + pd.Timedelta(hours=12)
    else:
        # Fallback to central half of available timeline.
        all_times = np.concatenate([d['times'].to_numpy() for d in run_data.values()])
        all_times = pd.to_datetime(all_times)
        tmin, tmax = all_times.min(), all_times.max()
        span = (tmax - tmin) / 4
        center = tmin + (tmax - tmin) / 2
        zoom_start = center - span
        zoom_end = center + span

    for ax_idx, ax in enumerate(axes):
        for run_name, data in run_data.items():
            c = colors.get(run_name, None)
            ax.plot(
                data['times'],
                data['b_smooth'],
                color=c,
                lw=2,
                label=run_name,
                alpha=0.95,
            )

            # Mark first threshold crossing for timing emphasis.
            if pd.notna(data['et_start']):
                i0 = int(np.where(pd.to_datetime(data['times']) == data['et_start'])[0][0])
                ax.scatter(
                    data['times'][i0],
                    data['b_smooth'][i0],
                    color=c,
                    s=35,
                    zorder=5,
                )
                ax.axvline(data['times'][i0], color=c, lw=1, ls=':')

        ax.axhline(threshold, color='k', lw=1.0)
        ax.grid(axis='x', alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d %HZ'))
        ax.tick_params(axis='x', rotation=45)
        ax.set_ylabel('B (m)')

        if ax_idx == 0:
            ax.set_title('(a) 600-900 hPa asymmetry (full period)')
            ax.legend(loc='best')
        else:
            ax.set_title('(b) ETT-start timing window')
            ax.set_xlim([zoom_start, zoom_end])

    fig.suptitle('Hurricane Kirk 2024: ETT Start Timing Across Simulations', fontsize=13)
    fig.tight_layout()

    fig_path = os.path.join(_ROOT, 'plots/ett_start_timing.png')
    fig.savefig(fig_path, dpi=160)
    print(f'Saved: {fig_path}')

    # Generate additional full-period plot (no zoom).
    fig_full, ax = plt.subplots(1, 1, figsize=(10, 5))

    for run_name, data in run_data.items():
        c = colors.get(run_name, None)
        ax.plot(
            data['times'],
            data['b_smooth'],
            color=c,
            lw=2,
            label=run_name,
            alpha=0.95,
        )

        # Mark first threshold crossing for timing emphasis.
        if pd.notna(data['et_start']):
            i0 = int(np.where(pd.to_datetime(data['times']) == data['et_start'])[0][0])
            ax.scatter(
                data['times'][i0],
                data['b_smooth'][i0],
                color=c,
                s=35,
                zorder=5,
            )
            ax.axvline(data['times'][i0], color=c, lw=1, ls=':')

    ax.axhline(threshold, color='k', lw=1.0)
    ax.grid(axis='x', alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d %HZ'))
    ax.tick_params(axis='x', rotation=45)
    ax.set_ylabel('B (m)')
    ax.set_title('600-900 hPa asymmetry (full simulation period)', fontsize=12)
    ax.legend(loc='upper left')

    fig_full.suptitle('Hurricane Kirk 2024: ETT Start Timing Across Simulations', fontsize=13)
    fig_full.tight_layout()

    fig_path_full = os.path.join(_ROOT, 'plots/ett_start_timing_fullperiod.png')
    fig_full.savefig(fig_path_full, dpi=160)
    print(f'Saved: {fig_path_full}')


if __name__ == '__main__':
    main()
