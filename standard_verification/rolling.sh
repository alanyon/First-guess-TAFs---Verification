#!/bin/bash

export DATA_DIR=/data/users/andre.lanyon/tafs/verification/current
export STATS_DIR=${DATA_DIR}/stats
export TAF_TYPES="opt_no_obs_ml opt_no_obs opt_obs_update_1_ml opt_obs_update_1 \
                  opt_obs_update_2_ml opt_obs_update_2 pes_no_obs_ml pes_no_obs \
                  pes_obs_update_1_ml pes_obs_update_1 pes_obs_update_2_ml pes_obs_update_2 \
                  manual"
export TAF_TYPES_SHORT="o1 o2 o3 o4 o5 o6 p1 p2 p3 p4 p5 p6 ma"
export CYCLE_DATE=20260522
export PYTHONPATH=~clare.bysouth/VerPy/stable
export ORACLE_OWNER=oracle
export ORACLE_BASE=/usr/lib/oracle/23/client64
export TNS_ADMIN=~andre.lanyon/oracle
export ORACLE_TERM=xterm
export ORACLE_HOME=/usr/lib/oracle/23/client64
export SHLIB_PATH=/usr/lib/oracle/23/client64/lib
export PATH=$PATH:/usr/lib/oracle/23/client64/bin

module load scitools/production-os46-3

python rolling.py
