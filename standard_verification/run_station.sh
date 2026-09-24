#!/bin/bash -l
#SBATCH --partition=cpu
#SBATCH --mem=4G
#SBATCH --ntasks=1
#SBATCH --time=180
#SBATCH --output=logs/station_%A_%a.out
#SBATCH --error=logs/station_%A_%a.err

# ---------------------------------------------------------------------------
# One SLURM array task per station (ICAO).
#
# Each task runs driver.py for every month and TAF type for a SINGLE station,
# then computes that station's stats into its OWN per-station CSV (written by
# print_stats.py under ${STATS_DIR}/per_station/). Because every task writes
# only to files whose names contain its own ICAO, there are no simultaneous
# writes to any shared file, so all tasks are safe to run in parallel.
#
# Submit via submit_verify.sh (which also sets the --array range).
# ---------------------------------------------------------------------------

# Load constants and Python environment
source setup_constants.sh
module load scitools/production-os48-1

# Pick this task's station from the station list using the array index
stations=(${ALL_TAFS})
icao=${stations[${SLURM_ARRAY_TASK_ID}]}
echo "Array task ${SLURM_ARRAY_TASK_ID} -> station ${icao}"

# Determine the TAF length (verification period) for this station
typeset -A length
for i in ${TAF_30HR}; do length[$i]=30; done
for i in ${TAF_24HR}; do length[$i]=24; done
for i in ${TAF_9HR};  do length[$i]=9;  done
duration=${length[${icao}]}

# Ensure output directories exist
mkdir -p "${STATS_DIR}" "${STATS_DIR}/per_station"
for taf_type in ${TAF_TYPES}; do
    mkdir -p "${DATA_DIR}/${taf_type}"
done

# Run TAF analysis for every month and TAF type for this station
for month in ${MONTHS}; do
    year=${month:0:4}
    month_num=${month:4:2}
    ndays=$(cal ${month_num} ${year} | awk 'NF {DAYS = $NF}; END {print DAYS}')
    start=${month}010000
    end=${month}${ndays}2359
    echo "${icao} ${start} ${end}"
    for taf_type in ${TAF_TYPES}; do
        outdir=${DATA_DIR}/${taf_type}
        outfile=${outdir}/${icao}_${month}.out
        visfile=${outdir}/${icao}_${month}_vis.nc
        clbfile=${outdir}/${icao}_${month}_clb.nc
        uncvisfile=${outdir}/${icao}_${month}_vis_unc.nc
        uncclbfile=${outdir}/${icao}_${month}_clb_unc.nc
        configfile=${taf_type}.cfg
        # Remove stale NetCDF from previous runs (VerPy writes with
        # overwrite=False, so leftover files would cause problems on reruns)
        rm -f "${visfile}" "${clbfile}" "${uncvisfile}" "${uncclbfile}"
        date > "${outfile}"
        python driver.py "${start}" "${end}" "${icao}" "${duration}" \
            "${visfile}" "${clbfile}" "${uncvisfile}" "${uncclbfile}" \
            "${configfile}" >> "${outfile}"
        date >> "${outfile}"
    done
done

# Compute this station's stats into its own per-station CSV
python print_stats.py "${icao}"

echo "Finished station ${icao}"
exit 0
