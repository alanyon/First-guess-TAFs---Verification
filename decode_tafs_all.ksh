#!/bin/bash -l

module unload scitools
conda activate default_clone

ver_dates=20230805-20241004_ml_2
datadir=/data/users/alanyon/tafs/improver/verification/${ver_dates}
decode_dir=${datadir}/decodes

mkdir ${datadir}
mkdir ${decode_dir}
mkdir ${decode_dir}/Input_all
mkdir ${decode_dir}/Output_all

taf_files_all=${datadir}/tafs/*all_old.txt

cat ${taf_files_all} > ${decode_dir}/Input_all/tafs.txt

python TAFDecode_tafs.py -i ${decode_dir}/Input_all -o ${decode_dir}/Output_all >${decode_dir}/decode_all.out 2>${decode_dir}/decode_all.err

taf_data_all=${decode_dir}/Output_all/acceptedTafs.csv
taf_decoded_data_all=${decode_dir}/Output_all/decodedTafs.csv

sqlite3 ${decode_dir}/test_all.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_all} taf_load
.import ${taf_decoded_data_all} taf_decoded_load
.read copy_data.sql
EOF

echo "Decoding complete"