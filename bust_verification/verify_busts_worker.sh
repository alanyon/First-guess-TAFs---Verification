#!/bin/bash -l
#SBATCH --partition=cpu-long
#SBATCH --mem=8G
#SBATCH --ntasks=1
#SBATCH --time=12:00:00
#SBATCH --output=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/logs/worker_%a.out
#SBATCH --error=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/logs/worker_%a.err

# Worker job: processes one chunk of the verification days. The array
# index (SLURM_ARRAY_TASK_ID) selects the chunk and NUM_CHUNKS (exported
# by the submitter) gives the total number of chunks. The --array range
# is supplied on the sbatch command line by verify_busts.sh.

# Load in constants
source ../standard_verification/setup_constants.sh

# Activate conda environment
conda activate default_clone_may_2026

export PYTHONPATH=$PYTHONPATH:~andre.lanyon/python
export PYTHONPATH=$PYTHONPATH:/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/taf_monitor

python verify_busts.py worker "${SLURM_ARRAY_TASK_ID}" "${NUM_CHUNKS}"
