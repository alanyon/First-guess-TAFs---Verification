#!/bin/bash -l
#SBATCH --partition=cpu
#SBATCH --mem=32G
#SBATCH --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/logs/merge.out
#SBATCH --error=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/logs/merge.err

# With NUM_CHUNKS exported by verify_busts.sh, merge worker results and
# produce plots. Without NUM_CHUNKS, or with the 'plots' argument,
# regenerate plots and spreadsheets from the saved merged results.

# Load in constants
source ../standard_verification/setup_constants.sh

# Activate conda environment
conda activate default_clone_may_2026

export PYTHONPATH=$PYTHONPATH:~andre.lanyon/python
export PYTHONPATH=$PYTHONPATH:/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/taf_monitor

if [[ "${1:-}" == "plots" || -z "${NUM_CHUNKS:-}" ]]; then
	python verify_busts.py no
else
	python verify_busts.py merge "${NUM_CHUNKS}"
fi
