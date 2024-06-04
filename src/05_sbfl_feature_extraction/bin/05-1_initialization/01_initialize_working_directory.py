#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp

# Current working directory
script_path = Path(__file__).resolve()
initialization_dir = script_path.parent
bin_dir = initialization_dir.parent
sbfl_feature_extraction_dir = bin_dir.parent

# General directories
src_dir = sbfl_feature_extraction_dir.parent
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



def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)


def start_process(subject_name):
    # 1. Read configurations
    configs = read_configs(subject_name)

    # 2. Initialize working directory
    initialize_working_directory(configs, subject_name)

def read_configs(subject_name):
    global user_configs_dir

    config_json = user_configs_dir / subject_name / 'configurations.json'
    
    configs = None
    with config_json.open() as f:
        configs = json.load(f)
    
    if configs is None:
        raise Exception('Configurations are not loaded')
    
    return configs

def initialize_working_directory(configs, subject_name):
    global sbfl_feature_extraction_dir, user_configs_dir, subjects_dir, external_tools_dir

    # Create working directory
    working_dir = sbfl_feature_extraction_dir / f'{subject_name}-working_directory'
    working_dir.mkdir(exist_ok=True)
    
    # Copy configure directory to working directory as <subject_name>-configures
    subject_config_dir = user_configs_dir / subject_name
    new_configure_dir = working_dir / f'{subject_name}-configures'
    cmd = ['cp', '-r', subject_config_dir, new_configure_dir]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy configure directory to working directory')
    
    print(f'Initialized working directory: {working_dir}')
    

def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser
    


if __name__ == "__main__":
    main()
