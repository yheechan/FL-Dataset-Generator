#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp

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
    start_process(args.subject, args.versions_set_name, args.output_csv)


def start_process(subject_name, versions_set_name, output_csv):
    global configure_json_file

    subject_working_dir = select_usable_buggy_versions_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    analyze_test_suite(configs, subject_working_dir, versions_set_name, output_csv)


def analyze_test_suite(configs, subject_working_dir, versions_set_name, output_csv):
    usable_buggy_versions_dir = subject_working_dir / versions_set_name
    assert usable_buggy_versions_dir.exists(), f"Usable buggy versions directory {usable_buggy_versions_dir} does not exist"

    # 1. get usable buggy versions
    buggy_version_list = get_usable_buggy_versions(usable_buggy_versions_dir)

    # 2. save statistics of buggy versions
    if not output_csv.endswith('.csv'):
        output_csv += '.csv'
    summary_stats_csv = subject_working_dir / output_csv

    tot_failing_TCs = []
    tot_passing_TCs = []

    total_testsuite = set()
    failing_set = set()

    # bad versions are buggy versions with failing TCs more than 1,000
    bad_versions = []

    # zero_versinos are buggy versions with no failing TCs
    zero_failings = []
    zero_passings = []

    total_buggy_versions = len(buggy_version_list)
    
    csv_keys = ["buggy_version_name", "#_failiing_TCs", "#_passing_TCs", "#_excluded_failing_TCs", "#_excluded_passing_TCs", "#_excluded_TCs", "#_total_TCs"]

    with open(summary_stats_csv, 'w') as f:
        f.write(','.join(csv_keys) + '\n')
        for buggy_version in buggy_version_list:
            buggy_version_name = buggy_version.name
            print(f"Analyzing {buggy_version_name}")

            # get test cases directory position
            testsuite_dir = buggy_version / 'testsuite_info'
            assert testsuite_dir.exists(), f"Test suite directory {testsuite_dir} does not exist"

            # get test cases file position
            failing_tcs = testsuite_dir / failing_txt
            passing_tcs = testsuite_dir / passing_txt
            assert failing_tcs.exists(), f"Failing test cases file {failing_tcs} does not exist"
            assert passing_tcs.exists(), f"Passing test cases file {passing_tcs} does not exist"

            # get excluded test cases
            excluded_failing_tcs = testsuite_dir / excluded_failing_txt
            excluded_passing_tcs = testsuite_dir / excluded_passing_txt
            excluded_tcs = testsuite_dir / excluded_txt

            # get excluded test cases
            excluded_failing_tcs_list = get_test_cases(excluded_failing_tcs)
            excluded_passing_tcs_list = get_test_cases(excluded_passing_tcs)
            excludeded_tcs_list = get_test_cases(excluded_tcs)
            
            # assert that excluded failing_tcs and excluded passsings_tcs == excluded tcs
            assert len(excludeded_tcs_list) == len(excluded_failing_tcs_list) + len(excluded_passing_tcs_list), f"Excluded test cases are not equal to the sum of excluded failing and excluded passing test cases"

            # get test cases
            failing_tcs_list = get_test_cases(failing_tcs)
            passing_tcs_list = get_test_cases(passing_tcs)

            total_testsuite.update(failing_tcs_list)
            total_testsuite.update(passing_tcs_list)
            total_testsuite.update(excludeded_tcs_list)


            # save statistics (later for average, max, min, etc.)
            failing_TCs = len(failing_tcs_list)
            passing_TCs = len(passing_tcs_list)
            exclued_failing_TCs = len(excluded_failing_tcs_list)
            excluded_passing_TCs = len(excluded_passing_tcs_list)
            excluded_TCs = len(excludeded_tcs_list)
            total_TCs = failing_TCs + passing_TCs + excluded_TCs

            # write to csv
            f.write(f"{buggy_version_name}, {failing_TCs}, {passing_TCs}, {exclued_failing_TCs}, {excluded_passing_TCs}, {excluded_TCs}, {total_TCs}\n")

            # if failing test cases are more than 500, skip this buggy version
            if failing_TCs > 500:
                bad_versions.append((buggy_version_name, failing_TCs))
                total_buggy_versions -= 1
                continue

            if failing_TCs == 0:
                zero_failings.append(buggy_version_name)
                total_buggy_versions -= 1
                continue
            
            if passing_TCs == 0:
                zero_passings.append(buggy_version_name)
                total_buggy_versions -= 1
                continue
            
            # make failing test cases set
            failing_set.update(failing_tcs_list)

            tot_failing_TCs.append(failing_TCs)
            tot_passing_TCs.append(passing_TCs)
    

    with open(subject_working_dir / 'total_TCs.txt', 'w') as f:
        sorted_total_testsuite = sorted(total_testsuite, key=custome_sort)
        content = '\n'.join(sorted_total_testsuite)
        f.write(content)

    print(f"\n\nTotal # of buggy versions: {len(buggy_version_list)}")
    print(f"Total # of test cases: {len(total_testsuite)}")

    average_failing_TCs = sum(tot_failing_TCs) / total_buggy_versions
    print(f"\nAverage failing test cases (excluding TCs from buggy versions with # of failing TCs > 500): {average_failing_TCs}")

    average_passing_TCs = sum(tot_passing_TCs) / total_buggy_versions
    print(f"Average passing test cases (excluding TCs from buggy versions with # of failing TCs > 500): {average_passing_TCs}")

    max_failing_TCs = max(tot_failing_TCs)
    print(f"\nMax # of failing test cases (from a single buggy version): {max_failing_TCs}")

    min_failing_TCs = min(tot_failing_TCs)
    print(f"Min # of failing test cases (from a single buggy version): {min_failing_TCs}")

    print(f"\nbuggy versions with # of failing TCs > 500: {len(bad_versions)}")
    # for bad_version, failing_TCs in bad_versions:
    #     print(f"\t > {bad_version}: {failing_TCs} failing TCs")

    print(f"\nbuggy versions with # failing TCs == 0: {len(zero_failings)}")
    for zero_version in zero_failings:
        print(f"\t > {zero_version}")

    print(f"\nbuggy versions with # passing TCs == 0: {len(zero_passings)}")
    # for zero_version in zero_passings:
    #     print(f"\t > {zero_version}")
    
    print(f"\nSize of failing TCs set (excluding TCs from buggy versions with # of failing TCs > 500): {len(failing_set)}")
    # for idx, tc in enumerate(failing_set):
    #     print(f"\t{idx+1}. {tc}")

    print(f"\nSize of passing TCs set (excluding TCs from buggy versions with # of failing TCs > 500): {len(total_testsuite) - len(failing_set)}")

def custome_sort(tc_script):
    tc_name = tc_script.split('.')[0]
    return (int(tc_name[2:]))


def get_test_cases(test_case_file):
    test_cases = []
    
    if test_case_file.exists():
        with open(test_case_file, 'r') as f:
            for line in f:
                test_cases.append(line.strip())
    else:
        return []
    
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
    parser.add_argument('--output-csv', type=str, help='Output csv file to save statistics', required=True)
    return parser
    


if __name__ == "__main__":
    main()