#!/bin/bash -l
# ---------------------------------------------------------------------------
# Orchestrates the parallel TAF verification pipeline. Run this on a login
# node (it submits SLURM jobs, it is not itself a batch job):
#
#     ./submit_verify.sh
#
# It replaces the single long-running verify.sh job with:
#   1. A one-off preparation step (config files + directories).
#   2. A SLURM job array with one small task per station (run_station.sh).
#   3. A dependent plotting job (run_plots.sh) that only runs once every
#      station task has succeeded.
#
# Splitting the work this way means each task is small and the stations run
# in parallel, while all shared-file writes (config files and the combined
# stats CSVs) happen in single, serial steps so nothing is written twice at
# once.
# ---------------------------------------------------------------------------

source setup_constants.sh

# Update config files ONCE, up front. Doing this inside each array task would
# make many tasks rewrite the same .cfg files at the same time (a race).
module load scitools/production-os48-1
python update_configs.py
module unload scitools

# Create output directories and a logs directory for the batch jobs
mkdir -p logs "${STATS_DIR}" "${STATS_DIR}/per_station"
for taf_type in ${TAF_TYPES}; do
    mkdir -p "${DATA_DIR}/${taf_type}"
done

# Start each run from a clean slate for the stats CSVs so reruns don't
# accumulate duplicate rows.
rm -f "${STATS_DIR}/per_station/"*.csv
rm -f "${STATS_DIR}/"*_stats_*.csv

# Number of stations -> array size (indices 0..last)
nstations=$(echo ${ALL_TAFS} | wc -w)
last=$(( nstations - 1 ))

# Submit the station array. "%20" throttles it to 20 concurrent tasks at a
# time - adjust to suit the queue limits on SPICE.
array_id=$(sbatch --parsable --array=0-${last}%20 run_station.sh)
echo "Submitted station array job ${array_id} (${nstations} tasks)"

# Submit the plotting job so it runs only if the whole array succeeds.
plot_id=$(sbatch --parsable --dependency=afterok:${array_id} run_plots.sh)
echo "Submitted plotting job ${plot_id} (runs after array ${array_id})"
