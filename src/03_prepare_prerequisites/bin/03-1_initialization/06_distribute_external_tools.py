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
prepare_prerequisites = bin_dir.parent

# General directories
src_dir = prepare_prerequisites.parent
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
    start_process(args.subject, args.buggy_versions_set)


def start_process(subject_name, buggy_versions_set):
    global configure_json_file

    subject_working_dir = prepare_prerequisites / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. make a list of buggy_versions: list, path to the buggy versions directory
    buggy_versions = get_buggy_versions(subject_name, buggy_versions_set)

    # 3. get machine-core information
    # machine_cores_list (list): [machine_name:core_id]
    machine_cores_list = get_machine_cores_list(configs, subject_working_dir)

    # # 4. distribute bugs to machine-cores equally
    # # distribution_machineCore2bugsList (dict): {machine_name:core_id: [buggy_version_dir_list]}
    distribution_machineCore2bugsList = assign_buggy_versions(configs, subject_working_dir, buggy_versions, machine_cores_list)

    # 3. distribute config directory to each machine-core
    distribute_external_tools(configs, subject_working_dir, distribution_machineCore2bugsList)


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

def get_buggy_versions(subject_name, buggy_versions_set):
    global src_dir
    
    # copy usable buggy versions directory to working directory
    select_usable_buggy_versions_dir = src_dir / '02_select_usable_buggy_versions'
    buggy_versions_working_dir = select_usable_buggy_versions_dir / f'{subject_name}-working_directory'
    buggy_versions_dir = buggy_versions_working_dir / buggy_versions_set
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


def distribute_external_tools(configs, subject_working_dir, distribution_machineCore2bugsList):
    global use_distributed_machines

    if configs[use_distributed_machines] == True:
        distribute_external_tools_distributed_machines(configs, subject_working_dir, distribution_machineCore2bugsList)


def distribute_external_tools_distributed_machines(configs, subject_working_dir, distribution_machineCore2bugsList):
    home_directory = configs['home_directory']
    subject_name = configs['subject_name']
    base_dir = f"{home_directory}{subject_name}-prepare_prerequisites/"
    machine_subject_working_dir = base_dir + f"{subject_name}-working_directory/"

    # item being sent
    ext_tool_dir = subject_working_dir / "external_tools"
    assert ext_tool_dir.exists(), f"Subject repository {ext_tool_dir} does not exist"

    bash_file = open('06-1_distribute_external_tools.sh', 'w')
    bash_file.write('date\n')
    cnt = 0
    laps = 50
    machine_list = []
    for machine_core, buggy_versions_list in distribution_machineCore2bugsList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]

        if machine_id not in machine_list:
            machine_list.append(machine_id)
            cmd = "scp -r {} {}:{} & \n".format(ext_tool_dir, machine_id, machine_subject_working_dir)
            bash_file.write(cmd)
        
            cnt += 1
            if cnt % laps == 0:
                bash_file.write("sleep 0.2s\n")
                bash_file.write("wait\n")
    
    bash_file.write('echo scp done, waiting...\n')
    bash_file.write('date\n')
    bash_file.write('wait\n')
    bash_file.write('date\n')
    
    cmd = ['chmod', '+x', '06-1_distribute_external_tools.sh']
    res = sp.call(cmd)

    # time.sleep(1)

    # cmd = ['./06-1_distribute_external_tools.sh']
    # print("Distributing subject repository to workers...")
    # res = sp.call(cmd)



def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    parser.add_argument('--buggy-versions-set', type=str, help='Buggy versions set', required=True)
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
