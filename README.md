# Hurricane Kirk OIFS Forecast Analysis

Analysis of Hurricane Kirk (2024) track and core size using OpenIFS (OIFS) forecast
simulations with different SST perturbations. Based on methods from
[Ribberink et al. (2025)](https://doi.org/10.5194/egusphere-2025-218).

## Experiments

| Run | Description | Path on Mahti |
|-----|-------------|---------------|
| baserun | Control run (no SST pert.) | `/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/int_exp_1003` |
| +3K | +3 K SST perturbation | `/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/3k_run` |
| +6K | +6 K SST perturbation | `/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/6k_run` |
| -3K | -3 K SST perturbation | `/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/minus_3k_run` |

- **Model**: OpenIFS T639L91 (~31 km horizontal resolution, 91 vertical levels)
- **Init time**: 2024-10-03 06:00 UTC
- **Output frequency**: 3-hourly (`+000012` in file names means 12 model steps = 3 h at 15 min timestep)
- **Forecast length**: ~576 h (baserun), ~264 h (SST runs)

## OIFS Output Files

Each run directory contains three GRIB file types per timestep:

| File pattern | Contents |
|-------------|---------|
| `ICMGGac3u+XXXXXX` | Surface fields: `msl` (MSLP), `10u`, `10v`, `tp`, `sst` |
| `ICMSHac3u+XXXXXX` | Pressure levels: `u`, `v`, `t`, `z` (geopotential), `r`, `w`, `vo` (100–950 hPa) |
| `ICMUAac3u+XXXXXX` | Additional upper-air: `q`, `pv` (100–950 hPa) |

## Analysis Goals

1. **Track** – Hurricane centre position and minimum sea-level pressure over time
2. **Core size** – Wind radii (R17, R34 in m/s) and Cyclone Phase Space (Hart 2003)
3. **SST sensitivity** – Compare track/intensity/size across the four SST perturbation experiments

## Methods (Ribberink et al. 2025)

- **Storm tracking** (`storm_tracker`): follows minimum MSLP within a search box, initialised
  from the IBTrACS best track position at the first timestep. The local tracker now
  applies a seed sanity check against the model's first-step North Atlantic MSL minimum
  to avoid locking onto the wrong low-pressure system if the external seed is inconsistent.
- **Cyclone Phase Space** (`hart`): asymmetry parameter *B* and thermal wind *V_T* from
  geopotential height differences at 300/600 and 600/900 hPa across a 500 km radius.
- **Wind radius** (`wind_radius`): meridional/zonal slices through storm centre of 10 m wind speed.

## Best-Track Data

- **Preferred source**: IBTrACS v04r01 NetCDF, loaded directly from NOAA/NCEI.
- **Local file**: `data/IBTrACS.NA.v04r01.nc`
- **Storm selection**: `name == "KIRK"` and `season == 2024`
- **Time coverage used here**: clipped to the model-track time window when plotting comparisons
- **Longitude convention**: IBTrACS longitudes are converted to `-180..180` for plotting consistency

The older `IBTrACS.NA.v04r00.nc` file in this repository does not contain the 2024 Kirk entry,
so the analysis should use v04r01. The `kirk_best_track.pickle` file is retained only as a
fallback and should not be preferred when v04r01 is available.

## Data Requirements vs Availability

| Required variable | Ribberink name | OIFS file | OIFS shortName | Available? |
|------------------|---------------|-----------|----------------|------------|
| Mean sea-level pressure | `msl` | `ICMGGac3u` | `msl` | ✅ |
| 10 m U-wind | `u10m` | `ICMGGac3u` | `10u` | ✅ |
| 10 m V-wind | `v10m` | `ICMGGac3u` | `10v` | ✅ |
| Geopotential @ 300 hPa | `z` | `ICMSHac3u` | `z` | ✅ |
| Geopotential @ 600 hPa | `z` | `ICMSHac3u` | `z` | ✅ |
| Geopotential @ 900 hPa | `z` | `ICMSHac3u` | `z` | ✅ |
| IBTrACS best track | `best_track` | `data/IBTrACS.NA.v04r01.nc` | — | ✅ |

**Note on geopotential**: OIFS outputs geopotential *Φ* (m² s⁻²). Ribberink's code uses
geopotential height *Z* = Φ / g. The adapter in `scripts/oifs_adapter.py` performs this
conversion automatically (g = 9.80665 m s⁻²).

## Project Structure

```
hurricane_kirk/
├── notebooks/
│   ├── 01_data_check.ipynb        # Verify GRIB files and variables
│   ├── 02_track_analysis.ipynb    # Storm tracking for all runs
│   ├── 03_cps_analysis.ipynb      # Cyclone Phase Space diagrams
│   ├── 04_wind_radius.ipynb       # Core size / wind radius analysis
│   └── 05_multi_run_comparison.ipynb  # Compare all SST experiments
├── scripts/
│   ├── oifs_adapter.py            # Read OIFS GRIB → xarray (Ribberink-compatible)
│   ├── run_track.py               # Batch track computation for all runs
│   ├── plot_tracks_comparison.py  # Plot all runs and optional best-track overlay
│   └── download_ibtracs.py        # Download IBTrACS best track for Kirk 2024
├── ribberink_code/                # Cloned from MRibberink/OpheliaPaperCode
├── plots/                         # Output figures (not committed)
├── data/                          # IBTrACS file (not committed, too large)
├── .gitignore
├── README.md
└── requirements.txt
```

## Setup

### 1. Python environment

The analysis uses the existing `.venv` in `run_oifs`. Additional packages needed:

```bash
source /users/jfkarhu/Numlab/run_oifs/.venv/bin/activate
pip install haversine matplotlib cartopy jupyter scipy
```

### 2. IBTrACS data for Kirk 2024

```bash
# Download the current North Atlantic IBTrACS release used by the scripts
cd data/
wget https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/netcdf/IBTrACS.NA.v04r01.nc
```

### 3. Run the analysis

```bash
cd /users/jfkarhu/Numlab/hurricane_kirk
source /users/jfkarhu/Numlab/run_oifs/.venv/bin/activate
module load eccodes git/2.40.0
jupyter notebook
```

### 4. Generate model-track and comparison plots

```bash
cd /users/jfkarhu/Numlab/hurricane_kirk
source /users/jfkarhu/Numlab/run_oifs/.venv/bin/activate

# Recompute tracks for all four SST experiments
python scripts/run_track.py

# Plot only model tracks
python scripts/plot_tracks_comparison.py --no-best-track --label-hour 12

# Plot model tracks with IBTrACS best track over the same time extent
python scripts/plot_tracks_comparison.py --label-hour 12
```

## Version Control

This project is tracked with Git. Large data files (GRIB, NetCDF) are excluded via `.gitignore`.

```bash
# First-time GitHub setup (replace YOUR_USERNAME with your GitHub username):
git remote add origin git@github.com:YOUR_USERNAME/hurricane_kirk.git
git push -u origin main
```

## References

- Ribberink, M., et al. (2025). *The impact of SST warming on the track, intensity and
  structure of Hurricane Ophelia (2017)*. EGUsphere preprint.
  https://doi.org/10.5194/egusphere-2025-218
- Hart, R. E. (2003). A Cyclone Phase Space Derived from Thermal Wind and Thermal
  Asymmetry. *Monthly Weather Review*, 131, 585–616.
