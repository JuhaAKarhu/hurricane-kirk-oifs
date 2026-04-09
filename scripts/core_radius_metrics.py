"""
core_radius_metrics.py
======================
Compute direction-aware and mean wind-radius metrics for Hurricane Kirk OIFS runs.

Outputs one CSV per run in plots/tracks/:
  core_radius_<run>.csv

Each row is one timestamp and includes, for each threshold (default 17/34/50 m s-1):
  - forward radius (km): along storm-motion direction
  - backward radius (km): opposite storm-motion direction
  - left radius (km): 90 deg left of storm-motion direction
  - right radius (km): 90 deg right of storm-motion direction
  - mean radius (km): mean radial distance of all above-threshold points
  - mean quadrant radius (km): mean of available directional radii

A summary CSV with run-level means is also written to:
  plots/tracks/core_radius_summary.csv
"""

from __future__ import annotations

import argparse
import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import xarray as xr

from oifs_adapter import OIFSRun, RUNS


def run_name_to_safe(run_name: str) -> str:
    return run_name.replace("+", "p").replace("-", "m")


def _angular_lon_distance_deg(lon_vals: np.ndarray, lon0: float) -> np.ndarray:
    """Shortest signed longitude difference in degrees."""
    return ((lon_vals - lon0 + 180.0) % 360.0) - 180.0


def _offset_km(lat_grid: np.ndarray, lon_grid: np.ndarray, lat0: float, lon0: float) -> Tuple[np.ndarray, np.ndarray]:
    """Return eastward and northward offsets in km from (lat0, lon0)."""
    dlat = lat_grid - lat0
    dlon = _angular_lon_distance_deg(lon_grid, lon0)

    # Spherical approximations are adequate for storm-scale diagnostics.
    north_km = dlat * 110.574
    east_km = dlon * (111.320 * np.cos(np.deg2rad(lat0)))
    return east_km, north_km


def _track_unit_vectors(track_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Compute unit motion vectors (east, north) for each track timestamp."""
    lats = track_df["lat"].to_numpy(dtype=float)
    lons = track_df["lon"].to_numpy(dtype=float)
    n = len(track_df)

    ux = np.zeros(n, dtype=float)
    uy = np.zeros(n, dtype=float)

    for i in range(n):
        if n == 1:
            dx_km, dy_km = 1.0, 0.0
        elif i < n - 1:
            dlon = _angular_lon_distance_deg(np.array([lons[i + 1]]), lons[i])[0]
            dlat = lats[i + 1] - lats[i]
            dy_km = dlat * 110.574
            dx_km = dlon * (111.320 * np.cos(np.deg2rad(lats[i])))
        else:
            dlon = _angular_lon_distance_deg(np.array([lons[i]]), lons[i - 1])[0]
            dlat = lats[i] - lats[i - 1]
            dy_km = dlat * 110.574
            dx_km = dlon * (111.320 * np.cos(np.deg2rad(lats[i])))

        norm = float(np.hypot(dx_km, dy_km))
        if norm < 1e-6:
            ux[i], uy[i] = 1.0, 0.0
        else:
            ux[i], uy[i] = dx_km / norm, dy_km / norm

    return ux, uy


def _directional_radii(
    ws2d: xr.DataArray,
    lat0: float,
    lon0: float,
    ux: float,
    uy: float,
    threshold_ms: float,
    max_radius_km: float,
) -> Dict[str, float]:
    """Compute directional and mean radii for one timestep and one threshold."""
    lat_vals = ws2d["lat"].to_numpy()
    lon_vals = ws2d["lon"].to_numpy()
    ws_vals = ws2d.to_numpy()

    # Support both regular (lat, lon) grids and reduced/point grids.
    if ws_vals.ndim == 1 and lat_vals.ndim == 1 and lon_vals.ndim == 1 and lat_vals.shape[0] == lon_vals.shape[0]:
        east_km, north_km = _offset_km(lat_vals, lon_vals, lat0, lon0)
    else:
        lon_grid, lat_grid = np.meshgrid(lon_vals, lat_vals)
        east_km, north_km = _offset_km(lat_grid, lon_grid, lat0, lon0)
    radial_km = np.hypot(east_km, north_km)

    in_radius = radial_km <= max_radius_km
    strong_wind = ws_vals >= threshold_ms
    mask = in_radius & strong_wind

    if not np.any(mask):
        return {
            "forward_km": np.nan,
            "backward_km": np.nan,
            "left_km": np.nan,
            "right_km": np.nan,
            "mean_km": np.nan,
            "mean_quadrant_km": np.nan,
        }

    # Along-track axis: +forward, -backward.
    along = east_km * ux + north_km * uy
    # Cross-track axis: +left, -right.
    left_axis = east_km * (-uy) + north_km * ux

    forward = np.nan
    backward = np.nan
    left = np.nan
    right = np.nan

    m_forward = mask & (along >= 0.0)
    if np.any(m_forward):
        forward = float(np.max(along[m_forward]))

    m_backward = mask & (along <= 0.0)
    if np.any(m_backward):
        backward = float(np.max(-along[m_backward]))

    m_left = mask & (left_axis >= 0.0)
    if np.any(m_left):
        left = float(np.max(left_axis[m_left]))

    m_right = mask & (left_axis <= 0.0)
    if np.any(m_right):
        right = float(np.max(-left_axis[m_right]))

    mean_all = float(np.mean(radial_km[mask]))
    directional = np.array([forward, backward, left, right], dtype=float)
    mean_quad = float(np.nanmean(directional)) if np.any(~np.isnan(directional)) else np.nan

    return {
        "forward_km": forward,
        "backward_km": backward,
        "left_km": left,
        "right_km": right,
        "mean_km": mean_all,
        "mean_quadrant_km": mean_quad,
    }


def load_track(track_path: str) -> pd.DataFrame:
    ds = xr.open_dataset(track_path)
    df = ds[["lat", "lon"]].to_dataframe().reset_index()
    df["time"] = pd.to_datetime(df["time"])
    return df[["time", "lat", "lon"]]


def compute_run_metrics(
    run_name: str,
    run_dir: str,
    tracks_dir: str,
    thresholds: List[float],
    max_radius_km: float,
) -> pd.DataFrame:
    safe = run_name_to_safe(run_name)
    track_path = os.path.join(tracks_dir, f"track_{safe}.nc")
    if not os.path.exists(track_path):
        raise FileNotFoundError(f"Track file missing: {track_path}")

    track_df = load_track(track_path)
    ux, uy = _track_unit_vectors(track_df)

    oifs_run = OIFSRun(run_dir)
    wind_ds = oifs_run.get_10m_wind()
    ws = np.hypot(wind_ds["u10m"], wind_ds["v10m"]).rename("ws10m")

    ws_times = pd.to_datetime(ws["time"].to_numpy())
    time_to_idx = {pd.Timestamp(t): i for i, t in enumerate(ws_times)}

    rows: List[Dict[str, float]] = []
    for i, row in track_df.iterrows():
        t = pd.Timestamp(row["time"])
        if t not in time_to_idx:
            continue

        ws2d = ws.isel(time=time_to_idx[t])
        lat0 = float(row["lat"])
        lon0 = float(row["lon"])

        out: Dict[str, float] = {
            "time": t,
            "lat": lat0,
            "lon": lon0,
            "ux": float(ux[i]),
            "uy": float(uy[i]),
        }

        for thr in thresholds:
            r = _directional_radii(
                ws2d=ws2d,
                lat0=lat0,
                lon0=lon0,
                ux=float(ux[i]),
                uy=float(uy[i]),
                threshold_ms=float(thr),
                max_radius_km=max_radius_km,
            )
            key = f"r{int(thr)}"
            out[f"{key}_forward_km"] = r["forward_km"]
            out[f"{key}_backward_km"] = r["backward_km"]
            out[f"{key}_left_km"] = r["left_km"]
            out[f"{key}_right_km"] = r["right_km"]
            out[f"{key}_mean_km"] = r["mean_km"]
            out[f"{key}_mean_quadrant_km"] = r["mean_quadrant_km"]

        rows.append(out)

    if not rows:
        raise RuntimeError(f"No overlapping wind/track times for run {run_name}")

    return pd.DataFrame(rows)


def build_summary(df: pd.DataFrame, run_name: str, thresholds: List[float]) -> pd.DataFrame:
    recs = []
    for thr in thresholds:
        key = f"r{int(thr)}"
        recs.append(
            {
                "run": run_name,
                "threshold_ms": float(thr),
                "n_times": int(len(df)),
                "forward_mean_km": float(df[f"{key}_forward_km"].mean(skipna=True)),
                "backward_mean_km": float(df[f"{key}_backward_km"].mean(skipna=True)),
                "left_mean_km": float(df[f"{key}_left_km"].mean(skipna=True)),
                "right_mean_km": float(df[f"{key}_right_km"].mean(skipna=True)),
                "radius_mean_km": float(df[f"{key}_mean_km"].mean(skipna=True)),
                "radius_mean_quadrant_km": float(df[f"{key}_mean_quadrant_km"].mean(skipna=True)),
            }
        )
    return pd.DataFrame.from_records(recs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute directional and mean core-radius metrics from OIFS 10m winds."
    )
    parser.add_argument(
        "--tracks-dir",
        default="plots/tracks",
        help="Directory containing track_<run>.nc files (default: plots/tracks)",
    )
    parser.add_argument(
        "--out-dir",
        default="plots/tracks",
        help="Output directory for core-radius CSV files (default: plots/tracks)",
    )
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=[17.0, 34.0, 50.0],
        help="Wind thresholds in m/s for radius metrics (default: 17 34 50)",
    )
    parser.add_argument(
        "--max-radius-km",
        type=float,
        default=800.0,
        help="Maximum search radius around track center in km (default: 800)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    summary_frames = []
    for run_name, run_dir in RUNS.items():
        if not os.path.isdir(run_dir):
            print(f"Skipping {run_name}: run directory not found ({run_dir})")
            continue

        print(f"Computing core radius metrics: {run_name}")
        df = compute_run_metrics(
            run_name=run_name,
            run_dir=run_dir,
            tracks_dir=args.tracks_dir,
            thresholds=args.thresholds,
            max_radius_km=args.max_radius_km,
        )

        safe = run_name_to_safe(run_name)
        out_path = os.path.join(args.out_dir, f"core_radius_{safe}.csv")
        df.to_csv(out_path, index=False)
        print(f"  Saved {out_path} ({len(df)} rows)")

        summary_frames.append(build_summary(df, run_name, args.thresholds))

    if summary_frames:
        summary = pd.concat(summary_frames, ignore_index=True)
        summary_path = os.path.join(args.out_dir, "core_radius_summary.csv")
        summary.to_csv(summary_path, index=False)
        print(f"Saved {summary_path} ({len(summary)} rows)")


if __name__ == "__main__":
    main()
