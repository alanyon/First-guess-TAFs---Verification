#!/bin/bash -l

module unload scitools
conda activate default_clone

ver_dates=20230805-20250104
datadir=/data/users/alanyon/tafs/verification/imp_vs_bd_${ver_dates}
decode_dir=${datadir}/decodes

mkdir ${datadir}
mkdir ${decode_dir}
mkdir ${decode_dir}/Input_bd
mkdir ${decode_dir}/Input_im
mkdir ${decode_dir}/Output_bd
mkdir ${decode_dir}/Output_im

taf_files_bd=/data/users/alanyon/tafs/ml/verification/${ver_dates}/tafs/*txt
taf_files_im=/data/users/alanyon/tafs/improver/verification/${ver_dates}_ml/tafs/*txt

cat ${taf_files_bd} > ${decode_dir}/Input_bd/tafs.txt
cat ${taf_files_im} > ${decode_dir}/Input_im/tafs.txt

python TAFDecode_tafs.py -i ${decode_dir}/Input_bd -o ${decode_dir}/Output_bd >${decode_dir}/decode_bd.out 2>${decode_dir}/decode_bd.err
python TAFDecode_tafs.py -i ${decode_dir}/Input_im -o ${decode_dir}/Output_im >${decode_dir}/decode_im.out 2>${decode_dir}/decode_im.err

taf_data_bd=${decode_dir}/Output_bd/acceptedTafs.csv
taf_decoded_data_bd=${decode_dir}/Output_bd/decodedTafs.csv

sqlite3 ${decode_dir}/test_bd.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_bd} taf_load
.import ${taf_decoded_data_bd} taf_decoded_load
.read copy_data.sql
EOF

taf_data_im=${decode_dir}/Output_im/acceptedTafs.csv
taf_decoded_data_im=${decode_dir}/Output_im/decodedTafs.csv

sqlite3 ${decode_dir}/test_im.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_im} taf_load
.import ${taf_decoded_data_im} taf_decoded_load
.read copy_data.sql
EOF
