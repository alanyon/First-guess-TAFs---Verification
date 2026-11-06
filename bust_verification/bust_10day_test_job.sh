#!/bin/bash -l
#SBATCH --partition=cpu-long
#SBATCH --mem=8G
#SBATCH --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --output=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/logs/bust_10day_test.out
#SBATCH --error=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/logs/bust_10day_test.err

source /home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/standard_verification/setup_constants.sh

conda activate default_clone_may_2026

export PYTHONPATH=$PYTHONPATH:~andre.lanyon/python
export PYTHONPATH=$PYTHONPATH:/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/taf_monitor

cd /home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification
python -u bust_10day_test.py
