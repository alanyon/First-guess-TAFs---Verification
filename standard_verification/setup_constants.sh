# This script sets up the constants for the verification process.

# For decoding and verification of TAFs
VER_DATES=20230805-20251204_ml
export DATA_DIR=/data/users/andre.lanyon/tafs/verification/${VER_DATES}
export DECODE_DIR=${DATA_DIR}/decodes
export TAF_TYPES="no_pes_old xgboost_no_pes_new Manual_ml"
export TAF_TYPES_SHORT="o2 x2 ma"
export COMBS="o2x2 x2ma"
export PLOT_TITLES='{"o2": "Auto TAFs (without ML)",
                     "x2": "Auto TAFs (with ML)",
                     "ma": "Manual TAFs"}'
export PYTHONPATH=~clare.bysouth/VerPy/stable
export ORACLE_OWNER=oracle
export ORACLE_BASE=/usr/lib/oracle/23/client64
export TNS_ADMIN=~andre.lanyon/oracle
export ORACLE_TERM=xterm
export ORACLE_HOME=/usr/lib/oracle/23/client64
export SHLIB_PATH=/usr/lib/oracle/23/client64/lib
export PATH=$PATH:/usr/lib/oracle/23/client64/bin
export STATS_DIR=${DATA_DIR}/stats
export ALL_TAFS="EGAA EGAC EGAE EGBB EGBJ EGCC EGCK EGCN EGEC EGEO EGFF EGGD \
                 EGGP EGGW EGHC EGHE EGHH EGHI EGHQ EGKA EGKB EGKK EGLC EGLF \
                 EGLL EGMC EGMD EGNC EGNH EGNJ EGNM EGNO EGNR EGNT EGNV EGNX \
                 EGPA EGPB EGPC EGPD EGPE EGPF EGPH EGPI EGPK EGPL EGPN EGPO \
                 EGPU EGSC EGSH EGSS EGSY EGTC EGTE EGTK"
export TAF_30HR="EGCC EGLL EGKK EGSS"
export TAF_24HR="EGAA EGGP EGNT EGPF EGNM EGPD EGPH EGFF EGNX EGBB EGCN EGGD \
                 EGGW EGPK EGLC"
export TAF_9HR="EGHH EGSY EGNJ EGAC EGAE EGBJ EGCK EGEC EGEO EGHI EGNV EGPE \
                EGTE EGPO EGNH EGNR EGNC EGHC EGHE EGKA EGKB EGLF EGMC EGMD \
                EGNO EGPA EGPB EGPC EGPI EGPL EGPN EGPU EGSC EGSH EGTC EGTK \
                EGHQ"
export VERIF_START=20230805
export VERIF_END=20251204
MONTHS="202308 202309 202310 202311 202312 202401 202402 202403 202404 202405 \
        202406 202407 202408 202409 202410 202411 202412 202501 202502 202503 \
        202504 202505 202506 202507 202508 202509 202510 202511 202512"
# Factor to address that in ML work, test data is 0.25 * full dataset 
# (set to 1 otherwise)
export ML_FACTOR=0.25
