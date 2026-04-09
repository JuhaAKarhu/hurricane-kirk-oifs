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
    def get_geopotential_height(self, levels=(300, 600, 900)):
        """
        Return geopotential height (Z = Φ/g) at requested pressure levels.
        OIFS outputs geopotential Φ (m² s⁻²); division by G converts to
        geopotential height in metres.

        Parameters
        ----------
        levels : tuple of int
            Pressure levels in hPa. Default (300, 600, 900) for CPS analysis.

        Returns
        -------
        xr.Dataset with variable 'zg' [m] and dimensions (time, level, lat, lon)
        """
        chunks = []
        for filepath, step in zip(self._sh_files, self.steps):
            ds = _read_pressure_field(filepath, 'z', levels=levels)
            ds = ds.rename({'z': 'zg'})
            ds['zg'] = ds['zg'] / G  # geopotential → geopotential height
            ds = _add_time_coord(ds, step)
            chunks.append(ds)
        z_ds = xr.concat(chunks, dim='time')
        return z_ds

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
