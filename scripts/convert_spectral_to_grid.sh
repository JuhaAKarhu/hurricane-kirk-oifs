#!/bin/bash
# convert_spectral_to_grid.sh
# ===========================
# Converts OIFS ICMSHac3u spectral GRIB1 files to regular lat/lon grid
# by extracting geopotential (z) at 300/600/900 hPa and applying CDO sp2gp.
#
# Output structure:
#   /scratch/project_2001271/jfkarhu/cps_z_gridded/{run_name}/z+XXXXXX_ll.grib
#
# Runs all 4 SST-perturbation runs in parallel (one background job each).
# Expected total time: ~5-8 minutes.
#
# Usage:
#   bash scripts/convert_spectral_to_grid.sh
#   # Or for a single run:
#   bash scripts/convert_spectral_to_grid.sh baserun

set -e

module load eccodes 2>/dev/null || true
module load cdo    2>/dev/null || true

BASEDIR=/scratch/project_2001271/vasiakan/oifs_expt/kirk/T639L91/2024100306
OUTBASE=/scratch/project_2001271/jfkarhu/cps_z_gridded

# Map: run_name → source directory
declare -A RUN_DIRS=(
    [baserun]="$BASEDIR/int_exp_1003"
    [p3K]="$BASEDIR/3k_run"
    [p6K]="$BASEDIR/6k_run"
    [m3K]="$BASEDIR/minus_3k_run"
)

convert_run() {
    local run_name=$1
    local run_dir=$2
    local outdir="$OUTBASE/$run_name"

    mkdir -p "$outdir"

    local count=0
    local skipped=0

    for srcfile in "$run_dir"/ICMSHac3u+??????; do
        [[ -f "$srcfile" ]] || continue
        local step
        step=$(basename "$srcfile" | sed 's/ICMSHac3u+//')
        local outfile="$outdir/z+${step}_ll.grib"

        if [[ -f "$outfile" && -s "$outfile" ]]; then
            skipped=$((skipped + 1))
            continue
        fi

        # Extract spectral z at 300/600/900 hPa into a temp file
        local tmp
        tmp=$(mktemp /tmp/z_spectral_XXXXXX.grib1)

        grib_copy -w shortName=z,typeOfLevel=isobaricInhPa,level=300/600/900 \
            "$srcfile" "$tmp"

        # Spectral → Gaussian lat/lon grid
        cdo -s sp2gp "$tmp" "$outfile"

        rm -f "$tmp"
        count=$((count + 1))
        echo "[$run_name] +${step} → done"
    done

    echo "[$run_name] Finished: $count converted, $skipped skipped → $outdir"
}

# If a specific run is requested, process only that one
if [[ -n "$1" ]]; then
    if [[ -z "${RUN_DIRS[$1]+x}" ]]; then
        echo "ERROR: Unknown run '$1'. Valid: ${!RUN_DIRS[*]}"
        exit 1
    fi
    convert_run "$1" "${RUN_DIRS[$1]}"
else
    # Process all runs in parallel
    echo "Starting parallel conversion of all 4 runs..."
    for run_name in "${!RUN_DIRS[@]}"; do
        convert_run "$run_name" "${RUN_DIRS[$run_name]}" &
    done
    wait
    echo "=== All conversions complete ==="
    echo "Output in: $OUTBASE"
fi
