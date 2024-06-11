#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import random
from copy import deepcopy

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
excluded_txt = 'excluded_tcs.txt'


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.versions_set_name, args.testsuite_size)


def start_process(subject_name, versions_set_name, testsuite_size):
    global configure_json_file

    subject_working_dir = select_usable_buggy_versions_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    analyze_and_reduce(configs, subject_working_dir, versions_set_name, testsuite_size)


def analyze_and_reduce(configs, subject_working_dir, versions_set_name, testsuite_size):
    usable_buggy_versions_dir = subject_working_dir / versions_set_name
    assert usable_buggy_versions_dir.exists(), f"Usable buggy versions directory {usable_buggy_versions_dir} does not exist"

    # 1. get usable buggy versions
    buggy_version_list = get_usable_buggy_versions(usable_buggy_versions_dir)

    total_testsuite = set()
    failing_set = set()
    passing_set = set()

    keep_set = set()


    total_buggy_versions = len(buggy_version_list)

    # 2. accumulate test cases
    for buggy_version in buggy_version_list:
        keep = 0
        buggy_version_name = buggy_version.name
        print(f"Analyzing {buggy_version_name}")

        # or make it say not contain MUT
        if 'issue' in buggy_version_name:
            keep = 1

        # get test cases directory position
        testsuite_dir = buggy_version / 'testsuite_info'
        assert testsuite_dir.exists(), f"Test suite directory {testsuite_dir} does not exist"

        # get test cases file position
        failing_tcs = testsuite_dir / failing_txt
        passing_tcs = testsuite_dir / passing_txt
        assert failing_tcs.exists(), f"Failing test cases file {failing_tcs} does not exist"
        assert passing_tcs.exists(), f"Passing test cases file {passing_tcs} does not exist"

        # get test cases
        failing_tcs_list = get_test_cases(failing_tcs)
        passing_tcs_list = get_test_cases(passing_tcs)


        # make failing test cases set
        failing_set.update(failing_tcs_list)
        passing_set.update(passing_tcs_list)

        if keep == 1:
            keep_set.update(failing_tcs_list)

        total_testsuite.update(failing_tcs_list)
        total_testsuite.update(passing_tcs_list)
    
    # remove testcase in passing_set that exists in failing_set
    passing_set = passing_set - failing_set
    failing_set = failing_set - keep_set

    # print statistics
    print(f"\n\nTotal # of buggy versions: {len(buggy_version_list)}")
    print(f"Total # of test cases: {len(total_testsuite)}")

    print(f"\n# of failing test cases: {len(failing_set)}")
    print(f"# of passing test cases: {len(passing_set)}")

    print(f"\n# of keep test cases: {len(keep_set)}")

    select_reduced_testsuite(failing_set, passing_set, keep_set, testsuite_size, subject_working_dir)


def select_reduced_testsuite(failing_set, passing_set, keep_set, testsuite_size, subject_working_dir):
    excluded_tc_list = []

    # 1. get failing test cases
    failing_test_cases = list(failing_set)

    # 2. get passing test cases
    passing_test_cases = list(passing_set)

    # 3. get keep test cases
    reduced_test_suite = []
    # assert no tc in keep is in failing
    keep_test_cases = list(keep_set)
    # add keep set to reduced_test_suite
    reduced_test_suite = deepcopy(keep_test_cases)

    # 3. randomly select test cases
    random.shuffle(failing_test_cases)
    random.shuffle(passing_test_cases)


    # 4. select test cases the amount of testsuite_size
    while len(reduced_test_suite) < testsuite_size:
        if len(failing_test_cases) > 0:
            tc = failing_test_cases.pop()
            reduced_test_suite.append(tc)
        elif len(passing_test_cases) > 0:
            tc = passing_test_cases.pop()
            reduced_test_suite.append(tc)

    # 5. get excluded test cases
    excluded_tc_list = failing_test_cases + passing_test_cases

    # 5. save reduced test suite
    reduced_test_suite_file = subject_working_dir / 'reduced_test_suite.txt'
    with open(reduced_test_suite_file, 'w') as f:
        reduced_test_suite = sorted(reduced_test_suite, key=custome_sort)
        content = '\n'.join(reduced_test_suite)
        f.write(content)
    
    # 6. save excluded test cases
    excluded_test_suite_file = subject_working_dir / 'excluded_test_suite.txt'
    with open(excluded_test_suite_file, 'w') as f:
        excluded_tc_list = sorted(excluded_tc_list, key=custome_sort)
        content = '\n'.join(excluded_tc_list)
        f.write(content)

    print(f"\n\n>>>>> REDUCED RESULTS <<<<<")
    print(f"Reduced test suite size: {len(reduced_test_suite)}")
    print(f"\tExcluded Failing test cases: {len(failing_test_cases)}")
    print(f"\tExcluded passing test cases: {len(passing_test_cases)}")
    print(f"Excluded test suite size: {len(excluded_tc_list)}")


def custome_sort(tc_script):
    tc_name = tc_script.split('.')[0]
    return (int(tc_name[2:]))


def get_test_cases(test_case_file):
    test_cases = []
    with open(test_case_file, 'r') as f:
        for line in f:
            test_cases.append(line.strip())
    test_cases = sorted(test_cases, key=custome_sort)
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
    parser.add_argument('--testsuite-size', type=int, help='Size expected reduced test suite', required=True)
    return parser
    


if __name__ == "__main__":
    main()