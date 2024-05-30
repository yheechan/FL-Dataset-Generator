#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import os
import random

# Current working directory
script_path = Path(__file__).resolve()
mbfl_feature_extraction_dir = script_path.parent
bin_dir = mbfl_feature_extraction_dir.parent
extract_mbfl_features_cmd_dir = bin_dir.parent

# General directories
src_dir = extract_mbfl_features_cmd_dir.parent
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

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker, args.version)


def start_process(subject_name, worker_name, version_name):
    subject_working_dir = extract_mbfl_features_cmd_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_extracting_mbfl_features' / worker_name
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

    # 4. get buggy code file
    buggy_code_file = get_buggy_code_file(version_dir, buggy_code_filename)
    # print(f"Buggy code file: {buggy_code_file.name}")


    # 6. get lines executed by failing test cases per target files
    # IT ALSO VALIDATES THE LINES EXECUTED BY FAILING TC CONTAINS THE BUGGY LINE
    lines_executed_by_failing_tc = get_lines_executed_by_failing_tcs(version_dir, target_code_file_path, buggy_lineno, configs['target_files'])
    print(f"Lines executed by failing test cases:")
    for target_file, lines in lines_executed_by_failing_tc.items():
        print(f"{target_file}: {len(lines)}")


    # 7. select mutants from core_working_dir/generated_mutants/<version_name>/<mutant_dir_for_each_target_file>
    selected_fileline2mutants = select_mutants(configs, core_working_dir, version_name, version_dir, lines_executed_by_failing_tc, subject_name)

    # 8. write selected mutants to a file
    write_selected_mutants(core_working_dir, version_name, selected_fileline2mutants)

def write_selected_mutants(core_working_dir, version_name, selected_fileline2mutants):
    mutant_data_dir = core_working_dir / 'mutant_data'
    mutant_data_dir.mkdir(exist_ok=True)

    version_mutant_dir = mutant_data_dir / version_name
    version_mutant_dir.mkdir(exist_ok=True)

    selected_mutants_file = version_mutant_dir / 'selected_mutants.csv'
    mutant_cnt = 1
    with selected_mutants_file.open('w') as f:
        f.write(",,,,,Before Mutation,,,,,After Mutation\n")
        f.write("target filename,mutant_id,lineno,Mutant Filename,Mutation Operator,Start Line#,Start Col#,End Line#,End Col#,Target Token,Start Line#,Start Col#,End Line#,End Col#,Mutated Token,Extra Info\n")
        for filename, fileline2mutants in selected_fileline2mutants.items():
            for line, mutants in fileline2mutants.items():
                for mutant in mutants:
                    mutant_id = f"mutant_{mutant_cnt}"
                    f.write(f"{filename},{mutant_id},{line},{mutant}\n")
                    mutant_cnt += 1


def select_mutants(
        configs, core_working_dir, version_name,
        version_dir, lines_executed_by_failing_tc, subject_name):
    
    # --- prepare needed directories
    version_mutants_dir = core_working_dir / 'generated_mutants' / version_name
    assert version_mutants_dir.exists(), f"Version mutants directory {version_mutants_dir} does not exist"

    max_mutants = configs['max_mutants']

    # --- start selecting mutants
    files2mutants = {}
    tot_mutant_cnt = 0
    for target_file, lines in lines_executed_by_failing_tc.items():
        file_tot_mutant_cnt = 0

        filename = target_file.split('/')[-1]
        # initiate dictionary for selected mutants on file-line basis
        files2mutants[filename] = {}
        for line in lines:
            files2mutants[filename][line] = []
        
        # get mutants for each line
        file_mutants_dir = version_mutants_dir / f"{subject_name}-{filename}"
        assert file_mutants_dir.exists(), f"File mutants directory {file_mutants_dir} does not exist"
        
        code_name = target_file.split('.')[0]
        mut_db_csv_name = f"{code_name}_mut_db.csv"
        mut_db_csv = file_mutants_dir / mut_db_csv_name
        # this is when failing tcs doesn't execute any line in the target file
        if not mut_db_csv.exists():
            print(f"Mutants database csv {mut_db_csv.name} does not exist")
            continue

        print(f"Reading mutants from {mut_db_csv.name}")
        with mut_db_csv.open() as f:
            lines = f.readlines()
            mutants = lines[2:]
            random.shuffle(mutants)
            print(f"Total mutants: {len(mutants)}")
            for mutant_line in mutants:
                mutant_line = mutant_line.strip()

                # 0 Mutant Filename
                # 1 Mutation Operator
                # 2 Start Line#
                # 3 Start Col#
                # 4 End Line#
                # 5 End Col#
                # 6 Target Token
                # 7 Start Line#
                # 8 Start Col#
                # 9 End Line#
                # 10 End Col#
                # 11 Mutated Token
                # 12 Extra Info
                info = mutant_line.split(',')
                mutant_filename = info[0]
                mutant_lineno = info[2]

                # do not select mutants for lines that are not executed by failing test cases
                if mutant_lineno not in files2mutants[filename]:
                    print(f"Mutant line {mutant_lineno} is not executed by failing test cases")
                    continue

                # select mutant
                if len(files2mutants[filename][mutant_lineno]) < max_mutants:
                    files2mutants[filename][mutant_lineno].append(mutant_line)
                    file_tot_mutant_cnt += 1
                    tot_mutant_cnt += 1

            print(f"Selected mutants for {filename}: {file_tot_mutant_cnt}")
    print(f"Total selected mutants: {tot_mutant_cnt}")

    return files2mutants



def get_lines_executed_by_failing_tcs(version_dir, target_code_file_path, buggy_lineno, target_files):
    lines_executed_by_failing_tc_file = version_dir / 'coverage_info/lines_executed_by_failing_tc.json'
    assert lines_executed_by_failing_tc_file.exists(), f"Lines executed by failing test cases file {lines_executed_by_failing_tc_file} does not exist"

    lines_executed_by_failing_tc_json = json.loads(lines_executed_by_failing_tc_file.read_text())

    execed_lines = {}
    for target_file in target_files:
        filename = target_file.split('/')[-1]
        execed_lines[filename] = []

    # TODO: read the file and return the content
    buggy_filename = target_code_file_path.split('/')[-1]
    executed_buggy_line = False
    for key, tcs in lines_executed_by_failing_tc_json.items():
        info = key.split('#')
        filename = info[0].split('/')[-1]
        function_name = info[1]
        lineno = info[2]

        if filename not in execed_lines:
            execed_lines[filename] = []
        execed_lines[filename].append(lineno)

        if filename == buggy_filename and lineno == buggy_lineno:
            executed_buggy_line = True

    assert executed_buggy_line, f"Buggy line {buggy_lineno} is not executed by any failing test cases"

    return execed_lines


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
