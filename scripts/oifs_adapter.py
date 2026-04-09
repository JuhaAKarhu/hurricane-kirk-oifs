"""
oifs_adapter.py
===============
Reads OpenIFS GRIB output files and returns xarray Datasets in a format
compatible with Ribberink et al. (2025) hurricane analysis functions.

OIFS file types (per timestep, e.g. +000012 = 12 model steps):
  ICMGGac3u+XXXXXX  – surface fields: msl, 10u, 10v, tp, sst
  ICMSHac3u+XXXXXX  – pressure-level fields: u, v, t, z, r, w, vo
  ICMUAac3u+XXXXXX  – pressure-level fields: q, pv

The adapter wraps cfgrib to decode these GRIB files and renames/converts
variables to match the expectations of hurricane_functions.py:
  - model='OPER' → expects data.msl (MSLP in Pa)
  - geopotential z (m² s⁻²) → height zg = z / g (m)  for CPS analysis
  - 10u/10v → u10m/v10m  for wind radius

Usage example:
    from oifs_adapter import OIFSRun
    run = OIFSRun('/scratch/.../int_exp_1003', init_time='2024100306')
    msl_ds = run.get_msl()           # for storm tracking
    z_ds   = run.get_geopotential()  # for CPS analysis
    wind_ds= run.get_10m_wind()      # for wind radius
"""

import os
import glob
import xarray as xr
import numpy as np
import pandas as pd
import cfgrib

# Standard gravity (m s⁻²)
G = 9.80665

# OIFS forecast start time for Kirk runs
INIT_DATETIME = pd.Timestamp('2024-10-03 06:00:00')


def _step_to_timedelta(step_str):
    """Convert '+XXXXXX' model-step string to timedelta.

    For these Kirk runs, one model step is 15 minutes, so +000012 = 3 hours.
    """
    nsteps = int(step_str.lstrip('+'))
    return pd.Timedelta(minutes=15 * nsteps)


def _list_grib_files(run_dir, prefix):
    """Return sorted list of GRIB files matching prefix+XXXXXX."""
    pattern = os.path.join(run_dir, f'{prefix}+??????')
    files = sorted(glob.glob(pattern))
    return files


def _add_time_coord(ds, step_str):
    """Assign a 'time' coordinate from the OIFS step string."""
    valid_time = INIT_DATETIME + _step_to_timedelta(step_str)
    ds = ds.expand_dims('time')
    ds = ds.assign_coords(time=('time', [valid_time]))
    return ds


def _read_surface_field(filepath, shortname):
    """Read a single surface variable from an ICMGG GRIB file."""
    ds_list = cfgrib.open_datasets(filepath, backend_kwargs={'indexpath': ''})
    for ds in ds_list:
        if shortname in ds:
            out = ds[[shortname]]
            rename_map = {}
            if 'latitude' in out.dims or 'latitude' in out.coords:
                rename_map['latitude'] = 'lat'
            if 'longitude' in out.dims or 'longitude' in out.coords:
                rename_map['longitude'] = 'lon'
            if rename_map:
                out = out.rename(rename_map)
            return out
    raise KeyError(f"'{shortname}' not found in {filepath}")


def _read_surface_field_any(filepath, shortnames):
    """Read the first available shortName from a list in an ICMGG file."""
    last_err = None
    for name in shortnames:
        try:
            return _read_surface_field(filepath, name), name
        except KeyError as e:
            last_err = e
            continue
    raise last_err if last_err is not None else KeyError(f"No shortName found in {filepath}")


def _read_pressure_field(filepath, shortname, levels=None):
    """Read pressure-level variable from an ICMSH or ICMUA GRIB file."""
    ds_list = cfgrib.open_datasets(filepath, backend_kwargs={'indexpath': ''})
    for ds in ds_list:
        if shortname in ds:
            out = ds[[shortname]]
            rename_map = {}
            if 'latitude' in out.dims or 'latitude' in out.coords:
                rename_map['latitude'] = 'lat'
            if 'longitude' in out.dims or 'longitude' in out.coords:
                rename_map['longitude'] = 'lon'
            if rename_map:
                out = out.rename(rename_map)

            # Pressure-level data must carry a vertical coordinate.
            # Some cfgrib groups can expose the same shortName on a flattened
            # "values" dimension; skip those when levels are requested.
            if levels is not None and ('isobaricInhPa' not in out.dims and 'level' not in out.dims):
                continue

            if 'isobaricInhPa' in out.dims:
                out = out.rename({'isobaricInhPa': 'level'})
            if levels is not None:
                out = out.sel(level=list(levels), method='nearest')
            return out
    raise KeyError(f"'{shortname}' not found in {filepath}")


class OIFSRun:
    """
    Represents a single OIFS forecast run directory.

    Parameters
    ----------
    run_dir : str
        Path to the OIFS run output directory (contains ICMGGac3u+XXXXXX files).
    gg_prefix : str
        Prefix for Gaussian-grid surface files. Default 'ICMGGac3u'.
    sh_prefix : str
        Prefix for spectral/pressure-level files. Default 'ICMSHac3u'.
    """

    def __init__(self, run_dir, gg_prefix='ICMGGac3u', sh_prefix='ICMSHac3u'):
        self.run_dir = run_dir
        self.gg_prefix = gg_prefix
        self.sh_prefix = sh_prefix

        self._gg_files = _list_grib_files(run_dir, gg_prefix)
        self._sh_files = _list_grib_files(run_dir, sh_prefix)

        if not self._gg_files:
            raise FileNotFoundError(
                f"No {gg_prefix}+XXXXXX files found in {run_dir}")

        self.steps = [os.path.basename(f).split('+')[1] for f in self._gg_files]
        self.valid_times = [
            INIT_DATETIME + _step_to_timedelta(s) for s in self.steps
        ]

        print(f"OIFSRun: {run_dir}")
        print(f"  GG files  : {len(self._gg_files)} timesteps")
        print(f"  SH files  : {len(self._sh_files)} timesteps")
        print(f"  First step: {self.steps[0]} h → {self.valid_times[0]}")
        print(f"  Last  step: {self.steps[-1]} h → {self.valid_times[-1]}")

    # ------------------------------------------------------------------
    # MSLP — for storm tracking
    # ------------------------------------------------------------------
    def get_msl(self):
        """
        Return mean sea-level pressure as an xarray Dataset with variable 'msl'
        and dimensions (time, lat, lon). Compatible with model='OPER' in
        Ribberink's cyclone_tracker / storm_tracker functions.

        Returns
        -------
        xr.Dataset with data variable 'msl' [Pa]
        """
        chunks = []
        for filepath, step in zip(self._gg_files, self.steps):
            ds = _read_surface_field(filepath, 'msl')
            ds = _add_time_coord(ds, step)
            chunks.append(ds)
        msl_ds = xr.concat(chunks, dim='time')
        return msl_ds

    # ------------------------------------------------------------------
    # 10 m winds — for wind radius analysis
    # ------------------------------------------------------------------
    def get_10m_wind(self):
        """
        Return 10 m U and V wind components as an xarray Dataset with variables
        'u10m' and 'v10m' and dimensions (time, lat, lon).

        Returns
        -------
        xr.Dataset with data variables 'u10m' and 'v10m' [m s⁻¹]
        """
        chunks = []
        for filepath, step in zip(self._gg_files, self.steps):
            # Some OIFS outputs expose 10m winds as 10u/10v, others as u10/v10.
            u, u_name = _read_surface_field_any(filepath, ['10u', 'u10'])
            v, v_name = _read_surface_field_any(filepath, ['10v', 'v10'])
            u = u.rename({u_name: 'u10m'})
            v = v.rename({v_name: 'v10m'})
            ds = xr.merge([u, v])
            ds = _add_time_coord(ds, step)
            chunks.append(ds)
        wind_ds = xr.concat(chunks, dim='time')
        return wind_ds

    # ------------------------------------------------------------------
    # Geopotential height — for Cyclone Phase Space (Hart) analysis
    # ------------------------------------------------------------------
    def get_geopotential_height(self, levels=(300, 600, 900), gridded_z_dir=None):
        """
        Return geopotential height (Z = Φ/g) at requested pressure levels.
        OIFS outputs geopotential Φ (m² s⁻²); division by G converts to
        geopotential height in metres.

        The ICMSHac3u GRIB files use spectral encoding and lack lat/lon
        coordinates.  Pre-convert them to a regular Gaussian grid with:

            bash scripts/convert_spectral_to_grid.sh

        then pass the output directory as `gridded_z_dir`.

        Parameters
        ----------
        levels : tuple of int
            Pressure levels in hPa. Default (300, 600, 900) for CPS analysis.
        gridded_z_dir : str or None
            Directory containing pre-converted gridded z files named
            ``z+XXXXXX_ll.grib`` (produced by convert_spectral_to_grid.sh).
            If None, falls back to reading the raw spectral ICMSHac3u files
            (which will raise RuntimeError for spectral-only data).

        Returns
        -------
        xr.Dataset with variable 'zg' [m] and dimensions (time, level, lat, lon)
        """
        if gridded_z_dir is not None:
            return self._get_geopotential_gridded(levels, gridded_z_dir)

        # --- fallback: attempt to read spectral ICMSHac3u directly ---
        chunks = []
        for filepath, step in zip(self._sh_files, self.steps):
            ds = _read_pressure_field(filepath, 'z', levels=levels)

            has_lat = 'latitude' in ds.coords or 'lat' in ds.coords
            has_lon = 'longitude' in ds.coords or 'lon' in ds.coords
            has_vals = 'values' in ds.dims and 'lat' not in ds.dims

            if not (has_lat and has_lon):
                if has_vals:
                    raise RuntimeError(
                        f"Geopotential data from {filepath} are in spectral format "
                        "(no lat/lon coordinates). Run:\n"
                        "    bash scripts/convert_spectral_to_grid.sh\n"
                        "then pass gridded_z_dir=<output_dir> to get_geopotential_height()."
                    )
                raise RuntimeError(
                    f"Geopotential data from {filepath} lack lat/lon coordinates. "
                    f"coords: {list(ds.coords)}, dims: {dict(ds.dims)}"
                )

            ds = ds.rename({'z': 'zg'})
            ds['zg'] = ds['zg'] / G
            ds = _add_time_coord(ds, step)
            if 'latitude' in ds.coords or 'latitude' in ds.dims:
                ds = ds.rename({'latitude': 'lat'})
            if 'longitude' in ds.coords or 'longitude' in ds.dims:
                ds = ds.rename({'longitude': 'lon'})
            chunks.append(ds)
        z_ds = xr.concat(chunks, dim='time')
        return z_ds

    def _get_geopotential_gridded(self, levels, gridded_z_dir):
        """Read pre-converted gridded z files (z+XXXXXX_ll.grib)."""
        chunks = []
        for step in self.steps:
            filepath = os.path.join(gridded_z_dir, f'z+{step}_ll.grib')
            if not os.path.isfile(filepath):
                raise FileNotFoundError(
                    f"Gridded z file not found: {filepath}\n"
                    "Run: bash scripts/convert_spectral_to_grid.sh"
                )
            ds_list = cfgrib.open_datasets(filepath, backend_kwargs={'indexpath': ''})
            merged = None
            for ds in ds_list:
                if 'z' in ds:
                    merged = ds[['z']]
                    break
            if merged is None:
                raise KeyError(f"'z' not found in {filepath}")

            # Rename coordinates for Ribberink compatibility
            rename_map = {}
            if 'isobaricInhPa' in merged.dims:
                rename_map['isobaricInhPa'] = 'level'
            if 'latitude' in merged.coords or 'latitude' in merged.dims:
                rename_map['latitude'] = 'lat'
            if 'longitude' in merged.coords or 'longitude' in merged.dims:
                rename_map['longitude'] = 'lon'
            if rename_map:
                merged = merged.rename(rename_map)

            # Convert longitude from 0-360 to -180 to +180 convention
            # (to match IBTrACS track coordinates which use negative western hemisphere)
            if 'lon' in merged.coords and merged['lon'].min() >= 0:
                merged['lon'] = xr.where(merged['lon'] > 180, merged['lon'] - 360, merged['lon'])
                merged = merged.sortby('lon')

            # Select requested levels (nearest match)
            if levels is not None and 'level' in merged.dims:
                merged = merged.sel(level=list(levels), method='nearest')

            merged = merged.rename({'z': 'zg'})
            merged['zg'] = merged['zg'] / G  # geopotential → height [m]
            merged = _add_time_coord(merged, step)
            chunks.append(merged)

        return xr.concat(chunks, dim='time')

    # ------------------------------------------------------------------
    # Convenience: load single timestep (faster for interactive use)
    # ------------------------------------------------------------------
    def get_msl_timestep(self, step_index):
        """Return MSL for a single step index (0-based)."""
        filepath = self._gg_files[step_index]
        step = self.steps[step_index]
        ds = _read_surface_field(filepath, 'msl')
        return _add_time_coord(ds, step)


# ------------------------------------------------------------------
# Pre-defined run paths on Mahti
# ------------------------------------------------------------------
MAHTI_BASE = '/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306'

RUNS = {
    'baserun': os.path.join(MAHTI_BASE, 'int_exp_1003'),
    '+3K':     os.path.join(MAHTI_BASE, '3k_run'),
    '+6K':     os.path.join(MAHTI_BASE, '6k_run'),
    '-3K':     os.path.join(MAHTI_BASE, 'minus_3k_run'),
}

# Directory containing pre-converted gridded z GRIB files per run
# (produced by scripts/convert_spectral_to_grid.sh)
GRIDDED_Z_BASE = '/scratch/project_2001271/jfkarhu/cps_z_gridded'

# Map from RUNS key to the sub-directory name under GRIDDED_Z_BASE
_GRIDDED_Z_SUBDIR = {
    'baserun': 'baserun',
    '+3K':     'p3K',
    '+6K':     'p6K',
    '-3K':     'm3K',
}


def gridded_z_dir(run_name):
    """Return the directory with pre-converted gridded z files for a run."""
    sub = _GRIDDED_Z_SUBDIR.get(run_name)
    if sub is None:
        raise KeyError(f"Unknown run name '{run_name}'. Valid: {list(RUNS)}")
    return os.path.join(GRIDDED_Z_BASE, sub)


def load_all_runs():
    """
    Convenience function: returns a dict of OIFSRun objects for all
    currently available experiments.
    """
    return {name: OIFSRun(path) for name, path in RUNS.items()
            if os.path.isdir(path)}


if __name__ == '__main__':
    # Quick smoke test
    runs = load_all_runs()
    for name, run in runs.items():
        print(f"\n=== {name} ===")
        msl = run.get_msl_timestep(0)
        print(f"  MSL at t=0: min={float(msl.msl.min()):.0f} Pa, "
              f"max={float(msl.msl.max()):.0f} Pa")
