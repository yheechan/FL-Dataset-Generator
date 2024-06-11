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
mbfl_dataset_dir = script_path.parent
bin_dir = mbfl_dataset_dir.parent
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

# measure how many failing tcs have been excluded

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)


def start_process(subject_name):
    global configure_json_file

    subject_working_dir = mbfl_feature_extraction_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    mbfl_features_per_bug = get_buggy_versions(subject_working_dir, "mbfl_features")

    # 3. Check whether all failing tcs are in the reduced failing tcs
    bad_versions = start_analysis(configs, subject_name, mbfl_features_per_bug)

    excluded_len = []
    print(f"Bad versions: {len(bad_versions)}")
    for bad_version in bad_versions:
        print(f"{bad_version[0]}: {len(bad_version[1])}")
        excluded_len.append(len(bad_version[1]))

    minimum = min(excluded_len)
    maximum = max(excluded_len)
    average = sum(excluded_len) / len(excluded_len)

    print(f"Minimum: {minimum}")
    print(f"Maximum: {maximum}")
    print(f"Average: {average}")



def start_analysis(configs, subject_name, mbfl_features_per_bug):
    bad_version = []

    usable_buggy_versions_dir = src_dir / '02_select_usable_buggy_versions' / f"{subject_name}-working_directory" / 'usable_buggy_versions'

    for idx, bug_dir in enumerate(mbfl_features_per_bug):
        bug_name = bug_dir.name
        # if bug_name != 'relaxng.MUT4445.c': continue
        # print(f"Processing bug {bug_name}")

        # GET: mbfl_features.csv
        mbfl_features_csv_file = bug_dir / 'mbfl_features.csv'
        assert mbfl_features_csv_file.exists(), f"MBFL features file {mbfl_features_csv_file} does not exist"

        # GET: list of failing TCs
        failing_tcs = get_tcs(bug_dir, 'failing_tcs.txt')

        # GET: bug_dir from usable_buggy_versions_dir
        og_bug_dir = usable_buggy_versions_dir / bug_name
        assert og_bug_dir.exists(), f"Usable buggy version directory {og_bug_dir} does not exist"

        og_failing_tcs = get_tcs(og_bug_dir, 'failing_tcs.txt')

        failing_tcs = set(failing_tcs)
        og_failing_tcs = set(og_failing_tcs)

        # Check that all tcs from original failing tcs are in the reduced failing tcs
        if not og_failing_tcs.issubset(failing_tcs):
            # also return how many tcs are missing
            missing_tcs = og_failing_tcs - failing_tcs
            bad_version.append((bug_name, missing_tcs))
    
    return bad_version

            

def get_mutant_keys(max_mutants):
    mutant_keys = []
    for i in range(1, max_mutants+1):
        mutant_keys.append(f'm{i}:f2p')
        mutant_keys.append(f'm{i}:p2f')
    return mutant_keys

def custome_sort(tc_script):
    tc_filename = tc_script.split('.')[0]
    return int(tc_filename[2:])

def get_tcs(version_dir, tc_file):
    testsuite_info_dir = version_dir / 'testsuite_info'
    assert testsuite_info_dir.exists(), f"Testsuite info directory {testsuite_info_dir} does not exist"

    tc_file_txt = testsuite_info_dir / tc_file
    assert tc_file_txt.exists(), f"Failing test cases file {tc_file_txt} does not exist"

    tcs_list = []

    with open(tc_file_txt, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            tcs_list.append(line)
        
    tcs_list = sorted(tcs_list, key=custome_sort)

    return tcs_list


def analysis_non_buggy_function_with_f2p_above_th(bug_name, mbfl_features_csv_file, buggy_line_key, mutant_keys, fail_cnt, threshold):
    target_buggy_file = buggy_line_key.split('#')[0].split('/')[-1]
    buggy_function_name = buggy_line_key.split('#')[1]
    buggy_lineno = int(buggy_line_key.split('#')[-1])

    bad_line = []

    with open(mbfl_features_csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row['key']
            current_target_file = key.split('#')[0].split('/')[-1]
            current_function_name = key.split('#')[1]
            current_lineno = int(key.split('#')[-1])

            num_mutants = int(row['|muse(s)|'])

            if current_target_file != target_buggy_file or \
                current_function_name != buggy_function_name:

                # mutant list which its mutants have f2p == fail_cnt
                fully_killed_mutants_list = fully_killed_mutants(row, mutant_keys, 'f2p', fail_cnt)

                # if line has no mutants with f2p == fail_cnt
                # then add the line to bad_line
                if len(fully_killed_mutants_list) > num_mutants/2:
                    bad_line.append(row)
    
    # if there is no line with f2p == fail_cnt
    # then return 0
    if len(bad_line) > threshold:
        return 0
    
    # if there is at least one line with f2p == fail_cnt
    # then return 1
    return 1


def fully_killed_mutants(row, mutant_keys, f2p_or_p2f, fail_cnt):
    # fully killed mutant is the list of mutant in a line
    # that kills all failing TCs (f2p == fail_cnt)
    fully_killed_mutants_list = []

    for key in mutant_keys:
        if f2p_or_p2f in key and int(row[key]) != -1:
            if int(row[key]) == fail_cnt:
                fully_killed_mutants_list.append(row)

    return fully_killed_mutants_list
    # if len(fully_killed_mutants_list) != 0:
    #     return 0
    
    # return 1


def analysis_buggy_function_with_f2p_0(bug_name, mbfl_features_csv_file, buggy_line_key, mutant_keys):
    target_buggy_file = buggy_line_key.split('#')[0].split('/')[-1]
    buggy_function_name = buggy_line_key.split('#')[1]
    buggy_lineno = int(buggy_line_key.split('#')[-1])

    good_mutants = []

    with open(mbfl_features_csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row['key']
            current_target_file = key.split('#')[0].split('/')[-1]
            current_function_name = key.split('#')[1]
            current_lineno = int(key.split('#')[-1])

            if current_target_file == target_buggy_file and \
                current_function_name == buggy_function_name:

                feature_value = measure_feature_value(row, mutant_keys, 'f2p')
                if feature_value != 0:
                    good_mutants.append(row)
    
    if len(good_mutants) == 0:
        return 0
    
    return 1
    




def measure_feature_value(row, mutant_keys, f2p_or_p2f):
    feature_value = 0

    for key in mutant_keys:
        if f2p_or_p2f in key and int(row[key]) != -1:
            feature_value += int(row[key])

    return feature_value


def get_mutants_data(bug_dir, buggy_line_key):
    mutation_testing_results_csv = bug_dir / 'mutation_testing_results.csv'

    buggy_target_file = buggy_line_key.split('#')[0].split('/')[-1]
    buggy_lineno = buggy_line_key.split('#')[-1]

    mutants_data = {
        '# mutants': 0,
        '# uncompilable mutants': 0,
        '# mutans on buggy line': 0,
        '# uncompilable mutants on buggy line': 0,
        '# compilable mutants on buggy line': 0,
        'total_p2f': 0,
        'total_f2p': 0,
    }

    with open(mutation_testing_results_csv, 'r') as f:
        lines = f.readlines()

        for line in lines[1:]:
            mutants_data['# mutants'] += 1

            info = line.strip().split(',')
            target_file = info[0].split('/')[-1]
            mutant_name = info[1]
            mutant_lineno = info[2]
            mutant_build_result = info[3]
            mutant_p2f = info[4]
            mutant_p2p = info[5]
            mutant_f2p = info[6]
            mutant_f2f = info[7]

            if mutant_build_result == 'FAIL':
                mutants_data['# uncompilable mutants'] += 1
            else:
                mutants_data['total_p2f'] += int(mutant_p2f)
                mutants_data['total_f2p'] += int(mutant_f2p)
            
            if target_file == buggy_target_file and mutant_lineno == buggy_lineno:
                mutants_data['# mutans on buggy line'] += 1

                if mutant_build_result == 'PASS':
                    mutants_data['# compilable mutants on buggy line'] += 1
                else:
                    mutants_data['# uncompilable mutants on buggy line'] += 1
    
    return mutants_data


def get_buggy_line_key(bug_dir):
    buggy_line_key_file = bug_dir / 'buggy_line_key.txt'
    buggy_line_key = None

    with buggy_line_key_file.open() as f:
        buggy_line_key = f.readline().strip()

    return buggy_line_key

def get_lines_executed_by_failing_tcs(bug_dir):
    get_lines_executed_by_failing_tcs_file = bug_dir / 'coverage_info/lines_executed_by_failing_tc.json'
    assert get_lines_executed_by_failing_tcs_file.exists(), f"Lines executed by failing TCs file {get_lines_executed_by_failing_tcs_file} does not exist"

    lines_executed_by_failing_tcs = None
    with get_lines_executed_by_failing_tcs_file.open() as f:
        lines_executed_by_failing_tcs = json.load(f)

    return lines_executed_by_failing_tcs


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