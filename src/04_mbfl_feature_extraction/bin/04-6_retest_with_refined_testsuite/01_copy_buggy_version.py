#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import csv
import pandas as pd
import sys

# Current working directory
script_path = Path(__file__).resolve()
refine_testsuite_dir = script_path.parent
bin_dir = refine_testsuite_dir.parent
mbfl_feature_extraction_dir = bin_dir.parent

# General directories
src_dir = mbfl_feature_extraction_dir.parent
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
ccts_txt = 'ccts.txt'
excluded_failing_txt = 'excluded_failing_tcs.txt'
excluded_passing_txt = 'excluded_passing_tcs.txt'
excluded_txt = 'excluded_tcs.txt'
additional_failing_txt = 'additional_failing_tcs.txt'


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.mbfl_set_name, args.rank_summary_file_name)


def start_process(subject_name, mbfl_set_name, rank_summary_file_name):
    global configure_json_file

    subject_working_dir = mbfl_feature_extraction_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    mbfl_features_per_bug = get_buggy_versions(subject_working_dir, mbfl_set_name)

    # 1. save buggy versions to copy
    retest_buggy_versions = get_retesting_buggy_versions(subject_working_dir, rank_summary_file_name)

    copy_bug_version202_select_usable_buggy_versions(configs, subject_working_dir, mbfl_set_name, retest_buggy_versions)

    print(f"\nRetesting buggy versions: {len(retest_buggy_versions)}")

def copy_bug_version202_select_usable_buggy_versions(configs, subject_working_dir, mbfl_set_name, retest_buggy_versions):
    global src_dir
    select_usable_buggy_versions_dir = src_dir / '02_select_usable_buggy_versions'
    assert select_usable_buggy_versions_dir.exists(), f"Select usable buggy versions directory {select_usable_buggy_versions_dir} does not exist"

    select_working_dir = select_usable_buggy_versions_dir / f"{configs['subject_name']}-working_directory"
    assert select_working_dir.exists(), f"Select usable buggy versions working directory {select_working_dir} does not exist"

    mkdir_cmd = f"mkdir -p {select_working_dir / mbfl_set_name}"
    sp.run(mkdir_cmd, shell=True)

    for buggy_version in retest_buggy_versions:
        buggy_version_dir = subject_working_dir / mbfl_set_name / buggy_version
        assert buggy_version_dir.exists(), f"Buggy version directory {buggy_version_dir} does not exist"

        copy_cmd = f"cp -r {buggy_version_dir} {select_working_dir / mbfl_set_name}"
        sp.run(copy_cmd, shell=True)


def get_retesting_buggy_versions(subject_working_dir, rank_summary_file_name):
    retest_buggy_versions_list = []

    mbfl_feature_summary_file = subject_working_dir / rank_summary_file_name
    with mbfl_feature_summary_file.open('r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            failing_tcs = int(row['# of failing tcs'])
            excluded_failing_tcs = int(row['# of excluded failing tcs'])
            # additional_failing_tcs = int(row['# of additional failing tcs'])

            if (failing_tcs + excluded_failing_tcs) < 500:
                retest_buggy_versions_list.append(row['bug_name'])
    
    return retest_buggy_versions_list



def custome_sort(tc_script):
    tc_filename = tc_script.split('.')[0]
    return int(tc_filename[2:])

def get_tcs(version_dir, tc_file):
    testsuite_info_dir = version_dir / 'testsuite_info'
    assert testsuite_info_dir.exists(), f"Testsuite info directory {testsuite_info_dir} does not exist"

    tc_file_txt = testsuite_info_dir / tc_file
    if not tc_file_txt.exists():
        return []

    tcs_list = []

    with open(tc_file_txt, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            tcs_list.append(line)
        
    tcs_list = sorted(tcs_list, key=custome_sort)

    return tcs_list



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
    parser.add_argument('--mbfl-set-name', type=str, help='MBFL set name', required=True)
    parser.add_argument('--rank-summary-file-name', type=str, help='Rank summary file name', required=True)
    return parser
    


if __name__ == "__main__":
    main()