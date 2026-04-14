# Hurricane Kirk OIFS Forecast Analysis

Analysis of Hurricane Kirk (2024) in OpenIFS (OIFS) SST-perturbation forecasts,
with **Hart Cyclone Phase Space (CPS)** as the central diagnostic and storm-track/
wind-radius analyses as supporting components. The workflow explicitly reuses
Ribberink et al. (2025) methods and code interfaces from `ribberink_code/`.

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

## Start Here (Mahti User Workflow)

This section is the fastest path to run the repository if you have access to Mahti and the
OpenIFS output directories listed above.

### 1. Minimal setup

```bash
cd /users/jfkarhu/Numlab/hurricane_kirk
source .venv/bin/activate
source .project_setup.sh
module load eccodes
```

### 2. Fixed paths for this repository

This repository is configured to reproduce the same Hurricane Kirk dataset on Mahti.
In normal use, do **not** edit paths or initialization time.

Path and timing constants are intentionally fixed in `scripts/oifs_adapter.py`:
- `MAHTI_BASE`
- `GRIDDED_Z_BASE`
- `INIT_DATETIME`

Before running, just verify access to those fixed paths:

```bash
ls /scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306/int_exp_1003 | head
ls /scratch/project_2001271/jfkarhu/cps_z_gridded/baserun | head
```

If these checks fail, the issue is typically permissions or filesystem availability, not a repository configuration issue.

### 3. Recommended run order

```bash
# 1) Track files (required by all downstream diagnostics)
python scripts/run_track.py

# 2) ETT timing (produces ett_start_summary.csv used by marker overlays)
python scripts/run_ett_timing_analysis.py

# 3) CPS figure
python scripts/run_cps_analysis.py

# 4) Track comparison plot (with polygon + ETT markers)
python scripts/plot_tracks_comparison.py

# 5) Execute notebook analyses that generate remaining comparison figures
python -m jupyter nbconvert --execute --to notebook --inplace notebooks/04_wind_radius.ipynb
python -m jupyter nbconvert --execute --to notebook --inplace notebooks/05_multi_run_comparison.ipynb
```

### 4. Typical hiccups and fixes

- `RuntimeError ... spectral format (no lat/lon coordinates)` in CPS:
  run `scripts/convert_spectral_to_grid.sh` and ensure `GRIDDED_Z_BASE` points to the converted files.
- `git: command not found` on Mahti:
  run `source .project_setup.sh` before git commands.
- `cartopy` missing:
  notebook 05 falls back to plain axes for map plotting, but install cartopy for full map rendering.
- IBTrACS file not found:
  ensure `data/IBTrACS.NA.v04r01.nc` exists (see setup section below).

## OIFS Output Files

Each run directory contains three GRIB file types per timestep:

| File pattern | Contents |
|-------------|---------|
| `ICMGGac3u+XXXXXX` | Surface fields: `msl` (MSLP), `10u`, `10v`, `tp`, `sst` |
| `ICMSHac3u+XXXXXX` | Pressure levels: `u`, `v`, `t`, `z` (geopotential), `r`, `w`, `vo` (100–950 hPa) |
| `ICMUAac3u+XXXXXX` | Additional upper-air: `q`, `pv` (100–950 hPa) |

## Analysis Goals

1. **CPS-first structure diagnosis** – Hart parameters (*B*, *V_T^U*, *V_T^L*) across runs
2. **Core radius evolution** – Direction-aware and mean wind-radius diagnostics (R17, R34, R50)
3. **Track as required input** – Storm-centre time series for storm-relative sampling
4. **SST sensitivity** – Compare structure/intensity evolution across all four experiments

## Methods (Ribberink et al. 2025)

This project follows a **CPS-centered pipeline** derived from Ribberink et al.:

1. Compute storm track (minimum MSLP search-box propagation)
2. Use that track to construct storm-relative geopotential fields
3. Compute Hart CPS via Ribberink `hart` implementation
4. Complement with wind-radius/core-size diagnostics

Primary reused code is in `ribberink_code/hurricane_functions.py`:

- `storm_tracker` for centre tracking
- `hart` for CPS metrics and hemisphere-aware asymmetry
- `magnitude` and related helpers used by wind diagnostics

- **Storm tracking** (`storm_tracker`): follows minimum MSLP within a search box, initialised
  from the IBTrACS best track position at the first timestep. The local tracker now
  applies a seed sanity check against the model's first-step North Atlantic MSL minimum
  to avoid locking onto the wrong low-pressure system if the external seed is inconsistent.
- **Cyclone Phase Space** (`hart`): asymmetry parameter *B* and thermal wind *V_T* from
  geopotential height differences at 300/600 and 600/900 hPa across a 500 km radius.
- **Wind radius** (`wind_radius`): meridional/zonal slices through storm centre of 10 m wind speed.
- **Directional core radius** (this repo): radii are evaluated relative to storm motion
  (forward/backward/left/right), plus mean-radius diagnostics for each wind threshold.

## Status Snapshot (April 2026)

### Track analysis

- Status: **completed baseline**
- Implemented in `notebooks/02_track_analysis.ipynb` and `scripts/run_track.py`
- Outputs present in `plots/tracks/` for all four runs (`track_*.nc` and CSV exports)

### CPS analysis (core project axis)

- Status: **completed and validated**
- Implemented in `notebooks/03_cps_analysis.ipynb` and `scripts/run_cps_analysis.py`
- Uses OIFS geopotential-height conversion in `scripts/oifs_adapter.py` and Ribberink `hart`
- Verified output: `plots/kirk_cps.png`

### Core radius / wind-radius analysis

- Status: **completed and validated**
- Implemented in `notebooks/04_wind_radius.ipynb` (R17 time series) and directional core-radius CSV workflow
- Batch script implemented in `scripts/core_radius_metrics.py` for directional + mean radius metrics
- Outputs: `plots/tracks/core_radius_<run>.csv` and `plots/tracks/core_radius_summary.csv`
- Verified output: `plots/kirk_R17.png`

### Session handoff (2026-04-10, end of day)

- CPS preprocessing and plotting path is now working with gridded geopotential input (`scripts/convert_spectral_to_grid.sh`, `scripts/oifs_adapter.py`, `scripts/run_cps_analysis.py`).
- Ribberink Fig. 5-style ETT timing logic has been identified from `ribberink_code/new_hart_comp.ipynb`:
  - ETT start criterion used there is first time where lower-layer asymmetry exceeds threshold: `B > 10 m` (600-900 hPa layer).
- A dedicated multi-run timing script has been created and validated: `scripts/run_ett_timing_analysis.py`.
  - It computes lower-layer B series per run and ET-start timestamps using the same threshold criterion.
  - It writes `plots/ett_start_timing.png`, `plots/tracks/ett_start_summary.csv`, and per-run `plots/tracks/ett_B_timeseries_<run>.csv` files.
  - Latest ET-start timestamps:
    - `baserun`: 2024-10-06 06:00 UTC
    - `+3K`: 2024-10-06 15:00 UTC
    - `+6K`: 2024-10-06 15:00 UTC
    - `-3K`: 2024-10-07 09:00 UTC

Suggested restart sequence:
1. `cd /users/jfkarhu/Numlab/hurricane_kirk`
2. `source .venv/bin/activate`
3. If needed, rerun `python scripts/run_ett_timing_analysis.py`
4. Continue with `notebooks/05_multi_run_comparison.ipynb`

### Latest verified outputs (April 2026)

- `plots/ett_start_timing.png`
- `plots/kirk_cps.png`
- `plots/track_comparison_polygon_ett.png`
- `plots/kirk_R17.png`
- `plots/kirk_mslp_comparison.png`
- `plots/kirk_summary_stats.csv`

## Session Workflow & Reproducibility

### At Session Start
1. Read `docs/session_archive/COMPLETION_SUMMARY_<DATE>.md` for quick status recap.
2. Read `project_prompts.md` and `project_prompts_and_responses.md` headers to continue numbering.
3. Refer to README.md "Status Snapshot" section for current completion state.

### During Session
- **Append promptly**: After each new user prompt, immediately add entries to both:
  - `project_prompts.md` (user prompt only)
  - `project_prompts_and_responses.md` (prompt #N + response summary)
- **Avoid stalls during wrap-up**: When committing, do NOT load data files or run expensive operations. Keep wrap-up operations lightweight (log-writing + git commands only).
- **Include logs in commits**: Every commit should include both log files if they changed.

### At Session End (Wrap-Up Protocol)
1. **Update prompt logs** with final prompt+response entries.
2. **Create/update completion summary**: `docs/session_archive/COMPLETION_SUMMARY_<DATE>.md`
   - Key achievements, file modifications, pending tasks.
   - Quick-start commands for next session.
   - Known issues and blockers.
3. **Avoid data loading**: Do not run analysis scripts or load GRIB/NetCDF during wrap-up. Use only lightweight file I/O.
4. **Git setup for HPC** (IMPORTANT):
   - **Use bash terminal only** (not Python terminal) for git commands
   - **Load git module** before committing:
     ```bash
     source .project_setup.sh    # Auto-loads git/2.40.0
     # OR manually:
     module load git
     ```
   - Why: Git is installed via spack on HPC but not in default PATH
5. **Commit & push**:
   ```bash
   # Ensure git is available first:
   source .project_setup.sh

   # Then stage and commit:
  git add project_prompts.md project_prompts_and_responses.md docs/session_archive/COMPLETION_SUMMARY_*.md <modified-scripts>
   git commit -m "Session <date>: <brief achievement summary>"
   git push
   ```

### Prompt Reproducibility Logs

- `project_prompts.md` (user prompts only)
- `project_prompts_and_responses.md` (prompt + response summaries)
- Prior-session prompts were not found at start, so logging began at first recorded entry.

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
| Mean sea-level pressure | `msl` | `ICMGGac3u` | `msl` | OK |
| 10 m U-wind | `u10m` | `ICMGGac3u` | `10u` | OK |
| 10 m V-wind | `v10m` | `ICMGGac3u` | `10v` | OK |
| Geopotential @ 300 hPa | `z` | `ICMSHac3u` | `z` | OK |
| Geopotential @ 600 hPa | `z` | `ICMSHac3u` | `z` | OK |
| Geopotential @ 900 hPa | `z` | `ICMSHac3u` | `z` | OK |
| IBTrACS best track | `best_track` | `data/IBTrACS.NA.v04r01.nc` | — | OK |

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
│   ├── run_cps_analysis.py        # CPS multi-run plotting/diagnostics runner
│   ├── run_ett_timing_analysis.py # ETT-start timing runner
│   ├── core_radius_metrics.py     # Direction-aware and mean core-radius metrics
│   ├── plot_tracks_comparison.py  # Plot all runs and optional best-track overlay
│   └── download_ibtracs.py        # Download IBTrACS best track for Kirk 2024
├── dev_tools/                     # Optional diagnostics and ad hoc sanity checks
│   ├── diag_grib_coords.py
│   └── test_hart_minimal.py
├── docs/
│   └── session_archive/           # Archived session handoff summaries
├── ribberink_code/                # Cloned from MRibberink/OpheliaPaperCode
├── plots/                         # Output figures and tracked CSV diagnostics
├── data/                          # IBTrACS file (not committed, too large)
├── .gitignore
├── project_prompts.md             # Prompt-only reproducibility log
├── project_prompts_and_responses.md  # Prompt+response reproducibility log
├── README.md
└── requirements.txt
```

## Setup

### 1. Python environment

Use a project-local environment in this repository (`hurricane_kirk/.venv`) so sessions are reproducible and independent from sibling workspaces.

```bash
cd /users/jfkarhu/Numlab/hurricane_kirk
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Note:
- `cfgrib`/`eccodes` Python packages are included in `requirements.txt`.
- Depending on system configuration, ecCodes system libraries may still be needed (on Mahti, use `module load eccodes`).

### 2. IBTrACS data for Kirk 2024

```bash
# Download the current North Atlantic IBTrACS release used by the scripts
cd data/
wget https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/netcdf/IBTrACS.NA.v04r01.nc
```

### 3. Run the analysis

```bash
cd /users/jfkarhu/Numlab/hurricane_kirk
source .venv/bin/activate
module load eccodes git/2.40.0
jupyter notebook
```

### 4. Generate model-track and comparison plots

```bash
cd /users/jfkarhu/Numlab/hurricane_kirk
source .venv/bin/activate

# Recompute tracks for all four SST experiments
python scripts/run_track.py
python scripts/run_ett_timing_analysis.py
python scripts/run_cps_analysis.py

# Plot only model tracks
python scripts/plot_tracks_comparison.py --no-best-track --label-hour 12

# Plot model tracks with IBTrACS best track over the same time extent
python scripts/plot_tracks_comparison.py --label-hour 12
```

## Version Control

This project is tracked with Git. Large data files (GRIB, NetCDF) are excluded via `.gitignore`.
Selected plot products (PNG) and diagnostic CSV outputs are tracked for reproducibility.

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
