#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import os
import csv
import math

# Current working directory
script_path = Path(__file__).resolve()
sbfl_feature_extraction_dir = script_path.parent
bin_dir = sbfl_feature_extraction_dir.parent
extract_sbfl_features_cmd_dir = bin_dir.parent

# General directories
src_dir = extract_sbfl_features_cmd_dir.parent
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
real_world_buggy_versions = 'real_world_buggy_versions'

my_env = os.environ.copy()


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker, args.version)


def start_process(subject_name, worker_name, version_name):
    subject_working_dir = extract_sbfl_features_cmd_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_extracting_sbfl_features' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    assigned_buggy_versions_dir = core_working_dir / 'assigned_buggy_versions'
    assert assigned_buggy_versions_dir.exists(), f"Assigned buggy versions directory {assigned_buggy_versions_dir} does not exist"

    version_dir = assigned_buggy_versions_dir / version_name
    assert version_dir.exists(), f"Version directory {version_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. get test cases
    # list of tc script name (e.g., TC1.sh, TC2.sh, ...)
    failing_tc_list = get_tcs(version_dir, 'failing_tcs.txt')
    passing_tc_list = get_tcs(version_dir, 'passing_tcs.txt')

    # 3. get buggy line key
    buggy_line_key = get_buggy_line_key(version_dir)

    # 4. get lines from postprocessed coverage info
    # {key, TC1, TC2, ..., TCn}
    lines = get_lines_from_postprocessed_coverage(version_dir, buggy_line_key, failing_tc_list, passing_tc_list)

    # 5. initialize spectrums per line {key, ep, ef, np, nf}
    spectrum_per_line = initialize_spectrums_per_line(lines, buggy_line_key, failing_tc_list, passing_tc_list)

    # 5. calculate SBFL suspsiciousness scores based on the spectrum
    sbfl_per_line = measure_total_sbfl(spectrum_per_line)

    # 6. write SBFL scores to a file
    write_sbfl_features(version_dir, sbfl_per_line)


def write_sbfl_features(version_dir, spectrum_per_line):
    sbfl_features_csv = version_dir / 'sbfl_features.csv'

    with open(sbfl_features_csv, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'key', 'ep', 'ef', 'np', 'nf',
            'Binary', 'GP13', 'Jaccard', 'Naish1',
            'Naish2', 'Ochiai', 'Russel+Rao', 'Wong1',
            'bug'
        ])
        writer.writeheader()

        for line_info in spectrum_per_line:
            writer.writerow(line_info)



def measure_total_sbfl(spectrum_per_line):
    SBFL_formulas = [
        'Binary', 'GP13', 'Jaccard', 'Naish1',
        'Naish2', 'Ochiai', 'Russel+Rao', 'Wong1'
    ]
    
    for line_info in spectrum_per_line:
        ep = line_info['ep']
        ef = line_info['ef']
        np = line_info['np']
        nf = line_info['nf']

        for formula in SBFL_formulas:
            sbfl_value = sbfl(ep, ef, np, nf, formula)
            line_info[formula] = sbfl_value
    
    return spectrum_per_line


def sbfl(e_p, e_f, n_p, n_f, formula="Ochiai"):
    if formula == "Jaccard":
        denominator = e_f + n_f + e_p
        if denominator == 0:
            return 0
        return e_f / denominator
    elif formula == "Binary":
        if 0 < n_f:
            return 0
        elif n_f == 0:
            return 1
    elif formula == "GP13":
        denominator = 2*e_p + e_f
        if denominator == 0:
            return 0
        return e_f + (e_f / denominator)
    elif formula == "Naish1":
        if 0 < n_f:
            return -1
        elif 0 == n_f:
            return n_p
    elif formula == "Naish2":
        x = e_p / (e_p + n_p + 1)
        return e_f - x
    elif formula == "Ochiai":
        denominator = math.sqrt((e_f + n_f) * (e_f + e_p))
        if denominator == 0:
            return 0
        return e_f / denominator
    elif formula == "Russel+Rao":
        return e_f/(e_p + n_p + e_f + n_f)
    elif formula == "Wong1":
        return e_f
    else:
        raise Exception(f"Unknown formula: {formula}")


def initialize_spectrums_per_line(lines, buggy_line_key, failing_tc_list, passing_tc_list):
    spectrums_per_line = []

    buggy_line_cnt = 0
    for line in lines:
        line_key = line['key']

        bug_stat = 0
        if line_key == buggy_line_key:
            assert buggy_line_cnt == 0, f"Multiple buggy lines found: {buggy_line_key}"
            buggy_line_cnt += 1
            bug_stat = 1
        
        ef, nf = calculate_spectrum(line, failing_tc_list)
        ep, np = calculate_spectrum(line, passing_tc_list)

        # VALIDATE: sum of executed and not executed test cases should be equal to total number of test cases
        assert ef + ep == len(failing_tc_list), f"Sum of executed test cases {ef} and not executed test cases {ep} should be equal to total number of failing test cases {len(failing_tc_list)}"
        assert nf + np == len(passing_tc_list), f"Sum of executed test cases {nf} and not executed test cases {np} should be equal to total number of passing test cases {len(passing_tc_list)}"

        spectrums_per_line.append({
            'key': line_key,
            'ep': ep, 'ef': ef, 'np': np, 'nf': nf,
            'bug': bug_stat
        })

    return spectrums_per_line

def calculate_spectrum(line, tc_list):
    executed = 0
    not_executed = 0

    for tc in tc_list:
        tc_name = tc.split('.')[0]
        if line[tc_name] == 1:
            executed += 1
        else:
            not_executed += 1
    
    return executed, not_executed


def get_buggy_line_key(version_dir):
    buggy_line_key_file = version_dir / 'buggy_line_key.txt'
    assert buggy_line_key_file.exists(), f"Buggy line key file {buggy_line_key_file} does not exist"

    with open(buggy_line_key_file, 'r') as f:
        line = f.readline().strip()
        return line


def get_lines_from_postprocessed_coverage(version_dir, buggy_line_key, failing_tc_list, passing_tc_list):
    cov_data_csv = version_dir / 'coverage_info/postprocessed_coverage.csv'
    assert cov_data_csv.exists(), f'{cov_data_csv} does not exist'

    tc_list = failing_tc_list + passing_tc_list

    cov_per_line = []
    check_tc_col = True
    buggy_line_exists = False
    with open(cov_data_csv, 'r') as csv_fp:
        csv_reader = csv.reader(csv_fp)
        next(csv_reader)
        for row in csv_reader:
            line_key = row['key']

            # VALIDATE: postprocessed coverage data has buggy line key
            if line_key == buggy_line_key:
                buggy_line_exists = True
            
            cov_per_line.append(row)

            # VALIDATE: postprocessed coverage data has all test cases
            if check_tc_col:
                for tc in tc_list:
                    tc_name = tc.split('.')[0]
                    if tc_name not in row:
                        raise Exception(f"Test case {tc_name} is not found in postprocessed coverage data")
                check_tc_col = False


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
    parser.add_argument('--worker', type=str, help='Worker name (e.g., <machine-name>/<core-id>)', required=True)
    parser.add_argument('--version', type=str, help='Version name', required=True)
    return parser

if __name__ == "__main__":
    main()
    exit(0)
