#!/bin/bash -l

conda activate default_clone

ver_dates=20230805-20250304
datadir=/data/users/andre.lanyon/tafs/verification/${ver_dates}_test
decode_dir=${datadir}/decodes

mkdir ${decode_dir}
mkdir ${decode_dir}/Input_im_no_obs_opt
mkdir ${decode_dir}/Input_im_no_obs_pes
mkdir ${decode_dir}/Input_im_obs_opt
mkdir ${decode_dir}/Input_im_obs_pes
mkdir ${decode_dir}/Output_im_no_obs_opt
mkdir ${decode_dir}/Output_im_no_obs_pes
mkdir ${decode_dir}/Output_im_obs_opt
mkdir ${decode_dir}/Output_im_obs_pes

taf_files_im_no_obs_opt=${datadir}/tafs/*no_opt.txt
taf_files_im_no_obs_pes=${datadir}/tafs/*no_pes.txt
taf_files_im_obs_opt=${datadir}/tafs/*2_opt.txt
taf_files_im_obs_pes=${datadir}/tafs/*2_pes.txt

cat ${taf_files_im_no_obs_opt} > ${decode_dir}/Input_im_no_obs_opt/tafs.txt
cat ${taf_files_im_no_obs_pes} > ${decode_dir}/Input_im_no_obs_pes/tafs.txt
cat ${taf_files_im_obs_opt} > ${decode_dir}/Input_im_obs_opt/tafs.txt
cat ${taf_files_im_obs_pes} > ${decode_dir}/Input_im_obs_pes/tafs.txt

python TAFDecode_tafs.py -i ${decode_dir}/Input_im_no_obs_opt -o ${decode_dir}/Output_im_no_obs_opt >${decode_dir}/decode_im_no_obs_opt.out 2>${decode_dir}/decode_im_no_obs_opt.err
python TAFDecode_tafs.py -i ${decode_dir}/Input_im_no_obs_pes -o ${decode_dir}/Output_im_no_obs_pes >${decode_dir}/decode_im_no_obs_pes.out 2>${decode_dir}/decode_im_no_obs_pes.err
python TAFDecode_tafs.py -i ${decode_dir}/Input_im_obs_opt -o ${decode_dir}/Output_im_obs_opt >${decode_dir}/decode_im_obs_opt.out 2>${decode_dir}/decode_im_obs_opt.err
python TAFDecode_tafs.py -i ${decode_dir}/Input_im_obs_pes -o ${decode_dir}/Output_im_obs_pes >${decode_dir}/decode_im_obs_pes.out 2>${decode_dir}/decode_im_obs_pes.err

taf_data_im_no_obs_opt=${decode_dir}/Output_im_no_obs_opt/acceptedTafs.csv
taf_decoded_data_im_no_obs_opt=${decode_dir}/Output_im_no_obs_opt/decodedTafs.csv

sqlite3 ${decode_dir}/im_no_obs_opt.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_im_no_obs_opt} taf_load
.import ${taf_decoded_data_im_no_obs_opt} taf_decoded_load
.read copy_data.sql
EOF

taf_data_im_no_obs_pes=${decode_dir}/Output_im_no_obs_pes/acceptedTafs.csv
taf_decoded_data_im_no_obs_pes=${decode_dir}/Output_im_no_obs_pes/decodedTafs.csv

sqlite3 ${decode_dir}/im_no_obs_pes.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_im_no_obs_opt} taf_load
.import ${taf_decoded_data_im_no_obs_pes} taf_decoded_load
.read copy_data.sql
EOF

taf_data_im_obs_opt=${decode_dir}/Output_im_obs_opt/acceptedTafs.csv
taf_decoded_data_im_obs_opt=${decode_dir}/Output_im_obs_opt/decodedTafs.csv

sqlite3 ${decode_dir}/im_obs_opt.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_im_obs_opt} taf_load
.import ${taf_decoded_data_im_obs_opt} taf_decoded_load
.read copy_data.sql
EOF

taf_data_im_obs_pes=${decode_dir}/Output_im_obs_pes/acceptedTafs.csv
taf_decoded_data_im_obs_pes=${decode_dir}/Output_im_obs_pes/decodedTafs.csv

sqlite3 ${decode_dir}/im_obs_pes.db <<EOF
.read create_tables.sql
.separator ","
.import ${taf_data_im_obs_pes} taf_load
.import ${taf_decoded_data_im_obs_pes} taf_decoded_load
.read copy_data.sql
EOF
