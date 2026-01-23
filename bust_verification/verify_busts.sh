#!/bin/bash -l
#SBATCH --partition=cpu-long
#SBATCH --mem=16G
#SBATCH --ntasks=4
#SBATCH --output=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/test.out
#SBATCH --time=3000
#SBATCH --error=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/test.err

# Load in constants 
source ../standard_verification/setup_constants.sh

# Activate conda environment
conda activate default_clone

export PYTHONPATH=$PYTHONPATH:~andre.lanyon/python 
export PYTHONPATH=$PYTHONPATH:/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/taf_monitor

python verify_busts.py no