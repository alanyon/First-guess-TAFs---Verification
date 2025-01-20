#!/bin/bash -l

module unload scitools
conda activate default_clone

ver_dates=20230805-20241225_ml
datadir=/data/users/alanyon/tafs/improver/verification/${ver_dates}
decode_dir=${datadir}/decodes

mkdir ${datadir}
mkdir ${decode_dir}
mkdir ${decode_dir}/Input_old
mkdir ${decode_dir}/Input_new_rf
mkdir ${decode_dir}/Input_new_xg
mkdir ${decode_dir}/Output_old
mkdir ${decode_dir}/Output_new_rf
mkdir ${decode_dir}/Output_new_xg

taf_files_old=${datadir}/tafs/*old.txt
taf_files_new_rf=${datadir}/tafs/*random*new.txt
taf_files_new_xg=${datadir}/tafs/*xg*new.txt

cat ${taf_files_old} > ${decode_dir}/Input_old/tafs.txt
cat ${taf_files_new_rf} > ${decode_dir}/Input_new_rf/tafs.txt
cat ${taf_files_new_xg} > ${decode_dir}/Input_new_xg/tafs.txt

python TAFDecode_tafs.py -i ${decode_dir}/Input_old -o ${decode_dir}/Output_old >${decode_dir}/decode_old.out 2>${decode_dir}/decode_old.err
python TAFDecode_tafs.py -i ${decode_dir}/Input_new_rf -o ${decode_dir}/Output_new_rf >${decode_dir}/decode_new_rf.out 2>${decode_dir}/decode_new_rf.err
python TAFDecode_tafs.py -i ${decode_dir}/Input_new_xg -o ${decode_dir}/Output_new_xg >${decode_dir}/decode_new_xg.out 2>${decode_dir}/decode_new_xg.err

taf_data_old=${decode_dir}/Output_old/acceptedTafs.csv
taf_decoded_data_old=${decode_dir}/Output_old/decodedTafs.csv

sqlite3 ${decode_dir}/test_old.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_old} taf_load
.import ${taf_decoded_data_old} taf_decoded_load
.read copy_data.sql
EOF

taf_data_new_rf=${decode_dir}/Output_new_rf/acceptedTafs.csv
taf_decoded_data_new_rf=${decode_dir}/Output_new_rf/decodedTafs.csv

sqlite3 ${decode_dir}/test_new_rf.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_new_rf} taf_load
.import ${taf_decoded_data_new_rf} taf_decoded_load
.read copy_data.sql
EOF

taf_data_new_xg=${decode_dir}/Output_new_xg/acceptedTafs.csv
taf_decoded_data_new_xg=${decode_dir}/Output_new_xg/decodedTafs.csv

sqlite3 ${decode_dir}/test_new_xg.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_new_xg} taf_load
.import ${taf_decoded_data_new_xg} taf_decoded_load
.read copy_data.sql
EOF

echo "Decoding complete"