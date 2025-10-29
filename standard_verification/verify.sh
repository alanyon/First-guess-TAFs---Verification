#!/bin/bash -l
#SBATCH --partition=cpu-long
#SBATCH --mem=2G
#SBATCH --ntasks=4
#SBATCH --output=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/standard_verification/test2.out
#SBATCH --time=3000
#SBATCH --error=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/standard_verification/test2.err

# Load in constants 
source setup_constants.sh

# Activate conda environment
module load scitools/production-os46-3

# Update config files
python update_configs.py

# Make directories if necessary
if [ ! -d "${STATS_DIR}" ]; then
    mkdir ${STATS_DIR}
fi
for taf_type in ${TAF_TYPES}; do
        if [ ! -d "${DATA_DIR}/${taf_type}" ]; then
        mkdir ${DATA_DIR}/${taf_type}
        fi
done

# Set taf lengths
typeset -A length
for icao in $TAF_30HR; do
    length[$icao]=30
done
for icao in $TAF_24HR; do
    length[$icao]=24
done
for icao in $TAF_9HR; do
    length[$icao]=9
done

# Run TAF analysis for Operational and FirstGuess
for icao in $ALL_TAFS; do
duration=${length[$icao]}
  for month in $MONTHS; do
    year=${month:0:4}
    month_num=${month:4:2}
    ndays=$(cal $month_num $year | awk 'NF {DAYS = $NF}; END {print DAYS}')
    start=${month}010000
    end=${month}${ndays}2359
    echo ${icao} ${start} ${end}
    for taf_type in ${TAF_TYPES}; do
      outdir=${DATA_DIR}/${taf_type}
      outfile=${outdir}/${icao}_${month}.out
      visfile=${outdir}/${icao}_${month}_vis.nc
      clbfile=${outdir}/${icao}_${month}_clb.nc
      uncvisfile=${outdir}/${icao}_${month}_vis_unc.nc
      uncclbfile=${outdir}/${icao}_${month}_clb_unc.nc
      configfile=${taf_type}.cfg
      date >  $outfile
      python driver.py ${start} ${end} ${icao} ${duration} ${visfile} ${clbfile} ${uncvisfile} ${uncclbfile} ${configfile} >> $outfile
      date >>  $outfile
    done
  done
  python print_stats.py ${icao}
done

# Make some plots
module unload scitools
conda activate default_clone
python plot_stats.py
conda deactivate

exit 0
