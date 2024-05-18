#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp

script_path = Path(__file__).resolve()
bin_dir = script_path.parent
action_dir = bin_dir.parent
src_dir = action_dir.parent

root_dir = src_dir.parent
working_dir = root_dir / 'working_directory'
working_dir.mkdir(exist_ok=True)
user_configs_dir = root_dir / 'user_configs'
subjects_dir = root_dir / 'subjects'

config_sh_wd = 'configure_script_working_directory'
build_sh_wd = 'build_script_working_directory'
configure_script = 'configure_no_cov_script.sh'
build_script = 'build_script.sh'



def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser


def read_configs(subject_name):
    config_json = user_configs_dir / subject_name / 'configurations.json'
    
    configs = None
    with config_json.open() as f:
        configs = json.load(f)
    
    if configs is None:
        raise Exception('Configurations are not loaded')
    
    return configs

def copy_subject_to_working_dir(subject_name):
    subject_dir = subjects_dir / subject_name
    working_subject_dir = working_dir / subject_name

    if working_subject_dir.exists():
        raise Exception('Working subject directory already exists')
    
    cmd = ['cp', '-r', subject_dir, working_dir]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy subject to working directory')
    
    print(f'Copied subject to working directory: {working_subject_dir}')

def copy_scripts_to_working_dir(subject_name, config_sh_wd, build_sh_wd):
    config_sh = user_configs_dir / subject_name / configure_script
    build_sh = user_configs_dir / subject_name / build_script

    working_config_sh = working_dir / config_sh_wd
    working_build_sh = working_dir / build_sh_wd

    cmd = ['cp', config_sh, working_config_sh]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy configure script to working directory')
    
    cmd = ['cp', build_sh, working_build_sh]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy build script to working directory')
    
    print(f'Copied configure & build script to working directory: {working_config_sh}')

def start_copy_process(subject_name):
    # 1. Read configurations
    configs = read_configs(subject_name)

    # 2. Copy subject to working directory
    copy_subject_to_working_dir(subject_name)

    # 3. Copy configure script and build script to working directory
    copy_scripts_to_working_dir(
        subject_name,
        configs[config_sh_wd],
        configs[build_sh_wd]
    )
    


if __name__ == "__main__":
    parser = make_parser()
    args = parser.parse_args()
    

    start_copy_process(args.subject)