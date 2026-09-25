#!/bin/bash -l
#SBATCH --partition=cpu
#SBATCH --mem=8G
#SBATCH --ntasks=1
#SBATCH --time=60
#SBATCH --output=logs/plots_%j.out
#SBATCH --error=logs/plots_%j.err

# ---------------------------------------------------------------------------
# Final stage of the pipeline. Runs once, after every station array task has
# finished successfully (enforced by submit_verify.sh via --dependency).
#
#   1. merge_stats.py  - concatenates all per-station CSVs into the combined
#                        CSVs (single serial writer => no race conditions).
#   2. plot_stats.py   - produces the comparison plots.
# ---------------------------------------------------------------------------

source setup_constants.sh
module load scitools/production-os48-1

# Combine per-station stats into the combined CSVs used for plotting
python merge_stats.py

# Make plots
module unload scitools
conda activate default_clone_may_2026
python plot_stats.py
conda deactivate

exit 0
