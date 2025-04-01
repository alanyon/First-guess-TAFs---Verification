#!/bin/bash -l

module load scitools/production-os46-3

export PYTHONPATH=~clare.bysouth/VerPy/stable
export ORACLE_OWNER=oracle
export ORACLE_BASE=/usr/lib/oracle/23/client64
export TNS_ADMIN=~andre.lanyon/oracle
export ORACLE_TERM=xterm
export ORACLE_HOME=/usr/lib/oracle/23/client64
export SHLIB_PATH=/usr/lib/oracle/23/client64/lib
export PATH=$PATH:/usr/lib/oracle/23/client64/bin
export DATA_DIR=/data/users/andre.lanyon/tafs/verification/20230805-20250104_imp_vs_bd
export STATS_DIR=${DATA_DIR}/stats
export ALL_TAFS="EGAA EGAC EGAE EGBB EGBJ EGCC EGCK EGCN EGEC EGEO EGFF EGGD \
                 EGGP EGGW EGHC EGHE EGHH EGHI EGHQ EGKA EGKB EGKK EGLF EGLL \
                 EGMC EGMD EGNC EGNH EGNJ EGNM EGNO EGNR EGNT EGNV EGNX EGPA \
                 EGPB EGPC EGPD EGPE EGPF EGPH EGPI EGPK EGPL EGPN EGPO EGPU \
                 EGSC EGSH EGSS EGSY EGTC EGTE EGTK"
export TAF_30HR="EGCC EGLL EGKK EGSS"
export TAF_24HR="EGAA EGGP EGNT EGPF EGNM EGPD EGPH EGFF EGNX EGBB EGCN EGGD \
                 EGGW EGHQ EGPK"
export TAF_9HR="EGHH EGSY EGNJ EGAC EGAE EGBJ EGCK EGEC EGEO EGHI EGNV EGPE \
                EGTE EGPO EGNH EGNR EGNC EGHC EGHE EGKA EGKB EGLF EGMC EGMD \
                EGNO EGPA EGPB EGPC EGPI EGPL EGPN EGPU EGSC EGSH EGTC EGTK"
export TAF_TYPES="BestData Improver Manual"
export COMBS="bdim mabd maim"
export VERIF_START=20230804
export VERIF_END=20250104
MONTHS="202308 202309 202310 202311 202312 202401 202402 202403 202404 202405 \
        202406 202407 202408 202409 202410 202411 202412 202501"

# Update config files
python update_configs.py

# Make directories
mkdir ${STATS_DIR}
for taf_type in ${TAF_TYPES}; do
    mkdir ${DATA_DIR}/${taf_type}
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
