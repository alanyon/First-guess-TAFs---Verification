#!/bin/bash -l

# Load in constants 
source ../standard_verification/setup_constants.sh

# Activate conda environment
conda activate default_clone

export PYTHONPATH=$PYTHONPATH:~andre.lanyon/python 
export PYTHONPATH=$PYTHONPATH:/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/taf_monitor

python verify_busts.py no > output.txt 2>&1 &