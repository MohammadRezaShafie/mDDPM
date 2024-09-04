#!/bin/bash
# cli arguments: 
# 1. path to data directory
# 2. path to output directory
INPUT_DIR=$1
DATA_DIR=$2

# make the arguments mandatory and that the data dir is not a relative path
if [ -z "$INPUT_DIR" ] || [ -z "$DATA_DIR" ] 
then
  echo "Usage: ./prepare_mri.sh <input_dir> <output_dir>"
  exit 1
fi

if [ "$INPUT_DIR" == "." ] || [ "$INPUT_DIR" == ".." ]
then
  echo "Please use absolute paths for input_dir"
  exit 1
fi

echo "Resample"
mkdir -p $DATA_DIR/v1resampled/mri/t2
python resample.py -i $INPUT_DIR/t2 -o $DATA_DIR/v1resampled/mri/t2 -r 1.0 1.0 1.0 
# rename files for standard naming
for file in $DATA_DIR/v1resampled/mri/t2/*
do
  mv "$file" "${file%-T2.nii.gz}_t2.nii.gz"
done

echo "Generate masks"
CUDA_VISIBLE_DEVICES=0 hd-bet -i $DATA_DIR/v1resampled/mri/t2 -o $DATA_DIR/v2skullstripped/mri/t2 
python extract_masks.py -i $DATA_DIR/v2skullstripped/mri/t2 -o $DATA_DIR/v2skullstripped/mri/mask
python replace.py -i $DATA_DIR/v2skullstripped/mri/mask -s " _t2" ""

echo "Register t2"
python registration.py -i $DATA_DIR/v2skullstripped/mri/t2 -o $DATA_DIR/v3registered_non_iso/mri/t2 --modality=_t2 -trans Affine -templ sri_atlas/templates/T1_brain.nii

echo "Cut to brain"
python cut.py -i $DATA_DIR/v3registered_non_iso/mri/t2 -m $DATA_DIR/v3registered_non_iso/mri/mask/ -o $DATA_DIR/v3registered_non_iso_cut/mri/ -mode t2

echo "Bias Field Correction"
python n4filter.py -i $DATA_DIR/v3registered_non_iso_cut/mri/t2 -o $DATA_DIR/v4correctedN4_non_iso_cut/mri/t2 -m $DATA_DIR/v3registered_non_iso_cut/mri/mask

mkdir $DATA_DIR/v4correctedN4_non_iso_cut/mri/mask
cp $DATA_DIR/v3registered_non_iso_cut/mri/mask/* $DATA_DIR/v4correctedN4_non_iso_cut/mri/mask
echo "Done"

# now, you should copy the files in the output directory to the data directory of the project









