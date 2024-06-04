#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp

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

    # 3. make summary according to coverage_summary.csv
    make_summary(subject_working_dir, prerequisite_data_per_bug)

def make_summary(subject_working_dir, prerequisite_data_per_bug):
    num_failing_tcs = []
    num_passing_tcs = []
    num_ccts = []
    num_excluded_tcs = []
    num_utilized_tcs = []
    num_lines_executed_by_failing_tcs = []
    num_lines_executed_by_passing_tcs = []
    num_total_lines_executed = []
    num_total_lines = []
    all_coverage = []

    features = [
        'buggy version name', '#_failing_tcs', '#_passing_tcs', '#_ccts', '#_excluded_tcs',
        '#_utilized_tcs', '#_lines_executed_by_failing_tcs', '#_lines_executed_by_passing_tcs',
        '#_total_lines_executed', '#_total_lines', 'coverage'
    ]
    statistics_summary_file = subject_working_dir / 'statistics_summary.csv'
    statics_summary_fp = statistics_summary_file.open('w')
    statics_summary_fp.write(','.join(features) + '\n')

    buggy_versions_with_big_lines_executed_by_failing_tcs = []

    for bug_dir in prerequisite_data_per_bug:
        bug_name = bug_dir.name

        # GET: coverage_summary.csv
        coverage_summary_file = bug_dir / 'coverage_summary.csv'
        assert coverage_summary_file.exists(), f"Coverage summary file {coverage_summary_file} does not exist"

        with open(coverage_summary_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2, f"Coverage summary file {coverage_summary_file} is not in correct format"

            line = lines[1].strip()
            info = line.split(',')

            num_failing_tcs.append(int(info[0]))
            num_passing_tcs.append(int(info[1]))
            num_ccts.append(int(info[2]))
            num_excluded_tcs.append(int(info[3]))
            num_utilized_tcs.append(int(info[4]))
            num_lines_executed_by_failing_tcs.append(int(info[5]))
            num_lines_executed_by_passing_tcs.append(int(info[6]))
            num_total_lines_executed.append(int(info[7]))
            num_total_lines.append(int(info[8]))

            if int(info[5]) > 6000:
                buggy_versions_with_big_lines_executed_by_failing_tcs.append(bug_name)
                
            coverage = int(info[7]) / int(info[8])
            all_coverage.append(coverage)
            
            info.append(coverage)
            info.insert(0, bug_name)

            statics_summary_fp.write(','.join([str(i) for i in info]) + '\n')


    statics_summary_fp.close()

    # measure the average
    avg_failing_tcs = sum(num_failing_tcs) / len(num_failing_tcs)
    avg_passing_tcs = sum(num_passing_tcs) / len(num_passing_tcs)
    avg_ccts = sum(num_ccts) / len(num_ccts)
    avg_excluded_tcs = sum(num_excluded_tcs) / len(num_excluded_tcs)
    avg_utilized_tcs = sum(num_utilized_tcs) / len(num_utilized_tcs)
    avg_lines_executed_by_failing_tcs = sum(num_lines_executed_by_failing_tcs) / len(num_lines_executed_by_failing_tcs)
    avg_lines_executed_by_passing_tcs = sum(num_lines_executed_by_passing_tcs) / len(num_lines_executed_by_passing_tcs)
    avg_total_lines_executed = sum(num_total_lines_executed) / len(num_total_lines_executed)
    avg_total_lines = sum(num_total_lines) / len(num_total_lines)
    avg_coverage = sum(all_coverage) / len(all_coverage)

    print(f"Average failing test cases: {avg_failing_tcs}")
    print(f"Average passing test cases: {avg_passing_tcs}")
    print(f"Average cct: {avg_ccts}")
    print(f"Average excluded test cases: {avg_excluded_tcs}")
    print(f"Average utilized test cases: {avg_utilized_tcs}")
    print(f"Average lines executed by failing test cases: {avg_lines_executed_by_failing_tcs}")
    print(f"Average lines executed by passing test cases: {avg_lines_executed_by_passing_tcs}")
    print(f"Average total lines executed: {avg_total_lines_executed}")
    print(f"Average total lines: {avg_total_lines}")
    print(f"Average coverage: {avg_coverage}")

    # get max of lines executed by failing test cases
    max_lines_executed_by_failing_tcs = max(num_lines_executed_by_failing_tcs)
    print(f"Max lines executed by failing test cases: {max_lines_executed_by_failing_tcs}")

    # get min of lines executed by failing test cases
    min_lines_executed_by_failing_tcs = min(num_lines_executed_by_failing_tcs)
    print(f"Min lines executed by failing test cases: {min_lines_executed_by_failing_tcs}")

    print(f"Buggy versions with big lines executed by failing test cases: {len(buggy_versions_with_big_lines_executed_by_failing_tcs)}")




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