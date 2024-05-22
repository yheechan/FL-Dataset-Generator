#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import time
import multiprocessing

# Current working directory
script_path = Path(__file__).resolve()
gen_mutants_dir = script_path.parent
bin_dir = gen_mutants_dir.parent
collect_buggy_mutants_dir = bin_dir.parent

# General directories
src_dir = collect_buggy_mutants_dir.parent
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

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)


def start_process(subject_name):
    global configure_json_file

    subject_working_dir = collect_buggy_mutants_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. initialize buggy_mutants directory
    buggy_mutant_dir = initialize_buggy_mutants_directory(configs, subject_working_dir)

    # 3. get machine-core information
    # machine_cores_list (list): [machine_name:core_id]
    machine_cores_list = get_machine_cores_list(configs, subject_working_dir)

    # 4. retrieve buggy mutants from workers
    retrieve_buggy_mutants(configs, subject_working_dir, buggy_mutant_dir, machine_cores_list)

def initialize_buggy_mutants_directory(configs, subject_working_dir):
    buggy_mutants_dir = subject_working_dir / 'buggy_mutants'
    buggy_mutants_dir.mkdir(exist_ok=True)
    return buggy_mutants_dir

def retrieve_buggy_mutants(configs, subject_working_dir, buggy_mutant_dir, machine_cores_list):
    global use_distributed_machines

    if configs[use_distributed_machines] == True:
        retrieve_buggy_mutants_distributed_machines(configs, subject_working_dir, buggy_mutant_dir, machine_cores_list)
    else:
        retrieve_buggy_mutants_single_machine(configs, subject_working_dir, buggy_mutant_dir, machine_cores_list)

def retrieve_buggy_mutants_distributed_machines(configs, subject_working_dir, buggy_mutant_dir, machine_cores_list):
    home_directory = configs['home_directory']
    subject_name = configs['subject_name']
    workers = f"{home_directory}{subject_name}-collect_buggy_mutants/{subject_name}-working_directory/workers/"

    bash_file = open('01-1_retrieve_buggy_mutants.sh', 'w')
    bash_file.write('date\n')
    cnt = 0
    laps = 100
    for machine_core in machine_cores_list:
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machine_core_dir = f"{workers}{machine_id}/{core_id}/buggy_mutants/*"

        cmd = 'scp -r {}:{} {} & \n'.format(machine_id, machine_core_dir, buggy_mutant_dir)
        bash_file.write(f"{cmd}")
        
        cnt += 1
        if cnt % laps == 0:
            bash_file.write("sleep 0.2s\n")
            bash_file.write("wait\n")
    
    bash_file.write('echo scp done, waiting...\n')
    bash_file.write('date\n')
    bash_file.write('wait\n')
    bash_file.write('date\n')
    
    cmd = ['chmod', '+x', '01-1_retrieve_buggy_mutants.sh']
    res = sp.call(cmd)

    # time.sleep(1)

    # cmd = ['./01-1_retrieve_buggy_mutants.sh']
    # print("Retrieving buggy mutants from workers...")
    # res = sp.call(cmd)


def retrieve_buggy_mutants_single_machine(configs, subject_working_dir, buggy_mutant_dir, machine_cores_list):
    workers_dir = subject_working_dir / 'workers'

    for machine_core in machine_cores_list:
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machine_core_bug_dir = workers_dir.__str__() + f"/{machine_id}/{core_id}/buggy_mutants/*"
        cmd = f"cp -r {machine_core_bug_dir} {buggy_mutant_dir}"
        res = sp.call(cmd, shell=True)
        
    print("Retrieved buggy mutants from workers")


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



def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
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
