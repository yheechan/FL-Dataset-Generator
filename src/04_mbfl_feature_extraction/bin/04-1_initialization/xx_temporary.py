#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import time
import multiprocessing

# Current working directory
script_path = Path(__file__).resolve()
initialization_dir = script_path.parent
bin_dir = initialization_dir.parent
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
real_world_buggy_versions = 'real_world_buggy_versions'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)


def start_process(subject_name):
    global configure_json_file, mbfl_feature_extraction_dir

    subject_working_dir = mbfl_feature_extraction_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. make a list of buggy_versions: list, path to the buggy versions directory
    buggy_versions = get_buggy_versions(subject_name)

    # 3. get machine-core information
    # machine_cores_list (list): [machine_name:core_id]
    machine_cores_list = get_machine_cores_list(configs, subject_working_dir)

    # # 4. distribute bugs to machine-cores equally
    # # distribution_machineCore2bugsList (dict): {machine_name:core_id: [buggy_version_dir_list]}
    distribution_machineCore2bugsList = assign_buggy_versions(configs, subject_working_dir, buggy_versions, machine_cores_list)

    # # 5. initialize directory for each machine-core
    # initialize_directories(configs, subject_working_dir, distribution_machineCore2bugsList)

    # # 6. distribute mutants to each machine-core
    distribute_buggy_versions_to_workers(configs, subject_working_dir, distribution_machineCore2bugsList)



def get_buggy_versions(subject_name):
    global src_dir
    
    # copy usable buggy versions directory to working directory
    prepare_prerequisites_dir = src_dir / '03_prepare_prerequisites'
    subject_working_dir = prepare_prerequisites_dir / f'{subject_name}-working_directory'
    buggy_versions_dir = subject_working_dir / 'prerequisite_data'
    assert buggy_versions_dir.exists(), 'Buggy versions directory does not exist'

    buggy_versions = []
    for bug_version_dir in buggy_versions_dir.iterdir():
        buggy_versions.append(bug_version_dir)
    
    print(f"Total buggy versions: {len(buggy_versions)}")

    return buggy_versions


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


def initialize_directories(configs, subject_working_dir, distribution_machineCore2bugsList):
    global use_distributed_machines

    if configs[use_distributed_machines] == True:
        initialize_directories_distributed_machines(configs, subject_working_dir, distribution_machineCore2bugsList)
    else:
        initialize_directories_single_machine(configs, subject_working_dir, distribution_machineCore2bugsList)


def initialize_directories_distributed_machines(configs, subject_working_dir, distribution_machineCore2bugsList):
    home_directory = configs['home_directory']
    subject_name = configs['subject_name']
    base_dir = f"{home_directory}{subject_name}-mbfl_feature_extraction/"
    subject_working_dir = base_dir + f"{subject_name}-working_directory/"
    workers_dir = subject_working_dir + 'workers_extracting_mbfl_features/'


    bash_file = open('02-1_initiate_directory.sh', 'w')
    bash_file.write('date\n')
    cnt = 0
    laps = 50
    for machine_core, buggy_versions_list in distribution_machineCore2bugsList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machine_core_dir = f"{workers_dir}{machine_id}/{core_id}/assigned_buggy_versions/"

        # 1. create assigned dir
        cmd = 'ssh {} \"mkdir -p {}" & \n'.format(machine_id, machine_core_dir)
        bash_file.write(cmd)

        cnt += 1
        if cnt % laps == 0:
            bash_file.write("sleep 0.5s\n")
            bash_file.write("wait\n")

        # 2. create machines bin dir
        machines_bin_dir = f"{base_dir}bin/"
        machine_list = []
        if machine_id not in machine_list:
            machine_list.append(machine_id)
            cmd = 'ssh {} \"mkdir -p {}" & \n'.format(machine_id, machines_bin_dir)
            bash_file.write(cmd)
        
        cnt += 1
        if cnt % laps == 0:
            bash_file.write("sleep 0.5s\n")
            bash_file.write("wait\n")

        
        # 3. create directory for generated mutants
        coverage_dir = f"{workers_dir}{machine_id}/{core_id}/generated_mutants/"
        cmd = 'ssh {} \"mkdir -p {}" & \n'.format(machine_id, coverage_dir)
        bash_file.write(cmd)

        cnt += 1
        if cnt % laps == 0:
            bash_file.write("sleep 0.5s\n")
            bash_file.write("wait\n")
        
        # 4. create directory for per_mutant_info
        mutant_data_dir = f"{workers_dir}{machine_id}/{core_id}/mutant_data/"
        cmd = 'ssh {} \"mkdir -p {}" & \n'.format(machine_id, mutant_data_dir)
        bash_file.write(cmd)

        cnt += 1
        if cnt % laps == 0:
            bash_file.write("sleep 0.5s\n")
            bash_file.write("wait\n")
    
    bash_file.write('echo ssh done, waiting...\n')
    bash_file.write('date\n')
    bash_file.write('wait\n')
    bash_file.write('date\n')
    
    cmd = ['chmod', '+x', '02-1_initiate_directory.sh']
    res = sp.call(cmd)

    # time.sleep(1)

    # cmd = ['./02-1_initiate_directory.sh']
    # print("Initiating directories for distributed machines...")
    # res = sp.call(cmd)

def initialize_directories_single_machine(configs, subject_working_dir, distribution_machineCore2bugsList):

    workers_dir = subject_working_dir / 'workers_extracting_mbfl_features'
    workers_dir.mkdir(exist_ok=True)

    for machine_core, buggy_version_list in distribution_machineCore2bugsList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machine_core_dir = workers_dir / f"{machine_id}/{core_id}" / 'assigned_buggy_versions'
        machine_core_dir.mkdir(exist_ok=True, parents=True)
        
        buggy_mutant_dir = workers_dir / f"{machine_id}/{core_id}" / 'generated_mutants'
        buggy_mutant_dir.mkdir(exist_ok=True, parents=True)

        mutant_data_dir = workers_dir / f"{machine_id}/{core_id}" / 'mutant_data'
        mutant_data_dir.mkdir(exist_ok=True, parents=True)
        

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


    bash_file = open('xx.sh', 'w')
    bash_file.write('date\n')
    cnt = 0
    laps = 100
    for machine_core, buggy_versions_list in distribution_machineCore2bugsList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        core_dir = f"{workers_dir}{machine_id}/{core_id}/"
        machineCore_assigned_dir = f"{workers_dir}{machine_id}/{core_id}/assigned_buggy_versions/"

        for buggy_version_dir in buggy_versions_list:
            bug_name = buggy_version_dir.name

            cmd = 'ssh {} \"cp {}mutant_data/{}/selected_mutants.csv {}{}\" & \n'.format(machine_id, core_dir, bug_name, machineCore_assigned_dir, bug_name)
            bash_file.write(f"{cmd}")
        
            cnt += 1
            if cnt % laps == 0:
                bash_file.write("sleep 0.2s\n")
                bash_file.write("wait\n")

            cmd = 'ssh {} \"cp {}mutant_data/{}/mutation_testing_results.csv {}{}\" & \n'.format(machine_id, core_dir, bug_name, machineCore_assigned_dir, bug_name)
            bash_file.write(f"{cmd}")
        
            cnt += 1
            if cnt % laps == 0:
                bash_file.write("sleep 0.2s\n")
                bash_file.write("wait\n")
    
    bash_file.write('echo scp done, waiting...\n')
    bash_file.write('date\n')
    bash_file.write('wait\n')
    bash_file.write('date\n')
    
    cmd = ['chmod', '+x', 'xx.sh']
    res = sp.call(cmd)

    # time.sleep(1)

    # cmd = ['./xx.sh']
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
