#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import random

# Current working directory
script_path = Path(__file__).resolve()
analyze_buggy_versions = script_path.parent
bin_dir = analyze_buggy_versions.parent
select_usable_buggy_versions_dir = bin_dir.parent

# General directories
src_dir = select_usable_buggy_versions_dir.parent
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
excluded_failing_txt = 'excluded_failing_tcs.txt'
excluded_passing_txt = 'excluded_passing_tcs.txt'
excluded_txt = 'excluded_tcs.txt'


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.versions_set_name)


def start_process(subject_name, versions_set_name):
    global configure_json_file

    subject_working_dir = select_usable_buggy_versions_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    select_appropriate_versions(configs, subject_working_dir, versions_set_name)


def select_appropriate_versions(configs, subject_working_dir, versions_set_name):
    target_buggy_version_dir = subject_working_dir / versions_set_name
    assert target_buggy_version_dir.exists(), f"Usable buggy versions directory {target_buggy_version_dir} does not exist"

    # 1. get usable buggy versions
    buggy_version_list = get_usable_buggy_versions(target_buggy_version_dir)

    # 2. initiate reduced_usable_buggy_versions directory
    appr_buggy_version_dir = subject_working_dir / f"{versions_set_name}-appropriate"
    if not appr_buggy_version_dir.exists():
        appr_buggy_version_dir.mkdir()

    included_buggy_version_cnt = 0
    excluded_buggy_version_cnt = 0

    # 5. reduce test suite of each buggy version
    for buggy_version in buggy_version_list:
        buggy_version_name = buggy_version.name
        print(f"Select? {buggy_version_name}")

        buggy_version_dir = target_buggy_version_dir / buggy_version_name
        assert buggy_version_dir.exists(), f"Reduced buggy version {buggy_version_dir} does not exist"


        # get test cases directory position
        testsuite_dir = buggy_version_dir / 'testsuite_info'
        assert testsuite_dir.exists(), f"Test suite directory {testsuite_dir} does not exist"

        # get test cases file position
        failing_tcs = testsuite_dir / failing_txt
        passing_tcs = testsuite_dir / passing_txt
        assert failing_tcs.exists(), f"Failing test cases file {failing_tcs} does not exist"
        assert passing_tcs.exists(), f"Passing test cases file {passing_tcs} does not exist"

        excluded_failing_tcs = testsuite_dir / excluded_failing_txt
        excluded_passing_tcs = testsuite_dir / excluded_passing_txt
        excluded_tcs = testsuite_dir / excluded_txt
        assert excluded_failing_tcs.exists(), f"Excluded failing test cases file {excluded_failing_tcs} does not exist"
        assert excluded_passing_tcs.exists(), f"Excluded passing test cases file {excluded_passing_tcs} does not exist"
        assert excluded_tcs.exists(), f"Excluded test cases file {excluded_tcs} does not exist"

        # get test cases
        failing_tc_set = get_test_cases(failing_tcs)
        passing_tc_set = get_test_cases(passing_tcs)
        excluded_failing_tc_set = get_test_cases(excluded_failing_tcs)
        excluded_passing_tc_set = get_test_cases(excluded_passing_tcs)
        excluded_tc_set = get_test_cases(excluded_tcs)

        total_failing_tcs = failing_tc_set.union(excluded_failing_tc_set)

        if len(total_failing_tcs) < 500:
            # copy buggy version to reduced_usable_buggy_versions directory
            sp.run(['cp', '-r', buggy_version, appr_buggy_version_dir])
            included_buggy_version_cnt += 1
        else:
            excluded_buggy_version_cnt += 1
    
    print(f"Number of buggy versions included: {included_buggy_version_cnt}")
    print(f"Number of buggy versions excluded: {excluded_buggy_version_cnt}")

def custome_sort(tc_script):
    tc_name = tc_script.split('.')[0]
    return (int(tc_name[2:]))


def get_test_cases(test_case_file):
    if not test_case_file.exists():
        return []
    
    test_cases_list = []
    with open(test_case_file, 'r') as f:
        for line in f:
            test_cases_list.append(line.strip())
    sorted_tc_list = sorted(test_cases_list, key=custome_sort)
    test_cases = set(sorted_tc_list)
    return test_cases




def get_usable_buggy_versions(usable_buggy_versions_dir):
    buggy_versions_list = []
    for buggy_version in usable_buggy_versions_dir.iterdir():
        if buggy_version.is_dir():
            buggy_versions_list.append(buggy_version)
    print(f"Number of usable buggy versions: {len(buggy_versions_list)}")
    return buggy_versions_list


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
    parser.add_argument('--versions-set-name', type=str, help='Name of buggy versions set to analyze', required=True)
    return parser
    


if __name__ == "__main__":
    main()