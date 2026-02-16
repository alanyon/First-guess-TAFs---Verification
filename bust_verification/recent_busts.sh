#!/bin/bash -l

# Activate conda environment
conda activate default_clone_nov_2025

export PYTHONPATH=$PYTHONPATH:/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/taf_monitor
export CYCLE_TIME=2026020900
export OUTDIR=/home/users/andre.lanyon/public_html/tafs
export DATA_DIR=/data/users/andre.lanyon/tafs/recent_busts

python recent_busts.py

conda deactivate
