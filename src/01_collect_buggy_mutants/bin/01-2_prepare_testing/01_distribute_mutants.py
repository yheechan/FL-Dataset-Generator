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
clean_build_script = 'clean_build_script.sh'
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

    # 2. make a dictionary for mutants on each target file
    # mutant_list (tuple): (target_file, mutant_file)
    mutants_list = get_mutants_list(configs, subject_working_dir)

    # 3. get machine-core information
    # machine_cores_list (list): [machine_name:core_id]
    machine_cores_list = get_machine_cores_list(configs, subject_working_dir)

    # 4. distribute mutants to machine-cores equally
    # distribution_machineCore2mutantList (dict): {machine_name:core_id: [(target_file, mutant_file)]}
    distribution_machineCore2mutantList = distribute_mutants(configs, subject_working_dir, mutants_list, machine_cores_list)

    # 5. initialize directory for each machine-core
    initialize_directories(configs, subject_working_dir, distribution_machineCore2mutantList)

    # 6. distribute mutants to each machine-core
    distribute_mutants_to_workers(configs, subject_working_dir, distribution_machineCore2mutantList)



def get_mutants_list(configs, subject_working_dir):
    generated_mutants_dir = subject_working_dir / 'generated_mutants'

    subj_lang = None
    if configs["subject_language"] == "C":
        subj_lang = "*.c"
    elif configs["subject_language"] == "CPP":
        subj_lang = "*.cpp"
    else:
        raise Exception("Subject language is not supported")

    mutants_list = []
    for target_mutants_dir in generated_mutants_dir.iterdir():
        target_file = target_mutants_dir.name.replace('-', '/')

        target_mutants = list(target_mutants_dir.glob(subj_lang))
        for mutant in target_mutants:
            mutants_list.append((target_file, mutant))

        # print(f"Target file: {target_file}, Mutants: {len(target_mutants)}")
    
    print(f"Total mutants: {len(mutants_list)}")

    return mutants_list


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


def distribute_mutants(configs, subject_working_dir, mutants_list, machine_cores_list):

    # equally distribute the mutants in mutants_list to machine_cores_list
    distribution_machineCore2mutantList = {}
    for idx, (target_file, mutant) in enumerate(mutants_list):
        machine_core = machine_cores_list[idx % len(machine_cores_list)]

        if machine_core not in distribution_machineCore2mutantList:
            distribution_machineCore2mutantList[machine_core] = []
        
        distribution_machineCore2mutantList[machine_core].append((target_file, mutant))
    
    print(f"Mutants are distributed to {len(distribution_machineCore2mutantList)} machine-cores")
    # for machine_core, mutants in distribution_machineCore2mutantList.items():
    #     print(f"{machine_core}: {len(mutants)}")
    
    return distribution_machineCore2mutantList


def initialize_directories(configs, subject_working_dir, distribution_machineCore2mutantList):
    global use_distributed_machines

    if configs[use_distributed_machines] == True:
        initialize_directories_distributed_machines(configs, subject_working_dir, distribution_machineCore2mutantList)
    else:
        initialize_directories_single_machine(configs, subject_working_dir, distribution_machineCore2mutantList)


def initialize_directories_distributed_machines(configs, subject_working_dir, distribution_machineCore2mutantList):
    home_directory = configs['home_directory']
    subject_name = configs['subject_name']
    base_dir = f"{home_directory}{subject_name}-collect_buggy_mutants/"
    subject_working_dir = base_dir + f"{subject_name}-working_directory/"
    workers_dir = subject_working_dir + 'workers/'


    bash_file = open('01-1_initiate_directory.sh', 'w')
    bash_file.write('date\n')
    cnt = 0
    laps = 50
    for machine_core, mutants in distribution_machineCore2mutantList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machine_core_dir = f"{workers_dir}{machine_id}/{core_id}/assigned_mutations/"

        machines_bin_dir = f"{base_dir}bin/"

        machine_list = []
        if machine_id not in machine_list:
            machine_list.append(machine_id)
            cmd = 'ssh {} \"mkdir -p {}" & \n'.format(machine_id, machines_bin_dir)
            bash_file.write(cmd)

        target_directories = []
        for target_file, mutant in mutants:
            target_dir = mutant.parent.name
            if target_dir not in target_directories:
                
                target_directories.append(target_dir)
                cmd = 'ssh {} \"mkdir -p {}" & \n'.format(machine_id, machine_core_dir + target_dir)
                bash_file.write(cmd)


                cnt += 1
                if cnt % laps == 0:
                    bash_file.write("sleep 0.5s\n")
                    bash_file.write("wait\n")
        
        buggy_mutant_dir = f"{workers_dir}{machine_id}/{core_id}/buggy_mutants/"
        cmd = 'ssh {} \"mkdir -p {}" & \n'.format(machine_id, buggy_mutant_dir)
        bash_file.write(cmd)

    
    bash_file.write('echo ssh done, waiting...\n')
    bash_file.write('date\n')
    bash_file.write('wait\n')
    bash_file.write('date\n')
    
    cmd = ['chmod', '+x', '01-1_initiate_directory.sh']
    res = sp.call(cmd)

    # time.sleep(1)

    # cmd = ['./01-1_initiate_directory.sh']
    # print("Initiating directories for distributed machines...")
    # res = sp.call(cmd)

def initialize_directories_single_machine(configs, subject_working_dir, distribution_machineCore2mutantList):

    workers_dir = subject_working_dir / 'workers'
    workers_dir.mkdir(exist_ok=True)

    for machine_core, mutants in distribution_machineCore2mutantList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machine_core_dir = workers_dir / f"{machine_id}/{core_id}" / 'assigned_mutations'
        
        target_directories = []
        for target_file, mutant in mutants:
            target_dir = mutant.parent.name
            if target_dir not in target_directories:
                target_directories.append(target_dir)
                target_dir_path = machine_core_dir / target_dir
                target_dir_path.mkdir(exist_ok=True, parents=True)
        
        buggy_mutant_dir = workers_dir / f"{machine_id}/{core_id}" / 'buggy_mutants'
        buggy_mutant_dir.mkdir(exist_ok=True, parents=True)
        

def distribute_mutants_to_workers(configs, subject_working_dir, distribution_machineCore2mutantList):
    global use_distributed_machines

    if configs[use_distributed_machines] == True:
        distribute_mutants_to_workers_distributed_machines(configs, subject_working_dir, distribution_machineCore2mutantList)
    else:
        distribute_mutants_to_workers_single_machine(configs, subject_working_dir, distribution_machineCore2mutantList)

def distribute_mutants_to_workers_distributed_machines(configs, subject_working_dir, distribution_machineCore2mutantList):
    home_directory = configs['home_directory']
    subject_name = configs['subject_name']
    base_dir = f"{home_directory}{subject_name}-collect_buggy_mutants/{subject_name}-working_directory/workers/"

    bash_file = open('01-2_distribute_mutants.sh', 'w')
    bash_file.write('date\n')
    cnt = 0
    laps = 100
    for machine_core, mutants in distribution_machineCore2mutantList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machine_core_dir = f"{base_dir}{machine_id}/{core_id}/assigned_mutations/"

        for target_file, mutant in mutants:
            target_dir = mutant.parent.name
            cmd = 'scp {} {}:{} & \n'.format(mutant, machine_id, machine_core_dir + target_dir)
            bash_file.write(f"{cmd}")
        
            cnt += 1
            if cnt % laps == 0:
                bash_file.write("sleep 0.2s\n")
                bash_file.write("wait\n")
    
    bash_file.write('echo scp done, waiting...\n')
    bash_file.write('date\n')
    bash_file.write('wait\n')
    bash_file.write('date\n')
    
    cmd = ['chmod', '+x', '01-2_distribute_mutants.sh']
    res = sp.call(cmd)

    # time.sleep(1)

    # cmd = ['./01-2_distribute_mutants.sh']
    # print("Distributing mutants to workers...")
    # res = sp.call(cmd)


def distribute_mutants_to_workers_single_machine(configs, subject_working_dir, distribution_machineCore2mutantList):
    workers_dir = subject_working_dir / 'workers'

    for machine_core, mutants in distribution_machineCore2mutantList.items():
        machine_id = machine_core.split(':')[0]
        core_id = machine_core.split(':')[1]
        machine_core_dir = workers_dir / f"{machine_id}/{core_id}" / 'assigned_mutations'

        for target_file, mutant in mutants:
            target_dir = mutant.parent.name
            target_dir_path = machine_core_dir / target_dir
            mutant_path = target_dir_path / mutant.name
            mutant_path.symlink_to(mutant)

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
