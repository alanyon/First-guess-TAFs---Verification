#!/bin/bash -l
#SBATCH --partition=cpu
#SBATCH --mem=8G
#SBATCH --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/logs/merge.out
#SBATCH --error=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification/logs/merge.err

# Merge job: combines the pickled holders produced by every worker chunk
# into a single set of holders and produces the plots. NUM_CHUNKS is
# exported by the submitter (verify_busts.sh).

# Load in constants
source ../standard_verification/setup_constants.sh

# Activate conda environment
conda activate default_clone_may_2026

export PYTHONPATH=$PYTHONPATH:~andre.lanyon/python
export PYTHONPATH=$PYTHONPATH:/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/taf_monitor

python verify_busts.py merge "${NUM_CHUNKS}"
