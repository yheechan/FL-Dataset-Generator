#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import csv

# Current working directory
script_path = Path(__file__).resolve()
sbfl_dataset_dir = script_path.parent
bin_dir = sbfl_dataset_dir.parent
sbfl_feature_extraction_dir = bin_dir.parent

# General directories
src_dir = sbfl_feature_extraction_dir.parent
root_dir = src_dir.parent
user_configs_dir = root_dir / 'user_configs'
subjects_dir = root_dir / 'subjects'
external_tools_dir = root_dir / 'external_tools'

# keywords in configurations.json
config_sh_wd_key = 'configure_script_working_directory'
build_sh_wd_key = 'build_script_working_directory'

# files in user_configs_dir
configure_no_cov_script = 'configure_no_cov_script.sh'
configure_yes_cov_script = 'configure_yes_cov_script.sh'
build_script = 'build_script.sh'
clean_script = 'clean_script.sh'
machines_json_file = 'machines.json'
configure_json_file = 'configurations.json'
use_distributed_machines = 'use_distributed_machines'
copy_real_world_buggy_versions = 'copy_real_world_buggy_versions'

# file names
failing_txt = 'failing_tcs.txt'
passing_txt = 'passing_tcs.txt'


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)


def start_process(subject_name):
    global configure_json_file

    subject_working_dir = sbfl_feature_extraction_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    sbfl_features_per_bug = get_buggy_versions(subject_working_dir, "sbfl_features")

    # 3. VALIDATE: 01 - Check sbfl_features.csv files exist
    validate_01(sbfl_features_per_bug)


def validate_01(sbfl_features_per_bug):
    for bug_dir in sbfl_features_per_bug:
        bug_name = bug_dir.name
        print(f"Validating bug {bug_name}")

        # GET: mbfl_features.csv
        mbfl_features_csv_file = bug_dir / 'sbfl_features.csv'
        assert mbfl_features_csv_file.exists(), f"MBFL features file {mbfl_features_csv_file} does not exist"
    
    print(f"All {len(sbfl_features_per_bug)} bugs have been validated successfully")


# def validate_02(mbfl_features_csv_file):

#     with open(mbfl_features_csv_file, 'r') as f:
#         reader = csv.DictReader(f)

#         buggy_line_cnt = 0
#         for row in reader:
#             bug_stat = int(row['bug'])
#             if bug_stat == 1:
#                 buggy_line_cnt += 1
        
#         assert buggy_line_cnt == 1, f"buggy line count: {buggy_line_cnt} != 1"

def get_buggy_versions(subject_working_dir, versions_set_name):
    buggy_versions_dir = subject_working_dir / versions_set_name
    assert buggy_versions_dir.exists(), f"Buggy versions directory {buggy_versions_dir} does not exist"

    buggy_versions = []
    for buggy_version in buggy_versions_dir.iterdir():
        if buggy_version.is_dir():
            buggy_versions.append(buggy_version)

    return buggy_versions



def read_configs(subject_name, subject_working_dir):
    global configure_json_file

    subject_config_dir = subject_working_dir / f"{subject_name}-configures"
    assert subject_config_dir.exists(), f"Subject configurations directory {subject_config_dir} does not exist"

    config_json = subject_config_dir / configure_json_file
    assert config_json.exists(), f"Configurations file {config_json} does not exist"
    
    configs = None
    with config_json.open() as f:
        configs = json.load(f)
    
    if configs is None:
        raise Exception('Configurations are not loaded')
    
    return configs


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser
    


if __name__ == "__main__":
    main()