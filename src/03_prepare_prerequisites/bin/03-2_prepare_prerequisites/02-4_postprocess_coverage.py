#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import os

# Current working directory
script_path = Path(__file__).resolve()
prepare_prerequisites_cmd_dir = script_path.parent
bin_dir = prepare_prerequisites_cmd_dir.parent
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
real_world_buggy_versions = 'real_world_buggy_versions'

my_env = os.environ.copy()

coverage_summary = {
    '#_failing_tcs': 0,
    '#_passing_tcs': 0,
    '#_cc_tcs': 0,
    '#_excluded_tcs': 0,
    '#_total_utilized_tcs': 0,
    '#_lines_executed_by_failing_tcs': 0,
    '#_lines_executed_by_passing_tcs': 0,
    '#_total_lines_executed': 0,
    '#_total_lines': 0,
}

lines_execed_by_failing_tc = {}
lines_execed_by_passing_tc = {}
lines_execed = {}

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker, args.version)


def start_process(subject_name, worker_name, version_name):
    subject_working_dir = prepare_prerequisites_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_preparing_prerequisites' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    assigned_buggy_versions_dir = core_working_dir / 'assigned_buggy_versions'
    assert assigned_buggy_versions_dir.exists(), f"Assigned buggy versions directory {assigned_buggy_versions_dir} does not exist"

    version_dir = assigned_buggy_versions_dir / version_name
    assert version_dir.exists(), f"Version directory {version_dir} does not exist"


    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)


    # 2. get bug_info
    target_code_file_path, buggy_code_filename, buggy_lineno = get_bug_info(version_dir)
    # print(f"Target code file: {target_code_file_path}")
    # print(f"Buggy code filename: {buggy_code_filename}")
    # print(f"Buggy line number: {buggy_lineno}")
    assert version_name == buggy_code_filename, f"Version name {version_name} does not match with buggy code filename {buggy_code_filename}"

    # 3. get failing tc list (ex, TC1, TC2, ...)
    failing_tc_list = get_tcs(version_dir, 'failing_tcs.txt')
    coverage_summary['#_failing_tcs'] = len(failing_tc_list)
    print(f"Total failing test cases: {len(failing_tc_list)}")

    passing_tc_list = get_tcs(version_dir, 'passing_tcs.txt')
    coverage_summary['#_passing_tcs'] = len(passing_tc_list)
    print(f"Total passing test cases: {len(passing_tc_list)}")

    ccts_list = get_tcs(version_dir, 'ccts.txt')
    coverage_summary['#_cc_tcs'] = len(ccts_list)
    print(f"Total cct test cases: {len(ccts_list)}")

    excluded_tc_list = get_tcs(version_dir, 'excluded_tcs.txt')
    coverage_summary['#_excluded_tcs'] = len(excluded_tc_list)
    print(f"Total excluded test cases: {len(excluded_tc_list)}")

    total_utilized_tc = len(failing_tc_list) + len(passing_tc_list)
    coverage_summary['#_total_utilized_tcs'] = total_utilized_tc

    # 5. get line2function information
    line2function_dict = get_line2function_dict(version_dir)

    # 5. make buggy line key
    # ex) <filename>#<function_name>#<line_number>
    buggy_line_key = make_key(target_code_file_path, buggy_lineno, line2function_dict)
    found_func = buggy_line_key.split('#')[1]
    assert found_func != 'FUNCTIONNOTFOUND', f"Function not found for buggy line {buggy_lineno}"
    print(f"Buggy line key: {buggy_line_key}")

    # 6. start postprocess of coverage files
    postprocess_coverage(
        configs, core_working_dir, version_name,
        target_code_file_path, buggy_code_filename, buggy_lineno,
        failing_tc_list, passing_tc_list,
        version_dir, buggy_line_key, line2function_dict
    )


def postprocess_coverage(
        configs, core_working_dir, version_name,
        target_code_file_path, buggy_code_filename, buggy_lineno,
        failing_tc_list, passing_tc_list,
        version_dir, buggy_line_key, line2function_dict
):
    global coverage_summary, lines_execed_by_failing_tc, lines_execed_by_passing_tc

    # make coverage directory
    version_coverage_dir = version_dir / 'coverage_info'
    if not version_coverage_dir.exists():
        version_coverage_dir.mkdir(parents=True, exist_ok=True)

    cov_dir = core_working_dir / 'coverage'
    version_cov_dir = cov_dir / version_name
    assert version_cov_dir.exists(), f"Version coverage directory {version_cov_dir} does not exist"

    # make total tc list
    total_tc_list = failing_tc_list + passing_tc_list
    total_tc_list = sorted(total_tc_list, key=custome_sort)
    print(f"Total test cases: {len(total_tc_list)}")


    # make a csv file for coverage where the column is each test case
    # and the row is each line key (filename#function_name#line_number)
    # the contents is 0 or 1 (0: not covered, 1: covered)
    first = True
    cov_data = {
        'col_data': [],
        'row_data': []
    }
    for idx, tc_script_name in enumerate(total_tc_list):
        print(f"Processing {idx+1}/{len(total_tc_list)}: {tc_script_name}")

        tc_name = tc_script_name.split('.')[0]
        tc_cov_filename = f"{tc_name}.raw.json"
        tc_cov_file = version_cov_dir / tc_cov_filename
        assert tc_cov_file.exists(), f"Test case coverage file {tc_cov_file} does not exist"

        tc_cov_json = json.load(tc_cov_file.open())

        if first:
            first = False
            add_key_data(cov_data, tc_cov_json, line2function_dict)
        
        add_cov_data(
            cov_data, tc_cov_json, tc_script_name,
            failing_tc_list, passing_tc_list,
            line2function_dict, buggy_line_key
        )
    
    coverage_summary['#_lines_executed_by_failing_tcs'] = len(lines_execed_by_failing_tc)
    coverage_summary['#_lines_executed_by_passing_tcs'] = len(lines_execed_by_passing_tc)
    coverage_summary['#_total_lines_executed'] = len(lines_execed)
    
    # write coverage data to a csv file
    write_postprocessed_coverage(
        version_coverage_dir, cov_data
    )
    write_executed_lines(version_coverage_dir, lines_execed_by_failing_tc, 'lines_executed_by_failing_tc.json')
    write_executed_lines(version_coverage_dir, lines_execed_by_passing_tc, 'lines_executed_by_passing_tc.json')
    write_summary(version_dir, coverage_summary)
    write_buggy_line_key(version_dir, buggy_line_key)

def write_buggy_line_key(version_dir, buggy_line_key):
    buggy_line_key_file = version_dir / 'buggy_line_key.txt'
    with open(buggy_line_key_file, 'w') as f:
        f.write(buggy_line_key)
    
    print(f"Buggy line key is saved at {buggy_line_key_file.name}")

def write_summary(version_dir, coverage_summary):
    cov_summary_file = version_dir / 'coverage_summary.csv'
    columns = coverage_summary.keys()
    with open(cov_summary_file, 'w') as f:
        f.write(','.join(columns) + '\n')
        f.write(','.join([str(coverage_summary[key]) for key in columns]) + '\n')
    
    print(f"Coverage summary is saved at {cov_summary_file.name}")

def write_executed_lines(version_coverage_dir, lines_execed_by_tc, filename):
    lines_execed_by_tc_file = version_coverage_dir / filename
    with open(lines_execed_by_tc_file, 'w') as f:
        json.dump(lines_execed_by_tc, f)
    
    print(f"Executed lines by test cases are saved at {lines_execed_by_tc_file.name}")

def write_postprocessed_coverage(version_coverage_dir, cov_data):
    cov_csv_file = version_coverage_dir / f"postprocessed_coverage.csv"
    with open(cov_csv_file, 'w') as f:
        f.write(','.join(cov_data['col_data']) + '\n')

        for row in cov_data['row_data']:
            f.write(','.join([f"\"{str(x)}\"" for x in row]) + '\n')
    
    print(f"Coverage csv file is saved at {cov_csv_file.name}")



def add_cov_data(
        cov_data, tc_cov_json, tc_script_name,
        failing_tc_list, passing_tc_list,
        line2function_dict, buggy_line_key
):
    global coverage_summary, lines_execed_by_failing_tc, lines_execed_by_passing_tc

    tc_name = tc_script_name.split('.')[0]
    cov_data['col_data'].append(tc_name)

    pass_or_fail = False if tc_script_name in failing_tc_list else True
    if pass_or_fail:
        assert tc_script_name in passing_tc_list, f"Test case {tc_script_name} is not in passing test cases"
    
    cnt = 0
    for file in tc_cov_json['files']:
        filename = file['file']
        for i in range(len(file['lines'])):
            line = file['lines'][i]
            lineno = line['line_number']
            key = make_key(filename, lineno, line2function_dict)
            assert key == cov_data['row_data'][cnt][0], f"Key {key} does not match with the row data key {cov_data['row_data'][i][0]}"

            covered = 1 if line['count'] > 0 else 0
            cov_data['row_data'][cnt].append(covered)

            if covered == 1:
                if key not in lines_execed:
                    lines_execed[key] = 0
                lines_execed[key] += 1

                if pass_or_fail:
                    if key not in lines_execed_by_passing_tc:
                        lines_execed_by_passing_tc[key] = []
                    lines_execed_by_passing_tc[key].append(tc_script_name)
                else:
                    if key not in lines_execed_by_failing_tc:
                        lines_execed_by_failing_tc[key] = []
                    lines_execed_by_failing_tc[key].append(tc_script_name)

            # assert that failing line executes buggy line
            if not pass_or_fail and key == buggy_line_key:
                assert covered == 1, f"Failing test case {tc_script_name} does not execute buggy line {buggy_line_key}"
                print(f"Failing test case {tc_script_name} executes buggy line {buggy_line_key}")
            
            cnt += 1
                    

def add_key_data(cov_data, tc_cov_json, line2function_dict):
    global coverage_summary
    cov_data['col_data'].append('key')

    for file in tc_cov_json['files']:
        filename = file['file']
        for line in file['lines']:
            lineno = line['line_number']
            key = make_key(filename, lineno, line2function_dict)
            
            assert [key] not in cov_data['row_data'], f"Key {key} already exists in the row data"
            cov_data['row_data'].append([key])
            coverage_summary['#_total_lines'] += 1

def make_key(target_code_file_path, buggy_lineno, line2function_dict):
    filename = target_code_file_path.split('/')[-1]
    function = None
    for key, value in line2function_dict.items():
        if key.endswith(filename):
            for func_info in value:
                if int(func_info[1]) <= int(buggy_lineno) <= int(func_info[2]):
                    function = f"{filename}#{func_info[0]}#{buggy_lineno}"
                    return function
    function = f"{filename}#FUNCTIONNOTFOUND#{buggy_lineno}"
    return function

def get_line2function_dict(version_dir):
    line2function_dir = version_dir / 'line2function_info'
    assert line2function_dir.exists(), f"Line2function info directory {line2function_dir} does not exist"

    line2function_file = line2function_dir / 'line2function.json'
    assert line2function_file.exists(), f"Line2function file {line2function_file} does not exist"

    line2function_dict = {}
    with open(line2function_file, 'r') as f:
        line2function_dict = json.load(f)

    return line2function_dict

def get_bug_info(version_dir):
    bug_info_csv = version_dir / 'bug_info.csv'
    assert bug_info_csv.exists(), f"Bug info csv file {bug_info_csv} does not exist"

    with open(bug_info_csv, 'r') as f:
        lines = f.readlines()
        target_code_file, buggy_code_filename, buggy_lineno = lines[1].strip().split(',')
        return target_code_file, buggy_code_filename, buggy_lineno

def get_buggy_code_file(version_dir, buggy_code_filename):
    buggy_code_file_dir = version_dir / 'buggy_code_file'
    assert buggy_code_file_dir.exists(), f"Buggy code file directory {buggy_code_file_dir} does not exist"

    buggy_code_file = buggy_code_file_dir / buggy_code_filename
    assert buggy_code_file.exists(), f"Buggy code file {buggy_code_file} does not exist"

    return buggy_code_file

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
