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
refine_testsuite_dir = script_path.parent
bin_dir = refine_testsuite_dir.parent
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
ccts_txt = 'ccts.txt'
excluded_failing_txt = 'excluded_failing_tcs.txt'
excluded_passing_txt = 'excluded_passing_tcs.txt'
# excluded_txt = 'excluded_tcs.txt'
additional_failing_txt = 'additional_failing_tcs.txt'


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.mbfl_set_name)


def start_process(subject_name, mbfl_set_name):
    global configure_json_file

    subject_working_dir = mbfl_feature_extraction_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    mbfl_features_per_bug = get_buggy_versions(subject_working_dir, mbfl_set_name)

    # 3. rank buggy line with mbfl features
    total_additional_testcases = retrieve_total_additional_tcs(configs, mbfl_features_per_bug)

    # 4. write total_additional_tcs.txt to working directory
    total_additional_tcs_file = subject_working_dir / 'total_additional_tcs.txt'
    with open(total_additional_tcs_file, 'w') as f:
        content = '\n'.join(total_additional_testcases)
        f.write(content)
    
    # 5. copy total_additional_tcs.txt to testsuite_info directory of each buggy version
    include_total_additional_tcs_file(mbfl_features_per_bug, total_additional_tcs_file)


    # 6. distribute total_additional_tcs.txt to each buggy version
    machine_cores_list = get_machine_cores_list(configs, subject_working_dir)

    distribution_machineCore2bugsList = assign_buggy_versions(configs, subject_working_dir, mbfl_features_per_bug, machine_cores_list)

    distribute_buggy_versions_to_workers(configs, subject_working_dir, distribution_machineCore2bugsList)

def distribute_buggy_versions_to_workers(configs, subject_working_dir, distribution_machineCore2bugsList):
    global use_distributed_machines

    if configs[use_distributed_machines] == True:
        distribute_buggy_versions_to_workers_distributed_machines(configs, subject_working_dir, distribution_machineCore2bugsList)
    else:
        distribute_buggy_versions_to_workers_single_machine(configs, subject_working_dir, distribution_machineCore2bugsList)

def distribute_buggy_versions_to_workers_distributed_machines(configs, subject_working_dir, distribution_machineCore2bugsList):
    home_directory = configs['home_directory']
    subject_name = configs['subject_name']
    base_dir = f"{home_directory}{subject_name}-mbfl_feature_extraction/"
    machine_working_dir = base_dir + f'{subject_name}-working_directory/'
    workers_dir = machine_working_dir + 'workers_extracting_mbfl_features/'


    bash_file = open('04-1_distribute_total_additional_testsuite.sh', 'w')
    bash_file.write('date\n')
    cnt = 0
    laps = 100
    for machine_core, buggy_versions_list in distribution_machineCore2bugsList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machineCore_assigned_dir = f"{workers_dir}{machine_id}/{core_id}/assigned_buggy_versions/"

        for buggy_version_dir in buggy_versions_list:
            bug_name = buggy_version_dir.name
            bug_additional_tcs_file = buggy_version_dir / 'testsuite_info/total_additional_tcs.txt'
            destination = f"{machineCore_assigned_dir}{bug_name}/testsuite_info"
            # new_position = machineCore_assigned_dir + bug_name + '/'
            cmd = 'scp -r {} {}:{} & \n'.format(bug_additional_tcs_file, machine_id, machineCore_assigned_dir)
            bash_file.write(f"{cmd}")
        
            cnt += 1
            if cnt % laps == 0:
                bash_file.write("sleep 0.2s\n")
                bash_file.write("wait\n")
    
    bash_file.write('echo scp done, waiting...\n')
    bash_file.write('date\n')
    bash_file.write('wait\n')
    bash_file.write('date\n')
    
    cmd = ['chmod', '+x', '04-1_distribute_total_additional_testsuite.sh']
    res = sp.call(cmd)

    # time.sleep(1)

    # cmd = ['./04-1_distribute_total_additional_testsuite.sh']
    # print("Distributing mutants to workers...")
    # res = sp.call(cmd)


def distribute_buggy_versions_to_workers_single_machine(configs, subject_working_dir, distribution_machineCore2bugsList):
    workers_dir = subject_working_dir / 'workers_extracting_mbfl_features'

    for machine_core, buggy_versions_list in distribution_machineCore2bugsList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machineCore_assigned_dir = workers_dir / f"{machine_id}/{core_id}" / 'assigned_buggy_versions'

        for buggy_version_dir in buggy_versions_list:
            cmd = ['cp', '-r', buggy_version_dir, machineCore_assigned_dir]
            res = sp.call(cmd)

    print("Distributed mutants to workers")


def assign_buggy_versions(configs, subject_working_dir, buggy_versions, machine_cores_list):

    # equally distribute the bugs in buggy_verisons_list to machine_cores_list
    distribution_machineCore2bugsList = {}
    for idx, buggy_version_dir in enumerate(buggy_versions):
        machine_core = machine_cores_list[idx % len(machine_cores_list)]

        if machine_core not in distribution_machineCore2bugsList:
            distribution_machineCore2bugsList[machine_core] = []
        
        distribution_machineCore2bugsList[machine_core].append(buggy_version_dir)
    
    print(f"Buggy versions are assigned to {len(distribution_machineCore2bugsList)} machine-cores")
    # for machine_core, mutants in distribution_machineCore2bugsList.items():
    #     print(f"{machine_core}: {len(mutants)}")
    
    return distribution_machineCore2bugsList

def get_machine_cores_list(configs, subject_working_dir):
    global use_distributed_machines

    machine_cores_list = []
    if configs[use_distributed_machines] == True:
        machine_core_list = get_from_distributed_machines(configs, subject_working_dir)
    else:
        machine_core_list = get_from_local_machine(configs)

    print(f"Machine cores: {len(machine_core_list)}")
    
    return machine_core_list


def get_from_distributed_machines(configs, subject_working_dir):
    global machines_json_file

    subject_config_dir = subject_working_dir / f"{configs['subject_name']}-configures"
    assert subject_config_dir.exists(), f"Subject configurations directory {subject_config_dir} does not exist"

    machines_json = subject_config_dir / machines_json_file
    assert machines_json.exists(), f'Machines json file {machines_json} does not exist'


    machines = {}
    with machines_json.open() as f:
        machines = json.load(f)


    machine_cores_list = []
    for machine_name, core_cnt in machines.items():
        for num in range(core_cnt):
            core_id = f"core{num}"
            machine_cores_list.append(f"{machine_name}:{core_id}")
    
    if machines is None:
        raise Exception('Machines are not loaded')
    
    return machine_cores_list

def get_from_local_machine(configs):
    machine_name = configs['single_machine']['machine_name']
    core_cnt = configs['single_machine']['machine_cores']

    machine_cores_list = []
    for num in range(core_cnt):
        core_id = f"core{num}"
        machine_cores_list.append(f"{machine_name}:{core_id}")
    
    return machine_cores_list

def include_total_additional_tcs_file(mbfl_features_per_bug, total_additional_tcs_file):
    for bug_dir in mbfl_features_per_bug:
        testsuite_info_dir = bug_dir / 'testsuite_info'
        assert testsuite_info_dir.exists(), f"Testsuite info directory {testsuite_info_dir} does not exist"

        total_additional_tcs_file_dest = testsuite_info_dir / 'total_additional_tcs.txt'
        sp.run(['cp', total_additional_tcs_file, total_additional_tcs_file_dest])

def retrieve_total_additional_tcs(configs, mbfl_features_per_bug):

    total_additional_testcases = set()

    for idx, bug_dir in enumerate(mbfl_features_per_bug):
        bug_name = bug_dir.name
        # if bug_name != 'relaxng.MUT4445.c': continue
        print(f"\n{idx+1}/{len(mbfl_features_per_bug)}: {bug_name}")

        # GET: mbfl_features.csv
        mbfl_features_csv_file = bug_dir / 'mbfl_features.csv'
        assert mbfl_features_csv_file.exists(), f"MBFL features file {mbfl_features_csv_file} does not exist"

        # GET: list of failing TCs
        additional_failing_tcs = get_tcs(bug_dir, 'additional_failing_tcs.txt')
        additional_failing_tcs = set(additional_failing_tcs)
        total_additional_testcases.update(additional_failing_tcs)

    total_additional_testcases = sorted(total_additional_testcases, key=custome_sort)
    return total_additional_testcases


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
    parser.add_argument('--mbfl-set-name', type=str, help='MBFL set name', required=True)
    return parser
    


if __name__ == "__main__":
    main()