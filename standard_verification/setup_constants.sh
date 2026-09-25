# This script sets up the constants for the verification process.

# Select which set of TAF types to verify. Override before sourcing, e.g.
#   export VERIF_PROFILE=ml
# Supported profiles:
#   standard - Optimistic/Pessimistic auto TAFs vs Manual TAFs (default)
#   ml       - Auto TAFs before/after machine learning vs Manual TAFs
#   fog      - Auto TAFs before/after fog machine learning vs Manual TAFs
export VERIF_PROFILE=${VERIF_PROFILE:-standard}

# For decoding and verification of TAFs
VER_DATES=20230805-20260805
export DATA_DIR=/data/users/andre.lanyon/tafs/verification/${VER_DATES}
export DECODE_DIR=${DATA_DIR}/decodes

# Profile-specific TAF types, combinations, plot labels and ML factor.
# TAF_TYPES        : names of the TAF types (also used for cfg/db/out names)
# TAF_TYPES_SHORT  : short codes used as keys throughout the code
# COMBS            : pairwise combinations to compare in scatter plots
# PLOT_TITLES      : display names (JSON) keyed by short code
# ML_FACTOR        : addresses ML test data being 0.25 * full dataset
#                    (set to 1 when the full dataset is used)
case "${VERIF_PROFILE}" in
    standard)
        export TAF_TYPES="opt_all pes_all Manual"
        export TAF_TYPES_SHORT="op pe ma"
        export COMBS="opma pema oppe"
        export PLOT_TITLES='{"op": "Auto TAFs (Optimistic)",
                             "pe": "Auto TAFs (Pessimistic)",
                             "ma": "Manual TAFs"}'
        export ML_FACTOR=1
        ;;
    ml)
        export TAF_TYPES="no_pes_old xgboost_no_pes_new no_opt_old xgboost_no_opt_new Manual_ml"
        export TAF_TYPES_SHORT="p1 p2 o1 o2 ma"
        export COMBS="p2ma o2ma o2p2"
        export PLOT_TITLES='{"p1": "Pessimistic Auto TAFs\n(without ML)",
                             "p2": "Pessimistic Auto TAFs\n(with ML)",
                             "o1": "Optimistic Auto TAFs\n(without ML)",
                             "o2": "Optimistic Auto TAFs\n(with ML)",
                             "ma": "Manual TAFs"}'
        export ML_FACTOR=0.25
        ;;
    fog)
        export TAF_TYPES="no_pes_all no_pes_ml_all_fog Manual_ml"
        export TAF_TYPES_SHORT="p2 f2 ma"
        export COMBS="p2f2 f2ma"
        export PLOT_TITLES='{"p2": "Auto TAFs (without fog ML)",
                             "f2": "Auto TAFs (with fog ML)",
                             "ma": "Manual TAFs"}'
        export ML_FACTOR=1
        ;;
    *)
        echo "Unknown VERIF_PROFILE='${VERIF_PROFILE}'." \
             "Valid options: standard, ml, fog" >&2
        exit 1
        ;;
esac
# VerPy plus a local pkg_resources compat shim (compat/) so VerPy imports
# under scitools os48+ where setuptools no longer ships pkg_resources.
_SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH=~clare.bysouth/VerPy/stable:${_SETUP_DIR}/compat
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
export VERIF_END=20260805
MONTHS="202308 202309 202310 202311 202312 202401 202402 202403 202404 202405 \
        202406 202407 202408 202409 202410 202411 202412 202501 202502 202503 \
        202504 202505 202506 202507 202508 202509 202510 202511 202512 202601 \
        202602 202603 202604 202605 202606 202607 202608"
