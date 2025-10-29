#!/bin/bash -l

# Load in constants 
source setup_constants.sh

# Activate conda environment
conda activate default_clone

# Make decode directorY if necessary
if [ ! -d "${DECODE_DIR}" ]; then
    mkdir "${DECODE_DIR}"
fi

# Loop through all taf types
for taf_type in ${TAF_TYPES}; do

    # Ignore Manual taf type
    if [[ "${taf_type}" == *"Manual"* ]]; then
        continue
    fi

    # Make directories if necessary
    if [ ! -d "${DECODE_DIR}/Input_${taf_type}" ]; then
        mkdir "${DECODE_DIR}/Input_${taf_type}"
    fi
    if [ ! -d "${DECODE_DIR}/Output_${taf_type}" ]; then
        mkdir "${DECODE_DIR}/Output_${taf_type}"
    fi

    # Inport TAFs
    taf_files="${DATA_DIR}/tafs/*${taf_type}.txt"
    cat ${taf_files} > ${DECODE_DIR}/Input_${taf_type}/tafs.txt

    # Convert TAFs into correct format and save to output directory
    python TAFDecode_tafs.py -i "${DECODE_DIR}/Input_${taf_type}" \
                             -o "${DECODE_DIR}/Output_${taf_type}" \
                             >"${DECODE_DIR}/decode_${taf_type}.out" \
                             2>"${DECODE_DIR}/decode_${taf_type}.err"

    # Create sql database
    taf_data="${DECODE_DIR}/Output_${taf_type}/acceptedTafs.csv"
    taf_decoded_data="${DECODE_DIR}/Output_${taf_type}/decodedTafs.csv"

    sqlite3 "${DECODE_DIR}/${taf_type}.db" <<EOF
.read create_tables.sql
.separator ","
.import "${taf_data}" taf_load
.import "${taf_decoded_data}" taf_decoded_load
.read copy_data.sql
EOF

done

# Deactivate conda environment
conda deactivate