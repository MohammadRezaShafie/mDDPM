import os
import sys
import subprocess
import shutil

def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        sys.exit(1)

def main(input_dir, data_dir):
    # Check if the arguments are provided
    if not input_dir or not data_dir:
        print("Usage: python prepare_mri.py <input_dir> <output_dir>")
        sys.exit(1)

    # Check if the input directory is not a relative path
    if input_dir == "." or input_dir == "..":
        print("Please use absolute paths for input_dir")
        sys.exit(1)

    # Step 1: Resample
    print("Resample")
    os.makedirs(os.path.join(data_dir, 'v1resampled/mri/t2'), exist_ok=True)
    run_command(f"python resample.py -i {input_dir} -o {data_dir}/v1resampled/mri/t2 -r 1.0 1.0 1.0")

    # Step 2: Rename files for standard naming
    resampled_dir = os.path.join(data_dir, 'v1resampled/mri/t2')
    for file_name in os.listdir(resampled_dir):
        if file_name.endswith('-T2.nii.gz'):
            src_file = os.path.join(resampled_dir, file_name)
            dst_file = os.path.join(resampled_dir, file_name.replace('-T2.nii.gz', '_t2.nii.gz'))
            os.rename(src_file, dst_file)

    # Step 3: Generate masks
    print("Generate masks")
    run_command(f"CUDA_VISIBLE_DEVICES=0 hd-bet -i {data_dir}/v1resampled/mri/t2 -o {data_dir}/v2skullstripped/mri/t2")
    run_command(f"python extract_masks.py -i {data_dir}/v2skullstripped/mri/t2 -o {data_dir}/v2skullstripped/mri/mask")
    run_command(f"python replace.py -i {data_dir}/v2skullstripped/mri/mask -s ' _t2' ''")

    # Step 4: Register t2
    print("Register t2")
    run_command(f"python registration.py -i {data_dir}/v2skullstripped/mri/t2 -o {data_dir}/v3registered_non_iso/mri/t2 "
                f"--modality=_t2 -trans Affine -templ sri_atlas/templates/T1_brain.nii")

    # Step 5: Cut to brain
    print("Cut to brain")
    run_command(f"python cut.py -i {data_dir}/v3registered_non_iso/mri/t2 -m {data_dir}/v3registered_non_iso/mri/mask/ "
                f"-o {data_dir}/v3registered_non_iso_cut/mri/ -mode t2")

    # Step 6: Bias Field Correction
    print("Bias Field Correction")
    run_command(f"python n4filter.py -i {data_dir}/v3registered_non_iso_cut/mri/t2 -o {data_dir}/v4correctedN4_non_iso_cut/mri/t2 "
                f"-m {data_dir}/v3registered_non_iso_cut/mri/mask")

    # Step 7: Copy mask files
    mask_dir_v3 = os.path.join(data_dir, 'v3registered_non_iso_cut/mri/mask')
    mask_dir_v4 = os.path.join(data_dir, 'v4correctedN4_non_iso_cut/mri/mask')
    os.makedirs(mask_dir_v4, exist_ok=True)
    for mask_file in os.listdir(mask_dir_v3):
        shutil.copy(os.path.join(mask_dir_v3, mask_file), mask_dir_v4)

    print("Done")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python prepare_mri.py <input_dir> <output_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    data_dir = sys.argv[2]

    main(input_dir, data_dir)
