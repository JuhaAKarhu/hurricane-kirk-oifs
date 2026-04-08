"""
Plot all saved track NetCDF files on one map-style lon/lat figure.

Usage:
    cd /users/jfkarhu/Numlab/hurricane_kirk
    python3 scripts/plot_tracks_comparison.py

Optional arguments:
    --tracks-dir plots/tracks
    --output plots/track_comparison.png
"""

import argparse
import glob
import os
import sys

import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr

sys.path.insert(0, os.path.dirname(__file__))

from run_track import load_kirk_best_track


def label_from_filename(path: str) -> str:
    """Convert track filename into a run label."""
    name = os.path.basename(path)
    # track_baserun.nc -> baserun, track_p3K.nc -> +3K, track_m3K.nc -> -3K
    stem = name.replace("track_", "").replace(".nc", "")
    if stem.startswith("p") and len(stem) > 1 and stem[1].isdigit():
        return f"+{stem[1:]}"
    if stem.startswith("m") and len(stem) > 1 and stem[1].isdigit():
        return f"-{stem[1:]}"
    return stem


def pick_daily_label_indices(times, target_hour=12):
    """Pick one index per day, preferring exact target hour.

    If exact hour is unavailable for a day, choose the nearest available hour
    for that day (tie-breaker: later hour).
    """
    if len(times) == 0:
        return []

    idx_out = []
    # Group by calendar day while preserving order.
    day_keys = pd.to_datetime(times).strftime("%Y-%m-%d")
    unique_days = []
    for d in day_keys:
        if not unique_days or unique_days[-1] != d:
            unique_days.append(d)

    for d in unique_days:
        day_idx = [i for i, key in enumerate(day_keys) if key == d]
        exact = [i for i in day_idx if times[i].hour == target_hour]
        if exact:
            idx_out.append(exact[0])
            continue

        # Fallback to nearest hour if target is not present in this day's data.
        best = sorted(day_idx, key=lambda i: (abs(times[i].hour - target_hour), -times[i].hour))[0]
        idx_out.append(best)

    return idx_out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot all track_*.nc files on one lon/lat figure.")
    parser.add_argument(
        "--tracks-dir",
        default="plots/tracks",
        help="Directory containing track_*.nc files (default: plots/tracks)",
    )
    parser.add_argument(
        "--output",
        default="plots/track_comparison.png",
        help="Output PNG path (default: plots/track_comparison.png)",
    )
    parser.add_argument(
        "--no-best-track",
        action="store_true",
        help="Disable overlay of best-track reference",
    )
    parser.add_argument(
        "--label-hour",
        type=int,
        default=12,
        help="Preferred UTC hour for date labels on model tracks (default: 12)",
    )
    parser.add_argument(
        "--print-labeled-points",
        action="store_true",
        help="Print timestamp/lon/lat of labeled points for verification",
    )
    args = parser.parse_args()

    pattern = os.path.join(args.tracks_dir, "track_*.nc")
    files = sorted(glob.glob(pattern))

    if not files:
        raise FileNotFoundError(f"No track files found with pattern: {pattern}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    plt.figure(figsize=(10, 8))
    all_track_times = []

    for path in files:
        ds = xr.open_dataset(path)
        if "lon" not in ds or "lat" not in ds:
            print(f"Skipping {path}: missing lon/lat")
            continue

        if "time" in ds:
            all_track_times.extend(pd.to_datetime(ds["time"].values))

        label = label_from_filename(path)
        plt.plot(ds["lon"], ds["lat"], marker="o", markersize=2, linewidth=1.5,
                 label=label, alpha=0.7)

        # Mark one labeled point per day, preferring --label-hour UTC.
        if "time" in ds:
            times = pd.to_datetime(ds["time"].values)
            label_idx = pick_daily_label_indices(times, target_hour=args.label_hour)

            if not any(t.hour == args.label_hour for t in times):
                print(
                    f"[{label}] requested {args.label_hour:02d}UTC labels, "
                    f"but available hours are {sorted(set(t.hour for t in times))}; using nearest daily points."
                )

            for i in label_idx:
                t = times[i]
                lon_val = float(ds["lon"].values[i])
                lat_val = float(ds["lat"].values[i])
                plt.scatter(
                    lon_val,
                    lat_val,
                    s=52,
                    marker="o",
                    edgecolors="black",
                    linewidth=0.8,
                    zorder=5,
                )
                date_str = t.strftime("%m-%d")
                plt.annotate(
                    date_str,
                    (lon_val, lat_val),
                    xytext=(3, 3),
                    textcoords="offset points",
                    fontsize=7,
                    alpha=0.85,
                )

                if args.print_labeled_points:
                    print(
                        f"[{label}] label {date_str} at {t.strftime('%Y-%m-%d %H:%M')} "
                        f"-> lon={lon_val:.2f}, lat={lat_val:.2f}"
                    )

    if not args.no_best_track:
        best_track = load_kirk_best_track()
        bt = best_track.copy()
        if all_track_times:
            tmin = min(all_track_times)
            tmax = max(all_track_times)
            bt = bt.sel(time=slice(tmin, tmax))

        bt_times = pd.to_datetime(bt.time.values)
        bt_lon = ((bt.lon.values.astype(float) + 180.0) % 360.0) - 180.0
        bt_lat = bt.lat.values.astype(float)
        plt.plot(
            bt_lon,
            bt_lat,
            linestyle="--",
            linewidth=2.2,
            color="black",
            marker="x",
            markersize=4,
            label="Best track (archive)",
            zorder=10,
        )

        bt_label_idx = pick_daily_label_indices(bt_times, target_hour=args.label_hour)
        for i in bt_label_idx:
            t = bt_times[i]
            plt.scatter(
                bt_lon[i],
                bt_lat[i],
                s=58,
                marker="x",
                color="black",
                linewidths=1.3,
                zorder=11,
            )
            date_str = t.strftime("%m-%d")
            plt.annotate(
                date_str,
                (bt_lon[i], bt_lat[i]),
                xytext=(3, -8),
                textcoords="offset points",
                fontsize=7,
                alpha=0.9,
                color="black",
                fontweight="bold",
            )

            if args.print_labeled_points:
                print(
                    f"[best-track] label {date_str} at {t.strftime('%Y-%m-%d %H:%M')} "
                    f"-> lon={bt_lon[i]:.2f}, lat={bt_lat[i]:.2f}"
                )

    plt.title("Hurricane Kirk OIFS Track Comparison with Timesteps")
    plt.xlabel("Longitude (deg)")
    plt.ylabel("Latitude (deg)")
    plt.grid(True, alpha=0.3)
    plt.legend(title="Run", loc="upper left", fontsize=9)
    plt.tight_layout()
    plt.savefig(args.output, dpi=170, bbox_inches="tight")

    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
