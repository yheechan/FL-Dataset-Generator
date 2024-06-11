#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import csv

# Current working directory
script_path = Path(__file__).resolve()
analyze_prerequisites = script_path.parent
bin_dir = analyze_prerequisites.parent
prepare_prerequisites_dir = bin_dir.parent

# General directories
src_dir = prepare_prerequisites_dir.parent
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

    subject_working_dir = prepare_prerequisites_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    prerequisite_data_per_bug = get_buggy_versions(subject_working_dir, "prerequisite_data")

    # 3. validate reduced test suite
    validate_reduced_test_suite(subject_working_dir, prerequisite_data_per_bug)

def validate_reduced_test_suite(subject_working_dir, prerequisite_data_per_bug):
    for idx, bug_dir in enumerate(prerequisite_data_per_bug):
        bug_name = bug_dir.name
        print(f"Validating {idx+1}/{len(prerequisite_data_per_bug)}: {bug_name}")

        # GET: buggy lineno from bug_info.csv
        bug_info = bug_dir / 'bug_info.csv'
        assert bug_info.exists(), f"Bug info file {bug_info} does not exist"
        target_file, bug_file, bug_lineno = get_bug_info(bug_info)

        # VALIDATE: Assert that buggy_line_key.txt exists
        buggy_line_key_file = bug_dir / 'buggy_line_key.txt'
        assert buggy_line_key_file.exists(), f"Buggy line key file {buggy_line_key_file} does not exist"
        buggy_line_key = check_buggy_lineno(buggy_line_key_file, bug_lineno)

        # VALIDATE: Assert that coverage_summary.csv exists
        coverage_summary = bug_dir / 'coverage_summary.csv'
        assert coverage_summary.exists(), f"Coverage summary file {coverage_summary} does not exist"

        # GET: failing_tcs.txt and passing_tcs.txt
        failing_tc_list = get_tcs(bug_dir, failing_txt)

        # VALIDATE: Assert that coverage_info/postprocessed_coverage.csv exists
        postprocessed_coverage = bug_dir / 'coverage_info' / 'postprocessed_coverage.csv'
        assert postprocessed_coverage.exists(), f"Postprocessed coverage file {postprocessed_coverage} does not exist"

        # VALIDATE: Assert the failing TCs execute the buggy line in postprocessed_coverage.csv
        result = check_failing_tcs(postprocessed_coverage, failing_tc_list, buggy_line_key)

        # VALIDATE: Assert that coverage_info/lines_executed_by_failing_tc.json exists
        lines_executed_by_failing_tc = bug_dir / 'coverage_info' / 'lines_executed_by_failing_tc.json'
        assert lines_executed_by_failing_tc.exists(), f"Lines executed by failing test cases file {lines_executed_by_failing_tc} does not exist"
        lines_executed_by_failing_tc_dict = json.load(lines_executed_by_failing_tc.open())
        assert lines_executed_by_failing_tc_dict is not None, f"Lines executed by failing test cases dictionary is empty for {bug_name}"

        # VALIDATE: Assert that line2function_info/line2function.json exists
        line2function_info = bug_dir / 'line2function_info' / 'line2function.json'
        assert line2function_info.exists(), f"Line to function mapping file {line2function_info} does not exist"
    
    print(f"All {len(prerequisite_data_per_bug)} bugs have been validated successfully")


def check_failing_tcs(postprocessed_coverage, failing_tc_list, buggy_line_key):
    with open(postprocessed_coverage, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row['key'] == buggy_line_key:
                for failing_tc in failing_tc_list:
                    tc_name = failing_tc.split('.')[0]
                    if row[tc_name] == '0':
                        return False
                return True


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

def check_buggy_lineno(buggy_line_key_file, bug_lineno):
    with buggy_line_key_file.open() as f:
        buggy_line_key = f.readline().strip()
        
        # HTMLparser.c#htmlParsePubidLiteral(htmlParserCtxtPtr ctxt)#3034
        buggy_lineno = buggy_line_key.split('#')[-1]

        assert buggy_lineno == bug_lineno, f"Bug line number mismatch: {buggy_lineno} != {bug_lineno}"
        
        return buggy_line_key

def get_bug_info(bug_info):
    target_file = None
    bug_file = None
    bug_lineno = None

    # target_code_file,buggy_code_file,buggy_lineno 
    with bug_info.open() as f:
        bug_info_lines = f.readlines()
        assert len(bug_info_lines) == 2, f"Bug info file {bug_info} is not in correct format"

        target_file, bug_file, bug_lineno = bug_info_lines[1].strip().split(',')

    return target_file, bug_file, bug_lineno


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