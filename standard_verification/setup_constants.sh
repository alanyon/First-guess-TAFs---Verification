# This script sets up the constants for the verification process.

# For decoding and verification of TAFs
VER_DATES=20230805-20250404
export DATA_DIR=/data/users/andre.lanyon/tafs/verification/${VER_DATES}
export DECODE_DIR=${DATA_DIR}/decodes
export TAF_TYPES="no_opt no_pes 2_opt 2_pes Manual"
export TAF_TYPES_SHORT="i1 i2 i3 i4 ma"
export COMBS="i1ma i2ma i3ma i4ma i1i2 i1i3 i1i4 i2i3 i2i4 i3i4"
export PLOT_TITLES='{"i1": "IMPROVER TAFs\n(optimistic)",
                     "i2": "IMPROVER TAFs\n(pessimistic)",
                     "i3": "IMPROVER TAFs\nwith obs (optimistic)",
                     "i4": "IMPROVER TAFs\nwith obs (pessimistic)",
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

export VERIF_START=20230804
export VERIF_END=20250404
MONTHS="202308 202309 202310 202311 202312 202401 202402 202403 202404 202405 \
        202406 202407 202408 202409 202410 202411 202412 202501 202502 202503 \
        202504"
