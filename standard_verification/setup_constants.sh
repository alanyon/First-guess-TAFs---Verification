# This script sets up the constants for the verification process.

# For decoding and verification of TAFs
VER_DATES=20230805-20251004_ml
export DATA_DIR=/data/users/andre.lanyon/tafs/verification/${VER_DATES}
export DECODE_DIR=${DATA_DIR}/decodes
# export TAF_TYPES="no_opt_old no_pes_old 2_opt_old 2_pes_old no_opt_new \
#                   no_pes_new 2_opt_new 2_pes_new Manual"
# export TAF_TYPES="no_pes_old no_pes_new Manual"
export TAF_TYPES="no_pes_old no_pes_new Manual_ml"
# export TAF_TYPES="no_pes no_opt 2_pes 2_opt Manual"
# export TAF_TYPES_SHORT="o1 o2 o3 o4 n1 n2 n3 n4 ma"
# export TAF_TYPES_SHORT="o2 n2 ma"
export TAF_TYPES_SHORT="o2 n2 ma"
# export COMBS="o2n2 o2ma n2ma"
export COMBS="n2ma o2na"
# export COMBS="map1 mao1 map2 mao2"
# export PLOT_TITLES='{"o1": "Old Auto TAFs (optimistic)",
#                      "o2": "Old Auto TAFs (pessimistic)",
#                      "o3": "Old Auto TAFs with\nobs (optimistic)",
#                      "o4": "Old Auto TAFs with\nobs (pessimistic)",
#                      "n1": "New Auto TAFs (optimistic)",
#                      "n2": "New Auto TAFs (pessimistic)",
#                      "n3": "New Auto TAFs with\nobs (optimistic)",
#                      "n4": "New Auto TAFs with\nobs (pessimistic)",
#                      "ma": "Manual TAFs"}'
# export PLOT_TITLES='{"n2": "Auto TAFs",
#                      "ma": "Manual TAFs"}'
export PLOT_TITLES='{"o2": "Old Auto TAFs without\nobs (pessimistic)",
                     "n2": "New Auto TAFs without\nobs (pessimistic)",
                     "ma": "Manual TAFs"}'
# export PLOT_TITLES='{"p1": "Auto TAFs without\nobs (pessimistic)",
#                      "o1": "Auto TAFs without\nobs (optimistic)",
#                      "p2": "Auto TAFs with\nobs (pessimistic)",
#                      "o2": "Auto TAFs with\nobs (optimistic)",
#                      "ma": "Manual TAFs"}'
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
                 EGGW EGHQ EGPK EGLC"
export TAF_9HR="EGHH EGSY EGNJ EGAC EGAE EGBJ EGCK EGEC EGEO EGHI EGNV EGPE \
                EGTE EGPO EGNH EGNR EGNC EGHC EGHE EGKA EGKB EGLF EGMC EGMD \
                EGNO EGPA EGPB EGPC EGPI EGPL EGPN EGPU EGSC EGSH EGTC EGTK "
export VERIF_START=20230805
export VERIF_END=20251004
MONTHS="202308 202309 202310 202311 202312 202401 202402 202403 202404 202405 \
        202406 202407 202408 202409 202410 202411 202412 202501 202502 202503 \
        202504 202505 202506 202507 202508 202509 202510"
# Factor to address that in ML work, test data is 0.25 * full dataset 
# (set to 1 otherwise)
export ML_FACTOR=0.25
