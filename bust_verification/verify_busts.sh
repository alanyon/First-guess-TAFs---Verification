#!/bin/bash -l
#
# Orchestrator for the parallel TAF bust verification.
#
# Splits the (previously single, very long) SPICE job into NUM_CHUNKS
# independent worker tasks that each process a subset of the verification
# days, followed by a single merge task that combines their results and
# produces the plots.
#
# Run this directly with bash (NOT sbatch):
#     ./verify_busts.sh
# or:
#     bash verify_busts.sh
#
set -euo pipefail

BASE=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification

# Total worker chunks. At most five run concurrently to limit MetDB load.
# The worker array size is derived from this value.
export NUM_CHUNKS=${NUM_CHUNKS:-15}
LAST_IDX=$((NUM_CHUNKS - 1))

# Verification period (full or recent); see setup_constants.sh
export VERIF_PERIOD=${VERIF_PERIOD:-full}
LOGS="${BASE}/logs"

# Make sure the log directory exists (sbatch will not create it)
mkdir -p "${LOGS}"

cd "${BASE}"

# Submit the worker array job (one array task per chunk)
ARRAY_JID=$(sbatch --parsable \
    --array=0-"${LAST_IDX}"%5 \
    --export=ALL,NUM_CHUNKS="${NUM_CHUNKS}" \
    --output="${LOGS}/worker_${VERIF_PERIOD}_%a.out" \
    --error="${LOGS}/worker_${VERIF_PERIOD}_%a.err" \
    "${BASE}/verify_busts_worker.sh")
echo "Submitted ${VERIF_PERIOD} worker array job ${ARRAY_JID} with ${NUM_CHUNKS} chunks"

# Submit the merge job, dependent on ALL workers finishing successfully
MERGE_JID=$(sbatch --parsable \
    --dependency=afterok:"${ARRAY_JID}" \
    --export=ALL,NUM_CHUNKS="${NUM_CHUNKS}" \
    --output="${LOGS}/merge_${VERIF_PERIOD}.out" \
    --error="${LOGS}/merge_${VERIF_PERIOD}.err" \
    "${BASE}/verify_busts_merge.sh")
echo "Submitted merge job ${MERGE_JID} (runs after ${ARRAY_JID} succeeds)"