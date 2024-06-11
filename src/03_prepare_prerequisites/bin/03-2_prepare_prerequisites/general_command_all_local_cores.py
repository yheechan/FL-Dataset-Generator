#!/usr/bin/python3

from pathlib import Path
import subprocess as sp
import argparse
import json
import multiprocessing

# Current working directory
script_path = Path(__file__).resolve()
prepare_prerequisite_cmd_dir = script_path.parent
bin_dir = prepare_prerequisite_cmd_dir.parent
prepare_prerequisite_src_dir = bin_dir.parent

# General directories
src_dir = prepare_prerequisite_src_dir.parent
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



general_command_for_worker = 'general_command.py'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)


def start_process(subject_name):

    subject_working_dir = prepare_prerequisite_src_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 3. get machine-core information
    # machine_cores_list (list): [machine_name:core_id]
    machine_cores_list = get_from_local_machine(configs)


    jobs = []
    for machine_core in machine_cores_list:
        machine_name, core_id = machine_core.split(':')
        worker = f"{machine_name}/{core_id}"

        proc = multiprocessing.Process(
            target=execute_worker_function,
            args=(subject_name, worker)
        )

        jobs.append(proc)
        proc.start()
    
    for job in jobs:
        job.join()

    print('Successfully executed the worker scripts')

def execute_worker_function(subject_name, worker_name):
    # 1. Execute worker
    cmd = ['python3', general_command_for_worker, '--subject', subject_name, '--worker', worker_name]
    res = sp.run(cmd, stderr=sp.PIPE, stdout=sp.PIPE)
    if res.returncode != 0:
        raise Exception('Failed to execute worker script')
    
    print('Successfully executed the worker script: extracting MBFL features')


def get_from_local_machine(configs):
    machine_name = configs['single_machine']['machine_name']
    core_cnt = configs['single_machine']['machine_cores']

    machine_cores_list = []
    for num in range(core_cnt):
        core_id = f"core{num}"
        machine_cores_list.append(f"{machine_name}:{core_id}")
    
    return machine_cores_list


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