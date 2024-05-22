#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import time
import multiprocessing
import random

# Current working directory
script_path = Path(__file__).resolve()
select_initial_buggy_versions_dir = script_path.parent
bin_dir = select_initial_buggy_versions_dir.parent
select_usable_buggy_versions = bin_dir.parent

# General directories
src_dir = select_usable_buggy_versions.parent
root_dir = src_dir.parent
user_configs_dir = root_dir / 'user_configs'
subjects_dir = root_dir / 'subjects'
external_tools_dir = root_dir / 'external_tools'
collect_buggy_mutants_step_dir = src_dir / '01_collect_buggy_mutants'

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
real_world_buggy_versions = 'real_world_buggy_versions'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.num_versions)


def start_process(subject_name, num_versions):
    global configure_json_file

    subject_working_dir = select_usable_buggy_versions / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. initialize selected_buggy_versions directory
    selected_buggy_versions_dir = initialize_selected_buggy_versions_directory(subject_working_dir)

    # 3. copy real-world-buggy-versions if any exists
    included_cnt = 0
    if configs[real_world_buggy_versions] == True:
        included_cnt = copy_real_world_buggy_versions(subject_name, subject_working_dir, selected_buggy_versions_dir)
    num_versions -= included_cnt

    # 4. randomly select buggy versions from buggy_mutants directory
    #    and copy them to selected_buggy_versions directory
    #    until the number of selected buggy versions reaches num_versions
    select_buggy_versions(configs, subject_name, selected_buggy_versions_dir, num_versions)


def initialize_selected_buggy_versions_directory(subject_working_dir):
    selected_buggy_versions_dir = subject_working_dir / 'initial_selected_buggy_versions'
    selected_buggy_versions_dir.mkdir(exist_ok=True)
    return selected_buggy_versions_dir

def copy_real_world_buggy_versions(subject_name, subject_working_dir, selected_buggy_versions_dir):
    global real_world_buggy_versions

    subject_config_dir = subject_working_dir / f"{subject_name}-configures"
    assert subject_config_dir.exists(), f"Subject configurations directory {subject_config_dir} does not exist"

    real_world_buggy_versions_dir = subject_config_dir / real_world_buggy_versions
    assert real_world_buggy_versions_dir.exists(), f"Real world buggy versions directory {real_world_buggy_versions_dir} does not exist"

    count = 0
    for buggy_version_dir in real_world_buggy_versions_dir.iterdir():
        if buggy_version_dir.is_dir():
            cmd = f"cp -r {buggy_version_dir} {selected_buggy_versions_dir}"
            res = sp.call(cmd, shell=True)
            count += 1
    
    return count


def select_buggy_versions(configs, subject_name, selected_buggy_versions_dir, num_versions):
    # 0. bring back the datas from past step
    buggy_mutant_dir, generated_mutants_dir = get_past_step_datas(subject_name)

    # 1. get list of buggy mutants
    buggy_mutants_list = get_buggy_mutants_list(buggy_mutant_dir)

    # 2. shuffle the list
    random.shuffle(buggy_mutants_list)

    # 3. select num_versions of buggy mutants
    selected_buggy_mutants = buggy_mutants_list[:num_versions]

    # 4. copy selected buggy mutants to selected_buggy_versions directory
    for selected_buggy_mutant_dir in selected_buggy_mutants:
        print(f"Selected buggy mutant: {selected_buggy_mutant_dir.name}")
        copy_mutant_to_selected(selected_buggy_mutant_dir, selected_buggy_versions_dir, generated_mutants_dir)
        # break

def get_past_step_datas(subject_name):
    global collect_buggy_mutants_step_dir
    assert collect_buggy_mutants_step_dir.exists(), f"Collect buggy mutants step directory {collect_buggy_mutants_step_dir} does not exist"

    b4_subject_working_dir = collect_buggy_mutants_step_dir / f"{subject_name}-working_directory"
    assert b4_subject_working_dir.exists(), f"Before subject working directory {b4_subject_working_dir} does not exist"

    buggy_mutant_dir = b4_subject_working_dir / 'buggy_mutants'
    assert buggy_mutant_dir.exists(), f"Buggy mutants directory {buggy_mutant_dir} does not exist"

    generated_mutants_dir = b4_subject_working_dir / 'generated_mutants'
    assert generated_mutants_dir.exists(), f"Generated mutants directory {generated_mutants_dir} does not exist"

    return buggy_mutant_dir, generated_mutants_dir


def copy_mutant_to_selected(selected_buggy_mutant_dir, selected_buggy_versions_dir, generated_mutants_dir):
    mutant_name = selected_buggy_mutant_dir.name

    # ---- Preparation stage
    # 1. read bug_info.csv contents
    target_code_filename, mutant_code_filename = read_bug_info_csv(selected_buggy_mutant_dir)

    # ex) libxml2/parser.c, parser.MUT123.c
    target_file_mutant_dirname = target_code_filename.replace('/', '-')
    target_file_mutant_dir = generated_mutants_dir / target_file_mutant_dirname
    assert target_file_mutant_dir.exists(), f"Target code file directory {target_file_mutant_dir} does not exist"

    # 2. get buggy code file
    buggy_code_file = get_buggy_code_file(target_file_mutant_dir, mutant_code_filename)

    # 3. get line number of mutant code
    buggy_lineno, mut_db_line = get_buggy_lineno(target_file_mutant_dir, mutant_code_filename)


    # ---- Copying stage
    # 1. initialize needed directory
    mutant_dir_dest = intialize_directory_for_buggy_mutant(selected_buggy_versions_dir, mutant_name)

    # 2. write bug_info.csv contents
    # target_code_file,buggy_code_file,buggy_lineno
    write_bug_info_csv(mutant_dir_dest, target_code_filename, mutant_code_filename, buggy_lineno, mut_db_line)

    # 3. copy testsuite_info
    copy_testsuite_info(selected_buggy_mutant_dir, mutant_dir_dest)

    # 2. copy contents of buggy mutant to selected_buggy_versions directory
    copy_contents(mutant_dir_dest, buggy_code_file)

def read_bug_info_csv(selected_buggy_mutant):
    bug_info_csv = selected_buggy_mutant / 'bug_info.csv'
    assert bug_info_csv.exists(), f"Bug info csv file {bug_info_csv} does not exist"

    with bug_info_csv.open() as f:
        lines = f.readlines()
        for line in lines[1:]:
            info = line.strip().split(',')
            target_code_file = info[0]
            mutant_code_file = info[1]
            return target_code_file, mutant_code_file

def get_buggy_code_file(target_file_mutant_dir, mutant_code_filename):
    mutant_code_file = target_file_mutant_dir / mutant_code_filename
    assert mutant_code_file.exists(), f"Mutant code file {mutant_code_file} does not exist"

    return mutant_code_file

def get_buggy_lineno(target_file_mutant_dir, mutant_code_filename):
    # ex) parser.MUT123.c -> parser
    filename = mutant_code_filename.split('.')[0]

    mut_db_csv_name = f"{filename}_mut_db.csv"
    mut_db_csv = target_file_mutant_dir / mut_db_csv_name
    assert mut_db_csv.exists(), f"Mutant database csv file {mut_db_csv} does not exist"

    with mut_db_csv.open() as f:
        lines = f.readlines()
        for line in lines[2:]:
            mut_db_line = line.strip()
            info = line.strip().split(',')

            mut_name = info[0]
            if mut_name == mutant_code_filename:
                buggy_lineno = info[2]
                return buggy_lineno, mut_db_line


def intialize_directory_for_buggy_mutant(selected_buggy_versions_dir, mutant_name):
    # 1. initialize directory for selected buggy mutant
    selected_buggy_mutant_dir = selected_buggy_versions_dir / mutant_name
    selected_buggy_mutant_dir.mkdir(exist_ok=True)

    # 2. initialize directory for testsuite_info
    testsuite_info_dir = selected_buggy_mutant_dir / 'testsuite_info'
    testsuite_info_dir.mkdir(exist_ok=True)

    # 3. initialize directory for buggy_code_file
    buggy_code_file_dir = selected_buggy_mutant_dir / 'buggy_code_file'
    buggy_code_file_dir.mkdir(exist_ok=True)

    return selected_buggy_mutant_dir


def write_bug_info_csv(mutant_dir_dest, target_code_file, mutant_code_file, buggy_lineno, mut_db_line):
    bug_info_csv = mutant_dir_dest / 'bug_info.csv'
    with bug_info_csv.open(mode='w') as f:
        f.write("target_code_file,buggy_code_file,buggy_lineno\n")
        f.write(f"{target_code_file},{mutant_code_file},{buggy_lineno}")
    
    mutant_info_csv = mutant_dir_dest / 'mutant_info.csv'
    with mutant_info_csv.open(mode='w') as f:
        f.write(",,,Before Mutation,,,,,After Mutation\n")
        f.write("Mutant Filename,Mutation Operator,Start Line#,Start Col#,End Line#,End Col#,Target Token,Start Line#,Start Col#,End Line#,End Col#,Mutated Token,Extra Info\n")
        f.write(mut_db_line)


def copy_testsuite_info(selected_buggy_mutant_dir, mutant_dir_dest):
    testsuite_info_dir = mutant_dir_dest / 'testsuite_info'
    assert testsuite_info_dir.exists(), f"Testsuite info directory {testsuite_info_dir} does not exist"

    # 1. copy failing_tcs.txt
    failing_tcs_file = selected_buggy_mutant_dir / 'failing_tcs.txt'
    cmd = f"cp {failing_tcs_file} {testsuite_info_dir}"
    res = sp.call(cmd, shell=True)

    # 2. copy passing_tcs.txt
    passing_tcs_file = selected_buggy_mutant_dir / 'passing_tcs.txt'
    cmd = f"cp {passing_tcs_file} {testsuite_info_dir}"
    res = sp.call(cmd, shell=True)


def copy_contents(mutant_dir_dest, buggy_code_file):
    buggy_code_file_dir = mutant_dir_dest / 'buggy_code_file'
    assert buggy_code_file_dir.exists(), f"Buggy code file directory {buggy_code_file_dir} does not exist"

    mutant_name = buggy_code_file.name
    assert mutant_name == buggy_code_file.name, f"Mutant name {mutant_name} is not equal to buggy code file name {buggy_code_file.name}"

    cmd = f"cp {buggy_code_file} {buggy_code_file_dir}"
    res = sp.call(cmd, shell=True)



def get_buggy_mutants_list(buggy_mutant_dir):

    buggy_mutants_list = []
    for buggy_mutant in buggy_mutant_dir.iterdir():
        if buggy_mutant.is_dir():
            buggy_mutants_list.append(buggy_mutant)
    return buggy_mutants_list



def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    parser.add_argument('--num-versions', type=int, help='Number of buggy versions to select', required=True)
    return parser

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

if __name__ == "__main__":
    main()
